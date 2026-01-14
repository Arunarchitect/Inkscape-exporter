import tkinter as tk
from tkinter import ttk
import converter_tab
import settings_tab
import pdf_merge_tab

class SVGtoPNGGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SVG to PNG Converter & PDF Merger")
        self.root.geometry("700x800")
        self.root.minsize(650, 750)
        
        # Set icon if available
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
        
        # Variables
        self.shared_vars = {
            'svg_folder': tk.StringVar(),
            'output_folder': tk.StringVar(value="png_output"),
            'output_location': tk.StringVar(),
            'dpi': tk.StringVar(value="96"),
            'create_subfolders': tk.BooleanVar(value=True),
            'open_output': tk.BooleanVar(value=False),
            'inkscape_path': tk.StringVar(value=r"C:\Program Files\Inkscape\bin\inkscape.exe")
        }
        
        # Reference to log text widget (will be set by converter tab)
        self.log_text = None
        
        self.setup_ui()
    
    def setup_ui(self):
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill='both', expand=True)
        
        # Initialize all tabs
        self.converter_tab = converter_tab.ConverterTab(notebook, self.shared_vars, self)
        self.settings_tab = settings_tab.SettingsTab(notebook, self.shared_vars, self)
        self.pdf_merge_tab = pdf_merge_tab.PDFMergeTab(notebook, self.shared_vars, self)
        
        # Add tabs to notebook
        notebook.add(self.converter_tab.frame, text='SVG to PNG')
        notebook.add(self.pdf_merge_tab.frame, text='PDF Merge')
        notebook.add(self.settings_tab.frame, text='Settings')
    
    def set_log_widget(self, log_widget):
        """Allow converter tab to set the log widget reference"""
        self.log_text = log_widget
    
    def log_message(self, message):
        """Centralized logging that both tabs can use"""
        if self.log_text:
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.root.update()

def main():
    root = tk.Tk()
    
    # Set style
    style = ttk.Style()
    style.theme_use('clam')
    
    # Center window on screen
    window_width = 700
    window_height = 800
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width/2 - window_width/2)
    center_y = int(screen_height/2 - window_height/2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    
    app = SVGtoPNGGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()