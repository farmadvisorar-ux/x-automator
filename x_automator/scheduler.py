"""
Task scheduler and queue runner for automated posting and actions with organic jitter.
"""

import json
import time
import random
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .bot import XAutomator
from .config import Config, config

logger = logging.getLogger("x_automator.scheduler")


class ActionQueue:
    """
    Manages and executes queued X actions (posts, likes, retweets, replies, follows)
    with randomized intervals to mimic organic human behavior.
    """

    def __init__(self, queue_file: Path | str, cfg: Optional[Config] = None):
        self.queue_file = Path(queue_file)
        self.config = cfg or config
        self.automator = XAutomator(self.config)

    def load_queue(self) -> List[Dict[str, Any]]:
        """Loads action items from JSON file."""
        if not self.queue_file.exists():
            return []
        with open(self.queue_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_queue(self, items: List[Dict[str, Any]]):
        """Saves remaining or updated items back to JSON file."""
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)

    def run(
        self,
        min_interval_minutes: float = 15.0,
        max_interval_minutes: float = 45.0,
        max_items: Optional[int] = None
    ):
        """
        Processes queue sequentially with randomized intervals between tasks.
        """
        items = self.load_queue()
        if not items:
            logger.info("No items in queue to process.")
            return

        logger.info(f"Loaded {len(items)} items from queue.")
        processed = 0

        with self.automator:
            while items and (max_items is None or processed < max_items):
                item = items[0]
                action = item.get("action", "post").lower()
                status = item.get("status", "pending")

                if status == "completed":
                    items.pop(0)
                    self.save_queue(items)
                    continue

                logger.info(f"Executing action [{action}]: {item.get('text') or item.get('url') or item.get('user')}")

                try:
                    if action == "post":
                        self.automator.post_tweet(
                            text=item["text"],
                            media_paths=item.get("media", [])
                        )
                    elif action == "like":
                        self.automator.like_tweet(tweet_url=item["url"])
                    elif action == "retweet":
                        self.automator.retweet(tweet_url=item["url"])
                    elif action == "reply":
                        self.automator.reply_to_tweet(
                            tweet_url=item["url"],
                            text=item["text"],
                            media_paths=item.get("media", [])
                        )
                    elif action == "follow":
                        self.automator.follow_user(username=item["user"])
                    else:
                        logger.warning(f"Unknown action type: {action}")

                    item["status"] = "completed"
                    item["executed_at"] = datetime.now().isoformat()
                    # Remove from pending queue or mark completed
                    items.pop(0)
                    self.save_queue(items)
                    processed += 1
                    logger.info(f"Successfully finished item {processed}.")

                except Exception as e:
                    logger.error(f"Failed action item: {e}")
                    item["status"] = "failed"
                    item["error"] = str(e)
                    self.save_queue(items)
                    break

                if items and (max_items is None or processed < max_items):
                    delay_s = random.uniform(min_interval_minutes * 60, max_interval_minutes * 60)
                    logger.info(f"Sleeping for {delay_s/60:.1f} minutes before next task...")
                    time.sleep(delay_s)

        logger.info(f"Queue run finished. Processed {processed} tasks.")
