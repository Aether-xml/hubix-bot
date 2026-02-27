import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from typing import Literal, Optional
import aiohttp

from config import (
    SUCCESS_COLOR, ERROR_COLOR, EMBED_COLOR, UTILITY_COLOR, LOG_COLOR,
    get_plan_limits, get_plan_info
)
from utils.database import (
    check_feature, get_guild_plan,
    get_logging_settings, update_logging_setting,
    get_auto_role, set_auto_role, remove_auto_role,
    get_bot_customization, set_bot_customization, reset_bot_customization
)


async def send_upgrade_message(interaction: discord.Interaction, feature_name: str, current_plan: str):
    """Send an upgrade required embed."""
    plan_info = get_plan_info(current_plan)
    embed = discord.Embed(
        title="🔒 Upgrade Required",
        description=(
            f"**{feature_name}** is not available on your current plan.\n\n"
            f"**Current Plan:** {plan_info['emoji']} {plan_info['name']}\n\n"
            f"Use `/plan` to view available upgrades!"
        ),
        color=ERROR_COLOR
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


class Utility(commands.Cog):
    """🔧 Utility commands for server management"""

    def __init__(self, bot):
        self.bot = bot

    # ═══════════════════════════════════════════════════════════
    #  /ping — Bot Latency
    # ═══════════════════════════════════════════════════════════

    @app_commands.command(name="ping", description="🏓 Check bot latency")
    async def ping_cmd(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**Latency:** `{latency}ms`",
            color=SUCCESS_COLOR if latency < 200 else ERROR_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        await interaction.response.send_message(embed=embed)

    # ═══════════════════════════════════════════════════════════
    #  /serverinfo — Server Information
    # ═══════════════════════════════════════════════════════════

    @app_commands.command(name="serverinfo", description="📊 Show detailed server information")
    async def serverinfo_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild

        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles = len(guild.roles) - 1

        online = sum(1 for m in guild.members if m.status != discord.Status.offline)
        bots = sum(1 for m in guild.members if m.bot)
        humans = guild.member_count - bots

        embed = discord.Embed(
            title=f"📊 {guild.name}",
            color=UTILITY_COLOR,
            timestamp=datetime.now(timezone.utc)
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="👑 Owner", value=f"{guild.owner.mention}" if guild.owner else "Unknown", inline=True)
        embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="📅 Created", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)

        embed.add_field(name="👥 Members", value=f"Total: **{guild.member_count}**\nHumans: **{humans}** | Bots: **{bots}**", inline=True)
        embed.add_field(name="🟢 Online", value=f"**{online}**", inline=True)
        embed.add_field(name="🔒 Verification", value=f"`{guild.verification_level}`", inline=True)

        embed.add_field(
            name="📁 Channels",
            value=f"💬 Text: **{text_channels}** | 🔊 Voice: **{voice_channels}**\n📂 Categories: **{categories}**",
            inline=True
        )
        embed.add_field(name="🏷️ Roles", value=f"**{roles}**", inline=True)
        embed.add_field(name="😀 Emojis", value=f"**{len(guild.emojis)}**", inline=True)

        if guild.premium_tier > 0:
            embed.add_field(
                name="🚀 Boost",
                value=f"Level **{guild.premium_tier}** — **{guild.premium_subscription_count}** boosts",
                inline=False
            )

        if guild.banner:
            embed.set_image(url=guild.banner.url)

        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ═══════════════════════════════════════════════════════════
    #  /userinfo — User Information
    # ═══════════════════════════════════════════════════════════

    @app_commands.command(name="userinfo", description="👤 Show information about a user")
    @app_commands.describe(user="The user to get info about")
    async def userinfo_cmd(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        user = user or interaction.user

        roles = [r.mention for r in user.roles if r != interaction.guild.default_role]
        roles_text = ", ".join(roles[:10]) if roles else "None"
        if len(roles) > 10:
            roles_text += f" ... and {len(roles) - 10} more"

        embed = discord.Embed(
            title=f"👤 {user}",
            color=user.color if user.color != discord.Color.default() else UTILITY_COLOR,
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(name="🆔 User ID", value=f"`{user.id}`", inline=True)
        embed.add_field(name="📛 Nickname", value=f"`{user.nick or 'None'}`", inline=True)
        embed.add_field(name="🤖 Bot", value="Yes" if user.bot else "No", inline=True)

        embed.add_field(name="📅 Account Created", value=f"<t:{int(user.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="📥 Joined Server", value=f"<t:{int(user.joined_at.timestamp())}:R>" if user.joined_at else "Unknown", inline=True)

        if user.premium_since:
            embed.add_field(name="🚀 Boosting Since", value=f"<t:{int(user.premium_since.timestamp())}:R>", inline=True)

        embed.add_field(name=f"🏷️ Roles [{len(roles)}]", value=roles_text, inline=False)

        perms = []
        if user.guild_permissions.administrator:
            perms.append("Administrator")
        if user.guild_permissions.manage_guild:
            perms.append("Manage Server")
        if user.guild_permissions.manage_roles:
            perms.append("Manage Roles")
        if user.guild_permissions.manage_channels:
            perms.append("Manage Channels")
        if user.guild_permissions.ban_members:
            perms.append("Ban Members")
        if user.guild_permissions.kick_members:
            perms.append("Kick Members")

        if perms:
            embed.add_field(name="🔑 Key Permissions", value=", ".join(perms), inline=False)

        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ═══════════════════════════════════════════════════════════
    #  /avatar — User Avatar
    # ═══════════════════════════════════════════════════════════

    @app_commands.command(name="avatar", description="🖼️ Show a user's avatar")
    @app_commands.describe(user="The user to get avatar of")
    async def avatar_cmd(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        user = user or interaction.user

        embed = discord.Embed(
            title=f"🖼️ {user.display_name}'s Avatar",
            color=UTILITY_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_image(url=user.display_avatar.replace(size=1024).url)

        links = []
        for fmt in ["png", "jpg", "webp"]:
            links.append(f"[{fmt.upper()}]({user.display_avatar.replace(format=fmt, size=1024)})")
        if user.display_avatar.is_animated():
            links.append(f"[GIF]({user.display_avatar.replace(format='gif', size=1024)})")

        embed.add_field(name="🔗 Download", value=" | ".join(links), inline=False)
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ═══════════════════════════════════════════════════════════
    #  /banner — User Banner
    # ═══════════════════════════════════════════════════════════

    @app_commands.command(name="banner", description="🎨 Show a user's banner")
    @app_commands.describe(user="The user to get banner of")
    async def banner_cmd(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        user = user or interaction.user

        try:
            fetched = await self.bot.fetch_user(user.id)
        except Exception:
            return await interaction.response.send_message("❌ Could not fetch user!", ephemeral=True)

        if not fetched.banner:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ No Banner",
                    description=f"{user.mention} doesn't have a banner.",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        embed = discord.Embed(
            title=f"🎨 {user.display_name}'s Banner",
            color=UTILITY_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_image(url=fetched.banner.replace(size=1024).url)
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ═══════════════════════════════════════════════════════════
    #  /embed — Send Custom Embed
    # ═══════════════════════════════════════════════════════════

    @app_commands.command(name="embed", description="📨 Send a custom embed message")
    @app_commands.describe(channel="Channel to send the embed to")
    @app_commands.default_permissions(manage_messages=True)
    async def embed_cmd(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        allowed, plan = await check_feature(interaction.guild.id, "embed_editor")
        if not allowed:
            return await send_upgrade_message(interaction, "Embed Editor", plan)

        channel = channel or interaction.channel
        modal = SendEmbedModal(channel)
        await interaction.response.send_modal(modal)

    # ═══════════════════════════════════════════════════════════
    #  /editembed — Edit Existing Embed by Message ID
    # ═══════════════════════════════════════════════════════════

    @app_commands.command(name="editembed", description="✏️ Edit an existing embed message by ID")
    @app_commands.describe(
        message_id="The message ID to edit",
        channel="The channel containing the message (defaults to current channel)"
    )
    @app_commands.default_permissions(manage_messages=True)
    async def edit_embed_cmd(self, interaction: discord.Interaction, message_id: str, channel: Optional[discord.TextChannel] = None):
        allowed, plan = await check_feature(interaction.guild.id, "embed_editor")
        if not allowed:
            return await send_upgrade_message(interaction, "Embed Editor", plan)

        try:
            msg_id = int(message_id)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid message ID!", ephemeral=True)

        search_channel = channel or interaction.channel
        try:
            target_msg = await search_channel.fetch_message(msg_id)
        except discord.NotFound:
            return await interaction.response.send_message(f"❌ Message not found in {search_channel.mention}!", ephemeral=True)
        except Exception:
            return await interaction.response.send_message("❌ Could not fetch the message!", ephemeral=True)

        if target_msg.author != interaction.guild.me:
            return await interaction.response.send_message("❌ I can only edit messages sent by me!", ephemeral=True)

        if not target_msg.embeds:
            return await interaction.response.send_message("❌ That message has no embeds!", ephemeral=True)

        old_embed = target_msg.embeds[0]
        modal = EditEmbedModal(target_msg, old_embed)
        await interaction.response.send_modal(modal)

    # ═══════════════════════════════════════════════════════════
    #  /nuke — Nuke Channel
    # ═══════════════════════════════════════════════════════════

    @app_commands.command(name="nuke", description="💣 Nuke a channel (clone & delete)")
    @app_commands.describe(reason="Reason for nuking")
    @app_commands.default_permissions(manage_channels=True)
    async def nuke_cmd(self, interaction: discord.Interaction, reason: Optional[str] = "No reason provided"):
        embed = discord.Embed(
            title="💣 Nuke Confirmation",
            description=(
                f"Are you sure you want to nuke {interaction.channel.mention}?\n\n"
                f"**This will:**\n"
                f"• Delete this channel\n"
                f"• Create an identical clone\n"
                f"• All messages will be lost\n\n"
                f"**Reason:** {reason}"
            ),
            color=ERROR_COLOR
        )
        view = NukeConfirmView(interaction.channel, reason)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ═══════════════════════════════════════════════════════════
    #  /logging — Logging Setup
    # ═══════════════════════════════════════════════════════════

    @app_commands.command(name="logging", description="📋 Setup audit logging for your server")
    @app_commands.default_permissions(administrator=True)
    async def logging_cmd(self, interaction: discord.Interaction):
        allowed, plan = await check_feature(interaction.guild.id, "logging_enabled")
        if not allowed:
            return await send_upgrade_message(interaction, "Logging", plan)

        settings = await get_logging_settings(interaction.guild.id)
        limits = get_plan_limits(plan)

        embed = discord.Embed(
            title="📋 Logging Settings",
            description="Configure what events are logged in your server.",
            color=LOG_COLOR,
            timestamp=datetime.now(timezone.utc)
        )

        enabled = settings["enabled"] if settings else False
        log_ch = interaction.guild.get_channel(settings["log_channel_id"]) if settings and settings.get("log_channel_id") else None

        embed.add_field(name="📊 Status", value=f"{'🟢 Enabled' if enabled else '🔴 Disabled'}", inline=True)
        embed.add_field(name="📍 Log Channel", value=log_ch.mention if log_ch else "`Not set`", inline=True)
        embed.add_field(name="📋 Plan", value=f"{get_plan_info(plan)['emoji']} {get_plan_info(plan)['name']}", inline=True)

        log_types = {
            "log_messages": ("🗑️ Messages", "Edit/Delete"),
            "log_members": ("👥 Members", "Join/Leave/Nick"),
            "log_roles": ("🏷️ Roles", "Create/Delete/Assign"),
            "log_channels": ("📁 Channels", "Create/Delete"),
            "log_bans": ("🔨 Bans", "Ban/Unban"),
            "log_voice": ("🔊 Voice", "Join/Leave/Move"),
        }

        status_text = ""
        for key, (name, desc) in log_types.items():
            plan_allowed = limits.get(key, False)
            if not plan_allowed:
                status_text += f"🔒 {name} — *{desc}* (Upgrade required)\n"
            else:
                s_enabled = settings.get(key, 1) if settings else True
                status_text += f"{'✅' if s_enabled else '❌'} {name} — *{desc}*\n"

        embed.add_field(name="📋 Log Types", value=status_text, inline=False)
        embed.set_footer(text="Use the buttons below to configure")

        view = LoggingSetupView(interaction.guild.id, plan)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ═══════════════════════════════════════════════════════════
    #  /autorole — Auto Role Setup
    # ═══════════════════════════════════════════════════════════

    @app_commands.command(name="autorole", description="🏷️ Auto-assign a role to new members")
    @app_commands.describe(
        action="Set or remove auto role",
        role="The role to auto-assign (for 'set' action)"
    )
    @app_commands.default_permissions(manage_roles=True)
    async def autorole_cmd(self, interaction: discord.Interaction,
                           action: Literal["set", "remove", "status"],
                           role: Optional[discord.Role] = None):
        allowed, plan = await check_feature(interaction.guild.id, "auto_role")
        if not allowed:
            return await send_upgrade_message(interaction, "Auto Role", plan)

        if action == "set":
            if not role:
                return await interaction.response.send_message("❌ Please specify a role!", ephemeral=True)
            if role >= interaction.guild.me.top_role:
                return await interaction.response.send_message("❌ That role is higher than my highest role!", ephemeral=True)

            await set_auto_role(interaction.guild.id, role.id)
            embed = discord.Embed(
                title="✅ Auto Role Set",
                description=f"New members will automatically receive {role.mention}",
                color=SUCCESS_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "remove":
            success = await remove_auto_role(interaction.guild.id)
            if success:
                embed = discord.Embed(title="✅ Auto Role Removed", color=SUCCESS_COLOR)
            else:
                embed = discord.Embed(title="❌ No auto role was set", color=ERROR_COLOR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "status":
            ar = await get_auto_role(interaction.guild.id)
            if ar:
                role_obj = interaction.guild.get_role(ar["role_id"])
                embed = discord.Embed(
                    title="🏷️ Auto Role Status",
                    description=f"**Role:** {role_obj.mention if role_obj else '`Deleted Role`'}\n**Enabled:** {'✅ Yes' if ar['enabled'] else '❌ No'}",
                    color=UTILITY_COLOR
                )
            else:
                embed = discord.Embed(
                    title="🏷️ Auto Role Status",
                    description="No auto role configured.",
                    color=UTILITY_COLOR
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # ═══════════════════════════════════════════════════════════
    #  /botcustomize — Bot Customization (Premium/Business)
    # ═══════════════════════════════════════════════════════════

    @app_commands.command(name="botcustomize", description="🎨 Customize the bot for your server")
    @app_commands.default_permissions(administrator=True)
    async def customize_cmd(self, interaction: discord.Interaction):
        plan = await get_guild_plan(interaction.guild.id)
        limits = get_plan_limits(plan)

        can_nick = limits.get("bot_nickname", False)
        can_avatar = limits.get("bot_avatar", False)

        if not can_nick and not can_avatar:
            return await send_upgrade_message(interaction, "Bot Customization", plan)

        custom = await get_bot_customization(interaction.guild.id)
        me = interaction.guild.me

        embed = discord.Embed(
            title="🎨 Bot Customization",
            description="Personalize Hubix for your server!",
            color=UTILITY_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="📛 Current Nickname", value=f"`{me.nick or me.name}`", inline=True)
        embed.add_field(name="🖼️ Server Avatar", value="Custom" if (custom and custom.get("custom_avatar_url")) else "Default", inline=True)
        embed.add_field(
            name="🔓 Available",
            value=f"{'✅' if can_nick else '🔒'} Nickname\n{'✅' if can_avatar else '🔒'} Server Avatar",
            inline=False
        )
        embed.set_thumbnail(url=me.display_avatar.url)

        view = BotCustomizeView(interaction.guild.id, can_nick, can_avatar)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ═══════════════════════════════════════════════════════════
    #  EVENT: Auto Role on Member Join
    # ═══════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        # --- Auto Role ---
        ar = await get_auto_role(member.guild.id)
        if ar and ar.get("enabled"):
            role = member.guild.get_role(ar["role_id"])
            if role and role < member.guild.me.top_role:
                try:
                    await member.add_roles(role, reason="Hubix Auto Role")
                except Exception:
                    pass

        # --- Logging: Member Join ---
        await self._log_event(member.guild, "log_members", discord.Embed(
            title="👤 Member Joined",
            description=f"{member.mention} ({member})",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc)
        ).add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
         .add_field(name="📅 Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
         .set_thumbnail(url=member.display_avatar.url))

    # ═══════════════════════════════════════════════════════════
    #  EVENT: Member Leave
    # ═══════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return

        roles = [r.mention for r in member.roles if r != member.guild.default_role]
        roles_text = ", ".join(roles[:10]) if roles else "None"

        await self._log_event(member.guild, "log_members", discord.Embed(
            title="👤 Member Left",
            description=f"{member.mention} ({member})",
            color=ERROR_COLOR,
            timestamp=datetime.now(timezone.utc)
        ).add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
         .add_field(name="🏷️ Roles", value=roles_text, inline=False)
         .set_thumbnail(url=member.display_avatar.url))

    # ═══════════════════════════════════════════════════════════
    #  EVENT: Message Delete
    # ═══════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        content = message.content[:1024] if message.content else "*No text content*"

        await self._log_event(message.guild, "log_messages", discord.Embed(
            title="🗑️ Message Deleted",
            description=f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}",
            color=ERROR_COLOR,
            timestamp=datetime.now(timezone.utc)
        ).add_field(name="📝 Content", value=content, inline=False)
         .set_thumbnail(url=message.author.display_avatar.url))

    # ═══════════════════════════════════════════════════════════
    #  EVENT: Message Edit
    # ═══════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.author.bot:
            return
        if before.content == after.content:
            return

        before_content = before.content[:512] if before.content else "*Empty*"
        after_content = after.content[:512] if after.content else "*Empty*"

        await self._log_event(before.guild, "log_messages", discord.Embed(
            title="✏️ Message Edited",
            description=f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n[Jump to message]({after.jump_url})",
            color=0xFFA500,
            timestamp=datetime.now(timezone.utc)
        ).add_field(name="📝 Before", value=before_content, inline=False)
         .add_field(name="📝 After", value=after_content, inline=False)
         .set_thumbnail(url=before.author.display_avatar.url))

    # ═══════════════════════════════════════════════════════════
    #  EVENT: Member Ban
    # ═══════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        await self._log_event(guild, "log_bans", discord.Embed(
            title="🔨 Member Banned",
            description=f"{user.mention} ({user})",
            color=ERROR_COLOR,
            timestamp=datetime.now(timezone.utc)
        ).add_field(name="🆔 ID", value=f"`{user.id}`", inline=True)
         .set_thumbnail(url=user.display_avatar.url))

    # ═══════════════════════════════════════════════════════════
    #  EVENT: Member Unban
    # ═══════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        await self._log_event(guild, "log_bans", discord.Embed(
            title="🔓 Member Unbanned",
            description=f"{user.mention} ({user})",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc)
        ).add_field(name="🆔 ID", value=f"`{user.id}`", inline=True)
         .set_thumbnail(url=user.display_avatar.url))

    # ═══════════════════════════════════════════════════════════
    #  EVENT: Role Create
    # ═══════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        await self._log_event(role.guild, "log_roles", discord.Embed(
            title="🏷️ Role Created",
            description=f"{role.mention} (`{role.name}`)",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc)
        ).add_field(name="🆔 ID", value=f"`{role.id}`", inline=True)
         .add_field(name="🎨 Color", value=f"`{role.color}`", inline=True))

    # ═══════════════════════════════════════════════════════════
    #  EVENT: Role Delete
    # ═══════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await self._log_event(role.guild, "log_roles", discord.Embed(
            title="🏷️ Role Deleted",
            description=f"`{role.name}`",
            color=ERROR_COLOR,
            timestamp=datetime.now(timezone.utc)
        ).add_field(name="🆔 ID", value=f"`{role.id}`", inline=True))

    # ═══════════════════════════════════════════════════════════
    #  EVENT: Channel Create
    # ═══════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if not hasattr(channel, 'guild') or not channel.guild:
            return

        await self._log_event(channel.guild, "log_channels", discord.Embed(
            title="📁 Channel Created",
            description=f"{channel.mention} (`{channel.name}`)",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc)
        ).add_field(name="🆔 ID", value=f"`{channel.id}`", inline=True)
         .add_field(name="📂 Type", value=f"`{channel.type}`", inline=True))

    # ═══════════════════════════════════════════════════════════
    #  EVENT: Channel Delete
    # ═══════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if not hasattr(channel, 'guild') or not channel.guild:
            return

        await self._log_event(channel.guild, "log_channels", discord.Embed(
            title="📁 Channel Deleted",
            description=f"`{channel.name}`",
            color=ERROR_COLOR,
            timestamp=datetime.now(timezone.utc)
        ).add_field(name="🆔 ID", value=f"`{channel.id}`", inline=True)
         .add_field(name="📂 Type", value=f"`{channel.type}`", inline=True))

    # ═══════════════════════════════════════════════════════════
    #  EVENT: Voice State Update
    # ═══════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        if not before.channel and after.channel:
            embed = discord.Embed(
                title="🔊 Voice Join",
                description=f"{member.mention} joined {after.channel.mention}",
                color=SUCCESS_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
        elif before.channel and not after.channel:
            embed = discord.Embed(
                title="🔇 Voice Leave",
                description=f"{member.mention} left {before.channel.mention}",
                color=ERROR_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
        elif before.channel and after.channel and before.channel != after.channel:
            embed = discord.Embed(
                title="🔀 Voice Move",
                description=f"{member.mention}\n{before.channel.mention} → {after.channel.mention}",
                color=0xFFA500,
                timestamp=datetime.now(timezone.utc)
            )
        else:
            return

        embed.set_thumbnail(url=member.display_avatar.url)
        await self._log_event(member.guild, "log_voice", embed)

    # ═══════════════════════════════════════════════════════════
    #  EVENT: Member Role Update
    # ═══════════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.bot:
            return

        # Role changes
        if before.roles != after.roles:
            added = [r.mention for r in after.roles if r not in before.roles]
            removed = [r.mention for r in before.roles if r not in after.roles]

            if added or removed:
                embed = discord.Embed(
                    title="🏷️ Member Roles Updated",
                    description=f"{after.mention} ({after})",
                    color=0xFFA500,
                    timestamp=datetime.now(timezone.utc)
                )
                if added:
                    embed.add_field(name="➕ Added", value=", ".join(added), inline=False)
                if removed:
                    embed.add_field(name="➖ Removed", value=", ".join(removed), inline=False)
                embed.set_thumbnail(url=after.display_avatar.url)
                await self._log_event(after.guild, "log_roles", embed)

        # Nickname changes
        if before.nick != after.nick:
            embed = discord.Embed(
                title="📛 Nickname Changed",
                description=f"{after.mention} ({after})",
                color=0xFFA500,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Before", value=f"`{before.nick or 'None'}`", inline=True)
            embed.add_field(name="After", value=f"`{after.nick or 'None'}`", inline=True)
            embed.set_thumbnail(url=after.display_avatar.url)
            await self._log_event(after.guild, "log_members", embed)

    # ═══════════════════════════════════════════════════════════
    #  HELPER: Log Event to Channel
    # ═══════════════════════════════════════════════════════════

    async def _log_event(self, guild: discord.Guild, log_type: str, embed: discord.Embed):
        """Send a log embed to the configured log channel if enabled."""
        try:
            settings = await get_logging_settings(guild.id)
            if not settings:
                return
            if not settings.get("enabled"):
                return
            if not settings.get(log_type, 1):
                return

            channel_id = settings.get("log_channel_id")
            if not channel_id:
                return

            # Plan check
            plan = await get_guild_plan(guild.id)
            limits = get_plan_limits(plan)
            if not limits.get(log_type, False):
                return

            channel = guild.get_channel(channel_id)
            if not channel:
                return

            await channel.send(embed=embed)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
#  SEND EMBED MODAL
# ═══════════════════════════════════════════════════════════════

class SendEmbedModal(discord.ui.Modal, title="📨 Create Embed"):
    title_input = discord.ui.TextInput(
        label="Title",
        placeholder="Embed title",
        required=False,
        max_length=256
    )
    desc_input = discord.ui.TextInput(
        label="Description",
        placeholder="Embed description",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=4000
    )
    color_input = discord.ui.TextInput(
        label="Color (hex, e.g. FF5733)",
        placeholder="5865F2",
        required=False,
        max_length=6
    )
    image_input = discord.ui.TextInput(
        label="Image URL",
        placeholder="https://...",
        required=False
    )
    thumb_input = discord.ui.TextInput(
        label="Thumbnail URL",
        placeholder="https://...",
        required=False
    )

    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction):
        try:
            color = int(self.color_input.value, 16) if self.color_input.value else EMBED_COLOR
        except ValueError:
            color = EMBED_COLOR

        e = discord.Embed(
            title=self.title_input.value or None,
            description=self.desc_input.value or None,
            color=color
        )

        if self.image_input.value:
            e.set_image(url=self.image_input.value)
        if self.thumb_input.value:
            e.set_thumbnail(url=self.thumb_input.value)

        e.set_footer(text=f"Sent by {interaction.user}", icon_url=interaction.user.display_avatar.url)

        await self.channel.send(embed=e)
        await interaction.response.send_message(
            embed=discord.Embed(title="✅ Embed Sent!", description=f"Sent to {self.channel.mention}", color=SUCCESS_COLOR),
            ephemeral=True
        )


# ═══════════════════════════════════════════════════════════════
#  EDIT EMBED MODAL
# ═══════════════════════════════════════════════════════════════

class EditEmbedModal(discord.ui.Modal, title="✏️ Edit Embed"):
    def __init__(self, target_msg, old_embed):
        super().__init__()
        self.target_msg = target_msg
        self.title_input = discord.ui.TextInput(
            label="Title",
            placeholder="Embed title",
            default=old_embed.title or "",
            required=False,
            max_length=256
        )
        self.desc_input = discord.ui.TextInput(
            label="Description",
            placeholder="Embed description",
            default=old_embed.description or "",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=4000
        )
        self.color_input = discord.ui.TextInput(
            label="Color (hex, e.g. FF5733)",
            placeholder="5865F2",
            default=hex(old_embed.color.value)[2:].upper() if old_embed.color else "",
            required=False,
            max_length=6
        )
        self.image_input = discord.ui.TextInput(
            label="Image URL",
            placeholder="https://...",
            default=old_embed.image.url if old_embed.image else "",
            required=False
        )
        self.thumb_input = discord.ui.TextInput(
            label="Thumbnail URL",
            placeholder="https://...",
            default=old_embed.thumbnail.url if old_embed.thumbnail else "",
            required=False
        )
        self.add_item(self.title_input)
        self.add_item(self.desc_input)
        self.add_item(self.color_input)
        self.add_item(self.image_input)
        self.add_item(self.thumb_input)

    async def on_submit(self, interaction):
        try:
            color = int(self.color_input.value, 16) if self.color_input.value else EMBED_COLOR
        except ValueError:
            color = EMBED_COLOR

        new_embed = discord.Embed(
            title=self.title_input.value or None,
            description=self.desc_input.value or None,
            color=color
        )

        old_embed = self.target_msg.embeds[0]
        for field in old_embed.fields:
            new_embed.add_field(name=field.name, value=field.value, inline=field.inline)

        if old_embed.footer:
            new_embed.set_footer(text=old_embed.footer.text, icon_url=old_embed.footer.icon_url)
        if old_embed.author:
            new_embed.set_author(name=old_embed.author.name, icon_url=old_embed.author.icon_url, url=old_embed.author.url)

        if self.image_input.value:
            new_embed.set_image(url=self.image_input.value)
        if self.thumb_input.value:
            new_embed.set_thumbnail(url=self.thumb_input.value)

        try:
            await self.target_msg.edit(embed=new_embed)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Embed Updated!",
                    description=f"Message edited in {self.target_msg.channel.mention}",
                    color=SUCCESS_COLOR
                ),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to edit: {e}", ephemeral=True)


# ═══════════════════════════════════════════════════════════════
#  LOGGING SETUP VIEW
# ═══════════════════════════════════════════════════════════════

class LoggingChannelModal(discord.ui.Modal, title="📍 Set Log Channel"):
    channel_input = discord.ui.TextInput(
        label="Channel ID",
        placeholder="Right-click a channel → Copy Channel ID"
    )

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction):
        try:
            channel_id = int(self.channel_input.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Invalid channel ID!", ephemeral=True)

        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            return await interaction.response.send_message("❌ Channel not found!", ephemeral=True)

        await update_logging_setting(self.guild_id, "log_channel_id", channel_id)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Log Channel Set",
                description=f"Logs will be sent to {channel.mention}",
                color=SUCCESS_COLOR
            ),
            ephemeral=True
        )


