import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIXES = ["flame ", "f "]
OWNER_ID = "justaflamewithfragz" # Replace with your actual ID if needed
DATABASE = "flame_main.db"
CURRENCY = "embers"

# Emojis for the Industrial Aesthetic
E_SUCCESS = "✔️"
E_ERROR = "❌"
E_WARNING = "⚠️"

# Intents setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Initialize Bot
bot = commands.Bot(command_prefix=PREFIXES, intents=intents, help_command=None)
# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    conn = get_db()
    c = conn.cursor()
    
    # Global Profiles: Tracks levels, balance, and bio
    c.execute("""CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance INTEGER DEFAULT 1000,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        prestige INTEGER DEFAULT 0,
        bio TEXT DEFAULT 'No bio set.'
    )""")
    
    # Player Inventories
    c.execute("""CREATE TABLE IF NOT EXISTS inventory (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER,
        item_name TEXT,
        item_type TEXT
    )""")

    conn.commit()
    conn.close()
    print("--- DATABASE READY ---")
# ==========================================
# CORE EVENTS
# ==========================================

@bot.event
async def on_ready():
    # This runs the database setup we just wrote
    initialize_db()
    
    # Industrial-themed status
    await bot.change_presence(activity=discord.Game(name="CORE // BOOTING"))
    
    print(f"--- FLAME CORE ONLINE ---")
    print(f"Logged in as: {bot.user.name}")
    print(f"Latency: {round(bot.latency * 1000)}ms")

# ==========================================
# CORE UTILITIES
# ==========================================

def sync_profile(user_id, username):
    """Ensures a user exists in the database before doing anything"""
    conn = get_db()
    user = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    
    if not user:
        conn.execute("INSERT INTO profiles (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
    conn.close()
# ==========================================
# ECONOMY & PROFILES
# ==========================================

@bot.command(name="profile", aliases=["p"])
async def profile(ctx, member: discord.Member = None):
    """View industrial stats and balance"""
    target = member or ctx.author
    sync_profile(target.id, target.name)
    
    conn = get_db()
    user = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (target.id,)).fetchone()
    conn.close()

    embed = discord.Embed(
        title=f"PROTOTYPE PROFILE // {target.display_name}",
        description=f"Status: **Active**\nBio: {user['bio']}",
        color=0xff4500 # Safety Orange
    )
    embed.add_field(name="LEVEL", value=f"LVL {user['level']}", inline=True)
    embed.add_field(name="CURRENCY", value=f"{user['balance']} {CURRENCY}", inline=True)
    embed.add_field(name="XP", value=f"{user['xp']}", inline=True)
    
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    """Claim your daily resource allocation"""
    sync_profile(ctx.author.id, ctx.author.name)
    
    reward = 500
    conn = get_db()
    conn.execute("UPDATE profiles SET balance = balance + ? WHERE user_id = ?", (reward, ctx.author.id))
    conn.commit()
    conn.close()
    
    await ctx.send(f"{E_SUCCESS} | **RESOURCE ALLOCATION SUCCESSFUL.** +{reward} {CURRENCY} added to your core.")

@daily.error
async def daily_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        hours = int(error.retry_after // 3600)
        minutes = int((error.retry_after % 3600) // 60)
        await ctx.send(f"{E_ERROR} | **SYSTEM COOLING.** Try again in {hours}h {minutes}m.")
# ==========================================
# FINAL EXECUTION
# ==========================================

@bot.command()
async def ping(ctx):
    """Check system latency"""
    await ctx.send(f"**PONG.** Latency: {round(bot.latency * 1000)}ms")

if __name__ == "__main__":
    if TOKEN:
        try:
            print("--- ATTEMPTING CONNECTION ---")
            bot.run(TOKEN)
        except discord.errors.LoginFailure:
            print("ERROR: Invalid Token. Check your Railway Variables.")
        except Exception as e:
            print(f"ERROR: {e}")
    else:
        print("CRITICAL ERROR: DISCORD_TOKEN not found in environment.")
