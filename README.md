# 🤖 X.com (Twitter) API-Free Automator

A resilient, API-free browser automation engine for X.com (Twitter) built with Python and Playwright. It automates **Posting**, **Commenting/Replying**, **Liking**, **Retweeting/Reposting**, **Following**, and **Scheduled Queues** without needing an official X Developer API key or subscription.

---

## ⚡ Key Highlights

- **No Official API Required**: Runs via browser automation directly through X's web interface.
- **Persistent Profile & Session Capture**: Logs in once interactively (handling 2FA, Captchas, or email checks) and permanently saves cookies and browser state. No repeated logins or suspicious login flags.
- **Full Action Suite**:
  - 📝 **Post**: Publish tweets with text and images/videos.
  - 💬 **Comment / Reply**: Reply directly to tweets by URL.
  - ❤️ **Like / Unlike**: Safe engagement with duplicate check.
  - 🔁 **Retweet / Repost**: One-click reposting with confirmation verification.
  - 👤 **Follow / Unfollow**: Target profiles by username.
  - 🔍 **Auto Engage**: Search hashtags/keywords and pace out likes/replies.
  - ⏳ **Queue & Scheduler**: Run batch tasks with natural random delays.
- **Stealth & Anti-Detection**:
  - Random keystroke intervals (`human_type`).
  - Organic sleep jitter between actions (`human_sleep`).
  - Hides `navigator.webdriver` automation flags.
  - Native Google Chrome & Microsoft Edge channel fallback.
- 🌐 **Web Studio Dashboard**: Full visual glassmorphic web dashboard with live activity logging, tweet compose, queue management, and REST API.

---

## 🌐 Web Studio Dashboard

You can run the web dashboard locally or host it publicly:

```powershell
# Launch local web studio on port 8000
uv run python main.py web --port 8000
```
Open **`http://localhost:8000`** in your browser.

To expose as a public hosted URL, you can tunnel port 8000 (e.g. via SSH `ssh -T -o StrictHostKeyChecking=no -R 80:127.0.0.1:8000 nokey@localhost.run` or Cloudflare tunnel).

---

## 📦 Quick Setup

1. **Navigate to the project directory:**
   ```powershell
   cd C:\Users\Admin\.gemini\antigravity\scratch\x-automator
   ```

2. **One-Time Session Login:**
   Run the interactive login command. A browser window will open for you to log in normally to your X account:
   ```powershell
   uv run python main.py login
   ```
   *Once you log in and reach your home feed, the automator detects authentication, saves your profile session to `./sessions/`, and closes cleanly.*

3. **Verify Authentication:**
   ```powershell
   uv run python main.py check-auth
   ```

---

## 🚀 CLI Commands

### 1. Post a Tweet
```powershell
# Plain text
uv run python main.py post "Building autonomous tools with Python! 🚀 #dev"

# With media attachments
uv run python main.py post "Check out this screenshot!" --media "C:\path\to\image.png"
```

### 2. Comment / Reply to a Tweet
```powershell
uv run python main.py reply "https://x.com/username/status/123456789" "Great insight! Thanks for sharing."
```

### 3. Like or Unlike a Tweet
```powershell
# Like
uv run python main.py like "https://x.com/username/status/123456789"

# Unlike
uv run python main.py unlike "https://x.com/username/status/123456789"
```

### 4. Retweet (Repost)
```powershell
uv run python main.py retweet "https://x.com/username/status/123456789"
```

### 5. Follow or Unfollow a User
```powershell
# Follow
uv run python main.py follow "elonmusk"

# Unfollow
uv run python main.py unfollow "elonmusk"
```

### 6. View Live Feed
```powershell
uv run python main.py feed --count 5
```

### 7. Keyword / Hashtag Auto-Engagement
Searches live posts on a topic and automatically likes them with organic pacing:
```powershell
uv run python main.py engage "#buildinpublic" --count 3 --like
```

### 8. Batch Action Queue
Process scheduled posts, likes, replies, and follows sequentially with humanized intervals:
```powershell
uv run python main.py run-queue --file posts_queue.json --min-mins 15 --max-mins 30
```

---

## 🐍 Python Library Usage

You can also import and use `XAutomator` directly in your Python code:

```python
from x_automator import XAutomator

# Use context manager for automatic browser startup and cleanup
with XAutomator(headless=True) as bot:
    # 1. Post a tweet
    bot.post_tweet("Automated tweet via Python!", media_paths=["./chart.png"])

    # 2. Like a tweet
    bot.like_tweet("https://x.com/username/status/123456789")

    # 3. Retweet
    bot.retweet("https://x.com/username/status/123456789")

    # 4. Reply
    bot.reply_to_tweet("https://x.com/username/status/123456789", "Awesome post!")

    # 5. Follow a user
    bot.follow_user("github")
```

---

## 🛡️ Anti-Ban & Safety Guidelines

1. **Avoid aggressive volume**: Don't post 50 tweets or like 200 tweets in 10 minutes. Real humans don't do that.
2. **Use organic intervals**: In `posts_queue.json` or `engage`, allow at least 5–15 minutes between automated posts.
3. **Keep browser profiles persistent**: Never clear the `./sessions/` directory unnecessarily, as retaining cache and persistent cookies makes browser fingerprinting appear 100% natural.
