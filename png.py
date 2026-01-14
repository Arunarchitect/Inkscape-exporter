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
    """Convert a single SVG file to PNG(s)"""
    cmd = [
        inkscape_path,
        svg_path,
        "--export-type=png",
        "--export-page=all",
        f"--export-dpi={dpi}",
        f"--export-filename={output_pattern}"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    return result

def batch_convert(svg_folder, output_path, dpi, create_subfolders=True, 
                  inkscape_path=None, log_callback=None):
    """
    Batch convert all SVG files in a folder to PNG
    
    Args:
        svg_folder: Folder containing SVG files
        output_path: Complete output path (including folder name)
        dpi: DPI quality
        create_subfolders: If True, create subfolder for each SVG
        inkscape_path: Custom Inkscape executable path
        log_callback: Function to call for logging messages
    """
    def log(message):
        if log_callback:
            log_callback(message)
        else:
            # Remove or replace emojis for Windows console compatibility
            clean_message = message.replace('📁', '[FOLDER]').replace('🎯', '[TARGET]')
            clean_message = clean_message.replace('📊', '[STATS]').replace('✅', '[OK]')
            clean_message = clean_message.replace('❌', '[ERROR]').replace('⚠️', '[WARNING]')
            clean_message = clean_message.replace('📂', '[FOLDER]')
            print(clean_message)
    
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
        
        if create_subfolders:
            # Create subfolder for each SVG file
            file_base_name = os.path.splitext(svg_file)[0]
            file_output_dir = os.path.join(output_dir, file_base_name)
            os.makedirs(file_output_dir, exist_ok=True)
            output_pattern = os.path.join(file_output_dir, "page.png")
        else:
            # All PNGs in same folder
            file_base_name = os.path.splitext(svg_file)[0]
            output_pattern = os.path.join(output_dir, f"{file_base_name}_page.png")
        
        log(f"\n[{i}/{total_files}] Processing: {svg_file}")
        
        result = convert_svg_to_png(svg_path, output_pattern, dpi, inkscape_path)
        
        if result.returncode == 0:
            successful += 1
            
            # Count exported PNGs
            if create_subfolders:
                exported = [f for f in os.listdir(file_output_dir) if f.endswith('.png')]
                log_location = file_output_dir
            else:
                exported = [f for f in os.listdir(output_dir) 
                          if f.startswith(file_base_name) and f.endswith('.png')]
                log_location = output_dir
            
            if exported:
                log(f"[OK] Success! Exported {len(exported)} PNG files to: {log_location}")
            else:
                log(f"[WARNING] No PNG files generated for {svg_file}")
        else:
            failed += 1
            log(f"[ERROR] Failed to process {svg_file}")
            if result.stderr:
                error_msg = result.stderr[:200]
                log(f"   Error: {error_msg}")
    
    # Summary
    log("\n" + "="*50)
    log("CONVERSION SUMMARY")
    log("="*50)
    log(f"[STATS] Total SVG files processed: {total_files}")
    log(f"[OK] Successful conversions: {successful}")
    log(f"[ERROR] Failed conversions: {failed}")
    log(f"[FOLDER] Output location: {output_dir}")
    
    # Count total PNG files created
    total_pngs = 0
    if create_subfolders:
        for root, dirs, files in os.walk(output_dir):
            pngs = [f for f in files if f.lower().endswith('.png')]
            total_pngs += len(pngs)
    else:
        total_pngs = len([f for f in os.listdir(output_dir) if f.lower().endswith('.png')])
    
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