"""PorkChop CLI — Click-based command interface.

Commands:
  porkchop process <file>          Full v0 pipeline (clean → chunk → extract)
  porkchop clean <file>            Clean raw bill text
  porkchop chunk <file>            Chunk cleaned text
  porkchop fetch <bill-id>         Fetch bill from Congress.gov
  porkchop analyze <bill-id>       Claude-powered analysis
  porkchop compare <bill-id>       Compare bill versions
  porkchop score <bill-id>         Pork scoring
  porkchop search <query>          Search analyzed bills
  porkchop info <bill-id>          Show bill details
  porkchop stats                   Database statistics
  porkchop import <file> <bill-id> Import local file
"""

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from rich import print as rprint

from . import __version__
from .database import Database
from .cleaner import clean_text, clean_file
from .chunker import chunk_text
from .extractor import extract_facts, extract_from_chunks

console = Console()


def get_db(db_path=None):
    return Database(Path(db_path) if db_path else None)


@click.group()
@click.version_option(__version__, prog_name="porkchop")
@click.option("--db", "db_path", envvar="PORKCHOP_DB", help="Database path")
@click.pass_context
def cli(ctx, db_path):
    """PorkChop — AI that reads the bills so you don't have to."""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db_path


# --- Phase 0: Foundation ---


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("-o", "--output", help="Output file path")
@click.pass_context
def clean(ctx, file, output):
    """Clean raw GPO bill text (remove formatting artifacts)."""
    with console.status("Cleaning text..."):
        result = clean_file(file, output)

    lines_in = sum(1 for _ in open(file))
    lines_out = result.count("\n") + 1
    reduction = round((1 - lines_out / lines_in) * 100, 1)

    console.print(f"[green]Cleaned:[/green] {lines_in:,} → {lines_out:,} lines ({reduction}% reduction)")
    if output:
        console.print(f"Written to: {output}")
    else:
        console.print("(use -o to write to file)")


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--strategy", type=click.Choice(["size", "structure"]), default="structure")
@click.option("--max-chars", default=20000, help="Max characters per chunk")
def chunk(file, strategy, max_chars):
    """Chunk cleaned bill text into processable pieces."""
    with open(file, "r", encoding="utf-8") as f:
        text = f.read()

    with console.status("Chunking text..."):
        chunks = chunk_text(text, strategy=strategy, max_chars=max_chars)

    table = Table(title=f"Chunks ({strategy} strategy)")
    table.add_column("ID", style="cyan")
    table.add_column("Division")
    table.add_column("Title")
    table.add_column("Characters", justify="right")

    for c in chunks:
        table.add_row(c.chunk_id, c.division or "-", c.title or "-", f"{c.char_count:,}")

    console.print(table)
    console.print(f"[green]{len(chunks)} chunks created[/green]")


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--strategy", type=click.Choice(["size", "structure"]), default="structure")
@click.option("--max-chars", default=20000, help="Max characters per chunk")
@click.option("-o", "--output", help="Output JSON file")
@click.option("--bill-id", help="Bill identifier for database storage (e.g., HR-10515)")
@click.pass_context
def process(ctx, file, strategy, max_chars, output, bill_id):
    """Full pipeline: clean → chunk → extract → store."""
    db = get_db(ctx.obj.get("db_path"))

    # Step 1: Clean
    with console.status("[1/3] Cleaning text..."):
        with open(file, "r", encoding="utf-8") as f:
            raw = f.read()
        cleaned = clean_text(raw)
    console.print(f"[green]Cleaned:[/green] {raw.count(chr(10)):,} → {cleaned.count(chr(10)):,} lines")

    # Step 2: Chunk
    with console.status("[2/3] Chunking..."):
        chunks = chunk_text(cleaned, strategy=strategy, max_chars=max_chars)
    console.print(f"[green]Chunked:[/green] {len(chunks)} chunks ({strategy})")

    # Step 3: Extract
    with console.status("[3/3] Extracting facts..."):
        all_facts = extract_from_chunks(chunks)

    # Aggregate stats
    total_funding = sum(len(f.get("funding", [])) for f in all_facts)
    total_refs = sum(
        len(f.get("references", {}).get("us_code", []))
        + len(f.get("references", {}).get("public_laws", []))
        for f in all_facts
    )
    total_deadlines = sum(len(f.get("deadlines", [])) for f in all_facts)
    total_duties = sum(len(f.get("duties", [])) for f in all_facts)
    total_entities = sum(len(f.get("entities", [])) for f in all_facts)

    # Store in database if bill_id provided
    if bill_id:
        from .ingestion import parse_bill_id, import_from_file

        congress, bill_type, bill_number = parse_bill_id(bill_id)
        db_id = db.upsert_bill(congress, bill_type, bill_number, source="local_file")
        version_id = db.upsert_version(db_id, "local", raw_text=raw, cleaned_text=cleaned)

        for i, (c, facts) in enumerate(zip(chunks, all_facts)):
            section_id = db.add_section(
                db_id,
                c.text,
                version_id=version_id,
                section_number=c.chunk_id,
                title=c.division or c.title,
                level=c.division and "division" or c.title and "title" or "chunk",
                position=i,
            )

            for item in facts.get("funding", []):
                db.add_spending_item(
                    db_id,
                    item["amount"],
                    section_id=section_id,
                    amount_numeric=item.get("amount_numeric", 0),
                    purpose=item.get("purpose"),
                    availability=item.get("availability"),
                    source_text=item.get("source_text"),
                )

            for ref in facts.get("references", {}).get("us_code", []):
                db.add_reference(db_id, "us_code", ref, section_id=section_id)
            for ref in facts.get("references", {}).get("public_laws", []):
                db.add_reference(db_id, "public_law", ref, section_id=section_id)
            for ref in facts.get("references", {}).get("acts", []):
                db.add_reference(db_id, "act", ref, section_id=section_id)

            for dl in facts.get("deadlines", []):
                db.add_deadline(
                    db_id,
                    section_id=section_id,
                    date=dl.get("date"),
                    action=dl.get("action"),
                )

            for entity in facts.get("entities", []):
                db.add_entity(db_id, entity, section_id=section_id)

        console.print(f"[green]Stored in database as bill #{db_id}[/green]")

    # Display results
    table = Table(title="Extraction Results")
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right")
    table.add_row("Funding items", str(total_funding))
    table.add_row("Legal references", str(total_refs))
    table.add_row("Deadlines", str(total_deadlines))
    table.add_row("Duties/requirements", str(total_duties))
    table.add_row("Entities", str(total_entities))
    console.print(table)

    # Output JSON
    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(all_facts, f, indent=2, ensure_ascii=False)
        console.print(f"Written to: {output}")


