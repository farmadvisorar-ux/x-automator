import sys
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .bot import XAutomator
from .config import config
from .scheduler import ActionQueue

app = typer.Typer(
    name="xbot",
    help="X.com (Twitter) API-free Browser Automator",
    add_completion=False,
)
console = Console(legacy_windows=False)



@app.command()
def login(
    timeout: int = typer.Option(300, "--timeout", "-t", help="Timeout in seconds for manual login"),
):
    """
    Launch browser headfully to log in to X manually and persist cookies.
    """
    console.print(Panel.fit("[bold cyan]X.com Interactive Session Login[/bold cyan]\nA browser window will open. Please log into your X account.\nYour session and cookies will be automatically captured and saved.", border_style="cyan"))
    
    automator = XAutomator(headless=False)
    try:
        automator.login_interactive(timeout_seconds=timeout)
        console.print("[bold green]✓ Session successfully captured and saved![/bold green]")
        console.print(f"[dim]Saved profile to: {config.profile_dir}[/dim]")
    except Exception as e:
        console.print(f"[bold red]✗ Login failed or timed out:[/bold red] {e}")
        raise typer.Exit(code=1)
    finally:
        automator.close()


@app.command(name="check-auth")
def check_auth():
    """
    Check if the saved session is currently logged in.
    """
    automator = XAutomator(headless=True)
    try:
        automator.start()
        logged_in = automator.is_logged_in()
        if logged_in:
            console.print("[bold green]✓ Session is active and authenticated![/bold green]")
        else:
            console.print("[bold yellow]! No active login session found. Run 'xbot login' first.[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]Error checking session:[/bold red] {e}")
    finally:
        automator.close()


@app.command()
def post(
    text: str = typer.Argument(..., help="Text content of the tweet/post"),
    media: Optional[List[str]] = typer.Option(None, "--media", "-m", help="Path(s) to images/videos to attach"),
    headless: bool = typer.Option(False, "--headless/--headful", help="Run in headless mode"),
):
    """
    Publish a post (tweet) with optional media attachments.
    """
    console.print(f"[cyan]Posting to X...[/cyan]\n[italic]\"{text}\"[/italic]")
    automator = XAutomator(headless=headless)
    try:
        with automator:
            res = automator.post_tweet(text=text, media_paths=media)
            console.print("[bold green]✓ Post published successfully![/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to post:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def like(
    url: str = typer.Argument(..., help="Full tweet URL to like"),
    headless: bool = typer.Option(False, "--headless/--headful", help="Run in headless mode"),
):
    """
    Like a tweet by URL.
    """
    automator = XAutomator(headless=headless)
    try:
        with automator:
            res = automator.like_tweet(url)
            console.print(f"[bold green]✓ Tweet {res.get('status')}: {url}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to like tweet:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def unlike(
    url: str = typer.Argument(..., help="Full tweet URL to unlike"),
    headless: bool = typer.Option(False, "--headless/--headful", help="Run in headless mode"),
):
    """
    Unlike a tweet by URL.
    """
    automator = XAutomator(headless=headless)
    try:
        with automator:
            res = automator.unlike_tweet(url)
            console.print(f"[bold green]✓ Tweet {res.get('status')}: {url}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to unlike tweet:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def retweet(
    url: str = typer.Argument(..., help="Full tweet URL to retweet/repost"),
    headless: bool = typer.Option(False, "--headless/--headful", help="Run in headless mode"),
):
    """
    Retweet / repost a tweet by URL.
    """
    automator = XAutomator(headless=headless)
    try:
        with automator:
            res = automator.retweet(url)
            console.print(f"[bold green]✓ Tweet {res.get('status')}: {url}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to retweet:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def reply(
    url: str = typer.Argument(..., help="Full tweet URL to comment on"),
    text: str = typer.Argument(..., help="Reply comment text"),
    media: Optional[List[str]] = typer.Option(None, "--media", "-m", help="Media files to attach"),
    headless: bool = typer.Option(False, "--headless/--headful", help="Run in headless mode"),
):
    """
    Reply/comment on a tweet.
    """
    automator = XAutomator(headless=headless)
    try:
        with automator:
            res = automator.reply_to_tweet(tweet_url=url, text=text, media_paths=media)
            console.print(f"[bold green]✓ Reply submitted successfully to {url}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to reply:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def follow(
    user: str = typer.Argument(..., help="Twitter handle (e.g. @elonmusk)"),
    headless: bool = typer.Option(False, "--headless/--headful", help="Run in headless mode"),
):
    """
    Follow a user by handle.
    """
    automator = XAutomator(headless=headless)
    try:
        with automator:
            res = automator.follow_user(user)
            console.print(f"[bold green]✓ User @{res.get('user')} status: {res.get('status')}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to follow user:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def unfollow(
    user: str = typer.Argument(..., help="Twitter handle to unfollow"),
    headless: bool = typer.Option(False, "--headless/--headful", help="Run in headless mode"),
):
    """
    Unfollow a user.
    """
    automator = XAutomator(headless=headless)
    try:
        with automator:
            res = automator.unfollow_user(user)
            console.print(f"[bold green]✓ User @{res.get('user')} status: {res.get('status')}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to unfollow user:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def feed(
    count: int = typer.Option(5, "--count", "-c", help="Number of tweets to retrieve"),
    headless: bool = typer.Option(False, "--headless/--headful", help="Run in headless mode"),
):
    """
    View recent tweets from your home feed.
    """
    automator = XAutomator(headless=headless)
    try:
        with automator:
            tweets = automator.get_timeline_tweets(count=count)
            table = Table(title=f"Recent Home Feed Tweets ({len(tweets)})")
            table.add_column("URL", style="cyan")
            table.add_column("Snippet", style="white")
            for t in tweets:
                table.add_row(t["url"], t["text"])
            console.print(table)
    except Exception as e:
        console.print(f"[bold red]✗ Failed to fetch feed:[/bold red] {e}")
    finally:
        automator.close()


