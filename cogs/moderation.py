import discord
from discord.ext import commands
from discord import app_commands
import datetime

from core import OWNER_ID, warns, save_data

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):

        if member.id == OWNER_ID:
            return await interaction.response.send_message(
                "You can't moderate the bot owner.",
                ephemeral=True
            )

        if member.bot:
            return await interaction.response.send_message("you cant warn bots.", ephemeral=True)

        gid = str(interaction.guild.id)
        uid = str(member.id)

        warns.setdefault(gid, {}).setdefault(uid, [])

        warn_data = {
            "reason": reason,
            "moderator": str(interaction.user),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }

        warns[gid][uid].append(warn_data)
        total_warns = len(warns[gid][uid])

        await save_data()

        try:
            await member.send(
                f"You have been warned in {interaction.guild.name}\nReason: {reason}\nTotal warns: {total_warns}"
            )
        except:
            pass

        if total_warns >= 5:
            try:
                await member.ban(reason="Reached 5 warnings")
            except:
                pass

            warns[gid].pop(uid, None)
            await save_data()

            await interaction.response.send_message(
                f"{member.mention} reached 5 warns and was banned.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"{member.mention} warned.\nTotal warns: {total_warns}",
            ephemeral=True
        )

        if total_warns == 3:
            try:
                await member.timeout(datetime.timedelta(minutes=10))
            except:
                pass

    @app_commands.command(name="warns", description="View warnings")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def view_warns(self, interaction: discord.Interaction, member: discord.Member):

        gid = str(interaction.guild.id)
        uid = str(member.id)

        if gid not in warns or uid not in warns[gid]:
            return await interaction.response.send_message("no warnings", ephemeral=True)

        msg = ""
        for i, w in enumerate(warns[gid][uid], 1):
            msg += f"{i}. {w['reason']} ({w['timestamp']})\n"

        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="clearwarns", description="Clear warnings")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def clear_warns(self, interaction: discord.Interaction, member: discord.Member):

        gid = str(interaction.guild.id)
        uid = str(member.id)

        if gid in warns and uid in warns[gid]:
            warns[gid][uid] = []
            await save_data()
            await interaction.response.send_message("cleared", ephemeral=True)
        else:
            await interaction.response.send_message("no warns", ephemeral=True)

    @app_commands.command(name="ban", description="Ban member")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):

        if member.id == OWNER_ID:
            return await interaction.response.send_message(
                "You can't moderate the bot owner.",
                ephemeral=True
            )

        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("role too high", ephemeral=True)

        try:
            await member.send(f"Banned from {interaction.guild.name}\nReason: {reason}")
        except:
            pass

        await member.ban(reason=reason)
        await interaction.response.send_message("banned", ephemeral=True)

    @app_commands.command(name="kick", description="Kick member")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        if member.id == OWNER_ID:
            return await interaction.response.send_message(
                "You can't moderate the bot owner.",
                ephemeral=True
            )

        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("role too high", ephemeral=True)

        await member.kick(reason=reason)
        await interaction.response.send_message("kicked", ephemeral=True)

    @app_commands.command(name="mute", description="Timeout member")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, minutes: int):

        if member.id == OWNER_ID:
            return await interaction.response.send_message(
                "You can't moderate the bot owner.",
                ephemeral=True
            )

        await member.timeout(datetime.timedelta(minutes=minutes))
        await interaction.response.send_message("muted", ephemeral=True)

    @app_commands.command(name="unmute", description="Unmute member")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):

        if member.id == OWNER_ID:
            return await interaction.response.send_message(
                "You can't moderate the bot owner.",
                ephemeral=True
            )

        await member.timeout(None)
        await interaction.response.send_message("unmuted", ephemeral=True)

    @app_commands.command(name="unban", description="Unban user")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):

        user = await self.bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message("unbanned", ephemeral=True)

    @app_commands.command(name="slowmode", description="Set slowmode")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        await interaction.channel.edit(slowmode_delay=seconds)
        await interaction.response.send_message("done", ephemeral=True)

    @app_commands.command(name="purge", description="Delete messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"deleted {len(deleted)}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))