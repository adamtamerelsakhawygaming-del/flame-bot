import discord

from discord.ext import commands

import sqlite3

import random

import asyncio

from datetime import datetime


==========================================

CONFIGURATION

==========================================

TOKEN = "MTUwMzMwODQyNjk4NDQyNzYwMQ.GZsc6i.HSF3YhBlbUs8vNw0zkgfmLqI0R_13KrNSjFsG0"

PREFIXES = ["flame ", "f "]

OWNER_ID = "justaflamewithfragz"

DATABASE = "flame_main.db"

CURRENCY = "embers"


Custom Emojis (Optional: Replace with your own IDs or keep as text)

E_SUCCESS = "●"

E_ERROR = "×"


Intents setup for a professional bot

intents = discord.Intents.default()

intents.members = True

intents.message_content = True


bot = commands.Bot(command_prefix=PREFIXES, intents=intents, help_command=None)


==========================================

DATABASE INITIALIZATION

==========================================

def get_db():

conn = sqlite3.connect(DATABASE)

conn.row_factory = sqlite3.Row

return conn


def initialize_db():

conn = get_db()

c = conn.cursor()


# User Profiles: Now includes Bio and Custom Color

c.execute("""CREATE TABLE IF NOT EXISTS profiles (

user_id INTEGER PRIMARY KEY,

username TEXT,

balance INTEGER DEFAULT 1000,

xp INTEGER DEFAULT 0,

level INTEGER DEFAULT 1,

prestige INTEGER DEFAULT 0,

bio TEXT DEFAULT 'No bio set.',

profile_color TEXT DEFAULT '#2b2d31'

)""")


# Global Inventory

c.execute("""CREATE TABLE IF NOT EXISTS inventory (

item_id INTEGER PRIMARY KEY AUTOINCREMENT,

owner_id INTEGER,

item_name TEXT,

item_type TEXT

)""")


# Global Marketplace

c.execute("""CREATE TABLE IF NOT EXISTS marketplace (

list_id INTEGER PRIMARY KEY AUTOINCREMENT,

seller_id INTEGER,

item_id INTEGER,

item_name TEXT,

price INTEGER

)""")


# Role Rewards (For Part 3)

c.execute("""CREATE TABLE IF NOT EXISTS role_rewards (

guild_id INTEGER,

level INTEGER,

role_id INTEGER,

PRIMARY KEY (guild_id, level)

)""")


conn.commit()

conn.close()


==========================================

CORE UTILITIES

==========================================

def sync_profile(user_id, username):

conn = get_db()

c = conn.cursor()

c.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))

user = c.fetchone()


if not user:

c.execute("INSERT INTO profiles (user_id, username) VALUES (?, ?)", (user_id, username))

conn.commit()

c.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))

user = c.fetchone()


conn.close()

return dict(user)


def update_profile(user_id, **kwargs):

conn = get_db()

c = conn.cursor()

fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])

values = list(kwargs.values())

values.append(user_id)

c.execute(f"UPDATE profiles SET {fields} WHERE user_id = ?", values)

conn.commit()

conn.close()


def is_owner():

async def predicate(ctx):

return ctx.author.name == OWNER_ID

return commands.check(predicate)


==========================================

ADMIN TOOLKIT (CURRENCY MANAGEMENT)

==========================================

@bot.command(name="add")

@is_owner()

async def admin_add(ctx, amount: int, member: discord.Member):

"""Owner only: Add embers to a user."""

u = sync_profile(member.id, member.name)

update_profile(member.id, balance=u['balance'] + amount)

await ctx.send(f"{E_SUCCESS} SUCCESS: Added {amount} {CURRENCY} to {member.display_name}.")


@bot.command(name="remove")

@is_owner()

async def admin_remove(ctx, amount: int, member: discord.Member):

"""Owner only: Take embers from a user."""

u = sync_profile(member.id, member.name)

new_bal = max(0, u['balance'] - amount)

update_profile(member.id, balance=new_bal)

await ctx.send(f"{E_SUCCESS} SUCCESS: Removed {amount} {CURRENCY} from {member.display_name}.")


@bot.command(name="set")

