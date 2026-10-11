import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
PROFILE_DIR = SESSIONS_DIR / "browser_profile"
STORAGE_STATE_FILE = SESSIONS_DIR / "storage_state.json"


@dataclass
class Config:
    base_dir: Path = BASE_DIR
    sessions_dir: Path = SESSIONS_DIR
    profile_dir: Path = PROFILE_DIR
    storage_state_file: Path = STORAGE_STATE_FILE

    # Browser options
    # Set headless=False for visual monitoring or manual login
    headless: bool = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")
    # Browser channel: 'chrome', 'msedge', or None (uses Playwright bundled Chromium)
    browser_channel: str | None = os.getenv("BROWSER_CHANNEL", None)
    slow_mo_ms: int = int(os.getenv("SLOW_MO_MS", "50"))
    timeout_ms: int = int(os.getenv("TIMEOUT_MS", "30000"))

    # Humanized pacing (seconds)
    min_delay: float = float(os.getenv("MIN_DELAY", "2.0"))
    max_delay: float = float(os.getenv("MAX_DELAY", "5.0"))
    typing_delay_ms: int = int(os.getenv("TYPING_DELAY_MS", "35"))

    # Target URLs
    home_url: str = "https://x.com/home"
    login_url: str = "https://x.com/login"
    compose_url: str = "https://x.com/compose/post"

    def __post_init__(self):
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.profile_dir.mkdir(parents=True, exist_ok=True)


config = Config()
