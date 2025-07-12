import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional, List, Dict
from media_organiser import organize_files, get_proposed_changes
from logger import setup_logging
from config import DEFAULT_SOURCE, DEFAULT_TARGET, DRY_RUN

setup_logging()

class ConfirmationDialog(tk.Toplevel):
    def __init__(self, parent, proposed_changes: List[Dict]):
        super().__init__(parent)
        self.title("Review Proposed Changes")
        self.geometry("800x600")
        self.configure(bg="#f0f0f0")
        
        self.proposed_changes = proposed_changes
        self.confirmed = False
        
        # Create main frame
        frame = tk.Frame(self, bg="#f0f0f0", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        tk.Label(frame, text=f"Review {len(proposed_changes)} Proposed Changes", 
                bg="#f0f0f0", font=("Helvetica", 14, "bold")).pack(pady=(0, 10))
        
        # Create scrollable text area
        text_frame = tk.Frame(frame, bg="#f0f0f0")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.text_area = tk.Text(text_frame, font=("Consolas", 10), wrap=tk.WORD)
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=self.text_area.yview)
        self.text_area.configure(yscrollcommand=scrollbar.set)
        
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate with proposed changes
        self.populate_changes()
        
        # Buttons
        button_frame = tk.Frame(frame, bg="#f0f0f0")
        button_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(button_frame, text="Confirm & Proceed", command=self.confirm, 
                 bg="#28a745", fg="white", font=("Helvetica", 12, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=self.cancel, 
                 bg="#dc3545", fg="white", font=("Helvetica", 12)).pack(side=tk.LEFT, padx=5)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        self.wait_window()
    
    def populate_changes(self):
        """Populate the text area with proposed changes."""
        self.text_area.delete(1.0, tk.END)
        
        for i, change in enumerate(self.proposed_changes, 1):
            original = change['original']
            new_path = change['new_path']
            show_name = change['show_name']
            episode_info = change['episode_info']
            
            self.text_area.insert(tk.END, f"{i}. {show_name}\n")
            self.text_area.insert(tk.END, f"   Episode: {episode_info}\n")
            self.text_area.insert(tk.END, f"   From: {original}\n")
            self.text_area.insert(tk.END, f"   To: {new_path}\n")
            self.text_area.insert(tk.END, "-" * 80 + "\n\n")
    
    def confirm(self):
        self.confirmed = True
        self.destroy()
    
    def cancel(self):
        self.confirmed = False
        self.destroy()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Labels Organizer")
        self.geometry("600x500")
        self.configure(bg="#f0f0f0")
        
        # Variables
        self.source_var = tk.StringVar(value=DEFAULT_SOURCE)
        self.target_var = tk.StringVar(value=DEFAULT_TARGET)
        self.dry_var = tk.BooleanVar(value=DRY_RUN)
        
        # UI Elements (single-column, progressive disclosure)
        frame = tk.Frame(self, bg="#f0f0f0", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="Source Directory:", bg="#f0f0f0", font=("Helvetica", 12)).pack(anchor="w")
        tk.Entry(frame, textvariable=self.source_var, width=50, font=("Helvetica", 10)).pack(fill=tk.X)
        tk.Button(frame, text="Browse", command=self.browse_source).pack(pady=5)
        
        tk.Label(frame, text="Target Directory:", bg="#f0f0f0", font=("Helvetica", 12)).pack(anchor="w")
        tk.Entry(frame, textvariable=self.target_var, width=50, font=("Helvetica", 10)).pack(fill=tk.X)
        tk.Button(frame, text="Browse", command=self.browse_target).pack(pady=5)
        
        tk.Checkbutton(frame, text="Dry Run (Preview Only)", variable=self.dry_var, bg="#f0f0f0", font=("Helvetica", 10)).pack(anchor="w", pady=10)
        
        self.start_btn = tk.Button(frame, text="Analyze Files", command=self.start, bg="#007aff", fg="white", font=("Helvetica", 12, "bold"))
        self.start_btn.pack(pady=10)
        
        self.progress = ttk.Progressbar(frame, length=400, mode="determinate")
        self.progress.pack(pady=10)
        
        self.log_text = tk.Text(frame, height=8, font=("Helvetica", 10))
        self.log_text.pack(fill=tk.X, pady=10)
    
    def browse_source(self):
        dir = filedialog.askdirectory()
        if dir:
            self.source_var.set(dir)
    
    def browse_target(self):
        dir = filedialog.askdirectory()
        if dir:
            self.target_var.set(dir)
    
    def start(self):
        source = self.source_var.get()
        target = self.target_var.get()
        dry_run = self.dry_var.get()
        
        if not source or not target:
            messagebox.showerror("Error", "Select source and target directories.")
            return
        
        self.start_btn.config(state="disabled")
        self.progress['value'] = 0
        self.log_text.insert(tk.END, "Analyzing files...\n")
        
        try:
            def progress_update(percent: int):
                self.progress['value'] = percent
                self.update_idletasks()
            
            # Get proposed changes first
            proposed_changes = get_proposed_changes(source, target, progress_update)
            
            if not proposed_changes:
                self.log_text.insert(tk.END, "No changes to process.\n")
                return
            
            # Show confirmation dialog
            dialog = ConfirmationDialog(self, proposed_changes)
            
            if dialog.confirmed:
                self.log_text.insert(tk.END, f"Confirmed {len(proposed_changes)} changes. Proceeding...\n")
                # Now execute the actual changes
                organize_files(source, target, dry_run=False, progress_callback=progress_update)
                self.log_text.insert(tk.END, "Completed!\nCheck app.log for details.\n")
            else:
                self.log_text.insert(tk.END, "Operation cancelled by user.\n")
                
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.log_text.insert(tk.END, f"Error: {e}\n")
        finally:
            self.start_btn.config(state="normal")

if __name__ == "__main__":
    app = App()
    app.mainloop() 