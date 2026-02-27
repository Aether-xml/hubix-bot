import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta, timezone
from typing import Optional
import io

from utils.database import (
    get_ticket_settings, create_ticket_settings, update_ticket_setting,
    increment_ticket_counter, add_ticket_category, get_ticket_categories,
    remove_ticket_category, get_ticket_category_by_name,
    create_ticket, get_ticket_by_channel, get_open_tickets_by_user,
    get_all_open_tickets, close_ticket, claim_ticket, set_ticket_priority,
    get_ticket_stats, save_ticket_message, get_ticket_messages
)
from config import (
    EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR,
    TICKET_COLOR, PANEL_COLOR, get_plan_limits
)
from utils.database import get_guild_plan


# ═══════════════════════════════════════════════════════════════
#  TRANSCRIPT GENERATOR
# ═══════════════════════════════════════════════════════════════

async def generate_transcript(ticket: dict, messages: list[dict], guild: discord.Guild) -> str:
    """Generate an HTML transcript for a ticket."""
    user = guild.get_member(ticket["user_id"])
    user_name = str(user) if user else f"Unknown ({ticket['user_id']})"

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Ticket #{ticket['ticket_number']} — {guild.name}</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; background: #36393f; color: #dcddde; margin: 0; padding: 20px; }}
.header {{ background: #2f3136; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
.header h1 {{ color: #fff; margin: 0; font-size: 24px; }}
.header p {{ color: #b9bbbe; margin: 5px 0; }}
.message {{ display: flex; padding: 8px 16px; margin: 2px 0; }}
.message:hover {{ background: #32353b; }}
.avatar {{ width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; background: #5865f2; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; flex-shrink: 0; }}
.content {{ flex: 1; }}
.username {{ color: #fff; font-weight: 600; font-size: 14px; }}
.timestamp {{ color: #72767d; font-size: 12px; margin-left: 8px; }}
.text {{ color: #dcddde; font-size: 14px; margin-top: 4px; white-space: pre-wrap; word-break: break-word; }}
.info {{ background: #2f3136; padding: 15px; border-radius: 8px; margin-top: 20px; }}
.info p {{ margin: 4px 0; color: #b9bbbe; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
.open {{ background: #57f287; color: #000; }}
.closed {{ background: #ed4245; color: #fff; }}
</style>
</head>
<body>
<div class="header">
<h1>📋 Ticket #{ticket['ticket_number']} — {ticket['category_name']}</h1>
<p><strong>Server:</strong> {guild.name}</p>
<p><strong>Created by:</strong> {user_name}</p>
<p><strong>Created:</strong> {ticket['created_at']}</p>
<p><strong>Status:</strong> <span class="badge {'closed' if ticket['status']=='closed' else 'open'}">{ticket['status'].upper()}</span></p>
{'<p><strong>Closed:</strong> ' + str(ticket.get("closed_at", "")) + '</p>' if ticket['status']=='closed' else ''}
{'<p><strong>Close Reason:</strong> ' + str(ticket.get("close_reason", "N/A")) + '</p>' if ticket.get("close_reason") else ''}
</div>
<div class="messages">
"""

    for msg in messages:
        initial = msg["username"][0].upper() if msg["username"] else "?"
        html += f"""<div class="message">
<div class="avatar">{initial}</div>
<div class="content">
<span class="username">{msg['username']}</span>
<span class="timestamp">{msg['created_at']}</span>
<div class="text">{msg['content']}</div>
</div>
</div>
"""

    html += f"""</div>
<div class="info">
<p><strong>Total Messages:</strong> {len(messages)}</p>
<p><strong>Transcript generated:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
<p><strong>Powered by:</strong> Nexify Bot</p>
</div>
</body>
</html>"""

    return html


# ═══════════════════════════════════════════════════════════════
#  PERSISTENT VIEWS (survive bot restart)
# ═══════════════════════════════════════════════════════════════

class TicketPanelButton(discord.ui.View):
    """The persistent button shown in the ticket panel channel."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="nexify:ticket:create"
    )
    async def create_ticket_btn(self, interaction: discord.Interaction, button):
        settings = await get_ticket_settings(interaction.guild.id)
        if not settings or not settings.get("enabled"):
            return await interaction.response.send_message("❌ Ticket system is not enabled.", ephemeral=True)

        # Plan check — max open tickets
        plan = await get_guild_plan(interaction.guild.id)
        limits = get_plan_limits(plan)
        open_tickets = await get_open_tickets_by_user(interaction.guild.id, interaction.user.id)
        max_open = min(settings.get("max_open_tickets", 1), limits.get("max_open_tickets", 2))
        if len(open_tickets) >= max_open:
            return await interaction.response.send_message(
                f"❌ You already have **{len(open_tickets)}** open ticket(s). Maximum is **{max_open}**.",
                ephemeral=True
            )

        # Check if there are categories
        categories = await get_ticket_categories(interaction.guild.id)
        if categories:
            # Show category select
            view = TicketCategorySelect(categories, settings)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🎫 Select a Category",
                    description="Choose the type of support you need:",
                    color=TICKET_COLOR
                ),
                view=view,
                ephemeral=True
            )
        else:
            # Create directly
            await interaction.response.defer(ephemeral=True)
            await create_ticket_channel(interaction, settings, "General")


class TicketCategorySelect(discord.ui.View):
    def __init__(self, categories, settings):
        super().__init__(timeout=60)
        self.settings = settings
        options = []
        for cat in categories[:25]:
            options.append(discord.SelectOption(
                label=cat["name"],
                value=cat["name"],
                emoji=cat.get("emoji", "🎫"),
                description=cat.get("description", "")[:100] or None
            ))
        select = discord.ui.Select(
            placeholder="Choose a category...",
            options=options,
            custom_id="nexify:ticket:cat_select"
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        category_name = interaction.data["values"][0]
        await interaction.response.defer(ephemeral=True)
        await create_ticket_channel(interaction, self.settings, category_name)


class TicketControlView(discord.ui.View):
    """Controls shown inside a ticket channel (persistent)."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="nexify:ticket:close")
    async def close_btn(self, interaction: discord.Interaction, button):
        ticket = await get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("❌ Not a ticket channel.", ephemeral=True)

        settings = await get_ticket_settings(interaction.guild.id)

        if settings and settings.get("close_confirmation"):
            view = CloseConfirmView()
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔒 Close Ticket?",
                    description="Are you sure you want to close this ticket?",
                    color=WARNING_COLOR
                ),
                view=view
            )
        else:
            await interaction.response.defer()
            await handle_ticket_close(interaction, ticket, settings)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, emoji="✋", custom_id="nexify:ticket:claim")
    async def claim_btn(self, interaction: discord.Interaction, button):
        ticket = await get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("❌ Not a ticket channel.", ephemeral=True)

        if ticket.get("claimed_by"):
            return await interaction.response.send_message(
                f"❌ Already claimed by <@{ticket['claimed_by']}>", ephemeral=True
            )

        settings = await get_ticket_settings(interaction.guild.id)
        support_role = settings.get("support_role_id") if settings else None

        if support_role:
            role = interaction.guild.get_role(support_role)
            if role and role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message("❌ Only support staff can claim!", ephemeral=True)

        await claim_ticket(interaction.channel.id, interaction.user.id)

        embed = discord.Embed(
            title="✋ Ticket Claimed",
            description=f"This ticket has been claimed by {interaction.user.mention}.",
            color=SUCCESS_COLOR
        )
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, emoji="📋", custom_id="nexify:ticket:transcript")
    async def transcript_btn(self, interaction: discord.Interaction, button):
        ticket = await get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("❌ Not a ticket channel.", ephemeral=True)

        plan = await get_guild_plan(interaction.guild.id)
        limits = get_plan_limits(plan)
        if not limits.get("transcript_enabled"):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔒 Feature Locked",
                    description="**Transcripts** require **⭐ Premium** plan or higher.\nContact the bot owner to upgrade!",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        messages = await get_ticket_messages(ticket["id"])
        if not messages:
            return await interaction.followup.send("❌ No messages saved yet.", ephemeral=True)

        html = await generate_transcript(ticket, messages, interaction.guild)
        file = discord.File(
            io.BytesIO(html.encode("utf-8")),
            filename=f"ticket-{ticket['ticket_number']}-transcript.html"
        )
        await interaction.followup.send(
            embed=discord.Embed(
                title=f"📋 Transcript — Ticket #{ticket['ticket_number']}",
                description=f"**Messages:** {len(messages)}",
                color=TICKET_COLOR
            ),
            file=file,
            ephemeral=True
        )

    @discord.ui.button(label="Priority", style=discord.ButtonStyle.secondary, emoji="🔥", custom_id="nexify:ticket:priority")
    async def priority_btn(self, interaction: discord.Interaction, button):
        ticket = await get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("❌ Not a ticket.", ephemeral=True)

        view = PrioritySelectView()
        await interaction.response.send_message(
            embed=discord.Embed(title="🔥 Set Priority", color=TICKET_COLOR),
            view=view,
            ephemeral=True
        )


class PrioritySelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.select(
        placeholder="Select priority...",
        options=[
            discord.SelectOption(label="Low", value="low", emoji="🟢"),
            discord.SelectOption(label="Normal", value="normal", emoji="🟡"),
            discord.SelectOption(label="High", value="high", emoji="🟠"),
            discord.SelectOption(label="Urgent", value="urgent", emoji="🔴"),
        ]
    )
    async def select(self, interaction: discord.Interaction, select):
        priority = select.values[0]
        await set_ticket_priority(interaction.channel.id, priority)

        emojis = {"low": "🟢", "normal": "🟡", "high": "🟠", "urgent": "🔴"}
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{emojis[priority]} Priority → {priority.title()}",
                color=SUCCESS_COLOR
            )
        )
        self.stop()


class CloseConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger, emoji="🔒")
    async def confirm(self, interaction: discord.Interaction, button):
        ticket = await get_ticket_by_channel(interaction.channel.id)
        settings = await get_ticket_settings(interaction.guild.id)
        self.stop()
        await interaction.response.defer()
        await handle_ticket_close(interaction, ticket, settings)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button):
        self.stop()
        await interaction.response.edit_message(
            embed=discord.Embed(title="❌ Close Cancelled", color=ERROR_COLOR),
            view=None
        )


class ClosedTicketView(discord.ui.View):
    """Shown after ticket is closed — delete or reopen."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Delete Channel", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="nexify:ticket:delete")
    async def delete_btn(self, interaction: discord.Interaction, button):
        if not interaction.user.guild_permissions.manage_channels:
            settings = await get_ticket_settings(interaction.guild.id)
            if settings and settings.get("support_role_id"):
                role = interaction.guild.get_role(settings["support_role_id"])
                if role and role not in interaction.user.roles:
                    return await interaction.response.send_message("❌ Staff only!", ephemeral=True)
            else:
                return await interaction.response.send_message("❌ No permission!", ephemeral=True)

        await interaction.response.send_message("🗑️ Deleting in 5 seconds...")
        await discord.utils.sleep_until(datetime.now(timezone.utc) + timedelta(seconds=5))
        try:
            await interaction.channel.delete(reason="Ticket deleted")
        except:
            pass

    @discord.ui.button(label="Reopen", style=discord.ButtonStyle.success, emoji="🔓", custom_id="nexify:ticket:reopen")
    async def reopen_btn(self, interaction: discord.Interaction, button):
        ticket = await get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("❌ Not a ticket.", ephemeral=True)

        # Reopen
        from utils.database import aiosqlite, DB_PATH
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE tickets SET status='open', closed_at=NULL, closed_by=NULL, close_reason=NULL WHERE channel_id=?",
                (interaction.channel.id,)
            )
            await db.commit()

        # Restore permissions
        user = interaction.guild.get_member(ticket["user_id"])
        if user:
            await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)

        await interaction.channel.edit(name=interaction.channel.name.replace("closed-", "ticket-"))

        embed = discord.Embed(
            title="🔓 Ticket Reopened",
            description=f"Reopened by {interaction.user.mention}",
            color=SUCCESS_COLOR
        )
        await interaction.response.send_message(embed=embed, view=TicketControlView())


# ═══════════════════════════════════════════════════════════════
#  HELPER: CREATE TICKET CHANNEL
# ═══════════════════════════════════════════════════════════════

async def create_ticket_channel(interaction: discord.Interaction, settings: dict, category_name: str):
    guild = interaction.guild
    user = interaction.user

    # Get ticket number
    ticket_num = await increment_ticket_counter(guild.id)

    # Determine Discord category
    cat_data = await get_ticket_category_by_name(guild.id, category_name)
    discord_category_id = None
    support_role_id = settings.get("support_role_id")
    welcome_msg = settings.get("welcome_message", "Thank you for creating a ticket!")

    if cat_data:
        discord_category_id = cat_data.get("category_id") or settings.get("category_id")
        if cat_data.get("support_role_id"):
            support_role_id = cat_data["support_role_id"]
        if cat_data.get("welcome_message"):
            welcome_msg = cat_data["welcome_message"]
    else:
        discord_category_id = settings.get("category_id")

    category = guild.get_channel(discord_category_id) if discord_category_id else None

    # Build permissions
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(
            read_messages=True, send_messages=True,
            attach_files=True, embed_links=True, read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(
            read_messages=True, send_messages=True,
            manage_channels=True, manage_messages=True
        ),
    }

    if support_role_id:
        role = guild.get_role(support_role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True,
                attach_files=True, embed_links=True, read_message_history=True
            )

    # Create channel
    channel_name = f"ticket-{ticket_num:04d}"
    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket #{ticket_num} | {user} | {category_name}",
            reason=f"Ticket created by {user}"
        )
    except discord.Forbidden:
        return await interaction.followup.send("❌ I don't have permission to create channels!", ephemeral=True)
    except Exception as e:
        return await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # Save to DB
    ticket_id = await create_ticket(guild.id, channel.id, user.id, category_name, ticket_num)

    # Welcome embed
    priority_emoji = {"low": "🟢", "normal": "🟡", "high": "🟠", "urgent": "🔴"}

    embed = discord.Embed(
        title=f"🎫 Ticket #{ticket_num:04d}",
        description=welcome_msg,
        color=TICKET_COLOR,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="👤 Created By", value=user.mention, inline=True)
    embed.add_field(name="📂 Category", value=category_name, inline=True)
    embed.add_field(name="🔥 Priority", value="🟡 Normal", inline=True)
    embed.add_field(
        name="📝 How to use",
        value=(
            "• Describe your issue in detail\n"
            "• A staff member will assist you\n"
            "• Click **🔒 Close** when resolved"
        ),
        inline=False
    )
    embed.set_footer(text=f"Ticket ID: {ticket_id} • Nexify Tickets")

    view = TicketControlView()
    await channel.send(content=user.mention, embed=embed, view=view)

    # Ping support role
    if support_role_id:
        role = guild.get_role(support_role_id)
        if role:
            ping_msg = await channel.send(f"{role.mention} — New ticket from {user.mention}")
            await ping_msg.delete(delay=3)

    # Log
    log_ch_id = settings.get("log_channel_id")
    if log_ch_id:
        log_ch = guild.get_channel(log_ch_id)
        if log_ch:
            log_embed = discord.Embed(
                title="🎫 Ticket Created",
                color=SUCCESS_COLOR,
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="👤 User", value=f"{user.mention} (`{user.id}`)", inline=True)
            log_embed.add_field(name="📂 Category", value=category_name, inline=True)
            log_embed.add_field(name="📍 Channel", value=channel.mention, inline=True)
            log_embed.add_field(name="🔢 Number", value=f"`#{ticket_num:04d}`", inline=True)
            log_embed.set_thumbnail(url=user.display_avatar.url)
            log_embed.set_footer(text="Nexify Tickets")
            try:
                await log_ch.send(embed=log_embed)
            except:
                pass

    # Reply to user
    await interaction.followup.send(
        embed=discord.Embed(
            title="✅ Ticket Created!",
            description=f"Your ticket has been created: {channel.mention}",
            color=SUCCESS_COLOR
        ),
        ephemeral=True
    )


# ═══════════════════════════════════════════════════════════════
#  HELPER: CLOSE TICKET
# ═══════════════════════════════════════════════════════════════

async def handle_ticket_close(interaction: discord.Interaction, ticket: dict, settings: dict):
    guild = interaction.guild
    channel = interaction.channel

    if not ticket or ticket["status"] == "closed":
        return

    # Close in DB
    await close_ticket(channel.id, interaction.user.id, "Closed by user")

    # Generate transcript if enabled (and plan allows)
    transcript_file = None
    plan = await get_guild_plan(guild.id)
    plan_limits = get_plan_limits(plan)
    if settings and settings.get("transcript_on_close") and plan_limits.get("transcript_enabled"):
        messages = await get_ticket_messages(ticket["id"])
        if messages:
            html = await generate_transcript(ticket, messages, guild)
            transcript_file = discord.File(
                io.BytesIO(html.encode("utf-8")),
                filename=f"ticket-{ticket['ticket_number']}-transcript.html"
            )

    # Update channel
    try:
        await channel.edit(name=f"closed-{ticket['ticket_number']:04d}")
        user = guild.get_member(ticket["user_id"])
        if user:
            await channel.set_permissions(user, read_messages=True, send_messages=False)
    except:
        pass

    # Closed embed
    embed = discord.Embed(
        title="🔒 Ticket Closed",
        description=f"This ticket has been closed by {interaction.user.mention}.",
        color=ERROR_COLOR,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="🔢 Ticket", value=f"#{ticket['ticket_number']:04d}", inline=True)
    embed.add_field(name="👤 Created By", value=f"<@{ticket['user_id']}>", inline=True)

    kwargs = {"embed": embed, "view": ClosedTicketView()}
    if transcript_file:
        kwargs["file"] = transcript_file
    await channel.send(**kwargs)

    # DM the user
    user = guild.get_member(ticket["user_id"])
    if user:
        try:
            dm_embed = discord.Embed(
                title="🔒 Your Ticket Was Closed",
                description=f"Your ticket **#{ticket['ticket_number']:04d}** in **{guild.name}** has been closed.",
                color=TICKET_COLOR
            )
            await user.send(embed=dm_embed)
        except:
            pass

    # Log
    if settings:
        log_ch_id = settings.get("log_channel_id")
        if log_ch_id:
            log_ch = guild.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="🔒 Ticket Closed",
                    color=ERROR_COLOR,
                    timestamp=datetime.now(timezone.utc)
                )
                log_embed.add_field(name="🔢 Ticket", value=f"#{ticket['ticket_number']:04d}", inline=True)
                log_embed.add_field(name="👤 Created By", value=f"<@{ticket['user_id']}>", inline=True)
                log_embed.add_field(name="🔒 Closed By", value=interaction.user.mention, inline=True)
                if ticket.get("claimed_by"):
                    log_embed.add_field(name="✋ Claimed By", value=f"<@{ticket['claimed_by']}>", inline=True)
                log_embed.set_footer(text="Nexify Tickets")

                kwargs = {"embed": log_embed}
                if settings.get("transcript_on_close") and plan_limits.get("transcript_enabled"):
                    messages = await get_ticket_messages(ticket["id"])
                    if messages:
                        html = await generate_transcript(ticket, messages, guild)
                        kwargs["file"] = discord.File(
                            io.BytesIO(html.encode("utf-8")),
                            filename=f"ticket-{ticket['ticket_number']}-transcript.html"
                        )
                try:
                    await log_ch.send(**kwargs)
                except:
                    pass


# ═══════════════════════════════════════════════════════════════
#  MODALS
# ═══════════════════════════════════════════════════════════════

class SetupModal(discord.ui.Modal, title="🎫 Ticket Setup"):
    cat_input = discord.ui.TextInput(label="Ticket Category ID (Discord category)", placeholder="Right-click category → Copy ID")
    log_input = discord.ui.TextInput(label="Log Channel ID", placeholder="Right-click channel → Copy ID")
    role_input = discord.ui.TextInput(label="Support Role ID", placeholder="Right-click role → Copy ID")
    welcome_input = discord.ui.TextInput(
        label="Welcome Message",
        placeholder="Message shown when ticket is created...",
        style=discord.TextStyle.paragraph,
        default="Thank you for creating a ticket! A staff member will be with you shortly.",
        required=False
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction):
        try:
            cat_id = int(self.cat_input.value)
            log_id = int(self.log_input.value)
            role_id = int(self.role_input.value)
        except:
            return await interaction.response.send_message("❌ All IDs must be numbers!", ephemeral=True)

        cat = interaction.guild.get_channel(cat_id)
        log_ch = interaction.guild.get_channel(log_id)
        role = interaction.guild.get_role(role_id)

        errors = []
        if not cat:
            errors.append("Category not found")
        if not log_ch:
            errors.append("Log channel not found")
        if not role:
            errors.append("Role not found")
        if errors:
            return await interaction.response.send_message(f"❌ {', '.join(errors)}", ephemeral=True)

        await create_ticket_settings(interaction.guild.id)
        await update_ticket_setting(interaction.guild.id, "category_id", cat_id)
        await update_ticket_setting(interaction.guild.id, "log_channel_id", log_id)
        await update_ticket_setting(interaction.guild.id, "support_role_id", role_id)
        await update_ticket_setting(interaction.guild.id, "enabled", 1)

        if self.welcome_input.value:
            await update_ticket_setting(interaction.guild.id, "welcome_message", self.welcome_input.value)

        e = discord.Embed(title="✅ Ticket System Setup!", color=SUCCESS_COLOR)
        e.add_field(name="📂 Category", value=cat.name, inline=True)
        e.add_field(name="📌 Log Channel", value=log_ch.mention, inline=True)
        e.add_field(name="🏷️ Support Role", value=role.mention, inline=True)
        e.add_field(name="📝 Next Step", value="Use **Send Panel** to create the ticket panel in a channel!", inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)


class AddCategoryModal(discord.ui.Modal, title="📂 Add Ticket Category"):
    name_input = discord.ui.TextInput(label="Category Name", placeholder="e.g. General Support", max_length=50)
    emoji_input = discord.ui.TextInput(label="Emoji", placeholder="🎫", max_length=5, default="🎫", required=False)
    desc_input = discord.ui.TextInput(label="Description", placeholder="Short description...", max_length=100, required=False)
    welcome_input = discord.ui.TextInput(
        label="Custom Welcome Message (optional)",
        placeholder="Leave empty for default",
        style=discord.TextStyle.paragraph,
        required=False
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction):
        # Plan check — max ticket categories
        plan = await get_guild_plan(interaction.guild.id)
        limits = get_plan_limits(plan)
        max_cats = limits.get("max_ticket_categories", 1)
        existing_cats = await get_ticket_categories(interaction.guild.id)
        if len(existing_cats) >= max_cats:
            from config import get_plan_info
            plan_info = get_plan_info(plan)
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔒 Category Limit Reached",
                    description=(
                        f"Your **{plan_info['emoji']} {plan_info['name']}** plan allows max **{max_cats}** ticket categories.\n"
                        f"You currently have **{len(existing_cats)}**.\n\n"
                        f"Upgrade your plan to add more!"
                    ),
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        name = self.name_input.value.strip()
        emoji = self.emoji_input.value.strip() if self.emoji_input.value else "🎫"
        desc = self.desc_input.value.strip() if self.desc_input.value else ""
        welcome = self.welcome_input.value.strip() if self.welcome_input.value else ""

        cat_id = await add_ticket_category(
            interaction.guild.id, name, emoji, desc,
            welcome_message=welcome
        )

        e = discord.Embed(title="✅ Category Added", color=SUCCESS_COLOR)
        e.add_field(name="📂 Name", value=f"{emoji} {name}", inline=True)
        e.add_field(name="🆔 ID", value=f"`{cat_id}`", inline=True)
        if desc:
            e.add_field(name="📝 Description", value=desc, inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)


class RemoveCategoryModal(discord.ui.Modal, title="🗑️ Remove Category"):
    id_input = discord.ui.TextInput(label="Category ID", placeholder="From category list")

    async def on_submit(self, interaction):
        try:
            cat_id = int(self.id_input.value)
        except:
            return await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)
        ok = await remove_ticket_category(cat_id)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Removed" if ok else "❌ Not Found",
                color=SUCCESS_COLOR if ok else ERROR_COLOR
            ),
            ephemeral=True
        )


class SendPanelModal(discord.ui.Modal, title="📩 Send Ticket Panel"):
    ch_input = discord.ui.TextInput(label="Channel ID", placeholder="Where to send the panel")
    title_input = discord.ui.TextInput(label="Panel Title", default="🎫 Support Tickets", required=False)
    desc_input = discord.ui.TextInput(
        label="Panel Description",
        style=discord.TextStyle.paragraph,
        default="Click the button below to create a support ticket.\nA staff member will assist you shortly.",
        required=False
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction):
        try:
            ch_id = int(self.ch_input.value)
        except:
            return await interaction.response.send_message("❌ Invalid channel ID!", ephemeral=True)
        ch = interaction.guild.get_channel(ch_id)
        if not ch:
            return await interaction.response.send_message("❌ Channel not found!", ephemeral=True)

        title = self.title_input.value or "🎫 Support Tickets"
        desc = self.desc_input.value or "Click the button below to create a ticket."

        # Check for categories
        categories = await get_ticket_categories(interaction.guild.id)
        if categories:
            cat_list = "\n".join([f"{c['emoji']} **{c['name']}** — {c.get('description', '') or 'No description'}" for c in categories])
            desc += f"\n\n**Available Categories:**\n{cat_list}"

        embed = discord.Embed(title=title, description=desc, color=TICKET_COLOR)
        embed.set_footer(text="Nexify Ticket System")

        view = TicketPanelButton()
        msg = await ch.send(embed=embed, view=view)

        await update_ticket_setting(interaction.guild.id, "panel_channel_id", ch.id)
        await update_ticket_setting(interaction.guild.id, "panel_message_id", msg.id)

        await interaction.response.send_message(
            embed=discord.Embed(title="✅ Panel Sent!", description=f"Ticket panel sent to {ch.mention}", color=SUCCESS_COLOR),
            ephemeral=True
        )


# ═══════════════════════════════════════════════════════════════
#  TICKET PANEL VIEW
# ═══════════════════════════════════════════════════════════════

class TicketManagementView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label="Setup", style=discord.ButtonStyle.success, emoji="🛡️", row=0)
    async def setup_btn(self, interaction, btn):
        await interaction.response.send_modal(SetupModal(self.cog))

    @discord.ui.button(label="Send Panel", style=discord.ButtonStyle.primary, emoji="📩", row=0)
    async def panel_btn(self, interaction, btn):
        await interaction.response.send_modal(SendPanelModal(self.cog))

    @discord.ui.button(label="Enable", style=discord.ButtonStyle.success, emoji="🟢", row=0)
    async def enable_btn(self, interaction, btn):
        s = await get_ticket_settings(interaction.guild.id)
        if not s:
            return await interaction.response.send_message("❌ Run Setup first!", ephemeral=True)
        await update_ticket_setting(interaction.guild.id, "enabled", 1)
        await interaction.response.send_message(
            embed=discord.Embed(title="🟢 Tickets Enabled", color=SUCCESS_COLOR), ephemeral=True
        )

    @discord.ui.button(label="Disable", style=discord.ButtonStyle.danger, emoji="🔴", row=0)
    async def disable_btn(self, interaction, btn):
        await update_ticket_setting(interaction.guild.id, "enabled", 0)
        await interaction.response.send_message(
            embed=discord.Embed(title="🔴 Tickets Disabled", color=ERROR_COLOR), ephemeral=True
        )

    @discord.ui.button(label="Add Category", style=discord.ButtonStyle.secondary, emoji="📂", row=1)
    async def addcat_btn(self, interaction, btn):
        await interaction.response.send_modal(AddCategoryModal(self.cog))

    @discord.ui.button(label="Remove Category", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def rmcat_btn(self, interaction, btn):
        await interaction.response.send_modal(RemoveCategoryModal())

    @discord.ui.button(label="Categories", style=discord.ButtonStyle.secondary, emoji="📋", row=1)
    async def listcat_btn(self, interaction, btn):
        cats = await get_ticket_categories(interaction.guild.id)
        if not cats:
            return await interaction.response.send_message(
                embed=discord.Embed(title="📋 Categories", description="*No categories. Tickets will be created without categories.*", color=WARNING_COLOR),
                ephemeral=True
            )
        desc = "\n".join([f"`{c['id']}` {c['emoji']} **{c['name']}** — {c.get('description', '') or 'N/A'}" for c in cats])
        await interaction.response.send_message(
            embed=discord.Embed(title=f"📋 Ticket Categories ({len(cats)})", description=desc, color=TICKET_COLOR),
            ephemeral=True
        )

    @discord.ui.button(label="Open Tickets", style=discord.ButtonStyle.primary, emoji="📊", row=1)
    async def open_btn(self, interaction, btn):
        tickets = await get_all_open_tickets(interaction.guild.id)
        if not tickets:
            return await interaction.response.send_message(
                embed=discord.Embed(title="📊 Open Tickets", description="*No open tickets.*", color=SUCCESS_COLOR),
                ephemeral=True
            )
        desc = ""
        for t in tickets[:20]:
            priority_e = {"low": "🟢", "normal": "🟡", "high": "🟠", "urgent": "🔴"}.get(t.get("priority", "normal"), "🟡")
            claimed = f"✋ <@{t['claimed_by']}>" if t.get("claimed_by") else "❌ Unclaimed"
            desc += f"{priority_e} `#{t['ticket_number']:04d}` <#{t['channel_id']}> — <@{t['user_id']}> | {claimed}\n"
        await interaction.response.send_message(
            embed=discord.Embed(title=f"📊 Open Tickets ({len(tickets)})", description=desc, color=TICKET_COLOR),
            ephemeral=True
        )

    @discord.ui.button(label="Stats", style=discord.ButtonStyle.secondary, emoji="📈", row=2)
    async def stats_btn(self, interaction, btn):
        stats = await get_ticket_stats(interaction.guild.id)
        e = discord.Embed(title="📈 Ticket Statistics", color=TICKET_COLOR)
        e.add_field(name="📊 Total", value=f"```{stats['total']}```", inline=True)
        e.add_field(name="🟢 Open", value=f"```{stats['open']}```", inline=True)
        e.add_field(name="🔴 Closed", value=f"```{stats['closed']}```", inline=True)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="Settings", style=discord.ButtonStyle.secondary, emoji="⚙️", row=2)
    async def settings_btn(self, interaction, btn):
        s = await get_ticket_settings(interaction.guild.id)
        if not s:
            return await interaction.response.send_message(
                embed=discord.Embed(title="⚙️ Settings", description="*Not configured. Run Setup.*", color=WARNING_COLOR),
                ephemeral=True
            )
        status = "🟢 Enabled" if s["enabled"] else "🔴 Disabled"
        cat = f"<#{s['category_id']}>" if s.get("category_id") else "*Not set*"
        log = f"<#{s['log_channel_id']}>" if s.get("log_channel_id") else "*Not set*"
        role = f"<@&{s['support_role_id']}>" if s.get("support_role_id") else "*Not set*"

        e = discord.Embed(title="⚙️ Ticket Settings", color=TICKET_COLOR)
        e.add_field(name="Status", value=status, inline=True)
        e.add_field(name="Category", value=cat, inline=True)
        e.add_field(name="Log Channel", value=log, inline=True)
        e.add_field(name="Support Role", value=role, inline=True)
        e.add_field(name="Max Open", value=f"`{s.get('max_open_tickets', 1)}`", inline=True)
        e.add_field(name="Total Created", value=f"`{s.get('ticket_counter', 0)}`", inline=True)
        e.add_field(name="Transcript", value="✅" if s.get("transcript_on_close") else "❌", inline=True)
        e.add_field(name="Close Confirm", value="✅" if s.get("close_confirmation") else "❌", inline=True)
        await interaction.response.send_message(embed=e, ephemeral=True)


# ═══════════════════════════════════════════════════════════════
#  TICKET COG
# ═══════════════════════════════════════════════════════════════

class Tickets(commands.Cog):
    """🎫 Ticket System for Nexify"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketPanelButton())
        self.bot.add_view(TicketControlView())
        self.bot.add_view(ClosedTicketView())
        print("[COG] Ticket system loaded.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Save messages in ticket channels for transcripts."""
        if message.author.bot or not message.guild:
            return
        ticket = await get_ticket_by_channel(message.channel.id)
        if ticket and ticket["status"] == "open":
            content = message.content or ""
            if message.attachments:
                content += "\n" + "\n".join([a.url for a in message.attachments])
            if content.strip():
                await save_ticket_message(ticket["id"], message.author.id, str(message.author), content)

    @app_commands.command(name="ticket", description="🎫 Open the Ticket Management Panel")
    @app_commands.default_permissions(manage_guild=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        s = await get_ticket_settings(interaction.guild.id)

        embed = discord.Embed(title="🎫 Ticket Management Panel", color=PANEL_COLOR)

        if s and s.get("enabled"):
            stats = await get_ticket_stats(interaction.guild.id)
            cats = await get_ticket_categories(interaction.guild.id)
            status = "🟢 Enabled"
            log = f"<#{s['log_channel_id']}>" if s.get("log_channel_id") else "*Not set*"
            role = f"<@&{s['support_role_id']}>" if s.get("support_role_id") else "*Not set*"

            embed.description = (
                f"**Status:** {status} | **Log:** {log} | **Role:** {role}\n"
                f"**Stats:** 📊 `{stats['total']}` total | 🟢 `{stats['open']}` open | 🔴 `{stats['closed']}` closed\n"
                f"**Categories:** `{len(cats)}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🛡️ **Setup** — Configure ticket system\n"
                "📩 **Send Panel** — Create ticket button in a channel\n"
                "🟢 **Enable** / 🔴 **Disable** — Toggle system\n"
                "📂 **Add/Remove Category** — Manage ticket types\n"
                "📋 **Categories** — View all categories\n"
                "📊 **Open Tickets** — View current tickets\n"
                "📈 **Stats** — View statistics\n"
                "⚙️ **Settings** — View configuration"
            )
        else:
            embed.description = (
                "Ticket system is **not configured** or **disabled**.\n\n"
                "Click **🛡️ Setup** to configure:\n"
                "• Set a Discord category for tickets\n"
                "• Set a log channel\n"
                "• Set a support role\n"
                "• Customize welcome message\n\n"
                "Then use **📩 Send Panel** to create the ticket button!"
            )

        embed.set_footer(text="Nexify Tickets • Panel expires in 5 minutes")

        view = TicketManagementView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Tickets(bot))