@is_owner()

async def admin_set(ctx, amount: int, member: discord.Member):

"""Owner only: Set a user's exact ember balance."""

sync_profile(member.id, member.name)

update_profile(member.id, balance=amount)

await ctx.send(f"{E_SUCCESS} SUCCESS: {member.display_name} is now at {amount} {CURRENCY}.")


==========================================

BOOT SEQUENCE

==========================================

@bot.event

async def on_ready():

initialize_db()

print(f"--- FLAME CORE ONLINE ---")

print(f"Logged in as: {bot.user.name}")

print(f"Authorized Owner: {OWNER_ID}")

print(f"Currency: {CURRENCY}")

print(f"-------------------------")


RUN BOT (Uncomment when ready)

bot.run(TOKEN)


==========================================

SECTION 7: THE ITEM POOL (NORMAL ASSETS)

==========================================

Everyday items used for trading and the market.

ITEM_POOL = {

"Common": ["Vintage T-Shirt", "Leather Wallet", "Coffee Mug", "Poster", "Basic Beanie"],

"Uncommon": ["Film Camera", "Vinyl Record", "Graphic Hoodie", "Silver Chain", "Retro Hat"],

"Rare": ["Digital Camera", "Gold Watch", "Electric Guitar", "Designer Sneakers", "Skateboard"],

"Exotic": ["Luxury Watch", "Electric Bike", "Signed Jersey", "Diamond Earrings"]

}


The System Shop (Account Upgrades)

SYSTEM_SHOP = {

"bio": {"name": "Profile Bio", "price": 5000, "desc": "Unlocks the ability to write a bio on your profile."},

"color": {"name": "Custom Color", "price": 10000, "desc": "Allows you to change your profile's accent color."},

"tag": {"name": "Market Badge", "price": 25000, "desc": "Adds a 'Verified' checkmark to your profile."},

"reset": {"name": "Reset Reputation", "price": 1000, "desc": "Clears all your Aura points back to zero."}

}


==========================================

SECTION 8: THE GLOBAL LOTTERY (OWO STYLE)

==========================================

JACKPOT_POOL = 10000


@bot.command(name="lottery", aliases=["lotto"])

async def lottery_command(ctx, tickets: int = None):

"""Check the jackpot or buy tickets (100 embers each)."""

global JACKPOT_POOL

u = sync_profile(ctx.author.id, ctx.author.name)


if tickets is None:

return await ctx.send(f"{E_SUCCESS} CURRENT JACKPOT:{JACKPOT_POOL} {CURRENCY}\n» Buy tickets with f lottery [amount].")


cost = tickets * 100

if u['balance'] < cost:

return await ctx.send(f"{E_ERROR} You need {cost} {CURRENCY} for these tickets.")


JACKPOT_POOL += cost

update_profile(ctx.author.id, balance=u['balance'] - cost)


# 0.5% chance per ticket to win it all instantly

win_chance = 0.005 * tickets

if random.random() < win_chance:

winnings = JACKPOT_POOL

JACKPOT_POOL = 10000

update_profile(ctx.author.id, balance=u['balance'] + winnings)

await ctx.send(f"🎊 JACKPOT! {ctx.author.mention} just won the {winnings} {CURRENCY} pool!")

else:

await ctx.send(f"{E_SUCCESS} Tickets bought. The jackpot is now {JACKPOT_POOL}.")


==========================================

SECTION 9: THE SYSTEM SHOP

==========================================

@bot.command(name="shop")

async def show_shop(ctx):

"""List available account upgrades."""

embed = discord.Embed(title="● SYSTEM SHOP", color=0x2b2d31)

for key, item in SYSTEM_SHOP.items():

embed.add_field(

name=f"{item['name']} (f buy {key})",

value=f"Price: {item['price']} {CURRENCY}\n{item['desc']}",

inline=False

)

await ctx.send(embed=embed)


@bot.command(name="buy")

async def purchase_from_shop(ctx, item_key: str):

"""Buy an account upgrade using embers."""

u = sync_profile(ctx.author.id, ctx.author.name)

item = SYSTEM_SHOP.get(item_key.lower())


if not item:

