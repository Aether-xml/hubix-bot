import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

from config import OWNER_IDS, ERROR_COLOR, SUCCESS_COLOR

# ═══════════════════════════════════════════════════════════════
#  COLOR THEME
# ═══════════════════════════════════════════════════════════════

HUBIX_BLACK = 0x2B2D31
HUBIX_PURPLE = 0x9B59B6
HUBIX_DARK_PURPLE = 0x7B2FBE
HUBIX_ACCENT = 0xB266FF


# ═══════════════════════════════════════════════════════════════
#  VERIFY PERSISTENT VIEW
# ═══════════════════════════════════════════════════════════════

class VerifyButtonView(discord.ui.View):
    """Persistent verify button — survives bot restart."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.primary,
        emoji="✅",
        custom_id="hubix:verify"
    )
    async def verify_btn(self, interaction: discord.Interaction, btn: discord.ui.Button):
        verified_role = discord.utils.get(interaction.guild.roles, name="✅ Verified")
        if not verified_role:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Error",
                    description="Verified role not found. Contact an admin.",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        if verified_role in interaction.user.roles:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Already Verified",
                    description="You are already verified!",
                    color=HUBIX_PURPLE
                ),
                ephemeral=True
            )

        try:
            await interaction.user.add_roles(verified_role, reason="Verification")
            # Also add Member role
            member_role = discord.utils.get(interaction.guild.roles, name="👤 Member")
            if member_role:
                await interaction.user.add_roles(member_role, reason="Verification")

            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Verified!",
                    description="You have been verified! You can now access all channels.",
                    color=SUCCESS_COLOR
                ),
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Error",
                    description="I don't have permission to give you the role.",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )


# ═══════════════════════════════════════════════════════════════
#  SERVER SETUP COG
# ═══════════════════════════════════════════════════════════════

class ServerSetup(commands.Cog):
    """🏗️ Official Server Setup (Owner Only, One-Time Use)"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        print("[COG] Server Setup module loaded.")

    # ─── ROLE CREATION ────────────────────────────────────────

    async def create_roles(self, guild: discord.Guild):
        """Create all roles in order (bottom to top)."""
        roles = {}

        role_list = [
            # (name, color, hoist, mentionable)
            ("👤 Member", 0x95A5A6, False, False),
            ("✅ Verified", 0x2ECC71, False, False),
            ("💎 Basic", 0x3498DB, True, False),
            ("⭐ Premium", 0xF1C40F, True, False),
            ("🚀 Business", 0xE91E63, True, False),
            ("💼 Staff", 0xE67E22, True, True),
            ("👮 Moderator", 0x3498DB, True, True),
            ("🛡️ Admin", 0xE74C3C, True, True),
            ("👑 Owner", 0x9B59B6, True, False),
        ]

        for name, color, hoist, mentionable in role_list:
            existing = discord.utils.get(guild.roles, name=name)
            if existing:
                roles[name] = existing
            else:
                try:
                    role = await guild.create_role(
                        name=name,
                        color=discord.Color(color),
                        hoist=hoist,
                        mentionable=mentionable,
                        reason="Hubix Server Setup"
                    )
                    roles[name] = role
                except Exception as e:
                    print(f"[SETUP] Failed to create role {name}: {e}")

        return roles

    # ─── CATEGORY & CHANNEL CREATION ─────────────────────────

    async def create_channels(self, guild: discord.Guild, roles: dict):
        """Create all categories and channels with proper permissions."""
        channels = {}
        bot_member = guild.me

        everyone = guild.default_role
        verified = roles.get("✅ Verified")
        member = roles.get("👤 Member")
        staff = roles.get("💼 Staff")
        mod = roles.get("👮 Moderator")
        admin = roles.get("🛡️ Admin")
        owner_role = roles.get("👑 Owner")
        premium = roles.get("⭐ Premium")
        basic = roles.get("💎 Basic")
        business = roles.get("🚀 Business")

        # ── Helper: base deny everyone, allow verified ──
        def verified_perms():
            overwrites = {
                everyone: discord.PermissionOverwrite(view_channel=False),
                bot_member: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True,
                    embed_links=True, attach_files=True, manage_channels=True
                ),
            }
            if verified:
                overwrites[verified] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
            return overwrites

        def readonly_perms():
            overwrites = {
                everyone: discord.PermissionOverwrite(view_channel=False),
                bot_member: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True,
                    embed_links=True, attach_files=True, manage_channels=True
                ),
            }
            if verified:
                overwrites[verified] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=False, read_message_history=True
                )
            return overwrites

        def staff_perms():
            overwrites = {
                everyone: discord.PermissionOverwrite(view_channel=False),
                bot_member: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True,
                    embed_links=True, attach_files=True, manage_channels=True
                ),
            }
            if staff:
                overwrites[staff] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
            if mod:
                overwrites[mod] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    manage_messages=True
                )
            if admin:
                overwrites[admin] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    manage_messages=True, manage_channels=True
                )
            if owner_role:
                overwrites[owner_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    manage_messages=True, manage_channels=True
                )
            return overwrites

        def admin_perms():
            overwrites = {
                everyone: discord.PermissionOverwrite(view_channel=False),
                bot_member: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True,
                    embed_links=True, attach_files=True, manage_channels=True
                ),
            }
            if admin:
                overwrites[admin] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    manage_messages=True, manage_channels=True
                )
            if owner_role:
                overwrites[owner_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    manage_messages=True, manage_channels=True
                )
            return overwrites

        def premium_perms():
            overwrites = {
                everyone: discord.PermissionOverwrite(view_channel=False),
                bot_member: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True,
                    embed_links=True, attach_files=True, manage_channels=True
                ),
            }
            if premium:
                overwrites[premium] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
            if basic:
                overwrites[basic] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
            if business:
                overwrites[business] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
            if staff:
                overwrites[staff] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
            if admin:
                overwrites[admin] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
            if owner_role:
                overwrites[owner_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
            return overwrites

        def verify_channel_perms():
            overwrites = {
                everyone: discord.PermissionOverwrite(
                    view_channel=True, send_messages=False, read_message_history=True
                ),
                bot_member: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True,
                    embed_links=True, attach_files=True, manage_channels=True
                ),
            }
            if verified:
                overwrites[verified] = discord.PermissionOverwrite(view_channel=False)
            return overwrites

        def logs_perms():
            overwrites = {
                everyone: discord.PermissionOverwrite(view_channel=False),
                bot_member: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True,
                    embed_links=True, attach_files=True, manage_channels=True
                ),
            }
            if admin:
                overwrites[admin] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=False, read_message_history=True
                )
            if owner_role:
                overwrites[owner_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
            return overwrites

        # ════════════════════════════════════════════════════════
        #  CREATE CATEGORIES & CHANNELS
        # ════════════════════════════════════════════════════════

        # ── VERIFY (top, everyone can see) ──
        cat_verify = await guild.create_category(
            "═══ VERIFY ═══",
            overwrites=verify_channel_perms(),
            reason="Hubix Setup"
        )
        channels["verify"] = await cat_verify.create_text_channel(
            "verify", overwrites=verify_channel_perms(), reason="Hubix Setup"
        )

        # ── INFORMATION ──
        cat_info = await guild.create_category(
            "═══ INFORMATION ═══",
            overwrites=readonly_perms(),
            reason="Hubix Setup"
        )
        channels["announcements"] = await cat_info.create_text_channel(
            "📢│announcements", overwrites=readonly_perms(), reason="Hubix Setup"
        )
        channels["rules"] = await cat_info.create_text_channel(
            "📋│rules", overwrites=readonly_perms(), reason="Hubix Setup"
        )
        channels["changelog"] = await cat_info.create_text_channel(
            "📝│changelog", overwrites=readonly_perms(), reason="Hubix Setup"
        )
        channels["links"] = await cat_info.create_text_channel(
            "🔗│links", overwrites=readonly_perms(), reason="Hubix Setup"
        )

        # ── COMMUNITY ──
        cat_community = await guild.create_category(
            "═══ COMMUNITY ═══",
            overwrites=verified_perms(),
            reason="Hubix Setup"
        )
        channels["general"] = await cat_community.create_text_channel(
            "💬│general", overwrites=verified_perms(), reason="Hubix Setup"
        )
        channels["media"] = await cat_community.create_text_channel(
            "🖼️│media", overwrites=verified_perms(), reason="Hubix Setup"
        )
        channels["bot-commands"] = await cat_community.create_text_channel(
            "🤖│bot-commands", overwrites=verified_perms(), reason="Hubix Setup"
        )
        channels["giveaways"] = await cat_community.create_text_channel(
            "🎉│giveaways", overwrites=verified_perms(), reason="Hubix Setup"
        )

        # ── SUPPORT ──
        cat_support = await guild.create_category(
            "═══ SUPPORT ═══",
            overwrites=verified_perms(),
            reason="Hubix Setup"
        )
        channels["faq"] = await cat_support.create_text_channel(
            "❓│faq", overwrites=readonly_perms(), reason="Hubix Setup"
        )
        channels["documentation"] = await cat_support.create_text_channel(
            "📖│documentation", overwrites=readonly_perms(), reason="Hubix Setup"
        )
        channels["create-ticket"] = await cat_support.create_text_channel(
            "🎫│create-ticket",
            overwrites={
                everyone: discord.PermissionOverwrite(view_channel=False),
                bot_member: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True,
                    embed_links=True, attach_files=True, manage_channels=True
                ),
                **({verified: discord.PermissionOverwrite(
                    view_channel=True, send_messages=False, read_message_history=True
                )} if verified else {})
            },
            reason="Hubix Setup"
        )

        # ── PREMIUM ──
        cat_premium = await guild.create_category(
            "═══ PREMIUM ═══",
            overwrites=verified_perms(),
            reason="Hubix Setup"
        )
        channels["claim-premium"] = await cat_premium.create_text_channel(
            "🔑│claim-premium",
            overwrites={
                everyone: discord.PermissionOverwrite(view_channel=False),
                bot_member: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True,
                    embed_links=True, attach_files=True, manage_channels=True
                ),
                **({verified: discord.PermissionOverwrite(
                    view_channel=True, send_messages=False, read_message_history=True
                )} if verified else {})
            },
            reason="Hubix Setup"
        )
        channels["premium-chat"] = await cat_premium.create_text_channel(
            "⭐│premium-chat", overwrites=premium_perms(), reason="Hubix Setup"
        )
        channels["premium-support"] = await cat_premium.create_text_channel(
            "📦│premium-support", overwrites=premium_perms(), reason="Hubix Setup"
        )

        # ── SHOWCASE ──
        cat_showcase = await guild.create_category(
            "═══ SHOWCASE ═══",
            overwrites=readonly_perms(),
            reason="Hubix Setup"
        )
        channels["bot-showcase"] = await cat_showcase.create_text_channel(
            "🖥️│bot-showcase", overwrites=readonly_perms(), reason="Hubix Setup"
        )
        channels["reviews"] = await cat_showcase.create_text_channel(
            "⭐│reviews", overwrites=readonly_perms(), reason="Hubix Setup"
        )

        # ── STAFF ──
        cat_staff = await guild.create_category(
            "═══ STAFF ═══",
            overwrites=staff_perms(),
            reason="Hubix Setup"
        )
        channels["staff-chat"] = await cat_staff.create_text_channel(
            "📋│staff-chat", overwrites=staff_perms(), reason="Hubix Setup"
        )
        channels["staff-logs"] = await cat_staff.create_text_channel(
            "📊│staff-logs", overwrites=staff_perms(), reason="Hubix Setup"
        )
        channels["admin-chat"] = await cat_staff.create_text_channel(
            "🔒│admin-chat", overwrites=admin_perms(), reason="Hubix Setup"
        )

        # ── LOGS ──
        cat_logs = await guild.create_category(
            "═══ LOGS ═══",
            overwrites=logs_perms(),
            reason="Hubix Setup"
        )
        channels["mod-logs"] = await cat_logs.create_text_channel(
            "📝│mod-logs", overwrites=logs_perms(), reason="Hubix Setup"
        )
        channels["join-leave"] = await cat_logs.create_text_channel(
            "📨│join-leave", overwrites=logs_perms(), reason="Hubix Setup"
        )
        channels["bot-logs"] = await cat_logs.create_text_channel(
            "📊│bot-logs", overwrites=logs_perms(), reason="Hubix Setup"
        )

        # ── TICKETS (empty category) ──
        cat_tickets = await guild.create_category(
            "═══ TICKETS ═══",
            overwrites={
                everyone: discord.PermissionOverwrite(view_channel=False),
                bot_member: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True,
                    manage_channels=True, embed_links=True, attach_files=True
                ),
                **({staff: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )} if staff else {}),
                **({mod: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    manage_messages=True
                )} if mod else {}),
                **({admin: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    manage_messages=True, manage_channels=True
                )} if admin else {}),
            },
            reason="Hubix Setup"
        )
        channels["ticket_category"] = cat_tickets

        # ── VOICE ──
        cat_voice = await guild.create_category(
            "═══ VOICE ═══",
            overwrites=verified_perms(),
            reason="Hubix Setup"
        )
        channels["general-voice"] = await cat_voice.create_voice_channel(
            "🔊 General Voice", overwrites=verified_perms(), reason="Hubix Setup"
        )
        channels["support-voice"] = await cat_voice.create_voice_channel(
            "🔊 Support Voice", overwrites=verified_perms(), reason="Hubix Setup"
        )
        channels["staff-voice"] = await cat_voice.create_voice_channel(
            "🔊 Staff Voice", overwrites=staff_perms(), reason="Hubix Setup"
        )

        return channels

    # ─── SEND EMBEDS ──────────────────────────────────────────

    async def send_verify_embed(self, channel: discord.TextChannel, guild: discord.Guild):
        """Send the verify embed with button."""
        embed = discord.Embed(
            title="✅ Verification Required",
            description=(
                "Welcome to **Hubix**!\n\n"
                "To access the server, you need to verify yourself.\n"
                "Click the button below to get started.\n\n"
                "By verifying, you agree to our server rules."
            ),
            color=HUBIX_PURPLE,
            timestamp=datetime.now(timezone.utc)
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text="Hubix • Verification")

        view = VerifyButtonView()
        await channel.send(embed=embed, view=view)

    async def send_rules_embed(self, channel: discord.TextChannel, guild: discord.Guild):
        """Send the rules embeds."""
        # Header
        header = discord.Embed(
            title="📋 Server Rules",
            description=(
                "Welcome to the official **Hubix** server!\n"
                "Please read and follow all rules to keep this community safe and enjoyable.\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=HUBIX_PURPLE
        )
        if guild.icon:
            header.set_thumbnail(url=guild.icon.url)
        await channel.send(embed=header)

        # Rule 1-3
        rules_1 = discord.Embed(color=HUBIX_BLACK)
        rules_1.add_field(
            name="1️⃣ Be Respectful",
            value=(
                "• Treat everyone with respect\n"
                "• No harassment, hate speech, or discrimination\n"
                "• No personal attacks or toxic behavior\n"
                "• Keep discussions civil and constructive"
            ),
            inline=False
        )
        rules_1.add_field(
            name="2️⃣ No Spam",
            value=(
                "• No message spam, emoji spam, or sticker spam\n"
                "• No repeated messages or copy-paste flooding\n"
                "• No excessive caps or unicode abuse\n"
                "• Keep conversations in the appropriate channels"
            ),
            inline=False
        )
        rules_1.add_field(
            name="3️⃣ No NSFW Content",
            value=(
                "• No NSFW images, videos, links, or discussions\n"
                "• No suggestive or inappropriate content\n"
                "• No NSFW profile pictures or usernames"
            ),
            inline=False
        )
        await channel.send(embed=rules_1)

        # Rule 4-6
        rules_2 = discord.Embed(color=HUBIX_BLACK)
        rules_2.add_field(
            name="4️⃣ No Advertising",
            value=(
                "• No self-promotion or advertising without permission\n"
                "• No Discord server invites in chat\n"
                "• No DM advertising to members\n"
                "• Partnerships must be approved by staff"
            ),
            inline=False
        )
        rules_2.add_field(
            name="5️⃣ No Scamming or Phishing",
            value=(
                "• No scam links, phishing attempts, or malware\n"
                "• No fake giveaways or fraudulent offers\n"
                "• No impersonating staff or other members\n"
                "• Report suspicious activity to staff immediately"
            ),
            inline=False
        )
        rules_2.add_field(
            name="6️⃣ English Only",
            value=(
                "• Please communicate in English in all channels\n"
                "• This ensures everyone can understand and participate\n"
                "• Use translation tools if needed"
            ),
            inline=False
        )
        await channel.send(embed=rules_2)

        # Rule 7-9
        rules_3 = discord.Embed(color=HUBIX_BLACK)
        rules_3.add_field(
            name="7️⃣ Use Channels Properly",
            value=(
                "• Use the correct channel for your topic\n"
                "• Bot commands go in <#bot-commands>\n"
                "• Support questions go in tickets\n"
                "• Off-topic discussions in general"
            ),
            inline=False
        )
        rules_3.add_field(
            name="8️⃣ Follow Discord ToS",
            value=(
                "• Follow [Discord Terms of Service](https://discord.com/terms)\n"
                "• Follow [Discord Community Guidelines](https://discord.com/guidelines)\n"
                "• You must be 13+ to use Discord"
            ),
            inline=False
        )
        rules_3.add_field(
            name="9️⃣ Staff Decisions are Final",
            value=(
                "• Respect staff decisions and instructions\n"
                "• If you disagree, create a ticket to discuss\n"
                "• Do not argue with moderators in public channels\n"
                "• False reports will result in warnings"
            ),
            inline=False
        )
        await channel.send(embed=rules_3)

        # Footer
        footer = discord.Embed(
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ **Breaking these rules will result in warnings, mutes, kicks, or bans.**\n\n"
                "📩 If you see someone breaking the rules, create a ticket or ping a staff member.\n\n"
                "*Last updated: " + datetime.now(timezone.utc).strftime("%B %d, %Y") + "*"
            ),
            color=HUBIX_PURPLE
        )
        footer.set_footer(text="Hubix • Rules")
        await channel.send(embed=footer)

    async def send_faq_embed(self, channel: discord.TextChannel, guild: discord.Guild):
        """Send FAQ embeds."""
        header = discord.Embed(
            title="❓ Frequently Asked Questions",
            description="Find answers to the most common questions about Hubix below.",
            color=HUBIX_PURPLE
        )
        if guild.icon:
            header.set_thumbnail(url=guild.icon.url)
        await channel.send(embed=header)

        faq_1 = discord.Embed(color=HUBIX_BLACK)
        faq_1.add_field(
            name="🤖 What is Hubix?",
            value=(
                "Hubix is an all-in-one Discord bot that provides:\n"
                "• 🛒 **Shop & Order System** — Sell products directly in Discord\n"
                "• 🎫 **Ticket System** — Professional support tickets\n"
                "• 🎉 **Giveaway System** — Create and manage giveaways\n"
                "• 📨 **Invite Tracking** — Track and reward invites\n"
                "• 🛡️ **AutoMod** — Advanced auto-moderation\n"
                "• 🔧 **Utility** — Essential server tools"
            ),
            inline=False
        )
        faq_1.add_field(
            name="📥 How do I add Hubix to my server?",
            value=(
                "1. Click the bot's invite link\n"
                "2. Select your server\n"
                "3. Authorize the required permissions\n"
                "4. Start using `/` commands!"
            ),
            inline=False
        )
        faq_1.add_field(
            name="💰 Is Hubix free?",
            value=(
                "Yes! Hubix has a **free plan** with basic features.\n"
                "For advanced features, check out our premium plans:\n\n"
                "🆓 **Free** — Basic features\n"
                "💎 **Basic** — $8/mo — Shop, AutoMod filters, Invite leaderboard\n"
                "⭐ **Premium** — $15/mo — All features, Reviews, Transcripts\n"
                "🚀 **Business** — $25/mo — Everything + Multi-server support"
            ),
            inline=False
        )
        await channel.send(embed=faq_1)

        faq_2 = discord.Embed(color=HUBIX_BLACK)
        faq_2.add_field(
            name="🔑 How do I claim a premium key?",
            value=(
                "1. Go to the <#claim-premium> channel\n"
                "2. Click the **Claim Premium** button\n"
                "3. Enter your license key\n"
                "4. Enter the Server ID where you want to activate\n"
                "5. Done! Your plan is now active."
            ),
            inline=False
        )
        faq_2.add_field(
            name="🆔 How do I find my Server ID?",
            value=(
                "1. Enable **Developer Mode** in Discord Settings → Advanced\n"
                "2. Right-click your server name\n"
                "3. Click **Copy Server ID**"
            ),
            inline=False
        )
        faq_2.add_field(
            name="🎫 How do I get support?",
            value=(
                "1. Go to the <#create-ticket> channel\n"
                "2. Click the ticket button to create a support ticket\n"
                "3. Describe your issue and wait for a staff response\n\n"
                "**Response times:**\n"
                "• 🚀 Business: Priority support (< 1 hour)\n"
                "• ⭐ Premium: Fast support (< 4 hours)\n"
                "• 💎 Basic: Standard support (< 12 hours)\n"
                "• 🆓 Free: Community support (< 24 hours)"
            ),
            inline=False
        )
        await channel.send(embed=faq_2)

        faq_3 = discord.Embed(color=HUBIX_BLACK)
        faq_3.add_field(
            name="📋 What permissions does Hubix need?",
            value=(
                "Hubix needs the following permissions to function:\n"
                "• `Manage Channels` — Create ticket/order channels\n"
                "• `Manage Roles` — Assign roles\n"
                "• `Manage Messages` — AutoMod, transcripts\n"
                "• `Send Messages` & `Embed Links` — Core functionality\n"
                "• `View Audit Log` — Invite tracking\n"
                "• `Kick/Ban Members` — AutoMod actions"
            ),
            inline=False
        )
        faq_3.add_field(
            name="⏰ What happens when my subscription expires?",
            value=(
                "• Your server will automatically downgrade to the **Free** plan\n"
                "• Premium features will be disabled\n"
                "• Your data (products, orders, etc.) will be preserved\n"
                "• You can re-activate anytime with a new key"
            ),
            inline=False
        )
        faq_3.add_field(
            name="🔄 Can I transfer my plan to another server?",
            value="Currently, plans are tied to a specific server and cannot be transferred. Contact staff if you need help.",
            inline=False
        )
        await channel.send(embed=faq_3)

        footer = discord.Embed(
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "Still have questions? Create a ticket in <#create-ticket>!"
            ),
            color=HUBIX_PURPLE
        )
        footer.set_footer(text="Hubix • FAQ")
        await channel.send(embed=footer)

    async def send_showcase_embed(self, channel: discord.TextChannel, guild: discord.Guild):
        """Send bot showcase embeds."""
        header = discord.Embed(
            title="🖥️ Hubix — Feature Showcase",
            description=(
                "Discover everything Hubix can do for your server!\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=HUBIX_PURPLE
        )
        if guild.icon:
            header.set_thumbnail(url=guild.icon.url)
        await channel.send(embed=header)

        # Shop System
        shop = discord.Embed(
            title="🛒 Shop & Order System",
            description=(
                "Turn your Discord server into a professional storefront!\n\n"
                "**Features:**\n"
                "• 📦 **Product Management** — Add, edit, categorize products\n"
                "• 💳 **Multiple Payment Methods** — Crypto, PayPal, Gift Cards\n"
                "• 📋 **Order Channels** — Auto-created private order channels\n"
                "• ⭐ **Review System** — Customers can leave reviews\n"
                "• 👤 **Customer Profiles** — Track customer history\n"
                "• 🚫 **Blacklist System** — Block problem customers\n"
                "• 📊 **Analytics** — Revenue tracking and order stats\n"
                "• ⚡ **Quick-Add** — Paste formatted text to add products fast"
            ),
            color=0xF1C40F
        )
        await channel.send(embed=shop)

        # Ticket System
        tickets = discord.Embed(
            title="🎫 Ticket System",
            description=(
                "Professional support ticket management.\n\n"
                "**Features:**\n"
                "• 📁 **Categories** — Multiple ticket categories\n"
                "• 👋 **Claim System** — Staff can claim tickets\n"
                "• ⚡ **Priority Levels** — Low, Normal, High, Urgent\n"
                "• 📝 **Transcripts** — Save ticket conversations\n"
                "• ⏰ **Auto-Close** — Close inactive tickets automatically\n"
                "• 🎨 **Custom Welcome** — Custom messages per category"
            ),
            color=0xEB459E
        )
        await channel.send(embed=tickets)

        # Giveaway System
        giveaway = discord.Embed(
            title="🎉 Giveaway System",
            description=(
                "Create exciting giveaways for your community!\n\n"
                "**Features:**\n"
                "• ⏱️ **Timed Giveaways** — Set custom durations\n"
                "• 🎯 **Role Requirements** — Require specific roles to enter\n"
                "• 🏆 **Multiple Winners** — Pick multiple winners\n"
                "• 🔄 **Reroll** — Reroll winners if needed\n"
                "• 📊 **Entry Tracking** — See who entered"
            ),
            color=0x5865F2
        )
        await channel.send(embed=giveaway)

        # AutoMod
        automod = discord.Embed(
            title="🛡️ AutoMod System",
            description=(
                "Advanced automatic moderation to keep your server safe.\n\n"
                "**15 Filters Including:**\n"
                "• 🚫 Anti-Spam, Anti-Invite, Anti-Link\n"
                "• 🔤 Bad Word Filter (7 languages built-in)\n"
                "• 🔗 Blocked Links (phishing, scam, NSFW)\n"
                "• 📝 Anti-Caps, Anti-Zalgo, Anti-Mass Ping\n"
                "• 🔍 **Anti-Evasion** — Detects leet speak & unicode tricks\n"
                "• ⚠️ **Warn System** — Auto-punish after X warns\n"
                "• ✅ **Whitelist** — Exempt users, roles, channels"
            ),
            color=0xFF6B35
        )
        await channel.send(embed=automod)

        # Invite Tracking
        invites = discord.Embed(
            title="📨 Invite Tracking",
            description=(
                "Track and reward member invites.\n\n"
                "**Features:**\n"
                "• 📊 **Leaderboard** — See top inviters\n"
                "• 📝 **Join/Leave Logs** — Track who invited who\n"
                "• 🔍 **Who Invited** — Check any member's inviter\n"
                "• 📈 **Stats** — Total, active, and left invites"
            ),
            color=0x2EAADC
        )
        await channel.send(embed=invites)

        # Plans
        plans = discord.Embed(
            title="💎 Premium Plans",
            description=(
                "Choose the plan that fits your needs!\n\n"
                "🆓 **Free** — Basic features to get started\n"
                "💎 **Basic** ($8/mo) — Shop, AutoMod, Invite Leaderboard\n"
                "⭐ **Premium** ($15/mo) — All features, Reviews, Transcripts\n"
                "🚀 **Business** ($25/mo) — Everything + Multi-server\n\n"
                "Get your key in <#claim-premium>!"
            ),
            color=HUBIX_DARK_PURPLE
        )
        await channel.send(embed=plans)

        footer = discord.Embed(
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "Ready to get started? Add Hubix to your server today! 🚀\n"
                "Need help? Create a ticket in <#create-ticket>"
            ),
            color=HUBIX_PURPLE
        )
        footer.set_footer(text="Hubix • Bot Showcase")
        await channel.send(embed=footer)

    async def send_claim_embed(self, channel: discord.TextChannel, guild: discord.Guild):
        """Send the claim premium embed with persistent button."""
        from cogs.subscription import ClaimButtonView

        embed = discord.Embed(
            title="🔑 Claim Your Premium",
            description=(
                "Have a license key? Click the button below to redeem it!\n\n"
                "**How it works:**\n"
                "1️⃣ Click **Claim Premium** below\n"
                "2️⃣ Enter your license key\n"
                "3️⃣ Enter the Server ID where you want to activate\n"
                "4️⃣ Enjoy your premium features! 🚀\n\n"
                "*License keys are single-use and plan-specific.*"
            ),
            color=HUBIX_PURPLE,
            timestamp=datetime.now(timezone.utc)
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text="Hubix • Premium Licensing")

        view = ClaimButtonView()
        await channel.send(embed=embed, view=view)

    async def send_links_embed(self, channel: discord.TextChannel, guild: discord.Guild):
        """Send the links embed."""
        embed = discord.Embed(
            title="🔗 Important Links",
            description=(
                "**🤖 Bot Invite:**\n"
                "> [Click here to invite Hubix](https://discord.com/oauth2/authorize)\n\n"
                "**🌐 Website:**\n"
                "> Coming soon...\n\n"
                "**📖 Documentation:**\n"
                "> Coming soon...\n\n"
                "**💬 Support Server:**\n"
                "> You're already here! 🎉\n\n"
                "**⭐ Reviews:**\n"
                "> Leave a review after purchasing!"
            ),
            color=HUBIX_PURPLE
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text="Hubix • Links")
        await channel.send(embed=embed)

    # ─── DELETE EXISTING CHANNELS ─────────────────────────────

    async def cleanup_server(self, guild: discord.Guild):
        """Delete all existing channels and categories."""
        for channel in guild.channels:
            try:
                await channel.delete(reason="Hubix Setup — Cleanup")
            except:
                pass

    # ─── MAIN SETUP COMMAND ───────────────────────────────────

    @app_commands.command(name="setupserver", description="🏗️ Setup the official Hubix server (Owner Only)")
    @app_commands.describe(confirm="Type 'CONFIRM' to proceed — this will DELETE all existing channels!")
    async def setup_server(self, interaction: discord.Interaction, confirm: str):
        if interaction.user.id not in OWNER_IDS:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Access Denied",
                    description="This command is only for the bot owner.",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        if confirm != "CONFIRM":
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="⚠️ Confirmation Required",
                    description=(
                        "This will **DELETE ALL existing channels** and rebuild the server from scratch!\n\n"
                        "Use `/setupserver confirm:CONFIRM` to proceed."
                    ),
                    color=0xFEE75C
                ),
                ephemeral=True
            )

        # Respond immediately, then use DM for progress since channels will be deleted
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🏗️ Setting Up Server...",
                description="Progress will be sent to your DMs. Please wait...",
                color=HUBIX_PURPLE
            ),
            ephemeral=True
        )

        guild = interaction.guild
        user = interaction.user

        # Open DM for progress
        try:
            dm = await user.create_dm()
            progress_msg = await dm.send(
                embed=discord.Embed(
                    title="🏗️ Step 1/6 — Cleaning Up...",
                    description=f"Deleting existing channels in **{guild.name}**...",
                    color=HUBIX_PURPLE
                )
            )
        except discord.Forbidden:
            return  # Can't DM user

        try:
            # Step 1: Cleanup
            await self.cleanup_server(guild)

            # Step 2: Create Roles
            await progress_msg.edit(
                embed=discord.Embed(
                    title="🏗️ Step 2/6 — Creating Roles...",
                    description="Setting up roles...",
                    color=HUBIX_PURPLE
                )
            )
            roles = await self.create_roles(guild)

            # Assign Owner role to the person running the command
            owner_role = roles.get("👑 Owner")
            if owner_role:
                try:
                    await user.add_roles(owner_role, reason="Server Setup")
                except:
                    pass

            # Step 3: Create Channels
            await progress_msg.edit(
                embed=discord.Embed(
                    title="🏗️ Step 3/6 — Creating Channels...",
                    description="Setting up categories and channels...",
                    color=HUBIX_PURPLE
                )
            )
            channels = await self.create_channels(guild, roles)

            # Step 4: Send Embeds
            await progress_msg.edit(
                embed=discord.Embed(
                    title="🏗️ Step 4/6 — Sending Content...",
                    description="Setting up verify, rules, FAQ...",
                    color=HUBIX_PURPLE
                )
            )

            # Verify
            if channels.get("verify"):
                await self.send_verify_embed(channels["verify"], guild)

            # Rules
            if channels.get("rules"):
                await self.send_rules_embed(channels["rules"], guild)

            # Links
            if channels.get("links"):
                await self.send_links_embed(channels["links"], guild)

            # FAQ
            if channels.get("faq"):
                await self.send_faq_embed(channels["faq"], guild)

            # Step 5: Showcase & Claim
            await progress_msg.edit(
                embed=discord.Embed(
                    title="🏗️ Step 5/6 — Setting Up Panels...",
                    description="Showcase, Claim Premium...",
                    color=HUBIX_PURPLE
                )
            )

            # Bot Showcase
            if channels.get("bot-showcase"):
                await self.send_showcase_embed(channels["bot-showcase"], guild)

            # Claim Premium
            if channels.get("claim-premium"):
                await self.send_claim_embed(channels["claim-premium"], guild)

            # Step 6: Final
            await progress_msg.edit(
                embed=discord.Embed(
                    title="🏗️ Step 6/6 — Finishing Up...",
                    description="Almost done...",
                    color=HUBIX_PURPLE
                )
            )

            # Set server name if needed
            try:
                if guild.name != "Hubix":
                    await guild.edit(name="Hubix", reason="Server Setup")
            except:
                pass

            # Send completion message in general
            if channels.get("general"):
                complete_embed = discord.Embed(
                    title="🎉 Server Setup Complete!",
                    description=(
                        "The **Hubix** official server has been set up successfully!\n\n"
                        "**Created:**\n"
                        f"• 🏷️ {len(roles)} roles\n"
                        f"• 📁 {len([c for c in channels.values() if isinstance(c, (discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel))])} channels\n"
                        "• ✅ Verify system\n"
                        "• 📋 Rules\n"
                        "• ❓ FAQ\n"
                        "• 🖥️ Bot showcase\n"
                        "• 🔑 Claim premium panel\n\n"
                        "Welcome to Hubix! 🚀"
                    ),
                    color=SUCCESS_COLOR,
                    timestamp=datetime.now(timezone.utc)
                )
                if guild.icon:
                    complete_embed.set_thumbnail(url=guild.icon.url)
                await channels["general"].send(embed=complete_embed)

            # Final DM
            await progress_msg.edit(
                embed=discord.Embed(
                    title="✅ Setup Complete!",
                    description=(
                        f"The **Hubix** server has been set up successfully!\n\n"
                        f"**Created:**\n"
                        f"• 🏷️ {len(roles)} roles\n"
                        f"• 📁 {len(channels)} channels/categories\n"
                        f"• ✅ Verify system\n"
                        f"• 📋 Rules & FAQ\n"
                        f"• 🖥️ Bot showcase\n"
                        f"• 🔑 Claim premium panel\n\n"
                        f"You can now remove this cog with:\n"
                        f"`/unloadsetup`"
                    ),
                    color=SUCCESS_COLOR,
                    timestamp=datetime.now(timezone.utc)
                )
            )

        except Exception as e:
            try:
                await progress_msg.edit(
                    embed=discord.Embed(
                        title="❌ Setup Failed!",
                        description=f"An error occurred:\n```{str(e)[:1000]}```",
                        color=ERROR_COLOR
                    )
                )
            except:
                pass

    # ─── UNLOAD SETUP COG ────────────────────────────────────

    @app_commands.command(name="unloadsetup", description="🗑️ Unload the server setup module")
    async def unload_setup(self, interaction: discord.Interaction):
        if interaction.user.id not in OWNER_IDS:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Access Denied",
                    description="This command is only for the bot owner.",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        try:
            await self.bot.unload_extension("cogs.server_setup")
            await self.bot.tree.sync()
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Setup Module Unloaded",
                    description="The server setup module has been unloaded. You can delete `cogs/server_setup.py`.",
                    color=SUCCESS_COLOR
                ),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Error",
                    description=f"```{e}```",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(ServerSetup(bot))