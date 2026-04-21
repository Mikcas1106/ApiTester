import typer
import yaml
import asyncio
from rich.console import Console
from core.runner import LoadRunner

app = typer.Typer(help="ApiStorm - Modern API Load Testing Tool")
console = Console()

@app.command()
def run(
    config: str = typer.Argument(..., help="Path to scenario YAML config"),
    out_csv: str = typer.Option("results.csv", "--csv", help="Output CSV file"),
    out_html: str = typer.Option("report.html", "--html", help="Output HTML report")
):
    """Run a load testing scenario"""
    console.print(f"[bold green]🌩️ Starting ApiStorm with {config}[/bold green]")
    try:
        with open(config, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[bold red]Failed to read config: {e}[/bold red]")
        raise typer.Exit(1)

    runner = LoadRunner(config_data)
    
    try:
        # Avoid issues with loop in some Windows environments
        import sys
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        reporter = asyncio.run(runner.run())
        stats = reporter.get_final_result()
    except KeyboardInterrupt:
        console.print("[bold yellow]Test interrupted by user.[/bold yellow]")
        raise typer.Exit(1)
        
    console.print("\n[bold cyan]Test Completed. Final Stats:[/bold cyan]")
    console.print(stats)
    
    # Generation of reports
    reporter.save_csv(out_csv)
    console.print(f"✅ CSV results saved to [bold blue]{out_csv}[/bold blue]")
    reporter.generate_html(out_html, stats)
    console.print(f"✅ HTML report saved to [bold blue]{out_html}[/bold blue]")

if __name__ == "__main__":
    app()
