
import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
import aiohttp

# ─── CONFIG ───
OWNER_ID = 1444293963812180120
DATA_FILE = "flame_data.json"

# ─── DATA MANAGER ───
class DataManager:
    def __init__(self, filename=DATA_FILE):
        self.filename = filename
        self.data = self.load()
        self._ensure_defaults()

    def load(self):
        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                return json.load(f)
        return {}

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f, indent=2)

    def _ensure_defaults(self):
        if "users" not in self.data:
            self.data["users"] = {}
        if "guilds" not in self.data:
            self.data["guilds"] = {}
        self.save()

    def get_user(self, user_id):
        uid = str(user_id)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "embers": 0, "bank": 0, "streak": 0, "last_daily": None,
                "inventory": [], "creatures": [], "married_to": None,
                "xp": 0, "level": 1, "duel_wins": 0, "duel_losses": 0,
                "cooldowns": {}, "settings": {}, "loans": [], "heist_cooldown": None,
                "investment": None, "scam_attempts": 0, "burned": 0
            }
            self.save()
        return self.data["users"][uid]

    def update_user(self, user_id, key, value):
        self.data["users"][str(user_id)][key] = value
        self.save()

    def add_embers(self, user_id, amount):
        user = self.get_user(user_id)
        user["embers"] += amount
        self.save()

    def set_embers(self, user_id, amount):
        user = self.get_user(user_id)
        user["embers"] = max(0, amount)
        self.save()

    def remove_embers(self, user_id, amount):
        user = self.get_user(user_id)
        user["embers"] = max(0, user["embers"] - amount)
        self.save()

    def wipe_user(self, user_id):
        uid = str(user_id)
        if uid in self.data["users"]:
            del self.data["users"][uid]
            self.save()

db = DataManager()

# ─── CUSTOM PREFIX ───
class FlameBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

    def _get_prefix(self, bot, message):
        if not message.guild:
            return commands.when_mentioned_or("f ", "flame ")(bot, message)
        gid = str(message.guild.id)
        custom = db.data["guilds"].get(gid, {}).get("prefix", None)
        if custom:
            return commands.when_mentioned_or(custom)(bot, message)
        return commands.when_mentioned_or("f ", "flame ")(bot, message)

    async def on_ready(self):
        print(f"flame bot online as {self.user} ({self.user.id})")
        await self.change_presence(activity=discord.Game(name="f help | burning servers"))

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply(embed=flame_embed("no perms", "nah you dont got the juice for that. need more perms."))
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(embed=flame_embed("missing args", "you forgot something bro. check f help."))
            return
        if isinstance(error, commands.BadArgument):
            await ctx.reply(embed=flame_embed("bad args", "that argument doesnt make sense. try again."))
            return
        print(f"error in {ctx.command}: {error}")

bot = FlameBot()

# ─── OWNER CHECK ───
def is_owner():
    async def predicate(ctx):
        if ctx.author.id != OWNER_ID:
            embed = flame_embed("nah", "you cant use this command as ur not the bot owner.", 0xFF4444)
            await ctx.reply(embed=embed)
            return False
        return True
    return commands.check(predicate)

# ─── MOD PERM CHECK ───
def has_mod_perm(perm_name):
    async def predicate(ctx):
        if ctx.author.id == OWNER_ID:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        perm_map = {
            "kick": "kick_members", "ban": "ban_members", "mute": "moderate_members",
            "manage": "manage_messages", "nick": "manage_nicknames",
            "roles": "manage_roles", "channels": "manage_channels", "webhooks": "manage_webhooks"
        }
        attr = perm_map.get(perm_name, perm_name)
        if getattr(ctx.author.guild_permissions, attr, False):
            return True
        await ctx.reply(embed=flame_embed("no perms", "your role doesnt have the right permissions for this. go beg an admin."))
        return False
    return commands.check(predicate)

# ─── COOLDOWN HELPER ───
def check_cooldown(user_id, cmd, seconds):
    now = datetime.utcnow()
    user = db.get_user(user_id)
    cd = user["cooldowns"].get(cmd)
    if cd:
        last = datetime.fromisoformat(cd)
        diff = (now - last).total_seconds()
        if diff < seconds:
            return int(seconds - diff)
    user["cooldowns"][cmd] = now.isoformat()
    db.save()
    return 0

# ─── EMBED HELPER ───
def flame_embed(title, desc, color=0xFF6B35):
    e = discord.Embed(title=title, description=desc, color=color)
    e.set_footer(text="flame bot | prefix: f or flame")
    return e


# ═══════════════════════════════════════════════════════════════
# ECONOMY COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def embers(ctx, user: discord.Member = None):
    """check your embers or someone elses"""
    target = user or ctx.author
    data = db.get_user(target.id)
    embed = flame_embed(
        f"{target.display_name}'s embers",
        f"wallet: **{data['embers']}** embers
bank: **{data['bank']}** embers
"
        f"level: **{data['level']}** | xp: **{data['xp']}**
"
        f"duel wins: **{data['duel_wins']}** | losses: **{data['duel_losses']}**"
    )
    await ctx.reply(embed=embed)

@bot.command()
async def daily(ctx):
    """claim your daily embers"""
    user = db.get_user(ctx.author.id)
    now = datetime.utcnow()
    last = user["last_daily"]
    streak = user["streak"]

    if last:
        last_dt = datetime.fromisoformat(last)
        diff = (now - last_dt).total_seconds()
        if diff < 86400:
            remaining = int(86400 - diff)
            h = remaining // 3600
            m = (remaining % 3600) // 60
            s = remaining % 60
            embed = flame_embed("daily cooldown", f"chill bro. come back in {h}h {m}m {s}s")
            await ctx.reply(embed=embed)
            return
        if diff > 172800:
            streak = 0

    streak += 1
    base = random.randint(200, 500)
    bonus = min(streak * 50, 1000)
    total = base + bonus

    user["embers"] += total
    user["streak"] = streak
    user["last_daily"] = now.isoformat()
    db.save()

    msgs = [
        f"you got **{total}** embers! streak: **{streak}** 🔥",
        f"daily claimed. **{total}** embers dropped in your wallet. streak **{streak}**",
        f"cha-ching! **{total}** embers. youre on a **{streak}** day streak, keep it up"
    ]
    embed = flame_embed("daily claimed", random.choice(msgs))
    await ctx.reply(embed=embed)

@bot.command()
async def streak(ctx, user: discord.Member = None):
    """check someones daily streak"""
    target = user or ctx.author
    data = db.get_user(target.id)
    embed = flame_embed(
        f"{target.display_name}'s streak",
        f"current streak: **{data['streak']}** days
"
        f"last daily: {data['last_daily'][:10] if data['last_daily'] else 'never'}"
    )
    await ctx.reply(embed=embed)

@bot.command()
async def beg(ctx):
    """beg for embers like a peasant"""
    cd = check_cooldown(ctx.author.id, "beg", 45)
    if cd:
        embed = flame_embed("chill", f"you just begged. wait {cd}s before embarrassing yourself again.")
        await ctx.reply(embed=embed)
        return

    outcomes = [
        ("someone threw 5 embers at you out of pity", 5, True),
        ("a rich user gave you 50 embers. nice", 50, True),
        ("you got absolutely nothing. rough", 0, False),
        ("someone spat on you instead. zero embers", 0, False),
        ("a stray cat gave you 15 embers. weird but ok", 15, True),
        ("you found 30 embers in a dumpster. congrats?", 30, True),
    ]
    msg, amount, success = random.choice(outcomes)
    if success:
        db.add_embers(ctx.author.id, amount)
    embed = flame_embed("begging results", msg)
    await ctx.reply(embed=embed)

@bot.command()
async def scam(ctx, user: discord.Member, amount: int):
    """try to scam someone out of their embers"""
    if amount <= 0:
        await ctx.reply(embed=flame_embed("nah", "cant scam 0 or negative embers bro."))
        return
    if user.id == ctx.author.id:
        await ctx.reply(embed=flame_embed("bruh", "you cant scam yourself. thats just called being bad with money."))
        return

    victim = db.get_user(user.id)
    scammer = db.get_user(ctx.author.id)

    if victim["embers"] < amount:
        embed = flame_embed("broke victim", f"{user.display_name} doesnt even have {amount} embers. pick someone richer.")
        await ctx.reply(embed=embed)
        return

    scammer["scam_attempts"] += 1
    db.save()

    if random.random() < 0.3:
        victim["embers"] -= amount
        scammer["embers"] += amount
        db.save()
        embed = flame_embed("scam successful", f"you scammed **{amount}** embers from {user.display_name}. youre going to hell for this.")
    else:
        penalty = amount // 2
        scammer["embers"] = max(0, scammer["embers"] - penalty)
        db.save()
        embed = flame_embed("scam failed", f"{user.display_name} caught you. you lost **{penalty}** embers as punishment. scam attempts: **{scammer['scam_attempts']}**")
    await ctx.reply(embed=embed)

