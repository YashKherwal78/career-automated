from src.system.logger import setup_logger
logger = setup_logger('human_review_gate')
import json
from rich.console import Console
from rich.panel import Panel

console = Console()

def human_review_gate(company_name: str, subject: str, email_body: str, resume_path: str, tailored_project: str):
    """
    Displays the generated outreach for human approval before sending.
    """
    console.print(f"\n[bold yellow]=== HUMAN REVIEW GATE: {company_name} ===[/bold yellow]")
    console.print(Panel(f"[bold cyan]Subject:[/bold cyan] {subject}\n\n[bold cyan]Body:[/bold cyan]\n{email_body}", title="Generated Email"))
    console.print(f"[bold green]Tailored Resume Path:[/bold green] {resume_path}")
    console.print(f"[bold green]Selected Project:[/bold green] {tailored_project}")
    
    while True:
        choice = input(f"\nApprove outreach to {company_name}? (Y/n/edit): ").strip().lower()
        if choice == "" or choice == "y":
            return True, email_body
        elif choice == "n":
            return False, email_body
        elif choice == "edit":
            logger.info("Feature coming soon: Manual edits.")
        else:
            logger.info("Invalid choice. Please enter Y, n, or edit.")
