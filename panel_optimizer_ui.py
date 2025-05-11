import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import json
import threading
from web.demo_last_saved import (
    Casting, Shape, optimize_panels, load_castings_from_json, print_results
)
import sys
import io

class PanelOptimizerUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Panel Optimizer System")
        self.root.geometry("1000x800")
        
        self.castings = []
        self.setup_ui()

    def setup_ui(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)

        # Create main tabs
        self.input_tab = ttk.Frame(self.notebook)
        self.results_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.input_tab, text="Input Data")
        self.notebook.add(self.results_tab, text="Results")

        self.setup_input_tab()
        self.setup_results_tab()

    def setup_input_tab(self):
        # Input method selection
        input_frame = ttk.LabelFrame(self.input_tab, text="Data Input Method")
        input_frame.pack(fill='x', padx=10, pady=5)

        self.input_method = tk.StringVar(value="json")
        ttk.Radiobutton(input_frame, text="Load from JSON", variable=self.input_method, 
                       value="json", command=self.toggle_input_method).pack(side='left', padx=5)
        ttk.Radiobutton(input_frame, text="Manual Input", variable=self.input_method, 
                       value="manual", command=self.toggle_input_method).pack(side='left', padx=5)

        # JSON input section
        self.json_frame = ttk.LabelFrame(self.input_tab, text="JSON Input")
        self.json_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(self.json_frame, text="Browse JSON File", 
                  command=self.browse_json).pack(padx=5, pady=5)
        self.json_path_var = tk.StringVar()
        ttk.Entry(self.json_frame, textvariable=self.json_path_var, 
                 state='readonly').pack(fill='x', padx=5, pady=5)

        # Manual input section
        self.manual_frame = ttk.LabelFrame(self.input_tab, text="Manual Input")
        self.manual_frame.pack(fill='x', padx=10, pady=5)
        
        # Casting controls
        casting_controls = ttk.Frame(self.manual_frame)
        casting_controls.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(casting_controls, text="Casting Name:").pack(side='left', padx=5)
        self.casting_name = ttk.Entry(casting_controls, width=20)
        self.casting_name.pack(side='left', padx=5)
        
        ttk.Button(casting_controls, text="Add Casting", 
                  command=self.add_casting).pack(side='left', padx=5)

        # Shape controls
        shape_controls = ttk.Frame(self.manual_frame)
        shape_controls.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(shape_controls, text="Shape Name:").pack(side='left', padx=5)
        self.shape_name = ttk.Entry(shape_controls, width=20)
        self.shape_name.pack(side='left', padx=5)
        
        ttk.Label(shape_controls, text="Side Lengths:").pack(side='left', padx=5)
        self.side_lengths = ttk.Entry(shape_controls, width=30)
        self.side_lengths.pack(side='left', padx=5)
        
        ttk.Button(shape_controls, text="Add Shape", 
                  command=self.add_shape).pack(side='left', padx=5)

        # Data preview
        preview_frame = ttk.LabelFrame(self.input_tab, text="Data Preview")
        preview_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.preview_text = ScrolledText(preview_frame, height=10)
        self.preview_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Optimization controls
        control_frame = ttk.Frame(self.input_tab)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(control_frame, text="Primary Casting:").pack(side='left', padx=5)
        self.primary_casting_var = tk.StringVar()
        self.primary_casting_select = ttk.Combobox(control_frame, 
                                                  textvariable=self.primary_casting_var)
        self.primary_casting_select.pack(side='left', padx=5)
        
        ttk.Button(control_frame, text="Run Optimization", 
                  command=self.run_optimization).pack(side='right', padx=5)

        # Initially hide manual input
        self.manual_frame.pack_forget()

    def setup_results_tab(self):
        # Results display
        self.results_text = ScrolledText(self.results_tab)
        self.results_text.pack(fill='both', expand=True, padx=10, pady=5)

        # Export button
        ttk.Button(self.results_tab, text="Export Results", 
                  command=self.export_results).pack(pady=5)

    def toggle_input_method(self):
        if self.input_method.get() == "json":
            self.manual_frame.pack_forget()
            self.json_frame.pack(after=self.input_frame)
        else:
            self.json_frame.pack_forget()
            self.manual_frame.pack(after=self.input_frame)

    def browse_json(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.json_path_var.set(filename)
            self.load_json_data()

    def load_json_data(self):
        try:
            self.castings = load_castings_from_json(self.json_path_var.get())
            self.update_preview()
            self.update_primary_casting_options()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON: {str(e)}")

    def add_casting(self):
        name = self.casting_name.get().strip()
        if name:
            casting = Casting(name)
            self.castings.append(casting)
            self.casting_name.delete(0, tk.END)
            self.update_preview()
            self.update_primary_casting_options()

    def add_shape(self):
        if not self.castings:
            messagebox.showwarning("Warning", "Please add a casting first")
            return

        name = self.shape_name.get().strip()
        lengths = self.side_lengths.get().strip()
        
        try:
            sides = [int(x) for x in lengths.split(',')]
            shape = Shape(name, sides)
            self.castings[-1].add_shape(shape)
            
            self.shape_name.delete(0, tk.END)
            self.side_lengths.delete(0, tk.END)
            self.update_preview()
        except ValueError:
            messagebox.showerror("Error", "Invalid side lengths. Use comma-separated numbers")

    def update_preview(self):
        self.preview_text.delete('1.0', tk.END)
        for casting in self.castings:
            self.preview_text.insert(tk.END, f"Casting: {casting.name}\n")
            for shape in casting.shapes:
                self.preview_text.insert(tk.END, 
                    f"  Shape: {shape.name}, Sides: {shape.sides}\n")
            self.preview_text.insert(tk.END, "\n")

    def update_primary_casting_options(self):
        options = [casting.name for casting in self.castings]
        self.primary_casting_select['values'] = options
        if options:
            self.primary_casting_select.set(options[0])

    def run_optimization(self):
        if not self.castings:
            messagebox.showwarning("Warning", "No castings available")
            return

        try:
            # Redirect stdout to capture print outputs
            output = io.StringIO()
            sys.stdout = output

            # Find primary casting index
            primary_name = self.primary_casting_var.get()
            primary_idx = next(i for i, c in enumerate(self.castings) 
                             if c.name == primary_name)

            # Run optimization in a separate thread
            def optimize():
                try:
                    optimize_panels(self.castings, primary_idx)
                    print_results(self.castings, primary_idx)
                    
                    # Update UI in main thread
                    self.root.after(0, lambda: self.show_results(output.getvalue()))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", 
                                  f"Optimization failed: {str(e)}"))
                finally:
                    sys.stdout = sys.__stdout__

            threading.Thread(target=optimize, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start optimization: {str(e)}")
            sys.stdout = sys.__stdout__

    def show_results(self, results):
        self.results_text.delete('1.0', tk.END)
        self.results_text.insert('1.0', results)
        self.notebook.select(self.results_tab)

    def export_results(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w') as f:
                f.write(self.results_text.get('1.0', tk.END))

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = PanelOptimizerUI()
    app.run()
