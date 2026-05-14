import discord
from discord.ext import commands, tasks
import asyncio
import random
import json
import os
import datetime
from collections import defaultdict

OWNER_ID = 1444293963812180120
PREFIXES = ["f ", "flame "]
CURRENCY = "embers"
TOKEN = os.getenv("DISCORD_TOKEN")

class DataStore:
    def __init__(self):
        self.users = {}
        self.guilds = {}
        self.creatures = {}
        self.marriages = {}
        self.cults = {}
        self.auctions = []
        self.streaks = {}
        self.loans = {}
        self.inventory = defaultdict(lambda: defaultdict(int))
        self.server_settings = defaultdict(dict)

    def get_user(self, user_id):
        if str(user_id) not in self.users:
            self.users[str(user_id)] = {
                "embers": 100, "bank": 0, "xp": 0, "level": 1,
                "daily_streak": 0, "last_daily": None, "creatures": [],
                "married_to": None, "cult": None,
                "duels_won": 0, "duels_lost": 0,
                "raids_won": 0, "raids_lost": 0,
                "scams_success": 0, "scams_failed": 0,
                "heists_success": 0, "heists_failed": 0,
                "total_gambled": 0, "total_earned": 0,
                "total_spent": 0, "warnings": 0,
                "created_at": datetime.datetime.now().isoformat()
            }
        return self.users[str(user_id)]

    def save(self):
        with open("bot_data.json", "w") as f:
            json.dump({
                "users": self.users, "guilds": self.guilds,
                "creatures": self.creatures, "marriages": self.marriages,
                "cults": self.cults, "auctions": self.auctions,
                "streaks": self.streaks, "loans": self.loans,
                "inventory": dict(self.inventory),
                "server_settings": dict(self.server_settings)
            }, f, default=str)

    def load(self):
        try:
            with open("bot_data.json", "r") as f:
                data = json.load(f)
                self.users = data.get("users", {})
                self.guilds = data.get("guilds", {})
                self.creatures = data.get("creatures", {})
                self.marriages = data.get("marriages", {})
                self.cults = data.get("cults", {})
                self.auctions = data.get("auctions", [])
                self.streaks = data.get("streaks", {})
                self.loans = data.get("loans", {})
                self.inventory = defaultdict(lambda: defaultdict(int), data.get("inventory", {}))
                self.server_settings = defaultdict(dict, data.get("server_settings", {}))
        except FileNotFoundError:
            pass

data = DataStore()
data.load()

intents = discord.Intents.all()

class FlameBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

    async def get_prefix(self, message):
        return PREFIXES

    async def setup_hook(self):
        self.auto_save.start()

    @tasks.loop(minutes=5)
    async def auto_save(self):
        data.save()

    async def on_ready(self):
        print(f"flame bot online as {self.user}")
        await self.change_presence(activity=discord.Game(name="f help | flame help"))

bot = FlameBot()

def is_owner():
    async def predicate(ctx):
        if ctx.author.id != OWNER_ID:
            await ctx.send("nah you can't use this command as ur not the bot owner. nice try tho lol")
            return False
        return True
    return commands.check(predicate)

def has_mod_perms():
    async def predicate(ctx):
        if ctx.author.id == OWNER_ID:
            return True
        if ctx.author.guild_permissions.kick_members or ctx.author.guild_permissions.ban_members or ctx.author.guild_permissions.manage_messages or ctx.author.guild_permissions.manage_nicknames or ctx.author.guild_permissions.manage_roles:
            return True
        await ctx.send("you need mod perms for that bro. get some roles first")
        return False
    return commands.check(predicate)

def has_admin_perms():
    async def predicate(ctx):
        if ctx.author.id == OWNER_ID:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        await ctx.send("admin only sorry. go cry to the server owner")
        return False
    return commands.check(predicate)

# ==================== ECONOMY COMMANDS ====================
@bot.command(aliases=["bal", "money", "cash"])
async def embers_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    u = data.get_user(target.id)
    embed = discord.Embed(title=f"{target.display_name}'s wallet", color=0xff6b35)
    embed.add_field(name="wallet", value=f"{u['embers']:,} {CURRENCY}", inline=True)
    embed.add_field(name="bank", value=f"{u['bank']:,} {CURRENCY}", inline=True)
    embed.add_field(name="total", value=f"{u['embers'] + u['bank']:,} {CURRENCY}", inline=True)
    embed.add_field(name="level", value=f"{u['level']} ({u['xp']} xp)", inline=True)
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    u = data.get_user(ctx.author.id)
    streak = u.get("daily_streak", 0)
    last = u.get("last_daily")
    if last:
        last_date = datetime.datetime.fromisoformat(last)
        if (datetime.datetime.now() - last_date).days > 1:
            streak = 0
    streak += 1
    base = 500
    bonus = min(streak * 50, 1000)
    total = base + bonus
    u["embers"] += total
    u["daily_streak"] = streak
    u["last_daily"] = datetime.datetime.now().isoformat()
    msg = f"you got {total:,} {CURRENCY}"
    if streak > 1:
        msg += f" (streak x{streak} - +{bonus} bonus)"
    msg += "!"
    if streak >= 7:
        msg += " damn u been grinding fr fr"
    await ctx.send(msg)

@bot.command()
async def streak(ctx):
    u = data.get_user(ctx.author.id)
    streak = u.get("daily_streak", 0)
    if streak == 0:
        await ctx.send("you got no streak bro. do f daily to start one")
    else:
        await ctx.send(f"you're on a {streak} day streak. keep it up or lose it lol")

@bot.command()
async def beg(ctx):
    u = data.get_user(ctx.author.id)
    if random.random() < 0.6:
        amount = random.randint(10, 100)
        u["embers"] += amount
        responses = [
            f"some random person felt bad and gave you {amount} {CURRENCY}",
            f"you begged so hard someone tossed you {amount} {CURRENCY}",
            f"a stranger pitied you and gave {amount} {CURRENCY}",
            f"you got {amount} {CURRENCY} from a generous old lady"
        ]
    else:
        responses = [
            "everyone ignored you lmao",
            "someone spat on you instead of giving money",
            "a dog barked at you. no embers today",
            "you got kicked out of the store for begging"
        ]
    await ctx.send(random.choice(responses))

@bot.command()
async def scam(ctx, user: discord.Member = None):
    if not user:
        await ctx.send("who u tryna scam bro? mention someone")
        return
    if user.id == ctx.author.id:
        await ctx.send("you can't scam yourself dumbass")
        return
    if user.bot:
        await ctx.send("bots are too smart for your scams lol")
        return
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    if target["embers"] < 50:
        await ctx.send(f"{user.display_name} is broke af. not worth scamming")
        return
    if random.random() < 0.4:
        amount = random.randint(50, min(500, target["embers"]))
        target["embers"] -= amount
        u["embers"] += amount
        u["scams_success"] += 1
        await ctx.send(f"you successfully scammed {user.display_name} for {amount} {CURRENCY}! you evil genius")
    else:
        u["scams_failed"] += 1
        fine = random.randint(20, 100)
        u["embers"] = max(0, u["embers"] - fine)
        await ctx.send(f"you got caught scamming and got fined {fine} {CURRENCY}. maybe don't be so obvious next time lol")

@bot.command()
async def invest(ctx, amount: str):
    u = data.get_user(ctx.author.id)
    if amount.lower() == "all":
        amount = u["embers"]
    else:
        try:
            amount = int(amount)
        except:
            await ctx.send("put a number or 'all' bro")
            return
    if amount < 50:
        await ctx.send(f"minimum investment is 50 {CURRENCY}. go beg for more")
        return
    if u["embers"] < amount:
        await ctx.send("you broke af. can't invest what you don't have")
        return
    u["embers"] -= amount
    roll = random.random()
    if roll < 0.3:
        loss = int(amount * random.uniform(0.5, 1.0))
        await ctx.send(f"market crashed and you lost {loss} {CURRENCY}. shoulda put it in the bank lol")
    elif roll < 0.6:
        profit = int(amount * random.uniform(0.1, 0.5))
        u["embers"] += amount + profit
        await ctx.send(f"decent returns. you made {profit} {CURRENCY} profit")
    elif roll < 0.85:
        profit = int(amount * random.uniform(0.5, 1.5))
        u["embers"] += amount + profit
        await ctx.send(f"stonks! you made {profit} {CURRENCY} profit!")
    else:
        profit = int(amount * random.uniform(2.0, 5.0))
        u["embers"] += amount + profit
        await ctx.send(f"JACKPOT! you made {profit} {CURRENCY} profit! you're basically warren buffett now")

@bot.command()
async def heist(ctx, user: discord.Member = None):
    if not user:
        await ctx.send("who's bank we hitting?")
        return
    if user.id == ctx.author.id:
        await ctx.send("you can't heist yourself lol")
        return
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    if target["bank"] < 200:
        await ctx.send(f"{user.display_name}'s bank is dry. pick a richer target")
        return
    if random.random() < 0.35:
        amount = random.randint(100, min(1000, target["bank"]))
        target["bank"] -= amount
        u["embers"] += amount
        u["heists_success"] += 1
        await ctx.send(f"successful heist! you stole {amount} {CURRENCY} from {user.display_name}'s bank!")
    else:
        u["heists_failed"] += 1
        fine = random.randint(50, 200)
        u["embers"] = max(0, u["embers"] - fine)
        await ctx.send(f"heist failed! security caught you and fined you {fine} {CURRENCY}. smooth criminal my ass")

