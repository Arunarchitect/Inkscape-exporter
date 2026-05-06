# pdf_merge_tab.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import threading
from pathlib import Path

# Import img2pdf at module level
try:
    import img2pdf
    IMG2PDF_AVAILABLE = True
except ImportError:
    IMG2PDF_AVAILABLE = False


class PDFMergeTab:
    def __init__(self, parent, shared_vars, gui_app):
        self.parent = parent
        self.shared_vars = shared_vars
        self.gui_app = gui_app

        # Create tab frame
        self.frame = ttk.Frame(parent)
        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill='both', expand=True)

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=0)

        # ====== TOP SECTION (Scrollable Content) ======
        top_container = ttk.Frame(main_frame)
        top_container.grid(row=0, column=0, sticky='nsew', pady=(0, 5))

        canvas    = tk.Canvas(top_container)
        scrollbar = ttk.Scrollbar(top_container, orient="vertical", command=canvas.yview)
        scrollable_content = ttk.Frame(canvas)

        scrollable_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        content = scrollable_content

        # Title
        title_frame = ttk.Frame(content)
        title_frame.pack(fill='x', padx=10, pady=(10, 5))
        ttk.Label(title_frame, text="📄 PNG to PDF Merger",
                  font=("Arial", 16, "bold")).pack()
        ttk.Label(title_frame, text="Combine PNG files from subfolders into a single PDF",
                  font=("Arial", 9)).pack()

        if not IMG2PDF_AVAILABLE:
            warning_frame = ttk.Frame(content)
            warning_frame.pack(fill='x', padx=10, pady=5)
            ttk.Label(warning_frame,
                      text="⚠️ img2pdf not installed! Please run: pip install img2pdf",
                      foreground="red", font=("Arial", 9, "bold")).pack()

        # ====== PNG FOLDER SELECTION ======
        folder_frame = ttk.LabelFrame(content, text="PNG Folder Selection", padding="10")
        folder_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(folder_frame, text="Detected from last conversion:").pack(
            anchor='w', pady=(0, 5))
        self.auto_folder_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.auto_folder_var,
                  state='readonly', font=("Arial", 9)).pack(fill='x', pady=(0, 10))

        ttk.Label(folder_frame, text="Or select folder manually:").pack(
            anchor='w', pady=(0, 5))

        manual_frame = ttk.Frame(folder_frame)
        manual_frame.pack(fill='x', pady=(0, 10))

        self.manual_folder_var = tk.StringVar()
        ttk.Entry(manual_frame, textvariable=self.manual_folder_var).pack(
            side='left', fill='x', expand=True, padx=(0, 10))
        ttk.Button(manual_frame, text="Browse",
                   command=self.browse_png_folder, width=10).pack(side='right')

        quick_frame = ttk.Frame(folder_frame)
        quick_frame.pack(fill='x', pady=(0, 10))
        ttk.Button(quick_frame, text="Use Converter Output",
                   command=self.use_converter_output, width=20).pack(side='left', padx=(0, 10))
        ttk.Button(quick_frame, text="Same as Converter Input",
                   command=self.use_converter_input, width=20).pack(side='left')

        # ====== PDF OUTPUT SETTINGS ======
        output_frame = ttk.LabelFrame(content, text="PDF Output Settings", padding="10")
        output_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(output_frame, text="PDF Filename:").grid(
            row=0, column=0, sticky='w', pady=(0, 5))
        self.pdf_filename_var = tk.StringVar(value="combined_output.pdf")
        ttk.Entry(output_frame, textvariable=self.pdf_filename_var,
                  width=30).grid(row=0, column=1, sticky='w', pady=(0, 5), padx=(5, 0))

        ttk.Label(output_frame, text="Save PDF to:").grid(
            row=1, column=0, sticky='w', pady=(0, 5))
        output_loc_frame = ttk.Frame(output_frame)
        output_loc_frame.grid(row=1, column=1, sticky='ew', pady=(0, 5), padx=(5, 0))
        self.output_location_var = tk.StringVar()
        ttk.Entry(output_loc_frame, textvariable=self.output_location_var).pack(
            side='left', fill='x', expand=True, padx=(0, 10))
        ttk.Button(output_loc_frame, text="Browse",
                   command=self.browse_output_location, width=10).pack(side='right')

        quick_output_frame = ttk.Frame(output_frame)
        quick_output_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(5, 0))
        ttk.Button(quick_output_frame, text="Same as PNG Folder",
                   command=self.output_same_as_png, width=18).pack(side='left', padx=(0, 5))
        ttk.Button(quick_output_frame, text="Desktop",
                   command=self.output_to_desktop, width=10).pack(side='left', padx=(0, 5))
        ttk.Button(quick_output_frame, text="Current Directory",
                   command=self.output_to_current, width=15).pack(side='left')

        output_frame.columnconfigure(1, weight=1)

        # ====== PROCESSING OPTIONS ======
        options_frame = ttk.LabelFrame(content, text="Processing Options", padding="10")
        options_frame.pack(fill='x', padx=10, pady=10)

        self.open_pdf_var          = tk.BooleanVar(value=True)
        self.sort_alphabetically_var = tk.BooleanVar(value=True)
        self.include_subfolders_var  = tk.BooleanVar(value=True)

        ttk.Checkbutton(options_frame, text="Open PDF after creation",
                        variable=self.open_pdf_var).pack(anchor='w', pady=2)
        ttk.Checkbutton(options_frame, text="Sort folders alphabetically",
                        variable=self.sort_alphabetically_var).pack(anchor='w', pady=2)
        ttk.Checkbutton(options_frame,
                        text="Include all subfolders (uncheck to merge flat PNGs only)",
                        variable=self.include_subfolders_var).pack(anchor='w', pady=2)

        self.folder_info_label = ttk.Label(content, text="No PNG folder selected",
                                           font=("Arial", 9))
        self.folder_info_label.pack(anchor='w', padx=10, pady=(10, 0))

        ttk.Frame(content, height=10).pack()

        # ====== BOTTOM SECTION ======
        bottom_container = ttk.Frame(main_frame)
        bottom_container.grid(row=1, column=0, sticky='nsew', pady=(5, 0))
        bottom_container.columnconfigure(0, weight=1)
        bottom_container.rowconfigure(0, weight=1)
        bottom_container.rowconfigure(1, weight=0)

        log_frame = ttk.LabelFrame(bottom_container, text="PDF Merge Log", padding="10")
        log_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=(0, 5))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky='nsew')

        button_frame = ttk.Frame(bottom_container)
        button_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 10))

        left_button_frame = ttk.Frame(button_frame)
        left_button_frame.pack(side='left', fill='x', expand=True)

        self.merge_btn = tk.Button(left_button_frame, text="MERGE PNG TO PDF",
                                   command=self.start_merge,
                                   bg="#28a745", fg="white",
                                   font=("Arial", 10, "bold"),
                                   padx=20, pady=10, relief="raised", bd=2)
        self.merge_btn.pack(side='left', padx=(0, 10))

        tk.Button(left_button_frame, text="Clear Log",
                  command=self.clear_log,
                  bg="#f0f0f0", fg="black",
                  font=("Arial", 9), padx=15, pady=8).pack(side='left')

        tk.Button(left_button_frame, text="Scan Folder",
                  command=self.scan_folder,
                  bg="#17a2b8", fg="white",
                  font=("Arial", 9), padx=15, pady=8).pack(side='left', padx=(10, 0))

        right_button_frame = ttk.Frame(button_frame)
        right_button_frame.pack(side='right')
        tk.Button(right_button_frame, text="Test Merge",
                  command=self.test_merge,
                  bg="#ffc107", fg="black",
                  font=("Arial", 9), padx=15, pady=8).pack(side='right', padx=(0, 10))

        if not IMG2PDF_AVAILABLE:
            self.merge_btn.config(state='disabled', bg="#6c757d",
                                  text="MERGE (install img2pdf)")

    # ------------------------------------------------------------------
    # Folder helpers
    # ------------------------------------------------------------------

    def browse_png_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing PNG subfolders")
        if folder:
            self.manual_folder_var.set(folder)
            self.scan_folder()

    def browse_output_location(self):
        folder = filedialog.askdirectory(title="Select folder to save PDF")
        if folder:
            self.output_location_var.set(folder)

    def use_converter_output(self):
        output_location = self.shared_vars['output_location'].get()
        output_folder   = self.shared_vars['output_folder'].get()
        if output_location and output_folder:
            converter_output = os.path.join(output_location, output_folder)
            if os.path.exists(converter_output):
                self.manual_folder_var.set(converter_output)
                self.log_message(f"Using converter output: {converter_output}")
                self.scan_folder()
            else:
                messagebox.showwarning("Warning",
                    f"Converter output folder not found:\n{converter_output}")
        else:
            messagebox.showinfo("Info", "No converter output available yet")

    def use_converter_input(self):
        svg_folder = self.shared_vars['svg_folder'].get()
        if svg_folder and os.path.exists(svg_folder):
            png_output = os.path.join(svg_folder, "png_output")
            if os.path.exists(png_output):
                self.manual_folder_var.set(png_output)
                self.log_message(f"Using PNG folder in SVG directory: {png_output}")
                self.scan_folder()
            else:
                messagebox.showinfo("Info",
                    f"No 'png_output' folder found in:\n{svg_folder}")
        else:
            messagebox.showinfo("Info", "No converter input folder available")

    def output_same_as_png(self):
        png_folder = self.get_selected_folder()
        if png_folder:
            self.output_location_var.set(png_folder)

    def output_to_desktop(self):
        self.output_location_var.set(os.path.join(os.path.expanduser('~'), 'Desktop'))

    def output_to_current(self):
        self.output_location_var.set(os.path.dirname(os.path.abspath(__file__)))

    def get_selected_folder(self):
        manual = self.manual_folder_var.get()
        if manual and os.path.exists(manual):
            return manual
        return None

    def get_output_path(self):
        pdf_filename = self.pdf_filename_var.get()
        if not pdf_filename.lower().endswith('.pdf'):
            pdf_filename += '.pdf'
        output_location = self.output_location_var.get()
        if not output_location:
            png_folder = self.get_selected_folder()
            output_location = png_folder if png_folder else os.path.dirname(
                os.path.abspath(__file__))
        return os.path.join(output_location, pdf_filename)

    # ------------------------------------------------------------------
    # PNG file discovery
    # ------------------------------------------------------------------

    def _collect_png_files(self, png_folder):
        """
        Collect PNG files from png_folder respecting current options.

        Returns a list of absolute paths in the order they should appear in
        the PDF.

        Handles two layouts:
          A) Subfolders mode (include_subfolders=True):
             Each direct subfolder contains PNGs for one SVG page / document.
             Folders are sorted alphabetically; PNGs within each folder too.
          B) Flat mode (include_subfolders=False  OR  no subfolders exist):
             PNGs sit directly inside png_folder (create_subfolders=False was
             used during conversion).  Sorted alphabetically.
        """
        png_root = Path(png_folder)
        sort_key = lambda p: p.name.lower()

        # Check whether subfolders containing PNGs actually exist
        subdirs = sorted([d for d in png_root.iterdir() if d.is_dir()], key=sort_key) \
                  if self.sort_alphabetically_var.get() \
                  else [d for d in png_root.iterdir() if d.is_dir()]

        use_subfolders = self.include_subfolders_var.get() and bool(subdirs)

        all_pngs = []

        if use_subfolders:
            for folder in subdirs:
                pngs = sorted(folder.glob("*.png"), key=sort_key) \
                       if self.sort_alphabetically_var.get() \
                       else list(folder.glob("*.png"))
                all_pngs.extend(pngs)
        else:
            # Flat: PNGs directly in the root folder
            pngs = sorted(png_root.glob("*.png"), key=sort_key) \
                   if self.sort_alphabetically_var.get() \
                   else list(png_root.glob("*.png"))
            all_pngs.extend(pngs)

        # Exclude any accidentally present combined output file
        output_name = Path(self.get_output_path()).name.lower()
        all_pngs = [p for p in all_pngs if p.name.lower() != output_name]

        return [str(p) for p in all_pngs]

    def scan_folder(self):
        png_folder = self.get_selected_folder()
        if not png_folder or not os.path.exists(png_folder):
            self.log_message("❌ Please select a valid PNG folder first")
            return

        try:
            png_files = self._collect_png_files(png_folder)
            png_root  = Path(png_folder)
            folders   = [d for d in png_root.iterdir() if d.is_dir()]

            if not png_files:
                self.folder_info_label.config(
                    text=f"No PNG files found in: {png_folder}")
                self.log_message("⚠ No PNG files found in selected folder or its subfolders")
                return

            info_text = (f"Found {len(png_files)} PNG file(s)"
                         + (f" across {len(folders)} subfolder(s)" if folders else " (flat)"))
            self.folder_info_label.config(text=info_text)

            self.log_message(f"📁 Scanned folder: {png_folder}")
            self.log_message(f"📊 {info_text}")

            for i, p in enumerate(png_files[:8]):
                self.log_message(f"  {Path(p).parent.name}/{Path(p).name}")
            if len(png_files) > 8:
                self.log_message(f"  ... and {len(png_files) - 8} more files")

        except Exception as e:
            self.log_message(f"❌ Error scanning folder: {str(e)}")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log_message(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.gui_app.root.update()

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    def start_merge(self):
        if not IMG2PDF_AVAILABLE:
            messagebox.showerror("Error",
                "img2pdf is not installed!\n\nPlease run:\npip install img2pdf")
            return
        png_folder = self.get_selected_folder()
        if not png_folder or not os.path.exists(png_folder):
            messagebox.showerror("Error", "Please select a valid PNG folder")
            return
        self.merge_btn.config(state='disabled', bg="#6c757d")
        thread = threading.Thread(target=self.run_merge)
        thread.daemon = True
        thread.start()

    def run_merge(self):
        try:
            png_folder = self.get_selected_folder()
            output_pdf = self.get_output_path()

            self.log_message("\n" + "=" * 50)
            self.log_message("Starting PDF Merge...")
            self.log_message(f"PNG Folder: {png_folder}")
            self.log_message(f"Output PDF: {output_pdf}")
            self.log_message(f"Sort Alphabetically: {self.sort_alphabetically_var.get()}")
            self.log_message(f"Open PDF After: {self.open_pdf_var.get()}")
            self.log_message("=" * 50)

            success = self.merge_pngs_to_pdf(png_folder, output_pdf)

            if success:
                self.log_message("\n✅ PDF created successfully!")
                self.log_message(f"📄 Saved to: {output_pdf}")
                if self.open_pdf_var.get() and os.path.exists(output_pdf):
                    try:
                        os.startfile(output_pdf)
                        self.log_message(f"📂 Opened PDF: {output_pdf}")
                    except Exception:
                        self.log_message(f"📂 PDF file: {output_pdf}")
                messagebox.showinfo("Success", "PDF merge completed successfully!")
            else:
                self.log_message("\n❌ PDF merge failed!")
                messagebox.showerror("Error", "PDF merge failed. Check log for details.")

        except Exception as e:
            self.log_message(f"❌ Error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        finally:
            if IMG2PDF_AVAILABLE:
                self.gui_app.root.after(
                    0, lambda: self.merge_btn.config(state='normal', bg="#28a745"))

    def merge_pngs_to_pdf(self, png_folder, output_pdf):
        """Core merge function using img2pdf."""
        try:
            all_png_paths = self._collect_png_files(png_folder)

            if not all_png_paths:
                self.log_message("❌ No PNG files found to merge")
                return False

            # Create output directory if needed
            output_dir = os.path.dirname(output_pdf)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            self.log_message(f"\n🔄 Creating PDF: {os.path.basename(output_pdf)}")
            self.log_message(f"📊 Total pages: {len(all_png_paths)}")

            for p in all_png_paths:
                self.log_message(
                    f"  - {Path(p).parent.name}/{Path(p).name}")

            with open(output_pdf, "wb") as f:
                f.write(img2pdf.convert(all_png_paths))

            file_size = os.path.getsize(output_pdf) / 1024
            self.log_message(f"📦 PDF size: {file_size:.2f} KB")
            return True

        except Exception as e:
            self.log_message(f"❌ Error during PDF creation: {str(e)}")
            return False

    # ------------------------------------------------------------------
    # Test
    # ------------------------------------------------------------------

    def test_merge(self):
        self.log_message("\n🔍 Running Merge Test...")

        if IMG2PDF_AVAILABLE:
            self.log_message("✅ img2pdf is installed")
        else:
            self.log_message("❌ img2pdf is NOT installed")
            self.log_message("   Run: pip install img2pdf")

        png_folder = self.get_selected_folder()
        if png_folder and os.path.exists(png_folder):
            self.log_message(f"✅ PNG folder exists: {png_folder}")
            png_files = self._collect_png_files(png_folder)
            self.log_message(f"   Would merge {len(png_files)} PNG file(s)")
            if png_files:
                self.log_message(f"   First: {Path(png_files[0]).name}")
                self.log_message(f"   Last:  {Path(png_files[-1]).name}")
        else:
            self.log_message("❌ No valid PNG folder selected")

        self.log_message("✅ Test completed")