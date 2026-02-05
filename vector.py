# vector.py - SVG to PDF conversion module with merging capability
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import shutil
from pathlib import Path
import sys

# Global variable for log callback
global_log_callback = None

def get_svg_files(folder_path):
    """Get all SVG files from folder, sorted alphabetically"""
    svg_files = []
    for file in sorted(os.listdir(folder_path)):
        if file.lower().endswith('.svg'):
            svg_files.append(file)
    return svg_files

def parse_svg_layers(svg_content):
    """Parse SVG to extract layer information"""
    namespaces = {
        'svg': 'http://www.w3.org/2000/svg',
        'inkscape': 'http://www.inkscape.org/namespaces/inkscape'
    }
    
    try:
        root = ET.fromstring(svg_content)
        
        # Find all groups with inkscape:groupmode="layer"
        layers = {}
        for elem in root.iter():
            # Check for Inkscape layers
            groupmode = elem.get('{http://www.inkscape.org/namespaces/inkscape}groupmode')
            label = elem.get('{http://www.inkscape.org/namespaces/inkscape}label')
            
            if groupmode == 'layer' and label:
                layer_id = elem.get('id', '')
                layers[label] = {
                    'id': layer_id,
                    'elem': elem,
                    'style': elem.get('style', '')
                }
        
        return layers
    except Exception as e:
        if global_log_callback:
            global_log_callback(f"Warning: Could not parse SVG layers: {e}")
        else:
            print(f"Warning: Could not parse SVG layers: {e}")
        return {}

def apply_layer_visibility(svg_content, layer_rules, filename=None):
    """Apply visibility rules to SVG layers"""
    if not layer_rules:
        return svg_content
    
    try:
        # Parse SVG
        namespaces = {
            'svg': 'http://www.w3.org/2000/svg',
            'inkscape': 'http://www.inkscape.org/namespaces/inkscape'
        }
        
        root = ET.fromstring(svg_content)
        
        # Check both global rules and filename-specific rules
        applicable_rules = {}
        
        # Add global rules
        if 'global' in layer_rules:
            applicable_rules.update(layer_rules['global'])
        
        # Add filename-specific rules
        if filename:
            # Try exact match first
            if filename in layer_rules:
                applicable_rules.update(layer_rules[filename])
            
            # Try without extension
            basename = os.path.splitext(filename)[0]
            if basename in layer_rules:
                applicable_rules.update(layer_rules[basename])
        
        if not applicable_rules:
            return svg_content
        
        # Apply rules to layers
        layers_modified = 0
        for elem in root.iter():
            # Check if this is a layer
            groupmode = elem.get('{http://www.inkscape.org/namespaces/inkscape}groupmode')
            label = elem.get('{http://www.inkscape.org/namespaces/inkscape}label')
            elem_id = elem.get('id', '')
            
            # Check by label (preferred) or by ID
            layer_key = None
            if label and label in applicable_rules:
                layer_key = label
            elif elem_id in applicable_rules:
                layer_key = elem_id
            
            if layer_key and groupmode == 'layer':
                action = applicable_rules[layer_key]
                
                # Get current style
                current_style = elem.get('style', '')
                
                # Parse style attributes
                style_parts = {}
                if current_style:
                    for part in current_style.split(';'):
                        if ':' in part:
                            key, value = part.split(':', 1)
                            style_parts[key.strip()] = value.strip()
                
                # Set visibility
                if action == 'hide':
                    style_parts['display'] = 'none'
                elif action == 'show':
                    # Remove display:none if present
                    if 'display' in style_parts and style_parts['display'] == 'none':
                        del style_parts['display']
                
                # Rebuild style string
                new_style = ';'.join([f"{k}:{v}" for k, v in style_parts.items()])
                elem.set('style', new_style)
                
                layers_modified += 1
                if global_log_callback:
                    global_log_callback(f"  Applied {action} to layer: {layer_key}")
                else:
                    print(f"  Applied {action} to layer: {layer_key}")
        
        if layers_modified > 0:
            if global_log_callback:
                global_log_callback(f"  Modified {layers_modified} layers")
            else:
                print(f"  Modified {layers_modified} layers")
            return ET.tostring(root, encoding='unicode')
        else:
            return svg_content
            
    except Exception as e:
        if global_log_callback:
            global_log_callback(f"Warning: Error applying layer rules: {e}")
        else:
            print(f"Warning: Error applying layer rules: {e}")
        return svg_content

