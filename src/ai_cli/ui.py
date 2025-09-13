"""Nano-style full-screen UI for AI CLI."""

import os
import sys
import termios
import tty
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import ConfigManager, ProjectConfig


class NanoStyleUI:
    """Nano-style full-screen interface for project selection."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.projects = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.terminal_height = 24
        self.terminal_width = 80
        self._update_terminal_size()
        
    def _update_terminal_size(self):
        """Get current terminal dimensions."""
        try:
            size = os.get_terminal_size()
            self.terminal_height = size.lines
            self.terminal_width = size.columns
        except:
            # Fallback if terminal size detection fails
            self.terminal_height = 24
            self.terminal_width = 80
    
    def run(self) -> Optional[ProjectConfig]:
        """Main entry point - run the project selector."""
        try:
            self._load_projects()
            return self._main_loop()
        except KeyboardInterrupt:
            self._clear_screen()
            return None
        except Exception as e:
            self._clear_screen()
            print(f"Error: {e}")
            return None
    
    def _load_projects(self):
        """Load projects from config."""
        config = self.config_manager.load_config()
        self.projects = config.projects
        if self.projects and self.selected_index >= len(self.projects):
            self.selected_index = len(self.projects) - 1
    
    def _main_loop(self) -> Optional[ProjectConfig]:
        """Main interaction loop."""
        self._setup_terminal()
        
        try:
            while True:
                self._draw_screen()
                
                key = self._get_key()
                
                if key == '\x03':  # Ctrl+C
                    self._restore_terminal()
                    raise KeyboardInterrupt()
                elif key == 'q' or key == '\x1b':  # q or ESC
                    return None
                elif key == '\r' or key == '\n':  # Enter
                    if self.projects and 0 <= self.selected_index < len(self.projects):
                        selected = self.projects[self.selected_index]
                        self.config_manager.update_project_last_used(selected.name)
                        return selected
                elif key == '\x1b[A':  # Up arrow
                    self._move_selection(-1)
                elif key == '\x1b[B':  # Down arrow
                    self._move_selection(1)
                elif key == 'n':  # New project
                    self._create_new_project()
                elif key == 'e':  # Edit project
                    self._edit_current_project()
                elif key == 'd':  # Delete project
                    self._delete_current_project()
                elif key == 'r':  # Refresh
                    self._load_projects()
                elif key == 'h' or key == '?':  # Help
                    self._show_help()
                    
        finally:
            self._restore_terminal()
    
    def _setup_terminal(self):
        """Setup terminal for raw input."""
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
        self._clear_screen()
        self._hide_cursor()
    
    def _setup_terminal_raw(self):
        """Setup terminal for raw input (used after restoring)."""
        tty.setraw(sys.stdin.fileno())
        self._hide_cursor()
    
    def _restore_terminal_for_input(self):
        """Temporarily restore terminal for normal input."""
        self._show_cursor()
        self._clear_screen()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
    
    def _restore_terminal(self):
        """Restore terminal to original state."""
        self._show_cursor()
        self._clear_screen()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
        print()  # Final newline
    
    def _get_key(self) -> str:
        """Get a single key press."""
        key = sys.stdin.read(1)
        
        # Handle escape sequences (arrow keys)
        if key == '\x1b':
            key += sys.stdin.read(2)
        
        return key
    
    def _move_selection(self, direction: int):
        """Move selection up or down."""
        if not self.projects:
            return
            
        self.selected_index += direction
        
        # Wrap around
        if self.selected_index < 0:
            self.selected_index = len(self.projects) - 1
        elif self.selected_index >= len(self.projects):
            self.selected_index = 0
        
        # Handle scrolling
        visible_lines = self.terminal_height - 6  # Account for header/footer
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + visible_lines:
            self.scroll_offset = self.selected_index - visible_lines + 1
    
    def _draw_screen(self):
        """Draw the entire screen."""
        # Update terminal size in case it changed
        self._update_terminal_size()
        
        self._clear_screen()
        self._draw_header()
        self._draw_projects()
        self._draw_footer()
        self._position_cursor()
    
    def _draw_header(self):
        """Draw the header section."""
        title = "AI CLI - Project Manager"
        subtitle = f"{len(self.projects)} projects available"
        
        # Center the title
        title_line = title.center(self.terminal_width)
        subtitle_line = subtitle.center(self.terminal_width)
        
        print(f"\x1b[7m{title_line}\x1b[0m")  # Inverted colors
        print(f"\x1b[2m{subtitle_line}\x1b[0m")  # Dim
        print("─" * self.terminal_width)
    
    def _draw_projects(self):
        """Draw the projects list."""
        if not self.projects:
            self._draw_empty_state()
            return
        
        visible_lines = self.terminal_height - 7  # -1 more for column header
        start_idx = self.scroll_offset
        end_idx = min(start_idx + visible_lines, len(self.projects))
        
        # Calculate column widths based on terminal size
        available_width = self.terminal_width - 4  # Reserve 4 chars for status and spacing
        
        # Minimum widths
        min_name_width = 15
        min_path_width = 20
        date_width = 12  # Fixed width for date
        
        # Calculate dynamic widths
        remaining_width = available_width - date_width - 4  # -4 for spacing
        name_width = max(min_name_width, min(30, remaining_width // 2))
        path_width = max(min_path_width, remaining_width - name_width)
        
        # Draw column headers
        header = f" S {'Name':<{name_width}} {'Path':<{path_width}} {'Last Used':<{date_width}}"
        header = header[:self.terminal_width]
        print(f"\x1b[2m{header}\x1b[0m")  # Dim header
        
        for i in range(start_idx, end_idx):
            project = self.projects[i]
            is_selected = (i == self.selected_index)
            
            # Check if path exists
            status = "✓" if Path(project.path).exists() else "✗"
            
            # Format last used
            last_used = "Never"
            if project.last_used:
                try:
                    dt = datetime.fromisoformat(project.last_used)
                    last_used = dt.strftime("%m/%d %H:%M")
                except:
                    last_used = "Unknown"
            
            # Truncate and format fields
            name = self._truncate_text(project.name, name_width)
            path = self._truncate_text(project.path, path_width)
            
            # Create the line with proper spacing
            line = f" {status} {name:<{name_width}} {path:<{path_width}} {last_used:<{date_width}}"
            
            # Ensure line doesn't exceed terminal width
            line = line[:self.terminal_width]
            
            if is_selected:
                # Pad to full width for proper highlighting
                padded_line = line.ljust(self.terminal_width)
                print(f"\x1b[7m{padded_line}\x1b[0m")  # Inverted
            else:
                print(line)
        
        # Fill remaining lines
        current_lines = end_idx - start_idx + 4  # +4 for header + column header
        while current_lines < self.terminal_height - 3:  # -3 for footer
            print()
            current_lines += 1
    
    def _draw_empty_state(self):
        """Draw empty state when no projects exist."""
        empty_msg = "No projects found. Press 'n' to create a new project."
        lines_used = 3  # Header lines
        
        # Center the message vertically
        padding_lines = (self.terminal_height - 6 - 1) // 2  # -6 for header/footer, -1 for message
        
        for _ in range(padding_lines):
            print()
            lines_used += 1
        
        centered_msg = empty_msg.center(self.terminal_width)
        print(f"\x1b[2m{centered_msg}\x1b[0m")  # Dim
        lines_used += 1
        
        # Fill remaining lines
        while lines_used < self.terminal_height - 3:
            print()
            lines_used += 1
    
    def _draw_footer(self):
        """Draw the footer with shortcuts."""
        shortcuts = [
            "↑↓ Navigate", "Enter Select", "n New", "e Edit", "d Delete", 
            "r Refresh", "h Help", "q Quit"
        ]
        
        footer_line = " | ".join(shortcuts)
        
        print("─" * self.terminal_width)
        
        # Split into multiple lines if too long
        if len(footer_line) <= self.terminal_width:
            print(f"\x1b[2m{footer_line.center(self.terminal_width)}\x1b[0m")
            print()
        else:
            # Split shortcuts into two lines
            mid = len(shortcuts) // 2
            line1 = " | ".join(shortcuts[:mid]).center(self.terminal_width)
            line2 = " | ".join(shortcuts[mid:]).center(self.terminal_width)
            print(f"\x1b[2m{line1}\x1b[0m")
            print(f"\x1b[2m{line2}\x1b[0m")
    
    def _create_new_project(self):
        """Create a new project interactively."""
        # Temporarily restore terminal for input
        self._restore_terminal_for_input()
        
        print("Create New Project")
        print("═" * 20)
        print()
        
        try:
            # Get project details
            name = input("Project name: ").strip()
            if not name:
                self._show_message("Project name cannot be empty!")
                return
            
            default_path = str(Path.cwd())
            path = input(f"Project path [{default_path}]: ").strip()
            if not path:
                path = default_path
            
            description = input("Description (optional): ").strip()
            
            # Create the project
            project = self.config_manager.add_project(name, path, description)
            self._load_projects()  # Reload projects
            
            # Set selection to new project
            for i, p in enumerate(self.projects):
                if p.name == project.name:
                    self.selected_index = i
                    break
            
            self._show_message(f"Project '{name}' created successfully!", 1)
            
        except ValueError as e:
            self._show_message(f"Error: {e}")
        except KeyboardInterrupt:
            self._show_message("Cancelled")
        finally:
            # Restore raw mode
            self._setup_terminal_raw()
    
    def _edit_current_project(self):
        """Edit the currently selected project."""
        if not self.projects or self.selected_index >= len(self.projects):
            return
        
        project = self.projects[self.selected_index]
        
        # Temporarily restore terminal for input
        self._restore_terminal_for_input()
        
        print(f"Edit Project: {project.name}")
        print("═" * 30)
        print("(Press Enter to keep current value)")
        print()
        
        try:
            # Edit name
            new_name = input(f"Project name [{project.name}]: ").strip()
            if not new_name:
                new_name = project.name
            
            # Edit path  
            new_path = input(f"Project path [{project.path}]: ").strip()
            if not new_path:
                new_path = project.path
            
            # Edit description
            current_desc = project.description or "None"
            new_description = input(f"Description [{current_desc}]: ").strip()
            if not new_description or new_description.lower() == "none":
                new_description = project.description
            
            # Check if anything changed
            if (new_name == project.name and 
                new_path == project.path and 
                new_description == project.description):
                self._show_message("No changes made")
                return
            
            # Validate that new name/path don't conflict with other projects
            config = self.config_manager.load_config()
            for i, p in enumerate(config.projects):
                if i != self.selected_index:  # Skip current project
                    if p.name == new_name and new_name != project.name:
                        self._show_message(f"Project name '{new_name}' already exists!")
                        return
                    if p.path == new_path and new_path != project.path:
                        self._show_message(f"Project path '{new_path}' already exists!")
                        return
            
            # Update the project
            old_name = project.name
            project.name = new_name
            project.path = new_path
            project.description = new_description
            
            # Save changes
            self.config_manager.save_config(config)
            self._load_projects()  # Reload projects
            
            self._show_message(f"Project '{old_name}' updated successfully!", 1)
            
        except KeyboardInterrupt:
            self._show_message("Cancelled")
        finally:
            # Restore raw mode
            self._setup_terminal_raw()
    
    def _delete_current_project(self):
        """Delete the currently selected project."""
        if not self.projects or self.selected_index >= len(self.projects):
            return
        
        project = self.projects[self.selected_index]
        
        # Temporarily restore terminal for input
        self._restore_terminal_for_input()
        
        print(f"Delete Project: {project.name}")
        print("═" * 30)
        print(f"Path: {project.path}")
        if project.description:
            print(f"Description: {project.description}")
        print()
        
        try:
            confirm = input("Are you sure? [y/N]: ").strip().lower()
            if confirm == 'y':
                if self.config_manager.remove_project(project.name):
                    self._load_projects()
                    if self.selected_index >= len(self.projects):
                        self.selected_index = max(0, len(self.projects) - 1)
                    self._show_message(f"Project '{project.name}' deleted", 1)
                else:
                    self._show_message("Failed to delete project")
            else:
                self._show_message("Cancelled")
        except KeyboardInterrupt:
            self._show_message("Cancelled")
        finally:
            # Restore raw mode
            self._setup_terminal_raw()
    
    def _show_help(self):
        """Show help screen."""
        self._clear_screen()
        
        help_text = """
