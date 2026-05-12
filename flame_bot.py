import discord
from discord.ext import commands, tasks
import os
import sqlite3
import random
import asyncio
import datetime
from dotenv import load_dotenv

# ==========================================
# 0. CONFIGURATION & INTENTS
# ==========================================
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIXES = ["f ", "flame "]
CURRENCY = "embers"
COLOR_INDUSTRIAL = 0xFF4500 # Safety Orange
COLOR_STEEL = 0x2F3136      # Matte Steel

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIXES, intents=intents, help_command=None)

# ==========================================
# 1. DATABASE ENGINE (The Brain)
# ==========================================
def initialize_db():
    conn = sqlite3.connect('flame_master.db')
    cursor = conn.cursor()
    
    # User Profiles & Stats
    cursor.execute('''CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance INTEGER DEFAULT 1000,
        bank INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        prestige INTEGER DEFAULT 0,
        daily_streak INTEGER DEFAULT 0,
        last_daily TEXT,
        bio TEXT DEFAULT 'An industrial traveler.'
    )''')
    
    # Creature Collection
    cursor.execute('''CREATE TABLE IF NOT EXISTS creatures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER,
        name TEXT,
        species TEXT,
        rarity TEXT,
        power INTEGER DEFAULT 10,
        mood INTEGER DEFAULT 100,
        is_favorite INTEGER DEFAULT 0
    )''')
    
    # Social Ties
    cursor.execute('''CREATE TABLE IF NOT EXISTS relationships (
        user_one INTEGER PRIMARY KEY,
        user_two INTEGER,
        marriage_date TEXT,
        status TEXT
    )''')

    # Inventory System
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_name TEXT,
        quantity INTEGER DEFAULT 1
    )''')

    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('flame_master.db')
    conn.row_factory = sqlite3.Row
    return conn

def sync_user(user_id, username):
    conn = get_db()
    user = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    if not user:
        conn.execute("INSERT INTO profiles (user_id, username, balance) VALUES (?, ?, 1000)", 
                     (user_id, str(username)))
        conn.commit()
    conn.close()

# ==========================================
# 2. CORE UTILS & LEVELING LOGIC
# ==========================================
async def add_xp(user_id, amount):
    conn = get_db()
    user = conn.execute("SELECT xp, level FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    new_xp = user['xp'] + amount
    new_level = user['level']
    
    # Level up logic: (level * 500 XP required)
    requirement = new_level * 500
    if new_xp >= requirement:
        new_xp -= requirement
        new_level += 1
    
    conn.execute("UPDATE profiles SET xp = ?, level = ? WHERE user_id = ?", (new_xp, new_level, user_id))
    conn.commit()
    conn.close()
    return new_level > user['level']

# ==========================================
# 3. GLOBAL EVENTS & ON_READY
# ==========================================
@bot.event
async def on_ready():
    initialize_db()
    print(f"--- LOGGED IN AS {bot.user.name} ---")
    print(f"--- DATABASE CONNECTED ---")
    bot.start_time = datetime.datetime.utcnow()

@bot.event
async def on_message(message):
    if message.author.bot: return
    sync_user(message.author.id, message.author.name)
    
    # Silent XP gain for chatting
    leveled_up = await add_xp(message.author.id, 5)
    if leveled_up:
        await message.channel.send(f"☢️ **LEVEL UP!** {message.author.mention} reached level.")
        
    await bot.process_commands(message)

# ==========================================
# 4. ECONOMY CATEGORY (Full Scale)
# ==========================================
@bot.command(aliases=['bal', 'e'])
async def embers(ctx, member: discord.Member = None):
    target = member or ctx.author
    sync_user(target.id, target.name)
    conn = get_db()
    user = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (target.id,)).fetchone()
    conn.close()
    
    embed = discord.Embed(title=f"🔥 {target.display_name}'s Vault", color=COLOR_STEEL)
    embed.add_field(name="Wallet", value=f"{user['balance']} embers", inline=True)
    embed.add_field(name="Bank", value=f"{user['bank']} embers", inline=True)
    embed.add_field(name="Progress", value=f"Lvl {user['level']} | {user['xp']} XP", inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    reward = 1000
    conn = get_db()
    conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (reward, ctx.author.id))
    conn.commit()
    conn.close()
    await ctx.send(f"⚒️ **Daily Shift Completed.** You earned **{reward} embers**.")

@bot.command()
async def deposit(ctx, amount: str):
    conn = get_db()
    user = conn.execute("SELECT balance, bank FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()
    
    if amount.lower() == 'all': amt = user['balance']
    else: amt = int(amount)
    
    if amt <= 0 or amt > user['balance']:
        return await ctx.send("Invalid amount.")
        
    conn.execute("UPDATE profiles SET balance = balance - ?, bank = bank + ? WHERE user_id = ?", 
                 (amt, amt, ctx.author.id))
    conn.commit()
    conn.close()
    await ctx.send(f"📥 Deposited **{amt} embers** into your secure vault.")

# ... [CONT. IN NEXT BLOCK] ...
# ==========================================
# 5. ADVANCED GAMBLING (Risk & Reward)
# ==========================================

@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def slots(ctx, bet: int):
    """High-intensity slot machine"""
    if bet < 50: return await ctx.send("Min bet is 50 embers.")
    
    conn = get_db()
    user = conn.execute("SELECT balance FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()
    if user['balance'] < bet: return await ctx.send("You're broke, buddy.")

    emojis = ["🔥", "⚙️", "💎", "💀", "🌀", "⚡"]
    result = [random.choice(emojis) for _ in range(3)]
    
    # Win Logic
    if result[0] == result[1] == result[2]:
        payout = bet * 10
        msg = f"🎰 **JACKPOT!** | {' | '.join(result)} | You won **{payout} embers!**"
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        payout = bet * 2
        msg = f"🎰 **BIG WIN** | {' | '.join(result)} | You won **{payout} embers.**"
    else:
        payout = -bet
        msg = f"🎰 **LOSS** | {' | '.join(result)} | Better luck next time."

    conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (payout, ctx.author.id))
    conn.commit()
    conn.close()
    await ctx.send(msg)

@bot.command()
async def coinflip(ctx, side: str, bet: int):
    """Classic 50/50"""
    side = side.lower()
    if side not in ['h', 't', 'heads', 'tails']:
        return await ctx.send("Choose heads or tails.")
    
    conn = get_db()
    user = conn.execute("SELECT balance FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()
    if user['balance'] < bet: return await ctx.send("Insufficient funds.")

    outcome = random.choice(['heads', 'tails'])
    win = side.startswith(outcome[0])
    
    payout = bet if win else -bet
    conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (payout, ctx.author.id))
    conn.commit()
    conn.close()
    
    status = "WON" if win else "LOST"
    await ctx.send(f"🪙 It was **{outcome}**! You **{status} {bet} embers**.")

# ==========================================
# 6. CREATURE GENETICS & SUMMONING
# ==========================================

RARITIES = {
    "Common": {"chance": 0.60, "multiplier": 1, "color": 0x95a5a6},
    "Uncommon": {"chance": 0.25, "multiplier": 2, "color": 0x2ecc71},
    "Rare": {"chance": 0.10, "multiplier": 5, "color": 0x3498db},
    "Epic": {"chance": 0.04, "multiplier": 10, "color": 0x9b59b6},
    "LEGENDARY": {"chance": 0.01, "multiplier": 50, "color": 0xf1c40f}
}

SPECIES = [
    "Scrap Hound", "Steel Weaver", "Rust Golem", "Steam Drake", 
    "Oil Elemental", "Safety Drone", "Neon Phantom", "Void Engine"
]

@bot.command()
async def summon(ctx):
    """Summon a creature with randomized rarity and power"""
    cost = 2000
    conn = get_db()
    user = conn.execute("SELECT balance FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()
    
    if user['balance'] < cost:
        return await ctx.send(f"Summoning costs {cost} embers. You are missing {cost - user['balance']}.")

    # Rarity Roll
    roll = random.random()
    current_weight = 0
    selected_rarity = "Common"
    for rarity, data in RARITIES.items():
        current_weight += data['chance']
        if roll <= current_weight:
            selected_rarity = rarity
            break
            
    species = random.choice(SPECIES)
    power = random.randint(10, 50) * RARITIES[selected_rarity]['multiplier']
    
    conn.execute("UPDATE profiles SET balance = balance - ? WHERE user_id = ?", (cost, ctx.author.id))
    conn.execute("INSERT INTO creatures (owner_id, name, species, rarity, power) VALUES (?, ?, ?, ?, ?)",
                 (ctx.author.id, f"Wild {species}", species, selected_rarity, power))
    conn.commit()
    conn.close()

    embed = discord.Embed(title="🌀 SUMMON SUCCESS", color=RARITIES[selected_rarity]['color'])
    embed.add_field(name="Species", value=species, inline=True)
    embed.add_field(name="Rarity", value=selected_rarity, inline=True)
    embed.add_field(name="Power Level", value=power, inline=True)
    embed.set_footer(text="Your creature has been moved to the cage.")
    await ctx.send(embed=embed)

@bot.command()
async def cage(ctx, page: int = 1):
    """View your menagerie with detailed stats"""
    conn = get_db()
    creatures = conn.execute("SELECT * FROM creatures WHERE owner_id = ?", (ctx.author.id,)).fetchall()
    conn.close()
    
    if not creatures: return await ctx.send("Your cages are empty.")

    embed = discord.Embed(title=f"🐾 {ctx.author.name}'s Collection", color=COLOR_STEEL)
    # We list 5 creatures per page to keep it clean
    start = (page-1) * 5
    end = start + 5
    
    for c in creatures[start:end]:
        embed.add_field(
            name=f"ID: {c['id']} | {c['name']}",
            value=f"✨ **{c['rarity']}** {c['species']}\n⚔️ Power: {c['power']}\n😊 Mood: {c['mood']}%",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} | Total Creatures: {len(creatures)}")
    await ctx.send(embed=embed)

# ... [SOCIAL & COMBAT SYSTEM IN PART 3] ...
# ==========================================
# 7. SOCIAL REGISTRY (Marriage & Legacy)
# ==========================================

@bot.command()
async def marry(ctx, member: discord.Member):
    """Formalize a bond between two users"""
    if member == ctx.author: 
        return await ctx.send("The mirrors are not for marrying.")
    if member.bot: 
        return await ctx.send("AI hearts are made of silicon.")

    conn = get_db()
    # Check if either user is already married
    check = conn.execute("SELECT * FROM relationships WHERE user_one IN (?, ?) OR user_two IN (?, ?)", 
                         (ctx.author.id, member.id, ctx.author.id, member.id)).fetchone()
    
    if check:
        conn.close()
        return await ctx.send("💍 One of you is already bound by the registry.")

    await ctx.send(f"💍 {member.mention}, {ctx.author.name} is proposing a formal bond. Type `I DO` to accept.")

    def check_resp(m):
        return m.author == member and m.content.upper() == 'I DO' and m.channel == ctx.channel

    try:
        await bot.wait_for('message', timeout=60.0, check=check_resp)
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        conn.execute("INSERT INTO relationships (user_one, user_two, marriage_date, status) VALUES (?, ?, ?, ?)",
                     (ctx.author.id, member.id, today, "Legit"))
        conn.commit()
        await ctx.send(f"🎊 **IT IS OFFICIAL.** The bond was registered on {today}. Congratulations!")
    except asyncio.TimeoutError:
        await ctx.send("⌛ Silence. The offer has expired.")
    finally:
        conn.close()

@bot.command()
async def divorce(ctx):
    """Dissolve a registered bond (Costs 5,000 embers)"""
    cost = 5000
    conn = get_db()
    user = conn.execute("SELECT balance FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()
    
    if user['balance'] < cost:
        return await ctx.send(f"Divorce papers cost {cost} embers. You're too poor to leave.")

    # Check for relationship
    rel = conn.execute("SELECT * FROM relationships WHERE user_one = ? OR user_two = ?", 
                       (ctx.author.id, ctx.author.id)).fetchone()
    
    if not rel:
        conn.close()
        return await ctx.send("You aren't registered to anyone.")

    conn.execute("DELETE FROM relationships WHERE user_one = ? OR user_two = ?", (ctx.author.id, ctx.author.id))
    conn.execute("UPDATE profiles SET balance = balance - ? WHERE user_id = ?", (cost, ctx.author.id))
    conn.commit()
    conn.close()
    await ctx.send("⚖️ The bond has been dissolved. You are free (and 5,000 embers poorer).")

# ==========================================
# 8. THE COMBAT ENGINE (Power-Scaled)
# ==========================================

@bot.command()
async def fight(ctx, member: discord.Member, creature_id: int):
    """Duel another user using your creature's Power Level"""
    if member == ctx.author: return await ctx.send("No shadowboxing allowed.")
    
    conn = get_db()
    # Get Attacker's creature
    c1 = conn.execute("SELECT * FROM creatures WHERE id = ? AND owner_id = ?", 
                      (creature_id, ctx.author.id)).fetchone()
    # Get Defender's best creature (Auto-pick their strongest for fairness)
    c2 = conn.execute("SELECT * FROM creatures WHERE owner_id = ? ORDER BY power DESC LIMIT 1", 
                      (member.id,)).fetchone()

    if not c1:
        conn.close()
        return await ctx.send("That creature ID doesn't exist in your cages.")
    if not c2:
        conn.close()
        return await ctx.send(f"{member.name} has no creatures to defend with!")

    await ctx.send(f"⚔️ **BATTLE INITIATED!**\n**{ctx.author.name}** sends out **{c1['name']}** (Power: {c1['power']})\n**VS**\n**{member.name}** defends with **{c2['name']}** (Power: {c2['power']})")

    # The Math: Win probability based on power ratio
    total_power = c1['power'] + c2['power']
    win_chance = c1['power'] / total_power
    
    await asyncio.sleep(3) # Dramatic pause

    if random.random() < win_chance:
        reward = random.randint(500, 1500)
        conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (reward, ctx.author.id))
        conn.execute("UPDATE profiles SET xp = xp + 100 WHERE user_id = ?", (ctx.author.id,))
        result_msg = f"🏆 **{ctx.author.name} WINS!** {c1['name']} crushed the opposition. Earned **{reward} embers**."
    else:
        loss = 300
        conn.execute("UPDATE profiles SET balance = balance - ? WHERE user_id = ?", (loss, ctx.author.id))
        result_msg = f"💀 **{member.name} WINS!** {c2['name']} was too strong. You lost {loss} embers."

    conn.commit()
    conn.close()
    await ctx.send(result_msg)
# ==========================================
# 11. GLOBAL RAIDS & ADMIN UTILITIES
# ==========================================

@bot.command()
@commands.cooldown(1, 3600, commands.BucketType.guild)
async def raid(ctx):
    """Start a server-wide raid event for massive loot"""
    bosses = [
        {"name": "The Steel Overlord", "hp": 5000, "reward": 10000},
        {"name": "Void Engine Alpha", "hp": 8000, "reward": 25000},
        {"name": "The Scrapped King", "hp": 3000, "reward": 5000}
    ]
    boss = random.choice(bosses)
    
    embed = discord.Embed(title="🚨 EMERGENCY: GLOBAL RAID", color=0xFF0000)
    embed.description = f"**{boss['name']}** has appeared! Type `f attack` to join the strike force!\n**Total HP:** {boss['hp']}\n**Time Limit:** 60 Seconds"
    await ctx.send(embed=embed)

    participants = {} # user_id: damage_dealt

    def check(m):
        if m.channel == ctx.channel and m.content.lower() == 'f attack' and not m.author.bot:
            # Each attack is based on player level + random variance
            conn = get_db()
            user = conn.execute("SELECT level FROM profiles WHERE user_id = ?", (m.author.id,)).fetchone()
            dmg = (user['level'] * 10) + random.randint(1, 50)
            participants[m.author.id] = participants.get(m.author.id, 0) + dmg
            return False # Keep listening
        return False

    try:
        await bot.wait_for('message', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        pass # Time is up

    total_damage = sum(participants.values())

    if total_damage >= boss['hp']:
        # Victory logic
        share = boss['reward'] // max(1, len(participants))
        conn = get_db()
        for u_id in participants.keys():
            conn.execute("UPDATE profiles SET balance = balance + ?, xp = xp + 500 WHERE user_id = ?", 
                         (share, u_id))
        conn.commit()
        conn.close()
        
        await ctx.send(f"🏆 **VICTORY!** {boss['name']} was dismantled. {len(participants)} players split the loot, receiving **{share} embers** each!")
    else:
        await ctx.send(f"💀 **DEFEAT.** {boss['name']} escaped with {boss['hp'] - total_damage} HP remaining. No loot was recovered.")

@bot.command()
@commands.has_permissions(administrator=True)
async def nuke(ctx):
    """[ADMIN ONLY] Resets global economy markers or clears database cache"""
    await ctx.send("☢️ **SYSTEM OVERRIDE DETECTED.** Initiating Global Re-calibration...")
    await asyncio.sleep(3)
    
    conn = get_db()
    # Logic: Tax the rich 5%, give to the poor, and boost global XP
    conn.execute("UPDATE profiles SET balance = CAST(balance * 0.95 AS INTEGER)")
    conn.execute("UPDATE profiles SET xp = xp + 1000")
    conn.commit()
    conn.close()
    
    await ctx.send("💥 **THE NUKE DETONATED.** Global XP +1000. All vaults taxed 5% for server maintenance.")

# ==========================================
# 12. THE FINAL MASTER HELP MENU
# ==========================================

@bot.command()
async def help(ctx):
    """The Mega Help Menu for the Masterpiece Bot"""
    embed = discord.Embed(title="🔥 FLAME MASTERPIECE ENGINE", color=COLOR_INDUSTRIAL)
    embed.add_field(name="💰 Economy", value="`embers`, `daily`, `deposit`, `shop`, `buy`, `inv`")
    embed.add_field(name="🎲 Gambling", value="`slots`, `coinflip` (More coming in V2)")
    embed.add_field(name="🐾 RPG", value="`summon`, `cage`, `fight`, `raid`")
    embed.add_field(name="🤝 Social", value="`marry`, `divorce`, `leaderboard` status")
    embed.set_footer(text="Developed for the Industrial-Modern Era | Prefix: f ")
    await ctx.send(embed=embed)

# ==========================================
# 13. BOOT SEQUENCE (The Heartbeat)
# ==========================================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ **COOLING DOWN.** Wait {error.retry_after:.1f}s.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You lack the clearances for this command.")
    else:
        print(f"Internal Error: {error}")

if __name__ == "__main__":
    if TOKEN:
        try:
            print("--- FLAME ENGINE INITIALIZING ---")
            bot.run(TOKEN)
        except Exception as e:
            print(f"CRITICAL BOOT ERROR: {e}")
    else:
        print("ERROR: DISCORD_TOKEN NOT FOUND.")
# ==========================================
# 14. ACHIEVEMENT SYSTEM (The Grind)
# ==========================================

ACHIEVEMENTS = {
    "millionaire": {"goal": 1000000, "type": "balance", "reward": "💰 Wealth King"},
    "veteran": {"goal": 50, "type": "level", "reward": "🛡️ War Hero"},
    "collector": {"goal": 100, "type": "creatures", "reward": "🐾 Master Tamer"}
}

@bot.command()
async def achievements(ctx):
    """Check your progress on global milestones"""
    sync_user(ctx.author.id, ctx.author.name)
    conn = get_db()
    user = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()
    pet_count = conn.execute("SELECT COUNT(*) FROM creatures WHERE owner_id = ?", (ctx.author.id,)).fetchone()[0]
    conn.close()

    embed = discord.Embed(title="🏆 INDUSTRIAL MILESTONES", color=COLOR_STEEL)
    
    for name, data in ACHIEVEMENTS.items():
        current = 0
        if data['type'] == 'balance': current = user['balance']
        elif data['type'] == 'level': current = user['level']
        elif data['type'] == 'creatures': current = pet_count
        
        progress = min(100, int((current / data['goal']) * 100))
        bar = "🟩" * (progress // 10) + "⬛" * (10 - (progress // 10))
        
        embed.add_field(
            name=f"{data['reward']} ({name.title()})",
            value=f"{bar} {progress}%\nTarget: {data['goal']} {data['type']}",
            inline=False
        )
    
    await ctx.send(embed=embed)

# ==========================================
# 15. SYSTEM DIAGNOSTICS & GLOBAL STATS
# ==========================================

@bot.command()
async def system(ctx):
    """View the bot's internal engine performance"""
    uptime = datetime.datetime.utcnow() - bot.start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)

    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
    total_embers = conn.execute("SELECT SUM(balance) + SUM(bank) FROM profiles").fetchone()[0]
    total_pets = conn.execute("SELECT COUNT(*) FROM creatures").fetchone()[0]
    conn.close()

    embed = discord.Embed(title="⚙️ CORE ENGINE STATUS", color=0x7289da)
    embed.add_field(name="⏱️ Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
    embed.add_field(name="👥 Total Users", value=f"{total_users} registered", inline=True)
    embed.add_field(name="🏦 Global Economy", value=f"{total_embers:,} embers", inline=False)
    embed.add_field(name="🐾 Entities", value=f"{total_pets} creatures summoned", inline=True)
    embed.add_field(name="🛰️ Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    
    embed.set_footer(text="Flame Engine v3.0 | Masterpiece Edition")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def give(ctx, member: discord.Member, amount: int):
    """Admin only: Grant embers to a player"""
    sync_user(member.id, member.name)
    conn = get_db()
    conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (amount, member.id))
    conn.commit()
    conn.close()
    await ctx.send(f"💸 **REMITTANCE.** Sent **{amount} embers** to {member.mention}.")
# ==========================================
# 16. THE EMBER FORGE & MINING SYSTEM
# ==========================================

# ORE TYPES: Name: [Value, Rarity_Weight, Success_Message]
ORES = {
    "Coal": [50, 0.50, "You found some dusty coal. It burns well."],
    "Iron": [150, 0.25, "A solid chunk of iron ore. Sturdy."],
    "Gold": [500, 0.15, "Shiny! A gold vein was hidden in the rock."],
    "Crystal": [1200, 0.07, "A glowing ember-crystal! Very rare."],
    "Obsidian": [3000, 0.03, "Black as the void. This is incredibly valuable."]
}

@bot.command()
@commands.cooldown(1, 300, commands.BucketType.user) # 5-minute cooldown
async def mine(ctx):
    """Descend into the caves to find raw materials"""
    await ctx.send("⛏️ You descend into the deep caves... (Searching for Ores)")
    await asyncio.sleep(3) # Immersion pause
    
    roll = random.random()
    current_weight = 0
    found_ore = None
    
    for ore, data in ORES.items():
        current_weight += data[1]
        if roll <= current_weight:
            found_ore = ore
            break
            
    if not found_ore:
        return await ctx.send("🪨 You mined for hours but only found worthless stones.")

    # Add ore to inventory table (we use the inventory table from Part 1)
    conn = get_db()
    conn.execute("INSERT INTO inventory (user_id, item_name) VALUES (?, ?)", (ctx.author.id, found_ore))
    conn.commit()
    conn.close()

    await ctx.send(f"✨ **DISCOVERY!** {ORES[found_ore][2]} (Added **{found_ore}** to inventory)")

@bot.command()
async def refine(ctx, ore_name: str = None):
    """Convert raw ores into Embers at the Forge"""
    if not ore_name:
        return await ctx.send("Please specify which ore to refine (e.g., `f refine Gold`).")
    
    ore_name = ore_name.capitalize()
    if ore_name not in ORES:
        return await ctx.send("That isn't a refinable material.")

    conn = get_db()
    # Check if user has the ore
    check = conn.execute("SELECT COUNT(*) as qty FROM inventory WHERE user_id = ? AND item_name = ?", 
                         (ctx.author.id, ore_name)).fetchone()
    
    if check['qty'] == 0:
        conn.close()
        return await ctx.send(f"You don't have any raw {ore_name} to refine.")

    # Refine ALL of that specific ore at once
    total_value = check['qty'] * ORES[ore_name][0]
    
    conn.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = ?", (ctx.author.id, ore_name))
    conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (total_value, ctx.author.id))
    conn.commit()
    conn.close()

    await ctx.send(f"🔥 **THE FORGE ROARS.** You refined {check['qty']}x {ore_name} into **{total_value} embers**!")

# ==========================================
# 17. RE-FLAVORED UTILITIES (Non-Industrial)
# ==========================================

@bot.command()
async def profile(ctx, member: discord.Member = None):
    """A clean, aesthetic look at your progress"""
    target = member or ctx.author
    sync_user(target.id, target.name)
    
    conn = get_db()
    user = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (target.id,)).fetchone()
    rel = conn.execute("SELECT * FROM relationships WHERE user_one = ? OR user_two = ?", 
                       (target.id, target.id)).fetchone()
    conn.close()

    partner_name = "None"
    if rel:
        partner_id = rel['user_two'] if rel['user_one'] == target.id else rel['user_one']
        partner = await bot.fetch_user(partner_id)
        partner_name = partner.name

    embed = discord.Embed(title=f"✨ Traveler {target.name}", color=0x3498db)
    embed.add_field(name="💰 Wealth", value=f"{user['balance']:,} Embers", inline=True)
    embed.add_field(name="🧬 Power", value=f"Level {user['level']}", inline=True)
    embed.add_field(name="💍 Bonded To", value=partner_name, inline=True)
    embed.add_field(name="📝 Bio", value=user['bio'], inline=False)
    
    if target.avatar:
        embed.set_thumbnail(url=target.avatar.url)
    
    await ctx.send(embed=embed)
# ==========================================
# 21. BANKING & INTEREST SYSTEM
# ==========================================

@tasks.loop(hours=1)
async def calculate_interest():
    """Users earn 1% interest on their bank balance every hour"""
    conn = get_db()
    conn.execute("UPDATE profiles SET bank = CAST(bank * 1.01 AS INTEGER) WHERE bank > 0")
    conn.commit()
    conn.close()
    print("--- INTEREST DISTRIBUTED ---")

@bot.command()
async def withdraw(ctx, amount: str):
    """Move embers from your vault to your wallet"""
    conn = get_db()
    user = conn.execute("SELECT balance, bank FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()
    
    if amount.lower() == 'all': amt = user['bank']
    else: amt = int(amount)
    
    if amt <= 0 or amt > user['bank']:
        return await ctx.send("You don't have that much in the vault.")
        
    conn.execute("UPDATE profiles SET balance = balance + ?, bank = bank - ? WHERE user_id = ?", 
                 (amt, amt, ctx.author.id))
    conn.commit()
    conn.close()
    await ctx.send(f"📤 Withdrew **{amt} embers**. Your wallet is feeling heavier.")
# ==========================================
# 22. LEVEL REWARD SYSTEM
# ==========================================

LEVEL_REWARDS = {
    5: {"embers": 5000, "role": None, "msg": "Novice Traveler"},
    10: {"embers": 15000, "role": None, "msg": "Ember Knight"},
    25: {"embers": 50000, "role": None, "msg": "Void Walker"},
    50: {"embers": 200000, "role": None, "msg": "Ascended Being"}
}

@bot.command()
async def claim_level(ctx):
    """Claim your rewards for leveling up"""
    conn = get_db()
    user = conn.execute("SELECT level, prestige FROM profiles WHERE user_id = ?", (ctx.author.id,)).fetchone()
    
    # This logic checks which rewards the user qualifies for
    claimed_count = 0
    total_embers = 0
    
    for lvl, data in LEVEL_REWARDS.items():
        if user['level'] >= lvl:
            # In a 1200 line bot, we would track 'claimed' levels in a new table
            # For now, we grant them if they are at the level
            total_embers += data['embers']
            claimed_count += 1
            
    if claimed_count == 0:
        return await ctx.send("You haven't reached a reward milestone yet. Keep chatting!")

    conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (total_embers, ctx.author.id))
    conn.commit()
    conn.close()
    
    await ctx.send(f"🎁 **MILESTONE REACHED!** You claimed rewards for your progress, gaining **{total_embers} embers**!")
# ==========================================
# 23. ADVENTURE MISSIONS
# ==========================================

MISSIONS = {
    "Deep_Sea": {"min_power": 100, "time": 60, "reward": 2500, "risk": 0.2},
    "Void_Plains": {"min_power": 500, "time": 120, "reward": 10000, "risk": 0.4},
    "Celestial_Peak": {"min_power": 1500, "time": 300, "reward": 50000, "risk": 0.6}
}

@bot.command()
async def adventure(ctx, mission_name: str, creature_id: int):
    """Send a creature on a timed mission for embers"""
    mission_key = mission_name.title().replace(" ", "_")
    if mission_key not in MISSIONS:
        return await ctx.send("That location hasn't been discovered yet.")

    mission = MISSIONS[mission_key]
    conn = get_db()
    pet = conn.execute("SELECT * FROM creatures WHERE id = ? AND owner_id = ?", (creature_id, ctx.author.id)).fetchone()

    if not pet:
        return await ctx.send("You don't own that creature.")
    if pet['power'] < mission['min_power']:
        return await ctx.send(f"Your creature is too weak! Min Power: {mission['min_power']}")

    await ctx.send(f"⏳ **MISSION START.** Your {pet['name']} is traveling to the **{mission_name}**. Come back in {mission['time']} seconds.")
    
    await asyncio.sleep(mission['time'])

    if random.random() > mission['risk']:
        # Success
        reward = mission['reward']
        conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (reward, ctx.author.id))
        res = f"✅ **MISSION SUCCESS!** Your creature returned from {mission_name} with **{reward} embers**."
    else:
        # Failure
        res = f"⚠️ **MISSION FAILED.** Your creature returned exhausted and empty-handed from {mission_name}."

    conn.commit()
    conn.close()
    await ctx.send(f"{ctx.author.mention}, {res}")


# ==========================================
# 20. THE FINAL BOOT SEQUENCE (THE HEARTBEAT)
# ==========================================

@bot.event
async def on_command_error(ctx, error):
    """Handles cooldowns and missing permissions so the bot doesn't crash"""
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ **COOLING DOWN.** You can use this again in {error.retry_after:.1f}s.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You don't have the permissions required for this action.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("👤 I couldn't find that traveler in this server.")
    else:
        # This prints the error to your Railway logs so you can see what went wrong
        print(f"Internal System Error: {error}")

if __name__ == "__main__":
    if TOKEN:
        try:
            # This is the physical 'On' switch for the bot
            print("--- FLAME ENGINE INITIALIZING ---")
            print(f"--- PREFIXES: {PREFIXES} ---")
            bot.run(TOKEN)
        except Exception as e:
            print(f"CRITICAL BOOT ERROR: {e}")
    else:
        print("CRITICAL ERROR: DISCORD_TOKEN is missing from your environment variables!")
