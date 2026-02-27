import aiosqlite
import os
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nexify.db")


# ═══════════════════════════════════════════════════════════════
#  DATABASE INITIALIZATION
# ═══════════════════════════════════════════════════════════════

async def init_db():
    """Initialize the database and create all tables."""
    async with aiosqlite.connect(DB_PATH) as db:

        # ─── Giveaway Tables ────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL UNIQUE,
                host_id INTEGER NOT NULL,
                prize TEXT NOT NULL,
                description TEXT DEFAULT '',
                winner_count INTEGER NOT NULL DEFAULT 1,
                required_role_id INTEGER DEFAULT NULL,
                end_time TEXT NOT NULL,
                ended INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                giveaway_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                entered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (giveaway_id) REFERENCES giveaways(id) ON DELETE CASCADE,
                UNIQUE(giveaway_id, user_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                giveaway_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                selected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (giveaway_id) REFERENCES giveaways(id) ON DELETE CASCADE
            )
        """)

        # ─── Invite Tables ──────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invite_settings (
                guild_id INTEGER PRIMARY KEY,
                log_channel_id INTEGER DEFAULT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS invite_cache (
                guild_id INTEGER NOT NULL,
                invite_code TEXT NOT NULL,
                inviter_id INTEGER NOT NULL,
                uses INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, invite_code)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS invite_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                inviter_id INTEGER NOT NULL,
                invited_id INTEGER NOT NULL,
                invite_code TEXT NOT NULL,
                joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS invite_leaves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                inviter_id INTEGER NOT NULL,
                left_id INTEGER NOT NULL,
                left_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ─── AutoMod Tables ─────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS automod_settings (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0,
                log_channel_id INTEGER DEFAULT NULL,
                anti_spam INTEGER NOT NULL DEFAULT 1,
                spam_threshold INTEGER NOT NULL DEFAULT 5,
                spam_interval INTEGER NOT NULL DEFAULT 5,
                anti_caps INTEGER NOT NULL DEFAULT 1,
                caps_percentage INTEGER NOT NULL DEFAULT 70,
                caps_min_length INTEGER NOT NULL DEFAULT 10,
                anti_mention_spam INTEGER NOT NULL DEFAULT 1,
                max_mentions INTEGER NOT NULL DEFAULT 5,
                anti_emoji_spam INTEGER NOT NULL DEFAULT 1,
                max_emojis INTEGER NOT NULL DEFAULT 10,
                anti_newline_spam INTEGER NOT NULL DEFAULT 1,
                max_lines INTEGER NOT NULL DEFAULT 30,
                anti_invite INTEGER NOT NULL DEFAULT 1,
                anti_link INTEGER NOT NULL DEFAULT 0,
                max_links INTEGER NOT NULL DEFAULT 3,
                anti_zalgo INTEGER NOT NULL DEFAULT 1,
                anti_massping INTEGER NOT NULL DEFAULT 1,
                bad_words_enabled INTEGER NOT NULL DEFAULT 1,
                blocked_links_enabled INTEGER NOT NULL DEFAULT 1,
                warn_expire_days INTEGER NOT NULL DEFAULT 30,
                max_warns INTEGER NOT NULL DEFAULT 3,
                warn_action TEXT NOT NULL DEFAULT 'mute',
                warn_action_duration INTEGER NOT NULL DEFAULT 600,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS automod_whitelist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                added_by INTEGER NOT NULL,
                added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, type, target_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS automod_bad_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                added_by INTEGER NOT NULL,
                added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, word)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS automod_blocked_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                domain TEXT NOT NULL,
                added_by INTEGER NOT NULL,
                added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, domain)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS automod_warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS automod_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                details TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ─── Ticket Tables ──────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_settings (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0,
                category_id INTEGER DEFAULT NULL,
                log_channel_id INTEGER DEFAULT NULL,
                support_role_id INTEGER DEFAULT NULL,
                panel_channel_id INTEGER DEFAULT NULL,
                panel_message_id INTEGER DEFAULT NULL,
                max_open_tickets INTEGER NOT NULL DEFAULT 1,
                ticket_counter INTEGER NOT NULL DEFAULT 0,
                welcome_message TEXT DEFAULT 'Thank you for creating a ticket! A staff member will be with you shortly.',
                close_confirmation INTEGER NOT NULL DEFAULT 1,
                transcript_on_close INTEGER NOT NULL DEFAULT 1,
                auto_close_hours INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                emoji TEXT DEFAULT '🎫',
                description TEXT DEFAULT '',
                category_id INTEGER DEFAULT NULL,
                support_role_id INTEGER DEFAULT NULL,
                welcome_message TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                category_name TEXT DEFAULT 'General',
                ticket_number INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                claimed_by INTEGER DEFAULT NULL,
                priority TEXT DEFAULT 'normal',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                closed_at TEXT DEFAULT NULL,
                closed_by INTEGER DEFAULT NULL,
                close_reason TEXT DEFAULT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
            )
        """)

        # ─── Order System Tables ─────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shop_settings (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0,
                order_channel_id INTEGER DEFAULT NULL,
                log_channel_id INTEGER DEFAULT NULL,
                review_channel_id INTEGER DEFAULT NULL,
                review_channel_name TEXT NOT NULL DEFAULT 'reviews',
                delivery_category_id INTEGER DEFAULT NULL,
                staff_role_id INTEGER DEFAULT NULL,
                customer_role_id INTEGER DEFAULT NULL,
                panel_channel_id INTEGER DEFAULT NULL,
                panel_message_id INTEGER DEFAULT NULL,
                order_counter INTEGER NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT '$',
                payment_methods TEXT NOT NULL DEFAULT '<:Crypto:1476080247853289614> Crypto; (Litecoin, Eth, Bitcoin)