AI CLI - Help

Navigation:
  ↑ / ↓     Navigate through projects
  Enter     Select project
  
Actions:
  n         Create new project
  e         Edit selected project
  d         Delete selected project
  r         Refresh project list
  h / ?     Show this help
  q / Esc   Quit
  
Project Information:
  ✓ Path exists and accessible
  ✗ Path not found or inaccessible
  
The selected project is highlighted.
Use arrow keys to navigate and Enter to select.

Press any key to continue...
"""
        
        print(help_text)
        self._get_key()  # Wait for keypress
    
    def _show_message(self, message: str, duration: float = 2.0):
        """Show a temporary message."""
        self._clear_screen()
        
        # Center message vertically and horizontally
        lines = message.split('\n')
        start_line = (self.terminal_height - len(lines)) // 2
        
        for i in range(start_line):
            print()
        
        for line in lines:
            print(line.center(self.terminal_width))
        
        if duration > 0:
            import time
            time.sleep(duration)
    
    def _truncate_text(self, text: str, max_width: int) -> str:
        """Truncate text to fit within max_width, adding ellipsis if needed."""
        if len(text) <= max_width:
            return text
        elif max_width <= 3:
            return "..." if max_width == 3 else text[:max_width]
        else:
            return text[:max_width - 3] + "..."
    
    def _clear_screen(self):
        """Clear the entire screen."""
        print('\x1b[2J\x1b[H', end='', flush=True)
    
    def _hide_cursor(self):
        """Hide the cursor."""
        print('\x1b[?25l', end='', flush=True)
    
    def _show_cursor(self):
        """Show the cursor.""" 
        print('\x1b[?25h', end='', flush=True)
    
    def _position_cursor(self):
        """Position cursor at bottom of screen."""
        print(f'\x1b[{self.terminal_height};1H', end='', flush=True)