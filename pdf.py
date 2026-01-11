import os
import sys
import img2pdf
from PIL import Image
from pathlib import Path

def pngs_to_pdf_using_img2pdf():
    """Convert PNG files to a single PDF using img2pdf"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    png_dir = os.path.join(script_dir, "png_output")
    output_pdf = os.path.join(script_dir, "combined_output.pdf")
    
    if not os.path.exists(png_dir):
        print(f"❌ PNG directory not found: {png_dir}")
        sys.exit(1)
    
    # Get all PNG files, sorted
    png_files = sorted([f for f in os.listdir(png_dir) if f.lower().endswith('.png')])
    
    if not png_files:
        print(f"❌ No PNG files found in: {png_dir}")
        sys.exit(1)
    
    print(f"📄 Found {len(png_files)} PNG files:")
    for png in png_files:
        print(f"  - {png}")
    
    # Create full paths
    png_paths = [os.path.join(png_dir, png) for png in png_files]
    
    try:
        # Convert to PDF
        with open(output_pdf, "wb") as f:
            f.write(img2pdf.convert(png_paths))
        
        print(f"✅ PDF created successfully: {output_pdf}")
        print(f"📊 File size: {os.path.getsize(output_pdf) / 1024:.2f} KB")
        
    except Exception as e:
        print(f"❌ Error creating PDF: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # First install required packages:
    # pip install img2pdf Pillow
    
    pngs_to_pdf_using_img2pdf()
    input("\nPress Enter to exit...")