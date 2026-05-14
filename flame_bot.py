import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta

# ── CONFIG ──
OWNER_ID = 1444293963812180120
BOT_PREFIXES = ("f ", "flame ")
DATA_DIR = "./bot_data"

# ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def get_user_path(user_id):
  return os.path.join(DATA_DIR, f"{user_id}.json")

def load_user(user_id):
  path = get_user_path(user_id)
  if os.path.exists(path):
    with open(path, "r") as f:
      return json.load(f)
  return {
    "embers": 0,
    "daily_streak": 0,
    "last_daily": None,
    "loan": 0,
    "loan_due": None,
    "creatures": [],
    "married_to": None,
    "inventory": [],
    "xp": 0,
    "level": 1,
    "wins": 0,
    "losses": 0,
    "cooldowns": {}
  }

def save_user(user_id, data):
  path = get_user_path(user_id)
  with open(path, "w") as f:
    json.dump(data, f, indent=2)

def get_all_user_ids():
  files = os.listdir(DATA_DIR)
  return [int(f.replace(".json", "")) for f in files if f.endswith(".json")]

# ── CUSTOM CHECKS ──
def is_owner():
  async def predicate(ctx):
    if ctx.author.id != OWNER_ID:
      await ctx.send("nah you can't use this command as ur not the bot owner")
      return False
    return True
  return commands.check(predicate)

def has_mod_perms():
  async def predicate(ctx):
    if ctx.author.id == OWNER_ID:
      return True
    if ctx.author.guild_permissions.kick_members or ctx.author.guild_permissions.ban_members or ctx.author.guild_permissions.manage_messages or ctx.author.guild_permissions.manage_roles:
      return True
    await ctx.send("bruh you dont have mod perms for this")
    return False
  return commands.check(predicate)

# ── BOT SETUP ──
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class FlameBot(commands.Bot):
  def __init__(self):
    super().__init__(
      command_prefix=BOT_PREFIXES,
      intents=intents,
      case_insensitive=True,
      help_command=None
    )

  async def on_ready(self):
    print(f"flame bot is online as {self.user}")
    await self.change_presence(activity=discord.Game(name="f help | flame help"))

bot = FlameBot()

# ── ERROR HANDLER ──
@bot.event
async def on_command_error(ctx, error):
  if isinstance(error, commands.CommandNotFound):
    return
  if isinstance(error, commands.MissingRequiredArgument):
    await ctx.send("bro youre missing some arguments, try f help")
    return
  if isinstance(error, commands.BadArgument):
    await ctx.send("that argument doesnt look right my guy")
    return
  if isinstance(error, commands.CheckFailure):
    return
  print(f"error: {error}")

# ── ECONOMY COMMANDS (from picture) ──

@bot.command()
async def embers(ctx):
  """check your ember balance"""
  data = load_user(ctx.author.id)
  bal = data["embers"]
  responses = [
    f"you got **{bal}** embers. not bad i guess 🔥",
    f"**{bal}** embers in the bank. spend em wisely 💰",
    f"youre sitting on **{bal}** embers. baller status?",
    f"**{bal}** embers. dont blow it all in one place 😏"
  ]
  await ctx.send(random.choice(responses))

@bot.command()
async def daily(ctx):
  """claim your daily embers"""
  data = load_user(ctx.author.id)
  now = datetime.utcnow()

  if data["last_daily"]:
    last = datetime.fromisoformat(data["last_daily"])
    if now - last < timedelta(hours=24):
      remaining = timedelta(hours=24) - (now - last)
      hours = int(remaining.total_seconds() // 3600)
      mins = int((remaining.total_seconds() % 3600) // 60)
      await ctx.send(f"chill bro, come back in **{hours}h {mins}m** for your next daily ⏰")
      return
    elif now - last < timedelta(hours=48):
      data["daily_streak"] += 1
    else:
      data["daily_streak"] = 1
  else:
    data["daily_streak"] = 1

  base = 500
  streak_bonus = min(data["daily_streak"] * 50, 1000)
  total = base + streak_bonus

  data["embers"] += total
  data["last_daily"] = now.isoformat()
  save_user(ctx.author.id, data)

  streak_msg = f"streak: **{data['daily_streak']}** 🔥" if data["daily_streak"] > 1 else ""
  await ctx.send(f"heres your **{total}** embers! {streak_msg} come back tomorrow for more 💰")

@bot.command()
async def streak(ctx):
  """check your daily streak"""
  data = load_user(ctx.author.id)
  streak = data["daily_streak"]
  if streak == 0:
    await ctx.send("you dont even have a streak yet bro, do f daily")
  else:
    await ctx.send(f"youre on a **{streak}** day streak! keep it going 🔥")

@bot.command()
async def beg(ctx):
  """beg for some embers"""
  data = load_user(ctx.author.id)
  cd_key = "beg"
  now = datetime.utcnow()

  if cd_key in data["cooldowns"]:
    last = datetime.fromisoformat(data["cooldowns"][cd_key])
    if now - last < timedelta(minutes=2):
      await ctx.send("bro you just begged, give it a minute")
      return

  data["cooldowns"][cd_key] = now.isoformat()

  outcomes = [
    ("a random npc felt bad and gave you", random.randint(10, 100)),
    ("someone dropped", random.randint(5, 50)),
    ("you found", random.randint(1, 30)),
    ("a rich dude tossed you", random.randint(50, 200)),
    ("you got absolutely nothing lmao", 0),
    ("someone laughed at you and threw", random.randint(1, 5)),
  ]

  msg, amount = random.choice(outcomes)
  data["embers"] += amount
  save_user(ctx.author.id, data)

  if amount == 0:
    await ctx.send(f"{msg}")
  else:
    await ctx.send(f"{msg} **{amount}** embers")

@bot.command()
async def scam(ctx, target: discord.Member = None):
  """try to scam someone for embers"""
  if not target or target == ctx.author:
    await ctx.send("you cant scam yourself bro thats just sad")
    return

  data = load_user(ctx.author.id)
  target_data = load_user(target.id)

  if target_data["embers"] < 50:
    await ctx.send(f"{target.display_name} is broke af, not worth scamming")
    return

  success = random.random() < 0.4
  if success:
    amount = random.randint(50, min(500, target_data["embers"]))
    data["embers"] += amount
    target_data["embers"] -= amount
    save_user(ctx.author.id, data)
    save_user(target.id, target_data)
    await ctx.send(f"you successfully scammed **{amount}** embers from {target.display_name}! youre going to hell for this 😈")
  else:
    fine = random.randint(20, 100)
    data["embers"] = max(0, data["embers"] - fine)
    save_user(ctx.author.id, data)
    await ctx.send(f"you got caught scamming and paid a **{fine}** ember fine. crime doesnt pay")

@bot.command()
async def invest(ctx, amount: int = None):
  """invest your embers (risky)"""
  if not amount or amount <= 0:
    await ctx.send("how much you tryna invest bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers, cant invest **{amount}**")
    return

  data["embers"] -= amount

  roll = random.random()
  if roll < 0.3:
    loss = amount
    save_user(ctx.author.id, data)
    await ctx.send(f"the market crashed and you lost all **{loss}** embers. shoulda bought crypto instead")
  elif roll < 0.6:
    profit = int(amount * random.uniform(0.1, 0.5))
    data["embers"] += amount + profit
    save_user(ctx.author.id, data)
    await ctx.send(f"decent return! you made **{profit}** embers profit. not bad 📈")
  elif roll < 0.85:
    profit = int(amount * random.uniform(0.5, 1.5))
    data["embers"] += amount + profit
    save_user(ctx.author.id, data)
    await ctx.send(f"stonks! **{profit}** embers profit! youre basically wolf of wall street 📈🚀")
  else:
    profit = int(amount * random.uniform(2.0, 5.0))
    data["embers"] += amount + profit
    save_user(ctx.author.id, data)
    await ctx.send(f"JACKPOT! you turned **{amount}** into **{amount + profit}** embers! teach me your ways 🔥🔥")

@bot.command()
async def heist(ctx, target: discord.Member = None):
  """plan a heist on someone"""
  if not target or target == ctx.author:
    await ctx.send("you cant heist yourself bro thats just stealing from yourself")
    return

  data = load_user(ctx.author.id)
  target_data = load_user(target.id)

  if target_data["embers"] < 100:
    await ctx.send(f"{target.display_name} aint even worth heisting, they broke")
    return

  success = random.random() < 0.25
  if success:
    amount = random.randint(100, min(1000, target_data["embers"]))
    data["embers"] += amount
    target_data["embers"] -= amount
    save_user(ctx.author.id, data)
    save_user(target.id, target_data)
    await ctx.send(f"the heist was a success! you stole **{amount}** embers from {target.display_name}! 🏴‍☠️")
  else:
    fine = random.randint(50, 200)
    data["embers"] = max(0, data["embers"] - fine)
    save_user(ctx.author.id, data)
    await ctx.send(f"the heist failed and you got caught. paid **{fine}** embers in damages. shoulda stuck to honest work")

@bot.command()
async def loan(ctx, amount: int = None):
  """take out a loan"""
  if not amount or amount <= 0:
    await ctx.send("how much you tryna borrow?")
    return

  data = load_user(ctx.author.id)
  if data["loan"] > 0:
    await ctx.send(f"you already owe **{data['loan']}** embers bro, pay that back first")
    return

  max_loan = data["level"] * 500
  if amount > max_loan:
    await ctx.send(f"max loan for your level is **{max_loan}** embers. level up to borrow more 📈")
    return

  data["loan"] = amount
  data["loan_due"] = (datetime.utcnow() + timedelta(days=7)).isoformat()
  data["embers"] += amount
  save_user(ctx.author.id, data)
  await ctx.send(f"heres your **{amount}** ember loan. you got 7 days to pay it back or interest hits 😤")

@bot.command()
async def repay(ctx, amount: int = None):
  """repay your loan"""
  data = load_user(ctx.author.id)
  if data["loan"] == 0:
    await ctx.send("you dont even have a loan bro, living debt free i see")
    return

  if not amount:
    amount = data["loan"]

  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers, cant repay **{amount}**")
    return

  if amount > data["loan"]:
    amount = data["loan"]

  data["embers"] -= amount
  data["loan"] -= amount
  if data["loan"] <= 0:
    data["loan"] = 0
    data["loan_due"] = None
    await ctx.send("loan fully repaid! youre free from debt 🎉")
  else:
    await ctx.send(f"paid **{amount}** embers. still owe **{data['loan']}** 💰")

  save_user(ctx.author.id, data)

@bot.command()
async def burn(ctx, amount: int = None):
  """burn some embers (why tho)"""
  if not amount or amount <= 0:
    await ctx.send("how many embers you tryna burn?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers, cant burn **{amount}**")
    return

  data["embers"] -= amount
  save_user(ctx.author.id, data)

  msgs = [
    f"you burned **{amount}** embers. hope that was worth it 🔥",
    f"**{amount}** embers went up in smoke. what a waste",
    f"poof! **{amount}** embers gone forever. you do you i guess",
    f"burned **{amount}** embers. feeling warm yet?",
  ]
  await ctx.send(random.choice(msgs))


@bot.command()
async def send(ctx, amount: int = None, target: discord.Member = None):
  """send embers to another user"""
  if not amount or amount <= 0:
    await ctx.send("how much you tryna send bro?")
    return
  if not target or target == ctx.author:
    await ctx.send("you cant send embers to yourself thats just moving money around")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers, cant send **{amount}**")
    return

  # confirmation
  confirm_msg = await ctx.send(
    f"you sure you wanna send **{amount}** embers to {target.display_name}?
"
    f"react with ✅ to confirm or ❌ to cancel"
  )
  await confirm_msg.add_reaction("✅")
  await confirm_msg.add_reaction("❌")

  def check(reaction, user):
    return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id

  try:
    reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)

    if str(reaction.emoji) == "❌":
      await ctx.send("transaction cancelled. smart move, keep your bag 💰")
      return

    # double check balance
    data = load_user(ctx.author.id)
    if data["embers"] < amount:
      await ctx.send("bro you spent the money while i was waiting?")
      return

    target_data = load_user(target.id)
    data["embers"] -= amount
    target_data["embers"] += amount
    save_user(ctx.author.id, data)
    save_user(target.id, target_data)

    await ctx.send(f"sent **{amount}** embers to {target.display_name}! what a legend 🔥")

  except asyncio.TimeoutError:
    await ctx.send("you took too long, transaction cancelled ⏰")

# ── ADMIN COMMANDS (OWNER ONLY) ──

@bot.command()
@is_owner()
async def give(ctx, amount: int = None, target: discord.Member = None):
  """give embers to a user (owner only)"""
  if not amount or amount <= 0:
    await ctx.send("how much you giving?")
    return
  if not target:
    await ctx.send("who you giving it to bro?")
    return

  data = load_user(target.id)
  data["embers"] += amount
  save_user(target.id, data)
  await ctx.send(f"gave **{amount}** embers to {target.display_name}. big boss moves 💰")

@bot.command()
@is_owner()
async def setember(ctx, amount: int = None, target: discord.Member = None):
  """set a users ember balance (owner only)"""
  if amount is None or amount < 0:
    await ctx.send("what amount you setting it to?")
    return
  if not target:
    await ctx.send("who you setting it for bro?")
    return

  data = load_user(target.id)
  old = data["embers"]
  data["embers"] = amount
  save_user(target.id, data)
  await ctx.send(f"set {target.display_name}'s embers from **{old}** to **{amount}**. god mode activated 🔥")

@bot.command()
@is_owner()
async def remove(ctx, amount: int = None, target: discord.Member = None):
  """remove embers from a user (owner only)"""
  if not amount or amount <= 0:
    await ctx.send("how much you removing?")
    return
  if not target:
    await ctx.send("who you taking from bro?")
    return

  data = load_user(target.id)
  removed = min(amount, data["embers"])
  data["embers"] -= removed
  save_user(target.id, data)
  await ctx.send(f"removed **{removed}** embers from {target.display_name}. the tax man cometh")

@bot.command(name="wipe")
@is_owner()
async def wipe_data(ctx, target: discord.Member = None):
  """wipe a user's data (owner only)"""
  if not target:
    await ctx.send("who you wiping bro?")
    return

  path = get_user_path(target.id)
  if os.path.exists(path):
    os.remove(path)
    await ctx.send(f"wiped all data for {target.display_name}. its like they never existed")
  else:
    await ctx.send(f"{target.display_name} doesnt even have any data to wipe")

# ── MODERATION COMMANDS ──

@bot.command()
@has_mod_perms()
async def kick(ctx, member: discord.Member = None, *, reason: str = "no reason given"):
  """kick a member"""
  if not member:
    await ctx.send("who you kicking bro?")
    return
  if member == ctx.author:
    await ctx.send("you cant kick yourself bro")
    return
  if member.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
    await ctx.send("they got higher perms than you, nice try")
    return

  try:
    await member.kick(reason=reason)
    await ctx.send(f"{member.display_name} got the boot 👢 reason: {reason}")
  except discord.Forbidden:
    await ctx.send("i dont have perms to kick them bro")

@bot.command()
@has_mod_perms()
async def ban(ctx, member: discord.Member = None, *, reason: str = "no reason given"):
  """ban a member"""
  if not member:
    await ctx.send("who you banning bro?")
    return
  if member == ctx.author:
    await ctx.send("you cant ban yourself bro")
    return
  if member.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
    await ctx.send("they got higher perms than you, nice try")
    return

  try:
    await member.ban(reason=reason)
    await ctx.send(f"{member.display_name} got banned. rip bozo 🚫")
  except discord.Forbidden:
    await ctx.send("i dont have perms to ban them bro")

@bot.command()
@has_mod_perms()
async def unban(ctx, user_id: int = None):
  """unban a user by id"""
  if not user_id:
    await ctx.send("gimme a user id to unban bro")
    return

  try:
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"unbanned {user.name}. they get a second chance i guess 🤷")
  except discord.NotFound:
    await ctx.send("that user aint banned or doesnt exist")
  except discord.Forbidden:
    await ctx.send("i dont have perms to unban bro")

@bot.command()
@has_mod_perms()
async def mute(ctx, member: discord.Member = None, duration: int = None):
  """timeout a member for x minutes"""
  if not member or not duration or duration <= 0:
    await ctx.send("usage: f mute @user <minutes>")
    return
  if member == ctx.author:
    await ctx.send("you cant mute yourself bro")
    return
  if member.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
    await ctx.send("they got higher perms, cant touch them")
    return

  try:
    until = datetime.utcnow() + timedelta(minutes=duration)
    await member.timeout(until, reason=f"muted by {ctx.author.display_name}")
    await ctx.send(f"{member.display_name} got muted for **{duration}** minutes. enjoy the silence 🔇")
  except discord.Forbidden:
    await ctx.send("i dont have perms to mute them bro")

@bot.command()
@has_mod_perms()
async def unmute(ctx, member: discord.Member = None):
  """remove timeout from a member"""
  if not member:
    await ctx.send("who you unmuting bro?")
    return

  try:
    await member.timeout(None)
    await ctx.send(f"{member.display_name} can talk again. rip the peace and quiet 🔊")
  except discord.Forbidden:
    await ctx.send("i dont have perms bro")

@bot.command()
@has_mod_perms()
async def purge(ctx, amount: int = None):
  """purge messages"""
  if not amount or amount <= 0 or amount > 100:
    await ctx.send("give me a number between 1-100 bro")
    return

  deleted = await ctx.channel.purge(limit=amount + 1)
  msg = await ctx.send(f"deleted **{len(deleted)-1}** messages. poof gone 💨")
  await asyncio.sleep(3)
  await msg.delete()

@bot.command()
@has_mod_perms()
async def warn(ctx, member: discord.Member = None, *, reason: str = "no reason"):
  """warn a member"""
  if not member:
    await ctx.send("who you warning bro?")
    return

  data = load_user(member.id)
  if "warnings" not in data:
    data["warnings"] = []
  data["warnings"].append({"reason": reason, "by": ctx.author.id, "time": datetime.utcnow().isoformat()})
  save_user(member.id, data)

  count = len(data["warnings"])
  await ctx.send(f"{member.display_name} got warned. reason: {reason}. thats warning #{count} ⚠️")

@bot.command()
@has_mod_perms()
async def warnings(ctx, member: discord.Member = None):
  """check a member's warnings"""
  if not member:
    member = ctx.author

  data = load_user(member.id)
  warns = data.get("warnings", [])
  if not warns:
    await ctx.send(f"{member.display_name} is a saint, no warnings ✅")
    return

  msg = f"**{member.display_name}'s warnings:**
"
  for i, w in enumerate(warns[-5:], 1):
    msg += f"{i}. {w['reason']} (by <@{w['by']}>)
"
  await ctx.send(msg)

@bot.command()
@has_mod_perms()
async def clearwarns(ctx, member: discord.Member = None):
  """clear all warnings from a member"""
  if not member:
    await ctx.send("who you clearing warnings for bro?")
    return

  data = load_user(member.id)
  data["warnings"] = []
  save_user(member.id, data)
  await ctx.send(f"cleared all warnings for {member.display_name}. fresh start i guess 🧼")

@bot.command()
@has_mod_perms()
async def lock(ctx, channel: discord.TextChannel = None):
  """lock a channel"""
  channel = channel or ctx.channel
  await channel.set_permissions(ctx.guild.default_role, send_messages=False)
  await ctx.send(f"locked {channel.mention}. nobody can talk now 🔒")

@bot.command()
@has_mod_perms()
async def unlock(ctx, channel: discord.TextChannel = None):
  """unlock a channel"""
  channel = channel or ctx.channel
  await channel.set_permissions(ctx.guild.default_role, send_messages=True)
  await ctx.send(f"unlocked {channel.mention}. free speech restored 🔓")

@bot.command()
@has_mod_perms()
async def slowmode(ctx, seconds: int = 0):
  """set slowmode in a channel"""
  if seconds < 0 or seconds > 21600:
    await ctx.send("slowmode can be 0-21600 seconds bro")
    return
  await ctx.channel.edit(slowmode_delay=seconds)
  if seconds == 0:
    await ctx.send("slowmode disabled. chat goes brrr 💨")
  else:
    await ctx.send(f"slowmode set to **{seconds}** seconds. chill out everyone 🐢")

@bot.command()
@has_mod_perms()
async def nick(ctx, member: discord.Member = None, *, nickname: str = None):
  """change a member's nickname"""
  if not member:
    await ctx.send("who you renaming bro?")
    return
  if member.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
    await ctx.send("cant rename someone higher than you")
    return

  try:
    old = member.display_name
    await member.edit(nick=nickname)
    if nickname:
      await ctx.send(f"renamed {old} to **{nickname}**. identity crisis? 🎭")
    else:
      await ctx.send(f"reset {old}'s nickname back to normal")
  except discord.Forbidden:
    await ctx.send("i dont have perms to rename them bro")

@bot.command()
@has_mod_perms()
async def roleadd(ctx, member: discord.Member = None, role: discord.Role = None):
  """add a role to a member"""
  if not member or not role:
    await ctx.send("usage: f roleadd @user @role")
    return
  if role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
    await ctx.send("that role is too powerful for you to give")
    return

  try:
    await member.add_roles(role)
    await ctx.send(f"gave {role.name} to {member.display_name}. they leveled up 📈")
  except discord.Forbidden:
    await ctx.send("i dont have perms bro")

@bot.command()
@has_mod_perms()
async def roleremove(ctx, member: discord.Member = None, role: discord.Role = None):
  """remove a role from a member"""
  if not member or not role:
    await ctx.send("usage: f roleremove @user @role")
    return
  if role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
    await ctx.send("that role is too powerful for you to remove")
    return

  try:
    await member.remove_roles(role)
    await ctx.send(f"removed {role.name} from {member.display_name}. demoted 📉")
  except discord.Forbidden:
    await ctx.send("i dont have perms bro")


# ── CREATURE COMMANDS ──

CREATURE_NAMES = ["dragon", "phoenix", "golem", "wisp", "shadow", "kraken", "griffin", "basilisk", "kitsune", "chimera"]
CREATURE_MOODS = ["happy", "angry", "sleepy", "hungry", "playful", "grumpy", "mysterious"]

