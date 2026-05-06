"""
png.py  -  SVG to PNG batch converter

Fixes applied:
1. Pre-process SVGs to remove/fix malformed empty path elements (e.g. "M Z")
   that cause Inkscape to emit warnings and fail to produce output.
2. Removed broken page-loop logic; Inkscape is called once per file.
3. Improved temp-file placement (same dir as SVG so relative links resolve).
"""

import base64
import copy
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Namespace URIs
# ---------------------------------------------------------------------------
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

global_log_callback = None


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log(message):
    if global_log_callback:
        global_log_callback(message)
    else:
        try:
            print(message)
        except UnicodeEncodeError:
            print(message.encode('ascii', 'ignore').decode('ascii'))


# ---------------------------------------------------------------------------
# SVG sanitizer  ← KEY FIX
# ---------------------------------------------------------------------------

def _sanitize_svg_content(content):
    """
    Remove or fix SVG elements that cause Inkscape to emit warnings and
    fail to produce output.

    Known problems fixed here:
    - path d="M Z"   → empty move-then-close: remove the entire path element
    - path d="M"     → bare M with no coordinates: remove
    - path d=""      → empty d attribute: remove
    - Any path whose d attribute, after stripping whitespace, matches the
      regex ^[Mm]\s*[Zz]?$ (nothing but an optional move + optional close).
    """
    try:
        root = ET.fromstring(content)
        removed = 0

        # Collect (parent, element) pairs for bad paths
        bad_pairs = []
        for parent in root.iter():
            for child in list(parent):
                if child.tag != f'{{{NS_SVG}}}path':
                    # Also handle un-namespaced <path> tags
                    if not (child.tag == 'path' or
                            child.tag.endswith('}path')):
                        continue
                d = child.get('d', '').strip()
                # Empty d, or just "M Z" / "m z" / "M" / "m"
                if not d or re.match(r'^[Mm]\s*[Zz]?\s*$', d):
                    bad_pairs.append((parent, child))

        for parent, child in bad_pairs:
            parent.remove(child)
            removed += 1

        if removed:
            _log(f"  [SANITIZE] Removed {removed} empty/malformed path(s) "
                 f"(e.g. d=\"M Z\") that would cause Inkscape warnings.")
            # Re-serialise
            for pfx, uri in _NAMESPACES.items():
                ET.register_namespace(pfx, uri)
            return ET.tostring(root, encoding='unicode', xml_declaration=False)

        return content

    except ET.ParseError as e:
        _log(f"  [WARN] XML parse error during sanitization: {e} — skipping")
        return content
    except Exception as e:
        _log(f"  [WARN] Sanitization error: {e} — skipping")
        return content


# ---------------------------------------------------------------------------
# File utilities
# ---------------------------------------------------------------------------

def get_svg_files(folder_path):
    try:
        return sorted(
            (f for f in os.listdir(folder_path) if f.lower().endswith('.svg')),
            key=str.lower,
        )
    except OSError as e:
        _log(f"[ERROR] Cannot list folder {folder_path}: {e}")
        return []


# ---------------------------------------------------------------------------
# External-resource embedder (same logic as vector.py)
# ---------------------------------------------------------------------------

def _safe_tostring(root):
    for pfx, uri in _NAMESPACES.items():
        ET.register_namespace(pfx, uri)
    return ET.tostring(root, encoding='unicode', xml_declaration=False)


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
        linked_dir = os.path.dirname(abs_path)
        content, _ = _embed_all_resources(content, linked_dir, seen=set(seen))
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
                    continue
                ext = os.path.splitext(file_path)[1].lower()
                if ext == '.svg':
                    linked_elem = _inline_svg_file(file_path, fragment,
                                                   seen=set(seen))
                    if linked_elem is not None:
                        for geo in ('x', 'y', 'width', 'height',
                                    'id', 'style', 'transform',
                                    'preserveAspectRatio'):
                            val = elem.get(geo)
                            if val:
                                linked_elem.set(geo, val)
                        parent = _find_parent(root, elem)
                        if parent is not None:
                            idx = list(parent).index(elem)
                            parent.remove(elem)
                            parent.insert(idx, linked_elem)
                            changes += 1
                else:
                    mime, _ = mimetypes.guess_type(file_path)
                    if not mime:
                        mime = 'image/png'
                    try:
                        with open(file_path, 'rb') as fh:
                            b64 = base64.b64encode(fh.read()).decode('ascii')
                        data_uri = f"data:{mime};base64,{b64}"
                        elem.set(attr, data_uri)
                        other = ('href' if attr.endswith('}href')
                                 else f'{{{NS_XLINK}}}href')
                        if elem.get(other) == href:
                            del elem.attrib[other]
                        changes += 1
                    except OSError as e:
                        _log(f"  [WARN] Could not read {file_path}: {e}")
                break

        if changes:
            return _safe_tostring(root), True
        return svg_content, False

    except ET.ParseError:
        return svg_content, False
    except Exception:
        return svg_content, False