class LoggingSetupView(discord.ui.View):
    def __init__(self, guild_id, plan):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.plan = plan

    @discord.ui.button(label="Enable/Disable", style=discord.ButtonStyle.primary, emoji="🔄", row=0)
    async def toggle_btn(self, interaction, btn):
        settings = await get_logging_settings(self.guild_id)
        current = settings["enabled"] if settings else 0
        new_val = 0 if current else 1
        await update_logging_setting(self.guild_id, "enabled", new_val)
        status = "🟢 Enabled" if new_val else "🔴 Disabled"
        await interaction.response.send_message(
            embed=discord.Embed(title=f"📋 Logging {status}", color=SUCCESS_COLOR if new_val else ERROR_COLOR),
            ephemeral=True
        )

    @discord.ui.button(label="Set Channel", style=discord.ButtonStyle.primary, emoji="📍", row=0)
    async def channel_btn(self, interaction, btn):
        await interaction.response.send_modal(LoggingChannelModal(self.guild_id))

    @discord.ui.button(label="Toggle Messages", style=discord.ButtonStyle.secondary, emoji="🗑️", row=1)
    async def msg_btn(self, interaction, btn):
        limits = get_plan_limits(self.plan)
        if not limits.get("log_messages"):
            return await interaction.response.send_message("🔒 Upgrade required for message logging!", ephemeral=True)
        settings = await get_logging_settings(self.guild_id)
        current = settings.get("log_messages", 1) if settings else 1
        await update_logging_setting(self.guild_id, "log_messages", 0 if current else 1)
        await interaction.response.send_message(f"{'✅ Enabled' if not current else '❌ Disabled'} message logging", ephemeral=True)

    @discord.ui.button(label="Toggle Members", style=discord.ButtonStyle.secondary, emoji="👥", row=1)
    async def member_btn(self, interaction, btn):
        limits = get_plan_limits(self.plan)
        if not limits.get("log_members"):
            return await interaction.response.send_message("🔒 Upgrade required!", ephemeral=True)
        settings = await get_logging_settings(self.guild_id)
        current = settings.get("log_members", 1) if settings else 1
        await update_logging_setting(self.guild_id, "log_members", 0 if current else 1)
        await interaction.response.send_message(f"{'✅ Enabled' if not current else '❌ Disabled'} member logging", ephemeral=True)

    @discord.ui.button(label="Toggle Roles", style=discord.ButtonStyle.secondary, emoji="🏷️", row=1)
    async def role_btn(self, interaction, btn):
        limits = get_plan_limits(self.plan)
        if not limits.get("log_roles"):
            return await interaction.response.send_message("🔒 Upgrade to Premium/Business for role logging!", ephemeral=True)
        settings = await get_logging_settings(self.guild_id)
        current = settings.get("log_roles", 1) if settings else 1
        await update_logging_setting(self.guild_id, "log_roles", 0 if current else 1)
        await interaction.response.send_message(f"{'✅ Enabled' if not current else '❌ Disabled'} role logging", ephemeral=True)

    @discord.ui.button(label="Toggle Channels", style=discord.ButtonStyle.secondary, emoji="📁", row=2)
    async def channel_log_btn(self, interaction, btn):
        limits = get_plan_limits(self.plan)
        if not limits.get("log_channels"):
            return await interaction.response.send_message("🔒 Upgrade to Premium/Business!", ephemeral=True)
        settings = await get_logging_settings(self.guild_id)
        current = settings.get("log_channels", 1) if settings else 1
        await update_logging_setting(self.guild_id, "log_channels", 0 if current else 1)
        await interaction.response.send_message(f"{'✅ Enabled' if not current else '❌ Disabled'} channel logging", ephemeral=True)

    @discord.ui.button(label="Toggle Bans", style=discord.ButtonStyle.secondary, emoji="🔨", row=2)
    async def ban_btn(self, interaction, btn):
        limits = get_plan_limits(self.plan)
        if not limits.get("log_bans"):
            return await interaction.response.send_message("🔒 Upgrade required!", ephemeral=True)
        settings = await get_logging_settings(self.guild_id)
        current = settings.get("log_bans", 1) if settings else 1
        await update_logging_setting(self.guild_id, "log_bans", 0 if current else 1)
        await interaction.response.send_message(f"{'✅ Enabled' if not current else '❌ Disabled'} ban logging", ephemeral=True)

    @discord.ui.button(label="Toggle Voice", style=discord.ButtonStyle.secondary, emoji="🔊", row=2)
    async def voice_btn(self, interaction, btn):
        limits = get_plan_limits(self.plan)
        if not limits.get("log_voice"):
            return await interaction.response.send_message("🔒 Upgrade to Premium/Business!", ephemeral=True)
        settings = await get_logging_settings(self.guild_id)
        current = settings.get("log_voice", 1) if settings else 1
        await update_logging_setting(self.guild_id, "log_voice", 0 if current else 1)
        await interaction.response.send_message(f"{'✅ Enabled' if not current else '❌ Disabled'} voice logging", ephemeral=True)


