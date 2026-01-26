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
        
        ttk.Label(title_frame, text="🖼️ SVG to PNG Converter", 
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
        dpi_label = ttk.Label(conv_frame, text="DPI Quality:")
        dpi_label.grid(row=0, column=0, sticky='w', pady=(0, 5))
        
        dpi_buttons_frame = ttk.Frame(conv_frame)
        dpi_buttons_frame.grid(row=1, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        dpi_values = [72, 96, 150, 300]
        for dpi_val in dpi_values:
            ttk.Button(dpi_buttons_frame, text=str(dpi_val), width=6,
                      command=lambda v=dpi_val: self.shared_vars['dpi'].set(str(v))).pack(side='left', padx=2)
        
        ttk.Label(dpi_buttons_frame, text="Custom:").pack(side='left', padx=(10, 5))
        ttk.Entry(dpi_buttons_frame, textvariable=self.shared_vars['dpi'], width=8).pack(side='left')
        
        # Options
        options_frame = ttk.Frame(conv_frame)
        options_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 5))
        
        # Add auto-merge checkbox
        if 'auto_merge' not in self.shared_vars:
            self.shared_vars['auto_merge'] = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(options_frame, text="Merge to PDF automatically after conversion", 
                       variable=self.shared_vars['auto_merge']).pack(anchor='w', pady=2)
        
        ttk.Checkbutton(options_frame, text="Create subfolders for each SVG", 
                       variable=self.shared_vars['create_subfolders']).pack(anchor='w', pady=2)
        
        ttk.Checkbutton(options_frame, text="Open output folder after conversion", 
                       variable=self.shared_vars['open_output']).pack(anchor='w', pady=2)
        
        # Configure grid weights
        conv_frame.columnconfigure(0, weight=1)
        
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
        """Run conversion and optionally merge to PDF"""
        try:
            # Run the conversion first
            success = self.run_conversion()
            
            # If conversion successful and auto-merge is checked
            if success and self.shared_vars.get('auto_merge', tk.BooleanVar(value=True)).get():
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
        """Run the SVG to PNG conversion with real-time progress tracking"""
        try:
            # Import png module directly
            sys.path.append('.')  # Add current directory to path
            import png as png_module
            
            # Prepare arguments
            svg_folder = self.shared_vars['svg_folder'].get()
            output_location = self.shared_vars['output_location'].get()
            output_folder = self.shared_vars['output_folder'].get()
            dpi = self.shared_vars['dpi'].get()
            create_subfolders = self.shared_vars['create_subfolders'].get()
            inkscape_path = self.shared_vars['inkscape_path'].get()
            open_output = self.shared_vars['open_output'].get()
            
            # Build complete output path
            complete_output_path = os.path.join(output_location, output_folder)
            
            self.gui_app.log_message("\n" + "="*50)
            self.gui_app.log_message("Starting conversion...")
            self.gui_app.log_message(f"SVG Folder: {svg_folder}")
            self.gui_app.log_message(f"Output Location: {complete_output_path}")
            self.gui_app.log_message(f"DPI: {dpi}")
            self.gui_app.log_message(f"Create Subfolders: {create_subfolders}")
            self.gui_app.log_message(f"Inkscape Path: {inkscape_path}")
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
                
                # Update progress bar - FIXED: use config instead of assignment
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
            success = png_module.batch_convert(
                svg_folder=svg_folder,
                output_path=complete_output_path,
                dpi=dpi,
                create_subfolders=create_subfolders,
                inkscape_path=inkscape_path,
                log_callback=log_callback,
                progress_callback=progress_callback
            )
            
            if success:
                self.gui_app.log_message("\n✅ Conversion completed successfully!")
                self.gui_app.root.after(0, lambda: self.set_progress_complete("Conversion successful!"))
                
                # Store the conversion output path for PDF merge
                self.conversion_output_path = complete_output_path
                
                # Open output folder if option is selected (but not if auto-merge is on)
                if open_output and os.path.exists(complete_output_path) and not self.shared_vars.get('auto_merge', tk.BooleanVar(value=True)).get():
                    try:
                        os.startfile(complete_output_path)
                        self.gui_app.log_message(f"📂 Opened output folder: {complete_output_path}")
                    except:
                        self.gui_app.log_message(f"📂 Output folder: {complete_output_path}")
                
                return True
            else:
                self.gui_app.log_message("\n❌ Conversion failed!")
                self.gui_app.root.after(0, lambda: self.set_progress_error("Conversion failed"))
                messagebox.showerror("Error", "Conversion failed. Check log for details.")
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
        """Trigger the PDF merge after conversion"""
        try:
            if not hasattr(self, 'conversion_output_path'):
                self.gui_app.log_message("❌ No conversion output path found for PDF merge")
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