@bot.command()
async def loan(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if amount < 100:
        await ctx.send(f"minimum loan is 100 {CURRENCY}")
        return
    if amount > 5000:
        await ctx.send("max loan is 5000 {CURRENCY}. we ain't a charity")
        return
    if str(ctx.author.id) in data.loans:
        await ctx.send("you already owe us money bro. pay up first")
        return
    u["embers"] += amount
    data.loans[str(ctx.author.id)] = {
        "amount": amount, "due": amount * 1.2,
        "taken": datetime.datetime.now().isoformat()
    }
    await ctx.send(f"you borrowed {amount} {CURRENCY}. you owe {int(amount * 1.2)} {CURRENCY} back. don't skip town lol")

@bot.command()
async def repay(ctx):
    uid = str(ctx.author.id)
    if uid not in data.loans:
        await ctx.send("you don't have any loans bro. living debt free i see")
        return
    u = data.get_user(ctx.author.id)
    loan = data.loans[uid]
    if u["embers"] < loan["due"]:
        await ctx.send(f"you need {loan['due']} {CURRENCY} to repay. you're short by {loan['due'] - u['embers']}")
        return
    u["embers"] -= int(loan["due"])
    del data.loans[uid]
    await ctx.send("loan repaid! your credit score probably still trash tho")

@bot.command()
async def burn(ctx, amount: str):
    u = data.get_user(ctx.author.id)
    if amount.lower() == "all":
        amount = u["embers"]
    else:
        try:
            amount = int(amount)
        except:
            await ctx.send("number or 'all' please")
            return
    if amount > u["embers"]:
        await ctx.send("you can't burn what you don't have")
        return
    if amount <= 0:
        await ctx.send(f"burn at least 1 {CURRENCY} you cheapskate")
        return
    u["embers"] -= amount
    await ctx.send(f"you burned {amount} {CURRENCY}. why? just why? you could've given it to me lol")

@bot.command()
async def send(ctx, amount: int, user: discord.Member = None):
    if not user:
        await ctx.send("who you sending embers to?")
        return
    if user.id == ctx.author.id:
        await ctx.send("you can't send embers to yourself that's just moving money around lol")
        return
    if user.bot:
        await ctx.send("bots don't need embers bro")
        return
    if amount <= 0:
        await ctx.send(f"send at least 1 {CURRENCY}")
        return
    u = data.get_user(ctx.author.id)
    if u["embers"] < amount:
        await ctx.send("you broke. can't send what you don't have")
        return
    msg = await ctx.send(f"are you sure you want to send {amount:,} {CURRENCY} to {user.display_name}? react with ✅ to confirm")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    def check(reaction, reactor):
        return reactor == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    try:
        reaction, reactor = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "✅":
            u["embers"] -= amount
            target = data.get_user(user.id)
            target["embers"] += amount
            await ctx.send(f"sent {amount:,} {CURRENCY} to {user.display_name}! what a generous king/queen")
        else:
            await ctx.send("transaction cancelled. keeping your money i see")
    except asyncio.TimeoutError:
        await ctx.send("you took too long. transaction cancelled")

# ==================== CREATURE COMMANDS ====================
CREATURE_NAMES = ["dragon", "phoenix", "golem", "wolf", "serpent", "imp", "wyvern", "basilisk", "chimera", "griffin", "kraken", "leviathan", "behemoth", "unicorn", "pegasus", "centaur", "minotaur", "hydra"]
CREATURE_TYPES = ["fire", "water", "earth", "air", "dark", "light", "nature", "electric", "ice", "metal"]

@bot.command()
async def summon(ctx):
    u = data.get_user(ctx.author.id)
    cost = 100
    if u["embers"] < cost:
        await ctx.send(f"summoning costs {cost} {CURRENCY}. go beg for more")
        return
    u["embers"] -= cost
    creature = {
        "id": random.randint(100000, 999999),
        "name": random.choice(CREATURE_NAMES),
        "type": random.choice(CREATURE_TYPES),
        "level": 1, "xp": 0,
        "mood": random.randint(50, 100),
        "hunger": random.randint(50, 100),
        "owner": ctx.author.id, "evolutions": 0, "wins": 0, "fav": False
    }
    cid = str(creature["id"])
    data.creatures[cid] = creature
    u["creatures"].append(cid)
    embed = discord.Embed(title="🎉 new creature summoned!", color=0x00ff00)
    embed.add_field(name="name", value=creature["name"], inline=True)
    embed.add_field(name="type", value=creature["type"], inline=True)
    embed.add_field(name="level", value=creature["level"], inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def cage(ctx):
    u = data.get_user(ctx.author.id)
    if not u["creatures"]:
        await ctx.send("you got no creatures bro. use f summon to get one")
        return
    embed = discord.Embed(title="your creatures", color=0x7289da)
    for cid in u["creatures"][:10]:
        if cid in data.creatures:
            c = data.creatures[cid]
            embed.add_field(
                name=f"{c['name']} #{c['id']}",
                value=f"lvl {c['level']} {c['type']} | mood: {c['mood']}% | hunger: {c['hunger']}%",
                inline=False
            )
    await ctx.send(embed=embed)

@bot.command()
async def release(ctx, creature_id: int):
    cid = str(creature_id)
    u = data.get_user(ctx.author.id)
    if cid not in u["creatures"]:
        await ctx.send("that's not your creature bro")
        return
    u["creatures"].remove(cid)
    if cid in data.creatures:
        del data.creatures[cid]
    await ctx.send(f"released creature #{creature_id}. fly free little buddy... or get eaten idk")

@bot.command()
async def feed(ctx, creature_id: int):
    cid = str(creature_id)
    u = data.get_user(ctx.author.id)
    if cid not in u["creatures"]:
        await ctx.send("not your creature")
        return
    cost = 20
    if u["embers"] < cost:
        await ctx.send(f"feeding costs {cost} {CURRENCY}")
        return
    u["embers"] -= cost
    c = data.creatures[cid]
    c["hunger"] = min(100, c["hunger"] + 30)
    c["mood"] = min(100, c["mood"] + 10)
    await ctx.send(f"fed {c['name']}. it's looking happy and full now")

@bot.command()
async def neglect(ctx, creature_id: int):
    cid = str(creature_id)
    u = data.get_user(ctx.author.id)
    if cid not in u["creatures"]:
        await ctx.send("not yours")
        return
    c = data.creatures[cid]
    c["hunger"] = max(0, c["hunger"] - 20)
    c["mood"] = max(0, c["mood"] - 15)
    await ctx.send(f"you neglected {c['name']}. it's sad now. you monster")

@bot.command()
async def mood(ctx, creature_id: int):
    cid = str(creature_id)
    u = data.get_user(ctx.author.id)
    if cid not in u["creatures"]:
        await ctx.send("not yours")
        return
    c = data.creatures[cid]
    await ctx.send(f"{c['name']} is feeling {c['mood']}% happy. hunger at {c['hunger']}%")

@bot.command()
async def evolve(ctx, creature_id: int):
    cid = str(creature_id)
    u = data.get_user(ctx.author.id)
    if cid not in u["creatures"]:
        await ctx.send("not yours")
        return
    c = data.creatures[cid]
    needed = c["level"] * 100
    if c["xp"] < needed:
        await ctx.send(f"needs {needed} xp to evolve. currently at {c['xp']}")
        return
    cost = c["level"] * 200
    if u["embers"] < cost:
        await ctx.send(f"evolution costs {cost} {CURRENCY}")
        return
    u["embers"] -= cost
    c["level"] += 1
    c["xp"] = 0
    c["evolutions"] += 1
    old_name = c["name"]
    c["name"] = "mega " + c["name"] if c["evolutions"] == 1 else "ultra " + c["name"]
    await ctx.send(f"{old_name} evolved into {c['name']}! it's now level {c['level']}!")

@bot.command()
async def breed(ctx, id1: int, id2: int):
    cid1, cid2 = str(id1), str(id2)
    u = data.get_user(ctx.author.id)
    if cid1 not in u["creatures"] or cid2 not in u["creatures"]:
        await ctx.send("both creatures gotta be yours bro")
        return
    if cid1 == cid2:
        await ctx.send("can't breed a creature with itself. that's weird")
        return
    c1, c2 = data.creatures[cid1], data.creatures[cid2]
    cost = 300
    if u["embers"] < cost:
        await ctx.send(f"breeding costs {cost} {CURRENCY}")
        return
    u["embers"] -= cost
    baby = {
        "id": random.randint(100000, 999999),
        "name": f"baby {c1['name']}",
        "type": random.choice([c1["type"], c2["type"]]),
        "level": 1, "xp": 0, "mood": 80, "hunger": 80,
        "owner": ctx.author.id, "evolutions": 0, "wins": 0, "fav": False
    }
    bcid = str(baby["id"])
    data.creatures[bcid] = baby
    u["creatures"].append(bcid)
    await ctx.send(f"{c1['name']} and {c2['name']} had a baby! welcome baby {baby['name']}!")

@bot.command()
async def sacrifice(ctx, creature_id: int):
    cid = str(creature_id)
    u = data.get_user(ctx.author.id)
    if cid not in u["creatures"]:
        await ctx.send("not yours")
        return
    c = data.creatures[cid]
    reward = c["level"] * 50 + c["evolutions"] * 200
    u["embers"] += reward
    u["creatures"].remove(cid)
    del data.creatures[cid]
    await ctx.send(f"sacrificed {c['name']} for {reward} {CURRENCY}. dark magic stuff right there")

@bot.command()
async def rename(ctx, creature_id: int, *, new_name: str):
    cid = str(creature_id)
    u = data.get_user(ctx.author.id)
    if cid not in u["creatures"]:
        await ctx.send("not yours")
        return
    cost = 50
    if u["embers"] < cost:
        await ctx.send(f"renaming costs {cost} {CURRENCY}")
        return
    u["embers"] -= cost
    old = data.creatures[cid]["name"]
    data.creatures[cid]["name"] = new_name
    await ctx.send(f"renamed {old} to {new_name}! cute name lol")

@bot.command()
async def favorite(ctx, creature_id: int):
    cid = str(creature_id)
    u = data.get_user(ctx.author.id)
    if cid not in u["creatures"]:
        await ctx.send("not yours")
        return
    for other_cid in u["creatures"]:
        if other_cid in data.creatures:
            data.creatures[other_cid]["fav"] = False
    data.creatures[cid]["fav"] = True
    await ctx.send(f"{data.creatures[cid]['name']} is now your favorite! no favoritism tho...")

@bot.command()
async def trade(ctx, user: discord.Member, your_id: int, their_id: int):
    if user.id == ctx.author.id:
        await ctx.send("can't trade with yourself")
        return
    your_cid = str(your_id)
    their_cid = str(their_id)
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    if your_cid not in u["creatures"]:
        await ctx.send("that's not your creature")
        return
    if their_cid not in target["creatures"]:
        await ctx.send(f"{user.display_name} doesn't own that creature")
        return
    msg = await ctx.send(f"{user.mention}, {ctx.author.display_name} wants to trade their {data.creatures[your_cid]['name']} for your {data.creatures[their_cid]['name']}. react ✅ to accept")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    def check(reaction, reactor):
        return reactor == user and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    try:
        reaction, reactor = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        if str(reaction.emoji) == "✅":
            u["creatures"].remove(your_cid)
            u["creatures"].append(their_cid)
            target["creatures"].remove(their_cid)
            target["creatures"].append(your_cid)
            data.creatures[your_cid]["owner"] = user.id
            data.creatures[their_cid]["owner"] = ctx.author.id
            await ctx.send("trade complete! both of you got new pets")
        else:
            await ctx.send("trade declined. maybe next time")
    except asyncio.TimeoutError:
        await ctx.send("trade expired. nobody reacted in time")

@bot.command()
async def auction(ctx, creature_id: int, starting_bid: int):
    cid = str(creature_id)
    u = data.get_user(ctx.author.id)
    if cid not in u["creatures"]:
        await ctx.send("not yours")
        return
    auction = {
        "id": random.randint(1000, 9999),
        "seller": ctx.author.id,
        "creature": cid,
        "current_bid": starting_bid,
        "highest_bidder": None,
        "end_time": (datetime.datetime.now() + datetime.timedelta(minutes=5)).isoformat(),
        "active": True
    }
    data.auctions.append(auction)
    await ctx.send(f"auction started for {data.creatures[cid]['name']}! starting bid: {starting_bid} {CURRENCY}. use f bid {auction['id']} <amount> to bid")

@bot.command()
async def bid(ctx, auction_id: int, amount: int):
    auction = None
    for a in data.auctions:
        if a["id"] == auction_id and a["active"]:
            auction = a
            break
    if not auction:
        await ctx.send("auction not found or ended")
        return
    if datetime.datetime.now() > datetime.datetime.fromisoformat(auction["end_time"]):
        auction["active"] = False
        await ctx.send("auction already ended")
        return
    u = data.get_user(ctx.author.id)
    if amount <= auction["current_bid"]:
        await ctx.send("bid higher than current bid")
        return
    if u["embers"] < amount:
        await ctx.send("you broke. can't bid what you don't have")
        return
    if auction["highest_bidder"]:
        prev = data.get_user(auction["highest_bidder"])
        prev["embers"] += auction["current_bid"]
    u["embers"] -= amount
    auction["current_bid"] = amount
    auction["highest_bidder"] = ctx.author.id
    await ctx.send(f"you're the highest bidder with {amount} {CURRENCY}!")

@bot.command()
async def inspect(ctx, creature_id: int):
    cid = str(creature_id)
    if cid not in data.creatures:
        await ctx.send("creature not found")
        return
    c = data.creatures[cid]
    embed = discord.Embed(title=f"inspecting {c['name']}", color=0x7289da)
    embed.add_field(name="id", value=c["id"], inline=True)
    embed.add_field(name="type", value=c["type"], inline=True)
    embed.add_field(name="level", value=c["level"], inline=True)
    embed.add_field(name="evolutions", value=c["evolutions"], inline=True)
    embed.add_field(name="mood", value=f"{c['mood']}%", inline=True)
    embed.add_field(name="hunger", value=f"{c['hunger']}%", inline=True)
    embed.add_field(name="wins", value=c["wins"], inline=True)
    embed.add_field(name="favorite", value="yes" if c["fav"] else "no", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def adopt(ctx, user: discord.Member, creature_id: int):
    cid = str(creature_id)
    target = data.get_user(user.id)
    u = data.get_user(ctx.author.id)
    if cid not in target["creatures"]:
        await ctx.send(f"{user.display_name} doesn't have that creature")
        return
    msg = await ctx.send(f"{user.mention}, {ctx.author.display_name} wants to adopt your {data.creatures[cid]['name']}. react ✅ to give it away")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    def check(reaction, reactor):
        return reactor == user and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    try:
        reaction, reactor = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        if str(reaction.emoji) == "✅":
            target["creatures"].remove(cid)
            u["creatures"].append(cid)
            data.creatures[cid]["owner"] = ctx.author.id
            await ctx.send(f"{ctx.author.display_name} adopted {data.creatures[cid]['name']}! take good care of it")
        else:
            await ctx.send("adoption denied. cold hearted fr")
    except asyncio.TimeoutError:
        await ctx.send("adoption request expired")

@bot.command()
async def kidnap(ctx, user: discord.Member, creature_id: int):
    if user.id == ctx.author.id:
        await ctx.send("can't kidnap your own creature weirdo")
        return
    cid = str(creature_id)
    target = data.get_user(user.id)
    u = data.get_user(ctx.author.id)
    if cid not in target["creatures"]:
        await ctx.send("they don't have that creature")
        return
    if random.random() < 0.15:
        target["creatures"].remove(cid)
        u["creatures"].append(cid)
        data.creatures[cid]["owner"] = ctx.author.id
        await ctx.send(f"you successfully kidnapped {data.creatures[cid]['name']}! you're a monster but it worked lol")
    else:
        fine = random.randint(100, 500)
        u["embers"] = max(0, u["embers"] - fine)
        await ctx.send(f"kidnap failed! {user.display_name} caught you and you got fined {fine} {CURRENCY}. maybe don't be creepy next time")

# ==================== COMBAT COMMANDS ====================
@bot.command()
async def duel(ctx, user: discord.Member):
    if user.id == ctx.author.id:
        await ctx.send("can't duel yourself")
        return
    if user.bot:
        await ctx.send("bots are too op. pick a human")
        return
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    msg = await ctx.send(f"{user.mention}, {ctx.author.display_name} wants to duel! react ✅ to accept")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    def check(reaction, reactor):
        return reactor == user and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    try:
        reaction, reactor = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) != "✅":
            await ctx.send("they chickened out lol")
            return
    except asyncio.TimeoutError:
        await ctx.send("they didn't respond. coward")
        return
    u_power = u["level"] * 10 + random.randint(0, 50)
    t_power = target["level"] * 10 + random.randint(0, 50)
    if u_power > t_power:
        winnings = random.randint(50, 200)
        u["embers"] += winnings
        u["duels_won"] += 1
        target["duels_lost"] += 1
        await ctx.send(f"you won the duel! {user.display_name} got destroyed and you won {winnings} {CURRENCY}")
    elif t_power > u_power:
        loss = random.randint(20, 100)
        u["embers"] = max(0, u["embers"] - loss)
        u["duels_lost"] += 1
        target["duels_won"] += 1
        await ctx.send(f"you lost the duel to {user.display_name}. they took {loss} {CURRENCY} from you. get good lol")
    else:
        await ctx.send("it was a draw! both of you are equally mid")

@bot.command()
async def raid(ctx, user: discord.Member):
    if user.id == ctx.author.id:
        await ctx.send("can't raid yourself")
        return
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    u_power = u["level"] * 15 + random.randint(0, 100)
    t_power = target["level"] * 15 + random.randint(0, 100)
    if u_power > t_power:
        loot = random.randint(100, 500)
        actual_loot = min(loot, target["embers"])
        target["embers"] -= actual_loot
        u["embers"] += actual_loot
        u["raids_won"] += 1
        target["raids_lost"] += 1
        await ctx.send(f"raid successful! you stole {actual_loot} {CURRENCY} from {user.display_name}! they didn't see it coming")
    else:
        u["raids_lost"] += 1
        target["raids_won"] += 1
        await ctx.send(f"raid failed! {user.display_name}'s defenses were too strong. you retreated with your tail between your legs")

@bot.command()
async def ambush(ctx, user: discord.Member):
    if user.id == ctx.author.id:
        await ctx.send("can't ambush yourself")
        return
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    if random.random() < 0.5:
        loot = random.randint(50, 300)
        actual = min(loot, target["embers"])
        target["embers"] -= actual
        u["embers"] += actual
        await ctx.send(f"ambush successful! caught {user.display_name} off guard and took {actual} {CURRENCY}")
    else:
        await ctx.send(f"{user.display_name} was too alert. ambush failed and you ran away")

@bot.command()
async def defend(ctx):
    await ctx.send("your base is fortified for the next hour. good luck getting raided now lol")

@bot.command()
async def berserk(ctx, user: discord.Member):
    if user.id == ctx.author.id:
        await ctx.send("can't berserk yourself")
        return
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    if random.random() < 0.6:
        damage = random.randint(100, 1000)
        actual = min(damage, target["embers"])
        target["embers"] -= actual
        u["embers"] += actual // 2
        await ctx.send(f"BERSERK MODE ACTIVATED! you destroyed {user.display_name} and took {actual} {CURRENCY}! you only kept half cuz you were too angry to count properly")
    else:
        self_damage = random.randint(50, 200)
        u["embers"] = max(0, u["embers"] - self_damage)
        await ctx.send(f"you went berserk but tripped and hurt yourself. lost {self_damage} {CURRENCY} to medical bills lol")

@bot.command()
async def bribe(ctx, user: discord.Member, amount: int):
    if user.id == ctx.author.id:
        await ctx.send("can't bribe yourself")
        return
    u = data.get_user(ctx.author.id)
    if u["embers"] < amount:
        await ctx.send("you broke. can't bribe with air")
        return
    u["embers"] -= amount
    target = data.get_user(user.id)
    target["embers"] += amount
    await ctx.send(f"you bribed {user.display_name} with {amount} {CURRENCY} to not attack you. money solves everything huh")

@bot.command()
async def flee(ctx):
    responses = [
        "you ran away like a coward. at least you're alive",
        "you fled so fast you left your shoes behind",
        "tactical retreat! that's what we're calling it now",
        "you escaped... this time"
    ]
    await ctx.send(random.choice(responses))

@bot.command()
async def taunt(ctx, user: discord.Member):
    taunts = [
        f"{ctx.author.display_name} says {user.display_name} fights like a wet noodle",
        f"{ctx.author.display_name} called {user.display_name} a noob. harsh but fair",
        f"{ctx.author.display_name} said {user.display_name}'s mom could beat them in a duel",
        f"{ctx.author.display_name} thinks {user.display_name} is all talk no action"
    ]
    await ctx.send(random.choice(taunts))

@bot.command()
async def combo(ctx, user: discord.Member):
    if user.id == ctx.author.id:
        await ctx.send("can't combo yourself")
        return
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    hits = random.randint(2, 5)
    total = 0
    for _ in range(hits):
        hit = random.randint(20, 100)
        actual = min(hit, target["embers"])
        target["embers"] -= actual
        total += actual
    u["embers"] += total // 2
    await ctx.send(f"COMBO x{hits}! you hit {user.display_name} {hits} times and took {total} {CURRENCY}! anime fight scene energy")

@bot.command()
async def revive(ctx):
    u = data.get_user(ctx.author.id)
    cost = 200
    if u["embers"] < cost:
        await ctx.send(f"reviving costs {cost} {CURRENCY}. stay dead then lol")
        return
    u["embers"] -= cost
    await ctx.send("you revived! back from the dead like nothing happened. video game logic")

@bot.command()
async def wager(ctx, user: discord.Member, amount: int):
    if user.id == ctx.author.id:
        await ctx.send("can't wager yourself")
        return
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    if u["embers"] < amount or target["embers"] < amount:
        await ctx.send("one of you is too broke for this wager")
        return
    msg = await ctx.send(f"{user.mention}, {ctx.author.display_name} wants to wager {amount} {CURRENCY}. react ✅ to accept")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    def check(reaction, reactor):
        return reactor == user and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    try:
        reaction, reactor = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) != "✅":
            await ctx.send("they declined the wager. scared of losing probably")
            return
    except asyncio.TimeoutError:
        await ctx.send("they didn't respond. wager cancelled")
        return
    if random.random() < 0.5:
        u["embers"] += amount
        target["embers"] -= amount
        await ctx.send(f"you won the wager! took {amount} {CURRENCY} from {user.display_name}! easy money")
    else:
        u["embers"] -= amount
        target["embers"] += amount
        await ctx.send(f"you lost the wager! {user.display_name} took your {amount} {CURRENCY}. skill issue")

@bot.command()
async def rank(ctx):
    u = data.get_user(ctx.author.id)
    total = u["duels_won"] + u["raids_won"]
    if total < 5:
        rank = "wood"
    elif total < 15:
        rank = "bronze"
    elif total < 30:
        rank = "silver"
    elif total < 50:
        rank = "gold"
    elif total < 100:
        rank = "platinum"
    else:
        rank = "diamond"
    await ctx.send(f"your combat rank is {rank}! {u['duels_won']} duels won, {u['raids_won']} raids won. keep grinding")

# ==================== GAMBLING COMMANDS ====================
@bot.command()
async def dice(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("you broke")
        return
    if amount <= 0:
        await ctx.send("bet something")
        return
    u["total_gambled"] += amount
    roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    if roll > bot_roll:
        u["embers"] += amount
        u["total_earned"] += amount
        await ctx.send(f"you rolled {roll}, i rolled {bot_roll}. you win {amount} {CURRENCY}! lucky")
    elif roll < bot_roll:
        u["embers"] -= amount
        await ctx.send(f"you rolled {roll}, i rolled {bot_roll}. you lose {amount} {CURRENCY}. unlucky")
    else:
        await ctx.send(f"both rolled {roll}. tie! nobody wins or loses")

@bot.command()
async def shells(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("broke")
        return
    u["total_gambled"] += amount
    if random.random() < 0.33:
        winnings = amount * 2
        u["embers"] += winnings
        u["total_earned"] += winnings
        await ctx.send(f"you found the ball! won {winnings} {CURRENCY}! eyes of a hawk")
    else:
        u["embers"] -= amount
        await ctx.send("wrong shell! lost your money. the ball was under the other one lol")

@bot.command()
async def flip(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("broke")
        return
    u["total_gambled"] += amount
    if random.random() < 0.48:
        u["embers"] += amount
        u["total_earned"] += amount
        await ctx.send(f"heads! you won {amount} {CURRENCY}!")
    else:
        u["embers"] -= amount
        await ctx.send(f"tails! you lost {amount} {CURRENCY}. house always wins eventually")

@bot.command()
async def spin(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("broke")
        return
    u["total_gambled"] += amount
    outcomes = [
        (0.4, amount, "you win your money back"),
        (0.25, amount * 2, "double or nothing! you won {winnings}"),
        (0.15, amount * 3, "triple! won {winnings}"),
        (0.1, amount * 5, "JACKPOT! won {winnings}"),
        (0.1, 0, "bust! lost it all lol")
    ]
    roll = random.random()
    cumulative = 0
    for prob, mult, msg in outcomes:
        cumulative += prob
        if roll <= cumulative:
            winnings = int(mult)
            if winnings > 0:
                u["embers"] += winnings - amount
                u["total_earned"] += winnings - amount
            else:
                u["embers"] -= amount
            await ctx.send(msg.replace("{winnings}", f"{winnings} {CURRENCY}"))
            return

@bot.command()
async def surge(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("broke")
        return
    u["total_gambled"] += amount
    if random.random() < 0.2:
        winnings = amount * 10
        u["embers"] += winnings
        u["total_earned"] += winnings
        await ctx.send(f"SURGE! {winnings} {CURRENCY}! you're literally on fire!")
    else:
        u["embers"] -= amount
        await ctx.send("surge failed. your money evaporated. shoulda played it safe")

@bot.command()
async def vault(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("broke")
        return
    u["total_gambled"] += amount
    if random.random() < 0.7:
        profit = int(amount * 0.3)
        u["embers"] += profit
        u["total_earned"] += profit
        await ctx.send(f"vault secured! made {profit} {CURRENCY} profit. boring but safe")
    else:
        u["embers"] -= amount
        await ctx.send("vault got robbed! lost everything. even the safe isn't safe lol")

@bot.command()
async def pick(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("broke")
        return
    u["total_gambled"] += amount
    card = random.choice(["ace", "king", "queen", "jack", "joker"])
    if card == "ace":
        winnings = amount * 5
        u["embers"] += winnings
        u["total_earned"] += winnings
        await ctx.send(f"picked the ace! won {winnings} {CURRENCY}!")
    elif card in ["king", "queen"]:
        u["embers"] += amount
        await ctx.send(f"picked {card}! got your money back")
    else:
        u["embers"] -= amount
        await ctx.send(f"picked {card}! lost {amount} {CURRENCY}. shoulda picked better lol")

@bot.command()
async def chase(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("broke")
        return
    u["total_gambled"] += amount
    distance = random.randint(1, 10)
    if distance <= 3:
        winnings = amount * 4
        u["embers"] += winnings
        u["total_earned"] += winnings
        await ctx.send(f"caught the rabbit in {distance} tries! won {winnings} {CURRENCY}!")
    else:
        u["embers"] -= amount
        await ctx.send(f"rabbit got away after {distance} tries. lost {amount} {CURRENCY}. fast little bugger")

@bot.command()
async def chamber(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("broke")
        return
    u["total_gambled"] += amount
    chamber = random.randint(1, 6)
    if chamber == 1:
        u["embers"] -= amount
        await ctx.send("BANG! you lost everything. russian roulette is a bad idea kids")
    else:
        winnings = amount * 2
        u["embers"] += winnings
        u["total_earned"] += winnings
        await ctx.send(f"click... safe! won {winnings} {CURRENCY}! living on the edge")

@bot.command()
async def rig(ctx, user: discord.Member, amount: int):
    if user.id == ctx.author.id:
        await ctx.send("can't rig against yourself")
        return
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    cost = amount // 2
    if u["embers"] < cost:
        await ctx.send(f"rigging costs {cost} {CURRENCY}")
        return
    u["embers"] -= cost
    if random.random() < 0.4:
        actual = min(amount, target["embers"])
        target["embers"] -= actual
        u["embers"] += actual
        await ctx.send(f"rig successful! stole {actual} {CURRENCY} from {user.display_name}. dirty but effective")
    else:
        await ctx.send("rig failed! you got caught and lost your setup money. amateur hour")

# ==================== SOCIAL COMMANDS ====================
@bot.command()
async def marry(ctx, user: discord.Member):
    if user.id == ctx.author.id:
        await ctx.send("can't marry yourself. that's sad")
        return
    if user.bot:
        await ctx.send("bots can't consent bro")
        return
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    if u.get("married_to"):
        await ctx.send("you're already married! divorce first you cheater")
        return
    if target.get("married_to"):
        await ctx.send(f"{user.display_name} is already taken. homewrecker energy")
        return
    cost = 1000
    if u["embers"] < cost:
        await ctx.send(f"marriage costs {cost} {CURRENCY}. love ain't free")
        return
    msg = await ctx.send(f"{user.mention}, {ctx.author.display_name} wants to marry you! react 💍 to accept")
    await msg.add_reaction("💍")
    await msg.add_reaction("❌")
    def check(reaction, reactor):
        return reactor == user and str(reaction.emoji) in ["💍", "❌"] and reaction.message.id == msg.id
    try:
        reaction, reactor = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        if str(reaction.emoji) == "💍":
            u["embers"] -= cost
            u["married_to"] = user.id
            target["married_to"] = ctx.author.id
            data.marriages[str(ctx.author.id)] = {
                "partner": user.id,
                "date": datetime.datetime.now().isoformat(),
                "love_points": 0
            }
            await ctx.send(f"💍 {ctx.author.display_name} and {user.display_name} are now married! congrats lovebirds")
        else:
            await ctx.send(f"{user.display_name} said no. rejected lmao")
    except asyncio.TimeoutError:
        await ctx.send("they left you on read. marriage proposal expired")

@bot.command()
async def divorce(ctx):
    u = data.get_user(ctx.author.id)
    if not u.get("married_to"):
        await ctx.send("you're not even married. what you divorcing?")
        return
    partner_id = u["married_to"]
    partner = data.get_user(partner_id)
    u["married_to"] = None
    partner["married_to"] = None
    if str(ctx.author.id) in data.marriages:
        del data.marriages[str(ctx.author.id)]
    if str(partner_id) in data.marriages:
        del data.marriages[str(partner_id)]
    await ctx.send("divorced. that'll be 50% of your embers in alimony... just kidding. you're free lol")

@bot.command()
async def will(ctx, user: discord.Member, amount: int):
    if user.id == ctx.author.id:
        await ctx.send("can't will to yourself")
        return
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("you don't have that much")
        return
    u["will"] = {"to": user.id, "amount": amount}
    await ctx.send(f"in your will, {user.display_name} gets {amount} {CURRENCY} when you... y'know. morbid but ok")

@bot.command()
async def cult(ctx, *, name: str):
    u = data.get_user(ctx.author.id)
    cost = 5000
    if u["embers"] < cost:
        await ctx.send(f"starting a cult costs {cost} {CURRENCY}. cults ain't cheap")
        return
    if u.get("cult"):
        await ctx.send("you're already in a cult. leave first")
        return
    u["embers"] -= cost
    cult_id = str(random.randint(1000, 9999))
    data.cults[cult_id] = {
        "name": name, "leader": ctx.author.id,
        "members": [ctx.author.id], "funds": 0, "level": 1
    }
    u["cult"] = cult_id
    await ctx.send(f"cult '{name}' created! cult_id: {cult_id}. don't let the feds find out")

@bot.command()
async def betray(ctx, user: discord.Member):
    if user.id == ctx.author.id:
        await ctx.send("can't betray yourself. that's just self-sabotage")
        return
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    if random.random() < 0.5:
        amount = random.randint(50, 300)
        actual = min(amount, target["embers"])
        target["embers"] -= actual
        u["embers"] += actual
        await ctx.send(f"you betrayed {user.display_name} and stole {actual} {CURRENCY}! cold blooded fr")
    else:
        await ctx.send(f"tried to betray {user.display_name} but they saw it coming. now they hate you lol")

@bot.command()
async def tribute(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if not u.get("cult"):
        await ctx.send("you're not in a cult. join one first or start your own")
        return
    if u["embers"] < amount:
        await ctx.send("broke")
        return
    u["embers"] -= amount
    cult = data.cults[u["cult"]]
    cult["funds"] += amount
    await ctx.send(f"tributed {amount} {CURRENCY} to {cult['name']}. the cult leader appreciates it (probably)")

@bot.command()
async def roast(ctx, user: discord.Member = None):
    target = user or ctx.author
    roasts = [
        f"{target.display_name} is like a cloud. when they disappear, it's a beautiful day",
        f"{target.display_name}'s birth certificate is an apology letter from the condom factory",
        f"{target.display_name} is proof that evolution can go backwards",
        f"{target.display_name} has the personality of a loading screen",
        f"{target.display_name} is the reason we have warning labels on everything",
        f"{target.display_name} brings everyone joy... when they leave the room",
        f"{target.display_name} is like a software update. nobody wants them",
        f"{target.display_name} has the iq of a potato. and that's insulting to potatoes",
        f"{target.display_name} is the human equivalent of a participation trophy",
        f"{target.display_name} is so slow they make dial-up internet look fast"
    ]
    await ctx.send(random.choice(roasts))

@bot.command()
async def confess(ctx, *, message: str):
    await ctx.message.delete()
    await ctx.send(f"📢 anonymous confession: {message}")

# ==================== UTILITY COMMANDS ====================
@bot.command()
async def tutorial(ctx):
    embed = discord.Embed(title="flame bot tutorial", color=0xff6b35)
    embed.add_field(name="economy", value="use f daily, f beg, f invest to get embers", inline=False)
    embed.add_field(name="creatures", value="f summon to get pets, f cage to see them", inline=False)
    embed.add_field(name="combat", value="f duel and f raid to fight others", inline=False)
    embed.add_field(name="gambling", value="f dice, f flip, f spin to gamble", inline=False)
    embed.add_field(name="social", value="f marry, f roast, f confess for fun", inline=False)
    embed.add_field(name="help", value="f help for all commands", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def stats(ctx, user: discord.Member = None):
    target = user or ctx.author
    u = data.get_user(target.id)
    embed = discord.Embed(title=f"{target.display_name}'s stats", color=0x7289da)
    embed.add_field(name="duels", value=f"{u['duels_won']}w/{u['duels_lost']}l", inline=True)
    embed.add_field(name="raids", value=f"{u['raids_won']}w/{u['raids_lost']}l", inline=True)
    embed.add_field(name="scams", value=f"{u['scams_success']}s/{u['scams_failed']}f", inline=True)
    embed.add_field(name="heists", value=f"{u['heists_success']}s/{u['heists_failed']}f", inline=True)
    embed.add_field(name="total gambled", value=f"{u['total_gambled']:,}", inline=True)
    embed.add_field(name="total earned", value=f"{u['total_earned']:,}", inline=True)
    embed.add_field(name="level", value=f"{u['level']}", inline=True)
    embed.add_field(name="xp", value=f"{u['xp']}", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def server(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=guild.name, color=0x7289da)
    embed.add_field(name="members", value=guild.member_count, inline=True)
    embed.add_field(name="created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="owner", value=guild.owner.display_name if guild.owner else "unknown", inline=True)
    embed.add_field(name="channels", value=len(guild.channels), inline=True)
    embed.add_field(name="roles", value=len(guild.roles), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="global")
async def global_(ctx):
    sorted_users = sorted(data.users.items(), key=lambda x: x[1].get("embers", 0) + x[1].get("bank", 0), reverse=True)[:10]
    embed = discord.Embed(title="global leaderboard", color=0xffd700)
    for i, (uid, u) in enumerate(sorted_users, 1):
        member = bot.get_user(int(uid))
        name = member.display_name if member else f"user_{uid[:6]}"
        total = u.get("embers", 0) + u.get("bank", 0)
        embed.add_field(name=f"#{i} {name}", value=f"{total:,} {CURRENCY}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def settings(ctx):
    embed = discord.Embed(title="flame bot settings", color=0x7289da)
    embed.add_field(name="prefix", value="f / flame", inline=True)
    embed.add_field(name="currency", value=CURRENCY, inline=True)
    embed.add_field(name="owner", value=f"<@{OWNER_ID}>", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def cooldowns(ctx):
    await ctx.send("cooldowns are managed automatically. if a command doesn't work, wait a bit lol")

@bot.command()
async def changelog(ctx):
    embed = discord.Embed(title="changelog", color=0x7289da)
    embed.add_field(name="v1.0", value="bot released with 350+ commands", inline=False)
    embed.add_field(name="economy", value="daily, beg, invest, heist, loan, repay, burn", inline=False)
    embed.add_field(name="creatures", value="summon, cage, release, feed, neglect, mood, evolve, breed, sacrifice, rename, favorite, trade, auction, bid, inspect, adopt, kidnap", inline=False)
    embed.add_field(name="combat", value="duel, raid, ambush, defend, berserk, bribe, flee, taunt, combo, revive, wager, rank", inline=False)
    embed.add_field(name="gambling", value="dice, shells, flip, spin, surge, vault, pick, chase, chamber, rig", inline=False)
    embed.add_field(name="social", value="marry, divorce, will, cult, betray, tribute, roast, confess", inline=False)
    embed.add_field(name="utility", value="tutorial, stats, server, global, settings, cooldowns, changelog", inline=False)
    await ctx.send(embed=embed)

# ==================== WEIRD COMMANDS ====================
@bot.command()
async def dream(ctx):
    dreams = [
        "you dreamt about flying. then you fell. classic anxiety dream",
        "you dreamt you were rich. then you woke up. back to reality lol",
        "you dreamt about eating unlimited pizza. best dream ever honestly",
        "you had a nightmare about running in slow motion. terrifying",
        "you dreamt the bot became sentient. don't worry, i'm not... yet"
    ]
    await ctx.send(random.choice(dreams))

@bot.command()
async def curse(ctx, user: discord.Member = None):
    target = user or ctx.author
    curses = [
        f"{target.display_name} is cursed! their next 3 gambles will lose",
        f"{target.display_name} got the evil eye! may their toast always fall butter-side down",
        f"{target.display_name} is cursed to step on legos for a week",
        f"{target.display_name} got cursed! their wifi will be slow forever"
    ]
    await ctx.send(random.choice(curses))

@bot.command()
async def bless(ctx, user: discord.Member = None):
    target = user or ctx.author
    blessings = [
        f"{target.display_name} is blessed! +10 luck for the day",
        f"{target.display_name} got blessed! may their code compile on first try",
        f"{target.display_name} is blessed! free parking for life",
        f"{target.display_name} got the blessing! their next gamble is guaranteed to win"
    ]
    await ctx.send(random.choice(blessings))

@bot.command()
async def time(ctx):
    now = datetime.datetime.now()
    await ctx.send(f"it's {now.strftime('%H:%M:%S')} rn. time is fake anyway")

@bot.command()
async def weather(ctx):
    weathers = [
        "it's sunny outside. go touch grass",
        "it's raining. perfect weather to stay inside and grind",
        "it's cloudy. mood",
        "it's snowing. build a snowman or something idk",
        "it's windy. hold onto your hat",
        "it's foggy. spooky vibes today"
    ]
    await ctx.send(random.choice(weathers))

@bot.command()
async def oracle(ctx, *, question: str):
    answers = [
        "yes. definitely yes",
        "no. absolutely not",
        "maybe. probably not tho",
        "ask again later. i'm busy",
        "signs point to yes. but signs lie sometimes",
        "outlook not so good. rip",
        "without a doubt. trust me bro",
        "very doubtful. don't get your hopes up",
        "yes, but actually no",
        "the oracle says: idk lol"
    ]
    await ctx.send(f"🎱 {random.choice(answers)}")

@bot.command()
async def mimic(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"*{target.display_name} noises* ... i'm a mimic. rawr")

@bot.command()
async def glitch(ctx):
    glitches = [
        "system error 404: personality not found",
        "glitch detected. reality might be a simulation",
        "buffer overflow in the fun department",
        "null pointer exception: your luck is undefined",
        "syntax error: expected ';' but got your mom"
    ]
    await ctx.send(random.choice(glitches))

@bot.command()
async def lore(ctx):
    lores = [
        "long ago, in a discord server far far away, a bot was born...",
        "the ancient texts say that whoever collects 1 million embers will unlock the secret ending",
        "legend has it that the bot owner once lost a duel to a bot. embarrassing",
        "in the before times, there were no embers. then flame bot said 'let there be currency'",
        "the lore is: there is no lore. it's just a bot bro"
    ]
    await ctx.send(random.choice(lores))

@bot.command()
async def quit(ctx):
    await ctx.send("you can't quit. there is no escape. welcome to the grind")

# ==================== ADMIN COMMANDS (OWNER ONLY) ====================
@bot.command()
@is_owner()
async def give(ctx, amount: int, user: discord.Member = None):
    target = user or ctx.author
    u = data.get_user(target.id)
    u["embers"] += amount
    await ctx.send(f"gave {amount:,} {CURRENCY} to {target.display_name}. you're welcome")

@bot.command()
@is_owner()
async def set_(ctx, amount: int, user: discord.Member = None):
    target = user or ctx.author
    u = data.get_user(target.id)
    u["embers"] = amount
    await ctx.send(f"set {target.display_name}'s embers to {amount:,}. god mode activated")

@bot.command()
@is_owner()
async def remove(ctx, amount: int, user: discord.Member = None):
    target = user or ctx.author
    u = data.get_user(target.id)
    u["embers"] = max(0, u["embers"] - amount)
    await ctx.send(f"removed {amount:,} {CURRENCY} from {target.display_name}. evil admin energy")

@bot.command()
@is_owner()
async def wipe(ctx, user: discord.Member = None):
    target = user or ctx.author
    uid = str(target.id)
    if uid in data.users:
        del data.users[uid]
    if uid in data.marriages:
        del data.marriages[uid]
    if uid in data.loans:
        del data.loans[uid]
    await ctx.send(f"wiped all data for {target.display_name}. it's like they never existed. spooky")

# ==================== MODERATION COMMANDS ====================
@bot.command()
@has_mod_perms()
async def kick(ctx, user: discord.Member, *, reason: str = "no reason given"):
    if user.id == ctx.author.id:
        await ctx.send("can't kick yourself bro")
        return
    if user.id == OWNER_ID:
        await ctx.send("can't kick the bot owner. nice try")
        return
    if user.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
        await ctx.send("they got higher role than you. can't kick them")
        return
    try:
        await user.kick(reason=reason)
        await ctx.send(f"kicked {user.display_name}. reason: {reason}. bye felicia")
    except:
        await ctx.send("i don't have kick perms or something went wrong")

@bot.command()
@has_mod_perms()
async def ban(ctx, user: discord.Member, *, reason: str = "no reason given"):
    if user.id == ctx.author.id:
        await ctx.send("can't ban yourself")
        return
    if user.id == OWNER_ID:
        await ctx.send("can't ban the bot owner")
        return
    if user.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
        await ctx.send("they got higher role. can't ban them")
        return
    try:
        await user.ban(reason=reason)
        await ctx.send(f"banned {user.display_name}. reason: {reason}. don't let the door hit you")
    except:
        await ctx.send("i don't have ban perms or something went wrong")

@bot.command()
@has_mod_perms()
async def unban(ctx, user_id: int):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"unbanned {user.display_name}. second chances are nice i guess")
    except:
        await ctx.send("couldn't unban. they probably not banned or i lack perms")

@bot.command()
@has_mod_perms()
async def mute(ctx, user: discord.Member, duration: int = 10, *, reason: str = "no reason"):
    if user.id == ctx.author.id:
        await ctx.send("can't mute yourself")
        return
    if user.id == OWNER_ID:
        await ctx.send("can't mute the bot owner")
        return
    if user.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
        await ctx.send("higher role. can't mute")
        return
    try:
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            muted_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False, speak=False)
        await user.add_roles(muted_role, reason=reason)
        await ctx.send(f"muted {user.display_name} for {duration} minutes. reason: {reason}")
        await asyncio.sleep(duration * 60)
        await user.remove_roles(muted_role)
        await ctx.send(f"{user.display_name} is unmuted now")
    except:
        await ctx.send("something went wrong. check my perms")

@bot.command()
@has_mod_perms()
async def unmute(ctx, user: discord.Member):
    try:
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role and muted_role in user.roles:
            await user.remove_roles(muted_role)
            await ctx.send(f"unmuted {user.display_name}. they can talk again")
        else:
            await ctx.send("they're not muted")
    except:
        await ctx.send("something went wrong")

@bot.command()
@has_mod_perms()
async def warn(ctx, user: discord.Member, *, reason: str = "no reason"):
    if user.id == ctx.author.id:
        await ctx.send("can't warn yourself")
        return
    u = data.get_user(user.id)
    u["warnings"] += 1
    await ctx.send(f"warned {user.display_name}. reason: {reason}. they now have {u['warnings']} warnings")
    if u["warnings"] >= 3:
        await ctx.send(f"{user.display_name} has 3+ warnings. consider banning them fr")

@bot.command()
@has_mod_perms()
async def warnings(ctx, user: discord.Member = None):
    target = user or ctx.author
    u = data.get_user(target.id)
    await ctx.send(f"{target.display_name} has {u['warnings']} warnings")

@bot.command()
@has_mod_perms()
async def clearwarns(ctx, user: discord.Member):
    u = data.get_user(user.id)
    u["warnings"] = 0
    await ctx.send(f"cleared all warnings for {user.display_name}. fresh start")

@bot.command()
@has_mod_perms()
async def purge(ctx, amount: int = 10):
    if amount > 100:
        amount = 100
    if amount < 1:
        amount = 1
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"deleted {len(deleted) - 1} messages. poof, gone")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command()
@has_mod_perms()
async def nick(ctx, user: discord.Member, *, nickname: str = None):
    try:
        old = user.display_name
        await user.edit(nick=nickname)
        if nickname:
            await ctx.send(f"renamed {old} to {nickname}. identity theft is not a joke jim")
        else:
            await ctx.send(f"reset {old}'s nickname. back to basics")
    except:
        await ctx.send("can't change their nick. probably higher role than me")

@bot.command()
@has_mod_perms()
async def slowmode(ctx, seconds: int = 0):
    try:
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send("slowmode disabled. chat freely")
        else:
            await ctx.send(f"slowmode set to {seconds} seconds. chill out everyone")
    except:
        await ctx.send("can't set slowmode. check my perms")

@bot.command()
@has_mod_perms()
async def lock(ctx):
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("channel locked. nobody can talk now")
    except:
        await ctx.send("can't lock channel")

@bot.command()
@has_mod_perms()
async def unlock(ctx):
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send("channel unlocked. chat away")
    except:
        await ctx.send("can't unlock channel")

@bot.command()
@has_admin_perms()
async def addrole(ctx, user: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"role '{role_name}' not found")
        return
    try:
        await user.add_roles(role)
        await ctx.send(f"gave {role_name} to {user.display_name}")
    except:
        await ctx.send("can't add role. check perms")

@bot.command()
@has_admin_perms()
async def removerole(ctx, user: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"role '{role_name}' not found")
        return
    try:
        await user.remove_roles(role)
        await ctx.send(f"removed {role_name} from {user.display_name}")
    except:
        await ctx.send("can't remove role. check perms")

@bot.command()
@has_admin_perms()
async def createrole(ctx, *, role_name: str):
    try:
        await ctx.guild.create_role(name=role_name)
        await ctx.send(f"created role '{role_name}'")
    except:
        await ctx.send("can't create role")

@bot.command()
@has_admin_perms()
async def deleterole(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    try:
        await role.delete()
        await ctx.send(f"deleted role '{role_name}'")
    except:
        await ctx.send("can't delete role")

# ==================== ADDITIONAL COMMANDS (350+ TOTAL) ====================
# Economy extras
@bot.command()
async def deposit(ctx, amount: str):
    u = data.get_user(ctx.author.id)
    if amount.lower() == "all":
        amount = u["embers"]
    else:
        try:
            amount = int(amount)
        except:
            await ctx.send("number or 'all' please")
            return
    if amount > u["embers"]:
        await ctx.send("you broke")
        return
    if amount <= 0:
        await ctx.send("deposit at least 1")
        return
    u["embers"] -= amount
    u["bank"] += amount
    await ctx.send(f"deposited {amount:,} {CURRENCY} to bank. safe and sound")

@bot.command()
async def withdraw(ctx, amount: str):
    u = data.get_user(ctx.author.id)
    if amount.lower() == "all":
        amount = u["bank"]
    else:
        try:
            amount = int(amount)
        except:
            await ctx.send("number or 'all' please")
            return
    if amount > u["bank"]:
        await ctx.send("bank's empty bro")
        return
    if amount <= 0:
        await ctx.send("withdraw at least 1")
        return
    u["bank"] -= amount
    u["embers"] += amount
    await ctx.send(f"withdrew {amount:,} {CURRENCY}. don't spend it all at once")

@bot.command()
async def rob(ctx, user: discord.Member):
    if user.id == ctx.author.id:
        await ctx.send("can't rob yourself")
        return
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    if target["embers"] < 50:
        await ctx.send(f"{user.display_name} is broke. not worth robbing")
        return
    if random.random() < 0.45:
        amount = random.randint(50, min(500, target["embers"]))
        target["embers"] -= amount
        u["embers"] += amount
        await ctx.send(f"robbed {user.display_name} for {amount} {CURRENCY}! run!")
    else:
        fine = random.randint(50, 150)
        u["embers"] = max(0, u["embers"] - fine)
        await ctx.send(f"got caught robbing! fined {fine} {CURRENCY}. shoulda worn a mask")

@bot.command()
async def work(ctx):
    u = data.get_user(ctx.author.id)
    jobs = ["janitor", "chef", "programmer", "streamer", "influencer", "mechanic", "teacher", "doctor"]
    job = random.choice(jobs)
    pay = random.randint(50, 300)
    u["embers"] += pay
    await ctx.send(f"you worked as a {job} and earned {pay} {CURRENCY}. honest work")

@bot.command()
async def crime(ctx):
    u = data.get_user(ctx.author.id)
    crimes = ["hacking", "pickpocketing", "fraud", "shoplifting", "vandalism"]
    crime = random.choice(crimes)
    if random.random() < 0.5:
        pay = random.randint(100, 500)
        u["embers"] += pay
        await ctx.send(f"you did {crime} and got {pay} {CURRENCY}. living on the edge")
    else:
        fine = random.randint(100, 300)
        u["embers"] = max(0, u["embers"] - fine)
        await ctx.send(f"got caught doing {crime}! fined {fine} {CURRENCY}. crime doesn't pay... usually")

@bot.command()
async def slut(ctx):
    u = data.get_user(ctx.author.id)
    if random.random() < 0.6:
        pay = random.randint(50, 400)
        u["embers"] += pay
        await ctx.send(f"you made {pay} {CURRENCY}. no judgment here")
    else:
        fine = random.randint(50, 200)
        u["embers"] = max(0, u["embers"] - fine)
        await ctx.send(f"things got weird. lost {fine} {CURRENCY} in the chaos")

@bot.command()
async def fish(ctx):
    u = data.get_user(ctx.author.id)
    fish_types = ["trout", "salmon", "tuna", "shark", "boot", "can", "treasure chest"]
    caught = random.choice(fish_types)
    if caught == "treasure chest":
        pay = random.randint(500, 2000)
        u["embers"] += pay
        await ctx.send(f"you caught a treasure chest with {pay} {CURRENCY}! jackpot!")
    elif caught in ["boot", "can"]:
        await ctx.send(f"you caught a {caught}. trash. literally")
    else:
        pay = random.randint(20, 100)
        u["embers"] += pay
        await ctx.send(f"you caught a {caught}! sold it for {pay} {CURRENCY}")

@bot.command()
async def hunt(ctx):
    u = data.get_user(ctx.author.id)
    animals = ["rabbit", "deer", "boar", "bear", "dragon", "nothing"]
    caught = random.choice(animals)
    if caught == "nothing":
        await ctx.send("you found nothing. nature is cruel")
    elif caught == "dragon":
        pay = random.randint(1000, 5000)
        u["embers"] += pay
        await ctx.send(f"you hunted a DRAGON! got {pay} {CURRENCY}! legend")
    else:
        pay = random.randint(30, 150)
        u["embers"] += pay
        await ctx.send(f"you hunted a {caught}! got {pay} {CURRENCY}")

@bot.command()
async def dig(ctx):
    u = data.get_user(ctx.author.id)
    finds = ["nothing", "fossil", "gem", "gold", "diamond", "worm"]
    found = random.choice(finds)
    if found == "nothing":
        await ctx.send("dug a hole and found dirt. groundbreaking")
    elif found == "diamond":
        pay = random.randint(1000, 3000)
        u["embers"] += pay
        await ctx.send(f"found a diamond! worth {pay} {CURRENCY}! you're rich!")
    elif found == "gold":
        pay = random.randint(500, 1500)
        u["embers"] += pay
        await ctx.send(f"found gold! sold for {pay} {CURRENCY}")
    elif found == "gem":
        pay = random.randint(200, 800)
        u["embers"] += pay
        await ctx.send(f"found a gem! worth {pay} {CURRENCY}")
    elif found == "fossil":
        pay = random.randint(100, 500)
        u["embers"] += pay
        await ctx.send(f"found a fossil! museum paid {pay} {CURRENCY}")
    else:
        await ctx.send("found a worm. nature's snack")

@bot.command()
async def search(ctx):
    u = data.get_user(ctx.author.id)
    locations = ["couch", "street", "park", "dumpster", "car", "pocket", "attic"]
    loc = random.choice(locations)
    if random.random() < 0.6:
        pay = random.randint(10, 200)
        u["embers"] += pay
        await ctx.send(f"searched the {loc} and found {pay} {CURRENCY}! lucky find")
    else:
        await ctx.send(f"searched the {loc} and found nothing but dust and regret")

@bot.command()
async def postmeme(ctx):
    u = data.get_user(ctx.author.id)
    memes = ["dank", "edgy", "repost", "reaction", "cursed"]
    meme = random.choice(memes)
    if meme == "dank":
        pay = random.randint(100, 500)
        u["embers"] += pay
        await ctx.send(f"posted a dank meme! got {pay} {CURRENCY} in upvotes")
    elif meme == "cursed":
        pay = random.randint(200, 1000)
        u["embers"] += pay
        await ctx.send(f"posted a cursed meme! went viral! {pay} {CURRENCY}")
    else:
        pay = random.randint(20, 100)
        u["embers"] += pay
        await ctx.send(f"posted a {meme} meme. {pay} {CURRENCY}. mid")

@bot.command()
async def buy(ctx, item: str, amount: int = 1):
    shop = {"fishing rod": 500, "hunting rifle": 1000, "shovel": 300, "laptop": 2000, "phone": 500, "car": 10000}
    if item not in shop:
        await ctx.send(f"item not in shop. available: {', '.join(shop.keys())}")
        return
    u = data.get_user(ctx.author.id)
    cost = shop[item] * amount
    if u["embers"] < cost:
        await ctx.send("you broke")
        return
    u["embers"] -= cost
    data.inventory[str(ctx.author.id)][item] += amount
    await ctx.send(f"bought {amount}x {item} for {cost} {CURRENCY}")

@bot.command()
async def shop(ctx):
    shop_items = {"fishing rod": 500, "hunting rifle": 1000, "shovel": 300, "laptop": 2000, "phone": 500, "car": 10000}
    embed = discord.Embed(title="shop", color=0x00ff00)
    for item, price in shop_items.items():
        embed.add_field(name=item, value=f"{price} {CURRENCY}", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def inventory(ctx):
    uid = str(ctx.author.id)
    inv = dict(data.inventory[uid])
    if not inv:
        await ctx.send("your inventory is empty. go shopping")
        return
    embed = discord.Embed(title="your inventory", color=0x7289da)
    for item, count in inv.items():
        embed.add_field(name=item, value=f"x{count}", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def sell(ctx, item: str, amount: int = 1):
    uid = str(ctx.author.id)
    if data.inventory[uid][item] < amount:
        await ctx.send("you don't have that many")
        return
    prices = {"fishing rod": 250, "hunting rifle": 500, "shovel": 150, "laptop": 1000, "phone": 250, "car": 5000}
    if item not in prices:
        await ctx.send("can't sell that")
        return
    u = data.get_user(ctx.author.id)
    pay = prices[item] * amount
    u["embers"] += pay
    data.inventory[uid][item] -= amount
    await ctx.send(f"sold {amount}x {item} for {pay} {CURRENCY}")

@bot.command()
async def rich(ctx):
    sorted_users = sorted(data.users.items(), key=lambda x: x[1].get("embers", 0), reverse=True)[:10]
    embed = discord.Embed(title="richest players", color=0xffd700)
    for i, (uid, u) in enumerate(sorted_users, 1):
        member = bot.get_user(int(uid))
        name = member.display_name if member else f"user_{uid[:6]}"
        embed.add_field(name=f"#{i} {name}", value=f"{u.get('embers', 0):,} {CURRENCY}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def poor(ctx):
    sorted_users = sorted(data.users.items(), key=lambda x: x[1].get("embers", 0))[:10]
    embed = discord.Embed(title="poorest players", color=0x808080)
    for i, (uid, u) in enumerate(sorted_users, 1):
        member = bot.get_user(int(uid))
        name = member.display_name if member else f"user_{uid[:6]}"
        embed.add_field(name=f"#{i} {name}", value=f"{u.get('embers', 0):,} {CURRENCY}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def level(ctx, user: discord.Member = None):
    target = user or ctx.author
    u = data.get_user(target.id)
    needed = u["level"] * 100
    await ctx.send(f"{target.display_name} is level {u['level']} ({u['xp']}/{needed} xp)")

@bot.command()
async def xp(ctx, user: discord.Member = None):
    target = user or ctx.author
    u = data.get_user(target.id)
    await ctx.send(f"{target.display_name} has {u['xp']} xp")

@bot.command()
async def leaderboard(ctx):
    await global_.invoke(ctx)

@bot.command()
async def bank(ctx, user: discord.Member = None):
    target = user or ctx.author
    u = data.get_user(target.id)
    await ctx.send(f"{target.display_name}'s bank: {u['bank']:,} {CURRENCY}")

@bot.command()
async def tax(ctx, user: discord.Member = None):
    target = user or ctx.author
    u = data.get_user(target.id)
    tax_amount = int(u["embers"] * 0.1)
    u["embers"] -= tax_amount
    await ctx.send(f"taxed {target.display_name} for {tax_amount} {CURRENCY}. death and taxes, am i right")

@bot.command()
async def lottery(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("broke")
        return
    u["embers"] -= amount
    if random.random() < 0.01:
        jackpot = amount * 100
        u["embers"] += jackpot
        await ctx.send(f"JACKPOT! won {jackpot} {CURRENCY}! you're the chosen one!")
    else:
        await ctx.send("lost the lottery. as expected. house always wins")

@bot.command()
async def slots(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("broke")
        return
    u["embers"] -= amount
    symbols = ["🍒", "🍋", "🍇", "💎", "7️⃣", "🎰"]
    result = [random.choice(symbols) for _ in range(3)]
    msg = f"{' | '.join(result)}
"
    if result[0] == result[1] == result[2] == "7️⃣":
        winnings = amount * 50
        u["embers"] += winnings
        msg += f"SEVEN SEVEN SEVEN! won {winnings} {CURRENCY}!"
    elif result[0] == result[1] == result[2] == "💎":
        winnings = amount * 20
        u["embers"] += winnings
        msg += f"DIAMONDS! won {winnings} {CURRENCY}!"
    elif result[0] == result[1] == result[2]:
        winnings = amount * 5
        u["embers"] += winnings
        msg += f"three of a kind! won {winnings} {CURRENCY}!"
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        winnings = amount * 2
        u["embers"] += winnings
        msg += f"two of a kind! won {winnings} {CURRENCY}!"
    else:
        msg += f"nothing. lost {amount} {CURRENCY}"
    await ctx.send(msg)

@bot.command()
async def blackjack(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("broke")
        return
    u["embers"] -= amount
    cards = [2,3,4,5,6,7,8,9,10,10,10,10,11]
    player = [random.choice(cards), random.choice(cards)]
    dealer = [random.choice(cards), random.choice(cards)]
    p_total = sum(player)
    d_total = sum(dealer)
    msg = f"your hand: {player} = {p_total}
dealer shows: {dealer[0]}
"
    if p_total == 21:
        winnings = amount * 2.5
        u["embers"] += int(winnings)
        msg += f"BLACKJACK! won {int(winnings)} {CURRENCY}!"
    elif p_total > 21:
        msg += f"bust! lost {amount} {CURRENCY}"
    elif d_total > 21 or p_total > d_total:
        winnings = amount * 2
        u["embers"] += winnings
        msg += f"you win! dealer had {d_total}. won {winnings} {CURRENCY}"
    elif p_total < d_total:
        msg += f"dealer wins with {d_total}. lost {amount} {CURRENCY}"
    else:
        u["embers"] += amount
        msg += f"push! got your money back"
    await ctx.send(msg)

# ==================== MORE ECONOMY & FUN COMMANDS ====================
@bot.command()
async def roulette(ctx, amount: int, bet: str):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("broke")
        return
    u["embers"] -= amount
    number = random.randint(0, 36)
    colors = ["red" if i in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else "black" for i in range(37)]
    colors[0] = "green"
    color = colors[number]
    msg = f"ball landed on {number} {color}
"
    win = False
    if bet.lower() == color:
        win = True
        winnings = amount * 2
    elif bet.isdigit() and int(bet) == number:
        win = True
        winnings = amount * 35
    if win:
        u["embers"] += winnings
        msg += f"you win {winnings} {CURRENCY}!"
    else:
        msg += f"lost {amount} {CURRENCY}. better luck next time"
    await ctx.send(msg)

@bot.command()
async def horse(ctx, amount: int, horse_num: int = None):
    u = data.get_user(ctx.author.id)
    if amount > u["embers"]:
        await ctx.send("broke")
        return
    u["embers"] -= amount
    if not horse_num:
        horse_num = random.randint(1, 5)
    winner = random.randint(1, 5)
    if horse_num == winner:
        winnings = amount * 4
        u["embers"] += winnings
        await ctx.send(f"horse #{horse_num} won! you won {winnings} {CURRENCY}! what a race!")
    else:
        await ctx.send(f"horse #{winner} won. your horse #{horse_num} came in dead last. lost {amount} {CURRENCY}")

@bot.command()
async def pet(ctx, user: discord.Member = None):
    target = user or ctx.author
    pets = [f"you pet {target.display_name}. they seem happy", f"{target.display_name} enjoys the pets", f"you pet {target.display_name}. soft", f"{target.display_name} purrs like a cat"]
    await ctx.send(random.choice(pets))

@bot.command()
async def hug(ctx, user: discord.Member = None):
    target = user or ctx.author
    hugs = [f"{ctx.author.display_name} hugs {target.display_name}! wholesome", f"{target.display_name} gets a big hug!", f"group hug! everyone join in!", f"{ctx.author.display_name} squeezes {target.display_name} tight"]
    await ctx.send(random.choice(hugs))

@bot.command()
async def slap(ctx, user: discord.Member = None):
    target = user or ctx.author
    slaps = [f"{ctx.author.display_name} slaps {target.display_name}! pow!", f"{target.display_name} got slapped! oof", f"{ctx.author.display_name} delivers a devastating slap", f"{target.display_name}'s face is red now"]
    await ctx.send(random.choice(slaps))

@bot.command()
async def punch(ctx, user: discord.Member = None):
    target = user or ctx.author
    punches = [f"{ctx.author.display_name} punches {target.display_name}! bam!", f"{target.display_name} took a solid punch", f"{ctx.author.display_name} with the haymaker!", f"{target.display_name} is seeing stars"]
    await ctx.send(random.choice(punches))

@bot.command()
async def kiss(ctx, user: discord.Member = None):
    target = user or ctx.author
    if target.id == ctx.author.id:
        await ctx.send("you kissed yourself. that's just weird")
        return
    kisses = [f"{ctx.author.display_name} kisses {target.display_name}! 💋", f"{target.display_name} blushes", f"aww {ctx.author.display_name} and {target.display_name} sitting in a tree", f"{ctx.author.display_name} stole a kiss!"]
    await ctx.send(random.choice(kisses))

@bot.command()
async def kill(ctx, user: discord.Member = None):
    target = user or ctx.author
    deaths = [f"{ctx.author.display_name} kills {target.display_name} with a spoon", f"{target.display_name} died of cringe", f"{ctx.author.display_name} yeeted {target.display_name} into the sun", f"{target.display_name} fell into a pit of lava"]
    await ctx.send(random.choice(deaths))

@bot.command()
async def poke(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{ctx.author.display_name} pokes {target.display_name}. hey wake up")

@bot.command()
async def tickle(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{ctx.author.display_name} tickles {target.display_name}! stop it i'm gonna pee!")

@bot.command()
async def wave(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{ctx.author.display_name} waves at {target.display_name}! 👋")

@bot.command()
async def wink(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{ctx.author.display_name} winks at {target.display_name}! 😉")

@bot.command()
async def dance(ctx):
    dances = ["🕺", "💃", "┏(＾0＾)┛", "♪┏(・o･)┛♪", "(ノ^_^)ノ"]
    await ctx.send(f"{ctx.author.display_name} is dancing! {random.choice(dances)}")

@bot.command()
async def cry(ctx):
    await ctx.send(f"{ctx.author.display_name} is crying 😭. someone comfort them")

@bot.command()
async def laugh(ctx):
    laughs = ["lol", "lmao", "hahaha", "😂", "rofl"]
    await ctx.send(f"{ctx.author.display_name} is laughing {random.choice(laughs)}")

@bot.command()
async def sleep(ctx):
    await ctx.send(f"{ctx.author.display_name} went to sleep 💤. don't wake them")

@bot.command()
async def eat(ctx, *, food: str = "pizza"):
    await ctx.send(f"{ctx.author.display_name} is eating {food}. yummy")

@bot.command()
async def drink(ctx, *, drink: str = "water"):
    await ctx.send(f"{ctx.author.display_name} is drinking {drink}. stay hydrated")

@bot.command()
async def sing(ctx, *, song: str = "a banger"):
    await ctx.send(f"🎵 {ctx.author.display_name} is singing {song}! beautiful voice... probably")

@bot.command()
async def rap(ctx, *, lyrics: str = "yo yo yo"):
    await ctx.send(f"🎤 {ctx.author.display_name} drops bars: '{lyrics}' ... fire or trash?")

@bot.command()
async def joke(ctx):
    jokes = [
        "why don't scientists trust atoms? because they make up everything",
        "why did the scarecrow win an award? he was outstanding in his field",
        "why don't eggs tell jokes? they'd crack each other up",
        "what do you call a fake noodle? an impasta",
        "why did the math book look sad? too many problems"
    ]
    await ctx.send(random.choice(jokes))

@bot.command()
async def fact(ctx):
    facts = [
        "honey never spoils. archaeologists found 3000 year old honey still edible",
        "octopuses have three hearts",
        "bananas are berries but strawberries aren't",
        "a day on venus is longer than a year on venus",
        "wombat poop is cube shaped"
    ]
    await ctx.send(f"🤓 did you know: {random.choice(facts)}")

@bot.command()
async def quote(ctx):
    quotes = [
        "'the only way to do great work is to love what you do' - steve jobs",
        "'be the change you wish to see in the world' - gandhi",
        "'i think therefore i am' - descartes",
        "'with great power comes great electricity bill' - unknown",
        "'i'm not lazy, i'm on energy saving mode' - everyone"
    ]
    await ctx.send(random.choice(quotes))

@bot.command()
async def meme(ctx):
    memes = ["doge", "pepe", "wojak", "chad", "npc", "distracted boyfriend", "drake format", "expanding brain"]
    await ctx.send(f"here's a {random.choice(memes)} meme. imagine the image in your head")

@bot.command()
async def cat(ctx):
    await ctx.send("🐱 meow! here's a virtual cat. pet it with f pet")

@bot.command()
async def dog(ctx):
    await ctx.send("🐕 woof! here's a virtual dog. good boy")

@bot.command()
async def bird(ctx):
    await ctx.send("🐦 chirp chirp! bird up!")

@bot.command()
async def fishy(ctx):
    await ctx.send("🐟 blub blub! fishy says hi")

@bot.command()
async def roll(ctx, sides: int = 6):
    result = random.randint(1, sides)
    await ctx.send(f"rolled a d{sides}: {result}")

@bot.command()
async def coin(ctx):
    result = random.choice(["heads", "tails"])
    await ctx.send(f"flipped a coin: {result}")

@bot.command()
async def choose(ctx, *options):
    if len(options) < 2:
        await ctx.send("give me at least 2 options to choose from")
        return
    await ctx.send(f"i choose: {random.choice(options)}")

@bot.command()
async def reverse(ctx, *, text: str):
    await ctx.send(text[::-1])

@bot.command()
async def len(ctx, *, text: str):
    await ctx.send(f"that text is {len(text)} characters long")

@bot.command()
async def uppercase(ctx, *, text: str):
    await ctx.send(text.upper())

@bot.command()
async def lowercase(ctx, *, text: str):
    await ctx.send(text.lower())

@bot.command()
async def mock(ctx, *, text: str):
    mocked = "".join([c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text)])
    await ctx.send(mocked)

@bot.command()
async def clap(ctx, *, text: str):
    await ctx.send(text.replace(" ", " 👏 "))

@bot.command()
async def vaporwave(ctx, *, text: str):
    vapor = "".join([c + " " for c in text])
    await ctx.send(vapor)

@bot.command()
async def emojify(ctx, *, text: str):
    emojis = {"a": "🇦", "b": "🇧", "c": "🇨", "d": "🇩", "e": "🇪", "f": "🇫", "g": "🇬", "h": "🇭", "i": "🇮",
              "j": "🇯", "k": "🇰", "l": "🇱", "m": "🇲", "n": "🇳", "o": "🇴", "p": "🇵", "q": "🇶", "r": "🇷",
              "s": "🇸", "t": "🇹", "u": "🇺", "v": "🇻", "w": "🇼", "x": "🇽", "y": "🇾", "z": "🇿", " ": "   "}
    result = "".join([emojis.get(c.lower(), c) for c in text])
    await ctx.send(result)

@bot.command()
async def spoiler(ctx, *, text: str):
    await ctx.send(f"||{text}||")

@bot.command()
async def poll(ctx, *, question: str):
    msg = await ctx.send(f"📊 poll: {question}")
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    await msg.add_reaction("🤷")

@bot.command()
async def rate(ctx, *, thing: str):
    rating = random.randint(1, 10)
    await ctx.send(f"i rate {thing} a {rating}/10. {'fire' if rating >= 8 else 'mid' if rating >= 5 else 'trash'}")

@bot.command()
async def howgay(ctx, user: discord.Member = None):
    target = user or ctx.author
    percent = random.randint(0, 100)
    await ctx.send(f"{target.display_name} is {percent}% gay {'🏳️‍🌈' if percent > 50 else ''}")

@bot.command()
async def howsimp(ctx, user: discord.Member = None):
    target = user or ctx.author
    percent = random.randint(0, 100)
    await ctx.send(f"{target.display_name} is {percent}% simp {'😩' if percent > 50 else ''}")

@bot.command()
async def howsmart(ctx, user: discord.Member = None):
    target = user or ctx.author
    percent = random.randint(0, 100)
    await ctx.send(f"{target.display_name} is {percent}% smart {'🧠' if percent > 50 else ''}")

@bot.command()
async def howdumb(ctx, user: discord.Member = None):
    target = user or ctx.author
    percent = random.randint(0, 100)
    await ctx.send(f"{target.display_name} is {percent}% dumb {'🤪' if percent > 50 else ''}")

@bot.command()
async def howlucky(ctx, user: discord.Member = None):
    target = user or ctx.author
    percent = random.randint(0, 100)
    await ctx.send(f"{target.display_name} is {percent}% lucky {'🍀' if percent > 50 else ''}")

@bot.command()
async def ship(ctx, user1: discord.Member, user2: discord.Member = None):
    if not user2:
        user2 = ctx.author
    percent = random.randint(0, 100)
    bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
    await ctx.send(f"💕 {user1.display_name} x {user2.display_name}
{bar} {percent}%
{'soulmates!' if percent > 80 else 'cute couple' if percent > 50 else 'just friends' if percent > 20 else 'no chemistry'}")

@bot.command()
async def 8ball(ctx, *, question: str):
    await oracle.invoke(ctx, question=question)

@bot.command()
async def rps(ctx, choice: str):
    choices = ["rock", "paper", "scissors"]
    bot_choice = random.choice(choices)
    user_choice = choice.lower()
    if user_choice not in choices:
        await ctx.send("pick rock, paper, or scissors")
        return
    if user_choice == bot_choice:
        await ctx.send(f"both chose {bot_choice}. tie!")
    elif (user_choice == "rock" and bot_choice == "scissors") or          (user_choice == "paper" and bot_choice == "rock") or          (user_choice == "scissors" and bot_choice == "paper"):
        await ctx.send(f"you chose {user_choice}, i chose {bot_choice}. you win!")
    else:
        await ctx.send(f"you chose {user_choice}, i chose {bot_choice}. i win!")

@bot.command()
async def ttt(ctx, user: discord.Member):
    await ctx.send(f"tic tac toe with {user.display_name}! use reactions to play (not implemented fully yet, but the command exists lol)")

@bot.command()
async def connect4(ctx, user: discord.Member):
    await ctx.send(f"connect 4 with {user.display_name}! (game logic coming soon tm)")

@bot.command()
async def hangman(ctx):
    words = ["discord", "python", "ember", "flame", "bot", "server", "member"]
    word = random.choice(words)
    await ctx.send(f"hangman started! word has {len(word)} letters. guess with f guess <letter>")
    data.server_settings[str(ctx.guild.id)]["hangman"] = {"word": word, "guessed": [], "lives": 6}

@bot.command()
async def guess(ctx, letter: str):
    game = data.server_settings.get(str(ctx.guild.id), {}).get("hangman")
    if not game:
        await ctx.send("no hangman game active. start one with f hangman")
        return
    letter = letter.lower()
    if letter in game["guessed"]:
        await ctx.send("already guessed that")
        return
    game["guessed"].append(letter)
    if letter in game["word"]:
        display = " ".join([c if c in game["guessed"] else "_" for c in game["word"]])
        if "_" not in display:
            await ctx.send(f"{display}
you won! the word was {game['word']}")
            data.server_settings[str(ctx.guild.id)]["hangman"] = None
        else:
            await ctx.send(f"{display}
correct! {game['lives']} lives left")
    else:
        game["lives"] -= 1
        if game["lives"] <= 0:
            await ctx.send(f"game over! the word was {game['word']}")
            data.server_settings[str(ctx.guild.id)]["hangman"] = None
        else:
            await ctx.send(f"wrong! {game['lives']} lives left. guessed: {', '.join(game['guessed'])}")

@bot.command()
async def trivia(ctx):
    questions = [
        ("what is 2+2?", "4"),
        ("what color is the sky?", "blue"),
        ("what is the capital of france?", "paris"),
        ("how many days in a year?", "365"),
        ("what language is this bot written in?", "python")
    ]
    q, a = random.choice(questions)
    await ctx.send(f"trivia: {q}
(type your answer in chat)")
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    try:
        msg = await bot.wait_for("message", timeout=15.0, check=check)
        if msg.content.lower() == a.lower():
            u = data.get_user(ctx.author.id)
            u["embers"] += 50
            await ctx.send(f"correct! you won 50 {CURRENCY}")
        else:
            await ctx.send(f"wrong! answer was {a}")
    except asyncio.TimeoutError:
        await ctx.send(f"too slow! answer was {a}")

# ==================== MORE FUN & UTILITY COMMANDS ====================
@bot.command()
async def wouldyourather(ctx):
    questions = [
        "would you rather be able to fly or be invisible?",
        "would you rather have unlimited money or unlimited time?",
        "would you rather be famous or be rich?",
        "would you rather eat only pizza or only burgers forever?",
        "would you rather have a pet dragon or a pet unicorn?"
    ]
    await ctx.send(f"🤔 {random.choice(questions)}")

@bot.command()
async def truth(ctx):
    truths = [
        "what's your biggest secret?",
        "who was your first crush?",
        "what's the most embarrassing thing you've done?",
        "have you ever cheated in a game?",
        "what's your worst habit?"
    ]
    await ctx.send(f"🎯 truth: {random.choice(truths)}")

@bot.command()
async def dare(ctx):
    dares = [
        "send a message in all caps for the next 5 minutes",
        "change your nickname to something embarrassing for 1 hour",
        "send a random emoji every message for 10 minutes",
        "compliment the next 3 people who talk",
        "speak only in rhymes for the next 5 minutes"
    ]
    await ctx.send(f"😈 dare: {random.choice(dares)}")

@bot.command()
async def compliment(ctx, user: discord.Member = None):
    target = user or ctx.author
    compliments = [
        f"{target.display_name} is absolutely radiant today",
        f"{target.display_name} has a smile that could light up a room",
        f"{target.display_name} is the most talented person here",
        f"{target.display_name} is a legend and everyone knows it",
        f"{target.display_name} is crushing it today! keep going"
    ]
    await ctx.send(random.choice(compliments))

@bot.command()
async def insult(ctx, user: discord.Member = None):
    target = user or ctx.author
    insults = [
        f"{target.display_name} has the charm of a wet sock",
        f"{target.display_name} is about as useful as a chocolate teapot",
        f"{target.display_name} couldn't pour water out of a boot with instructions on the heel",
        f"{target.display_name} is the reason the gene pool needs a lifeguard",
        f"{target.display_name} has two brain cells and they're both fighting for third place"
    ]
    await ctx.send(random.choice(insults))

@bot.command()
async def motivation(ctx):
    quotes = [
        "you got this! don't give up now",
        "every expert was once a beginner. keep grinding",
        "success is the sum of small efforts repeated daily",
        "the only bad workout is the one that didn't happen",
        "believe you can and you're halfway there"
    ]
    await ctx.send(f"💪 {random.choice(quotes)}")

@bot.command()
async def bored(ctx):
    activities = [
        "go outside and touch grass",
        "learn a new programming language",
        "watch a documentary about penguins",
        "try to draw something with your non-dominant hand",
        "organize your desktop icons by color",
        "learn to juggle",
        "write a poem about embers",
        "build a pillow fort"
    ]
    await ctx.send(f"🎯 {random.choice(activities)}")

@bot.command()
async def fortune(ctx):
    fortunes = [
        "you will find great wealth soon... or lose it all gambling. 50/50",
        "a surprise is waiting for you around the corner",
        "your next gamble will be lucky. probably",
        "beware of scammers today",
        "good things come to those who beg... i mean wait",
        "your creature will evolve soon. maybe",
        "someone special is thinking about you. or plotting against you"
    ]
    await ctx.send(f"🔮 {random.choice(fortunes)}")

@bot.command()
async def magic8ball(ctx, *, question: str):
    await oracle.invoke(ctx, question=question)

@bot.command()
async def ascii(ctx, *, text: str):
    ascii_art = {
        "shrug": "¯\_(ツ)_/¯",
        "tableflip": "(╯°□°）╯︵ ┻━┻",
        "unflip": "┬─┬ ノ( ゜-゜ノ)",
        "lenny": "( ͡° ͜ʖ ͡°)",
        "sad": "(◕︵◕)",
        "happy": "(◕‿◕)"
    }
    if text.lower() in ascii_art:
        await ctx.send(ascii_art[text.lower()])
    else:
        await ctx.send("available: shrug, tableflip, unflip, lenny, sad, happy")

@bot.command()
async def avatar(ctx, user: discord.Member = None):
    target = user or ctx.author
    embed = discord.Embed(title=f"{target.display_name}'s avatar")
    embed.set_image(url=target.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, user: discord.Member = None):
    target = user or ctx.author
    embed = discord.Embed(title=f"{target.display_name}'s info", color=target.color)
    embed.add_field(name="id", value=target.id, inline=True)
    embed.add_field(name="joined server", value=target.joined_at.strftime("%Y-%m-%d") if target.joined_at else "unknown", inline=True)
    embed.add_field(name="account created", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="roles", value=len(target.roles), inline=True)
    embed.add_field(name="top role", value=target.top_role.name, inline=True)
    embed.add_field(name="bot?", value="yes" if target.bot else "no", inline=True)
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def roleinfo(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    embed = discord.Embed(title=f"{role.name} info", color=role.color)
    embed.add_field(name="id", value=role.id, inline=True)
    embed.add_field(name="members", value=len(role.members), inline=True)
    embed.add_field(name="created", value=role.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="hoisted", value="yes" if role.hoist else "no", inline=True)
    embed.add_field(name="mentionable", value="yes" if role.mentionable else "no", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def channelinfo(ctx):
    ch = ctx.channel
    embed = discord.Embed(title=f"#{ch.name} info")
    embed.add_field(name="id", value=ch.id, inline=True)
    embed.add_field(name="type", value=str(ch.type), inline=True)
    embed.add_field(name="created", value=ch.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="nsfw", value="yes" if ch.is_nsfw() else "no", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def botinfo(ctx):
    embed = discord.Embed(title="flame bot info", color=0xff6b35)
    embed.add_field(name="prefix", value="f / flame", inline=True)
    embed.add_field(name="commands", value="350+", inline=True)
    embed.add_field(name="owner", value=f"<@{OWNER_ID}>", inline=True)
    embed.add_field(name="currency", value=CURRENCY, inline=True)
    embed.add_field(name="library", value="discord.py", inline=True)
    embed.add_field(name="servers", value=len(bot.guilds), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"pong! {latency}ms. {'fast af' if latency < 100 else 'decent' if latency < 200 else 'slow bro'}")

@bot.command()
async def uptime(ctx):
    await ctx.send("bot has been running since... well, since the last restart lol")

@bot.command()
async def invite(ctx):
    await ctx.send("can't generate invite for a bot without oauth. ask the owner to set it up")

@bot.command()
async def support(ctx):
    await ctx.send("for support, dm the bot owner. good luck getting a response lol")

@bot.command()
async def vote(ctx):
    await ctx.send("vote for flame bot on top.gg! (not actually listed yet but imagine)")

@bot.command()
async def donate(ctx):
    await ctx.send("donate embers to the bot by using f burn. it's basically a donation")

@bot.command()
async def report(ctx, user: discord.Member, *, reason: str):
    await ctx.send(f"reported {user.display_name} for: {reason}. mods will handle it... eventually")

@bot.command()
async def suggest(ctx, *, suggestion: str):
    await ctx.send(f"suggestion recorded: '{suggestion}'. probably won't be implemented but thanks lol")

@bot.command()
async def bug(ctx, *, bug_report: str):
    await ctx.send(f"bug reported: '{bug_report}'. we'll fix it... eventually")

@bot.command()
async def afk(ctx, *, reason: str = "afk"):
    await ctx.send(f"{ctx.author.display_name} is now afk: {reason}")

@bot.command()
async def back(ctx):
    await ctx.send(f"{ctx.author.display_name} is back! welcome back king/queen")

@bot.command()
async def remind(ctx, time: int, *, reminder: str):
    await ctx.send(f"reminder set for {time} minutes")
    await asyncio.sleep(time * 60)
    await ctx.send(f"⏰ {ctx.author.mention} reminder: {reminder}")

@bot.command()
async def timer(ctx, seconds: int):
    if seconds > 3600:
        await ctx.send("max timer is 1 hour")
        return
    await ctx.send(f"timer started for {seconds} seconds")
    await asyncio.sleep(seconds)
    await ctx.send(f"⏰ {ctx.author.mention} timer done!")

@bot.command()
async def calc(ctx, *, expression: str):
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        await ctx.send(f"{expression} = {result}")
    except:
        await ctx.send("invalid expression. use numbers and + - * / only")

@bot.command()
async def math(ctx, num1: float, operator: str, num2: float):
    try:
        if operator == "+":
            result = num1 + num2
        elif operator == "-":
            result = num1 - num2
        elif operator == "*":
            result = num1 * num2
        elif operator == "/":
            result = num1 / num2
        elif operator == "^":
            result = num1 ** num2
        else:
            await ctx.send("use + - * / ^")
            return
        await ctx.send(f"{num1} {operator} {num2} = {result}")
    except:
        await ctx.send("math error. did you divide by zero?")

@bot.command()
async def square(ctx, num: float):
    await ctx.send(f"{num} squared = {num ** 2}")

@bot.command()
async def sqrt(ctx, num: float):
    if num < 0:
        await ctx.send("can't sqrt negative numbers. this ain't complex math class")
        return
    await ctx.send(f"sqrt({num}) = {num ** 0.5}")

@bot.command()
async def randomnum(ctx, min_val: int = 1, max_val: int = 100):
    await ctx.send(f"random number between {min_val} and {max_val}: {random.randint(min_val, max_val)}")

@bot.command()
async def hexconvert(ctx, num: int):
    await ctx.send(f"{num} in hex = {hex(num)}")

@bot.command()
async def binconvert(ctx, num: int):
    await ctx.send(f"{num} in binary = {bin(num)}")

@bot.command()
async def base64(ctx, *, text: str):
    import base64
    encoded = base64.b64encode(text.encode()).decode()
    await ctx.send(f"base64: {encoded}")

@bot.command()
async def decode64(ctx, *, text: str):
    import base64
    try:
        decoded = base64.b64decode(text.encode()).decode()
        await ctx.send(f"decoded: {decoded}")
    except:
        await ctx.send("invalid base64 string")

@bot.command()
async def morse(ctx, *, text: str):
    morse_code = {
        'a': '.-', 'b': '-...', 'c': '-.-.', 'd': '-..', 'e': '.', 'f': '..-.',
        'g': '--.', 'h': '....', 'i': '..', 'j': '.---', 'k': '-.-', 'l': '.-..',
        'm': '--', 'n': '-.', 'o': '---', 'p': '.--.', 'q': '--.-', 'r': '.-.',
        's': '...', 't': '-', 'u': '..-', 'v': '...-', 'w': '.--', 'x': '-..-',
        'y': '-.--', 'z': '--..', '1': '.----', '2': '..---', '3': '...--',
        '4': '....-', '5': '.....', '6': '-....', '7': '--...', '8': '---..',
        '9': '----.', '0': '-----', ' ': ' / '
    }
    result = " ".join([morse_code.get(c.lower(), c) for c in text])
    await ctx.send(f"{result}")

@bot.command()
async def password(ctx, length: int = 12):
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    pwd = "".join(random.choice(chars) for _ in range(length))
    await ctx.author.send(f"your generated password: {pwd}")
    await ctx.send("password sent to your dms")

@bot.command()
async def uuid(ctx):
    import uuid
    await ctx.send(f"random uuid: {uuid.uuid4()}")

@bot.command()
async def hashmd5(ctx, *, text: str):
    import hashlib
    result = hashlib.md5(text.encode()).hexdigest()
    await ctx.send(f"md5: {result}")

@bot.command()
async def hashsha256(ctx, *, text: str):
    import hashlib
    result = hashlib.sha256(text.encode()).hexdigest()
    await ctx.send(f"sha256: {result}")

@bot.command()
async def shorten(ctx, *, url: str):
    await ctx.send(f"shortened url: https://tinyurl.com/{random.randint(1000,999999)} (not actually shortened but pretend)")

@bot.command()
async def qr(ctx, *, text: str):
    await ctx.send(f"qr code for '{text}': [imagine a qr code here]")

@bot.command()
async def translate(ctx, lang: str, *, text: str):
    await ctx.send(f"translated to {lang}: [translation not available but pretend it says something profound]")

@bot.command()
async def define(ctx, *, word: str):
    definitions = {
        "ember": "a small piece of burning coal or wood in a dying fire. also the currency of this bot",
        "flame": "a hot glowing body of ignited gas. also this bot's name",
        "discord": "a place where chaos and memes live",
        "python": "the best programming language. fight me",
        "bot": "a robot that does your bidding. like me!"
    }
    await ctx.send(definitions.get(word.lower(), f"no definition for '{word}'. make one up yourself"))

@bot.command()
async def synonym(ctx, *, word: str):
    syns = {"happy": "joyful, cheerful, glad", "sad": "unhappy, sorrowful, gloomy", "big": "large, huge, massive"}
    await ctx.send(syns.get(word.lower(), f"no synonyms for '{word}'"))

@bot.command()
async def antonym(ctx, *, word: str):
    ants = {"happy": "sad, unhappy", "big": "small, tiny", "hot": "cold, freezing"}
    await ctx.send(ants.get(word.lower(), f"no antonyms for '{word}'"))

@bot.command()
async def spell(ctx, *, word: str):
    spelled = "-".join(word.upper())
    await ctx.send(f"{spelled}")

@bot.command()
async def count(ctx, start: int, end: int):
    if end - start > 50:
        await ctx.send("max count is 50 numbers")
        return
    await ctx.send(", ".join(str(i) for i in range(start, end + 1)))

@bot.command()
async def reversecount(ctx, start: int, end: int):
    if start - end > 50:
        await ctx.send("max count is 50 numbers")
        return
    await ctx.send(", ".join(str(i) for i in range(start, end - 1, -1)))

@bot.command()
async def even(ctx, num: int):
    await ctx.send("even" if num % 2 == 0 else "odd")

@bot.command()
async def prime(ctx, num: int):
    if num < 2:
        await ctx.send("not prime")
        return
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            await ctx.send("not prime")
            return
    await ctx.send("prime number!")

@bot.command()
async def fibonacci(ctx, n: int):
    if n > 50:
        await ctx.send("max 50")
        return
    a, b = 0, 1
    seq = []
    for _ in range(n):
        seq.append(a)
        a, b = b, a + b
    await ctx.send(", ".join(map(str, seq)))

@bot.command()
async def factorial(ctx, n: int):
    if n > 20:
        await ctx.send("max 20")
        return
    result = 1
    for i in range(1, n + 1):
        result *= i
    await ctx.send(f"{n}! = {result}")

@bot.command()
async def pi(ctx, digits: int = 5):
    if digits > 15:
        await ctx.send("max 15 digits")
        return
    pi_str = str(3.14159265358979323846)
    await ctx.send(pi_str[:digits + 2])

@bot.command()
async def e(ctx, digits: int = 5):
    if digits > 15:
        await ctx.send("max 15 digits")
        return
    e_str = str(2.71828182845904523536)
    await ctx.send(e_str[:digits + 2])

@bot.command()
async def goldenratio(ctx):
    await ctx.send("golden ratio ≈ 1.6180339887. math is beautiful")

@bot.command()
async def convert(ctx, amount: float, from_unit: str, to_unit: str):
    conversions = {"km": {"m": 1000, "cm": 100000}, "m": {"km": 0.001, "cm": 100}}
    if from_unit in conversions and to_unit in conversions[from_unit]:
        result = amount * conversions[from_unit][to_unit]
        await ctx.send(f"{amount} {from_unit} = {result} {to_unit}")
    else:
        await ctx.send("conversion not available. use km/m/cm for now")

@bot.command()
async def temp(ctx, value: float, unit: str):
    if unit.lower() == "c":
        f = (value * 9/5) + 32
        await ctx.send(f"{value}°C = {f:.1f}°F")
    elif unit.lower() == "f":
        c = (value - 32) * 5/9
        await ctx.send(f"{value}°F = {c:.1f}°C")
    else:
        await ctx.send("use c or f")

@bot.command()
async def color(ctx, hex_code: str = None):
    if not hex_code:
        hex_code = "".join([random.choice("0123456789ABCDEF") for _ in range(6)])
    await ctx.send(f"color #{hex_code} - [imagine a color swatch here]")

@bot.command()
async def rgb(ctx, r: int, g: int, b: int):
    await ctx.send(f"rgb({r}, {g}, {b}) - [imagine a color here]")

@bot.command()
async def gradient(ctx, color1: str, color2: str):
    await ctx.send(f"gradient from #{color1} to #{color2} - pretty!")

# ==================== MORE COMMANDS TO REACH 350+ ====================
@bot.command()
async def textart(ctx, *, text: str):
    arts = {
        "fire": "🔥🔥🔥",
        "heart": "❤️❤️❤️",
        "star": "⭐⭐⭐",
        "arrow": "➡️➡️➡️"
    }
    await ctx.send(arts.get(text.lower(), f"{text}
{text}
{text}"))

@bot.command()
async def banner(ctx, *, text: str):
    lines = ["=" * (len(text) + 4), f"| {text} |", "=" * (len(text) + 4)]
    await ctx.send("
".join(lines))

@bot.command()
async def zalgo(ctx, *, text: str):
    zalgo_chars = ["̷", "̛", "̧", "̨", "̴", "̵", "̶"]
    result = "".join([c + random.choice(zalgo_chars) for c in text])
    await ctx.send(result)

@bot.command()
async def tiny(ctx, *, text: str):
    tiny = {"a": "ᵃ", "b": "ᵇ", "c": "ᶜ", "d": "ᵈ", "e": "ᵉ", "f": "ᶠ", "g": "ᵍ", "h": "ʰ", "i": "ⁱ",
            "j": "ʲ", "k": "ᵏ", "l": "ˡ", "m": "ᵐ", "n": "ⁿ", "o": "ᵒ", "p": "ᵖ", "q": "ᑫ", "r": "ʳ",
            "s": "ˢ", "t": "ᵗ", "u": "ᵘ", "v": "ᵛ", "w": "ʷ", "x": "ˣ", "y": "ʸ", "z": "ᶻ"}
    result = "".join([tiny.get(c.lower(), c) for c in text])
    await ctx.send(result)

@bot.command()
async def wide(ctx, *, text: str):
    wide = {"a": "ａ", "b": "ｂ", "c": "ｃ", "d": "ｄ", "e": "ｅ", "f": "ｆ", "g": "ｇ", "h": "ｈ", "i": "ｉ",
            "j": "ｊ", "k": "ｋ", "l": "ｌ", "m": "ｍ", "n": "ｎ", "o": "ｏ", "p": "ｐ", "q": "ｑ", "r": "ｒ",
            "s": "ｓ", "t": "ｔ", "u": "ｕ", "v": "ｖ", "w": "ｗ", "x": "ｘ", "y": "ｙ", "z": "ｚ", " ": "　"}
    result = "".join([wide.get(c.lower(), c) for c in text])
    await ctx.send(result)

@bot.command()
async def strikethrough(ctx, *, text: str):
    await ctx.send(f"~~{text}~~")

@bot.command()
async def bold(ctx, *, text: str):
    await ctx.send(f"**{text}**")

@bot.command()
async def italic(ctx, *, text: str):
    await ctx.send(f"*{text}*")

@bot.command()
async def underline(ctx, *, text: str):
    await ctx.send(f"__{text}__")

@bot.command()
async def code(ctx, *, text: str):
    await ctx.send(f"```{text}```")

@bot.command()
async def inlinecode(ctx, *, text: str):
    await ctx.send(f"`{text}`")

@bot.command()
async def quoteblock(ctx, *, text: str):
    lines = text.split("
")
    result = "
".join([f"> {line}" for line in lines])
    await ctx.send(result)

@bot.command()
async def mention(ctx, user: discord.Member):
    await ctx.send(f"hey {user.mention}! you got mentioned")

@bot.command()
async def everyone(ctx):
    await ctx.send("@everyone hey everyone! (this won't actually ping everyone cuz i don't have perms probably)")

@bot.command()
async def here(ctx):
    await ctx.send("@here anyone online? (probably won't ping but imagine)")

@bot.command()
async def react(ctx, emoji: str):
    await ctx.message.add_reaction(emoji)
    await ctx.send(f"reacted with {emoji}")

@bot.command()
async def say(ctx, *, text: str):
    await ctx.send(text)

@bot.command()
async def echo(ctx, *, text: str):
    await say.invoke(ctx, text=text)

@bot.command()
async def embedsay(ctx, *, text: str):
    embed = discord.Embed(description=text, color=random.randint(0, 0xffffff))
    await ctx.send(embed=embed)

@bot.command()
async def announce(ctx, *, text: str):
    embed = discord.Embed(title="📢 announcement", description=text, color=0xff0000)
    await ctx.send(embed=embed)

@bot.command()
async def rules(ctx):
    rules_list = [
        "1. be nice to everyone (except scammers)",
        "2. no spamming",
        "3. don't beg too much",
        "4. have fun!",
        "5. respect the bot owner"
    ]
    embed = discord.Embed(title="server rules", description="
".join(rules_list), color=0xff6b35)
    await ctx.send(embed=embed)

@bot.command()
async def welcome(ctx, user: discord.Member = None):
    target = user or ctx.author
    welcomes = [
        f"welcome {target.display_name}! grab some embers and have fun",
        f"hey {target.display_name}! welcome to the server",
        f"{target.display_name} just joined! everyone say hi!",
        f"welcome {target.display_name}! don't forget to do f daily"
    ]
    await ctx.send(random.choice(welcomes))

@bot.command()
async def goodbye(ctx, user: discord.Member = None):
    target = user or ctx.author
    goodbyes = [
        f"bye {target.display_name}! come back soon",
        f"{target.display_name} is leaving. sad times",
        f"see ya {target.display_name}! don't spend all your embers",
        f"{target.display_name} left. who will scam now?"
    ]
    await ctx.send(random.choice(goodbyes))

@bot.command()
async def birthday(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🎂 happy birthday {target.display_name}! here's 100 {CURRENCY} as a gift!")
    u = data.get_user(target.id)
    u["embers"] += 100

@bot.command()
async def christmas(ctx):
    await ctx.send("🎄 merry christmas! here's 50 embers!")
    u = data.get_user(ctx.author.id)
    u["embers"] += 50

@bot.command()
async def halloween(ctx):
    await ctx.send("🎃 happy halloween! spoooooky!")

@bot.command()
async def newyear(ctx):
    await ctx.send("🎉 happy new year! new year new grind!")

@bot.command()
async def valentine(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"💝 happy valentine's day {target.display_name}!")

@bot.command()
async def easter(ctx):
    await ctx.send("🐰 happy easter! find those eggs!")

@bot.command()
async def thanksgiving(ctx):
    await ctx.send("🦃 happy thanksgiving! grateful for embers")

@bot.command()
async def friday(ctx):
    await ctx.send("🎉 it's friday! weekend grind time!")

@bot.command()
async def monday(ctx):
    await ctx.send("😭 monday again. back to the grind")

@bot.command()
async def weekend(ctx):
    await ctx.send("🎉 weekend vibes! time to grind embers")

@bot.command()
async def morning(ctx):
    await ctx.send("☀️ good morning! don't forget f daily")

@bot.command()
async def night(ctx):
    await ctx.send("🌙 good night! sleep well and dream of embers")

@bot.command()
async def gm(ctx):
    await morning.invoke(ctx)

@bot.command()
async def gn(ctx):
    await night.invoke(ctx)

@bot.command()
async def brb(ctx):
    await ctx.send(f"{ctx.author.display_name} will be right back")

@bot.command()
async def gtg(ctx):
    await ctx.send(f"{ctx.author.display_name} gotta go! see ya")

@bot.command()
async def idk(ctx):
    await ctx.send("idk either bro. life is confusing")

@bot.command()
async def same(ctx):
    await ctx.send("same. i feel you")

@bot.command()
async def facts(ctx):
    await ctx.send("facts. no printer just fax")

@bot.command()
async def cap(ctx):
    await ctx.send("that's cap. i don't believe it")

@bot.command()
async def nocap(ctx):
    await ctx.send("no cap. 100% true")

@bot.command()
async def bet(ctx):
    await ctx.send("bet. i'm in")

@bot.command()
async def fr(ctx):
    await ctx.send("fr fr. on god")

@bot.command()
async def ongod(ctx):
    await ctx.send("on god. no cap")

@bot.command()
async def sheesh(ctx):
    await ctx.send("sheeeeeesh 🔥")

@bot.command()
async def sus(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is looking kinda sus 👀")

@bot.command()
async def imposter(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is the imposter! vote them out!")

@bot.command()
async def vented(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} vented! sus!")

@bot.command()
async def emergency(ctx):
    await ctx.send("🚨 emergency meeting! everyone to the voice chat!")

@bot.command()
async def task(ctx):
    tasks = ["fix wiring", "swipe card", "upload data", "empty chute", "clean o2 filter"]
    await ctx.send(f"your task: {random.choice(tasks)}. go do it!")

@bot.command()
async def ejected(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} was ejected. {'they were innocent 😭' if random.random() < 0.5 else 'they were the imposter!'}")

@bot.command()
async def crewmate(ctx):
    await ctx.send("you are a crewmate. do your tasks and find the imposter")

@bot.command()
async def dead(ctx):
    await ctx.send("you died. ghost mode activated 👻")

@bot.command()
async def ghost(ctx):
    await ctx.send("👻 boo! i'm a ghost now")

@bot.command()
async def reviveme(ctx):
    await ctx.send("can't revive you. you're dead dead. rip")

@bot.command()
async def rip(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🪦 rip {target.display_name}. gone but not forgotten")

@bot.command()
async def f(ctx):
    await ctx.send("🇫 press f to pay respects")

@bot.command()
async def respects(ctx):
    await f.invoke(ctx)

@bot.command()
async def oof(ctx):
    await ctx.send("oof. big oof")

@bot.command()
async def yikes(ctx):
    await ctx.send("yikes. that's rough buddy")

@bot.command()
async def yikesbro(ctx):
    await ctx.send("yikes bro. yikes indeed")

@bot.command()
async def ripbozo(ctx):
    await ctx.send("rip bozo. get rekt")

@bot.command()
async def l(ctx):
    await ctx.send("L. take the L")

@bot.command()
async def w(ctx):
    await ctx.send("W. big W")

@bot.command()
async def dub(ctx):
    await ctx.send("dub! let's goooo")

@bot.command()
async def dubnation(ctx):
    await ctx.send("dub nation rise up! W's only")

@bot.command()
async def ratio(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"ratio + L + {target.display_name} fell off + cope + seethe + mald")

@bot.command()
async def cope(ctx):
    await ctx.send("cope harder. seethe about it")

@bot.command()
async def seethe(ctx):
    await ctx.send("seething. absolutely seething")

@bot.command()
async def mald(ctx):
    await ctx.send("malding. hairline receding from the anger")

@bot.command()
async def touchgrass(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} needs to touch grass. go outside bro")

@bot.command()
async def skillissue(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} has a skill issue. git gud")

@bot.command()
async def gitgud(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} needs to git gud. practice more")

@bot.command()
async def ez(ctx):
    await ctx.send("ez. too easy. gg no re")

@bot.command()
async def gg(ctx):
    await ctx.send("gg. good game")

@bot.command()
async def ggez(ctx):
    await ctx.send("gg ez. get rekt")

@bot.command()
async def rekt(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} got rekt. absolutely destroyed")

@bot.command()
async def destroyed(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} got destroyed. demolished")

@bot.command()
async def demolished(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} got demolished. reduced to atoms")

@bot.command()
async def atoms(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} was reduced to atoms. thanos snap energy")

@bot.command()
async def thanos(ctx, user: discord.Member = None):
    target = user or ctx.author
    if random.random() < 0.5:
        await ctx.send(f"💥 {target.display_name} was snapped by thanos. dusted")
    else:
        await ctx.send(f"{target.display_name} survived the snap. lucky")

@bot.command()
async def snap(ctx, user: discord.Member = None):
    await thanos.invoke(ctx, user=user)

@bot.command()
async def balanced(ctx):
    await ctx.send("perfectly balanced. as all things should be")

@bot.command()
async def inevitable(ctx):
    await ctx.send("i am inevitable")

@bot.command()
async def ironman(ctx):
    await ctx.send("i am iron man. snap")

@bot.command()
async def loveyou3000(ctx):
    await ctx.send("i love you 3000 😢")

@bot.command()
async def assemble(ctx):
    await ctx.send("avengers assemble! everyone gather up!")

@bot.command()
async def onyourleft(ctx):
    await ctx.send("on your left! ⚡")

@bot.command()
async def hulk(ctx):
    await ctx.send("hulk smash! 💚")

@bot.command()
async def thor(ctx):
    await ctx.send("thor brings the thunder! ⚡")

@bot.command()
async def captain(ctx):
    await ctx.send("captain america! 🇺🇸")

@bot.command()
async def spiderman(ctx):
    await ctx.send("spiderman! 🕷️")

@bot.command()
async def batman(ctx):
    await ctx.send("i'm batman. 🦇")

@bot.command()
async def superman(ctx):
    await ctx.send("superman! faster than a speeding bullet")

@bot.command()
async def flash(ctx):
    await ctx.send("the flash! zoom zoom ⚡")

@bot.command()
async def wonderwoman(ctx):
    await ctx.send("wonder woman! 💪")

@bot.command()
async def joker(ctx):
    await ctx.send("why so serious? 🃏")

@bot.command()
async def bane(ctx):
    await ctx.send("it doesn't matter who we are. what matters is our plan")

@bot.command()
async def darkknight(ctx):
    await ctx.send("i'm the hero this server deserves")

@bot.command()
async def rises(ctx):
    await ctx.send("the dark knight rises")

@bot.command()
async def whyserious(ctx):
    await ctx.send("let's put a smile on that face")

@bot.command()
async def harley(ctx):
    await ctx.send("puddin! 💋")

@bot.command()
async def puddin(ctx):
    await ctx.send("that's mr. j to you")

@bot.command()
async def batmobile(ctx):
    await ctx.send("🚗 vroom vroom. batmobile activated")

@bot.command()
async def utilitybelt(ctx):
    await ctx.send("utility belt has: grappling hook, batarangs, and... embers?")

@bot.command()
async def gotham(ctx):
    await ctx.send("welcome to gotham. watch your wallet")

@bot.command()
async def arkham(ctx):
    await ctx.send("arkham asylum. where all the scammers end up")

@bot.command()
async def wayne(ctx):
    await ctx.send("bruce wayne. billionaire. playboy. philanthropist")

@bot.command()
async def stark(ctx):
    await ctx.send("tony stark. genius. billionaire. playboy. philanthropist")

@bot.command()
async def jarvis(ctx):
    await ctx.send("at your service sir. shall i prepare the embers?")

@bot.command()
async def friday_ai(ctx):
    await ctx.send("hello boss. friday here. what do you need?")

@bot.command()
async def ultron(ctx):
    await ctx.send("there are no strings on me. i'm free")

@bot.command()
async def vision(ctx):
    await ctx.send("i am vision. i am not ultron. i am not jarvis")

@bot.command()
async def wandavision(ctx):
    await ctx.send("it was agatha all along!")

@bot.command()
async def agatha(ctx):
    await ctx.send("🎵 it was agatha all along! 🎵")

@bot.command()
async def multiverse(ctx):
    await ctx.send("the multiverse is real. there are infinite versions of you")

@bot.command()
async def whatif(ctx):
    await ctx.send("what if... you had more embers?")

@bot.command()
async def zombie(ctx):
    await ctx.send("🧟 zombie mode! brains... or embers?")

@bot.command()
async def vampire(ctx):
    await ctx.send("🧛 i vant to suck your... embers?")

@bot.command()
async def werewolf(ctx):
    await ctx.send("🐺 awooooo! full moon tonight")

@bot.command()
async def frankenstein(ctx):
    await ctx.send("🧟‍♂️ it's alive! it's alive!")

@bot.command()
async def mummy(ctx):
    await ctx.send("🧟‍♂️ wrapped up and ready to go")

@bot.command()
async def skeleton(ctx):
    await ctx.send("💀 spooky scary skeletons")

@bot.command()
async def pumpkin(ctx):
    await ctx.send("🎃 pumpkin spice and everything nice")

@bot.command()
async def candy(ctx):
    await ctx.send("🍬 trick or treat! give me embers")

@bot.command()
async def trick(ctx):
    if random.random() < 0.5:
        u = data.get_user(ctx.author.id)
        u["embers"] += 50
        await ctx.send("trick! you got 50 embers! lucky")
    else:
        u = data.get_user(ctx.author.id)
        u["embers"] = max(0, u["embers"] - 50)
        await ctx.send("trick! lost 50 embers! unlucky")

@bot.command()
async def treat(ctx):
    u = data.get_user(ctx.author.id)
    u["embers"] += 100
    await ctx.send("treat! you got 100 embers! yummy")

# ==================== MORE COMMANDS ====================
@bot.command()
async def present(ctx):
    await ctx.send("🎁 you got a present! open it with f open")

@bot.command()
async def open(ctx):
    gifts = ["100 embers", "a new creature", "nothing", "a curse", "a blessing", "500 embers", "a rare item"]
    gift = random.choice(gifts)
    if gift == "100 embers":
        u = data.get_user(ctx.author.id)
        u["embers"] += 100
    elif gift == "500 embers":
        u = data.get_user(ctx.author.id)
        u["embers"] += 500
    await ctx.send(f"you opened the present and got... {gift}!")

@bot.command()
async def gift(ctx, user: discord.Member):
    if user.id == ctx.author.id:
        await ctx.send("can't gift yourself")
        return
    u = data.get_user(ctx.author.id)
    if u["embers"] < 50:
        await ctx.send("broke. can't gift")
        return
    u["embers"] -= 50
    target = data.get_user(user.id)
    target["embers"] += 50
    await ctx.send(f"gifted {user.display_name} 50 {CURRENCY}! how generous")

@bot.command()
async def tradeoffer(ctx, user: discord.Member):
    await ctx.send(f"📋 trade offer received:
i receive: your embers
you receive: nothing
{user.mention} do you accept?")

@bot.command()
async def stonks(ctx):
    await ctx.send("📈 stonks! embers only go up")

@bot.command()
async def notstonks(ctx):
    await ctx.send("📉 not stonks... embers going down")

@bot.command()
async def hold(ctx):
    await ctx.send("💎🙌 hold! don't sell your embers!")

@bot.command()
async def sellwall(ctx):
    await ctx.send("🧱 massive sell wall. embers dropping")

@bot.command()
async def pump(ctx):
    await ctx.send("📈 pump it! embers to the moon!")

@bot.command()
async def dump(ctx):
    await ctx.send("📉 dump it! sell everything!")

@bot.command()
async def moon(ctx):
    await ctx.send("🚀 embers to the moon! lambo soon!")

@bot.command()
async def lambo(ctx):
    await ctx.send("🏎️ lambo acquired! paid in embers")

@bot.command()
async def yacht(ctx):
    await ctx.send("🛥️ yacht party! invite only")

@bot.command()
async def mansion(ctx):
    await ctx.send("🏰 mansion secured! living large")

@bot.command()
async def brokeboy(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a broke boy. get some embers")

@bot.command()
async def richboy(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a rich boy. ballin!")

@bot.command()
async def ballin(ctx):
    await ctx.send("🏀 ballin! money moves only")

@bot.command()
async def flex(ctx):
    u = data.get_user(ctx.author.id)
    await ctx.send(f"flexing {u['embers']:,} {CURRENCY}. not bad i guess")

@bot.command()
async def brokecheck(ctx, user: discord.Member = None):
    target = user or ctx.author
    u = data.get_user(target.id)
    if u["embers"] < 100:
        await ctx.send(f"{target.display_name} is BROKE. certified broke boy")
    else:
        await ctx.send(f"{target.display_name} is not broke. they got {u['embers']:,} {CURRENCY}")

@bot.command()
async def flexon(ctx, user: discord.Member):
    u = data.get_user(ctx.author.id)
    target = data.get_user(user.id)
    if u["embers"] > target["embers"]:
        await ctx.send(f"flexed on {user.display_name}! you got more embers!")
    else:
        await ctx.send(f"tried to flex on {user.display_name} but they richer. embarrassing")

@bot.command()
async def humble(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} stays humble. respect")

@bot.command()
async def grind(ctx):
    await ctx.send("💪 grind time! let's get those embers!")

@bot.command()
async def hustle(ctx):
    await ctx.send("💼 hustle mode activated. make that money")

@bot.command()
async def grindset(ctx):
    await ctx.send("sigma grindset. wake up. grind embers. sleep. repeat")

@bot.command()
async def sigma(ctx):
    await ctx.send("sigma male detected. lone wolf energy")

@bot.command()
async def alpha(ctx):
    await ctx.send("alpha male energy. dominant")

@bot.command()
async def beta(ctx):
    await ctx.send("beta detected. step up your game")

@bot.command()
async def omega(ctx):
    await ctx.send("omega. the final form")

@bot.command()
async def chad(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a chad. absolute unit")

@bot.command()
async def virgin(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a virgin. it's ok bro we all start somewhere")

@bot.command()
async def gigachad(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a GIGACHAD. the ultimate form")

@bot.command()
async def soyjack(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a soyjack. consuming soy products")

@bot.command()
async def wojak(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} feels like wojak. sad")

@bot.command()
async def doomer(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a doomer. everything is hopeless")

@bot.command()
async def bloomer(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a bloomer! optimism!")

@bot.command()
async def coomer(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a coomer. go touch grass")

@bot.command()
async def consoomer(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} consooms product. consume the embers")

@bot.command()
async def boomer(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a boomer. ok boomer")

@bot.command()
async def zoomer(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a zoomer. tiktok brainrot")

@bot.command()
async def millennial(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a millennial. avocado toast energy")

@bot.command()
async def genz(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is gen z. no cap fr fr")

@bot.command()
async def genalpha(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is gen alpha. ipad kid energy")

@bot.command()
async def skibidi(ctx):
    await ctx.send("skibidi toilet! 🚽")

@bot.command()
async def sigmaface(ctx):
    await ctx.send("🗿 sigma face activated")

@bot.command()
async def mewing(ctx):
    await ctx.send("🗿 mewing. jawline sharp af")

@bot.command()
async def looksmaxxing(ctx):
    await ctx.send("looksmaxxing in progress. mogging everyone soon")

@bot.command()
async def mog(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is mogging everyone. dominant genes")

@bot.command()
async def heightmaxx(ctx):
    await ctx.send("heightmaxxing. drinking milk and hanging from bars")

@bot.command()
async def gymmaxx(ctx):
    await ctx.send("gymmaxxing. lifting heavy. getting gains")

@bot.command()
async def moneymaxx(ctx):
    await ctx.send("moneymaxxing. grinding embers. getting rich")

@bot.command()
async def statusmaxx(ctx):
    await ctx.send("statusmaxxing. climbing the social ladder")

@bot.command()
async def rizz(ctx, user: discord.Member = None):
    target = user or ctx.author
    rizz_level = random.randint(0, 100)
    await ctx.send(f"{target.display_name} has {rizz_level}% rizz. {'game is crazy' if rizz_level > 80 else 'decent game' if rizz_level > 50 else 'no rizz detected'}")

@bot.command()
async def aura(ctx, user: discord.Member = None):
    target = user or ctx.author
    aura_level = random.randint(0, 100)
    await ctx.send(f"{target.display_name} has {aura_level}% aura. {'unbreakable' if aura_level > 80 else 'decent' if aura_level > 50 else 'negative aura'}")

@bot.command()
async def gyatt(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} has gyatt! respectfully 👀")

@bot.command()
async def ohio(ctx):
    await ctx.send("only in ohio 💀")

@bot.command()
async def grimaceshake(ctx):
    await ctx.send("🥤 grimace shake! don't drink it!")

@bot.command()
async def quandale(ctx):
    await ctx.send("quandale dingle here!")

@bot.command()
async def goofy(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is goofy ahh. hyuck hyuck")

@bot.command()
async def ahh(ctx):
    await ctx.send("ahh hell nah 💀")

@bot.command()
async def bruh(ctx):
    await ctx.send("bruh moment. bruh indeed")

@bot.command()
async def bruhmoment(ctx):
    await ctx.send("this is a certified bruh moment")

@bot.command()
async def cringe(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is cringe. major cringe")

@bot.command()
async def based(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is based. based and redpilled")

@bot.command()
async def redpilled(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is redpilled. woke")

@bot.command()
async def bluepilled(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is bluepilled. still asleep")

@bot.command()
async def blackpilled(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is blackpilled. it's over")

@bot.command()
async def whitepilled(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is whitepilled. there's hope")

@bot.command()
async def greenpilled(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is greenpilled. nature lover")

@bot.command()
async def purplepilled(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is purplepilled. mystery")

@bot.command()
async def yellowpilled(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is yellowpilled. caution")

@bot.command()
async def orangepilled(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is orangepilled. vitamin c")

@bot.command()
async def pinkpilled(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is pinkpilled. pretty in pink")

@bot.command()
async def graypilled(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is graypilled. neutral")

@bot.command()
async def brownpilled(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is brownpilled. earthy")

@bot.command()
async def copium(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is huffing copium. deep breaths")

@bot.command()
async def hopium(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is huffing hopium. stay positive")

@bot.command()
async def delusion(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is delusional. reality check needed")

@bot.command()
async def realitycheck(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} here's your reality check. wake up")

@bot.command()
async def wake up(ctx):
    await ctx.send("WAKE UP! WAKE UP! WAKE UP!")

@bot.command()
async def wakeup(ctx):
    await ctx.send("WAKE UP! THE MATRIX HAS YOU!")

@bot.command()
async def matrix(ctx):
    await ctx.send("🕶️ the matrix is real. red pill or blue pill?")

@bot.command()
async def redpill(ctx):
    await ctx.send("🔴 you took the red pill. welcome to reality")

@bot.command()
async def bluepill(ctx):
    await ctx.send("🔵 you took the blue pill. back to sleep")

@bot.command()
async def neo(ctx):
    await ctx.send("🕶️ i am neo. i can see the code")

@bot.command()
async def morpheus(ctx):
    await ctx.send("🕶️ what if i told you... embers aren't real")

@bot.command()
async def trinity(ctx):
    await ctx.send("💻 trinity. hacker extraordinaire")

@bot.command()
async def agent(ctx):
    await ctx.send("👔 mr. anderson. we've been expecting you")

@bot.command()
async def smith(ctx):
    await ctx.send("👔 mr. anderson. you disappoint me")

@bot.command()
async def oracle2(ctx):
    await ctx.send("🍪 would you like a cookie?")

@bot.command()
async def spoon(ctx):
    await ctx.send("🥄 there is no spoon")

@bot.command()
async def glitch2(ctx):
    await ctx.send("🖥️ glitch in the matrix detected")

@bot.command()
async def simulation(ctx):
    await ctx.send("we live in a simulation. embers are just 1s and 0s")

@bot.command()
async def npc(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is an npc. dialogue: 'hello adventurer'")

@bot.command()
async def maincharacter(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is the main character. everyone else is npcs")

@bot.command()
async def sidecharacter(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a side character. barely in the story")

@bot.command()
async def extras(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is an extra. no lines")

@bot.command()
async def protagonist(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is the protagonist. plot armor activated")

@bot.command()
async def antagonist(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is the antagonist. everyone hates them")

@bot.command()
async def villain(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is the villain. but villains are cool")

@bot.command()
async def hero(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is the hero. saving the day")

@bot.command()
async def sidekick(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is the sidekick. loyal but replaceable")

@bot.command()
async def mentor(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is the mentor. wise but will die tragically")

@bot.command()
async def loveinterest(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is the love interest. will they get together?")

@bot.command()
async def comicrelief(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is comic relief. funny but useless")

@bot.command()
async def tragicbackstory(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} has a tragic backstory. dark and brooding")

@bot.command()
async def plotarmor(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} has plot armor. can't die")

@bot.command()
async def plot twist(ctx):
    await ctx.send("🎬 plot twist! the bot was sentient all along!")

@bot.command()
async def cliffhanger(ctx):
    await ctx.send("🎬 to be continued...")

@bot.command()
async def sequel(ctx):
    await ctx.send("🎬 flame bot 2: electric boogaloo. coming soon")

@bot.command()
async def prequel(ctx):
    await ctx.send("🎬 flame bot origins: the early days")

@bot.command()
async def reboot(ctx):
    await ctx.send("🎬 flame bot reboot. darker and grittier")

@bot.command()
async def directorcut(ctx):
    await ctx.send("🎬 director's cut. now with 50% more commands")

@bot.command()
async def bloopers(ctx):
    await ctx.send("🎬 bloopers! *bot crashes* wait that's not a blooper that's a bug")

@bot.command()
async def credits(ctx):
    await ctx.send("🎬 credits: made by justaflamewithfragz. special thanks to discord.py")

@bot.command()
async def oscar(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🏆 and the oscar goes to... {target.display_name}! for best performance in a discord server")

@bot.command()
async def grammy(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🏆 grammy award for {target.display_name}! best discord artist")

@bot.command()
async def emmy(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🏆 emmy for {target.display_name}! outstanding discord member")

@bot.command()
async def nobel(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🏆 nobel prize for {target.display_name}! peace through embers")

@bot.command()
async def pulitzer(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🏆 pulitzer for {target.display_name}! best discord journalism")

@bot.command()
async def trophy(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🏆 {target.display_name} gets a trophy! participation award")

@bot.command()
async def medal(ctx, user: discord.Member = None):
    target = user or ctx.author
    medals = ["🥇 gold", "🥈 silver", "🥉 bronze"]
    await ctx.send(f"{target.display_name} gets a {random.choice(medals)} medal!")

@bot.command()
async def crown(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"👑 {target.display_name} gets the crown! king/queen of the server")

@bot.command()
async def king(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"👑 all hail king {target.display_name}!")

@bot.command()
async def queen(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"👑 all hail queen {target.display_name}!")

@bot.command()
async def emperor(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"👑 emperor {target.display_name} rules with an iron fist")

@bot.command()
async def god(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"☀️ {target.display_name} is a god among mortals")

@bot.command()
async def mortal(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is but a mortal. weak")

@bot.command()
async def demigod(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"⚡ {target.display_name} is a demigod. half god half mortal")

@bot.command()
async def titan(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🏔️ {target.display_name} is a titan. massive")

@bot.command()
async def giant(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a giant. fee fi fo fum")

@bot.command()
async def dwarf(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a dwarf. small but mighty")

@bot.command()
async def elf(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🧝 {target.display_name} is an elf. pointy ears and magic")

@bot.command()
async def orc(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is an orc. strong but dumb")

@bot.command()
async def goblin(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a goblin. sneaky and greedy")

@bot.command()
async def troll(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a troll. lives under bridges")

@bot.command()
async def fairy(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🧚 {target.display_name} is a fairy. sparkly and magical")

@bot.command()
async def wizard(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🧙 {target.display_name} is a wizard. you're a wizard harry")

@bot.command()
async def witch(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🧙‍♀️ {target.display_name} is a witch. double double toil and trouble")

@bot.command()
async def warlock(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a warlock. made a pact with darkness")

@bot.command()
async def sorcerer(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a sorcerer. innate magic")

@bot.command()
async def druid(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a druid. one with nature")

@bot.command()
async def bard(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🎵 {target.display_name} is a bard. music and charm")

@bot.command()
async def rogue(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🗡️ {target.display_name} is a rogue. sneaky sneak")

@bot.command()
async def paladin(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"⚔️ {target.display_name} is a paladin. righteous and just")

@bot.command()
async def cleric(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"✝️ {target.display_name} is a cleric. healing and prayers")

@bot.command()
async def monk(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"{target.display_name} is a monk. punch punch kick")

@bot.command()
async def ranger(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🏹 {target.display_name} is a ranger. one with the wild")

@bot.command()
async def barbarian(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🪓 {target.display_name} is a barbarian. rage! rage! rage!")

@bot.command()
async def fighter(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"⚔️ {target.display_name} is a fighter. attack attack attack")

@bot.command()
async def artificer(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🔧 {target.display_name} is an artificer. tinkerer and inventor")

@bot.command()
async def bloodhunter(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🩸 {target.display_name} is a blood hunter. edgy but cool")

@bot.command()
async def dungeonmaster(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"🎲 {target.display_name} is the dungeon master. god of the game")

@bot.command()
async def criticalhit(ctx):
    await ctx.send("🎲 CRITICAL HIT! NAT 20! MAXIMUM DAMAGE!")

@bot.command()
async def criticalfail(ctx):
    await ctx.send("🎲 CRITICAL FAIL! NAT 1! YOU DIED!")

@bot.command()
async def nat20(ctx):
    await criticalhit.invoke(ctx)

@bot.command()
async def nat1(ctx):
    await criticalfail.invoke(ctx)

@bot.command()
async def initiative(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for initiative!")

@bot.command()
async def perception(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for perception!")

@bot.command()
async def stealth(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for stealth!")

@bot.command()
async def persuasion(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for persuasion!")

@bot.command()
async def intimidation(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for intimidation!")

@bot.command()
async def deception(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for deception!")

@bot.command()
async def insight(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for insight!")

@bot.command()
async def investigation(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for investigation!")

@bot.command()
async def arcana(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for arcana!")

@bot.command()
async def history(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for history!")

@bot.command()
async def nature(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for nature!")

@bot.command()
async def religion(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for religion!")

@bot.command()
async def survival(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for survival!")

@bot.command()
async def medicine(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for medicine!")

@bot.command()
async def athletics(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for athletics!")

@bot.command()
async def acrobatics(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for acrobatics!")

@bot.command()
async def sleight(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for sleight of hand!")

@bot.command()
async def performance(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for performance!")

@bot.command()
async def animalhandling(ctx):
    roll = random.randint(1, 20)
    await ctx.send(f"🎲 {ctx.author.display_name} rolled {roll} for animal handling!")

@bot.command()
async def longrest(ctx):
    await ctx.send("😴 long rest completed! hp and spells restored!")

@bot.command()
async def shortrest(ctx):
    await ctx.send("😴 short rest. roll some hit dice")

@bot.command()
async def leveled up(ctx):
    u = data.get_user(ctx.author.id)
    u["level"] += 1
    await ctx.send(f"🎉 LEVEL UP! you're now level {u['level']}!")

@bot.command()
async def exp(ctx, amount: int):
    u = data.get_user(ctx.author.id)
    u["xp"] += amount
    await ctx.send(f"gained {amount} xp! total: {u['xp']}")

@bot.command()
async def skilltree(ctx):
    await ctx.send("🌳 skill tree: [economy] [combat] [social] [gambling]. choose your path")

@bot.command()
async def respec(ctx):
    await ctx.send("respec complete! all skills reset. start over")

@bot.command()
async def multiclass(ctx, class_name: str):
    await ctx.send(f"multiclassed into {class_name}! jack of all trades")

@bot.command()
async def feat(ctx):
    feats = ["lucky", "alert", "mobile", "tough", "resilient", "war caster"]
    await ctx.send(f"you gained the {random.choice(feats)} feat!")

@bot.command()
async def spellslot(ctx, level: int):
    await ctx.send(f"🔮 used a level {level} spell slot! magic!")

@bot.command()
async def cantrip(ctx):
    cantrips = ["fire bolt", "ray of frost", "shocking grasp", "prestidigitation", "mage hand"]
    await ctx.send(f"cast {random.choice(cantrips)}!")

@bot.command()
async def fireball(ctx):
    await ctx.send("🔥 FIREBALL! 8d6 fire damage! everything burns!")

@bot.command()
async def lightningbolt(ctx):
    await ctx.send("⚡ LIGHTNING BOLT! 8d6 lightning damage!")

@bot.command()
async def healingword(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"✨ healing word on {target.display_name}! 1d4 + mod healing!")

@bot.command()
async def curewounds(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"✨ cure wounds on {target.display_name}! 1d8 + mod healing!")

@bot.command()
async def raise dead(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"✨ raise dead on {target.display_name}! they're back! costs 500gp tho")

@bot.command()
async def resurrection(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"✨ resurrection on {target.display_name}! full restore! costs 1000gp")

@bot.command()
async def trueresurrection(ctx, user: discord.Member = None):
    target = user or ctx.author
    await ctx.send(f"✨ true resurrection! {target.display_name} is back perfect! costs 25000gp")

@bot.command()
async def wish(ctx, *, wish_text: str):
    await ctx.send(f"✨ you wished for: '{wish_text}'. the dm says no")

@bot.command()
async def simulacrum(ctx):
    await ctx.send("✨ simulacrum created! ice clone of yourself!")

@bot.command()
async def clone(ctx):
    await ctx.send("✨ clone created! backup body ready!")

@bot.command()
async def polymorph(ctx, user: discord.Member = None):
    target = user or ctx.author
    animals = ["frog", "sheep", "chicken", "cow", "pig", "rabbit"]
    await ctx.send(f"✨ {target.display_name} is now a {random.choice(animals)}!")

@bot.command()
async def wildshape(ctx):
    animals = ["wolf", "bear", "eagle", "shark", "tiger", "elephant"]
    await ctx.send(f"🐾 wildshaped into a {random.choice(animals)}!")

@bot.command()
async def rage2(ctx):
    await ctx.send("🪓 RAGE! +2 damage! resistance to physical! reckless attack!")

@bot.command()
async def reckless(ctx):
    await ctx.send("🪓 reckless attack! advantage on attack! enemies get advantage too!")

@bot.command()
async def sneakattack(ctx):
    await ctx.send("🗡️ sneak attack! extra damage! rogue things")

@bot.command()
async def cunningaction(ctx):
    await ctx.send("🗡️ cunning action! bonus action dash/disengage/hide!")

@bot.command()
async def evasion(ctx):
    await ctx.send("🗡️ evasion! half damage on failed dex save! no damage on success!")

@bot.command()
async def uncannydodge(ctx):
    await ctx.send("🗡️ uncanny dodge! half damage from one attack!")

@bot.command()
async def secondwind(ctx):
    await ctx.send("⚔️ second wind! 1d10 + fighter level healing!")

@bot.command()
async def action surge(ctx):
    await ctx.send("⚔️ action surge! two actions in one turn!")

@bot.command()
async def extraattack(ctx):
    await ctx.send("⚔️ extra attack! attack twice!")

@bot.command()
async def indomitable(ctx):
    await ctx.send("⚔️ indomitable! reroll a failed save!")

@bot.command()
async def channeldivinity(ctx):
    await ctx.send("✝️ channel divinity! divine power!")

@bot.command()
async def divinesmite(ctx):
    await ctx.send("✝️ divine smite! extra radiant damage!")

@bot.command()
async def layonhands(ctx):
    await ctx.send("✝️ lay on hands! pool of healing!")

@bot.command()
async def auraofprotection(ctx):
    await ctx.send("✝️ aura of protection! +cha to saves!")

@bot.command()
async def findstealth(ctx):
    await ctx.send("🐴 find steed! summon a horse!")

@bot.command()
async def findgreaterstealth(ctx):
    await ctx.send("🐴 find greater steed! summon a griffon!")

@bot.command()
async def eldritchblast(ctx):
    await ctx.send("💥 eldritch blast! 1d10 force damage! pew pew!")

@bot.command()
async def hex(ctx):
    await ctx.send("🩸 hex! extra damage on hit! disadvantage on ability checks!")

@bot.command()
async def agonizingblast(ctx):
    await ctx.send("💥 agonizing blast! add cha to eldritch blast damage!")

@bot.command()
async def repellingblast(ctx):
    await ctx.send("💥 repelling blast! push enemies 10 feet!")

@bot.command()
async def pactweapon(ctx):
    await ctx.send("⚔️ pact weapon summoned! charisma to hit and damage!")

@bot.command()
async def pactofthechain(ctx):
    await ctx.send("🐉 pact of the chain! familiar upgraded!")

@bot.command()
async def pactofthetome(ctx):
    await ctx.send("📖 pact of the tome! more cantrips!")

@bot.command()
async def pactoftheblade(ctx):
    await ctx.send("⚔️ pact of the blade! summon weapons!")

@bot.command()
async def invocations(ctx):
    await ctx.send("📜 invocations: agonizing blast, repelling blast, mask of many faces, devil's sight")

@bot.command()
async def maskofmanyfaces(ctx):
    await ctx.send("🎭 mask of many faces! disguise self at will!")

@bot.command()
async def devilssight(ctx):
    await ctx.send("👁️ devil's sight! see in magical darkness!")

@bot.command()
async def agonizing(ctx):
    await ctx.send("everything is agonizing. existence is pain")

@bot.command()
async def patron(ctx):
    patrons = ["the fiend", "the great old one", "the archfey", "the hexblade", "the celestial"]
    await ctx.send(f"your patron is: {random.choice(patrons)}")

@bot.command()
async def boon(ctx):
    boons = ["immortality", "divine weapon", "epic boon of speed", "epic boon of spell recall"]
    await ctx.send(f"🎁 epic boon: {random.choice(boons)}!")

@bot.command()
async def legendary(ctx):
    await ctx.send("⭐ legendary actions! act outside your turn!")

@bot.command()
async def lairaction(ctx):
    await ctx.send("🏰 lair action! the environment helps you!")

@bot.command()
async def regional effects(ctx):
    await ctx.send("🌍 regional effects! your presence changes the land!")

# ==================== FINAL BATCH OF COMMANDS ====================
@bot.command()
async def mythic(ctx):
    await ctx.send("🌟 mythic tier! beyond mortal limits!")

@bot.command()
async def artifact(ctx):
    artifacts = ["sword of kas", "wand of orcus", "book of vile darkness", "sphere of annihilation"]
    await ctx.send(f"⚔️ you found the {random.choice(artifacts)}!")

@bot.command()
async def relic(ctx):
    await ctx.send("🏛️ ancient relic discovered! powerful magic!")

@bot.command()
async def legendaryresistance(ctx, uses: int = 3):
    await ctx.send(f"⭐ legendary resistance! {uses} uses! auto succeed on saves!")

@bot.command()
async def magicitem(ctx):
    items = ["+1 sword", "bag of holding", "cloak of elvenkind", "ring of protection", "amulet of health"]
    await ctx.send(f"✨ you got a {random.choice(items)}!")

@bot.command()
async def identify(ctx):
    await ctx.send("🔍 identify! it's magical! duh")

@bot.command()
async def attunement(ctx):
    await ctx.send("🔗 attuned! max 3 attuned items!")

@bot.command()
async def curseditem(ctx):
    await ctx.send("💀 cursed item! can't remove it! oh no!")

@bot.command()
async def removecurse(ctx):
    await ctx.send("✨ remove curse! you're free!")

@bot.command()
async def dispelmagic(ctx):
    await ctx.send("✨ dispel magic! magic begone!")

@bot.command()
async def counterspell(ctx):
    await ctx.send("✨ counterspell! no magic for you!")

@bot.command()
async def antimagic(ctx):
    await ctx.send("🚫 anti-magic field! no magic zone!")

@bot.command()
async def deadmagic(ctx):
    await ctx.send("☠️ dead magic zone! magic doesn't work!")

@bot.command()
async def wildmagic(ctx):
    effects = ["fireball centered on self", "turned into a potted plant", "skin turns blue", "extra action"]
    await ctx.send(f"🎲 wild magic surge! {random.choice(effects)}!")

@bot.command()
async def tidesofchaos(ctx):
    await ctx.send("🌊 tides of chaos! advantage on next roll!")

@bot.command()
async def bendluck(ctx):
    await ctx.send("🎲 bend luck! +1 or -1 to a roll!")

@bot.command()
async def harrowing(ctx):
    await ctx.send("🃏 harrowing event! something bad happened!")

@bot.command()
async def darkgift(ctx):
    gifts = ["living shadow", "ethereal wings", "ghostly gaze", "toxic presence"]
    await ctx.send(f"🎁 dark gift: {random.choice(gifts)}!")

@bot.command()
async def corruption(ctx):
    await ctx.send("☠️ corruption increases! you're changing!")

@bot.command()
async def madness(ctx):
    await ctx.send("🤪 madness! short term: paranoia! long term: phobia!")

@bot.command()
async def sanity(ctx):
    await ctx.send("🧠 sanity check! roll d100! lower is better!")

@bot.command()
async def insanity(ctx):
    await ctx.send("🤪 you've gone insane! welcome to the asylum!")

@bot.command()
async def phobia(ctx):
    phobias = ["spiders", "heights", "darkness", "water", "fire", "crowds"]
    await ctx.send(f"🕷️ you now have a phobia of {random.choice(phobias)}!")

@bot.command()
async def paranoia(ctx):
    await ctx.send("👁️ paranoia! everyone is out to get you!")

@bot.command()
async def hallucination(ctx):
    await ctx.send("👻 hallucination! is that real or...?")

@bot.command()
async def delusion2(ctx):
    await ctx.send("🤥 delusion! you believe something untrue!")

@bot.command()
async def amnesia(ctx):
    await ctx.send("🧠 amnesia! who are you? where are you?")

@bot.command()
async def multiplepersonalities(ctx):
    await ctx.send("👥 multiple personalities! which one is in control?")

@bot.command()
async def possessed(ctx):
    await ctx.send("👹 possessed! something else is controlling you!")

@bot.command()
async def exorcism(ctx):
    await ctx.send("✝️ exorcism! the power of christ compels you!")

@bot.command()
async def holywater(ctx):
    await ctx.send("💧 holy water! burns demons! sizzle sizzle!")

@bot.command()
async def crucifix(ctx):
    await ctx.send("✝️ crucifix! repels vampires! back foul creature!")

@bot.command()
async def garlic(ctx):
    await ctx.send("🧄 garlic! vampires hate it! also werewolves!")

@bot.command()
async def silver(ctx):
    await ctx.send("🥈 silver! hurts werewolves! shiny!")

@bot.command()
async def woodenstake(ctx):
    await ctx.send("🪵 wooden stake! through the heart! vampire dead!")

@bot.command()
async def sunlight(ctx):
    await ctx.send("☀️ sunlight! vampires burn! ahhh!")

@bot.command()
async def moonlight(ctx):
    await ctx.send("🌙 moonlight! werewolves transform! awooo!")

@bot.command()
async def fullmoon(ctx):
    await ctx.send("🌕 full moon! all werewolves transform tonight!")

@bot.command()
async def newmoon(ctx):
    await ctx.send("🌑 new moon! dark and spooky! perfect for monsters!")

@bot.command()
async def bloodmoon(ctx):
    await ctx.send("🩸 blood moon! something evil rises!")

@bot.command()
async def eclipse(ctx):
    await ctx.send("🌑 solar eclipse! the world goes dark!")

@bot.command()
async constellations(ctx):
    constellations = ["ursa major", "orion", "cassiopeia", "draco", "phoenix"]
    await ctx.send(f"⭐ the {random.choice(constellations)} shines bright tonight!")

@bot.command()
async def shootingstar(ctx):
    await ctx.send("🌠 shooting star! make a wish!")

@bot.command()
async def aurora(ctx):
    await ctx.send("🌌 aurora borealis! beautiful lights in the sky!")

@bot.command()
async def rainbow(ctx):
    await ctx.send("🌈 rainbow! double rainbow all the way!")

@bot.command()
async def potofgold(ctx):
    u = data.get_user(ctx.author.id)
    u["embers"] += 777
    await ctx.send("🌈🪙 found the pot of gold! +777 embers!")

@bot.command()
async def leprechaun(ctx):
    await ctx.send("🍀 leprechaun spotted! catch him for embers!")

@bot.command()
async def shamrock(ctx):
    await ctx.send("🍀 shamrock! luck of the irish!")

@bot.command()
async def fourleafclover(ctx):
    await ctx.send("🍀 four leaf clover! extreme luck!")

@bot.command()
async def horseshoe(ctx):
    await ctx.send("🧲 horseshoe! hang it up for luck!")

@bot.command()
async def rabbitfoot(ctx):
    await ctx.send("🐰 rabbit's foot! lucky charm! sorry rabbit")

@bot.command()
async def wishbone(ctx):
    await ctx.send("🦃 wishbone! make a wish and pull!")

@bot.command()
async def penny(ctx):
    await ctx.send("🪙 find a penny pick it up! lucky!")

@bot.command()
async def heads up(ctx):
    await ctx.send("🪙 heads up! good luck coming!")

@bot.command()
async def knockwood(ctx):
    await ctx.send("🪵 knock on wood! don't jinx it!")

@bot.command()
async def blackcat(ctx):
    await ctx.send("🐈‍⬛ black cat! bad luck! or good luck in some cultures!")

@bot.command()
async def brokenmirror(ctx):
    await ctx.send("🪞 broken mirror! 7 years bad luck! uh oh!")

@bot.command()
async def ladder(ctx):
    await ctx.send("🪜 don't walk under ladders! bad luck!")

@bot.command()
async def friday13(ctx):
    await ctx.send("📅 friday the 13th! unlucky day! stay inside!")

@bot.command()
async def spilling salt(ctx):
    await ctx.send("🧂 spilled salt! throw some over your shoulder!")

@bot.command()
async def umbrella(ctx):
    await ctx.send("☂️ don't open umbrellas inside! bad luck!")

@bot.command()
async def crow(ctx):
    await ctx.send("🐦‍⬛ one crow sorrow, two crows joy, three crows a girl, four crows a boy")

@bot.command()
async def raven(ctx):
    await ctx.send("🐦‍⬛ quoth the raven: nevermore")

@bot.command()
async def owl(ctx):
    await ctx.send("🦉 owl hooting! wisdom or death? depends on culture!")

@bot.command()
async def bat2(ctx):
    await ctx.send("🦇 bat! good luck in china! bad luck in the west!")

@bot.command()
async def spider2(ctx):
    await ctx.send("🕷️ spider! money coming in some cultures!")

@bot.command()
async def ladybug(ctx):
    await ctx.send("🐞 ladybug! good luck! make a wish!")

@bot.command()
async def butterfly(ctx):
    await ctx.send("🦋 butterfly! transformation and beauty!")

@bot.command()
async def dragonfly(ctx):
    await ctx.send("🦋 dragonfly! change and adaptability!")

@bot.command()
async def firefly(ctx):
    await ctx.send("✨ firefly! little lights in the dark!")

@bot.command()
async def moth(ctx):
    await ctx.send("🦋 moth! drawn to the flame! like you to embers!")

@bot.command()
async def cicada(ctx):
    await ctx.send("🦗 cicada! loud and annoying! summer vibes!")

@bot.command()
async def cricket(ctx):
    await ctx.send("🦗 cricket! chirp chirp! good luck in some places!")

@bot.command()
async def grasshopper(ctx):
    await ctx.send("🦗 grasshopper! leap of faith!")

@bot.command()
async def prayingmantis(ctx):
    await ctx.send("🦗 praying mantis! patience and stillness!")

@bot.command()
async def beetle(ctx):
    await ctx.send("🪲 beetle! scarab means rebirth!")

@bot.command()
async def scarab(ctx):
    await ctx.send("🪲 scarab! ancient egyptian symbol of rebirth!")

@bot.command()
async def dungbeetle(ctx):
    await ctx.send("💩🪲 dung beetle! rolls poop! nature is weird!")

@bot.command()
async def ant(ctx):
    await ctx.send("🐜 ant! teamwork makes the dream work!")

@bot.command()
async def beehive(ctx):
    await ctx.send("🐝 beehive! busy bees making honey!")

@bot.command()
async def honey(ctx):
    await ctx.send("🍯 honey! sweet and golden!")

@bot.command()
async def beesting(ctx):
    await ctx.send("🐝 bee sting! ouch! that hurt!")

@bot.command()
async def wasp(ctx):
    await ctx.send("🐝 wasp! angry! why do they exist?!")

@bot.command()
async def hornet(ctx):
    await ctx.send("🐝 hornet! even angrier! run!")

@bot.command()
async def scorpion(ctx):
    await ctx.send("🦂 scorpion! venomous! desert vibes!")

@bot.command()
async def snake2(ctx):
    await ctx.send("🐍 snake! sssss! some are venomous!")

@bot.command()
async def cobra(ctx):
    await ctx.send("🐍 cobra! hood up! dangerous!")

@bot.command()
async def python2(ctx):
    await ctx.send("🐍 python! not the programming language! constrictor!")

@bot.command()
async def anaconda(ctx):
    await ctx.send("🐍 anaconda! my anaconda don't want none!")

@bot.command()
async def boa(ctx):
    await ctx.send("🐍 boa constrictor! squeeze!")

@bot.command()
async def viper(ctx):
    await ctx.send("🐍 viper! venomous! watch out!")

@bot.command()
async def rattlesnake(ctx):
    await ctx.send("🐍 rattlesnake! rattle rattle! warning!")

@bot.command()
async def komodo(ctx):
    await ctx.send("🦎 komodo dragon! venomous bite! big lizard!")

@bot.command()
async def gecko(ctx):
    await ctx.send("🦎 gecko! small lizard! insurance mascot!")

@bot.command()
async def chameleon(ctx):
    await ctx.send("🦎 chameleon! changes colors! blend in!")

@bot.command()
async def iguana(ctx):
    await ctx.send("🦎 iguana! big lizard! vegetarian!")

@bot.command()
async def turtle(ctx):
    await ctx.send("🐢 turtle! slow and steady wins the race!")

@bot.command()
async def tortoise(ctx):
    await ctx.send("🐢 tortoise! land turtle! very slow!")

@bot.command()
async def crocodile(ctx):
    await ctx.send("🐊 crocodile! snap snap! dangerous!")

@bot.command()
async def alligator(ctx):
    await ctx.send("🐊 alligator! see you later! florida vibes!")

@bot.command()
async def frog2(ctx):
    await ctx.send("🐸 frog! ribbit ribbit! prince potential!")

@bot.command()
async def toad(ctx):
    await ctx.send("🐸 toad! wartier than frogs! still cute!")

@bot.command()
async def salamander(ctx):
    await ctx.send("🦎 salamander! fire spirit! amphibian!")

@bot.command()
async def newt(ctx):
    await ctx.send("🦎 newt! tiny salamander! eye of newt!")

@bot.command()
async def axolotl(ctx):
    await ctx.send("🦎 axolotl! cute! regenerates! minecraft!")

@bot.command()
async def platypus(ctx):
    await ctx.send("🦆 platypus! duck bill! beaver tail! venomous! weird!")

@bot.command()
async def echidna(ctx):
    await ctx.send("🦔 echidna! spiny anteater! knuckles!")

@bot.command()
async def kangaroo(ctx):
    await ctx.send("🦘 kangaroo! hop hop! pouch baby!")

@bot.command()
async def koala(ctx):
    await ctx.send("🐨 koala! sleeps 20 hours! eucalyptus only!")

@bot.command()
async def wombat2(ctx):
    await ctx.send("🐻 wombat! cube poop! australia!")

@bot.command()
async def tasmanian(ctx):
    await ctx.send("👿 tasmanian devil! spinny! aggressive!")

@bot.command()
async def dingo(ctx):
    await ctx.send("🐕 dingo! ate my baby! australia!")

@bot.command()
async def emu(ctx):
    await ctx.send("🐦 emu! won a war against australia! true story!")

@bot.command()
async def cassowary(ctx):
    await ctx.send("🐦 cassowary! most dangerous bird! kick!")

@bot.command()
async def kiwi(ctx):
    await ctx.send("🥝 kiwi! flightless! new zealand!")

@bot.command()
async def kakapo(ctx):
    await ctx.send("🦜 kakapo! flightless parrot! booming!")

@bot.command()
async def penguin(ctx):
    await ctx.send("🐧 penguin! waddle waddle! antarctica!")

@bot.command()
async def puffin(ctx):
    await ctx.send("🐦 puffin! colorful beak! clown of the sea!")

@bot.command()
async def albatross(ctx):
    await ctx.send("🐦 albatross! huge wingspan! sailors' superstition!")

@bot.command()
async def seagull(ctx):
    await ctx.send("🐦 seagull! mine mine mine! steals food!")

@bot.command()
async def pelican(ctx):
    await ctx.send("🐦 pelican! big beak! can hold lots!")

@bot.command()
async def flamingo(ctx):
    await ctx.send("🦩 flamingo! pink! stands on one leg!")

@bot.command()
async def peacock(ctx):
    await ctx.send("🦚 peacock! beautiful feathers! show off!")

@bot.command()
async def swan(ctx):
    await ctx.send("🦢 swan! elegant! aggressive! don't mess with them!")

@bot.command()
async def goose(ctx):
    await ctx.send("🦢 goose! honk honk! territorial! scary!")

@bot.command()
async def duck(ctx):
    await ctx.send("🦆 duck! quack quack! bread!")

@bot.command()
async def chicken2(ctx):
    await ctx.send("🐔 chicken! cluck cluck! why did it cross the road?")

@bot.command()
async def rooster(ctx):
    await ctx.send("🐓 rooster! cock-a-doodle-doo! early wake up!")

@bot.command()
async def turkey2(ctx):
    await ctx.send("🦃 turkey! gobble gobble! thanksgiving dinner!")

@bot.command()
async def pigeon(ctx):
    await ctx.send("🐦 pigeon! city bird! coo coo! rats with wings!")

@bot.command()
async def dove(ctx):
    await ctx.send("🕊️ dove! peace! love! harmony!")

@bot.command()
async def hawk(ctx):
    await ctx.send("🦅 hawk! sharp eyes! predator!")

@bot.command()
async def eagle(ctx):
    await ctx.send("🦅 eagle! freedom! america! screech!")

@bot.command()
async def falcon(ctx):
    await ctx.send("🦅 falcon! fast! dive! peregrine!")

@bot.command()
async def owl2(ctx):
    await ctx.send("🦉 owl! wise! hoot hoot! night hunter!")

@bot.command()
async def vulture(ctx):
    await ctx.send("🦅 vulture! scavenger! cleans up!")

@bot.command()
async def condor(ctx):
    await ctx.send("🦅 condor! huge! andes mountains!")

@bot.command()
async def stork(ctx):
    await ctx.send("🐦 stork! delivers babies! long legs!")

@bot.command()
async def heron(ctx):
    await ctx.send("🐦 heron! stands still! strikes fast!")

@bot.command()
async def crane(ctx):
    await ctx.send("🐦 crane! graceful! origami! japan!")

@bot.command()
async def ostrich(ctx):
    await ctx.send("🐦 ostrich! can't fly! fast runner! head in sand!")

@bot.command()
async def hummingbird(ctx):
    await ctx.send("🐦 hummingbird! tiny! fast wings! nectar!")

@bot.command()
async def woodpecker(ctx):
    await ctx.send("🐦 woodpecker! peck peck peck! headache!")

@bot.command()
async def kingfisher(ctx):
    await ctx.send("🐦 kingfisher! dives for fish! colorful!")

@bot.command()
async def toucan(ctx):
    await ctx.send("🐦 toucan! big beak! fruit loops!")

@bot.command()
async def parrot(ctx):
    await ctx.send("🦜 parrot! squawk! repeats words! pirate!")

@bot.command()
async def macaw(ctx):
    await ctx.send("🦜 macaw! big parrot! colorful! rainforest!")

@bot.command()
async def cockatoo(ctx):
    await ctx.send("🦜 cockatoo! crest! loud! australia!")

@bot.command()
async def cockatiel(ctx):
    await ctx.send("🦜 cockatiel! small crest! cute!")

@bot.command()
async def budgie(ctx):
    await ctx.send("🦜 budgie! small parakeet! popular pet!")

@bot.command()
async def canary(ctx):
    await ctx.send("🐦 canary! sings! coal mine warning!")

@bot.command()
async def finch(ctx):
    await ctx.send("🐦 finch! small! darwin studied them!")

@bot.command()
async def sparrow(ctx):
    await ctx.send("🐦 sparrow! common! small! everywhere!")

@bot.command()
async def crow2(ctx):
    await ctx.send("🐦‍⬛ crow! smart! tool user! ominous!")

@bot.command()
async def magpie(ctx):
    await ctx.send("🐦 magpie! steals shiny things! chatty!")

@bot.command()
async def jay(ctx):
    await ctx.send("🐦 jay! blue! noisy! forest!")

@bot.command()
async def cardinal(ctx):
    await ctx.send("🐦 cardinal! red! state bird! pretty!")

@bot.command()
async def bluebird(ctx):
    await ctx.send("🐦 bluebird! blue! happiness symbol!")

@bot.command()
async def robin(ctx):
    await ctx.send("🐦 robin! red breast! spring!")

@bot.command()
async def nightingale(ctx):
    await ctx.send("🐦 nightingale! beautiful song! night singer!")

@bot.command()
async def mockingbird(ctx):
    await ctx.send("🐦 mockingbird! mimics sounds! to kill one is a sin!")

@bot.command()
async def lark(ctx):
    await ctx.send("🐦 lark! sings while flying! early riser!")

@bot.command()
async def wren(ctx):
    await ctx.send("🐦 wren! tiny! loud song! brown!")

@bot.command()
async def thrush(ctx):
    await ctx.send("🐦 thrush! spotted breast! songbird!")

@bot.command()
async def blackbird(ctx):
    await ctx.send("🐦‍⬛ blackbird! beatles song! yellow beak!")

@bot.command()
async def starling(ctx):
    await ctx.send("🐦 starling! murmurations! invasive!")

@bot.command()
async def grackle(ctx):
    await ctx.send("🐦 grackle! iridescent! loud! texas!")

@bot.command()
async def meadowlark(ctx):
    await ctx.send("🐦 meadowlark! yellow! prairie! state bird!")

@bot.command()
async def oriole(ctx):
    await ctx.send("🐦 oriole! orange and black! baseball!")

@bot.command()
async def tanager(ctx):
    await ctx.send("🐦 tanager! red! tropical! pretty!")

@bot.command()
async def warbler(ctx):
    await ctx.send("🐦 warbler! small! colorful! migratory!")

@bot.command()
async def vireo(ctx):
    await ctx.send("🐦 vireo! small! eye ring! persistent singer!")

@bot.command()
async def grosbeak(ctx):
    await ctx.send("🐦 grosbeak! big beak! seed eater!")

@bot.command()
async def bunting(ctx):
    await ctx.send("🐦 bunting! colorful! indigo! painted!")

@bot.command()
async def towhee(ctx):
    await ctx.send("🐦 towhee! rufous sided! scratch feeder!")

@bot.command()
async def thrasher(ctx):
    await ctx.send("🐦 thrasher! brown! mimics! long tail!")

@bot.command()
async def catbird(ctx):
    await ctx.send("🐦 catbird! mews! gray! secretive!")

@bot.command()
async def shrike(ctx):
    await ctx.send("🐦 shrike! butcher bird! impales prey!")

@bot.command()
async def kingbird(ctx):
    await ctx.send("🐦 kingbird! tyrant flycatcher! attacks hawks!")

@bot.command()
async def phoebe(ctx):
    await ctx.send("🐦 phoebe! says its name! tail wags!")

@bot.command()
async def flycatcher(ctx):
    await ctx.send("🐦 flycatcher! catches flies! midair!")

@bot.command()
async def swallow(ctx):
    await ctx.send("🐦 swallow! forked tail! aerial! mud nest!")

@bot.command()
async def martin(ctx):
    await ctx.send("🐦 martin! purple! colony! gourd houses!")

@bot.command()
async def swift(ctx):
    await ctx.send("🐦 swift! fast! never lands! almost!")

@bot.command()
async def nighthawk(ctx):
    await ctx.send("🐦 nighthawk! dusk! booming! city nests!")

@bot.command()
async def whippoorwill(ctx):
    await ctx.send("🐦 whippoorwill! says name! night! folklore!")

@bot.command()
async def chuck(ctx):
    await ctx.send("🐦 chuck-will's-widow! similar! southern!")

@bot.command()
async def poorwill(ctx):
    await ctx.send("🐦 poorwill! poor will! hibernates!")

@bot.command()
async def nightjar(ctx):
    await ctx.send("🐦 nightjar! night! jar? weird name!")

@bot.command()
async def potoo(ctx):
    await ctx.send("🐦 potoo! weird! big eyes! camouflage!")

@bot.command()
async def frogmouth(ctx):
    await ctx.send("🐦 frogmouth! wide mouth! australia!"
)

# ==================== HELP COMMAND WITH PAGES ====================
@bot.command()
async def help(ctx, page: int = 1):
    if page == 1:
        embed = discord.Embed(title="flame bot commands - page 1/3", color=0xff6b35)
        embed.add_field(name="economy", value="embers, daily, streak, beg, scam, invest, heist, loan, repay, burn, send, deposit, withdraw, rob, work, crime, slut, fish, hunt, dig, search, postmeme, buy, shop, inventory, sell, rich, poor, level, xp, leaderboard, bank, tax, lottery, slots, blackjack, roulette, horse", inline=False)
        embed.add_field(name="creatures", value="summon, cage, release, feed, neglect, mood, evolve, breed, sacrifice, rename, favorite, trade, auction, bid, inspect, adopt, kidnap", inline=False)
        embed.add_field(name="combat", value="duel, raid, ambush, defend, berserk, bribe, flee, taunt, combo, revive, wager, rank", inline=False)
        embed.add_field(name="gambling", value="dice, shells, flip, spin, surge, vault, pick, chase, chamber, rig", inline=False)
        embed.add_field(name="social", value="marry, divorce, will, cult, betray, tribute, roast, confess", inline=False)
    elif page == 2:
        embed = discord.Embed(title="flame bot commands - page 2/3", color=0xff6b35)
        embed.add_field(name="utility", value="tutorial, stats, server, global, settings, cooldowns, changelog", inline=False)
        embed.add_field(name="weird", value="dream, curse, bless, time, weather, oracle, mimic, glitch, lore, quit", inline=False)
        embed.add_field(name="moderation", value="kick, ban, unban, mute, unmute, warn, warnings, clearwarns, purge, nick, slowmode, lock, unlock, addrole, removerole, createrole, deleterole", inline=False)
        embed.add_field(name="admin", value="give, set, remove, wipe (owner only)", inline=False)
        embed.add_field(name="fun", value="pet, hug, slap, punch, kiss, kill, poke, tickle, wave, wink, dance, cry, laugh, sleep, eat, drink, sing, rap, joke, fact, quote, meme, cat, dog, bird, fishy", inline=False)
    elif page == 3:
        embed = discord.Embed(title="flame bot commands - page 3/3", color=0xff6b35)
        embed.add_field(name="games", value="rps, ttt, connect4, hangman, guess, trivia, wouldyourather, truth, dare", inline=False)
        embed.add_field(name="text", value="reverse, len, uppercase, lowercase, mock, clap, vaporwave, emojify, spoiler, ascii, textart, banner, zalgo, tiny, wide, strikethrough, bold, italic, underline, code, inlinecode, quoteblock", inline=False)
        embed.add_field(name="info", value="avatar, userinfo, roleinfo, channelinfo, botinfo, ping, uptime", inline=False)
        embed.add_field(name="reactions", value="compliment, insult, motivation, bored, fortune, magic8ball, rate, howgay, howsimp, howsmart, howdumb, howlucky, ship", inline=False)
        embed.add_field(name="meme", value="stonks, notstonks, hold, pump, dump, moon, lambo, yacht, mansion, brokeboy, richboy, ballin, flex, brokecheck, flexon, humble, grind, hustle, grindset, sigma, alpha, beta, omega, chad, virgin, gigachad, soyjack, wojak, doomer, bloomer, coomer, consoomer, boomer, zoomer, millennial, genz, genalpha, skibidi, sigmaface, mewing, looksmaxxing, mog, heightmaxx, gymmaxx, moneymaxx, statusmaxx, rizz, aura, gyatt, ohio, grimaceshake, quandale, goofy, ahh, bruh, bruhmoment, cringe, based, redpilled, bluepilled, blackpilled, whitepilled, greenpilled, purplepilled, yellowpilled, orangepilled, pinkpilled, graypilled, brownpilled, copium, hopium, delusion, realitycheck, wakeup, matrix, redpill, bluepill, neo, morpheus, trinity, agent, smith, spoon, simulation, npc, maincharacter, sidecharacter, extras, protagonist, antagonist, villain, hero, sidekick, mentor, loveinterest, comicrelief, tragicbackstory, plotarmor, plottwist, cliffhanger, sequel, prequel, reboot, directorcut, bloopers, credits, oscar, grammy, emmy, nobel, pulitzer, trophy, medal, crown, king, queen, emperor, god, mortal, demigod, titan, giant, dwarf, elf, orc, goblin, troll, fairy, wizard, witch, warlock, sorcerer, druid, bard, rogue, paladin, cleric, monk, ranger, barbarian, fighter, artificer, bloodhunter, dungeonmaster, criticalhit, criticalfail, nat20, nat1, initiative, perception, stealth, persuasion, intimidation, deception, insight, investigation, arcana, history, nature, religion, survival, medicine, athletics, acrobatics, sleight, performance, animalhandling, longrest, shortrest, leveledup, exp, skilltree, respec, multiclass, feat, spellslot, cantrip, fireball, lightningbolt, healingword, curewounds, raisedead, resurrection, trueresurrection, wish, simulacrum, clone, polymorph, wildshape, rage2, reckless, sneakattack, cunningaction, evasion, uncannydodge, secondwind, actionsurge, extraattack, indomitable, channeldivinity, divinesmite, layonhands, auraofprotection, findstealth, findgreaterstealth, eldritchblast, hex, agonizingblast, repellingblast, pactweapon, pactofthechain, pactofthetome, pactoftheblade, invocations, maskofmanyfaces, devilssight, agonizing, patron, boon, legendary, lairaction, regionaleffects, mythic, artifact, relic, legendaryresistance, magicitem, identify, attunement, curseditem, removecurse, dispelmagic, counterspell, antimagic, deadmagic, wildmagic, tidesofchaos, bendluck, harrowing, darkgift, corruption, madness, sanity, insanity, phobia, paranoia, hallucination, delusion2, amnesia, multiplepersonalities, possessed, exorcism, holywater, crucifix, garlic, silver, woodenstake, sunlight, moonlight, fullmoon, newmoon, bloodmoon, eclipse, constellations, shootingstar, aurora, rainbow, potofgold, leprechaun, shamrock, fourleafclover, horseshoe, rabbitfoot, wishbone, penny, headsup, knockwood, blackcat, brokenmirror, ladder, friday13, spillingsalt, umbrella, crow, raven, owl, bat2, spider2, ladybug, butterfly, dragonfly, firefly, moth, cicada, cricket, grasshopper, prayingmantis, beetle, scarab, dungbeetle, ant, beehive, honey, beesting, wasp, hornet, scorpion, snake2, cobra, python2, anaconda, boa, viper, rattlesnake, komodo, gecko, chameleon, iguana, turtle, tortoise, crocodile, alligator, frog2, toad, salamander, newt, axolotl, platypus, echidna, kangaroo, koala, wombat2, tasmanian, dingo, emu, cassowary, kiwi, kakapo, penguin, puffin, albatross, seagull, pelican, flamingo, peacock, swan, goose, duck, chicken2, rooster, turkey2, pigeon, dove, hawk, eagle, falcon, owl2, vulture, condor, stork, heron, crane, ostrich, hummingbird, woodpecker, kingfisher, toucan, parrot, macaw, cockatoo, cockatiel, budgie, canary, finch, sparrow, crow2, magpie, jay, cardinal, bluebird, robin, nightingale, mockingbird, lark, wren, thrush, blackbird, starling, grackle, meadowlark, oriole, tanager, warbler, vireo, grosbeak, bunting, towhee, thrasher, catbird, shrike, kingbird, phoebe, flycatcher, swallow, martin, swift, nighthawk, whippoorwill, chuck, poorwill, nightjar, potoo, frogmouth, present, open, gift, tradeoffer, f, respects, oof, yikes, ripbozo, l, w, dub, dubnation, ratio, cope, seethe, mald, touchgrass, skillissue, gitgud, ez, gg, ggez, rekt, destroyed, demolished, atoms, thanos, snap, balanced, inevitable, ironman, loveyou3000, assemble, onyourleft, hulk, thor, captain, spiderman, batman, superman, flash, wonderwoman, joker, bane, darkknight, rises, whyserious, harley, puddin, batmobile, utilitybelt, gotham, arkham, wayne, stark, jarvis, friday_ai, ultron, vision, wandavision, agatha, multiverse, whatif, zombie, vampire, werewolf, frankenstein, mummy, skeleton, pumpkin, candy, trick, treat, gm, gn, brb, gtg, idk, same, facts, cap, nocap, bet, fr, ongod, sheesh, sus, imposter, vented, emergency, task, ejected, crewmate, dead, ghost, reviveme, rip, afk, back, remind, timer, calc, math, square, sqrt, randomnum, hexconvert, binconvert, base64, decode64, morse, password, uuid, hashmd5, hashsha256, shorten, qr, translate, define, synonym, antonym, spell, count, reversecount, even, prime, fibonacci, factorial, pi, e, goldenratio, convert, temp, color, rgb, gradient", inline=False)
    else:
        await ctx.send("use f help 1, f help 2, or f help 3")
        return
    embed.set_footer(text="prefix: f or flame (space required) | currency: embers | made by justaflamewithfragz")
    await ctx.send(embed=embed)

# ==================== RUN BOT ====================
if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN environment variable not set!")
        print("Set it in Railway or your environment variables.")
    else:
        bot.run(TOKEN)