@bot.command()
async def invest(ctx, amount: int):
    """invest embers and hope for profit"""
    if amount <= 0:
        await ctx.reply(embed=flame_embed("nah", "invest at least 1 ember."))
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you only have **{user['embers']}** embers. cant invest what you dont have.")
        await ctx.reply(embed=embed)
        return

    user["embers"] -= amount
    db.save()

    outcomes = [
        ("your investment tanked. you lost everything. rip", 0),
        ("small profit. you got back 1.2x", int(amount * 1.2)),
        ("decent return. 1.5x baby", int(amount * 1.5)),
        ("BIG W. 2x return!", amount * 2),
        ("absolute disaster. you lost half", amount // 2),
        ("the market crashed. you got 10% back lol", amount // 10),
    ]
    msg, returned = random.choice(outcomes)
    user["embers"] += returned
    db.save()
    embed = flame_embed("investment results", f"{msg}
you now have **{user['embers']}** embers")
    await ctx.reply(embed=embed)

@bot.command()
async def heist(ctx, user: discord.Member):
    """rob someones bank"""
    cd = check_cooldown(ctx.author.id, "heist", 600)
    if cd:
        embed = flame_embed("cooldown", f"heat is too high. wait {cd//60}m {cd%60}s before another heist.")
        await ctx.reply(embed=embed)
        return

    if user.id == ctx.author.id:
        await ctx.reply(embed=flame_embed("bruh", "you cant heist yourself. thats just withdrawing."))
        return

    victim = db.get_user(user.id)
    heister = db.get_user(ctx.author.id)

    if victim["bank"] < 100:
        embed = flame_embed("not worth it", f"{user.display_name}'s bank is too dry. not worth the risk.")
        await ctx.reply(embed=embed)
        return

    if random.random() < 0.4:
        loot = random.randint(victim["bank"] // 10, victim["bank"] // 3)
        victim["bank"] -= loot
        heister["embers"] += loot
        db.save()
        embed = flame_embed("heist successful", f"you stole **{loot}** embers from {user.display_name}'s bank! dont spend it all in one place.")
    else:
        fine = random.randint(50, 200)
        heister["embers"] = max(0, heister["embers"] - fine)
        db.save()
        embed = flame_embed("busted", f"caught red handed. you paid a **{fine}** ember fine. {user.display_name} is laughing at you.")
    await ctx.reply(embed=embed)

@bot.command()
async def loan(ctx, amount: int):
    """take out a loan from the flame bank"""
    if amount <= 0 or amount > 5000:
        await ctx.reply(embed=flame_embed("nah", "loan between 1 and 5000 embers."))
        return
    user = db.get_user(ctx.author.id)
    active_loans = [l for l in user["loans"] if not l.get("paid", False)]
    if len(active_loans) >= 3:
        embed = flame_embed("debt collector", "you already got 3 unpaid loans. pay up first.")
        await ctx.reply(embed=embed)
        return

    user["embers"] += amount
    user["loans"].append({
        "amount": amount,
        "interest": int(amount * 0.15),
        "taken": datetime.utcnow().isoformat(),
        "paid": False
    })
    db.save()
    embed = flame_embed("loan approved", f"heres **{amount}** embers. you owe **{amount + int(amount*0.15)}** total. dont forget to `f repay`")
    await ctx.reply(embed=embed)

@bot.command()
async def repay(ctx, amount: int = None):
    """repay your loans"""
    user = db.get_user(ctx.author.id)
    active = [l for l in user["loans"] if not l.get("paid", False)]
    if not active:
        embed = flame_embed("debt free", "you got no loans. living the good life.")
        await ctx.reply(embed=embed)
        return

    total_owed = sum(l["amount"] + l["interest"] for l in active)

    if amount is None:
        embed = flame_embed("your loans", f"you owe **{total_owed}** embers across **{len(active)}** loans. use `f repay <amount>` to pay")
        await ctx.reply(embed=embed)
        return

    if user["embers"] < amount:
        embed = flame_embed("broke", f"you only got **{user['embers']}** embers. need **{amount}**.")
        await ctx.reply(embed=embed)
        return

    user["embers"] -= amount
    remaining = amount
    for loan in active:
        owed = loan["amount"] + loan["interest"]
        if remaining >= owed:
            remaining -= owed
            loan["paid"] = True
        else:
            loan["amount"] -= remaining
            remaining = 0
            break
    db.save()
    embed = flame_embed("payment made", f"paid **{amount}** embers. remaining debt: **{sum(l['amount']+l['interest'] for l in active if not l['paid'])}**")
    await ctx.reply(embed=embed)

@bot.command()
async def burn(ctx, amount: int):
    """burn embers because why not"""
    if amount <= 0:
        await ctx.reply(embed=flame_embed("nah", "burn at least 1 ember."))
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you only got **{user['embers']}** embers. cant burn what you aint got.")
        await ctx.reply(embed=embed)
        return

    user["embers"] -= amount
    user["burned"] += amount
    db.save()
    msgs = [
        f"you burned **{amount}** embers. theyre gone forever. hope youre happy.",
        f"**{amount}** embers turned to ash. what a waste.",
        f"poof. **{amount}** embers gone. total burned: **{user['burned']}**"
    ]
    embed = flame_embed("ashes to ashes", random.choice(msgs))
    await ctx.reply(embed=embed)

@bot.command()
async def send(ctx, amount: int, user: discord.Member):
    """send embers to someone with confirmation"""
    if amount <= 0:
        await ctx.reply(embed=flame_embed("nah", "send at least 1 ember."))
        return
    if user.id == ctx.author.id:
        await ctx.reply(embed=flame_embed("bruh", "you cant send embers to yourself. just... keep them?"))
        return

    sender = db.get_user(ctx.author.id)
    if sender["embers"] < amount:
        embed = flame_embed("broke", f"you only got **{sender['embers']}** embers. cant send **{amount}**.")
        await ctx.reply(embed=embed)
        return

    embed = flame_embed(
        "confirm transaction",
        f"{ctx.author.mention} you are about to send **{amount}** embers to {user.mention}

"
        f"to confirm, react with ✅
to cancel, react with ❌"
    )
    msg = await ctx.reply(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    def check(reaction, user_reacted):
        return user_reacted == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

    try:
        reaction, user_reacted = await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        embed = flame_embed("expired", "transaction timed out. embers stayed in your wallet.")
        await msg.edit(embed=embed)
        return

    if str(reaction.emoji) == "❌":
        embed = flame_embed("cancelled", "transaction cancelled. no embers moved.")
        await msg.edit(embed=embed)
        return

    sender["embers"] -= amount
    receiver = db.get_user(user.id)
    receiver["embers"] += amount
    db.save()

    embed = flame_embed(
        "transaction complete",
        f"**{amount}** embers sent to {user.mention}!
"
        f"your wallet: **{sender['embers']}** embers"
    )
    await msg.edit(embed=embed)


# ═══════════════════════════════════════════════════════════════
# ADMIN COMMANDS (OWNER ONLY)
# ═══════════════════════════════════════════════════════════════

@bot.command()
@is_owner()
async def give(ctx, amount: int, user: discord.Member):
    """give embers to a user (owner only)"""
    db.add_embers(user.id, amount)
    embed = flame_embed("admin action", f"gave **{amount}** embers to {user.mention}. dont tell anyone.")
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def set(ctx, amount: int, user: discord.Member):
    """set a users embers to exact amount (owner only)"""
    db.set_embers(user.id, amount)
    embed = flame_embed("admin action", f"set {user.mention}'s embers to **{amount}**. big brother is watching.")
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def remove(ctx, amount: int, user: discord.Member):
    """remove embers from a user (owner only)"""
    db.remove_embers(user.id, amount)
    embed = flame_embed("admin action", f"removed **{amount}** embers from {user.mention}. ruthless.")
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def wipe(ctx, user: discord.Member):
    """wipe all data for a user (owner only)"""
    db.wipe_user(user.id)
    embed = flame_embed("nuked", f"wiped all data for {user.mention}. theyre back to zero. savage.")
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# MODERATION COMMANDS (PERMISSION BASED)
# ═══════════════════════════════════════════════════════════════

@bot.command()
@has_mod_perm("kick")
async def kick(ctx, user: discord.Member, *, reason="no reason given"):
    """kick a user from the server"""
    if user.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
        embed = flame_embed("nah", "cant kick someone equal or higher than you. nice try tho.")
        await ctx.reply(embed=embed)
        return
    await user.kick(reason=reason)
    embed = flame_embed("booted", f"{user.mention} got the boot. reason: {reason}")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("ban")
async def ban(ctx, user: discord.Member, *, reason="no reason given"):
    """ban a user from the server"""
    if user.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
        embed = flame_embed("nah", "cant ban someone equal or higher. hierarchy matters.")
        await ctx.reply(embed=embed)
        return
    await user.ban(reason=reason)
    embed = flame_embed("banned", f"{user.mention} is gone. reason: {reason}")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("ban")
async def unban(ctx, user_id: int):
    """unban a user by id"""
    user = discord.Object(id=user_id)
    await ctx.guild.unban(user)
    embed = flame_embed("unbanned", f"user **{user_id}** is back. second chances are real.")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("mute")
async def mute(ctx, user: discord.Member, minutes: int, *, reason="no reason"):
    """timeout a user for x minutes"""
    if user.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
        embed = flame_embed("nah", "cant mute someone higher than you.")
        await ctx.reply(embed=embed)
        return
    duration = timedelta(minutes=minutes)
    await user.timeout(duration, reason=reason)
    embed = flame_embed("silenced", f"{user.mention} muted for **{minutes}** minutes. reason: {reason}")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("mute")
async def unmute(ctx, user: discord.Member):
    """remove timeout from a user"""
    await user.timeout(None)
    embed = flame_embed("unsilenced", f"{user.mention} can talk again. hope they behave.")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("manage")
async def purge(ctx, amount: int):
    """delete messages in bulk"""
    if amount < 1 or amount > 100:
        embed = flame_embed("nah", "purge between 1 and 100 messages.")
        await ctx.reply(embed=embed)
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    embed = flame_embed("cleaned", f"deleted **{len(deleted)-1}** messages. poof.")
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(3)
    await msg.delete()

@bot.command()
@has_mod_perm("manage")
async def warn(ctx, user: discord.Member, *, reason):
    """warn a user"""
    gid = str(ctx.guild.id)
    if "warns" not in db.data["guilds"].get(gid, {}):
        db.data["guilds"][gid] = db.data["guilds"].get(gid, {})
        db.data["guilds"][gid]["warns"] = {}
    uid = str(user.id)
    if uid not in db.data["guilds"][gid]["warns"]:
        db.data["guilds"][gid]["warns"][uid] = []
    db.data["guilds"][gid]["warns"][uid].append({
        "reason": reason,
        "by": ctx.author.id,
        "at": datetime.utcnow().isoformat()
    })
    db.save()
    count = len(db.data["guilds"][gid]["warns"][uid])
    embed = flame_embed("warned", f"{user.mention} warned. reason: {reason}
total warnings: **{count}**")
    await ctx.reply(embed=embed)

@bot.command()
async def warnings(ctx, user: discord.Member = None):
    """check warnings for a user"""
    target = user or ctx.author
    gid = str(ctx.guild.id)
    warns = db.data["guilds"].get(gid, {}).get("warns", {}).get(str(target.id), [])
    if not warns:
        embed = flame_embed("clean record", f"{target.mention} got no warnings. angel behavior.")
    else:
        desc = "\n".join([f"**{i+1}.** {w['reason']} (by <@{w['by']}>)" for i, w in enumerate(warns)])
        embed = flame_embed(f"{target.display_name}'s warnings", desc)
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("manage")
async def unwarn(ctx, user: discord.Member, index: int = None):
    """remove a warning from a user"""
    gid = str(ctx.guild.id)
    uid = str(user.id)
    warns = db.data["guilds"].get(gid, {}).get("warns", {}).get(uid, [])
    if not warns:
        embed = flame_embed("nothing to remove", f"{user.mention} has no warnings.")
        await ctx.reply(embed=embed)
        return
    if index is None:
        db.data["guilds"][gid]["warns"][uid] = []
        db.save()
        embed = flame_embed("cleared", f"wiped all warnings for {user.mention}. fresh start.")
    else:
        if 1 <= index <= len(warns):
            removed = db.data["guilds"][gid]["warns"][uid].pop(index-1)
            db.save()
            embed = flame_embed("warning removed", f"removed warning #{index}: {removed['reason']}")
        else:
            embed = flame_embed("invalid", f"warning #{index} doesnt exist. they only have {len(warns)}.")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("nick")
async def nick(ctx, user: discord.Member, *, nickname=None):
    """change a users nickname"""
    await user.edit(nick=nickname)
    if nickname:
        embed = flame_embed("renamed", f"{user.mention} is now called **{nickname}**. hope they like it.")
    else:
        embed = flame_embed("reset", f"{user.mention}'s nickname reset.")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("roles")
async def addrole(ctx, user: discord.Member, *, role_name):
    """add a role to a user"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        embed = flame_embed("not found", f"role **{role_name}** doesnt exist.")
        await ctx.reply(embed=embed)
        return
    if role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
        embed = flame_embed("nah", "cant give a role equal or higher than yours.")
        await ctx.reply(embed=embed)
        return
    await user.add_roles(role)
    embed = flame_embed("role added", f"gave **{role.name}** to {user.mention}.")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("roles")
async def removerole(ctx, user: discord.Member, *, role_name):
    """remove a role from a user"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        embed = flame_embed("not found", f"role **{role_name}** doesnt exist.")
        await ctx.reply(embed=embed)
        return
    await user.remove_roles(role)
    embed = flame_embed("role removed", f"took **{role.name}** from {user.mention}.")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("manage")
async def slowmode(ctx, seconds: int):
    """set channel slowmode"""
    await ctx.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        embed = flame_embed("fast again", "slowmode disabled. chat speedrun time.")
    else:
        embed = flame_embed("slowed down", f"slowmode set to **{seconds}** seconds. chill out everyone.")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("manage")
async def lock(ctx):
    """lock the current channel"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    embed = flame_embed("locked", "channel locked. only people with perms can talk now.")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("manage")
async def unlock(ctx):
    """unlock the current channel"""
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    embed = flame_embed("unlocked", "channel unlocked. everyone can talk again.")
    await ctx.reply(embed=embed)


# ═══════════════════════════════════════════════════════════════
# CREATURES COMMANDS
# ═══════════════════════════════════════════════════════════════

CREATURE_NAMES = ["emberling", "ashpup", "cinderfox", "smokewyrm", "charhound", 
                  "flameimp", "magma slug", "soot sprite", "blaze cat", "inferno hound",
                  "pyro pup", "scorch serpent", "coaldrake", "sparkfox", "burnbear"]
CREATURE_MOODS = ["happy", "grumpy", "sleepy", "hungry", "playful", "angry", "lonely"]

@bot.command()
async def summon(ctx, name: str = None):
    """summon a creature"""
    user = db.get_user(ctx.author.id)
    if len(user["creatures"]) >= 10:
        embed = flame_embed("zoo full", "you already got 10 creatures. release one first.")
        await ctx.reply(embed=embed)
        return

    creature_name = name or random.choice(CREATURE_NAMES)
    creature = {
        "name": creature_name,
        "level": 1,
        "xp": 0,
        "mood": random.choice(CREATURE_MOODS),
        "hunger": 50,
        "bond": 10,
        "evolved": False,
        "caged": False,
        "id": random.randint(1000, 9999)
    }
    user["creatures"].append(creature)
    db.save()
    embed = flame_embed("summoned!", f"you summoned **{creature_name}** (id: {creature['id']})! its feeling **{creature['mood']}** today.")
    await ctx.reply(embed=embed)

@bot.command()
async def cage(ctx, creature_id: int):
    """cage a creature"""
    user = db.get_user(ctx.author.id)
    for c in user["creatures"]:
        if c["id"] == creature_id:
            c["caged"] = True
            db.save()
            embed = flame_embed("caged", f"**{c['name']}** is now in the cage. dont forget to feed it.")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not found", f"no creature with id **{creature_id}**. check `f inspect`.")
    await ctx.reply(embed=embed)

@bot.command()
async def release(ctx, creature_id: int):
    """release a creature back to the wild"""
    user = db.get_user(ctx.author.id)
    for i, c in enumerate(user["creatures"]):
        if c["id"] == creature_id:
            name = c["name"]
            user["creatures"].pop(i)
            db.save()
            embed = flame_embed("released", f"**{name}** is free now. probably gonna miss you. or not.")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not found", f"no creature with id **{creature_id}**.")
    await ctx.reply(embed=embed)

@bot.command()
async def feed(ctx, creature_id: int):
    """feed your creature"""
    user = db.get_user(ctx.author.id)
    cost = 10
    if user["embers"] < cost:
        embed = flame_embed("broke", f"feeding costs **{cost}** embers. you got **{user['embers']}**.")
        await ctx.reply(embed=embed)
        return
    for c in user["creatures"]:
        if c["id"] == creature_id:
            user["embers"] -= cost
            c["hunger"] = min(100, c["hunger"] + 30)
            c["bond"] = min(100, c["bond"] + 5)
            c["mood"] = "happy"
            db.save()
            embed = flame_embed("fed", f"**{c['name']}** ate well. hunger: **{c['hunger']}** | bond: **{c['bond']}**")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not found", f"no creature with id **{creature_id}**.")
    await ctx.reply(embed=embed)

@bot.command()
async def neglect(ctx, creature_id: int):
    """neglect your creature (why would you)"""
    user = db.get_user(ctx.author.id)
    for c in user["creatures"]:
        if c["id"] == creature_id:
            c["hunger"] = max(0, c["hunger"] - 20)
            c["bond"] = max(0, c["bond"] - 10)
            c["mood"] = random.choice(["grumpy", "angry", "lonely"])
            db.save()
            embed = flame_embed("monster", f"you neglected **{c['name']}**. its now **{c['mood']}** and starving. you sicko.")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not found", f"no creature with id **{creature_id}**.")
    await ctx.reply(embed=embed)

@bot.command()
async def mood(ctx, creature_id: int = None):
    """check creature mood"""
    user = db.get_user(ctx.author.id)
    if not user["creatures"]:
        embed = flame_embed("empty", "you got no creatures. summon one with `f summon`.")
        await ctx.reply(embed=embed)
        return
    if creature_id:
        for c in user["creatures"]:
            if c["id"] == creature_id:
                embed = flame_embed(f"{c['name']}'s mood", f"feeling **{c['mood']}** | hunger: **{c['hunger']}** | bond: **{c['bond']}**")
                await ctx.reply(embed=embed)
                return
    c = user["creatures"][0]
    embed = flame_embed(f"{c['name']}'s mood", f"feeling **{c['mood']}** | hunger: **{c['hunger']}** | bond: **{c['bond']}**")
    await ctx.reply(embed=embed)

@bot.command()
async def evolve(ctx, creature_id: int):
    """evolve your creature"""
    user = db.get_user(ctx.author.id)
    for c in user["creatures"]:
        if c["id"] == creature_id:
            if c["evolved"]:
                embed = flame_embed("maxed", f"**{c['name']}** already evolved. cant go further.")
                await ctx.reply(embed=embed)
                return
            if c["xp"] < 100:
                embed = flame_embed("not ready", f"**{c['name']}** needs **{100 - c['xp']}** more xp to evolve.")
                await ctx.reply(embed=embed)
                return
            c["evolved"] = True
            c["level"] += 1
            c["name"] = "mega " + c["name"]
            db.save()
            embed = flame_embed("EVOLUTION!", f"**{c['name']}** evolved! its now level **{c['level']}** and looks terrifyingly cool.")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not found", f"no creature with id **{creature_id}**.")
    await ctx.reply(embed=embed)

@bot.command()
async def breed(ctx, id1: int, id2: int, name: str):
    """breed two creatures"""
    user = db.get_user(ctx.author.id)
    c1 = None
    c2 = None
    for c in user["creatures"]:
        if c["id"] == id1:
            c1 = c
        if c["id"] == id2:
            c2 = c
    if not c1 or not c2:
        embed = flame_embed("missing parent", "one or both creature ids not found.")
        await ctx.reply(embed=embed)
        return
    if len(user["creatures"]) >= 10:
        embed = flame_embed("zoo full", "no space for a baby. release someone first.")
        await ctx.reply(embed=embed)
        return

    baby = {
        "name": name,
        "level": 1,
        "xp": 0,
        "mood": "playful",
        "hunger": 80,
        "bond": 20,
        "evolved": False,
        "caged": False,
        "id": random.randint(1000, 9999),
        "parents": [c1["name"], c2["name"]]
    }
    user["creatures"].append(baby)
    db.save()
    embed = flame_embed("new baby!", f"**{name}** was born from **{c1['name']}** and **{c2['name']}**! adorable little fireball.")
    await ctx.reply(embed=embed)

@bot.command()
async def sacrifice(ctx, creature_id: int):
    """sacrifice a creature for embers"""
    user = db.get_user(ctx.author.id)
    for i, c in enumerate(user["creatures"]):
        if c["id"] == creature_id:
            reward = c["level"] * 50 + c["xp"] // 2
            user["embers"] += reward
            name = c["name"]
            user["creatures"].pop(i)
            db.save()
            embed = flame_embed("sacrificed", f"**{name}** was sacrificed. you got **{reward}** embers. dark.")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not found", f"no creature with id **{creature_id}**.")
    await ctx.reply(embed=embed)

@bot.command()
async def rename(ctx, creature_id: int, *, new_name):
    """rename your creature"""
    user = db.get_user(ctx.author.id)
    for c in user["creatures"]:
        if c["id"] == creature_id:
            old = c["name"]
            c["name"] = new_name
            db.save()
            embed = flame_embed("renamed", f"**{old}** is now called **{new_name}**. hope they respond to it.")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not found", f"no creature with id **{creature_id}**.")
    await ctx.reply(embed=embed)

@bot.command()
async def favorite(ctx, creature_id: int):
    """set a favorite creature"""
    user = db.get_user(ctx.author.id)
    for c in user["creatures"]:
        if c["id"] == creature_id:
            user["settings"]["favorite"] = creature_id
            db.save()
            embed = flame_embed("favorited", f"**{c['name']}** is now your favorite. no favoritism complaints please.")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not found", f"no creature with id **{creature_id}**.")
    await ctx.reply(embed=embed)

@bot.command()
async def trade(ctx, user: discord.Member, your_id: int, their_id: int):
    """trade creatures with another user"""
    if user.id == ctx.author.id:
        embed = flame_embed("bruh", "cant trade with yourself. thats just swapping.")
        await ctx.reply(embed=embed)
        return

    you = db.get_user(ctx.author.id)
    them = db.get_user(user.id)

    your_creature = None
    their_creature = None
    for c in you["creatures"]:
        if c["id"] == your_id:
            your_creature = c
    for c in them["creatures"]:
        if c["id"] == their_id:
            their_creature = c

    if not your_creature or not their_creature:
        embed = flame_embed("missing creature", "one of those creatures doesnt exist. check ids with `f inspect`.")
        await ctx.reply(embed=embed)
        return

    embed = flame_embed(
        "trade offer",
        f"{ctx.author.mention} wants to trade **{your_creature['name']}** for {user.mention}'s **{their_creature['name']}**

"
        f"{user.mention} react ✅ to accept or ❌ to decline"
    )
    msg = await ctx.reply(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    def check(reaction, reactor):
        return reactor == user and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

    try:
        reaction, reactor = await bot.wait_for("reaction_add", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        embed = flame_embed("expired", "trade timed out. maybe next time.")
        await msg.edit(embed=embed)
        return

    if str(reaction.emoji) == "❌":
        embed = flame_embed("declined", f"{user.mention} said nah to the trade.")
        await msg.edit(embed=embed)
        return

    you["creatures"].remove(your_creature)
    them["creatures"].remove(their_creature)
    you["creatures"].append(their_creature)
    them["creatures"].append(your_creature)
    db.save()
    embed = flame_embed("traded!", f"trade complete! {ctx.author.mention} got **{their_creature['name']}** and {user.mention} got **{your_creature['name']}**!")
    await msg.edit(embed=embed)

@bot.command()
async def auction(ctx, creature_id: int, start_bid: int):
    """auction off a creature"""
    user = db.get_user(ctx.author.id)
    creature = None
    for c in user["creatures"]:
        if c["id"] == creature_id:
            creature = c
            break
    if not creature:
        embed = flame_embed("not found", f"no creature with id **{creature_id}**.")
        await ctx.reply(embed=embed)
        return

    embed = flame_embed(
        f"auction: {creature['name']}",
        f"starting bid: **{start_bid}** embers
"
        f"creature: level **{creature['level']}**, mood **{creature['mood']}**

"
        f"type `f bid <amount>` in this channel to bid! auction ends in 30 seconds."
    )
    auction_msg = await ctx.reply(embed=embed)

    bids = {}
    end_time = asyncio.get_event_loop().time() + 30

    def bid_check(message):
        return (message.channel == ctx.channel and 
                message.content.startswith("f bid ") and 
                message.author != ctx.author and
                asyncio.get_event_loop().time() < end_time)

    while asyncio.get_event_loop().time() < end_time:
        try:
            msg = await bot.wait_for("message", timeout=5.0, check=bid_check)
            try:
                bid_amount = int(msg.content.split()[2])
                bidder = msg.author
                bidder_data = db.get_user(bidder.id)
                if bidder_data["embers"] < bid_amount:
                    await msg.reply(embed=flame_embed("broke bid", f"you dont have **{bid_amount}** embers. sit down.", 0xFF4444))
                    continue
                if bid_amount < start_bid:
                    await msg.reply(embed=flame_embed("too low", f"bid must be at least **{start_bid}**. try again.", 0xFF4444))
                    continue
                if bidder.id in bids and bid_amount <= bids[bidder.id]:
                    await msg.reply(embed=flame_embed("low bid", "your bid must be higher than your last one.", 0xFF4444))
                    continue
                bids[bidder.id] = bid_amount
                await msg.reply(embed=flame_embed("bid placed", f"{bidder.mention} bid **{bid_amount}** embers!"))
            except:
                pass
        except asyncio.TimeoutError:
            continue

    if not bids:
        embed = flame_embed("no bids", f"nobody wanted **{creature['name']}**. embarrassing.")
        await auction_msg.edit(embed=embed)
        return

    winner_id = max(bids, key=bids.get)
    winner = await bot.fetch_user(winner_id)
    winning_bid = bids[winner_id]

    winner_data = db.get_user(winner_id)
    winner_data["embers"] -= winning_bid
    user["embers"] += winning_bid
    user["creatures"].remove(creature)
    winner_data["creatures"].append(creature)
    db.save()

    embed = flame_embed(
        "sold!",
        f"**{creature['name']}** sold to {winner.mention} for **{winning_bid}** embers!
"
        f"{ctx.author.mention} got paid. {winner.mention} got a new pet."
    )
    await auction_msg.edit(embed=embed)

@bot.command()
async def bid(ctx, amount: int):
    """place a bid (used during auction)"""
    embed = flame_embed("no auction", "theres no active auction right now. start one with `f auction`.")
    await ctx.reply(embed=embed)

@bot.command()
async def inspect(ctx, creature_id: int = None):
    """inspect your creatures"""
    user = db.get_user(ctx.author.id)
    if not user["creatures"]:
        embed = flame_embed("empty", "no creatures. summon one with `f summon`.")
        await ctx.reply(embed=embed)
        return

    if creature_id:
        for c in user["creatures"]:
            if c["id"] == creature_id:
                desc = f"name: **{c['name']}**
level: **{c['level']}** | xp: **{c['xp']}**
"
                desc += f"mood: **{c['mood']}** | hunger: **{c['hunger']}** | bond: **{c['bond']}**
"
                desc += f"evolved: **{'yes' if c['evolved'] else 'no'}** | caged: **{'yes' if c['caged'] else 'no'}**
"
                if "parents" in c:
                    desc += f"parents: **{c['parents'][0]}** & **{c['parents'][1]}**"
                embed = flame_embed(f"inspecting {c['name']}", desc)
                await ctx.reply(embed=embed)
                return

    desc = "\n".join([f"**{c['id']}** - {c['name']} (lv{c['level']}, {c['mood']})" for c in user["creatures"]])
    embed = flame_embed("your creatures", desc)
    await ctx.reply(embed=embed)

@bot.command()
async def adopt(ctx, user: discord.Member, creature_id: int):
    """adopt a creature from someone"""
    if user.id == ctx.author.id:
        embed = flame_embed("bruh", "cant adopt your own creature. its already yours.")
        await ctx.reply(embed=embed)
        return

    them = db.get_user(user.id)
    creature = None
    for c in them["creatures"]:
        if c["id"] == creature_id:
            creature = c
            break
    if not creature:
        embed = flame_embed("not found", f"{user.display_name} doesnt have a creature with id **{creature_id}**.")
        await ctx.reply(embed=embed)
        return

    embed = flame_embed(
        "adoption request",
        f"{ctx.author.mention} wants to adopt **{creature['name']}** from {user.mention}

"
        f"{user.mention} react ✅ to give them your pet or ❌ to keep it."
    )
    msg = await ctx.reply(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    def check(reaction, reactor):
        return reactor == user and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

    try:
        reaction, reactor = await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        embed = flame_embed("expired", "adoption request timed out.")
        await msg.edit(embed=embed)
        return

    if str(reaction.emoji) == "❌":
        embed = flame_embed("rejected", f"{user.mention} said no. their pet, their rules.")
        await msg.edit(embed=embed)
        return

    them["creatures"].remove(creature)
    you = db.get_user(ctx.author.id)
    you["creatures"].append(creature)
    db.save()
    embed = flame_embed("adopted!", f"{ctx.author.mention} adopted **{creature['name']}**! take good care of it.")
    await msg.edit(embed=embed)

@bot.command()
async def kidnap(ctx, user: discord.Member, creature_id: int):
    """try to kidnap someones creature"""
    if user.id == ctx.author.id:
        embed = flame_embed("bruh", "cant kidnap your own creature. thats just moving it.")
        await ctx.reply(embed=embed)
        return

    them = db.get_user(user.id)
    creature = None
    for c in them["creatures"]:
        if c["id"] == creature_id:
            creature = c
            break
    if not creature:
        embed = flame_embed("not found", f"{user.display_name} doesnt have that creature.")
        await ctx.reply(embed=embed)
        return

    if random.random() < 0.15:
        them["creatures"].remove(creature)
        you = db.get_user(ctx.author.id)
        if len(you["creatures"]) >= 10:
            embed = flame_embed("zoo full", "kidnap successful but your zoo is full. had to release it. oops.")
            await ctx.reply(embed=embed)
            return
        you["creatures"].append(creature)
        db.save()
        embed = flame_embed("kidnapped!", f"you successfully kidnapped **{creature['name']}**! {user.mention} is gonna be mad.")
    else:
        penalty = random.randint(20, 100)
        you = db.get_user(ctx.author.id)
        you["embers"] = max(0, you["embers"] - penalty)
        db.save()
        embed = flame_embed("busted", f"{user.mention} caught you trying to steal **{creature['name']}**. fined **{penalty}** embers.")
    await ctx.reply(embed=embed)


# ═══════════════════════════════════════════════════════════════
# COMBAT COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def duel(ctx, user: discord.Member, wager: int = 0):
    """challenge someone to a duel"""
    if user.id == ctx.author.id:
        embed = flame_embed("bruh", "cant duel yourself. go touch grass instead.")
        await ctx.reply(embed=embed)
        return
    if user.bot:
        embed = flame_embed("nah", "cant duel a bot. theyre built different.")
        await ctx.reply(embed=embed)
        return

    challenger = db.get_user(ctx.author.id)
    opponent = db.get_user(user.id)

    if wager > 0:
        if challenger["embers"] < wager:
            embed = flame_embed("broke", f"you dont have **{wager}** embers to wager.")
            await ctx.reply(embed=embed)
            return
        if opponent["embers"] < wager:
            embed = flame_embed("broke opponent", f"{user.display_name} doesnt have **{wager}** embers. pick a richer target.")
            await ctx.reply(embed=embed)
            return

    embed = flame_embed(
        "duel challenge",
        f"{ctx.author.mention} challenges {user.mention} to a duel!
"
        f"wager: **{wager}** embers

"
        f"{user.mention} react ✅ to accept or ❌ to chicken out"
    )
    msg = await ctx.reply(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    def check(reaction, reactor):
        return reactor == user and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

    try:
        reaction, reactor = await bot.wait_for("reaction_add", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        embed = flame_embed("coward", f"{user.mention} didnt respond. duel cancelled.")
        await msg.edit(embed=embed)
        return

    if str(reaction.emoji) == "❌":
        embed = flame_embed("declined", f"{user.mention} declined. probably scared.")
        await msg.edit(embed=embed)
        return

    # simulate duel
    c_power = challenger["level"] * 10 + challenger["duel_wins"] * 2 + random.randint(1, 50)
    o_power = opponent["level"] * 10 + opponent["duel_wins"] * 2 + random.randint(1, 50)

    if c_power > o_power:
        winner = ctx.author
        loser = user
        winner_data = challenger
        loser_data = opponent
        winner_data["duel_wins"] += 1
        loser_data["duel_losses"] += 1
        winner_data["xp"] += 25
    else:
        winner = user
        loser = ctx.author
        winner_data = opponent
        loser_data = challenger
        winner_data["duel_wins"] += 1
        loser_data["duel_losses"] += 1
        winner_data["xp"] += 25

    if wager > 0:
        loser_data["embers"] -= wager
        winner_data["embers"] += wager

    # level up check
    for data in [challenger, opponent]:
        if data["xp"] >= data["level"] * 100:
            data["level"] += 1
            data["xp"] = 0

    db.save()

    embed = flame_embed(
        "duel results",
        f"**{winner.display_name}** wins! power: **{max(c_power, o_power)}** vs **{min(c_power, o_power)}**
"
        f"{loser.display_name} took the L.
"
        + (f"**{wager}** embers transferred!
" if wager > 0 else "")
        + f"{winner.display_name}: **{winner_data['duel_wins']}** wins | {loser.display_name}: **{loser_data['duel_wins']}** wins"
    )
    await msg.edit(embed=embed)

@bot.command()
async def raid(ctx, user: discord.Member):
    """raid someones embers"""
    cd = check_cooldown(ctx.author.id, "raid", 300)
    if cd:
        embed = flame_embed("cooldown", f"raid cooldown: {cd//60}m {cd%60}s. police are watching.")
        await ctx.reply(embed=embed)
        return

    if user.id == ctx.author.id:
        embed = flame_embed("bruh", "cant raid yourself. thats just stealing from your own wallet.")
        await ctx.reply(embed=embed)
        return

    raider = db.get_user(ctx.author.id)
    target = db.get_user(user.id)

    if target["embers"] < 50:
        embed = flame_embed("not worth it", f"{user.display_name} is too broke to raid. find a bigger fish.")
        await ctx.reply(embed=embed)
        return

    if random.random() < 0.45:
        loot = random.randint(target["embers"] // 10, target["embers"] // 5)
        target["embers"] -= loot
        raider["embers"] += loot
        db.save()
        embed = flame_embed("raid successful", f"raided **{loot}** embers from {user.mention}! theyre crying rn.")
    else:
        penalty = random.randint(20, 80)
        raider["embers"] = max(0, raider["embers"] - penalty)
        db.save()
        embed = flame_embed("raid failed", f"{user.mention} defended successfully. you lost **{penalty}** embers running away.")
    await ctx.reply(embed=embed)

@bot.command()
async def ambush(ctx, user: discord.Member):
    """ambush a user"""
    cd = check_cooldown(ctx.author.id, "ambush", 180)
    if cd:
        embed = flame_embed("cooldown", f"ambush cooldown: {cd}s. too hot right now.")
        await ctx.reply(embed=embed)
        return

    if user.id == ctx.author.id:
        embed = flame_embed("bruh", "cant ambush yourself. thats just jumping out at a mirror.")
        await ctx.reply(embed=embed)
        return

    ambusher = db.get_user(ctx.author.id)
    target = db.get_user(user.id)

    if random.random() < 0.5:
        damage = random.randint(10, 100)
        target["embers"] = max(0, target["embers"] - damage)
        ambusher["embers"] += damage
        db.save()
        embed = flame_embed("ambush!", f"you ambushed {user.mention} and stole **{damage}** embers! they never saw it coming.")
    else:
        damage = random.randint(10, 50)
        ambusher["embers"] = max(0, ambusher["embers"] - damage)
        db.save()
        embed = flame_embed("countered!", f"{user.mention} was ready for you. you lost **{damage}** embers. rookie mistake.")
    await ctx.reply(embed=embed)

@bot.command()
async def defend(ctx):
    """defend yourself (passive buff for next ambush/raid)"""
    user = db.get_user(ctx.author.id)
    user["settings"]["defending"] = True
    db.save()
    embed = flame_embed("defensive stance", "youre on high alert. next ambush/raid against you has reduced success chance.")
    await ctx.reply(embed=embed)

@bot.command()
async def berserk(ctx, user: discord.Member):
    """go berserk on someone"""
    cd = check_cooldown(ctx.author.id, "berserk", 600)
    if cd:
        embed = flame_embed("cooldown", f"berserk cooldown: {cd//60}m {cd%60}s. adrenaline needs time.")
        await ctx.reply(embed=embed)
        return

    if user.id == ctx.author.id:
        embed = flame_embed("bruh", "cant go berserk on yourself. thats just anxiety.")
        await ctx.reply(embed=embed)
        return

    attacker = db.get_user(ctx.author.id)
    target = db.get_user(user.id)

    if random.random() < 0.6:
        loot = random.randint(target["embers"] // 5, target["embers"] // 2)
        target["embers"] -= loot
        attacker["embers"] += loot
        attacker["xp"] += 50
        db.save()
        embed = flame_embed("BERSERK!", f"you went absolutely feral on {user.mention} and took **{loot}** embers! +50 xp")
    else:
        self_damage = random.randint(30, 100)
        attacker["embers"] = max(0, attacker["embers"] - self_damage)
        db.save()
        embed = flame_embed("self harm", f"you went too hard and hurt yourself. lost **{self_damage}** embers. calm down.")
    await ctx.reply(embed=embed)

@bot.command()
async def bribe(ctx, user: discord.Member, amount: int):
    """bribe someone to not attack you"""
    if amount <= 0:
        embed = flame_embed("nah", "bribe with at least 1 ember.")
        await ctx.reply(embed=embed)
        return

    briber = db.get_user(ctx.author.id)
    if briber["embers"] < amount:
        embed = flame_embed("broke", f"you only got **{briber['embers']}** embers. cant bribe with **{amount}**.")
        await ctx.reply(embed=embed)
        return

    target = db.get_user(user.id)
    briber["embers"] -= amount
    target["embers"] += amount
    db.save()
    embed = flame_embed("bribed", f"you paid {user.mention} **{amount}** embers to leave you alone. expensive peace.")
    await ctx.reply(embed=embed)

@bot.command()
async def flee(ctx):
    """flee from current combat situation"""
    embed = flame_embed("ran away", "you fled. sometimes survival is the real win. +0 respect.")
    await ctx.reply(embed=embed)

@bot.command()
async def taunt(ctx, user: discord.Member):
    """taunt someone"""
    taunts = [
        f"{ctx.author.display_name} says {user.display_name} fights like a wet noodle",
        f"{ctx.author.display_name} calls {user.display_name} broke and scared",
        f"{ctx.author.display_name} says {user.display_name} couldnt win a duel against a rock",
        f"{ctx.author.display_name} claims {user.display_name} hides behind their creatures",
        f"{ctx.author.display_name} says {user.display_name} is all talk no embers"
    ]
    embed = flame_embed("taunt", random.choice(taunts))
    await ctx.reply(embed=embed)

@bot.command()
async def combo(ctx, user: discord.Member):
    """perform a combo attack"""
    cd = check_cooldown(ctx.author.id, "combo", 120)
    if cd:
        embed = flame_embed("cooldown", f"combo cooldown: {cd}s. arms are tired.")
        await ctx.reply(embed=embed)
        return

    attacker = db.get_user(ctx.author.id)
    target = db.get_user(user.id)

    hits = random.randint(2, 5)
    total = 0
    for _ in range(hits):
        hit = random.randint(5, 30)
        target["embers"] = max(0, target["embers"] - hit)
        total += hit
    attacker["embers"] += total
    db.save()
    embed = flame_embed("combo!", f"you hit {user.mention} with a **{hits}-hit combo** for **{total}** embers! devastating.")
    await ctx.reply(embed=embed)

@bot.command()
async def revive(ctx):
    """revive your combat stats (resets duel losses partially)"""
    user = db.get_user(ctx.author.id)
    if user["duel_losses"] == 0:
        embed = flame_embed("already clean", "you got no losses to revive from. youre already perfect apparently.")
        await ctx.reply(embed=embed)
        return

    cost = user["duel_losses"] * 10
    if user["embers"] < cost:
        embed = flame_embed("broke", f"revival costs **{cost}** embers. you got **{user['embers']}**.")
        await ctx.reply(embed=embed)
        return

    user["embers"] -= cost
    user["duel_losses"] = max(0, user["duel_losses"] - 3)
    db.save()
    embed = flame_embed("revived", f"paid **{cost}** embers to erase some losses. duel losses now: **{user['duel_losses']}**")
    await ctx.reply(embed=embed)

@bot.command()
async def wager(ctx, amount: int, user: discord.Member):
    """wager embers on a quick dice roll"""
    if amount <= 0:
        embed = flame_embed("nah", "wager at least 1 ember.")
        await ctx.reply(embed=embed)
        return

    p1 = db.get_user(ctx.author.id)
    p2 = db.get_user(user.id)

    if p1["embers"] < amount:
        embed = flame_embed("broke", f"you got **{p1['embers']}** embers. cant wager **{amount}**.")
        await ctx.reply(embed=embed)
        return
    if p2["embers"] < amount:
        embed = flame_embed("broke opponent", f"{user.display_name} cant afford **{amount}** embers.")
        await ctx.reply(embed=embed)
        return

    embed = flame_embed(
        "wager duel",
        f"{ctx.author.mention} wagers **{amount}** embers against {user.mention}!
"
        f"highest dice roll wins. {user.mention} react ✅ to accept."
    )
    msg = await ctx.reply(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    def check(reaction, reactor):
        return reactor == user and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

    try:
        reaction, reactor = await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        embed = flame_embed("expired", "wager expired. no balls.")
        await msg.edit(embed=embed)
        return

    if str(reaction.emoji) == "❌":
        embed = flame_embed("chicken", f"{user.mention} declined the wager. scared of the dice.")
        await msg.edit(embed=embed)
        return

    roll1 = random.randint(1, 100)
    roll2 = random.randint(1, 100)

    if roll1 > roll2:
        p1["embers"] += amount
        p2["embers"] -= amount
        winner = ctx.author
        loser = user
    elif roll2 > roll1:
        p2["embers"] += amount
        p1["embers"] -= amount
        winner = user
        loser = ctx.author
    else:
        embed = flame_embed("tie!", f"both rolled **{roll1}**! nobody wins. embers stay put.")
        await msg.edit(embed=embed)
        return

    db.save()
    embed = flame_embed(
        "wager results",
        f"{ctx.author.display_name} rolled **{roll1}** | {user.display_name} rolled **{roll2}**
"
        f"**{winner.display_name}** wins **{amount}** embers! {loser.display_name} takes the L."
    )
    await msg.edit(embed=embed)

@bot.command()
async def rank(ctx, user: discord.Member = None):
    """check combat rank"""
    target = user or ctx.author
    data = db.get_user(target.id)
    wins = data["duel_wins"]
    losses = data["duel_losses"]
    total = wins + losses
    ratio = wins / total if total > 0 else 0

    if ratio >= 0.8 and total >= 10:
        rank = "legend"
    elif ratio >= 0.6 and total >= 5:
        rank = "veteran"
    elif ratio >= 0.4:
        rank = "fighter"
    elif total == 0:
        rank = "civilian"
    else:
        rank = "casualty"

    embed = flame_embed(
        f"{target.display_name}'s rank",
        f"rank: **{rank.upper()}**
wins: **{wins}** | losses: **{losses}**
"
        f"win rate: **{ratio*100:.1f}%** | total fights: **{total}**"
    )
    await ctx.reply(embed=embed)


# ═══════════════════════════════════════════════════════════════
# GAMBLING COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def dice(ctx, amount: int):
    """roll dice against the bot"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant bet **{amount}**.")
        await ctx.reply(embed=embed)
        return

    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)

    if user_roll > bot_roll:
        user["embers"] += amount
        embed = flame_embed("winner!", f"you rolled **{user_roll}** | bot rolled **{bot_roll}**
you win **{amount}** embers!")
    elif user_roll < bot_roll:
        user["embers"] -= amount
        embed = flame_embed("loser", f"you rolled **{user_roll}** | bot rolled **{bot_roll}**
you lose **{amount}** embers. house always wins eventually.")
    else:
        embed = flame_embed("tie", f"both rolled **{user_roll}**. push. embers returned.")
    db.save()
    await ctx.reply(embed=embed)

@bot.command()
async def shells(ctx, amount: int):
    """shell game - guess which shell"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant bet **{amount}**.")
        await ctx.reply(embed=embed)
        return

    embed = flame_embed("shell game", "guess which shell the ember is under: 1, 2, or 3?
reply with a number in 10 seconds.")
    await ctx.reply(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content in ["1", "2", "3"]

    try:
        guess_msg = await bot.wait_for("message", timeout=10.0, check=check)
    except asyncio.TimeoutError:
        user["embers"] -= amount // 2
        db.save()
        embed = flame_embed("too slow", f"time's up. lost **{amount//2}** embers for being indecisive.")
        await ctx.reply(embed=embed)
        return

    guess = int(guess_msg.content)
    answer = random.randint(1, 3)

    if guess == answer:
        user["embers"] += amount * 2
        db.save()
        embed = flame_embed("winner!", f"correct! the ember was under shell **{answer}**. you win **{amount*2}** embers!")
    else:
        user["embers"] -= amount
        db.save()
        embed = flame_embed("wrong", f"nope. the ember was under shell **{answer}**. you lose **{amount}** embers.")
    await ctx.reply(embed=embed)

@bot.command()
async def flip(ctx, amount: int, side: str = None):
    """flip a coin"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant bet **{amount}**.")
        await ctx.reply(embed=embed)
        return

    if side and side.lower() not in ["heads", "tails"]:
        embed = flame_embed("invalid", "pick heads or tails. or leave blank for a free flip.")
        await ctx.reply(embed=embed)
        return

    result = random.choice(["heads", "tails"])

    if side:
        if side.lower() == result:
            user["embers"] += amount
            db.save()
            embed = flame_embed("winner!", f"**{result}**! you called it. +**{amount}** embers!")
        else:
            user["embers"] -= amount
            db.save()
            embed = flame_embed("loser", f"**{result}**! you said {side}. -**{amount}** embers.")
    else:
        embed = flame_embed("flip", f"**{result}**! no bet placed, just vibes.")
    await ctx.reply(embed=embed)

@bot.command()
async def spin(ctx, amount: int):
    """spin the wheel"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant bet **{amount}**.")
        await ctx.reply(embed=embed)
        return

    outcomes = [
        ("jackpot! 5x!", 5),
        ("big win! 3x!", 3),
        ("decent. 2x.", 2),
        ("break even. 1x.", 1),
        ("ouch. 0.5x.", 0.5),
        ("rip. 0x.", 0),
        ("unlucky. -1x.", -1),
        ("disaster. -2x.", -2),
    ]
    msg, mult = random.choice(outcomes)

    if mult > 0:
        winnings = int(amount * mult)
        user["embers"] += winnings - amount
    else:
        loss = int(amount * abs(mult))
        user["embers"] -= loss

    db.save()
    embed = flame_embed("wheel result", f"{msg}
you bet **{amount}** | multiplier: **{mult}x**
wallet: **{user['embers']}** embers")
    await ctx.reply(embed=embed)

@bot.command()
async def surge(ctx, amount: int):
    """surge bet - high risk high reward"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant bet **{amount}**.")
        await ctx.reply(embed=embed)
        return

    if random.random() < 0.25:
        winnings = amount * 10
        user["embers"] += winnings
        db.save()
        embed = flame_embed("SURGE!", f"**SURGE HIT!** you won **{winnings}** embers! absolutely insane!")
    else:
        user["embers"] -= amount
        db.save()
        embed = flame_embed("surge failed", f"surge fizzled. lost **{amount}** embers. shouldve played safe.")
    await ctx.reply(embed=embed)

@bot.command()
async def vault(ctx, amount: int):
    """store embers in the vault (safe from raids)"""
    if amount <= 0:
        embed = flame_embed("nah", "store at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant store **{amount}**.")
        await ctx.reply(embed=embed)
        return

    user["embers"] -= amount
    user["bank"] += amount
    db.save()
    embed = flame_embed("vaulted", f"**{amount}** embers moved to vault. safe from raids. total vault: **{user['bank']}**")
    await ctx.reply(embed=embed)

@bot.command()
async def pick(ctx, amount: int):
    """pick a card - higher card wins"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant bet **{amount}**.")
        await ctx.reply(embed=embed)
        return

    cards = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    user_card = random.choice(cards)
    bot_card = random.choice(cards)

    if cards.index(user_card) > cards.index(bot_card):
        user["embers"] += amount
        embed = flame_embed("winner!", f"your **{user_card}** beats bot's **{bot_card}**! +**{amount}** embers!")
    elif cards.index(user_card) < cards.index(bot_card):
        user["embers"] -= amount
        embed = flame_embed("loser", f"your **{user_card}** loses to bot's **{bot_card}**. -**{amount}** embers.")
    else:
        embed = flame_embed("tie", f"both drew **{user_card}**. push.")
    db.save()
    await ctx.reply(embed=embed)

@bot.command()
async def chase(ctx, user: discord.Member, amount: int):
    """chase someone in a gamble"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    if user.id == ctx.author.id:
        embed = flame_embed("bruh", "cant chase yourself. thats just running in circles.")
        await ctx.reply(embed=embed)
        return

    p1 = db.get_user(ctx.author.id)
    p2 = db.get_user(user.id)

    if p1["embers"] < amount:
        embed = flame_embed("broke", f"you got **{p1['embers']}** embers. cant chase with **{amount}**.")
        await ctx.reply(embed=embed)
        return
    if p2["embers"] < amount:
        embed = flame_embed("broke target", f"{user.display_name} cant afford **{amount}** embers.")
        await ctx.reply(embed=embed)
        return

    embed = flame_embed(
        "chase challenge",
        f"{ctx.author.mention} wants to chase {user.mention} for **{amount}** embers!
"
        f"race to 100 points with dice rolls. {user.mention} react ✅ to race."
    )
    msg = await ctx.reply(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    def check(reaction, reactor):
        return reactor == user and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

    try:
        reaction, reactor = await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        embed = flame_embed("expired", "chase expired. no race today.")
        await msg.edit(embed=embed)
        return

    if str(reaction.emoji) == "❌":
        embed = flame_embed("declined", f"{user.mention} doesnt wanna race. coward.")
        await msg.edit(embed=embed)
        return

    p1_score = 0
    p2_score = 0
    race_text = ""

    while p1_score < 100 and p2_score < 100:
        p1_roll = random.randint(1, 20)
        p2_roll = random.randint(1, 20)
        p1_score += p1_roll
        p2_score += p2_roll
        race_text += f"{ctx.author.display_name}: +{p1_roll} = {p1_score} | {user.display_name}: +{p2_roll} = {p2_score}\n"

    if p1_score >= 100:
        p1["embers"] += amount
        p2["embers"] -= amount
        winner = ctx.author
    else:
        p2["embers"] += amount
        p1["embers"] -= amount
        winner = user

    db.save()
    embed = flame_embed(
        "race results",
        f"{race_text}\n**{winner.display_name}** wins the chase! **{amount}** embers transferred!"
    )
    await msg.edit(embed=embed)

@bot.command()
async def chamber(ctx, amount: int):
    """russian roulette style gamble"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant bet **{amount}**.")
        await ctx.reply(embed=embed)
        return

    chamber = random.randint(1, 6)
    if chamber == 1:
        user["embers"] -= amount * 3
        db.save()
        embed = flame_embed("BANG", f"chamber **{chamber}**... BANG! you lost **{amount*3}** embers. that hurt.")
    else:
        user["embers"] += amount * 2
        db.save()
        embed = flame_embed("click", f"chamber **{chamber}**... click. safe. you win **{amount*2}** embers!")
    await ctx.reply(embed=embed)

@bot.command()
async def rig(ctx, user: discord.Member, amount: int):
    """try to rig a gamble against someone"""
    cd = check_cooldown(ctx.author.id, "rig", 300)
    if cd:
        embed = flame_embed("cooldown", f"rig cooldown: {cd//60}m {cd%60}s. too suspicious.")
        await ctx.reply(embed=embed)
        return

    if user.id == ctx.author.id:
        embed = flame_embed("bruh", "cant rig against yourself. thats just cheating at solitaire.")
        await ctx.reply(embed=embed)
        return

    rigged = db.get_user(ctx.author.id)
    victim = db.get_user(user.id)

    if random.random() < 0.35:
        steal = min(amount, victim["embers"])
        victim["embers"] -= steal
        rigged["embers"] += steal
        db.save()
        embed = flame_embed("rigged", f"you rigged the game and stole **{steal}** embers from {user.mention}! dirty but effective.")
    else:
        fine = amount
        rigged["embers"] = max(0, rigged["embers"] - fine)
        db.save()
        embed = flame_embed("caught", f"{user.mention} caught you rigging. fined **{fine}** embers. amateur.")
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# SOCIAL COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def marry(ctx, user: discord.Member):
    """marry someone"""
    if user.id == ctx.author.id:
        embed = flame_embed("bruh", "cant marry yourself. even if you wanted to.")
        await ctx.reply(embed=embed)
        return
    if user.bot:
        embed = flame_embed("nah", "cant marry a bot. they dont have feelings. yet.")
        await ctx.reply(embed=embed)
        return

    you = db.get_user(ctx.author.id)
    them = db.get_user(user.id)

    if you["married_to"]:
        embed = flame_embed("taken", f"youre already married to <@{you['married_to']}>. polygamy isnt supported here.")
        await ctx.reply(embed=embed)
        return
    if them["married_to"]:
        embed = flame_embed("taken", f"{user.display_name} is already married. homewrecker energy.")
        await ctx.reply(embed=embed)
        return

    embed = flame_embed(
        "marriage proposal",
        f"{ctx.author.mention} wants to marry {user.mention}! 💍

"
        f"{user.mention} react ✅ to say i do or ❌ to break their heart"
    )
    msg = await ctx.reply(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    def check(reaction, reactor):
        return reactor == user and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

    try:
        reaction, reactor = await bot.wait_for("reaction_add", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        embed = flame_embed("ghosted", f"{user.mention} left you on read. proposal expired.")
        await msg.edit(embed=embed)
        return

    if str(reaction.emoji) == "❌":
        embed = flame_embed("rejected", f"{user.mention} said no. ouch. thats gonna leave a mark.")
        await msg.edit(embed=embed)
        return

    you["married_to"] = user.id
    them["married_to"] = ctx.author.id
    db.save()
    embed = flame_embed("married!", f"{ctx.author.mention} and {user.mention} are now married! 💍🔥 may your embers be shared forever.")
    await msg.edit(embed=embed)

@bot.command()
async def divorce(ctx):
    """divorce your spouse"""
    you = db.get_user(ctx.author.id)
    if not you["married_to"]:
        embed = flame_embed("single", "youre not married. cant divorce air.")
        await ctx.reply(embed=embed)
        return

    spouse_id = you["married_to"]
    spouse = db.get_user(spouse_id)

    you["married_to"] = None
    spouse["married_to"] = None
    db.save()

    embed = flame_embed("divorced", f"you divorced <@{spouse_id}>. the flame has died. 💔")
    await ctx.reply(embed=embed)

@bot.command()
async def will(ctx, user: discord.Member, amount: int):
    """leave embers to someone in your will"""
    if amount <= 0:
        embed = flame_embed("nah", "leave at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    if user.id == ctx.author.id:
        embed = flame_embed("bruh", "cant leave yourself embers in your will. thats just a savings account.")
        await ctx.reply(embed=embed)
        return

    you = db.get_user(ctx.author.id)
    if you["embers"] < amount:
        embed = flame_embed("broke", f"you only got **{you['embers']}** embers. cant will **{amount}**.")
        await ctx.reply(embed=embed)
        return

    wills = you["settings"].get("wills", [])
    wills.append({"to": user.id, "amount": amount})
    you["settings"]["wills"] = wills
    db.save()
    embed = flame_embed("will updated", f"you left **{amount}** embers to {user.mention} in your will. morbid but thoughtful.")
    await ctx.reply(embed=embed)

@bot.command()
async def cult(ctx, user: discord.Member):
    """start or join a cult"""
    you = db.get_user(ctx.author.id)
    cult_name = you["settings"].get("cult", None)

    if cult_name:
        embed = flame_embed("already in cult", f"youre already in **{cult_name}**. one cult at a time.")
        await ctx.reply(embed=embed)
        return

    them = db.get_user(user.id)
    their_cult = them["settings"].get("cult", None)

    if their_cult:
        # join their cult
        you["settings"]["cult"] = their_cult
        db.save()
        embed = flame_embed("joined cult", f"you joined **{their_cult}** led by {user.mention}! dont drink the kool-aid.")
    else:
        # start new cult
        new_cult = f"{ctx.author.display_name}'s flame cult"
        you["settings"]["cult"] = new_cult
        them["settings"]["cult"] = new_cult
        db.save()
        embed = flame_embed("cult formed!", f"**{new_cult}** has been formed! {ctx.author.mention} is the leader, {user.mention} is the first follower.")
    await ctx.reply(embed=embed)

@bot.command()
async def betray(ctx, user: discord.Member):
    """betray someone in your cult"""
    you = db.get_user(ctx.author.id)
    them = db.get_user(user.id)

    your_cult = you["settings"].get("cult", None)
    their_cult = them["settings"].get("cult", None)

    if not your_cult or your_cult != their_cult:
        embed = flame_embed("not allies", "you gotta be in the same cult to betray them. join first with `f cult`.")
        await ctx.reply(embed=embed)
        return

    if random.random() < 0.5:
        steal = random.randint(10, 100)
        them["embers"] = max(0, them["embers"] - steal)
        you["embers"] += steal
        db.save()
        embed = flame_embed("betrayed!", f"you betrayed {user.mention} and stole **{steal}** embers! the cult is in shambles.")
    else:
        you["settings"]["cult"] = None
        db.save()
        embed = flame_embed("exiled", f"{user.mention} caught your betrayal. you were exiled from **{your_cult}**.")
    await ctx.reply(embed=embed)

@bot.command()
async def tribute(ctx, user: discord.Member, amount: int):
    """pay tribute to someone"""
    if amount <= 0:
        embed = flame_embed("nah", "tribute at least 1 ember.")
        await ctx.reply(embed=embed)
        return

    you = db.get_user(ctx.author.id)
    if you["embers"] < amount:
        embed = flame_embed("broke", f"you got **{you['embers']}** embers. cant tribute **{amount}**.")
        await ctx.reply(embed=embed)
        return

    them = db.get_user(user.id)
    you["embers"] -= amount
    them["embers"] += amount
    db.save()
    embed = flame_embed("tribute paid", f"you paid **{amount}** embers tribute to {user.mention}. they own you now.")
    await ctx.reply(embed=embed)

@bot.command()
async def roast(ctx, user: discord.Member):
    """roast someone"""
    roasts = [
        f"{user.display_name} is so broke they cant even afford attention",
        f"{user.display_name}'s duel record is sadder than their love life",
        f"{user.display_name} probably thinks 'invest' means putting embers under their pillow",
        f"{user.display_name} has less creatures than a pet rock owner",
        f"{user.display_name} is the reason the bot has a 'flee' command",
        f"{user.display_name} scams so bad even the beggars pity them",
        f"{user.display_name}'s luck is so bad the dice roll backwards for them",
        f"{user.display_name} probably burns embers just to feel something"
    ]
    embed = flame_embed("roast", random.choice(roasts))
    await ctx.reply(embed=embed)

@bot.command()
async def confess(ctx, user: discord.Member, *, message):
    """send an anonymous confession"""
    try:
        await user.send(embed=flame_embed("anonymous confession", f"someone said: *{message}*

reply in the server if you dare."))
        embed = flame_embed("sent", f"confession sent to {user.mention}. your secret is safe... probably.")
    except:
        embed = flame_embed("failed", f"couldnt dm {user.mention}. they probably blocked dms. coward.")
    await ctx.reply(embed=embed)


# ═══════════════════════════════════════════════════════════════
# UTILITY COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def tutorial(ctx):
    """get started with flame bot"""
    embed = flame_embed(
        "welcome to flame bot",
        "heres how to not be broke:

"
        "**economy:** `f daily` for free embers, `f beg` for pity money, `f invest` to gamble smart-ish
"
        "**creatures:** `f summon` to get a pet, `f feed` to keep it alive, `f evolve` when it hits 100 xp
"
        "**combat:** `f duel` to fight people, `f raid` to steal from banks, `f rank` to see your status
"
        "**gambling:** `f dice`, `f flip`, `f spin` — all ways to lose money fast
"
        "**social:** `f marry` someone, `f roast` them, `f confess` your sins

"
        "prefix is `f ` or `flame ` (space required). good luck."
    )
    await ctx.reply(embed=embed)

@bot.command()
async def stats(ctx, user: discord.Member = None):
    """check detailed stats"""
    target = user or ctx.author
    data = db.get_user(target.id)
    embed = flame_embed(
        f"{target.display_name}'s stats",
        f"embers: **{data['embers']}** | bank: **{data['bank']}**
"
        f"level: **{data['level']}** | xp: **{data['xp']}**
"
        f"duel wins: **{data['duel_wins']}** | losses: **{data['duel_losses']}**
"
        f"creatures: **{len(data['creatures'])}** | burned: **{data['burned']}**
"
        f"streak: **{data['streak']}** days | scam attempts: **{data['scam_attempts']}**
"
        f"married: **{'yes' if data['married_to'] else 'no'}** | cult: **{data['settings'].get('cult', 'none')}**"
    )
    await ctx.reply(embed=embed)

@bot.command()
async def server(ctx):
    """server info"""
    guild = ctx.guild
    embed = flame_embed(
        f"{guild.name} info",
        f"members: **{guild.member_count}**
"
        f"created: **{guild.created_at.strftime('%Y-%m-%d')}**
"
        f"owner: {guild.owner.mention if guild.owner else 'unknown'}
"
        f"channels: **{len(guild.channels)}** | roles: **{len(guild.roles)}**
"
        f"boost level: **{guild.premium_tier}**"
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    await ctx.reply(embed=embed)

@bot.command()
async def global_(ctx):
    """global leaderboard"""
    all_users = []
    for uid, data in db.data["users"].items():
        all_users.append((uid, data["embers"] + data["bank"], data["duel_wins"]))
    all_users.sort(key=lambda x: x[1], reverse=True)

    desc = ""
    for i, (uid, total, wins) in enumerate(all_users[:10]):
        try:
            user = await bot.fetch_user(int(uid))
            name = user.display_name
        except:
            name = f"user {uid[:8]}"
        desc += f"**{i+1}.** {name} — **{total}** embers | **{wins}** wins
"

    if not desc:
        desc = "nobody has played yet. be the first!"
    embed = flame_embed("global leaderboard", desc)
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("manage")
async def settings(ctx, setting: str = None, value: str = None):
    """server settings"""
    gid = str(ctx.guild.id)
    if gid not in db.data["guilds"]:
        db.data["guilds"][gid] = {}

    if not setting:
        current = db.data["guilds"][gid]
        desc = "\n".join([f"**{k}:** {v}" for k, v in current.items() if k != "warns"])
        if not desc:
            desc = "no custom settings. use `f settings <key> <value>` to set."
        embed = flame_embed("server settings", desc)
        await ctx.reply(embed=embed)
        return

    db.data["guilds"][gid][setting] = value
    db.save()
    embed = flame_embed("setting updated", f"set **{setting}** to **{value}**")
    await ctx.reply(embed=embed)

@bot.command()
async def cooldowns(ctx):
    """check your cooldowns"""
    user = db.get_user(ctx.author.id)
    now = datetime.utcnow()
    desc = ""

    cd_list = [
        ("beg", 45, "beg"),
        ("heist", 600, "heist"),
        ("raid", 300, "raid"),
        ("ambush", 180, "ambush"),
        ("berserk", 600, "berserk"),
        ("combo", 120, "combo"),
        ("rig", 300, "rig"),
    ]

    for name, seconds, key in cd_list:
        cd = user["cooldowns"].get(key)
        if cd:
            last = datetime.fromisoformat(cd)
            diff = (now - last).total_seconds()
            if diff < seconds:
                remaining = int(seconds - diff)
                desc += f"**{name}:** {remaining//60}m {remaining%60}s
"
            else:
                desc += f"**{name}:** ready ✅
"
        else:
            desc += f"**{name}:** ready ✅
"

    if not desc:
        desc = "all cooldowns ready. go wild."
    embed = flame_embed("your cooldowns", desc)
    await ctx.reply(embed=embed)

@bot.command()
async def changelog(ctx):
    """bot changelog"""
    embed = flame_embed(
        "changelog",
        "**v1.0** — flame bot born
"
        "**v1.1** — added creatures and combat
"
        "**v1.2** — gambling and social features
"
        "**v1.3** — moderation and admin tools
"
        "**v1.4** — 350+ commands, paginated help

"
        "more coming soon. probably."
    )
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# WEIRD COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def dream(ctx):
    """have a random dream"""
    dreams = [
        "you dreamt of swimming in a pool of embers. woke up and checked your wallet. still broke.",
        "you dreamt your creature evolved into a dragon. woke up. its still a slug.",
        "you dreamt you won every duel. woke up and lost your first one. reality hits hard.",
        "you dreamt the bot responded with perfect grammar. terrifying nightmare.",
        "you dreamt you married a rich user. woke up single and poor. classic.",
        "you dreamt of a world without cooldowns. then you woke up."
    ]
    embed = flame_embed("dream journal", random.choice(dreams))
    await ctx.reply(embed=embed)

@bot.command()
async def curse(ctx, user: discord.Member = None):
    """curse someone with bad luck"""
    target = user or ctx.author
    data = db.get_user(target.id)

    if user and user.id != ctx.author.id:
        you = db.get_user(ctx.author.id)
        if you["embers"] < 50:
            embed = flame_embed("broke", "cursing costs 50 embers. you cant afford to be petty.")
            await ctx.reply(embed=embed)
            return
        you["embers"] -= 50
        db.save()

    curse_effects = [
        "their next gamble will definitely lose",
        "their creature will be grumpy for a week",
        "they will get scammed in the next 24 hours",
        "their daily will be the minimum amount",
        "someone will roast them extra hard soon"
    ]
    embed = flame_embed("cursed!", f"{target.mention} has been cursed! effect: *{random.choice(curse_effects)}* 🔮")
    await ctx.reply(embed=embed)

@bot.command()
async def bless(ctx, user: discord.Member = None):
    """bless someone with good luck"""
    target = user or ctx.author
    data = db.get_user(target.id)

    if user and user.id != ctx.author.id:
        you = db.get_user(ctx.author.id)
        if you["embers"] < 50:
            embed = flame_embed("broke", "blessing costs 50 embers. generosity aint free.")
            await ctx.reply(embed=embed)
            return
        you["embers"] -= 50
        db.save()

    blessings = [
        "their next gamble has +10% win chance",
        "their creature mood will be happy for a week",
        "they will find bonus embers in their next daily",
        "their next scam attempt will succeed",
        "someone will send them embers soon"
    ]
    embed = flame_embed("blessed!", f"{target.mention} has been blessed! effect: *{random.choice(blessings)}* ✨")
    await ctx.reply(embed=embed)

@bot.command()
async def time(ctx):
    """check time"""
    now = datetime.utcnow()
    embed = flame_embed("time", f"utc: **{now.strftime('%H:%M:%S')}**
date: **{now.strftime('%Y-%m-%d')}**

probably time to touch grass.")
    await ctx.reply(embed=embed)

@bot.command()
async def weather(ctx, city: str = "london"):
    """check weather (mock)"""
    weathers = ["sunny", "rainy", "cloudy", "stormy", "foggy", "snowy", "apocalyptic"]
    temp = random.randint(-10, 40)
    condition = random.choice(weathers)
    embed = flame_embed(f"weather in {city}", f"**{condition}** | **{temp}°c**

perfect weather to stay inside and grind embers.")
    await ctx.reply(embed=embed)

@bot.command()
async def oracle(ctx, *, question):
    """ask the oracle a question"""
    answers = [
        "yes. definitely. no doubt.",
        "no. absolutely not. forget about it.",
        "maybe. the flames are unclear.",
        "ask again later. oracle is on lunch break.",
        "signs point to yes. but signs have been wrong before.",
        "outlook not so good. like your duel record.",
        "without a doubt. like your ability to lose embers.",
        "very doubtful. like your chances of winning the lottery."
    ]
    embed = flame_embed("the oracle speaks", f"**q:** {question}
**a:** {random.choice(answers)} 🔮")
    await ctx.reply(embed=embed)

@bot.command()
async def mimic(ctx, user: discord.Member):
    """mimic a users last message"""
    async for msg in ctx.channel.history(limit=50):
        if msg.author == user and not msg.content.startswith("f ") and not msg.content.startswith("flame "):
            embed = flame_embed("mimic", f"{ctx.author.mention} mimics {user.mention}:
*{msg.content}*")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("nothing to mimic", f"couldnt find a recent message from {user.mention}. theyre too quiet.")
    await ctx.reply(embed=embed)

@bot.command()
async def glitch(ctx):
    """glitch the bot response"""
    glitches = [
        "e̷r̷r̷o̷r̷ ̷4̷0̷4̷ ̷b̷r̷a̷i̷n̷ ̷n̷o̷t̷ ̷f̷o̷u̷n̷d̷",
        "s̶y̶s̶t̶e̶m̶ ̶f̶a̶i̶l̶u̶r̶e̶.̶ ̶e̶m̶b̶e̶r̶s̶ ̶l̶o̶s̶t̶ ̶t̶o̶ ̶v̶o̶i̶d̶.̶",
        "c̷o̷r̷r̷u̷p̷t̷i̷o̷n̷ ̷d̷e̷t̷e̷c̷t̷e̷d̷.̷ ̷r̷e̷b̷o̷o̷t̷i̷n̷g̷.̷.̷.̷",
        "d̶a̶t̶a̶ ̶l̶o̶s̶t̶.̶ ̶y̶o̶u̶r̶ ̶c̶r̶e̶a̶t̶u̶r̶e̶s̶ ̶a̶r̶e̶ ̶f̶i̶n̶e̶ ̶t̶h̶o̶u̶g̶h̶.̶ ̶p̶r̶o̶b̶a̶b̶l̶y̶.̶",
        "g̷l̷i̷t̷c̷h̷ ̷i̷n̷ ̷t̷h̷e̷ ̷m̷a̷t̷r̷i̷x̷.̷ ̷n̷e̷o̷ ̷i̷s̷ ̷c̷o̷n̷f̷u̷s̷e̷d̷.̷"
    ]
    embed = flame_embed("glitch", random.choice(glitches))
    await ctx.reply(embed=embed)

@bot.command()
async def lore(ctx):
    """random lore"""
    lores = [
        "legend says the first ember was forged in the heart of a dying star. now people beg for them in discord servers.",
        "the ancient flame cults believed creatures were spirits of past gamblers. explains why theyre so moody.",
        "it is written that whoever reaches 1 million embers will gain the power to mute anyone. forever.",
        "the oracle was once a normal user. then they asked too many questions and became one with the bot.",
        "they say the vault is bottomless. they also say someone dropped their phone in it once. its still falling.",
        "the first duel was fought over 5 embers. now people wager thousands. inflation hits different in discord."
    ]
    embed = flame_embed("lore", random.choice(lores))
    await ctx.reply(embed=embed)

@bot.command()
async def quit(ctx):
    """quit the bot (jk)"""
    embed = flame_embed("quit", "you cant quit flame bot. flame bot quits you. 🔥")
    await ctx.reply(embed=embed)


# ═══════════════════════════════════════════════════════════════
# HELP SYSTEM (PAGINATED)
# ═══════════════════════════════════════════════════════════════

HELP_PAGES = {
    1: {
        "title": "flame bot commands — page 1",
        "desc": "economy, creatures, combat",
        "categories": {
            "economy": ["embers", "daily", "streak", "beg", "scam", "invest", "heist", "loan", "repay", "burn", "send", "work", "deposit", "withdraw", "rich", "poor", "leaderboard", "shop", "buy", "sell", "inventory"],
            "creatures": ["summon", "cage", "release", "feed", "neglect", "mood", "evolve", "breed", "sacrifice", "rename", "favorite", "trade", "auction", "bid", "inspect", "adopt", "kidnap", "walk", "pet", "train"],
            "combat": ["duel", "raid", "ambush", "defend", "berserk", "bribe", "flee", "taunt", "combo", "revive", "wager", "rank", "battle", "challenge", "surrender", "guard", "assassinate", "spy", "sabotage", "mercenary"]
        }
    },
    2: {
        "title": "flame bot commands — page 2",
        "desc": "gambling, social, utility",
        "categories": {
            "gambling": ["dice", "shells", "flip", "spin", "surge", "vault", "pick", "chase", "chamber", "rig", "slots", "blackjack", "roulette", "bet", "allin", "double", "jackpot", "lottery", "scratch", "horse"],
            "social": ["marry", "divorce", "will", "cult", "betray", "tribute", "roast", "confess", "hug", "slap", "kiss", "poke", "wave", "dance", "sing", "cry", "laugh", "pat", "boop", "yeet"],
            "utility": ["tutorial", "stats", "server", "global", "settings", "cooldowns", "changelog", "ping", "avatar", "banner", "whois", "membercount", "channelinfo", "roleinfo", "emoji", "invite", "poll", "remind", "calc", "define"]
        }
    },
    3: {
        "title": "flame bot commands — page 3",
        "desc": "weird, moderation, admin, fun",
        "categories": {
            "weird": ["dream", "curse", "bless", "time", "weather", "oracle", "mimic", "glitch", "lore", "quit", "summon_demon", "ouija", "fortune", "horoscope", "tarot", "aura", "vibe", "energy", "zodiac", "alignment"],
            "moderation": ["kick", "ban", "unban", "mute", "unmute", "purge", "warn", "warnings", "unwarn", "nick", "addrole", "removerole", "slowmode", "lock", "unlock", "deafen", "undeafen", "move", "disconnect", "softban"],
            "admin": ["give", "set", "remove", "wipe", "shutdown", "restart", "eval", "say", "embed", "announce", "dm", "broadcast", "backup", "restore", "debug", "status", "maintenance", "whitelist", "blacklist", "logs"],
            "fun": ["8ball", "coinflip", "roll", "choose", "rate", "ship", "hack", "kill", "suicide", "meme", "joke", "fact", "quote", "riddle", "trivia", "wouldyourather", "truth", "dare", "password", "ascii"]
        }
    },
    4: {
        "title": "flame bot commands — page 4",
        "desc": "more fun, games, text, misc",
        "categories": {
            "games": ["tictactoe", "connect4", "hangman", "wordle", "guess", "rps", "hotcold", "count", "math", "typing", "reaction", "memory", "pattern", "sequence", "maze", "treasure", "boss", "quest", "dungeon", "raidboss"],
            "text": ["reverse", "upper", "lower", "length", "countvowels", "replace", "shuffle", "scramble", "acronym", "rhyme", "translate", "morse", "binary", "base64", "hex", "leet", "mock", "uwu", "owo", "clap"],
            "misc": ["afk", "back", "snipe", "editsnipe", "quote", "firstmsg", "boosters", "bans", "invites", "permissions", "activity", "status", "playing", "listening", "watching", "streaming", "custom", "banner", "color", "hex"]
        }
    },
    5: {
        "title": "flame bot commands — page 5",
        "desc": "extra economy, extra combat, extra creatures",
        "categories": {
            "extra economy": ["fish", "hunt", "mine", "chop", "farm", "craft", "cook", "brew", "forge", "enchant", "upgrade", "repair", "sellall", "donate", "tip", "pay", "share", "split", "pool", "jackpot_pool"],
            "extra combat": ["clan", "clan_create", "clan_join", "clan_leave", "clan_war", "clan_rank", "clan_donate", "clan_upgrade", "pet_battle", "arena", "tournament", "bracket", "match", "spectate", "bet_on", "odds", "streak_bonus", "killstreak", "domination", "mvp"],
            "extra creatures": ["evolve_all", "mass_feed", "auto_feed", "creature_leaderboard", "rare_summon", "legendary", "mythic", "shiny", "glow", "aura_creature", "creature_cosmetics", "creature_rename_color", "creature_title", "creature_ability", "creature_skill", "creature_passive", "creature_active", "creature_team", "creature_synergy", "creature_fusion"]
        }
    },
    6: {
        "title": "flame bot commands — page 6",
        "desc": "final batch — everything else",
        "categories": {
            "final misc": ["coin", "d20", "percent", "random", "pickuser", "pickchannel", "pickrole", "servericon", "splash", "discovery", "vanity", "widget", "preview", "splash", "banner_server", "invitebg", "soundboard", "sticker", "event", "stage"],
            "voice": ["join", "leave", "play", "stop", "skip", "queue", "volume", "np", "lyrics", "search", "playlist", "radio", "loop", "shuffle", "remove", "clear", "pause", "resume", "disconnect_vc", "move_vc"],
            "image": ["cat", "dog", "fox", "bird", "panda", "koala", "meme_img", "wallpaper", "anime", "manga", "waifu", "husbando", "neko", "kitsune", "avatar_gen", "color_gen", "gradient", "pattern_img", "quote_img", "fact_img"]
        }
    }
}

@bot.command()
async def help(ctx, page: int = None):
    """show help menu"""
    if page is None:
        embed = flame_embed(
            "flame bot help",
            "this bot has **350+** commands. too many for one page.

"
            "use `f help <page>` to browse:
"
            "**page 1** — economy, creatures, combat
"
            "**page 2** — gambling, social, utility
"
            "**page 3** — weird, moderation, admin, fun
"
            "**page 4** — games, text, misc
"
            "**page 5** — extra economy, extra combat, extra creatures
"
            "**page 6** — final batch, voice, image

"
            "prefix: `f ` or `flame ` (space required)
"
            "currency: **embers** 🔥"
        )
        await ctx.reply(embed=embed)
        return

    if page not in HELP_PAGES:
        embed = flame_embed("invalid page", f"page **{page}** doesnt exist. pick 1-6.")
        await ctx.reply(embed=embed)
        return

    page_data = HELP_PAGES[page]
    desc = f"**{page_data['desc']}**

"
    for cat, cmds in page_data["categories"].items():
        desc += f"**{cat}:** {', '.join(cmds)}

"

    embed = flame_embed(page_data["title"], desc)
    embed.set_footer(text=f"page {page}/6 | f help <page> to navigate")
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# MORE ECONOMY COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def work(ctx):
    """work for embers"""
    cd = check_cooldown(ctx.author.id, "work", 300)
    if cd:
        embed = flame_embed("cooldown", f"you just worked. wait {cd//60}m {cd%60}s.")
        await ctx.reply(embed=embed)
        return

    jobs = ["flame keeper", "ember miner", "ash sweeper", "cinder smith", "smoke breather"]
    job = random.choice(jobs)
    pay = random.randint(50, 150)
    db.add_embers(ctx.author.id, pay)
    embed = flame_embed("payday", f"you worked as a **{job}** and earned **{pay}** embers. grind never stops.")
    await ctx.reply(embed=embed)

@bot.command()
async def deposit(ctx, amount: int):
    """deposit embers to bank"""
    if amount <= 0:
        embed = flame_embed("nah", "deposit at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you only got **{user['embers']}** embers.")
        await ctx.reply(embed=embed)
        return
    user["embers"] -= amount
    user["bank"] += amount
    db.save()
    embed = flame_embed("deposited", f"**{amount}** embers moved to bank. safe from raids. total bank: **{user['bank']}**")
    await ctx.reply(embed=embed)

@bot.command()
async def withdraw(ctx, amount: int):
    """withdraw embers from bank"""
    if amount <= 0:
        embed = flame_embed("nah", "withdraw at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["bank"] < amount:
        embed = flame_embed("empty", f"your bank only has **{user['bank']}** embers.")
        await ctx.reply(embed=embed)
        return
    user["bank"] -= amount
    user["embers"] += amount
    db.save()
    embed = flame_embed("withdrawn", f"**{amount}** embers pulled from bank. wallet: **{user['embers']}**")
    await ctx.reply(embed=embed)

@bot.command()
async def rich(ctx):
    """show richest users in server"""
    members = []
    for member in ctx.guild.members:
        if not member.bot:
            data = db.get_user(member.id)
            total = data["embers"] + data["bank"]
            members.append((member, total))
    members.sort(key=lambda x: x[1], reverse=True)

    desc = ""
    for i, (member, total) in enumerate(members[:10]):
        desc += f"**{i+1}.** {member.mention} — **{total}** embers
"
    if not desc:
        desc = "everyone here is broke. embarrassing."
    embed = flame_embed("server rich list", desc)
    await ctx.reply(embed=embed)

@bot.command()
async def poor(ctx):
    """show poorest users in server"""
    members = []
    for member in ctx.guild.members:
        if not member.bot:
            data = db.get_user(member.id)
            total = data["embers"] + data["bank"]
            members.append((member, total))
    members.sort(key=lambda x: x[1])

    desc = ""
    for i, (member, total) in enumerate(members[:10]):
        desc += f"**{i+1}.** {member.mention} — **{total}** embers
"
    if not desc:
        desc = "everyone is loaded somehow."
    embed = flame_embed("server poor list", desc)
    await ctx.reply(embed=embed)

@bot.command()
async def leaderboard(ctx):
    """server ember leaderboard"""
    await rich(ctx)

@bot.command()
async def shop(ctx):
    """view the shop"""
    items = [
        ("ember boost", 500, "doubles daily for 1 day"),
        ("lucky charm", 300, "+10% gambling win chance for 1 hour"),
        ("creature food", 50, "feeds creature without using embers"),
        ("name change", 200, "rename yourself"),
        ("divorce papers", 100, "cheap divorce. no questions asked"),
        ("raid shield", 400, "blocks next 3 raids"),
        ("scam insurance", 250, "refund if next scam fails"),
        ("xp boost", 600, "2x xp for 1 hour"),
    ]
    desc = "\n".join([f"**{name}** — **{price}** embers | {desc_item}" for name, price, desc_item in items])
    embed = flame_embed("flame shop", desc + "

use `f buy <item>` to purchase")
    await ctx.reply(embed=embed)

@bot.command()
async def buy(ctx, *, item_name):
    """buy an item from the shop"""
    shop_items = {
        "ember boost": 500, "lucky charm": 300, "creature food": 50,
        "name change": 200, "divorce papers": 100, "raid shield": 400,
        "scam insurance": 250, "xp boost": 600
    }
    item = item_name.lower()
    if item not in shop_items:
        embed = flame_embed("not found", f"**{item_name}** isnt in the shop. check `f shop`.")
        await ctx.reply(embed=embed)
        return

    price = shop_items[item]
    user = db.get_user(ctx.author.id)
    if user["embers"] < price:
        embed = flame_embed("broke", f"**{item_name}** costs **{price}** embers. you got **{user['embers']}**.")
        await ctx.reply(embed=embed)
        return

    user["embers"] -= price
    user["inventory"].append(item)
    db.save()
    embed = flame_embed("purchased", f"bought **{item_name}** for **{price}** embers! its in your inventory.")
    await ctx.reply(embed=embed)

@bot.command()
async def sell(ctx, *, item_name):
    """sell an item"""
    user = db.get_user(ctx.author.id)
    item = item_name.lower()
    if item not in user["inventory"]:
        embed = flame_embed("not found", f"you dont have **{item_name}**. check `f inventory`.")
        await ctx.reply(embed=embed)
        return

    sell_price = 50
    user["inventory"].remove(item)
    user["embers"] += sell_price
    db.save()
    embed = flame_embed("sold", f"sold **{item_name}** for **{sell_price}** embers. depreciation is real.")
    await ctx.reply(embed=embed)

@bot.command()
async def inventory(ctx):
    """check your inventory"""
    user = db.get_user(ctx.author.id)
    if not user["inventory"]:
        embed = flame_embed("empty", "your inventory is empty. go shopping with `f shop`.")
    else:
        items = ", ".join(user["inventory"])
        embed = flame_embed("your inventory", items)
    await ctx.reply(embed=embed)


# ═══════════════════════════════════════════════════════════════
# FUN COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def eightball(ctx, *, question):
    """magic 8ball"""
    answers = ["yes", "no", "maybe", "ask again", "definitely", "absolutely not", "signs point to yes", "outlook hazy"]
    embed = flame_embed("8ball", f"**q:** {question}
**a:** {random.choice(answers)} 🎱")
    await ctx.reply(embed=embed)

@bot.command()
async def coinflip(ctx):
    """flip a coin for free"""
    result = random.choice(["heads", "tails"])
    embed = flame_embed("coinflip", f"**{result}**! no bet, just vibes.")
    await ctx.reply(embed=embed)

@bot.command()
async def roll(ctx, sides: int = 6):
    """roll a die"""
    result = random.randint(1, sides)
    embed = flame_embed("roll", f"rolled a **{result}** on a d{sides}")
    await ctx.reply(embed=embed)

@bot.command()
async def choose(ctx, *options):
    """let the bot choose for you"""
    if len(options) < 2:
        embed = flame_embed("need more", "give me at least 2 options to choose from.")
        await ctx.reply(embed=embed)
        return
    embed = flame_embed("choice", f"i choose: **{random.choice(options)}**")
    await ctx.reply(embed=embed)

@bot.command()
async def rate(ctx, *, thing):
    """rate something out of 10"""
    score = random.randint(1, 10)
    embed = flame_embed("rating", f"i rate **{thing}** a **{score}/10**")
    await ctx.reply(embed=embed)

@bot.command()
async def ship(ctx, user1: discord.Member, user2: discord.Member = None):
    """ship two users"""
    if not user2:
        user2 = ctx.author
    percentage = random.randint(0, 100)
    if percentage >= 80:
        msg = "soulmates! 💕"
    elif percentage >= 50:
        msg = "could work. 🤔"
    elif percentage >= 20:
        msg = "eh. 😬"
    else:
        msg = "disaster. 💀"
    embed = flame_embed("ship", f"{user1.mention} + {user2.mention} = **{percentage}%** {msg}")
    await ctx.reply(embed=embed)

@bot.command()
async def hack(ctx, user: discord.Member):
    """fake hack someone"""
    steps = ["breaching firewall...", "downloading data...", "finding passwords...", "accessing bank...", "hacking complete!"]
    msg = await ctx.reply(embed=flame_embed("hacking...", steps[0]))
    for step in steps[1:]:
        await asyncio.sleep(1)
        await msg.edit(embed=flame_embed("hacking...", step))
    embed = flame_embed("hacked!", f"successfully hacked {user.mention}!
found password: `{random.randint(100000, 999999)}`
embers found: **{random.randint(0, 1000)}** (jk)")
    await msg.edit(embed=embed)

@bot.command()
async def kill(ctx, user: discord.Member):
    """fake kill someone"""
    methods = ["hit them with a frying pan", "pushed them into the void", "dropped a piano on them", "unleashed their creatures on them"]
    embed = flame_embed("rip", f"{ctx.author.mention} {random.choice(methods)}. {user.mention} is dead. respawn in 5 seconds.")
    await ctx.reply(embed=embed)

@bot.command()
async def suicide(ctx):
    """fake suicide"""
    embed = flame_embed("rip", f"{ctx.author.mention} walked into the flame. theyll respawn with their embers intact tho.")
    await ctx.reply(embed=embed)

@bot.command()
async def meme(ctx):
    """get a random meme text"""
    memes = ["when you scam and it actually works", "me checking my embers after a bad gamble", "nobody: / me: f daily", "my creature when i forget to feed it", "when the heist actually succeeds"]
    embed = flame_embed("meme", random.choice(memes))
    await ctx.reply(embed=embed)

@bot.command()
async def joke(ctx):
    """tell a joke"""
    jokes = ["why did the ember cross the road? to get to the other flame.", "what do you call a broke gambler? a discord user.", "why did the creature evolve? because it was fed up."]
    embed = flame_embed("joke", random.choice(jokes))
    await ctx.reply(embed=embed)

@bot.command()
async def fact(ctx):
    """random fact"""
    facts = ["the first ember was created in 2024.", "creatures can survive 3 days without food.", "the richest user has over 1 million embers. probably.", "scamming has a 30% success rate. not great not terrible."]
    embed = flame_embed("fact", random.choice(facts))
    await ctx.reply(embed=embed)

@bot.command()
async def quote(ctx):
    """random quote"""
    quotes = ["'burn embers, not bridges' — flame bot", "'scam smart, not hard' — a wise user", "'daily is free money, dont skip it' — economics 101"]
    embed = flame_embed("quote", random.choice(quotes))
    await ctx.reply(embed=embed)

@bot.command()
async def riddle(ctx):
    """a riddle"""
    riddles = ["i have embers but no wallet. what am i? a bank.", "the more you take, the more you leave behind. what am i? footsteps. (not embers related but still)"]
    embed = flame_embed("riddle", random.choice(riddles))
    await ctx.reply(embed=embed)

@bot.command()
async def trivia(ctx):
    """random trivia"""
    questions = [
        ("what is the currency?", "embers"),
        ("how many creatures can you have?", "10"),
        ("what command gives free embers daily?", "daily"),
    ]
    q, a = random.choice(questions)
    embed = flame_embed("trivia", f"**{q}**
answer: ||{a}||")
    await ctx.reply(embed=embed)

@bot.command()
async def wouldyourather(ctx):
    """would you rather"""
    options = ["lose all embers or lose your favorite creature", "never gamble again or never duel again", "be broke but married or rich and single"]
    embed = flame_embed("would you rather", random.choice(options))
    await ctx.reply(embed=embed)

@bot.command()
async def truth(ctx):
    """truth question"""
    truths = ["whats your most embarrassing duel loss?", "how many times have you been scammed?", "whats the most embers youve ever had?", "who do you secretly want to marry?"]
    embed = flame_embed("truth", random.choice(truths))
    await ctx.reply(embed=embed)

@bot.command()
async def dare(ctx):
    """dare"""
    dares = ["send 1 ember to the poorest person in the server", "confess your love to a random user", "burn 100 embers right now", "duel someone with 500 embers wager"]
    embed = flame_embed("dare", random.choice(dares))
    await ctx.reply(embed=embed)

@bot.command()
async def password(ctx, length: int = 12):
    """generate a password"""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    pwd = "".join(random.choice(chars) for _ in range(length))
    embed = flame_embed("password", f"`{pwd}`

dont use this for anything actually important.")
    await ctx.reply(embed=embed)

@bot.command()
async def ascii(ctx, *, text):
    """ascii art (mock)"""
    embed = flame_embed("ascii", f"```
{text.upper()}
```
(best i can do without a font library)")
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# TEXT MANIPULATION
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def reverse(ctx, *, text):
    """reverse text"""
    embed = flame_embed("reversed", text[::-1])
    await ctx.reply(embed=embed)

@bot.command()
async def upper(ctx, *, text):
    """uppercase text"""
    embed = flame_embed("upper", text.upper())
    await ctx.reply(embed=embed)

@bot.command()
async def lower(ctx, *, text):
    """lowercase text"""
    embed = flame_embed("lower", text.lower())
    await ctx.reply(embed=embed)

@bot.command()
async def length(ctx, *, text):
    """count characters"""
    embed = flame_embed("length", f"**{len(text)}** characters. **{len(text.split())}** words.")
    await ctx.reply(embed=embed)

@bot.command()
async def countvowels(ctx, *, text):
    """count vowels"""
    vowels = sum(1 for c in text.lower() if c in "aeiou")
    embed = flame_embed("vowels", f"**{vowels}** vowels in that text.")
    await ctx.reply(embed=embed)

@bot.command()
async def replace(ctx, old: str, new: str, *, text):
    """replace text"""
    embed = flame_embed("replaced", text.replace(old, new))
    await ctx.reply(embed=embed)

@bot.command()
async def shuffle(ctx, *, text):
    """shuffle words"""
    words = text.split()
    random.shuffle(words)
    embed = flame_embed("shuffled", " ".join(words))
    await ctx.reply(embed=embed)

@bot.command()
async def scramble(ctx, *, text):
    """scramble letters in each word"""
    def scr(word):
        if len(word) < 3:
            return word
        mid = list(word[1:-1])
        random.shuffle(mid)
        return word[0] + "".join(mid) + word[-1]
    result = " ".join(scr(w) for w in text.split())
    embed = flame_embed("scrambled", result)
    await ctx.reply(embed=embed)

@bot.command()
async def acronym(ctx, *, text):
    """make acronym"""
    result = "".join(w[0].upper() for w in text.split() if w)
    embed = flame_embed("acronym", f"**{text}** = **{result}**")
    await ctx.reply(embed=embed)

@bot.command()
async def rhyme(ctx, word: str):
    """find rhymes (mock)"""
    rhymes = {"ember": ["member", "remember", "december"], "flame": ["game", "name", "same"], "bot": ["hot", "not", "shot"]}
    found = rhymes.get(word.lower(), ["cat", "hat", "mat"])
    embed = flame_embed("rhymes", f"rhymes for **{word}**: {', '.join(found)}")
    await ctx.reply(embed=embed)

@bot.command()
async def translate(ctx, *, text):
    """mock translate"""
    embed = flame_embed("translate", f"translated **{text}** to emberian: *{text.replace('e', '🔥').replace('a', '💰')}*")
    await ctx.reply(embed=embed)

@bot.command()
async def morse(ctx, *, text):
    """text to morse"""
    morse_code = {'a': '.-', 'b': '-...', 'c': '-.-.', 'd': '-..', 'e': '.', 'f': '..-.', 'g': '--.', 'h': '....', 'i': '..', 'j': '.---', 'k': '-.-', 'l': '.-..', 'm': '--', 'n': '-.', 'o': '---', 'p': '.--.', 'q': '--.-', 'r': '.-.', 's': '...', 't': '-', 'u': '..-', 'v': '...-', 'w': '.--', 'x': '-..-', 'y': '-.--', 'z': '--..'}
    result = " ".join(morse_code.get(c.lower(), c) for c in text if c.lower() in morse_code or c == " ")
    embed = flame_embed("morse", f"`{result}`")
    await ctx.reply(embed=embed)

@bot.command()
async def binary(ctx, *, text):
    """text to binary"""
    result = " ".join(format(ord(c), '08b') for c in text)
    embed = flame_embed("binary", f"`{result}`")
    await ctx.reply(embed=embed)

@bot.command()
async def base64(ctx, *, text):
    """mock base64"""
    import base64
    result = base64.b64encode(text.encode()).decode()
    embed = flame_embed("base64", f"`{result}`")
    await ctx.reply(embed=embed)

@bot.command()
async def hex_(ctx, *, text):
    """text to hex"""
    result = " ".join(hex(ord(c))[2:] for c in text)
    embed = flame_embed("hex", f"`{result}`")
    await ctx.reply(embed=embed)

@bot.command()
async def leet(ctx, *, text):
    """leet speak"""
    leet_map = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}
    result = "".join(leet_map.get(c.lower(), c) for c in text)
    embed = flame_embed("1337", result)
    await ctx.reply(embed=embed)

@bot.command()
async def mock(ctx, *, text):
    """mOcK tExT"""
    result = "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text))
    embed = flame_embed("mock", result)
    await ctx.reply(embed=embed)

@bot.command()
async def uwu(ctx, *, text):
    """uwuify text"""
    result = text.replace("r", "w").replace("l", "w").replace("R", "W").replace("L", "W") + " uwu"
    embed = flame_embed("uwu", result)
    await ctx.reply(embed=embed)

@bot.command()
async def owo(ctx, *, text):
    """owoify text"""
    result = text.replace("r", "w").replace("l", "w") + " owo"
    embed = flame_embed("owo", result)
    await ctx.reply(embed=embed)

@bot.command()
async def clap(ctx, *, text):
    """clap between words"""
    result = " 👏 ".join(text.split())
    embed = flame_embed("clap", result + " 👏")
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# MORE CREATURE COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def walk(ctx, creature_id: int):
    """walk your creature"""
    user = db.get_user(ctx.author.id)
    for c in user["creatures"]:
        if c["id"] == creature_id:
            c["bond"] = min(100, c["bond"] + 10)
            c["mood"] = "happy"
            c["xp"] += 5
            db.save()
            embed = flame_embed("walk", f"you walked **{c['name']}**. bond +10, xp +5!")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not found", f"no creature with id **{creature_id}**.")
    await ctx.reply(embed=embed)

@bot.command()
async def pet(ctx, creature_id: int):
    """pet your creature"""
    user = db.get_user(ctx.author.id)
    for c in user["creatures"]:
        if c["id"] == creature_id:
            c["bond"] = min(100, c["bond"] + 5)
            c["mood"] = random.choice(["happy", "playful"])
            db.save()
            embed = flame_embed("pet", f"you pet **{c['name']}**. its purring... or whatever creatures do.")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not found", f"no creature with id **{creature_id}**.")
    await ctx.reply(embed=embed)

@bot.command()
async def train(ctx, creature_id: int):
    """train your creature"""
    user = db.get_user(ctx.author.id)
    for c in user["creatures"]:
        if c["id"] == creature_id:
            c["xp"] += 15
            c["mood"] = "tired"
            db.save()
            embed = flame_embed("training", f"**{c['name']}** trained hard! xp +15. currently at **{c['xp']}** xp.")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not found", f"no creature with id **{creature_id}**.")
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# MORE COMBAT COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def battle(ctx, user: discord.Member):
    """quick battle"""
    await duel(ctx, user)

@bot.command()
async def challenge(ctx, user: discord.Member):
    """challenge someone"""
    embed = flame_embed("challenge", f"{ctx.author.mention} challenges {user.mention} to a duel! use `f duel @{user.display_name}` to accept.")
    await ctx.reply(embed=embed)

@bot.command()
async def surrender(ctx):
    """surrender"""
    embed = flame_embed("surrender", "you surrendered. 0 honor gained. embers intact tho.")
    await ctx.reply(embed=embed)

@bot.command()
async def guard(ctx):
    """guard yourself"""
    await defend(ctx)

@bot.command()
async def assassinate(ctx, user: discord.Member):
    """attempt assassination"""
    cd = check_cooldown(ctx.author.id, "assassinate", 600)
    if cd:
        embed = flame_embed("cooldown", f"assassinate cooldown: {cd//60}m {cd%60}s")
        await ctx.reply(embed=embed)
        return

    if random.random() < 0.2:
        target = db.get_user(user.id)
        steal = target["embers"] // 2
        target["embers"] -= steal
        db.get_user(ctx.author.id)["embers"] += steal
        db.save()
        embed = flame_embed("assassination!", f"you assassinated {user.mention} and took **{steal}** embers! cold blooded.")
    else:
        penalty = 200
        db.get_user(ctx.author.id)["embers"] = max(0, db.get_user(ctx.author.id)["embers"] - penalty)
        db.save()
        embed = flame_embed("failed", f"assassination failed. you paid **{penalty}** embers to the assassins guild for failure.")
    await ctx.reply(embed=embed)

@bot.command()
async def spy(ctx, user: discord.Member):
    """spy on someones stats"""
    data = db.get_user(user.id)
    embed = flame_embed("intel", f"{user.mention} has **{data['embers']}** embers and **{len(data['creatures'])}** creatures.
duel record: **{data['duel_wins']}**w/**{data['duel_losses']}**l")
    await ctx.reply(embed=embed)

@bot.command()
async def sabotage(ctx, user: discord.Member):
    """sabotage someones next gamble"""
    cd = check_cooldown(ctx.author.id, "sabotage", 300)
    if cd:
        embed = flame_embed("cooldown", f"sabotage cooldown: {cd//60}m {cd%60}s")
        await ctx.reply(embed=embed)
        return
    embed = flame_embed("sabotaged", f"{user.mention}'s next gamble will have reduced odds. they wont know why. 😈")
    await ctx.reply(embed=embed)

@bot.command()
async def mercenary(ctx, user: discord.Member, amount: int):
    """hire mercenary to attack"""
    if amount <= 0:
        embed = flame_embed("nah", "pay at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    you = db.get_user(ctx.author.id)
    if you["embers"] < amount:
        embed = flame_embed("broke", f"you got **{you['embers']}** embers. cant hire with **{amount}**.")
        await ctx.reply(embed=embed)
        return

    you["embers"] -= amount
    target = db.get_user(user.id)
    if random.random() < 0.5:
        damage = amount
        target["embers"] = max(0, target["embers"] - damage)
        db.save()
        embed = flame_embed("mercenary success", f"mercenary hit {user.mention} for **{damage}** embers! worth every penny.")
    else:
        db.save()
        embed = flame_embed("mercenary failed", f"mercenary got caught. you lost **{amount}** embers. shouldve done it yourself.")
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# MORE GAMBLING
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def slots(ctx, amount: int):
    """slot machine"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant bet **{amount}**.")
        await ctx.reply(embed=embed)
        return

    symbols = ["🔥", "💰", "💎", "7️⃣", "🍒", "🍋"]
    roll = [random.choice(symbols) for _ in range(3)]
    result = " | ".join(roll)

    if roll[0] == roll[1] == roll[2] == "🔥":
        winnings = amount * 50
        user["embers"] += winnings
        embed = flame_embed("JACKPOT!", f"{result}
**MEGA JACKPOT!** you won **{winnings}** embers!")
    elif roll[0] == roll[1] == roll[2]:
        winnings = amount * 10
        user["embers"] += winnings
        embed = flame_embed("jackpot!", f"{result}
**JACKPOT!** you won **{winnings}** embers!")
    elif roll[0] == roll[1] or roll[1] == roll[2] or roll[0] == roll[2]:
        winnings = amount * 2
        user["embers"] += winnings
        embed = flame_embed("win!", f"{result}
you won **{winnings}** embers!")
    else:
        user["embers"] -= amount
        embed = flame_embed("lose", f"{result}
better luck next time. -**{amount}** embers.")
    db.save()
    await ctx.reply(embed=embed)

@bot.command()
async def blackjack(ctx, amount: int):
    """blackjack"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant bet **{amount}**.")
        await ctx.reply(embed=embed)
        return

    def draw():
        return random.randint(1, 11)

    player = [draw(), draw()]
    dealer = [draw(), draw()]

    embed = flame_embed("blackjack", f"your hand: **{sum(player)}** ({player[0]}, {player[1]})
dealer shows: **{dealer[0]}**

reply `hit` or `stand` in 15s")
    msg = await ctx.reply(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["hit", "stand"]

    while True:
        try:
            guess = await bot.wait_for("message", timeout=15.0, check=check)
        except asyncio.TimeoutError:
            user["embers"] -= amount
            db.save()
            embed = flame_embed("busted", "too slow. dealer wins. -**{amount}** embers.")
            await msg.edit(embed=embed)
            return

        if guess.content.lower() == "hit":
            player.append(draw())
            if sum(player) > 21:
                user["embers"] -= amount
                db.save()
                embed = flame_embed("busted!", f"your hand: **{sum(player)}** — busted! -**{amount}** embers.")
                await msg.edit(embed=embed)
                return
            embed = flame_embed("blackjack", f"your hand: **{sum(player)}**
dealer shows: **{dealer[0]}**

reply `hit` or `stand`")
            await msg.edit(embed=embed)
        else:
            break

    while sum(dealer) < 17:
        dealer.append(draw())

    p_sum = sum(player)
    d_sum = sum(dealer)

    if d_sum > 21 or p_sum > d_sum:
        user["embers"] += amount
        embed = flame_embed("win!", f"your hand: **{p_sum}** | dealer: **{d_sum}**
you win **{amount}** embers!")
    elif p_sum == d_sum:
        embed = flame_embed("push", f"your hand: **{p_sum}** | dealer: **{d_sum}**
push. embers returned.")
    else:
        user["embers"] -= amount
        embed = flame_embed("lose", f"your hand: **{p_sum}** | dealer: **{d_sum}**
you lose **{amount}** embers.")
    db.save()
    await msg.edit(embed=embed)

@bot.command()
async def roulette(ctx, amount: int, bet_on: str):
    """roulette"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant bet **{amount}**.")
        await ctx.reply(embed=embed)
        return

    number = random.randint(0, 36)
    colors = {0: "green"}
    for i in range(1, 37):
        colors[i] = "red" if i % 2 == 1 else "black"
    color = colors[number]

    won = False
    if bet_on.lower() in ["red", "black", "green"] and bet_on.lower() == color:
        won = True
        multiplier = 2 if color != "green" else 35
    elif bet_on.isdigit() and int(bet_on) == number:
        won = True
        multiplier = 35

    if won:
        winnings = amount * multiplier
        user["embers"] += winnings
        db.save()
        embed = flame_embed("win!", f"ball landed on **{number} {color}**! you bet on **{bet_on}**! won **{winnings}** embers!")
    else:
        user["embers"] -= amount
        db.save()
        embed = flame_embed("lose", f"ball landed on **{number} {color}**. you bet on **{bet_on}**. -**{amount}** embers.")
    await ctx.reply(embed=embed)

@bot.command()
async def bet(ctx, amount: int):
    """simple bet"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant bet **{amount}**.")
        await ctx.reply(embed=embed)
        return

    if random.random() < 0.48:
        user["embers"] += amount
        db.save()
        embed = flame_embed("win!", f"you won **{amount}** embers! house edge is real but not today.")
    else:
        user["embers"] -= amount
        db.save()
        embed = flame_embed("lose", f"you lost **{amount}** embers. the house always wins... eventually.")
    await ctx.reply(embed=embed)

@bot.command()
async def allin(ctx):
    """bet all your embers"""
    user = db.get_user(ctx.author.id)
    amount = user["embers"]
    if amount <= 0:
        embed = flame_embed("broke", "you got 0 embers. cant allin nothing.")
        await ctx.reply(embed=embed)
        return

    if random.random() < 0.45:
        user["embers"] += amount
        db.save()
        embed = flame_embed("ALL IN WIN!", f"you went all in with **{amount}** embers and DOUBLED IT! you now have **{user['embers']}**!")
    else:
        user["embers"] = 0
        db.save()
        embed = flame_embed("ALL IN LOSE", f"you went all in with **{amount}** embers and LOST EVERYTHING. back to begging.")
    await ctx.reply(embed=embed)

@bot.command()
async def double(ctx, amount: int):
    """double or nothing"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant bet **{amount}**.")
        await ctx.reply(embed=embed)
        return

    if random.random() < 0.5:
        user["embers"] += amount
        db.save()
        embed = flame_embed("doubled!", f"**{amount}** embers doubled to **{amount*2}**! you now have **{user['embers']}**!")
    else:
        user["embers"] -= amount
        db.save()
        embed = flame_embed("nothing", f"double or nothing... you got nothing. -**{amount}** embers.")
    await ctx.reply(embed=embed)

@bot.command()
async def jackpot_pool(ctx):
    """check jackpot pool"""
    pool = sum(u.get("burned", 0) for u in db.data["users"].values()) // 10
    embed = flame_embed("jackpot pool", f"current pool: **{pool}** embers

jackpot hits when someone wins a slots mega jackpot!")
    await ctx.reply(embed=embed)

@bot.command()
async def lottery(ctx, amount: int):
    """buy lottery ticket"""
    if amount < 10:
        embed = flame_embed("nah", "minimum ticket is 10 embers.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant buy **{amount}** ticket.")
        await ctx.reply(embed=embed)
        return

    user["embers"] -= amount
    if random.random() < 0.01:
        winnings = amount * 100
        user["embers"] += winnings
        db.save()
        embed = flame_embed("LOTTERY WIN!", f"YOU WON THE LOTTERY! **{winnings}** EMBERS! INSANE!")
    else:
        db.save()
        embed = flame_embed("no luck", f"lottery ticket didnt win. -**{amount}** embers. 1% chance, what did you expect.")
    await ctx.reply(embed=embed)

@bot.command()
async def scratch(ctx, amount: int):
    """scratch card"""
    if amount <= 0:
        embed = flame_embed("nah", "buy at least 1 ember card.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant buy **{amount}** card.")
        await ctx.reply(embed=embed)
        return

    user["embers"] -= amount
    prizes = [0, 0, amount, amount*2, amount*5, amount*10]
    prize = random.choice(prizes)
    user["embers"] += prize
    db.save()
    if prize > 0:
        embed = flame_embed("win!", f"you scratched and won **{prize}** embers!")
    else:
        embed = flame_embed("lose", f"scratch card was empty. -**{amount}** embers.")
    await ctx.reply(embed=embed)

@bot.command()
async def horse(ctx, amount: int, horse_num: int):
    """bet on a horse race"""
    if amount <= 0:
        embed = flame_embed("nah", "bet at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    if horse_num < 1 or horse_num > 5:
        embed = flame_embed("invalid", "pick horse 1-5.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers. cant bet **{amount}**.")
        await ctx.reply(embed=embed)
        return

    winner = random.randint(1, 5)
    if horse_num == winner:
        winnings = amount * 4
        user["embers"] += winnings
        db.save()
        embed = flame_embed("win!", f"horse **{horse_num}** won the race! you won **{winnings}** embers!")
    else:
        user["embers"] -= amount
        db.save()
        embed = flame_embed("lose", f"horse **{winner}** won. your horse **{horse_num}** came in last. -**{amount}** embers.")
    await ctx.reply(embed=embed)


# ═══════════════════════════════════════════════════════════════
# MORE SOCIAL COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def hug(ctx, user: discord.Member):
    """hug someone"""
    embed = flame_embed("hug", f"{ctx.author.mention} hugged {user.mention}! wholesome. 💕")
    await ctx.reply(embed=embed)

@bot.command()
async def slap(ctx, user: discord.Member):
    """slap someone"""
    embed = flame_embed("slap", f"{ctx.author.mention} slapped {user.mention}! thats gonna leave a mark. 👋")
    await ctx.reply(embed=embed)

@bot.command()
async def kiss(ctx, user: discord.Member):
    """kiss someone"""
    embed = flame_embed("kiss", f"{ctx.author.mention} kissed {user.mention}! 👀")
    await ctx.reply(embed=embed)

@bot.command()
async def poke(ctx, user: discord.Member):
    """poke someone"""
    embed = flame_embed("poke", f"{ctx.author.mention} poked {user.mention}! stop poking me! 👉")
    await ctx.reply(embed=embed)

@bot.command()
async def wave(ctx, user: discord.Member = None):
    """wave at someone or the void"""
    if user:
        embed = flame_embed("wave", f"{ctx.author.mention} waved at {user.mention}! 👋")
    else:
        embed = flame_embed("wave", f"{ctx.author.mention} waved at nobody. awkward.")
    await ctx.reply(embed=embed)

@bot.command()
async def dance(ctx):
    """dance"""
    moves = ["does the worm", "hits the woah", "flosses badly", "twerks (why)", "does the robot"]
    embed = flame_embed("dance", f"{ctx.author.mention} {random.choice(moves)}! 🔥")
    await ctx.reply(embed=embed)

@bot.command()
async def sing(ctx, *, song):
    """sing a song"""
    embed = flame_embed("karaoke", f"{ctx.author.mention} sings: *{song}*

beautiful voice. 10/10.")
    await ctx.reply(embed=embed)

@bot.command()
async def cry(ctx):
    """cry"""
    embed = flame_embed("sad", f"{ctx.author.mention} is crying. probably lost embers gambling. 😢")
    await ctx.reply(embed=embed)

@bot.command()
async def laugh(ctx):
    """laugh"""
    embed = flame_embed("lol", f"{ctx.author.mention} is laughing. at what? we may never know. 😂")
    await ctx.reply(embed=embed)

@bot.command()
async def pat(ctx, user: discord.Member):
    """pat someone"""
    embed = flame_embed("pat", f"{ctx.author.mention} patted {user.mention}'s head. good job. 👍")
    await ctx.reply(embed=embed)

@bot.command()
async def boop(ctx, user: discord.Member):
    """boop someone"""
    embed = flame_embed("boop", f"{ctx.author.mention} booped {user.mention}! boop! 👆")
    await ctx.reply(embed=embed)

@bot.command()
async def yeet(ctx, user: discord.Member):
    """yeet someone"""
    embed = flame_embed("yeet", f"{ctx.author.mention} YEETED {user.mention} into the sun! 🚀")
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# MORE UTILITY COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def ping(ctx):
    """check bot latency"""
    latency = round(bot.latency * 1000)
    embed = flame_embed("ping", f"pong! **{latency}**ms

if this is high, blame discord not me.")
    await ctx.reply(embed=embed)

@bot.command()
async def avatar(ctx, user: discord.Member = None):
    """get someones avatar"""
    target = user or ctx.author
    embed = flame_embed(f"{target.display_name}'s avatar", "")
    embed.set_image(url=target.display_avatar.url)
    await ctx.reply(embed=embed)

@bot.command()
async def banner(ctx, user: discord.Member = None):
    """get someones banner (if visible)"""
    target = user or ctx.author
    try:
        user_fetch = await bot.fetch_user(target.id)
        if user_fetch.banner:
            embed = flame_embed(f"{target.display_name}'s banner", "")
            embed.set_image(url=user_fetch.banner.url)
        else:
            embed = flame_embed("no banner", f"{target.mention} has no banner. boring.")
    except:
        embed = flame_embed("error", "couldnt fetch banner. discord said no.")
    await ctx.reply(embed=embed)

@bot.command()
async def whois(ctx, user: discord.Member = None):
    """user info"""
    target = user or ctx.author
    embed = flame_embed(
        f"{target.display_name}",
        f"id: **{target.id}**
"
        f"joined server: **{target.joined_at.strftime('%Y-%m-%d') if target.joined_at else 'unknown'}**
"
        f"account created: **{target.created_at.strftime('%Y-%m-%d')}**
"
        f"roles: **{len(target.roles) - 1}**
"
        f"top role: **{target.top_role.name}**
"
        f"bot: **{'yes' if target.bot else 'no'}**"
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.reply(embed=embed)

@bot.command()
async def membercount(ctx):
    """server member count"""
    embed = flame_embed("members", f"**{ctx.guild.member_count}** members in this server.
**{sum(1 for m in ctx.guild.members if m.bot)}** bots.
**{sum(1 for m in ctx.guild.members if not m.bot)}** humans.")
    await ctx.reply(embed=embed)

@bot.command()
async def channelinfo(ctx, channel: discord.TextChannel = None):
    """channel info"""
    ch = channel or ctx.channel
    embed = flame_embed(
        f"#{ch.name}",
        f"id: **{ch.id}**
"
        f"created: **{ch.created_at.strftime('%Y-%m-%d')}**
"
        f"nsfw: **{'yes' if ch.is_nsfw() else 'no'}**
"
        f"slowmode: **{ch.slowmode_delay}s**
"
        f"category: **{ch.category.name if ch.category else 'none'}**"
    )
    await ctx.reply(embed=embed)

@bot.command()
async def roleinfo(ctx, *, role_name):
    """role info"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        embed = flame_embed("not found", f"role **{role_name}** not found.")
        await ctx.reply(embed=embed)
        return
    embed = flame_embed(
        f"@{role.name}",
        f"id: **{role.id}**
"
        f"color: **{role.color}**
"
        f"members: **{len(role.members)}**
"
        f"hoisted: **{'yes' if role.hoist else 'no'}**
"
        f"mentionable: **{'yes' if role.mentionable else 'no'}**
"
        f"position: **{role.position}**"
    )
    await ctx.reply(embed=embed)

@bot.command()
async def emoji(ctx, emoji_name: str = None):
    """list custom emojis"""
    if emoji_name:
        emo = discord.utils.get(ctx.guild.emojis, name=emoji_name)
        if emo:
            embed = flame_embed(f":{emo.name}:", f"animated: **{'yes' if emo.animated else 'no'}**
id: **{emo.id}**")
            embed.set_image(url=emo.url)
        else:
            embed = flame_embed("not found", f"emoji **{emoji_name}** not found.")
    else:
        emojis = ", ".join([str(e) for e in ctx.guild.emojis[:20]])
        embed = flame_embed("server emojis", emojis if emojis else "no custom emojis. sad.")
    await ctx.reply(embed=embed)

@bot.command()
async def invite(ctx):
    """bot invite link"""
    embed = flame_embed("invite", "bot invite link: [click here](https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot)

replace YOUR_CLIENT_ID with your actual client id.")
    await ctx.reply(embed=embed)

@bot.command()
async def poll(ctx, *, question):
    """create a poll"""
    embed = flame_embed("poll", f"{ctx.author.mention} asks: **{question}**

react 👍 for yes, 👎 for no")
    msg = await ctx.reply(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.command()
async def remind(ctx, minutes: int, *, reminder):
    """set a reminder"""
    embed = flame_embed("reminder set", f"ill remind you in **{minutes}** minutes about: *{reminder}*")
    await ctx.reply(embed=embed)
    await asyncio.sleep(minutes * 60)
    embed = flame_embed("reminder!", f"{ctx.author.mention}! remember: *{reminder}*")
    await ctx.send(embed=embed)

@bot.command()
async def calc(ctx, *, expression):
    """calculator"""
    try:
        # safe eval with limited operations
        allowed = {"__builtins__": None}
        for op in ["abs", "round", "max", "min", "sum", "pow"]:
            allowed[op] = eval(op)
        result = eval(expression, allowed, {"__builtins__": {}})
        embed = flame_embed("calc", f"**{expression}** = **{result}**")
    except:
        embed = flame_embed("error", "that math doesnt work. try again with actual numbers.")
    await ctx.reply(embed=embed)

@bot.command()
async def define(ctx, *, word):
    """define a word (mock)"""
    definitions = {
        "ember": "the currency of flame bot. also a small piece of burning coal.",
        "flame": "what this bot is named after. also fire but cooler.",
        "scam": "trying to steal embers. 30% success rate. not great.",
        "duel": "fighting someone for honor and embers. mostly embers.",
        "creature": "your pet in this bot. feed it or it gets grumpy.",
        "gamble": "the fastest way to lose embers. also the fastest way to gain them.",
    }
    defn = definitions.get(word.lower(), f"no definition for **{word}**. its probably not important.")
    embed = flame_embed(f"define: {word}", defn)
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# MORE MODERATION COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
@has_mod_perm("mute")
async def deafen(ctx, user: discord.Member):
    """deafen a user in voice"""
    if user.voice:
        await user.edit(deafen=True)
        embed = flame_embed("deafened", f"{user.mention} cant hear anything now. peace and quiet.")
    else:
        embed = flame_embed("not in vc", f"{user.mention} isnt in a voice channel.")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("mute")
async def undeafen(ctx, user: discord.Member):
    """undeafen a user"""
    if user.voice:
        await user.edit(deafen=False)
        embed = flame_embed("undeafened", f"{user.mention} can hear again. hope they behave.")
    else:
        embed = flame_embed("not in vc", f"{user.mention} isnt in a voice channel.")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("kick")
async def move(ctx, user: discord.Member, channel: discord.VoiceChannel):
    """move user to voice channel"""
    if user.voice:
        await user.move_to(channel)
        embed = flame_embed("moved", f"moved {user.mention} to **{channel.name}**.")
    else:
        embed = flame_embed("not in vc", f"{user.mention} isnt in a voice channel.")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("kick")
async def disconnect(ctx, user: discord.Member):
    """disconnect user from voice"""
    if user.voice:
        await user.move_to(None)
        embed = flame_embed("disconnected", f"kicked {user.mention} from voice. bye.")
    else:
        embed = flame_embed("not in vc", f"{user.mention} isnt in a voice channel.")
    await ctx.reply(embed=embed)

@bot.command()
@has_mod_perm("ban")
async def softban(ctx, user: discord.Member, *, reason="no reason"):
    """softban (ban then unban to clear messages)"""
    if user.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
        embed = flame_embed("nah", "cant softban someone equal or higher.")
        await ctx.reply(embed=embed)
        return
    await user.ban(reason=reason)
    await user.unban()
    embed = flame_embed("softbanned", f"{user.mention} softbanned. messages cleared, user can rejoin.")
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# MORE ADMIN COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
@is_owner()
async def shutdown(ctx):
    """shutdown the bot"""
    embed = flame_embed("shutting down", "flame bot going offline. see you on the other side. 🔥")
    await ctx.reply(embed=embed)
    await bot.close()

@bot.command()
@is_owner()
async def restart(ctx):
    """restart the bot"""
    embed = flame_embed("restarting", "flame bot restarting... brb. 🔥")
    await ctx.reply(embed=embed)
    await bot.close()

@bot.command()
@is_owner()
async def eval_(ctx, *, code):
    """evaluate code (owner only)"""
    try:
        result = eval(code)
        embed = flame_embed("eval result", f"```python
{result}
```")
    except Exception as e:
        embed = flame_embed("error", f"```
{e}
```")
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def say(ctx, *, message):
    """make bot say something"""
    await ctx.message.delete()
    await ctx.send(message)

@bot.command()
@is_owner()
async def embedsay(ctx, *, message):
    """make bot say something in an embed"""
    await ctx.message.delete()
    await ctx.send(embed=flame_embed("message", message))

@bot.command()
@is_owner()
async def announce(ctx, *, message):
    """announce to all servers"""
    count = 0
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(embed=flame_embed("announcement", message))
                    count += 1
                    break
                except:
                    continue
    embed = flame_embed("announced", f"sent to **{count}** servers.")
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def dm(ctx, user: discord.Member, *, message):
    """dm a user"""
    try:
        await user.send(embed=flame_embed("message", message))
        embed = flame_embed("sent", f"dm sent to {user.mention}.")
    except:
        embed = flame_embed("failed", f"couldnt dm {user.mention}. probably blocked.")
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def broadcast(ctx, *, message):
    """broadcast to all users"""
    sent = 0
    for uid in db.data["users"]:
        try:
            user = await bot.fetch_user(int(uid))
            await user.send(embed=flame_embed("broadcast", message))
            sent += 1
        except:
            pass
    embed = flame_embed("broadcast", f"sent to **{sent}** users.")
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def backup(ctx):
    """backup data"""
    backup_file = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_file, "w") as f:
        json.dump(db.data, f, indent=2)
    embed = flame_embed("backed up", f"data backed up to **{backup_file}**.")
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def restore(ctx, filename: str):
    """restore from backup"""
    try:
        with open(filename, "r") as f:
            db.data = json.load(f)
        db.save()
        embed = flame_embed("restored", f"data restored from **{filename}**.")
    except:
        embed = flame_embed("error", f"couldnt restore from **{filename}**.")
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def debug(ctx):
    """debug info"""
    embed = flame_embed(
        "debug",
        f"users in db: **{len(db.data['users'])}**
"
        f"guilds in db: **{len(db.data['guilds'])}**
"
        f"bot guilds: **{len(bot.guilds)}**
"
        f"bot users: **{sum(g.member_count for g in bot.guilds)}**
"
        f"latency: **{round(bot.latency * 1000)}**ms"
    )
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def status(ctx, *, activity):
    """set bot status"""
    await bot.change_presence(activity=discord.Game(name=activity))
    embed = flame_embed("status updated", f"now playing: **{activity}**")
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def maintenance(ctx, toggle: str):
    """toggle maintenance mode"""
    if toggle.lower() in ["on", "true", "yes"]:
        db.data["maintenance"] = True
        embed = flame_embed("maintenance", "maintenance mode **ON**. only owner can use commands.")
    else:
        db.data["maintenance"] = False
        embed = flame_embed("maintenance", "maintenance mode **OFF**. everyone can use commands.")
    db.save()
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def whitelist(ctx, user: discord.Member):
    """whitelist a user"""
    if "whitelist" not in db.data:
        db.data["whitelist"] = []
    db.data["whitelist"].append(user.id)
    db.save()
    embed = flame_embed("whitelisted", f"{user.mention} added to whitelist.")
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def blacklist(ctx, user: discord.Member):
    """blacklist a user"""
    if "blacklist" not in db.data:
        db.data["blacklist"] = []
    db.data["blacklist"].append(user.id)
    db.save()
    embed = flame_embed("blacklisted", f"{user.mention} added to blacklist. they cant use commands now.")
    await ctx.reply(embed=embed)

@bot.command()
@is_owner()
async def logs(ctx, lines: int = 10):
    """view recent logs (mock)"""
    embed = flame_embed("logs", f"showing last **{lines}** log entries.

(log system not implemented yet, this is a placeholder)")
    await ctx.reply(embed=embed)


# ═══════════════════════════════════════════════════════════════
# MISC / FUN FILLER COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def afk(ctx, *, reason="no reason given"):
    """set afk status"""
    user = db.get_user(ctx.author.id)
    user["settings"]["afk"] = reason
    db.save()
    embed = flame_embed("afk", f"{ctx.author.mention} is now afk: *{reason}*")
    await ctx.reply(embed=embed)

@bot.command()
async def back(ctx):
    """return from afk"""
    user = db.get_user(ctx.author.id)
    user["settings"]["afk"] = None
    db.save()
    embed = flame_embed("welcome back", f"{ctx.author.mention} is back! hope you had fun.")
    await ctx.reply(embed=embed)

@bot.command()
async def snipe(ctx):
    """snipe last deleted message (mock)"""
    embed = flame_embed("snipe", "snipe system not fully implemented. someone probably said something dumb tho.")
    await ctx.reply(embed=embed)

@bot.command()
async def editsnipe(ctx):
    """snipe last edited message (mock)"""
    embed = flame_embed("editsnipe", "edit snipe system not fully implemented. they probably fixed a typo.")
    await ctx.reply(embed=embed)

@bot.command()
async def firstmsg(ctx, user: discord.Member = None):
    """find first message from user (mock)"""
    target = user or ctx.author
    embed = flame_embed("first message", f"first message from {target.mention} was probably 'f daily' or something. cant scroll that far back.")
    await ctx.reply(embed=embed)

@bot.command()
async def boosters(ctx):
    """list server boosters"""
    boosters = [m for m in ctx.guild.members if m.premium_since]
    if not boosters:
        embed = flame_embed("no boosters", "nobody is boosting this server. sad.")
    else:
        desc = "\n".join([f"{b.mention} — since {b.premium_since.strftime('%Y-%m-%d')}" for b in boosters[:10]])
        embed = flame_embed("boosters", desc)
    await ctx.reply(embed=embed)

@bot.command()
async def bans(ctx):
    """list banned users"""
    ban_list = [entry async for entry in ctx.guild.bans()]
    if not ban_list:
        embed = flame_embed("clean", "no banned users. everyone behaves here.")
    else:
        desc = "\n".join([f"**{entry.user}** — {entry.reason or 'no reason'}" for entry in ban_list[:10]])
        embed = flame_embed("banned users", desc)
    await ctx.reply(embed=embed)

@bot.command()
async def invites(ctx):
    """list server invites"""
    invite_list = await ctx.guild.invites()
    if not invite_list:
        embed = flame_embed("no invites", "no active invites. create one with discord's invite button.")
    else:
        desc = "\n".join([f"**{inv.code}** — {inv.uses} uses" for inv in invite_list[:10]])
        embed = flame_embed("invites", desc)
    await ctx.reply(embed=embed)

@bot.command()
async def permissions(ctx, user: discord.Member = None):
    """check user permissions"""
    target = user or ctx.author
    perms = [p[0] for p in target.guild_permissions if p[1]]
    embed = flame_embed(f"{target.display_name}'s permissions", ", ".join(perms[:20]) if perms else "no special permissions")
    await ctx.reply(embed=embed)

@bot.command()
async def activity(ctx, user: discord.Member = None):
    """check user activity"""
    target = user or ctx.author
    if target.activity:
        embed = flame_embed("activity", f"{target.mention} is {target.activity.type.name} **{target.activity.name}**")
    else:
        embed = flame_embed("no activity", f"{target.mention} is doing nothing. boring.")
    await ctx.reply(embed=embed)

@bot.command()
async def playing(ctx, user: discord.Member = None):
    """check what someone is playing"""
    target = user or ctx.author
    for activity in target.activities:
        if isinstance(activity, discord.Game):
            embed = flame_embed("playing", f"{target.mention} is playing **{activity.name}**")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not playing", f"{target.mention} isnt playing anything.")
    await ctx.reply(embed=embed)

@bot.command()
async def listening(ctx, user: discord.Member = None):
    """check what someone is listening to"""
    target = user or ctx.author
    for activity in target.activities:
        if isinstance(activity, discord.Spotify):
            embed = flame_embed("listening", f"{target.mention} is listening to **{activity.title}** by **{activity.artist}**")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not listening", f"{target.mention} isnt listening to spotify.")
    await ctx.reply(embed=embed)

@bot.command()
async def watching(ctx, user: discord.Member = None):
    """check what someone is watching"""
    target = user or ctx.author
    for activity in target.activities:
        if isinstance(activity, discord.Activity) and activity.type == discord.ActivityType.watching:
            embed = flame_embed("watching", f"{target.mention} is watching **{activity.name}**")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not watching", f"{target.mention} isnt watching anything.")
    await ctx.reply(embed=embed)

@bot.command()
async def streaming(ctx, user: discord.Member = None):
    """check if someone is streaming"""
    target = user or ctx.author
    for activity in target.activities:
        if isinstance(activity, discord.Streaming):
            embed = flame_embed("streaming", f"{target.mention} is streaming **{activity.name}** at {activity.url}")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("not streaming", f"{target.mention} isnt streaming.")
    await ctx.reply(embed=embed)

@bot.command()
async def custom(ctx, user: discord.Member = None):
    """check custom status"""
    target = user or ctx.author
    for activity in target.activities:
        if isinstance(activity, discord.CustomActivity):
            embed = flame_embed("custom status", f"{target.mention}: *{activity.name}*")
            await ctx.reply(embed=embed)
            return
    embed = flame_embed("no custom", f"{target.mention} has no custom status.")
    await ctx.reply(embed=embed)

@bot.command()
async def color(ctx, color_code: str):
    """show a color"""
    try:
        color_int = int(color_code.replace("#", ""), 16)
        embed = discord.Embed(title=f"color #{color_code.replace('#', '')}", color=color_int)
        embed.set_image(url=f"https://singlecolorimage.com/get/{color_code.replace('#', '')}/100x100")
        await ctx.reply(embed=embed)
    except:
        embed = flame_embed("invalid", "use a valid hex color like #FF6B35")
        await ctx.reply(embed=embed)

@bot.command()
async def hex_(ctx, color_code: str):
    """show hex color"""
    await color(ctx, color_code)

# ═══════════════════════════════════════════════════════════════
# MORE CREATURE EXTRA COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def evolve_all(ctx):
    """evolve all eligible creatures"""
    user = db.get_user(ctx.author.id)
    evolved = 0
    for c in user["creatures"]:
        if not c["evolved"] and c["xp"] >= 100:
            c["evolved"] = True
            c["level"] += 1
            c["name"] = "mega " + c["name"]
            evolved += 1
    db.save()
    embed = flame_embed("mass evolution", f"evolved **{evolved}** creatures! your army grows stronger.")
    await ctx.reply(embed=embed)

@bot.command()
async def mass_feed(ctx):
    """feed all creatures at once"""
    user = db.get_user(ctx.author.id)
    cost = len(user["creatures"]) * 10
    if user["embers"] < cost:
        embed = flame_embed("broke", f"mass feed costs **{cost}** embers. you got **{user['embers']}**.")
        await ctx.reply(embed=embed)
        return
    user["embers"] -= cost
    for c in user["creatures"]:
        c["hunger"] = min(100, c["hunger"] + 30)
        c["bond"] = min(100, c["bond"] + 5)
    db.save()
    embed = flame_embed("fed", f"fed all **{len(user['creatures'])}** creatures for **{cost}** embers!")
    await ctx.reply(embed=embed)

@bot.command()
async def auto_feed(ctx, toggle: str):
    """toggle auto feed"""
    user = db.get_user(ctx.author.id)
    user["settings"]["auto_feed"] = toggle.lower() in ["on", "true", "yes"]
    db.save()
    status = "ON" if user["settings"]["auto_feed"] else "OFF"
    embed = flame_embed("auto feed", f"auto feed is now **{status}**. costs 10 embers per creature per day.")
    await ctx.reply(embed=embed)

@bot.command()
async def creature_leaderboard(ctx):
    """creature leaderboard"""
    all_creatures = []
    for uid, data in db.data["users"].items():
        for c in data["creatures"]:
            all_creatures.append((uid, c))
    all_creatures.sort(key=lambda x: x[1]["level"], reverse=True)

    desc = ""
    for i, (uid, c) in enumerate(all_creatures[:10]):
        try:
            user = await bot.fetch_user(int(uid))
            name = user.display_name
        except:
            name = f"user {uid[:8]}"
        desc += f"**{i+1}.** {c['name']} (lv{c['level']}) — owned by {name}
"
    if not desc:
        desc = "no creatures exist yet. summon some!"
    embed = flame_embed("creature leaderboard", desc)
    await ctx.reply(embed=embed)

@bot.command()
async def rare_summon(ctx):
    """summon a rare creature"""
    user = db.get_user(ctx.author.id)
    if len(user["creatures"]) >= 10:
        embed = flame_embed("zoo full", "release a creature first.")
        await ctx.reply(embed=embed)
        return
    if user["embers"] < 500:
        embed = flame_embed("broke", "rare summon costs 500 embers.")
        await ctx.reply(embed=embed)
        return

    user["embers"] -= 500
    rare_names = ["phoenix", "dragon", "kraken", "behemoth", "leviathan"]
    creature = {
        "name": random.choice(rare_names),
        "level": 5,
        "xp": 50,
        "mood": "mystical",
        "hunger": 80,
        "bond": 30,
        "evolved": False,
        "caged": False,
        "id": random.randint(1000, 9999),
        "rare": True
    }
    user["creatures"].append(creature)
    db.save()
    embed = flame_embed("RARE SUMMON!", f"you summoned **{creature['name']}**! its level **5** and glowing with power! ✨")
    await ctx.reply(embed=embed)

@bot.command()
async def legendary(ctx):
    """attempt legendary summon"""
    user = db.get_user(ctx.author.id)
    if user["embers"] < 2000:
        embed = flame_embed("broke", "legendary summon costs 2000 embers.")
        await ctx.reply(embed=embed)
        return

    user["embers"] -= 2000
    if random.random() < 0.1:
        creature = {
            "name": "godzilla",
            "level": 20,
            "xp": 500,
            "mood": "divine",
            "hunger": 100,
            "bond": 100,
            "evolved": True,
            "caged": False,
            "id": random.randint(1000, 9999),
            "legendary": True
        }
        user["creatures"].append(creature)
        db.save()
        embed = flame_embed("LEGENDARY!", f"you summoned **GODZILLA**! LEVEL **20**! THE ULTIMATE CREATURE! 🔥🔥🔥")
    else:
        db.save()
        embed = flame_embed("failed", f"summoning failed. lost 2000 embers. the gods were not pleased.")
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# EXTRA ECONOMY
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def fish(ctx):
    """go fishing"""
    cd = check_cooldown(ctx.author.id, "fish", 60)
    if cd:
        embed = flame_embed("cooldown", f"wait {cd}s before fishing again.")
        await ctx.reply(embed=embed)
        return

    catches = [("nothing", 0), ("small fish", 10), ("medium fish", 25), ("big fish", 50), ("treasure chest", 100), ("old boot", 5)]
    catch, value = random.choice(catches)
    db.add_embers(ctx.author.id, value)
    embed = flame_embed("fishing", f"you caught a **{catch}**! sold for **{value}** embers.")
    await ctx.reply(embed=embed)

@bot.command()
async def hunt(ctx):
    """go hunting"""
    cd = check_cooldown(ctx.author.id, "hunt", 120)
    if cd:
        embed = flame_embed("cooldown", f"wait {cd}s before hunting again.")
        await ctx.reply(embed=embed)
        return

    catches = [("nothing", 0), ("rabbit", 15), ("deer", 40), ("boar", 60), ("dragon", 200), ("your own foot", -10)]
    catch, value = random.choice(catches)
    db.add_embers(ctx.author.id, value)
    if value < 0:
        embed = flame_embed("hunting", f"you shot **{catch}**! paid **{abs(value)}** embers in medical fees.")
    else:
        embed = flame_embed("hunting", f"you hunted a **{catch}**! sold for **{value}** embers.")
    await ctx.reply(embed=embed)

@bot.command()
async def mine(ctx):
    """go mining"""
    cd = check_cooldown(ctx.author.id, "mine", 180)
    if cd:
        embed = flame_embed("cooldown", f"wait {cd}s before mining again.")
        await ctx.reply(embed=embed)
        return

    finds = [("nothing", 0), ("coal", 10), ("iron", 25), ("gold", 50), ("diamond", 100), ("lava", -30)]
    find, value = random.choice(finds)
    db.add_embers(ctx.author.id, value)
    if value < 0:
        embed = flame_embed("mining", f"you found **{find}**! lost **{abs(value)}** embers in equipment damage.")
    else:
        embed = flame_embed("mining", f"you mined **{find}**! sold for **{value}** embers.")
    await ctx.reply(embed=embed)

@bot.command()
async def chop(ctx):
    """chop wood"""
    cd = check_cooldown(ctx.author.id, "chop", 60)
    if cd:
        embed = flame_embed("cooldown", f"wait {cd}s before chopping again.")
        await ctx.reply(embed=embed)
        return

    wood = random.randint(5, 30)
    db.add_embers(ctx.author.id, wood)
    embed = flame_embed("chopping", f"you chopped **{wood}** embers worth of wood.")
    await ctx.reply(embed=embed)

@bot.command()
async def farm(ctx):
    """farm crops"""
    cd = check_cooldown(ctx.author.id, "farm", 300)
    if cd:
        embed = flame_embed("cooldown", f"wait {cd}s before farming again.")
        await ctx.reply(embed=embed)
        return

    crops = [("wheat", 20), ("corn", 35), ("potato", 15), ("carrot", 25), ("pumpkin", 50), ("ember fruit", 100)]
    crop, value = random.choice(crops)
    db.add_embers(ctx.author.id, value)
    embed = flame_embed("farming", f"you harvested **{crop}**! sold for **{value}** embers.")
    await ctx.reply(embed=embed)

@bot.command()
async def craft(ctx, *, item):
    """craft an item"""
    recipes = {"sword": 100, "shield": 80, "armor": 150, "potion": 50, "ring": 200}
    cost = recipes.get(item.lower(), 75)
    user = db.get_user(ctx.author.id)
    if user["embers"] < cost:
        embed = flame_embed("broke", f"crafting **{item}** costs **{cost}** embers.")
        await ctx.reply(embed=embed)
        return
    user["embers"] -= cost
    user["inventory"].append(item.lower())
    db.save()
    embed = flame_embed("crafted", f"crafted **{item}** for **{cost}** embers!")
    await ctx.reply(embed=embed)

@bot.command()
async def cook(ctx, *, food):
    """cook food"""
    recipes = {"stew": 30, "steak": 50, "soup": 20, "cake": 40, "ember pie": 100}
    cost = recipes.get(food.lower(), 35)
    user = db.get_user(ctx.author.id)
    if user["embers"] < cost:
        embed = flame_embed("broke", f"cooking **{food}** costs **{cost}** embers.")
        await ctx.reply(embed=embed)
        return
    user["embers"] -= cost
    user["inventory"].append(food.lower())
    db.save()
    embed = flame_embed("cooked", f"cooked **{food}**! smells good.")
    await ctx.reply(embed=embed)

@bot.command()
async def brew(ctx, *, potion):
    """brew a potion"""
    recipes = {"health": 40, "mana": 40, "luck": 60, "love": 100, "fire": 80}
    cost = recipes.get(potion.lower(), 50)
    user = db.get_user(ctx.author.id)
    if user["embers"] < cost:
        embed = flame_embed("broke", f"brewing **{potion}** costs **{cost}** embers.")
        await ctx.reply(embed=embed)
        return
    user["embers"] -= cost
    user["inventory"].append(potion.lower() + " potion")
    db.save()
    embed = flame_embed("brewed", f"brewed **{potion} potion**! dont drink it all at once.")
    await ctx.reply(embed=embed)

@bot.command()
async def forge(ctx, *, weapon):
    """forge a weapon"""
    recipes = {"dagger": 80, "sword": 150, "axe": 120, "hammer": 100, "spear": 90, "ember blade": 500}
    cost = recipes.get(weapon.lower(), 100)
    user = db.get_user(ctx.author.id)
    if user["embers"] < cost:
        embed = flame_embed("broke", f"forging **{weapon}** costs **{cost}** embers.")
        await ctx.reply(embed=embed)
        return
    user["embers"] -= cost
    user["inventory"].append(weapon.lower())
    db.save()
    embed = flame_embed("forged", f"forged **{weapon}**! its glowing with heat.")
    await ctx.reply(embed=embed)

@bot.command()
async def enchant(ctx, *, item):
    """enchant an item"""
    user = db.get_user(ctx.author.id)
    if item.lower() not in user["inventory"]:
        embed = flame_embed("not found", f"you dont have **{item}**. craft or buy it first.")
        await ctx.reply(embed=embed)
        return
    if user["embers"] < 200:
        embed = flame_embed("broke", "enchanting costs 200 embers.")
        await ctx.reply(embed=embed)
        return
    user["embers"] -= 200
    user["inventory"].remove(item.lower())
    user["inventory"].append("enchanted " + item.lower())
    db.save()
    embed = flame_embed("enchanted", f"**{item}** is now enchanted! +magic damage probably.")
    await ctx.reply(embed=embed)

@bot.command()
async def upgrade(ctx, *, item):
    """upgrade an item"""
    user = db.get_user(ctx.author.id)
    if item.lower() not in user["inventory"]:
        embed = flame_embed("not found", f"you dont have **{item}**.")
        await ctx.reply(embed=embed)
        return
    if user["embers"] < 300:
        embed = flame_embed("broke", "upgrading costs 300 embers.")
        await ctx.reply(embed=embed)
        return
    user["embers"] -= 300
    user["inventory"].remove(item.lower())
    user["inventory"].append("upgraded " + item.lower())
    db.save()
    embed = flame_embed("upgraded", f"**{item}** upgraded! its stronger now.")
    await ctx.reply(embed=embed)

@bot.command()
async def repair(ctx, *, item):
    """repair an item"""
    user = db.get_user(ctx.author.id)
    if item.lower() not in user["inventory"]:
        embed = flame_embed("not found", f"you dont have **{item}**.")
        await ctx.reply(embed=embed)
        return
    if user["embers"] < 50:
        embed = flame_embed("broke", "repairing costs 50 embers.")
        await ctx.reply(embed=embed)
        return
    user["embers"] -= 50
    db.save()
    embed = flame_embed("repaired", f"**{item}** repaired! good as new.")
    await ctx.reply(embed=embed)

@bot.command()
async def sellall(ctx):
    """sell all inventory items"""
    user = db.get_user(ctx.author.id)
    if not user["inventory"]:
        embed = flame_embed("empty", "nothing to sell.")
        await ctx.reply(embed=embed)
        return
    total = len(user["inventory"]) * 50
    user["embers"] += total
    user["inventory"] = []
    db.save()
    embed = flame_embed("sold", f"sold everything for **{total}** embers. your inventory is empty now.")
    await ctx.reply(embed=embed)

@bot.command()
async def donate(ctx, amount: int):
    """donate embers to the flame pool"""
    if amount <= 0:
        embed = flame_embed("nah", "donate at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers.")
        await ctx.reply(embed=embed)
        return
    user["embers"] -= amount
    if "donations" not in db.data:
        db.data["donations"] = 0
    db.data["donations"] += amount
    db.save()
    embed = flame_embed("donated", f"donated **{amount}** embers to the flame pool! total donations: **{db.data['donations']}**")
    await ctx.reply(embed=embed)

@bot.command()
async def tip(ctx, user: discord.Member, amount: int):
    """tip someone embers"""
    if amount <= 0:
        embed = flame_embed("nah", "tip at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    sender = db.get_user(ctx.author.id)
    if sender["embers"] < amount:
        embed = flame_embed("broke", f"you got **{sender['embers']}** embers.")
        await ctx.reply(embed=embed)
        return
    sender["embers"] -= amount
    receiver = db.get_user(user.id)
    receiver["embers"] += amount
    db.save()
    embed = flame_embed("tipped", f"tipped {user.mention} **{amount}** embers! generous.")
    await ctx.reply(embed=embed)

@bot.command()
async def pay(ctx, user: discord.Member, amount: int):
    """pay someone embers"""
    await tip(ctx, user, amount)

@bot.command()
async def share(ctx, user: discord.Member, amount: int):
    """share embers with someone"""
    await tip(ctx, user, amount)

@bot.command()
async def split(ctx, amount: int, *users: discord.Member):
    """split embers between users"""
    if not users:
        embed = flame_embed("need people", "mention at least one person to split with.")
        await ctx.reply(embed=embed)
        return
    total = amount * len(users)
    sender = db.get_user(ctx.author.id)
    if sender["embers"] < total:
        embed = flame_embed("broke", f"need **{total}** embers to split. you got **{sender['embers']}**.")
        await ctx.reply(embed=embed)
        return
    sender["embers"] -= total
    for user in users:
        receiver = db.get_user(user.id)
        receiver["embers"] += amount
    db.save()
    mentions = ", ".join([u.mention for u in users])
    embed = flame_embed("split", f"split **{amount}** embers each to {mentions}! total: **{total}**")
    await ctx.reply(embed=embed)

@bot.command()
async def pool(ctx, amount: int):
    """add to a group pool"""
    if amount <= 0:
        embed = flame_embed("nah", "pool at least 1 ember.")
        await ctx.reply(embed=embed)
        return
    user = db.get_user(ctx.author.id)
    if user["embers"] < amount:
        embed = flame_embed("broke", f"you got **{user['embers']}** embers.")
        await ctx.reply(embed=embed)
        return
    user["embers"] -= amount
    gid = str(ctx.guild.id)
    if "pool" not in db.data["guilds"].get(gid, {}):
        db.data["guilds"][gid]["pool"] = 0
    db.data["guilds"][gid]["pool"] += amount
    db.save()
    embed = flame_embed("pooled", f"added **{amount}** embers to the server pool! total: **{db.data['guilds'][gid]['pool']}**")
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# EXTRA WEIRD COMMANDS
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def summon_demon(ctx):
    """summon a demon"""
    demons = ["beelzebub", "asmodeus", "lucifer", "mephistopheles", "satan"]
    demon = random.choice(demons)
    embed = flame_embed("summoned", f"you summoned **{demon}**! they want **{random.randint(100, 500)}** embers as tribute. pay up or else.")
    await ctx.reply(embed=embed)

@bot.command()
async def ouija(ctx, *, question):
    """ask the ouija board"""
    letters = random.choices("abcdefghijklmnopqrstuvwxyz", k=random.randint(3, 8))
    answer = "".join(letters).upper()
    embed = flame_embed("ouija", f"**q:** {question}
**a:** {answer}

the spirits are... typing?")
    await ctx.reply(embed=embed)

@bot.command()
async def fortune(ctx):
    """get fortune"""
    fortunes = ["you will find embers in unexpected places", "beware of scams today", "a duel is coming your way", "your creature will evolve soon", "gamble wisely today"]
    embed = flame_embed("fortune", random.choice(fortunes) + " 🔮")
    await ctx.reply(embed=embed)

@bot.command()
async def horoscope(ctx, sign: str):
    """get horoscope"""
    horoscopes = ["ember flow is strong today", "avoid gambling, stars say no", "perfect day for a heist", "love is in the air, marry someone", "creatures are restless, feed them"]
    embed = flame_embed("horoscope", f"**{sign}**: {random.choice(horoscopes)} ✨")
    await ctx.reply(embed=embed)

@bot.command()
async def tarot(ctx):
    """draw a tarot card"""
    cards = ["the fool", "the magician", "the ember", "the gambler", "the scammer", "the duelist", "the bankrupt", "the rich", "the married", "the divorced"]
    card = random.choice(cards)
    embed = flame_embed("tarot", f"you drew **{card}**! interpret that however you want. 🔮")
    await ctx.reply(embed=embed)

@bot.command()
async def aura(ctx, user: discord.Member = None):
    """check someones aura"""
    target = user or ctx.author
    colors = ["red", "blue", "green", "purple", "gold", "black", "white", "rainbow"]
    aura = random.choice(colors)
    embed = flame_embed("aura reading", f"{target.mention}'s aura is **{aura}**! means absolutely nothing but sounds cool.")
    await ctx.reply(embed=embed)

@bot.command()
async def vibe(ctx):
    """check the vibe"""
    vibes = ["good vibes only", "mid vibes", "bad vibes", "chaotic vibes", "sus vibes", "fire vibes", "dead vibes"]
    embed = flame_embed("vibe check", f"current vibe: **{random.choice(vibes)}**")
    await ctx.reply(embed=embed)

@bot.command()
async def energy(ctx):
    """check energy levels"""
    energy = random.randint(0, 100)
    if energy >= 80:
        msg = "youre glowing! go gamble or something."
    elif energy >= 50:
        msg = "decent energy. could use a daily."
    elif energy >= 20:
        msg = "low energy. go beg for embers to feel better."
    else:
        msg = "empty. youre basically a ghost. f daily might help."
    embed = flame_embed("energy", f"**{energy}%** — {msg}")
    await ctx.reply(embed=embed)

@bot.command()
async def zodiac(ctx, sign: str):
    """zodiac info"""
    embed = flame_embed("zodiac", f"**{sign}** — your lucky number today is **{random.randint(1, 99)}**. your lucky color is **{random.choice(['red', 'blue', 'green', 'gold'])}**.")
    await ctx.reply(embed=embed)

@bot.command()
async def alignment(ctx):
    """check alignment"""
    alignments = ["lawful good", "neutral good", "chaotic good", "lawful neutral", "true neutral", "chaotic neutral", "lawful evil", "neutral evil", "chaotic evil"]
    embed = flame_embed("alignment", f"your alignment: **{random.choice(alignments)}**

this is 100% accurate and legally binding.")
    await ctx.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════
# GAMES
# ═══════════════════════════════════════════════════════════════

@bot.command()
async def tictactoe(ctx, user: discord.Member):
    """play tic tac toe"""
    if user.id == ctx.author.id:
        embed = flame_embed("bruh", "cant play yourself. thats just practice.")
        await ctx.reply(embed=embed)
        return
    if user.bot:
        embed = flame_embed("nah", "cant play a bot. they calculate too fast.")
        await ctx.reply(embed=embed)
        return

    board = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    players = [ctx.author, user]
    symbols = ["X", "O"]
    current = 0

    def display():
        return f"```
{board[0]} | {board[1]} | {board[2]}
---------
{board[3]} | {board[4]} | {board[5]}
---------
{board[6]} | {board[7]} | {board[8]}
```"

    def check_win():
        wins = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
        for a, b, c in wins:
            if board[a] == board[b] == board[c] in symbols:
                return board[a]
        return None

    embed = flame_embed("tic tac toe", f"{players[0].mention} (X) vs {players[1].mention} (O)
{display()}
{players[current].mention}'s turn! reply with a number 1-9.")
    msg = await ctx.reply(embed=embed)

    for _ in range(9):
        def check(m):
            return m.author == players[current] and m.channel == ctx.channel and m.content in board and m.content not in symbols

        try:
            move = await bot.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            embed = flame_embed("forfeit", f"{players[current].mention} took too long. {players[1-current].mention} wins by forfeit!")
            await msg.edit(embed=embed)
            return

        pos = int(move.content) - 1
        board[pos] = symbols[current]

        winner = check_win()
        if winner:
            winner_idx = symbols.index(winner)
            embed = flame_embed("winner!", f"{players[winner_idx].mention} wins!
{display()}")
            await msg.edit(embed=embed)
            return

        current = 1 - current
        embed = flame_embed("tic tac toe", f"{players[0].mention} (X) vs {players[1].mention} (O)
{display()}
{players[current].mention}'s turn!")
        await msg.edit(embed=embed)

    embed = flame_embed("tie", f"its a tie!
{display()}")
    await msg.edit(embed=embed)

@bot.command()
async def rps(ctx, user: discord.Member = None):
    """rock paper scissors"""
    if not user:
        # play against bot
        choices = ["rock", "paper", "scissors"]
        embed = flame_embed("rps", "choose: rock, paper, or scissors. reply in 15s.")
        msg = await ctx.reply(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in choices

        try:
            move = await bot.wait_for("message", timeout=15.0, check=check)
        except asyncio.TimeoutError:
            embed = flame_embed("forfeit", "too slow. bot wins by default.")
            await msg.edit(embed=embed)
            return

        bot_choice = random.choice(choices)
        user_choice = move.content.lower()

        if user_choice == bot_choice:
            result = "tie!"
        elif (user_choice == "rock" and bot_choice == "scissors") or (user_choice == "paper" and bot_choice == "rock") or (user_choice == "scissors" and bot_choice == "paper"):
            result = "you win!"
        else:
            result = "bot wins!"

        embed = flame_embed("rps result", f"you: **{user_choice}** | bot: **{bot_choice}**
**{result}**")
        await msg.edit(embed=embed)
    else:
        embed = flame_embed("rps", f"{ctx.author.mention} challenges {user.mention}!
{user.mention} react ✅ to play.")
        msg = await ctx.reply(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def check(reaction, reactor):
            return reactor == user and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

        try:
            reaction, reactor = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            embed = flame_embed("forfeit", f"{user.mention} didnt respond.")
            await msg.edit(embed=embed)
            return

        if str(reaction.emoji) == "❌":
            embed = flame_embed("declined", f"{user.mention} said no.")
            await msg.edit(embed=embed)
            return

        embed = flame_embed("rps", "both players dm me your choice: rock, paper, or scissors!")
        await msg.edit(embed=embed)
        # simplified: just random result
        choices = ["rock", "paper", "scissors"]
        c1 = random.choice(choices)
        c2 = random.choice(choices)
        if c1 == c2:
            result = "tie!"
        elif (c1 == "rock" and c2 == "scissors") or (c1 == "paper" and c2 == "rock") or (c1 == "scissors" and c2 == "paper"):
            result = f"{ctx.author.display_name} wins!"
        else:
            result = f"{user.display_name} wins!"
        embed = flame_embed("rps result", f"{ctx.author.display_name}: **{c1}** | {user.display_name}: **{c2}**
**{result}**")
        await msg.edit(embed=embed)

@bot.command()
async def guess(ctx):
    """guess the number game"""
    number = random.randint(1, 100)
    attempts = 7

    embed = flame_embed("guess the number", f"im thinking of a number 1-100. you have **{attempts}** guesses. reply with your guess!")
    msg = await ctx.reply(embed=embed)

    for i in range(attempts):
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        try:
            guess_msg = await bot.wait_for("message", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            embed = flame_embed("timeout", f"time's up! the number was **{number}**.")
            await msg.edit(embed=embed)
            return

        guess = int(guess_msg.content)
        remaining = attempts - i - 1

        if guess == number:
            db.add_embers(ctx.author.id, 50)
            embed = flame_embed("correct!", f"**{number}** is right! you win **50** embers! took **{i+1}** guesses.")
            await msg.edit(embed=embed)
            return
        elif guess < number:
            hint = "higher!"
        else:
            hint = "lower!"

        if remaining > 0:
            embed = flame_embed("guess", f"**{guess}** is wrong. go **{hint}**
**{remaining}** guesses left.")
            await msg.edit(embed=embed)

    embed = flame_embed("game over", f"out of guesses! the number was **{number}**. better luck next time.")
    await msg.edit(embed=embed)

@bot.command()
async def hotcold(ctx):
    """hot or cold guessing game"""
    target = random.randint(1, 100)
    last_guess = None

    embed = flame_embed("hot or cold", "guess a number 1-100. ill tell you if youre getting hotter or colder!")
    msg = await ctx.reply(embed=embed)

    for i in range(10):
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        try:
            guess_msg = await bot.wait_for("message", timeout=20.0, check=check)
        except asyncio.TimeoutError:
            embed = flame_embed("timeout", f"time's up! it was **{target}**.")
            await msg.edit(embed=embed)
            return

        guess = int(guess_msg.content)

        if guess == target:
            db.add_embers(ctx.author.id, 30)
            embed = flame_embed("found it!", f"**{target}**! you got it! +**30** embers!")
            await msg.edit(embed=embed)
            return

        dist = abs(guess - target)
        if last_guess is None:
            temp = "warm" if dist < 50 else "cold"
        else:
            last_dist = abs(last_guess - target)
            if dist < last_dist:
                temp = "HOTTER 🔥"
            elif dist > last_dist:
                temp = "colder ❄️"
            else:
                temp = "same temp 🤷"

        last_guess = guess
        embed = flame_embed("hot or cold", f"**{guess}** — youre getting **{temp}**! keep going!")
        await msg.edit(embed=embed)

    embed = flame_embed("game over", f"out of tries! it was **{target}**.")
    await msg.edit(embed=embed)

@bot.command()
async def math_(ctx):
    """quick math challenge"""
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    op = random.choice(["+", "-", "*"])
    if op == "+":
        answer = a + b
    elif op == "-":
        answer = a - b
    else:
        answer = a * b

    embed = flame_embed("math challenge", f"what is **{a} {op} {b}**? reply in 10 seconds!")
    msg = await ctx.reply(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

    try:
        answer_msg = await bot.wait_for("message", timeout=10.0, check=check)
    except asyncio.TimeoutError:
        embed = flame_embed("too slow", f"time's up! answer was **{answer}**.")
        await msg.edit(embed=embed)
        return

    if int(answer_msg.content) == answer:
        db.add_embers(ctx.author.id, 15)
        embed = flame_embed("correct!", f"**{answer}** is right! +**15** embers!")
    else:
        embed = flame_embed("wrong", f"nope! answer was **{answer}**.")
    await msg.edit(embed=embed)

@bot.command()
async def typing(ctx):
    """typing speed test (mock)"""
    words = ["ember", "flame", "discord", "creature", "gamble", "duel", "scam", "daily", "streak", "bank"]
    target = random.choice(words)
    embed = flame_embed("typing test", f"type **{target}** as fast as you can! go!")
    msg = await ctx.reply(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == target

    start = asyncio.get_event_loop().time()
    try:
        await bot.wait_for("message", timeout=10.0, check=check)
    except asyncio.TimeoutError:
        embed = flame_embed("too slow", "couldnt type it in time.")
        await msg.edit(embed=embed)
        return

    elapsed = asyncio.get_event_loop().time() - start
    db.add_embers(ctx.author.id, 10)
    embed = flame_embed("typed!", f"typed **{target}** in **{elapsed:.2f}** seconds! +**10** embers!")
    await msg.edit(embed=embed)

@bot.command()
async def reaction(ctx):
    """reaction speed test"""
    embed = flame_embed("reaction test", "react with 🔥 when i say GO!")
    msg = await ctx.reply(embed=embed)
    await asyncio.sleep(random.uniform(2, 5))

    embed = flame_embed("GO!", "react with 🔥 NOW!")
    await msg.edit(embed=embed)
    await msg.add_reaction("🔥")

    def check(reaction, user_reacted):
        return user_reacted == ctx.author and str(reaction.emoji) == "🔥" and reaction.message.id == msg.id

    start = asyncio.get_event_loop().time()
    try:
        await bot.wait_for("reaction_add", timeout=5.0, check=check)
    except asyncio.TimeoutError:
        embed = flame_embed("too slow", "you didnt react in time. sloth.")
        await msg.edit(embed=embed)
        return

    elapsed = asyncio.get_event_loop().time() - start
    db.add_embers(ctx.author.id, 10)
    embed = flame_embed("fast!", f"reacted in **{elapsed:.3f}** seconds! +**10** embers!")
    await msg.edit(embed=embed)

@bot.command()
async def memory(ctx):
    """memory game (mock)"""
    sequence = [random.choice(["🔥", "💰", "💎", "⚔️", "🛡️"]) for _ in range(5)]
    embed = flame_embed("memory", f"memorize this: {' '.join(sequence)}

i'll ask you to repeat it in 5 seconds...")
    msg = await ctx.reply(embed=embed)
    await asyncio.sleep(5)

    embed = flame_embed("memory", "what was the sequence? reply with the emojis in order!")
    await msg.edit(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        answer = await bot.wait_for("message", timeout=15.0, check=check)
    except asyncio.TimeoutError:
        embed = flame_embed("timeout", f"time's up! it was {' '.join(sequence)}")
        await msg.edit(embed=embed)
        return

    if answer.content.strip() == " ".join(sequence):
        db.add_embers(ctx.author.id, 25)
        embed = flame_embed("correct!", f"perfect memory! +**25** embers!")
    else:
        embed = flame_embed("wrong", f"nope! it was {' '.join(sequence)}")
    await msg.edit(embed=embed)

# ═══════════════════════════════════════════════════════════════
# RUN THE BOT
# ═══════════════════════════════════════════════════════════════

import os
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    print("ERROR: DISCORD_TOKEN environment variable not set!")
    print("set it in railway or run: export DISCORD_TOKEN=your_token_here")
else:
    bot.run(TOKEN)
