import tkinter as tk
from tkinter import ttk
from converter_tab import ConverterTab
from pdf_merger_tab import PDFMergerTab
from settings_tab import SettingsTab

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
        
        self.setup_notebook()
    
    def setup_notebook(self):
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill='both', expand=True)
        
        # Create tabs
        self.converter_tab = ConverterTab(notebook, self)
        self.pdf_merger_tab = PDFMergerTab(notebook, self)
        self.settings_tab = SettingsTab(notebook, self)
        
        # Add tabs to notebook
        notebook.add(self.converter_tab.frame, text='SVG to PNG')
        notebook.add(self.pdf_merger_tab.frame, text='PDF Merger')
        notebook.add(self.settings_tab.frame, text='Settings')