# ═══════════════════════════════════════════════════════════════
#  BOT CUSTOMIZATION VIEW
# ═══════════════════════════════════════════════════════════════

class NicknameModal(discord.ui.Modal, title="📛 Set Bot Nickname"):
    nick_input = discord.ui.TextInput(
        label="Nickname",
        placeholder="Leave empty to reset",
        required=False,
        max_length=32
    )

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction):
        nick = self.nick_input.value.strip() or None
        try:
            await interaction.guild.me.edit(nick=nick, reason="Bot Customization")
            await set_bot_customization(self.guild_id, "custom_nickname", nick)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Nickname Updated",
                    description=f"Bot nickname set to `{nick or 'Default'}`",
                    color=SUCCESS_COLOR
                ),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)


class AvatarModal(discord.ui.Modal, title="🖼️ Set Bot Server Avatar"):
    url_input = discord.ui.TextInput(
        label="Image URL",
        placeholder="https://... (PNG/JPG, leave empty to reset)",
        required=False
    )

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction):
        url = self.url_input.value.strip()
        try:
            if url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            return await interaction.response.send_message("❌ Could not download image!", ephemeral=True)
                        data = await resp.read()
                await interaction.guild.me.edit(avatar=data, reason="Bot Customization")
                await set_bot_customization(self.guild_id, "custom_avatar_url", url)
                await interaction.response.send_message(
                    embed=discord.Embed(title="✅ Server Avatar Updated", color=SUCCESS_COLOR),
                    ephemeral=True
                )
            else:
                await interaction.guild.me.edit(avatar=None, reason="Bot Customization Reset")
                await set_bot_customization(self.guild_id, "custom_avatar_url", None)
                await interaction.response.send_message(
                    embed=discord.Embed(title="✅ Server Avatar Reset", color=SUCCESS_COLOR),
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)


