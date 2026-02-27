import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from typing import Optional

from utils.database import *
from config import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, INVITE_COLOR, PANEL_COLOR, get_plan_limits
from utils.database import get_guild_plan


class InviteSetupModal(discord.ui.Modal, title="📌 Set Log Channel"):
    channel_input=discord.ui.TextInput(label="Channel ID",placeholder="Right-click channel → Copy Channel ID")

    def __init__(self, cog): super().__init__(); self.cog=cog

    async def on_submit(self, interaction: discord.Interaction):
        try: cid=int(self.channel_input.value)
        except: return await interaction.response.send_message("❌ Invalid channel ID!",ephemeral=True)
        ch=interaction.guild.get_channel(cid)
        if not ch: return await interaction.response.send_message("❌ Channel not found!",ephemeral=True)
        await set_invite_log_channel(interaction.guild.id,ch.id)
        await self.cog.cache_guild_invites(interaction.guild)
        try: await ch.send(embed=discord.Embed(title="📨 Invite Tracking Activated!",description="This channel will now log all joins/leaves.",color=INVITE_COLOR))
        except: pass
        await interaction.response.send_message(embed=discord.Embed(title="✅ Log Channel Set!",description=f"Channel: {ch.mention}",color=SUCCESS_COLOR),ephemeral=True)