return await ctx.send(f"{E_ERROR} Item {item_key} isn't in the shop.")


if u['balance'] < item['price']:

return await ctx.send(f"{E_ERROR} You don't have enough {CURRENCY}.")


update_profile(ctx.author.id, balance=u['balance'] - item['price'])


conn = get_db()

c = conn.cursor()

c.execute("INSERT INTO inventory (owner_id, item_name, item_type) VALUES (?, ?, ?)",

(ctx.author.id, item['name'], "Upgrade"))

conn.commit()

conn.close()


await ctx.send(f"{E_SUCCESS} PURCHASED: You now own the {item['name']}.")


==========================================

SECTION 10: PROFILE CUSTOMIZATION

==========================================

@bot.command(name="setbio")

async def update_bio(ctx, *, text: str):

"""Set your global profile bio."""

if len(text) > 100:

return await ctx.send(f"{E_ERROR} Keep it under 100 characters.")


update_profile(ctx.author.id, bio=text)

await ctx.send(f"{E_SUCCESS} UPDATED: Your bio has been saved.")


@bot.command(name="setcolor")

async def update_color(ctx, hex_code: str):

"""Change the color of your profile cards."""

if not hex_code.startswith("#") or len(hex_code) != 7:

return await ctx.send(f"{E_ERROR} Use a valid hex code (like #ff0000).")


update_profile(ctx.author.id, profile_color=hex_code)

await ctx.send(f"{E_SUCCESS} UPDATED: Profile color set to {hex_code}.")


==========================================

SECTION 11: FINDING ITEMS (SCOUT)

==========================================

@bot.command(name="scout")

@commands.cooldown(1, 30, commands.BucketType.user)

async def find_items(ctx):

"""Search for items to keep or sell on the market."""

sync_profile(ctx.author.id, ctx.author.name)


roll = random.random()

if roll < 0.03: rarity = "Exotic"

elif roll < 0.12: rarity = "Rare"

elif roll < 0.35: rarity = "Uncommon"

else: rarity = "Common"


item = random.choice(ITEM_POOL[rarity])


conn = get_db()

c = conn.cursor()

c.execute("INSERT INTO inventory (owner_id, item_name, item_type) VALUES (?, ?, ?)",

(ctx.author.id, item, rarity))

conn.commit()

conn.close()


await ctx.send(f"{E_SUCCESS} FOUND: You got a {item} ({rarity}).")


==========================================

SECTION 12: THE LEVELING ENGINE (PASSIVE)

==========================================


@bot.event

async def on_message(message):

"""Monitors activity and distributes Embers/XP/Roles."""

if message.author.bot or not message.guild:

return


# Sync profile and handle XP

u = sync_profile(message.author.id, message.author.name)


# Static XP/Ember gain per message (No cooldown)

xp_gain = random.randint(15, 25)

ember_gain = random.randint(5, 10)


new_xp = u['xp'] + xp_gain

needed_xp = u['level'] * 300


if new_xp >= needed_xp:

new_lvl = u['level'] + 1

update_profile(message.author.id, xp=0, level=new_lvl, balance=u['balance'] + ember_gain)


# Level Up Notification

await message.channel.send(f"⚡ LEVEL UP | {message.author.mention} reached level {new_lvl}.")


# Check for Role Rewards in this specific server

conn = get_db()

c = conn.cursor()

c.execute("SELECT role_id FROM role_rewards WHERE guild_id = ? AND level = ?",

(message.guild.id, new_lvl))

reward = c.fetchone()

conn.close()


if reward:

role = message.guild.get_role(reward['role_id'])

if role:

try:

await message.author.add_roles(role)

await message.channel.send(f"● ROLE GRANTED:{role.name} is now assigned.")

except discord.Forbidden:

pass # Silently fail if permissions are missing

else:

update_profile(message.author.id, xp=new_xp, balance=u['balance'] + ember_gain)


# CRITICAL: Allow other commands to run

await bot.process_commands(message)


==========================================

SECTION 13: ROLE DASHBOARD (MANAGEMENT)

==========================================


@bot.group(name="dashboard", aliases=["db", "rewards"], invoke_without_command=True)

