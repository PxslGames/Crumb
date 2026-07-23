import discord
from discord.ext import commands
from discord import app_commands
import random
import time
import psutil

from core import START_TIME, OWNER_ID, get_system_channel, PING_MESSAGES

class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="check if crumb is online")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(random.choice(PING_MESSAGES), ephemeral=True)

    @app_commands.command(name="info", description="bot info")
    async def info(self, interaction: discord.Interaction):

        uptime = int(time.time() - START_TIME)
        process = psutil.Process()

        await interaction.response.send_message(
            f"uptime: {uptime}s\nram: {process.memory_info().rss / 1024 / 1024:.1f}MB\nservers: {len(self.bot.guilds)}",
            ephemeral=True
        )

    @app_commands.command(name="status", description="set status")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def status(self, interaction: discord.Interaction, text: str):

        await self.bot.change_presence(activity=discord.CustomActivity(name=text))
        await interaction.response.send_message("yo updated status cuh", ephemeral=True)

    @app_commands.command(name="announce", description="Send a message to all servers system channels (owner only)")
    async def announce(self, interaction: discord.Interaction, message: str):

        if interaction.user.id != OWNER_ID:
            return await interaction.response.send_message(
                "you are not allowed to use this command.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "sending announcement...",
            ephemeral=True
        )

        sent = 0
        failed = 0

        for guild in self.bot.guilds:
            channel = get_system_channel(guild)

            if not channel:
                failed += 1
                continue

            try:
                await channel.send(message)
                sent += 1
            except:
                failed += 1

        await interaction.followup.send(
            f"done.\nsent: {sent}\nfailed: {failed}",
            ephemeral=True
        )

    @app_commands.command(name="stats", description="view server stats")
    async def stats(self, interaction: discord.Interaction):
        guild = interaction.guild

        total_members = guild.member_count or len(guild.members)
        bots = sum(1 for m in guild.members if m.bot)
        humans = total_members - bots

        online = sum(
            1 for m in guild.members
            if m.status != discord.Status.offline
        )

        boosts = guild.premium_subscription_count or 0
        boost_level = guild.premium_tier

        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)

        roles = len(guild.roles)
        emojis = len(guild.emojis)
        stickers = len(guild.stickers)

        msg = (
            f"**{guild.name} stats**\n\n"

            f"👥 **Members**\n"
            f"Total: {total_members}\n"
            f"Humans: {humans}\n"
            f"Bots: {bots}\n"
            f"Online: {online}\n\n"

            f"🚀 **Boosts**\n"
            f"Boosts: {boosts}\n"
            f"Level: {boost_level}\n\n"

            f"📊 **Server**\n"
            f"Roles: {roles}\n"
            f"Emojis: {emojis}\n"
            f"Stickers: {stickers}\n\n"

            f"📁 **Channels**\n"
            f"Text: {text_channels}\n"
            f"Voice: {voice_channels}\n"
            f"Categories: {categories}\n\n"

            f"ID: {guild.id}"
        )

        await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Misc(bot))