# ---------------------------------------------------------------------------
# Layer visibility
# ---------------------------------------------------------------------------

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
            key   = (label if label in applicable
                     else (eid if eid in applicable else None))
            if key is None:
                continue
            action = applicable[key]
            parts = {}
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
            _log(f"  Layer '{key}' → {action}")

        if modified:
            return _safe_tostring(root), True
        return svg_content, False

    except Exception as e:
        _log(f"  [WARN] Could not apply layer rules: {e}")
        return svg_content, False


# ---------------------------------------------------------------------------
# SVG preparation: sanitize + embed + layer rules
# ---------------------------------------------------------------------------

def _prepare_svg(svg_path, layer_rules, svg_filename):
    """
    1. Read the SVG.
    2. Sanitize malformed paths  ← NEW FIX
    3. Embed external resources.
    4. Apply layer rules.
    If any change was made, write a temp file in the SAME directory and
    return its path.  Returns (path_to_use, should_delete_temp).
    """
    svg_dir = os.path.dirname(os.path.abspath(svg_path))
    changed = False

    try:
        with open(svg_path, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()

        # Step 1: sanitize malformed paths
        sanitized = _sanitize_svg_content(content)
        if sanitized != content:
            content = sanitized
            changed = True

        # Step 2: embed external resources
        new_content, embed_changed = _embed_all_resources(content, svg_dir)
        if embed_changed:
            content = new_content
            changed = True

        # Step 3: layer rules
        if layer_rules:
            _log(f"  Applying layer rules to: {svg_filename}")
            new_content, layer_changed = apply_layer_visibility(
                content, layer_rules, svg_filename)
            if layer_changed:
                content = new_content
                changed = True

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
        _log(f"  [WARN] SVG preparation failed ({e}) — using original file")
        return svg_path, False


# ---------------------------------------------------------------------------
# Single Inkscape call → PNG
# ---------------------------------------------------------------------------

def _run_inkscape_png(inkscape_path, svg_abs, out_png, dpi,
                      timeout=180):
    """
    Export svg_abs to out_png at the given DPI.
    Returns True iff out_png was created with non-zero size.
    """
    cmd = [
        inkscape_path,
        svg_abs,
        '--export-type=png',
        f'--export-dpi={dpi}',
        f'--export-filename={out_png}',
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=timeout)
        stderr = result.stderr or ''
        if stderr.strip():
            # Log only real errors, not just the "M Z" warning noise
            for line in stderr.splitlines():
                if 'Malformed SVG path' in line or 'WARNING' in line:
                    _log(f"  Inkscape stderr: {line}")
        created = os.path.isfile(out_png) and os.path.getsize(out_png) > 0
        return created
    except subprocess.TimeoutExpired:
        _log(f"  [ERROR] Inkscape timed out after {timeout}s")
        return False
    except FileNotFoundError:
        _log(f"  [ERROR] Inkscape not found: {inkscape_path}")
        return False
    except Exception as e:
        _log(f"  [ERROR] Inkscape call failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Per-file conversion
# ---------------------------------------------------------------------------

def convert_svg_to_png(svg_path, output_dir, dpi, inkscape_path,
                       create_subfolders=True, layer_rules=None):
    """
    Convert one SVG to PNG(s).
    Returns (list_of_created_png_paths, success_bool).
    """
    os.makedirs(output_dir, exist_ok=True)
    svg_filename  = os.path.basename(svg_path)
    file_base     = os.path.splitext(svg_filename)[0]

    if create_subfolders:
        out_sub = os.path.join(output_dir, file_base)
        os.makedirs(out_sub, exist_ok=True)
    else:
        out_sub = output_dir

    out_png = os.path.join(out_sub, f"{file_base}.png")

    # Prepare (sanitize + embed + layers)
    work_path, cleanup_tmp = _prepare_svg(svg_path, layer_rules, svg_filename)
    work_path_abs = os.path.abspath(work_path)

    try:
        ok = _run_inkscape_png(inkscape_path, work_path_abs, out_png, dpi)
        if ok:
            sz = os.path.getsize(out_png)
            _log(f"  [OK] {os.path.basename(out_png)}  ({sz:,} bytes)")
            return [out_png], True
        else:
            _log(f"  [ERROR] Failed to create PNG for {svg_filename}")
            return [], False
    finally:
        if cleanup_tmp and os.path.exists(work_path_abs):
            try:
                os.unlink(work_path_abs)
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
                  selected_files=None):
    """
    Batch-convert SVG files to PNG.

    Parameters
    ----------
    svg_folder       : directory containing the SVG files.
    output_path      : directory where PNG files are written.
    dpi              : export DPI (controls PNG resolution).
    create_subfolders: create a subfolder per SVG in output_path.
    inkscape_path    : path to the Inkscape executable.
    log_callback     : callable(str) for log messages.
    progress_callback: callable(current, total, message).
    layer_rules      : dict of layer visibility rules.
    selected_files   : list of SVG filenames to process; None = all.
    """
    global global_log_callback
    global_log_callback = log_callback

    if not inkscape_path:
        inkscape_path = r"C:\Program Files\Inkscape\bin\inkscape.exe"

    svg_folder = os.path.abspath(svg_folder)
    output_dir = os.path.abspath(output_path)
    os.makedirs(output_dir, exist_ok=True)

    # Validate Inkscape
    if not os.path.isfile(inkscape_path):
        _log(f"[ERROR] Inkscape not found at: {inkscape_path}")
        _log("[ERROR] Please set the correct path in the Settings tab.")
        return False

    all_svg_files = get_svg_files(svg_folder)
    if selected_files is not None:
        selected_set = set(selected_files)
        svg_files    = [f for f in all_svg_files if f in selected_set]
    else:
        svg_files = all_svg_files

    if not svg_files:
        _log("[ERROR] No SVG files to convert in: " + svg_folder)
        return False

    _log("=" * 50)
    _log("--Starting PNG conversion...")
    _log(f"SVG Folder: {svg_folder}")
    _log(f"Output Location: {output_dir}")
    _log(f"DPI: {dpi}")
    _log(f"Output Format: PNG")
    _log(f"Files to convert: {len(svg_files)} of {len(all_svg_files)}")
    _log(f"Create Subfolders: {create_subfolders}")
    _log(f"Inkscape Path: {inkscape_path}")
    _log("=" * 50)

    total      = len(svg_files)
    successful = 0
    failed_list = []
    all_pngs   = []

    if progress_callback:
        progress_callback(0, total, "Starting PNG conversion...")

    for i, svg_file in enumerate(svg_files, 1):
        svg_path = os.path.join(svg_folder, svg_file)

        if progress_callback:
            progress_callback(i - 1, total, f"Processing: {svg_file}")

        _log(f"\n[{i}/{total}] Processing: {svg_file}")

        pngs, ok = convert_svg_to_png(
            svg_path=svg_path,
            output_dir=output_dir,
            dpi=dpi,
            inkscape_path=inkscape_path,
            create_subfolders=create_subfolders,
            layer_rules=layer_rules,
        )

        if ok and pngs:
            successful += 1
            all_pngs.extend(pngs)
        else:
            failed_list.append(svg_file)
            _log(f"[ERROR] Failed: {svg_file}")
            _log(f"        Failed to create any PNG files")

        if progress_callback:
            progress_callback(i, total, f"Done: {svg_file}")

    if progress_callback:
        progress_callback(total, total, "PNG conversion complete!")

    _log("\n" + "=" * 50)
    _log("PNG CONVERSION SUMMARY")
    _log("=" * 50)
    _log(f"  Total  : {total}")
    _log(f"  OK     : {successful}")
    _log(f"  Failed : {len(failed_list)}")
    _log(f"  Output : {output_dir}")
    _log(f"  Total PNG files created: {len(all_pngs)}")
    _log("=" * 50)

    if successful > 0:
        _log("✅ PNG conversion completed successfully!")
    else:
        _log("❌ PNG conversion failed!")

    return successful > 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) >= 4:
        svg_folder    = sys.argv[1]
        output_path   = sys.argv[2]
        dpi           = sys.argv[3]
        create_sub    = len(sys.argv) < 5 or sys.argv[4].lower() != 'false'
        inkscape_path = sys.argv[5] if len(sys.argv) >= 6 else None

        print(f"SVG → PNG  |  DPI: {dpi}  |  Subfolders: {create_sub}")
        print("=" * 50)
        success = batch_convert(
            svg_folder, output_path, dpi, create_sub, inkscape_path)
        return 0 if success else 1
    else:
        print("Usage: python png.py <svg_folder> <output_path> <dpi> "
              "[create_subfolders:true|false] [inkscape_path]")
        return 1


if __name__ == "__main__":
    sys.exit(main())