# --- Phase 1: Ingestion ---


@cli.command()
@click.argument("bill_id")
@click.option("--version", "bill_version", default="latest", help="Version to fetch (e.g., ih, enr, latest)")
@click.option("--text/--no-text", default=False, help="Also fetch full text")
@click.pass_context
def fetch(ctx, bill_id, bill_version, text):
    """Fetch a bill from Congress.gov by ID (e.g., HR-10515, 118-hr-10515)."""
    from .ingestion import fetch_bill, fetch_bill_text

    db = get_db(ctx.obj.get("db_path"))

    with console.status(f"Fetching {bill_id}..."):
        result = fetch_bill(bill_id, db=db)

    console.print(Panel(f"[bold]{result['title']}[/bold]", title=bill_id.upper()))
    console.print(f"Congress: {result['congress']}th | Type: {result['bill_type'].upper()} | Number: {result['bill_number']}")
    if result.get("sponsors"):
        console.print(f"Sponsors: {result['sponsors']}")
    if result.get("status"):
        console.print(f"Status: {result['status']}")

    if result.get("versions"):
        table = Table(title="Available Versions")
        table.add_column("Code")
        table.add_column("Name")
        table.add_column("Formats")
        for v in result["versions"]:
            formats = ", ".join(v.get("formats", {}).keys())
            table.add_row(v["version_code"], v.get("version_name", ""), formats)
        console.print(table)

    if text:
        with console.status("Fetching text..."):
            bill_text = fetch_bill_text(bill_id, version=bill_version, db=db)
        console.print(f"[green]Text fetched:[/green] {len(bill_text):,} characters")

    console.print(f"[dim]Database ID: {result.get('db_id', 'N/A')}[/dim]")


