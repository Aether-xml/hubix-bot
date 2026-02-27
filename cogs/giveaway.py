import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta, timezone
import random
import re
from typing import Optional

from utils.database import *
from config import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, PANEL_COLOR, get_plan_limits
from utils.database import get_guild_plan


def parse_duration(s):
    m=re.compile(r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?').fullmatch(s.strip().lower())
    if not m or not any(m.groups()): return None
    t=timedelta(days=int(m[1]or 0),hours=int(m[2]or 0),minutes=int(m[3]or 0),seconds=int(m[4]or 0))
    return t if 10<=t.total_seconds()<=5184000 else None

def fmt_ts(dt,s="R"): return f"<t:{int(dt.timestamp())}:{s}>"

def fmt_dur(td):
    ts=int(td.total_seconds()); d,r=divmod(ts,86400); h,r=divmod(r,3600); m,s=divmod(r,60)
    p=[]
    if d: p.append(f"{d}d")
    if h: p.append(f"{h}h")
    if m: p.append(f"{m}m")
    if s: p.append(f"{s}s")
    return " ".join(p) or "0s"


def build_giveaway_embed(prize, description, host_id, end_time, winner_count, entry_count=0, required_role_id=None, giveaway_id=None):
    e=discord.Embed(title=f"🎉  {prize}",color=EMBED_COLOR,timestamp=end_time)
    if description: e.description=f">>> {description}"
    e.add_field(name="📅 Ends",value=f"{fmt_ts(end_time,'F')}\n({fmt_ts(end_time,'R')})",inline=True)
    e.add_field(name="🎯 Winners",value=f"`{winner_count}`",inline=True)
    e.add_field(name="👤 Host",value=f"<@{host_id}>",inline=True)
    e.add_field(name="📊 Entries",value=f"`{entry_count}`",inline=True)
    if required_role_id: e.add_field(name="🔒 Required Role",value=f"<@&{required_role_id}>",inline=True)
    e.set_footer(text=f"Giveaway ID: {giveaway_id or '...'} • Ends at")
    return e

def build_ended_embed(prize, description, host_id, end_time, winner_count, entry_count, winners, giveaway_id):
    e=discord.Embed(title=f"🎉  {prize}  [ENDED]",color=0x2B2D31,timestamp=end_time)
    if description: e.description=f">>> {description}"
    if winners: e.add_field(name="🏆 Winner(s)",value="\n".join([f"🏆 <@{w}>" for w in winners]),inline=False)
    else: e.add_field(name="🏆 Winner(s)",value="*No valid entries*",inline=False)
    e.add_field(name="📊 Total Entries",value=f"`{entry_count}`",inline=True)
    e.add_field(name="👤 Host",value=f"<@{host_id}>",inline=True)
    e.set_footer(text=f"Giveaway ID: {giveaway_id} • Ended at")
    return e


# ─── Entry Button (persistent) ──────────────────────────────────

class GiveawayButton(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Enter Giveaway",style=discord.ButtonStyle.primary,emoji="🎉",custom_id="nexify:gw:enter")
    async def enter(self, interaction: discord.Interaction, btn):
        g=await get_giveaway_by_message(interaction.message.id)
        if not g: return await interaction.response.send_message("❌ Giveaway not found.",ephemeral=True)
        if g["ended"]: return await interaction.response.send_message("❌ This giveaway has ended!",ephemeral=True)
        if g["required_role_id"]:
            role=interaction.guild.get_role(g["required_role_id"])
            if role and role not in interaction.user.roles:
                return await interaction.response.send_message(f"❌ You need {role.mention} to enter!",ephemeral=True)
        if await has_entry(g["id"],interaction.user.id):
            await remove_entry(g["id"],interaction.user.id); cnt=await get_entry_count(g["id"])
            e=build_giveaway_embed(g["prize"],g["description"],g["host_id"],datetime.fromisoformat(g["end_time"]),g["winner_count"],cnt,g["required_role_id"],g["id"])
            try: await interaction.message.edit(embed=e)
            except: pass
            return await interaction.response.send_message("📤 You left the giveaway.",ephemeral=True)
        else:
            await add_entry(g["id"],interaction.user.id); cnt=await get_entry_count(g["id"])
            e=build_giveaway_embed(g["prize"],g["description"],g["host_id"],datetime.fromisoformat(g["end_time"]),g["winner_count"],cnt,g["required_role_id"],g["id"])
            try: await interaction.message.edit(embed=e)
            except: pass
            return await interaction.response.send_message("🎉 You entered! Good luck!",ephemeral=True)

    @discord.ui.button(label="Participants",style=discord.ButtonStyle.secondary,emoji="👥",custom_id="nexify:gw:parts")
    async def parts(self, interaction: discord.Interaction, btn):
        g=await get_giveaway_by_message(interaction.message.id)
        if not g: return await interaction.response.send_message("❌ Not found.",ephemeral=True)
        entries=await get_entries(g["id"]); cnt=len(entries)
        if not cnt: return await interaction.response.send_message("📋 No entries yet.",ephemeral=True)
        desc="\n".join([f"`{i}.` <@{uid}>" for i,uid in enumerate(entries[:20],1)])
        if cnt>20: desc+=f"\n\n*...and {cnt-20} more*"
        e=discord.Embed(title=f"👥 Participants — {g['prize']}",description=desc,color=EMBED_COLOR)
        e.set_footer(text=f"Total: {cnt}")
        await interaction.response.send_message(embed=e,ephemeral=True)


class GiveawayEndedView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Reroll",style=discord.ButtonStyle.danger,emoji="🔄",custom_id="nexify:gw:reroll")
    async def reroll(self, interaction: discord.Interaction, btn):
        g=await get_giveaway_by_message(interaction.message.id)
        if not g: return await interaction.response.send_message("❌ Not found.",ephemeral=True)
        if interaction.user.id!=g["host_id"] and not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Only host/admins can reroll!",ephemeral=True)
        entries=await get_entries(g["id"])
        if not entries: return await interaction.response.send_message("❌ No entries!",ephemeral=True)
        wc=min(g["winner_count"],len(entries)); nw=random.sample(entries,wc); await save_winners(g["id"],nw)
        wm=", ".join([f"<@{w}>" for w in nw])
        if interaction.message.embeds:
            emb=interaction.message.embeds[0]
            for i,f in enumerate(emb.fields):
                if f.name=="🏆 Winner(s)": emb.set_field_at(i,name="🏆 Winner(s)",value=wm,inline=False); break
            await interaction.message.edit(embed=emb)
        await interaction.response.send_message(f"🔄 **Rerolled!**\n🏆 {wm}\nCongratulations! 🎉")


# ─── Create Giveaway Modal ──────────────────────────────────────

class CreateGiveawayModal(discord.ui.Modal, title="🎉 Create a Giveaway"):
    prize_input=discord.ui.TextInput(label="Prize",placeholder="e.g. Nitro Classic",max_length=256)
    desc_input=discord.ui.TextInput(label="Description (optional)",placeholder="Extra info...",style=discord.TextStyle.paragraph,max_length=1024,required=False)
    dur_input=discord.ui.TextInput(label="Duration",placeholder="e.g. 1d, 2h30m, 10m",max_length=20)
    win_input=discord.ui.TextInput(label="Number of Winners",placeholder="1",max_length=3,default="1")

    def __init__(self, channel, required_role=None):
        super().__init__(); self.channel=channel; self.required_role=required_role

    async def on_submit(self, interaction: discord.Interaction):
        # Plan check — max active giveaways
        plan = await get_guild_plan(interaction.guild.id)
        limits = get_plan_limits(plan)
        active = await get_guild_giveaways(interaction.guild.id, active_only=True)
        max_giveaways = limits.get("max_active_giveaways", 1)
        if len(active) >= max_giveaways:
            from config import get_plan_info
            plan_info = get_plan_info(plan)
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔒 Giveaway Limit Reached",
                    description=(
                        f"Your **{plan_info['emoji']} {plan_info['name']}** plan allows max **{max_giveaways}** active giveaway(s).\n"
                        f"You currently have **{len(active)}** active.\n\n"
                        f"End a giveaway or upgrade your plan!"
                    ),
                    color=ERROR_COLOR
                ),
                ephemeral=True
            )

        dur=parse_duration(self.dur_input.value)
        if not dur: return await interaction.response.send_message("❌ Invalid duration! (e.g. `1d`, `2h30m`)",ephemeral=True)
        try:
            wc=int(self.win_input.value)
            if not 1<=wc<=50: raise ValueError
        except: return await interaction.response.send_message("❌ Winners must be 1-50!",ephemeral=True)
        end=datetime.now(timezone.utc)+dur; prize=self.prize_input.value.strip(); desc=self.desc_input.value.strip() if self.desc_input.value else ""
        rid=self.required_role.id if self.required_role else None
        e=build_giveaway_embed(prize,desc,interaction.user.id,end,wc,0,rid)
        msg=await self.channel.send(embed=e,view=GiveawayButton())
        gid=await create_giveaway(interaction.guild.id,self.channel.id,msg.id,interaction.user.id,prize,desc,wc,rid,end.isoformat())
        e=build_giveaway_embed(prize,desc,interaction.user.id,end,wc,0,rid,gid)
        await msg.edit(embed=e)
        ce=discord.Embed(title="✅ Giveaway Created!",color=SUCCESS_COLOR)
        ce.add_field(name="🎁 Prize",value=prize,inline=True); ce.add_field(name="📍 Channel",value=self.channel.mention,inline=True)
        ce.add_field(name="⏱️ Duration",value=fmt_dur(dur),inline=True); ce.add_field(name="🆔 ID",value=f"`{gid}`",inline=True)
        ce.add_field(name="🔗 Jump",value=f"[Click]({msg.jump_url})",inline=False)
        await interaction.response.send_message(embed=ce,ephemeral=True)


