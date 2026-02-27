import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
_owner_ids_raw = os.getenv("OWNER_IDS", "1222608506516144158")
OWNER_IDS = [int(x.strip()) for x in _owner_ids_raw.split(",") if x.strip()]
OWNER_ID = OWNER_IDS[0]  # Primary owner (backward compatibility)
PREFIX = "!"

EMBED_COLOR = 0x5865F2
SUCCESS_COLOR = 0x57F287
ERROR_COLOR = 0xED4245
WARNING_COLOR = 0xFEE75C
INVITE_COLOR = 0x2EAADC
AUTOMOD_COLOR = 0xFF6B35
PANEL_COLOR = 0x2B2D31
TICKET_COLOR = 0xEB459E
UTILITY_COLOR = 0x5865F2
ORDER_COLOR = 0xF1C40F
PRODUCT_COLOR = 0xE91E63
DELIVERED_COLOR = 0x2ECC71
OWNER_COLOR = 0xFF0000
LOG_COLOR = 0x2F3136

# Official server changelog channel name
CHANGELOG_CHANNEL = "📝・changelog"

# ═══════════════════════════════════════════════════════════════
#  SUBSCRIPTION PLANS
# ═══════════════════════════════════════════════════════════════

PLANS = {
    "free": {
        "name": "Free",
        "emoji": "🆓",
        "price": 0,
        "color": 0x95A5A6,
        "limits": {
            "max_products": 3,
            "max_active_giveaways": 1,
            "max_ticket_categories": 1,
            "max_open_tickets": 2,
            "shop_enabled": False,
            "reviews_enabled": False,
            "farm_enabled": False,
            "automod_full": False,
            "automod_anti_spam": True,
            "automod_anti_invite": False,
            "automod_anti_link": False,
            "automod_bad_words": False,
            "automod_warns": False,
            "invite_leaderboard": False,
            "invite_tracking": True,
            "transcript_enabled": False,
            "utility_full": False,
            "multi_server": 1,
            "logging_enabled": False,
            "log_messages": False,
            "log_members": True,
            "log_roles": False,
            "log_channels": False,
            "log_bans": False,
            "log_voice": False,
            "auto_role": False,
            "embed_editor": False,
            "bot_nickname": False,
            "bot_avatar": False,
        }
    },
    "basic": {
        "name": "Basic",
        "emoji": "💎",
        "price": 8,
        "color": 0x3498DB,
        "limits": {
            "max_products": 5,
            "max_active_giveaways": 3,
            "max_ticket_categories": 3,
            "max_open_tickets": 5,
            "shop_enabled": True,
            "reviews_enabled": False,
            "farm_enabled": False,
            "automod_full": False,
            "automod_anti_spam": True,
            "automod_anti_invite": True,
            "automod_anti_link": True,
            "automod_bad_words": True,
            "automod_warns": True,
            "invite_leaderboard": True,
            "invite_tracking": True,
            "transcript_enabled": False,
            "utility_full": True,
            "multi_server": 1,
            "logging_enabled": True,
            "log_messages": True,
            "log_members": True,
            "log_roles": False,
            "log_channels": False,
            "log_bans": True,
            "log_voice": False,
            "auto_role": True,
            "embed_editor": True,
            "bot_nickname": False,
            "bot_avatar": False,
        }
    },
    "premium": {
        "name": "Premium",
        "emoji": "⭐",
        "price": 15,
        "color": 0xF1C40F,
        "limits": {
            "max_products": 999,
            "max_active_giveaways": 999,
            "max_ticket_categories": 999,
            "max_open_tickets": 999,
            "shop_enabled": True,
            "reviews_enabled": True,
            "farm_enabled": True,
            "automod_full": True,
            "automod_anti_spam": True,
            "automod_anti_invite": True,
            "automod_anti_link": True,
            "automod_bad_words": True,
            "automod_warns": True,
            "invite_leaderboard": True,
            "invite_tracking": True,
            "transcript_enabled": True,
            "utility_full": True,
            "multi_server": 1,
            "logging_enabled": True,
            "log_messages": True,
            "log_members": True,
            "log_roles": True,
            "log_channels": True,
            "log_bans": True,
            "log_voice": True,
            "auto_role": True,
            "embed_editor": True,
            "bot_nickname": True,
            "bot_avatar": False,
        }
    },
    "business": {
        "name": "Business",
        "emoji": "🚀",
        "price": 25,
        "color": 0xE91E63,
        "limits": {
            "max_products": 999,
            "max_active_giveaways": 999,
            "max_ticket_categories": 999,
            "max_open_tickets": 999,
            "shop_enabled": True,
            "reviews_enabled": True,
            "farm_enabled": True,
            "automod_full": True,
            "automod_anti_spam": True,
            "automod_anti_invite": True,
            "automod_anti_link": True,
            "automod_bad_words": True,
            "automod_warns": True,
            "invite_leaderboard": True,
            "invite_tracking": True,
            "transcript_enabled": True,
            "utility_full": True,
            "multi_server": 3,
            "logging_enabled": True,
            "log_messages": True,
            "log_members": True,
            "log_roles": True,
            "log_channels": True,
            "log_bans": True,
            "log_voice": True,
            "auto_role": True,
            "embed_editor": True,
            "bot_nickname": True,
            "bot_avatar": True,
        }
    }
}


def get_plan_limits(plan_name):
    """Get limits for a plan."""
    plan = PLANS.get(plan_name, PLANS["free"])
    return plan["limits"]


def get_plan_info(plan_name):
    """Get full plan info."""
    return PLANS.get(plan_name, PLANS["free"])