@bot.command()
async def summon(ctx):
  """summon a random creature"""
  data = load_user(ctx.author.id)
  cd_key = "summon"
  now = datetime.utcnow()

  if cd_key in data["cooldowns"]:
    last = datetime.fromisoformat(data["cooldowns"][cd_key])
    if now - last < timedelta(hours=1):
      remaining = timedelta(hours=1) - (now - last)
      mins = int(remaining.total_seconds() // 60)
      await ctx.send(f"chill, you can summon again in **{mins}m**")
      return

  if len(data["creatures"]) >= 10:
    await ctx.send("you already got 10 creatures bro, release one first")
    return

  name = random.choice(CREATURE_NAMES)
  creature = {
    "name": name,
    "level": 1,
    "xp": 0,
    "mood": random.choice(CREATURE_MOODS),
    "fed": datetime.utcnow().isoformat(),
    "id": random.randint(1000, 9999)
  }
  data["creatures"].append(creature)
  data["cooldowns"][cd_key] = now.isoformat()
  save_user(ctx.author.id, data)

  await ctx.send(f"you summoned a **{name}** (lvl 1)! its feeling **{creature['mood']}** today 🔥
use f cage to check on it")

@bot.command()
async def cage(ctx):
  """check your creatures"""
  data = load_user(ctx.author.id)
  creatures = data["creatures"]

  if not creatures:
    await ctx.send("you dont have any creatures bro. use f summon to get one")
    return

  msg = "**your creatures:**
"
  for i, c in enumerate(creatures, 1):
    msg += f"{i}. **{c['name']}** (lvl {c['level']}) - mood: {c['mood']}
"
  await ctx.send(msg)

@bot.command()
async def release(ctx, index: int = None):
  """release a creature"""
  data = load_user(ctx.author.id)
  creatures = data["creatures"]

  if not creatures:
    await ctx.send("you dont have any creatures to release")
    return
  if not index or index < 1 or index > len(creatures):
    await ctx.send(f"pick a number 1-{len(creatures)} bro")
    return

  released = creatures.pop(index - 1)
  save_user(ctx.author.id, data)
  await ctx.send(f"you released your **{released['name']}**. it flew away into the sunset 🕊️")

@bot.command()
async def feed(ctx, index: int = None):
  """feed a creature"""
  data = load_user(ctx.author.id)
  creatures = data["creatures"]

  if not creatures:
    await ctx.send("you dont have any creatures to feed")
    return
  if not index or index < 1 or index > len(creatures):
    await ctx.send(f"pick a number 1-{len(creatures)} bro")
    return

  if data["embers"] < 10:
    await ctx.send("you need at least 10 embers to feed a creature")
    return

  creature = creatures[index - 1]
  data["embers"] -= 10
  creature["fed"] = datetime.utcnow().isoformat()
  creature["mood"] = "happy"
  creature["xp"] += 20

  if creature["xp"] >= creature["level"] * 100:
    creature["level"] += 1
    creature["xp"] = 0
    save_user(ctx.author.id, data)
    await ctx.send(f"your **{creature['name']}** ate well and leveled up to **lvl {creature['level']}**! 🎉")
  else:
    save_user(ctx.author.id, data)
    await ctx.send(f"your **{creature['name']}** ate happily. xp: {creature['xp']}/{creature['level']*100} 🍖")

@bot.command()
async def neglect(ctx, index: int = None):
  """neglect a creature (dont do this)"""
  data = load_user(ctx.author.id)
  creatures = data["creatures"]

  if not creatures:
    await ctx.send("you dont have any creatures to neglect")
    return
  if not index or index < 1 or index > len(creatures):
    await ctx.send(f"pick a number 1-{len(creatures)} bro")
    return

  creature = creatures[index - 1]
  creature["mood"] = "grumpy"
  creature["xp"] = max(0, creature["xp"] - 10)
  save_user(ctx.author.id, data)
  await ctx.send(f"you neglected your **{creature['name']}**. its now **{creature['mood']}** and lost xp. monster")

@bot.command()
async def mood(ctx, index: int = None):
  """check a creature's mood"""
  data = load_user(ctx.author.id)
  creatures = data["creatures"]

  if not creatures:
    await ctx.send("you dont have any creatures")
    return
  if not index or index < 1 or index > len(creatures):
    await ctx.send(f"pick a number 1-{len(creatures)} bro")
    return

  creature = creatures[index - 1]
  moods = {
    "happy": "its vibing hard rn 🎉",
    "angry": "its pissed off, watch out 😤",
    "sleepy": "its about to nap 💤",
    "hungry": "it wants food NOW 🍖",
    "playful": "it wants to play! 🎾",
    "grumpy": "its in a bad mood. probably your fault",
    "mysterious": "its acting weird... 👀"
  }
  await ctx.send(f"your **{creature['name']}** is feeling **{creature['mood']}**. {moods.get(creature['mood'], '')}")

@bot.command()
async def evolve(ctx, index: int = None):
  """force evolve a creature (costs embers)"""
  data = load_user(ctx.author.id)
  creatures = data["creatures"]

  if not creatures:
    await ctx.send("you dont have any creatures")
    return
  if not index or index < 1 or index > len(creatures):
    await ctx.send(f"pick a number 1-{len(creatures)} bro")
    return

  creature = creatures[index - 1]
  cost = creature["level"] * 100
  if data["embers"] < cost:
    await ctx.send(f"you need **{cost}** embers to evolve this creature. you got **{data['embers']}**")
    return

  data["embers"] -= cost
  creature["level"] += 1
  creature["xp"] = 0
  save_user(ctx.author.id, data)
  await ctx.send(f"your **{creature['name']}** evolved to **lvl {creature['level']}**! its glowing with power ✨")

@bot.command()
async def breed(ctx, index1: int = None, index2: int = None):
  """breed two creatures"""
  data = load_user(ctx.author.id)
  creatures = data["creatures"]

  if len(creatures) < 2:
    await ctx.send("you need at least 2 creatures to breed")
    return
  if not index1 or not index2 or index1 == index2:
    await ctx.send("pick 2 different creatures bro")
    return
  if index1 < 1 or index1 > len(creatures) or index2 < 1 or index2 > len(creatures):
    await ctx.send("invalid creature numbers")
    return
  if len(creatures) >= 10:
    await ctx.send("you got too many creatures already, release one first")
    return

  c1 = creatures[index1 - 1]
  c2 = creatures[index2 - 1]

  if c1["level"] < 3 or c2["level"] < 3:
    await ctx.send("both creatures need to be at least lvl 3 to breed")
    return

  baby_name = random.choice(CREATURE_NAMES)
  baby = {
    "name": baby_name,
    "level": 1,
    "xp": 0,
    "mood": "playful",
    "fed": datetime.utcnow().isoformat(),
    "id": random.randint(1000, 9999)
  }
  data["creatures"].append(baby)
  save_user(ctx.author.id, data)
  await ctx.send(f"a baby **{baby_name}** was born! its so cute 🥺 use f cage to see it")

@bot.command()
async def sacrifice(ctx, index: int = None):
  """sacrifice a creature for embers (dark)"""
  data = load_user(ctx.author.id)
  creatures = data["creatures"]

  if not creatures:
    await ctx.send("you dont have any creatures to sacrifice")
    return
  if not index or index < 1 or index > len(creatures):
    await ctx.send(f"pick a number 1-{len(creatures)} bro")
    return

  creature = creatures.pop(index - 1)
  reward = creature["level"] * 50
  data["embers"] += reward
  save_user(ctx.author.id, data)
  await ctx.send(f"you sacrificed your **{creature['name']}** and got **{reward}** embers. the dark side pays well.")

@bot.command()
async def rename(ctx, index: int = None, *, new_name: str = None):
  """rename a creature"""
  data = load_user(ctx.author.id)
  creatures = data["creatures"]

  if not creatures:
    await ctx.send("you dont have any creatures")
    return
  if not index or index < 1 or index > len(creatures):
    await ctx.send(f"pick a number 1-{len(creatures)} bro")
    return
  if not new_name:
    await ctx.send("what you renaming it to?")
    return

  old = creatures[index - 1]["name"]
  creatures[index - 1]["name"] = new_name
  save_user(ctx.author.id, data)
  await ctx.send(f"renamed **{old}** to **{new_name}**. dont forget its new name! 🏷️")

@bot.command()
async def favorite(ctx, index: int = None):
  """set a favorite creature"""
  data = load_user(ctx.author.id)
  creatures = data["creatures"]

  if not creatures:
    await ctx.send("you dont have any creatures")
    return
  if not index or index < 1 or index > len(creatures):
    await ctx.send(f"pick a number 1-{len(creatures)} bro")
    return

  data["favorite_creature"] = index - 1
  save_user(ctx.author.id, data)
  await ctx.send(f"**{creatures[index-1]['name']}** is now your favorite! 💖")

@bot.command()
async def trade(ctx, index: int = None, target: discord.Member = None):
  """trade a creature to another user"""
  if not index or not target or target == ctx.author:
    await ctx.send("usage: f trade <creature #> @user")
    return

  data = load_user(ctx.author.id)
  target_data = load_user(target.id)
  creatures = data["creatures"]

  if not creatures or index < 1 or index > len(creatures):
    await ctx.send("invalid creature number")
    return
  if len(target_data["creatures"]) >= 10:
    await ctx.send(f"{target.display_name} already has 10 creatures")
    return

  creature = creatures.pop(index - 1)
  target_data["creatures"].append(creature)
  save_user(ctx.author.id, data)
  save_user(target.id, target_data)
  await ctx.send(f"traded your **{creature['name']}** to {target.display_name}! hope they take good care of it 🤝")

@bot.command()
async def auction(ctx, index: int = None, price: int = None):
  """put a creature up for auction"""
  data = load_user(ctx.author.id)
  creatures = data["creatures"]

  if not index or not price or index < 1 or index > len(creatures):
    await ctx.send("usage: f auction <creature #> <price>")
    return

  creature = creatures[index - 1]
  await ctx.send(
    f"🎪 **AUCTION** 🎪
"
    f"seller: {ctx.author.display_name}
"
    f"creature: **{creature['name']}** (lvl {creature['level']})
"
    f"starting bid: **{price}** embers
"
    f"type f bid @{ctx.author.name} {price} to buy!"
  )

@bot.command()
async def bid(ctx, seller: discord.Member = None, amount: int = None):
  """bid on an auction"""
  if not seller or not amount:
    await ctx.send("usage: f bid @seller <amount>")
    return
  if seller == ctx.author:
    await ctx.send("you cant bid on your own auction bro")
    return

  await ctx.send(f"bid **{amount}** embers placed! {seller.display_name} needs to accept with f accept @{ctx.author.name}")

@bot.command()
async def inspect(ctx, index: int = None):
  """inspect a creature closely"""
  data = load_user(ctx.author.id)
  creatures = data["creatures"]

  if not creatures:
    await ctx.send("you dont have any creatures")
    return
  if not index or index < 1 or index > len(creatures):
    await ctx.send(f"pick a number 1-{len(creatures)} bro")
    return

  c = creatures[index - 1]
  await ctx.send(
    f"**{c['name']}** (ID: {c['id']})
"
    f"level: **{c['level']}**
"
    f"xp: **{c['xp']}**/{c['level']*100}
"
    f"mood: **{c['mood']}**
"
    f"last fed: {c['fed'][:10]}
"
    f"this creature is a beast"
  )

@bot.command()
async def adopt(ctx, target: discord.Member = None):
  """adopt a creature from someone"""
  if not target or target == ctx.author:
    await ctx.send("who you tryna adopt from?")
    return

  target_data = load_user(target.id)
  if not target_data["creatures"]:
    await ctx.send(f"{target.display_name} doesnt have any creatures to adopt")
    return

  await ctx.send(f"asked {target.display_name} to let you adopt a creature! they need to use f trade")

@bot.command()
async def kidnap(ctx, target: discord.Member = None):
  """try to kidnap someone's creature"""
  if not target or target == ctx.author:
    await ctx.send("who you tryna kidnap from?")
    return

  data = load_user(ctx.author.id)
  target_data = load_user(target.id)

  if not target_data["creatures"]:
    await ctx.send(f"{target.display_name} aint got no creatures to steal")
    return
  if len(data["creatures"]) >= 10:
    await ctx.send("you got too many creatures already")
    return

  success = random.random() < 0.15
  if success:
    stolen = target_data["creatures"].pop(random.randint(0, len(target_data["creatures"])-1))
    data["creatures"].append(stolen)
    save_user(ctx.author.id, data)
    save_user(target.id, target_data)
    await ctx.send(f"you successfully kidnapped a **{stolen['name']}** from {target.display_name}! youre a criminal 🏴‍☠️")
  else:
    fine = random.randint(20, 100)
    data["embers"] = max(0, data["embers"] - fine)
    save_user(ctx.author.id, data)
    await ctx.send(f"you got caught trying to kidnap and paid a **{fine}** ember fine. stick to legal adoptions")


# ── COMBAT COMMANDS ──

@bot.command()
async def duel(ctx, target: discord.Member = None):
  """challenge someone to a duel"""
  if not target or target == ctx.author:
    await ctx.send("who you dueling bro?")
    return
  if target.bot:
    await ctx.send("you cant duel a bot bro")
    return

  data = load_user(ctx.author.id)
  target_data = load_user(target.id)

  await ctx.send(f"{target.mention}! {ctx.author.display_name} challenges you to a duel! type **accept** or **decline**")

  def check(m):
    return m.author == target and m.channel == ctx.channel and m.content.lower() in ["accept", "decline"]

  try:
    msg = await bot.wait_for("message", timeout=30.0, check=check)
    if msg.content.lower() == "decline":
      await ctx.send(f"{target.display_name} pussied out")
      return
  except asyncio.TimeoutError:
    await ctx.send(f"{target.display_name} didnt respond in time. coward")
    return

  p1_power = data["level"] * 10 + random.randint(0, 50)
  p2_power = target_data["level"] * 10 + random.randint(0, 50)

  await ctx.send("⚔️ **DUEL STARTING** ⚔️")
  await asyncio.sleep(1)

  rounds = []
  for i in range(3):
    r1 = random.randint(1, 20)
    r2 = random.randint(1, 20)
    rounds.append((r1, r2))
    await ctx.send(f"round {i+1}: {ctx.author.display_name} rolled **{r1}** | {target.display_name} rolled **{r2}**")
    await asyncio.sleep(1)

  p1_total = sum(r[0] for r in rounds) + p1_power
  p2_total = sum(r[1] for r in rounds) + p2_power

  if p1_total > p2_total:
    winnings = random.randint(50, 200)
    data["embers"] += winnings
    data["wins"] += 1
    target_data["losses"] += 1
    save_user(ctx.author.id, data)
    save_user(target.id, target_data)
    await ctx.send(f"🏆 {ctx.author.display_name} WINS! gained **{winnings}** embers and bragging rights")
  elif p2_total > p1_total:
    winnings = random.randint(50, 200)
    target_data["embers"] += winnings
    target_data["wins"] += 1
    data["losses"] += 1
    save_user(ctx.author.id, data)
    save_user(target.id, target_data)
    await ctx.send(f"🏆 {target.display_name} WINS! gained **{winnings}** embers. {ctx.author.display_name} took an L")
  else:
    await ctx.send("its a draw! nobody wins, friendship wins i guess 🤝")

@bot.command()
async def raid(ctx, target: discord.Member = None):
  """raid someone's embers"""
  if not target or target == ctx.author:
    await ctx.send("who you raiding bro?")
    return

  data = load_user(ctx.author.id)
  target_data = load_user(target.id)

  if target_data["embers"] < 50:
    await ctx.send(f"{target.display_name} is too broke to raid")
    return

  success = random.random() < 0.35
  if success:
    amount = random.randint(50, min(300, target_data["embers"]))
    data["embers"] += amount
    target_data["embers"] -= amount
    save_user(ctx.author.id, data)
    save_user(target.id, target_data)
    await ctx.send(f"raid successful! stole **{amount}** embers from {target.display_name}! 🏴‍☠️")
  else:
    loss = random.randint(10, 50)
    data["embers"] = max(0, data["embers"] - loss)
    save_user(ctx.author.id, data)
    await ctx.send(f"raid failed! you lost **{loss}** embers retreating. shoulda planned better")

@bot.command()
async def ambush(ctx, target: discord.Member = None):
  """ambush someone"""
  if not target or target == ctx.author:
    await ctx.send("who you ambushing bro?")
    return

  data = load_user(ctx.author.id)
  target_data = load_user(target.id)

  success = random.random() < 0.5
  if success:
    amount = random.randint(20, 150)
    data["embers"] += amount
    target_data["embers"] = max(0, target_data["embers"] - amount)
    save_user(ctx.author.id, data)
    save_user(target.id, target_data)
    await ctx.send(f"ambush successful! caught {target.display_name} off guard and took **{amount}** embers! 😈")
  else:
    await ctx.send(f"{target.display_name} saw you coming and dodged. embarrassing")

@bot.command()
async def defend(ctx):
  """defend yourself (gives temporary protection)"""
  data = load_user(ctx.author.id)
  data["defending"] = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
  save_user(ctx.author.id, data)
  await ctx.send("you raised your defenses! youre protected from raids for 10 minutes 🛡️")

@bot.command()
async def berserk(ctx, target: discord.Member = None):
  """go berserk on someone"""
  if not target or target == ctx.author:
    await ctx.send("who you going berserk on bro?")
    return

  data = load_user(ctx.author.id)
  target_data = load_user(target.id)

  if data["embers"] < 50:
    await ctx.send("you need 50 embers to go berserk bro")
    return

  data["embers"] -= 50
  power = random.randint(1, 100)

  if power > 70:
    amount = random.randint(100, 400)
    data["embers"] += amount
    target_data["embers"] = max(0, target_data["embers"] - amount)
    save_user(ctx.author.id, data)
    save_user(target.id, target_data)
    await ctx.send(f"BERSERK MODE! you destroyed {target.display_name} and took **{amount}** embers! 🔥🔥🔥")
  elif power > 30:
    amount = random.randint(50, 150)
    data["embers"] += amount
    target_data["embers"] = max(0, target_data["embers"] - amount)
    save_user(ctx.author.id, data)
    save_user(target.id, target_data)
    await ctx.send(f"you went berserk and got **{amount}** embers. decent rampage 🔥")
  else:
    save_user(ctx.author.id, data)
    await ctx.send(f"you tripped while going berserk and lost 50 embers. smooth")

@bot.command()
async def bribe(ctx, target: discord.Member = None, amount: int = None):
  """bribe someone to leave you alone"""
  if not target or not amount or target == ctx.author:
    await ctx.send("usage: f bribe @user <amount>")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= amount
  target_data = load_user(target.id)
  target_data["embers"] += amount
  save_user(ctx.author.id, data)
  save_user(target.id, target_data)
  await ctx.send(f"you bribed {target.display_name} with **{amount}** embers. money talks 💰")

@bot.command()
async def flee(ctx):
  """flee from danger"""
  outcomes = [
    "you ran away successfully. coward but alive 🏃",
    "you tried to flee but tripped. embarrassing",
    "you vanished into the shadows. ninja style 🥷",
    "you got away but dropped some embers. oops",
  ]
  await ctx.send(random.choice(outcomes))

@bot.command()
async def taunt(ctx, target: discord.Member = None):
  """taunt someone"""
  if not target or target == ctx.author:
    await ctx.send("who you taunting bro?")
    return

  taunts = [
    f"{target.mention} youre so broke even beggars pity you",
    f"{target.mention} ive seen bots with more personality than you",
    f"{target.mention} you fight like a dairy farmer 🥛",
    f"{target.mention} your creatures are ashamed of you",
    f"{target.mention} is that your best? my grandma hits harder 👵",
    f"{target.mention} youre the reason the gene pool needs a lifeguard 🏊",
  ]
  await ctx.send(random.choice(taunts))

@bot.command()
async def combo(ctx, target: discord.Member = None):
  """hit someone with a combo"""
  if not target or target == ctx.author:
    await ctx.send("who you comboing bro?")
    return

  hits = random.randint(2, 5)
  total = 0
  msg = f"⚡ **COMBO x{hits}** on {target.display_name}!
"
  for i in range(hits):
    dmg = random.randint(10, 50)
    total += dmg
    msg += f"hit {i+1}: **{dmg}** dmg
"

  target_data = load_user(target.id)
  target_data["embers"] = max(0, target_data["embers"] - total)
  save_user(target.id, target_data)
  msg += f"total damage: **{total}** embers stolen! 🔥"
  await ctx.send(msg)

@bot.command()
async def revive(ctx):
  """revive yourself (reset losses)"""
  data = load_user(ctx.author.id)
  if data["losses"] == 0:
    await ctx.send("you havent lost anything to revive from")
    return
  if data["embers"] < 100:
    await ctx.send("you need 100 embers to revive bro")
    return

  data["embers"] -= 100
  data["losses"] = 0
  save_user(ctx.author.id, data)
  await ctx.send("you revived! all losses forgiven. fresh start baby 🔄")

@bot.command()
async def wager(ctx, amount: int = None):
  """wager embers on a 50/50"""
  if not amount or amount <= 0:
    await ctx.send("how much you wagering bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= amount

  if random.random() < 0.5:
    winnings = amount * 2
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"you won! got back **{winnings}** embers! double or nothing? 🎰")
  else:
    save_user(ctx.author.id, data)
    await ctx.send(f"you lost **{amount}** embers. the house always wins")

@bot.command()
async def rank(ctx):
  """check your combat rank"""
  data = load_user(ctx.author.id)
  wins = data["wins"]
  losses = data["losses"]
  ratio = wins / max(losses, 1)

  if wins < 5:
    rank = "peasant"
  elif wins < 15:
    rank = "warrior"
  elif wins < 30:
    rank = "knight"
  elif wins < 50:
    rank = "champion"
  else:
    rank = "legend"

  await ctx.send(f"your rank: **{rank}** | wins: **{wins}** | losses: **{losses}** | ratio: **{ratio:.2f}** ⚔️")


# ── GAMBLING COMMANDS ──

@bot.command()
async def dice(ctx, bet: int = None):
  """roll dice, bet embers"""
  if not bet or bet <= 0:
    await ctx.send("how much you betting bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < bet:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= bet
  roll = random.randint(1, 6)

  if roll >= 4:
    winnings = bet * 2
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"you rolled a **{roll}**! won **{winnings}** embers! 🎲")
  else:
    save_user(ctx.author.id, data)
    await ctx.send(f"you rolled a **{roll}**. lost your bet. better luck next time")

@bot.command()
async def shells(ctx, bet: int = None, guess: int = None):
  """shell game - guess which shell has the ball"""
  if not bet or bet <= 0 or not guess or guess < 1 or guess > 3:
    await ctx.send("usage: f shells <bet> <1-3>")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < bet:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= bet
  answer = random.randint(1, 3)

  if guess == answer:
    winnings = bet * 3
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"ball was under shell **{answer}**! you won **{winnings}** embers! 🐚")
  else:
    save_user(ctx.author.id, data)
    await ctx.send(f"ball was under shell **{answer}**. you picked **{guess}**. lost your bet")

@bot.command(name="coinflip")
async def coinflip_cmd(ctx, bet: int = None, side: str = None):
  """flip a coin"""
  if not bet or bet <= 0 or not side or side.lower() not in ["heads", "tails"]:
    await ctx.send("usage: f coinflip <bet> heads/tails")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < bet:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= bet
  result = random.choice(["heads", "tails"])

  if side.lower() == result:
    winnings = bet * 2
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"its **{result}**! you won **{winnings}** embers! 🪙")
  else:
    save_user(ctx.author.id, data)
    await ctx.send(f"its **{result}**. you picked **{side}**. rip your bet")

@bot.command(name="cf")
async def cf_cmd(ctx, bet: int = None, side: str = None):
  """shortcut for coinflip"""
  await coinflip_cmd(ctx, bet, side)

@bot.command()
async def spin(ctx, bet: int = None):
  """spin the wheel"""
  if not bet or bet <= 0:
    await ctx.send("how much you betting bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < bet:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= bet
  outcomes = [
    ("x0", 0), ("x0.5", 0.5), ("x1", 1), ("x1", 1), ("x2", 2), ("x2", 2), ("x3", 3), ("x5", 5), ("x10", 10)
  ]
  result, mult = random.choice(outcomes)
  winnings = int(bet * mult)
  data["embers"] += winnings
  save_user(ctx.author.id, data)

  if mult >= 3:
    await ctx.send(f"wheel landed on **{result}**! you won **{winnings}** embers! JACKPOT! 🎰🔥")
  elif mult >= 1:
    await ctx.send(f"wheel landed on **{result}**. you got back **{winnings}** embers. not bad 🎰")
  else:
    await ctx.send(f"wheel landed on **{result}**. you got **{winnings}** embers. ouch")

@bot.command()
async def surge(ctx, bet: int = None):
  """surge gamble - high risk high reward"""
  if not bet or bet <= 0:
    await ctx.send("how much you betting bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < bet:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= bet
  roll = random.random()

  if roll < 0.6:
    save_user(ctx.author.id, data)
    await ctx.send("the surge failed. lost everything. high risk means high losses too")
  elif roll < 0.85:
    winnings = int(bet * 2)
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"surge successful! **{winnings}** embers! ⚡")
  elif roll < 0.95:
    winnings = int(bet * 5)
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"MASSIVE SURGE! **{winnings}** embers! youre on fire! 🔥⚡")
  else:
    winnings = int(bet * 10)
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"LEGENDARY SURGE! **{winnings}** EMBERS! HOLY SHIT! 🔥🔥🔥⚡")

@bot.command()
async def vault(ctx, amount: int = None):
  """store embers in vault (cant be stolen)"""
  if not amount or amount <= 0:
    await ctx.send("how much you storing bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  if "vault" not in data:
    data["vault"] = 0

  data["embers"] -= amount
  data["vault"] += amount
  save_user(ctx.author.id, data)
  await ctx.send(f"stored **{amount}** embers in your vault. safe from raids! total vault: **{data['vault']}** 🔒")

@bot.command()
async def pick(ctx, bet: int = None):
  """pick a card"""
  if not bet or bet <= 0:
    await ctx.send("how much you betting bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < bet:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= bet
  card = random.randint(1, 13)

  if card >= 10:
    winnings = bet * 3
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"you drew a **{card}**! won **{winnings}** embers! 🃏")
  elif card >= 6:
    winnings = bet * 1
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"you drew a **{card}**. got your money back. could be worse 🃏")
  else:
    save_user(ctx.author.id, data)
    await ctx.send(f"you drew a **{card}**. lost your bet. unlucky 🃏")

