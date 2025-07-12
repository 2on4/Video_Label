"""
Modern Video Labels Organizer - Redesigned Interface
Following progressive disclosure patterns and WCAG AA compliance
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import queue
from typing import Optional, List, Dict, Any
import os
import logging
import traceback

from ui_components import (
    ModernButton, CollapsibleFrame, DirectorySelector, MultiDirectorySelector,
    ProgressSection, ActionPanel, COLORS, SPACING, FONTS
)
from media_organiser import organize_files, get_proposed_changes
from logger import setup_logging
from config import DEFAULT_SOURCE, DEFAULT_TARGET, DRY_RUN

setup_logging()

class ModernConfirmationDialog(tk.Toplevel):
    """Modern confirmation dialog with improved UX"""
    
    def __init__(self, parent, proposed_changes: List[Dict]):
        super().__init__(parent)
        self.title("Review Proposed Changes")
        self.geometry("900x700")
        self.configure(bg=COLORS['background_primary'])
        
        self.proposed_changes = proposed_changes
        self.confirmed = False
        
        # Center the dialog
        self.transient(parent)
        self.grab_set()
        
        # Use grid layout: content in row 0 (expands), buttons in row 1 (fixed)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Main content frame (scrollable area)
        main_frame = tk.Frame(self, bg=COLORS['background_primary'], padx=SPACING['lg'], pady=SPACING['lg'])
        main_frame.grid(row=0, column=0, sticky='nsew')
        main_frame.grid_rowconfigure(3, weight=1)  # Make changes_frame expand
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Header
        header_frame = tk.Frame(main_frame, bg=COLORS['background_primary'])
        header_frame.grid(row=0, column=0, sticky='ew', pady=(0, SPACING['md']))
        
        tk.Label(
            header_frame,
            text=f"Review {len(proposed_changes)} Proposed Changes",
            font=FONTS['xl'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_primary']
        ).pack(side=tk.LEFT)
        
        # Summary
        summary_frame = tk.Frame(main_frame, bg=COLORS['background_secondary'])
        summary_frame.grid(row=1, column=0, sticky='ew', pady=(0, SPACING['md']))
        
        tk.Label(
            summary_frame,
            text=f"Found {len(proposed_changes)} files to organize",
            font=FONTS['base'],
            bg=COLORS['background_secondary'],
            fg=COLORS['text_primary']
        ).pack(anchor='w', padx=SPACING['md'], pady=SPACING['sm'])
        
        # Changes list (scrollable)
        changes_frame = tk.Frame(main_frame, bg=COLORS['background_primary'])
        changes_frame.grid(row=3, column=0, sticky='nsew', pady=(0, SPACING['md']))
        changes_frame.grid_rowconfigure(0, weight=1)
        changes_frame.grid_columnconfigure(0, weight=1)
        
        tk.Label(
            changes_frame,
            text="Proposed Changes:",
            font=FONTS['lg'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_primary']
        ).pack(anchor='w', pady=(0, SPACING['sm']))
        
        # Scrollable text area
        text_frame = tk.Frame(changes_frame, bg=COLORS['background_primary'])
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_area = tk.Text(
            text_frame,
            font=FONTS['sm'],
            wrap=tk.WORD,
            bg=COLORS['background_secondary'],
            fg=COLORS['text_primary'],
            relief='solid',
            borderwidth=1,
            height=20
        )
        scrollbar = tk.Scrollbar(text_frame, orient='vertical', command=self.text_area.yview)
        self.text_area.configure(yscrollcommand=scrollbar.set)
        
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate with proposed changes
        self.populate_changes()
        
        # Action buttons (fixed footer)
        button_frame = tk.Frame(self, bg=COLORS['background_primary'])
        button_frame.grid(row=1, column=0, sticky='ew', padx=SPACING['lg'], pady=(0, SPACING['lg']))
        button_frame.grid_columnconfigure(0, weight=1)
        
        ModernButton(
            button_frame,
            text="Confirm & Proceed",
            variant='success',
            size='lg',
            command=self.confirm
        ).pack(side=tk.RIGHT, padx=(SPACING['sm'], 0))
        
        ModernButton(
            button_frame,
            text="Cancel",
            variant='danger',
            size='lg',
            command=self.cancel
        ).pack(side=tk.RIGHT)
        
        self.wait_window()
    
    def populate_changes(self):
        """Populate the text area with proposed changes."""
        self.text_area.delete(1.0, tk.END)
        
        for i, change in enumerate(self.proposed_changes, 1):
            original = change['original']
            new_path = change['new_path']
            show_name = change['show_name']
            episode_info = change['episode_info']
            
            # Format the change entry
            self.text_area.insert(tk.END, f"{i}. {show_name}\n", 'title')
            self.text_area.insert(tk.END, f"   Episode: {episode_info}\n", 'info')
            self.text_area.insert(tk.END, f"   From: {original}\n", 'path')
            self.text_area.insert(tk.END, f"   To: {new_path}\n", 'path')
            self.text_area.insert(tk.END, "-" * 80 + "\n\n", 'separator')
        
        # Configure text tags for styling
        self.text_area.tag_config('title', font=FONTS['bold'], foreground=COLORS['primary_blue'])
        self.text_area.tag_config('info', font=FONTS['sm'], foreground=COLORS['text_primary'])
        self.text_area.tag_config('path', font=FONTS['sm'], foreground=COLORS['text_secondary'])
        self.text_area.tag_config('separator', font=FONTS['sm'], foreground=COLORS['border'])
    
    def confirm(self):
        self.confirmed = True
        self.destroy()
    
    def cancel(self):
        self.confirmed = False
        self.destroy()

class ModernApp(tk.Tk):
    """Modern Video Labels Organizer with progressive disclosure"""
    
    def __init__(self):
        super().__init__()
        self.title("Video Labels Organizer")
        self.geometry("1000x800")
        self.configure(bg=COLORS['background_primary'])
        
        # State variables
        self.proposed_changes: List[Dict] = []
        self.is_processing = False
        
        # Setup UI
        self.setup_ui()
        self.setup_event_handlers()
        
        # Center window
        self.center_window()
    
    def center_window(self):
        """Center the window on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        """Setup the main UI with progressive disclosure"""
        
        # Main container with padding
        main_container = tk.Frame(self, bg=COLORS['background_primary'], padx=SPACING['lg'], pady=SPACING['lg'])
        main_container.pack(fill=tk.BOTH, expand=True)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1)

        # Content frame (row 0, expands)
        content_frame = tk.Frame(main_container, bg=COLORS['background_primary'])
        content_frame.grid(row=0, column=0, sticky='nsew')

        # Header Section
        self.setup_header(content_frame)
        # Configuration Panel (Collapsible)
        self.setup_configuration_panel(content_frame)
        # Preview & Progress Section
        self.setup_progress_section(content_frame)

        # Action Controls at the bottom (row 1, fixed)
        action_frame = tk.Frame(main_container, bg=COLORS['background_primary'])
        action_frame.grid(row=1, column=0, sticky='ew')
        self.setup_action_panel(action_frame)
    
    def setup_header(self, parent):
        """Setup header with branding and status"""
        header_frame = tk.Frame(parent, bg=COLORS['background_primary'])
        header_frame.pack(fill=tk.X, pady=(0, SPACING['lg']))
        
        # Application branding
        branding_frame = tk.Frame(header_frame, bg=COLORS['background_primary'])
        branding_frame.pack(side=tk.LEFT)
        
        tk.Label(
            branding_frame,
            text="Video Labels Organizer",
            font=FONTS['xl'],
            bg=COLORS['background_primary'],
            fg=COLORS['primary_blue']
        ).pack(anchor='w')
        
        tk.Label(
            branding_frame,
            text="AI-powered media organization",
            font=FONTS['sm'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_secondary']
        ).pack(anchor='w')
        
        # Status indicator
        self.status_frame = tk.Frame(header_frame, bg=COLORS['background_primary'])
        self.status_frame.pack(side=tk.RIGHT)
        
        self.status_label = tk.Label(
            self.status_frame,
            text="Ready",
            font=FONTS['base'],
            bg=COLORS['background_primary'],
            fg=COLORS['success_green']
        )
        self.status_label.pack(anchor='e')
        
        # Help button
        ModernButton(
            self.status_frame,
            text="?",
            variant='secondary',
            size='sm',
            command=self.show_help
        ).pack(anchor='e', pady=(SPACING['xs'], 0))
    
    def setup_configuration_panel(self, parent):
        """Setup collapsible configuration panel"""
        self.config_panel = CollapsibleFrame(
            parent,
            title="Configuration",
            initially_expanded=True
        )
        self.config_panel.pack(fill=tk.X, pady=(0, SPACING['lg']))
        
        # Instruction label for multi-folder selection
        tk.Label(
            self.config_panel.content_frame,
            text="Tip: Add multiple folders one at a time. (Standard library limitation: drag or Ctrl+Click is not supported)",
            font=FONTS['sm'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_secondary']
        ).pack(anchor='w', pady=(0, SPACING['xs']))
        
        # Multi-directory selector for sources
        self.source_selector = MultiDirectorySelector(
            self.config_panel.content_frame,
            label="Source Directories",
            initial_paths=[],
            on_change=self.on_source_change
        )
        self.source_selector.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        # Target directory selector
        self.target_selector = DirectorySelector(
            self.config_panel.content_frame,
            label="Target Directory", 
            initial_path=DEFAULT_TARGET,
            on_change=self.on_target_change
        )
        self.target_selector.pack(fill=tk.X, pady=(0, SPACING['xs']))
        
        # Target suggestions area
        self.target_suggestions_frame = tk.Frame(self.config_panel.content_frame, bg=COLORS['background_primary'])
        self.target_suggestions_frame.pack(fill=tk.X, pady=(0, SPACING['md']))
        self.target_suggestions_label = tk.Label(
            self.target_suggestions_frame,
            text="",
            font=FONTS['sm'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_secondary']
        )
        self.target_suggestions_label.pack(anchor='w')
        self.target_suggestion_buttons = []
        
        # Processing options
        options_frame = tk.Frame(self.config_panel.content_frame, bg=COLORS['background_primary'])
        options_frame.pack(fill=tk.X, pady=(0, SPACING['md']))
        
        tk.Label(
            options_frame,
            text="Processing Options",
            font=FONTS['lg'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_primary']
        ).pack(anchor='w', pady=(0, SPACING['sm']))
        
        # Dry run toggle
        self.dry_run_var = tk.BooleanVar(value=DRY_RUN)
        dry_run_frame = tk.Frame(options_frame, bg=COLORS['background_primary'])
        dry_run_frame.pack(fill=tk.X, pady=(0, SPACING['sm']))
        
        tk.Checkbutton(
            dry_run_frame,
            text="Preview Only (Dry Run)",
            variable=self.dry_run_var,
            font=FONTS['base'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_primary'],
            selectcolor=COLORS['background_secondary']
        ).pack(anchor='w')
        
        # Mode selector
        mode_frame = tk.Frame(options_frame, bg=COLORS['background_primary'])
        mode_frame.pack(fill=tk.X)
        
        tk.Label(
            mode_frame,
            text="Processing Mode:",
            font=FONTS['base'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_primary']
        ).pack(side=tk.LEFT, padx=(0, SPACING['sm']))
        
        self.mode_var = tk.StringVar(value="standard")
        mode_menu = tk.OptionMenu(
            mode_frame,
            self.mode_var,
            "standard",
            "aggressive",
            "conservative"
        )
        mode_menu.configure(
            font=FONTS['base'],
            bg=COLORS['background_primary'],
            fg=COLORS['text_primary']
        )
        mode_menu.pack(side=tk.LEFT)
    
    def setup_progress_section(self, parent):
        """Setup progress and preview section"""
        self.progress_section = ProgressSection(parent)
        self.progress_section.pack(fill=tk.BOTH, expand=True, pady=(0, SPACING['lg']))
    
    def setup_action_panel(self, parent):
        """Setup action controls"""
        self.action_panel = ActionPanel(parent)
        self.action_panel.pack(fill=tk.X)
        
        # Set up action handlers
        self.action_panel.set_primary_action(self.start_organization)
        self.action_panel.set_secondary_actions(
            preview_cmd=self.preview_changes,
            view_log_cmd=self.view_log,
            clear_cmd=self.clear_all
        )
    
    def setup_event_handlers(self):
        """Setup event handlers and callbacks"""
        pass  # Handlers are set up in individual methods
    
    def on_source_change(self, paths):
        """Handle source directories change (multi)"""
        import logging
        logging.info(f"User selected source directories: {paths}")
        self.update_status("Source directories updated")
        self.progress_section.add_log_entry(f"Source directories: {paths}", 'info')
        # Suggest target directories
        suggestions = self.suggest_targets(paths)
        self.show_target_suggestions(suggestions)
        # If no suggestions, set target to root of first source
        if not suggestions and paths:
            import os
            src = paths[0]
            drive = os.path.splitdrive(src)[0] or src.split('/')[0] + '/'
            if not drive.endswith(('/', '\\')):
                drive += '/'
            self.target_selector.path_var.set(drive)
            self.progress_section.add_log_entry(f"Target directory set to {drive} (default root)", 'info')

    def on_target_change(self, path: str):
        """Handle target directory change"""
        logging.info(f"User selected target directory: {path}")
        self.update_status("Target directory updated")
        self.progress_section.add_log_entry(f"Target directory: {path}", 'info')
    
    def update_status(self, status: str):
        """Update status display"""
        self.status_label.configure(text=status)
    
    def show_help(self):
        """Show help dialog"""
        help_text = """
Video Labels Organizer - Help

This application uses AI to automatically organize your video files by:
1. Analyzing file names and metadata
2. Identifying TV shows and episodes
3. Creating organized folder structures
4. Moving files to appropriate locations

Configuration:
- Source Directory: Where your video files are located
- Target Directory: Where organized files will be moved
- Preview Only: Test the organization without moving files
- Processing Mode: Choose how aggressive the AI should be

Usage:
1. Set your source and target directories
2. Click "Preview Changes" to see what will happen
3. Review the proposed changes
4. Click "Start Organisation" to proceed
        """
        messagebox.showinfo("Help", help_text)
    
    def preview_changes(self):
        """Preview proposed changes without executing"""
        if self.is_processing:
            logging.info("Preview requested but processing is already in progress.")
            return
        
        sources = self.source_selector.get_paths()
        target = self.target_selector.get_path()
        logging.info(f"User clicked Preview Changes. Sources: {sources}, Target: {target}")
        
        if not self.validate_paths(sources, target):
            logging.warning("Preview aborted: invalid source or target directory.")
            return
        
        self.is_processing = True
        self.action_panel.set_primary_state('disabled')
        self.update_status("Analyzing files...")
        self.progress_section.add_log_entry("Starting file analysis...", 'info')
        
        # Run in background thread
        thread = threading.Thread(target=self._preview_worker, args=(sources, target))
        thread.daemon = True
        thread.start()
    
    def _preview_worker(self, sources, target):
        """Background worker for preview operation"""
        try:
            all_changes = []
            for src in sources:
                def progress_callback(percent):
                    self.after(0, lambda: self.progress_section.update_progress(percent, f"Analyzing {src}... {percent}%"))
                changes = get_proposed_changes(src, target, progress_callback)
                all_changes.extend(changes)
            self.proposed_changes = all_changes
            self.after(0, self._preview_complete)
            
        except Exception as e:
            self.after(0, lambda: self._handle_error(str(e)))
    
    def _preview_complete(self):
        """Handle preview completion"""
        self.is_processing = False
        self.action_panel.set_primary_state('normal')
        ambiguous = [c for c in self.proposed_changes if c.get('needs_user_input')]
        if ambiguous:
            self.resolve_ambiguities(ambiguous)
        # Remove ambiguous/skipped files
        self.proposed_changes = [c for c in self.proposed_changes if not c.get('needs_user_input')]
        if self.proposed_changes:
            self.update_status(f"Found {len(self.proposed_changes)} files to organize")
            self.progress_section.update_stats(len(self.proposed_changes), 0)
            self.progress_section.add_log_entry(f"Analysis complete: {len(self.proposed_changes)} files found", 'success')
            self.action_panel.set_primary_text("Start Organisation")
        else:
            self.update_status("No files to organize")
            self.progress_section.add_log_entry("No files found to organize", 'warning')
        # Always show a scrollable preview inline
        self.show_inline_preview()

    def show_inline_preview(self):
        # Remove old preview if exists
        if hasattr(self, 'inline_preview_frame'):
            self.inline_preview_frame.destroy()
        self.inline_preview_frame = tk.Frame(self.progress_section, bg=COLORS['background_primary'])
        self.inline_preview_frame.pack(fill=tk.BOTH, expand=True, pady=(SPACING['md'], 0))
        tk.Label(
            self.inline_preview_frame,
            text=f"Proposed Changes ({len(self.proposed_changes)})",
            font=FONTS['lg'],
            bg=COLORS['background_primary'],
            fg=COLORS['primary_blue']
        ).pack(anchor='w')
        text_frame = tk.Frame(self.inline_preview_frame, bg=COLORS['background_primary'])
        text_frame.pack(fill=tk.BOTH, expand=True)
        text = tk.Text(
            text_frame,
            font=FONTS['sm'],
            wrap=tk.WORD,
            bg=COLORS['background_secondary'],
            fg=COLORS['text_primary'],
            relief='solid',
            borderwidth=1,
            height=12
        )
        scrollbar = tk.Scrollbar(text_frame, orient='vertical', command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        for i, change in enumerate(self.proposed_changes, 1):
            text.insert(tk.END, f"{i}. {change.get('show_name', '')}\n", 'title')
            text.insert(tk.END, f"   {change.get('episode_info', '')}\n", 'info')
            text.insert(tk.END, f"   From: {change['original']}\n", 'path')
            text.insert(tk.END, f"   To: {change['new_path']}\n", 'path')
            text.insert(tk.END, "-" * 80 + "\n\n", 'separator')
        text.tag_config('title', font=FONTS['bold'], foreground=COLORS['primary_blue'])
        text.tag_config('info', font=FONTS['sm'], foreground=COLORS['text_primary'])
        text.tag_config('path', font=FONTS['sm'], foreground=COLORS['text_secondary'])
        text.tag_config('separator', font=FONTS['sm'], foreground=COLORS['border'])
    
    def resolve_ambiguities(self, ambiguous_changes):
        import logging
        from tkinter import simpledialog
        for change in ambiguous_changes:
            file = change['original']
            # Ask user for type
            answer = simpledialog.askstring(
                "Ambiguous File Type",
                f"File: {file}\nCannot determine if this is a TV show or Movie.\nEnter 'tv' or 'movie':",
                parent=self
            )
            if answer and answer.lower() in ('tv', 'movie'):
                change['type'] = answer.lower()
                change['needs_user_input'] = False
                logging.info(f"User override: {file} set to {answer.lower()}")
                self.progress_section.add_log_entry(f"User override: {file} set to {answer.lower()}", 'info')
            else:
                logging.warning(f"User skipped override for ambiguous file: {file}")
                self.progress_section.add_log_entry(f"User skipped override for ambiguous file: {file}", 'warning')
                change['needs_user_input'] = True
    
    def start_organization(self):
        """Start the organization process"""
        if self.is_processing:
            logging.info("Start Organisation requested but processing is already in progress.")
            return
        
        if not self.proposed_changes:
            logging.warning("Start Organisation aborted: no proposed changes to process.")
            messagebox.showwarning("No Changes", "Please preview changes first.")
            return
        
        logging.info(f"User clicked Start Organisation for {len(self.proposed_changes)} changes.")
        # Show confirmation dialog
        dialog = ModernConfirmationDialog(self, self.proposed_changes)
        
        if dialog.confirmed:
            logging.info("User confirmed proposed changes. Proceeding with organization.")
            self.execute_organization()
        else:
            logging.warning("User cancelled organization in confirmation dialog.")
            self.progress_section.add_log_entry("Operation cancelled by user", 'info')
    
    def execute_organization(self):
        """Execute the organization process"""
        if self.is_processing:
            logging.info("Execute Organisation requested but processing is already in progress.")
            return
        
        sources = self.source_selector.get_paths()
        target = self.target_selector.get_path()
        dry_run = self.dry_run_var.get()
        logging.info(f"Executing organization. Sources: {sources}, Target: {target}, Dry run: {dry_run}")
        
        self.is_processing = True
        self.action_panel.set_primary_state('disabled')
        self.update_status("Organizing files...")
        self.progress_section.add_log_entry("Starting file organization...", 'info')
        
        # Run in background thread
        thread = threading.Thread(target=self._organize_worker, args=(sources, target, dry_run))
        thread.daemon = True
        thread.start()
    
    def _organize_worker(self, sources, target, dry_run):
        """Background worker for organization process"""
        try:
            for src in sources:
                def progress_callback(percent):
                    self.after(0, lambda: self.progress_section.update_progress(percent, f"Organizing {src}... {percent}%"))
                organize_files(src, target, dry_run=dry_run, progress_callback=progress_callback)
            self.after(0, lambda: self._organization_complete(dry_run))
            
        except Exception as e:
            self.after(0, lambda: self._handle_error(str(e)))
    
    def _organization_complete(self, dry_run: bool):
        """Handle organization completion"""
        self.is_processing = False
        self.action_panel.set_primary_state('normal')
        
        if dry_run:
            self.update_status("Preview completed")
            self.progress_section.add_log_entry("Preview completed successfully", 'success')
        else:
            self.update_status("Organization completed")
            self.progress_section.add_log_entry("File organization completed successfully", 'success')
            self.progress_section.update_stats(len(self.proposed_changes), len(self.proposed_changes))
    
    def _handle_error(self, error_message: str):
        """Handle errors"""
        logging.error(f"Exception occurred: {error_message}\n{traceback.format_exc()}")
        self.is_processing = False
        self.action_panel.set_primary_state('normal')
        self.update_status("Error occurred")
        self.progress_section.add_log_entry(f"Error: {error_message}", 'error')
        messagebox.showerror("Error", error_message)
    
    def validate_paths(self, sources, target: str) -> bool:
        """Validate source and target paths"""
        import logging
        if not sources or not target:
            logging.warning("Validation failed: source or target directory not set.")
            messagebox.showerror("Error", "Please select at least one source and a target directory.")
            return False
        import os
        invalid = [s for s in sources if not (os.path.exists(s) and os.path.isdir(s))]
        if invalid:
            logging.warning(f"Validation failed: invalid source directories: {invalid}")
            messagebox.showerror("Error", f"Invalid source directories: {', '.join(invalid)}")
            return False
        if not os.path.exists(target):
            logging.warning(f"Validation failed: target directory does not exist: {target}")
            messagebox.showerror("Error", "Target directory does not exist.")
            return False
        return True
    
    def view_log(self):
        """View the application log"""
        try:
            import subprocess
            import sys
            
            if sys.platform == "win32":
                subprocess.Popen(["notepad", "app.log"])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-a", "TextEdit", "app.log"])
            else:
                subprocess.Popen(["xdg-open", "app.log"])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open log file: {e}")
    
    def clear_all(self):
        """Clear all progress and reset state"""
        self.proposed_changes = []
        self.progress_section.update_progress(0, "Ready")
        self.progress_section.update_stats(0, 0)
        self.progress_section.log_text.delete(1.0, tk.END)
        self.update_status("Ready")
        self.action_panel.set_primary_text("Start Organisation")
        self.progress_section.add_log_entry("Cleared all data", 'info')

    def suggest_targets(self, sources):
        """Suggest likely target directories based on sources."""
        import os
        suggestions = set()
        for src in sources:
            # If root of drive, suggest TV Shows and Movies subfolders
            if os.path.dirname(src) == src or src.endswith(":/") or src.endswith(":\\"):
                suggestions.add(os.path.join(src, "TV Shows"))
                suggestions.add(os.path.join(src, "Movies"))
            else:
                # Suggest sibling TV Shows/Movies folders if they exist
                parent = os.path.dirname(src)
                for folder in ["TV Shows", "Movies"]:
                    candidate = os.path.join(parent, folder)
                    if os.path.exists(candidate):
                        suggestions.add(candidate)
        logging.info(f"Target directory suggestions for sources {sources}: {list(suggestions)}")
        return list(suggestions)

    def show_target_suggestions(self, suggestions):
        # Remove old buttons
        for btn in getattr(self, 'target_suggestion_buttons', []):
            btn.destroy()
        self.target_suggestion_buttons = []
        if suggestions:
            self.target_suggestions_label.config(text="Suggested targets:")
            for suggestion in suggestions:
                btn = ModernButton(
                    self.target_suggestions_frame,
                    text=suggestion,
                    variant='secondary',
                    size='sm',
                    command=lambda s=suggestion: self.select_target_suggestion(s)
                )
                btn.pack(side=tk.LEFT, padx=(0, SPACING['sm']))
                self.target_suggestion_buttons.append(btn)
        else:
            self.target_suggestions_label.config(text="")

    def select_target_suggestion(self, suggestion):
        import logging
        logging.info(f"User selected target suggestion: {suggestion}")
        self.target_selector.path_var.set(suggestion)
        self.update_status(f"Target directory set to {suggestion}")
        self.progress_section.add_log_entry(f"Target directory set to {suggestion}", 'info')

def main():
    """Main entry point"""
    app = ModernApp()
    app.mainloop()

if __name__ == "__main__":
    main() 