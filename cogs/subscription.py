import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timezone, timedelta

from utils.database import (
    get_subscription, get_guild_plan, create_subscription,
    update_subscription_plan, extend_subscription, revoke_subscription,
    get_all_subscriptions, get_active_subscriptions,
    get_subscription_logs, get_subscription_stats, get_expiring_soon,
    create_license_key, get_license_key, redeem_license_key,
    get_all_license_keys, delete_license_key, get_license_key_stats
)
from config import (
    OWNER_ID, OWNER_IDS, OWNER_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR,
    PLANS, get_plan_limits, get_plan_info
)


# ═══════════════════════════════════════════════════════════════
#  PERMISSION CHECK HELPER
# ═══════════════════════════════════════════════════════════════

async def check_feature(interaction, feature_key):
    """Check if a feature is available for this guild's plan.
    Returns (allowed, plan_name, limit_value)"""
    plan_name = await get_guild_plan(interaction.guild.id)
    limits = get_plan_limits(plan_name)
    value = limits.get(feature_key, False)
    return value, plan_name


async def send_upgrade_message(interaction, feature_name, current_plan):
    """Send a standardized upgrade message."""
    plan_info = get_plan_info(current_plan)

    # Find which plan unlocks this feature
    unlock_plan = None
    for p_name in ["basic", "premium", "business"]:
        p_limits = get_plan_limits(p_name)
        if p_limits.get(feature_name.lower().replace(" ", "_"), False):
            unlock_plan = p_name
            break

    embed = discord.Embed(
        title="🔒 Feature Locked",
        description=(
            f"**{feature_name}** is not available on the **{plan_info['emoji']} {plan_info['name']}** plan.\n\n"
            f"{'Upgrade to **' + get_plan_info(unlock_plan)['emoji'] + ' ' + get_plan_info(unlock_plan)['name'] + '** ($' + str(get_plan_info(unlock_plan)['price']) + '/mo) to unlock this feature!' if unlock_plan else 'Contact the bot owner for more info.'}\n\n"
            f"Contact the bot owner to upgrade your plan."
        ),
        color=ERROR_COLOR
    )
    embed.set_footer(text=f"Current Plan: {plan_info['emoji']} {plan_info['name']}")

    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ═══════════════════════════════════════════════════════════════
#  OWNER PANEL MODALS
# ═══════════════════════════════════════════════════════════════

