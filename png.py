import subprocess
import os
import sys
import json
from pathlib import Path

def get_svg_files(folder_path):
    """Get all SVG files from folder, sorted alphabetically"""
    svg_files = []
    for file in sorted(os.listdir(folder_path)):
        if file.lower().endswith('.svg'):
            svg_files.append(file)
    return svg_files

def convert_svg_to_png(svg_path, output_pattern, dpi, inkscape_path):
    """Convert a single SVG file to PNG(s) - Handle multi-page"""
    # Ensure output directory exists
    output_dir = os.path.dirname(output_pattern)
    os.makedirs(output_dir, exist_ok=True)
    
    # First, try to get the number of pages
    print(f"DEBUG: Converting multi-page SVG: {svg_path}")
    
    # Create a temporary command to check pages
    temp_output = os.path.join(output_dir, "temp_page_%d.png")
    test_cmd = f'"{inkscape_path}" "{svg_path}" --export-type=png --export-page=all --export-dpi={dpi} --export-filename="{temp_output}"'
    
    print(f"DEBUG: Testing with --export-page=all: {test_cmd}")
    result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
    
    # Check what files were created
    files_created = []
    if os.path.exists(output_dir):
        files_created = [f for f in os.listdir(output_dir) if f.startswith("temp_page_") and f.endswith('.png')]
    
    if files_created:
        print(f"DEBUG: Multi-page export created files: {files_created}")
        
        # Rename files to match our pattern
        base_name = os.path.splitext(os.path.basename(output_pattern))[0]
        for i, temp_file in enumerate(sorted(files_created), 1):
            old_path = os.path.join(output_dir, temp_file)
            new_name = f"{base_name}_p{i}.png" if len(files_created) > 1 else f"{base_name}.png"
            new_path = os.path.join(output_dir, new_name)
            
            try:
                os.rename(old_path, new_path)
                print(f"DEBUG: Renamed {temp_file} to {new_name}")
            except Exception as e:
                print(f"DEBUG: Error renaming {temp_file}: {e}")
        
        return result
    else:
        print(f"DEBUG: Multi-page export failed, trying single page")
        
        # Try single page export
        single_cmd = f'"{inkscape_path}" "{svg_path}" --export-type=png --export-dpi={dpi} --export-filename="{output_pattern}"'
        print(f"DEBUG: Falling back to single page: {single_cmd}")
        
        return subprocess.run(single_cmd, shell=True, capture_output=True, text=True, encoding='utf-8')

