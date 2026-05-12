import discord
from discord.ext import commands
import os
import sqlite3
import random
import asyncio
from dotenv import load_dotenv

# ==========================================
# CORE CONFIG
# ==========================================
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = "f " # Support for 'f' or 'flame' as requested
CURRENCY = "embers"
COLOR_MAIN = 0x2f3136 # Sleek Dark Theme

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=["f ", "flame "], intents=intents, help_command=None)

# ==========================================
# THE MASTER DATABASE
# ==========================================
def get_db():
    conn = sqlite3.connect('flame_master.db')
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    conn = get_db()
    # Profiles & Economy
    conn.execute('''CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance INTEGER DEFAULT 1000,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        daily_streak INTEGER DEFAULT 0,
        last_daily TEXT,
        bio TEXT DEFAULT 'A mysterious traveler.'
    )''')
    
    # Creatures System
    conn.execute('''CREATE TABLE IF NOT EXISTS creatures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER,
        name TEXT,
        species TEXT,
        mood INTEGER DEFAULT 100,
        is_favorite INTEGER DEFAULT 0
    )''')
    
    # Social System (Marry/Divorce)
    conn.execute('''CREATE TABLE IF NOT EXISTS relationships (
        user_one INTEGER PRIMARY KEY,
        user_two INTEGER,
        status TEXT
    )''')
    
    conn.commit()
    conn.close()
    print("--- FLAME ENGINE INITIALIZED ---")

# ==========================================
# UTILS
# ==========================================
def sync_profile(user_id, username):
    conn = get_db()
    user = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    if not user:
        conn.execute("INSERT INTO profiles (user_id, username, balance) VALUES (?, ?, 1000)", 
                     (user_id, username))
        conn.commit()
    conn.close()
# ==========================================
# CORE EVENTS
# ==========================================

@bot.event
async def on_ready():
    initialize_db()
    await bot.change_presence(activity=discord.Game(name="f help | Gathering Embers"))
    print(f"--- {bot.user.name} IS LIVE ---")

@bot.event
async def on_message(message):
    if message.author.bot: return
    sync_profile(message.author.id, message.author.name)
    
    # Simple XP Gain
    conn = get_db()
    conn.execute("UPDATE profiles SET xp = xp + 5 WHERE user_id = ?", (message.author.id,))
    conn.commit()
    conn.close()
    
    await bot.process_commands(message)

# ==========================================
# ECONOMY COMMANDS
# ==========================================

@bot.command(aliases=["bal", "money"])
async def embers(ctx, member: discord.Member = None):
    """Check your current ember balance"""
    target = member or ctx.author
    sync_profile(target.id, target.name)
    conn = get_db()
    user = conn.execute("SELECT balance FROM profiles WHERE user_id = ?", (target.id,)).fetchone()
    conn.close()
    await ctx.send(f"🔥 {target.display_name} holds **{user['balance']} embers**.")

@bot.command()
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    """Claim your daily embers"""
    reward = 500
    conn = get_db()
    conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (reward, ctx.author.id))
    conn.commit()
    conn.close()
    await ctx.send(f"✨ **Daily Collected!** +{reward} embers.")

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def beg(ctx):
    """Beg for embers"""
    amount = random.randint(5, 50)
    if random.random() > 0.4:
        conn = get_db()
        conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (amount, ctx.author.id))
        conn.commit()
        conn.close()
        await ctx.send(f"🙏 A kind soul gave you **{amount} embers**.")
    else:
        await ctx.send("💀 Get a job. (No embers given)")

@bot.command()
@commands.cooldown(1, 300, commands.BucketType.user)
async def scam(ctx):
    """Attempt a high-risk scam"""
    if random.random() > 0.7: # 30% success
        amount = random.randint(300, 800)
        conn = get_db()
        conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (amount, ctx.author.id))
        conn.commit()
        conn.close()
        await ctx.send(f"😈 **SCAM SUCCESS.** You made off with {amount} embers!")
    else:
        loss = 200
        conn = get_db()
        conn.execute("UPDATE profiles SET balance = balance - ? WHERE user_id = ?", (loss, ctx.author.id))
        conn.commit()
        conn.close()
        await ctx.send(f"👮 **CAUGHT.** You were fined {loss} embers.")

@bot.command()
async def send(ctx, member: discord.Member, amount: int):
    """Transfer embers to another user"""
    if amount <= 0: return
    sync_profile(ctx.author.id, ctx.author.name)
    sync_profile(member.id, member.name)
    
    conn = get_db()
    user = conn.execute("SELECT balance FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()
    if user['balance'] < amount:
        return await ctx.send("You don't have enough embers.")
    
    conn.execute("UPDATE profiles SET balance = balance - ? WHERE user_id = ?", (amount, ctx.author.id))
    conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (amount, member.id))
    conn.commit()
    conn.close()
    await ctx.send(f"✅ Sent **{amount} embers** to {member.mention}.")
# ==========================================
# GAMBLING COMMANDS
# ==========================================