def detect_raster_content(svg_path):
    """
    Check if SVG contains raster (bitmap) images.
    Returns True if raster content is found, False otherwise.
    """
    try:
        with open(svg_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
        
        # Check for image tags with raster file extensions
        import re
        
        # Look for image tags
        image_patterns = [
            r'<image[^>]*>',
            r'xlink:href="[^"]*\.(?:jpg|jpeg|png|gif|bmp|tiff|tif)"',
            r'href="[^"]*\.(?:jpg|jpeg|png|gif|bmp|tiff|tif)"'
        ]
        
        for pattern in image_patterns:
            if re.search(pattern, svg_content, re.IGNORECASE):
                return True
        
        # Check for embedded base64 images
        if 'data:image/' in svg_content.lower():
            return True
            
        return False
    except:
        # If we can't read or parse, assume it might have raster content
        return True

def convert_svg_to_pdf(svg_path, output_pattern, dpi, inkscape_path, layer_rules=None):
    """Convert a single SVG file to PDF(s) with optional layer control"""
    # Use global log_callback
    global global_log_callback
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_pattern)
    os.makedirs(output_dir, exist_ok=True)
    
    # Get base name for output
    if output_pattern.endswith('.pdf'):
        base_name = os.path.basename(output_pattern[:-4])
    else:
        base_name = os.path.basename(output_pattern)
    
    # Get SVG filename for layer rule matching
    svg_filename = os.path.basename(svg_path)
    
    # Check if layer control is needed
    if layer_rules:
        try:
            # Read SVG content
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # Apply layer visibility rules
            if global_log_callback:
                global_log_callback(f"  Applying layer rules to: {svg_filename}")
            else:
                print(f"  Applying layer rules to: {svg_filename}")
            
            svg_content = apply_layer_visibility(svg_content, layer_rules, svg_filename)
            
            # Create temporary SVG file with modified layers
            with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False, encoding='utf-8') as temp_svg:
                temp_svg.write(svg_content)
                temp_svg_path = temp_svg.name
            
            # Clean up flag
            cleanup_temp = True
            
        except Exception as e:
            if global_log_callback:
                global_log_callback(f"Warning: Could not apply layer rules ({e}), using original file")
            else:
                print(f"Warning: Could not apply layer rules ({e}), using original file")
            temp_svg_path = svg_path
            cleanup_temp = False
    else:
        # No layer control needed
        temp_svg_path = svg_path
        cleanup_temp = False
    
    # Detect raster content to determine export method
    has_raster = detect_raster_content(temp_svg_path)
    
    # List to track created files
    files_created = []
    
    # Change to output directory before running commands
    original_dir = os.getcwd()
    os.chdir(output_dir)
    
    try:
        if has_raster:
            # If raster content found, use --export-dpi for bitmap resolution
            if global_log_callback:
                global_log_callback(f"  Detected raster content, exporting with DPI={dpi}")
            
            # Export page 1 with DPI setting
            output_file_1 = f"{base_name}.pdf"
            cmd1 = f'"{inkscape_path}" "{temp_svg_path}" --export-type=pdf --export-dpi={dpi} --export-filename="{output_file_1}"'
            
            result1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True, encoding='utf-8')
            
            if os.path.exists(output_file_1):
                files_created.append(output_file_1)
            else:
                # Try with --export-page=1 if basic export fails
                cmd1b = f'"{inkscape_path}" "{temp_svg_path}" --export-type=pdf --export-page=1 --export-dpi={dpi} --export-filename="{output_file_1}"'
                result1b = subprocess.run(cmd1b, shell=True, capture_output=True, text=True, encoding='utf-8')
                
                if os.path.exists(output_file_1):
                    files_created.append(output_file_1)
            
            # Export additional pages with DPI setting
            for page_num in range(2, 6):
                output_file = f"{base_name}_p{page_num}.pdf"
                cmd = f'"{inkscape_path}" "{temp_svg_path}" --export-type=pdf --export-page={page_num} --export-dpi={dpi} --export-filename="{output_file}"'
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
                
                if os.path.exists(output_file):
                    files_created.append(output_file)
                else:
                    # Stop if this page doesn't exist
                    break
        else:
            # Pure vector content - export directly without DPI setting
            if global_log_callback:
                global_log_callback(f"  Pure vector content, exporting directly to PDF")
            
            # Export page 1 (direct vector export)
            output_file_1 = f"{base_name}.pdf"
            cmd1 = f'"{inkscape_path}" "{temp_svg_path}" --export-type=pdf --export-filename="{output_file_1}"'
            
            result1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True, encoding='utf-8')
            
            if os.path.exists(output_file_1):
                files_created.append(output_file_1)
            else:
                # Try with --export-page=1 if basic export fails
                cmd1b = f'"{inkscape_path}" "{temp_svg_path}" --export-type=pdf --export-page=1 --export-filename="{output_file_1}"'
                result1b = subprocess.run(cmd1b, shell=True, capture_output=True, text=True, encoding='utf-8')
                
                if os.path.exists(output_file_1):
                    files_created.append(output_file_1)
            
            # Export additional pages (direct vector export)
            for page_num in range(2, 6):
                output_file = f"{base_name}_p{page_num}.pdf"
                cmd = f'"{inkscape_path}" "{temp_svg_path}" --export-type=pdf --export-page={page_num} --export-filename="{output_file}"'
                
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
                
                if os.path.exists(output_file):
                    files_created.append(output_file)
                else:
                    # Stop if this page doesn't exist
                    break
    
    finally:
        # Change back to original directory
        os.chdir(original_dir)
        
        # Clean up temporary file if created
        if cleanup_temp and os.path.exists(temp_svg_path):
            try:
                os.unlink(temp_svg_path)
            except:
                pass
    
    # Create result object
    if files_created:
        # Success result
        class SuccessResult:
            def __init__(self, files):
                self.returncode = 0
                self.stdout = f"Created {len(files)} PDF file(s)"
                self.stderr = ""
                self.files_created = files
        return SuccessResult(files_created)
    else:
        # Error result
        class ErrorResult:
            def __init__(self):
                self.returncode = 1
                self.stdout = ""
                self.stderr = "Failed to create any PDF files"
        return ErrorResult()

