"""
FastAPI Web Dashboard for X.com (Twitter) Automator.
Serves an interactive web application and REST API for all actions:
Posting, Replying, Liking, Retweeting, Following, Auto-Engagement, and Queue Management.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, Request, Form, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .bot import XAutomator
from .config import config
from .scheduler import ActionQueue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("x_automator.web")

app = FastAPI(title="X.com Automator Web Dashboard", version="0.1.0")

# Ensure upload directory
UPLOADS_DIR = config.base_dir / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Activity log buffer
activity_logs = []


def log_activity(action: str, status: str, details: str):
    import datetime
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    entry = {"time": now_str, "action": action, "status": status, "details": details}
    activity_logs.insert(0, entry)
    if len(activity_logs) > 50:
        activity_logs.pop()


# ------------------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/status")
def get_status():
    """Check if session is currently authenticated."""
    try:
        automator = XAutomator(headless=True)
        with automator:
            logged_in = automator.is_logged_in()
        return {"logged_in": logged_in, "profile_dir": str(config.profile_dir)}
    except Exception as e:
        return {"logged_in": False, "error": str(e)}


@app.post("/api/login")
def trigger_interactive_login(background_tasks: BackgroundTasks):
    """Launches headful interactive login in background."""
    def _do_login():
        try:
            log_activity("LOGIN", "STARTING", "Opening headful browser window for manual sign-in...")
            bot = XAutomator(headless=False)
            bot.login_interactive(timeout_seconds=300)
            bot.close()
            log_activity("LOGIN", "SUCCESS", "Interactive login completed! Session saved.")
        except Exception as e:
            log_activity("LOGIN", "FAILED", f"Login error: {str(e)}")

    background_tasks.add_task(_do_login)
    return {"message": "Browser login opened on host machine. Please complete sign-in."}


@app.post("/api/post")
async def api_post_tweet(
    text: str = Form(...),
    files: Optional[List[UploadFile]] = File(None)
):
    """Post a new tweet with optional media files."""
    media_paths = []
    if files:
        for f in files:
            if f.filename:
                save_path = UPLOADS_DIR / f.filename
                with open(save_path, "wb") as buffer:
                    buffer.write(await f.read())
                media_paths.append(str(save_path))

    try:
        log_activity("POST", "IN_PROGRESS", f"Posting: '{text[:60]}...'")
        bot = XAutomator(headless=False)
        with bot:
            res = bot.post_tweet(text=text, media_paths=media_paths if media_paths else None)
        log_activity("POST", "SUCCESS", f"Published post successfully: '{text[:40]}...'")
        return {"success": True, "result": res}
    except Exception as e:
        log_activity("POST", "ERROR", str(e))
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/reply")
async def api_reply_tweet(
    url: str = Form(...),
    text: str = Form(...),
    files: Optional[List[UploadFile]] = File(None)
):
    """Reply / comment on a tweet."""
    media_paths = []
    if files:
        for f in files:
            if f.filename:
                save_path = UPLOADS_DIR / f.filename
                with open(save_path, "wb") as buffer:
                    buffer.write(await f.read())
                media_paths.append(str(save_path))

    try:
        log_activity("REPLY", "IN_PROGRESS", f"Replying to {url}: '{text[:40]}...'")
        bot = XAutomator(headless=False)
        with bot:
            res = bot.reply_to_tweet(tweet_url=url, text=text, media_paths=media_paths if media_paths else None)
        log_activity("REPLY", "SUCCESS", f"Reply sent to {url}")
        return {"success": True, "result": res}
    except Exception as e:
        log_activity("REPLY", "ERROR", str(e))
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/like")
def api_like_tweet(url: str = Form(...)):
    """Like a tweet."""
    try:
        log_activity("LIKE", "IN_PROGRESS", f"Liking {url}")
        bot = XAutomator(headless=False)
        with bot:
            res = bot.like_tweet(tweet_url=url)
        log_activity("LIKE", "SUCCESS", f"Status: {res.get('status')} on {url}")
        return {"success": True, "result": res}
    except Exception as e:
        log_activity("LIKE", "ERROR", str(e))
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/unlike")
def api_unlike_tweet(url: str = Form(...)):
    """Unlike a tweet."""
    try:
        log_activity("UNLIKE", "IN_PROGRESS", f"Unliking {url}")
        bot = XAutomator(headless=False)
        with bot:
            res = bot.unlike_tweet(tweet_url=url)
        log_activity("UNLIKE", "SUCCESS", f"Status: {res.get('status')} on {url}")
        return {"success": True, "result": res}
    except Exception as e:
        log_activity("UNLIKE", "ERROR", str(e))
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/retweet")
def api_retweet(url: str = Form(...)):
    """Retweet / repost a tweet."""
    try:
        log_activity("RETWEET", "IN_PROGRESS", f"Retweeting {url}")
        bot = XAutomator(headless=False)
        with bot:
            res = bot.retweet(tweet_url=url)
        log_activity("RETWEET", "SUCCESS", f"Status: {res.get('status')} on {url}")
        return {"success": True, "result": res}
    except Exception as e:
        log_activity("RETWEET", "ERROR", str(e))
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/follow")
def api_follow(user: str = Form(...)):
    """Follow a user profile."""
    try:
        log_activity("FOLLOW", "IN_PROGRESS", f"Following @{user}")
        bot = XAutomator(headless=False)
        with bot:
            res = bot.follow_user(username=user)
        log_activity("FOLLOW", "SUCCESS", f"Status: {res.get('status')} for @{user}")
        return {"success": True, "result": res}
    except Exception as e:
        log_activity("FOLLOW", "ERROR", str(e))
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/unfollow")
def api_unfollow(user: str = Form(...)):
    """Unfollow a user."""
    try:
        log_activity("UNFOLLOW", "IN_PROGRESS", f"Unfollowing @{user}")
        bot = XAutomator(headless=False)
        with bot:
            res = bot.unfollow_user(username=user)
        log_activity("UNFOLLOW", "SUCCESS", f"Status: {res.get('status')} for @{user}")
        return {"success": True, "result": res}
    except Exception as e:
        log_activity("UNFOLLOW", "ERROR", str(e))
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/engage")
def api_engage(
    query: str = Form(...),
    count: int = Form(3),
    like: bool = Form(True),
    comment: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None
):
    """Run search engagement."""
    def _do_engage():
        try:
            log_activity("ENGAGE", "IN_PROGRESS", f"Searching '{query}' (up to {count} tweets)...")
            bot = XAutomator(headless=False)
            with bot:
                results = bot.auto_engage_search(
                    query=query,
                    max_actions=count,
                    auto_like=like,
                    comment_template=comment if comment else None
                )
            log_activity("ENGAGE", "SUCCESS", f"Engaged with {len(results)} tweets on '{query}'")
        except Exception as e:
            log_activity("ENGAGE", "ERROR", str(e))

    if background_tasks:
        background_tasks.add_task(_do_engage)
    else:
        _do_engage()
    return {"message": f"Engagement started for topic '{query}'"}


@app.get("/api/queue")
def api_get_queue():
    """Retrieve scheduled action queue."""
    q_file = config.base_dir / "posts_queue.json"
    queue = ActionQueue(queue_file=q_file)
    return {"items": queue.load_queue()}


@app.post("/api/queue/add")
def api_add_queue(
    action: str = Form(...),
    text: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    user: Optional[str] = Form(None),
):
    """Add a new task to queue."""
    q_file = config.base_dir / "posts_queue.json"
    queue = ActionQueue(queue_file=q_file)
    items = queue.load_queue()
    new_item = {"action": action, "status": "pending"}
    if text:
        new_item["text"] = text
    if url:
        new_item["url"] = url
    if user:
        new_item["user"] = user
    items.append(new_item)
    queue.save_queue(items)
    log_activity("QUEUE", "ADDED", f"Added {action} item to queue")
    return {"success": True, "items": items}


@app.post("/api/queue/run")
def api_run_queue(
    min_mins: float = Form(5.0),
    max_mins: float = Form(15.0),
    background_tasks: BackgroundTasks = None
):
    """Run the queue in background."""
    def _do_run():
        try:
            log_activity("QUEUE_RUNNER", "STARTED", "Processing scheduled queue with pacing...")
            q_file = config.base_dir / "posts_queue.json"
            queue = ActionQueue(queue_file=q_file)
            queue.run(min_interval_minutes=min_mins, max_interval_minutes=max_mins)
            log_activity("QUEUE_RUNNER", "FINISHED", "Queue execution completed.")
        except Exception as e:
            log_activity("QUEUE_RUNNER", "ERROR", str(e))

    background_tasks.add_task(_do_run)
    return {"message": "Queue execution initiated in background."}


@app.get("/api/logs")
def get_logs():
    return {"logs": activity_logs}


# ------------------------------------------------------------------------------
# Frontend Dashboard HTML
# ------------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index_page():
    return HTML_CONTENT


HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>X.com Automator Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { background-color: #0b0e14; color: #e2e8f0; font-family: system-ui, -apple-system, sans-serif; }
    .glass { background: rgba(18, 24, 38, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .tab-active { border-bottom: 2px solid #38bdf8; color: #38bdf8; font-weight: 600; }
  </style>
</head>
<body class="min-h-screen flex flex-col">

  <!-- Top Navigation -->
  <header class="glass sticky top-0 z-50 px-6 py-4 flex items-center justify-between border-b border-slate-800">
    <div class="flex items-center space-x-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-sky-500/20">
        𝕏
      </div>
      <div>
        <h1 class="font-bold text-lg text-white leading-tight">X Automator Studio</h1>
        <p class="text-xs text-slate-400">API-Free Browser Automation Engine</p>
      </div>
    </div>

    <!-- Status Badges & Controls -->
    <div class="flex items-center space-x-4">
      <div id="authBadge" class="flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
        <span class="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></span>
        <span>Checking Auth...</span>
      </div>
      <button onclick="checkAuth()" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition">
        <i class="fa-solid fa-arrows-rotate mr-1"></i> Refresh
      </button>
      <button onclick="triggerLogin()" class="text-xs px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium transition shadow-md shadow-sky-600/30">
        <i class="fa-solid fa-key mr-1"></i> Interactive Login
      </button>
    </div>
  </header>

  <!-- Main Container -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
    
    <!-- Left Column: Controls & Tabs (2 cols on large screen) -->
    <div class="lg:col-span-2 space-y-6">

      <!-- Navigation Tabs -->
      <div class="flex space-x-6 border-b border-slate-800 text-sm overflow-x-auto pb-1">
        <button onclick="switchTab('tab-post')" id="nav-tab-post" class="py-2 px-1 text-slate-400 hover:text-white tab-active">
          <i class="fa-solid fa-pen-nib mr-1.5"></i> Post Tweet
        </button>
        <button onclick="switchTab('tab-reply')" id="nav-tab-reply" class="py-2 px-1 text-slate-400 hover:text-white">
          <i class="fa-solid fa-comment-dots mr-1.5"></i> Reply / Comment
        </button>
        <button onclick="switchTab('tab-engage')" id="nav-tab-engage" class="py-2 px-1 text-slate-400 hover:text-white">
          <i class="fa-solid fa-heart mr-1.5"></i> Like / Retweet
        </button>
        <button onclick="switchTab('tab-follow')" id="nav-tab-follow" class="py-2 px-1 text-slate-400 hover:text-white">
          <i class="fa-solid fa-user-plus mr-1.5"></i> Follow / Unfollow
        </button>
        <button onclick="switchTab('tab-search')" id="nav-tab-search" class="py-2 px-1 text-slate-400 hover:text-white">
          <i class="fa-solid fa-magnifying-glass mr-1.5"></i> Auto-Engage
        </button>
        <button onclick="switchTab('tab-queue')" id="nav-tab-queue" class="py-2 px-1 text-slate-400 hover:text-white">
          <i class="fa-solid fa-list-check mr-1.5"></i> Queue
        </button>
      </div>

      <!-- Tab 1: Post Tweet -->
      <div id="tab-post" class="tab-pane glass rounded-2xl p-6 space-y-4">
        <div class="flex justify-between items-center">
          <h2 class="text-base font-semibold text-white">Create New Post</h2>
          <span id="charCount" class="text-xs text-slate-400">0 / 280</span>
        </div>
        <textarea id="postText" rows="4" maxlength="280" placeholder="What's happening? Type your tweet here..."
          oninput="updateCharCount(this)"
          class="w-full bg-slate-900/80 border border-slate-700 rounded-xl p-3 text-sm text-slate-100 focus:outline-none focus:border-sky-500"></textarea>
        
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Optional Media (Images/Videos):</label>
          <input type="file" id="postFiles" multiple class="block w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-sky-400 hover:file:bg-slate-700"/>
        </div>

        <button onclick="submitPost()" class="w-full py-2.5 rounded-xl bg-sky-500 hover:bg-sky-400 text-white font-medium text-sm transition shadow-lg shadow-sky-500/25 flex items-center justify-center space-x-2">
          <i class="fa-solid fa-paper-plane"></i>
          <span>Publish Post</span>
        </button>
      </div>

      <!-- Tab 2: Reply -->
      <div id="tab-reply" class="tab-pane hidden glass rounded-2xl p-6 space-y-4">
        <h2 class="text-base font-semibold text-white">Comment / Reply to Tweet</h2>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Target Tweet URL:</label>
          <input type="url" id="replyUrl" placeholder="https://x.com/username/status/123456789"
            class="w-full bg-slate-900/80 border border-slate-700 rounded-xl p-2.5 text-sm text-slate-100 focus:outline-none focus:border-sky-500"/>
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Reply Content:</label>
          <textarea id="replyText" rows="3" placeholder="Type your comment..."
            class="w-full bg-slate-900/80 border border-slate-700 rounded-xl p-3 text-sm text-slate-100 focus:outline-none focus:border-sky-500"></textarea>
        </div>
        <div>
          <input type="file" id="replyFiles" multiple class="block w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-sky-400 hover:file:bg-slate-700"/>
        </div>
        <button onclick="submitReply()" class="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition shadow-lg shadow-indigo-600/25">
          <i class="fa-solid fa-reply mr-1"></i> Send Reply
        </button>
      </div>

      <!-- Tab 3: Like / Retweet -->
      <div id="tab-engage" class="tab-pane hidden glass rounded-2xl p-6 space-y-4">
        <h2 class="text-base font-semibold text-white">Engage with a Tweet</h2>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Tweet URL:</label>
          <input type="url" id="engageUrl" placeholder="https://x.com/username/status/123456789"
            class="w-full bg-slate-900/80 border border-slate-700 rounded-xl p-2.5 text-sm text-slate-100 focus:outline-none focus:border-sky-500"/>
        </div>
        <div class="grid grid-cols-3 gap-3 pt-2">
          <button onclick="actionLike()" class="py-2.5 rounded-xl bg-rose-600/80 hover:bg-rose-500 text-white font-medium text-xs transition">
            <i class="fa-solid fa-heart mr-1"></i> Like
          </button>
          <button onclick="actionUnlike()" class="py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs transition border border-slate-700">
            <i class="fa-regular fa-heart mr-1"></i> Unlike
          </button>
          <button onclick="actionRetweet()" class="py-2.5 rounded-xl bg-emerald-600/80 hover:bg-emerald-500 text-white font-medium text-xs transition">
            <i class="fa-solid fa-repeat mr-1"></i> Retweet
          </button>
        </div>
      </div>

      <!-- Tab 4: Follow / Unfollow -->
      <div id="tab-follow" class="tab-pane hidden glass rounded-2xl p-6 space-y-4">
        <h2 class="text-base font-semibold text-white">Follow or Unfollow Profiles</h2>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Twitter Username / Handle:</label>
          <input type="text" id="followUser" placeholder="elonmusk or @elonmusk"
            class="w-full bg-slate-900/80 border border-slate-700 rounded-xl p-2.5 text-sm text-slate-100 focus:outline-none focus:border-sky-500"/>
        </div>
        <div class="grid grid-cols-2 gap-4 pt-2">
          <button onclick="actionFollow()" class="py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-medium text-sm transition">
            <i class="fa-solid fa-user-plus mr-1"></i> Follow
          </button>
          <button onclick="actionUnfollow()" class="py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-sm transition border border-slate-700">
            <i class="fa-solid fa-user-minus mr-1"></i> Unfollow
          </button>
        </div>
      </div>

      <!-- Tab 5: Auto-Engage Search -->
      <div id="tab-search" class="tab-pane hidden glass rounded-2xl p-6 space-y-4">
        <h2 class="text-base font-semibold text-white">Live Search & Auto-Engagement</h2>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Search Query or Hashtag:</label>
          <input type="text" id="searchQuery" placeholder="#buildinpublic or AI agents"
            class="w-full bg-slate-900/80 border border-slate-700 rounded-xl p-2.5 text-sm text-slate-100 focus:outline-none focus:border-sky-500"/>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-slate-400 mb-1">Max Tweets:</label>
            <input type="number" id="searchCount" value="3" min="1" max="10"
              class="w-full bg-slate-900/80 border border-slate-700 rounded-xl p-2 text-sm text-slate-100"/>
          </div>
          <div class="flex items-center pt-6 space-x-2">
            <input type="checkbox" id="searchLike" checked class="w-4 h-4 rounded text-sky-500 bg-slate-900 border-slate-700"/>
            <label class="text-xs text-slate-300">Auto-Like each tweet</label>
          </div>
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Optional Reply Template:</label>
          <input type="text" id="searchComment" placeholder="Interesting post! Keep it up."
            class="w-full bg-slate-900/80 border border-slate-700 rounded-xl p-2.5 text-sm text-slate-100 focus:outline-none focus:border-sky-500"/>
        </div>
        <button onclick="submitEngage()" class="w-full py-2.5 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-medium text-sm transition">
          <i class="fa-solid fa-bolt mr-1"></i> Launch Auto-Engagement
        </button>
      </div>

      <!-- Tab 6: Queue Manager -->
      <div id="tab-queue" class="tab-pane hidden glass rounded-2xl p-6 space-y-4">
        <div class="flex justify-between items-center">
          <h2 class="text-base font-semibold text-white">Action Queue</h2>
          <div class="space-x-2">
            <button onclick="loadQueue()" class="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-300">
              <i class="fa-solid fa-rotate-right"></i> Refresh
            </button>
            <button onclick="runQueue()" class="text-xs px-3 py-1 rounded bg-emerald-600 text-white font-medium">
              <i class="fa-solid fa-play mr-1"></i> Run Queue
            </button>
          </div>
        </div>
        <div id="queueTableContainer" class="overflow-x-auto text-xs">
          <!-- Populated dynamically -->
        </div>
        
        <!-- Add Task to Queue Form -->
        <div class="border-t border-slate-800 pt-4 space-y-3">
          <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Add Task to Queue</h3>
          <div class="grid grid-cols-3 gap-2">
            <select id="queueAction" class="bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-slate-100">
              <option value="post">Post</option>
              <option value="like">Like</option>
              <option value="retweet">Retweet</option>
              <option value="follow">Follow</option>
            </select>
            <input type="text" id="queueValue" placeholder="Content, URL, or @user" class="col-span-2 bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-slate-100"/>
          </div>
          <button onclick="addToQueue()" class="w-full py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition">
            + Add to Queue
          </button>
        </div>
      </div>

    </div>

    <!-- Right Column: Live Logs & Telemetry -->
    <div class="space-y-6">
      <div class="glass rounded-2xl p-6 flex flex-col h-[560px]">
        <div class="flex justify-between items-center pb-3 border-b border-slate-800">
          <h2 class="text-sm font-semibold text-white flex items-center space-x-2">
            <i class="fa-solid fa-terminal text-sky-400"></i>
            <span>Live Activity Console</span>
          </h2>
          <button onclick="fetchLogs()" class="text-xs text-slate-400 hover:text-white">
            <i class="fa-solid fa-sync"></i>
          </button>
        </div>
        <div id="logConsole" class="flex-1 overflow-y-auto space-y-2.5 pt-3 font-mono text-xs">
          <div class="text-slate-500 italic">Waiting for actions...</div>
        </div>
      </div>
    </div>

  </main>

  <script>
    function switchTab(tabId) {
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.add('hidden'));
      document.getElementById(tabId).classList.remove('hidden');

      document.querySelectorAll('[id^="nav-tab-"]').forEach(btn => {
        btn.classList.remove('tab-active');
      });
      document.getElementById('nav-' + tabId).classList.add('tab-active');
    }

    function updateCharCount(el) {
      document.getElementById('charCount').innerText = `${el.value.length} / 280`;
    }

    async function checkAuth() {
      const badge = document.getElementById('authBadge');
      badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></span><span>Checking...</span>`;
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.logged_in) {
          badge.className = "flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-700";
          badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400"></span><span>Authenticated</span>`;
        } else {
          badge.className = "flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-rose-950/80 text-rose-300 border border-rose-800";
          badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-rose-500"></span><span>Not Logged In</span>`;
        }
      } catch (e) {
        badge.innerHTML = `<span class="text-rose-400">Check failed</span>`;
      }
    }

    async function triggerLogin() {
      alert("Opening interactive login window on your host browser. Please sign into X and the session will be saved!");
      await fetch('/api/login', { method: 'POST' });
      fetchLogs();
    }

    async function submitPost() {
      const text = document.getElementById('postText').value.trim();
      if (!text) return alert("Please enter tweet text.");
      const formData = new FormData();
      formData.append('text', text);
      const files = document.getElementById('postFiles').files;
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }
      const res = await fetch('/api/post', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.success) {
        alert("Tweet posted successfully!");
        document.getElementById('postText').value = '';
      } else {
        alert("Failed to post: " + data.error);
      }
      fetchLogs();
    }

    async function submitReply() {
      const url = document.getElementById('replyUrl').value.trim();
      const text = document.getElementById('replyText').value.trim();
      if (!url || !text) return alert("URL and reply text are required.");
      const formData = new FormData();
      formData.append('url', url);
      formData.append('text', text);
      const res = await fetch('/api/reply', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.success) alert("Reply published successfully!");
      else alert("Error replying: " + data.error);
      fetchLogs();
    }

    async function actionLike() {
      const url = document.getElementById('engageUrl').value.trim();
      if (!url) return alert("Please enter tweet URL.");
      const formData = new FormData();
      formData.append('url', url);
      const res = await fetch('/api/like', { method: 'POST', body: formData });
      const data = await res.json();
      alert("Like result: " + JSON.stringify(data.result));
      fetchLogs();
    }

    async function actionUnlike() {
      const url = document.getElementById('engageUrl').value.trim();
      if (!url) return alert("Please enter tweet URL.");
      const formData = new FormData();
      formData.append('url', url);
      const res = await fetch('/api/unlike', { method: 'POST', body: formData });
      const data = await res.json();
      alert("Unlike result: " + JSON.stringify(data.result));
      fetchLogs();
    }

    async function actionRetweet() {
      const url = document.getElementById('engageUrl').value.trim();
      if (!url) return alert("Please enter tweet URL.");
      const formData = new FormData();
      formData.append('url', url);
      const res = await fetch('/api/retweet', { method: 'POST', body: formData });
      const data = await res.json();
      alert("Retweet result: " + JSON.stringify(data.result));
      fetchLogs();
    }

    async function actionFollow() {
      const user = document.getElementById('followUser').value.trim();
      if (!user) return alert("Please enter username.");
      const formData = new FormData();
      formData.append('user', user);
      const res = await fetch('/api/follow', { method: 'POST', body: formData });
      const data = await res.json();
      alert("Follow result: " + JSON.stringify(data.result));
      fetchLogs();
    }

    async function actionUnfollow() {
      const user = document.getElementById('followUser').value.trim();
      if (!user) return alert("Please enter username.");
      const formData = new FormData();
      formData.append('user', user);
      const res = await fetch('/api/unfollow', { method: 'POST', body: formData });
      const data = await res.json();
      alert("Unfollow result: " + JSON.stringify(data.result));
      fetchLogs();
    }

    async function submitEngage() {
      const query = document.getElementById('searchQuery').value.trim();
      const count = document.getElementById('searchCount').value;
      const like = document.getElementById('searchLike').checked;
      const comment = document.getElementById('searchComment').value.trim();
      if (!query) return alert("Please enter search query.");
      const formData = new FormData();
      formData.append('query', query);
      formData.append('count', count);
      formData.append('like', like);
      if (comment) formData.append('comment', comment);
      await fetch('/api/engage', { method: 'POST', body: formData });
      alert("Auto-engagement triggered! Check Live Activity Console for progress.");
      fetchLogs();
    }

    async function loadQueue() {
      const res = await fetch('/api/queue');
      const data = await res.json();
      const container = document.getElementById('queueTableContainer');
      if (!data.items || data.items.length === 0) {
        container.innerHTML = '<p class="text-slate-500 py-2">Queue is empty.</p>';
        return;
      }
      let html = '<table class="w-full text-left border-collapse"><tr class="border-b border-slate-800 text-slate-400 font-semibold"><th class="py-2">Action</th><th>Details</th><th>Status</th></tr>';
      data.items.forEach(it => {
        html += `<tr class="border-b border-slate-800/50">
          <td class="py-2 uppercase font-mono text-sky-400 font-bold">${it.action}</td>
          <td class="text-slate-300 truncate max-w-[200px]">${it.text || it.url || it.user || '-'}</td>
          <td><span class="px-2 py-0.5 rounded text-[10px] ${it.status === 'completed' ? 'bg-emerald-900/60 text-emerald-300' : 'bg-slate-800 text-slate-300'}">${it.status}</span></td>
        </tr>`;
      });
      html += '</table>';
      container.innerHTML = html;
    }

    async function addToQueue() {
      const action = document.getElementById('queueAction').value;
      const val = document.getElementById('queueValue').value.trim();
      if (!val) return alert("Please enter value.");
      const formData = new FormData();
      formData.append('action', action);
      if (action === 'post') formData.append('text', val);
      else if (action === 'like' || action === 'retweet') formData.append('url', val);
      else if (action === 'follow') formData.append('user', val);

      await fetch('/api/queue/add', { method: 'POST', body: formData });
      document.getElementById('queueValue').value = '';
      loadQueue();
      fetchLogs();
    }

    async function runQueue() {
      if (!confirm("Run pending actions in queue?")) return;
      const formData = new FormData();
      formData.append('min_mins', 2.0);
      formData.append('max_mins', 5.0);
      await fetch('/api/queue/run', { method: 'POST', body: formData });
      alert("Queue execution running in background!");
      fetchLogs();
    }

    async function fetchLogs() {
      try {
        const res = await fetch('/api/logs');
        const data = await res.json();
        const el = document.getElementById('logConsole');
        if (!data.logs || data.logs.length === 0) {
          el.innerHTML = '<div class="text-slate-500 italic">No activity recorded yet.</div>';
          return;
        }
        el.innerHTML = data.logs.map(l => `
          <div class="p-2 rounded bg-slate-900/60 border border-slate-800 flex flex-col space-y-1">
            <div class="flex justify-between items-center">
              <span class="font-bold text-sky-400">[${l.action}]</span>
              <span class="text-[10px] text-slate-500">${l.time}</span>
            </div>
            <div class="text-slate-300 text-xs">${l.details}</div>
          </div>
        `).join('');
      } catch (e) {}
    }

    // Auto refresh logs every 3 seconds
    setInterval(fetchLogs, 3000);
    // Initial check on load
    window.onload = () => {
      checkAuth();
      loadQueue();
      fetchLogs();
    };
  </script>
</body>
</html>
"""