class InviteCheckModal(discord.ui.Modal, title="📊 Check User Invites"):
    user_input=discord.ui.TextInput(label="User ID (leave empty for yourself)",placeholder="Right-click user → Copy User ID",required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if self.user_input.value:
            try: uid=int(self.user_input.value)
            except: return await interaction.response.send_message("❌ Invalid ID!",ephemeral=True)
            target=interaction.guild.get_member(uid)
            if not target: return await interaction.response.send_message("❌ User not found!",ephemeral=True)
        else: target=interaction.user
        stats=await get_user_invite_stats(interaction.guild.id,target.id)
        e=discord.Embed(title=f"📊 Invite Stats — {target.display_name}",color=INVITE_COLOR)
        e.set_thumbnail(url=target.display_avatar.url)
        e.add_field(name="📥 Total",value=f"```{stats['total']}```",inline=True)
        e.add_field(name="✅ Active",value=f"```{stats['active']}```",inline=True)
        e.add_field(name="📤 Left",value=f"```{stats['leaves']}```",inline=True)
        inv_list=await get_invite_list(interaction.guild.id,target.id,10)
        if inv_list:
            txt=""
            for inv in inv_list:
                s="📤" if inv["has_left"] else "✅"
                txt+=f"{s} <@{inv['invited_id']}>\n"
            e.add_field(name="📋 Recent",value=txt,inline=False)
        await interaction.response.send_message(embed=e,ephemeral=True)


class InviteWhoModal(discord.ui.Modal, title="🔍 Who Invited?"):
    user_input=discord.ui.TextInput(label="User ID",placeholder="Right-click user → Copy User ID")

    async def on_submit(self, interaction: discord.Interaction):
        try: uid=int(self.user_input.value)
        except: return await interaction.response.send_message("❌ Invalid ID!",ephemeral=True)
        target=interaction.guild.get_member(uid)
        inviter_id=await get_invited_by(interaction.guild.id,uid)
        name=target.display_name if target else str(uid)
        e=discord.Embed(title=f"🔍 Who Invited {name}?",color=INVITE_COLOR)
        if inviter_id:
            st=await get_user_invite_stats(interaction.guild.id,inviter_id)
            e.add_field(name="📨 Invited By",value=f"<@{inviter_id}>",inline=True)
            e.add_field(name="📊 Stats",value=f"Total: `{st['total']}` | Active: `{st['active']}` | Left: `{st['leaves']}`",inline=False)
        else: e.description="*Unknown — may have joined before tracking or via vanity URL.*"
        await interaction.response.send_message(embed=e,ephemeral=True)


class InviteResetModal(discord.ui.Modal, title="🗑️ Reset User Invites"):
    user_input=discord.ui.TextInput(label="User ID",placeholder="Right-click user → Copy User ID")

    async def on_submit(self, interaction: discord.Interaction):
        try: uid=int(self.user_input.value)
        except: return await interaction.response.send_message("❌ Invalid ID!",ephemeral=True)
        await reset_user_invites(interaction.guild.id,uid)
        await interaction.response.send_message(embed=discord.Embed(title="✅ Invites Reset",description=f"Data for <@{uid}> cleared.",color=SUCCESS_COLOR),ephemeral=True)


# ─── INVITE PANEL VIEW ──────────────────────────────────────────

class InvitePanelView(discord.ui.View):
    def __init__(self, cog): super().__init__(timeout=300); self.cog=cog

    @discord.ui.button(label="Set Log Channel",style=discord.ButtonStyle.success,emoji="📌",row=0)
    async def setup_btn(self, interaction: discord.Interaction, btn):
        await interaction.response.send_modal(InviteSetupModal(self.cog))

    @discord.ui.button(label="Enable",style=discord.ButtonStyle.success,emoji="🟢",row=0)
    async def enable_btn(self, interaction: discord.Interaction, btn):
        s=await get_invite_settings(interaction.guild.id)
        if not s or not s.get("log_channel_id"):
            return await interaction.response.send_message("❌ Set a log channel first!",ephemeral=True)
        await toggle_invite_tracking(interaction.guild.id,True)
        await self.cog.cache_guild_invites(interaction.guild)
        await interaction.response.send_message(embed=discord.Embed(title="🟢 Invite Tracking Enabled",color=SUCCESS_COLOR),ephemeral=True)

    @discord.ui.button(label="Disable",style=discord.ButtonStyle.danger,emoji="🔴",row=0)
    async def disable_btn(self, interaction: discord.Interaction, btn):
        await toggle_invite_tracking(interaction.guild.id,False)
        await interaction.response.send_message(embed=discord.Embed(title="🔴 Invite Tracking Disabled",color=ERROR_COLOR),ephemeral=True)

    @discord.ui.button(label="Check Invites",style=discord.ButtonStyle.primary,emoji="📊",row=1)
    async def check_btn(self, interaction: discord.Interaction, btn):
        await interaction.response.send_modal(InviteCheckModal())

    @discord.ui.button(label="Who Invited?",style=discord.ButtonStyle.primary,emoji="🔍",row=1)
    async def who_btn(self, interaction: discord.Interaction, btn):
        await interaction.response.send_modal(InviteWhoModal())

    @discord.ui.button(label="Leaderboard",style=discord.ButtonStyle.primary,emoji="🏆",row=1)
    async def lb_btn(self, interaction: discord.Interaction, btn):
        plan = await get_guild_plan(interaction.guild.id)
        limits = get_plan_limits(plan)
        if not limits.get("invite_leaderboard"):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔒 Feature Locked",
                    description="**Invite Leaderboard** requires **💎 Basic** plan or higher.\nContact the bot owner to upgrade!",
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )
        lb=await get_invite_leaderboard(interaction.guild.id,15)
        if not lb: return await interaction.response.send_message(embed=discord.Embed(title="🏆 Leaderboard",description="*No data yet.*",color=WARNING_COLOR),ephemeral=True)
        medals=["🥇","🥈","🥉"]; desc=""
        for i,en in enumerate(lb):
            m=medals[i] if i<3 else f"`#{i+1}`"
            desc+=f"{m} <@{en['inviter_id']}> — **{en['active']}** active ({en['total']} total, {en['leaves']} left)\n"
        e=discord.Embed(title=f"🏆 Invite Leaderboard",description=desc,color=INVITE_COLOR)
        await interaction.response.send_message(embed=e,ephemeral=True)

    @discord.ui.button(label="Reset User",style=discord.ButtonStyle.danger,emoji="🗑️",row=2)
    async def reset_btn(self, interaction: discord.Interaction, btn):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admin only!",ephemeral=True)
        await interaction.response.send_modal(InviteResetModal())

    @discord.ui.button(label="Reset All",style=discord.ButtonStyle.danger,emoji="💣",row=2)
    async def reset_all_btn(self, interaction: discord.Interaction, btn):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admin only!",ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(title="⚠️ Reset ALL invite data?",description="**This cannot be undone!**",color=WARNING_COLOR),view=ConfirmResetAllView(interaction.guild.id),ephemeral=True)

    @discord.ui.button(label="Settings",style=discord.ButtonStyle.secondary,emoji="⚙️",row=2)
    async def settings_btn(self, interaction: discord.Interaction, btn):
        s=await get_invite_settings(interaction.guild.id)
        e=discord.Embed(title="⚙️ Invite Settings",color=INVITE_COLOR)
        if s:
            status="🟢 Enabled" if s["enabled"] else "🔴 Disabled"
            ch=f"<#{s['log_channel_id']}>" if s["log_channel_id"] else "*Not set*"
            cached=len(self.cog.invite_cache.get(interaction.guild.id,{}))
            e.add_field(name="Status",value=status,inline=True); e.add_field(name="Channel",value=ch,inline=True)
            e.add_field(name="Cached",value=f"`{cached}`",inline=True)
        else: e.description="*Not configured. Use Set Log Channel.*"
        await interaction.response.send_message(embed=e,ephemeral=True)


