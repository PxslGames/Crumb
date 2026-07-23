import discord
from discord.ext import commands
import time
import datetime

from core import (
    OWNER_ID,
    log,
    safe_delete,
    issue_warn,
    normalize,
    NORMALIZED_BANNED,
    INVITE_REGEX,
    CRUMB_RESPONSES,
    spam_tracker,
    spam_cooldown,
    warned_cooldown,
    SPAM_WINDOW,
    SPAM_LIMIT,
    SPAM_PUNISH_COOLDOWN,
)
import random


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot or not message.guild:
                return

            if message.author.id == OWNER_ID:
                await self.bot.process_commands(message)
                return

            now = time.time()
            uid = message.author.id
            gid = message.guild.id
            key = (gid, uid)

            cooldown_end = spam_cooldown.get(key)
            if cooldown_end and now < cooldown_end:
                try:
                    await message.delete()
                except:
                    pass

                if key not in warned_cooldown:
                    warned_cooldown.add(key)
                    await message.channel.send(
                        f"⏳ {message.author.mention} you're on cooldown, slow down."
                    )

                return
            else:
                warned_cooldown.discard(key)

            timestamps = spam_tracker.setdefault(key, [])

            while timestamps and now - timestamps[0] > SPAM_WINDOW:
                timestamps.pop(0)

            if len(message.attachments) > 1:
                await safe_delete(message)

                try:
                    await message.author.send(
                        f"🚨 Your message in **{message.guild.name}** was removed because it contained **more than one attachment**.\n\n"
                        "Please send each attachment in a separate message."
                    )
                except discord.Forbidden:
                    pass

                return

            mention_count = (
                len(message.mentions)
                + len(message.role_mentions)
                + (1 if message.mention_everyone else 0)
            )

            if mention_count > 3 and not message.author.guild_permissions.manage_messages:
                await safe_delete(message)

                await issue_warn(
                    message.guild,
                    message.author,
                    f"Mass mentioning ({mention_count} mentions)"
                )

                await message.channel.send(
                    f"🚨 {message.author.mention} stop mass mentioning."
                )
                return

            timestamps.append(now)

            if len(timestamps) >= SPAM_LIMIT:
                spam_tracker[key] = []
                spam_cooldown[key] = now + SPAM_PUNISH_COOLDOWN

                await issue_warn(message.guild, message.author, "Spamming (rapid messages)")
                await message.channel.send(f"🚨 {message.author.mention} stop spamming.")

                try:
                    async for msg in message.channel.history(limit=20):
                        if msg.author.id == uid and (now - msg.created_at.timestamp()) <= SPAM_WINDOW:
                            try:
                                await msg.delete()
                            except:
                                pass
                except:
                    pass

                return

            if "crumb" in message.content.lower():
                await message.reply(random.choice(CRUMB_RESPONSES))

            if not message.author.guild_permissions.manage_messages:
                if INVITE_REGEX.search(message.content):
                    await safe_delete(message)

                    await message.channel.send(
                        f"{message.author.mention} no invite links allowed."
                    )

                    try:
                        await message.author.timeout(datetime.timedelta(minutes=10))
                    except:
                        pass

                    return

            norm = normalize(message.content)
            words = set(norm.split())
            matched = words.intersection(NORMALIZED_BANNED)

            if matched:
                await safe_delete(message)

                bad = next(iter(matched))

                await issue_warn(
                    message.guild,
                    message.author,
                    f"Used banned word: {bad}"
                )

                await message.channel.send(
                    f"🚨 {message.author.mention} watch your language."
                )
                return

            await self.bot.process_commands(message)

        except Exception:
            log.exception("on_message crashed")


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoMod(bot))