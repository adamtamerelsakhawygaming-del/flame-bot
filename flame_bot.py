import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
import os
from datetime import datetime, timedelta

# ========== CONFIG ==========
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIXES = ["flame ", "f "]
DB_FILE = "flame_bot.db"

# ========== INTENTS ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# ========== BOT SETUP ==========
bot = commands.Bot(command_prefix=PREFIXES, intents=intents, help_command=None)

# ========== DATABASE ==========
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        embers INTEGER DEFAULT 0,
        daily_streak INTEGER DEFAULT 0,
        last_daily TEXT,
        loan INTEGER DEFAULT 0,
        loan_time TEXT,
        gambling_ban_until TEXT,
        married_to INTEGER,
        will_to INTEGER,
        cult_id INTEGER,
        cult_name TEXT,
        cult_leader INTEGER,
        luck_buff_until TEXT,
        curse_debuff_until TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS creatures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        species TEXT,
        rarity TEXT,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        mood TEXT DEFAULT "neutral",
        mood_score INTEGER DEFAULT 50,
        evolved INTEGER DEFAULT 0,
        favorite INTEGER DEFAULT 0,
        custom_name TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS auctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER,
        creature_id INTEGER,
        current_bid INTEGER DEFAULT 0,
        highest_bidder INTEGER,
        end_time TEXT,
        active INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS lottery (
        user_id INTEGER PRIMARY KEY,
        tickets INTEGER DEFAULT 0,
        amount INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS pending_transfers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        amount INTEGER,
        channel_id INTEGER,
        timestamp TEXT
    )""")

    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect(DB_FILE)

def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
    conn.close()
    return row

def update_user(user_id, **kwargs):
    conn = get_db()
    c = conn.cursor()
    for key, val in kwargs.items():
        c.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (val, user_id))
    conn.commit()
    conn.close()

# ========== CREATURE DATA ==========
SPECIES = {
    "common": ["Grub", "Mossling", "Dust Bunny", "Pebbler", "Wisp"],
    "uncommon": ["Snapper", "Gloom", "Flicker", "Bramble", "Puddle"],
    "rare": ["Shade", "Glimmer", "Thorn", "Ripple", "Hollow"],
    "epic": ["Abyss", "Radiant", "Titan", "Phantom", "Sovereign"],
    "legendary": ["Eclipse", "Nova", "Abyssal King", "Celestial", "Void Walker"]
}

RARITY_WEIGHTS = {"common": 50, "uncommon": 30, "rare": 15, "epic": 4, "legendary": 1}

def get_rarity():
    rarities = list(RARITY_WEIGHTS.keys())
    weights = list(RARITY_WEIGHTS.values())
    return random.choices(rarities, weights=weights)[0]

# ========== ON READY ==========
@bot.event
async def on_ready():
    print(f"Flame Bot online as {bot.user}")
    await bot.change_presence(activity=discord.Game(name="flame help | f help"))

# ========== HELP ==========
@bot.command(aliases=["h"])
async def help(ctx, *, category=None):
    if not category:
        embed = discord.Embed(title="Flame Bot Commands", color=0xFF6B6B)
        embed.add_field(name="Economy", value="`embers daily streak beg scam invest heist loan repay burn send`", inline=False)
        embed.add_field(name="Creatures", value="`summon cage release feed neglect mood evolve breed sacrifice rename favorite trade auction bid inspect adopt kidnap`", inline=False)
        embed.add_field(name="Combat", value="`duel raid ambush defend berserk bribe flee taunt combo revive wager rank`", inline=False)
        embed.add_field(name="Gambling", value="`dice shells flip spin surge vault pick chase chamber rig`", inline=False)
        embed.add_field(name="Social", value="`marry divorce will cult betray tribute roast confess`", inline=False)
        embed.add_field(name="Utility", value="`tutorial stats server global settings cooldowns changelog`", inline=False)
        embed.add_field(name="Weird", value="`dream curse bless time weather oracle mimic glitch lore quit`", inline=False)
        embed.set_footer(text="Use flame help <category> for details | Prefix: flame or f")
        await ctx.send(embed=embed)
    else:
        cats = {
            "economy": ["embers", "daily", "streak", "beg", "scam", "invest", "heist", "loan", "repay", "burn", "send"],
            "creatures": ["summon", "cage", "release", "feed", "neglect", "mood", "evolve", "breed", "sacrifice", "rename", "favorite", "trade", "auction", "bid", "inspect", "adopt", "kidnap"],
            "combat": ["duel", "raid", "ambush", "defend", "berserk", "bribe", "flee", "taunt", "combo", "revive", "wager", "rank"],
            "gambling": ["dice", "shells", "flip", "spin", "surge", "vault", "pick", "chase", "chamber", "rig"],
            "social": ["marry", "divorce", "will", "cult", "betray", "tribute", "roast", "confess"],
            "utility": ["tutorial", "stats", "server", "global", "settings", "cooldowns", "changelog"],
            "weird": ["dream", "curse", "bless", "time", "weather", "oracle", "mimic", "glitch", "lore", "quit"]
        }
        cat = category.lower()
        if cat in cats:
            embed = discord.Embed(title=f"{cat.title()} Commands", color=0xFF6B6B)
            cmds = ", ".join([f"`{c}`" for c in cats[cat]])
            embed.description = cmds
            await ctx.send(embed=embed)
        else:
            await ctx.send("Category not found. Try: economy, creatures, combat, gambling, social, utility, weird")

# ========== ECONOMY ==========
@bot.command(aliases=["bal", "e"])
async def embers(ctx):
    user = get_user(ctx.author.id)
    embed = discord.Embed(title=f"{ctx.author.display_name}'s Embers", color=0xFFD93D)
    embed.add_field(name="Balance", value=f"{user[1]} embers", inline=False)
    if user[7] > 0:
        embed.add_field(name="Loan", value=f"{user[7]} embers owed", inline=False)
    await ctx.send(embed=embed)

@bot.command(aliases=["d"])
async def daily(ctx):
    user = get_user(ctx.author.id)
    now = datetime.now()
    last = user[3]
    streak_count = user[2]

    if last:
        last_dt = datetime.fromisoformat(last)
        diff = now - last_dt
        if diff < timedelta(hours=20):
            wait = timedelta(hours=20) - diff
            await ctx.send(f"Daily available in {wait.seconds//3600}h {(wait.seconds%3600)//60}m")
            return
        elif diff > timedelta(hours=48):
            streak_count = 0

    streak_count += 1
    base = random.randint(100, 300)
    bonus = min(streak_count * 10, 200)
    amount = base + bonus

    update_user(ctx.author.id, embers=user[1]+amount, daily_streak=streak_count, last_daily=now.isoformat())

    embed = discord.Embed(title="Daily Reward", color=0x00FF00)
    embed.add_field(name="Embers", value=f"+{amount}", inline=False)
    embed.add_field(name="Streak", value=f"{streak_count} days", inline=False)
    if streak_count >= 7:
        embed.add_field(name="Bonus", value="7+ day streak active!", inline=False)
    await ctx.send(embed=embed)

@bot.command(aliases=["str"])
async def streak(ctx):
    user = get_user(ctx.author.id)
    await ctx.send(f"{ctx.author.display_name}'s streak: {user[2]} days")

@bot.command()
async def beg(ctx):
    user = get_user(ctx.author.id)
    npcs = ["Old Merchant", "Street Urchin", "Wealthy Noble", "Suspicious Hooded Figure", "Lost Traveler"]
    npc = random.choice(npcs)

    outcomes = [
        ("gives", random.randint(10, 100), 0.4),
        ("ignores", 0, 0.3),
        ("insults", -random.randint(5, 20), 0.2),
        ("curses", -random.randint(20, 50), 0.1)
    ]

    roll = random.random()
    cum = 0
    for outcome, amount, prob in outcomes:
        cum += prob
        if roll <= cum:
            break

    if outcome == "gives":
        update_user(ctx.author.id, embers=max(0, user[1]+amount))
        await ctx.send(f"{npc} pities you and gives you {amount} embers.")
    elif outcome == "ignores":
        await ctx.send(f"{npc} walks past without a glance.")
    elif outcome == "insults":
        update_user(ctx.author.id, embers=max(0, user[1]+amount))
        await ctx.send(f"{npc} insults you and you lose {-amount} embers from shame.")
    else:
        update_user(ctx.author.id, embers=max(0, user[1]+amount))
        await ctx.send(f"{npc} curses you! You lose {-amount} embers.")

@bot.command()
async def scam(ctx):
    user = get_user(ctx.author.id)
    if random.random() < 0.6:
        gain = random.randint(50, 200)
        update_user(ctx.author.id, embers=user[1]+gain)
        await ctx.send(f"Scam successful! You swindled {gain} embers.")
    else:
        loss = random.randint(30, 100)
        update_user(ctx.author.id, embers=max(0, user[1]-loss))
        await ctx.send(f"Caught scamming! Fined {loss} embers.")

@bot.command()
async def invest(ctx, amount: int):
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("Invalid amount.")
        return

    update_user(ctx.author.id, embers=user[1]-amount)
    await ctx.send(f"Invested {amount} embers... checking market in 5 seconds...")
    await asyncio.sleep(5)

    roll = random.random()
    if roll < 0.4:
        result = int(amount * 0.5)
        update_user(ctx.author.id, embers=user[1]-amount+result)
        await ctx.send(f"Market crashed! You got back {result} embers.")
    elif roll < 0.7:
        result = int(amount * 1.5)
        update_user(ctx.author.id, embers=user[1]-amount+result)
        await ctx.send(f"Steady growth! You got back {result} embers.")
    elif roll < 0.9:
        result = amount * 2
        update_user(ctx.author.id, embers=user[1]-amount+result)
        await ctx.send(f"Moon! You got back {result} embers!")
    else:
        result = amount * 3
        update_user(ctx.author.id, embers=user[1]-amount+result)
        await ctx.send(f"Jackpot! You got back {result} embers!")

@bot.command()
async def heist(ctx):
    await ctx.send("Heist requires 3+ participants. Type `join` in 30s.")
    participants = [ctx.author.id]

    def check(m):
        return m.channel == ctx.channel and m.content.lower() == "join" and m.author.id not in participants

    try:
        for _ in range(5):
            msg = await bot.wait_for("message", timeout=30.0, check=check)
            participants.append(msg.author.id)
            await ctx.send(f"{msg.author.display_name} joined! ({len(participants)}/3)")
            if len(participants) >= 3:
                break
    except asyncio.TimeoutError:
        pass

    if len(participants) < 3:
        await ctx.send("Heist cancelled. Not enough crew.")
        return

    await ctx.send("Heist in progress...")
    await asyncio.sleep(3)

    if random.random() < 0.5:
        loot = random.randint(500, 1500) // len(participants)
        for pid in participants:
            u = get_user(pid)
            update_user(pid, embers=u[1]+loot)
        await ctx.send(f"Heist successful! Each member got {loot} embers.")
    else:
        for pid in participants:
            u = get_user(pid)
            loss = random.randint(50, 150)
            update_user(pid, embers=max(0, u[1]-loss))
        await ctx.send(f"Heist failed! Everyone lost embers to bail.")

@bot.command()
async def loan(ctx, amount: int):
    user = get_user(ctx.author.id)
    if user[7] > 0:
        await ctx.send(f"You already owe {user[7]} embers!")
        return
    if amount < 100 or amount > 5000:
        await ctx.send("Loan range: 100-5000 embers.")
        return

    update_user(ctx.author.id, embers=user[1]+amount, loan=amount, loan_time=datetime.now().isoformat())
    await ctx.send(f"Loaned {amount} embers. Interest compounds hourly. Repay with `flame repay`.")

@bot.command()
async def repay(ctx, amount: int = None):
    user = get_user(ctx.author.id)
    if user[7] <= 0:
        await ctx.send("No active loan.")
        return

    owed = user[7]
    if user[8]:
        loan_time = datetime.fromisoformat(user[8])
        hours = (datetime.now() - loan_time).seconds // 3600 + 1
        owed = int(owed * (1.05 ** hours))

    if amount is None:
        amount = owed

    if amount > user[1]:
        await ctx.send("Not enough embers.")
        return

    update_user(ctx.author.id, embers=user[1]-amount, loan=max(0, owed-amount))
    if owed - amount <= 0:
        update_user(ctx.author.id, loan=0, loan_time=None)
        await ctx.send("Loan fully repaid!")
    else:
        await ctx.send(f"Paid {amount}. Still owe {owed-amount} embers.")

@bot.command()
async def burn(ctx, amount: int):
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("Invalid amount.")
        return

    update_user(ctx.author.id, embers=user[1]-amount)
    await ctx.send(f"You burned {amount} embers into nothingness. Why?")

@bot.command()
async def send(ctx, member: discord.Member, amount: int):
    if member.id == ctx.author.id:
        await ctx.send("Can't send to yourself.")
        return
    if amount < 1:
        await ctx.send("Send at least 1 ember.")
        return

    sender = get_user(ctx.author.id)
    if sender[1] < amount:
        await ctx.send("Not enough embers.")
        return

    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO pending_transfers (sender_id, receiver_id, amount, channel_id, timestamp) VALUES (?, ?, ?, ?, ?)",
              (ctx.author.id, member.id, amount, ctx.channel.id, datetime.now().isoformat()))
    transfer_id = c.lastrowid
    conn.commit()
    conn.close()

    await ctx.send(f"{ctx.author.mention}, send {amount} embers to {member.mention}? Reply `yes` to confirm or `no` to cancel.")

    def check(m):
        return m.author.id == ctx.author.id and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

    try:
        msg = await bot.wait_for("message", timeout=60.0, check=check)
        if msg.content.lower() == "no":
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM pending_transfers WHERE id = ?", (transfer_id,))
            conn.commit()
            conn.close()
            await ctx.send("Transfer cancelled.")
            return
    except asyncio.TimeoutError:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM pending_transfers WHERE id = ?", (transfer_id,))
        conn.commit()
        conn.close()
        await ctx.send("Transfer timed out.")
        return

    sender = get_user(ctx.author.id)
    receiver = get_user(member.id)

    if sender[1] < amount:
        await ctx.send("Not enough embers anymore.")
        return

    update_user(ctx.author.id, embers=sender[1]-amount)
    update_user(member.id, embers=receiver[1]+amount)

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM pending_transfers WHERE id = ?", (transfer_id,))
    conn.commit()
    conn.close()

    await ctx.send(f"Sent {amount} embers to {member.mention}!")

# ========== CREATURES ==========
@bot.command(aliases=["hunt", "catch"])
async def summon(ctx):
    user = get_user(ctx.author.id)
    rarity = get_rarity()
    species = random.choice(SPECIES[rarity])

    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO creatures (user_id, name, species, rarity) VALUES (?, ?, ?, ?)",
              (ctx.author.id, species, species, rarity))
    conn.commit()
    creature_id = c.lastrowid
    conn.close()

    embed = discord.Embed(title="Creature Summoned!", color=0x9B59B6)
    embed.add_field(name="Species", value=species, inline=False)
    embed.add_field(name="Rarity", value=rarity.upper(), inline=False)
    embed.add_field(name="ID", value=creature_id, inline=False)
    embed.set_footer(text="Check with flame cage")
    await ctx.send(embed=embed)

@bot.command(aliases=["zoo", "inv"])
async def cage(ctx, page: int = 1):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE user_id = ? ORDER BY id", (ctx.author.id,))
    creatures = c.fetchall()
    conn.close()

    if not creatures:
        await ctx.send("Your cage is empty. Summon creatures with `flame summon`.")
        return

    per_page = 5
    total_pages = (len(creatures) + per_page - 1) // per_page
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_creatures = creatures[start:end]

    embed = discord.Embed(title=f"{ctx.author.display_name}'s Cage", color=0x9B59B6)
    for cr in page_creatures:
        name = cr[11] if cr[11] else cr[2]
        fav = " [FAV]" if cr[10] else ""
        embed.add_field(
            name=f"#{cr[0]} {name}{fav}",
            value=f"{cr[4]} | Lv.{cr[5]} | Mood: {cr[7]} | XP: {cr[6]}",
            inline=False
        )
    embed.set_footer(text=f"Page {page}/{total_pages} | {len(creatures)} creatures")
    await ctx.send(embed=embed)

@bot.command()
async def release(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    creature = c.fetchone()

    if not creature:
        await ctx.send("Creature not found.")
        conn.close()
        return

    c.execute("DELETE FROM creatures WHERE id = ?", (creature_id,))
    conn.commit()
    conn.close()

    if random.random() < 0.1:
        user = get_user(ctx.author.id)
        curse = random.randint(10, 50)
        update_user(ctx.author.id, embers=max(0, user[1]-curse))
        await ctx.send(f"Released {creature[2]}... it cursed you! Lost {curse} embers.")
    else:
        await ctx.send(f"Released {creature[2]} into the wild.")

@bot.command()
async def feed(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    creature = c.fetchone()

    if not creature:
        await ctx.send("Creature not found.")
        conn.close()
        return

    new_mood = min(100, creature[8] + random.randint(5, 15))
    mood_text = "happy" if new_mood > 70 else "content" if new_mood > 40 else "grumpy"

    c.execute("UPDATE creatures SET mood_score = ?, mood = ? WHERE id = ?", (new_mood, mood_text, creature_id))
    conn.commit()
    conn.close()

    await ctx.send(f"Fed {creature[2]}. Mood: {mood_text} ({new_mood}/100)")

@bot.command()
async def neglect(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    creature = c.fetchone()

    if not creature:
        await ctx.send("Creature not found.")
        conn.close()
        return

    new_mood = max(0, creature[8] - random.randint(10, 20))
    mood_text = "happy" if new_mood > 70 else "content" if new_mood > 40 else "grumpy" if new_mood > 20 else "feral"

    c.execute("UPDATE creatures SET mood_score = ?, mood = ? WHERE id = ?", (new_mood, mood_text, creature_id))
    conn.commit()
    conn.close()

    await ctx.send(f"Neglected {creature[2]}. Mood: {mood_text} ({new_mood}/100)")

@bot.command()
async def mood(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT mood, mood_score, name FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    row = c.fetchone()
    conn.close()

    if not row:
        await ctx.send("Creature not found.")
        return

    await ctx.send(f"{row[2]} is feeling {row[0]} ({row[1]}/100)")

@bot.command()
async def evolve(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    creature = c.fetchone()

    if not creature:
        await ctx.send("Creature not found.")
        conn.close()
        return

    if creature[11]:
        await ctx.send("Already evolved.")
        conn.close()
        return

    if creature[8] < 30 or creature[8] > 80:
        await ctx.send(f"{creature[2]} needs balanced care (mood 30-80) to evolve. Current: {creature[8]}")
        conn.close()
        return

    if creature[6] < 100:
        await ctx.send(f"{creature[2]} needs 100 XP to evolve. Current: {creature[6]}")
        conn.close()
        return

    c.execute("UPDATE creatures SET evolved = 1, level = level + 1, name = ? WHERE id = ?",
              (f"Evo {creature[2]}", creature_id))
    conn.commit()
    conn.close()

    await ctx.send(f"{creature[2]} evolved into Evo {creature[2]}! Level up!")

@bot.command()
async def breed(ctx, id1: int, id2: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (id1, ctx.author.id))
    cr1 = c.fetchone()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (id2, ctx.author.id))
    cr2 = c.fetchone()

    if not cr1 or not cr2:
        await ctx.send("One or both creatures not found.")
        conn.close()
        return

    if random.random() < 0.2:
        species = f"Abomination-{random.randint(1,999)}"
        rarity = "common"
    else:
        rarities = [cr1[4], cr2[4]]
        rarity = max(rarities, key=lambda x: list(RARITY_WEIGHTS.keys()).index(x))
        species = f"{cr1[2]}-{cr2[2]}"

    c.execute("INSERT INTO creatures (user_id, name, species, rarity) VALUES (?, ?, ?, ?)",
              (ctx.author.id, species, species, rarity))
    conn.commit()
    new_id = c.lastrowid
    conn.close()

    await ctx.send(f"Bred {cr1[2]} and {cr2[2]}... created #{new_id} {species} ({rarity})!")

@bot.command()
async def sacrifice(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    creature = c.fetchone()

    if not creature:
        await ctx.send("Creature not found.")
        conn.close()
        return

    c.execute("DELETE FROM creatures WHERE id = ?", (creature_id,))
    conn.commit()
    conn.close()

    drops = {"common": 10, "uncommon": 25, "rare": 60, "epic": 150, "legendary": 500}
    drop = drops.get(creature[4], 10)

    if random.random() < 0.3:
        drop *= 2
        msg = f"CRITICAL DROP! "
    else:
        msg = ""

    user = get_user(ctx.author.id)
    update_user(ctx.author.id, embers=user[1]+drop)

    await ctx.send(f"{msg}Sacrificed {creature[2]} for {drop} embers.")

@bot.command()
async def rename(ctx, creature_id: int, *, new_name: str):
    if len(new_name) > 20:
        await ctx.send("Name too long (20 chars max).")
        return

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE creatures SET custom_name = ? WHERE id = ? AND user_id = ?", (new_name, creature_id, ctx.author.id))
    conn.commit()
    conn.close()

    await ctx.send(f"Renamed creature #{creature_id} to {new_name}.")

@bot.command()
async def favorite(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT favorite FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    row = c.fetchone()

    if not row:
        await ctx.send("Creature not found.")
        conn.close()
        return

    new_fav = 0 if row[0] else 1
    c.execute("UPDATE creatures SET favorite = ? WHERE id = ?", (new_fav, creature_id))
    conn.commit()
    conn.close()

    await ctx.send(f"Creature #{creature_id} {'un' if not new_fav else ''}favorited.")

@bot.command()
async def trade(ctx, member: discord.Member, your_id: int, their_id: int):
    await ctx.send(f"{member.mention}, {ctx.author.display_name} wants to trade creature #{your_id} for your #{their_id}. Reply `accept` or `decline`.")

    def check(m):
        return m.author.id == member.id and m.channel == ctx.channel and m.content.lower() in ["accept", "decline"]

    try:
        msg = await bot.wait_for("message", timeout=60.0, check=check)
        if msg.content.lower() == "decline":
            await ctx.send("Trade declined.")
            return
    except asyncio.TimeoutError:
        await ctx.send("Trade timed out.")
        return

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM creatures WHERE id = ?", (your_id,))
    y = c.fetchone()
    c.execute("SELECT user_id FROM creatures WHERE id = ?", (their_id,))
    t = c.fetchone()

    if not y or y[0] != ctx.author.id or not t or t[0] != member.id:
        await ctx.send("Invalid creatures.")
        conn.close()
        return

    c.execute("UPDATE creatures SET user_id = ? WHERE id = ?", (member.id, your_id))
    c.execute("UPDATE creatures SET user_id = ? WHERE id = ?", (ctx.author.id, their_id))
    conn.commit()
    conn.close()

    await ctx.send("Trade complete!")

@bot.command()
async def auction(ctx, creature_id: int, start_bid: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    creature = c.fetchone()

    if not creature:
        await ctx.send("Creature not found.")
        conn.close()
        return

    end = (datetime.now() + timedelta(hours=1)).isoformat()
    c.execute("INSERT INTO auctions (seller_id, creature_id, current_bid, end_time) VALUES (?, ?, ?, ?)",
              (ctx.author.id, creature_id, start_bid, end))
    conn.commit()
    auction_id = c.lastrowid
    conn.close()

    await ctx.send(f"Auction #{auction_id} started for {creature[2]}! Starting bid: {start_bid} embers. Use `flame bid {auction_id} <amount>`")

@bot.command()
async def bid(ctx, auction_id: int, amount: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM auctions WHERE id = ? AND active = 1", (auction_id,))
    auction = c.fetchone()

    if not auction:
        await ctx.send("Auction not found or ended.")
        conn.close()
        return

    if amount <= auction[3]:
        await ctx.send(f"Bid must be higher than {auction[3]}.")
        conn.close()
        return

    user = get_user(ctx.author.id)
    if user[1] < amount:
        await ctx.send("Not enough embers.")
        conn.close()
        return

    if auction[5]:
        prev = get_user(auction[5])
        update_user(auction[5], embers=prev[1]+auction[3])

    update_user(ctx.author.id, embers=user[1]-amount)
    c.execute("UPDATE auctions SET current_bid = ?, highest_bidder = ? WHERE id = ?", (amount, ctx.author.id, auction_id))
    conn.commit()
    conn.close()

    await ctx.send(f"Bid {amount} embers on auction #{auction_id}!")

@bot.command()
async def inspect(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    cr = c.fetchone()
    conn.close()

    if not cr:
        await ctx.send("Creature not found.")
        return

    name = cr[11] if cr[11] else cr[2]
    embed = discord.Embed(title=f"Inspect: {name}", color=0x9B59B6)
    embed.add_field(name="Species", value=cr[3], inline=False)
    embed.add_field(name="Rarity", value=cr[4].upper(), inline=False)
    embed.add_field(name="Level", value=cr[5], inline=False)
    embed.add_field(name="XP", value=f"{cr[6]}/100", inline=False)
    embed.add_field(name="Mood", value=f"{cr[7]} ({cr[8]}/100)", inline=False)
    embed.add_field(name="Evolved", value="Yes" if cr[11] else "No", inline=False)
    embed.add_field(name="Favorite", value="Yes" if cr[10] else "No", inline=False)

    lores = {
        "Grub": "Born from decay, feeds on forgotten things.",
        "Mossling": "A patch of moss that gained consciousness.",
        "Dust Bunny": "Not actually a bunny. Just dust.",
        "Pebbler": "Collects pebbles. No one knows why.",
        "Wisp": "A fragment of someone else's dream.",
        "Snapper": "Bites first, asks questions never.",
        "Gloom": "Absorbs light. Emits sighs.",
        "Flicker": "Appears and disappears. Unreliable ally.",
        "Bramble": "Covered in thorns. Soft inside.",
        "Puddle": "Has depth you don't expect.",
        "Shade": "Lives in your peripheral vision.",
        "Glimmer": "Rarely seen. Never forgotten.",
        "Thorn": "Beautiful and painful.",
        "Ripple": "Disturbs still waters.",
        "Hollow": "Empty, but not without purpose.",
        "Abyss": "Stares back when stared at.",
        "Radiant": "Too bright to look at directly.",
        "Titan": "Ancient. Slow. Unstoppable.",
        "Phantom": "Was someone once. Maybe.",
        "Sovereign": "Demands respect. Doesn't receive it.",
        "Eclipse": "Darkness that remembers light.",
        "Nova": "Burns brightest before the end.",
        "Abyssal King": "Rules nothing. Feared anyway.",
        "Celestial": "Not from here. Doesn't understand here.",
        "Void Walker": "Walks where nothing should.",
    }
    embed.add_field(name="Lore", value=lores.get(cr[3], "Mysterious origins."), inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def adopt(ctx, member: discord.Member, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, member.id))
    cr = c.fetchone()

    if not cr:
        await ctx.send("Creature not found.")
        conn.close()
        return

    if cr[8] > 30:
        await ctx.send(f"{cr[2]} is too well cared for to be adopted.")
        conn.close()
        return

    await ctx.send(f"{member.mention}, {ctx.author.display_name} wants to adopt your neglected {cr[2]}. Reply `yes` or `no`.")

    def check(m):
        return m.author.id == member.id and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

    try:
        msg = await bot.wait_for("message", timeout=60.0, check=check)
        if msg.content.lower() == "no":
            await ctx.send("Adoption denied.")
            conn.close()
            return
    except asyncio.TimeoutError:
        await ctx.send("Adoption timed out.")
        conn.close()
        return

    c.execute("UPDATE creatures SET user_id = ? WHERE id = ?", (ctx.author.id, creature_id))
    conn.commit()
    conn.close()

    await ctx.send(f"Adopted {cr[2]}!")

@bot.command()
async def kidnap(ctx, member: discord.Member, creature_id: int):
    user = get_user(ctx.author.id)
    if user[1] < 100:
        await ctx.send("Kidnapping costs 100 embers.")
        return

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, member.id))
    cr = c.fetchone()

    if not cr:
        await ctx.send("Creature not found.")
        conn.close()
        return

    update_user(ctx.author.id, embers=user[1]-100)

    if random.random() < 0.5:
        c.execute("UPDATE creatures SET user_id = ? WHERE id = ?", (ctx.author.id, creature_id))
        conn.commit()
        conn.close()
        await ctx.send(f"Successfully kidnapped {cr[2]}! The perfect crime.")
    else:
        fine = random.randint(50, 150)
        update_user(ctx.author.id, embers=max(0, user[1]-100-fine))
        conn.close()
        await ctx.send(f"Caught kidnapping! Fined {fine} embers. {cr[2]} escaped.")

# ========== COMBAT ==========
@bot.command()
async def duel(ctx, member: discord.Member, wager: int = 0):
    if member.id == ctx.author.id:
        await ctx.send("Can't duel yourself.")
        return

    u1 = get_user(ctx.author.id)
    u2 = get_user(member.id)

    if wager > 0:
        if u1[1] < wager or u2[1] < wager:
            await ctx.send("One of you can't afford the wager.")
            return

    await ctx.send(f"{member.mention}, {ctx.author.display_name} challenges you to a duel{' for ' + str(wager) + ' embers' if wager else ''}! Reply `accept` or `decline`.")

    def check(m):
        return m.author.id == member.id and m.channel == ctx.channel and m.content.lower() in ["accept", "decline"]

    try:
        msg = await bot.wait_for("message", timeout=60.0, check=check)
        if msg.content.lower() == "decline":
            await ctx.send("Duel declined.")
            return
    except asyncio.TimeoutError:
        await ctx.send("Duel timed out.")
        return

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE user_id = ? AND favorite = 1 LIMIT 1", (ctx.author.id,))
    c1 = c.fetchone()
    c.execute("SELECT * FROM creatures WHERE user_id = ? AND favorite = 1 LIMIT 1", (member.id,))
    c2 = c.fetchone()
    conn.close()

    if not c1 or not c2:
        await ctx.send("Both need a favorited creature to duel.")
        return

    p1 = c1[5] * 10 + c1[8]
    p2 = c2[5] * 10 + c2[8]

    roll1 = random.randint(1, 100) + p1
    roll2 = random.randint(1, 100) + p2

    winner = ctx.author if roll1 > roll2 else member

    if wager > 0:
        update_user(ctx.author.id, embers=u1[1]-wager if winner.id != ctx.author.id else u1[1]+wager)
        update_user(member.id, embers=u2[1]-wager if winner.id != member.id else u2[1]+wager)

    await ctx.send(f"{c1[2]} ({roll1}) vs {c2[2]} ({roll2})... {winner.mention} wins!")

@bot.command()
async def raid(ctx):
    await ctx.send("Raid boss appears! Need 5 players. Type `join` in 30s.")
    participants = [ctx.author.id]

    def check(m):
        return m.channel == ctx.channel and m.content.lower() == "join" and m.author.id not in participants

    try:
        for _ in range(10):
            msg = await bot.wait_for("message", timeout=30.0, check=check)
            participants.append(msg.author.id)
            await ctx.send(f"{msg.author.display_name} joined! ({len(participants)}/5)")
            if len(participants) >= 5:
                break
    except asyncio.TimeoutError:
        pass

    if len(participants) < 5:
        await ctx.send("Raid cancelled. Not enough warriors.")
        return

    boss_hp = 1000
    total_dmg = 0

    for pid in participants:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT level FROM creatures WHERE user_id = ? ORDER BY level DESC LIMIT 1", (pid,))
        best = c.fetchone()
        conn.close()

        dmg = (best[0] if best else 1) * random.randint(10, 30)
        total_dmg += dmg

    await ctx.send(f"Party dealt {total_dmg} damage!")
    await asyncio.sleep(2)

    if total_dmg >= boss_hp:
        loot = random.randint(200, 500) // len(participants)
        for pid in participants:
            u = get_user(pid)
            update_user(pid, embers=u[1]+loot)
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE creatures SET xp = xp + 50 WHERE user_id = ? ORDER BY level DESC LIMIT 1", (pid,))
            conn.commit()
            conn.close()
        await ctx.send(f"Boss defeated! Everyone got {loot} embers and 50 XP.")
    else:
        await ctx.send(f"Boss survived with {boss_hp-total_dmg} HP. Raid failed.")

@bot.command()
async def ambush(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("Can't ambush yourself.")
        return

    u1 = get_user(ctx.author.id)
    u2 = get_user(member.id)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE user_id = ? ORDER BY level DESC LIMIT 1", (ctx.author.id,))
    c1 = c.fetchone()
    c.execute("SELECT * FROM creatures WHERE user_id = ? ORDER BY level DESC LIMIT 1", (member.id,))
    c2 = c.fetchone()
    conn.close()

    if not c1 or not c2:
        await ctx.send("Both need creatures.")
        return

    roll = random.randint(1, 100)
    if roll > 60:
        steal = random.randint(10, min(100, u2[1]))
        update_user(ctx.author.id, embers=u1[1]+steal)
        update_user(member.id, embers=max(0, u2[1]-steal))
        await ctx.send(f"Ambush successful! Stole {steal} embers from {member.display_name}.")
    else:
        fine = random.randint(20, 50)
        update_user(ctx.author.id, embers=max(0, u1[1]-fine))
        await ctx.send(f"Ambush failed! Lost {fine} embers fleeing.")

@bot.command()
async def defend(ctx):
    await ctx.send("Defense stance set. Next ambush against you has 50% reduced success chance. (Lasts 1 hour - simulated)")

@bot.command()
async def berserk(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("Can't berserk yourself.")
        return

    u1 = get_user(ctx.author.id)
    u2 = get_user(member.id)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE user_id = ? ORDER BY level DESC LIMIT 1", (ctx.author.id,))
    c1 = c.fetchone()
    c.execute("SELECT * FROM creatures WHERE user_id = ? ORDER BY level DESC LIMIT 1", (member.id,))
    c2 = c.fetchone()
    conn.close()

    if not c1 or not c2:
        await ctx.send("Both need creatures.")
        return

    dmg = random.randint(30, 80)
    self_dmg = random.randint(10, 30)

    await ctx.send(f"BERSERK! Dealt {dmg} damage but took {self_dmg} recoil!")

    if dmg > self_dmg + 20:
        steal = random.randint(20, 80)
        update_user(ctx.author.id, embers=u1[1]+steal)
        update_user(member.id, embers=max(0, u2[1]-steal))
        await ctx.send(f"Won the berserk clash! Stole {steal} embers.")
    else:
        await ctx.send("Berserk failed. Just hurt yourself for no reason.")

@bot.command()
async def bribe(ctx, member: discord.Member, amount: int):
    if amount < 50:
        await ctx.send("Minimum bribe: 50 embers.")
        return

    u1 = get_user(ctx.author.id)
    if u1[1] < amount:
        await ctx.send("Not enough embers.")
        return

    update_user(ctx.author.id, embers=u1[1]-amount)

    if random.random() < 0.6:
        await ctx.send(f"Bribed {member.display_name} with {amount} embers. They won't attack you for... a while.")
    else:
        await ctx.send(f"{member.display_name} took your {amount} embers and attacked anyway. Scammed.")

@bot.command()
async def flee(ctx):
    await ctx.send("You fled. Lost all pride. Gained nothing. But you're safe.")

@bot.command()
async def taunt(ctx, member: discord.Member):
    taunts = [
        f"{member.mention} fights like a confused Grub!",
        f"{member.mention}'s creatures are all 'common' for a reason.",
        f"{member.mention} probably loses to Dust Bunnies.",
        f"I've seen Mosslings with more strategy than {member.mention}."
    ]
    await ctx.send(random.choice(taunts))

@bot.command()
async def combo(ctx, member: discord.Member):
    await ctx.send(f"{member.mention}, {ctx.author.display_name} wants to combo attack with you! Reply `yes` to team up.")

    def check(m):
        return m.author.id == member.id and m.channel == ctx.channel and m.content.lower() == "yes"

    try:
        await bot.wait_for("message", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("Combo failed. No teamwork.")
        return

    dmg = random.randint(50, 150)
    loot = random.randint(30, 100)

    u1 = get_user(ctx.author.id)
    u2 = get_user(member.id)
    update_user(ctx.author.id, embers=u1[1]+loot)
    update_user(member.id, embers=u2[1]+loot)

    await ctx.send(f"Combo attack dealt {dmg} damage! Both got {loot} embers.")

@bot.command()
async def revive(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    cr = c.fetchone()
    conn.close()

    if not cr:
        await ctx.send("Creature not found.")
        return

    cost = cr[5] * 50
    user = get_user(ctx.author.id)

    if user[1] < cost:
        await ctx.send(f"Revive costs {cost} embers.")
        return

    update_user(ctx.author.id, embers=user[1]-cost)
    await ctx.send(f"Revived {cr[2]} for {cost} embers. It's back... different somehow.")

@bot.command()
async def wager(ctx, member: discord.Member, amount: int):
    if amount < 10:
        await ctx.send("Minimum wager: 10 embers.")
        return

    u1 = get_user(ctx.author.id)
    u2 = get_user(member.id)

    if u1[1] < amount or u2[1] < amount:
        await ctx.send("One of you can't afford it.")
        return

    await ctx.send(f"{member.mention}, wager {amount} embers on next duel? Reply `yes`.")

    def check(m):
        return m.author.id == member.id and m.channel == ctx.channel and m.content.lower() == "yes"

    try:
        await bot.wait_for("message", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("Wager declined.")
        return

    await ctx.send("Wager set! Use `flame duel` to settle it.")

@bot.command()
async def rank(ctx):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id, COUNT(*) as wins FROM creatures GROUP BY user_id ORDER BY wins DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()

    embed = discord.Embed(title="Combat Rankings", color=0xFF0000)
    for i, (uid, count) in enumerate(rows, 1):
        user = bot.get_user(uid)
        name = user.display_name if user else f"User {uid}"
        embed.add_field(name=f"#{i} {name}", value=f"{count} creatures", inline=False)
    await ctx.send(embed=embed)

# ========== GAMBLING ==========
def check_gambling_ban(user_id):
    user = get_user(user_id)
    if user[9]:
        ban_until = datetime.fromisoformat(user[9])
        if datetime.now() < ban_until:
            return False, (ban_until - datetime.now()).seconds
    return True, 0

@bot.command()
async def dice(ctx, amount: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send(f"Gambling banned for {remaining//60}m {remaining%60}s.")
        return

    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("Invalid amount.")
        return

    update_user(ctx.author.id, embers=user[1]-amount)

    roll1 = random.randint(1, 100)
    roll2 = random.randint(1, 100)

    await ctx.send(f"You: {roll1} | Bot: {roll2}")

    if roll1 > roll2:
        winnings = int(amount * 1.5)
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send(f"You win! Got {winnings} embers (1.5x).")
    elif roll1 == roll2:
        update_user(ctx.author.id, embers=user[1])
        await ctx.send("Draw! Embers returned.")
    else:
        await ctx.send("You lose. Embers gone.")

@bot.command()
async def shells(ctx, amount: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send(f"Gambling banned for {remaining//60}m {remaining%60}s.")
        return

    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("Invalid amount.")
        return

    update_user(ctx.author.id, embers=user[1]-amount)

    pearl = random.randint(1, 3)
    await ctx.send("Shells shuffled! Pick 1, 2, or 3.")

    def check(m):
        return m.author.id == ctx.author.id and m.channel == ctx.channel and m.content in ["1", "2", "3"]

    try:
        msg = await bot.wait_for("message", timeout=30.0, check=check)
        pick = int(msg.content)
    except asyncio.TimeoutError:
        await ctx.send("Too slow! Embers lost.")
        return

    if pick == pearl:
        winnings = amount * 2
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send(f"Pearl found! Won {winnings} embers (2x).")
    else:
        await ctx.send(f"Empty! Pearl was under shell {pearl}. Embers lost.")

@bot.command()
async def flip(ctx, amount: int, choice: str):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send(f"Gambling banned for {remaining//60}m {remaining%60}s.")
        return

    choice = choice.lower()
    if choice not in ["heads", "tails"]:
        await ctx.send("Pick heads or tails.")
        return

    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("Invalid amount.")
        return

    update_user(ctx.author.id, embers=user[1]-amount)

    result = random.choice(["heads", "tails"])
    await ctx.send(f"Coin flip... {result.upper()}!")

    if choice == result:
        winnings = amount * 2
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send(f"You win! Got {winnings} embers (2x).")
    else:
        await ctx.send("Wrong side. Embers lost.")

@bot.command()
async def spin(ctx, amount: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send(f"Gambling banned for {remaining//60}m {remaining%60}s.")
        return

    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("Invalid amount.")
        return

    update_user(ctx.author.id, embers=user[1]-amount)

    roll = random.random()
    if roll < 0.50:
        await ctx.send("Wheel: LOSE. Embers gone.")
    elif roll < 0.80:
        winnings = int(amount * 1.5)
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send(f"Wheel: 1.5x! Won {winnings} embers.")
    elif roll < 0.95:
        winnings = amount * 2
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send(f"Wheel: 2x! Won {winnings} embers.")
    elif roll < 0.99:
        winnings = amount * 3
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send(f"Wheel: 3x! Won {winnings} embers!")
    else:
        winnings = amount * 5
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send(f"Wheel: 5x JACKPOT! Won {winnings} embers!!!")

@bot.command()
async def surge(ctx, amount: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send(f"Gambling banned for {remaining//60}m {remaining%60}s.")
        return

    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("Invalid amount.")
        return

    update_user(ctx.author.id, embers=user[1]-amount)

    multiplier = 1.0
    await ctx.send("Surge started at 1.0x! Type `cash` to cash out or `hold` to keep going.")

    while True:
        await asyncio.sleep(2)
        crash = random.random() < (0.1 + (multiplier - 1.0) * 0.15)

        if crash:
            await ctx.send(f"CRASHED at {multiplier}x! Embers lost.")
            return

        multiplier += random.uniform(0.1, 0.5)
        multiplier = round(multiplier, 1)
        await ctx.send(f"Current: {multiplier}x | `cash` or `hold`?")

        def check(m):
            return m.author.id == ctx.author.id and m.channel == ctx.channel and m.content.lower() in ["cash", "hold"]

        try:
            msg = await bot.wait_for("message", timeout=15.0, check=check)
            if msg.content.lower() == "cash":
                winnings = int(amount * multiplier)
                update_user(ctx.author.id, embers=user[1]-amount+winnings)
                await ctx.send(f"Cashed out at {multiplier}x! Won {winnings} embers.")
                return
        except asyncio.TimeoutError:
            await ctx.send("Too slow! Auto-crashed.")
            return

@bot.command()
async def vault(ctx, amount: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send(f"Gambling banned for {remaining//60}m {remaining%60}s.")
        return

    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("Invalid amount.")
        return

    update_user(ctx.author.id, embers=user[1]-amount)

    code = str(random.randint(0, 999)).zfill(3)
    await ctx.send("Vault code is 3 digits (000-999). You have 3 guesses!")

    for attempt in range(3):
        def check(m):
            return m.author.id == ctx.author.id and m.channel == ctx.channel and m.content.isdigit() and len(m.content) == 3

        try:
            msg = await bot.wait_for("message", timeout=30.0, check=check)
            guess = msg.content
        except asyncio.TimeoutError:
            await ctx.send("Too slow! Vault locked.")
            return

        if guess == code:
            winnings = amount * 10
            update_user(ctx.author.id, embers=user[1]-amount+winnings)
            await ctx.send(f"VAULT CRACKED! Code was {code}. Won {winnings} embers (10x)!")
            return
        else:
            diff = sum(1 for a, b in zip(guess, code) if a == b)
            await ctx.send(f"Wrong! {diff} digits in correct position. {2-attempt} guesses left.")

    await ctx.send(f"Vault sealed. Code was {code}. Embers lost.")

@bot.command()
async def pick(ctx, amount: int, number: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send(f"Gambling banned for {remaining//60}m {remaining%60}s.")
        return

    if number < 1 or number > 10:
        await ctx.send("Pick 1-10.")
        return

    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("Invalid amount.")
        return

    update_user(ctx.author.id, embers=user[1]-amount)

    result = random.randint(1, 10)
    await ctx.send(f"Number drawn: {result}")

    if number == result:
        winnings = amount * 3
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send(f"Exact match! Won {winnings} embers (3x).")
    else:
        await ctx.send("No match. Embers lost.")

@bot.command()
async def chase(ctx, amount: int, pick: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send(f"Gambling banned for {remaining//60}m {remaining%60}s.")
        return

    if pick < 1 or pick > 4:
        await ctx.send("Pick creature 1-4.")
        return

    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("Invalid amount.")
        return

    update_user(ctx.author.id, embers=user[1]-amount)

    racers = [
        ("Swiftling", 2),
        ("Dash", 2.5),
        ("Blur", 3),
        ("Phantom", 4)
    ]

    weights = [1/r[1] for r in racers]
    winner = random.choices(racers, weights=weights)[0]
    winner_idx = racers.index(winner) + 1

    await ctx.send(f"Race results: #{winner_idx} {winner[0]} wins!")

    if pick == winner_idx:
        winnings = int(amount * winner[1])
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send(f"Your pick won! Odds {winner[1]}x. Won {winnings} embers.")
    else:
        await ctx.send("Your creature lost. Embers gone.")

@bot.command()
async def chamber(ctx, amount: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send(f"Gambling banned for {remaining//60}m {remaining%60}s.")
        return

    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("Invalid amount.")
        return

    update_user(ctx.author.id, embers=user[1]-amount)

    await ctx.send("Chamber has 6 slots. 1 is loaded. Type `spin` to pull trigger or `stop` to cash out 1.2x.")

    loaded = random.randint(1, 6)
    spins = 0

    while True:
        def check(m):
            return m.author.id == ctx.author.id and m.channel == ctx.channel and m.content.lower() in ["spin", "stop"]

        try:
            msg = await bot.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out. Embers lost.")
            return

        if msg.content.lower() == "stop":
            winnings = int(amount * 1.2)
            update_user(ctx.author.id, embers=user[1]-amount+winnings)
            await ctx.send(f"Cashed out! Won {winnings} embers (1.2x).")
            return

        spins += 1
        if spins == loaded:
            await ctx.send("BANG! Lost everything.")
            return
        else:
            await ctx.send(f"Click... {spins}/6 spins. Safe so far. `spin` or `stop`?")

@bot.command()
async def rig(ctx, amount: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send(f"Gambling banned for {remaining//60}m {remaining%60}s.")
        return

    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("Invalid amount.")
        return

    update_user(ctx.author.id, embers=user[1]-amount)

    if random.random() < 0.25:
        winnings = amount * 2
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send(f"Rig successful! Won {winnings} embers (2x).")
    else:
        ban_until = (datetime.now() + timedelta(minutes=3)).isoformat()
        update_user(ctx.author.id, gambling_ban_until=ban_until)
        await ctx.send("CAUGHT! Gambling banned for 3 minutes. Embers lost.")

# ========== SOCIAL ==========
@bot.command()
async def marry(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("Can't marry yourself.")
        return

    user = get_user(ctx.author.id)
    if user[7]:
        married = bot.get_user(user[7])
        name = married.display_name if married else "someone"
        await ctx.send(f"Already married to {name}!")
        return

    await ctx.send(f"{member.mention}, {ctx.author.display_name} proposes! Reply `yes` to marry.")

    def check(m):
        return m.author.id == member.id and m.channel == ctx.channel and m.content.lower() == "yes"

    try:
        await bot.wait_for("message", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("Proposal rejected (timed out).")
        return

    update_user(ctx.author.id, married_to=member.id)
    update_user(member.id, married_to=ctx.author.id)
    await ctx.send(f"{ctx.author.mention} and {member.mention} are now married! Shared ember pool... not really, but cute.")

@bot.command()
async def divorce(ctx):
    user = get_user(ctx.author.id)
    if not user[7]:
        await ctx.send("Not married.")
        return

    partner_id = user[7]
    update_user(ctx.author.id, married_to=None)
    update_user(partner_id, married_to=None)

    partner = bot.get_user(partner_id)
    name = partner.display_name if partner else "them"
    await ctx.send(f"Divorced {name}. Assets split. Emotional damage sustained.")

@bot.command()
async def will(ctx, member: discord.Member):
    update_user(ctx.author.id, will_to=member.id)
    await ctx.send(f"{member.mention} inherits your stuff if you... quit. Morbid but practical.")

@bot.command()
async def cult(ctx, *, name: str):
    if len(name) > 30:
        await ctx.send("Cult name too long (30 chars max).")
        return

    user = get_user(ctx.author.id)
    if user[9]:
        await ctx.send("Already in a cult. Betray it first.")
        return

    update_user(ctx.author.id, cult_id=ctx.author.id, cult_name=name, cult_leader=ctx.author.id)
    await ctx.send(f"Cult '{name}' founded! Recruit with `flame betray`... wait, use `flame cult` to check members.")

@bot.command()
async def betray(ctx):
    user = get_user(ctx.author.id)
    if not user[9]:
        await ctx.send("Not in a cult.")
        return

    if user[11] == ctx.author.id:
        await ctx.send("You can't betray your own cult. Disband it instead.")
        return

    profit = random.randint(50, 200)
    update_user(ctx.author.id, embers=user[1]+profit, cult_id=None, cult_name=None, cult_leader=None)
    await ctx.send(f"Betrayed the cult for {profit} embers. Cold.")

@bot.command()
async def tribute(ctx):
    owner = ctx.guild.owner
    if not owner:
        await ctx.send("No server owner found.")
        return

    user = get_user(ctx.author.id)
    amount = min(50, user[1])

    if amount < 1:
        await ctx.send("Too poor to tribute.")
        return

    update_user(ctx.author.id, embers=user[1]-amount)
    owner_data = get_user(owner.id)
    update_user(owner.id, embers=owner_data[1]+amount)

    await ctx.send(f"Paid {amount} embers tribute to {owner.display_name}. They probably won't notice.")

@bot.command()
async def roast(ctx, member: discord.Member):
    roasts = [
        f"{member.mention} has the personality of a loading screen.",
        f"{member.mention} is like a cloud. When they disappear, it's a beautiful day.",
        f"{member.mention}'s brain has too many tabs open and they're all 404.",
        f"{member.mention} brings everyone joy... when they leave.",
        f"{member.mention} is proof that evolution can go backwards.",
        f"{member.mention} has two brain cells and they're fighting for third place.",
        f"{member.mention} is the reason the gene pool needs a lifeguard.",
        f"{member.mention}'s WiFi signal is stronger than their personality."
    ]
    await ctx.send(random.choice(roasts))

@bot.command()
async def confess(ctx, *, confession: str):
    if len(confession) > 500:
        await ctx.send("Confession too long (500 chars max).")
        return

    await ctx.send(f"Anonymous confession: {confession}")
    await ctx.message.delete()

# ========== UTILITY ==========
@bot.command()
async def tutorial(ctx):
    steps = [
        "Welcome to Flame Bot! Here's how to start:",
        "1. `flame summon` - Get your first creature",
        "2. `flame cage` - View your creatures",
        "3. `flame daily` - Claim free embers every 20h",
        "4. `flame embers` - Check your balance",
        "5. `flame dice <amount>` - Try gambling (careful!)",
        "6. `flame duel @user` - Battle with your favorite creature",
        "7. `flame help` - See all commands",
        "Pro tip: Use `f` instead of `flame` for faster commands!"
    ]

    embed = discord.Embed(title="Flame Bot Tutorial", color=0x00FF00)
    embed.description = "\n".join(steps)
    await ctx.send(embed=embed)

@bot.command()
async def stats(ctx):
    user = get_user(ctx.author.id)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM creatures WHERE user_id = ?", (ctx.author.id,))
    creature_count = c.fetchone()[0]
    conn.close()

    embed = discord.Embed(title=f"{ctx.author.display_name}'s Stats", color=0x3498DB)
    embed.add_field(name="Embers", value=user[1], inline=True)
    embed.add_field(name="Streak", value=f"{user[2]} days", inline=True)
    embed.add_field(name="Creatures", value=creature_count, inline=True)
    embed.add_field(name="Loan", value=f"{user[7]} embers" if user[7] > 0 else "None", inline=True)
    embed.add_field(name="Married", value="Yes" if user[7] else "No", inline=True)
    embed.add_field(name="Cult", value=user[10] if user[10] else "None", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def server(ctx):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id, embers FROM users ORDER BY embers DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()

    embed = discord.Embed(title=f"{ctx.guild.name} Leaderboard", color=0xFFD93D)
    for i, (uid, embers) in enumerate(rows, 1):
        user = bot.get_user(uid)
        name = user.display_name if user else f"User {uid}"
        embed.add_field(name=f"#{i} {name}", value=f"{embers} embers", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def global_leaderboard(ctx):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id, embers FROM users ORDER BY embers DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()

    embed = discord.Embed(title="Global Leaderboard", color=0xFFD93D)
    for i, (uid, embers) in enumerate(rows, 1):
        user = bot.get_user(uid)
        name = user.display_name if user else f"User {uid}"
        embed.add_field(name=f"#{i} {name}", value=f"{embers} embers", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def settings(ctx, *, setting: str = None):
    if not setting:
        embed = discord.Embed(title="Settings", color=0x95A5A6)
        embed.add_field(name="Available", value="`notifications` - toggle DMs
`compact` - shorter messages", inline=False)
        await ctx.send(embed=embed)
        return

    await ctx.send(f"Setting '{setting}' updated. (This is a placeholder - add real settings logic)")

@bot.command()
async def cooldowns(ctx):
    user = get_user(ctx.author.id)
    now = datetime.now()

    embed = discord.Embed(title="Your Cooldowns", color=0xE74C3C)

    if user[3]:
        last_daily = datetime.fromisoformat(user[3])
        diff = now - last_daily
        if diff < timedelta(hours=20):
            wait = timedelta(hours=20) - diff
            embed.add_field(name="Daily", value=f"{wait.seconds//3600}h {(wait.seconds%3600)//60}m", inline=False)
        else:
            embed.add_field(name="Daily", value="Ready!", inline=False)
    else:
        embed.add_field(name="Daily", value="Ready!", inline=False)

    if user[9]:
        ban = datetime.fromisoformat(user[9])
        if ban > now:
            wait = ban - now
            embed.add_field(name="Gambling Ban", value=f"{wait.seconds//60}m {wait.seconds%60}s", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def changelog(ctx):
    embed = discord.Embed(title="Flame Bot Changelog", color=0x9B59B6)
    embed.add_field(name="v1.0", value="Initial release with 76 commands!", inline=False)
    embed.add_field(name="Features", value="Economy, Creatures, Combat, Gambling, Social, Utility, Weird", inline=False)
    await ctx.send(embed=embed)

# ========== WEIRD ==========
@bot.command()
async def dream(ctx):
    dreams = [
        "Your creature dreams of flying. Maybe evolve it?",
        "A shadow whispers: 'Invest today, moon tomorrow.'",
        "You see numbers: 7, 13, 42. Try them in `flame pick`.",
        "A Grub tells you: 'The vault code ends in 5.'",
        "Your creature dreams of battle. Duel someone today.",
        "You see a vision: a legendary creature awaits the patient.",
        "The oracle says: 'Risk brings reward, but not always yours.'"
    ]
    await ctx.send(f"Dream: {random.choice(dreams)}")

@bot.command()
async def curse(ctx, member: discord.Member):
    debuff_until = (datetime.now() + timedelta(hours=1)).isoformat()
    update_user(member.id, curse_debuff_until=debuff_until)
    await ctx.send(f"Cursed {member.mention}! Bad luck for 1 hour. Their gambling odds just got worse... (simulated)")

@bot.command()
async def bless(ctx, member: discord.Member):
    buff_until = (datetime.now() + timedelta(hours=1)).isoformat()
    update_user(member.id, luck_buff_until=buff_until)
    await ctx.send(f"Blessed {member.mention}! Good luck for 1 hour. May the odds be ever in their favor... (simulated)")

@bot.command()
async def time(ctx):
    now = datetime.now()
    await ctx.send(f"Server time: {now.strftime('%Y-%m-%d %H:%M:%S')}
Some commands are affected by time of day! (simulated)")

@bot.command()
async def weather(ctx):
    weathers = ["Sunny", "Rainy", "Stormy", "Foggy", "Eclipse"]
    weather = random.choice(weathers)

    effects = {
        "Sunny": "Summon rates normal.",
        "Rainy": "Uncommon creatures more likely.",
        "Stormy": "Epic creatures slightly more likely. Gambling riskier.",
        "Foggy": "Common creatures dominate. Hard to see ambushes coming.",
        "Eclipse": "Legendary creatures possible! Everything else breaks."
    }

    await ctx.send(f"Current weather: {weather}
{effects[weather]}")

@bot.command()
async def oracle(ctx, *, question: str):
    answers = [
        "The void whispers... yes.",
        "The stars align... no.",
        "A Grub chews thoughtfully... maybe.",
        "The answer is hidden in your cage.",
        "Ask again after `flame daily`.",
        "The oracle is napping. Try later.",
        "Yes, but at what cost?",
        "No, and be grateful.",
        "The creatures are divided. Flip a coin.",
        "Absolutely... not."
    ]
    await ctx.send(f"Q: {question}
A: {random.choice(answers)}")

@bot.command()
async def mimic(ctx, member: discord.Member):
    await ctx.send(f"{member.mention} Your creature mimics {member.display_name}'s last message. (This is a joke command - no actual mimicry)")

@bot.command()
async def glitch(ctx):
    glitches = [
        "01001000 01100101 01101100 01110000",
        "[REDACTED]",
        "ERROR: CREATUR_NOT_FOND",
        "Your embers are now imaginary. Just kidding.",
        "The bot is self-aware. Run.",
        "01001110 01101001 01100011 01100101",
        "Loading... 99%... stuck forever."
    ]
    await ctx.send(random.choice(glitches))

@bot.command()
async def lore(ctx):
    lores = [
        "In the beginning, there was only Ember. Then came the Grubs.",
        "The Abyssal King once ruled all cages. Now he waits.",
        "Legend says the first duel was between two Mosslings. It lasted 3 days.",
        "The Vault was built by a creature that could count to 1000. No one knows which one.",
        "Embers are crystallized time. Or maybe just shiny rocks.",
        "The Cult of the Flame was founded by a Dust Bunny with ambition.",
        "Void Walkers don't walk. They just... stop existing in one place and start in another."
    ]
    await ctx.send(f"Lore drop: {random.choice(lores)}")

@bot.command()
async def quit(ctx):
    user = get_user(ctx.author.id)
    if user[8]:
        heir = bot.get_user(user[8])
        heir_name = heir.display_name if heir else "someone"
        await ctx.send(f"Account 'deleted'. {heir_name} inherits your {user[1]} embers. (Just kidding - nothing was deleted. Use `flame will` to actually set an heir)")
    else:
        await ctx.send("You can't quit. No one can quit. The Flame consumes all. (Account still active)")

# ========== RUN ==========
bot.run(TOKEN)