<a:Paypal:1476080377851281471> PayPal; (Only <@1222941764143284258>)
<:Ccdbc:1476080108061069417> Steal a Brainrot; (High-Tier Secrets Only)
<:rrrrrrrrrrrrrrrrrr:1475838133676281918> Gift-Cards; (Roblox Or Crypto GiftCards)',
                auto_customer_role INTEGER NOT NULL DEFAULT 1,
                hide_product_list INTEGER NOT NULL DEFAULT 0,
                shop_info_message TEXT NOT NULL DEFAULT 'Click **🛒 Order Now** to browse and purchase our products!',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                price REAL NOT NULL DEFAULT 0.0,
                reseller_price REAL DEFAULT NULL,
                emoji TEXT DEFAULT '🛒',
                category TEXT DEFAULT 'General',
                in_stock INTEGER NOT NULL DEFAULT 1,
                stock_count INTEGER DEFAULT NULL,
                delivery_time TEXT DEFAULT '5M-2H',
                image_url TEXT DEFAULT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                order_number INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                price REAL NOT NULL,
                payment_method TEXT DEFAULT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                channel_id INTEGER DEFAULT NULL,
                staff_id INTEGER DEFAULT NULL,
                delivery_info TEXT DEFAULT NULL,
                notes TEXT DEFAULT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT DEFAULT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS order_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                order_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT DEFAULT '',
                review_message_id INTEGER DEFAULT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                UNIQUE(order_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS staff_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS customer_profiles (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                total_orders INTEGER NOT NULL DEFAULT 0,
                total_spent REAL NOT NULL DEFAULT 0.0,
                completed_orders INTEGER NOT NULL DEFAULT 0,
                avg_rating REAL DEFAULT NULL,
                blacklisted INTEGER NOT NULL DEFAULT 0,
                blacklist_reason TEXT DEFAULT NULL,
                first_order_at TEXT DEFAULT NULL,
                last_order_at TEXT DEFAULT NULL,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        # ─── Logging Settings Table ──────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logging_settings (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0,
                log_channel_id INTEGER DEFAULT NULL,
                log_messages INTEGER NOT NULL DEFAULT 1,
                log_members INTEGER NOT NULL DEFAULT 1,
                log_roles INTEGER NOT NULL DEFAULT 1,
                log_channels INTEGER NOT NULL DEFAULT 1,
                log_bans INTEGER NOT NULL DEFAULT 1,
                log_voice INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ─── Auto Role Table ─────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS auto_roles (
                guild_id INTEGER PRIMARY KEY,
                role_id INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ─── Bot Customization Table ─────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_customization (
                guild_id INTEGER PRIMARY KEY,
                custom_nickname TEXT DEFAULT NULL,
                custom_avatar_url TEXT DEFAULT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ─── License Keys Table ──────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS license_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                plan TEXT NOT NULL,
                duration_days INTEGER NOT NULL DEFAULT 30,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                redeemed INTEGER NOT NULL DEFAULT 0,
                redeemed_by INTEGER DEFAULT NULL,
                redeemed_guild_id INTEGER DEFAULT NULL,
                redeemed_at TEXT DEFAULT NULL,
                notes TEXT DEFAULT ''
            )
        """)

        # ─── Subscription Tables ─────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                guild_id INTEGER PRIMARY KEY,
                plan TEXT NOT NULL DEFAULT 'free',
                activated_by INTEGER DEFAULT NULL,
                activated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT DEFAULT NULL,
                auto_renew INTEGER NOT NULL DEFAULT 0,
                notes TEXT DEFAULT '',
                total_paid REAL NOT NULL DEFAULT 0.0,
                payment_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscription_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                old_plan TEXT DEFAULT NULL,
                new_plan TEXT DEFAULT NULL,
                duration_days INTEGER DEFAULT NULL,
                amount REAL DEFAULT 0.0,
                performed_by INTEGER NOT NULL,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()
    print("[DATABASE] Initialized successfully.")


# ═══════════════════════════════════════════════════════════════
#  GIVEAWAY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def create_giveaway(guild_id, channel_id, message_id, host_id, prize,
                          description, winner_count, required_role_id, end_time):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "INSERT INTO giveaways (guild_id, channel_id, message_id, host_id, prize, "
            "description, winner_count, required_role_id, end_time) VALUES (?,?,?,?,?,?,?,?,?)",
            (guild_id, channel_id, message_id, host_id, prize,
             description, winner_count, required_role_id, end_time)
        )
        await db.commit()
        return c.lastrowid


async def add_entry(giveaway_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO giveaway_entries (giveaway_id, user_id) VALUES (?,?)",
                (giveaway_id, user_id)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_entry(giveaway_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "DELETE FROM giveaway_entries WHERE giveaway_id=? AND user_id=?",
            (giveaway_id, user_id)
        )
        await db.commit()
        return c.rowcount > 0


async def get_entry_count(giveaway_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "SELECT COUNT(*) FROM giveaway_entries WHERE giveaway_id=?",
            (giveaway_id,)
        )
        return (await c.fetchone())[0]


async def get_entries(giveaway_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "SELECT user_id FROM giveaway_entries WHERE giveaway_id=?",
            (giveaway_id,)
        )
        return [r[0] for r in await c.fetchall()]


async def get_giveaway_by_message(message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM giveaways WHERE message_id=?", (message_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def get_giveaway_by_id(giveaway_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM giveaways WHERE id=?", (giveaway_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def get_active_giveaways():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM giveaways WHERE ended=0")
        return [dict(r) for r in await c.fetchall()]


async def get_guild_giveaways(guild_id, active_only=True):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if active_only:
            c = await db.execute(
                "SELECT * FROM giveaways WHERE guild_id=? AND ended=0 ORDER BY end_time ASC",
                (guild_id,)
            )
        else:
            c = await db.execute(
                "SELECT * FROM giveaways WHERE guild_id=? ORDER BY created_at DESC LIMIT 25",
                (guild_id,)
            )
        return [dict(r) for r in await c.fetchall()]


async def end_giveaway(giveaway_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE giveaways SET ended=1 WHERE id=?", (giveaway_id,))
        await db.commit()


async def save_winners(giveaway_id, winner_ids):
    async with aiosqlite.connect(DB_PATH) as db:
        for uid in winner_ids:
            await db.execute(
                "INSERT INTO giveaway_winners (giveaway_id, user_id) VALUES (?,?)",
                (giveaway_id, uid)
            )
        await db.commit()


async def get_winners(giveaway_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "SELECT user_id FROM giveaway_winners WHERE giveaway_id=?",
            (giveaway_id,)
        )
        return [r[0] for r in await c.fetchall()]


async def delete_giveaway(giveaway_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM giveaway_entries WHERE giveaway_id=?", (giveaway_id,))
        await db.execute("DELETE FROM giveaway_winners WHERE giveaway_id=?", (giveaway_id,))
        await db.execute("DELETE FROM giveaways WHERE id=?", (giveaway_id,))
        await db.commit()


async def has_entry(giveaway_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "SELECT 1 FROM giveaway_entries WHERE giveaway_id=? AND user_id=?",
            (giveaway_id, user_id)
        )
        return (await c.fetchone()) is not None


# ═══════════════════════════════════════════════════════════════
#  INVITE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def set_invite_log_channel(guild_id, channel_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO invite_settings (guild_id, log_channel_id, enabled) VALUES (?,?,1) "
            "ON CONFLICT(guild_id) DO UPDATE SET log_channel_id=excluded.log_channel_id, "
            "updated_at=CURRENT_TIMESTAMP",
            (guild_id, channel_id)
        )
        await db.commit()


async def get_invite_settings(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM invite_settings WHERE guild_id=?", (guild_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def toggle_invite_tracking(guild_id, enabled):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO invite_settings (guild_id, enabled) VALUES (?,?) "
            "ON CONFLICT(guild_id) DO UPDATE SET enabled=excluded.enabled, "
            "updated_at=CURRENT_TIMESTAMP",
            (guild_id, int(enabled))
        )
        await db.commit()


async def remove_invite_log_channel(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE invite_settings SET log_channel_id=NULL WHERE guild_id=?",
            (guild_id,)
        )
        await db.commit()


async def cache_invites(guild_id, invites):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM invite_cache WHERE guild_id=?", (guild_id,))
        for inv in invites:
            await db.execute(
                "INSERT INTO invite_cache (guild_id, invite_code, inviter_id, uses) VALUES (?,?,?,?)",
                (guild_id, inv["code"], inv["inviter_id"], inv["uses"])
            )
        await db.commit()


async def get_cached_invites(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM invite_cache WHERE guild_id=?", (guild_id,))
        return [dict(r) for r in await c.fetchall()]


async def track_invite(guild_id, inviter_id, invited_id, invite_code):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO invite_tracks (guild_id, inviter_id, invited_id, invite_code) VALUES (?,?,?,?)",
            (guild_id, inviter_id, invited_id, invite_code)
        )
        await db.commit()


async def track_leave(guild_id, left_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "SELECT inviter_id FROM invite_tracks WHERE guild_id=? AND invited_id=? "
            "ORDER BY joined_at DESC LIMIT 1",
            (guild_id, left_id)
        )
        r = await c.fetchone()
        if r:
            inviter_id = r[0]
            await db.execute(
                "INSERT INTO invite_leaves (guild_id, inviter_id, left_id) VALUES (?,?,?)",
                (guild_id, inviter_id, left_id)
            )
            await db.commit()
            return inviter_id
        return None


async def get_user_invite_stats(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "SELECT COUNT(*) FROM invite_tracks WHERE guild_id=? AND inviter_id=?",
            (guild_id, user_id)
        )
        total = (await c.fetchone())[0]
        c = await db.execute(
            "SELECT COUNT(*) FROM invite_leaves WHERE guild_id=? AND inviter_id=?",
            (guild_id, user_id)
        )
        leaves = (await c.fetchone())[0]
        return {"total": total, "leaves": leaves, "active": max(0, total - leaves)}


async def get_invited_by(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "SELECT inviter_id FROM invite_tracks WHERE guild_id=? AND invited_id=? "
            "ORDER BY joined_at DESC LIMIT 1",
            (guild_id, user_id)
        )
        r = await c.fetchone()
        return r[0] if r else None


async def get_invite_list(guild_id, inviter_id, limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("""
            SELECT t.invited_id, t.invite_code, t.joined_at,
                   CASE WHEN l.left_id IS NOT NULL THEN 1 ELSE 0 END as has_left
            FROM invite_tracks t
            LEFT JOIN invite_leaves l
                ON t.guild_id = l.guild_id
                AND t.invited_id = l.left_id
                AND t.inviter_id = l.inviter_id
            WHERE t.guild_id=? AND t.inviter_id=?
            ORDER BY t.joined_at DESC LIMIT ?
        """, (guild_id, inviter_id, limit))
        return [dict(r) for r in await c.fetchall()]


async def get_invite_leaderboard(guild_id, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("""
            SELECT t.inviter_id, COUNT(t.id) as total, COUNT(l.id) as leaves
            FROM invite_tracks t
            LEFT JOIN invite_leaves l
                ON t.guild_id = l.guild_id
                AND t.invited_id = l.left_id
                AND t.inviter_id = l.inviter_id
            WHERE t.guild_id=?
            GROUP BY t.inviter_id
            ORDER BY (COUNT(t.id) - COUNT(l.id)) DESC
            LIMIT ?
        """, (guild_id, limit))
        return [
            {"inviter_id": r[0], "total": r[1], "leaves": r[2], "active": max(0, r[1] - r[2])}
            for r in await c.fetchall()
        ]


async def reset_user_invites(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM invite_tracks WHERE guild_id=? AND inviter_id=?", (guild_id, user_id))
        await db.execute("DELETE FROM invite_leaves WHERE guild_id=? AND inviter_id=?", (guild_id, user_id))
        await db.commit()


async def reset_all_invites(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM invite_tracks WHERE guild_id=?", (guild_id,))
        await db.execute("DELETE FROM invite_leaves WHERE guild_id=?", (guild_id,))
        await db.execute("DELETE FROM invite_cache WHERE guild_id=?", (guild_id,))
        await db.commit()


# ═══════════════════════════════════════════════════════════════
#  AUTOMOD FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def get_automod_settings(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM automod_settings WHERE guild_id=?", (guild_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def create_automod_settings(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO automod_settings (guild_id) VALUES (?)", (guild_id,))
        await db.commit()
    return await get_automod_settings(guild_id)


async def update_automod_setting(guild_id, key, value):
    valid = [
        "enabled", "log_channel_id",
        "anti_spam", "spam_threshold", "spam_interval",
        "anti_caps", "caps_percentage", "caps_min_length",
        "anti_mention_spam", "max_mentions",
        "anti_emoji_spam", "max_emojis",
        "anti_newline_spam", "max_lines",
        "anti_invite", "anti_link", "max_links",
        "anti_zalgo", "anti_massping",
        "bad_words_enabled", "blocked_links_enabled",
        "warn_expire_days", "max_warns",
        "warn_action", "warn_action_duration"
    ]
    if key not in valid:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"INSERT INTO automod_settings (guild_id, {key}) VALUES (?, ?) "
            f"ON CONFLICT(guild_id) DO UPDATE SET {key}=excluded.{key}, "
            f"updated_at=CURRENT_TIMESTAMP",
            (guild_id, value)
        )
        await db.commit()
    return True


async def add_whitelist(guild_id, wl_type, target_id, added_by):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO automod_whitelist (guild_id, type, target_id, added_by) VALUES (?,?,?,?)",
                (guild_id, wl_type, target_id, added_by)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_whitelist(guild_id, wl_type, target_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "DELETE FROM automod_whitelist WHERE guild_id=? AND type=? AND target_id=?",
            (guild_id, wl_type, target_id)
        )
        await db.commit()
        return c.rowcount > 0


async def get_whitelist(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM automod_whitelist WHERE guild_id=?", (guild_id,))
        return [dict(r) for r in await c.fetchall()]


async def is_whitelisted(guild_id, user_id=None, role_ids=None, channel_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        if user_id:
            c = await db.execute(
                "SELECT 1 FROM automod_whitelist WHERE guild_id=? AND type='user' AND target_id=?",
                (guild_id, user_id)
            )
            if await c.fetchone():
                return True
        if role_ids:
            for rid in role_ids:
                c = await db.execute(
                    "SELECT 1 FROM automod_whitelist WHERE guild_id=? AND type='role' AND target_id=?",
                    (guild_id, rid)
                )
                if await c.fetchone():
                    return True
        if channel_id:
            c = await db.execute(
                "SELECT 1 FROM automod_whitelist WHERE guild_id=? AND type='channel' AND target_id=?",
                (guild_id, channel_id)
            )
            if await c.fetchone():
                return True
    return False


async def add_bad_word(guild_id, word, added_by):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO automod_bad_words (guild_id, word, added_by) VALUES (?,?,?)",
                (guild_id, word.lower(), added_by)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_bad_word(guild_id, word):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "DELETE FROM automod_bad_words WHERE guild_id=? AND word=?",
            (guild_id, word.lower())
        )
        await db.commit()
        return c.rowcount > 0


async def get_bad_words(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("SELECT word FROM automod_bad_words WHERE guild_id=?", (guild_id,))
        return [r[0] for r in await c.fetchall()]


async def clear_bad_words(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM automod_bad_words WHERE guild_id=?", (guild_id,))
        await db.commit()


async def add_blocked_link(guild_id, domain, added_by):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO automod_blocked_links (guild_id, domain, added_by) VALUES (?,?,?)",
                (guild_id, domain.lower(), added_by)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_blocked_link(guild_id, domain):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "DELETE FROM automod_blocked_links WHERE guild_id=? AND domain=?",
            (guild_id, domain.lower())
        )
        await db.commit()
        return c.rowcount > 0


async def get_blocked_links(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("SELECT domain FROM automod_blocked_links WHERE guild_id=?", (guild_id,))
        return [r[0] for r in await c.fetchall()]


async def clear_blocked_links(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM automod_blocked_links WHERE guild_id=?", (guild_id,))
        await db.commit()


async def add_warn(guild_id, user_id, moderator_id, reason, expire_days=30):
    expires_at = (datetime.now(timezone.utc) + timedelta(days=expire_days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "INSERT INTO automod_warns (guild_id, user_id, moderator_id, reason, expires_at) "
            "VALUES (?,?,?,?,?)",
            (guild_id, user_id, moderator_id, reason, expires_at)
        )
        await db.commit()
        return c.lastrowid


async def get_active_warns(guild_id, user_id):
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "SELECT * FROM automod_warns "
            "WHERE guild_id=? AND user_id=? AND active=1 AND expires_at > ? "
            "ORDER BY created_at DESC",
            (guild_id, user_id, now)
        )
        return [dict(r) for r in await c.fetchall()]


async def get_all_warns(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "SELECT * FROM automod_warns WHERE guild_id=? AND user_id=? "
            "ORDER BY created_at DESC LIMIT 25",
            (guild_id, user_id)
        )
        return [dict(r) for r in await c.fetchall()]


async def remove_warn(warn_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("UPDATE automod_warns SET active=0 WHERE id=?", (warn_id,))
        await db.commit()
        return c.rowcount > 0


async def clear_warns(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "UPDATE automod_warns SET active=0 WHERE guild_id=? AND user_id=? AND active=1",
            (guild_id, user_id)
        )
        await db.commit()
        return c.rowcount


async def log_automod_action(guild_id, user_id, action_type, reason, details=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO automod_actions (guild_id, user_id, action_type, reason, details) "
            "VALUES (?,?,?,?,?)",
            (guild_id, user_id, action_type, reason, details)
        )
        await db.commit()


async def get_action_log(guild_id, user_id=None, limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if user_id:
            c = await db.execute(
                "SELECT * FROM automod_actions WHERE guild_id=? AND user_id=? "
                "ORDER BY created_at DESC LIMIT ?",
                (guild_id, user_id, limit)
            )
        else:
            c = await db.execute(
                "SELECT * FROM automod_actions WHERE guild_id=? "
                "ORDER BY created_at DESC LIMIT ?",
                (guild_id, limit)
            )
        return [dict(r) for r in await c.fetchall()]


# ═══════════════════════════════════════════════════════════════
#  TICKET FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def get_ticket_settings(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM ticket_settings WHERE guild_id=?", (guild_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def create_ticket_settings(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO ticket_settings (guild_id) VALUES (?)", (guild_id,))
        await db.commit()


async def update_ticket_setting(guild_id, key, value):
    valid = [
        "enabled", "category_id", "log_channel_id", "support_role_id",
        "panel_channel_id", "panel_message_id", "max_open_tickets",
        "ticket_counter", "welcome_message", "close_confirmation",
        "transcript_on_close", "auto_close_hours"
    ]
    if key not in valid:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"INSERT INTO ticket_settings (guild_id, {key}) VALUES (?, ?) "
            f"ON CONFLICT(guild_id) DO UPDATE SET {key}=excluded.{key}, "
            f"updated_at=CURRENT_TIMESTAMP",
            (guild_id, value)
        )
        await db.commit()
    return True


async def increment_ticket_counter(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("SELECT ticket_counter FROM ticket_settings WHERE guild_id=?", (guild_id,))
        r = await c.fetchone()
        new_count = (r[0] if r else 0) + 1
        await db.execute("UPDATE ticket_settings SET ticket_counter=? WHERE guild_id=?", (new_count, guild_id))
        await db.commit()
        return new_count


async def add_ticket_category(guild_id, name, emoji="🎫", description="",
                               category_id=None, support_role_id=None, welcome_message=""):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "INSERT INTO ticket_categories "
            "(guild_id, name, emoji, description, category_id, support_role_id, welcome_message) "
            "VALUES (?,?,?,?,?,?,?)",
            (guild_id, name, emoji, description, category_id, support_role_id, welcome_message)
        )
        await db.commit()
        return c.lastrowid


async def get_ticket_categories(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM ticket_categories WHERE guild_id=?", (guild_id,))
        return [dict(r) for r in await c.fetchall()]


async def remove_ticket_category(cat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("DELETE FROM ticket_categories WHERE id=?", (cat_id,))
        await db.commit()
        return c.rowcount > 0


async def get_ticket_category_by_name(guild_id, name):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "SELECT * FROM ticket_categories WHERE guild_id=? AND name=?",
            (guild_id, name)
        )
        r = await c.fetchone()
        return dict(r) if r else None


async def create_ticket(guild_id, channel_id, user_id, category_name, ticket_number):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "INSERT INTO tickets "
            "(guild_id, channel_id, user_id, category_name, ticket_number) "
            "VALUES (?,?,?,?,?)",
            (guild_id, channel_id, user_id, category_name, ticket_number)
        )
        await db.commit()
        return c.lastrowid


async def get_ticket_by_channel(channel_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM tickets WHERE channel_id=?", (channel_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def get_open_tickets_by_user(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "SELECT * FROM tickets WHERE guild_id=? AND user_id=? AND status='open'",
            (guild_id, user_id)
        )
        return [dict(r) for r in await c.fetchall()]


async def get_all_open_tickets(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "SELECT * FROM tickets WHERE guild_id=? AND status='open' ORDER BY created_at DESC",
            (guild_id,)
        )
        return [dict(r) for r in await c.fetchall()]


async def close_ticket(channel_id, closed_by, reason=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tickets SET status='closed', closed_at=CURRENT_TIMESTAMP, "
            "closed_by=?, close_reason=? WHERE channel_id=?",
            (closed_by, reason, channel_id)
        )
        await db.commit()


async def claim_ticket(channel_id, staff_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET claimed_by=? WHERE channel_id=?", (staff_id, channel_id))
        await db.commit()


async def set_ticket_priority(channel_id, priority):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET priority=? WHERE channel_id=?", (priority, channel_id))
        await db.commit()


async def get_ticket_stats(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("SELECT COUNT(*) FROM tickets WHERE guild_id=? AND status='open'", (guild_id,))
        open_count = (await c.fetchone())[0]
        c = await db.execute("SELECT COUNT(*) FROM tickets WHERE guild_id=? AND status='closed'", (guild_id,))
        closed_count = (await c.fetchone())[0]
        c = await db.execute("SELECT COUNT(*) FROM tickets WHERE guild_id=?", (guild_id,))
        total = (await c.fetchone())[0]
        return {"open": open_count, "closed": closed_count, "total": total}


async def save_ticket_message(ticket_id, user_id, username, content):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ticket_messages (ticket_id, user_id, username, content) VALUES (?,?,?,?)",
            (ticket_id, user_id, username, content)
        )
        await db.commit()


async def get_ticket_messages(ticket_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "SELECT * FROM ticket_messages WHERE ticket_id=? ORDER BY created_at ASC",
            (ticket_id,)
        )
        return [dict(r) for r in await c.fetchall()]


# ═══════════════════════════════════════════════════════════════
#  ORDER SYSTEM FUNCTIONS
# ═══════════════════════════════════════════════════════════════

# ─── Shop Settings ──────────────────────────────────────────────

async def get_shop_settings(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM shop_settings WHERE guild_id=?", (guild_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def create_shop_settings(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO shop_settings (guild_id) VALUES (?)", (guild_id,))
        await db.commit()


async def update_shop_setting(guild_id, key, value):
    valid = [
        "enabled", "order_channel_id", "log_channel_id", "review_channel_id",
        "review_channel_name", "delivery_category_id", "staff_role_id",
        "customer_role_id", "panel_channel_id", "panel_message_id",
        "order_counter", "currency", "payment_methods", "auto_customer_role",
        "hide_product_list", "shop_info_message"
    ]
    if key not in valid:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"INSERT INTO shop_settings (guild_id, {key}) VALUES (?, ?) "
            f"ON CONFLICT(guild_id) DO UPDATE SET {key}=excluded.{key}, "
            f"updated_at=CURRENT_TIMESTAMP",
            (guild_id, value)
        )
        await db.commit()
    return True


async def increment_order_counter(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("SELECT order_counter FROM shop_settings WHERE guild_id=?", (guild_id,))
        r = await c.fetchone()
        new_count = (r[0] if r else 0) + 1
        await db.execute("UPDATE shop_settings SET order_counter=? WHERE guild_id=?", (new_count, guild_id))
        await db.commit()
        return new_count


# ─── Products ──────────────────────────────────────────────────

async def add_product(guild_id, name, description, price, emoji="🛒",
                      category="General", delivery_time="5M-2H",
                      reseller_price=None, image_url=None, stock_count=None):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "INSERT INTO products (guild_id, name, description, price, emoji, category, "
            "delivery_time, reseller_price, image_url, stock_count) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (guild_id, name, description, price, emoji, category,
             delivery_time, reseller_price, image_url, stock_count)
        )
        await db.commit()
        return c.lastrowid


async def get_products(guild_id, category=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if category:
            c = await db.execute(
                "SELECT * FROM products WHERE guild_id=? AND category=? ORDER BY sort_order, id",
                (guild_id, category)
            )
        else:
            c = await db.execute(
                "SELECT * FROM products WHERE guild_id=? ORDER BY category, sort_order, id",
                (guild_id,)
            )
        return [dict(r) for r in await c.fetchall()]


async def get_product_by_id(product_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM products WHERE id=?", (product_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def update_product(product_id, key, value):
    valid = ["name", "description", "price", "emoji", "category",
             "in_stock", "stock_count", "delivery_time", "reseller_price",
             "image_url", "sort_order"]
    if key not in valid:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE products SET {key}=? WHERE id=?", (value, product_id))
        await db.commit()
    return True


async def delete_product(product_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("DELETE FROM products WHERE id=?", (product_id,))
        await db.commit()
        return c.rowcount > 0


async def toggle_product_stock(product_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("SELECT in_stock FROM products WHERE id=?", (product_id,))
        r = await c.fetchone()
        if not r:
            return False
        new_val = 0 if r[0] else 1
        await db.execute("UPDATE products SET in_stock=? WHERE id=?", (new_val, product_id))
        await db.commit()
        return new_val


async def get_product_categories(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "SELECT DISTINCT category FROM products WHERE guild_id=? ORDER BY category",
            (guild_id,)
        )
        return [r[0] for r in await c.fetchall()]


async def decrement_stock(product_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("SELECT stock_count FROM products WHERE id=?", (product_id,))
        r = await c.fetchone()
        if r and r[0] is not None:
            new_count = max(0, r[0] - 1)
            await db.execute("UPDATE products SET stock_count=? WHERE id=?", (new_count, product_id))
            if new_count == 0:
                await db.execute("UPDATE products SET in_stock=0 WHERE id=?", (product_id,))
            await db.commit()
            return new_count
        return None


# ─── Orders ────────────────────────────────────────────────────

async def create_order(guild_id, order_number, user_id, product_id,
                       product_name, price, channel_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "INSERT INTO orders (guild_id, order_number, user_id, product_id, "
            "product_name, price, channel_id) VALUES (?,?,?,?,?,?,?)",
            (guild_id, order_number, user_id, product_id, product_name, price, channel_id)
        )
        await db.commit()
        return c.lastrowid


async def get_order_by_id(order_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def get_order_by_channel(channel_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM orders WHERE channel_id=?", (channel_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def get_order_by_number(guild_id, order_number):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "SELECT * FROM orders WHERE guild_id=? AND order_number=?",
            (guild_id, order_number)
        )
        r = await c.fetchone()
        return dict(r) if r else None


async def get_user_orders(guild_id, user_id, status=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            c = await db.execute(
                "SELECT * FROM orders WHERE guild_id=? AND user_id=? AND status=? "
                "ORDER BY created_at DESC",
                (guild_id, user_id, status)
            )
        else:
            c = await db.execute(
                "SELECT * FROM orders WHERE guild_id=? AND user_id=? "
                "ORDER BY created_at DESC LIMIT 25",
                (guild_id, user_id)
            )
        return [dict(r) for r in await c.fetchall()]


async def get_all_orders(guild_id, status=None, limit=50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            c = await db.execute(
                "SELECT * FROM orders WHERE guild_id=? AND status=? "
                "ORDER BY created_at DESC LIMIT ?",
                (guild_id, status, limit)
            )
        else:
            c = await db.execute(
                "SELECT * FROM orders WHERE guild_id=? ORDER BY created_at DESC LIMIT ?",
                (guild_id, limit)
            )
        return [dict(r) for r in await c.fetchall()]


async def update_order_status(order_id, status, staff_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        if status == "delivered":
            await db.execute(
                "UPDATE orders SET status=?, staff_id=?, completed_at=CURRENT_TIMESTAMP, "
                "updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (status, staff_id, order_id)
            )
        else:
            await db.execute(
                "UPDATE orders SET status=?, staff_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (status, staff_id, order_id)
            )
        await db.commit()


async def update_order_field(order_id, key, value):
    valid = ["payment_method", "delivery_info", "notes", "channel_id", "staff_id"]
    if key not in valid:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE orders SET {key}=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (value, order_id)
        )
        await db.commit()
    return True


async def get_order_stats(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}
        for status in ["pending", "processing", "delivered", "cancelled", "refunded"]:
            c = await db.execute(
                "SELECT COUNT(*) FROM orders WHERE guild_id=? AND status=?",
                (guild_id, status)
            )
            stats[status] = (await c.fetchone())[0]

        c = await db.execute("SELECT COUNT(*) FROM orders WHERE guild_id=?", (guild_id,))
        stats["total"] = (await c.fetchone())[0]

        c = await db.execute(
            "SELECT COALESCE(SUM(price), 0) FROM orders WHERE guild_id=? AND status='delivered'",
            (guild_id,)
        )
        stats["total_revenue"] = (await c.fetchone())[0]

        return stats


# ─── Reviews ───────────────────────────────────────────────────

async def add_review(guild_id, order_id, user_id, rating, comment="", review_message_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO order_reviews (guild_id, order_id, user_id, rating, comment, review_message_id) "
                "VALUES (?,?,?,?,?,?)",
                (guild_id, order_id, user_id, rating, comment, review_message_id)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def update_review_message_id(order_id, message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE order_reviews SET review_message_id=? WHERE order_id=?",
            (message_id, order_id)
        )
        await db.commit()


async def delete_review(review_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "SELECT review_message_id, guild_id FROM order_reviews WHERE id=?", (review_id,)
        )
        r = await c.fetchone()
        await db.execute("DELETE FROM order_reviews WHERE id=?", (review_id,))
        await db.commit()
        return {"message_id": r[0], "guild_id": r[1]} if r else None


async def get_review_by_id(review_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM order_reviews WHERE id=?", (review_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def get_review_count(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "SELECT COUNT(*) FROM order_reviews WHERE guild_id=?", (guild_id,)
        )
        return (await c.fetchone())[0]


async def get_last_staff_request(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "SELECT requested_at FROM staff_requests WHERE guild_id=? AND user_id=? "
            "ORDER BY requested_at DESC LIMIT 1",
            (guild_id, user_id)
        )
        r = await c.fetchone()
        return r[0] if r else None


async def save_staff_request(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO staff_requests (guild_id, user_id) VALUES (?,?)",
            (guild_id, user_id)
        )
        await db.commit()


async def get_reviews(guild_id, limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "SELECT r.*, o.product_name, o.order_number FROM order_reviews r "
            "JOIN orders o ON r.order_id = o.id "
            "WHERE r.guild_id=? ORDER BY r.created_at DESC LIMIT ?",
            (guild_id, limit)
        )
        return [dict(r) for r in await c.fetchall()]


async def get_average_rating(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "SELECT AVG(rating), COUNT(*) FROM order_reviews WHERE guild_id=?",
            (guild_id,)
        )
        r = await c.fetchone()
        return {"average": round(r[0], 1) if r[0] else 0, "count": r[1]}


# ─── Customer Profiles ─────────────────────────────────────────

async def get_customer_profile(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "SELECT * FROM customer_profiles WHERE guild_id=? AND user_id=?",
            (guild_id, user_id)
        )
        r = await c.fetchone()
        return dict(r) if r else None


async def update_customer_profile(guild_id, user_id, price):
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await get_customer_profile(guild_id, user_id)
        if existing:
            await db.execute(
                "UPDATE customer_profiles SET total_orders=total_orders+1, "
                "total_spent=total_spent+?, completed_orders=completed_orders+1, "
                "last_order_at=CURRENT_TIMESTAMP WHERE guild_id=? AND user_id=?",
                (price, guild_id, user_id)
            )
        else:
            await db.execute(
                "INSERT INTO customer_profiles (guild_id, user_id, total_orders, total_spent, "
                "completed_orders, first_order_at, last_order_at) "
                "VALUES (?,?,1,?,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
                (guild_id, user_id, price)
            )
        await db.commit()


async def blacklist_customer(guild_id, user_id, reason=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO customer_profiles (guild_id, user_id, blacklisted, blacklist_reason) "
            "VALUES (?,?,1,?) ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "blacklisted=1, blacklist_reason=?",
            (guild_id, user_id, reason, reason)
        )
        await db.commit()


async def unblacklist_customer(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE customer_profiles SET blacklisted=0, blacklist_reason=NULL "
            "WHERE guild_id=? AND user_id=?",
            (guild_id, user_id)
        )
        await db.commit()

# ═══════════════════════════════════════════════════════════════
#  SUBSCRIPTION FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def get_subscription(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM subscriptions WHERE guild_id=?", (guild_id,))
        r = await c.fetchone()
        if r:
            sub = dict(r)
            # Check if expired
            if sub.get("expires_at"):
                try:
                    expires = datetime.fromisoformat(sub["expires_at"]).replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) > expires:
                        # Expired — downgrade to free
                        await db.execute(
                            "UPDATE subscriptions SET plan='free', expires_at=NULL, "
                            "updated_at=CURRENT_TIMESTAMP WHERE guild_id=?",
                            (guild_id,)
                        )
                        await db.commit()
                        sub["plan"] = "free"
                        sub["expires_at"] = None
                except:
                    pass
            return sub
        return None


async def get_guild_plan(guild_id):
    sub = await get_subscription(guild_id)
    return sub["plan"] if sub else "free"


async def create_subscription(guild_id, plan="free", activated_by=None, days=None, amount=0.0, notes=""):
    expires_at = None
    if days:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO subscriptions (guild_id, plan, activated_by, expires_at, total_paid, notes) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(guild_id) DO UPDATE SET "
            "plan=?, activated_by=?, expires_at=?, total_paid=total_paid+?, "
            "payment_count=payment_count+1, notes=?, updated_at=CURRENT_TIMESTAMP",
            (guild_id, plan, activated_by, expires_at, amount, notes,
             plan, activated_by, expires_at, amount, notes)
        )
        # Log
        await db.execute(
            "INSERT INTO subscription_logs (guild_id, action, new_plan, duration_days, "
            "amount, performed_by, notes) VALUES (?,?,?,?,?,?,?)",
            (guild_id, "activate", plan, days, amount, activated_by or 0, notes)
        )
        await db.commit()


async def update_subscription_plan(guild_id, new_plan, performed_by, days=None, amount=0.0, notes=""):
    sub = await get_subscription(guild_id)
    old_plan = sub["plan"] if sub else "free"

    expires_at = None
    if days:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        if sub:
            if expires_at:
                await db.execute(
                    "UPDATE subscriptions SET plan=?, activated_by=?, expires_at=?, "
                    "total_paid=total_paid+?, payment_count=payment_count+1, notes=?, "
                    "updated_at=CURRENT_TIMESTAMP WHERE guild_id=?",
                    (new_plan, performed_by, expires_at, amount, notes, guild_id)
                )
            else:
                await db.execute(
                    "UPDATE subscriptions SET plan=?, activated_by=?, "
                    "total_paid=total_paid+?, payment_count=payment_count+1, notes=?, "
                    "updated_at=CURRENT_TIMESTAMP WHERE guild_id=?",
                    (new_plan, performed_by, amount, notes, guild_id)
                )
        else:
            await create_subscription(guild_id, new_plan, performed_by, days, amount, notes)

        # Log
        await db.execute(
            "INSERT INTO subscription_logs (guild_id, action, old_plan, new_plan, "
            "duration_days, amount, performed_by, notes) VALUES (?,?,?,?,?,?,?,?)",
            (guild_id, "change", old_plan, new_plan, days, amount, performed_by, notes)
        )
        await db.commit()


async def extend_subscription(guild_id, days, performed_by, amount=0.0, notes=""):
    sub = await get_subscription(guild_id)
    if not sub:
        return False

    async with aiosqlite.connect(DB_PATH) as db:
        current_expires = sub.get("expires_at")
        if current_expires:
            try:
                current_dt = datetime.fromisoformat(current_expires).replace(tzinfo=timezone.utc)
                if current_dt > datetime.now(timezone.utc):
                    new_expires = (current_dt + timedelta(days=days)).isoformat()
                else:
                    new_expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
            except:
                new_expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        else:
            new_expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

        await db.execute(
            "UPDATE subscriptions SET expires_at=?, total_paid=total_paid+?, "
            "payment_count=payment_count+1, notes=?, updated_at=CURRENT_TIMESTAMP "
            "WHERE guild_id=?",
            (new_expires, amount, notes, guild_id)
        )
        await db.execute(
            "INSERT INTO subscription_logs (guild_id, action, new_plan, duration_days, "
            "amount, performed_by, notes) VALUES (?,?,?,?,?,?,?)",
            (guild_id, "extend", sub["plan"], days, amount, performed_by, notes)
        )
        await db.commit()
    return True


async def revoke_subscription(guild_id, performed_by, notes=""):
    sub = await get_subscription(guild_id)
    old_plan = sub["plan"] if sub else "free"

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET plan='free', expires_at=NULL, "
            "updated_at=CURRENT_TIMESTAMP WHERE guild_id=?",
            (guild_id,)
        )
        await db.execute(
            "INSERT INTO subscription_logs (guild_id, action, old_plan, new_plan, "
            "performed_by, notes) VALUES (?,?,?,?,?,?)",
            (guild_id, "revoke", old_plan, "free", performed_by, notes)
        )
        await db.commit()


async def get_all_subscriptions():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "SELECT * FROM subscriptions ORDER BY "
            "CASE plan WHEN 'business' THEN 1 WHEN 'premium' THEN 2 "
            "WHEN 'basic' THEN 3 ELSE 4 END"
        )
        return [dict(r) for r in await c.fetchall()]


async def get_active_subscriptions():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "SELECT * FROM subscriptions WHERE plan != 'free' "
            "ORDER BY updated_at DESC"
        )
        return [dict(r) for r in await c.fetchall()]


async def get_subscription_logs(guild_id=None, limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if guild_id:
            c = await db.execute(
                "SELECT * FROM subscription_logs WHERE guild_id=? "
                "ORDER BY created_at DESC LIMIT ?",
                (guild_id, limit)
            )
        else:
            c = await db.execute(
                "SELECT * FROM subscription_logs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        return [dict(r) for r in await c.fetchall()]


async def get_subscription_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}
        for plan in ["free", "basic", "premium", "business"]:
            c = await db.execute(
                "SELECT COUNT(*) FROM subscriptions WHERE plan=?", (plan,)
            )
            stats[plan] = (await c.fetchone())[0]

        c = await db.execute("SELECT COUNT(*) FROM subscriptions")
        stats["total"] = (await c.fetchone())[0]

        c = await db.execute("SELECT COALESCE(SUM(total_paid), 0) FROM subscriptions")
        stats["total_revenue"] = (await c.fetchone())[0]

        c = await db.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE plan != 'free' AND expires_at IS NOT NULL "
            "AND expires_at < ?",
            (datetime.now(timezone.utc).isoformat(),)
        )
        stats["expired"] = (await c.fetchone())[0]

        return stats

async def get_expiring_soon(days=7):
    threshold = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "SELECT * FROM subscriptions WHERE plan != 'free' "
            "AND expires_at IS NOT NULL AND expires_at > ? AND expires_at < ?",
            (now, threshold)
        )
        return [dict(r) for r in await c.fetchall()]

async def is_customer_blacklisted(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute(
            "SELECT blacklisted FROM customer_profiles WHERE guild_id=? AND user_id=?",
            (guild_id, user_id)
        )
        r = await c.fetchone()
        return bool(r[0]) if r else False


# ═══════════════════════════════════════════════════════════════
#  LOGGING FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def get_logging_settings(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM logging_settings WHERE guild_id=?", (guild_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def update_logging_setting(guild_id, key, value):
    valid = [
        "enabled", "log_channel_id", "log_messages", "log_members",
        "log_roles", "log_channels", "log_bans", "log_voice"
    ]
    if key not in valid:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"INSERT INTO logging_settings (guild_id, {key}) VALUES (?, ?) "
            f"ON CONFLICT(guild_id) DO UPDATE SET {key}=excluded.{key}, "
            f"updated_at=CURRENT_TIMESTAMP",
            (guild_id, value)
        )
        await db.commit()
    return True


# ═══════════════════════════════════════════════════════════════
#  AUTO ROLE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def get_auto_role(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM auto_roles WHERE guild_id=?", (guild_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def set_auto_role(guild_id, role_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO auto_roles (guild_id, role_id) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET role_id=excluded.role_id, "
            "enabled=1, updated_at=CURRENT_TIMESTAMP",
            (guild_id, role_id)
        )
        await db.commit()


async def remove_auto_role(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("DELETE FROM auto_roles WHERE guild_id=?", (guild_id,))
        await db.commit()
        return c.rowcount > 0


# ═══════════════════════════════════════════════════════════════
#  BOT CUSTOMIZATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def get_bot_customization(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM bot_customization WHERE guild_id=?", (guild_id,))
        r = await c.fetchone()
        return dict(r) if r else None


async def set_bot_customization(guild_id, key, value):
    valid = ["custom_nickname", "custom_avatar_url"]
    if key not in valid:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"INSERT INTO bot_customization (guild_id, {key}) VALUES (?, ?) "
            f"ON CONFLICT(guild_id) DO UPDATE SET {key}=excluded.{key}, "
            f"updated_at=CURRENT_TIMESTAMP",
            (guild_id, value)
        )
        await db.commit()
    return True


async def reset_bot_customization(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM bot_customization WHERE guild_id=?", (guild_id,))
        await db.commit()


# ═══════════════════════════════════════════════════════════════
#  LICENSE KEY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def create_license_key(key, plan, duration_days, created_by, notes=""):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO license_keys (key, plan, duration_days, created_by, notes) "
                "VALUES (?,?,?,?,?)",
                (key, plan, duration_days, created_by, notes)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_license_key(key):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute("SELECT * FROM license_keys WHERE key=?", (key,))
        r = await c.fetchone()
        return dict(r) if r else None


async def redeem_license_key(key, user_id, guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE license_keys SET redeemed=1, redeemed_by=?, redeemed_guild_id=?, "
            "redeemed_at=CURRENT_TIMESTAMP WHERE key=?",
            (user_id, guild_id, key)
        )
        await db.commit()


async def get_all_license_keys(redeemed=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if redeemed is not None:
            c = await db.execute(
                "SELECT * FROM license_keys WHERE redeemed=? ORDER BY created_at DESC",
                (int(redeemed),)
            )
        else:
            c = await db.execute("SELECT * FROM license_keys ORDER BY created_at DESC")
        return [dict(r) for r in await c.fetchall()]


async def delete_license_key(key):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("DELETE FROM license_keys WHERE key=?", (key,))
        await db.commit()
        return c.rowcount > 0


async def get_license_key_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("SELECT COUNT(*) FROM license_keys WHERE redeemed=0")
        available = (await c.fetchone())[0]
        c = await db.execute("SELECT COUNT(*) FROM license_keys WHERE redeemed=1")
        used = (await c.fetchone())[0]
        c = await db.execute("SELECT COUNT(*) FROM license_keys")
        total = (await c.fetchone())[0]
        return {"available": available, "used": used, "total": total}


# ═══════════════════════════════════════════════════════════════
#  FEATURE CHECK HELPERS
# ═══════════════════════════════════════════════════════════════

async def check_feature(guild_id, feature_key):
    """Check if a feature is allowed for the guild's current plan.
    Returns (allowed: bool, plan: str)"""
    from config import get_plan_limits
    plan = await get_guild_plan(guild_id)
    limits = get_plan_limits(plan)
    allowed = bool(limits.get(feature_key, False))
    return allowed, plan