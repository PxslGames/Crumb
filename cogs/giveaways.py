import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import time

from core import get_giveaways, save_data, parse_time, log

class Giveaways(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.giveaway_loop.start()
        self.cleanup_giveaways.start()

    def cog_unload(self):
        self.giveaway_loop.cancel()
        self.cleanup_giveaways.cancel()

    @app_commands.command(name="giveaway", description="create a giveaway")
    @app_commands.checks.has_permissions(administrator=True)
    async def giveaway(self, interaction: discord.Interaction, winners: int, time_str: str, *, prize: str):

        seconds = parse_time(time_str)
        end_time = time.time() + seconds

        msg = await interaction.channel.send(
            f"🎉 **{prize}**\n"
            f"Winners: {winners}\n"
            f"Ends: <t:{int(end_time)}:R>\n"
            f"Entries: 0"
        )

        await msg.add_reaction("🎉")

        giveaways = get_giveaways()

        giveaways[str(msg.id)] = {
            "channel_id": interaction.channel.id,
            "message_id": msg.id,
            "winners": winners,
            "prize": prize,
            "end_time": end_time,
            "ended": False
        }

        await save_data()

        await interaction.response.send_message("giveaway created", ephemeral=True)

    async def update_giveaway_message(self, message_id: int, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return

        try:
            msg = await channel.fetch_message(message_id)
        except:
            return

        giveaways = get_giveaways()
        g = giveaways.get(str(message_id))
        if not g:
            return

        await msg.edit(
            content=(
                f"🎉 **{g['prize']}**\n"
                f"Winners: {g['winners']}\n"
                f"Ends: <t:{int(g['end_time'])}:R>\n"
            )
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        giveaways = get_giveaways()
        if str(payload.message_id) not in giveaways:
            return
        if str(payload.emoji) != "🎉":
            return

        await self.update_giveaway_message(payload.message_id, payload.channel_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        giveaways = get_giveaways()
        if str(payload.message_id) not in giveaways:
            return
        if str(payload.emoji) != "🎉":
            return

        await self.update_giveaway_message(payload.message_id, payload.channel_id)

    @tasks.loop(seconds=5)
    async def giveaway_loop(self):
        try:
            now = time.time()
            changed = False

            giveaways = get_giveaways()

            for msg_id in list(giveaways.keys()):
                try:
                    g = giveaways[msg_id]

                    if g.get("ended"):
                        continue

                    if now < g["end_time"]:
                        continue

                    channel = self.bot.get_channel(g["channel_id"])
                    if channel is None:
                        continue

                    try:
                        msg = await channel.fetch_message(int(msg_id))
                    except:
                        giveaways[msg_id]["ended"] = True
                        changed = True
                        continue

                    users = set()

                    for reaction in msg.reactions:
                        if str(reaction.emoji) == "🎉":
                            async for user in reaction.users():
                                if not user.bot:
                                    users.add(user.id)

                    if len(users) == 0:
                        await channel.send(f"🎉 Giveaway ended: **{g['prize']}**\nNo entries 😭")

                    else:
                        winner_count = min(g["winners"], len(users))
                        winners = random.sample(list(users), k=winner_count)

                        mentions = [f"<@{u}>" for u in winners]

                        await channel.send(
                            f"🎉 **GIVEAWAY ENDED** 🎉\n"
                            f"Prize: **{g['prize']}**\n"
                            f"Winners: {', '.join(mentions)}"
                        )

                    giveaways[msg_id]["ended"] = True
                    changed = True

                except Exception:
                    log.exception(f"Giveaway error for {msg_id}")

            if changed:
                await save_data()

        except Exception:
            log.exception("giveaway_loop crashed")

    @giveaway_loop.before_loop
    async def before_giveaway_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=300)
    async def cleanup_giveaways(self):
        try:
            giveaways = get_giveaways()

            to_delete = [k for k, v in giveaways.items() if v.get("ended")]

            for k in to_delete:
                del giveaways[k]

            if to_delete:
                await save_data()

        except Exception:
            log.exception("cleanup_giveaways crashed")

    @cleanup_giveaways.before_loop
    async def before_cleanup_giveaways(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaways(bot))