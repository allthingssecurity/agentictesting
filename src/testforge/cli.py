"""TestForge CLI — run, plan, evolve, tools."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from testforge.config import load_manifest

app = typer.Typer(name="testforge", help="TestForge v0.5 — Polyglot Agentic Testing Framework")
console = Console()

tools_app = typer.Typer(help="Manage tool adapters")
app.add_typer(tools_app, name="tools")


@app.command()
def run(
    manifest: Path = typer.Option("testforge.yaml", "--manifest", "-m"),
    project_root: Path = typer.Option(".", "--root", "-r"),
):
    """Run the full agentic testing pipeline."""
    config = load_manifest(manifest)

    console.print(Panel(
        f"[bold]TestForge[/bold] v0.5\n"
        f"Project: {config.project_name}\n"
        f"Model: {config.llm.get('model', 'gpt-5') if isinstance(config.llm, dict) else 'gpt-5'}",
        title="TestForge", border_style="blue",
    ))

    from testforge.graph import build_graph

    graph = build_graph()
    initial_state = {
        "messages": [],
        "project_root": str(project_root.resolve()),
        "manifest": config.model_dump(),
        "detected_languages": [],
        "tool_registry_snapshot": {},
        "plan": None,
        "_executor_language": "",
        "_executor_tools": [],
        "results": [],
        "healed_results": [],
        "findings": [],
        "memory": {"summary": "", "key_findings": [], "decisions": [], "errors": [], "token_count": 0},
        "meta_scores": {},
        "report": None,
    }

    console.print("[dim]Running pipeline: detect → plan → execute → heal → triage → report[/dim]\n")
    final_state = graph.invoke(initial_state)

    report = final_state.get("report")
    if report:
        console.print(Panel(report.summary, title="Summary", border_style="green"))

        table = Table(title="Results")
        table.add_column("Lang", style="blue")
        table.add_column("Tool", style="cyan")
        table.add_column("Type")
        table.add_column("Name")
        table.add_column("Status")

        for r in report.results:
            style = {"passed": "green", "failed": "red", "error": "red", "skipped": "dim", "healed": "blue"}.get(r.status, "white")
            table.add_row(r.language or "-", r.tool_adapter or "-", r.test_type, r.name, f"[{style}]{r.status}[/{style}]")
        console.print(table)

        if report.findings:
            ftable = Table(title="Findings")
            ftable.add_column("Severity")
            ftable.add_column("Category")
            ftable.add_column("Test")
            ftable.add_column("Recommendation")
            for f in report.findings:
                ftable.add_row(f.severity, f.category, f.test_result.name, f.recommendation[:80])
            console.print(ftable)

        console.print(f"\n[green]Reports: {project_root / 'artifacts'}[/green]")
    else:
        console.print("[red]No report generated[/red]")


@app.command()
def plan(
    manifest: Path = typer.Option("testforge.yaml", "--manifest", "-m"),
    project_root: Path = typer.Option(".", "--root", "-r"),
):
    """Dry-run: detect languages, discover tools, create test plan."""
    config = load_manifest(manifest)

    from testforge.detection.detector import LanguageDetector
    from testforge.tools.registry import ToolRegistry
    from testforge.models.enums import Language

    detector = LanguageDetector()
    languages = detector.detect(project_root.resolve())
    console.print(f"[bold]Languages:[/bold] {', '.join(l.value for l in languages) or 'none detected'}")

    registry = ToolRegistry()
    registry.auto_discover()
    applicable = registry.detect_applicable(project_root.resolve(), languages)
    console.print(f"[bold]Tools:[/bold] {', '.join(a.name for a in applicable) or 'none available'}")

    for a in applicable:
        console.print(f"  {a.name} ({a.category}) → {', '.join(l.value for l in a.languages) or 'any'}")


@app.command()
def evolve(
    manifest: Path = typer.Option("testforge.yaml", "--manifest", "-m"),
    project_root: Path = typer.Option(".", "--root", "-r"),
    iterations: int = typer.Option(3, "--iterations", "-n"),
):
    """Run Meta-Harness evolution loop (arXiv:2603.28052)."""
    config = load_manifest(manifest)

    console.print(Panel(
        f"[bold]Meta-Harness Evolution[/bold]\n"
        f"Iterations: {iterations}\n"
        f"Project: {config.project_name}",
        title="Evolve", border_style="yellow",
    ))

    from testforge.meta.evolver import HarnessEvolver

    def on_iteration(i, result):
        scores = result.get("scores", {})
        console.print(f"  Iteration {i}: composite={scores.get('composite_score', 0):.3f} "
                      f"pass_rate={scores.get('pass_rate', 0):.1%}")

    evolver = HarnessEvolver(project_root.resolve())
    result = evolver.evolve(config.model_dump(), iterations=iterations, on_iteration=on_iteration)

    best = result["best"]
    console.print(f"\n[green]Best candidate: {best['candidate_id']} "
                  f"(score: {best['scores']['composite_score']:.3f})[/green]")
    console.print(f"Evolution history: {project_root / '.testforge/evolution/'}")


@tools_app.command("list")
def tools_list(
    project_root: Path = typer.Option(".", "--root", "-r"),
):
    """List all available tool adapters and their detection status."""
    from testforge.tools.registry import ToolRegistry

    registry = ToolRegistry()
    registry.auto_discover()

    table = Table(title="Tool Adapters")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Languages")
    table.add_column("Binary")
    table.add_column("Detected")

    root = project_root.resolve()
    for adapter in registry.list_all():
        detected = adapter.detect(root)
        style = "green" if detected else "dim"
        table.add_row(
            adapter.name, adapter.category.value,
            ", ".join(l.value for l in adapter.languages) or "any",
            adapter.binary,
            f"[{style}]{'yes' if detected else 'no'}[/{style}]",
        )
    console.print(table)


if __name__ == "__main__":
    app()