def batch_convert(svg_folder, output_path, dpi, create_subfolders=True, 
                  inkscape_path=None, log_callback=None, progress_callback=None,
                  layer_rules=None, auto_merge_pdf=False):
    """
    Batch convert all SVG files in a folder to PDF with progress reporting
    """
    # Store log_callback in global variable for use in other functions
    global global_log_callback
    global_log_callback = log_callback
    
    def log(message):
        if log_callback:
            log_callback(message)
        else:
            # Remove or replace emojis for Windows console compatibility
            clean_message = message
            # Replace all Unicode symbols with ASCII equivalents
            replacements = {
                '📁': '[FOLDER]',
                '🎯': '[TARGET]', 
                '📊': '[STATS]',
                '✅': '[OK]',
                '❌': '[ERROR]',
                '⚠️': '[WARNING]',
                '📂': '[FOLDER]',
                '→': '->',  # Replace arrow with ASCII arrow
                '📄': '[PDF]',
                '🔍': '[DETECT]',
                '🔗': '[MERGE]'
            }
            
            for unicode_char, ascii_char in replacements.items():
                clean_message = clean_message.replace(unicode_char, ascii_char)
            
            # Safe print for Windows console
            try:
                print(clean_message)
            except UnicodeEncodeError:
                # If still fails, remove all non-ASCII
                safe_message = clean_message.encode('ascii', 'ignore').decode('ascii')
                print(safe_message)
    
    # Default Inkscape path if not provided
    if not inkscape_path:
        inkscape_path = r"C:\Program Files\Inkscape\bin\inkscape.exe"
    
    # Get absolute paths
    svg_folder = os.path.abspath(svg_folder)
    output_dir = os.path.abspath(output_path)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if Inkscape exists
    if not os.path.exists(inkscape_path):
        log(f"[ERROR] Inkscape not found at: {inkscape_path}")
        return False
    
    # Get SVG files
    svg_files = get_svg_files(svg_folder)
    
    if not svg_files:
        log("[ERROR] No SVG files found in: " + svg_folder)
        return False
    
    log(f"[FOLDER] Found {len(svg_files)} SVG files in: {svg_folder}")
    log(f"[FOLDER] Output folder: {output_dir}")
    log(f"[TARGET] DPI: {dpi} (for raster content)")
    log(f"[INKSCAPE] Using: {inkscape_path}")
    log(f"[OPTION] Create subfolders: {create_subfolders}")
    log(f"[OPTION] Auto-merge PDFs: {auto_merge_pdf}")
    
    if layer_rules:
        rule_count = sum(len(rules) for rules in layer_rules.values())
        log(f"[LAYER CONTROL] Enabled with {rule_count} rule(s)")
    
    total_files = len(svg_files)
    successful = 0
    failed = 0
    
    # Send initial progress (0%)
    if progress_callback:
        progress_callback(0, total_files, "Starting PDF conversion...")
    
    # Process each SVG file
    for i, svg_file in enumerate(svg_files, 1):
        svg_path = os.path.join(svg_folder, svg_file)
        file_base_name = os.path.splitext(svg_file)[0]
        
        # Update progress before starting this file
        if progress_callback:
            progress_callback(i-1, total_files, f"Processing: {svg_file}")
        
        if create_subfolders:
            # Create subfolder for each SVG file
            file_output_dir = os.path.join(output_dir, file_base_name)
            os.makedirs(file_output_dir, exist_ok=True)
            # Output pattern: use SVG filename as base
            output_pattern = os.path.join(file_output_dir, f"{file_base_name}.pdf")
            target_dir = file_output_dir
        else:
            # All PDFs in same folder
            # Output pattern: use SVG filename as base
            output_pattern = os.path.join(output_dir, f"{file_base_name}.pdf")
            target_dir = output_dir
        
        log(f"\n[{i}/{total_files}] Processing: {svg_file}")
        
        result = convert_svg_to_pdf(svg_path, output_pattern, dpi, inkscape_path, layer_rules)
        
        if result.returncode == 0:
            successful += 1
            
            # Get list of created files
            if hasattr(result, 'files_created'):
                # New format: result has files_created attribute
                pdf_files = result.files_created
            else:
                # Old format: list directory
                if os.path.exists(target_dir):
                    pdf_files = [f for f in os.listdir(target_dir) if f.lower().endswith('.pdf')]
                else:
                    pdf_files = []
            
            if pdf_files:
                log(f"[OK] Success! Created {len(pdf_files)} PDF file(s):")
                for pdf in sorted(pdf_files):
                    file_path = os.path.join(target_dir, pdf)
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        log(f"      -> {pdf} ({file_size} bytes)")
                    else:
                        log(f"      -> {pdf}")
            else:
                log(f"[WARNING] No PDF files generated for {svg_file}")
        else:
            failed += 1
            log(f"[ERROR] Failed to process {svg_file}")
            if result.stderr:
                error_msg = result.stderr[:500]
                log(f"   Error: {error_msg}")
    
    # Send final progress (100%)
    if progress_callback:
        progress_callback(total_files, total_files, "PDF conversion complete!")
    
    # Summary
    log("\n" + "="*50)
    log("PDF CONVERSION SUMMARY")
    log("="*50)
    log(f"[STATS] Total SVG files processed: {total_files}")
    log(f"[OK] Successful conversions: {successful}")
    log(f"[ERROR] Failed conversions: {failed}")
    log(f"[FOLDER] Output location: {output_dir}")
    
    # Count total PDF files created (walk through all directories)
    total_pdfs = 0
    all_pdf_files = []
    
    if create_subfolders:
        for root, dirs, files in os.walk(output_dir):
            pdfs = [f for f in files if f.lower().endswith('.pdf')]
            total_pdfs += len(pdfs)
            for pdf in pdfs:
                all_pdf_files.append(os.path.join(root, pdf))
            if pdfs:
                log(f"[INFO] In {root}: {len(pdfs)} PDF files")
                for pdf in sorted(pdfs):
                    log(f"      {pdf}")
    else:
        pdfs = [f for f in os.listdir(output_dir) if f.lower().endswith('.pdf')]
        total_pdfs = len(pdfs)
        for pdf in pdfs:
            all_pdf_files.append(os.path.join(output_dir, pdf))
        if pdfs:
            log(f"[INFO] PDF files in output directory:")
            for pdf in sorted(pdfs):
                log(f"      {pdf}")
    
    log(f"[STATS] Total PDF files created: {total_pdfs}")
    
    # Auto-merge PDFs if requested
    if auto_merge_pdf and total_pdfs > 1:
        log("\n" + "="*50)
        log("AUTO-MERGING PDF FILES")
        log("="*50)
        
        merged_pdf_path = os.path.join(output_dir, "merged_output.pdf")
        
        if progress_callback:
            progress_callback(0, 1, "Merging PDF files...")
        
        # Sort PDF files for consistent merging order
        all_pdf_files = sorted(all_pdf_files)
        
        log(f"[MERGE] Merging {total_pdfs} PDF files into: {merged_pdf_path}")
        
        merge_success = merge_pdfs_from_list(all_pdf_files, merged_pdf_path, log_callback)
        
        if merge_success:
            log(f"[OK] Successfully merged {total_pdfs} PDF files")
            if os.path.exists(merged_pdf_path):
                file_size = os.path.getsize(merged_pdf_path)
                log(f"[INFO] Merged file size: {file_size} bytes")
                log(f"[FILE] Merged PDF: {merged_pdf_path}")
        else:
            log(f"[ERROR] Failed to merge PDF files")
        
        if progress_callback:
            progress_callback(1, 1, "PDF merge complete!")
    
    log("="*50)
    
    # Store output path for potential PDF merging
    global conversion_output_path
    conversion_output_path = output_dir
    
    return successful > 0