@bot.command()
async def flip(ctx, side: str, amount: int):
    """Bet embers on a coin flip"""
    side = side.lower()
    if side not in ["heads", "tails"]:
        return await ctx.send("Pick **heads** or **tails**.")
    
    sync_profile(ctx.author.id, ctx.author.name)
    conn = get_db()
    user = conn.execute("SELECT balance FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()

    if user['balance'] < amount or amount <= 0:
        return await ctx.send("Invalid bet amount.")

    result = random.choice(["heads", "tails"])
    if side == result:
        conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (amount, ctx.author.id))
        res_msg = f"✨ It was **{result}**! You won **{amount} embers**."
    else:
        conn.execute("UPDATE profiles SET balance = balance - ? WHERE user_id = ?", (amount, ctx.author.id))
        res_msg = f"💀 It was **{result}**. You lost **{amount} embers**."
    
    conn.commit()
    conn.close()
    await ctx.send(res_msg)

@bot.command()
async def dice(ctx, bet: int, guess: int):
    """Roll a die (1-6) | 5x payout on correct guess"""
    if not (1 <= guess <= 6):
        return await ctx.send("Guess a number between 1 and 6.")
    
    sync_profile(ctx.author.id, ctx.author.name)
    conn = get_db()
    user = conn.execute("SELECT balance FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()

    if user['balance'] < bet or bet <= 0:
        return await ctx.send("Invalid bet.")

    roll = random.randint(1, 6)
    if roll == guess:
        payout = bet * 5
        conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (payout, ctx.author.id))
        msg = f"🎲 **JACKPOT!** It rolled a {roll}. You won **{payout} embers**!"
    else:
        conn.execute("UPDATE profiles SET balance = balance - ? WHERE user_id = ?", (bet, ctx.author.id))
        msg = f"🎲 Rolled a {roll}. You lost **{bet} embers**."

    conn.commit()
    conn.close()
    await ctx.send(msg)

@bot.command()
async def chamber(ctx):
    """Ember Roulette - 1/6 chance to lose everything"""
    sync_profile(ctx.author.id, ctx.author.name)
    conn = get_db()
    
    # 1 in 6 chance
    if random.randint(1, 6) == 1:
        conn.execute("UPDATE profiles SET balance = 0 WHERE user_id = ?", (ctx.author.id,))
        msg = "💥 **BANG.** You lost every single ember you owned."
    else:
        reward = 100
        conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (reward, ctx.author.id))
        msg = f"🔫 *Click.* You survived and earned **{reward} embers** for your bravery."
        
    conn.commit()
    conn.close()
    await ctx.send(msg)

@bot.command()
async def shells(ctx, bet: int, choice: int):
    """Find the ember under 3 shells (1, 2, or 3)"""
    if choice not in [1, 2, 3]:
        return await ctx.send("Pick shell 1, 2, or 3.")
    
    sync_profile(ctx.author.id, ctx.author.name)
    conn = get_db()
    user = conn.execute("SELECT balance FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()

    if user['balance'] < bet or bet <= 0:
        return await ctx.send("Not enough embers.")

    winning_shell = random.randint(1, 3)
    if choice == winning_shell:
        payout = bet * 2
        conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (payout, ctx.author.id))
        msg = f"🐚 Correct! The ember was under shell {winning_shell}. You won **{payout} embers**!"
    else:
        conn.execute("UPDATE profiles SET balance = balance - ? WHERE user_id = ?", (bet, ctx.author.id))
        msg = f"🐚 Wrong. It was under shell {winning_shell}. You lost **{bet} embers**."

    conn.commit()
    conn.close()
    await ctx.send(msg)
# ==========================================
# CREATURES SYSTEM
# ==========================================

