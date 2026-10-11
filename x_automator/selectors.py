"""
Centralized DOM selectors for X.com (Twitter).
X consistently uses data-testid attributes across its web interface.
"""

class Selectors:
    # Navigation & Auth verification
    ACCOUNT_SWITCHER = '[data-testid="SideNav_AccountSwitcher_Button"]'
    LOGIN_BUTTON = '[data-testid="loginButton"]'
    PRIMARY_COLUMN = '[data-testid="primaryColumn"]'

    # Tweet / Compose
    TWEET_TEXTAREA = '[data-testid="tweetTextarea_0"]'
    TWEET_BUTTON_INLINE = '[data-testid="tweetButtonInline"]'
    TWEET_BUTTON_MODAL = '[data-testid="tweetButton"]'
    MEDIA_INPUT = 'input[data-testid="fileInput"]'
    ATTACHMENTS_CONTAINER = '[data-testid="attachments"]'
    COMPOSE_BAR = '[data-testid="toolBar"]'

    # Tweet Actions (on individual tweet cards or tweet details page)
    TWEET_ARTICLE = 'article[data-testid="tweet"]'
    TWEET_TEXT = '[data-testid="tweetText"]'
    USER_NAME = '[data-testid="User-Name"]'

    LIKE_BUTTON = 'button[data-testid="like"]'
    UNLIKE_BUTTON = 'button[data-testid="unlike"]'

    RETWEET_BUTTON = 'button[data-testid="retweet"]'
    UNRETWEET_BUTTON = 'button[data-testid="unretweet"]'
    RETWEET_CONFIRM = '[data-testid="retweetConfirm"]'
    UNRETWEET_CONFIRM = '[data-testid="unretweetConfirm"]'

    REPLY_BUTTON = 'button[data-testid="reply"]'
    BOOKMARK_BUTTON = 'button[data-testid="bookmark"]'
    REMOVE_BOOKMARK_BUTTON = 'button[data-testid="removeBookmark"]'

    # Profile & Following
    # Selectors for follow buttons: often end with '-follow' like '12345-follow'
    FOLLOW_BUTTON = 'button[data-testid$="-follow"]'
    UNFOLLOW_BUTTON = 'button[data-testid$="-unfollow"]'
    CONFIRM_UNFOLLOW_BUTTON = 'button[data-testid="confirmationSheetConfirm"]'
    USER_AVATAR = '[data-testid="UserAvatar"]'

    # Search & Feed
    SEARCH_INPUT = 'input[data-testid="SearchBox_Search_Input"]'
    EMPTY_TIMELINE = '[data-testid="emptyState"]'
