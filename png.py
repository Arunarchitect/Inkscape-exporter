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
    """Convert a single SVG file to PNG(s) - WORKING VERSION"""
    # Ensure output directory exists
    output_dir = os.path.dirname(output_pattern)
    os.makedirs(output_dir, exist_ok=True)
    
    # Get base name for output (without directory)
    if output_pattern.endswith('.png'):
        base_name = os.path.basename(output_pattern[:-4])  # Remove .png and path
    else:
        base_name = os.path.basename(output_pattern)
    
    # List to track created files
    files_created = []
    
    # IMPORTANT: Change to output directory before running commands
    original_dir = os.getcwd()
    os.chdir(output_dir)
    
    try:
        # COMMAND 1: Export page 1 (without --export-page)
        output_file_1 = f"{base_name}.png"
        cmd1 = f'"{inkscape_path}" "{svg_path}" --export-type=png --export-dpi={dpi} --export-filename="{output_file_1}"'
        
        result1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True, encoding='utf-8')
        
        if os.path.exists(output_file_1):
            files_created.append(output_file_1)
        else:
            # Try with --export-page=1 if basic export fails
            cmd1b = f'"{inkscape_path}" "{svg_path}" --export-type=png --export-page=1 --export-dpi={dpi} --export-filename="{output_file_1}"'
            result1b = subprocess.run(cmd1b, shell=True, capture_output=True, text=True, encoding='utf-8')
            
            if os.path.exists(output_file_1):
                files_created.append(output_file_1)
        
        # COMMAND 2-5: Export additional pages
        for page_num in range(2, 6):
            output_file = f"{base_name}_p{page_num}.png"
            cmd = f'"{inkscape_path}" "{svg_path}" --export-type=png --export-page={page_num} --export-dpi={dpi} --export-filename="{output_file}"'
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
            
            if os.path.exists(output_file):
                files_created.append(output_file)
            else:
                # Stop if this page doesn't exist
                break
    
    finally:
        # Change back to original directory
        os.chdir(original_dir)
    
    # Create result object
    if files_created:
        # Success result
        class SuccessResult:
            def __init__(self, files):
                self.returncode = 0
                self.stdout = f"Created {len(files)} PNG file(s)"
                self.stderr = ""
                self.files_created = files
        return SuccessResult(files_created)
    else:
        # Error result
        class ErrorResult:
            def __init__(self):
                self.returncode = 1
                self.stdout = ""
                self.stderr = "Failed to create any PNG files"
        return ErrorResult()

def batch_convert(svg_folder, output_path, dpi, create_subfolders=True, 
                  inkscape_path=None, log_callback=None, progress_callback=None):
    """
    Batch convert all SVG files in a folder to PNG with progress reporting
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
    
    # Send initial progress (0%)
    if progress_callback:
        progress_callback(0, total_files, "Starting conversion...")
    
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
            output_pattern = os.path.join(file_output_dir, f"{file_base_name}.png")
            target_dir = file_output_dir
        else:
            # All PNGs in same folder
            # Output pattern: use SVG filename as base
            output_pattern = os.path.join(output_dir, f"{file_base_name}.png")
            target_dir = output_dir
        
        log(f"\n[{i}/{total_files}] Processing: {svg_file}")
        
        result = convert_svg_to_png(svg_path, output_pattern, dpi, inkscape_path)
        
        if result.returncode == 0:
            successful += 1
            
            # Get list of created files
            if hasattr(result, 'files_created'):
                # New format: result has files_created attribute
                png_files = result.files_created
            else:
                # Old format: list directory
                if os.path.exists(target_dir):
                    png_files = [f for f in os.listdir(target_dir) if f.lower().endswith('.png')]
                else:
                    png_files = []
            
            if png_files:
                log(f"[OK] Success! Created {len(png_files)} PNG files:")
                for png in sorted(png_files):
                    file_path = os.path.join(target_dir, png)
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        log(f"      -> {png} ({file_size} bytes)")
                    else:
                        log(f"      -> {png}")
            else:
                log(f"[WARNING] No PNG files generated for {svg_file}")
        else:
            failed += 1
            log(f"[ERROR] Failed to process {svg_file}")
            if result.stderr:
                error_msg = result.stderr[:500]
                log(f"   Error: {error_msg}")
    
    # Send final progress (100%)
    if progress_callback:
        progress_callback(total_files, total_files, "Conversion complete!")
    
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

# Function to handle command line interface (backward compatible)
def batch_convert_cli(svg_folder, output_path, dpi, create_subfolders=True, inkscape_path=None):
    """CLI wrapper for batch_convert without callbacks"""
    return batch_convert(svg_folder, output_path, dpi, create_subfolders, inkscape_path)

def convert_from_config(config_file='conversion_config.json'):
    """Convert using configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Run conversion
        return batch_convert_cli(
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
        
        success = batch_convert_cli(svg_folder, output_path, dpi, create_subfolders, inkscape_path)
        
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