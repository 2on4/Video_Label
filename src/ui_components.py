"""
Modern UI Components for Video Labels Organizer
Following WCAG AA compliance and progressive disclosure patterns
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Callable, Dict, Any
import threading
import queue

# Design System Constants
COLORS = {
    'primary_blue': '#0066CC',
    'success_green': '#28A745', 
    'warning_orange': '#FFC107',
    'error_red': '#DC3545',
    'text_primary': '#212529',
    'text_secondary': '#6C757D',
    'background_primary': '#FFFFFF',
    'background_secondary': '#F8F9FA',
    'border': '#DEE2E6'
}

SPACING = {
    'xs': 4,
    'sm': 8, 
    'md': 16,
    'lg': 24,
    'xl': 32
}

FONTS = {
    'sm': ('Segoe UI', 14),
    'base': ('Segoe UI', 16),
    'lg': ('Segoe UI', 18),
    'xl': ('Segoe UI', 24),
    'bold': ('Segoe UI', 16, 'bold')
}

class ModernButton(tk.Button):
    """Modern button with consistent styling and accessibility"""
    
    def __init__(self, parent, text: str, command: Optional[Callable] = None, 
                 variant: str = 'primary', size: str = 'md', **kwargs):
        self.variant = variant
        self.size = size
        
        # Configure styling based on variant
        if variant == 'primary':
            bg = COLORS['primary_blue']
            fg = 'white'
            active_bg = '#0056B3'
        elif variant == 'success':
            bg = COLORS['success_green']
            fg = 'white'
            active_bg = '#218838'
        elif variant == 'warning':
            bg = COLORS['warning_orange']
            fg = COLORS['text_primary']
            active_bg = '#E0A800'
        elif variant == 'danger':
            bg = COLORS['error_red']
            fg = 'white'
            active_bg = '#C82333'
        else:  # secondary
            bg = COLORS['background_secondary']
            fg = COLORS['text_primary']
            active_bg = '#E2E6EA'
        
        # Configure size
        if size == 'sm':
            padding = (8, 12)
            font = FONTS['sm']
        elif size == 'lg':
            padding = (16, 32)
            font = FONTS['lg']
        else:  # md
            padding = (12, 24)
            font = FONTS['base']
        
        super().__init__(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            font=font,
            relief='flat',
            borderwidth=0,
            padx=padding[0],
            pady=padding[1],
            cursor='hand2',
            **kwargs
        )
        
        # Bind hover effects
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        
    def _on_enter(self, event):
        if self.variant == 'primary':
            self.configure(bg='#0056B3')
        elif self.variant == 'success':
            self.configure(bg='#218838')
        elif self.variant == 'warning':
            self.configure(bg='#E0A800')
        elif self.variant == 'danger':
            self.configure(bg='#C82333')
        else:
            self.configure(bg='#E2E6EA')
    
    def _on_leave(self, event):
        if self.variant == 'primary':
            self.configure(bg=COLORS['primary_blue'])
        elif self.variant == 'success':
            self.configure(bg=COLORS['success_green'])
        elif self.variant == 'warning':
            self.configure(bg=COLORS['warning_orange'])
        elif self.variant == 'danger':
            self.configure(bg=COLORS['error_red'])
        else:
            self.configure(bg=COLORS['background_secondary'])

class CollapsibleFrame(tk.Frame):
    """Collapsible section with smooth animation"""
    
    def __init__(self, parent, title: str, initially_expanded: bool = True, **kwargs):
        super().__init__(parent, bg=COLORS['background_primary'], **kwargs)
        
        self.expanded = initially_expanded
        
        # Header
        header_frame = tk.Frame(self, bg=COLORS['background_primary'])
        header_frame.pack(fill=tk.X, pady=(0, SPACING['sm']))
        
        self.toggle_btn = tk.Button(
            header_frame,
            text=f"{'▼' if initially_expanded else '▶'} {title}",
            font=FONTS['bold'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_primary'],
            relief='flat',
            borderwidth=0,
            cursor='hand2',
            command=self._toggle
        )
        self.toggle_btn.pack(anchor='w')
        
        # Content area
        self.content_frame = tk.Frame(self, bg=COLORS['background_primary'])
        if initially_expanded:
            self.content_frame.pack(fill=tk.BOTH, expand=True)
    
    def _toggle(self):
        if self.expanded:
            self.content_frame.pack_forget()
            self.toggle_btn.configure(text=f"▶ {self.toggle_btn.cget('text').split(' ', 1)[1]}")
        else:
            self.content_frame.pack(fill=tk.BOTH, expand=True)
            self.toggle_btn.configure(text=f"▼ {self.toggle_btn.cget('text').split(' ', 1)[1]}")
        self.expanded = not self.expanded

class DirectorySelector(tk.Frame):
    """Modern directory selector with validation"""
    
    def __init__(self, parent, label: str, initial_path: str = "", 
                 on_change: Optional[Callable] = None, **kwargs):
        super().__init__(parent, bg=COLORS['background_primary'], **kwargs)
        
        self.on_change = on_change
        self.path_var = tk.StringVar(value=initial_path)
        
        # Label
        tk.Label(
            self,
            text=label,
            font=FONTS['base'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_primary']
        ).pack(anchor='w', pady=(0, SPACING['xs']))
        
        # Input frame
        input_frame = tk.Frame(self, bg=COLORS['background_primary'])
        input_frame.pack(fill=tk.X, pady=(0, SPACING['sm']))
        
        # Entry
        self.entry = tk.Entry(
            input_frame,
            textvariable=self.path_var,
            font=FONTS['base'],
            relief='solid',
            borderwidth=1,
            bg=COLORS['background_primary'],
            fg=COLORS['text_primary']
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, SPACING['sm']))
        
        # Browse button
        ModernButton(
            input_frame,
            text="Browse",
            variant='secondary',
            size='sm',
            command=self._browse
        ).pack(side=tk.RIGHT)
        
        # Validation indicator
        self.validation_label = tk.Label(
            self,
            text="",
            font=FONTS['sm'],
            bg=COLORS['background_primary']
        )
        self.validation_label.pack(anchor='w')
        
        # Bind change event
        self.path_var.trace('w', self._on_path_change)
    
    def _browse(self):
        directory = filedialog.askdirectory(initialdir=self.path_var.get())
        if directory:
            self.path_var.set(directory)
    
    def _on_path_change(self, *args):
        path = self.path_var.get()
        if path:
            import os
            if os.path.exists(path) and os.path.isdir(path):
                self.validation_label.configure(
                    text="✓ Valid directory",
                    fg=COLORS['success_green']
                )
            else:
                self.validation_label.configure(
                    text="✗ Invalid directory",
                    fg=COLORS['error_red']
                )
        else:
            self.validation_label.configure(text="", fg=COLORS['text_primary'])
        
        if self.on_change:
            self.on_change(path)
    
    def get_path(self) -> str:
        return self.path_var.get()

class MultiDirectorySelector(tk.Frame):
    """Multi-directory selector with add/remove and validation"""
    def __init__(self, parent, label: str, initial_paths=None, on_change: Optional[Callable] = None, **kwargs):
        super().__init__(parent, bg=COLORS['background_primary'], **kwargs)
        self.on_change = on_change
        self.paths = initial_paths or []

        # Label
        tk.Label(
            self,
            text=label,
            font=FONTS['base'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_primary']
        ).pack(anchor='w', pady=(0, SPACING['xs']))

        # Listbox for directories
        list_frame = tk.Frame(self, bg=COLORS['background_primary'])
        list_frame.pack(fill=tk.X, pady=(0, SPACING['sm']))
        self.listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, height=4, font=FONTS['sm'], activestyle='dotbox')
        self.listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        for p in self.paths:
            self.listbox.insert(tk.END, p)

        # Add/Remove buttons
        btn_frame = tk.Frame(list_frame, bg=COLORS['background_primary'])
        btn_frame.pack(side=tk.RIGHT, padx=(SPACING['sm'], 0))
        ModernButton(btn_frame, text="Add Folder", variant='secondary', size='sm', command=self._add_folder).pack(fill=tk.X, pady=(0, SPACING['xs']))
        ModernButton(btn_frame, text="Remove Selected", variant='danger', size='sm', command=self._remove_selected).pack(fill=tk.X)

        # Validation label
        self.validation_label = tk.Label(self, text="", font=FONTS['sm'], bg=COLORS['background_primary'])
        self.validation_label.pack(anchor='w')

        self._validate()

    def _add_folder(self):
        from tkinter import filedialog
        directory = filedialog.askdirectory()
        if directory and directory not in self.paths:
            self.paths.append(directory)
            self.listbox.insert(tk.END, directory)
            self._validate()
            if self.on_change:
                self.on_change(self.paths)

    def _remove_selected(self):
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            removed = self.paths.pop(idx)
            self.listbox.delete(idx)
            self._validate()
            if self.on_change:
                self.on_change(self.paths)

    def _validate(self):
        import os
        if not self.paths:
            self.validation_label.configure(text="No directories selected", fg=COLORS['error_red'])
        else:
            invalid = [p for p in self.paths if not (os.path.exists(p) and os.path.isdir(p))]
            if invalid:
                self.validation_label.configure(text=f"Invalid: {', '.join(invalid)}", fg=COLORS['error_red'])
            else:
                self.validation_label.configure(text="All directories valid", fg=COLORS['success_green'])

    def get_paths(self):
        return self.paths[:]

class ProgressSection(tk.Frame):
    """Progress display with detailed feedback"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS['background_primary'], **kwargs)
        
        # Header
        header_frame = tk.Frame(self, bg=COLORS['background_primary'])
        header_frame.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        tk.Label(
            header_frame,
            text="Processing Progress",
            font=FONTS['lg'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_primary']
        ).pack(side=tk.LEFT)
        
        self.status_label = tk.Label(
            header_frame,
            text="Ready",
            font=FONTS['base'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_secondary']
        )
        self.status_label.pack(side=tk.RIGHT)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self,
            variable=self.progress_var,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        # Details frame
        self.details_frame = tk.Frame(self, bg=COLORS['background_primary'])
        self.details_frame.pack(fill=tk.BOTH, expand=True)
        
        # Statistics
        stats_frame = tk.Frame(self.details_frame, bg=COLORS['background_secondary'])
        stats_frame.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        self.files_found_label = tk.Label(
            stats_frame,
            text="Files found: 0",
            font=FONTS['base'],
            bg=COLORS['background_secondary'],
            fg=COLORS['text_primary']
        )
        self.files_found_label.pack(anchor='w', padx=SPACING['md'], pady=SPACING['sm'])
        
        self.files_processed_label = tk.Label(
            stats_frame,
            text="Files processed: 0",
            font=FONTS['base'],
            bg=COLORS['background_secondary'],
            fg=COLORS['text_primary']
        )
        self.files_processed_label.pack(anchor='w', padx=SPACING['md'], pady=(0, SPACING['sm']))
        
        # Log display
        log_frame = tk.Frame(self.details_frame, bg=COLORS['background_primary'])
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            log_frame,
            text="Activity Log",
            font=FONTS['base'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_primary']
        ).pack(anchor='w', pady=(0, SPACING['xs']))
        
        # Scrollable text area
        text_frame = tk.Frame(log_frame, bg=COLORS['background_primary'])
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(
            text_frame,
            font=FONTS['sm'],
            wrap=tk.WORD,
            bg=COLORS['background_secondary'],
            fg=COLORS['text_primary'],
            relief='solid',
            borderwidth=1
        )
        scrollbar = tk.Scrollbar(text_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def update_progress(self, value: float, status: str = None):
        """Update progress bar and status"""
        self.progress_var.set(value)
        if status:
            self.status_label.configure(text=status)
    
    def update_stats(self, files_found: int, files_processed: int):
        """Update statistics"""
        self.files_found_label.configure(text=f"Files found: {files_found}")
        self.files_processed_label.configure(text=f"Files processed: {files_processed}")
    
    def add_log_entry(self, message: str, level: str = 'info'):
        """Add log entry with color coding"""
        colors = {
            'info': COLORS['text_primary'],
            'success': COLORS['success_green'],
            'warning': COLORS['warning_orange'],
            'error': COLORS['error_red']
        }
        
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        
        # Color the last line
        last_line_start = self.log_text.index("end-2c linestart")
        last_line_end = self.log_text.index("end-1c")
        self.log_text.tag_add(f"level_{level}", last_line_start, last_line_end)
        self.log_text.tag_config(f"level_{level}", foreground=colors.get(level, COLORS['text_primary']))

class ActionPanel(tk.Frame):
    """Action controls with primary and secondary actions"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS['background_primary'], **kwargs)
        # DEBUG: Add a visible border and label
        self.config(highlightbackground=COLORS['error_red'], highlightthickness=2)
        tk.Label(self, text="[DEBUG: ActionPanel Rendered]", fg=COLORS['error_red'], bg=COLORS['background_primary']).pack()
        
        # Primary action
        self.primary_btn = ModernButton(
            self,
            text="Start Organisation",
            variant='primary',
            size='lg'
        )
        self.primary_btn.pack(pady=(0, SPACING['md']))
        
        # Secondary actions frame
        secondary_frame = tk.Frame(self, bg=COLORS['background_primary'])
        secondary_frame.pack(fill=tk.X)
        
        # Secondary buttons
        self.preview_btn = ModernButton(
            secondary_frame,
            text="Preview Changes",
            variant='secondary',
            size='sm'
        )
        self.preview_btn.pack(side=tk.LEFT, padx=(0, SPACING['sm']))
        
        self.view_log_btn = ModernButton(
            secondary_frame,
            text="View Log",
            variant='secondary',
            size='sm'
        )
        self.view_log_btn.pack(side=tk.LEFT, padx=(0, SPACING['sm']))
        
        self.clear_btn = ModernButton(
            secondary_frame,
            text="Clear",
            variant='danger',
            size='sm'
        )
        self.clear_btn.pack(side=tk.LEFT)
    
    def set_primary_action(self, command: Callable):
        """Set the primary action command"""
        self.primary_btn.configure(command=command)
    
    def set_secondary_actions(self, preview_cmd: Callable = None, 
                            view_log_cmd: Callable = None, 
                            clear_cmd: Callable = None):
        """Set secondary action commands"""
        if preview_cmd:
            self.preview_btn.configure(command=preview_cmd)
        if view_log_cmd:
            self.view_log_btn.configure(command=view_log_cmd)
        if clear_cmd:
            self.clear_btn.configure(command=clear_cmd)
    
    def set_primary_text(self, text: str):
        """Update primary button text"""
        self.primary_btn.configure(text=text)
    
    def set_primary_state(self, state: str):
        """Set primary button state (normal/disabled)"""
        self.primary_btn.configure(state=state) 