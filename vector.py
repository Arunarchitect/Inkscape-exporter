"""
vector.py  -  SVG to PDF batch converter (vector-preserving)

Key design decisions
--------------------
1.  Each SVG is exported to PDF in a SINGLE Inkscape call with no
    --export-page flag.  Inkscape 1.2+ automatically writes every page
    of a multi-page SVG into one multi-page PDF.

2.  A page-by-page fallback is still available for very old Inkscape builds.

3.  ALL external references are resolved and inlined BEFORE handing the
    file to Inkscape:
      a) Raster images (<image href="photo.png">) -> base64 data URI.
      b) Linked SVG files (<image href="other.svg"> or
         <use href="other.svg#id">) -> SVG content inlined directly.

4.  SVGs are sanitized to remove malformed empty path elements (d="M Z")
    that cause Inkscape warnings and export failures.

5.  Temp files during preparation are always placed in the SAME directory
    as the source SVG so relative hrefs still resolve.

6.  os.chdir() is NEVER used.

7.  batch_convert() accepts an optional merged_pdf_path parameter.
    When auto_merge_pdf=True all per-SVG PDFs are merged into one final
    PDF at that path (or <output_path>/merged_output.pdf if not given).

8.  DPI DOWNSAMPLING  (fix for "72 dpi same file size as 300 dpi")
    ---------------------------------------------------------------
    Inkscape's --export-dpi does NOT resample raster images already embedded
    in the SVG -- they land in the PDF at full original resolution regardless
    of the DPI flag.  That is why file size did not change.

    Fix: after Inkscape writes the PDF we open it with pikepdf, find every
    raster XObject, and resample it with Pillow so that its longer pixel
    edge never exceeds:

        max_px = (page_longer_edge_inches) * target_dpi

    Example: A4 page (11.69 in) at 72 dpi -> cap = 842 px.
    A 3000 px photo shrinks to 842 px and is recompressed as JPEG.
    Vector paths, text, gradients are completely untouched.
    Shared XObjects (same image used multiple times) are processed once.
    Form XObjects (nested content) are recursed into.

    DPI -> JPEG quality:
        dpi >= 300 -> 92    dpi 150-299 -> 85
        dpi  96-149 -> 72   dpi  72-95  -> 60    dpi < 72 -> 45

    Requires:  pip install pikepdf Pillow
"""

import base64
import copy
import io
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Module-level log callback
# ---------------------------------------------------------------------------
global_log_callback = None

NS_SVG      = 'http://www.w3.org/2000/svg'
NS_INK      = 'http://www.inkscape.org/namespaces/inkscape'
NS_XLINK    = 'http://www.w3.org/1999/xlink'
NS_SODIPODI = 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd'

_NAMESPACES = {
    '':          NS_SVG,
    'svg':       NS_SVG,
    'inkscape':  NS_INK,
    'xlink':     NS_XLINK,
    'sodipodi':  NS_SODIPODI,
    'dc':        'http://purl.org/dc/elements/1.1/',
    'cc':        'http://creativecommons.org/ns#',
    'rdf':       'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
}
for _pfx, _uri in _NAMESPACES.items():
    ET.register_namespace(_pfx, _uri)


def _safe_tostring(root):
    for _pfx, _uri in _NAMESPACES.items():
        ET.register_namespace(_pfx, _uri)
    return ET.tostring(root, encoding='unicode', xml_declaration=False)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log(message):
    if global_log_callback:
        global_log_callback(message)
    else:
        msg = message
        for u, a in {'->': '->', '\u2192': '->'}.items():
            msg = msg.replace(u, a)
        try:
            print(msg)
        except UnicodeEncodeError:
            print(msg.encode('ascii', 'ignore').decode('ascii'))


# ---------------------------------------------------------------------------
# File utilities
# ---------------------------------------------------------------------------

def get_svg_files(folder_path):
    try:
        return sorted(
            (f for f in os.listdir(folder_path) if f.lower().endswith('.svg')),
            key=str.lower)
    except OSError as e:
        _log(f"[ERROR] Cannot list folder {folder_path}: {e}")
        return []