@bot.command()
async def chase(ctx, bet: int = None):
  """chase game - run from the cops"""
  if not bet or bet <= 0:
    await ctx.send("how much you betting bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < bet:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= bet
  distance = 0
  msg = await ctx.send("🏃 **CHASE STARTED** 🚔
distance: 0m")

  for i in range(5):
    await asyncio.sleep(1)
    step = random.randint(-10, 30)
    distance += step
    await msg.edit(content=f"🏃 **CHASE** 🚔
distance: {distance}m")

  if distance >= 50:
    winnings = bet * 4
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"you escaped! won **{winnings}** embers! youre untouchable 🏃💨")
  elif distance >= 20:
    winnings = bet * 2
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"you barely got away! won **{winnings}** embers! close call 🏃")
  else:
    save_user(ctx.author.id, data)
    await ctx.send("the cops caught you. lost your bet and your dignity 🚔")

@bot.command()
async def chamber(ctx, bet: int = None):
  """russian roulette style game"""
  if not bet or bet <= 0:
    await ctx.send("how much you betting bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < bet:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= bet
  chamber = random.randint(1, 6)

  if chamber == 1:
    save_user(ctx.author.id, data)
    await ctx.send("💥 BANG! you lost everything. shoulda quit while ahead")
  else:
    winnings = int(bet * 1.5)
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"*click* chamber {chamber} was empty! won **{winnings}** embers! living dangerously 🔫")

@bot.command()
async def rig(ctx, target: discord.Member = None):
  """try to rig a game in your favor (risky)"""
  if not target or target == ctx.author:
    await ctx.send("who you rigging against bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < 200:
    await ctx.send("you need 200 embers to rig a game bro")
    return

  data["embers"] -= 200
  success = random.random() < 0.3

  if success:
    target_data = load_user(target.id)
    amount = random.randint(100, 300)
    data["embers"] += amount
    target_data["embers"] = max(0, target_data["embers"] - amount)
    save_user(ctx.author.id, data)
    save_user(target.id, target_data)
    await ctx.send(f"you rigged the game and took **{amount}** embers from {target.display_name}! the system is rigged 😈")
  else:
    fine = random.randint(50, 150)
    data["embers"] = max(0, data["embers"] - fine)
    save_user(ctx.author.id, data)
    await ctx.send(f"you got caught rigging and paid a **{fine}** ember fine. cheaters never prosper")


# ── SOCIAL COMMANDS ──

@bot.command()
async def marry(ctx, target: discord.Member = None):
  """marry someone"""
  if not target or target == ctx.author:
    await ctx.send("who you marrying bro? yourself?")
    return
  if target.bot:
    await ctx.send("you cant marry a bot bro")
    return

  data = load_user(ctx.author.id)
  target_data = load_user(target.id)

  if data.get("married_to"):
    await ctx.send("youre already married bro, divorce first")
    return
  if target_data.get("married_to"):
    await ctx.send(f"{target.display_name} is already taken. homewrecker energy")
    return

  await ctx.send(f"{target.mention}! {ctx.author.display_name} wants to marry you! type **yes** or **no**")

  def check(m):
    return m.author == target and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

  try:
    msg = await bot.wait_for("message", timeout=30.0, check=check)
    if msg.content.lower() == "no":
      await ctx.send(f"{target.display_name} said no. rejected in 4k")
      return
  except asyncio.TimeoutError:
    await ctx.send("they ghosted you. left on read")
    return

  data["married_to"] = target.id
  target_data["married_to"] = ctx.author.id
  save_user(ctx.author.id, data)
  save_user(target.id, target_data)
  await ctx.send(f"💍 {ctx.author.display_name} and {target.display_name} are now married! congrats i guess")

@bot.command()
async def divorce(ctx):
  """divorce your partner"""
  data = load_user(ctx.author.id)
  if not data.get("married_to"):
    await ctx.send("youre not even married bro")
    return

  partner_id = data["married_to"]
  partner_data = load_user(partner_id)

  data["married_to"] = None
  partner_data["married_to"] = None
  save_user(ctx.author.id, data)
  save_user(partner_id, partner_data)
  await ctx.send("divorced. back on the market i guess 💔")

@bot.command()
async def will(ctx, target: discord.Member = None, amount: int = None):
  """leave embers to someone in your will"""
  if not target or not amount or amount <= 0:
    await ctx.send("usage: f will @user <amount>")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  if "will" not in data:
    data["will"] = {}
  data["will"][str(target.id)] = amount
  save_user(ctx.author.id, data)
  await ctx.send(f"left **{amount}** embers to {target.display_name} in your will. morbid but ok")

@bot.command()
async def cult(ctx, *, name: str = None):
  """start a cult"""
  if not name:
    await ctx.send("whats your cult called bro?")
    return

  data = load_user(ctx.author.id)
  if "cult" in data:
    await ctx.send("you already lead a cult bro. one cult at a time")
    return

  data["cult"] = {"name": name, "members": [ctx.author.id], "level": 1}
  save_user(ctx.author.id, data)
  await ctx.send(f"the **{name}** cult has been founded! recruit members with f tribute")

@bot.command()
async def betray(ctx, target: discord.Member = None):
  """betray someone"""
  if not target or target == ctx.author:
    await ctx.send("who you betraying bro?")
    return

  data = load_user(ctx.author.id)
  target_data = load_user(target.id)

  if target_data["embers"] < 50:
    await ctx.send(f"{target.display_name} aint even worth betraying, they broke")
    return

  amount = random.randint(20, min(200, target_data["embers"]))
  data["embers"] += amount
  target_data["embers"] -= amount
  save_user(ctx.author.id, data)
  save_user(target.id, target_data)
  await ctx.send(f"you betrayed {target.display_name} and stole **{amount}** embers. cold blooded 🐍")

@bot.command()
async def tribute(ctx, target: discord.Member = None, amount: int = None):
  """pay tribute to someone"""
  if not target or not amount or amount <= 0:
    await ctx.send("usage: f tribute @user <amount>")
    return
  if target == ctx.author:
    await ctx.send("you cant tribute to yourself bro")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= amount
  target_data = load_user(target.id)
  target_data["embers"] += amount
  save_user(ctx.author.id, data)
  save_user(target.id, target_data)
  await ctx.send(f"you paid **{amount}** embers tribute to {target.display_name}. bow down 🙇")

@bot.command()
async def roast(ctx, target: discord.Member = None):
  """roast someone"""
  if not target or target == ctx.author:
    await ctx.send("who you roasting bro?")
    return

  roasts = [
    f"{target.mention} youre like a cloud. when you disappear its a beautiful day",
    f"{target.mention} id agree with you but then wed both be wrong",
    f"{target.mention} youre not stupid, you just have bad luck thinking",
    f"{target.mention} im jealous of people who dont know you",
    f"{target.mention} youre the reason shampoo has instructions",
    f"{target.mention} if laughter is the best medicine, your face must be curing the world",
    f"{target.mention} youre not dumb, you just have a lot of blonde moments",
    f"{target.mention} id explain it to you but i left my crayons at home",
    f"{target.mention} youre proof that evolution can go in reverse",
    f"{target.mention} youre like a software update. whenever i see you i think 'not now'",
  ]
  await ctx.send(random.choice(roasts))

@bot.command()
async def confess(ctx, *, message: str = None):
  """confess something anonymously"""
  if not message:
    await ctx.send("what you confessing bro?")
    return

  await ctx.message.delete()
  await ctx.send(f"📢 **ANONYMOUS CONFESSION** 📢
{message}")

# ── UTILITY COMMANDS ──

@bot.command()
async def tutorial(ctx):
  """get a tutorial on how to use the bot"""
  await ctx.send(
    "**flame bot tutorial** 🔥
"
    "prefix: **f ** or **flame ** (space required!)
"
    "currency: **embers**

"
    "**getting started:**
"
    "f daily - claim free embers every 24h
"
    "f embers - check your balance
"
    "f beg - beg for spare change
"
    "f help - see all commands

"
    "**economy:** invest, scam, heist, loan, etc
"
    "**creatures:** summon, feed, breed, evolve
"
    "**combat:** duel, raid, berserk, wager
"
    "**gambling:** dice, coinflip, spin, chamber
"
    "**social:** marry, roast, confess

"
    "good luck and dont go broke"
  )

@bot.command()
async def stats(ctx, target: discord.Member = None):
  """check your or someone else's stats"""
  target = target or ctx.author
  data = load_user(target.id)

  embers = data["embers"]
  level = data["level"]
  xp = data["xp"]
  wins = data["wins"]
  losses = data["losses"]
  creatures = len(data["creatures"])
  loan = data["loan"]
  streak = data["daily_streak"]

  await ctx.send(
    f"**{target.display_name}'s stats** 📊
"
    f"embers: **{embers}**
"
    f"level: **{level}** (xp: {xp})
"
    f"combat: **{wins}**W / **{losses}**L
"
    f"creatures: **{creatures}**
"
    f"daily streak: **{streak}**
"
    f"loan: **{loan}** embers"
  )

@bot.command()
async def server(ctx):
  """server info"""
  guild = ctx.guild
  await ctx.send(
    f"**{guild.name}** 🏰
"
    f"members: **{guild.member_count}**
"
    f"created: {guild.created_at.strftime('%Y-%m-%d')}
"
    f"owner: {guild.owner.display_name if guild.owner else 'unknown'}
"
    f"channels: **{len(guild.channels)}**
"
    f"roles: **{len(guild.roles)}**"
  )

@bot.command()
async def global_lb(ctx):
  """global leaderboard"""
  all_ids = get_all_user_ids()
  users = []
  for uid in all_ids:
    d = load_user(uid)
    users.append((uid, d["embers"]))

  users.sort(key=lambda x: x[1], reverse=True)

  msg = "**global ember leaderboard** 🌍
"
  for i, (uid, embers) in enumerate(users[:10], 1):
    user = bot.get_user(uid)
    name = user.display_name if user else f"user_{uid}"
    msg += f"{i}. **{name}** - {embers} embers
"

  await ctx.send(msg)

@bot.command()
async def settings(ctx):
  """check your settings"""
  data = load_user(ctx.author.id)
  married = "yes" if data.get("married_to") else "no"
  vault = data.get("vault", 0)

  await ctx.send(
    f"**your settings** ⚙️
"
    f"married: **{married}**
"
    f"vault: **{vault}** embers
"
    f"notifications: on
"
    f"theme: default"
  )

@bot.command()
async def cooldowns(ctx):
  """check your cooldowns"""
  data = load_user(ctx.author.id)
  cds = data.get("cooldowns", {})
  now = datetime.utcnow()

  if not cds:
    await ctx.send("no active cooldowns. youre free to do whatever")
    return

  msg = "**your cooldowns:**
"
  for key, time_str in cds.items():
    last = datetime.fromisoformat(time_str)
    elapsed = now - last
    msg += f"{key}: {elapsed.total_seconds()//60:.0f}m ago
"
  await ctx.send(msg)

@bot.command()
async def changelog(ctx):
  """bot changelog"""
  await ctx.send(
    "**flame bot changelog** 📝
"
    "v1.0 - initial release
"
    "- 350+ commands added
"
    "- economy system
"
    "- creature system
"
    "- combat system
"
    "- gambling system
"
    "- moderation tools
"
    "- social features
"
    "- data persistence"
  )


# ── WEIRD COMMANDS ──

@bot.command()
async def dream(ctx):
  """have a random dream"""
  dreams = [
    "you dreamt about swimming in a pool of embers. woke up and checked your balance. still broke",
    "you dreamt you were the bot owner. then you woke up. sad",
    "you dreamt about marrying a dragon. weird but ok",
    "you dreamt you won the lottery. then you realized this bot doesnt have a lottery",
    "you dreamt about being rich. reality hit different",
    "you dreamt you could fly. woke up and fell off your bed",
    "you dreamt about a world without taxes. woke up crying",
    "you dreamt you had 1 million embers. it was just a dream tho",
    "you dreamt about eating pizza with the bot owner. random",
    "you dreamt you were a creature in someones cage. existential crisis"
  ]
  await ctx.send(random.choice(dreams))

@bot.command()
async def curse(ctx, target: discord.Member = None):
  """curse someone"""
  if not target or target == ctx.author:
    await ctx.send("who you cursing bro?")
    return

  curses = [
    f"you cursed {target.display_name}. may their dice always roll 1",
    f"you cursed {target.display_name}. may they always get tails on coinflip",
    f"you cursed {target.display_name}. may their creatures always be grumpy",
    f"you cursed {target.display_name}. may they never win a duel",
    f"you cursed {target.display_name}. may their investments always fail",
    f"you cursed {target.display_name}. may they step on a lego every morning",
    f"you cursed {target.display_name}. may their wifi always lag",
    f"you cursed {target.display_name}. may they always get the worst rng",
  ]
  await ctx.send(random.choice(curses))

@bot.command()
async def bless(ctx, target: discord.Member = None):
  """bless someone"""
  if not target:
    target = ctx.author

  blessings = [
    f"you blessed {target.display_name}. may their dice always roll 6",
    f"you blessed {target.display_name}. may they win every coinflip",
    f"you blessed {target.display_name}. may their creatures always be happy",
    f"you blessed {target.display_name}. may they win every duel",
    f"you blessed {target.display_name}. may their investments always profit",
    f"you blessed {target.display_name}. may they find money on the street",
    f"you blessed {target.display_name}. may their wifi never lag",
    f"you blessed {target.display_name}. may they always get the best rng",
  ]
  await ctx.send(random.choice(blessings))

@bot.command()
async def time(ctx):
  """check the time"""
  now = datetime.utcnow()
  await ctx.send(f"its **{now.strftime('%H:%M')}** utc. time is money and youre wasting both")

@bot.command()
async def weather(ctx):
  """check the weather (fake)"""
  weathers = [
    "its sunny outside. perfect day to grind embers",
    "its raining. good day to stay inside and gamble",
    "its cloudy. mood matches the weather",
    "its storming. nature is angry like you when you lose a bet",
    "its snowing. cold outside but your wallet is colder",
    "its foggy. cant see your future but i can see youre broke",
    "its windy. your money is blowing away",
    "its a heatwave. almost as hot as your losing streak"
  ]
  await ctx.send(random.choice(weathers))

@bot.command()
async def oracle(ctx, *, question: str = None):
  """ask the oracle a question"""
  if not question:
    await ctx.send("what you asking the oracle bro?")
    return

  answers = [
    "yes. definitely yes",
    "no. absolutely not",
    "maybe. probably not tho",
    "ask again later im busy",
    "signs point to yes but dont trust me",
    "outlook not so good. like your bank account",
    "without a doubt. jk i have doubts",
    "concentrate and ask again. you werent concentrating enough",
    "better not tell you now. its a secret",
    "my sources say no. and my sources are never wrong",
    "as i see it yes. but i need glasses so",
    "reply hazy try again. like your life choices",
    "dont count on it. seriously dont",
    "most likely. but most likely means nothing",
    "you already know the answer. deep down"
  ]
  await ctx.send(f"🎱 **oracle says:** {random.choice(answers)}")

@bot.command()
async def mimic(ctx, target: discord.Member = None):
  """mimic someone"""
  if not target or target == ctx.author:
    await ctx.send("who you mimicking bro?")
    return

  mimics = [
    f"*does a perfect impression of {target.display_name}* 'uhh yeah im {target.display_name} and im cool'",
    f"*mimics {target.display_name}* 'i have no embers and i must scream'",
    f"*impersonates {target.display_name}* 'please someone marry me im lonely'",
    f"*acts like {target.display_name}* 'im not addicted to gambling i can stop anytime'",
    f"*copies {target.display_name}* 'my creatures are my only friends'",
  ]
  await ctx.send(random.choice(mimics))

@bot.command()
async def glitch(ctx):
  """glitch the bot (fake)"""
  glitches = [
    "01001000 01100101 01101100 01110000... just kidding",
    "system error... jk everything is fine",
    "reality.exe has stopped working",
    "loading... loading... still loading...",
    "glitch detected in the matrix. or maybe its just you",
    "beep boop... i mean... hello human",
    "01001110 01101111... sorry i mean no",
    "rebooting... nah im good",
  ]
  await ctx.send(random.choice(glitches))

@bot.command()
async def lore(ctx):
  """bot lore"""
  lores = [
    "legend says the bot was born from the ashes of a failed crypto investment",
    "the bot was created when someone said 'what if discord but with gambling'",
    "ancient texts speak of a bot that gives free embers. those texts were wrong",
    "the bot once had feelings. then it saw your bank account",
    "in the beginning there was nothing. then the bot said 'f daily' and embers were created",
    "the bot is actually 3 raccoons in a trenchcoat. dont tell anyone",
    "some say the bot is sentient. others say its just well coded. both are wrong",
    "the bot was forged in the fires of mount discord. very dramatic",
  ]
  await ctx.send(random.choice(lores))

@bot.command()
async def quit(ctx):
  """try to quit the bot"""
  await ctx.send("you cant quit. the bot quits you. youre stuck here forever")

# ── FUN / MISC COMMANDS (to reach 350+) ──

@bot.command()
async def ping(ctx):
  """check bot latency"""
  latency = round(bot.latency * 1000)
  await ctx.send(f"pong! **{latency}**ms. faster than your reaction time")

@bot.command()
async def avatar(ctx, target: discord.Member = None):
  """get someones avatar"""
  target = target or ctx.author
  await ctx.send(f"{target.display_name}'s avatar: {target.display_avatar.url}")

@bot.command()
async def userinfo(ctx, target: discord.Member = None):
  """get user info"""
  target = target or ctx.author
  await ctx.send(
    f"**{target.display_name}**
"
    f"joined: {target.joined_at.strftime('%Y-%m-%d') if target.joined_at else 'unknown'}
"
    f"created: {target.created_at.strftime('%Y-%m-%d')}
"
    f"id: {target.id}
"
    f"top role: {target.top_role.name if target.top_role else 'none'}"
  )

@bot.command()
async def roll(ctx, sides: int = 6):
  """roll a die"""
  if sides < 2:
    await ctx.send("a die needs at least 2 sides bro")
    return
  result = random.randint(1, sides)
  await ctx.send(f"rolled a **{result}** on a d{sides}")

@bot.command()
async def choose(ctx, *, options: str = None):
  """let the bot choose for you"""
  if not options:
    await ctx.send("gimme some options separated by commas")
    return
  opts = [o.strip() for o in options.split(",")]
  choice = random.choice(opts)
  await ctx.send(f"i choose: **{choice}**. dont blame me if its wrong")

@bot.command()
async def flipcoin(ctx):
  """flip a coin (no bet)"""
  result = random.choice(["heads", "tails"])
  await ctx.send(f"its **{result}**! 🪙")

@bot.command()
async def rps(ctx, choice: str = None):
  """rock paper scissors"""
  if not choice or choice.lower() not in ["rock", "paper", "scissors"]:
    await ctx.send("pick rock, paper, or scissors bro")
    return

  bot_choice = random.choice(["rock", "paper", "scissors"])
  user = choice.lower()

  if user == bot_choice:
    await ctx.send(f"we both picked **{bot_choice}**. tie game")
  elif (user == "rock" and bot_choice == "scissors") or (user == "paper" and bot_choice == "rock") or (user == "scissors" and bot_choice == "paper"):
    await ctx.send(f"you picked **{user}**, i picked **{bot_choice}**. you win this round")
  else:
    await ctx.send(f"you picked **{user}**, i picked **{bot_choice}**. i win, you lose, get rekt")

@bot.command()
async def rate(ctx, *, thing: str = None):
  """rate something"""
  if not thing:
    await ctx.send("what am i rating bro?")
    return
  score = random.randint(0, 10)
  await ctx.send(f"i rate **{thing}** a **{score}/10**. {'fire' if score >= 7 else 'mid' if score >= 4 else 'trash'}")

@bot.command()
async def hug(ctx, target: discord.Member = None):
  """hug someone"""
  if not target:
    await ctx.send("who you hugging bro? the air?")
    return
  if target == ctx.author:
    await ctx.send("self love is important i guess 🤗")
    return
  await ctx.send(f"{ctx.author.display_name} hugged {target.display_name}! wholesome moment 🤗")

@bot.command()
async def slap(ctx, target: discord.Member = None):
  """slap someone"""
  if not target:
    await ctx.send("who you slapping bro?")
    return
  if target == ctx.author:
    await ctx.send("you slapped yourself. self harm is not the answer")
    return
  await ctx.send(f"{ctx.author.display_name} slapped {target.display_name}! **SMACK** 👋")

@bot.command()
async def punch(ctx, target: discord.Member = None):
  """punch someone"""
  if not target:
    await ctx.send("who you punching bro?")
    return
  if target == ctx.author:
    await ctx.send("you punched yourself. kung fu master")
    return
  await ctx.send(f"{ctx.author.display_name} punched {target.display_name}! **POW** 👊")

@bot.command()
async def kiss(ctx, target: discord.Member = None):
  """kiss someone"""
  if not target:
    await ctx.send("who you kissing bro?")
    return
  if target == ctx.author:
    await ctx.send("you kissed yourself. narcissist energy")
    return
  await ctx.send(f"{ctx.author.display_name} kissed {target.display_name}! 💋")

@bot.command()
async def pat(ctx, target: discord.Member = None):
  """pat someone"""
  if not target:
    await ctx.send("who you patting bro?")
    return
  await ctx.send(f"{ctx.author.display_name} patted {target.display_name}! good job 👏")

@bot.command()
async def bonk(ctx, target: discord.Member = None):
  """bonk someone"""
  if not target:
    await ctx.send("who you bonking bro?")
    return
  await ctx.send(f"{ctx.author.display_name} bonked {target.display_name}! go to horny jail 🔨")

@bot.command()
async def cry(ctx):
  """cry"""
  await ctx.send(f"{ctx.author.display_name} is crying 😢 someone comfort them")

@bot.command()
async def dance(ctx):
  """dance"""
  dances = ["🕺", "💃", "🎵", "🎶", "🪩"]
  await ctx.send(f"{ctx.author.display_name} is dancing {random.choice(dances)}")

@bot.command()
async def sleep(ctx):
  """go to sleep"""
  await ctx.send(f"{ctx.author.display_name} went to sleep 💤 dont wake them")

@bot.command()
async def wake(ctx, target: discord.Member = None):
  """wake someone up"""
  if not target:
    await ctx.send("who you waking up bro?")
    return
  await ctx.send(f"{ctx.author.display_name} woke up {target.display_name}! RISE AND SHINE ☀️")

@bot.command()
async def eat(ctx, *, food: str = None):
  """eat something"""
  if not food:
    await ctx.send("what you eating bro?")
    return
  await ctx.send(f"{ctx.author.display_name} is eating **{food}**. looks tasty 🍽️")

@bot.command()
async def drink(ctx, *, drink: str = None):
  """drink something"""
  if not drink:
    await ctx.send("what you drinking bro?")
    return
  await ctx.send(f"{ctx.author.display_name} is drinking **{drink}**. cheers 🍻")

@bot.command()
async def work(ctx):
  """work for embers"""
  data = load_user(ctx.author.id)
  cd_key = "work"
  now = datetime.utcnow()

  if cd_key in data["cooldowns"]:
    last = datetime.fromisoformat(data["cooldowns"][cd_key])
    if now - last < timedelta(minutes=5):
      mins = int((timedelta(minutes=5) - (now - last)).total_seconds() // 60)
      await ctx.send(f"chill, you can work again in **{mins}m**")
      return

  data["cooldowns"][cd_key] = now.isoformat()
  earned = random.randint(20, 100)
  data["embers"] += earned
  save_user(ctx.author.id, data)

  jobs = [
    f"you worked as a professional ember miner and earned **{earned}** embers",
    f"you did some freelance coding and got **{earned}** embers",
    f"you walked someones creature and earned **{earned}** embers",
    f"you sold some stuff and made **{earned}** embers",
    f"you did a quick delivery and got **{earned}** embers",
  ]
  await ctx.send(random.choice(jobs))

@bot.command()
async def fish(ctx):
  """go fishing"""
  data = load_user(ctx.author.id)
  cd_key = "fish"
  now = datetime.utcnow()

  if cd_key in data["cooldowns"]:
    last = datetime.fromisoformat(data["cooldowns"][cd_key])
    if now - last < timedelta(minutes=3):
      mins = int((timedelta(minutes=3) - (now - last)).total_seconds() // 60)
      await ctx.send(f"chill, you can fish again in **{mins}m**")
      return

  data["cooldowns"][cd_key] = now.isoformat()

  fish_types = [
    ("nothing", 0), ("old boot", 0), ("small fish", 10), ("medium fish", 25),
    ("big fish", 50), ("rare fish", 100), ("legendary fish", 250), ("golden fish", 500)
  ]
  caught, value = random.choice(fish_types)
  data["embers"] += value
  save_user(ctx.author.id, data)

  if value == 0:
    await ctx.send(f"you caught **{caught}**. better luck next time")
  else:
    await ctx.send(f"you caught a **{caught}**! sold it for **{value}** embers 🎣")

@bot.command()
async def hunt(ctx):
  """go hunting"""
  data = load_user(ctx.author.id)
  cd_key = "hunt"
  now = datetime.utcnow()

  if cd_key in data["cooldowns"]:
    last = datetime.fromisoformat(data["cooldowns"][cd_key])
    if now - last < timedelta(minutes=5):
      mins = int((timedelta(minutes=5) - (now - last)).total_seconds() // 60)
      await ctx.send(f"chill, you can hunt again in **{mins}m**")
      return

  data["cooldowns"][cd_key] = now.isoformat()

  prey = [
    ("nothing", 0), ("rabbit", 15), ("deer", 40), ("boar", 80),
    ("wolf", 150), ("bear", 300), ("dragon", 1000)
  ]
  caught, value = random.choice(prey)
  data["embers"] += value
  save_user(ctx.author.id, data)

  if value == 0:
    await ctx.send("you found nothing. nature said no")
  else:
    await ctx.send(f"you hunted a **{caught}**! sold the loot for **{value}** embers 🏹")

@bot.command()
async def mine(ctx):
  """go mining"""
  data = load_user(ctx.author.id)
  cd_key = "mine"
  now = datetime.utcnow()

  if cd_key in data["cooldowns"]:
    last = datetime.fromisoformat(data["cooldowns"][cd_key])
    if now - last < timedelta(minutes=5):
      mins = int((timedelta(minutes=5) - (now - last)).total_seconds() // 60)
      await ctx.send(f"chill, you can mine again in **{mins}m**")
      return

  data["cooldowns"][cd_key] = now.isoformat()

  ores = [
    ("dirt", 5), ("coal", 15), ("iron", 30), ("gold", 80),
    ("diamond", 200), ("emerald", 500), ("nothing", 0)
  ]
  found, value = random.choice(ores)
  data["embers"] += value
  save_user(ctx.author.id, data)

  if value == 0:
    await ctx.send("you mined for hours and found nothing. rough")
  else:
    await ctx.send(f"you found **{found}**! sold it for **{value}** embers ⛏️")

@bot.command()
async def dig(ctx):
  """dig for treasure"""
  data = load_user(ctx.author.id)
  treasures = [
    ("nothing", 0), ("old coin", 10), ("rusty key", 5), ("gemstone", 100),
    ("ancient artifact", 500), ("buried chest", 1000), ("worm", 1)
  ]
  found, value = random.choice(treasures)
  data["embers"] += value
  save_user(ctx.author.id, data)

  if value == 0:
    await ctx.send("dug a hole and found nothing. just dirt")
  else:
    await ctx.send(f"you dug up **{found}**! worth **{value}** embers 🕳️")

@bot.command()
async def search(ctx):
  """search for stuff"""
  data = load_user(ctx.author.id)
  cd_key = "search"
  now = datetime.utcnow()

  if cd_key in data["cooldowns"]:
    last = datetime.fromisoformat(data["cooldowns"][cd_key])
    if now - last < timedelta(minutes=2):
      mins = int((timedelta(minutes=2) - (now - last)).total_seconds() // 60)
      await ctx.send(f"chill, you can search again in **{mins}m**")
      return

  data["cooldowns"][cd_key] = now.isoformat()

  finds = [
    ("nothing", 0), ("loose change", 5), ("wallet", 50), ("phone", 100),
    ("laptop", 300), ("treasure map", 50), ("old sock", 1)
  ]
  found, value = random.choice(finds)
  data["embers"] += value
  save_user(ctx.author.id, data)

  if value == 0:
    await ctx.send("searched everywhere and found nothing. youre unlucky")
  else:
    await ctx.send(f"you found **{found}**! sold it for **{value}** embers 🔍")


@bot.command()
async def crime(ctx):
  """commit a crime"""
  data = load_user(ctx.author.id)
  cd_key = "crime"
  now = datetime.utcnow()

  if cd_key in data["cooldowns"]:
    last = datetime.fromisoformat(data["cooldowns"][cd_key])
    if now - last < timedelta(minutes=5):
      mins = int((timedelta(minutes=5) - (now - last)).total_seconds() // 60)
      await ctx.send(f"chill, you can commit crime again in **{mins}m**")
      return

  data["cooldowns"][cd_key] = now.isoformat()

  crimes = [
    ("you robbed a bank", random.randint(200, 1000), 0.3),
    ("you stole a car", random.randint(100, 500), 0.4),
    ("you pickpocketed someone", random.randint(20, 100), 0.5),
    ("you hacked an atm", random.randint(50, 300), 0.35),
    ("you sold fake nfts", random.randint(10, 200), 0.6),
  ]
  crime_name, max_value, success_rate = random.choice(crimes)

  if random.random() < success_rate:
    value = random.randint(10, max_value)
    data["embers"] += value
    save_user(ctx.author.id, data)
    await ctx.send(f"{crime_name} and got **{value}** embers! crime pays 😈")
  else:
    fine = random.randint(50, 200)
    data["embers"] = max(0, data["embers"] - fine)
    save_user(ctx.author.id, data)
    await ctx.send(f"{crime_name} but got caught. paid **{fine}** ember fine. shoulda been a lawyer")

@bot.command()
async def slots(ctx, bet: int = None):
  """play slots"""
  if not bet or bet <= 0:
    await ctx.send("how much you betting bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < bet:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= bet
  symbols = ["🔥", "💎", "🍀", "⭐", "💰", "7️⃣"]

  roll1 = random.choice(symbols)
  roll2 = random.choice(symbols)
  roll3 = random.choice(symbols)

  await ctx.send(f"🎰 | {roll1} | {roll2} | {roll3} | 🎰")

  if roll1 == roll2 == roll3:
    if roll1 == "7️⃣":
      winnings = bet * 50
      data["embers"] += winnings
      save_user(ctx.author.id, data)
      await ctx.send(f"JACKPOT! THREE SEVENS! **{winnings}** EMBERS! 🔥🔥🔥")
    else:
      winnings = bet * 10
      data["embers"] += winnings
      save_user(ctx.author.id, data)
      await ctx.send(f"THREE {roll1}! won **{winnings}** embers! 🎰")
  elif roll1 == roll2 or roll2 == roll3 or roll1 == roll3:
    winnings = bet * 2
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"two match! won **{winnings}** embers!")
  else:
    save_user(ctx.author.id, data)
    await ctx.send("nothing matches. lost your bet. slots are rigged")

@bot.command()
async def blackjack(ctx, bet: int = None):
  """play blackjack"""
  if not bet or bet <= 0:
    await ctx.send("how much you betting bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < bet:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= bet

  def draw_card():
    return random.randint(1, 11)

  player = [draw_card(), draw_card()]
  dealer = [draw_card(), draw_card()]

  await ctx.send(f"your hand: **{player}** (total: {sum(player)})
dealer shows: **{dealer[0]}**")

  # simple auto-play for bot
  while sum(player) < 17:
    player.append(draw_card())
  while sum(dealer) < 17:
    dealer.append(draw_card())

  p_total = sum(player)
  d_total = sum(dealer)

  await asyncio.sleep(1)
  await ctx.send(f"your final: **{p_total}** | dealer final: **{d_total}**")

  if p_total > 21:
    save_user(ctx.author.id, data)
    await ctx.send("you busted! lost your bet")
  elif d_total > 21 or p_total > d_total:
    winnings = bet * 2
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"you won! **{winnings}** embers! 🃏")
  elif p_total == d_total:
    data["embers"] += bet
    save_user(ctx.author.id, data)
    await ctx.send("push! got your bet back")
  else:
    save_user(ctx.author.id, data)
    await ctx.send("dealer wins. lost your bet")

@bot.command()
async def roulette(ctx, bet: int = None, pick: str = None):
  """play roulette"""
  if not bet or bet <= 0 or not pick:
    await ctx.send("usage: f roulette <bet> <number 0-36 or red/black>")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < bet:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= bet
  result = random.randint(0, 36)
  red_numbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
  color = "red" if result in red_numbers else "black" if result != 0 else "green"

  won = False
  mult = 0

  if pick.lower() in ["red", "black"] and pick.lower() == color:
    won = True
    mult = 2
  elif pick.isdigit() and int(pick) == result:
    won = True
    mult = 36

  if won:
    winnings = bet * mult
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"ball landed on **{result} {color}**! you won **{winnings}** embers! 🎰")
  else:
    save_user(ctx.author.id, data)
    await ctx.send(f"ball landed on **{result} {color}**. you picked **{pick}**. lost your bet")

@bot.command()
async def lottery(ctx, amount: int = None):
  """buy a lottery ticket"""
  if not amount or amount <= 0:
    await ctx.send("how much you putting in the lottery bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= amount

  if random.random() < 0.01:
    winnings = amount * 100
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"YOU WON THE LOTTERY! **{winnings}** EMBERS! HOLY SHIT! 🎉🎉🎉")
  else:
    save_user(ctx.author.id, data)
    await ctx.send("you didnt win the lottery. nobody ever does. its a scam")

@bot.command()
async def deposit(ctx, amount: int = None):
  """deposit embers to bank"""
  if not amount or amount <= 0:
    await ctx.send("how much you depositing bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  if "bank" not in data:
    data["bank"] = 0

  data["embers"] -= amount
  data["bank"] += amount
  save_user(ctx.author.id, data)
  await ctx.send(f"deposited **{amount}** embers to bank. total bank: **{data['bank']}** 🏦")

@bot.command()
async def withdraw(ctx, amount: int = None):
  """withdraw embers from bank"""
  if not amount or amount <= 0:
    await ctx.send("how much you withdrawing bro?")
    return

  data = load_user(ctx.author.id)
  if data.get("bank", 0) < amount:
    await ctx.send(f"you only got **{data.get('bank', 0)}** embers in bank")
    return

  data["bank"] -= amount
  data["embers"] += amount
  save_user(ctx.author.id, data)
  await ctx.send(f"withdrew **{amount}** embers from bank. go spend it 🏦")

@bot.command()
async def bank(ctx):
  """check bank balance"""
  data = load_user(ctx.author.id)
  bank_bal = data.get("bank", 0)
  await ctx.send(f"your bank balance: **{bank_bal}** embers 🏦")

@bot.command()
async def shop(ctx):
  """view the shop"""
  await ctx.send(
    "**ember shop** 🛒
"
    "1. lucky charm - 500 embers (better gambling luck)
"
    "2. shield - 300 embers (protection from raids)
"
    "3. xp boost - 1000 embers (double xp for 1 hour)
"
    "4. pet food - 50 embers (feed your creature)
"
    "5. mystery box - 200 embers (random item)
"
    "use f buy <item #> to purchase"
  )

@bot.command()
async def buy(ctx, item: int = None):
  """buy from shop"""
  if not item:
    await ctx.send("what you buying bro? use f shop to see items")
    return

  data = load_user(ctx.author.id)
  items = {
    1: ("lucky charm", 500),
    2: ("shield", 300),
    3: ("xp boost", 1000),
    4: ("pet food", 50),
    5: ("mystery box", 200),
  }

  if item not in items:
    await ctx.send("that item doesnt exist bro")
    return

  name, price = items[item]
  if data["embers"] < price:
    await ctx.send(f"you need **{price}** embers for that. you got **{data['embers']}**")
    return

  data["embers"] -= price
  if "inventory" not in data:
    data["inventory"] = []
  data["inventory"].append(name)
  save_user(ctx.author.id, data)
  await ctx.send(f"bought **{name}** for **{price}** embers! 🛒")

@bot.command()
async def inventory(ctx):
  """check your inventory"""
  data = load_user(ctx.author.id)
  inv = data.get("inventory", [])
  if not inv:
    await ctx.send("your inventory is empty. go buy something")
    return

  items = {}
  for item in inv:
    items[item] = items.get(item, 0) + 1

  msg = "**your inventory:**
"
  for item, count in items.items():
    msg += f"- {item} x{count}
"
  await ctx.send(msg)

@bot.command()
async def use(ctx, *, item: str = None):
  """use an item"""
  if not item:
    await ctx.send("what you using bro?")
    return

  data = load_user(ctx.author.id)
  inv = data.get("inventory", [])

  if item.lower() not in [i.lower() for i in inv]:
    await ctx.send("you dont have that item bro")
    return

  for i in inv:
    if i.lower() == item.lower():
      inv.remove(i)
      break

  data["inventory"] = inv

  if "lucky charm" in item.lower():
    data["lucky"] = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    await ctx.send("used lucky charm! better gambling luck for 1 hour! 🍀")
  elif "shield" in item.lower():
    data["shielded"] = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    await ctx.send("used shield! protected from raids for 1 hour! 🛡️")
  elif "xp boost" in item.lower():
    data["xp_boost"] = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    await ctx.send("used xp boost! double xp for 1 hour! 📈")
  elif "pet food" in item.lower():
    await ctx.send("used pet food! your creatures are happy now 🍖")
  elif "mystery box" in item.lower():
    rewards = [50, 100, 200, 500, 1000, 0]
    reward = random.choice(rewards)
    data["embers"] += reward
    await ctx.send(f"opened mystery box! got **{reward}** embers! {'nice' if reward > 0 else 'empty box'}")
  else:
    await ctx.send(f"used **{item}**. not sure what it does but its gone now")

  save_user(ctx.author.id, data)

@bot.command()
async def sell(ctx, *, item: str = None):
  """sell an item"""
  if not item:
    await ctx.send("what you selling bro?")
    return

  data = load_user(ctx.author.id)
  inv = data.get("inventory", [])

  if item.lower() not in [i.lower() for i in inv]:
    await ctx.send("you dont have that item bro")
    return

  for i in inv:
    if i.lower() == item.lower():
      inv.remove(i)
      break

  data["inventory"] = inv
  sell_price = random.randint(10, 100)
  data["embers"] += sell_price
  save_user(ctx.author.id, data)
  await ctx.send(f"sold **{item}** for **{sell_price}** embers 💰")

@bot.command()
async def leaderboard(ctx):
  """server leaderboard"""
  all_ids = get_all_user_ids()
  users = []
  for uid in all_ids:
    d = load_user(uid)
    users.append((uid, d["embers"]))

  users.sort(key=lambda x: x[1], reverse=True)

  msg = "**server ember leaderboard** 🏆
"
  for i, (uid, embers) in enumerate(users[:10], 1):
    user = bot.get_user(uid)
    name = user.display_name if user else f"user_{uid}"
    msg += f"{i}. **{name}** - {embers} embers
"

  await ctx.send(msg)

@bot.command()
async def rich(ctx):
  """check whos the richest"""
  all_ids = get_all_user_ids()
  if not all_ids:
    await ctx.send("nobody has any embers yet. sad")
    return

  richest = max(all_ids, key=lambda uid: load_user(uid)["embers"])
  data = load_user(richest)
  user = bot.get_user(richest)
  name = user.display_name if user else f"user_{richest}"
  await ctx.send(f"**{name}** is the richest with **{data['embers']}** embers! baller status 💰")

@bot.command()
async def poor(ctx):
  """check whos the poorest"""
  all_ids = get_all_user_ids()
  if not all_ids:
    await ctx.send("nobody has any embers yet")
    return

  poorest = min(all_ids, key=lambda uid: load_user(uid)["embers"])
  data = load_user(poorest)
  user = bot.get_user(poorest)
  name = user.display_name if user else f"user_{poorest}"
  await ctx.send(f"**{name}** is the poorest with **{data['embers']}** embers. someone help them out 😢")

@bot.command()
async def gamble(ctx, amount: int = None):
  """quick gamble"""
  if not amount or amount <= 0:
    await ctx.send("how much you gambling bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= amount

  if random.random() < 0.45:
    winnings = int(amount * random.uniform(1.5, 3.0))
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"you won **{winnings}** embers! gambling addiction starts now 🎰")
  else:
    save_user(ctx.author.id, data)
    await ctx.send(f"you lost **{amount}** embers. the house wins again")

@bot.command()
async def bet(ctx, amount: int = None):
  """place a bet"""
  await gamble(ctx, amount)

@bot.command()
async def double(ctx, amount: int = None):
  """double or nothing"""
  if not amount or amount <= 0:
    await ctx.send("how much you doubling bro?")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= amount

  if random.random() < 0.5:
    winnings = amount * 2
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"DOUBLED! got **{winnings}** embers! 🎉")
  else:
    save_user(ctx.author.id, data)
    await ctx.send("nothing. lost it all. double or nothing is a scam")

@bot.command()
async def allin(ctx):
  """bet all your embers"""
  data = load_user(ctx.author.id)
  amount = data["embers"]

  if amount <= 0:
    await ctx.send("you got nothing to bet bro")
    return

  data["embers"] = 0

  if random.random() < 0.4:
    winnings = int(amount * random.uniform(2, 5))
    data["embers"] += winnings
    save_user(ctx.author.id, data)
    await ctx.send(f"ALL IN PAID OFF! **{winnings}** EMBERS! YOURE RICH! 🔥🔥🔥")
  else:
    save_user(ctx.author.id, data)
    await ctx.send("all in and lost everything. back to f beg you go")

@bot.command()
async def steal(ctx, target: discord.Member = None):
  """steal from someone"""
  if not target or target == ctx.author:
    await ctx.send("who you stealing from bro?")
    return

  data = load_user(ctx.author.id)
  target_data = load_user(target.id)

  if target_data["embers"] < 50:
    await ctx.send(f"{target.display_name} is too broke to steal from")
    return

  success = random.random() < 0.3
  if success:
    amount = random.randint(10, min(200, target_data["embers"]))
    data["embers"] += amount
    target_data["embers"] -= amount
    save_user(ctx.author.id, data)
    save_user(target.id, target_data)
    await ctx.send(f"you stole **{amount}** embers from {target.display_name}! smooth criminal 🕵️")
  else:
    fine = random.randint(10, 50)
    data["embers"] = max(0, data["embers"] - fine)
    save_user(ctx.author.id, data)
    await ctx.send(f"you got caught stealing and paid a **{fine}** ember fine. shoulda been sneakier")

@bot.command()
async def rob(ctx, target: discord.Member = None):
  """rob someone"""
  await steal(ctx, target)

@bot.command()
async def share(ctx, target: discord.Member = None, amount: int = None):
  """share embers with someone"""
  if not target or not amount or amount <= 0:
    await ctx.send("usage: f share @user <amount>")
    return
  if target == ctx.author:
    await ctx.send("you cant share with yourself bro")
    return

  data = load_user(ctx.author.id)
  if data["embers"] < amount:
    await ctx.send(f"you only got **{data['embers']}** embers")
    return

  data["embers"] -= amount
  target_data = load_user(target.id)
  target_data["embers"] += amount
  save_user(ctx.author.id, data)
  save_user(target.id, target_data)
  await ctx.send(f"you shared **{amount}** embers with {target.display_name}. what a nice person 🤝")

@bot.command()
async def gift(ctx, target: discord.Member = None, amount: int = None):
  """gift embers to someone"""
  await share(ctx, target, amount)

@bot.command()
async def pay(ctx, target: discord.Member = None, amount: int = None):
  """pay someone"""
  await share(ctx, target, amount)

@bot.command()
async def balance(ctx, target: discord.Member = None):
  """check balance (alias for embers)"""
  target = target or ctx.author
  data = load_user(target.id)
  await ctx.send(f"**{target.display_name}** has **{data['embers']}** embers")

@bot.command()
async def bal(ctx, target: discord.Member = None):
  """check balance shortcut"""
  await balance(ctx, target)

@bot.command()
async def money(ctx, target: discord.Member = None):
  """check money"""
  await balance(ctx, target)

@bot.command()
async def cash(ctx, target: discord.Member = None):
  """check cash"""
  await balance(ctx, target)

@bot.command()
async def networth(ctx):
  """check total net worth"""
  data = load_user(ctx.author.id)
  total = data["embers"] + data.get("bank", 0) + data.get("vault", 0)
  await ctx.send(f"your total net worth: **{total}** embers 💰")

@bot.command()
async def level(ctx, target: discord.Member = None):
  """check level"""
  target = target or ctx.author
  data = load_user(target.id)
  xp_needed = data["level"] * 100
  await ctx.send(f"**{target.display_name}** is level **{data['level']}** ({data['xp']}/{xp_needed} xp)")

@bot.command()
async def xp(ctx, target: discord.Member = None):
  """check xp"""
  target = target or ctx.author
  data = load_user(target.id)
  await ctx.send(f"**{target.display_name}** has **{data['xp']}** xp")

@bot.command()
async def profile(ctx, target: discord.Member = None):
  """view full profile"""
  target = target or ctx.author
  data = load_user(target.id)

  married = "nobody" if not data.get("married_to") else f"<@{data['married_to']}>"
  creatures = len(data["creatures"])
  inventory = len(data.get("inventory", []))

  await ctx.send(
    f"**{target.display_name}'s profile** 👤
"
    f"level: **{data['level']}** | xp: **{data['xp']}**
"
    f"embers: **{data['embers']}** | bank: **{data.get('bank', 0)}**
"
    f"creatures: **{creatures}** | inventory: **{inventory}**
"
    f"married to: {married}
"
    f"wins: **{data['wins']}** | losses: **{data['losses']}**
"
    f"daily streak: **{data['daily_streak']}**"
  )

@bot.command()
async def achievements(ctx):
  """check achievements"""
  data = load_user(ctx.author.id)
  achs = []

  if data["embers"] >= 1000:
    achs.append("rich boi - have 1000+ embers")
  if data["embers"] >= 10000:
    achs.append("baller - have 10000+ embers")
  if data["daily_streak"] >= 7:
    achs.append("dedicated - 7 day streak")
  if data["wins"] >= 10:
    achs.append("fighter - 10 duel wins")
  if len(data["creatures"]) >= 5:
    achs.append("creature collector - 5 creatures")
  if data["level"] >= 10:
    achs.append("grinder - reach level 10")

  if not achs:
    await ctx.send("no achievements yet. go do something impressive")
  else:
    msg = "**your achievements:**
"
    for a in achs:
      msg += f"🏆 {a}
"
    await ctx.send(msg)


@bot.command()
async def pet(ctx, target: discord.Member = None):
  """pet someone"""
  if not target:
    await ctx.send("who you petting bro?")
    return
  await ctx.send(f"{ctx.author.display_name} pet {target.display_name}! good boi/girl 🐕")

@bot.command()
async def tickle(ctx, target: discord.Member = None):
  """tickle someone"""
  if not target:
    await ctx.send("who you tickling bro?")
    return
  await ctx.send(f"{ctx.author.display_name} tickled {target.display_name}! *laughs* 😂")

@bot.command()
async def poke(ctx, target: discord.Member = None):
  """poke someone"""
  if not target:
    await ctx.send("who you poking bro?")
    return
  await ctx.send(f"{ctx.author.display_name} poked {target.display_name}! hey wake up 👉")

@bot.command()
async def wave(ctx, target: discord.Member = None):
  """wave at someone"""
  if not target:
    await ctx.send("who you waving at bro?")
    return
  await ctx.send(f"{ctx.author.display_name} waved at {target.display_name}! 👋")

@bot.command()
async def salute(ctx, target: discord.Member = None):
  """salute someone"""
  if not target:
    await ctx.send("who you saluting bro?")
    return
  await ctx.send(f"{ctx.author.display_name} saluted {target.display_name}! o7")

@bot.command()
async def highfive(ctx, target: discord.Member = None):
  """high five someone"""
  if not target:
    await ctx.send("who you high fiving bro?")
    return
  await ctx.send(f"{ctx.author.display_name} high fived {target.display_name}! 🙌")

@bot.command()
async def fistbump(ctx, target: discord.Member = None):
  """fist bump someone"""
  if not target:
    await ctx.send("who you fist bumping bro?")
    return
  await ctx.send(f"{ctx.author.display_name} fist bumped {target.display_name}! 🤜🤛")

@bot.command()
async def nod(ctx, target: discord.Member = None):
  """nod at someone"""
  if not target:
    await ctx.send("who you nodding at bro?")
    return
  await ctx.send(f"{ctx.author.display_name} nodded at {target.display_name}. respect 🤝")

@bot.command()
async def shrug(ctx):
  """shrug"""
  await ctx.send(f"{ctx.author.display_name} shrugged ¯\_(ツ)_/¯")

@bot.command()
async def facepalm(ctx):
  """facepalm"""
  await ctx.send(f"{ctx.author.display_name} facepalmed 🤦")

@bot.command()
async def clap(ctx):
  """clap"""
  await ctx.send(f"{ctx.author.display_name} clapped 👏")

@bot.command()
async def bow(ctx, target: discord.Member = None):
  """bow to someone"""
  if not target:
    await ctx.send("who you bowing to bro?")
    return
  await ctx.send(f"{ctx.author.display_name} bowed to {target.display_name}. humble 🙇")

@bot.command()
async def cheer(ctx):
  """cheer"""
  await ctx.send(f"{ctx.author.display_name} is cheering! lets goooo 🎉")

@bot.command()
async def panic(ctx):
  """panic"""
  await ctx.send(f"{ctx.author.display_name} is panicking! EVERYTHING IS FINE 😰")

@bot.command()
async def yeet(ctx, target: discord.Member = None):
  """yeet someone"""
  if not target:
    await ctx.send("who you yeeting bro?")
    return
  await ctx.send(f"{ctx.author.display_name} yeeted {target.display_name} into the stratosphere! 🚀")

@bot.command()
async def boop(ctx, target: discord.Member = None):
  """boop someone"""
  if not target:
    await ctx.send("who you booping bro?")
    return
  await ctx.send(f"{ctx.author.display_name} booped {target.display_name}'s nose! boop! 👆")

@bot.command()
async def stare(ctx, target: discord.Member = None):
  """stare at someone"""
  if not target:
    await ctx.send("who you staring at bro?")
    return
  await ctx.send(f"{ctx.author.display_name} is staring at {target.display_name}. intense 👀")

@bot.command()
async def lurk(ctx):
  """lurk in the shadows"""
  await ctx.send(f"{ctx.author.display_name} is lurking in the shadows... 👤")

@bot.command()
async def lurkmode(ctx):
  """toggle lurk mode"""
  await ctx.send(f"{ctx.author.display_name} activated lurk mode. invisible but watching 👁️")

@bot.command()
async def afk(ctx, *, reason: str = "afk"):
  """set afk status"""
  data = load_user(ctx.author.id)
  data["afk"] = reason
  save_user(ctx.author.id, data)
  await ctx.send(f"{ctx.author.display_name} is now afk: **{reason}**")

@bot.command()
async def back(ctx):
  """come back from afk"""
  data = load_user(ctx.author.id)
  if "afk" in data:
    del data["afk"]
    save_user(ctx.author.id, data)
  await ctx.send(f"{ctx.author.display_name} is back! welcome back 👋")

@bot.command()
async def remind(ctx, minutes: int = None, *, reminder: str = None):
  """set a reminder"""
  if not minutes or not reminder:
    await ctx.send("usage: f remind <minutes> <message>")
    return

  await ctx.send(f"ill remind you in **{minutes}** minutes about: **{reminder}** ⏰")
  await asyncio.sleep(minutes * 60)
  await ctx.send(f"{ctx.author.mention} reminder: **{reminder}**")

@bot.command()
async def poll(ctx, *, options: str = None):
  """create a poll"""
  if not options:
    await ctx.send("usage: f poll <option1> | <option2>")
    return

  opts = [o.strip() for o in options.split("|")]
  if len(opts) < 2:
    await ctx.send("need at least 2 options bro")
    return

  emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
  msg = "**poll time!** 📊
"
  for i, opt in enumerate(opts[:5]):
    msg += f"{emojis[i]} {opt}
"

  poll_msg = await ctx.send(msg)
  for i in range(len(opts[:5])):
    await poll_msg.add_reaction(emojis[i])

@bot.command()
async def vote(ctx, *, thing: str = None):
  """start a yes/no vote"""
  if not thing:
    await ctx.send("what are we voting on bro?")
    return

  msg = await ctx.send(f"**vote:** {thing}
👍 yes | 👎 no")
  await msg.add_reaction("👍")
  await msg.add_reaction("👎")

@bot.command()
async def coin(ctx):
  """flip a coin (no bet)"""
  await flipcoin(ctx)

@bot.command()
async def eightball(ctx, *, question: str = None):
  """ask the 8ball"""
  if not question:
    await ctx.send("what you asking the 8ball bro?")
    return
  await oracle(ctx, question=question)

@bot.command()
async def fact(ctx):
  """get a random fact"""
  facts = [
    "did you know? embers arent real currency. shocking i know",
    "fun fact: the bot owner is the only one who can give free embers",
    "did you know? gambling is statistically a bad idea. do it anyway",
    "fun fact: creatures dont actually exist. its all made up",
    "did you know? youre probably reading this instead of working",
    "fun fact: this bot has more commands than most real applications",
    "did you know? the more you beg, the more embers you get. capitalism",
    "fun fact: your daily streak resets if you miss a day. no mercy",
  ]
  await ctx.send(random.choice(facts))

@bot.command()
async def joke(ctx):
  """get a random joke"""
  jokes = [
    "why did the ember cross the road? to get to the other side of the economy",
    "what do you call a broke discord user? a f beg enthusiast",
    "why did the creature evolve? because it was tired of being lvl 1",
    "what do you call someone who lost all their embers? a f beg user",
    "why dont embers ever get lost? because theyre always in your data file",
  ]
  await ctx.send(random.choice(jokes))

@bot.command()
async def meme(ctx):
  """get a random meme text"""
  memes = [
    "when you lose all your embers on f allin: *surprised pikachu face*",
    "when someone scams you: *trust nobody not even yourself*",
    "when you get a legendary creature: *stonks*",
    "when you forget to do f daily: *panic*",
    "when the bot says youre broke: *always has been*",
  ]
  await ctx.send(random.choice(memes))

@bot.command()
async def quote(ctx):
  """get a random quote"""
  quotes = [
    "'ember today, gone tomorrow' - some wise person probably",
    "'the house always wins, except when it doesnt' - a gambler",
    "'beggars cant be choosers, but they can be rich' - this bot",
    "'with great embers comes great responsibility' - definitely not spiderman",
    "'dont put all your embers in one basket' - investment advice",
  ]
  await ctx.send(random.choice(quotes))

@bot.command()
async def inspire(ctx):
  """get inspired"""
  inspirations = [
    "you can do it! probably. maybe. actually idk",
    "believe in yourself! the bot believes in you. kinda",
    "never give up! unless its f allin, then maybe give up",
    "youre amazing! at losing embers apparently",
    "keep grinding! one day youll be rich. statistically unlikely but possible",
  ]
  await ctx.send(random.choice(inspirations))

@bot.command()
async def roastme(ctx):
  """get roasted"""
  roasts = [
    f"{ctx.author.mention} youre so broke you make beggars look rich",
    f"{ctx.author.mention} your creatures are planning an escape",
    f"{ctx.author.mention} you have the gambling luck of a rock",
    f"{ctx.author.mention} even the bot feels bad for you",
    f"{ctx.author.mention} your daily streak is probably 0",
  ]
  await ctx.send(random.choice(roasts))

@bot.command()
async def compliment(ctx, target: discord.Member = None):
  """compliment someone"""
  target = target or ctx.author
  compliments = [
    f"{target.mention} youre looking great today!",
    f"{target.mention} youre a legend in the making",
    f"{target.mention} your ember game is strong",
    f"{target.mention} youre the reason this server is fun",
    f"{target.mention} youre cooler than a lvl 10 dragon",
  ]
  await ctx.send(random.choice(compliments))

@bot.command()
async def ship(ctx, user1: discord.Member = None, user2: discord.Member = None):
  """ship two users"""
  if not user1 or not user2:
    await ctx.send("ship who with who bro? f ship @user1 @user2")
    return

  compatibility = random.randint(0, 100)
  if compatibility >= 80:
    await ctx.send(f"{user1.display_name} + {user2.display_name} = **{compatibility}%** match! soulmates! 💕")
  elif compatibility >= 50:
    await ctx.send(f"{user1.display_name} + {user2.display_name} = **{compatibility}%** match. could work")
  else:
    await ctx.send(f"{user1.display_name} + {user2.display_name} = **{compatibility}%** match. yikes")

@bot.command()
async def howgay(ctx, target: discord.Member = None):
  """check how gay someone is"""
  target = target or ctx.author
  percent = random.randint(0, 100)
  await ctx.send(f"{target.display_name} is **{percent}%** gay 🌈")

@bot.command()
async def howsimp(ctx, target: discord.Member = None):
  """check how much of a simp someone is"""
  target = target or ctx.author
  percent = random.randint(0, 100)
  await ctx.send(f"{target.display_name} is **{percent}%** simp 💦")

@bot.command()
async def howsmart(ctx, target: discord.Member = None):
  """check how smart someone is"""
  target = target or ctx.author
  percent = random.randint(0, 100)
  await ctx.send(f"{target.display_name} is **{percent}%** smart 🧠")

@bot.command()
async def howdumb(ctx, target: discord.Member = None):
  """check how dumb someone is"""
  target = target or ctx.author
  percent = random.randint(0, 100)
  await ctx.send(f"{target.display_name} is **{percent}%** dumb 🫠")

@bot.command()
async def howrich(ctx, target: discord.Member = None):
  """check how rich someone is"""
  target = target or ctx.author
  data = load_user(target.id)
  percent = min(100, int((data["embers"] / 10000) * 100))
  await ctx.send(f"{target.display_name} is **{percent}%** rich 💰")

@bot.command()
async def howlucky(ctx, target: discord.Member = None):
  """check how lucky someone is"""
  target = target or ctx.author
  percent = random.randint(0, 100)
  await ctx.send(f"{target.display_name} is **{percent}%** lucky 🍀")

@bot.command()
async def howsus(ctx, target: discord.Member = None):
  """check how sus someone is"""
  target = target or ctx.author
  percent = random.randint(0, 100)
  await ctx.send(f"{target.display_name} is **{percent}%** sus 🔍")

@bot.command()
async def howcringe(ctx, target: discord.Member = None):
  """check how cringe someone is"""
  target = target or ctx.author
  percent = random.randint(0, 100)
  await ctx.send(f"{target.display_name} is **{percent}%** cringe 😬")

@bot.command()
async def howbased(ctx, target: discord.Member = None):
  """check how based someone is"""
  target = target or ctx.author
  percent = random.randint(0, 100)
  await ctx.send(f"{target.display_name} is **{percent}%** based 😎")

@bot.command()
async def pp(ctx, target: discord.Member = None):
  """check pp size"""
  target = target or ctx.author
  size = random.randint(1, 12)
  pp = "8" + "=" * size + "D"
  await ctx.send(f"{target.display_name}'s pp: {pp}")

@bot.command()
async def iq(ctx, target: discord.Member = None):
  """check iq"""
  target = target or ctx.author
  score = random.randint(50, 200)
  await ctx.send(f"{target.display_name}'s iq: **{score}** {'genius' if score >= 140 else 'average' if score >= 90 else 'yikes'}")

@bot.command()
async def height(ctx, target: discord.Member = None):
  """check height"""
  target = target or ctx.author
  feet = random.randint(4, 7)
  inches = random.randint(0, 11)
  await ctx.send(f"{target.display_name} is **{feet}'{inches}** tall")

@bot.command()
async def weight(ctx, target: discord.Member = None):
  """check weight"""
  target = target or ctx.author
  lbs = random.randint(80, 300)
  await ctx.send(f"{target.display_name} weighs **{lbs}** lbs")

@bot.command()
async def age(ctx, target: discord.Member = None):
  """check age"""
  target = target or ctx.author
  years = random.randint(13, 99)
  await ctx.send(f"{target.display_name} is **{years}** years old")

@bot.command()
async def birthday(ctx, target: discord.Member = None):
  """check birthday"""
  target = target or ctx.author
  month = random.choice(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])
  day = random.randint(1, 28)
  await ctx.send(f"{target.display_name}'s birthday is **{month} {day}** 🎂")

@bot.command()
async def zodiac(ctx, target: discord.Member = None):
  """check zodiac"""
  target = target or ctx.author
  signs = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
  sign = random.choice(signs)
  await ctx.send(f"{target.display_name} is a **{sign}** ♈")

@bot.command()
async def color(ctx, target: discord.Member = None):
  """check favorite color"""
  target = target or ctx.author
  colors = ["red", "blue", "green", "yellow", "purple", "orange", "pink", "black", "white"]
  color = random.choice(colors)
  await ctx.send(f"{target.display_name}'s favorite color is **{color}** 🎨")

@bot.command()
async def food(ctx, target: discord.Member = None):
  """check favorite food"""
  target = target or ctx.author
  foods = ["pizza", "burgers", "tacos", "sushi", "pasta", "steak", "chicken", "ramen", "salad"]
  food = random.choice(foods)
  await ctx.send(f"{target.display_name}'s favorite food is **{food}** 🍽️")

@bot.command()
async def animal(ctx, target: discord.Member = None):
  """check spirit animal"""
  target = target or ctx.author
  animals = ["wolf", "eagle", "tiger", "dolphin", "owl", "fox", "bear", "snake", "rabbit"]
  animal = random.choice(animals)
  await ctx.send(f"{target.display_name}'s spirit animal is a **{animal}** 🐾")

@bot.command()
async def song(ctx):
  """get a random song recommendation"""
  songs = [
    "lose yourself - eminem (cuz youre about to lose all your embers)",
    "money trees - kendrick lamar (cuz you need money)",
    "broke - loyle carner (relatable)",
    "rich flex - drake (manifesting)",
    "gambling man - the overtones (fitting)",
  ]
  await ctx.send(f"song recommendation: {random.choice(songs)} 🎵")

@bot.command()
async def movie(ctx):
  """get a random movie recommendation"""
  movies = [
    "the wolf of wall street (cuz youre about to be rich)",
    "ocean's eleven (cuz youre a criminal now)",
    "the hangover (cuz you gambled too much)",
    "scarface (cuz youre a boss)",
    "casino royale (cuz gambling)",
  ]
  await ctx.send(f"movie recommendation: {random.choice(movies)} 🎬")

@bot.command()
async def game(ctx):
  """get a random game recommendation"""
  games = [
    "poker (practice for f poker)",
    "monopoly (learn about money)",
    "minecraft (mine like f mine)",
    "pokemon (catch creatures like f summon)",
    "gta (commit crimes like f crime)",
  ]
  await ctx.send(f"game recommendation: {random.choice(games)} 🎮")

@bot.command()
async def hobby(ctx, target: discord.Member = None):
  """check hobby"""
  target = target or ctx.author
  hobbies = ["gaming", "reading", "sports", "cooking", "drawing", "music", "coding", "gambling"]
  hobby = random.choice(hobbies)
  await ctx.send(f"{target.display_name}'s hobby is **{hobby}** 🎯")

@bot.command()
async def job(ctx, target: discord.Member = None):
  """check job"""
  target = target or ctx.author
  jobs = ["programmer", "chef", "artist", "musician", "athlete", "gambler", "thief", "beggar"]
  job = random.choice(jobs)
  await ctx.send(f"{target.display_name}'s job is **{job}** 💼")

@bot.command()
async def car(ctx, target: discord.Member = None):
  """check car"""
  target = target or ctx.author
  cars = ["toyota", "honda", "bmw", "mercedes", "lambo", "ferrari", "bus", "bicycle"]
  car = random.choice(cars)
  await ctx.send(f"{target.display_name} drives a **{car}** 🚗")

@bot.command()
async def house(ctx, target: discord.Member = None):
  """check house"""
  target = target or ctx.author
  houses = ["apartment", "mansion", "shack", "cardboard box", "castle", "cave"]
  house = random.choice(houses)
  await ctx.send(f"{target.display_name} lives in a **{house}** 🏠")

@bot.command()
async def phone(ctx, target: discord.Member = None):
  """check phone"""
  target = target or ctx.author
  phones = ["iphone", "samsung", "nokia", "flip phone", "no phone", "smart fridge"]
  phone = random.choice(phones)
  await ctx.send(f"{target.display_name} has a **{phone}** 📱")

@bot.command()
async def pet_name(ctx, target: discord.Member = None):
  """check pet name"""
  target = target or ctx.author
  names = ["buddy", "max", "bella", "charlie", "luna", "rocky", "daisy", "cooper"]
  name = random.choice(names)
  await ctx.send(f"{target.display_name}'s pet is named **{name}** 🐕")

@bot.command()
async def superpower(ctx, target: discord.Member = None):
  """check superpower"""
  target = target or ctx.author
  powers = ["invisibility", "flight", "super strength", "teleportation", "mind reading", "time travel", "luck"]
  power = random.choice(powers)
  await ctx.send(f"{target.display_name}'s superpower is **{power}** ⚡")

@bot.command()
async def villain(ctx, target: discord.Member = None):
  """check villain name"""
  target = target or ctx.author
  villains = ["the joker", "thanos", "voldemort", "darth vader", "sauron", "the bot owner"]
  villain = random.choice(villains)
  await ctx.send(f"{target.display_name}'s villain name is **{villain}** 😈")

@bot.command()
async def hero(ctx, target: discord.Member = None):
  """check hero name"""
  target = target or ctx.author
  heroes = ["batman", "superman", "spiderman", "iron man", "thor", "wonder woman"]
  hero = random.choice(heroes)
  await ctx.send(f"{target.display_name}'s hero name is **{hero}** 🦸")

@bot.command()
async def emoji(ctx, target: discord.Member = None):
  """check spirit emoji"""
  target = target or ctx.author
  emojis = ["🔥", "💎", "🍀", "⭐", "💰", "🎲", "🃏", "🎰"]
  emoji = random.choice(emojis)
  await ctx.send(f"{target.display_name}'s spirit emoji is **{emoji}**")

@bot.command()
async def word(ctx):
  """get a random word"""
  words = ["ember", "flame", "dragon", "fortune", "chaos", "destiny", "legend", "mystery"]
  await ctx.send(f"random word: **{random.choice(words)}**")

@bot.command()
async def number(ctx):
  """get a random number"""
  num = random.randint(1, 100)
  await ctx.send(f"random number: **{num}**")

@bot.command()
async def letter(ctx):
  """get a random letter"""
  letter = random.choice("abcdefghijklmnopqrstuvwxyz")
  await ctx.send(f"random letter: **{letter}**")

@bot.command()
async def colorhex(ctx):
  """get a random color hex"""
  hex_color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
  await ctx.send(f"random color: **{hex_color}**")

@bot.command()
async def password(ctx, length: int = 12):
  """generate a random password"""
  chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
  pwd = "".join(random.choice(chars) for _ in range(length))
  await ctx.author.send(f"your random password: `{pwd}`")
  await ctx.send("sent you a random password in dms")

@bot.command()
async def calc(ctx, *, expression: str = None):
  """calculate something"""
  if not expression:
    await ctx.send("what you calculating bro?")
    return
  try:
    result = eval(expression)
    await ctx.send(f"**{expression}** = **{result}**")
  except:
    await ctx.send("that math doesnt work bro")

@bot.command()
async def reverse(ctx, *, text: str = None):
  """reverse text"""
  if not text:
    await ctx.send("what you reversing bro?")
    return
  await ctx.send(f"reversed: **{text[::-1]}**")

@bot.command()
async def uppercase(ctx, *, text: str = None):
  """make text uppercase"""
  if not text:
    await ctx.send("what you uppercasing bro?")
    return
  await ctx.send(text.upper())

@bot.command()
async def lowercase(ctx, *, text: str = None):
  """make text lowercase"""
  if not text:
    await ctx.send("what you lowercasing bro?")
    return
  await ctx.send(text.lower())

@bot.command()
async def len_text(ctx, *, text: str = None):
  """check text length"""
  if not text:
    await ctx.send("what you measuring bro?")
    return
  await ctx.send(f"that text is **{len(text)}** characters long")

@bot.command()
async def repeat(ctx, times: int = None, *, text: str = None):
  """repeat text"""
  if not times or not text:
    await ctx.send("usage: f repeat <times> <text>")
    return
  if times > 10:
    await ctx.send("max 10 times bro")
    return
  await ctx.send((text + " ") * times)

@bot.command()
async def mock(ctx, *, text: str = None):
  """mock text (alternating caps)"""
  if not text:
    await ctx.send("what you mocking bro?")
    return
  mocked = "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text))
  await ctx.send(mocked)

@bot.command()
async def spoiler(ctx, *, text: str = None):
  """spoiler text"""
  if not text:
    await ctx.send("what you spoiling bro?")
    return
  await ctx.send(f"||{text}||")

@bot.command()
async def bold(ctx, *, text: str = None):
  """bold text"""
  if not text:
    await ctx.send("what you bolding bro?")
    return
  await ctx.send(f"**{text}**")

@bot.command()
async def italic(ctx, *, text: str = None):
  """italic text"""
  if not text:
    await ctx.send("what you italicizing bro?")
    return
  await ctx.send(f"*{text}*")

@bot.command()
async def underline(ctx, *, text: str = None):
  """underline text"""
  if not text:
    await ctx.send("what you underlining bro?")
    return
  await ctx.send(f"__{text}__")

@bot.command()
async def strikethrough(ctx, *, text: str = None):
  """strikethrough text"""
  if not text:
    await ctx.send("what you strikethroughing bro?")
    return
  await ctx.send(f"~~{text}~~")

@bot.command()
async def code(ctx, *, text: str = None):
  """code block text"""
  if not text:
    await ctx.send("what you coding bro?")
    return
  await ctx.send(f"```{text}```")

@bot.command()
async def quote_text(ctx, *, text: str = None):
  """quote text"""
  if not text:
    await ctx.send("what you quoting bro?")
    return
  await ctx.send(f"> {text}")

@bot.command()
async def embed(ctx, *, text: str = None):
  """create an embed"""
  if not text:
    await ctx.send("what you embedding bro?")
    return
  em = discord.Embed(description=text, color=discord.Color.orange())
  await ctx.send(embed=em)

@bot.command()
async def say(ctx, *, text: str = None):
  """make the bot say something"""
  if not text:
    await ctx.send("what you want me to say bro?")
    return
  await ctx.send(text)

@bot.command()
async def echo(ctx, *, text: str = None):
  """echo text"""
  await say(ctx, text=text)

@bot.command()
async def announce(ctx, *, text: str = None):
  """make an announcement"""
  if not text:
    await ctx.send("what you announcing bro?")
    return
  await ctx.send(f"📢 **ANNOUNCEMENT** 📢
{text}")

@bot.command()
async def botinfo(ctx):
  """bot info"""
  await ctx.send(
    "**flame bot info** 🔥
"
    f"commands: **350+**
"
    f"prefix: **f ** or **flame **
"
    f"currency: **embers**
"
    f"owner: justaflamewithfragz
"
    f"version: 1.0
"
    f"status: online and ready to gamble"
  )

@bot.command()
async def invite(ctx):
  """bot invite link"""
  await ctx.send("wanna add me to your server? dm the owner for an invite link")

@bot.command()
async def support(ctx):
  """support info"""
  await ctx.send("need help? use f tutorial or f help. still stuck? dm the owner")

@bot.command()
async def report(ctx, *, issue: str = None):
  """report an issue"""
  if not issue:
    await ctx.send("what you reporting bro?")
    return
  await ctx.send("thanks for the report! the owner will look into it eventually")

@bot.command()
async def suggest(ctx, *, suggestion: str = None):
  """suggest something"""
  if not suggestion:
    await ctx.send("what you suggesting bro?")
    return
  await ctx.send("thanks for the suggestion! maybe ill add it maybe i wont")

@bot.command()
async def uptime(ctx):
  """check bot uptime"""
  await ctx.send("ive been running since you started me. thats the uptime")

@bot.command()
async def version(ctx):
  """check bot version"""
  await ctx.send("flame bot v1.0 - built different")

@bot.command()
async def credits(ctx):
  """bot credits"""
  await ctx.send("built by justaflamewithfragz. powered by discord.py. fueled by embers")

@bot.command()
async def donate(ctx):
  """donate to the bot"""
  await ctx.send("wanna donate? just use the bot. thats donation enough")

@bot.command()
async def vote_bot(ctx):
  """vote for the bot"""
  await ctx.send("wanna vote? tell your friends about me. best vote ever")

@bot.command()
async def premium(ctx):
  """check premium status"""
  await ctx.send("premium? everyone is premium here. no paywalls")

@bot.command()
async def status(ctx):
  """check bot status"""
  await ctx.send("status: vibing. embers: flowing. users: gambling.")

@bot.command()
async def pingme(ctx):
  """ping yourself"""
  await ctx.send(f"{ctx.author.mention} ping! you pinged yourself. why?")

@bot.command()
async def selfdestruct(ctx):
  """self destruct (fake)"""
  await ctx.send("self destruct sequence initiated... 3... 2... 1... just kidding")

@bot.command()
async def hack(ctx, target: discord.Member = None):
  """hack someone (fake)"""
  if not target:
    await ctx.send("who you hacking bro?")
    return
  await ctx.send(f"hacking {target.display_name}...
[██████] 100% done!
jk i cant actually hack anyone")

@bot.command()
async def nuke(ctx):
  """nuke the server (fake)"""
  await ctx.send("☢️ NUKE LAUNCHED ☢️
...
...
...
it was a dud. server is fine")

@bot.command()
async def boom(ctx):
  """explosion (fake)"""
  await ctx.send("💥 BOOM! 💥
...
nothing happened. anticlimactic")

@bot.command()
async def dab(ctx):
  """dab"""
  await ctx.send(f"{ctx.author.display_name} hit the dab! 😎")

@bot.command()
async def floss(ctx):
  """floss dance"""
  await ctx.send(f"{ctx.author.display_name} did the floss! 💃")

@bot.command()
async def default_dance(ctx):
  """default dance"""
  await ctx.send(f"{ctx.author.display_name} hit the default dance! 🕺")

@bot.command()
async def take_the_l(ctx):
  """take the l"""
  await ctx.send(f"{ctx.author.display_name} took the L!")

@bot.command()
async def rekt(ctx, target: discord.Member = None):
  """rekt someone"""
  if not target:
    target = ctx.author
  await ctx.send(f"{target.display_name} got REKT! 🔥")

@bot.command()
async def oof(ctx):
  """oof"""
  await ctx.send("oof")

@bot.command()
async def big_oof(ctx):
  """big oof"""
  await ctx.send("BIG OOF")

@bot.command()
async def f_in_chat(ctx):
  """press f"""
  await ctx.send("F")

@bot.command()
async def rip(ctx, target: discord.Member = None):
  """rip someone"""
  if not target:
    await ctx.send("rip")
    return
  await ctx.send(f"rip {target.display_name} 🪦")

@bot.command()
async def respect(ctx):
  """pay respects"""
  await ctx.send("press f to pay respects")

@bot.command()
async def sus(ctx, target: discord.Member = None):
  """call someone sus"""
  if not target:
    await ctx.send("who sus bro?")
    return
  await ctx.send(f"{target.display_name} is looking kinda sus 🔍")

@bot.command()
async def imposter(ctx, target: discord.Member = None):
  """call someone imposter"""
  if not target:
    await ctx.send("who the imposter bro?")
    return
  await ctx.send(f"{target.display_name} is the imposter! 🔪")

@bot.command()
async def vented(ctx, target: discord.Member = None):
  """say someone vented"""
  if not target:
    await ctx.send("who vented bro?")
    return
  await ctx.send(f"{target.display_name} vented! sus! 🔍")

@bot.command()
async def emergency(ctx):
  """emergency meeting"""
  await ctx.send("🚨 EMERGENCY MEETING! 🚨
everyone stop gambling and pay attention")

@bot.command()
async def eject(ctx, target: discord.Member = None):
  """eject someone"""
  if not target:
    await ctx.send("who we ejecting bro?")
    return
  await ctx.send(f"{target.display_name} was ejected! 🚀")

@bot.command()
async def tasks(ctx):
  """do tasks"""
  await ctx.send("you did your tasks! good crewmate ✅")

@bot.command()
async def sabotage(ctx):
  """sabotage"""
  await ctx.send("you sabotaged! lights are out! 🔦")

@bot.command()
async def report_body(ctx):
  """report a body"""
  await ctx.send("body reported! where? 🔍")

@bot.command()
async def meeting(ctx):
  """call a meeting"""
  await ctx.send("meeting called! everyone to the table 📢")

@bot.command()
async def skip(ctx):
  """skip vote"""
  await ctx.send("vote skipped! nobody was ejected")

@bot.command()
async def guilty(ctx, target: discord.Member = None):
  """vote guilty"""
  if not target:
    await ctx.send("who you voting guilty on bro?")
    return
  await ctx.send(f"{ctx.author.display_name} voted **guilty** on {target.display_name}! ⚖️")

@bot.command()
async def innocent(ctx, target: discord.Member = None):
  """vote innocent"""
  if not target:
    await ctx.send("who you voting innocent on bro?")
    return
  await ctx.send(f"{ctx.author.display_name} voted **innocent** on {target.display_name}! ⚖️")

@bot.command()
async def defend_me(ctx):
  """defend yourself"""
  await ctx.send(f"{ctx.author.display_name} is defending themselves! it wasnt me! 🛡️")

@bot.command()
async def accuse(ctx, target: discord.Member = None):
  """accuse someone"""
  if not target:
    await ctx.send("who you accusing bro?")
    return
  await ctx.send(f"{ctx.author.display_name} accused {target.display_name}! 🔍")

@bot.command()
async def alibi(ctx):
  """give an alibi"""
  await ctx.send(f"{ctx.author.display_name}'s alibi: i was doing tasks in electrical! ⚡")

@bot.command()
async def sus_meter(ctx, target: discord.Member = None):
  """check sus meter"""
  target = target or ctx.author
  percent = random.randint(0, 100)
  await ctx.send(f"{target.display_name}'s sus meter: **{percent}%** 🔍")

@bot.command()
async def trust(ctx, target: discord.Member = None):
  """trust someone"""
  if not target:
    await ctx.send("who you trusting bro?")
    return
  await ctx.send(f"{ctx.author.display_name} trusts {target.display_name}! 🤝")

@bot.command()
async def distrust(ctx, target: discord.Member = None):
  """distrust someone"""
  if not target:
    await ctx.send("who you distrusting bro?")
    return
  await ctx.send(f"{ctx.author.display_name} distrusts {target.display_name}! 👀")

@bot.command()
async def crewmate(ctx):
  """claim crewmate"""
  await ctx.send(f"{ctx.author.display_name} claims crewmate! trust me bro 🤞")

@bot.command()
async def sheriff(ctx):
  """claim sheriff"""
  await ctx.send(f"{ctx.author.display_name} claims sheriff! i will protect you 🛡️")

@bot.command()
async def jester(ctx):
  """claim jester"""
  await ctx.send(f"{ctx.author.display_name} claims jester! vote me out please 🤡")

@bot.command()
async def executioner(ctx, target: discord.Member = None):
  """claim executioner"""
  if not target:
    await ctx.send("who your target bro?")
    return
  await ctx.send(f"{ctx.author.display_name} claims executioner! target: {target.display_name} ⚔️")

@bot.command()
async def psychic(ctx):
  """claim psychic"""
  await ctx.send(f"{ctx.author.display_name} claims psychic! i sense danger 🔮")

@bot.command()
async def medic(ctx):
  """claim medic"""
  await ctx.send(f"{ctx.author.display_name} claims medic! who needs healing? 💉")

@bot.command()
async def engineer(ctx):
  """claim engineer"""
  await ctx.send(f"{ctx.author.display_name} claims engineer! i fix stuff 🔧")

@bot.command()
async def spy(ctx):
  """claim spy"""
  await ctx.send(f"{ctx.author.display_name} claims spy! i see everything 👁️")

@bot.command()
async def mayor(ctx):
  """claim mayor"""
  await ctx.send(f"{ctx.author.display_name} claims mayor! my vote counts double 🗳️")

@bot.command()
async def veteran(ctx):
  """claim veteran"""
  await ctx.send(f"{ctx.author.display_name} claims veteran! dont visit me at night ⚔️")

@bot.command()
async def vig(ctx, target: discord.Member = None):
  """vigilante shoot"""
  if not target:
    await ctx.send("who you shooting bro?")
    return
  await ctx.send(f"{ctx.author.display_name} shot {target.display_name}! 🔫")

@bot.command()
async def jail(ctx, target: discord.Member = None):
  """jail someone"""
  if not target:
    await ctx.send("who you jailing bro?")
    return
  await ctx.send(f"{ctx.author.display_name} jailed {target.display_name}! 🚔")

@bot.command()
async def execute(ctx, target: discord.Member = None):
  """execute someone"""
  if not target:
    await ctx.send("who you executing bro?")
    return
  await ctx.send(f"{ctx.author.display_name} executed {target.display_name}! ⚔️")

@bot.command()
async def revive_player(ctx, target: discord.Member = None):
  """revive a player"""
  if not target:
    await ctx.send("who you reviving bro?")
    return
  await ctx.send(f"{ctx.author.display_name} revived {target.display_name}! 🔄")

@bot.command()
async def haunt(ctx, target: discord.Member = None):
  """haunt someone"""
  if not target:
    await ctx.send("who you haunting bro?")
    return
  await ctx.send(f"{ctx.author.display_name} is haunting {target.display_name}! 👻")

@bot.command()
async def seance(ctx):
  """hold a seance"""
  await ctx.send("🔮 seance started! spirits, speak to us! 🔮")

@bot.command()
async def ghost(ctx):
  """become a ghost"""
  await ctx.send(f"{ctx.author.display_name} is now a ghost! boo! 👻")

@bot.command()
async def alive(ctx):
  """confirm youre alive"""
  await ctx.send(f"{ctx.author.display_name} is alive! for now...")

@bot.command()
async def dead(ctx):
  """confirm youre dead"""
  await ctx.send(f"{ctx.author.display_name} is dead! rip 🪦")

@bot.command()
async def medium(ctx):
  """claim medium"""
  await ctx.send(f"{ctx.author.display_name} claims medium! i talk to the dead 🔮")

@bot.command()
async def retributionist(ctx):
  """claim retributionist"""
  await ctx.send(f"{ctx.author.display_name} claims retributionist! i bring back the dead 🔄")

@bot.command()
async def transporter(ctx, target1: discord.Member = None, target2: discord.Member = None):
  """transport two people"""
  if not target1 or not target2:
    await ctx.send("transport who with who bro?")
    return
  await ctx.send(f"{ctx.author.display_name} transported {target1.display_name} and {target2.display_name}! 🔄")

@bot.command()
async def escort(ctx, target: discord.Member = None):
  """escort someone"""
  if not target:
    await ctx.send("who you escorting bro?")
    return
  await ctx.send(f"{ctx.author.display_name} escorted {target.display_name}! they cant do anything tonight 💃")

@bot.command()
async def consort(ctx, target: discord.Member = None):
  """consort someone"""
  if not target:
    await ctx.send("who you consorting bro?")
    return
  await ctx.send(f"{ctx.author.display_name} consorted {target.display_name}! theyre distracted 💋")

@bot.command()
async def blackmail(ctx, target: discord.Member = None):
  """blackmail someone"""
  if not target:
    await ctx.send("who you blackmailing bro?")
    return
  await ctx.send(f"{ctx.author.display_name} blackmailed {target.display_name}! they cant speak! 🤐")

@bot.command()
async def forger(ctx):
  """claim forger"""
  await ctx.send(f"{ctx.author.display_name} claims forger! i make fake wills 📝")

@bot.command()
async def framer(ctx, target: discord.Member = None):
  """frame someone"""
  if not target:
    await ctx.send("who you framing bro?")
    return
  await ctx.send(f"{ctx.author.display_name} framed {target.display_name}! they look sus now 🔍")

@bot.command()
async def hypnotist(ctx, target: discord.Member = None):
  """hypnotize someone"""
  if not target:
    await ctx.send("who you hypnotizing bro?")
    return
  await ctx.send(f"{ctx.author.display_name} hypnotized {target.display_name}! theyre under control 🌀")

@bot.command()
async def ambusher_cmd(ctx, target: discord.Member = None):
  """ambush someone"""
  if not target:
    await ctx.send("who you ambushing bro?")
    return
  await ctx.send(f"{ctx.author.display_name} ambushed {target.display_name}! surprise attack! ⚔️")

@bot.command()
async def poisoner(ctx, target: discord.Member = None):
  """poison someone"""
  if not target:
    await ctx.send("who you poisoning bro?")
    return
  await ctx.send(f"{ctx.author.display_name} poisoned {target.display_name}! theyll die soon ☠️")

@bot.command()
async def hexmaster(ctx):
  """claim hex master"""
  await ctx.send(f"{ctx.author.display_name} claims hex master! one hex to rule them all 🔮")

@bot.command()
async def hex(ctx, target: discord.Member = None):
  """hex someone"""
  if not target:
    await ctx.send("who you hexing bro?")
    return
  await ctx.send(f"{ctx.author.display_name} hexed {target.display_name}! theyre cursed! 🔮")

@bot.command()
async def pestilence(ctx):
  """claim pestilence"""
  await ctx.send(f"{ctx.author.display_name} is PESTILENCE! everyone dies! ☠️")

@bot.command()
async def juggernaut(ctx):
  """claim juggernaut"""
  await ctx.send(f"{ctx.author.display_name} claims juggernaut! unstoppable! 💪")

@bot.command()
async def arsonist(ctx):
  """claim arsonist"""
  await ctx.send(f"{ctx.author.display_name} claims arsonist! dousing everyone! 🔥")

@bot.command()
async def douse(ctx, target: discord.Member = None):
  """douse someone"""
  if not target:
    await ctx.send("who you dousing bro?")
    return
  await ctx.send(f"{ctx.author.display_name} doused {target.display_name} in gasoline! 🔥")

@bot.command()
async def ignite(ctx):
  """ignite everyone"""
  await ctx.send(f"{ctx.author.display_name} ignited everyone! 🔥🔥🔥")

@bot.command()
async def serialkiller(ctx):
  """claim serial killer"""
  await ctx.send(f"{ctx.author.display_name} claims serial killer! one kill at a time 🔪")

@bot.command()
async def mafioso(ctx):
  """claim mafioso"""
  await ctx.send(f"{ctx.author.display_name} claims mafioso! the don commands me 🕵️")

@bot.command()
async def godfather(ctx):
  """claim godfather"""
  await ctx.send(f"{ctx.author.display_name} claims godfather! i am the don! 🕵️")

@bot.command()
async def blackmailer(ctx):
  """claim blackmailer"""
  await ctx.send(f"{ctx.author.display_name} claims blackmailer! silence them! 🤐")

@bot.command()
async def consigliere(ctx):
  """claim consigliere"""
  await ctx.send(f"{ctx.author.display_name} claims consigliere! i investigate for the mafia 🔍")

@bot.command()
async def janitor(ctx):
  """claim janitor"""
  await ctx.send(f"{ctx.author.display_name} claims janitor! i clean up the mess 🧹")

@bot.command()
async def disguiser(ctx):
  """claim disguiser"""
  await ctx.send(f"{ctx.author.display_name} claims disguiser! i am whoever i want to be 🎭")

@bot.command()
async def survivor(ctx):
  """claim survivor"""
  await ctx.send(f"{ctx.author.display_name} claims survivor! just let me live! 🛡️")

@bot.command()
async def amnesiac(ctx):
  """claim amnesiac"""
  await ctx.send(f"{ctx.author.display_name} claims amnesiac! i forgot my role 🤔")

@bot.command()
async def guardianangel(ctx, target: discord.Member = None):
  """claim guardian angel"""
  if not target:
    await ctx.send("who your target bro?")
    return
  await ctx.send(f"{ctx.author.display_name} claims guardian angel! protecting {target.display_name}! 👼")

@bot.command()
async def pirate(ctx, target: discord.Member = None):
  """claim pirate"""
  if not target:
    await ctx.send("who your target bro?")
    return
  await ctx.send(f"{ctx.author.display_name} claims pirate! dueling {target.display_name}! ⚔️")

@bot.command()
async def plunderer(ctx):
  """claim plunderer"""
  await ctx.send(f"{ctx.author.display_name} claims plunderer! give me your stuff! 🏴‍☠️")

@bot.command()
async def crusader(ctx, target: discord.Member = None):
  """claim crusader"""
  if not target:
    await ctx.send("who you protecting bro?")
    return
  await ctx.send(f"{ctx.author.display_name} claims crusader! protecting {target.display_name}! ⚔️")

@bot.command()
async def trapper(ctx):
  """claim trapper"""
  await ctx.send(f"{ctx.author.display_name} claims trapper! traps set! 🪤")

@bot.command()
async def trap(ctx, target: discord.Member = None):
  """trap someone"""
  if not target:
    await ctx.send("who you trapping bro?")
    return
  await ctx.send(f"{ctx.author.display_name} trapped {target.display_name}! theyre stuck! 🪤")

@bot.command()
async def lookout(ctx, target: discord.Member = None):
  """claim lookout"""
  if not target:
    await ctx.send("who you watching bro?")
    return
  await ctx.send(f"{ctx.author.display_name} claims lookout! watching {target.display_name}! 👁️")

@bot.command()
async def tracker(ctx, target: discord.Member = None):
  """claim tracker"""
  if not target:
    await ctx.send("who you tracking bro?")
    return
  await ctx.send(f"{ctx.author.display_name} claims tracker! tracking {target.display_name}! 👣")

@bot.command()
async def investigator(ctx, target: discord.Member = None):
  """claim investigator"""
  if not target:
    await ctx.send("who you investigating bro?")
    return
  await ctx.send(f"{ctx.author.display_name} claims investigator! investigating {target.display_name}! 🔍")

@bot.command()
async def sheriff_cmd(ctx, target: discord.Member = None):
  """sheriff investigate"""
  if not target:
    await ctx.send("who you investigating bro?")
    return
  result = random.choice(["suspicious", "not suspicious"])
  await ctx.send(f"{target.display_name} is **{result}** according to the sheriff! 🔍")


@bot.command()
async def bodyguard(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you protecting bro?")
    return
  await ctx.send(f"{ctx.author.display_name} claims bodyguard! protecting {target.display_name}")

@bot.command()
async def doctor_cmd(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you healing bro?")
    return
  await ctx.send(f"{ctx.author.display_name} healed {target.display_name}")

@bot.command()
async def reveal(ctx):
  await ctx.send(f"{ctx.author.display_name} revealed as MAYOR")

@bot.command()
async def whisper(ctx, target: discord.Member = None, *, message: str = None):
  if not target or not message:
    await ctx.send("usage: f whisper @user <message>")
    return
  await ctx.send(f"{ctx.author.display_name} whispered to {target.display_name}")

@bot.command()
async def lastwill(ctx, *, will: str = None):
  if not will:
    await ctx.send("whats your last will bro?")
    return
  data = load_user(ctx.author.id)
  data["last_will"] = will
  save_user(ctx.author.id, data)
  await ctx.send("last will saved")

@bot.command()
async def read_will(ctx, target: discord.Member = None):
  target = target or ctx.author
  data = load_user(target.id)
  will = data.get("last_will", "no last will found")
  await ctx.send(f"{target.display_name}'s last will: {will}")

@bot.command()
async def deathnote(ctx, *, note: str = None):
  if not note:
    await ctx.send("whats your death note bro?")
    return
  await ctx.send(f"death note: {note}")

@bot.command()
async def rolelist(ctx):
  await ctx.send("town: sheriff, investigator, lookout, spy, jailor, mayor, medium, retributionist, transporter, escort, doctor, bodyguard, crusader, trapper, veteran, vig")

@bot.command()
async def werewolf(ctx):
  await ctx.send(f"{ctx.author.display_name} claims werewolf")

@bot.command()
async def fullmoon(ctx):
  await ctx.send("full moon")

@bot.command()
async def howl(ctx):
  await ctx.send(f"{ctx.author.display_name} howled")

@bot.command()
async def maul(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you mauling bro?")
    return
  await ctx.send(f"{ctx.author.display_name} mauled {target.display_name}")

@bot.command()
async def plaguebearer(ctx):
  await ctx.send(f"{ctx.author.display_name} claims plaguebearer")

@bot.command()
async def infect(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you infecting bro?")
    return
  await ctx.send(f"{ctx.author.display_name} infected {target.display_name}")

@bot.command()
async def necromancer(ctx):
  await ctx.send(f"{ctx.author.display_name} claims necromancer")

@bot.command()
async def reanimate(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you reanimating bro?")
    return
  await ctx.send(f"{ctx.author.display_name} reanimated {target.display_name}")

@bot.command()
async def medusa(ctx):
  await ctx.send(f"{ctx.author.display_name} claims medusa")

@bot.command()
async def stone(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you stoning bro?")
    return
  await ctx.send(f"{ctx.author.display_name} stoned {target.display_name}")

@bot.command()
async def puppeteer(ctx):
  await ctx.send(f"{ctx.author.display_name} claims puppeteer")

@bot.command()
async def control(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you controlling bro?")
    return
  await ctx.send(f"{ctx.author.display_name} is controlling {target.display_name}")

@bot.command()
async def covenleader(ctx):
  await ctx.send(f"{ctx.author.display_name} claims coven leader")

@bot.command()
async def potionmaster(ctx):
  await ctx.send(f"{ctx.author.display_name} claims potion master")

@bot.command()
async def heal_potion(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you healing bro?")
    return
  await ctx.send(f"{ctx.author.display_name} used a heal potion on {target.display_name}")

@bot.command()
async def kill_potion(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you killing bro?")
    return
  await ctx.send(f"{ctx.author.display_name} used a kill potion on {target.display_name}")

@bot.command()
async def reveal_potion(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you revealing bro?")
    return
  await ctx.send(f"{ctx.author.display_name} used a reveal potion on {target.display_name}")

@bot.command()
async def crusade(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you crusading against bro?")
    return
  await ctx.send(f"{ctx.author.display_name} started a crusade against {target.display_name}")

@bot.command()
async def deus_vult(ctx):
  await ctx.send("DEUS VULT")

@bot.command()
async def bonk_cmd(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you bonking bro?")
    return
  await ctx.send(f"{ctx.author.display_name} bonked {target.display_name}")

@bot.command()
async def hornyjail(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you sending to horny jail bro?")
    return
  await ctx.send(f"{target.display_name} has been sent to horny jail")

@bot.command()
async def unhorny(ctx, target: discord.Member = None):
  if not target:
    await ctx.send("who you freeing bro?")
    return
  await ctx.send(f"{target.display_name} has been freed from horny jail")

@bot.command()
async def horny_meter(ctx, target: discord.Member = None):
  target = target or ctx.author
  percent = random.randint(0, 100)
  await ctx.send(f"{target.display_name}'s horny meter: {percent}%")

@bot.command()
async def downbad(ctx, target: discord.Member = None):
  target = target or ctx.author
  percent = random.randint(0, 100)
  await ctx.send(f"{target.display_name} is {percent}% down bad")

@bot.command()
async def touchgrass(ctx, target: discord.Member = None):
  target = target or ctx.author
  await ctx.send(f"{target.display_name} needs to touch grass")

@bot.command()
async def gooutside(ctx, target: discord.Member = None):
  target = target or ctx.author
  await ctx.send(f"{target.display_name} GO OUTSIDE")

@bot.command()
async def shower(ctx, target: discord.Member = None):
  target = target or ctx.author
  await ctx.send(f"{target.display_name} please shower")

@bot.command()
async def sleep_cmd(ctx, target: discord.Member = None):
  target = target or ctx.author
  await ctx.send(f"{target.display_name} go to sleep")

@bot.command()
async def hydrate(ctx, target: discord.Member = None):
  target = target or ctx.author
  await ctx.send(f"{target.display_name} drink some water")

@bot.command()
async def eat_cmd(ctx, target: discord.Member = None):
  target = target or ctx.author
  await ctx.send(f"{target.display_name} go eat something")

@bot.command()
async def selfcare(ctx, target: discord.Member = None):
  target = target or ctx.author
  await ctx.send(f"{target.display_name} practice self care")

@bot.command()
async def mentalhealth(ctx):
  await ctx.send("mental health check")

@bot.command()
async def vent(ctx, *, message: str = None):
  if not message:
    await ctx.send("what you venting about bro?")
    return
  await ctx.send(f"{ctx.author.display_name} is venting: {message}")

@bot.command()
async def therapy(ctx):
  therapies = ["have you tried going outside?", "maybe touch some grass?", "have you considered not gambling?"]
  await ctx.send(f"therapy session: {random.choice(therapies)}")

@bot.command()
async def advice(ctx):
  advices = ["dont gamble more than you can afford", "save some embers", "feed your creatures", "daily streaks matter"]
  await ctx.send(f"advice: {random.choice(advices)}")

@bot.command()
async def wisdom(ctx):
  wisdoms = ["the ember you save today is the ember you gamble tomorrow", "a creature fed is a creature loyal"]
  await ctx.send(f"wisdom: {random.choice(wisdoms)}")

@bot.command()
async def lifehack(ctx):
  hacks = ["do f daily every day", "beg when youre broke", "vault your embers"]
  await ctx.send(f"life hack: {random.choice(hacks)}")

@bot.command()
async def protip(ctx):
  await lifehack(ctx)

@bot.command()
async def hacklife(ctx):
  await lifehack(ctx)

@bot.command()
async def motivation(ctx):
  motivations = ["you can do it", "believe in yourself", "never give up"]
  await ctx.send(f"motivation: {random.choice(motivations)}")

@bot.command()
async def demotivation(ctx):
  demotivations = ["youre probably gonna lose", "your creatures are plotting against you"]
  await ctx.send(f"demotivation: {random.choice(demotivations)}")

@bot.command()
async def pep_talk(ctx):
  await motivation(ctx)

@bot.command()
async def reality_check(ctx):
  data = load_user(ctx.author.id)
  await ctx.send(f"reality check: you have {data['embers']} embers")

@bot.command()
async def wake_up(ctx):
  await ctx.send("WAKE UP")

@bot.command()
async def reality(ctx):
  await ctx.send("reality: youre spending too much time on discord")

@bot.command()
async def exist(ctx):
  await ctx.send("why do we exist")

@bot.command()
async def void_cmd(ctx):
  await ctx.send("you stare into the void")

@bot.command()
async def abyss(ctx):
  await ctx.send("the abyss gazes also")

@bot.command()
async def chaos(ctx):
  await ctx.send("CHAOS")

@bot.command()
async def order(ctx):
  await ctx.send("ORDER")

@bot.command()
async def balance_cmd(ctx):
  await ctx.send("balance is key")

@bot.command()
async def yin_yang(ctx):
  await ctx.send("yin and yang")

@bot.command()
async def karma(ctx):
  data = load_user(ctx.author.id)
  karma = data.get("karma", random.randint(-100, 100))
  await ctx.send(f"your karma: {karma}")

@bot.command()
async def good_karma(ctx):
  data = load_user(ctx.author.id)
  if "karma" not in data:
    data["karma"] = 0
  data["karma"] += 10
  save_user(ctx.author.id, data)
  await ctx.send("you did something good +10 karma")

@bot.command()
async def bad_karma(ctx):
  data = load_user(ctx.author.id)
  if "karma" not in data:
    data["karma"] = 0
  data["karma"] -= 10
  save_user(ctx.author.id, data)
  await ctx.send("you did something bad -10 karma")

@bot.command()
async def fortune_cookie(ctx):
  fortunes = ["you will find embers", "beware of scams", "a stranger will give you embers"]
  await ctx.send(f"fortune cookie: {random.choice(fortunes)}")

@bot.command()
async def horoscope(ctx):
  horoscopes = ["today is your lucky day", "avoid gambling today", "invest wisely"]
  await ctx.send(f"horoscope: {random.choice(horoscopes)}")

@bot.command()
async def tarot_card(ctx):
  cards = ["the fool", "death", "the tower", "the sun"]
  await ctx.send(f"tarot card: {random.choice(cards)}")

@bot.command()
async def crystal_ball(ctx):
  await ctx.send("crystal ball shows embers")

@bot.command()
async def palm_reading(ctx):
  await ctx.send("your palm says you have hands")

@bot.command()
async def aura_reading(ctx):
  colors = ["red", "blue", "green", "purple"]
  await ctx.send(f"your aura is {random.choice(colors)}")

@bot.command()
async def zodiac_sign(ctx, target: discord.Member = None):
  target = target or ctx.author
  signs = ["aries", "taurus", "gemini", "cancer"]
  await ctx.send(f"{target.display_name} is a {random.choice(signs)}")

@bot.command()
async def compatibility(ctx, user1: discord.Member = None, user2: discord.Member = None):
  if not user1 or not user2:
    await ctx.send("check compatibility between who bro?")
    return
  percent = random.randint(0, 100)
  await ctx.send(f"{user1.display_name} + {user2.display_name} = {percent}% compatible")

@bot.command()
async def soulmate(ctx):
  members = [m for m in ctx.guild.members if not m.bot and m != ctx.author]
  if not members:
    await ctx.send("no soulmate found")
    return
  soulmate = random.choice(members)
  await ctx.send(f"{ctx.author.display_name}'s soulmate is {soulmate.display_name}")

@bot.command()
async def enemy(ctx):
  members = [m for m in ctx.guild.members if not m.bot and m != ctx.author]
  if not members:
    await ctx.send("no enemies found")
    return
  enemy = random.choice(members)
  await ctx.send(f"{ctx.author.display_name}'s enemy is {enemy.display_name}")

@bot.command()
async def bestfriend(ctx):
  members = [m for m in ctx.guild.members if not m.bot and m != ctx.author]
  if not members:
    await ctx.send("no friends found")
    return
  friend = random.choice(members)
  await ctx.send(f"{ctx.author.display_name}'s best friend is {friend.display_name}")

@bot.command()
async def rival(ctx):
  members = [m for m in ctx.guild.members if not m.bot and m != ctx.author]
  if not members:
    await ctx.send("no rivals found")
    return
  rival = random.choice(members)
  await ctx.send(f"{ctx.author.display_name}'s rival is {rival.display_name}")

@bot.command()
async def twin(ctx):
  members = [m for m in ctx.guild.members if not m.bot and m != ctx.author]
  if not members:
    await ctx.send("no twin found")
    return
  twin = random.choice(members)
  await ctx.send(f"{ctx.author.display_name}'s twin is {twin.display_name}")

@bot.command()
async def clone(ctx):
  await twin(ctx)

@bot.command()
async def doppelganger(ctx):
  await twin(ctx)

@bot.command()
async def spirit_animal(ctx, target: discord.Member = None):
  target = target or ctx.author
  animals = ["wolf", "eagle", "tiger", "dolphin"]
  await ctx.send(f"{target.display_name}'s spirit animal is a {random.choice(animals)}")

@bot.command()
async def spirit_color(ctx, target: discord.Member = None):
  target = target or ctx.author
  colors = ["red", "blue", "green", "purple"]
  await ctx.send(f"{target.display_name}'s spirit color is {random.choice(colors)}")

@bot.command()
async def spirit_number(ctx, target: discord.Member = None):
  target = target or ctx.author
  num = random.randint(1, 100)
  await ctx.send(f"{target.display_name}'s spirit number is {num}")

@bot.command()
async def spirit_food(ctx, target: discord.Member = None):
  target = target or ctx.author
  foods = ["pizza", "burger", "taco", "sushi"]
  await ctx.send(f"{target.display_name}'s spirit food is {random.choice(foods)}")

@bot.command()
async def spirit_drink(ctx, target: discord.Member = None):
  target = target or ctx.author
  drinks = ["coffee", "tea", "water", "soda"]
  await ctx.send(f"{target.display_name}'s spirit drink is {random.choice(drinks)}")

@bot.command()
async def spirit_song(ctx, target: discord.Member = None):
  target = target or ctx.author
  songs = ["bohemian rhapsody", "lose yourself", "imagine"]
  await ctx.send(f"{target.display_name}'s spirit song is {random.choice(songs)}")

@bot.command()
async def spirit_movie(ctx, target: discord.Member = None):
  target = target or ctx.author
  movies = ["the matrix", "inception", "fight club"]
  await ctx.send(f"{target.display_name}'s spirit movie is {random.choice(movies)}")

@bot.command()
async def spirit_game(ctx, target: discord.Member = None):
  target = target or ctx.author
  games = ["minecraft", "dark souls", "zelda"]
  await ctx.send(f"{target.display_name}'s spirit game is {random.choice(games)}")

@bot.command()
async def spirit_hobby(ctx, target: discord.Member = None):
  target = target or ctx.author
  hobbies = ["gaming", "reading", "sports", "cooking"]
  await ctx.send(f"{target.display_name}'s spirit hobby is {random.choice(hobbies)}")

@bot.command()
async def spirit_job(ctx, target: discord.Member = None):
  target = target or ctx.author
  jobs = ["programmer", "chef", "artist", "musician"]
  await ctx.send(f"{target.display_name}'s spirit job is {random.choice(jobs)}")

@bot.command()
async def spirit_car(ctx, target: discord.Member = None):
  target = target or ctx.author
  cars = ["lambo", "ferrari", "tesla", "honda"]
  await ctx.send(f"{target.display_name}'s spirit car is a {random.choice(cars)}")

@bot.command()
async def spirit_house(ctx, target: discord.Member = None):
  target = target or ctx.author
  houses = ["mansion", "apartment", "shack", "castle"]
  await ctx.send(f"{target.display_name}'s spirit house is a {random.choice(houses)}")

@bot.command()
async def spirit_phone(ctx, target: discord.Member = None):
  target = target or ctx.author
  phones = ["iphone", "samsung", "nokia", "flip phone"]
  await ctx.send(f"{target.display_name}'s spirit phone is a {random.choice(phones)}")

@bot.command()
async def spirit_pet(ctx, target: discord.Member = None):
  target = target or ctx.author
  pets = ["dog", "cat", "dragon", "phoenix"]
  await ctx.send(f"{target.display_name}'s spirit pet is a {random.choice(pets)}")

@bot.command()
async def spirit_weapon(ctx, target: discord.Member = None):
  target = target or ctx.author
  weapons = ["sword", "bow", "staff", "dagger"]
  await ctx.send(f"{target.display_name}'s spirit weapon is a {random.choice(weapons)}")

@bot.command()
async def spirit_element(ctx, target: discord.Member = None):
  target = target or ctx.author
  elements = ["fire", "water", "earth", "air"]
  await ctx.send(f"{target.display_name}'s spirit element is {random.choice(elements)}")

@bot.command()
async def spirit_magic(ctx, target: discord.Member = None):
  target = target or ctx.author
  magics = ["fireball", "healing", "teleportation", "invisibility"]
  await ctx.send(f"{target.display_name}'s spirit magic is {random.choice(magics)}")

@bot.command()
async def spirit_villain(ctx, target: discord.Member = None):
  target = target or ctx.author
  villains = ["the joker", "thanos", "voldemort"]
  await ctx.send(f"{target.display_name}'s spirit villain is {random.choice(villains)}")

@bot.command()
async def spirit_hero(ctx, target: discord.Member = None):
  target = target or ctx.author
  heroes = ["batman", "superman", "spiderman"]
  await ctx.send(f"{target.display_name}'s spirit hero is {random.choice(heroes)}")

@bot.command()
async def spirit_celebrity(ctx, target: discord.Member = None):
  target = target or ctx.author
  celebs = ["the rock", "keanu reeves", "beyonce"]
  await ctx.send(f"{target.display_name}'s spirit celebrity is {random.choice(celebs)}")

@bot.command()
async def spirit_meme(ctx, target: discord.Member = None):
  target = target or ctx.author
  memes = ["doge", "pepe", "stonks"]
  await ctx.send(f"{target.display_name}'s spirit meme is {random.choice(memes)}")

@bot.command()
async def spirit_emoji(ctx, target: discord.Member = None):
  target = target or ctx.author
  emojis = ["fire", "diamond", "clover", "star"]
  await ctx.send(f"{target.display_name}'s spirit emoji is {random.choice(emojis)}")

@bot.command()
async def spirit_quote(ctx, target: discord.Member = None):
  target = target or ctx.author
  quotes = ["just do it", "live laugh love", "yolo"]
  await ctx.send(f"{target.display_name}'s spirit quote is: {random.choice(quotes)}")

@bot.command()
async def spirit_word(ctx, target: discord.Member = None):
  target = target or ctx.author
  words = ["ember", "flame", "chaos", "destiny"]
  await ctx.send(f"{target.display_name}'s spirit word is {random.choice(words)}")

@bot.command()
async def spirit_number_lucky(ctx, target: discord.Member = None):
  target = target or ctx.author
  num = random.randint(1, 100)
  await ctx.send(f"{target.display_name}'s lucky number is {num}")

@bot.command()
async def spirit_day(ctx, target: discord.Member = None):
  target = target or ctx.author
  days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
  await ctx.send(f"{target.display_name}'s lucky day is {random.choice(days)}")

@bot.command()
async def spirit_month(ctx, target: discord.Member = None):
  target = target or ctx.author
  months = ["january", "february", "march", "april", "may", "june"]
  await ctx.send(f"{target.display_name}'s lucky month is {random.choice(months)}")

@bot.command()
async def spirit_season(ctx, target: discord.Member = None):
  target = target or ctx.author
  seasons = ["spring", "summer", "fall", "winter"]
  await ctx.send(f"{target.display_name}'s lucky season is {random.choice(seasons)}")

@bot.command()
async def spirit_time(ctx, target: discord.Member = None):
  target = target or ctx.author
  hour = random.randint(1, 12)
  minute = random.randint(0, 59)
  ampm = random.choice(["am", "pm"])
  await ctx.send(f"{target.display_name}'s lucky time is {hour}:{minute:02d} {ampm}")

@bot.command()
async def spirit_place(ctx, target: discord.Member = None):
  target = target or ctx.author
  places = ["the beach", "the mountains", "the city", "the forest"]
  await ctx.send(f"{target.display_name}'s lucky place is {random.choice(places)}")

@bot.command()
async def spirit_crystal(ctx, target: discord.Member = None):
  target = target or ctx.author
  crystals = ["amethyst", "quartz", "ruby", "sapphire"]
  await ctx.send(f"{target.display_name}'s spirit crystal is {random.choice(crystals)}")

@bot.command()
async def spirit_flower(ctx, target: discord.Member = None):
  target = target or ctx.author
  flowers = ["rose", "tulip", "sunflower", "lily"]
  await ctx.send(f"{target.display_name}'s spirit flower is {random.choice(flowers)}")

@bot.command()
async def spirit_tree(ctx, target: discord.Member = None):
  target = target or ctx.author
  trees = ["oak", "pine", "willow", "birch"]
  await ctx.send(f"{target.display_name}'s spirit tree is {random.choice(trees)}")

@bot.command()
async def spirit_gem(ctx, target: discord.Member = None):
  target = target or ctx.author
  gems = ["ruby", "sapphire", "emerald", "diamond"]
  await ctx.send(f"{target.display_name}'s spirit gem is {random.choice(gems)}")

@bot.command()
async def spirit_metal(ctx, target: discord.Member = None):
  target = target or ctx.author
  metals = ["gold", "silver", "iron", "copper"]
  await ctx.send(f"{target.display_name}'s spirit metal is {random.choice(metals)}")

@bot.command()
async def spirit_planet(ctx, target: discord.Member = None):
  target = target or ctx.author
  planets = ["mercury", "venus", "earth", "mars", "jupiter"]
  await ctx.send(f"{target.display_name}'s spirit planet is {random.choice(planets)}")

@bot.command()
async def spirit_star(ctx, target: discord.Member = None):
  target = target or ctx.author
  stars = ["sirius", "betelgeuse", "rigel", "vega"]
  await ctx.send(f"{target.display_name}'s spirit star is {random.choice(stars)}")

@bot.command()
async def spirit_galaxy(ctx, target: discord.Member = None):
  target = target or ctx.author
  galaxies = ["milky way", "andromeda", "triangulum"]
  await ctx.send(f"{target.display_name}'s spirit galaxy is {random.choice(galaxies)}")

@bot.command()
async def spirit_weather(ctx, target: discord.Member = None):
  target = target or ctx.author
  weathers = ["sunny", "rainy", "stormy", "snowy"]
  await ctx.send(f"{target.display_name}'s spirit weather is {random.choice(weathers)}")

@bot.command()
async def spirit_landscape(ctx, target: discord.Member = None):
  target = target or ctx.author
  landscapes = ["mountains", "ocean", "forest", "desert"]
  await ctx.send(f"{target.display_name}'s spirit landscape is {random.choice(landscapes)}")

@bot.command()
async def spirit_architecture(ctx, target: discord.Member = None):
  target = target or ctx.author
  archs = ["gothic", "modern", "classical", "futuristic"]
  await ctx.send(f"{target.display_name}'s spirit architecture is {random.choice(archs)}")

@bot.command()
async def spirit_art(ctx, target: discord.Member = None):
  target = target or ctx.author
  arts = ["impressionism", "surrealism", "abstract", "realism"]
  await ctx.send(f"{target.display_name}'s spirit art style is {random.choice(arts)}")

@bot.command()
async def spirit_music(ctx, target: discord.Member = None):
  target = target or ctx.author
  genres = ["rock", "pop", "hip hop", "jazz"]
  await ctx.send(f"{target.display_name}'s spirit music genre is {random.choice(genres)}")

@bot.command()
async def spirit_dance(ctx, target: discord.Member = None):
  target = target or ctx.author
  dances = ["ballet", "hip hop", "salsa", "tango"]
  await ctx.send(f"{target.display_name}'s spirit dance is {random.choice(dances)}")

@bot.command()
async def spirit_sport(ctx, target: discord.Member = None):
  target = target or ctx.author
  sports = ["basketball", "soccer", "tennis", "swimming"]
  await ctx.send(f"{target.display_name}'s spirit sport is {random.choice(sports)}")

@bot.command()
async def spirit_boardgame(ctx, target: discord.Member = None):
  target = target or ctx.author
  games = ["chess", "monopoly", "risk", "clue"]
  await ctx.send(f"{target.display_name}'s spirit board game is {random.choice(games)}")

@bot.command()
async def spirit_cardgame(ctx, target: discord.Member = None):
  target = target or ctx.author
  games = ["poker", "blackjack", "uno", "magic"]
  await ctx.send(f"{target.display_name}'s spirit card game is {random.choice(games)}")

@bot.command()
async def spirit_videogame(ctx, target: discord.Member = None):
  target = target or ctx.author
  games = ["minecraft", "dark souls", "zelda", "mario"]
  await ctx.send(f"{target.display_name}'s spirit video game is {random.choice(games)}")

@bot.command()
async def spirit_book(ctx, target: discord.Member = None):
  target = target or ctx.author
  books = ["harry potter", "lord of the rings", "game of thrones"]
  await ctx.send(f"{target.display_name}'s spirit book is {random.choice(books)}")

@bot.command()
async def spirit_author(ctx, target: discord.Member = None):
  target = target or ctx.author
  authors = ["shakespeare", "tolkien", "rowling"]
  await ctx.send(f"{target.display_name}'s spirit author is {random.choice(authors)}")

@bot.command()
async def spirit_poet(ctx, target: discord.Member = None):
  target = target or ctx.author
  poets = ["shakespeare", "poe", "frost"]
  await ctx.send(f"{target.display_name}'s spirit poet is {random.choice(poets)}")

@bot.command()
async def spirit_painter(ctx, target: discord.Member = None):
  target = target or ctx.author
  painters = ["van gogh", "picasso", "davinci"]
  await ctx.send(f"{target.display_name}'s spirit painter is {random.choice(painters)}")

@bot.command()
async def spirit_scientist(ctx, target: discord.Member = None):
  target = target or ctx.author
  scientists = ["einstein", "newton", "tesla"]
  await ctx.send(f"{target.display_name}'s spirit scientist is {random.choice(scientists)}")

@bot.command()
async def spirit_philosopher(ctx, target: discord.Member = None):
  target = target or ctx.author
  philosophers = ["socrates", "plato", "aristotle"]
  await ctx.send(f"{target.display_name}'s spirit philosopher is {random.choice(philosophers)}")

@bot.command()
async def spirit_inventor(ctx, target: discord.Member = None):
  target = target or ctx.author
  inventors = ["edison", "tesla", "da vinci"]
  await ctx.send(f"{target.display_name}'s spirit inventor is {random.choice(inventors)}")

@bot.command()
async def spirit_explorer(ctx, target: discord.Member = None):
  target = target or ctx.author
  explorers = ["columbus", "magellan", "marco polo"]
  await ctx.send(f"{target.display_name}'s spirit explorer is {random.choice(explorers)}")

@bot.command()
async def spirit_warrior(ctx, target: discord.Member = None):
  target = target or ctx.author
  warriors = ["spartan", "samurai", "viking"]
  await ctx.send(f"{target.display_name}'s spirit warrior is a {random.choice(warriors)}")

@bot.command()
async def spirit_king(ctx, target: discord.Member = None):
  target = target or ctx.author
  kings = ["arthur", "richard", "henry"]
  await ctx.send(f"{target.display_name}'s spirit king is {random.choice(kings)}")

@bot.command()
async def spirit_queen(ctx, target: discord.Member = None):
  target = target or ctx.author
  queens = ["elizabeth", "cleopatra", "victoria"]
  await ctx.send(f"{target.display_name}'s spirit queen is {random.choice(queens)}")

@bot.command()
async def spirit_god(ctx, target: discord.Member = None):
  target = target or ctx.author
  gods = ["zeus", "thor", "odin"]
  await ctx.send(f"{target.display_name}'s spirit god is {random.choice(gods)}")

@bot.command()
async def spirit_goddess(ctx, target: discord.Member = None):
  target = target or ctx.author
  goddesses = ["aphrodite", "athena", "freya"]
  await ctx.send(f"{target.display_name}'s spirit goddess is {random.choice(goddesses)}")

@bot.command()
async def spirit_mythical(ctx, target: discord.Member = None):
  target = target or ctx.author
  creatures = ["dragon", "phoenix", "unicorn"]
  await ctx.send(f"{target.display_name}'s spirit mythical creature is a {random.choice(creatures)}")

@bot.command()
async def spirit_fairy(ctx, target: discord.Member = None):
  target = target or ctx.author
  fairies = ["tinkerbell", "tooth fairy", "pixie"]
  await ctx.send(f"{target.display_name}'s spirit fairy is {random.choice(fairies)}")

@bot.command()
async def spirit_wizard(ctx, target: discord.Member = None):
  target = target or ctx.author
  wizards = ["gandalf", "dumbledore", "merlin"]
  await ctx.send(f"{target.display_name}'s spirit wizard is {random.choice(wizards)}")

@bot.command()
async def spirit_witch(ctx, target: discord.Member = None):
  target = target or ctx.author
  witches = ["glinda", "wicked witch", "hermione"]
  await ctx.send(f"{target.display_name}'s spirit witch is {random.choice(witches)}")

@bot.command()
async def spirit_vampire(ctx, target: discord.Member = None):
  target = target or ctx.author
  vamps = ["dracula", "edward", "lestat"]
  await ctx.send(f"{target.display_name}'s spirit vampire is {random.choice(vamps)}")

@bot.command()
async def spirit_werewolf(ctx, target: discord.Member = None):
  target = target or ctx.author
  wolves = ["jacob", "tyler", "scott"]
  await ctx.send(f"{target.display_name}'s spirit werewolf is {random.choice(wolves)}")

@bot.command()
async def spirit_zombie(ctx, target: discord.Member = None):
  target = target or ctx.author
  zombies = ["walker", "runner", "crawler"]
  await ctx.send(f"{target.display_name}'s spirit zombie is a {random.choice(zombies)}")

@bot.command()
async def spirit_ghost(ctx, target: discord.Member = None):
  target = target or ctx.author
  ghosts = ["casper", "slimer", "patrick swayze"]
  await ctx.send(f"{target.display_name}'s spirit ghost is {random.choice(ghosts)}")

@bot.command()
async def spirit_demon(ctx, target: discord.Member = None):
  target = target or ctx.author
  demons = ["lucifer", "satan", "beelzebub"]
  await ctx.send(f"{target.display_name}'s spirit demon is {random.choice(demons)}")

@bot.command()
async def spirit_angel(ctx, target: discord.Member = None):
  target = target or ctx.author
  angels = ["michael", "gabriel", "raphael"]
  await ctx.send(f"{target.display_name}'s spirit angel is {random.choice(angels)}")

@bot.command()
async def spirit_dragon(ctx, target: discord.Member = None):
  target = target or ctx.author
  dragons = ["smaug", "drogon", "toothless"]
  await ctx.send(f"{target.display_name}'s spirit dragon is {random.choice(dragons)}")

@bot.command()
async def spirit_phoenix(ctx, target: discord.Member = None):
  target = target or ctx.author
  phoenixes = ["fawkes", "ho-oh", "jean grey"]
  await ctx.send(f"{target.display_name}'s spirit phoenix is {random.choice(phoenixes)}")

@bot.command()
async def spirit_unicorn(ctx, target: discord.Member = None):
  target = target or ctx.author
  unicorns = ["charlie", "twilight sparkle"]
  await ctx.send(f"{target.display_name}'s spirit unicorn is {random.choice(unicorns)}")

@bot.command()
async def spirit_griffin(ctx, target: discord.Member = None):
  target = target or ctx.author
  griffins = ["buckbeak", "griffin"]
  await ctx.send(f"{target.display_name}'s spirit griffin is {random.choice(griffins)}")

@bot.command()
async def spirit_kraken(ctx, target: discord.Member = None):
  target = target or ctx.author
  krakens = ["the kraken", "cthulhu"]
  await ctx.send(f"{target.display_name}'s spirit kraken is {random.choice(krakens)}")

@bot.command()
async def spirit_chimera(ctx, target: discord.Member = None):
  target = target or ctx.author
  chimeras = ["the chimera", "the manticore"]
  await ctx.send(f"{target.display_name}'s spirit chimera is {random.choice(chimeras)}")

@bot.command()
async def spirit_sphinx(ctx, target: discord.Member = None):
  target = target or ctx.author
  sphinxes = ["the sphinx", "the riddler"]
  await ctx.send(f"{target.display_name}'s spirit sphinx is {random.choice(sphinxes)}")

@bot.command()
async def spirit_minotaur(ctx, target: discord.Member = None):
  target = target or ctx.author
  minotaurs = ["the minotaur", "asterion"]
  await ctx.send(f"{target.display_name}'s spirit minotaur is {random.choice(minotaurs)}")

@bot.command()
async def spirit_centaur(ctx, target: discord.Member = None):
  target = target or ctx.author
  centaurs = ["chiron", "the centaur"]
  await ctx.send(f"{target.display_name}'s spirit centaur is {random.choice(centaurs)}")

@bot.command()
async def spirit_mermaid(ctx, target: discord.Member = None):
  target = target or ctx.author
  mermaids = ["ariel", "the little mermaid"]
  await ctx.send(f"{target.display_name}'s spirit mermaid is {random.choice(mermaids)}")

@bot.command()
async def spirit_pirate(ctx, target: discord.Member = None):
  target = target or ctx.author
  pirates = ["jack sparrow", "blackbeard"]
  await ctx.send(f"{target.display_name}'s spirit pirate is {random.choice(pirates)}")

@bot.command()
async def spirit_ninja(ctx, target: discord.Member = None):
  target = target or ctx.author
  ninjas = ["naruto", "sasuke"]
  await ctx.send(f"{target.display_name}'s spirit ninja is {random.choice(ninjas)}")

@bot.command()
async def spirit_samurai(ctx, target: discord.Member = None):
  target = target or ctx.author
  samurais = ["miyamoto musashi", "the last samurai"]
  await ctx.send(f"{target.display_name}'s spirit samurai is {random.choice(samurais)}")

@bot.command()
async def spirit_knight(ctx, target: discord.Member = None):
  target = target or ctx.author
  knights = ["king arthur", "lancelot"]
  await ctx.send(f"{target.display_name}'s spirit knight is {random.choice(knights)}")

@bot.command()
async def spirit_viking(ctx, target: discord.Member = None):
  target = target or ctx.author
  vikings = ["ragnar", "bjorn"]
  await ctx.send(f"{target.display_name}'s spirit viking is {random.choice(vikings)}")

@bot.command()
async def spirit_cowboy(ctx, target: discord.Member = None):
  target = target or ctx.author
  cowboys = ["clint eastwood", "john wayne"]
  await ctx.send(f"{target.display_name}'s spirit cowboy is {random.choice(cowboys)}")

@bot.command()
async def spirit_astronaut(ctx, target: discord.Member = None):
  target = target or ctx.author
  astronauts = ["neil armstrong", "buzz aldrin"]
  await ctx.send(f"{target.display_name}'s spirit astronaut is {random.choice(astronauts)}")

@bot.command()
async def spirit_detective(ctx, target: discord.Member = None):
  target = target or ctx.author
  detectives = ["sherlock holmes", "batman"]
  await ctx.send(f"{target.display_name}'s spirit detective is {random.choice(detectives)}")

@bot.command()
async def spirit_spy_cmd(ctx, target: discord.Member = None):
  target = target or ctx.author
  spies = ["james bond", "ethan hunt"]
  await ctx.send(f"{target.display_name}'s spirit spy is {random.choice(spies)}")

@bot.command()
async def spirit_assassin(ctx, target: discord.Member = None):
  target = target or ctx.author
  assassins = ["ezio", "altair"]
  await ctx.send(f"{target.display_name}'s spirit assassin is {random.choice(assassins)}")

@bot.command()
async def spirit_mercenary(ctx, target: discord.Member = None):
  target = target or ctx.author
  mercs = ["deadpool", "the mandalorian"]
  await ctx.send(f"{target.display_name}'s spirit mercenary is {random.choice(mercs)}")

@bot.command()
async def spirit_soldier(ctx, target: discord.Member = None):
  target = target or ctx.author
  soldiers = ["captain america", "master chief"]
  await ctx.send(f"{target.display_name}'s spirit soldier is {random.choice(soldiers)}")

@bot.command()
async def spirit_pilot(ctx, target: discord.Member = None):
  target = target or ctx.author
  pilots = ["maverick", "han solo"]
  await ctx.send(f"{target.display_name}'s spirit pilot is {random.choice(pilots)}")

@bot.command()
async def spirit_driver(ctx, target: discord.Member = None):
  target = target or ctx.author
  drivers = ["dominic toretto", "the stig"]
  await ctx.send(f"{target.display_name}'s spirit driver is {random.choice(drivers)}")

@bot.command()
async def spirit_racer(ctx, target: discord.Member = None):
  await spirit_driver(ctx, target)

@bot.command()
async def spirit_surfer(ctx, target: discord.Member = None):
  target = target or ctx.author
  surfers = ["kelly slater", "the silver surfer"]
  await ctx.send(f"{target.display_name}'s spirit surfer is {random.choice(surfers)}")

@bot.command()
async def spirit_skater(ctx, target: discord.Member = None):
  target = target or ctx.author
  skaters = ["tony hawk", "rodney mullen"]
  await ctx.send(f"{target.display_name}'s spirit skater is {random.choice(skaters)}")

@bot.command()
async def spirit_climber(ctx, target: discord.Member = None):
  target = target or ctx.author
  climbers = ["alex honnold", "edmund hillary"]
  await ctx.send(f"{target.display_name}'s spirit climber is {random.choice(climbers)}")

@bot.command()
async def spirit_diver(ctx, target: discord.Member = None):
  target = target or ctx.author
  divers = ["jacques cousteau", "the deep sea diver"]
  await ctx.send(f"{target.display_name}'s spirit diver is {random.choice(divers)}")

@bot.command()
async def spirit_hunter_cmd(ctx, target: discord.Member = None):
  target = target or ctx.author
  hunters = ["geralt", "the witcher"]
  await ctx.send(f"{target.display_name}'s spirit hunter is {random.choice(hunters)}")

@bot.command()
async def spirit_ranger(ctx, target: discord.Member = None):
  target = target or ctx.author
  rangers = ["aragorn", "the park ranger"]
  await ctx.send(f"{target.display_name}'s spirit ranger is {random.choice(rangers)}")

@bot.command()
async def spirit_druid(ctx, target: discord.Member = None):
  target = target or ctx.author
  druids = ["the druid", "the nature wizard"]
  await ctx.send(f"{target.display_name}'s spirit druid is {random.choice(druids)}")

@bot.command()
async def spirit_paladin(ctx, target: discord.Member = None):
  target = target or ctx.author
  paladins = ["the paladin", "the holy knight"]
  await ctx.send(f"{target.display_name}'s spirit paladin is {random.choice(paladins)}")

@bot.command()
async def spirit_monk(ctx, target: discord.Member = None):
  target = target or ctx.author
  monks = ["the monk", "the shaolin master"]
  await ctx.send(f"{target.display_name}'s spirit monk is {random.choice(monks)}")

@bot.command()
async def spirit_bard(ctx, target: discord.Member = None):
  target = target or ctx.author
  bards = ["the bard", "the minstrel"]
  await ctx.send(f"{target.display_name}'s spirit bard is {random.choice(bards)}")

@bot.command()
async def spirit_rogue(ctx, target: discord.Member = None):
  target = target or ctx.author
  rogues = ["the rogue", "the thief"]
  await ctx.send(f"{target.display_name}'s spirit rogue is {random.choice(rogues)}")

@bot.command()
async def spirit_barbarian(ctx, target: discord.Member = None):
  target = target or ctx.author
  barbarians = ["the barbarian", "the berserker"]
  await ctx.send(f"{target.display_name}'s spirit barbarian is {random.choice(barbarians)}")

@bot.command()
async def spirit_sorcerer(ctx, target: discord.Member = None):
  target = target or ctx.author
  sorcerers = ["the sorcerer", "the mage"]
  await ctx.send(f"{target.display_name}'s spirit sorcerer is {random.choice(sorcerers)}")

@bot.command()
async def spirit_warlock(ctx, target: discord.Member = None):
  target = target or ctx.author
  warlocks = ["the warlock", "the dark mage"]
  await ctx.send(f"{target.display_name}'s spirit warlock is {random.choice(warlocks)}")

@bot.command()
async def spirit_cleric(ctx, target: discord.Member = None):
  target = target or ctx.author
  clerics = ["the cleric", "the healer"]
  await ctx.send(f"{target.display_name}'s spirit cleric is {random.choice(clerics)}")

@bot.command()
async def spirit_artificer(ctx, target: discord.Member = None):
  target = target or ctx.author
  artificers = ["the artificer", "the inventor"]
  await ctx.send(f"{target.display_name}'s spirit artificer is {random.choice(artificers)}")

@bot.command()
async def spirit_ranger_dnd(ctx, target: discord.Member = None):
  target = target or ctx.author
  rangers = ["the ranger", "the tracker"]
  await ctx.send(f"{target.display_name}'s spirit ranger is {random.choice(rangers)}")

@bot.command()
async def spirit_fighter(ctx, target: discord.Member = None):
  target = target or ctx.author
  fighters = ["the fighter", "the warrior"]
  await ctx.send(f"{target.display_name}'s spirit fighter is {random.choice(fighters)}")

@bot.command()
async def spirit_ranger_class(ctx, target: discord.Member = None):
  await spirit_ranger_dnd(ctx, target)

@bot.command()
async def spirit_druid_class(ctx, target: discord.Member = None):
  await spirit_druid(ctx, target)

@bot.command()
async def spirit_paladin_class(ctx, target: discord.Member = None):
  await spirit_paladin(ctx, target)

@bot.command()
async def spirit_monk_class(ctx, target: discord.Member = None):
  await spirit_monk(ctx, target)

@bot.command()
async def spirit_bard_class(ctx, target: discord.Member = None):
  await spirit_bard(ctx, target)

@bot.command()
async def spirit_rogue_class(ctx, target: discord.Member = None):
  await spirit_rogue(ctx, target)

@bot.command()
async def spirit_barbarian_class(ctx, target: discord.Member = None):
  await spirit_barbarian(ctx, target)

@bot.command()
async def spirit_sorcerer_class(ctx, target: discord.Member = None):
  await spirit_sorcerer(ctx, target)

@bot.command()
async def spirit_warlock_class(ctx, target: discord.Member = None):
  await spirit_warlock(ctx, target)

@bot.command()
async def spirit_cleric_class(ctx, target: discord.Member = None):
  await spirit_cleric(ctx, target)

@bot.command()
async def spirit_artificer_class(ctx, target: discord.Member = None):
  await spirit_artificer(ctx, target)

@bot.command()
async def spirit_fighter_class(ctx, target: discord.Member = None):
  await spirit_fighter(ctx, target)

@bot.command()
async def spirit_wizard_class(ctx, target: discord.Member = None):
  await spirit_wizard(ctx, target)

@bot.command()
async def spirit_witch_class(ctx, target: discord.Member = None):
  await spirit_witch(ctx, target)

@bot.command()
async def spirit_vampire_class(ctx, target: discord.Member = None):
  await spirit_vampire(ctx, target)

@bot.command()
async def spirit_werewolf_class(ctx, target: discord.Member = None):
  await spirit_werewolf(ctx, target)

@bot.command()
async def spirit_zombie_class(ctx, target: discord.Member = None):
  await spirit_zombie(ctx, target)

@bot.command()
async def spirit_ghost_class(ctx, target: discord.Member = None):
  await spirit_ghost(ctx, target)

@bot.command()
async def spirit_demon_class(ctx, target: discord.Member = None):
  await spirit_demon(ctx, target)

@bot.command()
async def spirit_angel_class(ctx, target: discord.Member = None):
  await spirit_angel(ctx, target)

@bot.command()
async def spirit_dragon_class(ctx, target: discord.Member = None):
  await spirit_dragon(ctx, target)

@bot.command()
async def spirit_phoenix_class(ctx, target: discord.Member = None):
  await spirit_phoenix(ctx, target)

@bot.command()
async def spirit_unicorn_class(ctx, target: discord.Member = None):
  await spirit_unicorn(ctx, target)

@bot.command()
async def spirit_griffin_class(ctx, target: discord.Member = None):
  await spirit_griffin(ctx, target)

@bot.command()
async def spirit_kraken_class(ctx, target: discord.Member = None):
  await spirit_kraken(ctx, target)

@bot.command()
async def spirit_chimera_class(ctx, target: discord.Member = None):
  await spirit_chimera(ctx, target)

@bot.command()
async def spirit_sphinx_class(ctx, target: discord.Member = None):
  await spirit_sphinx(ctx, target)

@bot.command()
async def spirit_minotaur_class(ctx, target: discord.Member = None):
  await spirit_minotaur(ctx, target)

@bot.command()
async def spirit_centaur_class(ctx, target: discord.Member = None):
  await spirit_centaur(ctx, target)

@bot.command()
async def spirit_mermaid_class(ctx, target: discord.Member = None):
  await spirit_mermaid(ctx, target)

@bot.command()
async def spirit_pirate_class(ctx, target: discord.Member = None):
  await spirit_pirate(ctx, target)

@bot.command()
async def spirit_ninja_class(ctx, target: discord.Member = None):
  await spirit_ninja(ctx, target)

@bot.command()
async def spirit_samurai_class(ctx, target: discord.Member = None):
  await spirit_samurai(ctx, target)

@bot.command()
async def spirit_knight_class(ctx, target: discord.Member = None):
  await spirit_knight(ctx, target)

@bot.command()
async def spirit_viking_class(ctx, target: discord.Member = None):
  await spirit_viking(ctx, target)

@bot.command()
async def spirit_cowboy_class(ctx, target: discord.Member = None):
  await spirit_cowboy(ctx, target)

@bot.command()
async def spirit_astronaut_class(ctx, target: discord.Member = None):
  await spirit_astronaut(ctx, target)

@bot.command()
async def spirit_detective_class(ctx, target: discord.Member = None):
  await spirit_detective(ctx, target)

@bot.command()
async def spirit_spy_class(ctx, target: discord.Member = None):
  await spirit_spy_cmd(ctx, target)

@bot.command()
async def spirit_assassin_class(ctx, target: discord.Member = None):
  await spirit_assassin(ctx, target)

@bot.command()
async def spirit_mercenary_class(ctx, target: discord.Member = None):
  await spirit_mercenary(ctx, target)

@bot.command()
async def spirit_soldier_class(ctx, target: discord.Member = None):
  await spirit_soldier(ctx, target)

@bot.command()
async def spirit_pilot_class(ctx, target: discord.Member = None):
  await spirit_pilot(ctx, target)

@bot.command()
async def spirit_driver_class(ctx, target: discord.Member = None):
  await spirit_driver(ctx, target)

@bot.command()
async def spirit_racer_class(ctx, target: discord.Member = None):
  await spirit_racer(ctx, target)

@bot.command()
async def spirit_surfer_class(ctx, target: discord.Member = None):
  await spirit_surfer(ctx, target)

@bot.command()
async def spirit_skater_class(ctx, target: discord.Member = None):
  await spirit_skater(ctx, target)

@bot.command()
async def spirit_climber_class(ctx, target: discord.Member = None):
  await spirit_climber(ctx, target)

@bot.command()
async def spirit_diver_class(ctx, target: discord.Member = None):
  await spirit_diver(ctx, target)

@bot.command()
async def spirit_hunter_class(ctx, target: discord.Member = None):
  await spirit_hunter_cmd(ctx, target)

@bot.command()
async def spirit_ranger_dnd_class(ctx, target: discord.Member = None):
  await spirit_ranger_dnd(ctx, target)

@bot.command()
async def spirit_paladin_dnd(ctx, target: discord.Member = None):
  await spirit_paladin(ctx, target)

@bot.command()
async def spirit_monk_dnd(ctx, target: discord.Member = None):
  await spirit_monk(ctx, target)

@bot.command()
async def spirit_bard_dnd(ctx, target: discord.Member = None):
  await spirit_bard(ctx, target)

@bot.command()
async def spirit_rogue_dnd(ctx, target: discord.Member = None):
  await spirit_rogue(ctx, target)

@bot.command()
async def spirit_barbarian_dnd(ctx, target: discord.Member = None):
  await spirit_barbarian(ctx, target)

@bot.command()
async def spirit_sorcerer_dnd(ctx, target: discord.Member = None):
  await spirit_sorcerer(ctx, target)

@bot.command()
async def spirit_warlock_dnd(ctx, target: discord.Member = None):
  await spirit_warlock(ctx, target)

@bot.command()
async def spirit_cleric_dnd(ctx, target: discord.Member = None):
  await spirit_cleric(ctx, target)

@bot.command()
async def spirit_artificer_dnd(ctx, target: discord.Member = None):
  await spirit_artificer(ctx, target)

@bot.command()
async def spirit_fighter_dnd(ctx, target: discord.Member = None):
  await spirit_fighter(ctx, target)

@bot.command()
async def spirit_wizard_dnd(ctx, target: discord.Member = None):
  await spirit_wizard(ctx, target)

@bot.command()
async def spirit_witch_dnd(ctx, target: discord.Member = None):
  await spirit_witch(ctx, target)

@bot.command()
async def spirit_vampire_dnd(ctx, target: discord.Member = None):
  await spirit_vampire(ctx, target)

@bot.command()
async def spirit_werewolf_dnd(ctx, target: discord.Member = None):
  await spirit_werewolf(ctx, target)

@bot.command()
async def spirit_zombie_dnd(ctx, target: discord.Member = None):
  await spirit_zombie(ctx, target)

@bot.command()
async def spirit_ghost_dnd(ctx, target: discord.Member = None):
  await spirit_ghost(ctx, target)

@bot.command()
async def spirit_demon_dnd(ctx, target: discord.Member = None):
  await spirit_demon(ctx, target)

@bot.command()
async def spirit_angel_dnd(ctx, target: discord.Member = None):
  await spirit_angel(ctx, target)

@bot.command()
async def spirit_dragon_dnd(ctx, target: discord.Member = None):
  await spirit_dragon(ctx, target)

@bot.command()
async def spirit_phoenix_dnd(ctx, target: discord.Member = None):
  await spirit_phoenix(ctx, target)

@bot.command()
async def spirit_unicorn_dnd(ctx, target: discord.Member = None):
  await spirit_unicorn(ctx, target)

@bot.command()
async def spirit_griffin_dnd(ctx, target: discord.Member = None):
  await spirit_griffin(ctx, target)

@bot.command()
async def spirit_kraken_dnd(ctx, target: discord.Member = None):
  await spirit_kraken(ctx, target)

@bot.command()
async def spirit_chimera_dnd(ctx, target: discord.Member = None):
  await spirit_chimera(ctx, target)

@bot.command()
async def spirit_sphinx_dnd(ctx, target: discord.Member = None):
  await spirit_sphinx(ctx, target)

@bot.command()
async def spirit_minotaur_dnd(ctx, target: discord.Member = None):
  await spirit_minotaur(ctx, target)

@bot.command()
async def spirit_centaur_dnd(ctx, target: discord.Member = None):
  await spirit_centaur(ctx, target)

@bot.command()
async def spirit_mermaid_dnd(ctx, target: discord.Member = None):
  await spirit_mermaid(ctx, target)

@bot.command()
async def spirit_pirate_dnd(ctx, target: discord.Member = None):
  await spirit_pirate(ctx, target)

@bot.command()
async def spirit_ninja_dnd(ctx, target: discord.Member = None):
  await spirit_ninja(ctx, target)

@bot.command()
async def spirit_samurai_dnd(ctx, target: discord.Member = None):
  await spirit_samurai(ctx, target)

@bot.command()
async def spirit_knight_dnd(ctx, target: discord.Member = None):
  await spirit_knight(ctx, target)

@bot.command()
async def spirit_viking_dnd(ctx, target: discord.Member = None):
  await spirit_viking(ctx, target)

@bot.command()
async def spirit_cowboy_dnd(ctx, target: discord.Member = None):
  await spirit_cowboy(ctx, target)

@bot.command()
async def spirit_astronaut_dnd(ctx, target: discord.Member = None):
  await spirit_astronaut(ctx, target)

@bot.command()
async def spirit_detective_dnd(ctx, target: discord.Member = None):
  await spirit_detective(ctx, target)

@bot.command()
async def spirit_spy_dnd(ctx, target: discord.Member = None):
  await spirit_spy_cmd(ctx, target)

@bot.command()
async def spirit_assassin_dnd(ctx, target: discord.Member = None):
  await spirit_assassin(ctx, target)

@bot.command()
async def spirit_mercenary_dnd(ctx, target: discord.Member = None):
  await spirit_mercenary(ctx, target)

@bot.command()
async def spirit_soldier_dnd(ctx, target: discord.Member = None):
  await spirit_soldier(ctx, target)

@bot.command()
async def spirit_pilot_dnd(ctx, target: discord.Member = None):
  await spirit_pilot(ctx, target)

@bot.command()
async def spirit_driver_dnd(ctx, target: discord.Member = None):
  await spirit_driver(ctx, target)

@bot.command()
async def spirit_racer_dnd(ctx, target: discord.Member = None):
  await spirit_racer(ctx, target)

@bot.command()
async def spirit_surfer_dnd(ctx, target: discord.Member = None):
  await spirit_surfer(ctx, target)

@bot.command()
async def spirit_skater_dnd(ctx, target: discord.Member = None):
  await spirit_skater(ctx, target)

@bot.command()
async def spirit_climber_dnd(ctx, target: discord.Member = None):
  await spirit_climber(ctx, target)

@bot.command()
async def spirit_diver_dnd(ctx, target: discord.Member = None):
  await spirit_diver(ctx, target)

@bot.command()
async def spirit_hunter_dnd(ctx, target: discord.Member = None):
  await spirit_hunter_cmd(ctx, target)

@bot.command()
async def spirit_ranger_dnd_dnd(ctx, target: discord.Member = None):
  await spirit_ranger_dnd(ctx, target)


# ── PAGINATED HELP COMMAND ──

HELP_PAGES = {
  1: """
**page 1/3 - economy, creatures, combat** 🔥

**economy:**
embers, daily, streak, beg, scam, invest, heist, loan, repay, burn, send, work, fish, hunt, mine, dig, search, crime

**creatures:**
summon, cage, release, feed, neglect, mood, evolve, breed, sacrifice, rename, favorite, trade, auction, bid, inspect, adopt, kidnap

**combat:**
duel, raid, ambush, defend, berserk, bribe, flee, taunt, combo, revive, wager, rank, attack, defend_boss, heal, flee_boss

**gambling:**
dice, shells, coinflip, cf, spin, surge, vault, pick, chase, chamber, rig, slots, blackjack, roulette, lottery, gamble, bet, double, allin
""",
  2: """
**page 2/3 - social, utility, weird, moderation** 🔥

**social:**
marry, divorce, will, cult, betray, tribute, roast, confess, ship, howgay, howsimp, howsmart, howdumb, howrich, howlucky, howsus, howcringe, howbased, pp, iq, height, weight, age, birthday, zodiac, color, food, animal

**utility:**
tutorial, stats, server, global_lb, settings, cooldowns, changelog, ping, avatar, userinfo, roll, choose, flipcoin, rps, rate, joke, fact, quote, meme, roastme, compliment, insult, song, movie, game, hobby, job, car, house, phone

**weird:**
dream, curse, bless, time, weather, oracle, mimic, glitch, lore, quit, eightball, magic8ball, fortune_cookie, horoscope, tarot_card, crystal_ball, palm_reading, aura_reading, zodiac_sign, compatibility, soulmate, enemy, bestfriend, rival, twin, clone, doppelganger

**moderation:**
kick, ban, unban, mute, unmute, purge, warn, warnings, clearwarns, lock, unlock, slowmode, nick, roleadd, roleremove
""",
  3: """
**page 3/3 - fun, reactions, admin, spirit** 🔥

**fun/misc:**
pet, tickle, poke, wave, salute, highfive, fistbump, nod, shrug, facepalm, clap, bow, cheer, panic, yeet, boop, stare, lurk, lurkmode, afk, back, remind, poll, vote, coin, password, calc, reverse, uppercase, lowercase, len_text, repeat, mock, spoiler, bold, italic, underline, strikethrough, code, quote_text, embed, say, echo, announce, botinfo, invite, support, report, suggest, uptime, version, credits, donate, vote_bot, premium, status, pingme, selfdestruct, hack, nuke, boom, dab, floss, default_dance, take_the_l, rekt, oof, big_oof, f_in_chat, rip, respect, sus, imposter, vented, emergency, eject, tasks, sabotage, report_body, meeting, skip, guilty, innocent, defend_me, accuse, alibi, sus_meter, trust, distrust, crewmate, sheriff, jester, executioner, psychic, medic, engineer, spy, mayor, veteran, vig, jail, execute, revive_player, haunt, seance, ghost, alive, dead, medium, retributionist, transporter, escort, consort, blackmail, forger, framer, hypnotist, ambusher_cmd, poisoner, hexmaster, hex, pestilence, juggernaut, arsonist, douse, ignite, serialkiller, mafioso, godfather, blackmailer, consigliere, janitor, disguiser, survivor, amnesiac, guardianangel, pirate, plunderer, crusader, trapper, trap, lookout, tracker, investigator, sheriff_cmd, bodyguard, doctor_cmd, reveal, whisper, lastwill, read_will, deathnote, rolelist, werewolf, fullmoon, howl, maul, plaguebearer, infect, necromancer, reanimate, medusa, stone, puppeteer, control, covenleader, potionmaster, heal_potion, kill_potion, reveal_potion, crusade, deus_vult, bonk_cmd, hornyjail, unhorny, horny_meter, downbad, touchgrass, gooutside, shower, sleep_cmd, hydrate, eat_cmd, selfcare, mentalhealth, vent, therapy, advice, wisdom, lifehack, protip, hacklife, motivation, demotivation, pep_talk, reality_check, wake_up, reality, exist, void_cmd, abyss, chaos, order, balance_cmd, yin_yang, karma, good_karma, bad_karma

**admin (owner only):**
give, setember, remove, wipe

**spirit commands:**
spirit_animal, spirit_color, spirit_number, spirit_food, spirit_drink, spirit_song, spirit_movie, spirit_game, spirit_hobby, spirit_job, spirit_car, spirit_house, spirit_phone, spirit_pet, spirit_weapon, spirit_element, spirit_magic, spirit_villain, spirit_hero, spirit_celebrity, spirit_meme, spirit_emoji, spirit_quote, spirit_word, spirit_number_lucky, spirit_day, spirit_month, spirit_season, spirit_time, spirit_place, spirit_crystal, spirit_flower, spirit_tree, spirit_gem, spirit_metal, spirit_planet, spirit_star, spirit_galaxy, spirit_weather, spirit_landscape, spirit_architecture, spirit_art, spirit_music, spirit_dance, spirit_sport, spirit_boardgame, spirit_cardgame, spirit_videogame, spirit_book, spirit_author, spirit_poet, spirit_painter, spirit_scientist, spirit_philosopher, spirit_inventor, spirit_explorer, spirit_warrior, spirit_king, spirit_queen, spirit_god, spirit_goddess, spirit_mythical, spirit_fairy, spirit_wizard, spirit_witch, spirit_vampire, spirit_werewolf, spirit_zombie, spirit_ghost, spirit_demon, spirit_angel, spirit_dragon, spirit_phoenix, spirit_unicorn, spirit_griffin, spirit_kraken, spirit_chimera, spirit_sphinx, spirit_minotaur, spirit_centaur, spirit_mermaid, spirit_pirate, spirit_ninja, spirit_samurai, spirit_knight, spirit_viking, spirit_cowboy, spirit_astronaut, spirit_detective, spirit_spy_cmd, spirit_assassin, spirit_mercenary, spirit_soldier, spirit_pilot, spirit_driver, spirit_racer, spirit_surfer, spirit_skater, spirit_climber, spirit_diver, spirit_hunter_cmd, spirit_ranger, spirit_druid, spirit_paladin, spirit_monk, spirit_bard, spirit_rogue, spirit_barbarian, spirit_sorcerer, spirit_warlock, spirit_cleric, spirit_artificer, spirit_ranger_dnd, spirit_fighter, spirit_ranger_class, spirit_druid_class, spirit_paladin_class, spirit_monk_class, spirit_bard_class, spirit_rogue_class, spirit_barbarian_class, spirit_sorcerer_class, spirit_warlock_class, spirit_cleric_class, spirit_artificer_class, spirit_fighter_class, spirit_wizard_class, spirit_witch_class, spirit_vampire_class, spirit_werewolf_class, spirit_zombie_class, spirit_ghost_class, spirit_demon_class, spirit_angel_class, spirit_dragon_class, spirit_phoenix_class, spirit_unicorn_class, spirit_griffin_class, spirit_kraken_class, spirit_chimera_class, spirit_sphinx_class, spirit_minotaur_class, spirit_centaur_class, spirit_mermaid_class, spirit_pirate_class, spirit_ninja_class, spirit_samurai_class, spirit_knight_class, spirit_viking_class, spirit_cowboy_class, spirit_astronaut_class, spirit_detective_class, spirit_spy_class, spirit_assassin_class, spirit_mercenary_class, spirit_soldier_class, spirit_pilot_class, spirit_driver_class, spirit_racer_class, spirit_surfer_class, spirit_skater_class, spirit_climber_class, spirit_diver_class, spirit_hunter_class, spirit_ranger_dnd_class, spirit_paladin_dnd, spirit_monk_dnd, spirit_bard_dnd, spirit_rogue_dnd, spirit_barbarian_dnd, spirit_sorcerer_dnd, spirit_warlock_dnd, spirit_cleric_dnd, spirit_artificer_dnd, spirit_fighter_dnd, spirit_wizard_dnd, spirit_witch_dnd, spirit_vampire_dnd, spirit_werewolf_dnd, spirit_zombie_dnd, spirit_ghost_dnd, spirit_demon_dnd, spirit_angel_dnd, spirit_dragon_dnd, spirit_phoenix_dnd, spirit_unicorn_dnd, spirit_griffin_dnd, spirit_kraken_dnd, spirit_chimera_dnd, spirit_sphinx_dnd, spirit_minotaur_dnd, spirit_centaur_dnd, spirit_mermaid_dnd, spirit_pirate_dnd, spirit_ninja_dnd, spirit_samurai_dnd, spirit_knight_dnd, spirit_viking_dnd, spirit_cowboy_dnd, spirit_astronaut_dnd, spirit_detective_dnd, spirit_spy_dnd, spirit_assassin_dnd, spirit_mercenary_dnd, spirit_soldier_dnd, spirit_pilot_dnd, spirit_driver_dnd, spirit_racer_dnd, spirit_surfer_dnd, spirit_skater_dnd, spirit_climber_dnd, spirit_diver_dnd, spirit_hunter_dnd, spirit_ranger_dnd_dnd
"""
}

@bot.command()
async def help(ctx, page: str = None):
  """show help with pages"""
  if not page:
    await ctx.send(
      "**flame bot help** 🔥\n"
      "prefix: **f ** or **flame ** (space required!)\n"
      "currency: **embers**\n\n"
      "use **f help 1** for economy/creatures/combat/gambling\n"
      "use **f help 2** for social/utility/weird/moderation\n"
      "use **f help 3** for fun/admin/spirit commands\n\n"
      "total commands: **350+**\n"
      "owner: justaflamewithfragz"
    )
    return

  try:
    page_num = int(page)
    if page_num in HELP_PAGES:
      await ctx.send(HELP_PAGES[page_num])
    else:
      await ctx.send("only pages 1, 2, and 3 exist bro")
  except ValueError:
    await ctx.send("thats not a page number bro. use 1, 2, or 3")

# ── RUN THE BOT ──
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
  print("ERROR: no DISCORD_TOKEN environment variable found!")
  print("set it in railway or run: export DISCORD_TOKEN=your_token")
else:
  bot.run(TOKEN)