class ConfirmResetAllView(discord.ui.View):
    def __init__(self, gid): super().__init__(timeout=30); self.gid=gid

    @discord.ui.button(label="Confirm",style=discord.ButtonStyle.danger,emoji="🗑️")
    async def confirm(self, interaction: discord.Interaction, btn):
        await reset_all_invites(self.gid); self.stop()
        await interaction.response.edit_message(embed=discord.Embed(title="🗑️ All Data Reset",color=SUCCESS_COLOR),view=None)

    @discord.ui.button(label="Cancel",style=discord.ButtonStyle.secondary,emoji="❌")
    async def cancel(self, interaction: discord.Interaction, btn):
        self.stop(); await interaction.response.edit_message(embed=discord.Embed(title="❌ Cancelled",color=ERROR_COLOR),view=None)


# ─── Invites Cog ─────────────────────────────────────────────────

class Invites(commands.Cog):
    def __init__(self, bot): self.bot=bot; self.invite_cache={}

    async def cog_load(self):
        self.bot.loop.create_task(self.initialize_cache()); print("[COG] Invite tracking loaded.")

    async def initialize_cache(self):
        await self.bot.wait_until_ready()
        for g in self.bot.guilds:
            try: await self.cache_guild_invites(g)
            except: pass
        print(f"[INVITES] Cached {len(self.invite_cache)} guild(s).")

    async def cache_guild_invites(self, guild):
        try:
            invites=await guild.invites(); self.invite_cache[guild.id]={}; db_inv=[]
            for i in invites:
                if i.inviter: self.invite_cache[guild.id][i.code]=i.uses or 0; db_inv.append({"code":i.code,"inviter_id":i.inviter.id,"uses":i.uses or 0})
            await cache_invites(guild.id,db_inv)
        except: pass

    async def find_used_invite(self, guild):
        try: current=await guild.invites()
        except: return None,None
        old=self.invite_cache.get(guild.id,{})
        for i in current:
            if i.uses and i.uses>old.get(i.code,0):
                self.invite_cache[guild.id][i.code]=i.uses
                db_inv=[{"code":x.code,"inviter_id":x.inviter.id,"uses":x.uses or 0} for x in current if x.inviter]
                await cache_invites(guild.id,db_inv)
                return i,i.inviter
        self.invite_cache[guild.id]={i.code:i.uses or 0 for i in current if i.inviter}
        return None,None

    @commands.Cog.listener()
    async def on_guild_join(self, guild): await self.cache_guild_invites(guild)
    @commands.Cog.listener()
    async def on_guild_remove(self, guild): self.invite_cache.pop(guild.id,None)
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if invite.guild:
            self.invite_cache.setdefault(invite.guild.id,{})[invite.code]=invite.uses or 0
    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        if invite.guild and invite.guild.id in self.invite_cache:
            self.invite_cache[invite.guild.id].pop(invite.code,None)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot: return
        guild=member.guild; s=await get_invite_settings(guild.id)
        if not s or not s.get("enabled"): await self.cache_guild_invites(guild); return
        inv,inviter=await self.find_used_invite(guild)
        ch_id=s.get("log_channel_id")
        if not ch_id: return
        ch=guild.get_channel(ch_id)
        if not ch: return
        now=datetime.now(timezone.utc)
        if inv and inviter and inviter.id!=member.id:
            await track_invite(guild.id,inviter.id,member.id,inv.code)
            st=await get_user_invite_stats(guild.id,inviter.id)
            e=discord.Embed(title="👋 New Member Joined",description=f"**{member}** joined the server!",color=SUCCESS_COLOR,timestamp=now)
            e.set_thumbnail(url=member.display_avatar.url)
            e.add_field(name="📊 Member Info",value=f"**User:** {member.mention}\n**ID:** `{member.id}`",inline=False)
            e.add_field(name="📨 Invited By",value=f"**User:** {inviter.mention}\n**Invites:** ✅ {st['total']} total, 📥 {st['active']} active, 📤 {st['leaves']} left",inline=False)
            e.set_footer(text=f"Total Server Members: {guild.member_count}")
        else:
            e=discord.Embed(title="👋 New Member Joined",description=f"**{member}** joined the server!",color=WARNING_COLOR,timestamp=now)
            e.set_thumbnail(url=member.display_avatar.url)
            e.add_field(name="📊 Member Info",value=f"**User:** {member.mention}\n**ID:** `{member.id}`",inline=False)
            e.add_field(name="🔗 Join Method",value="Vanity URL / Unknown",inline=False)
            e.set_footer(text=f"Total Server Members: {guild.member_count}")
        try: await ch.send(embed=e)
        except: pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.bot: return
        guild=member.guild; s=await get_invite_settings(guild.id)
        if not s or not s.get("enabled"): return
        inviter_id=await track_leave(guild.id,member.id)
        ch_id=s.get("log_channel_id")
        if not ch_id: return
        ch=guild.get_channel(ch_id)
        if not ch: return
        e=discord.Embed(title="👋 Member Left",description=f"**{member}** left the server.",color=ERROR_COLOR,timestamp=datetime.now(timezone.utc))
        e.set_thumbnail(url=member.display_avatar.url)
        info=f"**User:** `{member}` (`{member.id}`)"
        if member.joined_at: info+=f"\n**Joined:** <t:{int(member.joined_at.timestamp())}:R>"
        e.add_field(name="📊 Member Info",value=info,inline=False)
        if inviter_id:
            st=await get_user_invite_stats(guild.id,inviter_id)
            e.add_field(name="📨 Was Invited By",value=f"**User:** <@{inviter_id}>\n**Invites:** ✅ {st['total']} total, 📥 {st['active']} active, 📤 {st['leaves']} left",inline=False)
        else: e.add_field(name="📨 Was Invited By",value="*Unknown*",inline=False)
        e.set_footer(text=f"Total Server Members: {guild.member_count}")
        try: await ch.send(embed=e)
        except: pass
        await self.cache_guild_invites(guild)

    @app_commands.command(name="invites",description="📨 Open the Invite Tracking Panel")
    @app_commands.default_permissions(manage_guild=True)
    async def invites_panel(self, interaction: discord.Interaction):
        embed=discord.Embed(
            title="📨 Invite Tracking Panel",
            description=(
                "Use the buttons below to manage invite tracking.\n\n"
                "📌 **Set Log Channel** — Choose where logs go\n"
                "🟢 **Enable** / 🔴 **Disable** — Toggle tracking\n"
                "📊 **Check Invites** — View user's invite stats\n"
                "🔍 **Who Invited?** — Find who invited someone\n"
                "🏆 **Leaderboard** — Top inviters\n"
                "🗑️ **Reset User** — Clear a user's data\n"
                "💣 **Reset All** — Clear all server data\n"
                "⚙️ **Settings** — View current config"
            ),
            color=PANEL_COLOR
        )
        embed.set_footer(text="Nexify Invite System • Panel expires in 5 minutes")
        await interaction.response.send_message(embed=embed,view=InvitePanelView(self),ephemeral=True)


async def setup(bot): await bot.add_cog(Invites(bot))