class ActivateSubModal(discord.ui.Modal, title="✅ Activate Subscription"):
    guild_input = discord.ui.TextInput(label="Guild ID", placeholder="Server ID")
    plan_input = discord.ui.TextInput(label="Plan (free/basic/premium/business)", placeholder="premium")
    days_input = discord.ui.TextInput(label="Duration (days)", placeholder="30", default="30")
    amount_input = discord.ui.TextInput(label="Amount Paid ($)", placeholder="15.00", default="0", required=False)
    notes_input = discord.ui.TextInput(label="Notes", placeholder="Payment method, customer info...", required=False, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction):
        try:
            guild_id = int(self.guild_input.value)
            days = int(self.days_input.value)
        except:
            return await interaction.response.send_message("❌ Invalid Guild ID or days!", ephemeral=True)

        plan = self.plan_input.value.lower().strip()
        if plan not in PLANS:
            return await interaction.response.send_message(
                f"❌ Invalid plan! Use: `{', '.join(PLANS.keys())}`", ephemeral=True
            )

        try:
            amount = float(self.amount_input.value.replace("$", "")) if self.amount_input.value else 0
        except:
            amount = 0

        notes = self.notes_input.value or ""

        await update_subscription_plan(guild_id, plan, interaction.user.id, days, amount, notes)

        plan_info = get_plan_info(plan)
        expires = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M UTC")

        guild = interaction.client.get_guild(guild_id)
        guild_name = guild.name if guild else f"ID: {guild_id}"

        embed = discord.Embed(
            title="✅ Subscription Activated!",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="🏠 Server", value=f"**{guild_name}**\n`{guild_id}`", inline=True)
        embed.add_field(name="📋 Plan", value=f"{plan_info['emoji']} **{plan_info['name']}**", inline=True)
        embed.add_field(name="💰 Amount", value=f"`${amount:.2f}`", inline=True)
        embed.add_field(name="⏱️ Duration", value=f"`{days} days`", inline=True)
        embed.add_field(name="📅 Expires", value=f"`{expires}`", inline=True)
        if notes:
            embed.add_field(name="📝 Notes", value=notes, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # DM the server owner
        if guild:
            try:
                owner = guild.owner
                if owner:
                    dm_embed = discord.Embed(
                        title=f"{plan_info['emoji']} Subscription Activated!",
                        description=(
                            f"Your server **{guild.name}** has been upgraded to "
                            f"**{plan_info['name']}** plan!\n\n"
                            f"**Duration:** {days} days\n"
                            f"**Expires:** {expires}\n\n"
                            f"Enjoy all the features! 🚀"
                        ),
                        color=plan_info["color"]
                    )
                    await owner.send(embed=dm_embed)
            except:
                pass


class ExtendSubModal(discord.ui.Modal, title="⏱️ Extend Subscription"):
    guild_input = discord.ui.TextInput(label="Guild ID", placeholder="Server ID")
    days_input = discord.ui.TextInput(label="Days to Add", placeholder="30")
    amount_input = discord.ui.TextInput(label="Amount Paid ($)", placeholder="15.00", default="0", required=False)
    notes_input = discord.ui.TextInput(label="Notes", required=False)

    async def on_submit(self, interaction):
        try:
            guild_id = int(self.guild_input.value)
            days = int(self.days_input.value)
        except:
            return await interaction.response.send_message("❌ Invalid input!", ephemeral=True)

        try:
            amount = float(self.amount_input.value.replace("$", "")) if self.amount_input.value else 0
        except:
            amount = 0

        success = await extend_subscription(guild_id, days, interaction.user.id, amount, self.notes_input.value or "")
        if not success:
            return await interaction.response.send_message("❌ No subscription found for that server!", ephemeral=True)

        sub = await get_subscription(guild_id)
        guild = interaction.client.get_guild(guild_id)
        guild_name = guild.name if guild else f"ID: {guild_id}"

        embed = discord.Embed(
            title="⏱️ Subscription Extended!",
            description=(
                f"**{guild_name}** extended by **{days} days**\n"
                f"New expiry: `{sub['expires_at'][:16] if sub.get('expires_at') else 'N/A'}`"
            ),
            color=SUCCESS_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RevokeSubModal(discord.ui.Modal, title="❌ Revoke Subscription"):
    guild_input = discord.ui.TextInput(label="Guild ID", placeholder="Server ID")
    notes_input = discord.ui.TextInput(label="Reason", placeholder="Why revoking?", required=False)

    async def on_submit(self, interaction):
        try:
            guild_id = int(self.guild_input.value)
        except:
            return await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)

        sub = await get_subscription(guild_id)
        old_plan = sub["plan"] if sub else "free"

        await revoke_subscription(guild_id, interaction.user.id, self.notes_input.value or "")

        guild = interaction.client.get_guild(guild_id)
        guild_name = guild.name if guild else f"ID: {guild_id}"

        embed = discord.Embed(
            title="❌ Subscription Revoked!",
            description=f"**{guild_name}** downgraded from **{old_plan}** → **free**",
            color=ERROR_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ═══════════════════════════════════════════════════════════════
#  LICENSE KEY MODALS & VIEWS
# ═══════════════════════════════════════════════════════════════

class AddKeysModal(discord.ui.Modal, title="🔑 Add License Keys"):
    keys_input = discord.ui.TextInput(
        label="Keys (one per line)",
        placeholder="XXXX-XXXX-XXXX\nYYYY-YYYY-YYYY\nZZZZ-ZZZZ-ZZZZ",
        style=discord.TextStyle.paragraph
    )
    plan_input = discord.ui.TextInput(
        label="Plan (basic/premium/business)",
        placeholder="premium"
    )
    days_input = discord.ui.TextInput(
        label="Duration (days)",
        placeholder="30",
        default="30"
    )
    notes_input = discord.ui.TextInput(
        label="Notes",
        placeholder="Customer name, batch info...",
        required=False
    )

    async def on_submit(self, interaction):
        plan = self.plan_input.value.lower().strip()
        if plan not in ("basic", "premium", "business"):
            return await interaction.response.send_message(
                "❌ Invalid plan! Use: `basic`, `premium`, or `business`", ephemeral=True
            )

        try:
            days = int(self.days_input.value)
            if days < 1:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message(
                "❌ Days must be ≥1!", ephemeral=True
            )

        raw_keys = [k.strip() for k in self.keys_input.value.strip().splitlines() if k.strip()]
        if not raw_keys:
            return await interaction.response.send_message("❌ No keys provided!", ephemeral=True)

        if len(raw_keys) > 50:
            return await interaction.response.send_message("❌ Maximum 50 keys at once!", ephemeral=True)

        notes = self.notes_input.value or ""
        plan_info = get_plan_info(plan)
        added = []
        duplicates = []

        for key in raw_keys:
            key_upper = key.upper()
            success = await create_license_key(key_upper, plan, days, interaction.user.id, notes)
            if success:
                added.append(key_upper)
            else:
                duplicates.append(key_upper)

        desc = f"**Plan:** {plan_info['emoji']} {plan_info['name']}\n**Duration:** {days} days\n"
        if notes:
            desc += f"**Notes:** {notes}\n"
        desc += f"\n**✅ Added ({len(added)}):**\n"
        if added:
            desc += "\n".join([f"`{k}`" for k in added[:25]])
            if len(added) > 25:
                desc += f"\n*...and {len(added) - 25} more*"
        else:
            desc += "*None*"

        if duplicates:
            desc += f"\n\n**⚠️ Duplicates ({len(duplicates)}):**\n"
            desc += "\n".join([f"`{k}`" for k in duplicates[:10]])

        embed = discord.Embed(
            title=f"🔑 Added {len(added)} Key(s)",
            description=desc,
            color=SUCCESS_COLOR if added else ERROR_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Keys are single-use • Share carefully")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class DeleteKeyModal(discord.ui.Modal, title="🗑️ Delete License Key"):
    key_input = discord.ui.TextInput(
        label="Key to delete",
        placeholder="Hubix-XXXX-XXXX-XXXX"
    )

    async def on_submit(self, interaction):
        key = self.key_input.value.strip().upper()
        success = await delete_license_key(key)
        if success:
            embed = discord.Embed(
                title="🗑️ Key Deleted",
                description=f"`{key}` has been deleted.",
                color=SUCCESS_COLOR
            )
        else:
            embed = discord.Embed(
                title="❌ Key Not Found",
                description=f"`{key}` does not exist.",
                color=ERROR_COLOR
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class KeyPaginationView(discord.ui.View):
    def __init__(self, keys, title, color, per_page=10):
        super().__init__(timeout=300)
        self.keys = keys
        self.title = title
        self.color = color
        self.per_page = per_page
        self.page = 0
        self.max_page = max(0, (len(keys) - 1) // per_page)
        self.update_buttons()

    def update_buttons(self):
        self.prev_btn.disabled = self.page <= 0
        self.next_btn.disabled = self.page >= self.max_page

    def build_page(self):
        start = self.page * self.per_page
        end = start + self.per_page
        page_keys = self.keys[start:end]

        desc = ""
        for k in page_keys:
            plan_info = get_plan_info(k["plan"])
            if k.get("redeemed"):
                guild_name = f"ID: {k.get('redeemed_guild_id', '?')}"
                desc += (
                    f"{plan_info['emoji']} `{k['key']}` → **{guild_name}** | "
                    f"<@{k['redeemed_by']}> | {k.get('redeemed_at', '')[:10]}\n"
                )
            else:
                desc += (
                    f"{plan_info['emoji']} `{k['key']}` — **{plan_info['name']}** | "
                    f"{k['duration_days']}d"
                )
                if k.get("notes"):
                    desc += f" | {k['notes'][:30]}"
                desc += "\n"

        embed = discord.Embed(
            title=f"{self.title} ({len(self.keys)})",
            description=desc or "*No keys*",
            color=self.color
        )
        embed.set_footer(text=f"Page {self.page + 1}/{self.max_page + 1}")
        return embed

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction, btn):
        self.page = max(0, self.page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_page(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction, btn):
        self.page = min(self.max_page, self.page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_page(), view=self)


class KeyManagementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)

    @discord.ui.button(label="Add Keys", style=discord.ButtonStyle.success, emoji="🔑", row=0)
    async def add_keys_btn(self, interaction, btn):
        await interaction.response.send_modal(AddKeysModal())

    @discord.ui.button(label="Available Keys", style=discord.ButtonStyle.primary, emoji="📋", row=0)
    async def available_btn(self, interaction, btn):
        keys = await get_all_license_keys(redeemed=0)
        if not keys:
            return await interaction.response.send_message("❌ No available keys.", ephemeral=True)

        view = KeyPaginationView(keys, "📋 Available Keys", OWNER_COLOR)
        embed = view.build_page()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Used Keys", style=discord.ButtonStyle.secondary, emoji="✅", row=0)
    async def used_btn(self, interaction, btn):
        keys = await get_all_license_keys(redeemed=1)
        if not keys:
            return await interaction.response.send_message("❌ No used keys.", ephemeral=True)

        desc = ""
        for k in keys[:20]:
            plan_info = get_plan_info(k["plan"])
            guild = interaction.client.get_guild(k["redeemed_guild_id"]) if k.get("redeemed_guild_id") else None
            guild_name = guild.name if guild else f"ID: {k.get('redeemed_guild_id', '?')}"
            desc += (
                f"{plan_info['emoji']} `{k['key']}` → **{guild_name}** | "
                f"<@{k['redeemed_by']}> | {k.get('redeemed_at', '')[:10]}\n"
            )

        embed = discord.Embed(
            title=f"✅ Used Keys ({len(keys)})",
            description=desc,
            color=SUCCESS_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Delete Key", style=discord.ButtonStyle.danger, emoji="🗑️", row=0)
    async def delete_btn(self, interaction, btn):
        await interaction.response.send_modal(DeleteKeyModal())

    @discord.ui.button(label="Stats", style=discord.ButtonStyle.secondary, emoji="📊", row=1)
    async def stats_btn(self, interaction, btn):
        stats = await get_license_key_stats()
        embed = discord.Embed(
            title="📊 Key Statistics",
            color=OWNER_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="🔑 Total", value=f"```{stats['total']}```", inline=True)
        embed.add_field(name="📋 Available", value=f"```{stats['available']}```", inline=True)
        embed.add_field(name="✅ Used", value=f"```{stats['used']}```", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="← Back to Panel", style=discord.ButtonStyle.secondary, emoji="🔙", row=1)
    async def back_btn(self, interaction, btn):
        # Rebuild main panel
        stats = await get_subscription_stats()
        expiring = await get_expiring_soon(7)
        active_revenue = stats['basic'] * 8 + stats['premium'] * 15 + stats['business'] * 25

        embed = discord.Embed(
            title="👑 Hubix — Owner Panel",
            description=(
                f"```\n"
                f"  ╔═╗╔═╗╔═╗╔═╗╔═╗\n"
                f"  ║H║║U║║B║║I║║X║\n"
                f"  ╚═╝╚═╝╚═╝╚═╝╚═╝\n"
                f"```\n"
                f"**📊 Dashboard:**\n"
                f"🌐 Servers: `{len(interaction.client.guilds)}` | "
                f"👥 Users: `{sum(g.member_count or 0 for g in interaction.client.guilds)}`\n"
                f"💰 Revenue: `${stats['total_revenue']:.2f}` | "
                f"📈 Monthly: `${active_revenue}/mo`\n\n"
                f"**📋 Subscriptions:**\n"
                f"🆓 Free: `{stats['free']}` | 💎 Basic: `{stats['basic']}` | "
                f"⭐ Premium: `{stats['premium']}` | 🚀 Business: `{stats['business']}`\n"
            ),
            color=OWNER_COLOR,
            timestamp=datetime.now(timezone.utc)
        )

        if expiring:
            warn_text = "\n".join([
                f"⚠️ `{s['guild_id']}` — {s['plan']}" for s in expiring[:5]
            ])
            embed.add_field(name=f"⚠️ Expiring Soon ({len(expiring)})", value=warn_text, inline=False)

        embed.add_field(
            name="🛠️ Actions",
            value=(
                "✅ **Activate** — Set plan for a server\n"
                "⏱️ **Extend** — Add time to existing sub\n"
                "❌ **Revoke** — Downgrade to free\n"
                "🔍 **Check** — View server details\n"
                "📋 **All Clients** — List all servers\n"
                "💎 **Active** — Paid subs only\n"
                "⚠️ **Expiring** — Expiring within 7 days\n"
                "💰 **Revenue** — Financial stats\n"
                "📜 **Logs** — Recent activity\n"
                "🌐 **Bot Servers** — All servers bot is in\n"
                "🔑 **Keys** — License key management\n"
                "📝 **Changelog** — Post changelog to servers"
            ),
            inline=False
        )

        embed.set_footer(text="Owner Panel • Expires in 10 minutes")

        view = OwnerPanelView()
        await interaction.response.edit_message(embed=embed, view=view)


# ═══════════════════════════════════════════════════════════════
#  CLAIM SYSTEM — PERSISTENT VIEWS & MODALS
# ═══════════════════════════════════════════════════════════════

class ClaimRedeemModal(discord.ui.Modal, title="🔑 Redeem License Key"):
    key_input = discord.ui.TextInput(
        label="Enter your license key",
        placeholder="Hubix-XXXX-XXXX-XXXX",
        min_length=5,
        max_length=100
    )

    async def on_submit(self, interaction):
        key = self.key_input.value.strip().upper()

        # Validate key
        key_data = await get_license_key(key)
        if not key_data:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Invalid Key",
                    description="This license key does not exist. Please check and try again.",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        if key_data["redeemed"]:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Already Redeemed",
                    description="This license key has already been used.",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        # Key is valid — ask for Guild ID
        plan_info = get_plan_info(key_data["plan"])
        embed = discord.Embed(
            title="✅ Valid Key!",
            description=(
                f"**Plan:** {plan_info['emoji']} {plan_info['name']}\n"
                f"**Duration:** {key_data['duration_days']} days\n\n"
                f"Now enter the **Server ID** where you want to activate this plan.\n\n"
                f"*How to get Server ID: Server Settings → Widget → Server ID, "
                f"or enable Developer Mode and right-click the server.*"
            ),
            color=plan_info["color"]
        )

        view = GuildIdInputView(key)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class GuildIdModal(discord.ui.Modal, title="🏠 Enter Server ID"):
    def __init__(self, key):
        super().__init__()
        self.key = key

    guild_input = discord.ui.TextInput(
        label="Server ID",
        placeholder="123456789012345678",
        min_length=17,
        max_length=20
    )

    async def on_submit(self, interaction):
        try:
            guild_id = int(self.guild_input.value.strip())
        except ValueError:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Invalid Server ID",
                    description="Please enter a valid numeric Server ID.",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        # Check if bot is in that guild
        guild = interaction.client.get_guild(guild_id)
        if not guild:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Bot Not in Server",
                    description=(
                        "Hubix is not in that server. Make sure:\n\n"
                        "1️⃣ The bot is **invited** to the server\n"
                        "2️⃣ You entered the **correct Server ID**\n\n"
                        "Try again with the correct ID."
                    ),
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        # Re-validate key (prevent race condition)
        key_data = await get_license_key(self.key)
        if not key_data or key_data["redeemed"]:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Key No Longer Valid",
                    description="This key has already been redeemed or removed.",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        # Apply the plan
        plan = key_data["plan"]
        days = key_data["duration_days"]
        plan_info = get_plan_info(plan)

        # Check if server already has an active paid plan
        existing_sub = await get_subscription(guild_id)
        if existing_sub and existing_sub["plan"] != "free":
            # Extend if same plan, upgrade if different
            if existing_sub["plan"] == plan:
                await extend_subscription(guild_id, days, interaction.user.id, 0,
                                          f"Redeemed key by {interaction.user}")
            else:
                await update_subscription_plan(guild_id, plan, interaction.user.id, days, 0,
                                               f"Redeemed key by {interaction.user}")
        else:
            await update_subscription_plan(guild_id, plan, interaction.user.id, days, 0,
                                           f"Redeemed key by {interaction.user}")

        # Mark key as redeemed
        await redeem_license_key(self.key, interaction.user.id, guild_id)

        expires = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M UTC")

        embed = discord.Embed(
            title="🎉 Successfully Redeemed!",
            description=(
                f"**{plan_info['emoji']} {plan_info['name']}** plan has been activated!\n\n"
                f"**Server:** {guild.name}\n"
                f"**Duration:** {days} days\n"
                f"**Expires:** {expires}\n\n"
                f"Enjoy all the premium features! 🚀"
            ),
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.set_footer(text=f"Key: {self.key}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Notify bot owners
        for oid in OWNER_IDS:
            try:
                owner = interaction.client.get_user(oid)
                if owner:
                    log_embed = discord.Embed(
                        title="🔑 Key Redeemed!",
                        description=(
                            f"**User:** {interaction.user} (`{interaction.user.id}`)\n"
                            f"**Server:** {guild.name} (`{guild_id}`)\n"
                            f"**Plan:** {plan_info['emoji']} {plan_info['name']}\n"
                            f"**Duration:** {days} days\n"
                            f"**Key:** `{self.key}`"
                        ),
                        color=SUCCESS_COLOR,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await owner.send(embed=log_embed)
            except:
                pass


class GuildIdInputView(discord.ui.View):
    def __init__(self, key):
        super().__init__(timeout=300)
        self.key = key

    @discord.ui.button(label="Enter Server ID", style=discord.ButtonStyle.primary, emoji="🏠")
    async def enter_guild_btn(self, interaction, btn):
        await interaction.response.send_modal(GuildIdModal(self.key))


class ClaimButtonView(discord.ui.View):
    """Persistent claim button — survives bot restart."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Claim Premium",
        style=discord.ButtonStyle.primary,
        emoji="🔑",
        custom_id="nexify:claim_premium"
    )
    async def claim_btn(self, interaction, btn):
        await interaction.response.send_modal(ClaimRedeemModal())


class CheckSubModal(discord.ui.Modal, title="🔍 Check Subscription"):
    guild_input = discord.ui.TextInput(label="Guild ID", placeholder="Server ID")

    async def on_submit(self, interaction):
        try:
            guild_id = int(self.guild_input.value)
        except:
            return await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)

        sub = await get_subscription(guild_id)
        guild = interaction.client.get_guild(guild_id)
        guild_name = guild.name if guild else f"ID: {guild_id}"
        members = guild.member_count if guild else "?"

        if not sub or sub["plan"] == "free":
            plan_info = get_plan_info("free")
            embed = discord.Embed(
                title=f"🔍 {guild_name}",
                description=f"**Plan:** {plan_info['emoji']} Free\n**No active subscription.**",
                color=plan_info["color"]
            )
            embed.add_field(name="👥 Members", value=f"`{members}`", inline=True)
            embed.add_field(name="🆔 ID", value=f"`{guild_id}`", inline=True)
        else:
            plan_info = get_plan_info(sub["plan"])
            expires = sub.get("expires_at", "N/A")
            if expires and expires != "N/A":
                try:
                    exp_dt = datetime.fromisoformat(expires).replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    remaining = (exp_dt - now).days
                    expires_display = f"{expires[:16]}\n({remaining} days left)"
                except:
                    expires_display = expires[:16]
            else:
                expires_display = "Lifetime"

            embed = discord.Embed(
                title=f"🔍 {guild_name}",
                color=plan_info["color"],
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="📋 Plan", value=f"{plan_info['emoji']} **{plan_info['name']}**", inline=True)
            embed.add_field(name="💰 Total Paid", value=f"`${sub['total_paid']:.2f}`", inline=True)
            embed.add_field(name="💳 Payments", value=f"`{sub['payment_count']}`", inline=True)
            embed.add_field(name="📅 Expires", value=f"```{expires_display}```", inline=True)
            embed.add_field(name="👥 Members", value=f"`{members}`", inline=True)
            embed.add_field(name="🆔 ID", value=f"`{guild_id}`", inline=True)
            if sub.get("notes"):
                embed.add_field(name="📝 Notes", value=sub["notes"], inline=False)

            # Show logs
            logs = await get_subscription_logs(guild_id, 5)
            if logs:
                log_text = ""
                for l in logs:
                    log_text += f"`{l['created_at'][:10]}` {l['action']} → {l.get('new_plan', 'N/A')}"
                    if l.get("amount"):
                        log_text += f" (${l['amount']:.2f})"
                    log_text += "\n"
                embed.add_field(name="📜 Recent Activity", value=log_text, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ═══════════════════════════════════════════════════════════════
#  OWNER MANAGEMENT VIEW
# ═══════════════════════════════════════════════════════════════

class ChangelogModal(discord.ui.Modal, title="📝 Post Changelog"):
    version_input = discord.ui.TextInput(
        label="Version",
        placeholder="v1.2.0",
        max_length=20
    )
    changelog_title_input = discord.ui.TextInput(
        label="Title",
        placeholder="New Features & Fixes",
        max_length=100
    )
    changes_input = discord.ui.TextInput(
        label="Changes",
        placeholder="• Added new feature\n• Fixed bug\n• Improved performance",
        style=discord.TextStyle.paragraph,
        max_length=3000
    )
    notes_input = discord.ui.TextInput(
        label="Additional Notes",
        placeholder="Thank you for using Hubix!",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    async def on_submit(self, interaction):
        from config import CHANGELOG_CHANNEL

        # Find changelog channel in all guilds
        sent_to = []
        for guild in interaction.client.guilds:
            for channel in guild.text_channels:
                if channel.name == CHANGELOG_CHANNEL or channel.name == "changelog":
                    try:
                        embed = discord.Embed(
                            title=f"📝 {self.version_input.value} — {self.changelog_title_input.value}",
                            description=self.changes_input.value,
                            color=0x9B59B6,
                            timestamp=datetime.now(timezone.utc)
                        )
                        if self.notes_input.value:
                            embed.add_field(name="📌 Notes", value=self.notes_input.value, inline=False)
                        embed.set_footer(text=f"Hubix Changelog • {self.version_input.value}")
                        if guild.icon:
                            embed.set_thumbnail(url=guild.icon.url)
                        await channel.send(embed=embed)
                        sent_to.append(guild.name)
                    except:
                        pass
                    break

        if sent_to:
            desc = "\n".join([f"✅ **{name}**" for name in sent_to])
            embed = discord.Embed(
                title=f"📝 Changelog Posted!",
                description=f"Sent to {len(sent_to)} server(s):\n{desc}",
                color=SUCCESS_COLOR
            )
        else:
            embed = discord.Embed(
                title="❌ No Changelog Channels Found",
                description=f"No channels named `{CHANGELOG_CHANNEL}` or `changelog` found.",
                color=ERROR_COLOR
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class OwnerPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)

    @discord.ui.button(label="Activate", style=discord.ButtonStyle.success, emoji="✅", row=0)
    async def activate_btn(self, interaction, btn):
        await interaction.response.send_modal(ActivateSubModal())

    @discord.ui.button(label="Extend", style=discord.ButtonStyle.primary, emoji="⏱️", row=0)
    async def extend_btn(self, interaction, btn):
        await interaction.response.send_modal(ExtendSubModal())

    @discord.ui.button(label="Revoke", style=discord.ButtonStyle.danger, emoji="❌", row=0)
    async def revoke_btn(self, interaction, btn):
        await interaction.response.send_modal(RevokeSubModal())

    @discord.ui.button(label="Check Server", style=discord.ButtonStyle.secondary, emoji="🔍", row=0)
    async def check_btn(self, interaction, btn):
        await interaction.response.send_modal(CheckSubModal())

    @discord.ui.button(label="All Clients", style=discord.ButtonStyle.secondary, emoji="📋", row=1)
    async def all_clients_btn(self, interaction, btn):
        subs = await get_all_subscriptions()
        if not subs:
            return await interaction.response.send_message("❌ No subscriptions.", ephemeral=True)

        desc = ""
        for s in subs[:20]:
            guild = interaction.client.get_guild(s["guild_id"])
            name = guild.name if guild else f"ID: {s['guild_id']}"
            plan_info = get_plan_info(s["plan"])
            expires = ""
            if s.get("expires_at"):
                try:
                    exp_dt = datetime.fromisoformat(s["expires_at"]).replace(tzinfo=timezone.utc)
                    remaining = (exp_dt - datetime.now(timezone.utc)).days
                    if remaining < 0:
                        expires = " ⚠️ EXPIRED"
                    elif remaining < 7:
                        expires = f" ⚠️ {remaining}d left"
                    else:
                        expires = f" ({remaining}d)"
                except:
                    pass

            desc += f"{plan_info['emoji']} **{name}** — {plan_info['name']} | ${s['total_paid']:.2f}{expires}\n"

        embed = discord.Embed(
            title=f"📋 All Clients ({len(subs)})",
            description=desc,
            color=OWNER_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Active Only", style=discord.ButtonStyle.success, emoji="💎", row=1)
    async def active_btn(self, interaction, btn):
        subs = await get_active_subscriptions()
        if not subs:
            return await interaction.response.send_message("❌ No active subscriptions.", ephemeral=True)

        desc = ""
        for s in subs[:20]:
            guild = interaction.client.get_guild(s["guild_id"])
            name = guild.name if guild else f"ID: {s['guild_id']}"
            plan_info = get_plan_info(s["plan"])
            members = guild.member_count if guild else "?"
            desc += f"{plan_info['emoji']} **{name}** — {plan_info['name']} | 👥 {members} | ${s['total_paid']:.2f}\n"

        embed = discord.Embed(
            title=f"💎 Active Subscriptions ({len(subs)})",
            description=desc,
            color=SUCCESS_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Expiring Soon", style=discord.ButtonStyle.danger, emoji="⚠️", row=1)
    async def expiring_btn(self, interaction, btn):
        subs = await get_expiring_soon(7)
        if not subs:
            return await interaction.response.send_message("✅ No subscriptions expiring within 7 days.", ephemeral=True)

        desc = ""
        for s in subs:
            guild = interaction.client.get_guild(s["guild_id"])
            name = guild.name if guild else f"ID: {s['guild_id']}"
            plan_info = get_plan_info(s["plan"])
            try:
                exp_dt = datetime.fromisoformat(s["expires_at"]).replace(tzinfo=timezone.utc)
                remaining = (exp_dt - datetime.now(timezone.utc)).days
                desc += f"⚠️ **{name}** — {plan_info['name']} | **{remaining} days left** | `{s['guild_id']}`\n"
            except:
                desc += f"⚠️ **{name}** — {plan_info['name']}\n"

        embed = discord.Embed(
            title=f"⚠️ Expiring Soon ({len(subs)})",
            description=desc,
            color=WARNING_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Revenue", style=discord.ButtonStyle.secondary, emoji="💰", row=1)
    async def revenue_btn(self, interaction, btn):
        stats = await get_subscription_stats()

        embed = discord.Embed(
            title="💰 Revenue & Statistics",
            color=OWNER_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="📊 Total Servers", value=f"```{stats['total']}```", inline=True)
        embed.add_field(name="💰 Total Revenue", value=f"```${stats['total_revenue']:.2f}```", inline=True)
        embed.add_field(name="⚠️ Expired", value=f"```{stats['expired']}```", inline=True)
        embed.add_field(name="🆓 Free", value=f"```{stats['free']}```", inline=True)
        embed.add_field(name="💎 Basic", value=f"```{stats['basic']}```", inline=True)
        embed.add_field(name="⭐ Premium", value=f"```{stats['premium']}```", inline=True)
        embed.add_field(name="🚀 Business", value=f"```{stats['business']}```", inline=True)

        # Monthly revenue estimate
        active = stats['basic'] * 8 + stats['premium'] * 15 + stats['business'] * 25
        embed.add_field(name="📈 Monthly Est.", value=f"```${active}/mo```", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Keys", style=discord.ButtonStyle.primary, emoji="🔑", row=2)
    async def keys_btn(self, interaction, btn):
        stats = await get_license_key_stats()
        embed = discord.Embed(
            title="🔑 License Key Management",
            description=(
                f"**📊 Overview:**\n"
                f"🔑 Total: `{stats['total']}` | "
                f"📋 Available: `{stats['available']}` | "
                f"✅ Used: `{stats['used']}`\n\n"
                f"**🛠️ Actions:**\n"
                f"🔑 **Add Keys** — Add your own keys\n"
                f"📋 **Available** — View unused keys\n"
                f"✅ **Used** — View redeemed keys\n"
                f"🗑️ **Delete** — Remove a key\n"
                f"📊 **Stats** — Key statistics"
            ),
            color=OWNER_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Keys are single-use • Hubix-XXXX-XXXX-XXXX format")
        view = KeyManagementView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Recent Logs", style=discord.ButtonStyle.secondary, emoji="📜", row=2)
    async def logs_btn(self, interaction, btn):
        logs = await get_subscription_logs(limit=15)
        if not logs:
            return await interaction.response.send_message("❌ No logs.", ephemeral=True)

        desc = ""
        for l in logs:
            guild = interaction.client.get_guild(l["guild_id"])
            name = guild.name if guild else f"{l['guild_id']}"
            action_emoji = {"activate": "✅", "change": "🔄", "extend": "⏱️", "revoke": "❌"}.get(l["action"], "📝")
            desc += (
                f"{action_emoji} `{l['created_at'][:10]}` **{name}** — "
                f"{l['action']} → {l.get('new_plan', 'N/A')}"
            )
            if l.get("amount"):
                desc += f" (${l['amount']:.2f})"
            if l.get("duration_days"):
                desc += f" [{l['duration_days']}d]"
            desc += "\n"

        embed = discord.Embed(title="📜 Recent Logs", description=desc, color=OWNER_COLOR)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Changelog", style=discord.ButtonStyle.success, emoji="📝", row=2)
    async def changelog_btn(self, interaction, btn):
        await interaction.response.send_modal(ChangelogModal())

    @discord.ui.button(label="Bot Servers", style=discord.ButtonStyle.secondary, emoji="🌐", row=2)
    async def bot_servers_btn(self, interaction, btn):
        guilds = sorted(interaction.client.guilds, key=lambda g: g.member_count or 0, reverse=True)

        desc = ""
        for i, g in enumerate(guilds[:20], 1):
            plan = await get_guild_plan(g.id)
            plan_info = get_plan_info(plan)
            desc += f"`{i}.` {plan_info['emoji']} **{g.name}** — 👥 {g.member_count} | `{g.id}`\n"

        embed = discord.Embed(
            title=f"🌐 Bot Servers ({len(guilds)})",
            description=desc,
            color=OWNER_COLOR
        )
        total_members = sum(g.member_count or 0 for g in guilds)
        embed.set_footer(text=f"Total: {len(guilds)} servers | {total_members} members")
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ═══════════════════════════════════════════════════════════════
#  SUBSCRIPTION COG
# ═══════════════════════════════════════════════════════════════

class Subscription(commands.Cog):
    """👑 Subscription Management (Owner Only)"""

    async def notify_owners(self, embed):
        """Send a notification to all bot owners."""
        for oid in OWNER_IDS:
            try:
                owner = self.bot.get_user(oid)
                if owner:
                    await owner.send(embed=embed)
            except:
                pass

    def __init__(self, bot):
        self.bot = bot
        self.expiry_check.start()

    def cog_unload(self):
        self.expiry_check.cancel()

    async def cog_load(self):
        print("[COG] Subscription system loaded.")

    # ─── Auto Expiry Check ───────────────────────────────────
    @tasks.loop(hours=6)
    async def expiry_check(self):
        """Check for expired subscriptions and notify owner."""
        try:
            expiring = await get_expiring_soon(3)
            if expiring:
                owner = self.bot.get_user(OWNER_ID)
                if owner:
                    desc = ""
                    for s in expiring:
                        guild = self.bot.get_guild(s["guild_id"])
                        name = guild.name if guild else f"ID: {s['guild_id']}"
                        try:
                            exp_dt = datetime.fromisoformat(s["expires_at"]).replace(tzinfo=timezone.utc)
                            remaining = (exp_dt - datetime.now(timezone.utc)).days
                            desc += f"⚠️ **{name}** — {s['plan']} | **{remaining}d left** | `{s['guild_id']}`\n"
                        except:
                            pass

                    if desc:
                        embed = discord.Embed(
                            title="⚠️ Subscriptions Expiring Soon!",
                            description=desc,
                            color=WARNING_COLOR,
                            timestamp=datetime.now(timezone.utc)
                        )
                        try:
                            await owner.send(embed=embed)
                        except:
                            pass
        except:
            pass

    @expiry_check.before_loop
    async def before_expiry(self):
        await self.bot.wait_until_ready()

    # ─── Auto create free sub when bot joins ─────────────────
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Auto-create free subscription when bot joins a server."""
        sub = await get_subscription(guild.id)
        if not sub:
            await create_subscription(guild.id, "free", self.bot.user.id, notes="Auto-created on join")

        # Notify owner
        try:
            owner = self.bot.get_user(OWNER_ID)
            if owner:
                embed = discord.Embed(
                    title="📥 Bot Added to New Server!",
                    color=SUCCESS_COLOR,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="🏠 Server", value=guild.name, inline=True)
                embed.add_field(name="👥 Members", value=f"{guild.member_count}", inline=True)
                embed.add_field(name="👑 Owner", value=f"{guild.owner}", inline=True)
                embed.add_field(name="🆔 ID", value=f"`{guild.id}`", inline=True)
                embed.add_field(name="📋 Plan", value="🆓 Free", inline=True)
                embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
                await owner.send(embed=embed)
        except:
            pass

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Notify owner when bot is removed."""
        try:
            owner = self.bot.get_user(OWNER_ID)
            if owner:
                sub = await get_subscription(guild.id)
                plan = sub["plan"] if sub else "free"
                embed = discord.Embed(
                    title="📤 Bot Removed from Server!",
                    description=f"**{guild.name}** | 👥 {guild.member_count} | Plan: {plan}",
                    color=ERROR_COLOR,
                    timestamp=datetime.now(timezone.utc)
                )
                await owner.send(embed=embed)
        except:
            pass

    # ─── Owner Command ───────────────────────────────────────
    @app_commands.command(name="owner", description="👑 Owner Subscription Panel")
    async def owner_panel(self, interaction: discord.Interaction):
        if interaction.user.id not in OWNER_IDS:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Access Denied",
                    description="This command is only for the bot owner.",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        stats = await get_subscription_stats()
        expiring = await get_expiring_soon(7)
        active_revenue = stats['basic'] * 8 + stats['premium'] * 15 + stats['business'] * 25

        embed = discord.Embed(
            title="👑 Hubix — Owner Panel",
            description=(
                f"```\n"
                f"  ╔═╗╔═╗╔═╗╔═╗╔═╗\n"
                f"  ║H║║U║║B║║I║║X║\n"
                f"  ╚═╝╚═╝╚═╝╚═╝╚═╝\n"
                f"```\n"
                f"**📊 Dashboard:**\n"
                f"🌐 Servers: `{len(interaction.client.guilds)}` | "
                f"👥 Users: `{sum(g.member_count or 0 for g in interaction.client.guilds)}`\n"
                f"💰 Revenue: `${stats['total_revenue']:.2f}` | "
                f"📈 Monthly: `${active_revenue}/mo`\n\n"
                f"**📋 Subscriptions:**\n"
                f"🆓 Free: `{stats['free']}` | 💎 Basic: `{stats['basic']}` | "
                f"⭐ Premium: `{stats['premium']}` | 🚀 Business: `{stats['business']}`\n"
            ),
            color=OWNER_COLOR,
            timestamp=datetime.now(timezone.utc)
        )

        if expiring:
            warn_text = "\n".join([
                f"⚠️ `{s['guild_id']}` — {s['plan']}" for s in expiring[:5]
            ])
            embed.add_field(name=f"⚠️ Expiring Soon ({len(expiring)})", value=warn_text, inline=False)

        embed.add_field(
            name="🛠️ Actions",
            value=(
                "✅ **Activate** — Set plan for a server\n"
                "⏱️ **Extend** — Add time to existing sub\n"
                "❌ **Revoke** — Downgrade to free\n"
                "🔍 **Check** — View server details\n"
                "📋 **All Clients** — List all servers\n"
                "💎 **Active** — Paid subs only\n"
                "⚠️ **Expiring** — Expiring within 7 days\n"
                "💰 **Revenue** — Financial stats\n"
                "📜 **Logs** — Recent activity\n"
                "🌐 **Bot Servers** — All servers bot is in\n"
                "🔑 **Keys** — License key management\n"
                "📝 **Changelog** — Post changelog to servers"
            ),
            inline=False
        )

        embed.set_footer(text="Owner Panel • Expires in 10 minutes")

        view = OwnerPanelView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ─── Plan Check Command (Everyone) ───────────────────────
    @app_commands.command(name="plan", description="📋 Check your server's subscription plan")
    async def plan_check(self, interaction: discord.Interaction):
        sub = await get_subscription(interaction.guild.id)
        plan_name = sub["plan"] if sub else "free"
        plan_info = get_plan_info(plan_name)
        limits = get_plan_limits(plan_name)

        embed = discord.Embed(
            title=f"{plan_info['emoji']} {interaction.guild.name} — {plan_info['name']} Plan",
            color=plan_info["color"]
        )

        if sub and sub.get("expires_at"):
            try:
                exp_dt = datetime.fromisoformat(sub["expires_at"]).replace(tzinfo=timezone.utc)
                remaining = (exp_dt - datetime.now(timezone.utc)).days
                embed.add_field(name="📅 Expires", value=f"`{remaining} days left`", inline=True)
            except:
                pass

        # Feature list
        features = ""
        feature_map = {
            "shop_enabled": ("🛒 Shop/Orders", limits.get("shop_enabled")),
            "reviews_enabled": ("⭐ Reviews", limits.get("reviews_enabled")),
            "farm_enabled": ("🌱 Member Farm", limits.get("farm_enabled")),
            "automod_full": ("🛡️ Full AutoMod", limits.get("automod_full")),
            "invite_leaderboard": ("📨 Invite Leaderboard", limits.get("invite_leaderboard")),
            "transcript_enabled": ("📝 Transcripts", limits.get("transcript_enabled")),
            "utility_full": ("🔧 Full Utility", limits.get("utility_full")),
            "logging_enabled": ("📋 Audit Logging", limits.get("logging_enabled")),
            "auto_role": ("🏷️ Auto Role", limits.get("auto_role")),
            "embed_editor": ("✏️ Embed Editor", limits.get("embed_editor")),
            "bot_nickname": ("📛 Bot Nickname", limits.get("bot_nickname")),
            "bot_avatar": ("🖼️ Bot Server Avatar", limits.get("bot_avatar")),
        }

        for key, (name, enabled) in feature_map.items():
            status = "✅" if enabled else "❌"
            features += f"{status} {name}\n"

        embed.add_field(name="📋 Features", value=features, inline=False)

        limits_text = (
            f"📦 Products: `{limits['max_products']}`\n"
            f"🎉 Giveaways: `{limits['max_active_giveaways']}`\n"
            f"🎫 Ticket Categories: `{limits['max_ticket_categories']}`\n"
            f"🌐 Multi-Server: `{limits['multi_server']}`"
        )
        embed.add_field(name="📊 Limits", value=limits_text, inline=False)

        if plan_name == "free":
            embed.add_field(
                name="⬆️ Upgrade",
                value="Contact the bot owner to upgrade your plan!",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


    # ─── Claim Setup Command (Owner Only) ────────────────────
    @app_commands.command(name="claimsetup", description="🔑 Setup the claim premium panel in a channel")
    @app_commands.describe(channel="Channel to send the claim panel in")
    async def claim_setup(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if interaction.user.id not in OWNER_IDS:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Access Denied",
                    description="This command is only for the bot owner.",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        channel = channel or interaction.channel

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
            color=0x5865F2,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Hubix • Premium Licensing")

        view = ClaimButtonView()
        await channel.send(embed=embed, view=view)

        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Claim Panel Sent!",
                description=f"Claim panel has been set up in {channel.mention}",
                color=SUCCESS_COLOR
            ),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Subscription(bot))