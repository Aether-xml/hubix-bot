import discord
from discord.ext import commands
import os
import asyncio
from config import BOT_TOKEN, PREFIX, OWNER_ID
from utils.database import init_db
from api import BotAPI


class Nexify(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        super().__init__(
            command_prefix=PREFIX, intents=intents,
            activity=discord.Activity(type=discord.ActivityType.watching, name="hubix.dev | /help"),
            status=discord.Status.dnd
        )
        self._api_started = False

    async def setup_hook(self):
        print("=" * 55)
        print("  ╔═╗╔═╗╔═╗╔═╗╔═╗")
        print("  ║H║║U║║B║║I║║X║")
        print("  ╚═╝╚═╝╚═╝╚═╝╚═╝")
        print("=" * 55)
        await init_db()

        # Start API server early so Render detects the port
        if not self._api_started:
            self._api_started = True
            self.api = BotAPI(self)
            await self.api.start()

        # Register persistent views
        from cogs.subscription import ClaimButtonView
        self.add_view(ClaimButtonView())

        try:
            from cogs.server_setup import VerifyButtonView
            self.add_view(VerifyButtonView())
        except ImportError:
            pass

        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        loaded = failed = 0
        for f in os.listdir(cogs_dir):
            if f.endswith(".py") and not f.startswith("_"):
                try:
                    await self.load_extension(f"cogs.{f[:-3]}")
                    print(f"  ✅ {f[:-3]}")
                    loaded += 1
                except Exception as e:
                    print(f"  ❌ {f[:-3]}: {e}")
                    failed += 1
        print(f"\n  📦 {loaded} loaded, {failed} failed")
        try:
            synced = await self.tree.sync()
            print(f"  📡 Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"  ❌ Sync: {e}")
        print("=" * 55)

    async def on_ready(self):
        print(f"\n  🟢 {self.user} online!")
        print(f"  📊 {len(self.guilds)} servers | {sum(g.member_count or 0 for g in self.guilds)} users")
        print("=" * 55)


async def on_tree_error(interaction, error):
    if isinstance(error, discord.app_commands.MissingPermissions):
        e = discord.Embed(title="❌ Missing Permissions", color=0xED4245)
        e.description = f"Required: {', '.join([f'`{p}`' for p in error.missing_permissions])}"
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        e = discord.Embed(title="⏳ Cooldown", description=f"Try in **{error.retry_after:.1f}s**", color=0xFEE75C)
    else:
        print(f"[ERROR] {error}")
        e = discord.Embed(title="❌ Error", description="Something went wrong.", color=0xED4245)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=e, ephemeral=True)
        else:
            await interaction.response.send_message(embed=e, ephemeral=True)
    except Exception:
        pass


def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not found!")
        return
    bot = Nexify()
    bot.tree.on_error = on_tree_error
    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
