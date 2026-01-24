import sys
import json
import click
from .errors import format_error, FinFetchError
from .logging import configure_logging

# Configure logging at module level
configure_logging()

@click.group()
def cli():
    """finfetch: Financial data fetcher."""
    pass

@cli.command()
def version():
    """Print version information."""
    data = {
        "version": "0.1.0",
        "status": "M0 Scaffolding"
    }
    
    output = {
        "ok": True,
        "data": data,
        "meta": {
            "version": 1
        }
    }
    click.echo(json.dumps(output, indent=2))

def main():
    """Entry point for the CLI."""
    try:
        # Check for help flag in a crude way to redirect to stderr if possible,
        # but for now rely on click's default behavior for help.
        # We wrap the actual execution to catch logical/runtime errors.
        cli(standalone_mode=False)
    except Exception as e:
        # If it's a Click exit (like --help), let it pass if safe, 
        # or capture it if it's an error.
        if isinstance(e, click.exceptions.Exit):
             sys.exit(e.exit_code)
        
        if isinstance(e, click.exceptions.Abort):
             # User aborted
             sys.exit(130)

        # For actual errors, print JSON to stdout and exit non-zero
        print(format_error(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
