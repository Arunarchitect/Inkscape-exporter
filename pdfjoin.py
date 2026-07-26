"""
pdfjoin.py  -  Merge existing PDF files into one, in a user-chosen order,
with optional image downsampling to control output size/quality.

Design mirrors vector.py's conventions in this project:
  - global_log_callback + _log() for GUI logging
  - _downsample_pdf_images(): same raster-budget technique as vector.py
    (page-size-based max pixel budget, resample + recompress as JPEG)
  - merge_pdfs_ordered(): builds the merged PDF with pikepdf (preferred)
    or falls back to pypdf/PyPDF2 if pikepdf isn't installed
      (fallback has no compression support)

Requires:  pip install pikepdf Pillow      (pypdf optional fallback)
"""

import io
import os
import sys
import tempfile

# ---------------------------------------------------------------------------
# Module-level log callback
# ---------------------------------------------------------------------------
global_log_callback = None


def _log(message):
    if global_log_callback:
        global_log_callback(message)
    else:
        try:
            print(message)
        except UnicodeEncodeError:
            print(message.encode('ascii', 'ignore').decode('ascii'))


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def get_pdf_files(folder_path):
    try:
        return sorted(
            (f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')),
            key=str.lower)
    except OSError as e:
        _log(f"[ERROR] Cannot list folder {folder_path}: {e}")
        return []


# ---------------------------------------------------------------------------
# DPI / quality helper (same mapping as vector.py, kept consistent)
# ---------------------------------------------------------------------------

def jpeg_quality_for_dpi(dpi_int):
    if dpi_int >= 300: return 92
    if dpi_int >= 150: return 85
    if dpi_int >= 96:  return 72
    if dpi_int >= 72:  return 60
    return 45


# ---------------------------------------------------------------------------
# Raster downsampler (same technique as vector.py's _downsample_pdf_images,
# generalised to any source PDF, not just Inkscape output)
# ---------------------------------------------------------------------------

def downsample_pdf_images(pdf_path, target_dpi, log_fn=None):
    def mlog(m):
        (log_fn or _log)(m)

    try:
        import pikepdf
    except ImportError:
        mlog("  [WARN] pikepdf not installed -- downsampling skipped.")
        mlog("         pip install pikepdf")
        return False
    try:
        from PIL import Image
    except ImportError:
        mlog("  [WARN] Pillow not installed -- downsampling skipped.")
        mlog("         pip install Pillow")
        return False

    target_dpi   = int(target_dpi)
    jpeg_quality = jpeg_quality_for_dpi(target_dpi)
    mlog(f"  [RESAMPLE] target={target_dpi} dpi, JPEG quality={jpeg_quality}")

    try:
        pdf = pikepdf.open(pdf_path, allow_overwriting_input=False)
    except Exception as e:
        mlog(f"  [WARN] Cannot open PDF for resampling: {e}")
        return False

    resampled        = 0
    skipped          = 0
    errors           = 0
    processed_objids = set()

    def _process_resources(resources, max_px):
        nonlocal resampled, skipped, errors

        xobjs = resources.get('/XObject', None)
        if xobjs is None:
            return

        for key in list(xobjs.keys()):
            try:
                xobj = xobjs[key]
            except Exception:
                continue

            subtype = xobj.get('/Subtype', '')

            if subtype == '/Form':
                sub_res = xobj.get('/Resources', None)
                if sub_res is not None:
                    _process_resources(sub_res, max_px)
                continue

            if subtype != '/Image':
                continue

            try:
                obj_id = xobj.objgen
            except Exception:
                obj_id = id(xobj)
            if obj_id in processed_objids:
                continue
            processed_objids.add(obj_id)

            try:
                img_w = int(xobj['/Width'])
                img_h = int(xobj['/Height'])
            except Exception:
                skipped += 1
                continue

            longer_edge = max(img_w, img_h)
            if longer_edge <= max_px:
                skipped += 1
                continue

            scale = max_px / longer_edge
            new_w = max(1, int(round(img_w * scale)))
            new_h = max(1, int(round(img_h * scale)))

            try:
                raw        = bytes(xobj.read_raw_bytes())
                filters    = xobj.get('/Filter', None)
                filter_str = str(filters) if filters is not None else ''
                cs_str     = str(xobj.get('/ColorSpace', '/DeviceRGB'))

                img = None

                if 'DCTDecode' in filter_str:
                    img = Image.open(io.BytesIO(raw))

                elif 'FlateDecode' in filter_str:
                    import zlib
                    try:
                        raw = zlib.decompress(raw)
                    except Exception as ze:
                        mlog(f"  [WARN] zlib failed for {key}: {ze}")
                        skipped += 1
                        continue
                    if 'Gray' in cs_str or 'gray' in cs_str:
                        mode, bpp = 'L', 1
                    elif 'CMYK' in cs_str:
                        mode, bpp = 'CMYK', 4
                    else:
                        mode, bpp = 'RGB', 3
                    expected = img_w * img_h * bpp
                    if len(raw) < expected:
                        skipped += 1
                        continue
                    img = Image.frombytes(mode, (img_w, img_h), raw[:expected])

                elif not filter_str or filter_str in ('None', '[]', '/None'):
                    if 'Gray' in cs_str or 'gray' in cs_str:
                        mode, bpp = 'L', 1
                    elif 'CMYK' in cs_str:
                        mode, bpp = 'CMYK', 4
                    else:
                        mode, bpp = 'RGB', 3
                    expected = img_w * img_h * bpp
                    if len(raw) < expected:
                        skipped += 1
                        continue
                    img = Image.frombytes(mode, (img_w, img_h), raw[:expected])

                else:
                    mlog(f"  [SKIP] {key}: unsupported filter {filter_str!r}")
                    skipped += 1
                    continue

                if img is None:
                    skipped += 1
                    continue

                img_rs = img.resize((new_w, new_h), Image.LANCZOS)
                if img_rs.mode in ('RGBA', 'LA', 'P'):
                    img_rs = img_rs.convert('RGB')

                buf = io.BytesIO()
                img_rs.save(buf, format='JPEG', quality=jpeg_quality, optimize=True)
                jpeg_bytes = buf.getvalue()

                xobj.write(jpeg_bytes, filter=pikepdf.Name('/DCTDecode'))
                xobj['/Width']            = pikepdf.Integer(new_w)
                xobj['/Height']           = pikepdf.Integer(new_h)
                xobj['/BitsPerComponent'] = pikepdf.Integer(8)
                if img_rs.mode == 'L':
                    xobj['/ColorSpace'] = pikepdf.Name('/DeviceGray')
                elif img_rs.mode == 'CMYK':
                    xobj['/ColorSpace'] = pikepdf.Name('/DeviceCMYK')
                else:
                    xobj['/ColorSpace'] = pikepdf.Name('/DeviceRGB')
                for dp in ('/DecodeParms', '/DP'):
                    if dp in xobj:
                        del xobj[dp]

                resampled += 1
                mlog(f"  [RESAMPLE] {key}: {img_w}x{img_h} -> {new_w}x{new_h} "
                     f"(budget {max_px}px, q={jpeg_quality})")

            except Exception as ie:
                mlog(f"  [WARN] Image {key} failed: {ie}")
                errors += 1

    for page_idx, page in enumerate(pdf.pages):
        try:
            mb     = page.mediabox
            w_pt   = abs(float(mb[2]) - float(mb[0]))
            h_pt   = abs(float(mb[3]) - float(mb[1]))
            max_px = max(32, int(max(w_pt, h_pt) / 72.0 * target_dpi))
        except Exception:
            max_px = target_dpi * 8

        try:
            res = page.get('/Resources', None)
            if res is not None:
                _process_resources(res, max_px)
        except Exception as pe:
            mlog(f"  [WARN] Page {page_idx+1} error: {pe}")

    mlog(f"  [RESAMPLE] Done: {resampled} resampled, "
         f"{skipped} skipped (within budget), {errors} errors.")

    if resampled == 0:
        pdf.close()
        return False

    tmp_out = pdf_path + '._rs_tmp'
    try:
        pdf.save(tmp_out)
        pdf.close()
        os.replace(tmp_out, pdf_path)
        sz = os.path.getsize(pdf_path)
        mlog(f"  [RESAMPLE] Saved. Final PDF size: {sz:,} bytes")
        return True
    except Exception as se:
        try:
            pdf.close()
        except Exception:
            pass
        try:
            os.unlink(tmp_out)
        except Exception:
            pass
        mlog(f"  [WARN] Could not save resampled PDF: {se}")
        return False


# ---------------------------------------------------------------------------
# Merge (order-preserving, whole files -> consecutive page blocks)
# ---------------------------------------------------------------------------

def merge_pdfs_ordered(pdf_paths, output_pdf_path,
                       compress=False, target_dpi=150,
                       log_callback=None, progress_callback=None):
    """
    Merge pdf_paths (list, in the exact order supplied) into output_pdf_path.

    compress=True  -> after merging, run downsample_pdf_images() on the
                       merged file at target_dpi to shrink embedded rasters.
                       Vector content / text is untouched, same as vector.py.
    """
    global global_log_callback
    global_log_callback = log_callback

    output_abs = os.path.abspath(output_pdf_path)
    valid_pdfs = [p for p in pdf_paths
                  if os.path.abspath(p) != output_abs
                  and os.path.isfile(p)
                  and os.path.getsize(p) > 0]

    if not valid_pdfs:
        _log("[ERROR] No valid PDFs to merge")
        return False

    os.makedirs(os.path.dirname(output_abs) or '.', exist_ok=True)

    total = len(valid_pdfs)
    _log("=" * 60)
    _log(f"[JOIN] Merging {total} PDF(s) in the order given ->")
    _log(f"       {output_abs}")
    _log("=" * 60)

    use_pikepdf = False
    try:
        import pikepdf
        use_pikepdf = True
    except ImportError:
        pass

    try:
        if use_pikepdf:
            import pikepdf
            out = pikepdf.Pdf.new()
            for i, p in enumerate(valid_pdfs, 1):
                _log(f"  [{i}/{total}] + {os.path.basename(p)}")
                if progress_callback:
                    progress_callback(i - 1, total, f"Adding: {os.path.basename(p)}")
                src = pikepdf.Pdf.open(p)
                out.pages.extend(src.pages)
                src.close()
            out.save(output_pdf_path)
            out.close()
        else:
            use_pypdf_writer = use_pypdf_merger = use_pypdf2 = False
            try:
                import pypdf as _p
                if hasattr(_p, 'PdfWriter'):   use_pypdf_writer = True
                elif hasattr(_p, 'PdfMerger'): use_pypdf_merger = True
            except ImportError:
                pass
            if not use_pypdf_writer and not use_pypdf_merger:
                try:
                    import PyPDF2
                    use_pypdf2 = True
                except ImportError:
                    pass
            if not any([use_pypdf_writer, use_pypdf_merger, use_pypdf2]):
                _log("[ERROR] No PDF library available. "
                     "pip install pikepdf  (recommended, also enables compression)")
                return False

            _log("  [WARN] pikepdf not installed -- compression option will be "
                 "ignored. pip install pikepdf for size/quality control.")

            if use_pypdf_writer:
                import pypdf
                w = pypdf.PdfWriter()
                for i, p in enumerate(valid_pdfs, 1):
                    _log(f"  [{i}/{total}] + {os.path.basename(p)}")
                    if progress_callback:
                        progress_callback(i - 1, total, f"Adding: {os.path.basename(p)}")
                    for pg in pypdf.PdfReader(p).pages:
                        w.add_page(pg)
                with open(output_pdf_path, 'wb') as fh:
                    w.write(fh)
            elif use_pypdf_merger:
                import pypdf
                m = pypdf.PdfMerger()
                for i, p in enumerate(valid_pdfs, 1):
                    _log(f"  [{i}/{total}] + {os.path.basename(p)}")
                    if progress_callback:
                        progress_callback(i - 1, total, f"Adding: {os.path.basename(p)}")
                    m.append(p)
                with open(output_pdf_path, 'wb') as fh:
                    m.write(fh)
                m.close()
            else:
                import PyPDF2
                m = PyPDF2.PdfMerger()
                for i, p in enumerate(valid_pdfs, 1):
                    _log(f"  [{i}/{total}] + {os.path.basename(p)}")
                    if progress_callback:
                        progress_callback(i - 1, total, f"Adding: {os.path.basename(p)}")
                    m.append(p)
                with open(output_pdf_path, 'wb') as fh:
                    m.write(fh)
                m.close()
            compress = False  # no pikepdf => can't downsample

        if progress_callback:
            progress_callback(total, total, "Merge complete, finalizing...")

        if not (os.path.isfile(output_pdf_path) and os.path.getsize(output_pdf_path) > 0):
            _log(f"[ERROR] Merge produced no file: {output_pdf_path}")
            return False

        sz_before = os.path.getsize(output_pdf_path)
        _log(f"[OK] Merged {total} file(s) -> {output_pdf_path} ({sz_before:,} bytes)")

        if compress:
            _log("-" * 60)
            _log(f"[JOIN] Downsampling embedded images to {target_dpi} dpi ...")
            ok = downsample_pdf_images(output_pdf_path, target_dpi, log_fn=_log)
            sz_after = os.path.getsize(output_pdf_path)
            if ok:
                pct = 100 * (1 - sz_after / sz_before) if sz_before else 0
                _log(f"[OK] Compressed: {sz_before:,} -> {sz_after:,} bytes "
                     f"({pct:.1f}% smaller)")
            else:
                _log("[INFO] No images were downsampled (already within budget, "
                     "or pikepdf/Pillow missing).")

        _log("=" * 60)
        return True

    except Exception as e:
        _log(f"[ERROR] Merge failed: {e}")
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print("Usage: python pdfjoin.py <output.pdf> <in1.pdf> <in2.pdf> ... "
              "[--dpi=150]")
        return 1
    output = sys.argv[1]
    inputs = []
    dpi    = None
    for arg in sys.argv[2:]:
        if arg.startswith('--dpi='):
            dpi = int(arg.split('=', 1)[1])
        else:
            inputs.append(arg)
    ok = merge_pdfs_ordered(inputs, output, compress=dpi is not None,
                            target_dpi=dpi or 150)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())