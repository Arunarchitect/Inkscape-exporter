import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import subprocess
import threading


class ConverterTab:
    def __init__(self, parent, shared_vars, gui_app):
        self.parent = parent
        self.shared_vars = shared_vars
        self.gui_app = gui_app
        self.current_progress = 0
        self.total_files = 0

        # Dict mapping filename -> BooleanVar (checkbox state)
        self.svg_file_vars = {}

        # Add layer control variables
        if 'layer_control_enabled' not in self.shared_vars:
            self.shared_vars['layer_control_enabled'] = tk.BooleanVar(value=False)
        if 'layer_csv_path' not in self.shared_vars:
            self.shared_vars['layer_csv_path'] = tk.StringVar()
        if 'layer_text_content' not in self.shared_vars:
            self.shared_vars['layer_text_content'] = tk.StringVar()
        if 'layer_control_mode' not in self.shared_vars:
            self.shared_vars['layer_control_mode'] = tk.StringVar(value='csv')
        if 'layer_rules' not in self.shared_vars:
            self.shared_vars['layer_rules'] = None

        # Output format variable
        if 'output_format' not in self.shared_vars:
            self.shared_vars['output_format'] = tk.StringVar(value='png')

        # Auto-merge variable (used by both PNG and vector paths)
        if 'auto_merge' not in self.shared_vars:
            self.shared_vars['auto_merge'] = tk.BooleanVar(value=True)

        # CHANGED: variable for the user-chosen merged PDF save location
        if 'merged_pdf_folder' not in self.shared_vars:
            self.shared_vars['merged_pdf_folder'] = tk.StringVar()
        if 'merged_pdf_filename' not in self.shared_vars:
            self.shared_vars['merged_pdf_filename'] = tk.StringVar(value='merged_output.pdf')

        # Create tab frame
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
        ttk.Label(title_frame, text="🔄 SVG Converter",
                  font=("Arial", 16, "bold")).pack()

        # ====== INPUT SECTION ======
        input_outer = ttk.LabelFrame(content, text="Input Settings", padding="10")
        input_outer.pack(fill='x', padx=10, pady=5)
        input_outer.columnconfigure(0, weight=1)
        input_outer.columnconfigure(1, weight=1)
        input_outer.rowconfigure(0, weight=1)

        # --- Left column: folder selection ---
        input_left = ttk.Frame(input_outer)
        input_left.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        input_left.columnconfigure(0, weight=1)

        ttk.Label(input_left, text="SVG Files Folder:").grid(
            row=0, column=0, sticky='w', pady=(0, 4))

        svg_entry_frame = ttk.Frame(input_left)
        svg_entry_frame.grid(row=1, column=0, sticky='ew', pady=(0, 5))

        self.folder_entry = ttk.Entry(svg_entry_frame,
                                      textvariable=self.shared_vars['svg_folder'])
        self.folder_entry.pack(side='left', fill='x', expand=True, padx=(0, 6))
        ttk.Button(svg_entry_frame, text="Browse",
                   command=self.browse_svg_folder, width=10).pack(side='right')

        svg_quick_frame = ttk.Frame(input_left)
        svg_quick_frame.grid(row=2, column=0, sticky='w', pady=(0, 8))
        ttk.Button(svg_quick_frame, text="Current Directory",
                   command=self.use_current_dir, width=15).pack(side='left', padx=(0, 5))
        ttk.Button(svg_quick_frame, text="Desktop",
                   command=self.use_desktop, width=10).pack(side='left')

        self.file_count_label = ttk.Label(input_left, text="SVG files found: 0")
        self.file_count_label.grid(row=3, column=0, sticky='w')

        # --- Right column: SVG file list with checkboxes ---
        input_right = ttk.LabelFrame(input_outer, text="SVG Files  (uncheck to exclude)",
                                     padding="6")
        input_right.grid(row=0, column=1, sticky='nsew')
        input_right.columnconfigure(0, weight=1)
        input_right.rowconfigure(1, weight=1)

        list_toolbar = ttk.Frame(input_right)
        list_toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 4))

        ttk.Button(list_toolbar, text="✔ All", width=7,
                   command=self.select_all_files).pack(side='left', padx=(0, 4))
        ttk.Button(list_toolbar, text="✘ None", width=7,
                   command=self.deselect_all_files).pack(side='left')

        self.selected_count_label = ttk.Label(list_toolbar, text="0 selected",
                                              font=("Arial", 8), foreground="gray")
        self.selected_count_label.pack(side='right', padx=(4, 0))

        list_canvas_frame = ttk.Frame(input_right, relief='sunken', borderwidth=1)
        list_canvas_frame.grid(row=1, column=0, sticky='nsew')
        list_canvas_frame.columnconfigure(0, weight=1)
        list_canvas_frame.rowconfigure(0, weight=1)

        self.list_canvas = tk.Canvas(list_canvas_frame, height=130,
                                     highlightthickness=0, bg='white')
        list_vscroll = ttk.Scrollbar(list_canvas_frame, orient='vertical',
                                     command=self.list_canvas.yview)
        self.list_canvas.configure(yscrollcommand=list_vscroll.set)

        self.list_canvas.grid(row=0, column=0, sticky='nsew')
        list_vscroll.grid(row=0, column=1, sticky='ns')

        self.file_list_frame = ttk.Frame(self.list_canvas)
        self.file_list_window = self.list_canvas.create_window(
            (0, 0), window=self.file_list_frame, anchor='nw')

        self.file_list_frame.bind("<Configure>", self._on_file_list_configure)
        self.list_canvas.bind("<Configure>", self._on_canvas_resize)

        self.placeholder_label = ttk.Label(
            self.file_list_frame,
            text="Select a folder to see SVG files here.",
            foreground="gray", font=("Arial", 9, "italic"))
        self.placeholder_label.pack(padx=8, pady=8, anchor='w')

        # ====== OUTPUT SECTION ======
        output_frame = ttk.LabelFrame(content, text="Output Settings", padding="10")
        output_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(output_frame, text="Output Location:").grid(
            row=0, column=0, sticky='w', pady=(0, 5), columnspan=2)

        output_loc_entry_frame = ttk.Frame(output_frame)
        output_loc_entry_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 5))
        ttk.Entry(output_loc_entry_frame,
                  textvariable=self.shared_vars['output_location']).pack(
            side='left', fill='x', expand=True, padx=(0, 10))
        ttk.Button(output_loc_entry_frame, text="Browse",
                   command=self.browse_output_location, width=10).pack(side='right')

        output_name_frame = ttk.Frame(output_frame)
        output_name_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 10))
        ttk.Label(output_name_frame, text="Folder Name:").pack(side='left')
        ttk.Entry(output_name_frame, textvariable=self.shared_vars['output_folder'],
                  width=20).pack(side='left', padx=(5, 10))

        output_quick_frame = ttk.Frame(output_frame)
        output_quick_frame.grid(row=3, column=0, columnspan=2, sticky='w')
        ttk.Button(output_quick_frame, text="Same as SVG",
                   command=self.same_as_svg_folder, width=12).pack(side='left', padx=(0, 5))
        ttk.Button(output_quick_frame, text="Desktop",
                   command=self.output_to_desktop, width=10).pack(side='left', padx=(0, 5))
        ttk.Button(output_quick_frame, text="Custom",
                   command=self.browse_output_location, width=10).pack(side='left')

        output_frame.columnconfigure(0, weight=1)

        # ====== CONVERSION SETTINGS ======
        conv_frame = ttk.LabelFrame(content, text="Conversion Settings", padding="10")
        conv_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(conv_frame, text="DPI Quality:").grid(
            row=0, column=0, sticky='w', pady=(0, 5))
        ttk.Label(conv_frame,
                  text="(PNG: controls output resolution; PDF/Vector: controls embedded raster quality only)",
                  font=("Arial", 8), foreground="gray").grid(
            row=0, column=1, sticky='w', pady=(0, 5))

        dpi_buttons_frame = ttk.Frame(conv_frame)
        dpi_buttons_frame.grid(row=1, column=0, columnspan=2, sticky='w', pady=(0, 10))
        for dpi_val in [72, 96, 150, 300]:
            ttk.Button(dpi_buttons_frame, text=str(dpi_val), width=6,
                       command=lambda v=dpi_val: self.shared_vars['dpi'].set(str(v))).pack(
                side='left', padx=2)
        ttk.Label(dpi_buttons_frame, text="Custom:").pack(side='left', padx=(10, 5))
        ttk.Entry(dpi_buttons_frame, textvariable=self.shared_vars['dpi'],
                  width=8).pack(side='left')

        format_frame = ttk.Frame(conv_frame)
        format_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(10, 5))
        ttk.Label(format_frame, text="Output Format:").pack(side='left', padx=(0, 10))
        ttk.Radiobutton(format_frame, text="PNG (Raster)",
                        variable=self.shared_vars['output_format'],
                        value='png',
                        command=self._on_format_change).pack(side='left', padx=(0, 10))
        ttk.Radiobutton(format_frame, text="PDF (Vector-preserving)",
                        variable=self.shared_vars['output_format'],
                        value='vector',
                        command=self._on_format_change).pack(side='left')

        options_frame = ttk.Frame(conv_frame)
        options_frame.grid(row=3, column=0, columnspan=2, sticky='w', pady=(10, 5))

        # Single auto-merge checkbox
        self.auto_merge_checkbox = ttk.Checkbutton(
            options_frame,
            text="Merge to PDF automatically after conversion",
            variable=self.shared_vars['auto_merge'],
            command=self._on_format_change)  # CHANGED: update sub-panel on toggle
        self.auto_merge_checkbox.pack(anchor='w', pady=2)

        ttk.Checkbutton(options_frame, text="Create subfolders for each SVG",
                        variable=self.shared_vars['create_subfolders']).pack(anchor='w', pady=2)
        ttk.Checkbutton(options_frame, text="Open output folder after conversion",
                        variable=self.shared_vars['open_output']).pack(anchor='w', pady=2)

        # CHANGED: merged PDF destination panel — shown only for vector + auto_merge
        self.merged_pdf_frame = ttk.LabelFrame(
            conv_frame, text="Merged PDF Save Location", padding="8")
        self.merged_pdf_frame.grid(row=4, column=0, columnspan=2,
                                   sticky='ew', pady=(8, 0))
        self.merged_pdf_frame.columnconfigure(1, weight=1)

        ttk.Label(self.merged_pdf_frame, text="Filename:").grid(
            row=0, column=0, sticky='w', pady=(0, 4), padx=(0, 6))
        ttk.Entry(self.merged_pdf_frame,
                  textvariable=self.shared_vars['merged_pdf_filename'],
                  width=24).grid(row=0, column=1, sticky='w', pady=(0, 4))

        ttk.Label(self.merged_pdf_frame, text="Save to:").grid(
            row=1, column=0, sticky='w', padx=(0, 6))
        merged_loc_frame = ttk.Frame(self.merged_pdf_frame)
        merged_loc_frame.grid(row=1, column=1, sticky='ew')
        ttk.Entry(merged_loc_frame,
                  textvariable=self.shared_vars['merged_pdf_folder']).pack(
            side='left', fill='x', expand=True, padx=(0, 6))
        ttk.Button(merged_loc_frame, text="Browse",
                   command=self._browse_merged_pdf_folder,
                   width=10).pack(side='right')

        merged_quick = ttk.Frame(self.merged_pdf_frame)
        merged_quick.grid(row=2, column=0, columnspan=2, sticky='w', pady=(6, 0))
        ttk.Button(merged_quick, text="Same as Output",
                   command=self._merged_same_as_output,
                   width=14).pack(side='left', padx=(0, 5))
        ttk.Button(merged_quick, text="Desktop",
                   command=self._merged_to_desktop,
                   width=10).pack(side='left', padx=(0, 5))
        ttk.Button(merged_quick, text="Same as SVG",
                   command=self._merged_same_as_svg,
                   width=12).pack(side='left')

        conv_frame.columnconfigure(0, weight=0)
        conv_frame.columnconfigure(1, weight=1)

        # ====== LAYER CONTROL SECTION ======
        layer_frame = ttk.LabelFrame(content, text="Layer Visibility Control", padding="10")
        layer_frame.pack(fill='x', padx=10, pady=5)

        ttk.Checkbutton(layer_frame, text="Enable layer visibility control",
                        variable=self.shared_vars['layer_control_enabled'],
                        command=self.toggle_layer_controls).pack(anchor='w', pady=(0, 10))

        mode_frame = ttk.Frame(layer_frame)
        mode_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(mode_frame, text="Input Mode:").pack(side='left', padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="CSV File",
                        variable=self.shared_vars['layer_control_mode'],
                        value='csv', command=self.toggle_layer_input_mode).pack(
            side='left', padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="Text Input",
                        variable=self.shared_vars['layer_control_mode'],
                        value='text', command=self.toggle_layer_input_mode).pack(side='left')

        # CSV Frame
        self.csv_frame = ttk.Frame(layer_frame)
        ttk.Label(self.csv_frame, text="Layer Control CSV:").grid(
            row=0, column=0, sticky='w', pady=(0, 5), columnspan=2)
        csv_entry_frame = ttk.Frame(self.csv_frame)
        csv_entry_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 5))
        self.csv_entry = ttk.Entry(csv_entry_frame,
                                   textvariable=self.shared_vars['layer_csv_path'])
        self.csv_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        ttk.Button(csv_entry_frame, text="Browse",
                   command=self.browse_layer_csv, width=10).pack(side='right')
        ttk.Label(self.csv_frame,
                  text="CSV Format: layer_name,visibility (show/hide),svg_filename(optional)",
                  font=("Arial", 8), foreground="gray").grid(
            row=2, column=0, columnspan=2, sticky='w', pady=(0, 5))

        # Text Frame
        self.text_frame = ttk.Frame(layer_frame)
        ttk.Label(self.text_frame, text="Layer Control Text:").grid(
            row=0, column=0, sticky='w', pady=(0, 5))
        self.layer_text = scrolledtext.ScrolledText(self.text_frame, height=8, wrap=tk.WORD)
        self.layer_text.grid(row=1, column=0, sticky='nsew', pady=(0, 5))
        text_help = ("Enter layer visibility rules (one per line):\n"
                     "Format: layer_name:show/hide [for:filename.svg]\n"
                     "Examples:\n"
                     "  background:hide\n"
                     "  text_layer:show\n"
                     "  watermark:hide for:logo.svg")
        ttk.Label(self.text_frame, text=text_help, font=("Arial", 8),
                  foreground="gray").grid(row=2, column=0, sticky='w')
        self.text_frame.columnconfigure(0, weight=1)
        self.text_frame.rowconfigure(1, weight=1)

        self.toggle_layer_controls()
        self.toggle_layer_input_mode()
        layer_frame.columnconfigure(0, weight=1)

        ttk.Frame(content, height=10).pack()

        # ====== BOTTOM SECTION (Always visible) ======
        bottom_container = ttk.Frame(main_frame)
        bottom_container.grid(row=1, column=0, sticky='nsew', pady=(5, 0))
        bottom_container.columnconfigure(0, weight=1)
        bottom_container.rowconfigure(0, weight=1)
        bottom_container.rowconfigure(1, weight=1)
        bottom_container.rowconfigure(2, weight=0)

        # Progress bar
        progress_frame = ttk.LabelFrame(bottom_container, text="Conversion Progress",
                                        padding="10")
        progress_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=(0, 5))

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=100)
        self.progress_bar.pack(fill='x', expand=True, pady=(0, 5))

        progress_labels_frame = ttk.Frame(progress_frame)
        progress_labels_frame.pack(fill='x', expand=True)
        self.progress_text = ttk.Label(progress_labels_frame, text="Ready to start...")
        self.progress_text.pack(side='left', anchor='w')
        self.progress_percentage = ttk.Label(progress_labels_frame, text="0%")
        self.progress_percentage.pack(side='right', anchor='e')

        self.progress_details = ttk.Label(progress_frame, text="", font=("Arial", 9))
        self.progress_details.pack(fill='x', expand=True, pady=(2, 0))

        # Log area
        log_frame = ttk.LabelFrame(bottom_container, text="Conversion Log", padding="10")
        log_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0, 5))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky='nsew')
        self.gui_app.set_log_widget(self.log_text)

        # Control buttons
        button_frame = ttk.Frame(bottom_container)
        button_frame.grid(row=2, column=0, sticky='ew', padx=10, pady=(0, 10))

        left_button_frame = ttk.Frame(button_frame)
        left_button_frame.pack(side='left', fill='x', expand=True)

        self.convert_btn = tk.Button(
            left_button_frame, text="START CONVERSION",
            command=self.start_conversion,
            bg="#0078D7", fg="white",
            font=("Arial", 10, "bold"),
            padx=20, pady=10, relief="raised", bd=2)
        self.convert_btn.pack(side='left', padx=(0, 10))

        tk.Button(left_button_frame, text="Clear Log",
                  command=self.clear_log,
                  bg="#f0f0f0", fg="black",
                  font=("Arial", 9), padx=15, pady=8).pack(side='left')

        right_button_frame = ttk.Frame(button_frame)
        right_button_frame.pack(side='right')
        tk.Button(right_button_frame, text="Exit",
                  command=self.gui_app.root.quit,
                  bg="#f0f0f0", fg="black",
                  font=("Arial", 9), padx=15, pady=8).pack(side='right')

        # CHANGED: initialise panel visibility
        self._on_format_change()

    # ------------------------------------------------------------------
    # CHANGED: merged PDF location helpers
    # ------------------------------------------------------------------

    def _browse_merged_pdf_folder(self):
        folder = filedialog.askdirectory(title="Select folder to save the merged PDF")
        if folder:
            self.shared_vars['merged_pdf_folder'].set(folder)

    def _merged_same_as_output(self):
        loc  = self.shared_vars['output_location'].get()
        name = self.shared_vars['output_folder'].get()
        if loc:
            self.shared_vars['merged_pdf_folder'].set(
                os.path.join(loc, name) if name else loc)

    def _merged_to_desktop(self):
        self.shared_vars['merged_pdf_folder'].set(
            os.path.join(os.path.expanduser('~'), 'Desktop'))

    def _merged_same_as_svg(self):
        svg = self.shared_vars['svg_folder'].get()
        if svg:
            self.shared_vars['merged_pdf_folder'].set(svg)

    def _get_merged_pdf_path(self):
        """
        CHANGED: Return the full absolute path for the merged PDF.
        Falls back to <output_dir>/merged_output.pdf if the user left
        the folder field blank.
        """
        folder   = self.shared_vars['merged_pdf_folder'].get().strip()
        filename = self.shared_vars['merged_pdf_filename'].get().strip()
        if not filename:
            filename = 'merged_output.pdf'
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        if not folder:
            # default: same as the individual PDFs output folder
            folder = os.path.join(
                self.shared_vars['output_location'].get(),
                self.shared_vars['output_folder'].get())
        return os.path.join(folder, filename)

    # ------------------------------------------------------------------
    # File list panel helpers
    # ------------------------------------------------------------------

    def _on_file_list_configure(self, event):
        self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))

    def _on_canvas_resize(self, event):
        self.list_canvas.itemconfig(self.file_list_window, width=event.width)

    def _update_selected_count(self, *args):
        selected = sum(1 for v in self.svg_file_vars.values() if v.get())
        total = len(self.svg_file_vars)
        self.selected_count_label.config(text=f"{selected} of {total} selected")

    def populate_file_list(self, svg_files):
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        self.svg_file_vars.clear()

        if not svg_files:
            ttk.Label(self.file_list_frame,
                      text="No SVG files found in this folder.",
                      foreground="gray", font=("Arial", 9, "italic")).pack(
                padx=8, pady=8, anchor='w')
            self._update_selected_count()
            return

        for filename in sorted(svg_files, key=str.lower):
            var = tk.BooleanVar(value=True)
            var.trace_add('write', self._update_selected_count)
            self.svg_file_vars[filename] = var
            cb = ttk.Checkbutton(self.file_list_frame, text=filename, variable=var)
            cb.pack(anchor='w', padx=6, pady=1)

        self._update_selected_count()

    def select_all_files(self):
        for var in self.svg_file_vars.values():
            var.set(True)

    def deselect_all_files(self):
        for var in self.svg_file_vars.values():
            var.set(False)

    def get_selected_files(self):
        return [fname for fname, var in self.svg_file_vars.items() if var.get()]

    # ------------------------------------------------------------------
    # Format / UI helpers
    # ------------------------------------------------------------------

    def _on_format_change(self, *args):
        """
        CHANGED: Update auto-merge label and show/hide the merged PDF
        destination panel depending on format + merge checkbox state.
        """
        fmt        = self.shared_vars['output_format'].get()
        auto_merge = self.shared_vars['auto_merge'].get()

        if fmt == 'png':
            self.auto_merge_checkbox.config(
                text="Merge PNGs to PDF automatically after conversion")
            # Hide the vector-specific merged PDF location panel
            self.merged_pdf_frame.grid_remove()
        else:
            self.auto_merge_checkbox.config(
                text="Merge all PDF pages into one final PDF after conversion")
            # Show the panel only when merge is ticked
            if auto_merge:
                self.merged_pdf_frame.grid()
            else:
                self.merged_pdf_frame.grid_remove()

    def toggle_layer_controls(self):
        enabled = self.shared_vars['layer_control_enabled'].get()
        if enabled:
            self.toggle_layer_input_mode()
        else:
            self.csv_frame.pack_forget()
            self.text_frame.pack_forget()

    def toggle_layer_input_mode(self):
        if not self.shared_vars['layer_control_enabled'].get():
            return
        mode = self.shared_vars['layer_control_mode'].get()
        if mode == 'csv':
            self.text_frame.pack_forget()
            self.csv_frame.pack(fill='x', expand=True)
        else:
            self.csv_frame.pack_forget()
            self.text_frame.pack(fill='both', expand=True)

    # ------------------------------------------------------------------
    # Folder browsing / quick-select
    # ------------------------------------------------------------------

    def browse_svg_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing SVG files")
        if folder:
            self.shared_vars['svg_folder'].set(folder)
            self.update_file_count()
            if not self.shared_vars['output_location'].get():
                self.shared_vars['output_location'].set(folder)

    def browse_output_location(self):
        folder = filedialog.askdirectory(title="Select output folder location")
        if folder:
            self.shared_vars['output_location'].set(folder)

    def use_current_dir(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.shared_vars['svg_folder'].set(current_dir)
        self.update_file_count()
        if not self.shared_vars['output_location'].get():
            self.shared_vars['output_location'].set(current_dir)

    def use_desktop(self):
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.shared_vars['svg_folder'].set(desktop)
        self.update_file_count()
        if not self.shared_vars['output_location'].get():
            self.shared_vars['output_location'].set(desktop)

    def same_as_svg_folder(self):
        if self.shared_vars['svg_folder'].get():
            self.shared_vars['output_location'].set(self.shared_vars['svg_folder'].get())
        else:
            messagebox.showwarning("Warning", "Please select SVG folder first")

    def output_to_desktop(self):
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.shared_vars['output_location'].set(desktop)

    def update_file_count(self):
        folder = self.shared_vars['svg_folder'].get()
        if folder and os.path.exists(folder):
            svg_files = [f for f in os.listdir(folder) if f.lower().endswith('.svg')]
            count = len(svg_files)
            self.file_count_label.config(text=f"SVG files found: {count}")
            self.populate_file_list(svg_files)
            if count > 0:
                self.gui_app.log_message(f"Found {count} SVG files in: {folder}")
            else:
                self.gui_app.log_message("No SVG files found in selected folder")
        else:
            self.file_count_label.config(text="SVG files found: 0")
            self.populate_file_list([])

    # ------------------------------------------------------------------
    # Progress helpers
    # ------------------------------------------------------------------

    def update_progress(self, current, total, file_name=None):
        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_bar['value'] = percentage
        self.progress_percentage.config(text=f"{percentage}%")
        if file_name:
            self.progress_text.config(text=f"Processing: {file_name}")
            self.progress_details.config(
                text=f"File {current} of {total} - {os.path.basename(file_name)}")
        else:
            self.progress_text.config(text=f"Processing file {current} of {total}")
            self.progress_details.config(text=f"Progress: {current}/{total} files")
        self.gui_app.root.update_idletasks()

    def reset_progress(self, total_files):
        self.total_files = total_files
        self.current_progress = 0
        self.progress_bar['value'] = 0
        self.progress_percentage.config(text="0%")
        self.progress_text.config(text="Starting conversion...")
        self.progress_details.config(text=f"Total files to process: {total_files}")
        self.gui_app.root.update_idletasks()

    def increment_progress(self, file_name=None):
        self.current_progress += 1
        self.update_progress(self.current_progress, self.total_files, file_name)

    def set_progress_complete(self, message="Conversion complete!"):
        self.progress_bar['value'] = 100
        self.progress_percentage.config(text="100%")
        self.progress_text.config(text=message)
        self.progress_details.config(
            text=f"Successfully processed {self.total_files} files")

    def set_progress_error(self, message="Conversion failed"):
        self.progress_text.config(text=message, foreground="red")
        self.progress_details.config(text="Check log for details")

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    # ------------------------------------------------------------------
    # Layer CSV / Text parsing
    # ------------------------------------------------------------------

    def browse_layer_csv(self):
        filepath = filedialog.askopenfilename(
            title="Select Layer Control CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if filepath:
            self.shared_vars['layer_csv_path'].set(filepath)
            self.gui_app.log_message(f"Layer CSV loaded: {filepath}")

    def get_layer_control_data(self):
        if not self.shared_vars['layer_control_enabled'].get():
            return None
        mode = self.shared_vars['layer_control_mode'].get()
        if mode == 'csv':
            csv_path = self.shared_vars['layer_csv_path'].get()
            if csv_path and os.path.exists(csv_path):
                return self.parse_layer_csv(csv_path)
            else:
                messagebox.showwarning("Warning", "CSV file not found or not selected")
                return None
        else:
            text_content = self.layer_text.get(1.0, tk.END).strip()
            if text_content:
                return self.parse_layer_text(text_content)
            else:
                messagebox.showwarning("Warning", "No layer rules entered in text field")
                return None

    def parse_layer_csv(self, csv_path):
        layer_rules = {}
        try:
            import csv
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        layer_name = row[0].strip()
                        visibility = row[1].strip().lower()
                        filename   = row[2].strip() if len(row) > 2 else None
                        if visibility in ['show', 'hide', 'visible', 'invisible']:
                            action = 'show' if visibility in ['show', 'visible'] else 'hide'
                            key = filename if filename else 'global'
                            if key not in layer_rules:
                                layer_rules[key] = {}
                            layer_rules[key][layer_name] = action
            return layer_rules
        except Exception as e:
            self.gui_app.log_message(f"❌ Error parsing CSV: {str(e)}")
            return None

    def parse_layer_text(self, text_content):
        layer_rules = {}
        for line in text_content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or ':' not in line:
                continue
            parts = line.split(' for:')
            layer_part = parts[0].strip()
            if ':' not in layer_part:
                continue
            layer_name, action = layer_part.split(':', 1)
            layer_name = layer_name.strip()
            action     = action.strip().lower()
            if action not in ['show', 'hide', 'visible', 'invisible']:
                continue
            action   = 'show' if action in ['show', 'visible'] else 'hide'
            filename = parts[1].strip() if len(parts) > 1 else None
            key = filename if filename else 'global'
            if key not in layer_rules:
                layer_rules[key] = {}
            layer_rules[key][layer_name] = action
        return layer_rules

    # ------------------------------------------------------------------
    # Conversion entry point
    # ------------------------------------------------------------------

    def start_conversion(self):
        if not self.shared_vars['svg_folder'].get():
            messagebox.showerror("Error", "Please select a folder containing SVG files")
            return

        if not self.shared_vars['output_location'].get():
            self.shared_vars['output_location'].set(self.shared_vars['svg_folder'].get())

        if not self.shared_vars['dpi'].get().isdigit():
            messagebox.showerror("Error", "DPI must be a number")
            return

        selected_files = self.get_selected_files()
        if not selected_files:
            messagebox.showerror("Error",
                                 "No SVG files selected. Check at least one file to convert.")
            return

        # CHANGED: validate merged PDF filename when in vector+merge mode
        fmt        = self.shared_vars['output_format'].get()
        auto_merge = self.shared_vars['auto_merge'].get()
        if fmt == 'vector' and auto_merge:
            merged_path = self._get_merged_pdf_path()
            self.gui_app.log_message(f"📄 Merged PDF will be saved to: {merged_path}")

        layer_rules = None
        if self.shared_vars['layer_control_enabled'].get():
            layer_rules = self.get_layer_control_data()
            if layer_rules:
                self.gui_app.log_message("✅ Layer control rules loaded")
                self.shared_vars['layer_rules'] = layer_rules
            else:
                return

        self.reset_progress(len(selected_files))
        self.convert_btn.config(state='disabled', bg="#6c757d")

        thread = threading.Thread(
            target=self.run_conversion_and_merge,
            kwargs={'selected_files': selected_files})
        thread.daemon = True
        thread.start()

    def run_conversion_and_merge(self, selected_files=None):
        try:
            output_format = self.shared_vars['output_format'].get()
            success       = self.run_conversion(selected_files=selected_files)

            if success:
                auto_merge = self.shared_vars['auto_merge'].get()

                if output_format == 'png' and auto_merge:
                    self.gui_app.log_message("\n" + "=" * 50)
                    self.gui_app.log_message("Starting automatic PDF merge (PNG -> PDF)...")
                    self.gui_app.log_message("=" * 50)
                    self.gui_app.root.after(
                        0, lambda: self.progress_text.config(text="Starting PDF merge..."))
                    self.gui_app.root.after(
                        0, lambda: self.progress_details.config(text="Merging PNGs to PDF"))
                    self.trigger_pdf_merge()

                elif output_format == 'vector' and auto_merge:
                    # CHANGED: vector merge was already handled inside batch_convert
                    # (merged_pdf_path was passed in).  Just open the folder.
                    complete_output_path = os.path.join(
                        self.shared_vars['output_location'].get(),
                        self.shared_vars['output_folder'].get())
                    if self.shared_vars['open_output'].get() and \
                            os.path.exists(complete_output_path):
                        try:
                            os.startfile(complete_output_path)
                        except Exception:
                            pass

                    # CHANGED: also open the folder containing the merged PDF
                    # if it differs from the individual PDFs folder
                    merged_folder = self.shared_vars['merged_pdf_folder'].get().strip()
                    if (merged_folder and
                            os.path.exists(merged_folder) and
                            merged_folder != complete_output_path and
                            self.shared_vars['open_output'].get()):
                        try:
                            os.startfile(merged_folder)
                        except Exception:
                            pass

        except Exception as e:
            self.gui_app.log_message(f"❌ Error: {str(e)}")
            self.gui_app.root.after(
                0, lambda: self.set_progress_error(f"Error: {str(e)}"))
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        finally:
            self.gui_app.root.after(
                0, lambda: self.convert_btn.config(state='normal', bg="#0078D7"))

    def run_conversion(self, selected_files=None):
        """Run the SVG conversion, restricted to `selected_files` if provided."""
        try:
            output_format = self.shared_vars['output_format'].get()

            if output_format == 'png':
                import png as conversion_module
                format_name = "PNG"
            else:
                import vector as conversion_module
                format_name = "PDF (Vector-preserving)"

            svg_folder        = self.shared_vars['svg_folder'].get()
            output_location   = self.shared_vars['output_location'].get()
            output_folder     = self.shared_vars['output_folder'].get()
            dpi               = self.shared_vars['dpi'].get()
            create_subfolders = self.shared_vars['create_subfolders'].get()
            inkscape_path     = self.shared_vars['inkscape_path'].get()
            open_output       = self.shared_vars['open_output'].get()
            auto_merge        = self.shared_vars['auto_merge'].get()

            layer_rules = None
            if self.shared_vars['layer_control_enabled'].get():
                layer_rules = self.shared_vars.get('layer_rules')

            complete_output_path = os.path.join(output_location, output_folder)

            if selected_files is None:
                selected_files = self.get_selected_files()

            if not selected_files:
                self.gui_app.log_message("❌ No SVG files selected!")
                return False

            # CHANGED: resolve merged PDF path before starting
            merged_pdf_path = None
            if output_format == 'vector' and auto_merge:
                merged_pdf_path = self._get_merged_pdf_path()

            self.gui_app.log_message("\n" + "=" * 50)
            self.gui_app.log_message(f"Starting {format_name} conversion...")
            self.gui_app.log_message(f"SVG Folder: {svg_folder}")
            self.gui_app.log_message(f"Output Location: {complete_output_path}")
            self.gui_app.log_message(f"DPI: {dpi}")
            self.gui_app.log_message(f"Output Format: {format_name}")
            self.gui_app.log_message(
                f"Files to convert: {len(selected_files)} of {len(self.svg_file_vars)}")
            self.gui_app.log_message(f"Create Subfolders: {create_subfolders}")
            self.gui_app.log_message(f"Inkscape Path: {inkscape_path}")
            if output_format == 'vector' and auto_merge:
                self.gui_app.log_message(
                    f"Auto-merge PDFs: True  ->  {merged_pdf_path}")  # CHANGED
            if layer_rules:
                self.gui_app.log_message(
                    f"Layer Control: Enabled ({len(layer_rules)} rule groups)")
            self.gui_app.log_message("=" * 50)

            os.makedirs(complete_output_path, exist_ok=True)

            def log_callback(message):
                self.gui_app.log_message(message)

            def progress_callback(current, total, message):
                percentage = int((current / total) * 100) if total > 0 else 0
                self.gui_app.root.after(
                    0, lambda p=percentage: self.progress_bar.config(value=p))
                self.gui_app.root.after(
                    0, lambda p=percentage: self.progress_percentage.config(
                        text=f"{p}%"))
                self.gui_app.root.after(
                    0, lambda m=message: self.progress_text.config(text=m))
                self.gui_app.root.after(
                    0, lambda c=current, t=total:
                    self.progress_details.config(text=f"File {c} of {t}"))
                self.gui_app.root.update_idletasks()

            self.gui_app.root.after(
                0, lambda: self.reset_progress(len(selected_files)))

            style = ttk.Style()
            style.theme_use('clam')
            style.configure("green.Horizontal.TProgressbar",
                            foreground='#28a745', background='#28a745',
                            troughcolor='#e9ecef', bordercolor='#e9ecef',
                            lightcolor='#28a745', darkcolor='#28a745')
            self.progress_bar.config(style="green.Horizontal.TProgressbar")

            if output_format == 'png':
                success = conversion_module.batch_convert(
                    svg_folder=svg_folder,
                    output_path=complete_output_path,
                    dpi=dpi,
                    create_subfolders=create_subfolders,
                    inkscape_path=inkscape_path,
                    log_callback=log_callback,
                    progress_callback=progress_callback,
                    layer_rules=layer_rules,
                    selected_files=selected_files,
                )
            else:
                # CHANGED: pass merged_pdf_path so vector.py writes the
                # final merged PDF to the user's chosen location
                success = conversion_module.batch_convert(
                    svg_folder=svg_folder,
                    output_path=complete_output_path,
                    dpi=dpi,
                    create_subfolders=create_subfolders,
                    inkscape_path=inkscape_path,
                    log_callback=log_callback,
                    progress_callback=progress_callback,
                    layer_rules=layer_rules,
                    auto_merge_pdf=auto_merge,
                    selected_files=selected_files,
                    merged_pdf_path=merged_pdf_path,  # CHANGED
                )

            if success:
                self.gui_app.log_message(
                    f"\n✅ {format_name} conversion completed successfully!")
                self.gui_app.root.after(
                    0, lambda: self.set_progress_complete(
                        f"{format_name} conversion successful!"))

                if output_format == 'png':
                    self.conversion_output_path = complete_output_path

                should_open = open_output and os.path.exists(complete_output_path)
                will_merge  = auto_merge

                if should_open and not will_merge:
                    try:
                        os.startfile(complete_output_path)
                        self.gui_app.log_message(
                            f"📂 Opened output folder: {complete_output_path}")
                    except Exception:
                        self.gui_app.log_message(
                            f"📂 Output folder: {complete_output_path}")
                elif should_open and will_merge:
                    self.gui_app.log_message(
                        f"📂 Output folder: {complete_output_path}")

                return True
            else:
                self.gui_app.log_message(f"\n❌ {format_name} conversion failed!")
                self.gui_app.root.after(
                    0, lambda: self.set_progress_error(f"{format_name} conversion failed"))
                messagebox.showerror(
                    "Error", f"{format_name} conversion failed. Check log for details.")
                return False

        except ImportError as e:
            module_name = ('png.py' if self.shared_vars['output_format'].get() == 'png'
                           else 'vector.py')
            self.gui_app.log_message(
                f"❌ Error: Could not import conversion module: {str(e)}")
            self.gui_app.root.after(
                0, lambda: self.set_progress_error("Missing conversion module"))
            messagebox.showerror(
                "Error",
                f"Could not import conversion module.\n"
                f"Make sure {module_name} is in the same directory.")
            return False
        except Exception as e:
            import traceback
            self.gui_app.log_message(f"❌ Error: {str(e)}")
            self.gui_app.log_message(f"Traceback: {traceback.format_exc()}")
            self.gui_app.root.after(
                0, lambda: self.set_progress_error(f"Error: {str(e)}"))
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            return False

    # ------------------------------------------------------------------
    # PDF merge (PNG -> PDF via merge tab)
    # ------------------------------------------------------------------

    def trigger_pdf_merge(self):
        try:
            if not hasattr(self, 'conversion_output_path'):
                self.gui_app.log_message(
                    "❌ No conversion output path found for PDF merge")
                return

            if self.shared_vars['output_format'].get() != 'png':
                self.gui_app.log_message(
                    "❌ PNG->PDF merge is only available for PNG output format")
                return

            pdf_merge_tab = self.gui_app.pdf_merge_tab
            pdf_merge_tab.manual_folder_var.set(self.conversion_output_path)
            self.gui_app.log_message(
                f"📁 PNG folder set to: {self.conversion_output_path}")

            pdf_merge_tab.output_location_var.set(self.conversion_output_path)
            pdf_merge_tab.pdf_filename_var.set("combined_output.pdf")

            pdf_merge_tab.scan_folder()
            self.gui_app.root.after(1000, pdf_merge_tab.start_merge)

        except Exception as e:
            import traceback
            self.gui_app.log_message(f"❌ Failed to trigger PDF merge: {str(e)}")
            self.gui_app.log_message(f"Traceback: {traceback.format_exc()}")