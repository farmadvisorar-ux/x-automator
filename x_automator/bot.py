"""
Core X (Twitter) Automator Engine.
Performs headless or headful actions: post, reply, like, retweet, follow, search engagement.
"""

import time
import logging
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict, Any
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from .config import Config, config
from .selectors import Selectors
from .browser import BrowserManager, human_sleep, human_type, human_click

logger = logging.getLogger("x_automator.bot")


class XAutomator:
    """
    Main bot interface for automating actions on X.com without an API.
    """

    def __init__(self, cfg: Optional[Config] = None, headless: Optional[bool] = None):
        self.config = cfg or config
        self.headless = self.config.headless if headless is None else headless
        self.browser_manager = BrowserManager(self.config)
        self.context = None
        self.page: Optional[Page] = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self):
        """Starts browser session."""
        if not self.page:
            self.context, self.page = self.browser_manager.start(headless=self.headless)
        return self

    def close(self):
        """Closes browser session and flushes state."""
        if self.browser_manager:
            try:
                if self.is_logged_in():
                    self.browser_manager.save_storage_state()
            except Exception:
                pass
            self.browser_manager.close()
        self.page = None
        self.context = None

    # --------------------------------------------------------------------------
    # Authentication & Session Verification
    # --------------------------------------------------------------------------

    def is_logged_in(self) -> bool:
        """
        Checks whether the current browser session is logged in to X.
        """
        if not self.page:
            return False

        current_url = self.page.url
        if "x.com" not in current_url and "twitter.com" not in current_url:
            try:
                self.page.goto(self.config.home_url, wait_until="domcontentloaded")
                human_sleep(2.0, 3.5)
            except Exception:
                return False

        # Look for indicator of logged-in state (e.g., account switcher or primary column)
        try:
            account_btn = self.page.locator(Selectors.ACCOUNT_SWITCHER)
            if account_btn.is_visible(timeout=4000):
                return True
        except Exception:
            pass

        # Check if redirected to login page
        if "/login" in self.page.url or "/i/flow/login" in self.page.url:
            return False

        # Check for tweet compose box on home page
        try:
            compose_box = self.page.locator(Selectors.TWEET_TEXTAREA).first
            if compose_box.is_visible(timeout=3000):
                return True
        except Exception:
            pass

        return False

    def login_interactive(self, timeout_seconds: int = 300) -> bool:
        """
        Launches an interactive (visible) browser window for the user to log in manually.
        Once login is detected, cookies and persistent profile are saved.
        """
        # Close headless browser if running
        if self.page and self.headless:
            self.close()

        # Re-open headfully
        self.headless = False
        self.start()

        logger.info("Opening X.com login page for manual login...")
        self.page.goto(self.config.login_url, wait_until="domcontentloaded")

        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            # Check if user successfully reached home or authenticated
            if self.is_logged_in() or "/home" in self.page.url:
                logger.info("Login detected! Saving session state...")
                human_sleep(2.0, 4.0)
                self.browser_manager.save_storage_state()
                return True
            time.sleep(1.5)

        raise TimeoutError("Interactive login timed out before completion.")

    # --------------------------------------------------------------------------
    # Core Actions: Post / Tweet
    # --------------------------------------------------------------------------

    def post_tweet(self, text: str, media_paths: Optional[List[str | Path]] = None) -> Dict[str, Any]:
        """
        Creates a new post on X.
        Supports text and optional media attachments (images/videos).
        """
        self.start()
        if not self.is_logged_in():
            self.page.goto(self.config.home_url, wait_until="domcontentloaded")
            human_sleep(2.0, 3.0)
            if not self.is_logged_in():
                raise PermissionError("Not logged in. Run 'xbot login' first to save your session.")

        logger.info(f"Navigating to compose post...")
        self.page.goto(self.config.compose_url, wait_until="domcontentloaded")
        human_sleep(2.0, 3.0)

        # Locate textarea
        textarea = self.page.locator(Selectors.TWEET_TEXTAREA).first
        textarea.wait_for(state="visible", timeout=10000)
        
        # Humanized typing
        logger.info("Typing tweet content...")
        human_type(self.page, Selectors.TWEET_TEXTAREA, text, delay_ms=self.config.typing_delay_ms)
        human_sleep(1.0, 2.0)

        # Handle media attachments
        if media_paths:
            resolved_paths = []
            for p in media_paths:
                abs_path = Path(p).resolve()
                if not abs_path.exists():
                    raise FileNotFoundError(f"Media file not found: {p}")
                resolved_paths.append(str(abs_path))

            logger.info(f"Attaching {len(resolved_paths)} media files...")
            file_input = self.page.locator(Selectors.MEDIA_INPUT)
            file_input.set_input_files(resolved_paths)
            
            # Wait for media preview upload to process
            logger.info("Waiting for media upload preview...")
            self.page.locator(Selectors.ATTACHMENTS_CONTAINER).wait_for(state="visible", timeout=20000)
            human_sleep(2.5, 4.0)

        # Click Post button
        post_btn = self.page.locator(Selectors.TWEET_BUTTON_MODAL).or_(
            self.page.locator(Selectors.TWEET_BUTTON_INLINE)
        ).first

        post_btn.wait_for(state="visible", timeout=5000)
        if not post_btn.is_enabled():
            raise RuntimeError("Post button is disabled. Tweet might be empty or exceed character limit.")

        logger.info("Clicking Post...")
        human_click(self.page, Selectors.TWEET_BUTTON_MODAL if self.page.locator(Selectors.TWEET_BUTTON_MODAL).is_visible() else Selectors.TWEET_BUTTON_INLINE)
        
        # Wait for dialog/box to disappear or timeline update
        human_sleep(3.0, 5.0)

        return {
            "success": True,
            "action": "post",
            "text": text,
            "media_count": len(media_paths) if media_paths else 0,
        }

    # --------------------------------------------------------------------------
    # Core Actions: Like & Unlike
    # --------------------------------------------------------------------------

    def like_tweet(self, tweet_url: str) -> Dict[str, Any]:
        """
        Likes a tweet given its full URL (e.g., https://x.com/username/status/123456).
        """
        self.start()
        logger.info(f"Navigating to tweet: {tweet_url}")
        self.page.goto(tweet_url, wait_until="domcontentloaded")
        human_sleep(2.0, 3.5)

        # Check if already liked
        unlike_btn = self.page.locator(Selectors.UNLIKE_BUTTON).first
        if unlike_btn.is_visible():
            logger.info("Tweet is already liked.")
            return {"success": True, "status": "already_liked", "url": tweet_url}

        like_btn = self.page.locator(Selectors.LIKE_BUTTON).first
        like_btn.wait_for(state="visible", timeout=8000)
        logger.info("Clicking Like button...")
        like_btn.click()
        human_sleep(1.5, 3.0)

        # Verify like registered
        liked = self.page.locator(Selectors.UNLIKE_BUTTON).first.is_visible()
        return {"success": liked, "status": "liked" if liked else "failed", "url": tweet_url}

    def unlike_tweet(self, tweet_url: str) -> Dict[str, Any]:
        """
        Unlikes a tweet if currently liked.
        """
        self.start()
        self.page.goto(tweet_url, wait_until="domcontentloaded")
        human_sleep(2.0, 3.0)

        unlike_btn = self.page.locator(Selectors.UNLIKE_BUTTON).first
        if not unlike_btn.is_visible():
            return {"success": True, "status": "not_liked", "url": tweet_url}

        unlike_btn.click()
        human_sleep(1.5, 2.5)
        return {"success": True, "status": "unliked", "url": tweet_url}

    # --------------------------------------------------------------------------
    # Core Actions: Retweet / Repost
    # --------------------------------------------------------------------------

    def retweet(self, tweet_url: str) -> Dict[str, Any]:
        """
        Retweets / Reposts a tweet given its URL.
        """
        self.start()
        logger.info(f"Navigating to tweet for retweet: {tweet_url}")
        self.page.goto(tweet_url, wait_until="domcontentloaded")
        human_sleep(2.0, 3.5)

        # Check if already retweeted
        unretweet_btn = self.page.locator(Selectors.UNRETWEET_BUTTON).first
        if unretweet_btn.is_visible():
            logger.info("Tweet is already retweeted.")
            return {"success": True, "status": "already_retweeted", "url": tweet_url}

        retweet_btn = self.page.locator(Selectors.RETWEET_BUTTON).first
        retweet_btn.wait_for(state="visible", timeout=8000)
        retweet_btn.click()
        human_sleep(0.8, 1.5)

        # Click popup menu "Repost"
        confirm_btn = self.page.locator(Selectors.RETWEET_CONFIRM).first
        confirm_btn.wait_for(state="visible", timeout=5000)
        confirm_btn.click()
        human_sleep(2.0, 3.5)

        # Verify
        retweeted = self.page.locator(Selectors.UNRETWEET_BUTTON).first.is_visible()
        return {"success": retweeted, "status": "retweeted" if retweeted else "failed", "url": tweet_url}

    # --------------------------------------------------------------------------
    # Core Actions: Comment / Reply
    # --------------------------------------------------------------------------

    def reply_to_tweet(self, tweet_url: str, text: str, media_paths: Optional[List[str | Path]] = None) -> Dict[str, Any]:
        """
        Replies / comments on a tweet.
        """
        self.start()
        logger.info(f"Navigating to reply on tweet: {tweet_url}")
        self.page.goto(tweet_url, wait_until="domcontentloaded")
        human_sleep(2.5, 4.0)

        # Look for reply input box on the tweet details page
        # Usually has tweetTextarea_0 visible directly underneath the main tweet
        reply_box = self.page.locator(Selectors.TWEET_TEXTAREA).first
        if not reply_box.is_visible():
            # If not inline, click the Reply icon to open modal
            reply_icon = self.page.locator(Selectors.REPLY_BUTTON).first
            reply_icon.wait_for(state="visible", timeout=8000)
            reply_icon.click()
            human_sleep(1.0, 2.0)
            reply_box = self.page.locator(Selectors.TWEET_TEXTAREA).first

        reply_box.wait_for(state="visible", timeout=8000)
        logger.info("Typing reply text...")
        human_type(self.page, Selectors.TWEET_TEXTAREA, text, delay_ms=self.config.typing_delay_ms)
        human_sleep(1.0, 2.0)

        # Attach media if provided
        if media_paths:
            resolved_paths = [str(Path(p).resolve()) for p in media_paths]
            file_input = self.page.locator(Selectors.MEDIA_INPUT)
            file_input.set_input_files(resolved_paths)
            self.page.locator(Selectors.ATTACHMENTS_CONTAINER).wait_for(state="visible", timeout=15000)
            human_sleep(2.0, 3.5)

        # Submit reply
        submit_btn = self.page.locator(Selectors.TWEET_BUTTON_MODAL).or_(
            self.page.locator(Selectors.TWEET_BUTTON_INLINE)
        ).first
        submit_btn.wait_for(state="visible", timeout=5000)
        submit_btn.click()
        human_sleep(3.0, 5.0)

        return {"success": True, "action": "reply", "url": tweet_url, "text": text}

    # --------------------------------------------------------------------------
    # Core Actions: Follow & Unfollow
    # --------------------------------------------------------------------------

    def follow_user(self, username: str) -> Dict[str, Any]:
        """
        Follows a user profile by handle (e.g., 'elonmusk' or '@elonmusk').
        """
        clean_handle = username.lstrip("@").strip()
        profile_url = f"https://x.com/{clean_handle}"
        self.start()

        logger.info(f"Navigating to user profile: {profile_url}")
        self.page.goto(profile_url, wait_until="domcontentloaded")
        human_sleep(2.5, 4.0)

        # Check if already following
        unfollow_btn = self.page.locator(Selectors.UNFOLLOW_BUTTON).first
        if unfollow_btn.is_visible():
            logger.info(f"Already following @{clean_handle}.")
            return {"success": True, "status": "already_following", "user": clean_handle}

        follow_btn = self.page.locator(Selectors.FOLLOW_BUTTON).first
        if not follow_btn.is_visible():
            # Fallback text locator in case testid varies
            follow_btn = self.page.locator('button:has-text("Follow"):not(:has-text("Following"))').first

        follow_btn.wait_for(state="visible", timeout=8000)
        logger.info(f"Clicking Follow for @{clean_handle}...")
        follow_btn.click()
        human_sleep(2.0, 3.5)

        # Verify
        following = self.page.locator(Selectors.UNFOLLOW_BUTTON).first.is_visible()
        return {"success": following, "status": "followed" if following else "failed", "user": clean_handle}

    def unfollow_user(self, username: str) -> Dict[str, Any]:
        """
        Unfollows a user profile.
        """
        clean_handle = username.lstrip("@").strip()
        profile_url = f"https://x.com/{clean_handle}"
        self.start()

        self.page.goto(profile_url, wait_until="domcontentloaded")
        human_sleep(2.5, 4.0)

        unfollow_btn = self.page.locator(Selectors.UNFOLLOW_BUTTON).first
        if not unfollow_btn.is_visible():
            return {"success": True, "status": "not_following", "user": clean_handle}

        unfollow_btn.click()
        human_sleep(0.8, 1.5)

        # Confirm dialog
        confirm_btn = self.page.locator(Selectors.CONFIRM_UNFOLLOW_BUTTON).first
        if confirm_btn.is_visible():
            confirm_btn.click()
            human_sleep(1.5, 3.0)

        return {"success": True, "status": "unfollowed", "user": clean_handle}

    # --------------------------------------------------------------------------
    # Discovery & Timeline Engagement
    # --------------------------------------------------------------------------

    def get_timeline_tweets(self, count: int = 5) -> List[Dict[str, str]]:
        """
        Scrapes top N visible tweets from home feed.
        """
        self.start()
        self.page.goto(self.config.home_url, wait_until="domcontentloaded")
        human_sleep(3.0, 5.0)

        tweets_data = []
        articles = self.page.locator(Selectors.TWEET_ARTICLE).all()

        for art in articles[:count]:
            try:
                # Find author and text
                text_elem = art.locator(Selectors.TWEET_TEXT).first
                text = text_elem.inner_text() if text_elem.is_visible() else ""
                
                # Extract link to tweet
                links = art.locator('a[href*="/status/"]').all()
                tweet_link = ""
                for l in links:
                    href = l.get_attribute("href")
                    if href and "/status/" in href and not href.endswith("/analytics"):
                        tweet_link = f"https://x.com{href}" if href.startswith("/") else href
                        break

                if tweet_link:
                    tweets_data.append({"url": tweet_link, "text": text[:120]})
            except Exception:
                continue

        return tweets_data

    def auto_engage_search(
        self,
        query: str,
        max_actions: int = 3,
        auto_like: bool = True,
        comment_template: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Searches for a keyword or hashtag and organically likes / replies with pacing.
        """
        self.start()
        encoded = urllib.parse.quote(query)
        search_url = f"https://x.com/search?q={encoded}&f=live"
        logger.info(f"Searching for: {query}")
        self.page.goto(search_url, wait_until="domcontentloaded")
        human_sleep(3.5, 6.0)

        results = []
        articles = self.page.locator(Selectors.TWEET_ARTICLE).all()
        logger.info(f"Found {len(articles)} tweets in search feed.")

        for i, art in enumerate(articles[:max_actions]):
            try:
                # Extract tweet URL
                links = art.locator('a[href*="/status/"]').all()
                tweet_url = ""
                for l in links:
                    href = l.get_attribute("href")
                    if href and "/status/" in href and not href.endswith("/analytics"):
                        tweet_url = f"https://x.com{href}" if href.startswith("/") else href
                        break

                if not tweet_url:
                    continue

                action_res = {"url": tweet_url}

                # Like if requested
                if auto_like:
                    like_btn = art.locator(Selectors.LIKE_BUTTON).first
                    if like_btn.is_visible():
                        like_btn.scroll_into_view_if_needed()
                        human_sleep(0.8, 1.5)
                        like_btn.click()
                        action_res["liked"] = True
                        logger.info(f"Liked tweet: {tweet_url}")
                    else:
                        action_res["liked"] = False

                # Comment if template provided
                if comment_template:
                    self.reply_to_tweet(tweet_url, comment_template)
                    action_res["commented"] = True
                    # Re-navigate back to search
                    self.page.goto(search_url, wait_until="domcontentloaded")
                    human_sleep(3.0, 5.0)

                results.append(action_res)

                # Organic delay between actions to avoid rate limits
                human_sleep(8.0, 15.0)

            except Exception as e:
                logger.error(f"Error engaging with tweet: {e}")
                continue

        return results
