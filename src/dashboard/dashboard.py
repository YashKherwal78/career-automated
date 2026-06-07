import sqlite3
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from config import Config

def render_analytics():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    console = Console()

    cursor.execute("SELECT COUNT(*) as c FROM leads WHERE status != 'New'")
    processed = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM leads WHERE hr_contacted = 1 OR founder_contacted = 1")
    sent = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM leads WHERE hr_replied = 1 OR founder_replied = 1")
    replies = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM leads WHERE reply_classification = 'Positive Interest'")
    positives = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM leads WHERE interview_scheduled = 1 OR reply_classification = 'Interview Request'")
    interviews = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM leads WHERE bounce_status = 1")
    bounces = cursor.fetchone()["c"]
    
    cursor.execute("SELECT SUM(total_cost) as t FROM leads")
    row = cursor.fetchone()
    total_cost = row["t"] if row["t"] else 0.0

    bounce_rate = (bounces / sent * 100) if sent > 0 else 0
    reply_rate = (replies / sent * 100) if sent > 0 else 0
    cpi = (total_cost / interviews) if interviews > 0 else 0

    table = Table(title="AI Recruiting Intelligence Dashboard")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Companies Processed", str(processed))
    table.add_row("Total Emails Sent", str(sent))
    table.add_row("Total Replies", str(replies))
    table.add_row("Positive Replies", str(positives))
    table.add_row("Interviews Generated", str(interviews))
    table.add_row("Hard Bounces", str(bounces))
    table.add_row("Bounce Rate", f"{bounce_rate:.1f}%")
    table.add_row("Reply Rate", f"{reply_rate:.1f}%")
    table.add_row("Total Cost", f"${total_cost:.2f}")
    table.add_row("Cost Per Interview", f"${cpi:.2f}")

    console.print(Panel(table, title="Funnel & Cost Analytics", border_style="green"))
    conn.close()

if __name__ == "__main__":
    render_analytics()
