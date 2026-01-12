import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import subprocess
import threading
from pathlib import Path

class PDFMergerTab:
    def __init__(self, parent, main_app):
        self.main_app = main_app
        self.frame = ttk.Frame(parent)
        self.setup_ui()
    
    def setup_ui(self):
        # Create main frame
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(title_frame, text="📄 PNG to PDF Merger", 
                 font=("Arial", 16, "bold")).pack()
        
        # ====== INPUT SECTION ======
        input_frame = ttk.LabelFrame(main_frame, text="PNG Folder Selection", padding="15")
        input_frame.pack(fill='x', pady=(0, 15))
        
        # Auto-detect PNG output folder from converter tab
        auto_detect_frame = ttk.Frame(input_frame)
        auto_detect_frame.pack(fill='x', pady=(0, 10))
        
        tk.Button(auto_detect_frame, text="Auto-detect from Conversion", 
                 command=self.auto_detect_png_folder,
                 bg="#6f42c1", fg="white",
                 font=("Arial", 9, "bold"),
                 padx=15, pady=8).pack(side='left', padx=(0, 10))
        
        ttk.Label(auto_detect_frame, text="Detects PNG folder from last conversion").pack(side='left')
        
        # Manual folder selection
        ttk.Label(input_frame, text="PNG Folder Path:").pack(anchor='w')
        
        self.png_folder = tk.StringVar()
        
        folder_entry_frame = ttk.Frame(input_frame)
        folder_entry_frame.pack(fill='x', pady=5)
        
        ttk.Entry(folder_entry_frame, textvariable=self.png_folder).pack(
            side='left', fill='x', expand=True, padx=(0, 10))
        
        tk.Button(folder_entry_frame, text="Browse", 
                 command=self.browse_png_folder,
                 bg="#f0f0f0", fg="black",
                 padx=15, pady=5).pack(side='right')
        
        # Folder info
        self.folder_info_label = ttk.Label(input_frame, text="No folder selected")
        self.folder_info_label.pack(anchor='w', pady=(5, 0))
        
        # ====== OUTPUT SECTION ======
        output_frame = ttk.LabelFrame(main_frame, text="PDF Output Settings", padding="15")
        output_frame.pack(fill='x', pady=(0, 15))
        
        # Output location
        ttk.Label(output_frame, text="Output PDF Location:").pack(anchor='w')
        
        self.output_pdf_path = tk.StringVar()
        
        output_entry_frame = ttk.Frame(output_frame)
        output_entry_frame.pack(fill='x', pady=5)
        
        ttk.Entry(output_entry_frame, textvariable=self.output_pdf_path).pack(
            side='left', fill='x', expand=True, padx=(0, 10))
        
        tk.Button(output_entry_frame, text="Browse", 
                 command=self.browse_pdf_output,
                 bg="#f0f0f0", fg="black",
                 padx=15, pady=5).pack(side='right')
        
        # Default filename
        self.pdf_filename = tk.StringVar(value="combined_output.pdf")
        
        filename_frame = ttk.Frame(output_frame)
        filename_frame.pack(fill='x', pady=5)
        
        ttk.Label(filename_frame, text="PDF Filename:").pack(side='left')
        ttk.Entry(filename_frame, textvariable=self.pdf_filename, width=25).pack(side='left', padx=5)
        
        # Quick output locations
        quick_output_frame = ttk.Frame(output_frame)
        quick_output_frame.pack(fill='x', pady=10)
        
        tk.Button(quick_output_frame, text="Same as PNG Folder", 
                 command=self.output_same_folder,
                 bg="#f0f0f0", fg="black",
                 padx=10, pady=5).pack(side='left', padx=(0, 5))
        
        tk.Button(quick_output_frame, text="Desktop", 
                 command=self.output_to_desktop,
                 bg="#f0f0f0", fg="black",
                 padx=10, pady=5).pack(side='left', padx=(0, 5))
        
        tk.Button(quick_output_frame, text="Current Directory", 
                 command=self.output_to_current,
                 bg="#f0f0f0", fg="black",
                 padx=10, pady=5).pack(side='left')
        
        # ====== OPTIONS ======
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="15")
        options_frame.pack(fill='x', pady=(0, 15))
        
        self.open_pdf_after = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Open PDF after creation", 
                       variable=self.open_pdf_after).pack(anchor='w', pady=2)
        
        self.sort_numerically = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Sort folders numerically", 
                       variable=self.sort_numerically).pack(anchor='w', pady=2)
        
        # ====== LOG AREA ======
        log_frame = ttk.LabelFrame(main_frame, text="Merging Log", padding="10")
        log_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky='nsew')
        
        # ====== CONTROL BUTTONS ======
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        # Left buttons
        left_button_frame = ttk.Frame(button_frame)
        left_button_frame.pack(side='left')
        
        self.merge_btn = tk.Button(left_button_frame, text="MERGE TO PDF", 
                                  command=self.start_merge,
                                  bg="#28a745", fg="white",
                                  font=("Arial", 10, "bold"),
                                  padx=20, pady=10,
                                  relief="raised", bd=2)
        self.merge_btn.pack(side='left', padx=(0, 10))
        
        tk.Button(left_button_frame, text="Clear Log", 
                 command=self.clear_log,
                 bg="#f0f0f0", fg="black",
                 font=("Arial", 9),
                 padx=15, pady=8).pack(side='left')
        
        # Right buttons
        right_button_frame = ttk.Frame(button_frame)
        right_button_frame.pack(side='right')
        
        tk.Button(right_button_frame, text="Test Folder", 
                 command=self.test_folder,
                 bg="#17a2b8", fg="white",
                 font=("Arial", 9),
                 padx=15, pady=8).pack(side='right', padx=(0, 10))
    
    def auto_detect_png_folder(self):
        """Auto-detect PNG folder from converter tab output"""
        converter = self.main_app.converter_tab
        if converter.output_location.get() and converter.output_folder.get():
            png_path = os.path.join(
                converter.output_location.get(), 
                converter.output_folder.get()
            )
            if os.path.exists(png_path):
                self.png_folder.set(png_path)
                self.update_folder_info()
                self.log_message(f"✅ Auto-detected PNG folder: {png_path}")
            else:
                messagebox.showwarning("Warning", 
                    "PNG folder doesn't exist yet. Please run conversion first.")
        else:
            messagebox.showinfo("Info", 
                "No conversion output folder found. Please run SVG to PNG conversion first.")
    
    def browse_png_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing PNG subfolders")
        if folder:
            self.png_folder.set(folder)
            self.update_folder_info()
    
    def browse_pdf_output(self):
        file = filedialog.asksaveasfilename(
            title="Save PDF As",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file:
            self.output_pdf_path.set(file)
    
    def output_same_folder(self):
        if self.png_folder.get():
            folder = self.png_folder.get()
            filename = self.pdf_filename.get()
            self.output_pdf_path.set(os.path.join(folder, filename))
    
    def output_to_desktop(self):
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        filename = self.pdf_filename.get()
        self.output_pdf_path.set(os.path.join(desktop, filename))
    
    def output_to_current(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = self.pdf_filename.get()
        self.output_pdf_path.set(os.path.join(current_dir, filename))
    
    def update_folder_info(self):
        folder = self.png_folder.get()
        if folder and os.path.exists(folder):
            # Count numbered subfolders
            subfolders = [d for d in os.listdir(folder) 
                         if os.path.isdir(os.path.join(folder, d)) and d.isdigit()]
            count = len(subfolders)
            
            # Count total PNG files
            png_count = 0
            for root, dirs, files in os.walk(folder):
                png_count += len([f for f in files if f.lower().endswith('.png')])
            
            self.folder_info_label.config(
                text=f"Found {count} numbered subfolders with {png_count} total PNG files")
            
            if count > 0:
                self.log_message(f"📁 Found {count} numbered subfolders in: {folder}")
        else:
            self.folder_info_label.config(text="No folder selected or folder doesn't exist")
    
    def log_message(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.main_app.root.update()
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
    
    def test_folder(self):
        folder = self.png_folder.get()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Error", "Please select a valid PNG folder")
            return
        
        self.log_message("\n" + "="*50)
        self.log_message("Testing folder structure...")
        self.log_message(f"Folder: {folder}")
        
        # Find numbered folders
        numbered_folders = sorted(
            [d for d in os.listdir(folder) 
             if os.path.isdir(os.path.join(folder, d)) and d.isdigit()],
            key=lambda d: int(d) if self.sort_numerically.get() else d
        )
        
        if not numbered_folders:
            self.log_message("❌ No numbered folders found!")
            messagebox.showwarning("Warning", 
                "No numbered subfolders found. The folder should contain numbered subfolders (1, 2, 3, etc.)")
            return
        
        self.log_message(f"✅ Found {len(numbered_folders)} numbered folders")
        
        total_pngs = 0
        for folder_name in numbered_folders:
            folder_path = os.path.join(folder, folder_name)
            png_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
            total_pngs += len(png_files)
            self.log_message(f"  Folder {folder_name}: {len(png_files)} PNG files")
        
        self.log_message(f"\n📊 Total PNG files: {total_pngs}")
        self.log_message("="*50)
        
        if total_pngs > 0:
            messagebox.showinfo("Test Complete", 
                f"Found {len(numbered_folders)} folders with {total_pngs} PNG files.")
        else:
            messagebox.showwarning("Test Complete", 
                "Found numbered folders but no PNG files.")
    
    def start_merge(self):
        if not self.png_folder.get():
            messagebox.showerror("Error", "Please select a PNG folder")
            return
        
        if not os.path.exists(self.png_folder.get()):
            messagebox.showerror("Error", "Selected folder doesn't exist")
            return
        
        if not self.output_pdf_path.get():
            messagebox.showerror("Error", "Please specify output PDF path")
            return
        
        # Disable button during merge
        self.merge_btn.config(state='disabled', bg="#6c757d")
        
        # Run merge in separate thread
        thread = threading.Thread(target=self.run_merge)
        thread.daemon = True
        thread.start()
    
    def run_merge(self):
        try:
            png_folder = Path(self.png_folder.get())
            output_pdf = Path(self.output_pdf_path.get())
            
            self.log_message("\n" + "="*50)
            self.log_message("Starting PDF merge...")
            self.log_message(f"PNG Folder: {png_folder}")
            self.log_message(f"Output PDF: {output_pdf}")
            self.log_message("="*50)
            
            if not png_folder.exists():
                self.log_message("❌ PNG folder not found!")
                return
            
            # Get numbered folders
            numbered_folders = sorted(
                [d for d in png_folder.iterdir() if d.is_dir() and d.name.isdigit()],
                key=lambda d: int(d.name) if self.sort_numerically.get() else d.name
            )
            
            if not numbered_folders:
                self.log_message("❌ No numbered folders found inside PNG folder")
                return
            
            all_png_paths = []
            
            self.log_message("\n📂 Processing folders:")
            for folder in numbered_folders:
                self.log_message(f"  ▶ Folder {folder.name}")
                
                png_files = sorted(folder.glob("*.png"), key=lambda p: p.name.lower())
                
                if not png_files:
                    self.log_message(f"    ⚠ No PNG files in folder {folder.name}")
                    continue
                
                for png in png_files:
                    self.log_message(f"      - {png.name}")
                    all_png_paths.append(str(png))
            
            if not all_png_paths:
                self.log_message("❌ No PNG files found to merge")
                return
            
            self.log_message(f"\n📊 Total files to merge: {len(all_png_paths)}")
            
            # Check if img2pdf is available
            try:
                import img2pdf
            except ImportError:
                self.log_message("❌ img2pdf module not installed!")
                self.log_message("Please install: pip install img2pdf")
                return
            
            # Create PDF
            try:
                with open(output_pdf, "wb") as f:
                    f.write(img2pdf.convert(all_png_paths))
                
                self.log_message(f"\n✅ PDF created successfully!")
                self.log_message(f"📄 Location: {output_pdf}")
                self.log_message(f"📊 File size: {output_pdf.stat().st_size / 1024:.2f} KB")
                
                # Open PDF if option is selected
                if self.open_pdf_after.get():
                    try:
                        os.startfile(output_pdf)
                        self.log_message(f"📖 Opening PDF...")
                    except:
                        self.log_message(f"⚠ Could not open PDF automatically")
                
                messagebox.showinfo("Success", "PDF created successfully!")
                
            except Exception as e:
                self.log_message(f"❌ Error creating PDF: {str(e)}")
                messagebox.showerror("Error", f"Failed to create PDF:\n{str(e)}")
            
        except Exception as e:
            self.log_message(f"❌ Unexpected error: {str(e)}")
            messagebox.showerror("Error", f"An unexpected error occurred:\n{str(e)}")
        finally:
            # Re-enable button
            self.main_app.root.after(0, lambda: self.merge_btn.config(state='normal', bg="#28a745"))