@commands.has_permissions(manage_roles=True)

async def dashboard_group(ctx):

"""View the level-role rewards for this server."""

conn = get_db()

c = conn.cursor()

c.execute("SELECT level, role_id FROM role_rewards WHERE guild_id = ? ORDER BY level ASC",

(ctx.guild.id,))

rows = c.fetchall()

conn.close()


embed = discord.Embed(title="◈ SERVER ROLE REWARDS", color=0x2b2d31)

if not rows:

embed.description = "No rewards configured. Use f dashboard add [level] [@role]"

else:

for row in rows:

role = ctx.guild.get_role(row['role_id'])

role_str = role.mention if role else f"Unknown ID: {row['role_id']}"

embed.add_field(name=f"Level {row['level']}", value=role_str, inline=False)


await ctx.send(embed=embed)


@dashboard_group.command(name="add")

@commands.has_permissions(manage_roles=True)

async def dashboard_add(ctx, level: int, role: discord.Role):

"""Link a Discord role to a specific level."""

conn = get_db()

c = conn.cursor()

c.execute("INSERT OR REPLACE INTO role_rewards (guild_id, level, role_id) VALUES (?, ?, ?)",

(ctx.guild.id, level, role.id))

conn.commit()

conn.close()

await ctx.send(f"{E_SUCCESS} LINKED: Reaching level {level} now grants {role.name}.")


==========================================

SECTION 14: ENHANCED PROFILE CARD

==========================================


@bot.command(name="profile", aliases=["p"])

async def show_profile(ctx, member: discord.Member = None):

"""View status, embers, and your custom bio."""

target = member or ctx.author

u = sync_profile(target.id, target.name)


conn = get_db()

c = conn.cursor()

c.execute("SELECT COUNT(*) FROM inventory WHERE owner_id = ?", (target.id,))

item_count = c.fetchone()[0]

conn.close()


# Convert hex to integer for embed color

color_hex = u['profile_color'].replace("#", "")

embed_color = int(color_hex, 16)


embed = discord.Embed(title=f"◈ PROFILE: {target.display_name}", color=embed_color)

embed.description = u['bio']


embed.add_field(name="Statistics", value=f"Level: {u['level']}\n{CURRENCY.title()}: {u['balance']}", inline=True)

embed.add_field(name="Assets", value=f"Inventory: {item_count}\nReputation: {u['prestige']}", inline=True)


# Progress Bar (XP)

progress = int((u['xp'] / (u['level'] * 300)) * 10)

bar = "▰" * progress + "▱" * (10 - progress)

embed.add_field(name="Level Progress", value=f"{bar} ({u['xp']}/{u['level']*300} XP)", inline=False)


await ctx.send(embed=embed)


@bot.command(name="top", aliases=["lb"])

async def leaderboard(ctx):

"""See the top 10 richest users across all servers."""

conn = get_db()

c = conn.cursor()

c.execute("SELECT username, balance FROM profiles ORDER BY balance DESC LIMIT 10")

rows = c.fetchall()

conn.close()


desc = ""

for i, row in enumerate(rows, 1):

desc += f"{i}. {row['username']} — {row['balance']} {CURRENCY}\n"


embed = discord.Embed(title=f"◈ GLOBAL {CURRENCY.upper()} LEADERBOARD", description=desc or "No data available.", color=0x2b2d31)

await ctx.send(embed=embed)


==========================================

SECTION 15: GLOBAL TRANSFERS

==========================================


@bot.command(name="pay", aliases=["send", "transfer"])

async def transfer_embers(ctx, member: discord.Member, amount: int):

"""Send embers to another user globally."""

if member.id == ctx.author.id:

return await ctx.send(f"{E_ERROR} You cannot send {CURRENCY} to yourself.")


if amount <= 0:

return await ctx.send(f"{E_ERROR} You must send a positive amount.")


sender = sync_profile(ctx.author.id, ctx.author.name)

if sender['balance'] < amount:

return await ctx.send(f"{E_ERROR} You don't have enough {CURRENCY}.")


receiver = sync_profile(member.id, member.name)


# Execute transaction