@bot.command()
async def summon(ctx):
    """Summon a random creature for a price"""
    cost = 1500
    sync_profile(ctx.author.id, ctx.author.name)
    
    conn = get_db()
    user = conn.execute("SELECT balance FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()
    
    if user['balance'] < cost:
        return await ctx.send(f"❌ Summoning requires **{cost} embers**. You are too weak.")

    # Random species generation
    species_list = ["Shadow Stalker", "Ember Drake", "Void Crawler", "Neon Spirit", "Glitch Beast"]
    chosen_species = random.choice(species_list)
    
    conn.execute("UPDATE profiles SET balance = balance - ? WHERE user_id = ?", (cost, ctx.author.id))
    conn.execute("INSERT INTO creatures (owner_id, name, species) VALUES (?, ?, ?)", 
                 (ctx.author.id, f"Wild {chosen_species}", chosen_species))
    conn.commit()
    conn.close()
    
    await ctx.send(f"🌀 The air cracks open... You summoned a **{chosen_species}**!")

@bot.command()
async def cage(ctx):
    """View your collection of captured creatures"""
    conn = get_db()
    pets = conn.execute("SELECT * FROM creatures WHERE owner_id = ?", (ctx.author.id,)).fetchall()
    conn.close()
    
    if not pets:
        return await ctx.send("Your cages are empty. Use `f summon` to find a creature.")
    
    embed = discord.Embed(title=f"🐾 {ctx.author.display_name}'s Menagerie", color=0x7289da)
    for p in pets:
        fav = "⭐" if p['is_favorite'] else ""
        embed.add_field(
            name=f"{p['name']} {fav}", 
            value=f"Species: {p['species']}\nMood: {p['mood']}%", 
            inline=True
        )
    await ctx.send(embed=embed)

@bot.command()
async def feed(ctx, *, name: str):
    """Feed a creature to improve its mood"""
    cost = 100
    conn = get_db()
    pet = conn.execute("SELECT * FROM creatures WHERE owner_id = ? AND name = ?", 
                       (ctx.author.id, name)).fetchone()
    
    if not pet:
        return await ctx.send("Creature not found in your cages.")
    
    user = conn.execute("SELECT balance FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()
    if user['balance'] < cost:
        return await ctx.send("You don't have enough embers for food.")

    new_mood = min(100, pet['mood'] + 20)
    conn.execute("UPDATE profiles SET balance = balance - ? WHERE user_id = ?", (cost, ctx.author.id))
    conn.execute("UPDATE creatures SET mood = ? WHERE id = ?", (new_mood, pet['id']))
    conn.commit()
    conn.close()
    
    await ctx.send(f"🍖 You fed **{name}**. Its mood is now {new_mood}%.")

@bot.command()
async def release(ctx, *, name: str):
    """Release a creature back into the void"""
    conn = get_db()
    pet = conn.execute("SELECT * FROM creatures WHERE owner_id = ? AND name = ?", 
                       (ctx.author.id, name)).fetchone()
    
    if not pet:
        return await ctx.send("You can't release what you don't have.")
    
    conn.execute("DELETE FROM creatures WHERE id = ?", (pet['id']))
    conn.commit()
    conn.close()
    
    await ctx.send(f"💨 You opened the cage. **{name}** vanished into the mist.")
# ==========================================
# SOCIAL & RELATIONSHIPS
# ==========================================

@bot.command()
async def marry(ctx, member: discord.Member):
    """Propose to another user"""
    if member == ctx.author: return await ctx.send("You can't marry yourself, loner.")
    
    sync_profile(ctx.author.id, ctx.author.name)
    sync_profile(member.id, member.name)
    
    await ctx.send(f"💍 {member.mention}, {ctx.author.name} has proposed! Type `yes` to accept.")

    def check(m):
        return m.author == member and m.content.lower() == 'yes' and m.channel == ctx.channel

    try:
        await bot.wait_for('message', timeout=30.0, check=check)
        conn = get_db()
        conn.execute("INSERT OR REPLACE INTO relationships (user_one, user_two, status) VALUES (?, ?, ?)",
                     (ctx.author.id, member.id, "Married"))
        conn.commit()
        conn.close()
        await ctx.send(f"🎊 {ctx.author.mention} and {member.mention} are now married!")
    except asyncio.TimeoutError:
        await ctx.send("💔 Left on read. Rip.")

@bot.command()
async def divorce(ctx):
    """End your current marriage"""
    conn = get_db()
    conn.execute("DELETE FROM relationships WHERE user_one = ? OR user_two = ?", (ctx.author.id, ctx.author.id))
    conn.commit()
    conn.close()
    await ctx.send("⚖️ The papers are signed. You are now single.")

# ==========================================
# UTILITY & WEIRD
# ==========================================

@bot.command(name="help")
async def help_menu(ctx):
    """The custom help menu from your screenshot"""
    embed = discord.Embed(title="Flame Bot Commands", color=COLOR_MAIN)
    embed.add_field(name="Economy", value="embers, daily, beg, scam, send, burn", inline=False)
    embed.add_field(name="Creatures", value="summon, cage, release, feed", inline=False)
    embed.add_field(name="Gambling", value="dice, flip, shells, chamber", inline=False)
    embed.add_field(name="Social", value="marry, divorce", inline=False)
    embed.add_field(name="Weird", value="glitch, lore", inline=False)
    embed.set_footer(text="Use f help <category> for details | Prefix: f or flame")
    await ctx.send(embed=embed)

@bot.command()
async def glitch(ctx):
    """A 'weird' category command"""
    glitch_text = ["ERROR_777", "SYSTEM_FAILURE", "V_O_I_D", " embers.exe has stopped working "]
    await ctx.send(f"░{random.choice(glitch_text)}░")

@bot.command()
async def lore(ctx):
    """The lore of the Embers"""
    lore_bits = [
        "The first ember was stolen from a dying star.",
        "They say those who hold 1,000,000 embers can talk to the Void.",
        "Flame Bot isn't a bot. It's a containment unit."
    ]
    await ctx.send(f"📜 {random.choice(lore_bits)}")

# ==========================================
# FINAL EXECUTION - MUST BE AT THE VERY BOTTOM
# ==========================================

print("Checking for Token...")
if TOKEN is None:
    print("ERROR: DISCORD_TOKEN variable is empty!")
else:
    print("Token found. Starting bot...")
    bot.run(TOKEN)