def merge_pdfs_from_list(pdf_files, output_pdf_path, log_callback=None):
    """
    Merge multiple PDF files from a list into a single PDF
    """
    try:
        # Try to use PyPDF2 for merging
        try:
            import PyPDF2
            use_pypdf2 = True
        except ImportError:
            use_pypdf2 = False
            
        if not use_pypdf2:
            # Try to use pikepdf instead
            try:
                import pikepdf
                use_pikepdf = True
            except ImportError:
                use_pikepdf = False
                
        if not (use_pypdf2 or use_pikepdf):
            if log_callback:
                log_callback("[ERROR] Neither PyPDF2 nor pikepdf is installed")
                log_callback("Install with: pip install PyPDF2 or pip install pikepdf")
            return False
        
        if not pdf_files:
            if log_callback:
                log_callback("[ERROR] No PDF files to merge")
            return False
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
        
        # Merge PDFs
        if use_pypdf2:
            # Using PyPDF2
            merger = PyPDF2.PdfMerger()
            
            for pdf_file in pdf_files:
                if log_callback:
                    log_callback(f"[MERGE] Adding: {os.path.basename(pdf_file)}")
                merger.append(pdf_file)
            
            # Write merged PDF
            with open(output_pdf_path, 'wb') as output_file:
                merger.write(output_file)
            merger.close()
            
        else:
            # Using pikepdf
            pdf = pikepdf.Pdf.new()
            
            for pdf_file in pdf_files:
                if log_callback:
                    log_callback(f"[MERGE] Adding: {os.path.basename(pdf_file)}")
                src = pikepdf.Pdf.open(pdf_file)
                pdf.pages.extend(src.pages)
                src.close()
            
            # Save merged PDF
            pdf.save(output_pdf_path)
            pdf.close()
        
        if log_callback:
            log_callback(f"[OK] Merged PDF created: {output_pdf_path}")
        
        return True
        
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to merge PDFs: {str(e)}")
        return False

