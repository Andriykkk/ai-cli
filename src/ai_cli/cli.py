"""Main CLI entry point for AI CLI."""

import sys
import typer
from typing import Optional

from .ui import NanoStyleUI
from .config import ConfigManager


app = typer.Typer(
    name="ai-cli",
    help="AI-powered CLI tool for code development",
    add_completion=False
)


def main():
    """Main entry point for the CLI application."""
    try:
        # Create nano-style UI
        ui = NanoStyleUI()
        
        # Show projects and get selection
        project = ui.run()
        
        if project is None:
            return
        
        # TODO: Start chat interface with selected project
        print(f"\nSelected project: {project.name}")
        print(f"Path: {project.path}")
        print("Chat interface coming soon!")
        
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


@app.command()
def run():
    """Start the AI CLI interface."""
    main()


@app.command()
def add_project(
    name: str = typer.Argument(..., help="Project name"),
    path: str = typer.Argument(..., help="Project path"),
    description: str = typer.Option("", "--description", "-d", help="Project description")
):
    """Add a new project via command line."""
    try:
        config_manager = ConfigManager()
        project = config_manager.add_project(name, path, description)
        typer.echo(f"✓ Project '{project.name}' added successfully!")
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)


@app.command()
def list_projects():
    """List all projects."""
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    if not config.projects:
        typer.echo("No projects found.")
        return
    
    typer.echo("Projects:")
    for i, project in enumerate(config.projects, 1):
        typer.echo(f"{i}. {project.name} - {project.path}")
        if project.description:
            typer.echo(f"   {project.description}")


@app.command()
def remove_project(name: str = typer.Argument(..., help="Project name to remove")):
    """Remove a project."""
    config_manager = ConfigManager()
    
    if config_manager.remove_project(name):
        typer.echo(f"✓ Project '{name}' removed successfully!")
    else:
        typer.echo(f"Project '{name}' not found.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    # When run directly (python -m ai_cli.cli), start the main interface
    main()