update_profile(ctx.author.id, balance=sender['balance'] - amount)

update_profile(member.id, balance=receiver['balance'] + amount)


await ctx.send(f"{E_SUCCESS} Transaction Complete: Sent {amount} {CURRENCY} to {member.name}.")


==========================================

SECTION 16: REPUTATION (AURA) SYSTEM

==========================================


@bot.command(name="vouch", aliases=["rep"])

@commands.cooldown(1, 3600, commands.BucketType.user)

async def vouch_user(ctx, member: discord.Member):

"""Give a user +1 Reputation (Aura). 1-hour cooldown."""

if member.id == ctx.author.id:

return await ctx.send(f"{E_ERROR} You cannot vouch for yourself.")


target = sync_profile(member.id, member.name)

new_aura = target['prestige'] + 1

update_profile(member.id, prestige=new_aura)


await ctx.send(f"{E_SUCCESS} Vouch Recorded: {member.mention} now has {new_aura} Aura.")


==========================================

SECTION 17: BLACKJACK ENGINE

==========================================


@bot.command(name="blackjack", aliases=["bj"])

async def blackjack_game(ctx, amount: str):

"""Bet your embers in a game of Blackjack."""

u = sync_profile(ctx.author.id, ctx.author.name)


if amount.lower() == "all":

bet = u['balance']

else:

try: bet = int(amount)

except: return await ctx.send(f"{E_ERROR} Enter a valid number or 'all'.")


if bet > u['balance'] or bet <= 0:

return await ctx.send(f"{E_ERROR} You don't have enough {CURRENCY}.")


# Deck Setup

deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4

random.shuffle(deck)


p_hand = [deck.pop(), deck.pop()]

d_hand = [deck.pop(), deck.pop()]


def calc(hand):

v = sum(hand)

if v > 21 and 11 in hand:

hand.remove(11)

hand.append(1)

return sum(hand)

return v


async def draw_table(status="Playing"):

color = 0x2b2d31 if status == "Playing" else (0x44ff44 if "WIN" in status else 0xff4444)

emb = discord.Embed(title="◈ BLACKJACK TABLE", color=color)

emb.add_field(name="Your Hand", value=f"Cards: {p_hand}\nTotal: {calc(p_hand)}", inline=True)


# Dealer's second card is hidden until the end

d_val = [d_hand[0], "??"] if status == "Playing" else d_hand

emb.add_field(name="Dealer Hand", value=f"Cards: {d_val}\nTotal: {calc(d_hand) if status != 'Playing' else '??'}", inline=True)

emb.set_footer(text=f"Bet: {bet} {CURRENCY} | Status: {status}")

return emb


msg = await ctx.send(embed=await draw_table())


# Player Turn

while calc(p_hand) < 21:

await ctx.send("Type hit or stand.", delete_after=10)

try:

m = await bot.wait_for('message', timeout=30.0,

check=lambda m: m.author == ctx.author and m.content.lower() in ['hit', 'stand'])

if m.content.lower() == 'hit':

p_hand.append(deck.pop())

await msg.edit(embed=await draw_table())

if calc(p_hand) > 21: break

else: break

except asyncio.TimeoutError: break


p_total = calc(p_hand)

if p_total > 21:

update_profile(ctx.author.id, balance=u['balance'] - bet)

return await msg.edit(embed=await draw_table("BUST - You lost."))


# Dealer Turn

while calc(d_hand) < 17:

d_hand.append(deck.pop())


d_total = calc(d_hand)


# Results

if d_total > 21 or p_total > d_total:

update_profile(ctx.author.id, balance=u['balance'] + bet)

await msg.edit(embed=await draw_table("WIN - Payout received!"))

elif p_total == d_total:

await msg.edit(embed=await draw_table("PUSH - Embers returned."))

else:

update_profile(ctx.author.id, balance=u['balance'] - bet)

await msg.edit(embed=await draw_table("LOSS - Dealer wins."))


==========================================

SECTION 18: THE MASTER LOGGER

==========================================

def log_action(user_id, username, action, detail):

"""Internal system to log high-value events to the console."""

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