def merge_pdfs(pdf_folder, output_pdf_path, log_callback=None):
    """
    Merge multiple PDF files into a single PDF
    """
    # Get all PDF files sorted alphabetically
    pdf_files = []
    for root, dirs, files in os.walk(pdf_folder):
        for file in sorted(files):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    if not pdf_files:
        if log_callback:
            log_callback("[ERROR] No PDF files found to merge")
        return False
    
    return merge_pdfs_from_list(pdf_files, output_pdf_path, log_callback)

# Function to handle command line interface (backward compatible)
def batch_convert_cli(svg_folder, output_path, dpi, create_subfolders=True, 
                     inkscape_path=None, auto_merge_pdf=False):
    """CLI wrapper for batch_convert without callbacks"""
    return batch_convert(svg_folder, output_path, dpi, create_subfolders, 
                        inkscape_path, auto_merge_pdf=auto_merge_pdf)

def main():
    """Main function for command-line usage"""
    if len(sys.argv) >= 4:
        # Get arguments from command line
        svg_folder = sys.argv[1]
        output_path = sys.argv[2]
        dpi = sys.argv[3]
        create_subfolders = True if len(sys.argv) < 5 else sys.argv[4].lower() == 'true'
        
        # Check for auto-merge flag (7th argument)
        auto_merge_pdf = False
        if len(sys.argv) >= 6 and sys.argv[5].lower() == '--merge':
            auto_merge_pdf = True
            inkscape_path = sys.argv[6] if len(sys.argv) >= 7 else None
        elif len(sys.argv) >= 6:
            inkscape_path = sys.argv[5]
        else:
            inkscape_path = None
        
        # Use ASCII-safe printing for command line
        print("Command line PDF conversion:")
        print("SVG Folder: " + svg_folder)
        print("Output Path: " + output_path)
        print("DPI (for raster): " + dpi)
        print("Create Subfolders: " + str(create_subfolders))
        print("Auto-merge PDFs: " + str(auto_merge_pdf))
        if inkscape_path:
            print("Inkscape Path: " + inkscape_path)
        print("="*50)
        
        success = batch_convert_cli(svg_folder, output_path, dpi, create_subfolders, 
                                   inkscape_path, auto_merge_pdf)
        
        if success:
            print("\n[OK] PDF conversion completed successfully!")
            return 0
        else:
            print("\n[ERROR] PDF conversion failed or no files processed!")
            return 1
    else:
        print("Usage: python vector.py <svg_folder> <output_path> <dpi> [create_subfolders] [--merge] [inkscape_path]")
        print("Example: python vector.py ./svgs ./output/pdf_files 150 true")
        print("Example: python vector.py ./svgs ./output 300 false --merge")
        print("Example: python vector.py ./svgs ./output 300 true --merge \"C:\\Custom\\inkscape.exe\"")
        print("\nNote: output_path should include the folder name")
        print("\nAdd --merge flag to automatically merge PDFs after conversion")
        return 1

if __name__ == "__main__":
    sys.exit(main())