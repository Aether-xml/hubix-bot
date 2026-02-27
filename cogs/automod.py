import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta, timezone
import re
import unicodedata
from collections import defaultdict
from typing import Optional

from utils.database import *
from utils.badwords import (
    get_all_bad_words, get_all_blocked_links, ALLOWED_DOMAINS,
    get_stats, get_blocked_links_by_category, get_bad_words_by_language
)
from config import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, AUTOMOD_COLOR, PANEL_COLOR, get_plan_limits
from utils.database import get_guild_plan


# ═══════════════════════════════════════════════════════════════
#  REGEX PATTERNS
# ═══════════════════════════════════════════════════════════════

INVITE_PATTERN = re.compile(
    r"(discord\.(gg|io|me|li|com\/invite)|discordapp\.com\/invite|discord\.com\/invite)\/?[a-zA-Z0-9\-]+",
    re.IGNORECASE
)
LINK_PATTERN = re.compile(r"https?://([^\s/<>\"']+)", re.IGNORECASE)
EMOJI_PATTERN = re.compile(
    r"<a?:\w+:\d+>|[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
    r"\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0"
    r"\U000024C2-\U0001F251\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF]+",
    re.UNICODE
)
ZALGO_PATTERN = re.compile(r"[\u0300-\u036f\u0489\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f]{3,}")
REPEATED_CHARS_PATTERN = re.compile(r"(.)\1{9,}")  # 10+ repeated chars
REPEATED_WORDS_PATTERN = re.compile(r"\b(\w+)\b(?:\s+\1\b){4,}", re.IGNORECASE)  # 5+ repeated words


# ═══════════════════════════════════════════════════════════════
#  TEXT NORMALIZATION (anti-evasion)
# ═══════════════════════════════════════════════════════════════

LEET_MAP = {
    '0': 'o', '1': 'i', '2': 'z', '3': 'e', '4': 'a',
    '5': 's', '6': 'g', '7': 't', '8': 'b', '9': 'g',
    '@': 'a', '$': 's', '!': 'i', '+': 't',
    '€': 'e', '£': 'l', '¥': 'y',
}

UNICODE_CONFUSABLES = {
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y',
    'х': 'x', 'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M',
    'Н': 'H', 'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y',
    'Х': 'X', 'ᴀ': 'a', 'ʙ': 'b', 'ᴄ': 'c', 'ᴅ': 'd', 'ᴇ': 'e',
    'ꜰ': 'f', 'ɢ': 'g', 'ʜ': 'h', 'ɪ': 'i', 'ᴊ': 'j', 'ᴋ': 'k',
    'ʟ': 'l', 'ᴍ': 'm', 'ɴ': 'n', 'ᴏ': 'o', 'ᴘ': 'p', 'ǫ': 'q',
    'ʀ': 'r', 'ꜱ': 's', 'ᴛ': 't', 'ᴜ': 'u', 'ᴠ': 'v', 'ᴡ': 'w',
    'ʏ': 'y', 'ᴢ': 'z',
    'ⓐ': 'a', 'ⓑ': 'b', 'ⓒ': 'c', 'ⓓ': 'd', 'ⓔ': 'e',
    'ⓕ': 'f', 'ⓖ': 'g', 'ⓗ': 'h', 'ⓘ': 'i', 'ⓙ': 'j',
    'ⓚ': 'k', 'ⓛ': 'l', 'ⓜ': 'm', 'ⓝ': 'n', 'ⓞ': 'o',
    'ⓟ': 'p', 'ⓠ': 'q', 'ⓡ': 'r', 'ⓢ': 's', 'ⓣ': 't',
    'ⓤ': 'u', 'ⓥ': 'v', 'ⓦ': 'w', 'ⓧ': 'x', 'ⓨ': 'y', 'ⓩ': 'z',
}


def normalize_text(text: str) -> str:
    """Normalize text to catch evasion attempts."""
    result = text.lower()

    # Unicode confusables
    for k, v in UNICODE_CONFUSABLES.items():
        result = result.replace(k, v)

    # NFKD normalization (decomposes special chars)
    result = unicodedata.normalize('NFKD', result)

    # Remove combining chars (accents etc)
    result = ''.join(c for c in result if not unicodedata.combining(c))

    # Leet speak
    for k, v in LEET_MAP.items():
        result = result.replace(k, v)

    # Remove separators between letters: f.u.c.k → fuck, f-u-c-k → fuck
    result_no_sep = re.sub(r'(?<=\w)[.\-_*|/\\,;:~`\s]+(?=\w)', '', result)

    return result_no_sep


def check_word_in_text(word: str, text: str) -> bool:
    """Check if a bad word exists in text with word boundary awareness."""
    # Direct check
    if word in text:
        return True

    # Word boundary check for short words to avoid false positives
    if len(word) <= 3:
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, text):
            return True
        return False

    return word in text


# ═══════════════════════════════════════════════════════════════
#  AUTOMOD COG
# ═══════════════════════════════════════════════════════════════