def batch_convert(svg_folder, output_path, dpi, create_subfolders=True, 
                  inkscape_path=None, log_callback=None):
    """
    Batch convert all SVG files in a folder to PNG
    """
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
                '🖼️': '[IMAGE]'
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
    log(f"[TARGET] DPI: {dpi}")
    log(f"[INKSCAPE] Using: {inkscape_path}")
    log(f"[OPTION] Create subfolders: {create_subfolders}")
    
    total_files = len(svg_files)
    successful = 0
    failed = 0
    
    # Process each SVG file
    for i, svg_file in enumerate(svg_files, 1):
        svg_path = os.path.join(svg_folder, svg_file)
        file_base_name = os.path.splitext(svg_file)[0]
        
        if create_subfolders:
            # Create subfolder for each SVG file
            file_output_dir = os.path.join(output_dir, file_base_name)
            os.makedirs(file_output_dir, exist_ok=True)
            # Output pattern: use SVG filename as base
            output_pattern = os.path.join(file_output_dir, f"{file_base_name}.png")
            target_dir = file_output_dir
        else:
            # All PNGs in same folder
            # Output pattern: use SVG filename as base
            output_pattern = os.path.join(output_dir, f"{file_base_name}.png")
            target_dir = output_dir
        
        log(f"\n[{i}/{total_files}] Processing: {svg_file}")
        log(f"[INFO] Output pattern: {output_pattern}")
        
        result = convert_svg_to_png(svg_path, output_pattern, dpi, inkscape_path)
        
        if result.returncode == 0:
            successful += 1
            
            # Check what files were actually created
            if os.path.exists(target_dir):
                # List ALL PNG files in target directory
                all_pngs = [f for f in os.listdir(target_dir) if f.lower().endswith('.png')]
                
                # Filter to files starting with our base name
                base_pngs = [f for f in all_pngs if f.startswith(file_base_name)]
                
                if base_pngs:
                    log(f"[OK] Success! Created {len(base_pngs)} PNG files:")
                    for png in sorted(base_pngs):
                        file_size = os.path.getsize(os.path.join(target_dir, png))
                        log(f"      -> {png} ({file_size} bytes)")
                else:
                    # Check for any PNGs at all
                    if all_pngs:
                        log(f"[INFO] Created PNG files (different naming):")
                        for png in sorted(all_pngs):
                            file_size = os.path.getsize(os.path.join(target_dir, png))
                            log(f"      -> {png} ({file_size} bytes)")
                    else:
                        log(f"[WARNING] No PNG files generated for {svg_file}")
            else:
                log(f"[ERROR] Target directory doesn't exist: {target_dir}")
        else:
            failed += 1
            log(f"[ERROR] Failed to process {svg_file}")
            if result.stderr:
                error_msg = result.stderr[:500]
                log(f"   Error: {error_msg}")
    
    # Summary
    log("\n" + "="*50)
    log("CONVERSION SUMMARY")
    log("="*50)
    log(f"[STATS] Total SVG files processed: {total_files}")
    log(f"[OK] Successful conversions: {successful}")
    log(f"[ERROR] Failed conversions: {failed}")
    log(f"[FOLDER] Output location: {output_dir}")
    
    # Count total PNG files created (walk through all directories)
    total_pngs = 0
    if create_subfolders:
        for root, dirs, files in os.walk(output_dir):
            pngs = [f for f in files if f.lower().endswith('.png')]
            total_pngs += len(pngs)
            if pngs:
                log(f"[INFO] In {root}: {len(pngs)} PNG files")
                for png in sorted(pngs):
                    log(f"      {png}")
    else:
        pngs = [f for f in os.listdir(output_dir) if f.lower().endswith('.png')]
        total_pngs = len(pngs)
        if pngs:
            log(f"[INFO] PNG files in output directory:")
            for png in sorted(pngs):
                log(f"      {png}")
    
    log(f"[STATS] Total PNG files created: {total_pngs}")
    log("="*50)
    
    return successful > 0

def convert_from_config(config_file='conversion_config.json'):
    """Convert using configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Run conversion
        return batch_convert(
            svg_folder=config.get('svg_folder', '.'),
            output_path=config.get('output_path', './png_output'),
            dpi=str(config.get('dpi', '96')),
            create_subfolders=config.get('create_subfolders', True),
            inkscape_path=config.get('inkscape_path')
        )
    except FileNotFoundError:
        print("[ERROR] Config file not found: " + config_file)
        return False
    except json.JSONDecodeError:
        print("[ERROR] Invalid config file: " + config_file)
        return False

def main():
    """Main function for command-line usage"""
    if len(sys.argv) >= 4:
        # Get arguments from command line
        svg_folder = sys.argv[1]
        output_path = sys.argv[2]
        dpi = sys.argv[3]
        create_subfolders = True if len(sys.argv) < 5 else sys.argv[4].lower() == 'true'
        
        # Check for custom inkscape path (6th argument)
        inkscape_path = None
        if len(sys.argv) >= 6:
            inkscape_path = sys.argv[5]
        
        # Use ASCII-safe printing for command line
        print("Command line conversion:")
        print("SVG Folder: " + svg_folder)
        print("Output Path: " + output_path)
        print("DPI: " + dpi)
        print("Create Subfolders: " + str(create_subfolders))
        if inkscape_path:
            print("Inkscape Path: " + inkscape_path)
        print("="*50)
        
        success = batch_convert(svg_folder, output_path, dpi, create_subfolders, inkscape_path)
        
        if success:
            print("\n[OK] Conversion completed successfully!")
            return 0
        else:
            print("\n[ERROR] Conversion failed or no files processed!")
            return 1
    else:
        print("Usage: python png.py <svg_folder> <output_path> <dpi> [create_subfolders] [inkscape_path]")
        print("Example: python png.py ./svgs ./output/png_files 150 true")
        print("Example: python png.py ./svgs ./output 300 false \"C:\\Custom\\inkscape.exe\"")
        print("\nNote: output_path should include the folder name")
        print("\nOr use with GUI: python gui.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())