@cli.command("import")
@click.argument("file", type=click.Path(exists=True))
@click.argument("bill_id")
@click.pass_context
def import_file(ctx, file, bill_id):
    """Import bill text from a local file."""
    from .ingestion import import_from_file

    db = get_db(ctx.obj.get("db_path"))

    with console.status("Importing..."):
        result = import_from_file(file, bill_id, db=db)

    console.print(f"[green]Imported:[/green] {result['title']}")
    console.print(f"Text: {len(result['text']):,} characters")
    console.print(f"Database ID: {result.get('db_id', 'N/A')}")


# --- Phase 2: Analysis ---


@cli.command()
@click.argument("bill_id", type=int)
@click.option("--model", default="claude-haiku-4-5-20251001", help="Claude model for section analysis")
@click.pass_context
def analyze(ctx, bill_id, model):
    """Analyze a bill using Claude (requires ANTHROPIC_API_KEY)."""
    from .analyzer import analyze_bill

    db = get_db(ctx.obj.get("db_path"))

    bill = db.get_bill(bill_id)
    if not bill:
        console.print(f"[red]Bill #{bill_id} not found. Run 'porkchop fetch' or 'porkchop process' first.[/red]")
        return

    sections = db.get_sections(bill_id)
    console.print(f"Analyzing [bold]{bill['title']}[/bold] ({len(sections)} sections)...")

    with Progress() as progress:
        task = progress.add_task("Analyzing sections...", total=len(sections) + 1)
        # Monkey-patch to update progress (analyze_bill processes sections internally)
        result = analyze_bill(bill_id, db, model=model)
        progress.update(task, completed=len(sections) + 1)

    # Display summary
    console.print(Panel(result.get("summary", "No summary generated"), title="Bill Summary"))

    # Stats
    spending = db.get_spending(bill_id)
    total = db.get_total_spending(bill_id)
    console.print(f"[green]Analysis complete:[/green]")
    console.print(f"  Spending items: {len(spending)}")
    console.print(f"  Total spending: ${total:,.0f}")
    console.print(f"  Deadlines: {len(db.get_deadlines(bill_id))}")
    console.print(f"  Entities: {len(db.get_entities(bill_id))}")


# --- Phase 4: Comparison ---


@cli.command()
@click.argument("bill_id", type=int)
@click.option("--from", "from_version", required=True, type=int, help="From version ID")
@click.option("--to", "to_version", required=True, type=int, help="To version ID")
@click.option("--ai/--no-ai", default=False, help="Use Claude for semantic comparison")
@click.pass_context
def compare(ctx, bill_id, from_version, to_version, ai):
    """Compare two versions of a bill."""
    from .comparator import compare_versions

    db = get_db(ctx.obj.get("db_path"))

    with console.status("Comparing versions..."):
        result = compare_versions(db, bill_id, from_version, to_version, use_ai=ai)

    console.print(
        Panel(
            f"{result['from_version_name']} → {result['to_version_name']}",
            title="Version Comparison",
        )
    )
    console.print(f"Lines added: [green]+{result['additions_count']}[/green]")
    console.print(f"Lines removed: [red]-{result['removals_count']}[/red]")
    console.print(f"Similarity: {result['similarity_ratio']:.1%}")

    if result.get("spending_added"):
        console.print("\n[bold]Spending Added:[/bold]")
        for s in result["spending_added"][:10]:
            console.print(f"  [green]+[/green] {s['amount']} — {s['context'][:80]}")

    if result.get("spending_removed"):
        console.print("\n[bold]Spending Removed:[/bold]")
        for s in result["spending_removed"][:10]:
            console.print(f"  [red]-[/red] {s['amount']} — {s['context'][:80]}")

    if result.get("ai_analysis"):
        console.print("\n[bold]AI Analysis:[/bold]")
        for a in result["ai_analysis"][:10]:
            console.print(f"  {a.get('section', '?')}: {a.get('summary', '')}")


# --- Phase 5: Pork Scoring ---