class AutoMod(commands.Cog):
    """🛡️ Advanced AutoMod System for Nexify"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.spam_tracker: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        self.duplicate_tracker: dict[int, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
        self.settings_cache: dict[int, dict] = {}
        self.bad_words_cache: dict[int, list[str]] = {}
        self.blocked_links_cache: dict[int, list[str]] = {}
        self.builtin_words = get_all_bad_words()
        self.builtin_links = get_all_blocked_links()

    async def cog_load(self):
        self.cleanup_trackers.start()
        print("[COG] AutoMod system loaded.")

    async def cog_unload(self):
        self.cleanup_trackers.cancel()

    # ─── Periodic cleanup ────────────────────────────────────

    @tasks.loop(minutes=5)
    async def cleanup_trackers(self):
        """Clean up old spam/duplicate tracking data."""
        now = datetime.now(timezone.utc).timestamp()
        for gid in list(self.spam_tracker.keys()):
            for uid in list(self.spam_tracker[gid].keys()):
                self.spam_tracker[gid][uid] = [t for t in self.spam_tracker[gid][uid] if now - t < 60]
                if not self.spam_tracker[gid][uid]:
                    del self.spam_tracker[gid][uid]
            if not self.spam_tracker[gid]:
                del self.spam_tracker[gid]

        for gid in list(self.duplicate_tracker.keys()):
            for uid in list(self.duplicate_tracker[gid].keys()):
                msgs = self.duplicate_tracker[gid][uid]
                if len(msgs) > 10:
                    self.duplicate_tracker[gid][uid] = msgs[-5:]

    @cleanup_trackers.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

    # ─── Cache Helpers ───────────────────────────────────────

    async def get_settings(self, gid: int) -> dict | None:
        if gid in self.settings_cache:
            return self.settings_cache[gid]
        s = await get_automod_settings(gid)
        if s:
            self.settings_cache[gid] = s
        return s

    async def refresh_settings(self, gid: int):
        s = await get_automod_settings(gid)
        if s:
            self.settings_cache[gid] = s
        else:
            self.settings_cache.pop(gid, None)

    async def get_words(self, gid: int) -> list[str]:
        if gid in self.bad_words_cache:
            return self.bad_words_cache[gid]
        w = await get_bad_words(gid)
        self.bad_words_cache[gid] = w
        return w

    async def refresh_words(self, gid: int):
        self.bad_words_cache[gid] = await get_bad_words(gid)

    async def get_links(self, gid: int) -> list[str]:
        if gid in self.blocked_links_cache:
            return self.blocked_links_cache[gid]
        l = await get_blocked_links(gid)
        self.blocked_links_cache[gid] = l
        return l

    async def refresh_links(self, gid: int):
        self.blocked_links_cache[gid] = await get_blocked_links(gid)

    # ─── Logging ─────────────────────────────────────────────

    async def send_log(self, guild, settings, embed):
        cid = settings.get("log_channel_id")
        if not cid:
            return
        ch = guild.get_channel(cid)
        if ch:
            try:
                await ch.send(embed=embed)
            except:
                pass

    def make_log_embed(self, title, member, reason, action, message=None, extra_fields=None):
        e = discord.Embed(
            title=f"🛡️ AutoMod — {title}",
            color=AUTOMOD_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        e.add_field(name="👤 User", value=f"{member.mention} (`{member.id}`)", inline=True)
        e.add_field(name="⚡ Action", value=f"`{action}`", inline=True)
        e.add_field(name="📝 Reason", value=reason, inline=False)

        if message:
            c = message.content[:300] + ("..." if len(message.content) > 300 else "")
            if c:
                e.add_field(name="💬 Message", value=f"```{c}```", inline=False)
            e.add_field(name="📍 Channel", value=message.channel.mention, inline=True)

        if extra_fields:
            for name, value in extra_fields.items():
                e.add_field(name=name, value=value, inline=True)

        e.set_thumbnail(url=member.display_avatar.url)
        e.set_footer(text="Nexify AutoMod")
        return e

    # ─── Action Handler ──────────────────────────────────────

    async def take_action(self, message, violation, settings, severity="medium", delete_msg=True):
        """
        Handle a violation.
        severity: low (just delete), medium (delete + warn), high (delete + warn + immediate action)
        """
        member = message.author
        guild = message.guild

        if delete_msg:
            try:
                await message.delete()
            except:
                pass

        if severity == "low":
            # Just delete, no warn
            le = self.make_log_embed(violation, member, violation, "Message Deleted", message)
            await self.send_log(guild, settings, le)
            await log_automod_action(guild.id, member.id, "delete", violation, f"#{message.channel.name}")
            return

        # Add warn
        wid = await add_warn(guild.id, member.id, self.bot.user.id, violation, settings.get("warn_expire_days", 30))
        await log_automod_action(guild.id, member.id, "warn", violation, f"#{message.channel.name}")
        active = await get_active_warns(guild.id, member.id)
        wc = len(active)
        mw = settings.get("max_warns", 3)

        # DM user
        try:
            ne = discord.Embed(
                title="🛡️ AutoMod Warning",
                description=f"Your message in **{guild.name}** was removed.",
                color=WARNING_COLOR
            )
            ne.add_field(name="📝 Reason", value=violation, inline=False)
            ne.add_field(name="⚠️ Warnings", value=f"`{wc}/{mw}`", inline=True)

            if wc >= mw:
                act = settings.get("warn_action", "mute")
                ne.add_field(
                    name="🔨 Punishment Incoming",
                    value=f"You will be **{act}ed** for reaching {mw} warnings.",
                    inline=False
                )
                ne.color = ERROR_COLOR

            await member.send(embed=ne)
        except:
            pass

        # Log
        le = self.make_log_embed(
            violation, member, violation,
            f"Delete + Warn #{wc}", message,
            {"⚠️ Active Warns": f"`{wc}/{mw}`"}
        )
        await self.send_log(guild, settings, le)

        # High severity = immediate mute regardless of warn count
        if severity == "high":
            try:
                await member.timeout(timedelta(minutes=5), reason=f"AutoMod: {violation}")
                pe = discord.Embed(
                    title="🔨 AutoMod — Immediate Mute",
                    color=ERROR_COLOR,
                    timestamp=datetime.now(timezone.utc)
                )
                pe.add_field(name="👤 User", value=f"{member.mention}", inline=True)
                pe.add_field(name="⚡ Action", value="`Muted 5min`", inline=True)
                pe.add_field(name="📝 Reason", value=f"High severity: {violation}", inline=False)
                pe.set_thumbnail(url=member.display_avatar.url)
                await self.send_log(guild, settings, pe)
            except:
                pass

        # Auto punish on max warns
        if wc >= mw:
            await self.auto_punish(member, settings, wc)

    async def auto_punish(self, member, settings, wc):
        action = settings.get("warn_action", "mute")
        dur = settings.get("warn_action_duration", 600)
        guild = member.guild

        try:
            if action == "mute":
                await member.timeout(timedelta(seconds=dur), reason=f"AutoMod: {wc} warns")
                at = f"Muted {dur // 60}min"
            elif action == "kick":
                try:
                    await member.send(embed=discord.Embed(
                        title="👢 Kicked", description=f"Kicked from **{guild.name}** — max warnings.", color=ERROR_COLOR
                    ))
                except:
                    pass
                await member.kick(reason=f"AutoMod: {wc} warns")
                at = "Kicked"
            elif action == "ban":
                try:
                    await member.send(embed=discord.Embed(
                        title="🔨 Banned", description=f"Banned from **{guild.name}** — max warnings.", color=ERROR_COLOR
                    ))
                except:
                    pass
                await member.ban(reason=f"AutoMod: {wc} warns", delete_message_days=0)
                at = "Banned"
            else:
                return

            await log_automod_action(guild.id, member.id, action, f"Auto: {wc} warns")
            await clear_warns(guild.id, member.id)

            pe = discord.Embed(title="🔨 AutoMod — Auto Punishment", color=ERROR_COLOR, timestamp=datetime.now(timezone.utc))
            pe.add_field(name="👤 User", value=f"{member.mention} (`{member.id}`)", inline=True)
            pe.add_field(name="⚡ Action", value=f"`{at}`", inline=True)
            pe.add_field(name="📝 Reason", value=f"{wc} warnings reached", inline=False)
            pe.set_thumbnail(url=member.display_avatar.url)
            pe.set_footer(text="Nexify AutoMod")
            await self.send_log(guild, settings, pe)
        except:
            pass

    # ═══════════════════════════════════════════════════════════
    #  MAIN MESSAGE FILTER
    # ═══════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or message.webhook_id:
            return
        if message.author.guild_permissions.administrator:
            return

        gid = message.guild.id
        s = await self.get_settings(gid)
        if not s or not s.get("enabled"):
            return

        member = message.author
        rids = [r.id for r in member.roles]
        if await is_whitelisted(gid, user_id=member.id, role_ids=rids, channel_id=message.channel.id):
            return

        # Plan limits
        plan = await get_guild_plan(gid)
        plan_limits = get_plan_limits(plan)

        content = message.content
        normalized = normalize_text(content) if content else ""

        # ─── 1. Anti-Spam (message flood) ───────────────────
        if s.get("anti_spam"):
            now = datetime.now(timezone.utc).timestamp()
            th = s.get("spam_threshold", 5)
            iv = s.get("spam_interval", 5)

            msgs = self.spam_tracker[gid][member.id]
            msgs.append(now)
            self.spam_tracker[gid][member.id] = [t for t in msgs if now - t < iv]

            if len(self.spam_tracker[gid][member.id]) >= th:
                self.spam_tracker[gid][member.id] = []
                await self.take_action(message, "Spam Detected (Message Flood)", s, severity="medium")
                return

        # ─── 2. Duplicate Message Detection ─────────────────
        if s.get("anti_spam") and content:
            dupes = self.duplicate_tracker[gid][member.id]
            dupes.append(content.lower().strip())
            if len(dupes) > 15:
                self.duplicate_tracker[gid][member.id] = dupes[-10:]

            # Check last 5 messages for duplicates
            recent = self.duplicate_tracker[gid][member.id][-5:]
            if len(recent) >= 3 and len(set(recent)) == 1:
                self.duplicate_tracker[gid][member.id] = []
                await self.take_action(message, "Spam Detected (Duplicate Messages)", s, severity="medium")
                return

        # ─── 3. Anti-Invite ─────────────────────────────────
        if plan_limits.get("automod_anti_invite") and s.get("anti_invite") and content:
            if INVITE_PATTERN.search(content):
                await self.take_action(message, "Discord Invite Link", s, severity="medium")
                return

        # ─── 4. Blocked Links (scam/phishing/nsfw) ──────────
        if plan_limits.get("automod_anti_link") and s.get("blocked_links_enabled") and content:
            domains = LINK_PATTERN.findall(content)
            for domain in domains:
                domain_lower = domain.lower().split('/')[0].split(':')[0]

                # Built-in blocked links
                for blocked in self.builtin_links:
                    if blocked in domain_lower:
                        await self.take_action(
                            message,
                            f"Blocked Link Detected: `{domain_lower}`",
                            s, severity="high"
                        )
                        return

                # Custom blocked links
                custom = await self.get_links(gid)
                for blocked in custom:
                    if blocked in domain_lower:
                        await self.take_action(
                            message,
                            f"Blocked Link Detected: `{domain_lower}`",
                            s, severity="high"
                        )
                        return

        # ─── 5. Anti-Link (general) ─────────────────────────
        if plan_limits.get("automod_anti_link") and s.get("anti_link") and content:
            domains = LINK_PATTERN.findall(content)
            allowed = [d.lower() for d in ALLOWED_DOMAINS]
            filtered = []
            for d in domains:
                dl = d.lower().split('/')[0].split(':')[0]
                if not any(a in dl for a in allowed):
                    filtered.append(dl)
            ml = s.get("max_links", 3)
            if len(filtered) > ml:
                await self.take_action(
                    message,
                    f"Too Many Links ({len(filtered)}/{ml})",
                    s, severity="low"
                )
                return

        # ─── 6. Anti-Caps ───────────────────────────────────
        if s.get("anti_caps") and content:
            ml = s.get("caps_min_length", 10)
            cp = s.get("caps_percentage", 70)
            alpha = [c for c in content if c.isalpha()]
            if len(alpha) >= ml:
                ratio = (sum(1 for c in alpha if c.isupper()) / len(alpha)) * 100
                if ratio >= cp:
                    await self.take_action(message, f"Excessive Caps ({ratio:.0f}%)", s, severity="low")
                    return

        # ─── 7. Anti-Mention Spam ───────────────────────────
        if s.get("anti_mention_spam"):
            if s.get("anti_massping") and message.mention_everyone:
                await self.take_action(message, "Mass Ping (@everyone/@here)", s, severity="high")
                return

            total_mentions = len(message.mentions) + len(message.role_mentions)
            mm = s.get("max_mentions", 5)
            if total_mentions > mm:
                await self.take_action(
                    message,
                    f"Mention Spam ({total_mentions}/{mm})",
                    s, severity="medium"
                )
                return

        # ─── 8. Anti-Emoji Spam ─────────────────────────────
        if s.get("anti_emoji_spam") and content:
            me = s.get("max_emojis", 10)
            ec = len(EMOJI_PATTERN.findall(content))
            if ec > me:
                await self.take_action(message, f"Emoji Spam ({ec}/{me})", s, severity="low")
                return

        # ─── 9. Anti-Newline Spam ───────────────────────────
        if s.get("anti_newline_spam") and content:
            mlines = s.get("max_lines", 30)
            lc = content.count("\n")
            if lc > mlines:
                await self.take_action(message, f"Newline Spam ({lc}/{mlines} lines)", s, severity="low")
                return

        # ─── 10. Anti-Zalgo ─────────────────────────────────
        if s.get("anti_zalgo") and content:
            if ZALGO_PATTERN.search(content):
                await self.take_action(message, "Zalgo/Corrupted Text", s, severity="medium")
                return

        # ─── 11. Repeated Characters ────────────────────────
        if s.get("anti_spam") and content:
            if REPEATED_CHARS_PATTERN.search(content):
                await self.take_action(message, "Character Spam (Repeated Characters)", s, severity="low")
                return

        # ─── 12. Repeated Words ─────────────────────────────
        if s.get("anti_spam") and content:
            if REPEATED_WORDS_PATTERN.search(content):
                await self.take_action(message, "Word Spam (Repeated Words)", s, severity="low")
                return

        # ─── 13. Bad Words (built-in + custom, with normalization) ───
        if plan_limits.get("automod_bad_words") and s.get("bad_words_enabled") and content:
            # Check against normalized text (catches evasion)
            for w in self.builtin_words:
                if check_word_in_text(w, normalized):
                    await self.take_action(message, "Blocked Word Detected", s, severity="medium")
                    return

            # Custom words
            custom = await self.get_words(gid)
            for w in custom:
                if check_word_in_text(w, normalized):
                    await self.take_action(message, "Blocked Word Detected", s, severity="medium")
                    return

        # ─── 14. Wall of Text ───────────────────────────────
        if s.get("anti_newline_spam") and content:
            if len(content) > 2000:
                await self.take_action(message, "Wall of Text (2000+ chars)", s, severity="low")
                return

        # ─── 15. Attachment Spam ─────────────────────────────
        if s.get("anti_spam") and len(message.attachments) > 5:
            await self.take_action(message, f"Attachment Spam ({len(message.attachments)} files)", s, severity="medium")
            return

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.author.bot or not after.guild or before.content == after.content:
            return
        await self.on_message(after)

    # ═══════════════════════════════════════════════════════════
    #  MODALS
    # ═══════════════════════════════════════════════════════════

    class SetupModal(discord.ui.Modal, title="🛡️ AutoMod Setup"):
        ch_input = discord.ui.TextInput(label="Log Channel ID", placeholder="Right-click channel → Copy ID")

        def __init__(self, cog):
            super().__init__()
            self.cog = cog

        async def on_submit(self, interaction):
            try:
                cid = int(self.ch_input.value)
            except:
                return await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)
            ch = interaction.guild.get_channel(cid)
            if not ch:
                return await interaction.response.send_message("❌ Channel not found!", ephemeral=True)

            await interaction.response.defer(ephemeral=True)

            await create_automod_settings(interaction.guild.id)
            await update_automod_setting(interaction.guild.id, "log_channel_id", ch.id)
            await update_automod_setting(interaction.guild.id, "enabled", 1)

            # Load built-in bad words
            count_w = 0
            for w in get_all_bad_words():
                if await add_bad_word(interaction.guild.id, w, interaction.user.id):
                    count_w += 1

            # Load built-in blocked links
            count_l = 0
            for l in get_all_blocked_links():
                if await add_blocked_link(interaction.guild.id, l, interaction.user.id):
                    count_l += 1

            await self.cog.refresh_settings(interaction.guild.id)
            await self.cog.refresh_words(interaction.guild.id)
            await self.cog.refresh_links(interaction.guild.id)

            try:
                await ch.send(embed=discord.Embed(
                    title="🛡️ AutoMod Activated!",
                    description="This channel will receive all AutoMod logs.",
                    color=AUTOMOD_COLOR
                ))
            except:
                pass

            stats = get_stats()

            e = discord.Embed(title="✅ AutoMod Setup Complete!", color=SUCCESS_COLOR)
            e.add_field(name="📌 Log Channel", value=ch.mention, inline=True)
            e.add_field(name="📊 Status", value="🟢 Enabled", inline=True)
            e.add_field(
                name="📦 Pre-loaded Database",
                value=(
                    f"🚫 **{count_w}** bad words loaded\n"
                    f"🛑 **{count_l}** blocked domains loaded\n"
                    f"✅ **{stats['total_allowed']}** allowed domains\n\n"
                    f"**Languages:** {', '.join(stats['languages'].keys())}\n"
                    f"**Categories:** Phishing, Scam, NSFW, IP Loggers, Malware, Crypto Scam"
                ),
                inline=False
            )
            e.add_field(
                name="🔰 Active Filters (15 total)",
                value=(
                    "1️⃣ Message Flood Detection\n"
                    "2️⃣ Duplicate Message Detection\n"
                    "3️⃣ Anti-Invite Links\n"
                    "4️⃣ Scam/Phishing/NSFW Link Blocker\n"
                    "5️⃣ General Link Limiter\n"
                    "6️⃣ Anti-Caps\n"
                    "7️⃣ Anti-Mention Spam\n"
                    "8️⃣ Anti-Emoji Spam\n"
                    "9️⃣ Anti-Newline/Wall of Text\n"
                    "🔟 Anti-Zalgo/Corrupted Text\n"
                    "1️⃣1️⃣ Repeated Character Detection\n"
                    "1️⃣2️⃣ Repeated Word Detection\n"
                    "1️⃣3️⃣ Multi-Language Bad Word Filter\n"
                    "1️⃣4️⃣ Anti-Evasion (Leet/Unicode)\n"
                    "1️⃣5️⃣ Attachment Spam Detection"
                ),
                inline=False
            )
            e.add_field(
                name="⚙️ Default Punishment",
                value="**3 warns** → **Mute** (10 min)\n*High severity = immediate 5min mute*",
                inline=False
            )

            await interaction.followup.send(embed=e, ephemeral=True)

    class ConfigModal(discord.ui.Modal, title="⚙️ Configure Values"):
        spam_th = discord.ui.TextInput(label="Spam Threshold (msgs, 2-20)", placeholder="5", max_length=3, required=False)
        spam_iv = discord.ui.TextInput(label="Spam Interval (seconds, 3-30)", placeholder="5", max_length=3, required=False)
        max_ment = discord.ui.TextInput(label="Max Mentions (2-30)", placeholder="5", max_length=3, required=False)
        max_emoji = discord.ui.TextInput(label="Max Emojis (3-50)", placeholder="10", max_length=3, required=False)
        max_warns = discord.ui.TextInput(label="Max Warns before action (1-10)", placeholder="3", max_length=3, required=False)

        def __init__(self, cog):
            super().__init__()
            self.cog = cog

        async def on_submit(self, interaction):
            changes = []
            for field, key, mn, mx in [
                (self.spam_th, "spam_threshold", 2, 20),
                (self.spam_iv, "spam_interval", 3, 30),
                (self.max_ment, "max_mentions", 2, 30),
                (self.max_emoji, "max_emojis", 3, 50),
                (self.max_warns, "max_warns", 1, 10),
            ]:
                if field.value:
                    try:
                        v = int(field.value)
                        if mn <= v <= mx:
                            await update_automod_setting(interaction.guild.id, key, v)
                            changes.append(f"✅ **{key}** → `{v}`")
                        else:
                            changes.append(f"❌ **{key}**: {mn}-{mx}")
                    except:
                        changes.append(f"❌ **{key}**: invalid")
            await self.cog.refresh_settings(interaction.guild.id)
            await interaction.response.send_message(
                embed=discord.Embed(title="⚙️ Config Updated", description="\n".join(changes) or "*No changes*", color=SUCCESS_COLOR),
                ephemeral=True
            )

    class ConfigModal2(discord.ui.Modal, title="⚙️ Configure Values (Page 2)"):
        caps_pct = discord.ui.TextInput(label="Caps Percentage (50-100)", placeholder="70", max_length=3, required=False)
        caps_min = discord.ui.TextInput(label="Caps Min Length (5-50)", placeholder="10", max_length=3, required=False)
        max_lines = discord.ui.TextInput(label="Max Newlines (5-100)", placeholder="30", max_length=3, required=False)
        max_links = discord.ui.TextInput(label="Max Links (1-20)", placeholder="3", max_length=3, required=False)
        mute_dur = discord.ui.TextInput(label="Mute Duration (seconds, 60-604800)", placeholder="600", max_length=7, required=False)

        def __init__(self, cog):
            super().__init__()
            self.cog = cog

        async def on_submit(self, interaction):
            changes = []
            for field, key, mn, mx in [
                (self.caps_pct, "caps_percentage", 50, 100),
                (self.caps_min, "caps_min_length", 5, 50),
                (self.max_lines, "max_lines", 5, 100),
                (self.max_links, "max_links", 1, 20),
                (self.mute_dur, "warn_action_duration", 60, 604800),
            ]:
                if field.value:
                    try:
                        v = int(field.value)
                        if mn <= v <= mx:
                            await update_automod_setting(interaction.guild.id, key, v)
                            changes.append(f"✅ **{key}** → `{v}`")
                        else:
                            changes.append(f"❌ **{key}**: {mn}-{mx}")
                    except:
                        changes.append(f"❌ **{key}**: invalid")
            await self.cog.refresh_settings(interaction.guild.id)
            await interaction.response.send_message(
                embed=discord.Embed(title="⚙️ Config Updated", description="\n".join(changes) or "*No changes*", color=SUCCESS_COLOR),
                ephemeral=True
            )

    class AddWordModal(discord.ui.Modal, title="🚫 Add Bad Words"):
        words_input = discord.ui.TextInput(label="Words (one per line)", placeholder="word1\nword2\nphrase here", style=discord.TextStyle.paragraph)

        def __init__(self, cog):
            super().__init__()
            self.cog = cog

        async def on_submit(self, interaction):
            words = [w.strip().lower() for w in self.words_input.value.split("\n") if w.strip()]
            added = 0
            for w in words:
                if await add_bad_word(interaction.guild.id, w, interaction.user.id):
                    added += 1
            await self.cog.refresh_words(interaction.guild.id)
            await interaction.response.send_message(
                embed=discord.Embed(title=f"✅ Added {added}/{len(words)} word(s)", color=SUCCESS_COLOR),
                ephemeral=True
            )

    class RemoveWordModal(discord.ui.Modal, title="✂️ Remove Bad Words"):
        words_input = discord.ui.TextInput(label="Words to remove (one per line)", style=discord.TextStyle.paragraph)

        def __init__(self, cog):
            super().__init__()
            self.cog = cog

        async def on_submit(self, interaction):
            words = [w.strip().lower() for w in self.words_input.value.split("\n") if w.strip()]
            removed = 0
            for w in words:
                if await remove_bad_word(interaction.guild.id, w):
                    removed += 1
            await self.cog.refresh_words(interaction.guild.id)
            await interaction.response.send_message(
                embed=discord.Embed(title=f"✅ Removed {removed}/{len(words)}", color=SUCCESS_COLOR),
                ephemeral=True
            )

    class AddLinkModal(discord.ui.Modal, title="🔗 Add Blocked Domains"):
        links_input = discord.ui.TextInput(label="Domains (one per line)", placeholder="scam-site.com\nphishing.xyz", style=discord.TextStyle.paragraph)

        def __init__(self, cog):
            super().__init__()
            self.cog = cog

        async def on_submit(self, interaction):
            domains = [d.strip().lower() for d in self.links_input.value.split("\n") if d.strip()]
            added = 0
            for d in domains:
                if await add_blocked_link(interaction.guild.id, d, interaction.user.id):
                    added += 1
            await self.cog.refresh_links(interaction.guild.id)
            await interaction.response.send_message(
                embed=discord.Embed(title=f"✅ Added {added}/{len(domains)} domain(s)", color=SUCCESS_COLOR),
                ephemeral=True
            )

    class RemoveLinkModal(discord.ui.Modal, title="✂️ Remove Blocked Domains"):
        links_input = discord.ui.TextInput(label="Domains to remove (one per line)", style=discord.TextStyle.paragraph)

        def __init__(self, cog):
            super().__init__()
            self.cog = cog

        async def on_submit(self, interaction):
            domains = [d.strip().lower() for d in self.links_input.value.split("\n") if d.strip()]
            removed = 0
            for d in domains:
                if await remove_blocked_link(interaction.guild.id, d):
                    removed += 1
            await self.cog.refresh_links(interaction.guild.id)
            await interaction.response.send_message(
                embed=discord.Embed(title=f"✅ Removed {removed}/{len(domains)}", color=SUCCESS_COLOR),
                ephemeral=True
            )

    class WarnCheckModal(discord.ui.Modal, title="📊 Check Warns"):
        uid_input = discord.ui.TextInput(label="User ID", placeholder="Right-click → Copy ID")

        async def on_submit(self, interaction):
            try:
                uid = int(self.uid_input.value)
            except:
                return await interaction.response.send_message("❌ Invalid!", ephemeral=True)
            active = await get_active_warns(interaction.guild.id, uid)
            all_w = await get_all_warns(interaction.guild.id, uid)
            target = interaction.guild.get_member(uid)
            name = target.display_name if target else str(uid)
            e = discord.Embed(title=f"⚠️ Warns — {name}", color=WARNING_COLOR if active else SUCCESS_COLOR)
            if target:
                e.set_thumbnail(url=target.display_avatar.url)
            e.add_field(name="🔴 Active", value=f"`{len(active)}`", inline=True)
            e.add_field(name="📊 Total", value=f"`{len(all_w)}`", inline=True)
            if active:
                txt = "\n".join([f"`#{w['id']}` {w['reason']}" for w in active[:10]])
                e.add_field(name="📋 Details", value=txt, inline=False)
            await interaction.response.send_message(embed=e, ephemeral=True)

    class ManualWarnModal(discord.ui.Modal, title="⚠️ Warn User"):
        uid_input = discord.ui.TextInput(label="User ID", placeholder="Right-click → Copy ID")
        reason_input = discord.ui.TextInput(label="Reason", placeholder="Why?")

        def __init__(self, cog):
            super().__init__()
            self.cog = cog

        async def on_submit(self, interaction):
            try:
                uid = int(self.uid_input.value)
            except:
                return await interaction.response.send_message("❌ Invalid!", ephemeral=True)
            target = interaction.guild.get_member(uid)
            if not target:
                return await interaction.response.send_message("❌ Not found!", ephemeral=True)
            if target.bot:
                return await interaction.response.send_message("❌ Can't warn bots!", ephemeral=True)
            s = await get_automod_settings(interaction.guild.id)
            ed = s.get("warn_expire_days", 30) if s else 30
            mw = s.get("max_warns", 3) if s else 3
            wid = await add_warn(interaction.guild.id, uid, interaction.user.id, self.reason_input.value, ed)
            active = await get_active_warns(interaction.guild.id, uid)
            wc = len(active)
            await log_automod_action(interaction.guild.id, uid, "manual_warn", self.reason_input.value, f"By {interaction.user}")
            e = discord.Embed(title="⚠️ Warning Issued", color=WARNING_COLOR)
            e.add_field(name="👤 User", value=target.mention, inline=True)
            e.add_field(name="⚠️", value=f"`{wc}/{mw}`", inline=True)
            e.add_field(name="📝 Reason", value=self.reason_input.value, inline=False)
            await interaction.response.send_message(embed=e, ephemeral=True)
            try:
                dm = discord.Embed(title="⚠️ Warning", description=f"Warned in **{interaction.guild.name}**", color=WARNING_COLOR)
                dm.add_field(name="Reason", value=self.reason_input.value)
                dm.add_field(name="Warns", value=f"`{wc}/{mw}`")
                await target.send(embed=dm)
            except:
                pass
            if s and wc >= mw:
                await self.cog.auto_punish(target, s, wc)

    class ClearWarnsModal(discord.ui.Modal, title="🗑️ Clear Warns"):
        uid_input = discord.ui.TextInput(label="User ID", placeholder="Right-click → Copy ID")

        async def on_submit(self, interaction):
            try:
                uid = int(self.uid_input.value)
            except:
                return await interaction.response.send_message("❌ Invalid!", ephemeral=True)
            count = await clear_warns(interaction.guild.id, uid)
            await interaction.response.send_message(
                embed=discord.Embed(title=f"✅ Cleared {count} warn(s)", color=SUCCESS_COLOR),
                ephemeral=True
            )

    class WhitelistAddModal(discord.ui.Modal, title="📋 Add to Whitelist"):
        type_input = discord.ui.TextInput(label="Type", placeholder="user / role / channel")
        id_input = discord.ui.TextInput(label="ID", placeholder="Right-click → Copy ID")

        async def on_submit(self, interaction):
            t = self.type_input.value.lower().strip()
            if t not in ("user", "role", "channel"):
                return await interaction.response.send_message("❌ Must be user/role/channel!", ephemeral=True)
            try:
                tid = int(self.id_input.value)
            except:
                return await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)
            ok = await add_whitelist(interaction.guild.id, t, tid, interaction.user.id)
            await interaction.response.send_message(
                embed=discord.Embed(title=f"✅ {t.title()} Whitelisted" if ok else "❌ Already whitelisted", color=SUCCESS_COLOR if ok else ERROR_COLOR),
                ephemeral=True
            )

    class WhitelistRemoveModal(discord.ui.Modal, title="📋 Remove from Whitelist"):
        type_input = discord.ui.TextInput(label="Type", placeholder="user / role / channel")
        id_input = discord.ui.TextInput(label="ID", placeholder="Right-click → Copy ID")

        async def on_submit(self, interaction):
            t = self.type_input.value.lower().strip()
            if t not in ("user", "role", "channel"):
                return await interaction.response.send_message("❌ Invalid type!", ephemeral=True)
            try:
                tid = int(self.id_input.value)
            except:
                return await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)
            ok = await remove_whitelist(interaction.guild.id, t, tid)
            await interaction.response.send_message(
                embed=discord.Embed(title="✅ Removed" if ok else "❌ Not Found", color=SUCCESS_COLOR if ok else ERROR_COLOR),
                ephemeral=True
            )

    # ═══════════════════════════════════════════════════════════
    #  SELECT MENUS
    # ═══════════════════════════════════════════════════════════

    class FilterSelect(discord.ui.Select):
        def __init__(self, cog):
            self.cog = cog
            super().__init__(
                placeholder="🔀 Toggle a filter on/off...",
                options=[
                    discord.SelectOption(label="Anti-Spam", value="anti_spam", emoji="💬", description="Message flood + duplicate detection"),
                    discord.SelectOption(label="Anti-Caps", value="anti_caps", emoji="🔠", description="Excessive uppercase"),
                    discord.SelectOption(label="Anti-Mention Spam", value="anti_mention_spam", emoji="📢", description="Too many @mentions"),
                    discord.SelectOption(label="Anti-Emoji Spam", value="anti_emoji_spam", emoji="😀", description="Too many emojis"),
                    discord.SelectOption(label="Anti-Newline Spam", value="anti_newline_spam", emoji="📝", description="Wall of text / line spam"),
                    discord.SelectOption(label="Anti-Invite", value="anti_invite", emoji="📨", description="Discord invite links"),
                    discord.SelectOption(label="Anti-Links", value="anti_link", emoji="🌐", description="Limit general links"),
                    discord.SelectOption(label="Anti-Zalgo", value="anti_zalgo", emoji="👾", description="Corrupted/glitch text"),
                    discord.SelectOption(label="Anti-Mass Ping", value="anti_massping", emoji="📣", description="@everyone / @here"),
                    discord.SelectOption(label="Bad Words Filter", value="bad_words_enabled", emoji="🚫", description="Multi-language profanity"),
                    discord.SelectOption(label="Blocked Links", value="blocked_links_enabled", emoji="🛑", description="Scam/phishing/NSFW links"),
                ],
                row=0
            )

        async def callback(self, interaction):
            s = await get_automod_settings(interaction.guild.id)
            if not s:
                return await interaction.response.send_message("❌ Run setup first!", ephemeral=True)
            key = self.values[0]
            cur = s.get(key, 0)
            nv = 0 if cur else 1
            await update_automod_setting(interaction.guild.id, key, nv)
            await self.cog.refresh_settings(interaction.guild.id)
            st = "✅ Enabled" if nv else "❌ Disabled"
            name = [o for o in self.options if o.value == key][0].label
            await interaction.response.send_message(
                embed=discord.Embed(title=f"🔀 {name}: {st}", color=SUCCESS_COLOR if nv else ERROR_COLOR),
                ephemeral=True
            )

    class PunishSelect(discord.ui.Select):
        def __init__(self, cog):
            self.cog = cog
            super().__init__(
                placeholder="🔨 Set punishment type...",
                options=[
                    discord.SelectOption(label="Mute (Timeout)", value="mute", emoji="🔇", description="Timeout the user"),
                    discord.SelectOption(label="Kick", value="kick", emoji="👢", description="Kick from server"),
                    discord.SelectOption(label="Ban", value="ban", emoji="🔨", description="Permanent ban"),
                ],
                row=1
            )

        async def callback(self, interaction):
            await update_automod_setting(interaction.guild.id, "warn_action", self.values[0])
            await self.cog.refresh_settings(interaction.guild.id)
            await interaction.response.send_message(
                embed=discord.Embed(title=f"🔨 Punishment → {self.values[0].title()}", color=SUCCESS_COLOR),
                ephemeral=True
            )

    # ═══════════════════════════════════════════════════════════
    #  PANEL COMMAND
    # ═══════════════════════════════════════════════════════════

    @app_commands.command(name="automod", description="🛡️ Open the Advanced AutoMod Panel")
    @app_commands.default_permissions(manage_guild=True)
    async def automod_panel(self, interaction: discord.Interaction):
        # Show plan info
        plan = await get_guild_plan(interaction.guild.id)
        plan_lim = get_plan_limits(plan)

        s = await get_automod_settings(interaction.guild.id)

        embed = discord.Embed(title="🛡️ AutoMod Management Panel", color=PANEL_COLOR)

        if s and s.get("enabled"):
            def t(v):
                return "✅" if v else "❌"

            ch = f"<#{s['log_channel_id']}>" if s["log_channel_id"] else "*Not set*"
            act = s["warn_action"].title()
            dur_min = s["warn_action_duration"] // 60

            # Count data
            custom_words = await self.get_words(interaction.guild.id)
            custom_links = await self.get_links(interaction.guild.id)
            wl = await get_whitelist(interaction.guild.id)

            embed.description = (
                f"**Status:** 🟢 Enabled | **Log:** {ch}\n"
                f"**Punishment:** `{s['max_warns']}` warns → `{act}`"
                + (f" (`{dur_min}` min)" if s["warn_action"] == "mute" else "") +
                f"\n**Data:** `{len(custom_words)}` words | `{len(custom_links)}` links | `{len(wl)}` whitelisted\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{t(s['anti_spam'])} **Anti-Spam** — flood + duplicates + repeated chars/words\n"
                f"{t(s['anti_caps'])} **Anti-Caps** — `{s['caps_percentage']}%` threshold\n"
                f"{t(s['anti_mention_spam'])} **Anti-Mention** — max `{s['max_mentions']}`\n"
                f"{t(s['anti_emoji_spam'])} **Anti-Emoji** — max `{s['max_emojis']}`\n"
                f"{t(s['anti_newline_spam'])} **Anti-Newline** — max `{s['max_lines']}` lines\n"
                f"{t(s['anti_invite'])} **Anti-Invite** — discord invite links\n"
                f"{t(s['anti_link'])} **Anti-Links** — max `{s['max_links']}` general links\n"
                f"{t(s['anti_zalgo'])} **Anti-Zalgo** — corrupted text\n"
                f"{t(s['anti_massping'])} **Anti-Mass Ping** — @everyone/@here\n"
                f"{t(s['bad_words_enabled'])} **Bad Words** — 7 languages + anti-evasion\n"
                f"{t(s.get('blocked_links_enabled', 1))} **Blocked Links** — scam/phishing/NSFW\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 **Plan:** {plan.title()} | "
                f"{'✅' if plan_lim.get('automod_full') else '🔒'} Full AutoMod | "
                f"{'✅' if plan_lim.get('automod_anti_invite') else '🔒'} Anti-Invite | "
                f"{'✅' if plan_lim.get('automod_bad_words') else '🔒'} Bad Words"
            )
        else:
            stats = get_stats()
            embed.description = (
                "AutoMod is **not configured** or **disabled**.\n\n"
                "Click **🛡️ Setup** to activate with:\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🚫 **{stats['total_words']}** bad words across **7 languages**\n"
                + "\n".join([f"  └ {lang}: `{count}`" for lang, count in stats['languages'].items()]) +
                f"\n\n🛑 **{stats['total_links']}** blocked domains\n"
                + "\n".join([f"  └ {cat}: `{count}`" for cat, count in stats['link_categories'].items()]) +
                f"\n\n✅ **{stats['total_allowed']}** allowed domains (bypass anti-link)\n"
                f"\n**15 active filters** with anti-evasion (leet speak, unicode, separators)"
            )

        embed.set_footer(text="Nexify AutoMod • Panel expires in 5 minutes")

        view = AutoModPanelView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ═══════════════════════════════════════════════════════════════
#  PANEL VIEW
# ═══════════════════════════════════════════════════════════════

class AutoModPanelView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog
        self.add_item(AutoMod.FilterSelect(cog))
        self.add_item(AutoMod.PunishSelect(cog))

    # Row 2 — Core Controls
    @discord.ui.button(label="Setup", style=discord.ButtonStyle.success, emoji="🛡️", row=2)
    async def setup_btn(self, interaction, btn):
        await interaction.response.send_modal(AutoMod.SetupModal(self.cog))

    @discord.ui.button(label="Enable", style=discord.ButtonStyle.success, emoji="🟢", row=2)
    async def enable_btn(self, interaction, btn):
        s = await get_automod_settings(interaction.guild.id)
        if not s:
            return await interaction.response.send_message("❌ Run Setup first!", ephemeral=True)
        await update_automod_setting(interaction.guild.id, "enabled", 1)
        await self.cog.refresh_settings(interaction.guild.id)
        await interaction.response.send_message(embed=discord.Embed(title="🟢 AutoMod Enabled", color=SUCCESS_COLOR), ephemeral=True)

    @discord.ui.button(label="Disable", style=discord.ButtonStyle.danger, emoji="🔴", row=2)
    async def disable_btn(self, interaction, btn):
        await update_automod_setting(interaction.guild.id, "enabled", 0)
        await self.cog.refresh_settings(interaction.guild.id)
        await interaction.response.send_message(embed=discord.Embed(title="🔴 AutoMod Disabled", color=ERROR_COLOR), ephemeral=True)

    @discord.ui.button(label="Config ①", style=discord.ButtonStyle.primary, emoji="⚙️", row=2)
    async def config1_btn(self, interaction, btn):
        await interaction.response.send_modal(AutoMod.ConfigModal(self.cog))

    @discord.ui.button(label="Config ②", style=discord.ButtonStyle.primary, emoji="🔧", row=2)
    async def config2_btn(self, interaction, btn):
        await interaction.response.send_modal(AutoMod.ConfigModal2(self.cog))

    # Row 3 — Words & Links
    @discord.ui.button(label="+ Words", style=discord.ButtonStyle.secondary, emoji="🚫", row=3)
    async def addword_btn(self, interaction, btn):
        await interaction.response.send_modal(AutoMod.AddWordModal(self.cog))

    @discord.ui.button(label="− Words", style=discord.ButtonStyle.secondary, emoji="✂️", row=3)
    async def rmword_btn(self, interaction, btn):
        await interaction.response.send_modal(AutoMod.RemoveWordModal(self.cog))

    @discord.ui.button(label="+ Links", style=discord.ButtonStyle.secondary, emoji="🔗", row=3)
    async def addlink_btn(self, interaction, btn):
        await interaction.response.send_modal(AutoMod.AddLinkModal(self.cog))

    @discord.ui.button(label="− Links", style=discord.ButtonStyle.secondary, emoji="🔗", row=3)
    async def rmlink_btn(self, interaction, btn):
        await interaction.response.send_modal(AutoMod.RemoveLinkModal(self.cog))

    @discord.ui.button(label="Whitelist +", style=discord.ButtonStyle.secondary, emoji="📋", row=3)
    async def wl_add_btn(self, interaction, btn):
        await interaction.response.send_modal(AutoMod.WhitelistAddModal())

    # Row 4 — Warns & Logs
    @discord.ui.button(label="Warn", style=discord.ButtonStyle.danger, emoji="⚠️", row=4)
    async def warn_btn(self, interaction, btn):
        await interaction.response.send_modal(AutoMod.ManualWarnModal(self.cog))

    @discord.ui.button(label="Check", style=discord.ButtonStyle.primary, emoji="📊", row=4)
    async def warncheck_btn(self, interaction, btn):
        await interaction.response.send_modal(AutoMod.WarnCheckModal())

    @discord.ui.button(label="Clear", style=discord.ButtonStyle.danger, emoji="🗑️", row=4)
    async def warnclear_btn(self, interaction, btn):
        await interaction.response.send_modal(AutoMod.ClearWarnsModal())

    @discord.ui.button(label="Whitelist −", style=discord.ButtonStyle.danger, emoji="📋", row=4)
    async def wl_rm_btn(self, interaction, btn):
        await interaction.response.send_modal(AutoMod.WhitelistRemoveModal())

    @discord.ui.button(label="Log", style=discord.ButtonStyle.secondary, emoji="📜", row=4)
    async def log_btn(self, interaction, btn):
        actions = await get_action_log(interaction.guild.id, limit=15)
        if not actions:
            return await interaction.response.send_message(
                embed=discord.Embed(title="📜 Log", description="*Empty*", color=WARNING_COLOR),
                ephemeral=True
            )
        txt = ""
        for a in actions:
            ts = a.get("created_at", "")[:16]
            txt += f"`{ts}` <@{a['user_id']}> **{a['action_type']}** — {a['reason']}\n"
        await interaction.response.send_message(
            embed=discord.Embed(title="📜 AutoMod Log", description=txt[:4000], color=AUTOMOD_COLOR),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(AutoMod(bot))