@app.command()
def engage(
    query: str = typer.Argument(..., help="Search query or hashtag (e.g. #AI or 'build in public')"),
    count: int = typer.Option(3, "--count", "-c", help="Max number of tweets to engage with"),
    like: bool = typer.Option(True, "--like/--no-like", help="Like matching tweets"),
    comment: Optional[str] = typer.Option(None, "--comment", help="Optional comment template to post"),
    headless: bool = typer.Option(False, "--headless/--headful", help="Run in headless mode"),
):
    """
    Search for a topic/hashtag and automatically like or comment on live tweets.
    """
    automator = XAutomator(headless=headless)
    try:
        with automator:
            results = automator.auto_engage_search(
                query=query,
                max_actions=count,
                auto_like=like,
                comment_template=comment
            )
            console.print(f"[bold green]✓ Engaged with {len(results)} tweets on topic '{query}'[/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Engagement failed:[/bold red] {e}")
    finally:
        automator.close()


@app.command(name="run-queue")
def run_queue(
    file: Path = typer.Option(Path("posts_queue.json"), "--file", "-f", help="Queue JSON file"),
    min_mins: float = typer.Option(10.0, "--min-mins", help="Min delay between tasks in minutes"),
    max_mins: float = typer.Option(30.0, "--max-mins", help="Max delay between tasks in minutes"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Max actions to execute"),
):
    """
    Execute tasks from a queued JSON file with natural delays.
    """
    queue = ActionQueue(queue_file=file)
    queue.run(min_interval_minutes=min_mins, max_interval_minutes=max_mins, max_items=limit)


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host address to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto reload"),
):
    """
    Launch the interactive Web Dashboard & REST API.
    """
    import uvicorn
    console.print(Panel.fit(
        f"[bold cyan]Launching X Automator Web Studio[/bold cyan]\n"
        f"Local Dashboard URL: [bold green]http://{host}:{port}[/bold green]\n"
        f"API Documentation:  [bold green]http://{host}:{port}/docs[/bold green]",
        border_style="cyan"
    ))
    uvicorn.run("x_automator.web_app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()