@cli.command()
@click.argument("bill_id", type=int)
@click.option("--ai/--no-ai", default=False, help="Use Claude for deep scoring")
@click.option("--threshold", default=30, help="Heuristic score threshold for AI analysis")
@click.pass_context
def score(ctx, bill_id, ai, threshold):
    """Score spending items for pork likelihood."""
    from .scorer import score_bill

    db = get_db(ctx.obj.get("db_path"))

    with console.status("Scoring spending items..."):
        result = score_bill(bill_id, db, use_ai=ai, ai_threshold=threshold)

    console.print(
        Panel(
            f"Avg: {result['avg_score']}/100 | Max: {result['max_score']}/100 | Items: {result['items_scored']}",
            title=f"Pork Score — {result['title']}",
        )
    )

    if result["high_pork"]:
        table = Table(title="High Pork Items (score >= 60)")
        table.add_column("Score", justify="right", style="red")
        table.add_column("Amount")
        table.add_column("Purpose")
        table.add_column("Flags")
        for item in result["high_pork"][:20]:
            table.add_row(
                str(item["score"]),
                item.get("amount", "?"),
                (item.get("purpose") or "?")[:60],
                ", ".join(item.get("flags", [])),
            )
        console.print(table)
    else:
        console.print("[green]No high-pork items detected.[/green]")


# --- Utility Commands ---


@cli.command()
@click.argument("bill_id", type=int)
@click.pass_context
def info(ctx, bill_id):
    """Show detailed information about a stored bill."""
    db = get_db(ctx.obj.get("db_path"))
    bill = db.get_bill(bill_id)
    if not bill:
        console.print(f"[red]Bill #{bill_id} not found[/red]")
        return

    console.print(Panel(f"[bold]{bill['title']}[/bold]", title=f"Bill #{bill_id}"))
    console.print(f"Congress: {bill['congress']}th | Type: {bill['bill_type'].upper()} | Number: {bill['bill_number']}")
    if bill.get("sponsors"):
        console.print(f"Sponsors: {bill['sponsors']}")
    if bill.get("status"):
        console.print(f"Status: {bill['status']}")
    if bill.get("introduced_date"):
        console.print(f"Introduced: {bill['introduced_date']}")

    versions = db.get_versions(bill_id)
    if versions:
        table = Table(title="Versions")
        table.add_column("ID")
        table.add_column("Code")
        table.add_column("Name")
        table.add_column("Has Text")
        for v in versions:
            has_text = "yes" if v.get("raw_text") or v.get("cleaned_text") else "no"
            table.add_row(str(v["id"]), v["version_code"], v.get("version_name", ""), has_text)
        console.print(table)

    sections = db.get_sections(bill_id)
    spending = db.get_spending(bill_id)
    total = db.get_total_spending(bill_id)
    refs = db.get_references(bill_id)
    deadlines = db.get_deadlines(bill_id)
    entities = db.get_entities(bill_id)
    summaries = db.get_summaries(bill_id)
    pork = db.get_bill_pork_summary(bill_id)

    table = Table(title="Analysis Data")
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right")
    table.add_row("Sections", str(len(sections)))
    table.add_row("Spending items", str(len(spending)))
    table.add_row("Total spending", f"${total:,.0f}")
    table.add_row("Legal references", str(len(refs)))
    table.add_row("Deadlines", str(len(deadlines)))
    table.add_row("Entities", str(len(entities)))
    table.add_row("Summaries", str(len(summaries)))
    if pork.get("scored_items"):
        table.add_row("Pork scores", f"{pork['scored_items']} (avg: {pork.get('avg_score', 0):.0f})")
    console.print(table)

    # Show summary if available
    bill_summary = db.get_bill_summary(bill_id)
    if bill_summary:
        console.print(Panel(bill_summary[:1000], title="Summary"))


@cli.command()
@click.argument("query")
@click.pass_context
def search(ctx, query):
    """Search analyzed bills by keyword."""
    db = get_db(ctx.obj.get("db_path"))
    results = db.search_bills(query)

    if not results:
        console.print(f"No bills found matching '{query}'")
        return

    table = Table(title=f"Search: {query}")
    table.add_column("ID", style="cyan")
    table.add_column("Bill")
    table.add_column("Title")
    table.add_column("Status")
    for r in results:
        bill_label = f"{r['bill_type'].upper()} {r['bill_number']} ({r['congress']}th)"
        table.add_row(str(r["id"]), bill_label, (r.get("title") or "")[:60], r.get("status", "")[:40])
    console.print(table)


@cli.command()
@click.pass_context
def stats(ctx):
    """Show database statistics."""
    db = get_db(ctx.obj.get("db_path"))
    s = db.get_stats()

    console.print(Panel(
        f"Bills: {s['bills_analyzed']} | Spending items: {s['spending_items']} | "
        f"Total: ${s['total_spending']:,.0f} | Scored: {s['items_scored']}",
        title="PorkChop Database",
    ))


if __name__ == "__main__":
    cli()
