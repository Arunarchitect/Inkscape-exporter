import subprocess
import os
import sys

INKSCAPE_PATH = r"C:\Program Files\Inkscape\bin\inkscape.exe"

SVG_FILENAME = "1.svg"
OUTPUT_FOLDER = "png_output"

def svg_to_png_pages(dpi):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    svg_path = os.path.join(script_dir, SVG_FILENAME)
    output_dir = os.path.join(script_dir, OUTPUT_FOLDER)

    if not os.path.exists(svg_path):
        print(f"❌ SVG not found: {svg_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # Use a filename pattern that includes page number placeholder
    output_pattern = os.path.join(output_dir, "page.png")

    # Use --export-page (singular) instead of --export-pages
    cmd = [
        INKSCAPE_PATH,
        svg_path,
        "--export-type=png",
        "--export-page=all",  # CHANGED: singular 'page' not 'pages'
        f"--export-dpi={dpi}",
        f"--export-filename={output_pattern}"
    ]

    print("Running command:", " ".join(cmd))
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    
    if result.returncode != 0:
        print("❌ Error during export:")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        sys.exit(1)
    
    print("✅ Export successful")
    print("📁 Files saved in:", output_dir)
    
    # List exported files
    exported_files = [f for f in os.listdir(output_dir) if f.endswith('.png')]
    if exported_files:
        print("📄 Exported files:", exported_files)
    else:
        print("⚠️  No PNG files found in output directory")

if __name__ == "__main__":
    dpi = input("Enter DPI (e.g., 72 / 96 / 150 / 300): ").strip()
    svg_to_png_pages(dpi)
    input("Press Enter to exit...")