import discord
import re
import json
import logging
import time
import datetime
import asyncio
import os

BOT_VERSION = "1.2.4"

START_TIME = time.time()

DATA_FILE = "data.json"

OWNER_ID = 994116541559865416

JOIN_EMOJI = "<:join:1493694693840785598>"
LEAVE_EMOJI = "<:leave:1493694784815235153>"
BOOST_EMOJI = "<a:boost:1493695082799304764>"
NEW_EMOJI = "<a:emoji:1493702510928597073>"

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

log = logging.getLogger("crumb-bot")

# --------------------------------------------------------------------------
# Data persistence
# --------------------------------------------------------------------------

data_lock = asyncio.Lock()


def load_data():
    if not os.path.exists(DATA_FILE):
        default = {
            "token": "",
            "warns": {},
            "giveaways": {},
            "reminders": []
        }
        with open(DATA_FILE, "w") as f:
            json.dump(default, f, indent=4)
        return default

    with open(DATA_FILE, "r") as f:
        return json.load(f)


async def save_data():
    async with data_lock:
        await asyncio.to_thread(_write_data)


def _write_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def get_giveaways():
    return data.setdefault("giveaways", {})


def get_warns():
    return data.setdefault("warns", {})


data = load_data()
TOKEN = data.get("token", "")

if not TOKEN:
    raise RuntimeError("Bot token is missing in data.json")

data.setdefault("warns", {})
warns = data["warns"]

# --------------------------------------------------------------------------
# Time parsing
# --------------------------------------------------------------------------


def parse_time(t: str):
    t = t.lower()
    if t.endswith("m"):
        return int(t[:-1]) * 60
    if t.endswith("h"):
        return int(t[:-1]) * 3600
    if t.endswith("s"):
        return int(t[:-1])
    return int(t)

# --------------------------------------------------------------------------
# Banned word filtering
# --------------------------------------------------------------------------

BANNED_WORDS = [
  "nigger",
  "nigga",
  "fag",
  "faggot",
  "chink",
  "tranny",
  "niga",
  "igga",
  "niig",
  "blacky",
  "blackies",
  "pornhub.com",
  "xvideos",
  "e621.net",
  "onlyfans.com",
  "childporn",
  "rape",
  "raped",
  "raping",
  "raper",
  "rapes",
  "paki",
  "kys",
  "kill yourself",
  "commit suicide",
  "suicidal",
  "pedophile",
  "incest",
  "bestiality",
  "bdsm",
  "cp",
  "shota",
  "loli",
  "gore",
]

banned_words = BANNED_WORDS

LEET_MAP = {
    "0": "o", "1": "i", "3": "e", "4": "a",
    "5": "s", "7": "t", "@": "a", "$": "s"
}


def normalize(text: str) -> str:
    text = text.lower()
    for k, v in LEET_MAP.items():
        text = text.replace(k, v)
    text = re.sub(r'[^a-z\s]', '', text)
    text = re.sub(r'(.)\1{2,}', r'\1', text)
    return text


NORMALIZED_BANNED = [normalize(word) for word in banned_words]

INVITE_REGEX = re.compile(r"(discord\.gg|discord\.com/invite|discordapp\.com/invite)/[a-zA-Z0-9]+")

# --------------------------------------------------------------------------
# Spam tracking state (shared between automod cog instances/reloads is not
# needed, but kept module-level so it survives cog reloads)
# --------------------------------------------------------------------------

from collections import defaultdict

spam_tracker = defaultdict(list)
spam_cooldown = {}
warned_cooldown = set()
SPAM_WINDOW = 3
SPAM_LIMIT = 4
SPAM_PUNISH_COOLDOWN = 30

# --------------------------------------------------------------------------
# Guild helpers
# --------------------------------------------------------------------------


def get_member_count(guild: discord.Guild) -> int:
    return guild.member_count or len(guild.members)


def get_boost_count(guild: discord.Guild) -> int:
    return guild.premium_subscription_count or 0


def get_system_channel(guild: discord.Guild):
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        return guild.system_channel

    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            return channel
    return None

# --------------------------------------------------------------------------
# Message / moderation helpers
# --------------------------------------------------------------------------


async def safe_delete(msg):
    try:
        if msg.channel.permissions_for(msg.guild.me).manage_messages:
            await msg.delete()
    except:
        pass