class BotCustomizeView(discord.ui.View):
    def __init__(self, guild_id, can_nick, can_avatar):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        if not can_nick:
            self.nick_btn.disabled = True
            self.nick_btn.label = "Nickname 🔒"
        if not can_avatar:
            self.avatar_btn.disabled = True
            self.avatar_btn.label = "Server Avatar 🔒"

    @discord.ui.button(label="Change Nickname", style=discord.ButtonStyle.primary, emoji="📛", row=0)
    async def nick_btn(self, interaction, btn):
        await interaction.response.send_modal(NicknameModal(self.guild_id))

    @discord.ui.button(label="Change Server Avatar", style=discord.ButtonStyle.primary, emoji="🖼️", row=0)
    async def avatar_btn(self, interaction, btn):
        await interaction.response.send_modal(AvatarModal(self.guild_id))

    @discord.ui.button(label="Reset All", style=discord.ButtonStyle.danger, emoji="🔄", row=0)
    async def reset_btn(self, interaction, btn):
        try:
            await interaction.guild.me.edit(nick=None, reason="Reset Customization")
        except Exception:
            pass
        await reset_bot_customization(self.guild_id)
        await interaction.response.send_message(
            embed=discord.Embed(title="✅ Customization Reset", color=SUCCESS_COLOR),
            ephemeral=True
        )


# ═══════════════════════════════════════════════════════════════
#  NUKE CONFIRM VIEW
# ═══════════════════════════════════════════════════════════════

class NukeConfirmView(discord.ui.View):
    def __init__(self, channel, reason):
        super().__init__(timeout=15)
        self.channel = channel
        self.reason = reason

    @discord.ui.button(label="Confirm Nuke", style=discord.ButtonStyle.danger, emoji="💣")
    async def confirm(self, interaction: discord.Interaction, button):
        self.stop()
        ch = self.channel
        try:
            new_ch = await ch.clone(reason=self.reason)
            await new_ch.edit(position=ch.position)
            await ch.delete(reason=self.reason)

            e = discord.Embed(
                title="💣 Channel Nuked",
                description=f"This channel was nuked by {interaction.user.mention}.\n**Reason:** {self.reason}",
                color=ERROR_COLOR
            )
            await new_ch.send(embed=e)
        except Exception:
            await interaction.response.send_message("❌ Failed to nuke!", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.response.edit_message(
            embed=discord.Embed(title="❌ Nuke Cancelled", color=ERROR_COLOR),
            view=None
        )


async def setup(bot):
    await bot.add_cog(Utility(bot))