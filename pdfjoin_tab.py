# pdfjoin_tab.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading

import pdfjoin


class PDFJoinTab:
    """
    Tab: merge existing PDF files from a folder into one PDF.
    - Pick source folder, scan for PDFs
    - Build a merge order (Add / Remove / Move Up / Move Down / Top / Bottom)
    - Optional quality/size control: downsample embedded raster images to a
      target DPI (vector/text content is untouched)
    """

    def __init__(self, parent, shared_vars, gui_app):
        self.parent = parent
        self.shared_vars = shared_vars
        self.gui_app = gui_app

        # source folder -> available pdf filenames (not yet in the merge order)
        self.available_files = []
        # ordered list of absolute paths that will be merged
        self.order_paths = []

        self.frame = ttk.Frame(parent)
        self.setup_ui()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def setup_ui(self):
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill='both', expand=True)

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=0)

        # ====== TOP SECTION (Scrollable Content) ======
        top_container = ttk.Frame(main_frame)
        top_container.grid(row=0, column=0, sticky='nsew', pady=(0, 5))

        canvas = tk.Canvas(top_container)
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
        ttk.Label(title_frame, text="🧩 PDF Join / Merge",
                  font=("Arial", 16, "bold")).pack()
        ttk.Label(title_frame,
                  text="Combine existing PDF files into one, in the order you choose",
                  font=("Arial", 9)).pack()

        # ====== SOURCE FOLDER ======
        folder_frame = ttk.LabelFrame(content, text="Source Folder", padding="10")
        folder_frame.pack(fill='x', padx=10, pady=10)

        folder_entry_frame = ttk.Frame(folder_frame)
        folder_entry_frame.pack(fill='x', pady=(0, 5))
        self.folder_var = tk.StringVar()
        ttk.Entry(folder_entry_frame, textvariable=self.folder_var).pack(
            side='left', fill='x', expand=True, padx=(0, 6))
        ttk.Button(folder_entry_frame, text="Browse",
                   command=self.browse_folder, width=10).pack(side='right')

        quick_frame = ttk.Frame(folder_frame)
        quick_frame.pack(fill='x', pady=(0, 5))
        ttk.Button(quick_frame, text="Desktop",
                   command=self.use_desktop, width=10).pack(side='left', padx=(0, 5))
        ttk.Button(quick_frame, text="Use SVG Folder",
                   command=self.use_svg_folder, width=14).pack(side='left', padx=(0, 5))
        ttk.Button(quick_frame, text="Rescan",
                   command=self.scan_folder, width=10).pack(side='left')

        self.file_count_label = ttk.Label(folder_frame, text="PDF files found: 0")
        self.file_count_label.pack(anchor='w')

        # ====== FILE ORDER SECTION (two lists + controls) ======
        order_outer = ttk.LabelFrame(content, text="Merge Order", padding="10")
        order_outer.pack(fill='x', padx=10, pady=5)
        order_outer.columnconfigure(0, weight=1)
        order_outer.columnconfigure(2, weight=1)

        # --- Left: available files ---
        avail_col = ttk.Frame(order_outer)
        avail_col.grid(row=0, column=0, sticky='nsew')
        ttk.Label(avail_col, text="Available PDFs (in source folder)").pack(anchor='w')
        avail_list_frame = ttk.Frame(avail_col, relief='sunken', borderwidth=1)
        avail_list_frame.pack(fill='both', expand=True, pady=(4, 4))
        self.available_listbox = tk.Listbox(
            avail_list_frame, selectmode='extended', height=10, exportselection=False)
        avail_scroll = ttk.Scrollbar(avail_list_frame, orient='vertical',
                                     command=self.available_listbox.yview)
        self.available_listbox.configure(yscrollcommand=avail_scroll.set)
        self.available_listbox.pack(side='left', fill='both', expand=True)
        avail_scroll.pack(side='right', fill='y')

        # --- Middle: add/remove controls ---
        mid_col = ttk.Frame(order_outer)
        mid_col.grid(row=0, column=1, sticky='ns', padx=8)
        ttk.Frame(mid_col, height=30).pack()
        ttk.Button(mid_col, text="Add All →", width=12,
                   command=self.add_all).pack(pady=3)
        ttk.Button(mid_col, text="Add →", width=12,
                   command=self.add_selected).pack(pady=3)
        ttk.Button(mid_col, text="← Remove", width=12,
                   command=self.remove_selected).pack(pady=3)
        ttk.Button(mid_col, text="← Remove All", width=12,
                   command=self.remove_all).pack(pady=3)

        # --- Right: merge order ---
        order_col = ttk.Frame(order_outer)
        order_col.grid(row=0, column=2, sticky='nsew')
        ttk.Label(order_col, text="Merge Order (top -> bottom = page order)").pack(anchor='w')
        order_list_frame = ttk.Frame(order_col, relief='sunken', borderwidth=1)
        order_list_frame.pack(fill='both', expand=True, pady=(4, 4))
        self.order_listbox = tk.Listbox(
            order_list_frame, selectmode='browse', height=10, exportselection=False)
        order_scroll = ttk.Scrollbar(order_list_frame, orient='vertical',
                                     command=self.order_listbox.yview)
        self.order_listbox.configure(yscrollcommand=order_scroll.set)
        self.order_listbox.pack(side='left', fill='both', expand=True)
        order_scroll.pack(side='right', fill='y')

        reorder_frame = ttk.Frame(order_col)
        reorder_frame.pack(fill='x', pady=(0, 4))
        ttk.Button(reorder_frame, text="⤒ Top", width=8,
                   command=self.move_top).pack(side='left', padx=2)
        ttk.Button(reorder_frame, text="↑ Up", width=8,
                   command=self.move_up).pack(side='left', padx=2)
        ttk.Button(reorder_frame, text="↓ Down", width=8,
                   command=self.move_down).pack(side='left', padx=2)
        ttk.Button(reorder_frame, text="⤓ Bottom", width=8,
                   command=self.move_bottom).pack(side='left', padx=2)

        self.order_count_label = ttk.Label(order_col, text="0 file(s) in merge order",
                                           font=("Arial", 8), foreground="gray")
        self.order_count_label.pack(anchor='w')

        order_outer.rowconfigure(0, weight=1)

        # ====== OUTPUT SETTINGS ======
        output_frame = ttk.LabelFrame(content, text="Output Settings", padding="10")
        output_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(output_frame, text="Output Filename:").grid(
            row=0, column=0, sticky='w', pady=(0, 5))
        self.output_filename_var = tk.StringVar(value="joined_output.pdf")
        ttk.Entry(output_frame, textvariable=self.output_filename_var,
                  width=30).grid(row=0, column=1, sticky='w', pady=(0, 5), padx=(5, 0))

        ttk.Label(output_frame, text="Save To:").grid(
            row=1, column=0, sticky='w', pady=(0, 5))
        out_loc_frame = ttk.Frame(output_frame)
        out_loc_frame.grid(row=1, column=1, sticky='ew', pady=(0, 5), padx=(5, 0))
        self.output_location_var = tk.StringVar()
        ttk.Entry(out_loc_frame, textvariable=self.output_location_var).pack(
            side='left', fill='x', expand=True, padx=(0, 10))
        ttk.Button(out_loc_frame, text="Browse",
                   command=self.browse_output_location, width=10).pack(side='right')

        quick_out_frame = ttk.Frame(output_frame)
        quick_out_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(5, 0))
        ttk.Button(quick_out_frame, text="Same as Source",
                   command=self.output_same_as_source, width=16).pack(side='left', padx=(0, 5))
        ttk.Button(quick_out_frame, text="Desktop",
                   command=self.output_to_desktop, width=10).pack(side='left')

        output_frame.columnconfigure(1, weight=1)

        self.open_pdf_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(output_frame, text="Open PDF after merge",
                        variable=self.open_pdf_var).grid(
            row=3, column=0, columnspan=2, sticky='w', pady=(8, 0))

        # ====== QUALITY / SIZE SECTION ======
        quality_frame = ttk.LabelFrame(content, text="Quality / File Size", padding="10")
        quality_frame.pack(fill='x', padx=10, pady=10)

        self.compress_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            quality_frame,
            text="Downsample embedded images to reduce file size",
            variable=self.compress_var,
            command=self._on_compress_toggle).pack(anchor='w', pady=(0, 5))

        ttk.Label(quality_frame,
                  text=("Shrinks raster images (photos/scans) embedded in the PDFs to the "
                        "chosen DPI and recompresses as JPEG. Vector graphics and text are "
                        "never touched. Lower DPI = smaller file, lower image quality."),
                  font=("Arial", 8), foreground="gray", wraplength=560,
                  justify='left').pack(anchor='w', pady=(0, 8))

        self.dpi_row = ttk.Frame(quality_frame)
        self.dpi_row.pack(fill='x')
        ttk.Label(self.dpi_row, text="Target DPI:").pack(side='left', padx=(0, 10))
        self.dpi_var = tk.StringVar(value="150")
        for dpi_val in [72, 96, 150, 300]:
            ttk.Button(self.dpi_row, text=str(dpi_val), width=6,
                       command=lambda v=dpi_val: self.dpi_var.set(str(v))).pack(
                side='left', padx=2)
        ttk.Label(self.dpi_row, text="Custom:").pack(side='left', padx=(10, 5))
        ttk.Entry(self.dpi_row, textvariable=self.dpi_var, width=8).pack(side='left')

        self._on_compress_toggle()

        ttk.Frame(content, height=10).pack()

        # ====== BOTTOM SECTION (Always visible) ======
        bottom_container = ttk.Frame(main_frame)
        bottom_container.grid(row=1, column=0, sticky='nsew', pady=(5, 0))
        bottom_container.columnconfigure(0, weight=1)
        bottom_container.rowconfigure(0, weight=0)
        bottom_container.rowconfigure(1, weight=1)
        bottom_container.rowconfigure(2, weight=0)

        # Progress bar
        progress_frame = ttk.LabelFrame(bottom_container, text="Merge Progress", padding="10")
        progress_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=(0, 5))

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=100)
        self.progress_bar.pack(fill='x', expand=True, pady=(0, 5))

        progress_labels_frame = ttk.Frame(progress_frame)
        progress_labels_frame.pack(fill='x', expand=True)
        self.progress_text = ttk.Label(progress_labels_frame, text="Ready to start...")
        self.progress_text.pack(side='left', anchor='w')
        self.progress_percentage = ttk.Label(progress_labels_frame, text="0%")
        self.progress_percentage.pack(side='right', anchor='e')

        # Log area
        log_frame = ttk.LabelFrame(bottom_container, text="Join Log", padding="10")
        log_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0, 5))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky='nsew')

        # Control buttons
        button_frame = ttk.Frame(bottom_container)
        button_frame.grid(row=2, column=0, sticky='ew', padx=10, pady=(0, 10))

        left_button_frame = ttk.Frame(button_frame)
        left_button_frame.pack(side='left', fill='x', expand=True)

        self.join_btn = tk.Button(
            left_button_frame, text="JOIN PDFs",
            command=self.start_join,
            bg="#6f42c1", fg="white",
            font=("Arial", 10, "bold"),
            padx=20, pady=10, relief="raised", bd=2)
        self.join_btn.pack(side='left', padx=(0, 10))

        tk.Button(left_button_frame, text="Clear Log",
                  command=self.clear_log,
                  bg="#f0f0f0", fg="black",
                  font=("Arial", 9), padx=15, pady=8).pack(side='left')

    # ------------------------------------------------------------------
    # Folder / scanning
    # ------------------------------------------------------------------

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing PDF files")
        if folder:
            self.folder_var.set(folder)
            if not self.output_location_var.get():
                self.output_location_var.set(folder)
            self.scan_folder()

    def use_desktop(self):
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.folder_var.set(desktop)
        self.scan_folder()

    def use_svg_folder(self):
        svg_folder = self.shared_vars.get('svg_folder')
        if svg_folder and svg_folder.get():
            self.folder_var.set(svg_folder.get())
            self.scan_folder()
        else:
            messagebox.showinfo("Info", "No SVG folder set on the converter tab yet")

    def scan_folder(self):
        folder = self.folder_var.get()
        if not folder or not os.path.exists(folder):
            messagebox.showwarning("Warning", "Please select a valid folder first")
            return
        files = pdfjoin.get_pdf_files(folder)
        # keep files already placed in the merge order out of "available"
        already = {os.path.basename(p) for p in self.order_paths}
        self.available_files = [f for f in files if f not in already]
        self.file_count_label.config(text=f"PDF files found: {len(files)}")
        self._refresh_available_listbox()
        self.log_message(f"📁 Scanned: {folder} -> {len(files)} PDF(s) found")

    def _refresh_available_listbox(self):
        self.available_listbox.delete(0, tk.END)
        for f in self.available_files:
            self.available_listbox.insert(tk.END, f)

    # ------------------------------------------------------------------
    # Add / remove / reorder
    # ------------------------------------------------------------------

    def _refresh_order_listbox(self):
        self.order_listbox.delete(0, tk.END)
        for p in self.order_paths:
            self.order_listbox.insert(tk.END, os.path.basename(p))
        self.order_count_label.config(text=f"{len(self.order_paths)} file(s) in merge order")

    def add_all(self):
        folder = self.folder_var.get()
        for f in list(self.available_files):
            self.order_paths.append(os.path.join(folder, f))
        self.available_files = []
        self._refresh_available_listbox()
        self._refresh_order_listbox()

    def add_selected(self):
        folder = self.folder_var.get()
        sel = list(self.available_listbox.curselection())
        for idx in sel:
            f = self.available_files[idx]
            self.order_paths.append(os.path.join(folder, f))
        # remove added ones (by name) from available, preserving remaining order
        added_names = {self.available_files[i] for i in sel}
        self.available_files = [f for f in self.available_files if f not in added_names]
        self._refresh_available_listbox()
        self._refresh_order_listbox()

    def remove_selected(self):
        sel = list(self.order_listbox.curselection())
        if not sel:
            return
        idx = sel[0]
        removed = self.order_paths.pop(idx)
        self.available_files.append(os.path.basename(removed))
        self.available_files.sort(key=str.lower)
        self._refresh_available_listbox()
        self._refresh_order_listbox()

    def remove_all(self):
        for p in self.order_paths:
            self.available_files.append(os.path.basename(p))
        self.available_files.sort(key=str.lower)
        self.order_paths = []
        self._refresh_available_listbox()
        self._refresh_order_listbox()

    def move_up(self):
        sel = self.order_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.order_paths[i - 1], self.order_paths[i] = self.order_paths[i], self.order_paths[i - 1]
        self._refresh_order_listbox()
        self.order_listbox.selection_set(i - 1)

    def move_down(self):
        sel = self.order_listbox.curselection()
        if not sel or sel[0] == len(self.order_paths) - 1:
            return
        i = sel[0]
        self.order_paths[i + 1], self.order_paths[i] = self.order_paths[i], self.order_paths[i + 1]
        self._refresh_order_listbox()
        self.order_listbox.selection_set(i + 1)

    def move_top(self):
        sel = self.order_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        item = self.order_paths.pop(i)
        self.order_paths.insert(0, item)
        self._refresh_order_listbox()
        self.order_listbox.selection_set(0)

    def move_bottom(self):
        sel = self.order_listbox.curselection()
        if not sel or sel[0] == len(self.order_paths) - 1:
            return
        i = sel[0]
        item = self.order_paths.pop(i)
        self.order_paths.append(item)
        self._refresh_order_listbox()
        self.order_listbox.selection_set(len(self.order_paths) - 1)

    # ------------------------------------------------------------------
    # Output location helpers
    # ------------------------------------------------------------------

    def browse_output_location(self):
        folder = filedialog.askdirectory(title="Select folder to save the joined PDF")
        if folder:
            self.output_location_var.set(folder)

    def output_same_as_source(self):
        if self.folder_var.get():
            self.output_location_var.set(self.folder_var.get())
        else:
            messagebox.showwarning("Warning", "Please select the source folder first")

    def output_to_desktop(self):
        self.output_location_var.set(os.path.join(os.path.expanduser('~'), 'Desktop'))

    def get_output_path(self):
        filename = self.output_filename_var.get().strip() or "joined_output.pdf"
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        location = self.output_location_var.get().strip() or self.folder_var.get()
        return os.path.join(location, filename)

    # ------------------------------------------------------------------
    # Quality section toggle
    # ------------------------------------------------------------------

    def _on_compress_toggle(self):
        state = 'normal' if self.compress_var.get() else 'disabled'
        for child in self.dpi_row.winfo_children():
            try:
                child.config(state=state)
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # Logging / progress
    # ------------------------------------------------------------------

    def log_message(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.gui_app.root.update_idletasks()

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def _progress_callback(self, current, total, message):
        pct = int((current / total) * 100) if total > 0 else 0
        self.gui_app.root.after(0, lambda: self.progress_bar.config(value=pct))
        self.gui_app.root.after(0, lambda: self.progress_percentage.config(text=f"{pct}%"))
        self.gui_app.root.after(0, lambda: self.progress_text.config(text=message))

    # ------------------------------------------------------------------
    # Join / merge entry point
    # ------------------------------------------------------------------

    def start_join(self):
        if len(self.order_paths) < 1:
            messagebox.showerror("Error",
                                 "Add at least one PDF to the merge order first")
            return
        if self.compress_var.get() and not self.dpi_var.get().isdigit():
            messagebox.showerror("Error", "Target DPI must be a number")
            return

        output_path = self.get_output_path()
        if not os.path.dirname(output_path):
            messagebox.showerror("Error", "Please select an output location")
            return

        self.join_btn.config(state='disabled', bg="#6c757d")
        self.progress_bar['value'] = 0
        self.progress_percentage.config(text="0%")
        self.progress_text.config(text="Starting join...")

        thread = threading.Thread(target=self.run_join, args=(output_path,))
        thread.daemon = True
        thread.start()

    def run_join(self, output_path):
        try:
            compress = self.compress_var.get()
            dpi = int(self.dpi_var.get()) if compress else None

            self.log_message("\n" + "=" * 50)
            self.log_message("Starting PDF Join...")
            self.log_message(f"Files ({len(self.order_paths)}):")
            for i, p in enumerate(self.order_paths, 1):
                self.log_message(f"  {i}. {os.path.basename(p)}")
            self.log_message(f"Output: {output_path}")
            self.log_message(f"Downsample images: {compress}"
                             + (f" (target {dpi} dpi)" if compress else ""))
            self.log_message("=" * 50)

            success = pdfjoin.merge_pdfs_ordered(
                self.order_paths, output_path,
                compress=compress, target_dpi=dpi or 150,
                log_callback=self.log_message,
                progress_callback=self._progress_callback,
            )

            if success:
                self.gui_app.root.after(0, lambda: self.progress_bar.config(value=100))
                self.gui_app.root.after(0, lambda: self.progress_percentage.config(text="100%"))
                self.gui_app.root.after(
                    0, lambda: self.progress_text.config(text="Join complete!"))
                self.log_message(f"\n✅ Joined PDF created: {output_path}")

                if self.open_pdf_var.get() and os.path.exists(output_path):
                    try:
                        os.startfile(output_path)
                        self.log_message(f"📂 Opened: {output_path}")
                    except Exception:
                        self.log_message(f"📂 File: {output_path}")

                messagebox.showinfo("Success", "PDFs joined successfully!")
            else:
                self.gui_app.root.after(
                    0, lambda: self.progress_text.config(text="Join failed", foreground="red"))
                self.log_message("\n❌ Join failed!")
                messagebox.showerror("Error", "PDF join failed. Check log for details.")

        except Exception as e:
            import traceback
            self.log_message(f"❌ Error: {str(e)}")
            self.log_message(f"Traceback: {traceback.format_exc()}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        finally:
            self.gui_app.root.after(
                0, lambda: self.join_btn.config(state='normal', bg="#6f42c1"))