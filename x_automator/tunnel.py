"""
Resilient tunnel manager for exposing X Automator to a public HTTPS URL.
Includes automatic keepalive and auto-reconnection on disconnect.
"""

import re
import time
import subprocess
import logging
from rich.console import Console
from rich.panel import Panel

console = Console()
logger = logging.getLogger("x_automator.tunnel")


def start_tunnel(local_port: int = 8000):
    """Starts a public SSH tunnel with keep-alive and auto-reconnect."""
    cmd = [
        "ssh",
        "-T",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=6",
        "-o", "ExitOnForwardFailure=yes",
        "-R", f"80:127.0.0.1:{local_port}",
        "nokey@localhost.run"
    ]

    console.print(f"[cyan]Connecting persistent public tunnel for port {local_port}...[/cyan]")

    while True:
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace"
            )

            current_url = None
            for line in iter(proc.stdout.readline, ""):
                match = re.search(r"https://[a-zA-Z0-9-]+\.lhr\.life", line)
                if match:
                    current_url = match.group(0)
                    console.print(Panel.fit(
                        f"[bold green]Public Hosted URL Live:[/bold green] [bold underline white]{current_url}[/bold underline white]\n"
                        f"[dim]Auto-reconnect & keepalive active.[/dim]",
                        border_style="green"
                    ))

            proc.wait()
            console.print("[yellow]Tunnel disconnected. Reconnecting in 3 seconds...[/yellow]")
            time.sleep(3)

        except KeyboardInterrupt:
            console.print("\n[red]Tunnel stopped by user.[/red]")
            break
        except Exception as e:
            console.print(f"[red]Tunnel error: {e}. Retrying in 5 seconds...[/red]")
            time.sleep(5)


if __name__ == "__main__":
    start_tunnel()
