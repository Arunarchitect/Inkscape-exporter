import tkinter as tk
from tkinter import ttk, scrolledtext
import os

class SVGtoPNGGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SVG to PNG Converter")
        self.root.geometry("650x750")
        self.root.minsize(600, 700)
        
        # Set icon if available
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
        
        # Variables
        self.svg_folder = tk.StringVar()
        self.output_folder = tk.StringVar(value="png_output")
        self.output_location = tk.StringVar()
        self.dpi = tk.StringVar(value="96")
        self.create_subfolders = tk.BooleanVar(value=True)
        self.open_output = tk.BooleanVar(value=False)
        self.inkscape_path = tk.StringVar(value=r"C:\Program Files\Inkscape\bin\inkscape.exe")
        
        # Widget references (will be created in setup_ui)
        self.file_count_label = None
        self.log_text = None
        self.convert_btn = None
        self.folder_entry = None
        
        self.setup_ui()
    
    def setup_ui(self):
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill='both', expand=True)
        
        # Main Tab
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text='Converter')
        
        # Settings Tab
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text='Settings')
        
        self.setup_main_tab(main_tab)
        self.setup_settings_tab(settings_tab)
    
    def setup_main_tab(self, parent):
        # Create main frame with vertical arrangement
        main_frame = ttk.Frame(parent)
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
        
        self.folder_entry = ttk.Entry(svg_entry_frame, textvariable=self.svg_folder)
        self.folder_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        ttk.Button(svg_entry_frame, text="Browse", width=10).pack(side='right')
        
        # Quick folders for SVG
        svg_quick_frame = ttk.Frame(input_frame)
        svg_quick_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        ttk.Button(svg_quick_frame, text="Current Directory", width=15).pack(side='left', padx=(0, 5))
        ttk.Button(svg_quick_frame, text="Desktop", width=10).pack(side='left')
        
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
        
        ttk.Entry(output_loc_entry_frame, textvariable=self.output_location).pack(
            side='left', fill='x', expand=True, padx=(0, 10))
        
        ttk.Button(output_loc_entry_frame, text="Browse", width=10).pack(side='right')
        
        # Output folder name
        output_name_frame = ttk.Frame(output_frame)
        output_name_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        ttk.Label(output_name_frame, text="Folder Name:").pack(side='left')
        ttk.Entry(output_name_frame, textvariable=self.output_folder, width=20).pack(side='left', padx=(5, 10))
        
        # Quick output locations
        output_quick_frame = ttk.Frame(output_frame)
        output_quick_frame.grid(row=3, column=0, columnspan=2, sticky='w')
        
        ttk.Button(output_quick_frame, text="Same as SVG", width=12).pack(side='left', padx=(0, 5))
        ttk.Button(output_quick_frame, text="Desktop", width=10).pack(side='left', padx=(0, 5))
        ttk.Button(output_quick_frame, text="Custom", width=10).pack(side='left')
        
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
                      command=lambda v=dpi_val: self.dpi.set(str(v))).pack(side='left', padx=2)
        
        ttk.Label(dpi_buttons_frame, text="Custom:").pack(side='left', padx=(10, 5))
        ttk.Entry(dpi_buttons_frame, textvariable=self.dpi, width=8).pack(side='left')
        
        # Options
        options_frame = ttk.Frame(conv_frame)
        options_frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 5))
        
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
                                    bg="#0078D7", fg="white",
                                    font=("Arial", 10, "bold"),
                                    padx=20, pady=10,
                                    relief="raised", bd=2)
        self.convert_btn.pack(side='left', padx=(0, 10))
        
        tk.Button(left_button_frame, text="Clear Log",
                 bg="#f0f0f0", fg="black",
                 font=("Arial", 9),
                 padx=15, pady=8).pack(side='left')
        
        # Right side buttons
        right_button_frame = ttk.Frame(button_frame)
        right_button_frame.pack(side='right')
        
        tk.Button(right_button_frame, text="Exit",
                 bg="#f0f0f0", fg="black",
                 font=("Arial", 9),
                 padx=15, pady=8).pack(side='right')
    
    def setup_settings_tab(self, parent):
        # Create a frame with scroll
        settings_frame = ttk.Frame(parent)
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
        
        path_entry_frame = ttk.Frame(path_frame)
        path_entry_frame.pack(fill='x', pady=5)
        
        ttk.Entry(path_entry_frame, textvariable=self.inkscape_path).pack(
            side='left', fill='x', expand=True, padx=(0, 10))
        
        ttk.Button(path_entry_frame, text="Browse", width=10).pack(side='right')
        
        # Test Inkscape button
        test_button = tk.Button(path_frame, text="Test Inkscape Installation",
                               bg="#28a745", fg="white",
                               font=("Arial", 9, "bold"),
                               padx=15, pady=8)
        test_button.pack(pady=10)
        
        # About
        about_frame = ttk.LabelFrame(scrollable_settings, text="About", padding="10")
        about_frame.pack(fill='x', padx=10, pady=10)
        
        about_text = """SVG to PNG Batch Converter

Version: 1.1
Author: Your Name

This tool converts multiple SVG files to PNG format
using Inkscape command-line interface.

Features:
• Batch convert multiple SVG files
• Adjustable DPI quality
• Select custom output location
• Organized output folders
• Real-time progress log

Requirements:
• Inkscape 1.0+ installed
• Python 3.6+
"""
        
        about_label = ttk.Label(about_frame, text=about_text, justify='left', font=("Arial", 9))
        about_label.pack(anchor='w')
        
        # Add padding at bottom
        ttk.Frame(scrollable_settings, height=10).pack()
    
    # Public methods for gui.py to connect events
    def set_button_commands(self, commands_dict):
        """Set commands for all buttons"""
        # Find all buttons and set their commands
        # This is a simplified version - you'd need to modify to find all buttons
        
        # Example: Set convert button command
        if 'start_conversion' in commands_dict:
            self.convert_btn.config(command=commands_dict['start_conversion'])
        
        # You would add similar code for all other buttons
    
    def log_message(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def clear_log(self):
        """Clear log text"""
        self.log_text.delete(1.0, tk.END)
    
    def update_file_count(self, count):
        """Update file count display"""
        self.file_count_label.config(text=f"SVG files found: {count}")
    
    def get_input_values(self):
        """Get all input values as dictionary"""
        return {
            'svg_folder': self.svg_folder.get(),
            'output_folder': self.output_folder.get(),
            'output_location': self.output_location.get(),
            'dpi': self.dpi.get(),
            'create_subfolders': self.create_subfolders.get(),
            'open_output': self.open_output.get(),
            'inkscape_path': self.inkscape_path.get()
        }
    
    def disable_convert_button(self):
        """Disable convert button during conversion"""
        self.convert_btn.config(state='disabled', bg="#6c757d")
    
    def enable_convert_button(self):
        """Enable convert button after conversion"""
        self.convert_btn.config(state='normal', bg="#0078D7")