# ─── End Giveaway Modal ─────────────────────────────────────────

class EndGiveawayModal(discord.ui.Modal, title="⏹️ End a Giveaway"):
    gid_input=discord.ui.TextInput(label="Giveaway ID",placeholder="Enter the giveaway ID number")

    def __init__(self, cog): super().__init__(); self.cog=cog

    async def on_submit(self, interaction: discord.Interaction):
        try: gid=int(self.gid_input.value)
        except: return await interaction.response.send_message("❌ Invalid ID!",ephemeral=True)
        g=await get_giveaway_by_id(gid)
        if not g: return await interaction.response.send_message("❌ Not found!",ephemeral=True)
        if g["guild_id"]!=interaction.guild.id: return await interaction.response.send_message("❌ Wrong server!",ephemeral=True)
        if g["ended"]: return await interaction.response.send_message("❌ Already ended!",ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        await self.cog.finish_giveaway(g)
        await interaction.followup.send(f"✅ Giveaway **#{gid}** (`{g['prize']}`) ended!",ephemeral=True)


class RerollModal(discord.ui.Modal, title="🔄 Reroll Giveaway"):
    gid_input=discord.ui.TextInput(label="Giveaway ID",placeholder="Enter the giveaway ID")

    async def on_submit(self, interaction: discord.Interaction):
        try: gid=int(self.gid_input.value)
        except: return await interaction.response.send_message("❌ Invalid ID!",ephemeral=True)
        g=await get_giveaway_by_id(gid)
        if not g: return await interaction.response.send_message("❌ Not found!",ephemeral=True)
        if not g["ended"]: return await interaction.response.send_message("❌ Not ended yet!",ephemeral=True)
        entries=await get_entries(g["id"])
        if not entries: return await interaction.response.send_message("❌ No entries!",ephemeral=True)
        wc=min(g["winner_count"],len(entries)); nw=random.sample(entries,wc); await save_winners(g["id"],nw)
        wm=", ".join([f"<@{w}>" for w in nw])
        try:
            ch=interaction.guild.get_channel(g["channel_id"])
            if ch:
                msg=await ch.fetch_message(g["message_id"])
                et=datetime.fromisoformat(g["end_time"])
                emb=build_ended_embed(g["prize"],g["description"],g["host_id"],et,wc,len(entries),nw,g["id"])
                await msg.edit(embed=emb)
                await ch.send(f"🔄 **Rerolled!** ({g['prize']})\n🏆 {wm}\nCongrats! 🎉")
        except: pass
        await interaction.response.send_message(f"✅ Rerolled **#{gid}**!\n🏆 {wm}",ephemeral=True)


class CancelModal(discord.ui.Modal, title="🗑️ Cancel Giveaway"):
    gid_input=discord.ui.TextInput(label="Giveaway ID",placeholder="Enter the giveaway ID")

    async def on_submit(self, interaction: discord.Interaction):
        try: gid=int(self.gid_input.value)
        except: return await interaction.response.send_message("❌ Invalid ID!",ephemeral=True)
        g=await get_giveaway_by_id(gid)
        if not g: return await interaction.response.send_message("❌ Not found!",ephemeral=True)
        if g["guild_id"]!=interaction.guild.id: return await interaction.response.send_message("❌ Wrong server!",ephemeral=True)
        try:
            ch=interaction.guild.get_channel(g["channel_id"])
            if ch: msg=await ch.fetch_message(g["message_id"]); await msg.delete()
        except: pass
        await delete_giveaway(gid)
        await interaction.response.send_message(f"✅ Giveaway **#{gid}** cancelled!",ephemeral=True)


class InfoModal(discord.ui.Modal, title="ℹ️ Giveaway Info"):
    gid_input=discord.ui.TextInput(label="Giveaway ID",placeholder="Enter the giveaway ID")

    async def on_submit(self, interaction: discord.Interaction):
        try: gid=int(self.gid_input.value)
        except: return await interaction.response.send_message("❌ Invalid ID!",ephemeral=True)
        g=await get_giveaway_by_id(gid)
        if not g: return await interaction.response.send_message("❌ Not found!",ephemeral=True)
        et=datetime.fromisoformat(g["end_time"]); ec=await get_entry_count(g["id"])
        status="🔴 Ended" if g["ended"] else "🟢 Active"
        e=discord.Embed(title=f"ℹ️ Giveaway #{gid}",color=EMBED_COLOR if not g["ended"] else 0x2B2D31)
        e.add_field(name="🎁 Prize",value=g["prize"],inline=True); e.add_field(name="📌 Status",value=status,inline=True)
        e.add_field(name="👤 Host",value=f"<@{g['host_id']}>",inline=True); e.add_field(name="📊 Entries",value=str(ec),inline=True)
        e.add_field(name="🎯 Winners",value=str(g["winner_count"]),inline=True)
        e.add_field(name="📅 End",value=f"{fmt_ts(et,'F')} ({fmt_ts(et,'R')})",inline=False)
        if g["ended"]:
            winners=await get_winners(g["id"])
            if winners: e.add_field(name="🏆 Winners",value=", ".join([f"<@{w}>" for w in winners]),inline=False)
        await interaction.response.send_message(embed=e,ephemeral=True)


# ─── GIVEAWAY PANEL VIEW ────────────────────────────────────────

class GiveawayPanelView(discord.ui.View):
    def __init__(self, cog): super().__init__(timeout=300); self.cog=cog

    @discord.ui.button(label="Create Giveaway",style=discord.ButtonStyle.success,emoji="🎉",row=0)
    async def create_btn(self, interaction: discord.Interaction, btn):
        modal=CreateGiveawayModal(channel=interaction.channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="End Giveaway",style=discord.ButtonStyle.danger,emoji="⏹️",row=0)
    async def end_btn(self, interaction: discord.Interaction, btn):
        await interaction.response.send_modal(EndGiveawayModal(self.cog))

    @discord.ui.button(label="Reroll",style=discord.ButtonStyle.primary,emoji="🔄",row=0)
    async def reroll_btn(self, interaction: discord.Interaction, btn):
        await interaction.response.send_modal(RerollModal())

    @discord.ui.button(label="Cancel Giveaway",style=discord.ButtonStyle.danger,emoji="🗑️",row=1)
    async def cancel_btn(self, interaction: discord.Interaction, btn):
        await interaction.response.send_modal(CancelModal())

    @discord.ui.button(label="Giveaway Info",style=discord.ButtonStyle.secondary,emoji="ℹ️",row=1)
    async def info_btn(self, interaction: discord.Interaction, btn):
        await interaction.response.send_modal(InfoModal())

    @discord.ui.button(label="List Active",style=discord.ButtonStyle.secondary,emoji="📋",row=1)
    async def list_btn(self, interaction: discord.Interaction, btn):
        giveaways=await get_guild_giveaways(interaction.guild.id,True)
        if not giveaways:
            return await interaction.response.send_message(embed=discord.Embed(title="📋 Active Giveaways",description="*No active giveaways.*",color=WARNING_COLOR),ephemeral=True)
        e=discord.Embed(title="📋 Active Giveaways",color=EMBED_COLOR)
        for g in giveaways[:15]:
            et=datetime.fromisoformat(g["end_time"]); ec=await get_entry_count(g["id"])
            e.add_field(name=f"#{g['id']} — {g['prize']}",value=f"📍 <#{g['channel_id']}> | ⏱️ {fmt_ts(et,'R')}\n👤 <@{g['host_id']}> | 📊 `{ec}` entries | 🎯 `{g['winner_count']}` winners",inline=False)
        e.set_footer(text=f"Total: {len(giveaways)}")
        await interaction.response.send_message(embed=e,ephemeral=True)

    async def on_timeout(self):
        pass


# ─── Giveaway Cog ───────────────────────────────────────────────

class Giveaway(commands.Cog):
    def __init__(self, bot): self.bot=bot

    async def cog_load(self):
        self.bot.add_view(GiveawayButton()); self.bot.add_view(GiveawayEndedView())
        self.check_giveaways.start(); print("[COG] Giveaway system loaded.")

    async def cog_unload(self): self.check_giveaways.cancel()

    @tasks.loop(seconds=15)
    async def check_giveaways(self):
        try:
            for g in await get_active_giveaways():
                et=datetime.fromisoformat(g["end_time"])
                if et.tzinfo is None: et=et.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc)>=et: await self.finish_giveaway(g)
        except Exception as e: print(f"[GW ERROR] {e}")

    @check_giveaways.before_loop
    async def before_check(self): await self.bot.wait_until_ready()

    async def finish_giveaway(self, g):
        try:
            guild=self.bot.get_guild(g["guild_id"])
            if not guild: await end_giveaway(g["id"]); return
            ch=guild.get_channel(g["channel_id"])
            if not ch: await end_giveaway(g["id"]); return
            try: msg=await ch.fetch_message(g["message_id"])
            except: await end_giveaway(g["id"]); return
            entries=await get_entries(g["id"]); ec=len(entries); et=datetime.fromisoformat(g["end_time"])
            wc=min(g["winner_count"],len(entries)); winners=random.sample(entries,wc) if entries else []
            if winners: await save_winners(g["id"],winners)
            await end_giveaway(g["id"])
            emb=build_ended_embed(g["prize"],g["description"],g["host_id"],et,g["winner_count"],ec,winners,g["id"])
            await msg.edit(embed=emb,view=GiveawayEndedView())
            if winners:
                wm=", ".join([f"<@{w}>" for w in winners])
                ae=discord.Embed(title="🎊 Giveaway Ended!",description=f"**🎁** {g['prize']}\n**🏆** {wm}\n\nContact <@{g['host_id']}> to claim!",color=SUCCESS_COLOR)
                await ch.send(content=f"🎉 {wm}",embed=ae)
            else:
                await ch.send(embed=discord.Embed(title="🎊 Giveaway Ended!",description=f"**🎁** {g['prize']}\n\n*No entries — no winners.*",color=WARNING_COLOR))
        except Exception as e: print(f"[GW ERROR] finish: {e}"); await end_giveaway(g["id"])

    @app_commands.command(name="giveaway",description="🎉 Open the Giveaway Management Panel")
    @app_commands.default_permissions(manage_guild=True)
    async def giveaway_panel(self, interaction: discord.Interaction):
        embed=discord.Embed(
            title="🎉 Giveaway Management Panel",
            description=(
                "Use the buttons below to manage giveaways.\n\n"
                "🎉 **Create** — Start a new giveaway\n"
                "⏹️ **End** — End a giveaway early\n"
                "🔄 **Reroll** — Pick new winners\n"
                "🗑️ **Cancel** — Delete a giveaway\n"
                "ℹ️ **Info** — Get giveaway details\n"
                "📋 **List** — View all active giveaways"
            ),
            color=PANEL_COLOR
        )
        embed.set_footer(text="Nexify Giveaway System • Panel expires in 5 minutes")
        await interaction.response.send_message(embed=embed,view=GiveawayPanelView(self),ephemeral=True)


async def setup(bot): await bot.add_cog(Giveaway(bot))