import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
import os
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIXES = ["flame ", "f "]
DB_FILE = "flame_bot.db"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIXES, intents=intents, help_command=None)

COMMON = ["Grub", "Mossling", "Dust Bunny", "Pebbler", "Wisp"]
UNCOMMON = ["Snapper", "Gloom", "Flicker", "Bramble", "Puddle"]
RARE = ["Shade", "Glimmer", "Thorn", "Ripple", "Hollow"]
EPIC = ["Abyss", "Radiant", "Titan", "Phantom", "Sovereign"]
LEGENDARY = ["Eclipse", "Nova", "Abyssal King", "Celestial", "Void Walker"]

RARITY_WEIGHTS = {"common": 50, "uncommon": 30, "rare": 15, "epic": 4, "legendary": 1}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, embers INTEGER DEFAULT 0, daily_streak INTEGER DEFAULT 0, last_daily TEXT, loan INTEGER DEFAULT 0, loan_time TEXT, gambling_ban_until TEXT, married_to INTEGER, will_to INTEGER, cult_id INTEGER, cult_name TEXT, cult_leader INTEGER, luck_buff_until TEXT, curse_debuff_until TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS creatures (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, species TEXT, rarity TEXT, level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0, mood TEXT DEFAULT neutral, mood_score INTEGER DEFAULT 50, evolved INTEGER DEFAULT 0, favorite INTEGER DEFAULT 0, custom_name TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS auctions (id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id INTEGER, creature_id INTEGER, current_bid INTEGER DEFAULT 0, highest_bidder INTEGER, end_time TEXT, active INTEGER DEFAULT 1)")
    c.execute("CREATE TABLE IF NOT EXISTS lottery (user_id INTEGER PRIMARY KEY, tickets INTEGER DEFAULT 0, amount INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS pending_transfers (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, amount INTEGER, channel_id INTEGER, timestamp TEXT)")
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
        c.execute("UPDATE users SET " + key + " = ? WHERE user_id = ?", (val, user_id))
    conn.commit()
    conn.close()

def get_rarity():
    rarities = list(RARITY_WEIGHTS.keys())
    weights = list(RARITY_WEIGHTS.values())
    return random.choices(rarities, weights=weights)[0]

def get_species(rarity):
    if rarity == "common":
        return random.choice(COMMON)
    elif rarity == "uncommon":
        return random.choice(UNCOMMON)
    elif rarity == "rare":
        return random.choice(RARE)
    elif rarity == "epic":
        return random.choice(EPIC)
    else:
        return random.choice(LEGENDARY)

@bot.event
async def on_ready():
    print("flame bot online lol " + str(bot.user))
    await bot.change_presence(activity=discord.Game(name="flame help | f help"))

@bot.command(aliases=["h"])
async def help(ctx, *, category=None):
    if not category:
        embed = discord.Embed(title="Flame Bot Commands", color=0xFF6B6B)
        embed.add_field(name="Economy", value="embers daily streak beg scam invest heist loan repay burn send", inline=False)
        embed.add_field(name="Creatures", value="summon cage release feed neglect mood evolve breed sacrifice rename favorite trade auction bid inspect adopt kidnap", inline=False)
        embed.add_field(name="Combat", value="duel raid ambush defend berserk bribe flee taunt combo revive wager rank", inline=False)
        embed.add_field(name="Gambling", value="dice shells flip spin surge vault pick chase chamber rig", inline=False)
        embed.add_field(name="Social", value="marry divorce will cult betray tribute roast confess", inline=False)
        embed.add_field(name="Utility", value="tutorial stats server global settings cooldowns changelog", inline=False)
        embed.add_field(name="Weird", value="dream curse bless time weather oracle mimic glitch lore quit", inline=False)
        embed.set_footer(text="flame help <category> for more | prefix: flame or f")
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
            embed = discord.Embed(title=cat.title() + " Commands", color=0xFF6B6B)
            cmds = ", ".join(cats[cat])
            embed.description = cmds
            await ctx.send(embed=embed)
        else:
            await ctx.send("bruh thats not a category. try: economy, creatures, combat, gambling, social, utility, weird")

@bot.command(aliases=["bal", "e"])
async def embers(ctx):
    user = get_user(ctx.author.id)
    embed = discord.Embed(title=ctx.author.display_name + "'s Embers", color=0xFFD93D)
    embed.add_field(name="Balance", value=str(user[1]) + " embers", inline=False)
    if user[7] > 0:
        embed.add_field(name="Loan", value=str(user[7]) + " embers owed lmao", inline=False)
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
            await ctx.send("nah wait " + str(wait.seconds//3600) + "h " + str((wait.seconds%3600)//60) + "m buddy")
            return
        elif diff > timedelta(hours=48):
            streak_count = 0
            await ctx.send("streak reset bc u took too long lol")
    streak_count += 1
    base = random.randint(100, 300)
    bonus = min(streak_count * 10, 200)
    amount = base + bonus
    update_user(ctx.author.id, embers=user[1]+amount, daily_streak=streak_count, last_daily=now.isoformat())
    embed = discord.Embed(title="Daily Reward", color=0x00FF00)
    embed.add_field(name="Embers", value="+" + str(amount), inline=False)
    embed.add_field(name="Streak", value=str(streak_count) + " days", inline=False)
    if streak_count >= 7:
        embed.add_field(name="Bonus", value="7+ streak pog", inline=False)
    await ctx.send(embed=embed)

@bot.command(aliases=["str"])
async def streak(ctx):
    user = get_user(ctx.author.id)
    await ctx.send(ctx.author.display_name + " is at " + str(user[2]) + " days. dont break it lol")

@bot.command()
async def beg(ctx):
    user = get_user(ctx.author.id)
    npcs = ["some old dude", "a random hobo", "a rich guy", "shady guy in alley", "lost tourist"]
    npc = random.choice(npcs)
    roll = random.random()
    if roll < 0.4:
        amount = random.randint(10, 100)
        update_user(ctx.author.id, embers=user[1]+amount)
        await ctx.send(npc + " felt bad and gave u " + str(amount) + " embers. pathetic.")
    elif roll < 0.7:
        await ctx.send(npc + " ignored u completely. embarrassing.")
    elif roll < 0.9:
        amount = random.randint(5, 20)
        update_user(ctx.author.id, embers=max(0, user[1]-amount))
        await ctx.send(npc + " roasted u so hard u lost " + str(amount) + " embers from emotional damage")
    else:
        amount = random.randint(20, 50)
        update_user(ctx.author.id, embers=max(0, user[1]-amount))
        await ctx.send(npc + " put a CURSE on u!!! lost " + str(amount) + " embers. rip")

@bot.command()
async def scam(ctx):
    user = get_user(ctx.author.id)
    if random.random() < 0.6:
        gain = random.randint(50, 200)
        update_user(ctx.author.id, embers=user[1]+gain)
        await ctx.send("scam worked lol. +" + str(gain) + " embers. crime pays")
    else:
        loss = random.randint(30, 100)
        update_user(ctx.author.id, embers=max(0, user[1]-loss))
        await ctx.send("BUSTED. fined " + str(loss) + " embers. shouldve been sneakier")

@bot.command()
async def invest(ctx, amount: int):
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("u broke or what? invalid amount")
        return
    update_user(ctx.author.id, embers=user[1]-amount)
    await ctx.send("invested " + str(amount) + " embers... market doing stuff in 5s...")
    await asyncio.sleep(5)
    roll = random.random()
    if roll < 0.4:
        result = int(amount * 0.5)
        update_user(ctx.author.id, embers=user[1]-amount+result)
        await ctx.send("market CRASHED. got back " + str(result) + " embers. stonks down")
    elif roll < 0.7:
        result = int(amount * 1.5)
        update_user(ctx.author.id, embers=user[1]-amount+result)
        await ctx.send("stonks up! got back " + str(result) + " embers. nice")
    elif roll < 0.9:
        result = amount * 2
        update_user(ctx.author.id, embers=user[1]-amount+result)
        await ctx.send("MOONSHOT!!! " + str(result) + " embers back. ur a genius")
    else:
        result = amount * 3
        update_user(ctx.author.id, embers=user[1]-amount+result)
        await ctx.send("JACKPOT LMAO " + str(result) + " EMBERS. TELL NO ONE")

@bot.command()
async def heist(ctx):
    await ctx.send("HEIST TIME. need 3+ ppl. type join in 30s")
    participants = [ctx.author.id]
    def check(m):
        return m.channel == ctx.channel and m.content.lower() == "join" and m.author.id not in participants
    try:
        for _ in range(5):
            msg = await bot.wait_for("message", timeout=30.0, check=check)
            participants.append(msg.author.id)
            await ctx.send(msg.author.display_name + " joined the crew (" + str(len(participants)) + "/3)")
            if len(participants) >= 3:
                break
    except asyncio.TimeoutError:
        pass
    if len(participants) < 3:
        await ctx.send("heist cancelled. cowards.")
        return
    await ctx.send("robbing the vault...")
    await asyncio.sleep(3)
    if random.random() < 0.5:
        loot = random.randint(500, 1500) // len(participants)
        for pid in participants:
            u = get_user(pid)
            update_user(pid, embers=u[1]+loot)
        await ctx.send("WE RICH!! each got " + str(loot) + " embers. no snitching")
    else:
        for pid in participants:
            u = get_user(pid)
            loss = random.randint(50, 150)
            update_user(pid, embers=max(0, u[1]-loss))
        await ctx.send("cops showed up. everyone paid bail. -embers. sad")

@bot.command()
async def loan(ctx, amount: int):
    user = get_user(ctx.author.id)
    if user[7] > 0:
        await ctx.send("u already owe " + str(user[7]) + " embers bro. pay up first")
        return
    if amount < 100 or amount > 5000:
        await ctx.send("i lend 100-5000. nothing else")
        return
    update_user(ctx.author.id, embers=user[1]+amount, loan=amount, loan_time=datetime.now().isoformat())
    await ctx.send("heres " + str(amount) + " embers. interest is HIGH. flame repay when u got it")

@bot.command()
async def repay(ctx, amount: int = None):
    user = get_user(ctx.author.id)
    if user[7] <= 0:
        await ctx.send("u dont owe me anything. weirdo")
        return
    owed = user[7]
    if user[8]:
        loan_time = datetime.fromisoformat(user[8])
        hours = (datetime.now() - loan_time).seconds // 3600 + 1
        owed = int(owed * (1.05 ** hours))
    if amount is None:
        amount = owed
    if amount > user[1]:
        await ctx.send("broke boy cant even pay his debts lmao")
        return
    update_user(ctx.author.id, embers=user[1]-amount, loan=max(0, owed-amount))
    if owed - amount <= 0:
        update_user(ctx.author.id, loan=0, loan_time=None)
        await ctx.send("debt cleared. ur free... for now")
    else:
        await ctx.send("paid " + str(amount) + ". still owe " + str(owed-amount) + " embers. tick tock")

@bot.command()
async def burn(ctx, amount: int):
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("cant burn what u dont have")
        return
    update_user(ctx.author.id, embers=user[1]-amount)
    await ctx.send("burned " + str(amount) + " embers. literally. why would u do that")

@bot.command()
async def send(ctx, member: discord.Member, amount: int):
    if member.id == ctx.author.id:
        await ctx.send("cant send to urself dumbass")
        return
    if amount < 1:
        await ctx.send("send at least 1 ember bro")
        return
    sender = get_user(ctx.author.id)
    if sender[1] < amount:
        await ctx.send("ur too broke for this transaction")
        return
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO pending_transfers (sender_id, receiver_id, amount, channel_id, timestamp) VALUES (?, ?, ?, ?, ?)", (ctx.author.id, member.id, amount, ctx.channel.id, datetime.now().isoformat()))
    transfer_id = c.lastrowid
    conn.commit()
    conn.close()
    await ctx.send(ctx.author.mention + " wants to send " + str(amount) + " embers to " + member.mention + ". reply yes to confirm or no to cancel")
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
            await ctx.send("transfer cancelled. scaredy cat")
            return
    except asyncio.TimeoutError:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM pending_transfers WHERE id = ?", (transfer_id,))
        conn.commit()
        conn.close()
        await ctx.send("timed out. too slow lol")
        return
    sender = get_user(ctx.author.id)
    receiver = get_user(member.id)
    if sender[1] < amount:
        await ctx.send("u went broke during the transfer. awkward")
        return
    update_user(ctx.author.id, embers=sender[1]-amount)
    update_user(member.id, embers=receiver[1]+amount)
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM pending_transfers WHERE id = ?", (transfer_id,))
    conn.commit()
    conn.close()
    await ctx.send("sent " + str(amount) + " embers to " + member.mention + ". generous ig")

@bot.command(aliases=["hunt", "catch"])
async def summon(ctx):
    user = get_user(ctx.author.id)
    rarity = get_rarity()
    species = get_species(rarity)
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO creatures (user_id, name, species, rarity) VALUES (?, ?, ?, ?)", (ctx.author.id, species, species, rarity))
    conn.commit()
    creature_id = c.lastrowid
    conn.close()
    embed = discord.Embed(title="Creature Summoned!", color=0x9B59B6)
    embed.add_field(name="Species", value=species, inline=False)
    embed.add_field(name="Rarity", value=rarity.upper(), inline=False)
    embed.add_field(name="ID", value=str(creature_id), inline=False)
    embed.set_footer(text="check it with flame cage")
    await ctx.send(embed=embed)

@bot.command(aliases=["zoo", "inv"])
async def cage(ctx, page: int = 1):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE user_id = ? ORDER BY id", (ctx.author.id,))
    creatures = c.fetchall()
    conn.close()
    if not creatures:
        await ctx.send("ur cage empty bro. use flame summon")
        return
    per_page = 5
    total_pages = (len(creatures) + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    page_creatures = creatures[start:end]
    embed = discord.Embed(title=ctx.author.display_name + "'s Cage", color=0x9B59B6)
    for cr in page_creatures:
        name = cr[11] if cr[11] else cr[2]
        fav = " [FAV]" if cr[10] else ""
        embed.add_field(name="#" + str(cr[0]) + " " + name + fav, value=cr[4] + " | Lv." + str(cr[5]) + " | Mood: " + cr[7] + " | XP: " + str(cr[6]), inline=False)
    embed.set_footer(text="Page " + str(page) + "/" + str(total_pages) + " | " + str(len(creatures)) + " creatures total")
    await ctx.send(embed=embed)

@bot.command()
async def release(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    creature = c.fetchone()
    if not creature:
        await ctx.send("that creature dont exist bro")
        conn.close()
        return
    c.execute("DELETE FROM creatures WHERE id = ?", (creature_id,))
    conn.commit()
    conn.close()
    if random.random() < 0.1:
        user = get_user(ctx.author.id)
        curse = random.randint(10, 50)
        update_user(ctx.author.id, embers=max(0, user[1]-curse))
        await ctx.send("released " + creature[2] + "... it CURSED U!!! lost " + str(curse) + " embers. shouldnt have freed it")
    else:
        await ctx.send(creature[2] + " is free now. probably dead within the hour tbh")

@bot.command()
async def feed(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    creature = c.fetchone()
    if not creature:
        await ctx.send("creature not found. u hallucinating?")
        conn.close()
        return
    new_mood = min(100, creature[8] + random.randint(5, 15))
    mood_text = "happy" if new_mood > 70 else "content" if new_mood > 40 else "grumpy"
    c.execute("UPDATE creatures SET mood_score = ?, mood = ? WHERE id = ?", (new_mood, mood_text, creature_id))
    conn.commit()
    conn.close()
    await ctx.send("fed " + creature[2] + ". mood: " + mood_text + " (" + str(new_mood) + "/100). still ugly tho")

@bot.command()
async def neglect(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    creature = c.fetchone()
    if not creature:
        await ctx.send("cant neglect what u dont have")
        conn.close()
        return
    new_mood = max(0, creature[8] - random.randint(10, 20))
    mood_text = "happy" if new_mood > 70 else "content" if new_mood > 40 else "grumpy" if new_mood > 20 else "feral"
    c.execute("UPDATE creatures SET mood_score = ?, mood = ? WHERE id = ?", (new_mood, mood_text, creature_id))
    conn.commit()
    conn.close()
    await ctx.send("neglected " + creature[2] + ". mood: " + mood_text + " (" + str(new_mood) + "/100). ur a terrible parent")

@bot.command()
async def mood(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT mood, mood_score, name FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    row = c.fetchone()
    conn.close()
    if not row:
        await ctx.send("that creature aint urs")
        return
    await ctx.send(row[2] + " is feeling " + row[0] + " (" + str(row[1]) + "/100). probably bc of u")

@bot.command()
async def evolve(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    creature = c.fetchone()
    if not creature:
        await ctx.send("no creature found. skill issue")
        conn.close()
        return
    if creature[11]:
        await ctx.send("already evolved. cant evolve twice dummy")
        conn.close()
        return
    if creature[8] < 30 or creature[8] > 80:
        await ctx.send(creature[2] + " needs balanced care (mood 30-80) to evolve. current: " + str(creature[8]) + ". u messed up the balance")
        conn.close()
        return
    if creature[6] < 100:
        await ctx.send(creature[2] + " needs 100 XP. only has " + str(creature[6]) + ". go battle or something")
        conn.close()
        return
    c.execute("UPDATE creatures SET evolved = 1, level = level + 1, name = ? WHERE id = ?", ("Evo " + creature[2], creature_id))
    conn.commit()
    conn.close()
    await ctx.send(creature[2] + " EVOLVED into Evo " + creature[2] + "!!! LEVEL UP!!!")

@bot.command()
async def breed(ctx, id1: int, id2: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (id1, ctx.author.id))
    cr1 = c.fetchone()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (id2, ctx.author.id))
    cr2 = c.fetchone()
    if not cr1 or not cr2:
        await ctx.send("one or both creatures missing. check ur cage")
        conn.close()
        return
    if random.random() < 0.2:
        species = "Abomination-" + str(random.randint(1,999))
        rarity = "common"
    else:
        rarities = [cr1[4], cr2[4]]
        rarity = max(rarities, key=lambda x: list(RARITY_WEIGHTS.keys()).index(x))
        species = cr1[2] + "-" + cr2[2]
    c.execute("INSERT INTO creatures (user_id, name, species, rarity) VALUES (?, ?, ?, ?)", (ctx.author.id, species, species, rarity))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    await ctx.send("bred " + cr1[2] + " and " + cr2[2] + "... made #" + str(new_id) + " " + species + " (" + rarity + "). what have u done")

@bot.command()
async def sacrifice(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    creature = c.fetchone()
    if not creature:
        await ctx.send("cant sacrifice air bro")
        conn.close()
        return
    c.execute("DELETE FROM creatures WHERE id = ?", (creature_id,))
    conn.commit()
    conn.close()
    drops = {"common": 10, "uncommon": 25, "rare": 60, "epic": 150, "legendary": 500}
    drop = drops.get(creature[4], 10)
    if random.random() < 0.3:
        drop *= 2
        msg = "CRIT DROP!!! "
    else:
        msg = ""
    user = get_user(ctx.author.id)
    update_user(ctx.author.id, embers=user[1]+drop)
    await ctx.send(msg + "sacrificed " + creature[2] + " for " + str(drop) + " embers. dark stuff man")

@bot.command()
async def rename(ctx, creature_id: int, *, new_name: str):
    if len(new_name) > 20:
        await ctx.send("name too long. 20 chars max. keep it short")
        return
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE creatures SET custom_name = ? WHERE id = ? AND user_id = ?", (new_name, creature_id, ctx.author.id))
    conn.commit()
    conn.close()
    await ctx.send("renamed creature #" + str(creature_id) + " to " + new_name + ". cute")

@bot.command()
async def favorite(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT favorite FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    row = c.fetchone()
    if not row:
        await ctx.send("that creature aint real")
        conn.close()
        return
    new_fav = 0 if row[0] else 1
    c.execute("UPDATE creatures SET favorite = ? WHERE id = ?", (new_fav, creature_id))
    conn.commit()
    conn.close()
    await ctx.send("creature #" + str(creature_id) + " " + ("un" if not new_fav else "") + "favorited. playing favorites i see")

@bot.command()
async def trade(ctx, member: discord.Member, your_id: int, their_id: int):
    await ctx.send(member.mention + ", " + ctx.author.display_name + " wants to trade creature #" + str(your_id) + " for ur #" + str(their_id) + ". reply accept or decline")
    def check(m):
        return m.author.id == member.id and m.channel == ctx.channel and m.content.lower() in ["accept", "decline"]
    try:
        msg = await bot.wait_for("message", timeout=60.0, check=check)
        if msg.content.lower() == "decline":
            await ctx.send("trade declined. trust issues much?")
            return
    except asyncio.TimeoutError:
        await ctx.send("trade timed out. ghosted lmao")
        return
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM creatures WHERE id = ?", (your_id,))
    y = c.fetchone()
    c.execute("SELECT user_id FROM creatures WHERE id = ?", (their_id,))
    t = c.fetchone()
    if not y or y[0] != ctx.author.id or not t or t[0] != member.id:
        await ctx.send("invalid creatures. someone tryna scam")
        conn.close()
        return
    c.execute("UPDATE creatures SET user_id = ? WHERE id = ?", (member.id, your_id))
    c.execute("UPDATE creatures SET user_id = ? WHERE id = ?", (ctx.author.id, their_id))
    conn.commit()
    conn.close()
    await ctx.send("trade done. no refunds")

@bot.command()
async def auction(ctx, creature_id: int, start_bid: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    creature = c.fetchone()
    if not creature:
        await ctx.send("cant sell what u dont own")
        conn.close()
        return
    end = (datetime.now() + timedelta(hours=1)).isoformat()
    c.execute("INSERT INTO auctions (seller_id, creature_id, current_bid, end_time) VALUES (?, ?, ?, ?)", (ctx.author.id, creature_id, start_bid, end))
    conn.commit()
    auction_id = c.lastrowid
    conn.close()
    await ctx.send("auction #" + str(auction_id) + " started for " + creature[2] + "! starting bid: " + str(start_bid) + " embers. use flame bid " + str(auction_id) + " amount")

@bot.command()
async def bid(ctx, auction_id: int, amount: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM auctions WHERE id = ? AND active = 1", (auction_id,))
    auction = c.fetchone()
    if not auction:
        await ctx.send("auction dead or fake")
        conn.close()
        return
    if amount <= auction[3]:
        await ctx.send("bid higher than " + str(auction[3]) + " cheapskate")
        conn.close()
        return
    user = get_user(ctx.author.id)
    if user[1] < amount:
        await ctx.send("too broke to bid")
        conn.close()
        return
    if auction[5]:
        prev = get_user(auction[5])
        update_user(auction[5], embers=prev[1]+auction[3])
    update_user(ctx.author.id, embers=user[1]-amount)
    c.execute("UPDATE auctions SET current_bid = ?, highest_bidder = ? WHERE id = ?", (amount, ctx.author.id, auction_id))
    conn.commit()
    conn.close()
    await ctx.send("bid " + str(amount) + " embers on auction #" + str(auction_id) + ". big spender")

@bot.command()
async def inspect(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    cr = c.fetchone()
    conn.close()
    if not cr:
        await ctx.send("inspect what? thin air?")
        return
    name = cr[11] if cr[11] else cr[2]
    embed = discord.Embed(title="Inspect: " + name, color=0x9B59B6)
    embed.add_field(name="Species", value=cr[3], inline=False)
    embed.add_field(name="Rarity", value=cr[4].upper(), inline=False)
    embed.add_field(name="Level", value=str(cr[5]), inline=False)
    embed.add_field(name="XP", value=str(cr[6]) + "/100", inline=False)
    embed.add_field(name="Mood", value=cr[7] + " (" + str(cr[8]) + "/100)", inline=False)
    embed.add_field(name="Evolved", value="Yes" if cr[11] else "No", inline=False)
    embed.add_field(name="Favorite", value="Yes" if cr[10] else "No", inline=False)
    lores = {"Grub": "Born from decay, feeds on forgotten things.", "Mossling": "A patch of moss that gained consciousness.", "Dust Bunny": "Not actually a bunny. Just dust.", "Pebbler": "Collects pebbles. No one knows why.", "Wisp": "A fragment of someone elses dream.", "Snapper": "Bites first, asks questions never.", "Gloom": "Absorbs light. Emits sighs.", "Flicker": "Appears and disappears. Unreliable ally.", "Bramble": "Covered in thorns. Soft inside.", "Puddle": "Has depth you dont expect.", "Shade": "Lives in your peripheral vision.", "Glimmer": "Rarely seen. Never forgotten.", "Thorn": "Beautiful and painful.", "Ripple": "Disturbs still waters.", "Hollow": "Empty, but not without purpose.", "Abyss": "Stares back when stared at.", "Radiant": "Too bright to look at directly.", "Titan": "Ancient. Slow. Unstoppable.", "Phantom": "Was someone once. Maybe.", "Sovereign": "Demands respect. Doesnt receive it.", "Eclipse": "Darkness that remembers light.", "Nova": "Burns brightest before the end.", "Abyssal King": "Rules nothing. Feared anyway.", "Celestial": "Not from here. Doesnt understand here.", "Void Walker": "Walks where nothing should."}
    embed.add_field(name="Lore", value=lores.get(cr[3], "Mysterious origins."), inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def adopt(ctx, member: discord.Member, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, member.id))
    cr = c.fetchone()
    if not cr:
        await ctx.send("creature dont exist")
        conn.close()
        return
    if cr[8] > 30:
        await ctx.send(cr[2] + " is too happy to be adopted. neglect it first lol")
        conn.close()
        return
    await ctx.send(member.mention + ", " + ctx.author.display_name + " wants to adopt ur neglected " + cr[2] + ". reply yes or no")
    def check(m):
        return m.author.id == member.id and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]
    try:
        msg = await bot.wait_for("message", timeout=60.0, check=check)
        if msg.content.lower() == "no":
            await ctx.send("adoption denied. keep ur neglected pet i guess")
            conn.close()
            return
    except asyncio.TimeoutError:
        await ctx.send("adoption timed out. guess they dont care about the creature either")
        conn.close()
        return
    c.execute("UPDATE creatures SET user_id = ? WHERE id = ?", (ctx.author.id, creature_id))
    conn.commit()
    conn.close()
    await ctx.send("adopted " + cr[2] + "! give it a better life pls")

@bot.command()
async def kidnap(ctx, member: discord.Member, creature_id: int):
    user = get_user(ctx.author.id)
    if user[1] < 100:
        await ctx.send("kidnapping costs 100 embers. crime aint free")
        return
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, member.id))
    cr = c.fetchone()
    if not cr:
        await ctx.send("cant kidnap air")
        conn.close()
        return
    update_user(ctx.author.id, embers=user[1]-100)
    if random.random() < 0.5:
        c.execute("UPDATE creatures SET user_id = ? WHERE id = ?", (ctx.author.id, creature_id))
        conn.commit()
        conn.close()
        await ctx.send("YOINKED " + cr[2] + "! the perfect crime. no witnesses")
    else:
        fine = random.randint(50, 150)
        update_user(ctx.author.id, embers=max(0, user[1]-100-fine))
        conn.close()
        await ctx.send("BUSTED kidnapping! paid " + str(fine) + " embers bail. " + cr[2] + " escaped. skill issue")

@bot.command()
async def duel(ctx, member: discord.Member, wager: int = 0):
    if member.id == ctx.author.id:
        await ctx.send("cant duel urself. touch grass")
        return
    u1 = get_user(ctx.author.id)
    u2 = get_user(member.id)
    if wager > 0:
        if u1[1] < wager or u2[1] < wager:
            await ctx.send("one of yall too broke for this wager")
            return
    await ctx.send(member.mention + ", " + ctx.author.display_name + " wants to duel" + (" for " + str(wager) + " embers" if wager else "") + "! reply accept or decline")
    def check(m):
        return m.author.id == member.id and m.channel == ctx.channel and m.content.lower() in ["accept", "decline"]
    try:
        msg = await bot.wait_for("message", timeout=60.0, check=check)
        if msg.content.lower() == "decline":
            await ctx.send("duel declined. scared")
            return
    except asyncio.TimeoutError:
        await ctx.send("duel timed out. coward")
        return
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE user_id = ? AND favorite = 1 LIMIT 1", (ctx.author.id,))
    c1 = c.fetchone()
    c.execute("SELECT * FROM creatures WHERE user_id = ? AND favorite = 1 LIMIT 1", (member.id,))
    c2 = c.fetchone()
    conn.close()
    if not c1 or not c2:
        await ctx.send("both need a favorited creature. use flame favorite")
        return
    p1 = c1[5] * 10 + c1[8]
    p2 = c2[5] * 10 + c2[8]
    roll1 = random.randint(1, 100) + p1
    roll2 = random.randint(1, 100) + p2
    winner = ctx.author if roll1 > roll2 else member
    if wager > 0:
        update_user(ctx.author.id, embers=u1[1]-wager if winner.id != ctx.author.id else u1[1]+wager)
        update_user(member.id, embers=u2[1]-wager if winner.id != member.id else u2[1]+wager)
    await ctx.send(c1[2] + " (" + str(roll1) + ") vs " + c2[2] + " (" + str(roll2) + ")... " + winner.mention + " WINS!!!")

@bot.command()
async def raid(ctx):
    await ctx.send("RAID BOSS APPEARS! need 5 warriors. type join in 30s")
    participants = [ctx.author.id]
    def check(m):
        return m.channel == ctx.channel and m.content.lower() == "join" and m.author.id not in participants
    try:
        for _ in range(10):
            msg = await bot.wait_for("message", timeout=30.0, check=check)
            participants.append(msg.author.id)
            await ctx.send(msg.author.display_name + " joined! (" + str(len(participants)) + "/5)")
            if len(participants) >= 5:
                break
    except asyncio.TimeoutError:
        pass
    if len(participants) < 5:
        await ctx.send("raid cancelled. not enough heroes. boss wins by default")
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
    await ctx.send("party dealt " + str(total_dmg) + " damage!")
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
        await ctx.send("BOSS DEAD! everyone got " + str(loot) + " embers and 50 XP. GG")
    else:
        await ctx.send("boss survived with " + str(boss_hp-total_dmg) + " HP. yall weak. raid failed")

@bot.command()
async def ambush(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("cant ambush urself. thats just self harm")
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
        await ctx.send("both need creatures. go summon some")
        return
    roll = random.randint(1, 100)
    if roll > 60:
        steal = random.randint(10, min(100, u2[1]))
        update_user(ctx.author.id, embers=u1[1]+steal)
        update_user(member.id, embers=max(0, u2[1]-steal))
        await ctx.send("AMBUSH SUCCESS! stole " + str(steal) + " embers from " + member.display_name + ". sneaky")
    else:
        fine = random.randint(20, 50)
        update_user(ctx.author.id, embers=max(0, u1[1]-fine))
        await ctx.send("ambush FAILED! lost " + str(fine) + " embers running away. clown behavior")

@bot.command()
async def defend(ctx):
    await ctx.send("defense stance active. next ambush has reduced success. u paranoid or what")

@bot.command()
async def berserk(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("cant berserk urself. thats just screaming")
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
        await ctx.send("both need creatures. basic requirement")
        return
    dmg = random.randint(30, 80)
    self_dmg = random.randint(10, 30)
    await ctx.send("BERSERK MODE! dealt " + str(dmg) + " but took " + str(self_dmg) + " recoil. worth it?")
    if dmg > self_dmg + 20:
        steal = random.randint(20, 80)
        update_user(ctx.author.id, embers=u1[1]+steal)
        update_user(member.id, embers=max(0, u2[1]-steal))
        await ctx.send("won the berserk clash! stole " + str(steal) + " embers. violence works")
    else:
        await ctx.send("berserk failed. just hurt urself for no reason. embarrassing")

@bot.command()
async def bribe(ctx, member: discord.Member, amount: int):
    if amount < 50:
        await ctx.send("minimum bribe is 50 embers. im not cheap")
        return
    u1 = get_user(ctx.author.id)
    if u1[1] < amount:
        await ctx.send("too broke to bribe. sad")
        return
    update_user(ctx.author.id, embers=u1[1]-amount)
    if random.random() < 0.6:
        await ctx.send("bribed " + member.display_name + " with " + str(amount) + " embers. they wont attack... probably")
    else:
        await ctx.send(member.display_name + " took ur " + str(amount) + " embers and attacked anyway. SCAMMED")

@bot.command()
async def flee(ctx):
    await ctx.send("u fled. lost all dignity. gained nothing. but hey ur safe i guess")

@bot.command()
async def taunt(ctx, member: discord.Member):
    taunts = [member.mention + " fights like a confused Grub!", member.mention + " creatures are all common for a reason", member.mention + " probably loses to Dust Bunnies", "ive seen Mosslings with more strategy than " + member.mention]
    await ctx.send(random.choice(taunts))

@bot.command()
async def combo(ctx, member: discord.Member):
    await ctx.send(member.mention + ", " + ctx.author.display_name + " wants to combo attack! reply yes to team up")
    def check(m):
        return m.author.id == member.id and m.channel == ctx.channel and m.content.lower() == "yes"
    try:
        await bot.wait_for("message", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("combo failed. no teamwork. ever")
        return
    dmg = random.randint(50, 150)
    loot = random.randint(30, 100)
    u1 = get_user(ctx.author.id)
    u2 = get_user(member.id)
    update_user(ctx.author.id, embers=u1[1]+loot)
    update_user(member.id, embers=u2[1]+loot)
    await ctx.send("combo attack dealt " + str(dmg) + " damage! both got " + str(loot) + " embers. friendship wins")

@bot.command()
async def revive(ctx, creature_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM creatures WHERE id = ? AND user_id = ?", (creature_id, ctx.author.id))
    cr = c.fetchone()
    conn.close()
    if not cr:
        await ctx.send("cant revive what doesnt exist")
        return
    cost = cr[5] * 50
    user = get_user(ctx.author.id)
    if user[1] < cost:
        await ctx.send("revive costs " + str(cost) + " embers. start saving")
        return
    update_user(ctx.author.id, embers=user[1]-cost)
    await ctx.send("revived " + cr[2] + " for " + str(cost) + " embers. its back... different somehow")

@bot.command()
async def wager(ctx, member: discord.Member, amount: int):
    if amount < 10:
        await ctx.send("minimum wager 10 embers. go big or go home")
        return
    u1 = get_user(ctx.author.id)
    u2 = get_user(member.id)
    if u1[1] < amount or u2[1] < amount:
        await ctx.send("one of yall cant afford it. check ur balance")
        return
    await ctx.send(member.mention + ", wager " + str(amount) + " embers on next duel? reply yes")
    def check(m):
        return m.author.id == member.id and m.channel == ctx.channel and m.content.lower() == "yes"
    try:
        await bot.wait_for("message", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("wager declined. no balls")
        return
    await ctx.send("wager set! use flame duel to settle it. high stakes")

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
        name = user.display_name if user else "User " + str(uid)
        embed.add_field(name="#" + str(i) + " " + name, value=str(count) + " creatures", inline=False)
    await ctx.send(embed=embed)

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
        await ctx.send("gambling banned for " + str(remaining//60) + "m " + str(remaining%60) + "s. skill issue")
        return
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("invalid bet. u new?")
        return
    update_user(ctx.author.id, embers=user[1]-amount)
    roll1 = random.randint(1, 100)
    roll2 = random.randint(1, 100)
    await ctx.send("you: " + str(roll1) + " | bot: " + str(roll2))
    if roll1 > roll2:
        winnings = int(amount * 1.5)
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send("YOU WIN! got " + str(winnings) + " embers (1.5x). house always loses... eventually")
    elif roll1 == roll2:
        update_user(ctx.author.id, embers=user[1])
        await ctx.send("draw. embers back. boring")
    else:
        await ctx.send("you lose. embers gone. house wins again")

@bot.command()
async def shells(ctx, amount: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send("gambling banned for " + str(remaining//60) + "m " + str(remaining%60) + "s. rip")
        return
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("bad bet")
        return
    update_user(ctx.author.id, embers=user[1]-amount)
    pearl = random.randint(1, 3)
    await ctx.send("shells shuffled! pick 1, 2, or 3")
    def check(m):
        return m.author.id == ctx.author.id and m.channel == ctx.channel and m.content in ["1", "2", "3"]
    try:
        msg = await bot.wait_for("message", timeout=30.0, check=check)
        pick = int(msg.content)
    except asyncio.TimeoutError:
        await ctx.send("too slow! embers lost. git gud")
        return
    if pick == pearl:
        winnings = amount * 2
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send("PEARL FOUND! won " + str(winnings) + " embers (2x). lucky")
    else:
        await ctx.send("empty! pearl was under shell " + str(pearl) + ". embers lost. unlucky")

@bot.command()
async def flip(ctx, amount: int, choice: str):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send("gambling banned for " + str(remaining//60) + "m " + str(remaining%60) + "s. lol")
        return
    choice = choice.lower()
    if choice not in ["heads", "tails"]:
        await ctx.send("pick heads or tails. not hard")
        return
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("bad amount")
        return
    update_user(ctx.author.id, embers=user[1]-amount)
    result = random.choice(["heads", "tails"])
    await ctx.send("coin flip... " + result.upper() + "!")
    if choice == result:
        winnings = amount * 2
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send("you win! got " + str(winnings) + " embers (2x). ez")
    else:
        await ctx.send("wrong side. embers lost. 50/50 and u chose wrong")

@bot.command()
async def spin(ctx, amount: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send("gambling banned for " + str(remaining//60) + "m " + str(remaining%60) + "s. bruh")
        return
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("invalid")
        return
    update_user(ctx.author.id, embers=user[1]-amount)
    roll = random.random()
    if roll < 0.50:
        await ctx.send("wheel: LOSE. embers gone. 50% chance and u hit it. unlucky")
    elif roll < 0.80:
        winnings = int(amount * 1.5)
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send("wheel: 1.5x! won " + str(winnings) + " embers. decent")
    elif roll < 0.95:
        winnings = amount * 2
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send("wheel: 2x! won " + str(winnings) + " embers. nice")
    elif roll < 0.99:
        winnings = amount * 3
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send("wheel: 3x! won " + str(winnings) + " embers! pog")
    else:
        winnings = amount * 5
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send("wheel: 5x JACKPOT!!! won " + str(winnings) + " embers!!! INSANE")

@bot.command()
async def surge(ctx, amount: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send("gambling banned for " + str(remaining//60) + "m " + str(remaining%60) + "s. yikes")
        return
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("nah")
        return
    update_user(ctx.author.id, embers=user[1]-amount)
    multiplier = 1.0
    await ctx.send("surge started at 1.0x! type cash to cash out or hold to keep going")
    while True:
        await asyncio.sleep(2)
        crash = random.random() < (0.1 + (multiplier - 1.0) * 0.15)
        if crash:
            await ctx.send("CRASHED at " + str(multiplier) + "x! embers lost. shouldve cashed out")
            return
        multiplier += random.uniform(0.1, 0.5)
        multiplier = round(multiplier, 1)
        await ctx.send("current: " + str(multiplier) + "x | cash or hold?")
        def check(m):
            return m.author.id == ctx.author.id and m.channel == ctx.channel and m.content.lower() in ["cash", "hold"]
        try:
            msg = await bot.wait_for("message", timeout=15.0, check=check)
            if msg.content.lower() == "cash":
                winnings = int(amount * multiplier)
                update_user(ctx.author.id, embers=user[1]-amount+winnings)
                await ctx.send("cashed out at " + str(multiplier) + "x! won " + str(winnings) + " embers. smart")
                return
        except asyncio.TimeoutError:
            await ctx.send("too slow! auto-crashed. greed kills")
            return

@bot.command()
async def vault(ctx, amount: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send("gambling banned for " + str(remaining//60) + "m " + str(remaining%60) + "s. oof")
        return
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("bad bet")
        return
    update_user(ctx.author.id, embers=user[1]-amount)
    code = str(random.randint(0, 999)).zfill(3)
    await ctx.send("vault code is 3 digits (000-999). 3 guesses!")
    for attempt in range(3):
        def check(m):
            return m.author.id == ctx.author.id and m.channel == ctx.channel and m.content.isdigit() and len(m.content) == 3
        try:
            msg = await bot.wait_for("message", timeout=30.0, check=check)
            guess = msg.content
        except asyncio.TimeoutError:
            await ctx.send("too slow! vault locked. embers gone")
            return
        if guess == code:
            winnings = amount * 10
            update_user(ctx.author.id, embers=user[1]-amount+winnings)
            await ctx.send("VAULT CRACKED! code was " + code + ". won " + str(winnings) + " embers (10x)! HACKER")
            return
        else:
            diff = sum(1 for a, b in zip(guess, code) if a == b)
            await ctx.send("wrong! " + str(diff) + " digits correct. " + str(2-attempt) + " guesses left")
    await ctx.send("vault sealed. code was " + code + ". embers lost. better luck next time")

@bot.command()
async def pick(ctx, amount: int, number: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send("gambling banned for " + str(remaining//60) + "m " + str(remaining%60) + "s. L")
        return
    if number < 1 or number > 10:
        await ctx.send("pick 1-10. its not hard")
        return
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("bad amount")
        return
    update_user(ctx.author.id, embers=user[1]-amount)
    result = random.randint(1, 10)
    await ctx.send("number drawn: " + str(result))
    if number == result:
        winnings = amount * 3
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send("EXACT MATCH! won " + str(winnings) + " embers (3x). 10% chance and u hit it")
    else:
        await ctx.send("no match. embers lost. 90% chance to lose and u did")

@bot.command()
async def chase(ctx, amount: int, pick: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send("gambling banned for " + str(remaining//60) + "m " + str(remaining%60) + "s. F")
        return
    if pick < 1 or pick > 4:
        await ctx.send("pick creature 1-4. simple")
        return
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("invalid")
        return
    update_user(ctx.author.id, embers=user[1]-amount)
    racers = [("Swiftling", 2), ("Dash", 2.5), ("Blur", 3), ("Phantom", 4)]
    weights = [1/r[1] for r in racers]
    winner = random.choices(racers, weights=weights)[0]
    winner_idx = racers.index(winner) + 1
    await ctx.send("race results: #" + str(winner_idx) + " " + winner[0] + " wins!")
    if pick == winner_idx:
        winnings = int(amount * winner[1])
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send("your pick won! odds " + str(winner[1]) + "x. won " + str(winnings) + " embers. clairvoyant")
    else:
        await ctx.send("your creature lost. embers gone. shouldve picked #" + str(winner_idx))

@bot.command()
async def chamber(ctx, amount: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send("gambling banned for " + str(remaining//60) + "m " + str(remaining%60) + "s. rip bozo")
        return
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("nah")
        return
    update_user(ctx.author.id, embers=user[1]-amount)
    await ctx.send("chamber has 6 slots. 1 bullet. type spin to pull trigger or stop to cash out 1.2x")
    loaded = random.randint(1, 6)
    spins = 0
    while True:
        def check(m):
            return m.author.id == ctx.author.id and m.channel == ctx.channel and m.content.lower() in ["spin", "stop"]
        try:
            msg = await bot.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("timed out. embers lost. coward")
            return
        if msg.content.lower() == "stop":
            winnings = int(amount * 1.2)
            update_user(ctx.author.id, embers=user[1]-amount+winnings)
            await ctx.send("cashed out! won " + str(winnings) + " embers (1.2x). scaredy cat")
            return
        spins += 1
        if spins == loaded:
            await ctx.send("BANG! LOST EVERYTHING. shouldve stopped")
            return
        else:
            await ctx.send("click... " + str(spins) + "/6 spins. safe so far. spin or stop?")

@bot.command()
async def rig(ctx, amount: int):
    ok, remaining = check_gambling_ban(ctx.author.id)
    if not ok:
        await ctx.send("gambling banned for " + str(remaining//60) + "m " + str(remaining%60) + "s. caught again?")
        return
    user = get_user(ctx.author.id)
    if amount > user[1] or amount < 1:
        await ctx.send("invalid")
        return
    update_user(ctx.author.id, embers=user[1]-amount)
    if random.random() < 0.25:
        winnings = amount * 2
        update_user(ctx.author.id, embers=user[1]-amount+winnings)
        await ctx.send("rig successful! won " + str(winnings) + " embers (2x). criminal mastermind")
    else:
        ban_until = (datetime.now() + timedelta(minutes=3)).isoformat()
        update_user(ctx.author.id, gambling_ban_until=ban_until)
        await ctx.send("CAUGHT CHEATING! banned for 3 mins. embers lost. u suck at cheating")

@bot.command()
async def marry(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("cant marry urself. thats just self love")
        return
    user = get_user(ctx.author.id)
    if user[7]:
        married = bot.get_user(user[7])
        name = married.display_name if married else "someone"
        await ctx.send("ur already married to " + name + "! polygamy not supported")
        return
    await ctx.send(member.mention + ", " + ctx.author.display_name + " is proposing! reply yes to marry (or ignore them)")
    def check(m):
        return m.author.id == member.id and m.channel == ctx.channel and m.content.lower() == "yes"
    try:
        await bot.wait_for("message", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("proposal rejected (timed out). left on read lmao")
        return
    update_user(ctx.author.id, married_to=member.id)
    update_user(member.id, married_to=ctx.author.id)
    await ctx.send(ctx.author.mention + " and " + member.mention + " married! shared debt... i mean love!")

@bot.command()
async def divorce(ctx):
    user = get_user(ctx.author.id)
    if not user[7]:
        await ctx.send("ur not married. cant divorce air")
        return
    partner_id = user[7]
    update_user(ctx.author.id, married_to=None)
    update_user(partner_id, married_to=None)
    partner = bot.get_user(partner_id)
    name = partner.display_name if partner else "them"
    await ctx.send("divorced " + name + ". assets split. emotional damage sustained")

@bot.command()
async def will(ctx, member: discord.Member):
    update_user(ctx.author.id, will_to=member.id)
    await ctx.send(member.mention + " gets ur stuff when u quit. morbid but practical")

@bot.command()
async def cult(ctx, *, name: str):
    if len(name) > 30:
        await ctx.send("cult name too long. 30 chars max. keep it cult-y")
        return
    user = get_user(ctx.author.id)
    if user[9]:
        await ctx.send("already in a cult. betray it first traitor")
        return
    update_user(ctx.author.id, cult_id=ctx.author.id, cult_name=name, cult_leader=ctx.author.id)
    await ctx.send("cult " + name + " founded! indoctrinate the masses")

@bot.command()
async def betray(ctx):
    user = get_user(ctx.author.id)
    if not user[9]:
        await ctx.send("not in a cult. cant betray nothing")
        return
    if user[11] == ctx.author.id:
        await ctx.send("cant betray ur own cult. disband it if u want out")
        return
    profit = random.randint(50, 200)
    update_user(ctx.author.id, embers=user[1]+profit, cult_id=None, cult_name=None, cult_leader=None)
    await ctx.send("betrayed the cult for " + str(profit) + " embers. cold blooded. respect")

@bot.command()
async def tribute(ctx):
    owner = ctx.guild.owner
    if not owner:
        await ctx.send("no server owner found. anarchy?")
        return
    user = get_user(ctx.author.id)
    amount = min(50, user[1])
    if amount < 1:
        await ctx.send("too poor to tribute. embarrassing")
        return
    update_user(ctx.author.id, embers=user[1]-amount)
    owner_data = get_user(owner.id)
    update_user(owner.id, embers=owner_data[1]+amount)
    await ctx.send("paid " + str(amount) + " embers tribute to " + owner.display_name + ". they probably wont notice")

@bot.command()
async def roast(ctx, member: discord.Member):
    roasts = [member.mention + " has the personality of a loading screen", member.mention + " is like a cloud. when they disappear its a beautiful day", member.mention + " brain has too many tabs open and theyre all 404", member.mention + " brings everyone joy... when they leave", member.mention + " is proof that evolution can go backwards", member.mention + " has two brain cells and theyre fighting for third place", member.mention + " is the reason the gene pool needs a lifeguard", member.mention + " WiFi signal is stronger than their personality"]
    await ctx.send(random.choice(roasts))

@bot.command()
async def confess(ctx, *, confession: str):
    if len(confession) > 500:
        await ctx.send("confession too long. 500 chars max. keep it brief")
        return
    await ctx.send("anonymous confession: " + confession)
    await ctx.message.delete()

@bot.command()
async def tutorial(ctx):
    steps = ["Welcome to Flame Bot!", "1. flame summon - get ur first creature", "2. flame cage - see ur creatures", "3. flame daily - free embers every 20h", "4. flame embers - check balance", "5. flame dice amount - gamble (careful)", "6. flame duel user - battle someone", "7. flame help - see all commands", "Pro tip: use f instead of flame for speed"]
    embed = discord.Embed(title="Flame Bot Tutorial", color=0x00FF00)
    desc = " | ".join(steps)
    embed.description = desc
    await ctx.send(embed=embed)

@bot.command()
async def stats(ctx):
    user = get_user(ctx.author.id)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM creatures WHERE user_id = ?", (ctx.author.id,))
    creature_count = c.fetchone()[0]
    conn.close()
    embed = discord.Embed(title=ctx.author.display_name + " Stats", color=0x3498DB)
    embed.add_field(name="Embers", value=str(user[1]), inline=True)
    embed.add_field(name="Streak", value=str(user[2]) + " days", inline=True)
    embed.add_field(name="Creatures", value=str(creature_count), inline=True)
    embed.add_field(name="Loan", value=str(user[7]) + " embers" if user[7] > 0 else "None", inline=True)
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
    embed = discord.Embed(title=ctx.guild.name + " Leaderboard", color=0xFFD93D)
    for i, (uid, embers) in enumerate(rows, 1):
        user = bot.get_user(uid)
        name = user.display_name if user else "User " + str(uid)
        embed.add_field(name="#" + str(i) + " " + name, value=str(embers) + " embers", inline=False)
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
        name = user.display_name if user else "User " + str(uid)
        embed.add_field(name="#" + str(i) + " " + name, value=str(embers) + " embers", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def settings(ctx, *, setting: str = None):
    if not setting:
        embed = discord.Embed(title="Settings", color=0x95A5A6)
        embed.add_field(name="Available", value="notifications - toggle DMs, compact - shorter messages", inline=False)
        await ctx.send(embed=embed)
        return
    await ctx.send("setting " + setting + " updated. (placeholder lol)")

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
            embed.add_field(name="Daily", value=str(wait.seconds//3600) + "h " + str((wait.seconds%3600)//60) + "m", inline=False)
        else:
            embed.add_field(name="Daily", value="Ready!", inline=False)
    else:
        embed.add_field(name="Daily", value="Ready!", inline=False)
    if user[9]:
        ban = datetime.fromisoformat(user[9])
        if ban > now:
            wait = ban - now
            embed.add_field(name="Gambling Ban", value=str(wait.seconds//60) + "m " + str(wait.seconds%60) + "s", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def changelog(ctx):
    embed = discord.Embed(title="Flame Bot Changelog", color=0x9B59B6)
    embed.add_field(name="v1.0", value="Initial release with 76 commands!", inline=False)
    embed.add_field(name="Features", value="Economy, Creatures, Combat, Gambling, Social, Utility, Weird", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def dream(ctx):
    dreams = ["ur creature dreams of flying. maybe evolve it?", "a shadow whispers: invest today, moon tomorrow", "u see numbers: 7, 13, 42. try flame pick", "a Grub tells u: the vault code ends in 5", "ur creature dreams of battle. duel someone", "vision: legendary creature awaits the patient", "oracle says: risk brings reward, but not always urs"]
    await ctx.send("Dream: " + random.choice(dreams))

@bot.command()
async def curse(ctx, member: discord.Member):
    debuff_until = (datetime.now() + timedelta(hours=1)).isoformat()
    update_user(member.id, curse_debuff_until=debuff_until)
    await ctx.send("cursed " + member.mention + "! bad luck for 1 hour. their gambling odds just got worse")

@bot.command()
async def bless(ctx, member: discord.Member):
    buff_until = (datetime.now() + timedelta(hours=1)).isoformat()
    update_user(member.id, luck_buff_until=buff_until)
    await ctx.send("blessed " + member.mention + "! good luck for 1 hour. may the odds be ever in their favor")

@bot.command()
async def time(ctx):
    now = datetime.now()
    await ctx.send("server time: " + now.strftime("%Y-%m-%d %H:%M:%S") + " | some commands affected by time of day (not really but pretend)")

@bot.command()
async def weather(ctx):
    weathers = ["Sunny", "Rainy", "Stormy", "Foggy", "Eclipse"]
    weather = random.choice(weathers)
    effects = {"Sunny": "Summon rates normal.", "Rainy": "Uncommon creatures more likely.", "Stormy": "Epic creatures slightly more likely. Gambling riskier.", "Foggy": "Common creatures dominate. Hard to see ambushes coming.", "Eclipse": "Legendary creatures possible! Everything else breaks."}
    await ctx.send("Current weather: " + weather + " | " + effects[weather])

@bot.command()
async def oracle(ctx, *, question: str):
    answers = ["The void whispers... yes.", "The stars align... no.", "A Grub chews thoughtfully... maybe.", "The answer is hidden in your cage.", "Ask again after flame daily.", "The oracle is napping. Try later.", "Yes, but at what cost?", "No, and be grateful.", "The creatures are divided. Flip a coin.", "Absolutely... not."]
    await ctx.send("Q: " + question + " | A: " + random.choice(answers))

@bot.command()
async def mimic(ctx, member: discord.Member):
    await ctx.send(member.mention + " Your creature mimics " + member.display_name + " last message. (joke command lol)")

@bot.command()
async def glitch(ctx):
    glitches = ["01001000 01100101 01101100 01110000", "[REDACTED]", "ERROR: CREATUR_NOT_FOND", "Your embers are now imaginary. Just kidding.", "The bot is self-aware. Run.", "01001110 01101001 01100011 01100101", "Loading... 99%... stuck forever."]
    await ctx.send(random.choice(glitches))

@bot.command()
async def lore(ctx):
    lores = ["In the beginning, there was only Ember. Then came the Grubs.", "The Abyssal King once ruled all cages. Now he waits.", "Legend says the first duel was between two Mosslings. It lasted 3 days.", "The Vault was built by a creature that could count to 1000. No one knows which one.", "Embers are crystallized time. Or maybe just shiny rocks.", "The Cult of the Flame was founded by a Dust Bunny with ambition.", "Void Walkers dont walk. They just stop existing in one place and start in another."]
    await ctx.send("Lore drop: " + random.choice(lores))

@bot.command()
async def quit(ctx):
    user = get_user(ctx.author.id)
    if user[8]:
        heir = bot.get_user(user[8])
        heir_name = heir.display_name if heir else "someone"
        await ctx.send("Account 'deleted'. " + heir_name + " inherits your " + str(user[1]) + " embers. (Just kidding - nothing was deleted. Use flame will to actually set an heir)")
    else:
        await ctx.send("You cant quit. No one can quit. The Flame consumes all. (Account still active lol)")

bot.run(TOKEN)
