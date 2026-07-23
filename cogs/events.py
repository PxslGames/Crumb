import discord
from discord.ext import commands
import random

from core import (
    JOIN_EMOJI,
    LEAVE_EMOJI,
    BOOST_EMOJI,
    NEW_EMOJI,
    get_member_count,
    get_boost_count,
    get_system_channel,
    JOIN_MESSAGES,
    LEAVE_MESSAGES,
    BOOST_MESSAGES,
    EMOJI_ADD_MESSAGES,
    EMOJI_REMOVE_MESSAGES,
    STICKER_ADD_MESSAGES,
    STICKER_REMOVE_MESSAGES,
)

class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = get_system_channel(member.guild)
        if channel:
            count = get_member_count(member.guild)
            await channel.send(
                f"{JOIN_EMOJI} {member.mention} {random.choice(JOIN_MESSAGES)}, we now have {count} members!"
            )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel = get_system_channel(member.guild)
        if channel:
            count = get_member_count(member.guild)
            await channel.send(
                f"{LEAVE_EMOJI} {member.mention} {random.choice(LEAVE_MESSAGES)}, we now have {count} members!"
            )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not before.premium_since and after.premium_since:
            channel = get_system_channel(after.guild)
            if channel:
                boosts = get_boost_count(after.guild)

                await channel.send(
                    f"{BOOST_EMOJI} {after.mention} {random.choice(BOOST_MESSAGES)}, we now have {boosts} boosts!"
                )

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before, after):
        channel = get_system_channel(guild)
        if not channel:
            return

        before_set = {e.id: e for e in before}
        after_set = {e.id: e for e in after}

        added = [e for eid, e in after_set.items() if eid not in before_set]
        removed = [e for eid, e in before_set.items() if eid not in after_set]

        for emoji in added:
            msg = random.choice(EMOJI_ADD_MESSAGES).format(emoji=str(emoji))
            await channel.send(f"{NEW_EMOJI} {msg}")

        for emoji in removed:
            msg = random.choice(EMOJI_REMOVE_MESSAGES).format(emoji=str(emoji))
            await channel.send(f"{NEW_EMOJI} {msg}")

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild: discord.Guild, before, after):
        channel = get_system_channel(guild)
        if not channel:
            return

        before_set = {s.id: s for s in before}
        after_set = {s.id: s for s in after}

        added = [s for sid, s in after_set.items() if sid not in before_set]
        removed = [s for sid, s in before_set.items() if sid not in after_set]

        for sticker in added:
            msg = random.choice(STICKER_ADD_MESSAGES).format(sticker=sticker.name)
            try:
                await channel.send(
                    f"{NEW_EMOJI} {msg}",
                    stickers=[sticker]
                )
            except:
                await channel.send(f"{NEW_EMOJI} {msg}")

        for sticker in removed:
            msg = random.choice(STICKER_REMOVE_MESSAGES).format(sticker=sticker.name)

            if sticker.format == discord.StickerFormatType.lottie:
                await channel.send(f"{NEW_EMOJI} {msg} (animated sticker)")
            else:
                await channel.send(f"{NEW_EMOJI} {msg}\n{sticker.url}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))