import discord
from discord.ext import commands
import asyncio

from core import TOKEN, BOT_VERSION, log

INITIAL_EXTENSIONS = [
    "cogs.moderation",
    "cogs.automod",
    "cogs.giveaways",
    "cogs.events",
    "cogs.misc",
]

intents = discord.Intents.all()
intents.message_content = True

class CrumbBot(commands.Bot):
    def __init__(self): 
        super().__init__(command_prefix="c.", intents=intents)
        self.synced = False

    async def setup_hook(self):
        for ext in INITIAL_EXTENSIONS:
            try:
                await self.load_extension(ext)
                log.info(f"Loaded extension: {ext}")
            except Exception as e:
                log.exception(f"Failed to load extension {ext}: {e}")

bot = CrumbBot()

@bot.event
async def on_ready():
    if not bot.synced:
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                log.info(f"Synced commands to {guild.name}")
            except Exception as e:
                log.error(f"Sync failed for {guild.name}: {e}")

        bot.synced = True

    log.info(f"Logged in as {bot.user} (v{BOT_VERSION})")

@bot.event
async def on_guild_join(guild: discord.Guild):
    log.info(f"Joined {guild.name}")

    try:
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        log.info(f"Synced commands to {guild.name}")
    except Exception as e:
        log.error(f"Failed to sync commands for {guild.name}: {e}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    log.exception(error)

    if interaction.response.is_done():
        await interaction.followup.send("something broke 💀", ephemeral=True)
    else:
        await interaction.response.send_message("something broke 💀", ephemeral=True)

if __name__ == "__main__":
    log.info("Bot starting...")
    bot.run(TOKEN)