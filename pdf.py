import os
import sys
import img2pdf
from pathlib import Path

def pngs_to_pdf_using_img2pdf():
    script_dir = Path(__file__).parent.resolve()
    png_root_dir = script_dir / "png_output"
    output_pdf = script_dir / "combined_output2.pdf"

    if not png_root_dir.exists():
        print(f"❌ PNG root directory not found: {png_root_dir}")
        sys.exit(1)

    all_png_paths = []

    # Get numbered folders and sort numerically
    numbered_folders = sorted(
        [d for d in png_root_dir.iterdir() if d.is_dir() and d.name.isdigit()],
        key=lambda d: int(d.name)
    )

    if not numbered_folders:
        print("❌ No numbered folders found inside png_output")
        sys.exit(1)

    print("📂 Processing folders in order:")
    for folder in numbered_folders:
        print(f"  ▶ Folder {folder.name}")

        png_files = sorted(folder.glob("*.png"), key=lambda p: p.name.lower())

        if not png_files:
            print(f"    ⚠ No PNG files in folder {folder.name}")
            continue

        for png in png_files:
            print(f"      - {png.name}")
            all_png_paths.append(str(png))

    if not all_png_paths:
        print("❌ No PNG files found to merge")
        sys.exit(1)

    try:
        with open(output_pdf, "wb") as f:
            f.write(img2pdf.convert(all_png_paths))

        print(f"\n✅ PDF created successfully: {output_pdf}")
        print(f"📊 File size: {output_pdf.stat().st_size / 1024:.2f} KB")

    except Exception as e:
        print(f"❌ Error creating PDF: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # pip install img2pdf Pillow
    pngs_to_pdf_using_img2pdf()
    input("\nPress Enter to exit...")
