import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import os
import sys
import threading

class ConverterTab:
    def __init__(self, parent, main_app):
        self.main_app = main_app
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
        
        self.svg_folder = tk.StringVar()
        self.folder_entry = ttk.Entry(svg_entry_frame, textvariable=self.svg_folder)
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
        
        self.output_location = tk.StringVar()
        ttk.Entry(output_loc_entry_frame, textvariable=self.output_location).pack(
            side='left', fill='x', expand=True, padx=(0, 10))
        
        ttk.Button(output_loc_entry_frame, text="Browse", 
                  command=self.browse_output_location, width=10).pack(side='right')
        
        # Output folder name
        output_name_frame = ttk.Frame(output_frame)
        output_name_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        self.output_folder = tk.StringVar(value="png_output")
        ttk.Label(output_name_frame, text="Folder Name:").pack(side='left')
        ttk.Entry(output_name_frame, textvariable=self.output_folder, width=20).pack(side='left', padx=(5, 10))
        
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
        
        self.dpi = tk.StringVar(value="96")
        dpi_values = [72, 96, 150, 300]
        for dpi_val in dpi_values:
            ttk.Button(dpi_buttons_frame, text=str(dpi_val), width=6,
                      command=lambda v=dpi_val: self.dpi.set(str(v))).pack(side='left', padx=2)
        
        ttk.Label(dpi_buttons_frame, text="Custom:").pack(side='left', padx=(10, 5))
        ttk.Entry(dpi_buttons_frame, textvariable=self.dpi, width=8).pack(side='left')
        
        # Options
        options_frame = ttk.Frame(conv_frame)
        options_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 5))
        
        self.create_subfolders = tk.BooleanVar(value=True)
        self.open_output = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(options_frame, text="Create subfolders for each SVG", 
                       variable=self.create_subfolders).pack(anchor='w', pady=2)
        
        ttk.Checkbutton(options_frame, text="Open output folder after conversion", 
                       variable=self.open_output).pack(anchor='w', pady=2)
        
        # Configure grid weights
        conv_frame.columnconfigure(0, weight=1)
        
        # Add padding at the bottom of scrollable content
        ttk.Frame(content, height=10).pack()
        
        # ====== BOTTOM SECTION (Always visible) ======
        bottom_container = ttk.Frame(main_frame)
        bottom_container.grid(row=1, column=0, sticky='nsew', pady=(5, 0))
        
        # Configure bottom container
        bottom_container.columnconfigure(0, weight=1)
        bottom_container.rowconfigure(0, weight=1)  # Log area
        bottom_container.rowconfigure(1, weight=0)  # Buttons
        
        # ====== LOG AREA ======
        log_frame = ttk.LabelFrame(bottom_container, text="Conversion Log", padding="10")
        log_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=(0, 5))
        
        # Configure log frame
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky='nsew')
        
        # ====== CONTROL BUTTONS ======
        button_frame = ttk.Frame(bottom_container)
        button_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=(0, 10))
        
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
                 command=self.main_app.root.quit,
                 bg="#f0f0f0", fg="black",
                 font=("Arial", 9),
                 padx=15, pady=8).pack(side='right')
    
    def browse_svg_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing SVG files")
        if folder:
            self.svg_folder.set(folder)
            self.update_file_count()
            
            # Auto-set output location to SVG folder if not set
            if not self.output_location.get():
                self.output_location.set(folder)
    
    def browse_output_location(self):
        folder = filedialog.askdirectory(title="Select output folder location")
        if folder:
            self.output_location.set(folder)
    
    def use_current_dir(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.svg_folder.set(current_dir)
        self.update_file_count()
        
        if not self.output_location.get():
            self.output_location.set(current_dir)
    
    def use_desktop(self):
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.svg_folder.set(desktop)
        self.update_file_count()
        
        if not self.output_location.get():
            self.output_location.set(desktop)
    
    def same_as_svg_folder(self):
        if self.svg_folder.get():
            self.output_location.set(self.svg_folder.get())
        else:
            messagebox.showwarning("Warning", "Please select SVG folder first")
    
    def output_to_desktop(self):
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.output_location.set(desktop)
    
    def update_file_count(self):
        folder = self.svg_folder.get()
        if folder and os.path.exists(folder):
            svg_files = [f for f in os.listdir(folder) if f.lower().endswith('.svg')]
            count = len(svg_files)
            self.file_count_label.config(text=f"SVG files found: {count}")
            
            if count > 0:
                self.log_message(f"Found {count} SVG files in: {folder}")
            else:
                self.log_message("No SVG files found in selected folder")
    
    def log_message(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.main_app.root.update()
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
    
    def start_conversion(self):
        if not self.svg_folder.get():
            messagebox.showerror("Error", "Please select a folder containing SVG files")
            return
        
        if not self.output_location.get():
            # Default to SVG folder if output location not specified
            self.output_location.set(self.svg_folder.get())
        
        if not self.dpi.get().isdigit():
            messagebox.showerror("Error", "DPI must be a number")
            return
        
        # Disable button during conversion
        self.convert_btn.config(state='disabled', bg="#6c757d")
        
        # Run conversion in separate thread
        thread = threading.Thread(target=self.run_conversion)
        thread.daemon = True
        thread.start()
    
    def run_conversion(self):
        try:
            # Prepare arguments for png.py
            svg_folder = self.svg_folder.get()
            output_location = self.output_location.get()
            output_folder = self.output_folder.get()
            dpi = self.dpi.get()
            
            # Build complete output path
            complete_output_path = os.path.join(output_location, output_folder)
            
            self.log_message("\n" + "="*50)
            self.log_message("Starting conversion...")
            self.log_message(f"SVG Folder: {svg_folder}")
            self.log_message(f"Output Location: {complete_output_path}")
            self.log_message(f"DPI: {dpi}")
            self.log_message(f"Create Subfolders: {self.create_subfolders.get()}")
            self.log_message("="*50)
            
            # Run png.py as a subprocess with additional parameter
            png_script = "png.py"
            if not os.path.exists(png_script):
                self.log_message("❌ Error: png.py not found in current directory!")
                return
            
            # Create output directory
            os.makedirs(complete_output_path, exist_ok=True)
            
            # Run the conversion - pass create_subfolders as 4th parameter
            create_subfolders_str = "true" if self.create_subfolders.get() else "false"
            cmd = [sys.executable, png_script, svg_folder, complete_output_path, dpi, create_subfolders_str]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8'
            )
            
            # Read output in real-time
            for line in process.stdout:
                clean_line = line.strip()
                if clean_line:
                    self.log_message(clean_line)
            
            process.wait()
            
            if process.returncode == 0:
                self.log_message("\n✅ Conversion completed successfully!")
                
                # Open output folder if option is selected
                if self.open_output.get() and os.path.exists(complete_output_path):
                    try:
                        os.startfile(complete_output_path)
                        self.log_message(f"📂 Opened output folder: {complete_output_path}")
                    except:
                        self.log_message(f"📂 Output folder: {complete_output_path}")
                
                messagebox.showinfo("Success", "SVG to PNG conversion completed!")
            else:
                self.log_message("\n❌ Conversion failed!")
                messagebox.showerror("Error", "Conversion failed. Check log for details.")
            
        except Exception as e:
            self.log_message(f"❌ Error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        finally:
            # Re-enable button
            self.main_app.root.after(0, lambda: self.convert_btn.config(state='normal', bg="#0078D7"))