async def issue_warn(guild, user, reason):
    gid_str = str(guild.id)
    uid_str = str(user.id)

    warns.setdefault(gid_str, {}).setdefault(uid_str, [])

    warn_data = {
        "reason": reason,
        "moderator": "AutoMod",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    warns[gid_str][uid_str].append(warn_data)
    total_warns = len(warns[gid_str][uid_str])

    await save_data()

    # timeout ALWAYS on warn
    try:
        await user.timeout(datetime.timedelta(minutes=10), reason=reason)
    except Exception as e:
        log.warning(f"Timeout failed: {e}")

    try:
        await user.send(
            f"You were warned in {guild.name}\n"
            f"Reason: {reason}\n"
            f"Total warns: {total_warns}"
        )
    except:
        pass

    if total_warns >= 5:
        try:
            await guild.ban(user, reason="Reached 5 warnings (auto-mod)")
        except:
            pass

        warns[gid_str].pop(uid_str, None)
        await save_data()

    return total_warns

# --------------------------------------------------------------------------
# Flavor text
# --------------------------------------------------------------------------

CRUMB_RESPONSES = [
    "what, what do you want?", "yeah?", "huh?", "you called?",
    "ai mode activated", "im here, whats up?", "you rang?",
    "crumb at your service", "yessir?"
]

PING_MESSAGES = [
    "clanker mode activated",
    "im a clanker",
    "quite literally chronically online",
    "online and managing this server",
    "how many of these messages do i need bruh",
    "dude stop adding more ping messages",
    "ow that hurts",
    "dont say 'crumb' in chat btw",
]

JOIN_MESSAGES = [
    "existed here", "has joined", "arrived", "just spawned in",
    "loaded into the server", "connected to reality", "materialised out of nowhere",
    "slid into the server", "just pulled up", "entered the chat",
    "has appeared!", "joined like a legend", "joined… suspiciously",
    "has been summoned", "phased into existence", "teleported in",
    "has logged on", "came out of hiding", "just vibed in",
    "has entered the arena", "spawned without warning", "joined the chaos",
    "has been deployed", "joined successfully (probably)",
    "is now part of the problem", "just walked in like they own the place",
    "joined and immediately got judged", "has joined… everyone act normal",
    "just dropped in", "connected (wifi permitting)", "has entered the void",
    "joined the cult", "has arrived fashionably late",
    "just appeared out of thin air", "joined the madness",
]

LEAVE_MESSAGES = [
    "left", "disappeared", "vanished", "rage quit", "faded away",
    "evaporated", "has left the building", "disconnected from reality",
    "just dipped", "went offline forever (maybe)", "escaped", "ran away",
    "has logged off", "quit while ahead", "quit while behind",
    "just vanished into the void", "has left us 😔", "despawned",
    "went poof", "has exited stage left", "backspaced themselves",
    "left without saying goodbye", "has been yeeted", "took the exit",
    "ghosted the server", "just disappeared… weird", "has left the chaos",
    "rage quit (understandable)", "is gone. reduced to atoms.",
    "just dipped out", "has departed",
]

BOOST_MESSAGES = [
    "boosted the server!", "just boosted the server 🚀",
    "gave the server more power!", "boosted like a legend",
    "just dropped a boost 💜", "made the server stronger!",
    "boosted the vibes", "just powered up the server",
    "gave us extra juice ⚡", "boosted like an absolute unit",
    "just upgraded the server", "boosted the server (W)",
    "just gave us a level up!", "boosted because they're cool like that",
    "just carried the server", "boosted the server into the future",
    "just made everything better", "boosted the chaos",
    "just pressed the boost button", "boosted. everyone clap.",
    "just flexed with a boost", "boosted the server… respect",
    "just dropped a premium boost", "boosted and didn't even hesitate",
]

EMOJI_ADD_MESSAGES = [
    "new emoji just dropped: {emoji}",
    "someone cooked this emoji: {emoji}",
    "fresh emoji alert: {emoji}",
    "we got a new emoji: {emoji}",
    "this just got added → {emoji}",
    "emoji expansion pack unlocked: {emoji}",
]

EMOJI_REMOVE_MESSAGES = [
    "rip emoji: {emoji}",
    "this emoji got deleted: {emoji}",
    "we lost an emoji... {emoji}",
    "gone but not forgotten: {emoji}",
    "emoji got yeeted: {emoji}",
    "this one didn't make it: {emoji}",
]

STICKER_ADD_MESSAGES = [
    "new sticker just dropped: {sticker}",
    "fresh sticker added: {sticker}",
    "we got a new sticker: {sticker}",
    "sticker unlocked: {sticker}",
    "this sticker just appeared → {sticker}",
]

STICKER_REMOVE_MESSAGES = [
    "rip sticker: {sticker}",
    "sticker got deleted: {sticker}",
    "we lost a sticker... {sticker}",
    "gone but not forgotten: {sticker}",
    "sticker got yeeted: {sticker}",
]