# ---------------------------------------------------------------------------
# SVG sanitizer
# ---------------------------------------------------------------------------

def _sanitize_svg_content(content):
    try:
        root      = ET.fromstring(content)
        bad_pairs = []
        for parent in root.iter():
            for child in list(parent):
                if not child.tag.endswith('}path') and child.tag != 'path':
                    continue
                d = child.get('d', '').strip()
                if not d or re.match(r'^[Mm]\s*[Zz]?\s*$', d):
                    bad_pairs.append((parent, child))
        for parent, child in bad_pairs:
            parent.remove(child)
        if bad_pairs:
            _log(f"  [SANITIZE] Removed {len(bad_pairs)} empty/malformed path(s).")
            return _safe_tostring(root)
        return content
    except Exception as e:
        _log(f"  [WARN] Sanitization skipped: {e}")
        return content


# ---------------------------------------------------------------------------
# External-resource embedder
# ---------------------------------------------------------------------------

def _resolve_href(href, svg_dir):
    if not href:
        return None, ''
    if href.startswith('data:') or href.startswith('http://') \
            or href.startswith('https://') or href.startswith('//'):
        return None, ''
    fragment = ''
    if '#' in href:
        href, fragment = href.split('#', 1)
    if not href:
        return None, fragment
    path = href if os.path.isabs(href) \
        else os.path.normpath(os.path.join(svg_dir, href))
    if not os.path.isfile(path):
        candidate = os.path.join(svg_dir, os.path.basename(href))
        if os.path.isfile(candidate):
            path = candidate
    return (path if os.path.isfile(path) else None), fragment


def _find_parent(root, target):
    for parent in root.iter():
        if target in list(parent):
            return parent
    return None


