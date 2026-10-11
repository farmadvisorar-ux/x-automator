"""
X.com (Twitter) Browser Automator
API-free automation for posting, replying, liking, retweeting, and following.
"""

from .bot import XAutomator
from .config import Config

__version__ = "0.1.0"
__all__ = ["XAutomator", "Config"]
