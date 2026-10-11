"""
Browser management and stealth utilities for X.com automation.
Supports persistent contexts, humanized delays, realistic typing, and channel fallbacks.
"""

import time
import random
import logging
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright, Playwright, BrowserContext, Page

from .config import Config, config

logger = logging.getLogger("x_automator.browser")


def human_sleep(min_s: float = 1.5, max_s: float = 3.5):
    """Sleep for a random float duration between min_s and max_s."""
    duration = random.uniform(min_s, max_s)
    time.sleep(duration)


def human_type(page: Page, selector: str, text: str, delay_ms: int = 35):
    """
    Type text with realistic keystroke delays and natural variance.
    """
    page.click(selector)
    human_sleep(0.3, 0.7)

    for char in text:
        page.keyboard.type(char)
        # Add slight natural jitter per keystroke
        jitter = random.uniform(delay_ms * 0.5, delay_ms * 1.5) / 1000.0
        # Occasional micro-pause (e.g. after punctuation or space)
        if char in " .,!?\n":
            jitter += random.uniform(0.1, 0.25)
        time.sleep(jitter)


def human_click(page: Page, selector: str, timeout: int = 8000):
    """
    Move to element, wait a moment, and click naturally.
    """
    locator = page.locator(selector).first
    locator.wait_for(state="visible", timeout=timeout)
    locator.hover()
    human_sleep(0.2, 0.5)
    locator.click()


class BrowserManager:
    """Manages browser lifecycle, profiles, and stealth configs."""

    def __init__(self, cfg: Optional[Config] = None):
        self.config = cfg or config
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def start(self, headless: Optional[bool] = None) -> tuple[BrowserContext, Page]:
        """
        Launches a persistent browser context to retain sessions and cookies.
        Uses system Chrome/Edge or Playwright Chromium.
        """
        is_headless = self.config.headless if headless is None else headless
        self._playwright = sync_playwright().start()

        # Stealth browser arguments
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-default-browser-check",
            "--start-maximized",
        ]

        # Determine browser channel
        channel = self.config.browser_channel
        # Fallback to system Chrome if channel is not explicitly set and Chrome exists
        chrome_path = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
        edge_path = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
        
        launch_kwargs = {
            "user_data_dir": str(self.config.profile_dir),
            "headless": is_headless,
            "args": args,
            "no_viewport": True,
            "slow_mo": self.config.slow_mo_ms,
            "color_scheme": "dark",
        }

        # Attempt launching with specified channel, or fallback gracefully
        channels_to_try = []
        if channel:
            channels_to_try.append(channel)
        if chrome_path.exists():
            channels_to_try.append("chrome")
        if edge_path.exists():
            channels_to_try.append("msedge")
        channels_to_try.append(None)  # Bundled chromium

        last_error = None
        for ch in channels_to_try:
            try:
                kwargs = launch_kwargs.copy()
                if ch:
                    kwargs["channel"] = ch
                self._context = self._playwright.chromium.launch_persistent_context(**kwargs)
                break
            except Exception as e:
                last_error = e
                continue

        if not self._context:
            raise RuntimeError(f"Failed to launch browser context: {last_error}")

        # Apply stealth overrides on every new page
        self._context.add_init_script("""
            // Mask navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Mock chrome runtime if absent
            if (!window.chrome) {
                window.chrome = {
                    runtime: {}
                };
            }
        """)

        # Get existing page or open a new one
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = self._context.new_page()

        self._page.set_default_timeout(self.config.timeout_ms)
        return self._context, self._page

    def save_storage_state(self, filepath: Optional[Path] = None) -> Path:
        """Export session cookies and storage state to a JSON file."""
        if not self._context:
            raise RuntimeError("Browser context is not running.")
        out_path = filepath or self.config.storage_state_file
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self._context.storage_state(path=str(out_path))
        return out_path

    def close(self):
        """Clean up browser and playwright instances."""
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        finally:
            self._context = None
            self._page = None

        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        finally:
            self._playwright = None