def _inline_svg_file(linked_svg_path, fragment, seen=None):
    if seen is None:
        seen = set()
    abs_path = os.path.abspath(linked_svg_path)
    if abs_path in seen:
        _log(f"  [WARN] Circular SVG reference, skipping: {linked_svg_path}")
        return None
    seen.add(abs_path)
    try:
        with open(linked_svg_path, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()
        content, _ = _embed_all_resources(content, os.path.dirname(abs_path),
                                          seen=set(seen))
        linked_root = ET.fromstring(content)
        if fragment:
            for el in linked_root.iter():
                if el.get('id') == fragment:
                    return el
            return None
        return linked_root
    except Exception as e:
        _log(f"  [WARN] Could not inline {os.path.basename(linked_svg_path)}: {e}")
        return None


def _embed_all_resources(svg_content, svg_dir, seen=None):
    if seen is None:
        seen = set()
    try:
        root    = ET.fromstring(svg_content)
        changes = 0

        for elem in list(root.iter(f'{{{NS_SVG}}}image')):
            for attr in (f'{{{NS_XLINK}}}href', 'href'):
                href = elem.get(attr, '').strip()
                if not href or href.startswith('data:'):
                    continue
                file_path, fragment = _resolve_href(href, svg_dir)
                if file_path is None:
                    _log(f"  [WARN] Cannot find: {href!r}")
                    continue
                ext = os.path.splitext(file_path)[1].lower()
                if ext == '.svg':
                    linked = _inline_svg_file(file_path, fragment, seen=set(seen))
                    if linked is not None:
                        for geo in ('x', 'y', 'width', 'height', 'id',
                                    'style', 'transform', 'preserveAspectRatio'):
                            val = elem.get(geo)
                            if val:
                                linked.set(geo, val)
                        parent = _find_parent(root, elem)
                        if parent is not None:
                            idx = list(parent).index(elem)
                            parent.remove(elem)
                            parent.insert(idx, linked)
                            changes += 1
                else:
                    mime, _ = mimetypes.guess_type(file_path)
                    if not mime:
                        mime = 'image/png'
                    try:
                        with open(file_path, 'rb') as fh:
                            b64 = base64.b64encode(fh.read()).decode('ascii')
                        elem.set(attr, f"data:{mime};base64,{b64}")
                        other = ('href' if attr.endswith('}href')
                                 else f'{{{NS_XLINK}}}href')
                        if elem.get(other) == href:
                            del elem.attrib[other]
                        changes += 1
                        _log(f"  [EMBED] {os.path.basename(file_path)} -> base64")
                    except OSError as e:
                        _log(f"  [WARN] Could not read {file_path}: {e}")
                break

        defs_elem = root.find(f'{{{NS_SVG}}}defs')
        if defs_elem is None:
            defs_elem = ET.SubElement(root, f'{{{NS_SVG}}}defs')
            root.insert(0, defs_elem)

        for elem in list(root.iter(f'{{{NS_SVG}}}use')):
            for attr in (f'{{{NS_XLINK}}}href', 'href'):
                href = elem.get(attr, '').strip()
                if not href or href.startswith('#'):
                    continue
                file_path, fragment = _resolve_href(href, svg_dir)
                if file_path is None or \
                        os.path.splitext(file_path)[1].lower() != '.svg':
                    continue
                safe = re.sub(r'[^A-Za-z0-9_-]', '_',
                              os.path.splitext(os.path.basename(file_path))[0])
                local_id = f"_linked_{safe}"
                if fragment:
                    local_id += f"_{re.sub(r'[^A-Za-z0-9_-]', '_', fragment)}"
                if defs_elem.find(f".//*[@id='{local_id}']") is None:
                    linked = _inline_svg_file(file_path, fragment, seen=set(seen))
                    if linked is not None:
                        wrapper = ET.SubElement(defs_elem, f'{{{NS_SVG}}}g')
                        wrapper.set('id', local_id)
                        wrapper.append(copy.deepcopy(linked))
                elem.set(attr, f"#{local_id}")
                other = ('href' if attr.endswith('}href')
                         else f'{{{NS_XLINK}}}href')
                if other in elem.attrib and elem.get(other) != f"#{local_id}":
                    del elem.attrib[other]
                changes += 1
                break

        if changes:
            return _safe_tostring(root), True
        return svg_content, False
    except Exception as e:
        _log(f"  [WARN] Resource embedding failed: {e}")
        return svg_content, False


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def _has_filters(svg_content):
    return bool(re.search(r'<filter\b', svg_content, re.IGNORECASE))


def apply_layer_visibility(svg_content, layer_rules, filename=None):
    if not layer_rules:
        return svg_content, False
    try:
        root       = ET.fromstring(svg_content)
        applicable = {}
        if 'global' in layer_rules:
            applicable.update(layer_rules['global'])
        if filename:
            if filename in layer_rules:
                applicable.update(layer_rules[filename])
            base = os.path.splitext(filename)[0]
            if base in layer_rules:
                applicable.update(layer_rules[base])
        if not applicable:
            return svg_content, False
        modified = 0
        for elem in root.iter():
            if elem.get(f'{{{NS_INK}}}groupmode') != 'layer':
                continue
            label = elem.get(f'{{{NS_INK}}}label', '')
            eid   = elem.get('id', '')
            key   = label if label in applicable else (eid if eid in applicable else None)
            if key is None:
                continue
            action = applicable[key]
            parts  = {}
            for p in elem.get('style', '').split(';'):
                if ':' in p:
                    k, v = p.split(':', 1)
                    parts[k.strip()] = v.strip()
            if action == 'hide':
                parts['display'] = 'none'
            elif action == 'show':
                parts.pop('display', None)
                parts.pop('visibility', None)
            elem.set('style', ';'.join(f"{k}:{v}" for k, v in parts.items()))
            modified += 1
        if modified:
            return _safe_tostring(root), True
        return svg_content, False
    except Exception as e:
        _log(f"  [WARN] Layer rules failed: {e}")
        return svg_content, False


def _get_page_count(svg_path):
    try:
        with open(svg_path, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()
        count = len(re.findall(
            r'<(?:inkscape:)?page\b[^>]+(?:/>|>)', content, re.IGNORECASE))
        if count > 0:
            return count
        root = ET.fromstring(content)
        nv = root.find(f'{{{NS_SODIPODI}}}namedview')
        if nv is None:
            for child in root:
                if 'namedview' in child.tag:
                    nv = child
                    break
        if nv is not None:
            pages = [c for c in nv if 'page' in c.tag.lower()
                     and ('inkscape' in c.tag or c.tag == 'page')]
            if pages:
                return len(pages)
        return 1
    except Exception:
        return 1


def _prepare_svg(svg_path, layer_rules, svg_filename):
    svg_dir = os.path.dirname(os.path.abspath(svg_path))
    changed = False
    try:
        with open(svg_path, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()
        s = _sanitize_svg_content(content)
        if s != content:
            content, changed = s, True
        new_c, ec = _embed_all_resources(content, svg_dir)
        if ec:
            content, changed = new_c, True
        if layer_rules:
            new_c, lc = apply_layer_visibility(content, layer_rules, svg_filename)
            if lc:
                content, changed = new_c, True
        if not changed:
            return svg_path, False
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.svg', delete=False,
            encoding='utf-8', dir=svg_dir)
        tmp.write(content)
        tmp.close()
        _log(f"  Prepared temp SVG: {os.path.basename(tmp.name)}")
        return tmp.name, True
    except Exception as e:
        _log(f"  [WARN] SVG prep failed ({e}) -- using original")
        return svg_path, False


# ---------------------------------------------------------------------------
# DPI / quality helper
# ---------------------------------------------------------------------------

def _jpeg_quality_for_dpi(dpi_int):
    if dpi_int >= 300: return 92
    if dpi_int >= 150: return 85
    if dpi_int >= 96:  return 72
    if dpi_int >= 72:  return 60
    return 45


# ---------------------------------------------------------------------------
# PDF raster downsampler  -- THE CORE FIX
# ---------------------------------------------------------------------------

def _downsample_pdf_images(pdf_path, target_dpi, log_fn=None):
    """
    Post-process the Inkscape-exported PDF:

    For every page, compute:
        max_px = (longer page edge in inches) * target_dpi

    For every raster image XObject whose longer pixel edge > max_px,
    downsample proportionally and recompress as JPEG at the quality
    level for target_dpi.

    Why this works:
    - We never try to measure the actual display size of an image within
      the page (that requires evaluating the graphics state / CTM which
      is complex).  Instead we use the page size as an upper bound:
      no image can usefully have more pixels than it would need to fill
      the whole page at target_dpi.  Images that are displayed smaller
      than a full page will be over-sampled by this estimate, but they
      will ALWAYS be downsampled -- which is exactly what we want.
    - The previous version had a > 110% threshold that let images slip
      through when the estimate was wrong.  This version has NO threshold:
      every image whose pixel count exceeds the budget is resampled.
    """
    def mlog(m):
        (log_fn or _log)(m)

    try:
        import pikepdf
    except ImportError:
        mlog("  [WARN] pikepdf not installed -- raster downsampling skipped.")
        mlog("         pip install pikepdf")
        return False
    try:
        from PIL import Image
    except ImportError:
        mlog("  [WARN] Pillow not installed -- raster downsampling skipped.")
        mlog("         pip install Pillow")
        return False

    target_dpi   = int(target_dpi)
    jpeg_quality = _jpeg_quality_for_dpi(target_dpi)
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

            # Recurse into Form XObjects
            if subtype == '/Form':
                sub_res = xobj.get('/Resources', None)
                if sub_res is not None:
                    _process_resources(sub_res, max_px)
                continue

            if subtype != '/Image':
                continue

            # Deduplicate shared XObjects
            try:
                obj_id = xobj.objgen
            except Exception:
                obj_id = id(xobj)
            if obj_id in processed_objids:
                continue
            processed_objids.add(obj_id)

            # Read dimensions
            try:
                img_w = int(xobj['/Width'])
                img_h = int(xobj['/Height'])
            except Exception:
                skipped += 1
                continue

            longer_edge = max(img_w, img_h)
            if longer_edge <= max_px:
                skipped += 1
                continue          # already within budget

            # Compute new size
            scale = max_px / longer_edge
            new_w = max(1, int(round(img_w * scale)))
            new_h = max(1, int(round(img_h * scale)))

            # Decode
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

                # Resample
                img_rs = img.resize((new_w, new_h), Image.LANCZOS)

                # JPEG-compatible mode
                if img_rs.mode in ('RGBA', 'LA', 'P'):
                    img_rs = img_rs.convert('RGB')

                buf = io.BytesIO()
                img_rs.save(buf, format='JPEG', quality=jpeg_quality,
                            optimize=True)
                jpeg_bytes = buf.getvalue()

                # Replace in the PDF object
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
                mlog(f"  [RESAMPLE] {key}: "
                     f"{img_w}x{img_h} -> {new_w}x{new_h} "
                     f"(budget {max_px}px, q={jpeg_quality})")

            except Exception as ie:
                mlog(f"  [WARN] Image {key} failed: {ie}")
                errors += 1

    # Process every page
    for page_idx, page in enumerate(pdf.pages):
        try:
            mb     = page.mediabox
            w_pt   = abs(float(mb[2]) - float(mb[0]))
            h_pt   = abs(float(mb[3]) - float(mb[1]))
            # longer edge in inches * target_dpi = max useful pixels
            max_px = max(32, int(max(w_pt, h_pt) / 72.0 * target_dpi))
        except Exception:
            max_px = target_dpi * 8    # fallback: ~8 inch page

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
# Single-file conversion
# ---------------------------------------------------------------------------

def convert_svg_to_pdf(svg_path, output_pdf, dpi, inkscape_path,
                       layer_rules=None):
    output_dir = os.path.dirname(os.path.abspath(output_pdf))
    os.makedirs(output_dir, exist_ok=True)
    svg_filename = os.path.basename(svg_path)

    try:
        with open(svg_path, 'r', encoding='utf-8', errors='replace') as fh:
            raw = fh.read()
        if _has_filters(raw):
            _log("  [WARN] SVG has filter effects -- those regions will be "
                 "rasterised by Inkscape; all other content stays vector.")
        page_count = _get_page_count(svg_path)
        _log(f"  Pages detected: {page_count}")
    except Exception:
        page_count = 1

    work_path, cleanup_tmp = _prepare_svg(svg_path, layer_rules, svg_filename)
    work_abs = os.path.abspath(work_path)

    try:
        ok = _run_inkscape_export(inkscape_path, work_abs, output_pdf, dpi)

        if ok:
            _downsample_pdf_images(output_pdf, dpi, log_fn=_log)
            sz = os.path.getsize(output_pdf)
            _log(f"  [OK] {os.path.basename(output_pdf)} "
                 f"({sz:,} bytes, {page_count} page(s))")

            class _OK:
                returncode    = 0
                files_created = [output_pdf]
            return _OK()

        _log(f"  [INFO] Single-call failed -- fallback ({page_count} page(s))")
        result = _page_by_page_fallback(work_abs, output_pdf, dpi,
                                        inkscape_path, page_count)
        if result.returncode == 0 and os.path.isfile(output_pdf):
            _downsample_pdf_images(output_pdf, dpi, log_fn=_log)
        return result

    finally:
        if cleanup_tmp and os.path.exists(work_abs):
            try:
                os.unlink(work_abs)
            except Exception:
                pass


def _run_inkscape_export(inkscape_path, svg_abs, out_pdf, dpi,
                         extra_args=None, timeout=180):
    cmd = [inkscape_path, svg_abs,
           '--export-type=pdf',
           f'--export-dpi={dpi}',
           f'--export-filename={out_pdf}']
    if extra_args:
        cmd.extend(extra_args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout)
        if r.returncode != 0:
            _log(f"  [WARN] Inkscape exited {r.returncode}")
        for line in (r.stderr or '').splitlines():
            if line.strip():
                _log(f"  Inkscape: {line}")
        return os.path.isfile(out_pdf) and os.path.getsize(out_pdf) > 0
    except subprocess.TimeoutExpired:
        _log(f"  [ERROR] Inkscape timed out ({timeout}s)")
        return False
    except FileNotFoundError:
        _log(f"  [ERROR] Inkscape not found: {inkscape_path}")
        return False
    except Exception as e:
        _log(f"  [ERROR] Inkscape failed: {e}")
        return False


def _page_by_page_fallback(work_svg_abs, final_pdf, dpi,
                            inkscape_path, page_count):
    out_dir   = os.path.dirname(os.path.abspath(final_pdf))
    stem      = os.path.splitext(os.path.basename(final_pdf))[0]
    page_pdfs = []
    tmp_dir   = tempfile.mkdtemp(dir=out_dir, prefix=f"_pages_{stem}_")
    try:
        for p in range(1, page_count + 1):
            pp = os.path.join(tmp_dir, f"page_{p:04d}.pdf")
            if _run_inkscape_export(inkscape_path, work_svg_abs, pp, dpi,
                                    extra_args=[f'--export-page={p}']):
                page_pdfs.append(pp)
                _log(f"  [OK] Page {p}/{page_count}")
            else:
                _log(f"  [WARN] Page {p} -- no output, stopping")
                break

        if not page_pdfs:
            class _F:
                returncode    = 1
                stderr        = "Fallback produced no output"
                files_created = []
            return _F()

        if len(page_pdfs) == 1:
            import shutil
            shutil.move(page_pdfs[0], final_pdf)
        else:
            merge_pdfs_from_list(page_pdfs, final_pdf)

        if os.path.isfile(final_pdf) and os.path.getsize(final_pdf) > 0:
            class _OK:
                returncode    = 0
                files_created = [final_pdf]
            return _OK()

        class _F:
            returncode    = 1
            stderr        = "Page merge failed"
            files_created = []
        return _F()
    finally:
        try:
            import shutil as _sh
            _sh.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Batch conversion
# ---------------------------------------------------------------------------

def batch_convert(svg_folder, output_path, dpi,
                  create_subfolders=True,
                  inkscape_path=None,
                  log_callback=None,
                  progress_callback=None,
                  layer_rules=None,
                  auto_merge_pdf=False,
                  selected_files=None,
                  merged_pdf_path=None):
    """
    Batch-convert SVG files to PDF (vector-preserving).

    dpi affects ONLY embedded raster images (downsampled after export).
    All vector content is lossless regardless of dpi.
    Lower dpi => smaller files when SVGs contain PNG/JPEG underlays.
    """
    global global_log_callback
    global_log_callback = log_callback

    if not inkscape_path:
        inkscape_path = r"C:\Program Files\Inkscape\bin\inkscape.exe"

    svg_folder = os.path.abspath(svg_folder)
    output_dir = os.path.abspath(output_path)
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.isfile(inkscape_path):
        _log(f"[ERROR] Inkscape not found: {inkscape_path}")
        return False

    all_svgs = get_svg_files(svg_folder)
    if selected_files is not None:
        sel = set(selected_files)
        svg_files = [f for f in all_svgs if f in sel]
    else:
        svg_files = all_svgs

    if not svg_files:
        _log("[ERROR] No SVG files to convert in: " + svg_folder)
        return False

    final_merged = (os.path.abspath(merged_pdf_path) if merged_pdf_path
                    else os.path.join(output_dir, "merged_output.pdf")) \
        if auto_merge_pdf else None

    try:
        dpi_int = int(dpi)
    except (TypeError, ValueError):
        dpi_int = 96

    _log("=" * 60)
    _log(f"[FOLDER] SVG source      : {svg_folder}")
    _log(f"[FOLDER] Output          : {output_dir}")
    _log(f"[INFO]   Inkscape        : {inkscape_path}")
    _log(f"[OPTION] Subfolders      : {create_subfolders}")
    _log(f"[OPTION] Auto-merge PDFs : {auto_merge_pdf}")
    if final_merged:
        _log(f"[OPTION] Merged PDF      : {final_merged}")
    _log(f"[STATS]  SVGs to process : {len(svg_files)}"
         + (f" (of {len(all_svgs)} total)" if len(svg_files) != len(all_svgs) else ""))
    _log(f"[INFO]   DPI             : {dpi_int} "
         f"(vectors=lossless, raster images resampled to {dpi_int} dpi)")
    _log(f"[INFO]   JPEG quality    : {_jpeg_quality_for_dpi(dpi_int)}")
    if layer_rules:
        _log(f"[LAYER]  Rule groups    : {len(layer_rules)}")
    _log("=" * 60)

    total      = len(svg_files)
    successful = 0
    failed     = 0
    all_pdfs   = []

    if progress_callback:
        progress_callback(0, total, "Starting PDF conversion...")

    for i, svg_file in enumerate(svg_files, 1):
        svg_path = os.path.join(svg_folder, svg_file)
        stem     = os.path.splitext(svg_file)[0]

        if progress_callback:
            progress_callback(i - 1, total, f"Processing: {svg_file}")

        if create_subfolders:
            file_out_dir = os.path.join(output_dir, stem)
            os.makedirs(file_out_dir, exist_ok=True)
            out_pdf = os.path.join(file_out_dir, f"{stem}.pdf")
        else:
            out_pdf = os.path.join(output_dir, f"{stem}.pdf")

        _log(f"\n[{i}/{total}] {svg_file}")

        result = convert_svg_to_pdf(svg_path, out_pdf, dpi_int,
                                    inkscape_path, layer_rules)

        if result.returncode == 0 and result.files_created:
            successful += 1
            pdf_file = result.files_created[0]
            if os.path.isfile(pdf_file) and os.path.getsize(pdf_file) > 0:
                all_pdfs.append(pdf_file)
        else:
            failed += 1
            _log(f"  [FAILED] {svg_file}")

        if progress_callback:
            progress_callback(i, total, f"Done: {svg_file}")

    if progress_callback:
        progress_callback(total, total, "PDF conversion complete!")

    _log("\n" + "=" * 60)
    _log(f"SUMMARY  processed={total}  ok={successful}  failed={failed}"
         f"  pdfs={len(all_pdfs)}")
    _log(f"Output: {output_dir}")

    if auto_merge_pdf and all_pdfs:
        _log("\n" + "=" * 60)
        _log(f"MERGING {len(all_pdfs)} PDFs -> {final_merged}")
        os.makedirs(os.path.dirname(os.path.abspath(final_merged)),
                    exist_ok=True)
        if progress_callback:
            progress_callback(0, 1, "Merging PDFs...")
        ok = merge_pdfs_from_list(all_pdfs, final_merged, log_callback)
        if ok:
            sz = os.path.getsize(final_merged) if os.path.isfile(final_merged) else 0
            _log(f"[OK] Merged PDF: {final_merged}  ({sz:,} bytes)")
        else:
            _log(f"[ERROR] Merge failed -- individual PDFs in {output_dir}")
        if progress_callback:
            progress_callback(1, 1, "Merge complete!")
    elif auto_merge_pdf:
        _log("[WARN] No PDFs to merge.")

    _log("=" * 60)
    return successful > 0


# ---------------------------------------------------------------------------
# PDF merging utilities
# ---------------------------------------------------------------------------

def merge_pdfs_from_list(pdf_files, output_pdf_path, log_callback=None):
    def mlog(m):
        (log_callback or _log)(m)

    output_abs = os.path.abspath(output_pdf_path)
    valid_pdfs = [p for p in pdf_files
                  if os.path.abspath(p) != output_abs
                  and os.path.isfile(p)
                  and os.path.getsize(p) > 0]

    if not valid_pdfs:
        mlog("[ERROR] No valid PDFs to merge")
        return False

    mlog(f"  Merging {len(valid_pdfs)} PDF(s) -> "
         f"{os.path.basename(output_pdf_path)}")
    os.makedirs(os.path.dirname(output_abs) or '.', exist_ok=True)

    use_pypdf_writer = use_pypdf_merger = use_pypdf2 = use_pikepdf = False
    try:
        import pypdf as _p
        if hasattr(_p, 'PdfWriter'):   use_pypdf_writer = True
        elif hasattr(_p, 'PdfMerger'): use_pypdf_merger = True
    except ImportError:
        pass
    if not use_pypdf_writer and not use_pypdf_merger:
        try:
            import PyPDF2; use_pypdf2 = True
        except ImportError:
            pass
    if not any([use_pypdf_writer, use_pypdf_merger, use_pypdf2]):
        try:
            import pikepdf; use_pikepdf = True
        except ImportError:
            pass
    if not any([use_pypdf_writer, use_pypdf_merger, use_pypdf2, use_pikepdf]):
        mlog("[ERROR] No PDF library.  pip install pypdf  or  pip install pikepdf")
        return False

    try:
        if use_pypdf_writer:
            import pypdf
            w = pypdf.PdfWriter()
            for p in valid_pdfs:
                mlog(f"  + {os.path.basename(p)}")
                for pg in pypdf.PdfReader(p).pages:
                    w.add_page(pg)
            with open(output_pdf_path, 'wb') as fh:
                w.write(fh)
        elif use_pypdf_merger:
            import pypdf
            m = pypdf.PdfMerger()
            for p in valid_pdfs:
                mlog(f"  + {os.path.basename(p)}"); m.append(p)
            with open(output_pdf_path, 'wb') as fh:
                m.write(fh)
            m.close()
        elif use_pypdf2:
            import PyPDF2
            m = PyPDF2.PdfMerger()
            for p in valid_pdfs:
                mlog(f"  + {os.path.basename(p)}"); m.append(p)
            with open(output_pdf_path, 'wb') as fh:
                m.write(fh)
            m.close()
        else:
            import pikepdf
            out = pikepdf.Pdf.new()
            for p in valid_pdfs:
                mlog(f"  + {os.path.basename(p)}")
                src = pikepdf.Pdf.open(p)
                out.pages.extend(src.pages)
                src.close()
            out.save(output_pdf_path)
            out.close()

        if os.path.isfile(output_pdf_path) and os.path.getsize(output_pdf_path) > 0:
            sz = os.path.getsize(output_pdf_path)
            mlog(f"[OK] Merged: {output_pdf_path}  ({sz:,} bytes)")
            return True
        mlog(f"[ERROR] Merge produced no file: {output_pdf_path}")
        return False
    except Exception as e:
        mlog(f"[ERROR] Merge failed: {e}")
        return False


def merge_pdfs(pdf_folder, output_pdf_path, log_callback=None):
    pdf_files   = []
    output_name = os.path.basename(output_pdf_path).lower()
    for root_dir, _, files in os.walk(pdf_folder):
        for f in sorted(files, key=str.lower):
            if f.lower().endswith('.pdf') and f.lower() != output_name:
                pdf_files.append(os.path.join(root_dir, f))
    if not pdf_files:
        if log_callback:
            log_callback("[ERROR] No PDFs found to merge")
        return False
    return merge_pdfs_from_list(pdf_files, output_pdf_path, log_callback)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def batch_convert_cli(svg_folder, output_path, dpi,
                      create_subfolders=True,
                      inkscape_path=None,
                      auto_merge_pdf=False):
    return batch_convert(svg_folder, output_path, dpi,
                         create_subfolders, inkscape_path,
                         auto_merge_pdf=auto_merge_pdf)


def main():
    if len(sys.argv) >= 4:
        svg_folder    = sys.argv[1]
        output_path   = sys.argv[2]
        dpi           = sys.argv[3]
        create_sub    = len(sys.argv) < 5 or sys.argv[4].lower() != 'false'
        auto_merge    = False
        inkscape_path = None
        merged_path   = None
        for arg in sys.argv[5:]:
            if arg.lower() == '--merge':
                auto_merge = True
            elif arg.lower().startswith('--merged-output='):
                merged_path = arg.split('=', 1)[1]
            else:
                inkscape_path = arg
        print(f"SVG -> PDF  DPI={dpi}  sub={create_sub}  merge={auto_merge}")
        success = batch_convert(
            svg_folder, output_path, dpi, create_sub, inkscape_path,
            auto_merge_pdf=auto_merge, merged_pdf_path=merged_path)
        return 0 if success else 1
    print("Usage: python vector.py <svg_folder> <output_path> <dpi> "
          "[subfolders:true|false] [--merge] [--merged-output=PATH] "
          "[inkscape_path]")
    return 1


if __name__ == "__main__":
    sys.exit(main())