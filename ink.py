import subprocess
import os
import sys

INKSCAPE_PATH = r"C:\Program Files\Inkscape\bin\inkscape.exe"

def check_inkscape():
    """Check Inkscape version and available options"""
    try:
        # Check version
        result = subprocess.run([INKSCAPE_PATH, "--version"], 
                              capture_output=True, text=True, encoding='utf-8')
        print("📊 Inkscape Version Info:")
        print(result.stdout)
        
        # Check available export options
        result = subprocess.run([INKSCAPE_PATH, "--help"], 
                              capture_output=True, text=True, encoding='utf-8')
        
        # Look for export-related options
        print("\n🔍 Checking for export-pages option...")
        if "--export-pages" in result.stdout:
            print("✅ --export-pages option is AVAILABLE")
        else:
            print("❌ --export-pages option NOT FOUND")
            
        # Print first few lines of help to see syntax
        print("\n📋 First 50 lines of --help output:")
        lines = result.stdout.split('\n')[:50]
        for line in lines:
            if 'export' in line.lower():
                print(f"  {line}")
                
    except Exception as e:
        print(f"❌ Error checking Inkscape: {e}")

if __name__ == "__main__":
    check_inkscape()
    input("\nPress Enter to exit...")