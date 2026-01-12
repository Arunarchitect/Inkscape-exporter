import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess

class SettingsTab:
    def __init__(self, parent, main_app):
        self.main_app = main_app
        self.frame = ttk.Frame(parent)
        self.setup_ui()
    
    def setup_ui(self):
        # Create a frame with scroll
        settings_frame = ttk.Frame(self.frame)
        settings_frame.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(settings_frame)
        scrollbar = ttk.Scrollbar(settings_frame, orient="vertical", command=canvas.yview)
        scrollable_settings = ttk.Frame(canvas)
        
        scrollable_settings.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_settings, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Inkscape path
        path_frame = ttk.LabelFrame(scrollable_settings, text="Inkscape Settings", padding="10")
        path_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(path_frame, text="Inkscape executable path:").pack(anchor='w')
        
        self.inkscape_path = tk.StringVar(value=r"C:\Program Files\Inkscape\bin\inkscape.exe")
        
        path_entry_frame = ttk.Frame(path_frame)
        path_entry_frame.pack(fill='x', pady=5)
        
        ttk.Entry(path_entry_frame, textvariable=self.inkscape_path).pack(
            side='left', fill='x', expand=True, padx=(0, 10))
        
        ttk.Button(path_entry_frame, text="Browse", command=self.browse_inkscape, width=10).pack(side='right')
        
        # Test Inkscape
        test_button = tk.Button(path_frame, text="Test Inkscape Installation", 
                               command=self.test_inkscape,
                               bg="#28a745", fg="white",
                               font=("Arial", 9, "bold"),
                               padx=15, pady=8)
        test_button.pack(pady=10)
        
        # PDF Settings
        pdf_frame = ttk.LabelFrame(scrollable_settings, text="PDF Settings", padding="10")
        pdf_frame.pack(fill='x', padx=10, pady=10)
        
        self.auto_open_pdf = tk.BooleanVar(value=True)
        ttk.Checkbutton(pdf_frame, text="Auto-open PDF after creation", 
                       variable=self.auto_open_pdf).pack(anchor='w', pady=2)
        
        self.sort_folders = tk.BooleanVar(value=True)
        ttk.Checkbutton(pdf_frame, text="Sort folders numerically by default", 
                       variable=self.sort_folders).pack(anchor='w', pady=2)
        
        # Dependencies check
        deps_frame = ttk.LabelFrame(scrollable_settings, text="Dependencies Check", padding="10")
        deps_frame.pack(fill='x', padx=10, pady=10)
        
        check_button = tk.Button(deps_frame, text="Check Required Modules", 
                                command=self.check_dependencies,
                                bg="#17a2b8", fg="white",
                                font=("Arial", 9, "bold"),
                                padx=15, pady=8)
        check_button.pack(pady=5)
        
        # About
        about_frame = ttk.LabelFrame(scrollable_settings, text="About", padding="10")
        about_frame.pack(fill='x', padx=10, pady=10)
        
        about_text = """SVG to PNG Converter & PDF Merger

Version: 2.0
Author: Your Name

This tool provides two main functions:
1. Batch convert SVG files to PNG format
2. Merge PNG files from numbered folders into PDF

Features:
• Batch convert multiple SVG files to PNG
• Adjustable DPI quality for PNGs
• Merge PNGs from numbered folders into PDF
• Organized output folders
• Real-time progress log for both operations

Requirements:
• Inkscape 1.0+ (for SVG to PNG)
• Python modules: tkinter, img2pdf, Pillow
"""
        
        about_label = ttk.Label(about_frame, text=about_text, justify='left', font=("Arial", 9))
        about_label.pack(anchor='w')
        
        # Add padding at bottom
        ttk.Frame(scrollable_settings, height=10).pack()
    
    def browse_inkscape(self):
        file = filedialog.askopenfilename(
            title="Select Inkscape executable",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if file:
            self.inkscape_path.set(file)
    
    def test_inkscape(self):
        try:
            result = subprocess.run([self.inkscape_path.get(), "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                messagebox.showinfo("Inkscape Test", f"✅ Success!\n\n{version_line}")
            else:
                messagebox.showerror("Inkscape Test", "❌ Inkscape returned an error")
        except Exception as e:
            messagebox.showerror("Inkscape Test", f"❌ Error: {str(e)}")
    
    def check_dependencies(self):
        missing = []
        
        # Check img2pdf
        try:
            import img2pdf
        except ImportError:
            missing.append("img2pdf")
        
        if missing:
            messagebox.showwarning("Missing Dependencies", 
                f"The following modules are missing:\n\n{', '.join(missing)}\n\n"
                f"Please install using:\npip install {' '.join(missing)}")
        else:
            messagebox.showinfo("Dependencies Check", 
                "✅ All required modules are installed!")