log_entry = f"[{timestamp}] ID: {user_id} | {username} | {action.upper()}: {detail}"


# Prints to your hosting console (Railway/Local)

print(log_entry)


# Optional: Saves to a local file

with open("system_logs.txt", "a") as f:

f.write(log_entry + "\n")


==========================================

SECTION 19: BROADCAST (GLOBAL ANNOUNCER)

==========================================

@bot.command(name="broadcast", aliases=["gb"])

@is_owner()

async def global_broadcast(ctx, *, message: str):

"""Owner only: Sends a message to all connected servers."""

success = 0

failed = 0


for guild in bot.guilds:

# Attempts to find the most active/relevant channel

target = next((ch for ch in guild.text_channels if "bot" in ch.name or "gen" in ch.name), guild.text_channels[0])

try:

await target.send(f"● GLOBAL ANNOUNCEMENT ●\n{message}")

success += 1

except:

failed += 1

continue


await ctx.send(f"{E_SUCCESS} Broadcast delivered to {success} servers. Failed in {failed}.")

log_action(ctx.author.id, ctx.author.name, "broadcast", f"Msg: {message[:25]}...")


==========================================

SECTION 20: THE WIPE SYSTEM

==========================================

@bot.command(name="wipe")

@is_owner()

async def wipe_user_data(ctx, member: discord.Member, *, reason: str):

"""Owner only: Resets a user's entire profile and inventory."""

# Ensure they exist in DB before wiping

sync_profile(member.id, member.name)


conn = get_db()

c = conn.cursor()


# Delete from all primary tables

c.execute("DELETE FROM profiles WHERE user_id = ?", (member.id,))

c.execute("DELETE FROM inventory WHERE owner_id = ?", (member.id,))

c.execute("DELETE FROM marketplace WHERE seller_id = ?", (member.id,))


conn.commit()

conn.close()


log_action(ctx.author.id, ctx.author.name, "wipe", f"Target: {member.name} | Reason: {reason}")


embed = discord.Embed(title="● SYSTEM DATA WIPE", color=0xff4444)

embed.add_field(name="Target", value=member.mention, inline=True)

embed.add_field(name="Reason", value=reason, inline=True)

embed.set_footer(text="User data has been purged from the global database.")


await ctx.send(embed=embed)


==========================================

SECTION 21: GLOBAL ERROR SHIELD

==========================================

@bot.event

async def on_command_error(ctx, error):

"""Catches errors to keep the bot from crashing."""


if isinstance(error, commands.CommandOnCooldown):

await ctx.send(f"{E_ERROR} Cooldown: System recalibrating. Wait {error.retry_after:.1f}s.")


elif isinstance(error, commands.MissingPermissions):

await ctx.send(f"{E_ERROR} Access Denied: You don't have permission for this.")


elif isinstance(error, commands.CheckFailure):

# Triggered by @is_owner()

await ctx.send(f"{E_ERROR} Restricted: Owner Authorization Required.")


elif isinstance(error, commands.MemberNotFound):

await ctx.send(f"{E_ERROR} Logic Error: Target user could not be found.")


else:

# Logs the error to you so you can fix bugs silently

log_action("CORE", "SYSTEM", "CRITICAL_ERROR", str(error))

print(f"DEBUG ERROR: {error}")


==========================================

SECTION 22: SYSTEM DIAGNOSTICS

==========================================

@bot.command(name="sys", aliases=["stats"])

async def system_stats(ctx):

"""View bot health and database stats."""

conn = get_db()

c = conn.cursor()

c.execute("SELECT COUNT() FROM profiles")

users = c.fetchone()[0]

c.execute("SELECT COUNT() FROM marketplace")

market = c.fetchone()[0]

conn.close()


embed = discord.Embed(title="◈ FLAME SYSTEM STATUS", color=0x2b2d31)

embed.add_field(name="Total Users", value=f"{users}", inline=True)

embed.add_field(name="Market Listings", value=f"{market}", inline=True)

embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)

embed.set_footer(text=f"Authorized Node: {OWNER_ID}")


await ctx.send(embed=embed)


==========================================

FINAL EXECUTION

==========================================

bot.run(TOKEN)
