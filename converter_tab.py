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
        
        # Add layer control variables
        if 'layer_control_enabled' not in self.shared_vars:
            self.shared_vars['layer_control_enabled'] = tk.BooleanVar(value=False)
        if 'layer_csv_path' not in self.shared_vars:
            self.shared_vars['layer_csv_path'] = tk.StringVar()
        if 'layer_text_content' not in self.shared_vars:
            self.shared_vars['layer_text_content'] = tk.StringVar()
        if 'layer_control_mode' not in self.shared_vars:
            self.shared_vars['layer_control_mode'] = tk.StringVar(value='csv')  # 'csv' or 'text'
        if 'layer_rules' not in self.shared_vars:
            self.shared_vars['layer_rules'] = None
            
        # Add output format variable
        if 'output_format' not in self.shared_vars:
            self.shared_vars['output_format'] = tk.StringVar(value='png')  # 'png' or 'vector'
        
        # Create tab frame
        self.frame = ttk.Frame(parent)
        self.setup_ui()
    
    def setup_ui(self):
        # Create main frame with vertical arrangement
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill='both', expand=True)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)  # Scrollable content
        main_frame.rowconfigure(1, weight=0)  # Fixed bottom section
        
        # ====== TOP SECTION (Scrollable Content) ======
        top_container = ttk.Frame(main_frame)
        top_container.grid(row=0, column=0, sticky='nsew', pady=(0, 5))
        
        # Create canvas and scrollbar for top section
        canvas = tk.Canvas(top_container)
        scrollbar = ttk.Scrollbar(top_container, orient="vertical", command=canvas.yview)
        scrollable_content = ttk.Frame(canvas)
        
        scrollable_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # ====== CONTENT IN SCROLLABLE FRAME ======
        content = scrollable_content
        
        # Title
        title_frame = ttk.Frame(content)
        title_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        ttk.Label(title_frame, text="🔄 SVG Converter", 
                 font=("Arial", 16, "bold")).pack()
        
        # ====== INPUT SECTION ======
        input_frame = ttk.LabelFrame(content, text="Input Settings", padding="10")
        input_frame.pack(fill='x', padx=10, pady=5)
        
        # SVG Folder Selection
        svg_label = ttk.Label(input_frame, text="SVG Files Folder:")
        svg_label.grid(row=0, column=0, sticky='w', pady=(0, 5), columnspan=2)
        
        svg_entry_frame = ttk.Frame(input_frame)
        svg_entry_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 5))
        
        self.folder_entry = ttk.Entry(svg_entry_frame, textvariable=self.shared_vars['svg_folder'])
        self.folder_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        ttk.Button(svg_entry_frame, text="Browse", command=self.browse_svg_folder, width=10).pack(side='right')
        
        # Quick folders for SVG
        svg_quick_frame = ttk.Frame(input_frame)
        svg_quick_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        ttk.Button(svg_quick_frame, text="Current Directory", 
                  command=self.use_current_dir, width=15).pack(side='left', padx=(0, 5))
        
        ttk.Button(svg_quick_frame, text="Desktop", 
                  command=self.use_desktop, width=10).pack(side='left')
        
        # File count display
        self.file_count_label = ttk.Label(input_frame, text="SVG files found: 0")
        self.file_count_label.grid(row=3, column=0, sticky='w', pady=(0, 5), columnspan=2)
        
        # Configure grid weights
        input_frame.columnconfigure(0, weight=1)
        
        # ====== OUTPUT SECTION ======
        output_frame = ttk.LabelFrame(content, text="Output Settings", padding="10")
        output_frame.pack(fill='x', padx=10, pady=5)
        
        # Output Location Selection
        output_loc_label = ttk.Label(output_frame, text="Output Location:")
        output_loc_label.grid(row=0, column=0, sticky='w', pady=(0, 5), columnspan=2)
        
        output_loc_entry_frame = ttk.Frame(output_frame)
        output_loc_entry_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 5))
        
        ttk.Entry(output_loc_entry_frame, textvariable=self.shared_vars['output_location']).pack(
            side='left', fill='x', expand=True, padx=(0, 10))
        
        ttk.Button(output_loc_entry_frame, text="Browse", 
                  command=self.browse_output_location, width=10).pack(side='right')
        
        # Output folder name
        output_name_frame = ttk.Frame(output_frame)
        output_name_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        ttk.Label(output_name_frame, text="Folder Name:").pack(side='left')
        ttk.Entry(output_name_frame, textvariable=self.shared_vars['output_folder'], width=20).pack(side='left', padx=(5, 10))
        
        # Quick output locations
        output_quick_frame = ttk.Frame(output_frame)
        output_quick_frame.grid(row=3, column=0, columnspan=2, sticky='w')
        
        ttk.Button(output_quick_frame, text="Same as SVG", 
                  command=self.same_as_svg_folder, width=12).pack(side='left', padx=(0, 5))
        
        ttk.Button(output_quick_frame, text="Desktop", 
                  command=self.output_to_desktop, width=10).pack(side='left', padx=(0, 5))
        
        ttk.Button(output_quick_frame, text="Custom", 
                  command=self.browse_output_location, width=10).pack(side='left')
        
        # Configure grid weights
        output_frame.columnconfigure(0, weight=1)
        
        # ====== CONVERSION SETTINGS ======
        conv_frame = ttk.LabelFrame(content, text="Conversion Settings", padding="10")
        conv_frame.pack(fill='x', padx=10, pady=5)
        
        # DPI Settings
        dpi_label = ttk.Label(conv_frame, text="DPI Quality (for raster content):")
        dpi_label.grid(row=0, column=0, sticky='w', pady=(0, 5))
        
        dpi_buttons_frame = ttk.Frame(conv_frame)
        dpi_buttons_frame.grid(row=1, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        dpi_values = [72, 96, 150, 300]
        for dpi_val in dpi_values:
            ttk.Button(dpi_buttons_frame, text=str(dpi_val), width=6,
                      command=lambda v=dpi_val: self.shared_vars['dpi'].set(str(v))).pack(side='left', padx=2)
        
        ttk.Label(dpi_buttons_frame, text="Custom:").pack(side='left', padx=(10, 5))
        ttk.Entry(dpi_buttons_frame, textvariable=self.shared_vars['dpi'], width=8).pack(side='left')
        
        # Output Format Selection
        format_frame = ttk.Frame(conv_frame)
        format_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(10, 5))
        
        ttk.Label(format_frame, text="Output Format:").pack(side='left', padx=(0, 10))
        
        ttk.Radiobutton(format_frame, text="PNG (Raster)", 
                       variable=self.shared_vars['output_format'],
                       value='png').pack(side='left', padx=(0, 10))
        
        ttk.Radiobutton(format_frame, text="PDF (Vector)", 
                       variable=self.shared_vars['output_format'],
                       value='vector').pack(side='left')
        
        # Options
        options_frame = ttk.Frame(conv_frame)
        options_frame.grid(row=3, column=0, columnspan=2, sticky='w', pady=(10, 5))
        
        # Add auto-merge checkbox - only show for PNG format
        if 'auto_merge' not in self.shared_vars:
            self.shared_vars['auto_merge'] = tk.BooleanVar(value=True)
        
        self.auto_merge_checkbox = ttk.Checkbutton(options_frame, text="Merge to PDF automatically after conversion", 
                       variable=self.shared_vars['auto_merge'])
        self.auto_merge_checkbox.pack(anchor='w', pady=2)
        
        ttk.Checkbutton(options_frame, text="Create subfolders for each SVG", 
                       variable=self.shared_vars['create_subfolders']).pack(anchor='w', pady=2)
        
        ttk.Checkbutton(options_frame, text="Open output folder after conversion", 
                       variable=self.shared_vars['open_output']).pack(anchor='w', pady=2)
        
        # Configure grid weights
        conv_frame.columnconfigure(0, weight=1)
        
        # ====== LAYER CONTROL SECTION ======
        layer_frame = ttk.LabelFrame(content, text="Layer Visibility Control", padding="10")
        layer_frame.pack(fill='x', padx=10, pady=5)
        
        # Enable layer control checkbox
        ttk.Checkbutton(layer_frame, text="Enable layer visibility control",
                       variable=self.shared_vars['layer_control_enabled'],
                       command=self.toggle_layer_controls).pack(anchor='w', pady=(0, 10))
        
        # Mode selection (CSV or Text)
        mode_frame = ttk.Frame(layer_frame)
        mode_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(mode_frame, text="Input Mode:").pack(side='left', padx=(0, 10))
        
        ttk.Radiobutton(mode_frame, text="CSV File", 
                       variable=self.shared_vars['layer_control_mode'],
                       value='csv', command=self.toggle_layer_input_mode).pack(side='left', padx=(0, 10))
        
        ttk.Radiobutton(mode_frame, text="Text Input", 
                       variable=self.shared_vars['layer_control_mode'],
                       value='text', command=self.toggle_layer_input_mode).pack(side='left')
        
        # CSV File Input
        self.csv_frame = ttk.Frame(layer_frame)
        
        csv_label = ttk.Label(self.csv_frame, text="Layer Control CSV:")
        csv_label.grid(row=0, column=0, sticky='w', pady=(0, 5), columnspan=2)
        
        csv_entry_frame = ttk.Frame(self.csv_frame)
        csv_entry_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 5))
        
        self.csv_entry = ttk.Entry(csv_entry_frame, textvariable=self.shared_vars['layer_csv_path'])
        self.csv_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        ttk.Button(csv_entry_frame, text="Browse", 
                  command=self.browse_layer_csv, width=10).pack(side='right')
        
        # CSV instructions
        csv_help = "CSV Format: layer_name,visibility (show/hide),svg_filename(optional)"
        ttk.Label(self.csv_frame, text=csv_help, font=("Arial", 8), foreground="gray").grid(
            row=2, column=0, columnspan=2, sticky='w', pady=(0, 5))
        
        # Text Input
        self.text_frame = ttk.Frame(layer_frame)
        
        text_label = ttk.Label(self.text_frame, text="Layer Control Text:")
        text_label.grid(row=0, column=0, sticky='w', pady=(0, 5))
        
        # Text input area
        self.layer_text = scrolledtext.ScrolledText(self.text_frame, height=8, wrap=tk.WORD)
        self.layer_text.grid(row=1, column=0, sticky='nsew', pady=(0, 5))
        
        # Text input instructions
        text_help = """Enter layer visibility rules (one per line):
Format: layer_name:show/hide [for:filename.svg]
Examples:
  background:hide
  text_layer:show
  watermark:hide for:logo.svg
  foreground:show for:special_design.svg"""
        
        ttk.Label(self.text_frame, text=text_help, font=("Arial", 8), foreground="gray").grid(
            row=2, column=0, sticky='w')
        
        # Configure grid weights
        self.text_frame.columnconfigure(0, weight=1)
        self.text_frame.rowconfigure(1, weight=1)
        
        # Initialize visibility
        self.toggle_layer_controls()
        self.toggle_layer_input_mode()
        
        # Configure grid weights for layer frame
        layer_frame.columnconfigure(0, weight=1)
        
        # Add padding at the bottom of scrollable content
        ttk.Frame(content, height=10).pack()
        
        # ====== BOTTOM SECTION (Always visible) ======
        bottom_container = ttk.Frame(main_frame)
        bottom_container.grid(row=1, column=0, sticky='nsew', pady=(5, 0))
        
        # Configure bottom container
        bottom_container.columnconfigure(0, weight=1)
        bottom_container.rowconfigure(0, weight=1)  # Progress bar area
        bottom_container.rowconfigure(1, weight=1)  # Log area
        bottom_container.rowconfigure(2, weight=0)  # Buttons
        
        # ====== PROGRESS BAR SECTION ======
        progress_frame = ttk.LabelFrame(bottom_container, text="Conversion Progress", padding="10")
        progress_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=(0, 5))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=100)
        self.progress_bar.pack(fill='x', expand=True, pady=(0, 5))
        
        # Progress labels
        progress_labels_frame = ttk.Frame(progress_frame)
        progress_labels_frame.pack(fill='x', expand=True)
        
        self.progress_text = ttk.Label(progress_labels_frame, text="Ready to start...")
        self.progress_text.pack(side='left', anchor='w')
        
        self.progress_percentage = ttk.Label(progress_labels_frame, text="0%")
        self.progress_percentage.pack(side='right', anchor='e')
        
        # Progress details
        self.progress_details = ttk.Label(progress_frame, text="", font=("Arial", 9))
        self.progress_details.pack(fill='x', expand=True, pady=(2, 0))
        
        # ====== LOG AREA ======
        log_frame = ttk.LabelFrame(bottom_container, text="Conversion Log", padding="10")
        log_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0, 5))
        
        # Configure log frame
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky='nsew')
        
        # Share log widget with main GUI
        self.gui_app.set_log_widget(self.log_text)
        
        # ====== CONTROL BUTTONS ======
        button_frame = ttk.Frame(bottom_container)
        button_frame.grid(row=2, column=0, sticky='ew', padx=10, pady=(0, 10))
        
        # Left side buttons
        left_button_frame = ttk.Frame(button_frame)
        left_button_frame.pack(side='left', fill='x', expand=True)
        
        self.convert_btn = tk.Button(left_button_frame, text="START CONVERSION", 
                                    command=self.start_conversion,
                                    bg="#0078D7", fg="white",
                                    font=("Arial", 10, "bold"),
                                    padx=20, pady=10,
                                    relief="raised", bd=2)
        self.convert_btn.pack(side='left', padx=(0, 10))
        
        tk.Button(left_button_frame, text="Clear Log", 
                 command=self.clear_log,
                 bg="#f0f0f0", fg="black",
                 font=("Arial", 9),
                 padx=15, pady=8).pack(side='left')
        
        # Right side buttons
        right_button_frame = ttk.Frame(button_frame)
        right_button_frame.pack(side='right')
        
        tk.Button(right_button_frame, text="Exit", 
                 command=self.gui_app.root.quit,
                 bg="#f0f0f0", fg="black",
                 font=("Arial", 9),
                 padx=15, pady=8).pack(side='right')
        
        # Bind format change to update auto-merge checkbox state
        self.shared_vars['output_format'].trace('w', self.update_auto_merge_visibility)
        self.update_auto_merge_visibility()
    
    def update_auto_merge_visibility(self, *args):
        """Show/hide auto-merge checkbox based on output format"""
        output_format = self.shared_vars['output_format'].get()
        
        if output_format == 'png':
            self.auto_merge_checkbox.pack(anchor='w', pady=2)
        else:
            self.auto_merge_checkbox.pack_forget()
    
    def toggle_layer_controls(self):
        """Toggle layer control section visibility"""
        enabled = self.shared_vars['layer_control_enabled'].get()
        
        if enabled:
            self.toggle_layer_input_mode()
        else:
            self.csv_frame.pack_forget()
            self.text_frame.pack_forget()
    
    def toggle_layer_input_mode(self):
        """Switch between CSV and Text input modes"""
        if not self.shared_vars['layer_control_enabled'].get():
            return
            
        mode = self.shared_vars['layer_control_mode'].get()
        
        if mode == 'csv':
            self.text_frame.pack_forget()
            self.csv_frame.pack(fill='x', expand=True)
        else:
            self.csv_frame.pack_forget()
            self.text_frame.pack(fill='both', expand=True)
    
    def browse_layer_csv(self):
        """Browse for layer control CSV file"""
        filepath = filedialog.askopenfilename(
            title="Select Layer Control CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filepath:
            self.shared_vars['layer_csv_path'].set(filepath)
            self.gui_app.log_message(f"Layer CSV loaded: {filepath}")
    
    def get_layer_control_data(self):
        """Get layer control data based on selected mode"""
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
        else:  # text mode
            text_content = self.layer_text.get(1.0, tk.END).strip()
            if text_content:
                return self.parse_layer_text(text_content)
            else:
                messagebox.showwarning("Warning", "No layer rules entered in text field")
                return None
    
    def parse_layer_csv(self, csv_path):
        """Parse CSV file with layer control rules"""
        layer_rules = {}
        try:
            import csv
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        layer_name = row[0].strip()
                        visibility = row[1].strip().lower()
                        filename = row[2].strip() if len(row) > 2 else None
                        
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
        """Parse text input with layer control rules"""
        layer_rules = {}
        lines = text_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Parse format: layer_name:action [for:filename]
            if ':' not in line:
                continue
                
            # Split layer action and optional filename
            parts = line.split(' for:')
            layer_part = parts[0].strip()
            
            # Parse layer name and action
            if ':' not in layer_part:
                continue
                
            layer_name, action = layer_part.split(':', 1)
            layer_name = layer_name.strip()
            action = action.strip().lower()
            
            if action not in ['show', 'hide', 'visible', 'invisible']:
                continue
                
            action = 'show' if action in ['show', 'visible'] else 'hide'
            
            # Check for filename restriction
            filename = parts[1].strip() if len(parts) > 1 else None
            
            key = filename if filename else 'global'
            if key not in layer_rules:
                layer_rules[key] = {}
            layer_rules[key][layer_name] = action
        
        return layer_rules
    
    def browse_svg_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing SVG files")
        if folder:
            self.shared_vars['svg_folder'].set(folder)
            self.update_file_count()
            
            # Auto-set output location to SVG folder if not set
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
            
            if count > 0:
                self.gui_app.log_message(f"Found {count} SVG files in: {folder}")
            else:
                self.gui_app.log_message("No SVG files found in selected folder")
    
    def update_progress(self, current, total, file_name=None):
        """Update the progress bar and labels"""
        percentage = int((current / total) * 100) if total > 0 else 0
        
        # Update progress bar
        self.progress_bar['value'] = percentage
        
        # Update percentage label
        self.progress_percentage.config(text=f"{percentage}%")
        
        # Update progress text
        if file_name:
            self.progress_text.config(text=f"Processing: {file_name}")
            self.progress_details.config(text=f"File {current} of {total} - {os.path.basename(file_name)}")
        else:
            self.progress_text.config(text=f"Processing file {current} of {total}")
            self.progress_details.config(text=f"Progress: {current}/{total} files")
        
        # Force UI update
        self.gui_app.root.update_idletasks()
    
    def reset_progress(self, total_files):
        """Reset progress bar for new conversion"""
        self.total_files = total_files
        self.current_progress = 0
        self.progress_bar['value'] = 0
        self.progress_percentage.config(text="0%")
        self.progress_text.config(text="Starting conversion...")
        self.progress_details.config(text=f"Total files to process: {total_files}")
        self.gui_app.root.update_idletasks()
    
    def increment_progress(self, file_name=None):
        """Increment progress by one file"""
        self.current_progress += 1
        self.update_progress(self.current_progress, self.total_files, file_name)
    
    def set_progress_complete(self, message="Conversion complete!"):
        """Set progress bar to complete state"""
        self.progress_bar['value'] = 100
        self.progress_percentage.config(text="100%")
        self.progress_text.config(text=message)
        self.progress_details.config(text=f"Successfully processed {self.total_files} files")
    
    def set_progress_error(self, message="Conversion failed"):
        """Set progress bar to error state"""
        self.progress_text.config(text=message, foreground="red")
        self.progress_details.config(text="Check log for details")
    
    def clear_log(self):
        """Clear the log text widget"""
        self.log_text.delete(1.0, tk.END)
    
    def start_conversion(self):
        if not self.shared_vars['svg_folder'].get():
            messagebox.showerror("Error", "Please select a folder containing SVG files")
            return
        
        if not self.shared_vars['output_location'].get():
            # Default to SVG folder if output location not specified
            self.shared_vars['output_location'].set(self.shared_vars['svg_folder'].get())
        
        if not self.shared_vars['dpi'].get().isdigit():
            messagebox.showerror("Error", "DPI must be a number")
            return
        
        # Get layer control data if enabled
        layer_rules = None
        if self.shared_vars['layer_control_enabled'].get():
            layer_rules = self.get_layer_control_data()
            if layer_rules:
                self.gui_app.log_message("✅ Layer control rules loaded")
                # Store in shared vars for access by conversion script
                self.shared_vars['layer_rules'] = layer_rules
            else:
                return  # User cancelled or error occurred
        
        # Get total files for progress bar
        svg_folder = self.shared_vars['svg_folder'].get()
        svg_files = [f for f in os.listdir(svg_folder) if f.lower().endswith('.svg')] if os.path.exists(svg_folder) else []
        total_files = len(svg_files)
        
        if total_files == 0:
            messagebox.showerror("Error", "No SVG files found in selected folder")
            return
        
        # Reset progress bar
        self.reset_progress(total_files)
        
        # Disable button during conversion
        self.convert_btn.config(state='disabled', bg="#6c757d")
        
        # Run conversion in separate thread
        thread = threading.Thread(target=self.run_conversion_and_merge)
        thread.daemon = True
        thread.start()
    
    def run_conversion_and_merge(self):
        """Run conversion and optionally merge to PDF (only for PNG format)"""
        try:
            output_format = self.shared_vars['output_format'].get()
            
            # Run the conversion first
            success = self.run_conversion()
            
            # If conversion successful and auto-merge is checked AND format is PNG
            if success and output_format == 'png' and self.shared_vars.get('auto_merge', tk.BooleanVar(value=True)).get():
                self.gui_app.log_message("\n" + "="*50)
                self.gui_app.log_message("Starting automatic PDF merge...")
                self.gui_app.log_message("="*50)
                
                # Set progress for PDF merge
                self.gui_app.root.after(0, lambda: self.progress_text.config(text="Starting PDF merge..."))
                self.gui_app.root.after(0, lambda: self.progress_details.config(text="Merging PNG files to PDF"))
                
                self.trigger_pdf_merge()
            
        except Exception as e:
            self.gui_app.log_message(f"❌ Error: {str(e)}")
            self.gui_app.root.after(0, lambda: self.set_progress_error(f"Error: {str(e)}"))
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        finally:
            # Re-enable button
            self.gui_app.root.after(0, lambda: self.convert_btn.config(state='normal', bg="#0078D7"))
    
    def run_conversion(self):
        """Run the SVG to PNG/Vector conversion with real-time progress tracking"""
        try:
            output_format = self.shared_vars['output_format'].get()
            
            # Determine which module to use based on output format
            if output_format == 'png':
                import png as conversion_module
                format_name = "PNG"
            else:  # 'vector'
                import vector as conversion_module
                format_name = "PDF (Vector)"
            
            # Prepare arguments
            svg_folder = self.shared_vars['svg_folder'].get()
            output_location = self.shared_vars['output_location'].get()
            output_folder = self.shared_vars['output_folder'].get()
            dpi = self.shared_vars['dpi'].get()
            create_subfolders = self.shared_vars['create_subfolders'].get()
            inkscape_path = self.shared_vars['inkscape_path'].get()
            open_output = self.shared_vars['open_output'].get()
            
            # Get layer rules if enabled
            layer_rules = None
            if self.shared_vars['layer_control_enabled'].get():
                layer_rules = self.shared_vars.get('layer_rules')
            
            # Build complete output path
            complete_output_path = os.path.join(output_location, output_folder)
            
            # For vector output, check if auto-merge is enabled
            auto_merge_pdf = False
            if output_format == 'vector':
                # Check if auto-merge is checked (you might want to add this option to GUI)
                # For now, we'll default to True for vector output
                auto_merge_pdf = True
            
            self.gui_app.log_message("\n" + "="*50)
            self.gui_app.log_message(f"Starting {format_name} conversion...")
            self.gui_app.log_message(f"SVG Folder: {svg_folder}")
            self.gui_app.log_message(f"Output Location: {complete_output_path}")
            self.gui_app.log_message(f"DPI: {dpi}")
            self.gui_app.log_message(f"Output Format: {format_name}")
            self.gui_app.log_message(f"Create Subfolders: {create_subfolders}")
            self.gui_app.log_message(f"Inkscape Path: {inkscape_path}")
            if output_format == 'vector':
                self.gui_app.log_message(f"Auto-merge PDFs: {auto_merge_pdf}")
            if layer_rules:
                self.gui_app.log_message(f"Layer Control: Enabled ({len(layer_rules)} rules)")
            self.gui_app.log_message("="*50)
            
            # Create output directory
            os.makedirs(complete_output_path, exist_ok=True)
            
            # Define log callback
            def log_callback(message):
                self.gui_app.log_message(message)
            
            # Define progress callback
            def progress_callback(current, total, message):
                # Calculate percentage
                percentage = int((current / total) * 100) if total > 0 else 0
                
                # Update progress bar
                self.gui_app.root.after(0, lambda p=percentage: self.progress_bar.config(value=p))
                
                # Update labels
                self.gui_app.root.after(0, lambda p=percentage: self.progress_percentage.config(text=f"{p}%"))
                self.gui_app.root.after(0, lambda m=message: self.progress_text.config(text=m))
                self.gui_app.root.after(0, lambda c=current, t=total: 
                                    self.progress_details.config(text=f"File {c} of {t}"))
                
                # Force UI update
                self.gui_app.root.update_idletasks()
            
            # Get SVG files count for progress initialization
            svg_files = [f for f in os.listdir(svg_folder) if f.lower().endswith('.svg')] if os.path.exists(svg_folder) else []
            total_files = len(svg_files)
            
            if total_files == 0:
                self.gui_app.log_message("❌ No SVG files found!")
                return False
            
            # Reset progress bar
            self.gui_app.root.after(0, lambda: self.reset_progress(total_files))
            
            # Customize progress bar style for green color
            style = ttk.Style()
            style.theme_use('clam')
            style.configure("green.Horizontal.TProgressbar", 
                        foreground='#28a745', 
                        background='#28a745',
                        troughcolor='#e9ecef',
                        bordercolor='#e9ecef',
                        lightcolor='#28a745',
                        darkcolor='#28a745')
            
            # Apply green style to progress bar
            self.progress_bar.config(style="green.Horizontal.TProgressbar")
            
            # Run conversion directly (not as subprocess)
            if output_format == 'png':
                success = conversion_module.batch_convert(
                    svg_folder=svg_folder,
                    output_path=complete_output_path,
                    dpi=dpi,
                    create_subfolders=create_subfolders,
                    inkscape_path=inkscape_path,
                    log_callback=log_callback,
                    progress_callback=progress_callback,
                    layer_rules=layer_rules
                )
            else:  # vector
                success = conversion_module.batch_convert(
                    svg_folder=svg_folder,
                    output_path=complete_output_path,
                    dpi=dpi,
                    create_subfolders=create_subfolders,
                    inkscape_path=inkscape_path,
                    log_callback=log_callback,
                    progress_callback=progress_callback,
                    layer_rules=layer_rules,
                    auto_merge_pdf=auto_merge_pdf  # Pass auto-merge parameter
                )
            
            if success:
                self.gui_app.log_message(f"\n✅ {format_name} conversion completed successfully!")
                self.gui_app.root.after(0, lambda: self.set_progress_complete(f"{format_name} conversion successful!"))
                
                # Store the conversion output path for PDF merge (only for PNG)
                if output_format == 'png':
                    self.conversion_output_path = complete_output_path
                
                # Open output folder if option is selected (but not if auto-merge is on and format is PNG)
                if open_output and os.path.exists(complete_output_path):
                    if output_format == 'png' and self.shared_vars.get('auto_merge', tk.BooleanVar(value=True)).get():
                        # Don't open folder if auto-merge is enabled for PNG
                        self.gui_app.log_message(f"📂 Output folder: {complete_output_path}")
                    else:
                        try:
                            os.startfile(complete_output_path)
                            self.gui_app.log_message(f"📂 Opened output folder: {complete_output_path}")
                        except:
                            self.gui_app.log_message(f"📂 Output folder: {complete_output_path}")
                
                return True
            else:
                self.gui_app.log_message(f"\n❌ {format_name} conversion failed!")
                self.gui_app.root.after(0, lambda: self.set_progress_error(f"{format_name} conversion failed"))
                messagebox.showerror("Error", f"{format_name} conversion failed. Check log for details.")
                return False
            
        except ImportError as e:
            self.gui_app.log_message(f"❌ Error: Could not import conversion module: {str(e)}")
            self.gui_app.root.after(0, lambda: self.set_progress_error(f"Missing conversion module"))
            messagebox.showerror("Error", f"Could not import conversion module.\nMake sure you have {'png.py' if self.shared_vars['output_format'].get() == 'png' else 'vector.py'} in the same directory.")
            return False
        except Exception as e:
            self.gui_app.log_message(f"❌ Error: {str(e)}")
            import traceback
            self.gui_app.log_message(f"Traceback: {traceback.format_exc()}")
            self.gui_app.root.after(0, lambda: self.set_progress_error(f"Error: {str(e)}"))
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            return False
    
    
    
    
    def setup_progress_bar_style(self):
        """Setup the green progress bar style"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Create green progress bar style
        style.configure("green.Horizontal.TProgressbar", 
                    foreground='#28a745', 
                    background='#28a745',
                    troughcolor='#e9ecef',
                    bordercolor='#e9ecef',
                    lightcolor='#28a745',
                    darkcolor='#28a745')
        
        # Apply the style
        self.progress_bar.config(style="green.Horizontal.TProgressbar")
    
    def trigger_pdf_merge(self):
        """Trigger the PDF merge after PNG conversion"""
        try:
            if not hasattr(self, 'conversion_output_path'):
                self.gui_app.log_message("❌ No conversion output path found for PDF merge")
                return
            
            # Only trigger PDF merge if output format is PNG
            if self.shared_vars['output_format'].get() != 'png':
                self.gui_app.log_message("❌ PDF merge is only available for PNG output format")
                return
            
            # Get reference to PDF merge tab
            pdf_merge_tab = self.gui_app.pdf_merge_tab
            
            # Set the PNG folder to the converter output
            pdf_merge_tab.manual_folder_var.set(self.conversion_output_path)
            self.gui_app.log_message(f"📁 PNG folder set to: {self.conversion_output_path}")
            
            # Update the PDF output location
            pdf_output_path = os.path.join(self.conversion_output_path, "combined_output.pdf")
            pdf_merge_tab.output_location_var.set(self.conversion_output_path)
            pdf_merge_tab.pdf_filename_var.set("combined_output.pdf")
            
            # Trigger a scan of the folder
            pdf_merge_tab.scan_folder()
            
            # Wait a moment for UI to update, then start merge
            self.gui_app.root.after(1000, pdf_merge_tab.start_merge)
            
        except Exception as e:
            self.gui_app.log_message(f"❌ Failed to trigger PDF merge: {str(e)}")
            import traceback
            self.gui_app.log_message(f"Traceback: {traceback.format_exc()}")