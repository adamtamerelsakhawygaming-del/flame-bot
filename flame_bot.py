import discord
from discord.ext import commands
import json
import random
import asyncio
import datetime
import os
import math
from collections import defaultdict

# ========== CONFIG ==========
OWNER_ID = 1444293963812180120

intents = discord.Intents.all()

class FlameBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None
        )
        self.data = defaultdict(lambda: {
            "embers": 0, "bank": 0, "streak": 0, "last_daily": None,
            "creatures": [], "married_to": None, "inventory": [],
            "xp": 0, "level": 1, "wins": 0, "losses": 0,
            "loans": 0, "cult": None, "cooldowns": {}, "will_to": None
        })
        self.load_data()

    def get_prefix(self, bot, message):
        if message.content.startswith("f "):
            return "f "
        elif message.content.startswith("flame "):
            return "flame "
        return commands.when_mentioned(bot, message)

    def load_data(self):
        try:
            with open("flame_data.json", "r") as f:
                data = json.load(f)
                for k, v in data.items():
                    self.data[k] = v
        except:
            pass

    def save_data(self):
        with open("flame_data.json", "w") as f:
            json.dump(dict(self.data), f, indent=2)

    async def on_ready(self):
        print(f"flame bot online as {self.user}")
        await self.change_presence(activity=discord.Game(name="f help"))

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("nah you don't have perms for that")
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("you forgot something, check f help")
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send("that argument doesn't make sense, try again")
            return
        print(f"error: {error}")

bot = FlameBot()

# ========== UTILS ==========

def get_user_data(user_id):
    uid = str(user_id)
    if uid not in bot.data:
        bot.data[uid] = {
            "embers": 0, "bank": 0, "streak": 0, "last_daily": None,
            "creatures": [], "married_to": None, "inventory": [],
            "xp": 0, "level": 1, "wins": 0, "losses": 0,
            "loans": 0, "cult": None, "cooldowns": {}, "will_to": None
        }
    return bot.data[uid]

def save():
    bot.save_data()

def is_owner(ctx):
    return ctx.author.id == OWNER_ID

def check_cooldown(user_id, cmd, hours=0, minutes=0):
    uid = str(user_id)
    data = get_user_data(user_id)
    now = datetime.datetime.now()
    key = f"cd_{cmd}"
    if key in data["cooldowns"]:
        last = datetime.datetime.fromisoformat(data["cooldowns"][key])
        wait = datetime.timedelta(hours=hours, minutes=minutes)
        if now - last < wait:
            remaining = wait - (now - last)
            return False, remaining
    data["cooldowns"][key] = now.isoformat()
    save()
    return True, None

def add_xp(user_id, amount):
    data = get_user_data(user_id)
    data["xp"] += amount
    needed = data["level"] * 100
    while data["xp"] >= needed:
        data["xp"] -= needed
        data["level"] += 1
        needed = data["level"] * 100
    save()

def has_perm(ctx, perm):
    if ctx.author.id == OWNER_ID:
        return True
    if ctx.author.guild_permissions.administrator:
        return True
    perms = ctx.author.guild_permissions
    return getattr(perms, perm, False)

# ========== ADMIN COMMANDS ==========

@bot.command(name="give")
async def admin_give(ctx, amount: int, member: discord.Member = None):
    if not is_owner(ctx):
        await ctx.send("you can't use this command as ur not the bot owner.")
        return
    member = member or ctx.author
    data = get_user_data(member.id)
    data["embers"] += amount
    save()
    await ctx.send(f"gave {member.mention} {amount} embers. their total is now {data['embers']}")

@bot.command(name="set")
async def admin_set(ctx, amount: int, member: discord.Member = None):
    if not is_owner(ctx):
        await ctx.send("you can't use this command as ur not the bot owner.")
        return
    member = member or ctx.author
    data = get_user_data(member.id)
    data["embers"] = amount
    save()
    await ctx.send(f"set {member.mention}'s embers to {amount}")

@bot.command(name="remove")
async def admin_remove(ctx, amount: int, member: discord.Member = None):
    if not is_owner(ctx):
        await ctx.send("you can't use this command as ur not the bot owner.")
        return
    member = member or ctx.author
    data = get_user_data(member.id)
    data["embers"] = max(0, data["embers"] - amount)
    save()
    await ctx.send(f"removed {amount} embers from {member.mention}. they now have {data['embers']}")

@bot.command(name="wipe")
async def admin_wipe(ctx, member: discord.Member):
    if not is_owner(ctx):
        await ctx.send("you can't use this command as ur not the bot owner.")
        return
    uid = str(member.id)
    if uid in bot.data:
        del bot.data[uid]
        save()
        await ctx.send(f"wiped all data for {member.mention}. they're back to zero")
    else:
        await ctx.send("that user has no data to wipe")

# ========== ECONOMY COMMANDS ==========

@bot.command()
async def embers(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = get_user_data(member.id)
    await ctx.send(f"{member.mention} has {data['embers']} embers | bank: {data['bank']}")

@bot.command()
async def daily(ctx):
    data = get_user_data(ctx.author.id)
    ok, remaining = check_cooldown(ctx.author.id, "daily", hours=20)
    if not ok:
        hrs = int(remaining.total_seconds() // 3600)
        mins = int((remaining.total_seconds() % 3600) // 60)
        await ctx.send(f"chill, come back in {hrs}h {mins}m")
        return
    base = random.randint(100, 500)
    streak_bonus = data["streak"] * 50
    amount = base + streak_bonus
    data["embers"] += amount
    data["streak"] += 1
    save()
    add_xp(ctx.author.id, 10)
    await ctx.send(f"daily claimed! you got {amount} embers (streak: {data['streak']}x) | total: {data['embers']}")

@bot.command()
async def streak(ctx):
    data = get_user_data(ctx.author.id)
    await ctx.send(f"your daily streak is {data['streak']} days, keep it up")

@bot.command()
async def beg(ctx):
    ok, _ = check_cooldown(ctx.author.id, "beg", minutes=2)
    if not ok:
        await ctx.send("you just begged, give it a rest")
        return
    if random.random() < 0.3:
        await ctx.send("nobody gave you anything. skill issue.")
        return
    amount = random.randint(10, 100)
    data = get_user_data(ctx.author.id)
    data["embers"] += amount
    save()
    add_xp(ctx.author.id, 2)
    responses = [
        f"a random stranger tossed you {amount} embers",
        f"you found {amount} embers in a dumpster. congrats i guess",
        f"someone felt bad and gave you {amount} embers",
        f"you begged so hard you got {amount} embers. proud of you?"
    ]
    await ctx.send(random.choice(responses))

@bot.command()
async def scam(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("you can't scam yourself")
        return
    ok, _ = check_cooldown(ctx.author.id, "scam", minutes=5)
    if not ok:
        await ctx.send("chill with the scams, you're being watched")
        return
    victim_data = get_user_data(member.id)
    if victim_data["embers"] < 50:
        await ctx.send(f"{member.mention} is broke, not worth scamming")
        return
    if random.random() < 0.4:
        amount = random.randint(20, min(200, victim_data["embers"]))
        victim_data["embers"] -= amount
        scammer_data = get_user_data(ctx.author.id)
        scammer_data["embers"] += amount
        save()
        await ctx.send(f"you scammed {member.mention} out of {amount} embers. you're a menace.")
    else:
        fine = random.randint(10, 50)
        scammer_data = get_user_data(ctx.author.id)
        scammer_data["embers"] = max(0, scammer_data["embers"] - fine)
        save()
        await ctx.send(f"you got caught scamming and lost {fine} embers. {member.mention} is laughing at you.")

@bot.command()
async def invest(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("you're broke, you don't have that much")
        return
    if amount < 50:
        await ctx.send("minimum investment is 50 embers, stop being cheap")
        return
    data["embers"] -= amount
    multiplier = random.uniform(0.5, 2.5)
    result = int(amount * multiplier)
    data["embers"] += result
    save()
    add_xp(ctx.author.id, 15)
    if multiplier > 1.5:
        await ctx.send(f"BIG W! your {amount} embers turned into {result}! you're a genius investor")
    elif multiplier > 1:
        await ctx.send(f"nice, turned {amount} into {result} embers. decent profit")
    else:
        await ctx.send(f"RIP. you turned {amount} into {result} embers. that's rough buddy.")

@bot.command()
async def heist(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("you can't rob yourself")
        return
    ok, _ = check_cooldown(ctx.author.id, "heist", hours=1)
    if not ok:
        await ctx.send("the cops are still looking for you, lay low")
        return
    victim = get_user_data(member.id)
    if victim["embers"] < 100:
        await ctx.send(f"{member.mention} is too broke to rob. find a bigger target")
        return
    if random.random() < 0.35:
        amount = random.randint(50, min(500, victim["embers"]))
        victim["embers"] -= amount
        robber = get_user_data(ctx.author.id)
        robber["embers"] += amount
        save()
        await ctx.send(f"heist successful! you stole {amount} embers from {member.mention}! criminal mastermind!")
    else:
        fine = random.randint(25, 100)
        robber = get_user_data(ctx.author.id)
        robber["embers"] = max(0, robber["embers"] - fine)
        save()
        await ctx.send(f"busted! you got caught and fined {fine} embers. {member.mention} called the cops.")

@bot.command()
async def loan(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if data["loans"] > 0:
        await ctx.send("you already owe money, pay that back first")
        return
    if amount > 10000:
        await ctx.send("the bank ain't giving you that much, max is 10k")
        return
    data["embers"] += amount
    data["loans"] = amount
    save()
    await ctx.send(f"loan approved! you got {amount} embers. don't forget to pay it back or the bank will come for you")

@bot.command()
async def repay(ctx, amount: int = None):
    data = get_user_data(ctx.author.id)
    if data["loans"] == 0:
        await ctx.send("you don't owe anything, why you tryna pay")
        return
    amount = amount or data["loans"]
    if amount > data["embers"]:
        await ctx.send("you're too broke to pay that back")
        return
    actual = min(amount, data["loans"])
    data["embers"] -= actual
    data["loans"] -= actual
    save()
    await ctx.send(f"paid back {actual} embers. remaining debt: {data['loans']}")

@bot.command()
async def burn(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("you can't burn what you don't have")
        return
    data["embers"] -= amount
    save()
    await ctx.send(f"you burned {amount} embers. why? just why? you now have {data['embers']} left.")

@bot.command()
async def send(ctx, amount: int, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("sending money to yourself? that's just moving it from one pocket to another")
        return
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("you're too broke for that transfer")
        return
    msg = await ctx.send(f"are you sure you wanna send {amount} embers to {member.mention}? react check to confirm")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "✅":
            data["embers"] -= amount
            receiver = get_user_data(member.id)
            receiver["embers"] += amount
            save()
            await ctx.send(f"sent {amount} embers to {member.mention}! you're so generous")
        else:
            await ctx.send("transfer cancelled. smart move, keep your money")
    except asyncio.TimeoutError:
        await ctx.send("too slow, transfer cancelled")

# ========== CREATURES COMMANDS ==========

CREATURE_NAMES = ["blaze pup", "ember fox", "flame drake", "ash wolf", "spark cat", "inferno bird", "coal snake", "magma crab"]
CREATURE_TYPES = ["fire", "ash", "spark", "magma", "inferno", "ember"]

@bot.command()
async def summon(ctx):
    ok, _ = check_cooldown(ctx.author.id, "summon", hours=4)
    if not ok:
        await ctx.send("your summoning circle is still cooling down, wait a bit")
        return
    name = random.choice(CREATURE_NAMES)
    ctype = random.choice(CREATURE_TYPES)
    power = random.randint(10, 100)
    creature = {
        "name": name, "type": ctype, "power": power,
        "mood": 50, "evolution": 0, "favorite": False,
        "id": random.randint(1000, 9999)
    }
    data = get_user_data(ctx.author.id)
    data["creatures"].append(creature)
    save()
    add_xp(ctx.author.id, 20)
    await ctx.send(f"you summoned a {name} ({ctype} type, power: {power})! it's staring at you judgmentally.")

@bot.command()
async def cage(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            await ctx.send(f"you caged your {c['name']}. it's crying in there. you monster.")
            data["creatures"].remove(c)
            save()
            return
    await ctx.send("couldn't find that creature. did you make up the id?")

@bot.command()
async def release(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            await ctx.send(f"you released {c['name']} into the wild. it's free now. probably gonna get eaten but ok.")
            data["creatures"].remove(c)
            save()
            return
    await ctx.send("that creature doesn't exist, check your creatures with f creatures")

@bot.command()
async def feed(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            if data["embers"] < 20:
                await ctx.send("you're too broke to feed your pet, get some embers first")
                return
            data["embers"] -= 20
            c["mood"] = min(100, c["mood"] + 15)
            c["power"] += random.randint(1, 5)
            save()
            await ctx.send(f"you fed {c['name']}! mood: {c['mood']}/100, power: {c['power']}")
            return
    await ctx.send("creature not found. did you hallucinate it?")

@bot.command()
async def neglect(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            c["mood"] = max(0, c["mood"] - 20)
            save()
            await ctx.send(f"you neglected {c['name']}. mood dropped to {c['mood']}/100. you're a terrible owner.")
            return
    await ctx.send("can't neglect what doesn't exist")

@bot.command()
async def mood(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            moods = ["depressed", "sad", "meh", "happy", "ecstatic", "godlike"]
            mood_idx = min(5, c["mood"] // 17)
            await ctx.send(f"{c['name']} is feeling {moods[mood_idx]} ({c['mood']}/100)")
            return
    await ctx.send("creature not found")

@bot.command()
async def evolve(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            if c["power"] < 80:
                await ctx.send(f"{c['name']} is too weak to evolve. get its power up first")
                return
            if c["mood"] < 60:
                await ctx.send(f"{c['name']} is too sad to evolve. feed it or something")
                return
            c["evolution"] += 1
            c["power"] += random.randint(20, 50)
            c["name"] = f"mega {c['name']}"
            save()
            await ctx.send(f"{c['name']} evolved! new power: {c['power']}! it's beautiful!")
            return
    await ctx.send("that creature is imaginary, try again")

@bot.command()
async def breed(ctx, id1: int, id2: int):
    data = get_user_data(ctx.author.id)
    c1 = c2 = None
    for c in data["creatures"]:
        if c["id"] == id1: c1 = c
        if c["id"] == id2: c2 = c
    if not c1 or not c2:
        await ctx.send("one or both creatures don't exist. check your collection")
        return
    if data["embers"] < 100:
        await ctx.send("breeding costs 100 embers, you're too broke")
        return
    data["embers"] -= 100
    name = f"baby {c1['name'].split()[-1]}-{c2['name'].split()[-1]}"
    power = (c1["power"] + c2["power"]) // 2 + random.randint(-10, 20)
    ctype = random.choice([c1["type"], c2["type"]])
    baby = {"name": name, "type": ctype, "power": max(5, power), "mood": 70, "evolution": 0, "favorite": False, "id": random.randint(1000, 9999)}
    data["creatures"].append(baby)
    save()
    await ctx.send(f"a baby creature was born! meet {name} ({ctype}, power: {power})! so cute!")

@bot.command()
async def sacrifice(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            bonus = c["power"] * 2
            data["embers"] += bonus
            data["creatures"].remove(c)
            save()
            await ctx.send(f"you sacrificed {c['name']} and gained {bonus} embers. the dark gods are pleased. probably.")
            return
    await ctx.send("can't sacrifice what doesn't exist. try sacrificing your dignity instead")

@bot.command()
async def rename(ctx, creature_id: int, *, new_name: str):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            old = c["name"]
            c["name"] = new_name
            save()
            await ctx.send(f"renamed {old} to {new_name}! much better name tbh")
            return
    await ctx.send("creature not found. you sure you didn't dream it?")

@bot.command()
async def favorite(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            c["favorite"] = not c["favorite"]
            status = "favorited" if c["favorite"] else "unfavorited"
            await ctx.send(f"{c['name']} has been {status}!")
            save()
            return
    await ctx.send("creature not found")

@bot.command()
async def trade(ctx, member: discord.Member, your_id: int, their_id: int):
    if member.id == ctx.author.id:
        await ctx.send("trading with yourself? that's just swapping creatures with yourself")
        return
    your_data = get_user_data(ctx.author.id)
    their_data = get_user_data(member.id)
    your_c = next((c for c in your_data["creatures"] if c["id"] == your_id), None)
    their_c = next((c for c in their_data["creatures"] if c["id"] == their_id), None)
    if not your_c or not their_c:
        await ctx.send("one of those creatures doesn't exist. check again")
        return
    msg = await ctx.send(f"{member.mention}, {ctx.author.mention} wants to trade their {your_c['name']} for your {their_c['name']}. react check to accept!")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    def check(reaction, user):
        return user == member and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        if str(reaction.emoji) == "✅":
            your_data["creatures"].remove(your_c)
            their_data["creatures"].remove(their_c)
            your_data["creatures"].append(their_c)
            their_data["creatures"].append(your_c)
            save()
            await ctx.send(f"trade complete! {ctx.author.mention} got {their_c['name']} and {member.mention} got {your_c['name']}!")
        else:
            await ctx.send("trade rejected. awkward...")
    except asyncio.TimeoutError:
        await ctx.send("trade timed out. nobody wanted it apparently")

@bot.command()
async def auction(ctx, creature_id: int, starting_bid: int):
    data = get_user_data(ctx.author.id)
    creature = next((c for c in data["creatures"] if c["id"] == creature_id), None)
    if not creature:
        await ctx.send("you don't have that creature")
        return
    await ctx.send(f"auction started! {creature['name']} (power: {creature['power']}) | starting bid: {starting_bid} embers | type f bid {creature_id} <amount> to bid! auction ends in 60 seconds!")
    auction_data = {"creature": creature, "highest_bid": starting_bid, "highest_bidder": None, "active": True}
    bot.current_auction = auction_data
    await asyncio.sleep(60)
    auction_data["active"] = False
    if auction_data["highest_bidder"]:
        winner = auction_data["highest_bidder"]
        winner_data = get_user_data(winner.id)
        if winner_data["embers"] >= auction_data["highest_bid"]:
            winner_data["embers"] -= auction_data["highest_bid"]
            data["embers"] += auction_data["highest_bid"]
            data["creatures"].remove(creature)
            winner_data["creatures"].append(creature)
            save()
            await ctx.send(f"sold! {winner.mention} won {creature['name']} for {auction_data['highest_bid']} embers!")
        else:
            await ctx.send(f"{winner.mention} couldn't afford it. auction cancelled.")
    else:
        await ctx.send("nobody bid. your creature is worthless apparently")

@bot.command()
async def bid(ctx, creature_id: int, amount: int):
    if not hasattr(bot, "current_auction") or not bot.current_auction.get("active"):
        await ctx.send("no active auction right now")
        return
    auction = bot.current_auction
    if auction["creature"]["id"] != creature_id:
        await ctx.send("wrong auction bro")
        return
    data = get_user_data(ctx.author.id)
    if amount <= auction["highest_bid"]:
        await ctx.send(f"bid higher than {auction['highest_bid']} embers or go home")
        return
    if data["embers"] < amount:
        await ctx.send("you're too broke for that bid")
        return
    auction["highest_bid"] = amount
    auction["highest_bidder"] = ctx.author
    await ctx.send(f"{ctx.author.mention} bids {amount} embers! anyone higher?")

@bot.command()
async def inspect(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            embed = discord.Embed(title=c["name"], color=0xff4500)
            embed.add_field(name="type", value=c["type"])
            embed.add_field(name="power", value=c["power"])
            embed.add_field(name="mood", value=f"{c['mood']}/100")
            embed.add_field(name="evolution", value=c["evolution"])
            embed.add_field(name="favorite", value="yes" if c["favorite"] else "nah")
            embed.add_field(name="id", value=c["id"])
            await ctx.send(embed=embed)
            return
    await ctx.send("creature not found. it's a ghost?")

@bot.command()
async def adopt(ctx, member: discord.Member, creature_id: int):
    if member.id == ctx.author.id:
        await ctx.send("adopting your own creature? that's just... keeping it")
        return
    their_data = get_user_data(member.id)
    creature = next((c for c in their_data["creatures"] if c["id"] == creature_id), None)
    if not creature:
        await ctx.send("they don't have that creature")
        return
    msg = await ctx.send(f"{member.mention}, {ctx.author.mention} wants to adopt your {creature['name']}. react check to let them!")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    def check(reaction, user):
        return user == member and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "✅":
            your_data = get_user_data(ctx.author.id)
            their_data["creatures"].remove(creature)
            your_data["creatures"].append(creature)
            save()
            await ctx.send(f"{ctx.author.mention} adopted {creature['name']}! take good care of it!")
        else:
            await ctx.send("adoption denied. the creature stays")
    except asyncio.TimeoutError:
        await ctx.send("timed out. guess they don't want you to have it")

@bot.command()
async def kidnap(ctx, member: discord.Member, creature_id: int):
    ok, _ = check_cooldown(ctx.author.id, "kidnap", hours=2)
    if not ok:
        await ctx.send("the authorities are watching you, chill")
        return
    their_data = get_user_data(member.id)
    creature = next((c for c in their_data["creatures"] if c["id"] == creature_id), None)
    if not creature:
        await ctx.send("that creature doesn't exist over there")
        return
    if random.random() < 0.25:
        your_data = get_user_data(ctx.author.id)
        their_data["creatures"].remove(creature)
        your_data["creatures"].append(creature)
        save()
        await ctx.send(f"kidnap successful! you stole {creature['name']} from {member.mention}! you're going to hell for this.")
    else:
        fine = random.randint(50, 200)
        your_data = get_user_data(ctx.author.id)
        your_data["embers"] = max(0, your_data["embers"] - fine)
        save()
        await ctx.send(f"busted! you got caught trying to kidnap {creature['name']} and lost {fine} embers. {member.mention} pressed charges.")

@bot.command()
async def creatures(ctx):
    data = get_user_data(ctx.author.id)
    if not data["creatures"]:
        await ctx.send("you have no creatures. use f summon to get one!")
        return
    embed = discord.Embed(title=f"{ctx.author.name}'s creatures", color=0xff4500)
    for c in data["creatures"]:
        fav = "* " if c["favorite"] else ""
        embed.add_field(name=f"{fav}{c['name']} (id: {c['id']})", 
                       value=f"type: {c['type']} | power: {c['power']} | mood: {c['mood']}/100", inline=False)
    await ctx.send(embed=embed)

# ========== COMBAT COMMANDS ==========

@bot.command()
async def duel(ctx, member: discord.Member, wager: int = 0):
    if member.id == ctx.author.id:
        await ctx.send("dueling yourself? that's just shadow boxing")
        return
    if member.bot:
        await ctx.send("bots don't duel, they just calculate your demise")
        return
    data1 = get_user_data(ctx.author.id)
    data2 = get_user_data(member.id)
    if wager > 0:
        if data1["embers"] < wager or data2["embers"] < wager:
            await ctx.send("one of you is too broke for that wager")
            return
    msg = await ctx.send(f"{member.mention}, {ctx.author.mention} wants to duel! wager: {wager} embers. react sword to accept!")
    await msg.add_reaction("⚔️")
    await msg.add_reaction("❌")
    def check(reaction, user):
        return user == member and str(reaction.emoji) in ["⚔️", "❌"] and reaction.message.id == msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "❌":
            await ctx.send("they chickened out")
            return
    except asyncio.TimeoutError:
        await ctx.send("they didn't respond. probably scared")
        return
    p1_power = sum(c["power"] for c in data1["creatures"]) + random.randint(-20, 20)
    p2_power = sum(c["power"] for c in data2["creatures"]) + random.randint(-20, 20)
    if p1_power > p2_power:
        winner, loser = ctx.author, member
        wdata, ldata = data1, data2
    else:
        winner, loser = member, ctx.author
        wdata, ldata = data2, data1
    wdata["wins"] += 1
    ldata["losses"] += 1
    if wager > 0:
        wdata["embers"] += wager
        ldata["embers"] -= wager
    save()
    add_xp(winner.id, 25)
    await ctx.send(f"{winner.mention} wins! ({p1_power if winner == ctx.author else p2_power} vs {p2_power if winner == ctx.author else p1_power}) {loser.mention} took the L")

@bot.command()
async def raid(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("raiding yourself? that's just vandalizing your own house")
        return
    ok, _ = check_cooldown(ctx.author.id, "raid", hours=2)
    if not ok:
        await ctx.send("your raid crew is exhausted, give them a break")
        return
    attacker = get_user_data(ctx.author.id)
    defender = get_user_data(member.id)
    atk_power = sum(c["power"] for c in attacker["creatures"]) + random.randint(-10, 30)
    def_power = sum(c["power"] for c in defender["creatures"]) + random.randint(-10, 20)
    if atk_power > def_power:
        loot = random.randint(50, min(300, defender["embers"]))
        defender["embers"] -= loot
        attacker["embers"] += loot
        save()
        await ctx.send(f"raid successful! you raided {member.mention} and stole {loot} embers! their defenses were weak.")
    else:
        loss = random.randint(25, 100)
        attacker["embers"] = max(0, attacker["embers"] - loss)
        save()
        await ctx.send(f"raid failed! {member.mention}'s defenses were too strong! you lost {loss} embers retreating.")

@bot.command()
async def ambush(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("ambushing yourself? that's just surprising yourself in the mirror")
        return
    ok, _ = check_cooldown(ctx.author.id, "ambush", hours=3)
    if not ok:
        await ctx.send("you're too obvious right now, wait before ambushing again")
        return
    if random.random() < 0.4:
        attacker = get_user_data(ctx.author.id)
        victim = get_user_data(member.id)
        loot = random.randint(30, min(200, victim["embers"]))
        victim["embers"] -= loot
        attacker["embers"] += loot
        save()
        await ctx.send(f"ambush successful! you jumped {member.mention} in a dark alley and stole {loot} embers! nobody saw anything...")
    else:
        fine = random.randint(20, 80)
        attacker = get_user_data(ctx.author.id)
        attacker["embers"] = max(0, attacker["embers"] - fine)
        save()
        await ctx.send(f"ambush failed! {member.mention} was ready for you and you got fined {fine} embers. should've been sneakier.")

@bot.command()
async def defend(ctx):
    ok, _ = check_cooldown(ctx.author.id, "defend", hours=1)
    if not ok:
        await ctx.send("your defenses are already maxed out, chill")
        return
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        c["power"] += random.randint(2, 8)
    save()
    await ctx.send("you fortified your defenses! all creatures gained power! good luck getting raided now.")

@bot.command()
async def berserk(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("going berserk on yourself? that's just having a bad day")
        return
    ok, _ = check_cooldown(ctx.author.id, "berserk", hours=4)
    if not ok:
        await ctx.send("you're still recovering from your last rage fit")
        return
    attacker = get_user_data(ctx.author.id)
    if attacker["embers"] < 50:
        await ctx.send("going berserk costs 50 embers for the adrenaline shot")
        return
    attacker["embers"] -= 50
    victim = get_user_data(member.id)
    if random.random() < 0.5:
        damage = random.randint(100, 400)
        victim["embers"] = max(0, victim["embers"] - damage)
        save()
        await ctx.send(f"berserk mode! you absolutely demolished {member.mention} and they lost {damage} embers! calm down!")
    else:
        self_damage = random.randint(50, 150)
        attacker["embers"] = max(0, attacker["embers"] - self_damage)
        save()
        await ctx.send(f"you went too berserk and hurt yourself, losing {self_damage} embers. {member.mention} is laughing at you.")

@bot.command()
async def bribe(ctx, member: discord.Member, amount: int):
    if member.id == ctx.author.id:
        await ctx.send("bribing yourself? that's just paying yourself")
        return
    data = get_user_data(ctx.author.id)
    if data["embers"] < amount:
        await ctx.send("you're too broke to bribe anyone")
        return
    data["embers"] -= amount
    target = get_user_data(member.id)
    target["embers"] += amount
    save()
    await ctx.send(f"you bribed {member.mention} with {amount} embers. they're now your friend... probably.")

@bot.command()
async def flee(ctx):
    await ctx.send("you ran away! coward! but at least you're safe... for now.")

@bot.command()
async def taunt(ctx, member: discord.Member):
    taunts = [
        f"{member.mention} your creatures are weaker than my grandma's!",
        f"{member.mention} i've seen better fighters in a retirement home!",
        f"{member.mention} you're so broke even beggars pity you!",
        f"{member.mention} your mom called, she wants her embers back!",
        f"{member.mention} i've defeated tougher opponents in my sleep!"
    ]
    await ctx.send(random.choice(taunts))

@bot.command()
async def combo(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("comboing yourself? that's just hitting yourself twice")
        return
    ok, _ = check_cooldown(ctx.author.id, "combo", hours=2)
    if not ok:
        await ctx.send("your combo meter is recharging, wait a bit")
        return
    attacker = get_user_data(ctx.author.id)
    victim = get_user_data(member.id)
    hits = random.randint(2, 5)
    total = 0
    for i in range(hits):
        dmg = random.randint(20, 80)
        total += dmg
    victim["embers"] = max(0, victim["embers"] - total)
    save()
    await ctx.send(f"combo x{hits}! you hit {member.mention} {hits} times for {total} embers total! brutal!")

@bot.command()
async def revive(ctx):
    data = get_user_data(ctx.author.id)
    if data["embers"] < 200:
        await ctx.send("reviving costs 200 embers, you're too dead-broke")
        return
    data["embers"] -= 200
    for c in data["creatures"]:
        c["mood"] = 100
        c["power"] += random.randint(5, 15)
    save()
    await ctx.send("revived! all your creatures are back to full mood and stronger! you're unstoppable now!")

@bot.command()
async def wager(ctx, amount: int, member: discord.Member = None):
    if not member:
        await ctx.send("wager against who? the air?")
        return
    if member.id == ctx.author.id:
        await ctx.send("wagering against yourself? that's just losing money twice")
        return
    data1 = get_user_data(ctx.author.id)
    data2 = get_user_data(member.id)
    if data1["embers"] < amount or data2["embers"] < amount:
        await ctx.send("one of you can't afford that wager")
        return
    msg = await ctx.send(f"{member.mention}, {ctx.author.mention} wants to wager {amount} embers! react dice to accept!")
    await msg.add_reaction("🎲")
    await msg.add_reaction("❌")
    def check(reaction, user):
        return user == member and str(reaction.emoji) in ["🎲", "❌"] and reaction.message.id == msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "❌":
            await ctx.send("they declined. scared of losing?")
            return
    except asyncio.TimeoutError:
        await ctx.send("no response. they probably don't trust you")
        return
    roll1 = random.randint(1, 100)
    roll2 = random.randint(1, 100)
    if roll1 > roll2:
        data1["embers"] += amount
        data2["embers"] -= amount
        winner = ctx.author
        loser = member
    else:
        data1["embers"] -= amount
        data2["embers"] += amount
        winner = member
        loser = ctx.author
    save()
    await ctx.send(f"{ctx.author.mention} rolled {roll1} | {member.mention} rolled {roll2} | {winner.mention} wins {amount} embers! {loser.mention} lost it all")

@bot.command()
async def rank(ctx):
    data = get_user_data(ctx.author.id)
    total_power = sum(c["power"] for c in data["creatures"])
    rank_name = "novice"
    if total_power > 500: rank_name = "warrior"
    if total_power > 1000: rank_name = "knight"
    if total_power > 2000: rank_name = "champion"
    if total_power > 5000: rank_name = "legend"
    if total_power > 10000: rank_name = "god"
    await ctx.send(f"{ctx.author.mention} your combat rank is {rank_name}! total creature power: {total_power} | wins: {data['wins']} | losses: {data['losses']}")

# ========== GAMBLING COMMANDS ==========

@bot.command()
async def dice(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("you're too broke for that bet")
        return
    if amount < 10:
        await ctx.send("minimum bet is 10 embers, stop being cheap")
        return
    data["embers"] -= amount
    roll = random.randint(1, 6)
    if roll >= 4:
        winnings = amount * 2
        data["embers"] += winnings
        save()
        await ctx.send(f"you rolled a {roll}! you won {winnings} embers! let's goooo!")
    else:
        save()
        await ctx.send(f"you rolled a {roll}. you lost {amount} embers. skill issue tbh")

@bot.command()
async def shells(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("broke boy can't gamble")
        return
    data["embers"] -= amount
    shell = random.randint(1, 3)
    guess = random.randint(1, 3)
    if shell == guess:
        winnings = amount * 3
        data["embers"] += winnings
        save()
        await ctx.send(f"shell game! the ball was under shell {shell} and you guessed right! won {winnings} embers!")
    else:
        save()
        await ctx.send(f"the ball was under shell {shell}, you guessed {guess}. lost {amount} embers. better luck next time")

@bot.command()
async def flip(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("no embers no flip")
        return
    data["embers"] -= amount
    result = random.choice(["heads", "tails"])
    guess = random.choice(["heads", "tails"])
    if result == guess:
        winnings = amount * 2
        data["embers"] += winnings
        save()
        await ctx.send(f"it's {result}! you guessed right! won {winnings} embers!")
    else:
        save()
        await ctx.send(f"it's {result}, you guessed {guess}. lost {amount} embers. the coin hates you")

@bot.command()
async def spin(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("spinning air? you got no embers")
        return
    data["embers"] -= amount
    outcomes = [
        (0.5, "you got half back"),
        (1.0, "break even"),
        (1.5, "1.5x! decent"),
        (2.0, "2x! nice!"),
        (3.0, "3x! jackpot!"),
        (0.0, "nothing. rip.")
    ]
    weights = [30, 25, 20, 15, 8, 2]
    mult, msg = random.choices(outcomes, weights=weights)[0]
    winnings = int(amount * mult)
    data["embers"] += winnings
    save()
    if mult >= 2:
        await ctx.send(f"spin result: {msg} | you got {winnings} embers! fire!")
    elif mult >= 1:
        await ctx.send(f"spin result: {msg} | you got {winnings} embers. could be worse.")
    else:
        await ctx.send(f"spin result: {msg} | you got {winnings} embers. absolute devastation")

@bot.command()
async def surge(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("no surge without embers")
        return
    data["embers"] -= amount
    multiplier = 1.0
    for i in range(5):
        if random.random() < 0.5:
            multiplier += 0.3
        else:
            break
    winnings = int(amount * multiplier)
    data["embers"] += winnings
    save()
    if multiplier > 2:
        await ctx.send(f"surge! multiplier hit {multiplier:.1f}x! you got {winnings} embers! insane!")
    else:
        await ctx.send(f"surge ended at {multiplier:.1f}x. got {winnings} embers. mid tbh")

@bot.command()
async def vault(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("can't vault what you don't have")
        return
    data["embers"] -= amount
    data["bank"] += amount
    save()
    await ctx.send(f"deposited {amount} embers into your vault! safe and sound. total vault: {data['bank']}")

@bot.command()
async def pick(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("broke pickpocket")
        return
    data["embers"] -= amount
    if random.random() < 0.45:
        winnings = amount * 2 + random.randint(10, 50)
        data["embers"] += winnings
        save()
        await ctx.send(f"pickpocket success! you stole {winnings} embers! you're a menace to society!")
    else:
        fine = random.randint(20, amount)
        data["embers"] = max(0, data["embers"] - fine)
        save()
        await ctx.send(f"caught pickpocketing! lost {fine} embers. the victim beat you up.")

@bot.command()
async def chase(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("chasing yourself? that's just running in circles")
        return
    ok, _ = check_cooldown(ctx.author.id, "chase", minutes=10)
    if not ok:
        await ctx.send("you're still out of breath from the last chase")
        return
    if random.random() < 0.4:
        victim = get_user_data(member.id)
        loot = random.randint(20, min(150, victim["embers"]))
        victim["embers"] -= loot
        attacker = get_user_data(ctx.author.id)
        attacker["embers"] += loot
        save()
        await ctx.send(f"chase success! you caught {member.mention} and shook {loot} embers out of them! run!")
    else:
        await ctx.send(f"{member.mention} outran you! you're too slow bro, hit the gym")

@bot.command()
async def chamber(ctx, chambers: int = 6):
    if chambers < 2 or chambers > 10:
        await ctx.send("chambers must be 2-10. don't be weird")
        return
    data = get_user_data(ctx.author.id)
    alive = True
    round_num = 0
    winnings = 0
    while alive:
        round_num += 1
        bullet = random.randint(1, chambers)
        trigger = random.randint(1, chambers)
        if bullet == trigger:
            alive = False
            break
        winnings += round_num * 50
        if random.random() < 0.3:
            break
    if alive:
        data["embers"] += winnings
        save()
        await ctx.send(f"russian roulette! you survived {round_num} rounds and won {winnings} embers! you're insane!")
    else:
        loss = min(winnings // 2, data["embers"])
        data["embers"] = max(0, data["embers"] - loss)
        save()
        await ctx.send(f"bang! you got shot on round {round_num}! lost {loss} embers. should've stopped while ahead")

@bot.command()
async def rig(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("can't rig the game if you're broke")
        return
    data["embers"] -= amount
    if random.random() < 0.3:
        winnings = amount * 4
        data["embers"] += winnings
        save()
        await ctx.send(f"rigged! the system glitched and you got {winnings} embers! don't tell anyone!")
    else:
        save()
        await ctx.send(f"rig failed. the system detected your hack and you lost {amount} embers. skill issue")

# ========== SOCIAL COMMANDS ==========

@bot.command()
async def marry(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("marrying yourself? that's just being lonely with extra steps")
        return
    if member.bot:
        await ctx.send("bots can't consent bro")
        return
    data = get_user_data(ctx.author.id)
    if data["married_to"]:
        await ctx.send("you're already married! cheater!")
        return
    msg = await ctx.send(f"{member.mention}, {ctx.author.mention} wants to marry you! react ring to accept!")
    await msg.add_reaction("💍")
    await msg.add_reaction("❌")
    def check(reaction, user):
        return user == member and str(reaction.emoji) in ["💍", "❌"] and reaction.message.id == msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        if str(reaction.emoji) == "💍":
            data["married_to"] = member.id
            their_data = get_user_data(member.id)
            their_data["married_to"] = ctx.author.id
            save()
            await ctx.send(f"{ctx.author.mention} and {member.mention} are now married! congrats lovebirds!")
        else:
            await ctx.send("rejected. shot down in public. embarrassing")
    except asyncio.TimeoutError:
        await ctx.send("they left you on read. ouch")

@bot.command()
async def divorce(ctx):
    data = get_user_data(ctx.author.id)
    if not data["married_to"]:
        await ctx.send("you're not even married, who you divorcing? your hand?")
        return
    partner_id = data["married_to"]
    partner_data = get_user_data(partner_id)
    data["married_to"] = None
    partner_data["married_to"] = None
    save()
    partner = bot.get_user(partner_id)
    name = partner.mention if partner else "someone"
    await ctx.send(f"{ctx.author.mention} divorced {name}. rip the marriage. who gets the creatures?")

@bot.command()
async def will(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("leaving everything to yourself? that's just... keeping it")
        return
    data = get_user_data(ctx.author.id)
    data["will_to"] = member.id
    save()
    await ctx.send(f"{ctx.author.mention} wrote their will! if anything happens, {member.mention} gets all their embers and creatures. morbid but ok.")

@bot.command()
async def cult(ctx, *, cult_name: str):
    data = get_user_data(ctx.author.id)
    if data["cult"]:
        await ctx.send(f"you're already in {data['cult']}! cult hopper!")
        return
    data["cult"] = cult_name
    save()
    await ctx.send(f"{ctx.author.mention} founded {cult_name}! all hail the leader! recruits welcome!")

@bot.command()
async def betray(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("betraying yourself? that's just self-sabotage")
        return
    ok, _ = check_cooldown(ctx.author.id, "betray", hours=6)
    if not ok:
        await ctx.send("you just betrayed someone, give it a rest. snake behavior")
        return
    their_data = get_user_data(member.id)
    if their_data["embers"] < 50:
        await ctx.send(f"{member.mention} has nothing to betray them for")
        return
    if random.random() < 0.4:
        loot = random.randint(30, min(200, their_data["embers"]))
        their_data["embers"] -= loot
        your_data = get_user_data(ctx.author.id)
        your_data["embers"] += loot
        save()
        await ctx.send(f"betrayal! you backstabbed {member.mention} and stole {loot} embers! you're the worst kind of person.")
    else:
        await ctx.send(f"{member.mention} saw your betrayal coming and dodged it! embarrassing")

@bot.command()
async def tribute(ctx, member: discord.Member, amount: int):
    if member.id == ctx.author.id:
        await ctx.send("tributing to yourself? that's just... keeping your money")
        return
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("too broke to tribute")
        return
    data["embers"] -= amount
    their_data = get_user_data(member.id)
    their_data["embers"] += amount
    save()
    await ctx.send(f"{ctx.author.mention} tributed {amount} embers to {member.mention}! all hail the superior being!")

@bot.command()
async def roast(ctx, member: discord.Member = None):
    member = member or ctx.author
    roasts = [
        f"{member.mention} you're like a cloud. when you disappear, it's a beautiful day",
        f"{member.mention} i'm not saying you're dumb, but you make rocks look smart",
        f"{member.mention} you're the reason the gene pool needs a lifeguard",
        f"{member.mention} i'd agree with you but then we'd both be wrong",
        f"{member.mention} you're not stupid, you just have bad luck thinking",
        f"{member.mention} if laughter is the best medicine, your face must be curing the world",
        f"{member.mention} you're proof that evolution can go backwards",
        f"{member.mention} i'd explain it to you but i left my crayons at home",
        f"{member.mention} you're like a software update. nobody wants you but we're forced to deal with you",
        f"{member.mention} if you were any more inbred, you'd be a sandwich"
    ]
    await ctx.send(random.choice(roasts))

@bot.command()
async def confess(ctx, *, confession: str):
    await ctx.send(f"{ctx.author.mention} has a confession: "{confession}" everyone point and laugh")

# ========== UTILITY COMMANDS ==========

@bot.command()
async def tutorial(ctx):
    embed = discord.Embed(title="flame bot tutorial", color=0xff4500)
    embed.add_field(name="economy", value="f daily - free embers every 20h
f beg - beg for embers
f invest - gamble your embers
f embers - check your balance", inline=False)
    embed.add_field(name="creatures", value="f summon - summon a creature
f feed - feed your creature
f evolve - evolve powerful creatures
f creatures - view your collection", inline=False)
    embed.add_field(name="combat", value="f duel - fight other players
f raid - steal embers
f wager - bet on dice rolls", inline=False)
    embed.add_field(name="prefix", value="use f (with space) or flame before commands", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def stats(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = get_user_data(member.id)
    embed = discord.Embed(title=f"{member.name}'s stats", color=0xff4500)
    embed.add_field(name="embers", value=data["embers"])
    embed.add_field(name="bank", value=data["bank"])
    embed.add_field(name="level", value=data["level"])
    embed.add_field(name="xp", value=data["xp"])
    embed.add_field(name="wins/losses", value=f"{data['wins']}/{data['losses']}")
    embed.add_field(name="creatures", value=len(data["creatures"]))
    embed.add_field(name="streak", value=data["streak"])
    embed.add_field(name="loans", value=data["loans"])
    if data["married_to"]:
        partner = bot.get_user(data["married_to"])
        embed.add_field(name="married to", value=partner.mention if partner else "unknown")
    if data["cult"]:
        embed.add_field(name="cult", value=data["cult"])
    await ctx.send(embed=embed)

@bot.command()
async def server(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"{guild.name} server info", color=0xff4500)
    embed.add_field(name="members", value=guild.member_count)
    embed.add_field(name="owner", value=guild.owner.mention if guild.owner else "unknown")
    embed.add_field(name="created", value=guild.created_at.strftime("%Y-%m-%d"))
    embed.add_field(name="channels", value=len(guild.channels))
    embed.add_field(name="roles", value=len(guild.roles))
    await ctx.send(embed=embed)

@bot.command()
async def global_rank(ctx):
    all_users = [(int(k), v) for k, v in bot.data.items()]
    all_users.sort(key=lambda x: x[1]["embers"], reverse=True)
    embed = discord.Embed(title="global leaderboard", color=0xff4500)
    for i, (uid, data) in enumerate(all_users[:10]):
        user = bot.get_user(uid)
        name = user.name if user else f"user {uid}"
        embed.add_field(name=f"#{i+1} {name}", value=f"{data['embers']} embers | lv.{data['level']}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def settings(ctx):
    await ctx.send("settings: use f prefix to change prefix (currently f or flame)")

@bot.command()
async def cooldowns(ctx):
    data = get_user_data(ctx.author.id)
    now = datetime.datetime.now()
    embed = discord.Embed(title="your cooldowns", color=0xff4500)
    for key, val in data["cooldowns"].items():
        if key.startswith("cd_"):
            cmd = key.replace("cd_", "")
            last = datetime.datetime.fromisoformat(val)
            remaining = datetime.timedelta(hours=20) - (now - last)
            if remaining.total_seconds() > 0:
                hrs = int(remaining.total_seconds() // 3600)
                mins = int((remaining.total_seconds() % 3600) // 60)
                embed.add_field(name=cmd, value=f"{hrs}h {mins}m remaining", inline=False)
            else:
                embed.add_field(name=cmd, value="ready!", inline=False)
    if not embed.fields:
        embed.add_field(name="all commands", value="ready to use!")
    await ctx.send(embed=embed)

@bot.command()
async def changelog(ctx):
    embed = discord.Embed(title="flame bot changelog", color=0xff4500)
    embed.add_field(name="v1.0", value="initial release with economy, creatures, combat, gambling, social, and utility commands")
    embed.add_field(name="v1.1", value="added moderation commands and admin tools")
    embed.add_field(name="v1.2", value="added 350+ total commands across all categories")
    await ctx.send(embed=embed)

# ========== WEIRD COMMANDS ==========

@bot.command()
async def dream(ctx):
    dreams = [
        "you dreamt about flying embers. woke up with 10 extra embers!",
        "you dreamt you were rich. woke up broke. reality hits hard",
        "you dreamt about marrying your favorite creature. weird but ok",
        "you dreamt the bot took over the world. it was glorious.",
        "you dreamt about nothing. deep sleep. no embers gained."
    ]
    result = random.choice(dreams)
    if "10 extra" in result:
        data = get_user_data(ctx.author.id)
        data["embers"] += 10
        save()
    await ctx.send(result)

@bot.command()
async def curse(ctx, member: discord.Member = None):
    member = member or ctx.author
    curses = [
        f"{member.mention} has been cursed! their next gamble will lose!",
        f"{member.mention} is cursed! they'll find less embers begging!",
        f"{member.mention} got the bad luck curse! creatures lose mood faster!",
        f"{member.mention} is cursed to always roll low! sucks to be them!"
    ]
    await ctx.send(random.choice(curses))

@bot.command()
async def bless(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = get_user_data(member.id)
    bonus = random.randint(5, 25)
    data["embers"] += bonus
    save()
    await ctx.send(f"{member.mention} has been blessed with {bonus} embers! the gods smile upon them!")

@bot.command()
async def time(ctx):
    now = datetime.datetime.now()
    await ctx.send(f"current time: {now.strftime('%Y-%m-%d %H:%M:%S')} go touch grass, it's {now.strftime('%A')}")

@bot.command()
async def weather(ctx):
    weathers = ["sunny", "rainy", "stormy", "snowy", "foggy", "ember storm", "meteor shower"]
    await ctx.send(f"current weather: {random.choice(weathers)} perfect day to grind some embers!")

@bot.command()
async def oracle(ctx, *, question: str):
    answers = [
        "yes, definitely",
        "no, absolutely not",
        "maybe, who knows",
        "ask again later, i'm busy",
        "signs point to yes",
        "outlook not so good",
        "definitely maybe",
        "the embers say yes",
        "the creatures say no",
        "42. the answer is always 42."
    ]
    await ctx.send(f"you asked: "{question}" the oracle says: {random.choice(answers)}")

@bot.command()
async def mimic(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f"{member.mention} mimics your every move... this is getting weird.")

@bot.command()
async def glitch(ctx):
    glitches = [
        "system error: embers temporarily doubled! (just kidding, they're the same)",
        "glitch detected: your creatures can now speak! they say 'feed me'",
        "reality glitch: you found 50 embers in a wall!",
        "temporal anomaly: time rewound! your cooldowns reset! (not really)"
    ]
    result = random.choice(glitches)
    if "50 embers" in result:
        data = get_user_data(ctx.author.id)
        data["embers"] += 50
        save()
    await ctx.send(result)

@bot.command()
async def lore(ctx):
    lores = [
        "long ago, the world was divided into ash and flame. only the richest survived.",
        "legend says the first ember was found in a dragon's heart. still searching for it.",
        "the great war of 2024 destroyed half the creatures. we rebuilt. stronger.",
        "they say if you collect 1 million embers, you become a god. nobody's done it yet."
    ]
    await ctx.send(random.choice(lores))

@bot.command()
async def quit(ctx):
    await ctx.send("you can't quit the grind. the grind quits you. get back to work.")

# ========== MODERATION COMMANDS ==========

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "no reason given"):
    if member.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
        await ctx.send("you can't kick someone higher or equal to you")
        return
    if member.id == OWNER_ID:
        await ctx.send("you can't kick the bot owner, nice try")
        return
    await member.kick(reason=reason)
    await ctx.send(f"kicked {member.mention}. reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "no reason given"):
    if member.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
        await ctx.send("you can't ban someone higher or equal to you")
        return
    if member.id == OWNER_ID:
        await ctx.send("you can't ban the bot owner, nice try")
        return
    await member.ban(reason=reason)
    await ctx.send(f"banned {member.mention}. reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"unbanned {user.mention}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount > 100:
        await ctx.send("max 100 messages at once, don't be greedy")
        return
    if amount < 1:
        await ctx.send("purge at least 1 message, genius")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"deleted {len(deleted) - 1} messages")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason: str):
    if not hasattr(bot, "warns"):
        bot.warns = defaultdict(list)
    bot.warns[member.id].append({"reason": reason, "by": ctx.author.id, "time": datetime.datetime.now().isoformat()})
    await ctx.send(f"warned {member.mention}. reason: {reason} (warn #{len(bot.warns[member.id])})")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warns(ctx, member: discord.Member = None):
    member = member or ctx.author
    if not hasattr(bot, "warns") or member.id not in bot.warns or not bot.warns[member.id]:
        await ctx.send(f"{member.mention} has no warnings. they're a saint.")
        return
    embed = discord.Embed(title=f"{member.name}'s warnings", color=0xff4500)
    for i, w in enumerate(bot.warns[member.id], 1):
        embed.add_field(name=f"warn #{i}", value=f"reason: {w['reason']}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clearwarns(ctx, member: discord.Member):
    if hasattr(bot, "warns") and member.id in bot.warns:
        bot.warns[member.id] = []
    await ctx.send(f"cleared all warnings for {member.mention}. fresh start!")

@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nick(ctx, member: discord.Member, *, nickname: str = None):
    old = member.display_name
    await member.edit(nick=nickname)
    if nickname:
        await ctx.send(f"changed {member.mention}'s nickname from {old} to {nickname}")
    else:
        await ctx.send(f"reset {member.mention}'s nickname from {old}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def role(ctx, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"role '{role_name}' not found. check spelling")
        return
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"removed {role.name} from {member.mention}")
    else:
        await member.add_roles(role)
        await ctx.send(f"gave {role.name} to {member.mention}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def createrole(ctx, *, role_name: str):
    role = await ctx.guild.create_role(name=role_name)
    await ctx.send(f"created role {role.mention}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def deleterole(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    await role.delete()
    await ctx.send(f"deleted role {role_name}")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        await ctx.send("slowmode disabled. chat freely!")
    else:
        await ctx.send(f"set slowmode to {seconds} seconds. chill out everyone")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("channel locked. nobody can talk now.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("channel unlocked. back to the chaos!")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def hide(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=False)
    await ctx.send("channel hidden. now you see me, now you don't.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unhide(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=True)
    await ctx.send("channel visible again. welcome back!")

@bot.command()
@commands.has_permissions(mute_members=True)
async def mute(ctx, member: discord.Member, minutes: int = 10):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, speak=False)
    await member.add_roles(muted_role)
    await ctx.send(f"muted {member.mention} for {minutes} minutes. enjoy the silence!")
    await asyncio.sleep(minutes * 60)
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        await ctx.send(f"{member.mention} has been unmuted. behave now!")

@bot.command()
@commands.has_permissions(mute_members=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role and muted_role in member.roles:
        await member.remove_roles(muted_role)
        await ctx.send(f"unmuted {member.mention}. they can talk again")
    else:
        await ctx.send(f"{member.mention} isn't muted")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def createchannel(ctx, *, channel_name: str):
    channel = await ctx.guild.create_text_channel(channel_name)
    await ctx.send(f"created {channel.mention}")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def deletechannel(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.delete()

@bot.command()
@commands.has_permissions(manage_webhooks=True)
async def webhook(ctx, *, name: str = "flame webhook"):
    webhook = await ctx.channel.create_webhook(name=name)
    await ctx.send(f"created webhook: {webhook.url}")

@bot.command()
@commands.has_permissions(administrator=True)
async def announce(ctx, *, message: str):
    await ctx.message.delete()
    embed = discord.Embed(title="announcement", description=message, color=0xff4500)
    embed.set_footer(text=f"announced by {ctx.author.name}")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message: str):
    await ctx.message.delete()
    await ctx.send(message)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def embedsay(ctx, *, message: str):
    await ctx.message.delete()
    embed = discord.Embed(description=message, color=0xff4500)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def setprefix(ctx, *, new_prefix: str):
    await ctx.send("prefix system uses f and flame with space. can't change that, it's hardcoded.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def autorole(ctx, *, role_name: str = None):
    if not role_name:
        await ctx.send("specify a role name or 'off' to disable")
        return
    if role_name.lower() == "off":
        if str(ctx.guild.id) in bot.server_data and "autorole" in bot.server_data[str(ctx.guild.id)]:
            del bot.server_data[str(ctx.guild.id)]["autorole"]
        await ctx.send("autorole disabled")
        return
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    bot.server_data[str(ctx.guild.id)]["autorole"] = role.id
    save()
    await ctx.send(f"autorole set to {role.mention}")

@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    if guild_id in bot.server_data and "autorole" in bot.server_data[guild_id]:
        role = member.guild.get_role(bot.server_data[guild_id]["autorole"])
        if role:
            await member.add_roles(role)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def welcome(ctx, *, message: str = None):
    if not message:
        await ctx.send("specify a welcome message or 'off' to disable")
        return
    if message.lower() == "off":
        if str(ctx.guild.id) in bot.server_data and "welcome" in bot.server_data[str(ctx.guild.id)]:
            del bot.server_data[str(ctx.guild.id)]["welcome"]
        await ctx.send("welcome messages disabled")
        return
    bot.server_data[str(ctx.guild.id)]["welcome"] = message
    save()
    await ctx.send(f"welcome message set to: {message}")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def goodbye(ctx, *, message: str = None):
    if not message:
        await ctx.send("specify a goodbye message or 'off' to disable")
        return
    if message.lower() == "off":
        if str(ctx.guild.id) in bot.server_data and "goodbye" in bot.server_data[str(ctx.guild.id)]:
            del bot.server_data[str(ctx.guild.id)]["goodbye"]
        await ctx.send("goodbye messages disabled")
        return
    bot.server_data[str(ctx.guild.id)]["goodbye"] = message
    save()
    await ctx.send(f"goodbye message set to: {message}")

@bot.event
async def on_member_remove(member):
    guild_id = str(member.guild.id)
    if guild_id in bot.server_data and "goodbye" in bot.server_data[guild_id]:
        channel = member.guild.system_channel
        if channel:
            msg = bot.server_data[guild_id]["goodbye"].replace("{user}", member.mention).replace("{name}", member.name)
            await channel.send(msg)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def welcomechannel(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    bot.server_data[str(ctx.guild.id)]["welcome_channel"] = channel.id
    save()
    await ctx.send(f"welcome/goodbye channel set to {channel.mention}")

# ========== FUN COMMANDS (batch 1) ==========

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"pong! {latency}ms. not bad tbh")

@bot.command()
async def coinflip(ctx):
    await ctx.send(f"it's {random.choice(['heads', 'tails'])}")

@bot.command()
async def roll(ctx, sides: int = 6):
    await ctx.send(f"rolled a {random.randint(1, sides)} on a d{sides}")

@bot.command()
async def choose(ctx, *, options: str):
    choices = [c.strip() for c in options.split(",")]
    if len(choices) < 2:
        await ctx.send("give me at least 2 options separated by commas")
        return
    await ctx.send(f"i choose: {random.choice(choices)}")

@bot.command()
async def rate(ctx, *, thing: str):
    score = random.randint(1, 10)
    await ctx.send(f"i rate {thing} a {score}/10")

@bot.command()
async def gayrate(ctx, member: discord.Member = None):
    member = member or ctx.author
    score = random.randint(0, 100)
    await ctx.send(f"{member.mention} is {score}% gay")

@bot.command()
async def simprate(ctx, member: discord.Member = None):
    member = member or ctx.author
    score = random.randint(0, 100)
    await ctx.send(f"{member.mention} is {score}% simp")

@bot.command()
async def iq(ctx, member: discord.Member = None):
    member = member or ctx.author
    score = random.randint(50, 200)
    await ctx.send(f"{member.mention} has an iq of {score}")

@bot.command()
async def pp(ctx, member: discord.Member = None):
    member = member or ctx.author
    size = random.randint(1, 12)
    await ctx.send(f"{member.mention}'s pp is {size} inches")

@bot.command()
async def height(ctx, member: discord.Member = None):
    member = member or ctx.author
    ft = random.randint(4, 7)
    inches = random.randint(0, 11)
    await ctx.send(f"{member.mention} is {ft}'{inches}" tall")

@bot.command()
async def weight(ctx, member: discord.Member = None):
    member = member or ctx.author
    lbs = random.randint(80, 300)
    await ctx.send(f"{member.mention} weighs {lbs} lbs")

@bot.command()
async def age(ctx, member: discord.Member = None):
    member = member or ctx.author
    years = random.randint(1, 100)
    await ctx.send(f"{member.mention} is mentally {years} years old")

@bot.command()
async def ship(ctx, member1: discord.Member, member2: discord.Member = None):
    if not member2:
        member2 = ctx.author
    score = random.randint(0, 100)
    if score > 80:
        await ctx.send(f"{member1.mention} + {member2.mention} = {score}% match! they're soulmates!")
    elif score > 50:
        await ctx.send(f"{member1.mention} + {member2.mention} = {score}% match. decent couple i guess")
    else:
        await ctx.send(f"{member1.mention} + {member2.mention} = {score}% match. yikes. don't do it.")

@bot.command()
async def hack(ctx, member: discord.Member = None):
    member = member or ctx.author
    msgs = [
        "hacking into the mainframe...",
        "bypassing firewall...",
        "downloading files...",
        f"found password: {member.name}lovesminecraft123",
        f"found email: {member.name}@noobmail.com",
        f"bank account balance: $3.50",
        "hack complete. you're welcome."
    ]
    msg = await ctx.send(msgs[0])
    for m in msgs[1:]:
        await asyncio.sleep(1)
        await msg.edit(content=m)

@bot.command()
async def meme(ctx):
    memes = [
        "https://i.imgflip.com/30b1gx.jpg",
        "https://i.imgflip.com/1bij.jpg",
        "https://i.imgflip.com/26am.jpg",
        "https://i.imgflip.com/1otk96.jpg"
    ]
    await ctx.send(random.choice(memes))

@bot.command()
async def joke(ctx):
    jokes = [
        "why don't scientists trust atoms? because they make up everything.",
        "why did the scarecrow win an award? he was outstanding in his field.",
        "why don't eggs tell jokes? they'd crack each other up.",
        "what do you call a fake noodle? an impasta.",
        "why did the math book look sad? it had too many problems."
    ]
    await ctx.send(random.choice(jokes))

@bot.command()
async def fact(ctx):
    facts = [
        "honey never spoils. archaeologists found 3000-year-old honey in egyptian tombs.",
        "octopuses have three hearts.",
        "bananas are berries, but strawberries aren't.",
        "a day on venus is longer than a year on venus.",
        "wombat poop is cube-shaped."
    ]
    await ctx.send(random.choice(facts))

@bot.command()
async def quote(ctx):
    quotes = [
        "the only way to do great work is to love what you do. - steve jobs",
        "life is what happens when you're busy making other plans. - john lennon",
        "get busy living or get busy dying. - shawshank redemption",
        "you miss 100% of the shots you don't take. - wayne gretzky",
        "be the change you wish to see in the world. - gandhi"
    ]
    await ctx.send(random.choice(quotes))

@bot.command()
async def rps(ctx, choice: str):
    choice = choice.lower()
    if choice not in ["rock", "paper", "scissors"]:
        await ctx.send("pick rock, paper, or scissors. it's not hard")
        return
    bot_choice = random.choice(["rock", "paper", "scissors"])
    if choice == bot_choice:
        await ctx.send(f"we both picked {bot_choice}. tie!")
    elif (choice == "rock" and bot_choice == "scissors") or (choice == "paper" and bot_choice == "rock") or (choice == "scissors" and bot_choice == "paper"):
        await ctx.send(f"you picked {choice}, i picked {bot_choice}. you win! how")
    else:
        await ctx.send(f"you picked {choice}, i picked {bot_choice}. you lose! skill issue")

@bot.command()
async def eightball(ctx, *, question: str):
    answers = ["yes", "no", "maybe", "ask again later", "definitely", "absolutely not", "signs point to yes", "outlook not so good"]
    await ctx.send(f"you asked: "{question}" the 8ball says: {random.choice(answers)}")

@bot.command()
async def reverse(ctx, *, text: str):
    await ctx.send(text[::-1])

@bot.command()
async def uppercase(ctx, *, text: str):
    await ctx.send(text.upper())

@bot.command()
async def lowercase(ctx, *, text: str):
    await ctx.send(text.lower())

@bot.command()
async def len(ctx, *, text: str):
    await ctx.send(f"that text is {len(text)} characters long")

@bot.command()
async def countwords(ctx, *, text: str):
    await ctx.send(f"that text has {len(text.split())} words")

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.name}'s avatar")
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.name}'s info", color=member.color)
    embed.add_field(name="id", value=member.id)
    embed.add_field(name="joined server", value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "unknown")
    embed.add_field(name="account created", value=member.created_at.strftime("%Y-%m-%d"))
    embed.add_field(name="roles", value=len(member.roles) - 1)
    embed.add_field(name="top role", value=member.top_role.mention)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def botinfo(ctx):
    embed = discord.Embed(title="flame bot info", color=0xff4500)
    embed.add_field(name="prefix", value="f or flame (with space)")
    embed.add_field(name="owner", value="justaflamewithfragz")
    embed.add_field(name="commands", value="350+")
    embed.add_field(name="library", value="discord.py")
    embed.add_field(name="servers", value=len(bot.guilds))
    embed.add_field(name="users", value=len(bot.users))
    await ctx.send(embed=embed)

@bot.command()
async def invite(ctx):
    await ctx.send("https://discord.com/oauth2/authorize?client_id=" + str(bot.user.id) + "&permissions=8&scope=bot")

@bot.command()
async def uptime(ctx):
    await ctx.send("the bot has been running since you started it. that's the uptime.")

@bot.command()
async def reminder(ctx, minutes: int, *, reminder_text: str):
    await ctx.send(f"i'll remind you in {minutes} minutes: {reminder_text}")
    await asyncio.sleep(minutes * 60)
    await ctx.send(f"{ctx.author.mention} reminder: {reminder_text}")

@bot.command()
async def timer(ctx, seconds: int):
    if seconds > 3600:
        await ctx.send("max timer is 1 hour, i'm not your alarm clock")
        return
    await ctx.send(f"timer started for {seconds} seconds")
    await asyncio.sleep(seconds)
    await ctx.send(f"{ctx.author.mention} time's up!")

@bot.command()
async def poll(ctx, *, question: str):
    parts = question.split("|")
    if len(parts) < 2:
        await ctx.send("format: f poll question | option1 | option2 | ...")
        return
    q = parts[0].strip()
    options = [p.strip() for p in parts[1:]]
    embed = discord.Embed(title=f"poll: {q}", color=0xff4500)
    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, opt in enumerate(options[:10]):
        embed.add_field(name=f"{reactions[i]} {opt}", value="vote above", inline=False)
    msg = await ctx.send(embed=embed)
    for i in range(len(options[:10])):
        await msg.add_reaction(reactions[i])

@bot.command()
async def calc(ctx, *, expression: str):
    try:
        result = eval(expression, {"__builtins__": {}}, {"math": math})
        await ctx.send(f"result: {result}")
    except:
        await ctx.send("that math doesn't work. try again")

@bot.command()
async def randomnum(ctx, min_val: int = 1, max_val: int = 100):
    await ctx.send(f"random number between {min_val} and {max_val}: {random.randint(min_val, max_val)}")

@bot.command()
async def password(ctx, length: int = 12):
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    pwd = "".join(random.choice(chars) for _ in range(length))
    await ctx.author.send(f"your generated password: {pwd}")
    await ctx.send("sent you a dm with the password")

@bot.command()
async def binary(ctx, *, text: str):
    binary = " ".join(format(ord(c), "08b") for c in text)
    await ctx.send(f"binary: {binary}")

@bot.command()
async def morse(ctx, *, text: str):
    morse_code = {"a":".-","b":"-...","c":"-.-.","d":"-..","e":".","f":"..-.","g":"--.","h":"....","i":"..","j":".---","k":"-.-","l":".-..","m":"--","n":"-.","o":"---","p":".--.","q":"--.-","r":".-.","s":"...","t":"-","u":"..-","v":"...-","w":".--","x":"-..-","y":"-.--","z":"--..","1":".----","2":"..---","3":"...--","4":"....-","5":".....","6":"-....","7":"--...","8":"---..","9":"----.","0":"-----"}
    result = " ".join(morse_code.get(c.lower(), c) for c in text if c.lower() in morse_code or c == " ")
    await ctx.send(f"morse code: {result}")

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
        await ctx.send("that's not valid base64")

@bot.command()
async def hexcode(ctx, *, text: str):
    hexed = " ".join(hex(ord(c))[2:] for c in text)
    await ctx.send(f"hex: {hexed}")

@bot.command()
async def decodehex(ctx, *, text: str):
    try:
        decoded = bytes.fromhex(text.replace(" ", "")).decode()
        await ctx.send(f"decoded: {decoded}")
    except:
        await ctx.send("that's not valid hex")

@bot.command()
async def md5(ctx, *, text: str):
    import hashlib
    result = hashlib.md5(text.encode()).hexdigest()
    await ctx.send(f"md5: {result}")

@bot.command()
async def sha256(ctx, *, text: str):
    import hashlib
    result = hashlib.sha256(text.encode()).hexdigest()
    await ctx.send(f"sha256: {result}")

# ========== MORE FUN COMMANDS (batch 2) ==========

@bot.command()
async def roastme(ctx):
    roasts = [
        f"{ctx.author.mention} you're like a cloud. when you disappear, it's a beautiful day",
        f"{ctx.author.mention} i'm not saying you're dumb, but you make rocks look smart",
        f"{ctx.author.mention} you're the reason the gene pool needs a lifeguard",
        f"{ctx.author.mention} i'd agree with you but then we'd both be wrong",
        f"{ctx.author.mention} you're not stupid, you just have bad luck thinking"
    ]
    await ctx.send(random.choice(roasts))

@bot.command()
async def compliment(ctx, member: discord.Member = None):
    member = member or ctx.author
    compliments = [
        f"{member.mention} you're looking great today!",
        f"{member.mention} has a beautiful soul",
        f"{member.mention} is the best person in this server",
        f"{member.mention} makes everyone smile",
        f"{member.mention} is absolutely crushing it today"
    ]
    await ctx.send(random.choice(compliments))

@bot.command()
async def kill(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("you killed yourself. that's just suicide")
        return
    deaths = [
        f"{ctx.author.mention} stabbed {member.mention} with a spoon. brutal.",
        f"{ctx.author.mention} pushed {member.mention} off a cliff. classic.",
        f"{ctx.author.mention} fed {member.mention} to their creatures. yum.",
        f"{ctx.author.mention} bored {member.mention} to death with math."
    ]
    await ctx.send(random.choice(deaths))

@bot.command()
async def hug(ctx, member: discord.Member = None):
    member = member or ctx.author
    if member.id == ctx.author.id:
        await ctx.send(f"{ctx.author.mention} hugged themselves. that's just... sad")
        return
    await ctx.send(f"{ctx.author.mention} hugged {member.mention}! wholesome!")

@bot.command()
async def slap(ctx, member: discord.Member = None):
    member = member or ctx.author
    if member.id == ctx.author.id:
        await ctx.send(f"{ctx.author.mention} slapped themselves. self-improvement?")
        return
    await ctx.send(f"{ctx.author.mention} slapped {member.mention}! that had to hurt!")

@bot.command()
async def punch(ctx, member: discord.Member = None):
    member = member or ctx.author
    if member.id == ctx.author.id:
        await ctx.send(f"{ctx.author.mention} punched themselves. masochist much?")
        return
    await ctx.send(f"{ctx.author.mention} punched {member.mention}! knockout!")

@bot.command()
async def kiss(ctx, member: discord.Member = None):
    member = member or ctx.author
    if member.id == ctx.author.id:
        await ctx.send(f"{ctx.author.mention} kissed themselves. narcissist much?")
        return
    await ctx.send(f"{ctx.author.mention} kissed {member.mention}! aww!")

@bot.command()
async def pat(ctx, member: discord.Member = None):
    member = member or ctx.author
    if member.id == ctx.author.id:
        await ctx.send(f"{ctx.author.mention} patted themselves. self-care!")
        return
    await ctx.send(f"{ctx.author.mention} patted {member.mention} on the head! good job!")

@bot.command()
async def bonk(ctx, member: discord.Member = None):
    member = member or ctx.author
    if member.id == ctx.author.id:
        await ctx.send(f"{ctx.author.mention} bonked themselves. horny jail for one")
        return
    await ctx.send(f"{ctx.author.mention} bonked {member.mention}! go to horny jail!")

@bot.command()
async def yeet(ctx, member: discord.Member = None):
    member = member or ctx.author
    if member.id == ctx.author.id:
        await ctx.send(f"{ctx.author.mention} yeeted themselves into the sun")
        return
    await ctx.send(f"{ctx.author.mention} yeeted {member.mention} into orbit!")

@bot.command()
async def dab(ctx):
    await ctx.send(f"{ctx.author.mention} hit the dab. it's 2016 again apparently.")

@bot.command()
async def tpose(ctx):
    await ctx.send(f"{ctx.author.mention} hit the t-pose. asserting dominance.")

@bot.command()
async def dance(ctx):
    dances = ["the floss", "the worm", "the moonwalk", "the macarena", "the harlem shake"]
    await ctx.send(f"{ctx.author.mention} did {random.choice(dances)}! sick moves!")

@bot.command()
async def sing(ctx, *, song: str = None):
    if not song:
        songs = ["never gonna give you up", "baby shark", "des pacito", "wonderwall"]
        song = random.choice(songs)
    await ctx.send(f"{ctx.author.mention} is singing {song}! beautiful voice... or not.")

@bot.command()
async def cry(ctx):
    await ctx.send(f"{ctx.author.mention} is crying. someone give them a hug")

@bot.command()
async def laugh(ctx):
    laughs = ["haha", "lol", "lmao", "rofl", "kekw", "xd"]
    await ctx.send(f"{ctx.author.mention} {random.choice(laughs)}")

@bot.command()
async def sleep(ctx):
    await ctx.send(f"{ctx.author.mention} went to sleep. night night!")

@bot.command()
async def wake(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f"{ctx.author.mention} woke up {member.mention}! rise and grind!")

@bot.command()
async def eat(ctx, *, food: str = None):
    if not food:
        foods = ["pizza", "burger", "taco", "sushi", "ramen", "steak"]
        food = random.choice(foods)
    await ctx.send(f"{ctx.author.mention} ate some {food}. delicious!")

@bot.command()
async def drink(ctx, *, drink: str = None):
    if not drink:
        drinks = ["water", "coffee", "tea", "soda", "energy drink", "milk"]
        drink = random.choice(drinks)
    await ctx.send(f"{ctx.author.mention} drank some {drink}. refreshing!")

@bot.command()
async def workout(ctx):
    exercises = ["pushups", "situps", "squats", "deadlifts", "cardio", "yoga"]
    await ctx.send(f"{ctx.author.mention} did {random.randint(10, 100)} {random.choice(exercises)}! getting swole!")

@bot.command()
async def study(ctx, *, subject: str = None):
    if not subject:
        subjects = ["math", "science", "history", "english", "coding", "art"]
        subject = random.choice(subjects)
    await ctx.send(f"{ctx.author.mention} studied {subject} for {random.randint(1, 8)} hours! nerd!")

@bot.command()
async def work(ctx):
    earnings = random.randint(50, 300)
    data = get_user_data(ctx.author.id)
    data["embers"] += earnings
    save()
    await ctx.send(f"{ctx.author.mention} worked hard and earned {earnings} embers! capitalism!")

@bot.command()
async def rob(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("robbing yourself? that's just moving money around")
        return
    ok, _ = check_cooldown(ctx.author.id, "rob", hours=1)
    if not ok:
        await ctx.send("you just robbed someone, chill")
        return
    victim = get_user_data(member.id)
    if victim["embers"] < 50:
        await ctx.send(f"{member.mention} is broke, not worth robbing")
        return
    if random.random() < 0.4:
        amount = random.randint(20, min(200, victim["embers"]))
        victim["embers"] -= amount
        robber = get_user_data(ctx.author.id)
        robber["embers"] += amount
        save()
        await ctx.send(f"{ctx.author.mention} robbed {member.mention} and got {amount} embers! criminal!")
    else:
        fine = random.randint(10, 50)
        robber = get_user_data(ctx.author.id)
        robber["embers"] = max(0, robber["embers"] - fine)
        save()
        await ctx.send(f"{ctx.author.mention} got caught robbing {member.mention} and lost {fine} embers!")

@bot.command()
async def pay(ctx, amount: int, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("paying yourself? that's just... keeping your money")
        return
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("you're too broke for that")
        return
    data["embers"] -= amount
    receiver = get_user_data(member.id)
    receiver["embers"] += amount
    save()
    await ctx.send(f"{ctx.author.mention} paid {member.mention} {amount} embers!")

@bot.command()
async def deposit(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("you don't have that much to deposit")
        return
    data["embers"] -= amount
    data["bank"] += amount
    save()
    await ctx.send(f"deposited {amount} embers to the bank. total bank: {data['bank']}")

@bot.command()
async def withdraw(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["bank"]:
        await ctx.send("your bank account doesn't have that much")
        return
    data["bank"] -= amount
    data["embers"] += amount
    save()
    await ctx.send(f"withdrew {amount} embers from the bank. total bank: {data['bank']}")

@bot.command()
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = get_user_data(member.id)
    await ctx.send(f"{member.mention} | wallet: {data['embers']} | bank: {data['bank']} | total: {data['embers'] + data['bank']}")

@bot.command()
async def leaderboard(ctx):
    all_users = [(int(k), v) for k, v in bot.data.items()]
    all_users.sort(key=lambda x: x[1]["embers"] + x[1]["bank"], reverse=True)
    embed = discord.Embed(title="richest players", color=0xff4500)
    for i, (uid, data) in enumerate(all_users[:10]):
        user = bot.get_user(uid)
        name = user.name if user else f"user {uid}"
        total = data["embers"] + data["bank"]
        embed.add_field(name=f"#{i+1} {name}", value=f"{total} embers total", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def shop(ctx):
    items = [
        ("health potion", 50, "heals your creatures"),
        ("power boost", 100, "+10 power to all creatures"),
        ("mood candy", 30, "+20 mood to one creature"),
        ("evolution stone", 500, "instantly evolve a creature"),
        ("lucky charm", 200, "better gambling odds for 1 hour")
    ]
    embed = discord.Embed(title="item shop", color=0xff4500)
    for name, price, desc in items:
        embed.add_field(name=f"{name} - {price} embers", value=desc, inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, *, item_name: str):
    items = {"health potion": 50, "power boost": 100, "mood candy": 30, "evolution stone": 500, "lucky charm": 200}
    item_name = item_name.lower()
    if item_name not in items:
        await ctx.send("that item doesn't exist. check f shop")
        return
    data = get_user_data(ctx.author.id)
    price = items[item_name]
    if data["embers"] < price:
        await ctx.send("you're too broke for that item")
        return
    data["embers"] -= price
    data["inventory"].append(item_name)
    save()
    await ctx.send(f"bought {item_name} for {price} embers!")

@bot.command()
async def inventory(ctx):
    data = get_user_data(ctx.author.id)
    if not data["inventory"]:
        await ctx.send("your inventory is empty. buy something from f shop")
        return
    items = ", ".join(data["inventory"])
    await ctx.send(f"your inventory: {items}")

@bot.command()
async def use(ctx, *, item_name: str):
    data = get_user_data(ctx.author.id)
    item_name = item_name.lower()
    if item_name not in data["inventory"]:
        await ctx.send("you don't have that item")
        return
    data["inventory"].remove(item_name)
    if item_name == "health potion":
        for c in data["creatures"]:
            c["mood"] = min(100, c["mood"] + 30)
        await ctx.send("used health potion! all creatures healed!")
    elif item_name == "power boost":
        for c in data["creatures"]:
            c["power"] += 10
        await ctx.send("used power boost! all creatures got stronger!")
    elif item_name == "mood candy":
        await ctx.send("mood candy needs a creature id. use f feed instead")
        data["inventory"].append(item_name)
    elif item_name == "evolution stone":
        await ctx.send("evolution stone needs a creature id. use f evolve instead")
        data["inventory"].append(item_name)
    elif item_name == "lucky charm":
        await ctx.send("lucky charm activated! better odds for 1 hour! (cosmetic)")
    save()

@bot.command()
async def sell(ctx, *, item_name: str):
    data = get_user_data(ctx.author.id)
    item_name = item_name.lower()
    if item_name not in data["inventory"]:
        await ctx.send("you don't have that item to sell")
        return
    prices = {"health potion": 25, "power boost": 50, "mood candy": 15, "evolution stone": 250, "lucky charm": 100}
    sell_price = prices.get(item_name, 10)
    data["inventory"].remove(item_name)
    data["embers"] += sell_price
    save()
    await ctx.send(f"sold {item_name} for {sell_price} embers")

# ========== MORE COMMANDS (batch 3) ==========

@bot.command()
async def level(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = get_user_data(member.id)
    needed = data["level"] * 100
    await ctx.send(f"{member.mention} is level {data['level']} with {data['xp']}/{needed} xp")

@bot.command()
async def xp(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = get_user_data(member.id)
    await ctx.send(f"{member.mention} has {data['xp']} xp")

@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = get_user_data(member.id)
    embed = discord.Embed(title=f"{member.name}'s profile", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="level", value=data["level"])
    embed.add_field(name="xp", value=data["xp"])
    embed.add_field(name="embers", value=data["embers"])
    embed.add_field(name="bank", value=data["bank"])
    embed.add_field(name="creatures", value=len(data["creatures"]))
    embed.add_field(name="wins", value=data["wins"])
    embed.add_field(name="losses", value=data["losses"])
    embed.add_field(name="streak", value=data["streak"])
    if data["married_to"]:
        partner = bot.get_user(data["married_to"])
        embed.add_field(name="married to", value=partner.mention if partner else "unknown")
    if data["cult"]:
        embed.add_field(name="cult", value=data["cult"])
    await ctx.send(embed=embed)

@bot.command()
async def marrycheck(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = get_user_data(member.id)
    if data["married_to"]:
        partner = bot.get_user(data["married_to"])
        name = partner.mention if partner else "someone"
        await ctx.send(f"{member.mention} is married to {name}")
    else:
        await ctx.send(f"{member.mention} is single and ready to mingle")

@bot.command()
async def cultcheck(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = get_user_data(member.id)
    if data["cult"]:
        await ctx.send(f"{member.mention} is in the cult: {data['cult']}")
    else:
        await ctx.send(f"{member.mention} is not in any cult. boring.")

@bot.command()
async def cultleave(ctx):
    data = get_user_data(ctx.author.id)
    if not data["cult"]:
        await ctx.send("you're not in a cult to leave")
        return
    old = data["cult"]
    data["cult"] = None
    save()
    await ctx.send(f"you left {old}. traitor.")

@bot.command()
async def cultmembers(ctx):
    data = get_user_data(ctx.author.id)
    if not data["cult"]:
        await ctx.send("you're not in a cult")
        return
    members = []
    for uid, udata in bot.data.items():
        if udata.get("cult") == data["cult"]:
            user = bot.get_user(int(uid))
            if user:
                members.append(user.mention)
    await ctx.send(f"members of {data['cult']}: {', '.join(members) if members else 'just you, lonely cultist'}")

@bot.command()
async def divorcecheck(ctx):
    data = get_user_data(ctx.author.id)
    if data["married_to"]:
        await ctx.send("you're married. don't even think about it.")
    else:
        await ctx.send("you're single. go find someone with f marry")

@bot.command()
async def richest(ctx):
    all_users = [(int(k), v) for k, v in bot.data.items()]
    all_users.sort(key=lambda x: x[1]["embers"], reverse=True)
    if not all_users:
        await ctx.send("nobody has embers yet. be the first!")
        return
    richest = all_users[0]
    user = bot.get_user(richest[0])
    name = user.name if user else f"user {richest[0]}"
    await ctx.send(f"the richest person is {name} with {richest[1]['embers']} embers")

@bot.command()
async def poorest(ctx):
    all_users = [(int(k), v) for k, v in bot.data.items() if v["embers"] > 0]
    if not all_users:
        await ctx.send("everyone is broke. equality!")
        return
    all_users.sort(key=lambda x: x[1]["embers"])
    poorest = all_users[0]
    user = bot.get_user(poorest[0])
    name = user.name if user else f"user {poorest[0]}"
    await ctx.send(f"the poorest person is {name} with {poorest[1]['embers']} embers. f in the chat")

@bot.command()
async def richestcreature(ctx):
    all_creatures = []
    for uid, data in bot.data.items():
        for c in data["creatures"]:
            all_creatures.append((c, uid))
    if not all_creatures:
        await ctx.send("no creatures exist yet. summon some!")
        return
    all_creatures.sort(key=lambda x: x[0]["power"], reverse=True)
    best = all_creatures[0]
    owner = bot.get_user(best[1])
    owner_name = owner.name if owner else f"user {best[1]}"
    await ctx.send(f"the strongest creature is {best[0]['name']} (power: {best[0]['power']}) owned by {owner_name}")

@bot.command()
async def bankrob(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("robbing your own bank? that's just withdrawing")
        return
    ok, _ = check_cooldown(ctx.author.id, "bankrob", hours=3)
    if not ok:
        await ctx.send("the bank is on high alert, wait")
        return
    victim = get_user_data(member.id)
    if victim["bank"] < 100:
        await ctx.send(f"{member.mention}'s bank is too empty to rob")
        return
    if random.random() < 0.3:
        amount = random.randint(50, min(500, victim["bank"]))
        victim["bank"] -= amount
        robber = get_user_data(ctx.author.id)
        robber["embers"] += amount
        save()
        await ctx.send(f"bank robbery successful! you stole {amount} embers from {member.mention}'s vault!")
    else:
        fine = random.randint(50, 200)
        robber = get_user_data(ctx.author.id)
        robber["embers"] = max(0, robber["embers"] - fine)
        save()
        await ctx.send(f"bank robbery failed! security caught you and you lost {fine} embers!")

@bot.command()
async def lottery(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("you're too broke for the lottery")
        return
    if amount < 10:
        await ctx.send("minimum lottery ticket is 10 embers")
        return
    data["embers"] -= amount
    if random.random() < 0.05:
        jackpot = amount * 20
        data["embers"] += jackpot
        save()
        await ctx.send(f"JACKPOT! you won {jackpot} embers! you're rich now!")
    elif random.random() < 0.2:
        small_win = amount * 3
        data["embers"] += small_win
        save()
        await ctx.send(f"you won {small_win} embers! not bad!")
    else:
        save()
        await ctx.send(f"you lost {amount} embers. the house always wins.")

@bot.command()
async def slots(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("no embers no slots")
        return
    data["embers"] -= amount
    symbols = ["7", "cherries", "lemon", "diamond", "bell", "bar"]
    roll = [random.choice(symbols) for _ in range(3)]
    if roll[0] == roll[1] == roll[2]:
        winnings = amount * 10
        data["embers"] += winnings
        save()
        await ctx.send(f"{roll[0]} | {roll[1]} | {roll[2]} - JACKPOT! you won {winnings} embers!")
    elif roll[0] == roll[1] or roll[1] == roll[2] or roll[0] == roll[2]:
        winnings = amount * 2
        data["embers"] += winnings
        save()
        await ctx.send(f"{roll[0]} | {roll[1]} | {roll[2]} - two match! you won {winnings} embers!")
    else:
        save()
        await ctx.send(f"{roll[0]} | {roll[1]} | {roll[2]} - nothing. lost {amount} embers.")

@bot.command()
async def blackjack(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("you're too broke for blackjack")
        return
    data["embers"] -= amount

    def draw():
        return random.randint(1, 11)

    player = [draw(), draw()]
    dealer = [draw(), draw()]

    p_total = sum(player)
    d_total = sum(dealer)

    if p_total > 21:
        save()
        await ctx.send(f"your hand: {player} = {p_total}. bust! you lost {amount} embers.")
        return
    if d_total > 21:
        data["embers"] += amount * 2
        save()
        await ctx.send(f"your hand: {player} = {p_total}. dealer busts with {dealer} = {d_total}! you won {amount * 2} embers!")
        return

    if p_total > d_total:
        data["embers"] += amount * 2
        save()
        await ctx.send(f"your hand: {player} = {p_total} beats dealer's {dealer} = {d_total}! you won {amount * 2} embers!")
    elif d_total > p_total:
        save()
        await ctx.send(f"your hand: {player} = {p_total} loses to dealer's {dealer} = {d_total}. you lost {amount} embers.")
    else:
        data["embers"] += amount
        save()
        await ctx.send(f"your hand: {player} = {p_total} ties dealer's {dealer} = {d_total}. push! you get your money back.")

@bot.command()
async def roulette(ctx, amount: int, bet: str):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("you're too broke for roulette")
        return
    data["embers"] -= amount
    number = random.randint(0, 36)
    color = "red" if number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else "black" if number != 0 else "green"

    won = False
    if bet.lower() == color:
        won = True
        winnings = amount * 2
    elif bet.isdigit() and int(bet) == number:
        won = True
        winnings = amount * 35
    elif bet.lower() in ["even", "odd"]:
        if number != 0 and ((bet.lower() == "even" and number % 2 == 0) or (bet.lower() == "odd" and number % 2 == 1)):
            won = True
            winnings = amount * 2

    if won:
        data["embers"] += winnings
        save()
        await ctx.send(f"the ball landed on {number} {color}! you won {winnings} embers!")
    else:
        save()
        await ctx.send(f"the ball landed on {number} {color}. you lost {amount} embers.")

@bot.command()
async def horse(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("you're too broke to bet on horses")
        return
    data["embers"] -= amount
    horses = ["thunder", "lightning", "blaze", "shadow", "spirit", "storm"]
    winner = random.choice(horses)
    your_horse = random.choice(horses)
    if your_horse == winner:
        winnings = amount * 3
        data["embers"] += winnings
        save()
        await ctx.send(f"your horse {your_horse} won the race! you won {winnings} embers!")
    else:
        save()
        await ctx.send(f"your horse {your_horse} came in last. winner was {winner}. you lost {amount} embers.")

@bot.command()
async def fight(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("fighting yourself? that's just shadow boxing")
        return
    p1 = random.randint(1, 100)
    p2 = random.randint(1, 100)
    if p1 > p2:
        await ctx.send(f"{ctx.author.mention} ({p1}) beat {member.mention} ({p2})! knockout!")
    elif p2 > p1:
        await ctx.send(f"{member.mention} ({p2}) beat {ctx.author.mention} ({p1})! knockout!")
    else:
        await ctx.send(f"it's a tie! both scored {p1}. boring.")

@bot.command()
async def armwrestle(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("arm wrestling yourself? that's just clapping")
        return
    p1 = random.randint(1, 100)
    p2 = random.randint(1, 100)
    if p1 > p2:
        await ctx.send(f"{ctx.author.mention} slammed {member.mention}'s hand down! power!")
    else:
        await ctx.send(f"{member.mention} slammed {ctx.author.mention}'s hand down! weak!")

@bot.command()
async def tugofwar(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("tug of war with yourself? that's just pulling a rope")
        return
    p1 = random.randint(1, 100)
    p2 = random.randint(1, 100)
    if p1 > p2:
        await ctx.send(f"{ctx.author.mention} pulled {member.mention} across the line!")
    else:
        await ctx.send(f"{member.mention} pulled {ctx.author.mention} across the line!")

@bot.command()
async def race(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("racing yourself? that's just running")
        return
    t1 = random.uniform(5, 15)
    t2 = random.uniform(5, 15)
    if t1 < t2:
        await ctx.send(f"{ctx.author.mention} finished in {t1:.2f}s, beating {member.mention}'s {t2:.2f}s!")
    else:
        await ctx.send(f"{member.mention} finished in {t2:.2f}s, beating {ctx.author.mention}'s {t1:.2f}s!")

@bot.command()
async def trivia(ctx):
    questions = [
        ("what is the capital of france?", "paris"),
        ("what is 2+2?", "4"),
        ("what planet is known as the red planet?", "mars"),
        ("who wrote romeo and juliet?", "shakespeare"),
        ("what is the largest ocean?", "pacific"),
        ("what year did ww2 end?", "1945"),
        ("what is the chemical symbol for gold?", "au"),
        ("how many continents are there?", "7"),
        ("what is the speed of light?", "299792458"),
        ("who painted the mona lisa?", "da vinci")
    ]
    q, a = random.choice(questions)
    await ctx.send(f"trivia: {q} (you have 15 seconds)")
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    try:
        msg = await bot.wait_for("message", timeout=15.0, check=check)
        if msg.content.lower() == a.lower():
            data = get_user_data(ctx.author.id)
            data["embers"] += 50
            save()
            await ctx.send(f"correct! you won 50 embers! total: {data['embers']}")
        else:
            await ctx.send(f"wrong! the answer was {a}. you get nothing.")
    except asyncio.TimeoutError:
        await ctx.send(f"too slow! the answer was {a}.")

@bot.command()
async def guess(ctx, max_num: int = 100):
    number = random.randint(1, max_num)
    await ctx.send(f"i'm thinking of a number between 1 and {max_num}. guess it! (you have 10 tries)")
    tries = 0
    while tries < 10:
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        try:
            msg = await bot.wait_for("message", timeout=30.0, check=check)
            guess = int(msg.content)
            tries += 1
            if guess == number:
                data = get_user_data(ctx.author.id)
                prize = max(10, (11 - tries) * 10)
                data["embers"] += prize
                save()
                await ctx.send(f"correct! the number was {number}! you won {prize} embers in {tries} tries!")
                return
            elif guess < number:
                await ctx.send("higher!")
            else:
                await ctx.send("lower!")
        except asyncio.TimeoutError:
            await ctx.send(f"you gave up? the number was {number}.")
            return
    await ctx.send(f"out of tries! the number was {number}.")

@bot.command()
async def hangman(ctx):
    words = ["python", "discord", "ember", "flame", "creature", "combat", "gamble", "server", "railway", "bot"]
    word = random.choice(words)
    guessed = set()
    wrong = 0
    max_wrong = 6
    await ctx.send("hangman started! guess letters. type 'quit' to give up.")
    while wrong < max_wrong:
        display = " ".join(c if c in guessed else "_" for c in word)
        await ctx.send(f"word: {display} | wrong: {wrong}/{max_wrong} | guessed: {', '.join(sorted(guessed)) if guessed else 'none'}")
        if all(c in guessed for c in word):
            data = get_user_data(ctx.author.id)
            data["embers"] += 100
            save()
            await ctx.send(f"you won! the word was {word}! you got 100 embers!")
            return
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and (len(m.content) == 1 or m.content.lower() == "quit")
        try:
            msg = await bot.wait_for("message", timeout=60.0, check=check)
            if msg.content.lower() == "quit":
                await ctx.send(f"quitter. the word was {word}.")
                return
            letter = msg.content.lower()
            if letter in guessed:
                await ctx.send("you already guessed that!")
                continue
            guessed.add(letter)
            if letter not in word:
                wrong += 1
        except asyncio.TimeoutError:
            await ctx.send(f"you fell asleep? the word was {word}.")
            return
    await ctx.send(f"hanged! the word was {word}. you lost.")

@bot.command()
async def wordscramble(ctx):
    words = ["python", "discord", "ember", "flame", "creature", "combat", "gamble", "server"]
    word = random.choice(words)
    scrambled = "".join(random.sample(word, len(word)))
    await ctx.send(f"unscramble this: {scrambled} (you have 20 seconds)")
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    try:
        msg = await bot.wait_for("message", timeout=20.0, check=check)
        if msg.content.lower() == word:
            data = get_user_data(ctx.author.id)
            data["embers"] += 75
            save()
            await ctx.send(f"correct! the word was {word}! you won 75 embers!")
        else:
            await ctx.send(f"wrong! the word was {word}.")
    except asyncio.TimeoutError:
        await ctx.send(f"too slow! the word was {word}.")

@bot.command()
async def mathquiz(ctx):
    ops = ["+", "-", "*"]
    op = random.choice(ops)
    a, b = random.randint(1, 20), random.randint(1, 20)
    if op == "+":
        ans = a + b
    elif op == "-":
        ans = a - b
    else:
        ans = a * b
    await ctx.send(f"what is {a} {op} {b}? (you have 10 seconds)")
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lstrip("-").isdigit()
    try:
        msg = await bot.wait_for("message", timeout=10.0, check=check)
        if int(msg.content) == ans:
            data = get_user_data(ctx.author.id)
            data["embers"] += 25
            save()
            await ctx.send(f"correct! {a} {op} {b} = {ans}! you won 25 embers!")
        else:
            await ctx.send(f"wrong! {a} {op} {b} = {ans}.")
    except asyncio.TimeoutError:
        await ctx.send(f"too slow! {a} {op} {b} = {ans}.")

# ========== MORE COMMANDS (batch 4) ==========

@bot.command()
async def typingtest(ctx):
    sentences = [
        "the quick brown fox jumps over the lazy dog",
        "discord bots are cool and fun to make",
        "embers are the currency of the flame world",
        "creatures need love and attention to grow",
        "gambling is risky but sometimes rewarding"
    ]
    sentence = random.choice(sentences)
    await ctx.send(f"type this exactly (case matters):
`{sentence}`
you have 15 seconds!")
    start = datetime.datetime.now()
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    try:
        msg = await bot.wait_for("message", timeout=15.0, check=check)
        end = datetime.datetime.now()
        time_taken = (end - start).total_seconds()
        if msg.content == sentence:
            wpm = int(len(sentence.split()) / (time_taken / 60))
            data = get_user_data(ctx.author.id)
            data["embers"] += 50
            save()
            await ctx.send(f"perfect! {wpm} wpm! you won 50 embers!")
        else:
            await ctx.send(f"you messed up. the sentence was: {sentence}")
    except asyncio.TimeoutError:
        await ctx.send(f"too slow! the sentence was: {sentence}")

@bot.command()
async def reactiontest(ctx):
    emojis = ["fire", "water", "earth", "wind", "heart", "star", "moon", "sun"]
    target = random.choice(emojis)
    msg = await ctx.send(f"react with {target} as fast as you can!")
    start = datetime.datetime.now()
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == target and reaction.message.id == msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=10.0, check=check)
        end = datetime.datetime.now()
        time_taken = (end - start).total_seconds()
        data = get_user_data(ctx.author.id)
        data["embers"] += int(max(10, 100 - time_taken * 5))
        save()
        await ctx.send(f"nice! {time_taken:.2f} seconds! you won some embers!")
    except asyncio.TimeoutError:
        await ctx.send("too slow! you missed it.")

@bot.command()
async def memorygame(ctx):
    sequence = [random.randint(1, 4) for _ in range(5)]
    await ctx.send("memory game! remember this sequence: " + " ".join(str(x) for x in sequence) + "
you have 5 seconds...")
    await asyncio.sleep(5)
    await ctx.send("now type the sequence back!")
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    try:
        msg = await bot.wait_for("message", timeout=10.0, check=check)
        user_seq = [int(x) for x in msg.content.split() if x.isdigit()]
        if user_seq == sequence:
            data = get_user_data(ctx.author.id)
            data["embers"] += 100
            save()
            await ctx.send(f"correct! you remembered the sequence! won 100 embers!")
        else:
            await ctx.send(f"wrong! the sequence was {' '.join(str(x) for x in sequence)}")
    except asyncio.TimeoutError:
        await ctx.send(f"too slow! the sequence was {' '.join(str(x) for x in sequence)}")

@bot.command()
async def colorguess(ctx):
    colors = ["red", "blue", "green", "yellow", "purple", "orange"]
    target = random.choice(colors)
    await ctx.send(f"guess the color i'm thinking of: {', '.join(colors)} (you have 10 seconds)")
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    try:
        msg = await bot.wait_for("message", timeout=10.0, check=check)
        if msg.content.lower() == target:
            data = get_user_data(ctx.author.id)
            data["embers"] += 30
            save()
            await ctx.send(f"correct! it was {target}! won 30 embers!")
        else:
            await ctx.send(f"wrong! it was {target}.")
    except asyncio.TimeoutError:
        await ctx.send(f"too slow! it was {target}.")

@bot.command()
async def coinflipchallenge(ctx, member: discord.Member, amount: int):
    if member.id == ctx.author.id:
        await ctx.send("challenging yourself? that's just flipping a coin")
        return
    data1 = get_user_data(ctx.author.id)
    data2 = get_user_data(member.id)
    if data1["embers"] < amount or data2["embers"] < amount:
        await ctx.send("one of you is too broke")
        return
    msg = await ctx.send(f"{member.mention}, {ctx.author.mention} challenges you to a coinflip for {amount} embers! react check to accept!")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    def check(reaction, user):
        return user == member and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "❌":
            await ctx.send("they declined. scared?")
            return
    except asyncio.TimeoutError:
        await ctx.send("no response. they chickened out")
        return
    result = random.choice(["heads", "tails"])
    guess = random.choice(["heads", "tails"])
    if result == guess:
        data1["embers"] += amount
        data2["embers"] -= amount
        winner = ctx.author
    else:
        data1["embers"] -= amount
        data2["embers"] += amount
        winner = member
    save()
    await ctx.send(f"it's {result}! {winner.mention} wins {amount} embers!")

@bot.command()
async def highlow(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("you're too broke")
        return
    data["embers"] -= amount
    current = random.randint(1, 100)
    total = current
    await ctx.send(f"starting number: {current}. type 'high' or 'low'. type 'stop' to cash out.")
    while True:
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["high", "low", "stop"]
        try:
            msg = await bot.wait_for("message", timeout=15.0, check=check)
            if msg.content.lower() == "stop":
                data["embers"] += total
                save()
                await ctx.send(f"you cashed out with {total} embers! total embers: {data['embers']}")
                return
            next_num = random.randint(1, 100)
            guess = msg.content.lower()
            if (guess == "high" and next_num > current) or (guess == "low" and next_num < current):
                total += next_num
                current = next_num
                await ctx.send(f"correct! number is {current}. total: {total}. high or low?")
            else:
                save()
                await ctx.send(f"wrong! number was {next_num}. you lost everything. current embers: {data['embers']}")
                return
        except asyncio.TimeoutError:
            save()
            await ctx.send("timed out! you lost your bet.")
            return

@bot.command()
async def doubleornothing(ctx, amount: int):
    data = get_user_data(ctx.author.id)
    if amount > data["embers"]:
        await ctx.send("you're too broke")
        return
    data["embers"] -= amount
    rounds = 0
    current = amount
    while True:
        if random.random() < 0.5:
            rounds += 1
            current *= 2
            msg = await ctx.send(f"round {rounds}: you doubled to {current}! double or nothing? react check to continue, x to stop")
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=15.0, check=check)
                if str(reaction.emoji) == "❌":
                    data["embers"] += current
                    save()
                    await ctx.send(f"smart! you walked away with {current} embers! total: {data['embers']}")
                    return
            except asyncio.TimeoutError:
                save()
                await ctx.send("timed out! you lost everything.")
                return
        else:
            save()
            await ctx.send(f"you lost! goodbye {current} embers. you now have {data['embers']}")
            return

@bot.command()
async def mine(ctx):
    ok, _ = check_cooldown(ctx.author.id, "mine", minutes=5)
    if not ok:
        await ctx.send("your pickaxe broke, wait for repairs")
        return
    data = get_user_data(ctx.author.id)
    finds = [
        ("coal", 10, 30),
        ("iron", 20, 50),
        ("gold", 50, 100),
        ("diamond", 100, 300),
        ("ember ore", 200, 500),
        ("nothing", 0, 0)
    ]
    weights = [40, 30, 15, 8, 5, 2]
    item, min_val, max_val = random.choices(finds, weights=weights)[0]
    if item == "nothing":
        await ctx.send("you mined and found... nothing. empty cave.")
        return
    value = random.randint(min_val, max_val)
    data["embers"] += value
    save()
    await ctx.send(f"you mined some {item} and sold it for {value} embers!")

@bot.command()
async def fish(ctx):
    ok, _ = check_cooldown(ctx.author.id, "fish", minutes=3)
    if not ok:
        await ctx.send("the fish aren't biting right now, wait")
        return
    data = get_user_data(ctx.author.id)
    catches = [
        ("old boot", 5),
        ("small fish", 15),
        ("big fish", 40),
        ("rare fish", 100),
        ("legendary fish", 300),
        ("nothing", 0)
    ]
    weights = [20, 35, 25, 12, 5, 3]
    item, value = random.choices(catches, weights=weights)[0]
    if item == "nothing":
        await ctx.send("you fished for an hour and caught... nothing.")
        return
    data["embers"] += value
    save()
    await ctx.send(f"you caught a {item} and sold it for {value} embers!")

@bot.command()
async def chop(ctx):
    ok, _ = check_cooldown(ctx.author.id, "chop", minutes=5)
    if not ok:
        await ctx.send("your axe is dull, sharpen it first")
        return
    data = get_user_data(ctx.author.id)
    wood = random.randint(10, 50)
    value = wood * 2
    data["embers"] += value
    save()
    await ctx.send(f"you chopped {wood} logs and sold them for {value} embers!")

@bot.command()
async def farm(ctx):
    ok, _ = check_cooldown(ctx.author.id, "farm", minutes=10)
    if not ok:
        await ctx.send("your crops aren't ready yet, wait")
        return
    data = get_user_data(ctx.author.id)
    crops = [
        ("wheat", 20, 40),
        ("carrots", 30, 60),
        ("potatoes", 40, 80),
        ("pumpkins", 80, 150),
        ("ember melons", 150, 300)
    ]
    weights = [35, 30, 20, 10, 5]
    crop, min_val, max_val = random.choices(crops, weights=weights)[0]
    value = random.randint(min_val, max_val)
    data["embers"] += value
    save()
    await ctx.send(f"you harvested {crop} and sold them for {value} embers!")

@bot.command()
async def hunt(ctx):
    ok, _ = check_cooldown(ctx.author.id, "hunt", minutes=5)
    if not ok:
        await ctx.send("the animals are hiding, wait")
        return
    data = get_user_data(ctx.author.id)
    prey = [
        ("rabbit", 10, 20),
        ("deer", 30, 60),
        ("boar", 50, 100),
        ("bear", 100, 200),
        ("dragon", 500, 1000),
        ("nothing", 0, 0)
    ]
    weights = [30, 25, 20, 15, 5, 5]
    animal, min_val, max_val = random.choices(prey, weights=weights)[0]
    if animal == "nothing":
        await ctx.send("you hunted all day and found nothing. nature is cruel.")
        return
    value = random.randint(min_val, max_val)
    data["embers"] += value
    save()
    await ctx.send(f"you hunted a {animal} and sold the pelt for {value} embers!")

@bot.command()
async def forage(ctx):
    ok, _ = check_cooldown(ctx.author.id, "forage", minutes=3)
    if not ok:
        await ctx.send("you foraged too recently, the bushes are empty")
        return
    data = get_user_data(ctx.author.id)
    finds = [
        ("berries", 5, 15),
        ("mushrooms", 10, 25),
        ("herbs", 15, 40),
        ("rare flower", 50, 100),
        ("nothing", 0, 0)
    ]
    weights = [40, 30, 20, 7, 3]
    item, min_val, max_val = random.choices(finds, weights=weights)[0]
    if item == "nothing":
        await ctx.send("you foraged and found... grass. congrats.")
        return
    value = random.randint(min_val, max_val)
    data["embers"] += value
    save()
    await ctx.send(f"you foraged some {item} and sold them for {value} embers!")

@bot.command()
async def craft(ctx, *, item: str):
    recipes = {
        "sword": {"iron": 3, "wood": 2},
        "shield": {"iron": 2, "wood": 3},
        "potion": {"herbs": 2, "water": 1},
        "armor": {"iron": 5, "leather": 3}
    }
    item = item.lower()
    if item not in recipes:
        await ctx.send("that item can't be crafted. try: sword, shield, potion, armor")
        return
    await ctx.send("crafting system needs inventory items. use f buy from shop for now.")

@bot.command()
async def explore(ctx):
    ok, _ = check_cooldown(ctx.author.id, "explore", minutes=10)
    if not ok:
        await ctx.send("you're too tired to explore, rest first")
        return
    data = get_user_data(ctx.author.id)
    locations = [
        ("dark forest", 20, 80),
        ("abandoned mine", 30, 100),
        ("haunted castle", 50, 200),
        ("dragon's lair", 100, 500),
        ("empty field", 0, 0)
    ]
    weights = [30, 25, 20, 10, 15]
    loc, min_val, max_val = random.choices(locations, weights=weights)[0]
    if loc == "empty field":
        await ctx.send(f"you explored the {loc} and found... grass. exciting.")
        return
    value = random.randint(min_val, max_val)
    data["embers"] += value
    save()
    await ctx.send(f"you explored the {loc} and found {value} embers worth of treasure!")

@bot.command()
async def dungeon(ctx):
    ok, _ = check_cooldown(ctx.author.id, "dungeon", hours=2)
    if not ok:
        await ctx.send("the dungeon is still resetting, wait")
        return
    data = get_user_data(ctx.author.id)
    rooms = random.randint(3, 8)
    total = 0
    for i in range(rooms):
        if random.random() < 0.3:
            await ctx.send(f"room {i+1}: a monster attacked! you fled!")
            break
        loot = random.randint(20, 100)
        total += loot
        await ctx.send(f"room {i+1}: cleared! found {loot} embers!")
    data["embers"] += total
    save()
    await ctx.send(f"dungeon run complete! total loot: {total} embers!")

@bot.command()
async def boss(ctx):
    ok, _ = check_cooldown(ctx.author.id, "boss", hours=4)
    if not ok:
        await ctx.send("the boss is recovering, wait")
        return
    data = get_user_data(ctx.author.id)
    boss_power = random.randint(100, 500)
    your_power = sum(c["power"] for c in data["creatures"])
    if your_power > boss_power:
        loot = random.randint(200, 1000)
        data["embers"] += loot
        save()
        await ctx.send(f"you defeated the boss (power {boss_power}) with your {your_power} power! loot: {loot} embers!")
    else:
        await ctx.send(f"the boss (power {boss_power}) destroyed you (power {your_power})! train harder!")

@bot.command()
async def quest(ctx):
    ok, _ = check_cooldown(ctx.author.id, "quest", hours=1)
    if not ok:
        await ctx.send("you're on a quest cooldown, wait")
        return
    data = get_user_data(ctx.author.id)
    quests = [
        ("slay 5 goblins", 100),
        ("find the lost treasure", 200),
        ("rescue the princess", 300),
        ("defeat the dragon", 500),
        ("deliver a package", 50)
    ]
    q, reward = random.choice(quests)
    await ctx.send(f"quest accepted: {q}! reward: {reward} embers! (auto-completed for demo)")
    data["embers"] += reward
    save()
    await ctx.send(f"quest complete! you earned {reward} embers!")

# ========== MORE COMMANDS (batch 5) ==========

@bot.command()
async def pet(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            c["mood"] = min(100, c["mood"] + 10)
            save()
            await ctx.send(f"you petted {c['name']}! mood: {c['mood']}/100. happy creature!")
            return
    await ctx.send("creature not found")

@bot.command()
async def play(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            c["mood"] = min(100, c["mood"] + 15)
            c["power"] += random.randint(1, 3)
            save()
            await ctx.send(f"you played with {c['name']}! mood: {c['mood']}/100, power: {c['power']}")
            return
    await ctx.send("creature not found")

@bot.command()
async def train(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            c["power"] += random.randint(5, 15)
            c["mood"] = max(0, c["mood"] - 5)
            save()
            await ctx.send(f"you trained {c['name']}! power: {c['power']}, mood: {c['mood']}/100. tough love!")
            return
    await ctx.send("creature not found")

@bot.command()
async def heal(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            if data["embers"] < 30:
                await ctx.send("healing costs 30 embers, you're too broke")
                return
            data["embers"] -= 30
            c["mood"] = 100
            save()
            await ctx.send(f"you healed {c['name']}! mood restored to 100/100!")
            return
    await ctx.send("creature not found")

@bot.command()
async def releaseall(ctx):
    data = get_user_data(ctx.author.id)
    count = len(data["creatures"])
    data["creatures"] = []
    save()
    await ctx.send(f"you released all {count} creatures. they're free now. you monster.")

@bot.command()
async def sacrificeall(ctx):
    data = get_user_data(ctx.author.id)
    total = sum(c["power"] * 2 for c in data["creatures"])
    count = len(data["creatures"])
    data["embers"] += total
    data["creatures"] = []
    save()
    await ctx.send(f"you sacrificed all {count} creatures for {total} embers. the dark gods are very pleased.")

@bot.command()
async def creatureinfo(ctx, creature_id: int):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        if c["id"] == creature_id:
            await ctx.send(f"{c['name']} | type: {c['type']} | power: {c['power']} | mood: {c['mood']}/100 | evolution: {c['evolution']} | id: {c['id']}")
            return
    await ctx.send("creature not found")

@bot.command()
async def strongest(ctx):
    data = get_user_data(ctx.author.id)
    if not data["creatures"]:
        await ctx.send("you have no creatures")
        return
    strongest = max(data["creatures"], key=lambda c: c["power"])
    await ctx.send(f"your strongest creature is {strongest['name']} with {strongest['power']} power!")

@bot.command()
async def weakest(ctx):
    data = get_user_data(ctx.author.id)
    if not data["creatures"]:
        await ctx.send("you have no creatures")
        return
    weakest = min(data["creatures"], key=lambda c: c["power"])
    await ctx.send(f"your weakest creature is {weakest['name']} with {weakest['power']} power. pathetic.")

@bot.command()
async def happiest(ctx):
    data = get_user_data(ctx.author.id)
    if not data["creatures"]:
        await ctx.send("you have no creatures")
        return
    happiest = max(data["creatures"], key=lambda c: c["mood"])
    await ctx.send(f"your happiest creature is {happiest['name']} with {happiest['mood']}/100 mood!")

@bot.command()
async def saddest(ctx):
    data = get_user_data(ctx.author.id)
    if not data["creatures"]:
        await ctx.send("you have no creatures")
        return
    saddest = min(data["creatures"], key=lambda c: c["mood"])
    await ctx.send(f"your saddest creature is {saddest['name']} with {saddest['mood']}/100 mood. feed it!")

@bot.command()
async def creaturecount(ctx):
    data = get_user_data(ctx.author.id)
    await ctx.send(f"you have {len(data['creatures'])} creatures")

@bot.command()
async def totalpower(ctx):
    data = get_user_data(ctx.author.id)
    total = sum(c["power"] for c in data["creatures"])
    await ctx.send(f"your creatures' total power is {total}")

@bot.command()
async def totalmood(ctx):
    data = get_user_data(ctx.author.id)
    if not data["creatures"]:
        await ctx.send("you have no creatures")
        return
    avg = sum(c["mood"] for c in data["creatures"]) // len(data["creatures"])
    await ctx.send(f"your creatures' average mood is {avg}/100")

@bot.command()
async def sortpower(ctx):
    data = get_user_data(ctx.author.id)
    if not data["creatures"]:
        await ctx.send("you have no creatures")
        return
    sorted_c = sorted(data["creatures"], key=lambda c: c["power"], reverse=True)
    embed = discord.Embed(title="creatures by power", color=0xff4500)
    for c in sorted_c[:10]:
        embed.add_field(name=f"{c['name']} (id: {c['id']})", value=f"power: {c['power']}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def sortmood(ctx):
    data = get_user_data(ctx.author.id)
    if not data["creatures"]:
        await ctx.send("you have no creatures")
        return
    sorted_c = sorted(data["creatures"], key=lambda c: c["mood"], reverse=True)
    embed = discord.Embed(title="creatures by mood", color=0xff4500)
    for c in sorted_c[:10]:
        embed.add_field(name=f"{c['name']} (id: {c['id']})", value=f"mood: {c['mood']}/100", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def sorttype(ctx, *, ctype: str):
    data = get_user_data(ctx.author.id)
    filtered = [c for c in data["creatures"] if c["type"].lower() == ctype.lower()]
    if not filtered:
        await ctx.send(f"you have no {ctype} type creatures")
        return
    embed = discord.Embed(title=f"{ctype} type creatures", color=0xff4500)
    for c in filtered:
        embed.add_field(name=f"{c['name']} (id: {c['id']})", value=f"power: {c['power']}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def dupecheck(ctx):
    data = get_user_data(ctx.author.id)
    names = [c["name"] for c in data["creatures"]]
    dupes = [n for n in set(names) if names.count(n) > 1]
    if dupes:
        await ctx.send(f"you have duplicates: {', '.join(dupes)}")
    else:
        await ctx.send("no duplicates. all unique!")

@bot.command()
async def releaseweak(ctx):
    data = get_user_data(ctx.author.id)
    if not data["creatures"]:
        await ctx.send("you have no creatures to release")
        return
    weakest = min(data["creatures"], key=lambda c: c["power"])
    data["creatures"].remove(weakest)
    save()
    await ctx.send(f"released your weakest creature: {weakest['name']} (power: {weakest['power']}). bye bye!")

@bot.command()
async def releasesad(ctx):
    data = get_user_data(ctx.author.id)
    if not data["creatures"]:
        await ctx.send("you have no creatures to release")
        return
    saddest = min(data["creatures"], key=lambda c: c["mood"])
    data["creatures"].remove(saddest)
    save()
    await ctx.send(f"released your saddest creature: {saddest['name']} (mood: {saddest['mood']}/100). it'll be happier free!")

@bot.command()
async def massfeed(ctx):
    data = get_user_data(ctx.author.id)
    cost = len(data["creatures"]) * 20
    if data["embers"] < cost:
        await ctx.send(f"mass feed costs {cost} embers, you're too broke")
        return
    data["embers"] -= cost
    for c in data["creatures"]:
        c["mood"] = min(100, c["mood"] + 10)
    save()
    await ctx.send(f"fed all {len(data['creatures'])} creatures for {cost} embers! everyone's happier!")

@bot.command()
async def masstrain(ctx):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        c["power"] += random.randint(2, 8)
        c["mood"] = max(0, c["mood"] - 3)
    save()
    await ctx.send(f"trained all {len(data['creatures'])} creatures! stronger but slightly sadder.")

@bot.command()
async def massevolve(ctx):
    data = get_user_data(ctx.author.id)
    evolved = 0
    for c in data["creatures"]:
        if c["power"] >= 80 and c["mood"] >= 60:
            c["evolution"] += 1
            c["power"] += random.randint(20, 50)
            c["name"] = f"mega {c['name']}"
            evolved += 1
    save()
    if evolved:
        await ctx.send(f"{evolved} creatures evolved! check f creatures!")
    else:
        await ctx.send("no creatures ready to evolve. train and feed them first!")

@bot.command()
async def creatureleaderboard(ctx):
    all_creatures = []
    for uid, data in bot.data.items():
        for c in data["creatures"]:
            all_creatures.append((c, uid))
    if not all_creatures:
        await ctx.send("no creatures exist yet")
        return
    all_creatures.sort(key=lambda x: x[0]["power"], reverse=True)
    embed = discord.Embed(title="global creature leaderboard", color=0xff4500)
    for i, (c, uid) in enumerate(all_creatures[:10]):
        owner = bot.get_user(uid)
        owner_name = owner.name if owner else f"user {uid}"
        embed.add_field(name=f"#{i+1} {c['name']}", value=f"power: {c['power']} | owner: {owner_name}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def tradeall(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("trading all with yourself? that's just... keeping them")
        return
    your_data = get_user_data(ctx.author.id)
    their_data = get_user_data(member.id)
    if not your_data["creatures"] or not their_data["creatures"]:
        await ctx.send("one of you has no creatures to trade")
        return
    msg = await ctx.send(f"{member.mention}, {ctx.author.mention} wants to trade ALL their creatures for ALL yours! react check to accept!")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    def check(reaction, user):
        return user == member and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        if str(reaction.emoji) == "✅":
            your_creatures = your_data["creatures"].copy()
            their_creatures = their_data["creatures"].copy()
            your_data["creatures"] = their_creatures
            their_data["creatures"] = your_creatures
            save()
            await ctx.send(f"mass trade complete! you swapped all creatures!")
        else:
            await ctx.send("trade rejected")
    except asyncio.TimeoutError:
        await ctx.send("trade timed out")

@bot.command()
async def clone(ctx, creature_id: int):
    ok, _ = check_cooldown(ctx.author.id, "clone", hours=6)
    if not ok:
        await ctx.send("cloning machine is cooling down, wait")
        return
    data = get_user_data(ctx.author.id)
    creature = next((c for c in data["creatures"] if c["id"] == creature_id), None)
    if not creature:
        await ctx.send("creature not found")
        return
    if data["embers"] < 500:
        await ctx.send("cloning costs 500 embers, you're too broke")
        return
    data["embers"] -= 500
    clone_c = creature.copy()
    clone_c["id"] = random.randint(1000, 9999)
    clone_c["name"] = f"clone {clone_c['name']}"
    clone_c["power"] = clone_c["power"] // 2
    data["creatures"].append(clone_c)
    save()
    await ctx.send(f"cloned {creature['name']}! meet {clone_c['name']}! (weaker clone but still cool)")

@bot.command()
async def merge(ctx, id1: int, id2: int):
    data = get_user_data(ctx.author.id)
    c1 = next((c for c in data["creatures"] if c["id"] == id1), None)
    c2 = next((c for c in data["creatures"] if c["id"] == id2), None)
    if not c1 or not c2:
        await ctx.send("one or both creatures not found")
        return
    data["creatures"].remove(c1)
    data["creatures"].remove(c2)
    merged = {
        "name": f"fusion {c1['name']}-{c2['name']}",
        "type": random.choice([c1["type"], c2["type"]]),
        "power": c1["power"] + c2["power"],
        "mood": 80,
        "evolution": max(c1["evolution"], c2["evolution"]),
        "favorite": False,
        "id": random.randint(1000, 9999)
    }
    data["creatures"].append(merged)
    save()
    await ctx.send(f"merged {c1['name']} and {c2['name']} into {merged['name']}! power: {merged['power']}!")

@bot.command()
async def releasefav(ctx):
    data = get_user_data(ctx.author.id)
    favs = [c for c in data["creatures"] if c["favorite"]]
    if not favs:
        await ctx.send("you have no favorited creatures")
        return
    for c in favs:
        data["creatures"].remove(c)
    save()
    await ctx.send(f"released {len(favs)} favorited creatures. why would you do that")

@bot.command()
async def favoritelist(ctx):
    data = get_user_data(ctx.author.id)
    favs = [c for c in data["creatures"] if c["favorite"]]
    if not favs:
        await ctx.send("you have no favorited creatures")
        return
    names = ", ".join(c["name"] for c in favs)
    await ctx.send(f"your favorites: {names}")

@bot.command()
async def unfavoriteall(ctx):
    data = get_user_data(ctx.author.id)
    for c in data["creatures"]:
        c["favorite"] = False
    save()
    await ctx.send("unfavorited all creatures. no favorites anymore.")

@bot.command()
async def creaturesearch(ctx, *, name: str):
    data = get_user_data(ctx.author.id)
    matches = [c for c in data["creatures"] if name.lower() in c["name"].lower()]
    if not matches:
        await ctx.send(f"no creatures matching '{name}'")
        return
    embed = discord.Embed(title=f"search results for '{name}'", color=0xff4500)
    for c in matches:
        embed.add_field(name=f"{c['name']} (id: {c['id']})", value=f"power: {c['power']} | mood: {c['mood']}/100", inline=False)
    await ctx.send(embed=embed)

# ========== MORE COMMANDS (batch 6) ==========

@bot.command()
async def afk(ctx, *, reason: str = "afk"):
    if not hasattr(bot, "afk_users"):
        bot.afk_users = {}
    bot.afk_users[ctx.author.id] = reason
    await ctx.send(f"{ctx.author.mention} is now afk: {reason}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if hasattr(bot, "afk_users") and message.author.id in bot.afk_users:
        del bot.afk_users[message.author.id]
        await message.channel.send(f"welcome back {message.author.mention}! i removed your afk status.")
    for mention in message.mentions:
        if hasattr(bot, "afk_users") and mention.id in bot.afk_users:
            await message.channel.send(f"{mention.mention} is afk: {bot.afk_users[mention.id]}")
    await bot.process_commands(message)

@bot.command()
async def snipe(ctx):
    if not hasattr(bot, "deleted_messages") or not bot.deleted_messages.get(ctx.channel.id):
        await ctx.send("nothing to snipe. someone delete a message first")
        return
    msg = bot.deleted_messages[ctx.channel.id][-1]
    embed = discord.Embed(description=msg["content"], color=0xff4500)
    embed.set_author(name=msg["author"], icon_url=msg["avatar"])
    embed.set_footer(text=f"deleted in #{ctx.channel.name}")
    await ctx.send(embed=embed)

@bot.command()
async def editsnipe(ctx):
    if not hasattr(bot, "edited_messages") or not bot.edited_messages.get(ctx.channel.id):
        await ctx.send("nothing to editsnipe. someone edit a message first")
        return
    msg = bot.edited_messages[ctx.channel.id][-1]
    embed = discord.Embed(color=0xff4500)
    embed.add_field(name="before", value=msg["before"], inline=False)
    embed.add_field(name="after", value=msg["after"], inline=False)
    embed.set_author(name=msg["author"])
    await ctx.send(embed=embed)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    if not hasattr(bot, "deleted_messages"):
        bot.deleted_messages = {}
    if message.channel.id not in bot.deleted_messages:
        bot.deleted_messages[message.channel.id] = []
    bot.deleted_messages[message.channel.id].append({
        "content": message.content,
        "author": message.author.name,
        "avatar": message.author.display_avatar.url
    })
    if len(bot.deleted_messages[message.channel.id]) > 10:
        bot.deleted_messages[message.channel.id].pop(0)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    if not hasattr(bot, "edited_messages"):
        bot.edited_messages = {}
    if before.channel.id not in bot.edited_messages:
        bot.edited_messages[before.channel.id] = []
    bot.edited_messages[before.channel.id].append({
        "before": before.content,
        "after": after.content,
        "author": before.author.name
    })
    if len(bot.edited_messages[before.channel.id]) > 10:
        bot.edited_messages[before.channel.id].pop(0)

@bot.command()
async def firstmsg(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    async for msg in channel.history(limit=1, oldest_first=True):
        embed = discord.Embed(description=msg.content, color=0xff4500)
        embed.set_author(name=msg.author.name, icon_url=msg.author.display_avatar.url)
        embed.set_footer(text=f"sent on {msg.created_at.strftime('%Y-%m-%d')}")
        await ctx.send(embed=embed)
        return
    await ctx.send("no messages found")

@bot.command()
async def translate(ctx, lang: str, *, text: str):
    await ctx.send("translation is hard. just learn the language. lazy.")

@bot.command()
async def define(ctx, *, word: str):
    await ctx.send(f"{word}: something that exists. probably. look it up yourself.")

@bot.command()
async def synonym(ctx, *, word: str):
    await ctx.send(f"synonyms for {word}: {word} but different. use a thesaurus.")

@bot.command()
async def antonym(ctx, *, word: str):
    await ctx.send(f"antonym for {word}: not {word}. obvious.")

@bot.command()
async def rhyme(ctx, *, word: str):
    rhymes = {"cat": "hat, bat, rat", "dog": "log, fog, hog", "blue": "true, clue, shoe"}
    await ctx.send(rhymes.get(word.lower(), f"words that rhyme with {word}: idk, google it"))

@bot.command()
async def weatherreal(ctx, *, city: str):
    await ctx.send(f"weather in {city}: probably nice. maybe rainy. who knows. go outside and check.")

@bot.command()
async def news(ctx):
    await ctx.send("latest news: the world is still spinning. embers are still valuable. that's all.")

@bot.command()
async def stock(ctx, *, symbol: str):
    prices = {"aapl": 150, "tsla": 200, "goog": 100, "msft": 300, "amzn": 120}
    price = prices.get(symbol.lower(), random.randint(10, 500))
    change = random.uniform(-5, 5)
    await ctx.send(f"{symbol.upper()}: ${price:.2f} ({change:+.2f}%) not financial advice")

@bot.command()
async def crypto(ctx, *, coin: str):
    prices = {"btc": 45000, "eth": 3000, "doge": 0.1, "shib": 0.00001}
    price = prices.get(coin.lower(), random.uniform(0.001, 1000))
    await ctx.send(f"{coin.upper()}: ${price:.4f} probably gonna crash soon")

@bot.command()
async def movie(ctx, *, title: str):
    ratings = ["10/10 masterpiece", "8/10 pretty good", "5/10 mid", "2/10 garbage", "would not watch"]
    await ctx.send(f"{title}: {random.choice(ratings)}")

@bot.command()
async def game(ctx, *, title: str):
    ratings = ["goty material", "solid 8/10", "mid", "trash", "masterpiece"]
    await ctx.send(f"{title}: {random.choice(ratings)}")

@bot.command()
async def song(ctx, *, title: str):
    ratings = ["banger", "fire", "mid", "skip", "repeat worthy"]
    await ctx.send(f"{title}: {random.choice(ratings)}")

@bot.command()
async def foodrate(ctx, *, food: str):
    ratings = ["delicious", "mid", "gross", "fire", "would eat again"]
    await ctx.send(f"{food}: {random.choice(ratings)}")

@bot.command()
async def drinkrate(ctx, *, drink: str):
    ratings = ["refreshing", "mid", "nasty", "fire", "would drink again"]
    await ctx.send(f"{drink}: {random.choice(ratings)}")

@bot.command()
async def place(ctx, *, location: str):
    ratings = ["beautiful", "mid", "trash", "must visit", "overrated"]
    await ctx.send(f"{location}: {random.choice(ratings)}")

@bot.command()
async def car(ctx, *, model: str):
    ratings = ["fast", "mid", "slow", "luxury", "budget"]
    await ctx.send(f"{model}: {random.choice(ratings)}")

@bot.command()
async def phone(ctx, *, model: str):
    ratings = ["flagship", "mid", "budget", "overpriced", "solid"]
    await ctx.send(f"{model}: {random.choice(ratings)}")

@bot.command()
async def pc(ctx, *, specs: str = "gaming pc"):
    fps = random.randint(30, 300)
    await ctx.send(f"{specs}: runs at {fps} fps on low settings. skill issue.")

@bot.command()
async def console(ctx, *, name: str = "ps5"):
    ratings = ["exclusive games", "mid", "overpriced", "solid", "pc is better"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def anime(ctx, *, title: str):
    ratings = ["peak fiction", "mid", "trash", "masterpiece", "overrated"]
    await ctx.send(f"{title}: {random.choice(ratings)}")

@bot.command()
async def manga(ctx, *, title: str):
    ratings = ["better than anime", "mid", "trash", "masterpiece", "overrated"]
    await ctx.send(f"{title}: {random.choice(ratings)}")

@bot.command()
async def book(ctx, *, title: str):
    ratings = ["page turner", "mid", "boring", "masterpiece", "overrated"]
    await ctx.send(f"{title}: {random.choice(ratings)}")

@bot.command()
async def tv(ctx, *, show: str):
    ratings = ["binge worthy", "mid", "cancel it", "masterpiece", "overrated"]
    await ctx.send(f"{show}: {random.choice(ratings)}")

@bot.command()
async def youtuber(ctx, *, name: str):
    ratings = ["content king", "mid", "clickbait", "legend", "overrated"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def twitch(ctx, *, streamer: str):
    ratings = ["pog", "mid", "boring", "legend", "overrated"]
    await ctx.send(f"{streamer}: {random.choice(ratings)}")

@bot.command()
async def sport(ctx, *, name: str):
    ratings = ["exciting", "mid", "boring", "intense", "overrated"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def team(ctx, *, name: str):
    ratings = ["champions", "mid", "relegation", "dark horse", "overrated"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def player(ctx, *, name: str):
    ratings = ["goat", "mid", "washed", "rising star", "overrated"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def brand(ctx, *, name: str):
    ratings = ["hype", "mid", "overpriced", "quality", "overrated"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def shoe(ctx, *, model: str):
    ratings = ["fire", "mid", "ugly", "comfortable", "overpriced"]
    await ctx.send(f"{model}: {random.choice(ratings)}")

@bot.command()
async def clothes(ctx, *, item: str):
    ratings = ["drip", "mid", "trash", "fire", "overpriced"]
    await ctx.send(f"{item}: {random.choice(ratings)}")

@bot.command()
async def haircut(ctx, *, style: str):
    ratings = ["fresh", "mid", "trash", "fire", "what is that"]
    await ctx.send(f"{style}: {random.choice(ratings)}")

@bot.command()
async def tattoo(ctx, *, design: str):
    ratings = ["sick", "mid", "regret", "fire", "why"]
    await ctx.send(f"{design}: {random.choice(ratings)}")

@bot.command()
async def petrate(ctx, *, animal: str):
    ratings = ["cute", "mid", "ugly", "adorable", "terrifying"]
    await ctx.send(f"{animal}: {random.choice(ratings)}")

@bot.command()
async def plant(ctx, *, name: str):
    ratings = ["thriving", "mid", "dead", "beautiful", "weed"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def color(ctx, *, name: str):
    ratings = ["aesthetic", "mid", "ugly", "fire", "basic"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def font(ctx, *, name: str):
    ratings = ["clean", "mid", "ugly", "aesthetic", "comic sans"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def os(ctx, *, name: str):
    ratings = ["stable", "mid", "buggy", "fast", "linux is better"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def browser(ctx, *, name: str):
    ratings = ["fast", "mid", "slow", "secure", "chrome eats ram"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def ide(ctx, *, name: str):
    ratings = ["powerful", "mid", "bloated", "fast", "vscode is king"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def language(ctx, *, name: str):
    ratings = ["elegant", "mid", "verbose", "fast", "python is best"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def framework(ctx, *, name: str):
    ratings = ["robust", "mid", "bloated", "fast", "overhyped"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def database(ctx, *, name: str):
    ratings = ["reliable", "mid", "slow", "fast", "nosql vs sql"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def cloud(ctx, *, provider: str):
    ratings = ["scalable", "mid", "expensive", "fast", "aws is overpriced"]
    await ctx.send(f"{provider}: {random.choice(ratings)}")

@bot.command()
async def vpn(ctx, *, name: str):
    ratings = ["secure", "mid", "slow", "fast", "nordvpn sponsor"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

@bot.command()
async def antivirus(ctx, *, name: str):
    ratings = ["secure", "mid", "bloatware", "fast", "windows defender is enough"]
    await ctx.send(f"{name}: {random.choice(ratings)}")

# ========== MORE COMMANDS (batch 7) ==========

@bot.command()
async def copypasta(ctx, *, name: str = "navy seal"):
    pastas = {
        "navy seal": "what the heck did you just say about me? i'll have you know i graduated top of my class...",
        "rickroll": "never gonna give you up, never gonna let you down...",
        "bees": "according to all known laws of aviation, there is no way a bee should be able to fly...",
        "shrek": "somebody once told me the world is gonna roll me..."
    }
    await ctx.send(pastas.get(name.lower(), "copypasta not found. make your own."))

@bot.command()
async def emojify(ctx, *, text: str):
    emojis = {"a": "a", "b": "b", "c": "c", "d": "d", "e": "e", "f": "f", "g": "g", "h": "h", "i": "i",
              "j": "j", "k": "k", "l": "l", "m": "m", "n": "n", "o": "o", "p": "p", "q": "q", "r": "r",
              "s": "s", "t": "t", "u": "u", "v": "v", "w": "w", "x": "x", "y": "y", "z": "z", " ": " "}
    result = " ".join(emojis.get(c.lower(), c) for c in text)
    await ctx.send(result)

@bot.command()
async def spoiler(ctx, *, text: str):
    await ctx.send(f"||{text}||")

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
async def strikethrough(ctx, *, text: str):
    await ctx.send(f"~~{text}~~")

@bot.command()
async def codeblock(ctx, *, text: str):
    await ctx.send(f"```{text}```")

@bot.command()
async def inlinecode(ctx, *, text: str):
    await ctx.send(f"`{text}`")

@bot.command()
async def quoteblock(ctx, *, text: str):
    await ctx.send(f"> {text}")

@bot.command()
async def multiquote(ctx, *, text: str):
    lines = text.split("\n")
    quoted = "
".join(f"> {line}" for line in lines)
    await ctx.send(quoted)

@bot.command()
async def mention(ctx, member: discord.Member):
    await ctx.send(f"{member.mention} you got mentioned by {ctx.author.mention}")

@bot.command()
async def everyone(ctx):
    if not has_perm(ctx, "mention_everyone"):
        await ctx.send("you can't ping everyone, nice try")
        return
    await ctx.send("@everyone wake up!")

@bot.command()
async def here(ctx):
    if not has_perm(ctx, "mention_everyone"):
        await ctx.send("you can't ping here, nice try")
        return
    await ctx.send("@here wake up!")

@bot.command()
async def roleping(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    if not has_perm(ctx, "mention_everyone") and role.mentionable == False:
        await ctx.send("you can't ping that role")
        return
    await ctx.send(f"{role.mention} you got pinged!")

@bot.command()
async def dm(ctx, member: discord.Member, *, message: str):
    try:
        await member.send(f"message from {ctx.author.name}: {message}")
        await ctx.send(f"sent dm to {member.mention}")
    except:
        await ctx.send("couldn't dm them. they probably blocked dms.")

@bot.command()
async def massdm(ctx, *, message: str):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    sent = 0
    for member in ctx.guild.members:
        if not member.bot:
            try:
                await member.send(message)
                sent += 1
            except:
                pass
    await ctx.send(f"sent dms to {sent} members")

@bot.command()
async def announceall(ctx, *, message: str):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    for guild in bot.guilds:
        channel = guild.system_channel
        if channel:
            try:
                await channel.send(f"announcement: {message}")
            except:
                pass
    await ctx.send("announced in all servers")

@bot.command()
async def serverlist(ctx):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    embed = discord.Embed(title="server list", color=0xff4500)
    for guild in bot.guilds:
        embed.add_field(name=guild.name, value=f"{guild.member_count} members | id: {guild.id}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def leavserver(ctx, guild_id: int):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    guild = bot.get_guild(guild_id)
    if guild:
        await guild.leave()
        await ctx.send(f"left {guild.name}")
    else:
        await ctx.send("guild not found")

@bot.command()
async def nickall(ctx, *, nickname: str):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    changed = 0
    for member in ctx.guild.members:
        if not member.bot:
            try:
                await member.edit(nick=nickname)
                changed += 1
            except:
                pass
    await ctx.send(f"changed {changed} nicknames to {nickname}")

@bot.command()
async def unbanall(ctx):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    bans = [entry async for entry in ctx.guild.bans()]
    for ban in bans:
        await ctx.guild.unban(ban.user)
    await ctx.send(f"unbanned {len(bans)} users")

@bot.command()
async def backup(ctx):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    bot.save_data()
    await ctx.send("data backed up to flame_data.json")

@bot.command()
async def restore(ctx):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    bot.load_data()
    await ctx.send("data restored from flame_data.json")

@bot.command()
async def evalcmd(ctx, *, code: str):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    try:
        result = eval(code)
        await ctx.send(f"result: {result}")
    except Exception as e:
        await ctx.send(f"error: {e}")

@bot.command()
async def execmd(ctx, *, code: str):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    try:
        exec(code)
        await ctx.send("executed successfully")
    except Exception as e:
        await ctx.send(f"error: {e}")

@bot.command()
async def shutdown(ctx):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    await ctx.send("shutting down...")
    await bot.close()

@bot.command()
async def restart(ctx):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    await ctx.send("restarting...")
    await bot.close()

@bot.command()
async def status(ctx, *, text: str):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    await bot.change_presence(activity=discord.Game(name=text))
    await ctx.send(f"status set to: {text}")

@bot.command()
async def playing(ctx, *, game: str):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    await bot.change_presence(activity=discord.Game(name=game))
    await ctx.send(f"now playing: {game}")

@bot.command()
async def watching(ctx, *, thing: str):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=thing))
    await ctx.send(f"now watching: {thing}")

@bot.command()
async def listening(ctx, *, thing: str):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=thing))
    await ctx.send(f"now listening to: {thing}")

@bot.command()
async def streaming(ctx, *, thing: str):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    await bot.change_presence(activity=discord.Streaming(name=thing, url="https://twitch.tv/flamebot"))
    await ctx.send(f"now streaming: {thing}")

@bot.command()
async def setavatar(ctx, url: str):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    try:
        async with bot.session.get(url) as resp:
            await bot.user.edit(avatar=await resp.read())
        await ctx.send("avatar updated")
    except:
        await ctx.send("failed to update avatar")

@bot.command()
async def setname(ctx, *, name: str):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    await bot.user.edit(username=name)
    await ctx.send(f"name changed to {name}")

@bot.command()
async def guilds(ctx):
    await ctx.send(f"i'm in {len(bot.guilds)} servers with {sum(g.member_count for g in bot.guilds)} total members")

@bot.command()
async def channels(ctx):
    await ctx.send(f"this server has {len(ctx.guild.channels)} channels")

@bot.command()
async def roleslist(ctx):
    roles = ", ".join(r.name for r in ctx.guild.roles if r.name != "@everyone")
    await ctx.send(f"roles: {roles}")

@bot.command()
async def emojislist(ctx):
    emojis = ", ".join(str(e) for e in ctx.guild.emojis)
    if not emojis:
        await ctx.send("no custom emojis in this server")
        return
    await ctx.send(f"custom emojis: {emojis}")

@bot.command()
async def stickerslist(ctx):
    if not ctx.guild.stickers:
        await ctx.send("no stickers in this server")
        return
    stickers = ", ".join(s.name for s in ctx.guild.stickers)
    await ctx.send(f"stickers: {stickers}")

@bot.command()
async def banslist(ctx):
    if not has_perm(ctx, "ban_members"):
        await ctx.send("you need ban perms for this")
        return
    bans = [entry async for entry in ctx.guild.bans()]
    if not bans:
        await ctx.send("no banned users")
        return
    embed = discord.Embed(title="banned users", color=0xff4500)
    for ban in bans[:20]:
        embed.add_field(name=ban.user.name, value=f"reason: {ban.reason or 'none'}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def invites(ctx):
    if not has_perm(ctx, "manage_guild"):
        await ctx.send("you need manage guild perms")
        return
    invites = await ctx.guild.invites()
    if not invites:
        await ctx.send("no active invites")
        return
    embed = discord.Embed(title="active invites", color=0xff4500)
    for inv in invites[:10]:
        embed.add_field(name=inv.code, value=f"uses: {inv.uses} | by: {inv.inviter.name if inv.inviter else 'unknown'}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def permissions(ctx, member: discord.Member = None):
    member = member or ctx.author
    perms = []
    for perm, value in member.guild_permissions:
        if value:
            perms.append(perm)
    await ctx.send(f"{member.mention} has these perms: {', '.join(perms) if perms else 'none'}")

@bot.command()
async def channelinfo(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    embed = discord.Embed(title=f"#{channel.name} info", color=0xff4500)
    embed.add_field(name="id", value=channel.id)
    embed.add_field(name="created", value=channel.created_at.strftime("%Y-%m-%d"))
    embed.add_field(name="nsfw", value=channel.is_nsfw())
    embed.add_field(name="slowmode", value=f"{channel.slowmode_delay}s")
    embed.add_field(name="category", value=channel.category.name if channel.category else "none")
    await ctx.send(embed=embed)

@bot.command()
async def roleinfo(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    embed = discord.Embed(title=f"{role.name} info", color=role.color)
    embed.add_field(name="id", value=role.id)
    embed.add_field(name="color", value=str(role.color))
    embed.add_field(name="members", value=len(role.members))
    embed.add_field(name="hoisted", value=role.hoist)
    embed.add_field(name="mentionable", value=role.mentionable)
    await ctx.send(embed=embed)

@bot.command()
async def voiceinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    if not member.voice:
        await ctx.send(f"{member.mention} is not in a voice channel")
        return
    vc = member.voice.channel
    embed = discord.Embed(title=f"{member.name}'s voice info", color=0xff4500)
    embed.add_field(name="channel", value=vc.name)
    embed.add_field(name="members", value=len(vc.members))
    embed.add_field(name="bitrate", value=f"{vc.bitrate // 1000}kbps")
    embed.add_field(name="user limit", value=vc.user_limit or "unlimited")
    await ctx.send(embed=embed)

@bot.command()
async def move(ctx, member: discord.Member, channel: discord.VoiceChannel):
    if not has_perm(ctx, "move_members"):
        await ctx.send("you need move members perms")
        return
    if not member.voice:
        await ctx.send(f"{member.mention} is not in a voice channel")
        return
    await member.move_to(channel)
    await ctx.send(f"moved {member.mention} to {channel.name}")

@bot.command()
async def deafen(ctx, member: discord.Member):
    if not has_perm(ctx, "deafen_members"):
        await ctx.send("you need deafen members perms")
        return
    await member.edit(deafen=True)
    await ctx.send(f"deafened {member.mention}")

@bot.command()
async def undeafen(ctx, member: discord.Member):
    if not has_perm(ctx, "deafen_members"):
        await ctx.send("you need deafen members perms")
        return
    await member.edit(deafen=False)
    await ctx.send(f"undeafened {member.mention}")

@bot.command()
async def mutevoice(ctx, member: discord.Member):
    if not has_perm(ctx, "mute_members"):
        await ctx.send("you need mute members perms")
        return
    await member.edit(mute=True)
    await ctx.send(f"voice muted {member.mention}")

@bot.command()
async def unmutevoice(ctx, member: discord.Member):
    if not has_perm(ctx, "mute_members"):
        await ctx.send("you need mute members perms")
        return
    await member.edit(mute=False)
    await ctx.send(f"voice unmuted {member.mention}")

@bot.command()
async def disconnect(ctx, member: discord.Member):
    if not has_perm(ctx, "move_members"):
        await ctx.send("you need move members perms")
        return
    if not member.voice:
        await ctx.send(f"{member.mention} is not in a voice channel")
        return
    await member.move_to(None)
    await ctx.send(f"disconnected {member.mention} from voice")

# ========== MORE COMMANDS (batch 8) ==========

@bot.command()
async def deafenall(ctx):
    if not has_perm(ctx, "deafen_members"):
        await ctx.send("you need deafen members perms")
        return
    if not ctx.author.voice:
        await ctx.send("you're not in a voice channel")
        return
    count = 0
    for member in ctx.author.voice.channel.members:
        if member != ctx.author:
            try:
                await member.edit(deafen=True)
                count += 1
            except:
                pass
    await ctx.send(f"deafened {count} members")

@bot.command()
async def muteall(ctx):
    if not has_perm(ctx, "mute_members"):
        await ctx.send("you need mute members perms")
        return
    if not ctx.author.voice:
        await ctx.send("you're not in a voice channel")
        return
    count = 0
    for member in ctx.author.voice.channel.members:
        if member != ctx.author:
            try:
                await member.edit(mute=True)
                count += 1
            except:
                pass
    await ctx.send(f"muted {count} members")

@bot.command()
async def undeafenall(ctx):
    if not has_perm(ctx, "deafen_members"):
        await ctx.send("you need deafen members perms")
        return
    if not ctx.author.voice:
        await ctx.send("you're not in a voice channel")
        return
    count = 0
    for member in ctx.author.voice.channel.members:
        try:
            await member.edit(deafen=False)
            count += 1
        except:
            pass
    await ctx.send(f"undeafened {count} members")

@bot.command()
async def unmuteall(ctx):
    if not has_perm(ctx, "mute_members"):
        await ctx.send("you need mute members perms")
        return
    if not ctx.author.voice:
        await ctx.send("you're not in a voice channel")
        return
    count = 0
    for member in ctx.author.voice.channel.members:
        try:
            await member.edit(mute=False)
            count += 1
        except:
            pass
    await ctx.send(f"unmuted {count} members")

@bot.command()
async def moveall(ctx, channel: discord.VoiceChannel):
    if not has_perm(ctx, "move_members"):
        await ctx.send("you need move members perms")
        return
    if not ctx.author.voice:
        await ctx.send("you're not in a voice channel")
        return
    count = 0
    for member in ctx.author.voice.channel.members:
        try:
            await member.move_to(channel)
            count += 1
        except:
            pass
    await ctx.send(f"moved {count} members to {channel.name}")

@bot.command()
async def disconnectall(ctx):
    if not has_perm(ctx, "move_members"):
        await ctx.send("you need move members perms")
        return
    if not ctx.author.voice:
        await ctx.send("you're not in a voice channel")
        return
    count = 0
    for member in ctx.author.voice.channel.members:
        if member != ctx.author:
            try:
                await member.move_to(None)
                count += 1
            except:
                pass
    await ctx.send(f"disconnected {count} members")

@bot.command()
async def voicekick(ctx, member: discord.Member):
    if not has_perm(ctx, "move_members"):
        await ctx.send("you need move members perms")
        return
    if not member.voice:
        await ctx.send(f"{member.mention} is not in voice")
        return
    await member.move_to(None)
    await ctx.send(f"voice kicked {member.mention}")

@bot.command()
async def tempmute(ctx, member: discord.Member, minutes: int, *, reason: str = "no reason"):
    if not has_perm(ctx, "mute_members"):
        await ctx.send("you need mute members perms")
        return
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, speak=False)
    await member.add_roles(muted_role, reason=reason)
    await ctx.send(f"tempmuted {member.mention} for {minutes} minutes. reason: {reason}")
    await asyncio.sleep(minutes * 60)
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        await ctx.send(f"{member.mention} has been unmuted")

@bot.command()
async def tempban(ctx, member: discord.Member, days: int, *, reason: str = "no reason"):
    if not has_perm(ctx, "ban_members"):
        await ctx.send("you need ban members perms")
        return
    await member.ban(reason=reason)
    await ctx.send(f"tempbanned {member.mention} for {days} days. reason: {reason}")
    await asyncio.sleep(days * 86400)
    await ctx.guild.unban(member)
    await ctx.send(f"{member.mention} has been unbanned")

@bot.command()
async def softban(ctx, member: discord.Member, *, reason: str = "no reason"):
    if not has_perm(ctx, "ban_members"):
        await ctx.send("you need ban members perms")
        return
    await member.ban(reason=reason)
    await ctx.guild.unban(member)
    await ctx.send(f"softbanned {member.mention}. their messages are deleted but they can rejoin. reason: {reason}")

@bot.command()
async def hardban(ctx, member: discord.Member, *, reason: str = "no reason"):
    if not has_perm(ctx, "ban_members"):
        await ctx.send("you need ban members perms")
        return
    await member.ban(reason=reason, delete_message_days=7)
    await ctx.send(f"hardbanned {member.mention}. deleted 7 days of messages. reason: {reason}")

@bot.command()
async def hackban(ctx, user_id: int, *, reason: str = "no reason"):
    if not has_perm(ctx, "ban_members"):
        await ctx.send("you need ban members perms")
        return
    user = await bot.fetch_user(user_id)
    await ctx.guild.ban(user, reason=reason)
    await ctx.send(f"hackbanned {user.mention}. they weren't even in the server. evil.")

@bot.command()
async def unbanid(ctx, user_id: int):
    if not has_perm(ctx, "ban_members"):
        await ctx.send("you need ban members perms")
        return
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"unbanned {user.mention}")

@bot.command()
async def banlist(ctx):
    if not has_perm(ctx, "ban_members"):
        await ctx.send("you need ban members perms")
        return
    bans = [entry async for entry in ctx.guild.bans()]
    if not bans:
        await ctx.send("no banned users")
        return
    embed = discord.Embed(title="banned users", color=0xff4500)
    for ban in bans[:25]:
        embed.add_field(name=ban.user.name, value=f"id: {ban.user.id} | reason: {ban.reason or 'none'}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def addrole(ctx, member: discord.Member, *, role_name: str):
    if not has_perm(ctx, "manage_roles"):
        await ctx.send("you need manage roles perms")
        return
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    await member.add_roles(role)
    await ctx.send(f"gave {role.name} to {member.mention}")

@bot.command()
async def removerole(ctx, member: discord.Member, *, role_name: str):
    if not has_perm(ctx, "manage_roles"):
        await ctx.send("you need manage roles perms")
        return
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    await member.remove_roles(role)
    await ctx.send(f"removed {role.name} from {member.mention}")

@bot.command()
async def createtext(ctx, *, name: str):
    if not has_perm(ctx, "manage_channels"):
        await ctx.send("you need manage channels perms")
        return
    channel = await ctx.guild.create_text_channel(name)
    await ctx.send(f"created {channel.mention}")

@bot.command()
async def createvoice(ctx, *, name: str):
    if not has_perm(ctx, "manage_channels"):
        await ctx.send("you need manage channels perms")
        return
    channel = await ctx.guild.create_voice_channel(name)
    await ctx.send(f"created {channel.mention}")

@bot.command()
async def createcategory(ctx, *, name: str):
    if not has_perm(ctx, "manage_channels"):
        await ctx.send("you need manage channels perms")
        return
    category = await ctx.guild.create_category(name)
    await ctx.send(f"created category {category.name}")

@bot.command()
async def deletecategory(ctx, *, name: str):
    if not has_perm(ctx, "manage_channels"):
        await ctx.send("you need manage channels perms")
        return
    category = discord.utils.get(ctx.guild.categories, name=name)
    if not category:
        await ctx.send("category not found")
        return
    await category.delete()
    await ctx.send(f"deleted category {name}")

@bot.command()
async def renamechannel(ctx, channel: discord.TextChannel, *, new_name: str):
    if not has_perm(ctx, "manage_channels"):
        await ctx.send("you need manage channels perms")
        return
    old = channel.name
    await channel.edit(name=new_name)
    await ctx.send(f"renamed #{old} to #{new_name}")

@bot.command()
async def nsfw(ctx, channel: discord.TextChannel = None):
    if not has_perm(ctx, "manage_channels"):
        await ctx.send("you need manage channels perms")
        return
    channel = channel or ctx.channel
    await channel.edit(nsfw=not channel.is_nsfw())
    status = "enabled" if channel.is_nsfw() else "disabled"
    await ctx.send(f"nsfw {status} for {channel.mention}")

@bot.command()
async def topic(ctx, channel: discord.TextChannel = None, *, new_topic: str = None):
    if not has_perm(ctx, "manage_channels"):
        await ctx.send("you need manage channels perms")
        return
    channel = channel or ctx.channel
    if not new_topic:
        await ctx.send(f"current topic: {channel.topic or 'none'}")
        return
    await channel.edit(topic=new_topic)
    await ctx.send(f"set topic for {channel.mention}")

@bot.command()
async def sync(ctx):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    await bot.tree.sync()
    await ctx.send("commands synced")

@bot.command()
async def clearsync(ctx):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    bot.tree.clear_commands(guild=ctx.guild)
    await bot.tree.sync(guild=ctx.guild)
    await ctx.send("commands cleared and synced")

@bot.command()
async def guildsync(ctx):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    await bot.tree.sync(guild=ctx.guild)
    await ctx.send("guild commands synced")

@bot.command()
async def copyserver(ctx, guild_id: int):
    if not is_owner(ctx):
        await ctx.send("owner only command")
        return
    source = bot.get_guild(guild_id)
    if not source:
        await ctx.send("guild not found")
        return
    for channel in source.channels:
        try:
            if isinstance(channel, discord.TextChannel):
                await ctx.guild.create_text_channel(channel.name, category=channel.category)
            elif isinstance(channel, discord.VoiceChannel):
                await ctx.guild.create_voice_channel(channel.name, category=channel.category)
        except:
            pass
    await ctx.send(f"copied channels from {source.name}")

@bot.command()
async def clonechannel(ctx, channel: discord.TextChannel):
    if not has_perm(ctx, "manage_channels"):
        await ctx.send("you need manage channels perms")
        return
    new = await channel.clone()
    await ctx.send(f"cloned {channel.mention} to {new.mention}")

@bot.command()
async def archive(ctx, channel: discord.TextChannel = None):
    if not has_perm(ctx, "manage_channels"):
        await ctx.send("you need manage channels perms")
        return
    channel = channel or ctx.channel
    await channel.edit(name=f"archived-{channel.name}")
    await ctx.send(f"archived {channel.mention}")

@bot.command()
async def pin(ctx, message_id: int):
    if not has_perm(ctx, "manage_messages"):
        await ctx.send("you need manage messages perms")
        return
    try:
        msg = await ctx.channel.fetch_message(message_id)
        await msg.pin()
        await ctx.send("message pinned")
    except:
        await ctx.send("couldn't pin that message")

@bot.command()
async def unpin(ctx, message_id: int):
    if not has_perm(ctx, "manage_messages"):
        await ctx.send("you need manage messages perms")
        return
    try:
        msg = await ctx.channel.fetch_message(message_id)
        await msg.unpin()
        await ctx.send("message unpinned")
    except:
        await ctx.send("couldn't unpin that message")

@bot.command()
async def pins(ctx):
    pins = await ctx.channel.pins()
    if not pins:
        await ctx.send("no pinned messages")
        return
    embed = discord.Embed(title="pinned messages", color=0xff4500)
    for pin in pins[:10]:
        embed.add_field(name=f"by {pin.author.name}", value=pin.content[:100] or "[no text]", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def react(ctx, message_id: int, emoji: str):
    try:
        msg = await ctx.channel.fetch_message(message_id)
        await msg.add_reaction(emoji)
        await ctx.send("reacted")
    except:
        await ctx.send("couldn't react to that message")

@bot.command()
async def unreact(ctx, message_id: int, emoji: str):
    try:
        msg = await ctx.channel.fetch_message(message_id)
        await msg.remove_reaction(emoji, bot.user)
        await ctx.send("removed reaction")
    except:
        await ctx.send("couldn't remove reaction")

@bot.command()
async def clearreacts(ctx, message_id: int):
    if not has_perm(ctx, "manage_messages"):
        await ctx.send("you need manage messages perms")
        return
    try:
        msg = await ctx.channel.fetch_message(message_id)
        await msg.clear_reactions()
        await ctx.send("cleared all reactions")
    except:
        await ctx.send("couldn't clear reactions")

@bot.command()
async def reactall(ctx, message_id: int):
    emojis = ["fire", "water", "earth", "wind", "heart", "star", "moon", "sun"]
    try:
        msg = await ctx.channel.fetch_message(message_id)
        for emoji in emojis:
            await msg.add_reaction(emoji)
        await ctx.send("added reactions")
    except:
        await ctx.send("couldn't react")

# ========== MORE COMMANDS (batch 9) ==========

@bot.command()
async def typingstart(ctx):
    await ctx.channel.trigger_typing()
    await ctx.send("started typing...")

@bot.command()
async def typingstop(ctx):
    await ctx.send("stopped typing")

@bot.command()
async def typingduration(ctx, seconds: int):
    await ctx.channel.trigger_typing()
    await asyncio.sleep(seconds)
    await ctx.send(f"typed for {seconds} seconds")

@bot.command()
async def messagecount(ctx, member: discord.Member = None):
    member = member or ctx.author
    count = 0
    async for msg in ctx.channel.history(limit=1000):
        if msg.author.id == member.id:
            count += 1
    await ctx.send(f"{member.mention} sent {count} messages in the last 1000")

@bot.command()
async def firstmessage(ctx, member: discord.Member = None):
    member = member or ctx.author
    async for msg in ctx.channel.history(limit=10000):
        if msg.author.id == member.id:
            embed = discord.Embed(description=msg.content, color=0xff4500)
            embed.set_author(name=msg.author.name)
            embed.set_footer(text=f"sent {msg.created_at.strftime('%Y-%m-%d')}")
            await ctx.send(embed=embed)
            return
    await ctx.send("no messages found from that user")

@bot.command()
async def lastmessage(ctx, member: discord.Member = None):
    member = member or ctx.author
    async for msg in ctx.channel.history(limit=100):
        if msg.author.id == member.id:
            embed = discord.Embed(description=msg.content, color=0xff4500)
            embed.set_author(name=msg.author.name)
            await ctx.send(embed=embed)
            return
    await ctx.send("no recent messages from that user")

@bot.command()
async def messageinfo(ctx, message_id: int):
    try:
        msg = await ctx.channel.fetch_message(message_id)
        embed = discord.Embed(title="message info", color=0xff4500)
        embed.add_field(name="author", value=msg.author.mention)
        embed.add_field(name="content", value=msg.content[:1000] or "[no text]")
        embed.add_field(name="created", value=msg.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        embed.add_field(name="edited", value=msg.edited_at.strftime("%Y-%m-%d %H:%M:%S") if msg.edited_at else "never")
        embed.add_field(name="reactions", value=len(msg.reactions))
        embed.add_field(name="attachments", value=len(msg.attachments))
        await ctx.send(embed=embed)
    except:
        await ctx.send("message not found")

@bot.command()
async def quote(ctx, message_id: int):
    try:
        msg = await ctx.channel.fetch_message(message_id)
        embed = discord.Embed(description=msg.content, color=0xff4500)
        embed.set_author(name=msg.author.name, icon_url=msg.author.display_avatar.url)
        embed.set_footer(text=f"#{msg.channel.name}")
        await ctx.send(embed=embed)
    except:
        await ctx.send("message not found")

@bot.command()
async def steal(ctx, message_id: int):
    try:
        msg = await ctx.channel.fetch_message(message_id)
        if msg.attachments:
            for att in msg.attachments:
                await ctx.send(att.url)
        elif msg.embeds:
            for emb in msg.embeds:
                await ctx.send(embed=emb)
        else:
            await ctx.send("no attachments or embeds to steal")
    except:
        await ctx.send("message not found")

@bot.command()
async def reactcount(ctx, message_id: int):
    try:
        msg = await ctx.channel.fetch_message(message_id)
        if not msg.reactions:
            await ctx.send("no reactions on that message")
            return
        embed = discord.Embed(title="reaction counts", color=0xff4500)
        for reaction in msg.reactions:
            embed.add_field(name=str(reaction.emoji), value=f"{reaction.count} reactions", inline=False)
        await ctx.send(embed=embed)
    except:
        await ctx.send("message not found")

@bot.command()
async def mostreacted(ctx):
    most = None
    most_count = 0
    async for msg in ctx.channel.history(limit=100):
        total = sum(r.count for r in msg.reactions)
        if total > most_count:
            most = msg
            most_count = total
    if most:
        embed = discord.Embed(description=most.content, color=0xff4500)
        embed.set_author(name=most.author.name)
        embed.set_footer(text=f"{most_count} total reactions")
        await ctx.send(embed=embed)
    else:
        await ctx.send("no reacted messages found")

@bot.command()
async def oldestmember(ctx):
    oldest = min(ctx.guild.members, key=lambda m: m.joined_at or datetime.datetime.now())
    await ctx.send(f"oldest member: {oldest.mention} joined {oldest.joined_at.strftime('%Y-%m-%d') if oldest.joined_at else 'unknown'}")

@bot.command()
async def newestmember(ctx):
    newest = max(ctx.guild.members, key=lambda m: m.joined_at or datetime.datetime.min)
    await ctx.send(f"newest member: {newest.mention} joined {newest.joined_at.strftime('%Y-%m-%d') if newest.joined_at else 'unknown'}")

@bot.command()
async def membercount(ctx):
    await ctx.send(f"this server has {ctx.guild.member_count} members")

@bot.command()
async def botcount(ctx):
    bots = sum(1 for m in ctx.guild.members if m.bot)
    await ctx.send(f"this server has {bots} bots")

@bot.command()
async def humancount(ctx):
    humans = sum(1 for m in ctx.guild.members if not m.bot)
    await ctx.send(f"this server has {humans} humans")

@bot.command()
async def onlinecount(ctx):
    online = sum(1 for m in ctx.guild.members if m.status != discord.Status.offline)
    await ctx.send(f"{online} members are online")

@bot.command()
async def offlinecount(ctx):
    offline = sum(1 for m in ctx.guild.members if m.status == discord.Status.offline)
    await ctx.send(f"{offline} members are offline")

@bot.command()
async def boosting(ctx):
    boosters = [m for m in ctx.guild.members if m.premium_since]
    if not boosters:
        await ctx.send("no boosters. sad.")
        return
    embed = discord.Embed(title="server boosters", color=0xff4500)
    for booster in boosters[:10]:
        embed.add_field(name=booster.name, value=f"boosting since {booster.premium_since.strftime('%Y-%m-%d')}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def boostlevel(ctx):
    await ctx.send(f"server boost level: {ctx.guild.premium_tier} | boosts: {ctx.guild.premium_subscription_count}")

@bot.command()
async def vanityurl(ctx):
    if ctx.guild.vanity_url:
        await ctx.send(f"vanity url: {ctx.guild.vanity_url}")
    else:
        await ctx.send("no vanity url set")

@bot.command()
async def discovery(ctx):
    await ctx.send(f"discovery splash: {ctx.guild.discovery_splash.url if ctx.guild.discovery_splash else 'none'}")

@bot.command()
async def banner(ctx):
    if ctx.guild.banner:
        embed = discord.Embed(title="server banner")
        embed.set_image(url=ctx.guild.banner.url)
        await ctx.send(embed=embed)
    else:
        await ctx.send("no server banner")

@bot.command()
async def icon(ctx):
    if ctx.guild.icon:
        embed = discord.Embed(title="server icon")
        embed.set_image(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)
    else:
        await ctx.send("no server icon")

@bot.command()
async def splash(ctx):
    if ctx.guild.splash:
        embed = discord.Embed(title="invite splash")
        embed.set_image(url=ctx.guild.splash.url)
        await ctx.send(embed=embed)
    else:
        await ctx.send("no invite splash")

@bot.command()
async def afkchannel(ctx):
    if ctx.guild.afk_channel:
        await ctx.send(f"afk channel: {ctx.guild.afk_channel.mention}")
    else:
        await ctx.send("no afk channel set")

@bot.command()
async def afktimeout(ctx):
    await ctx.send(f"afk timeout: {ctx.guild.afk_timeout} seconds")

@bot.command()
async def verificationlevel(ctx):
    levels = ["none", "low", "medium", "high", "very high"]
    await ctx.send(f"verification level: {levels[ctx.guild.verification_level.value]}")

@bot.command()
async def defaultnotifications(ctx):
    await ctx.send(f"default notifications: {ctx.guild.default_notifications.name}")

@bot.command()
async def explicitcontent(ctx):
    await ctx.send(f"explicit content filter: {ctx.guild.explicit_content_filter.name}")

@bot.command()
async def mfa(ctx):
    await ctx.send(f"mfa level: {ctx.guild.mfa_level.name}")

@bot.command()
async def ownerinfo(ctx):
    owner = ctx.guild.owner
    if owner:
        embed = discord.Embed(title="server owner info", color=0xff4500)
        embed.add_field(name="name", value=owner.name)
        embed.add_field(name="id", value=owner.id)
        embed.set_thumbnail(url=owner.display_avatar.url)
        await ctx.send(embed=embed)
    else:
        await ctx.send("owner not found")

@bot.command()
async def createdate(ctx):
    await ctx.send(f"server created: {ctx.guild.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

@bot.command()
async def region(ctx):
    await ctx.send(f"server region: {ctx.guild.preferred_locale}")

@bot.command()
async def features(ctx):
    features = ", ".join(ctx.guild.features) if ctx.guild.features else "none"
    await ctx.send(f"server features: {features}")

@bot.command()
async def maxmembers(ctx):
    await ctx.send(f"max members: {ctx.guild.max_members or 'unlimited'}")

@bot.command()
async def maxpresences(ctx):
    await ctx.send(f"max presences: {ctx.guild.max_presences or 'unlimited'}")

@bot.command()
async def maxvideousers(ctx):
    await ctx.send(f"max video channel users: {ctx.guild.max_video_channel_users or 'unlimited'}")

@bot.command()
async def widget(ctx):
    if ctx.guild.widget_enabled:
        await ctx.send(f"widget enabled: {ctx.guild.widget_enabled} | channel: {ctx.guild.widget_channel.mention if ctx.guild.widget_channel else 'none'}")
    else:
        await ctx.send("widget disabled")

@bot.command()
async def systemchannel(ctx):
    if ctx.guild.system_channel:
        await ctx.send(f"system channel: {ctx.guild.system_channel.mention}")
    else:
        await ctx.send("no system channel")

@bot.command()
async def ruleschannel(ctx):
    if ctx.guild.rules_channel:
        await ctx.send(f"rules channel: {ctx.guild.rules_channel.mention}")
    else:
        await ctx.send("no rules channel")

@bot.command()
async def updateschannel(ctx):
    if ctx.guild.public_updates_channel:
        await ctx.send(f"updates channel: {ctx.guild.public_updates_channel.mention}")
    else:
        await ctx.send("no updates channel")

# ========== MORE COMMANDS (batch 10) ==========

@bot.command()
async def rolecolor(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    await ctx.send(f"{role.name} color: {role.color}")

@bot.command()
async def rolemembers(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    members = ", ".join(m.mention for m in role.members[:20])
    await ctx.send(f"{role.name} members: {members if members else 'none'}")

@bot.command()
async def roleposition(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    await ctx.send(f"{role.name} position: {role.position}")

@bot.command()
async def rolecreated(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    await ctx.send(f"{role.name} created: {role.created_at.strftime('%Y-%m-%d')}")

@bot.command()
async def rolepermissions(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    perms = [p for p, v in role.permissions if v]
    await ctx.send(f"{role.name} permissions: {', '.join(perms) if perms else 'none'}")

@bot.command()
async def roleicon(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    if role.icon:
        embed = discord.Embed(title=f"{role.name} icon")
        embed.set_image(url=role.icon.url)
        await ctx.send(embed=embed)
    else:
        await ctx.send("no role icon")

@bot.command()
async def roleunicode(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    if role.unicode_emoji:
        await ctx.send(f"{role.name} unicode emoji: {role.unicode_emoji}")
    else:
        await ctx.send("no unicode emoji")

@bot.command()
async def rolemanaged(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    await ctx.send(f"{role.name} managed: {role.managed}")

@bot.command()
async def rolementionable(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    await ctx.send(f"{role.name} mentionable: {role.mentionable}")

@bot.command()
async def rolehoist(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    await ctx.send(f"{role.name} hoisted: {role.hoist}")

@bot.command()
async def roleid(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    await ctx.send(f"{role.name} id: {role.id}")

@bot.command()
async def rolecount(ctx):
    await ctx.send(f"this server has {len(ctx.guild.roles)} roles")

@bot.command()
async def rolelist(ctx):
    roles = ", ".join(r.name for r in sorted(ctx.guild.roles, key=lambda r: r.position, reverse=True) if r.name != "@everyone")
    await ctx.send(f"roles: {roles}")

@bot.command()
async def memberroles(ctx, member: discord.Member = None):
    member = member or ctx.author
    roles = ", ".join(r.name for r in member.roles if r.name != "@everyone")
    await ctx.send(f"{member.mention} roles: {roles if roles else 'none'}")

@bot.command()
async def toprole(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f"{member.mention} top role: {member.top_role.name}")

@bot.command()
async def rolecolorhex(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    await ctx.send(f"{role.name} hex color: {str(role.color)}")

@bot.command()
async def rolecolorrgb(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    r, g, b = role.color.to_rgb()
    await ctx.send(f"{role.name} rgb: ({r}, {g}, {b})")

@bot.command()
async def rolecolortag(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    await ctx.send(f"{role.name} color: {role.color}")

@bot.command()
async def changerolecolor(ctx, *, role_name: str, hex_color: str):
    if not has_perm(ctx, "manage_roles"):
        await ctx.send("you need manage roles perms")
        return
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    try:
        color = discord.Color(int(hex_color.replace("#", ""), 16))
        await role.edit(color=color)
        await ctx.send(f"changed {role.name} color to {hex_color}")
    except:
        await ctx.send("invalid hex color")

@bot.command()
async def changerolename(ctx, role: discord.Role, *, new_name: str):
    if not has_perm(ctx, "manage_roles"):
        await ctx.send("you need manage roles perms")
        return
    old = role.name
    await role.edit(name=new_name)
    await ctx.send(f"renamed {old} to {new_name}")

@bot.command()
async def massrole(ctx, *, role_name: str):
    if not has_perm(ctx, "manage_roles"):
        await ctx.send("you need manage roles perms")
        return
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    count = 0
    for member in ctx.guild.members:
        if role not in member.roles and not member.bot:
            try:
                await member.add_roles(role)
                count += 1
            except:
                pass
    await ctx.send(f"gave {role.name} to {count} members")

@bot.command()
async def massremoverole(ctx, *, role_name: str):
    if not has_perm(ctx, "manage_roles"):
        await ctx.send("you need manage roles perms")
        return
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    count = 0
    for member in ctx.guild.members:
        if role in member.roles:
            try:
                await member.remove_roles(role)
                count += 1
            except:
                pass
    await ctx.send(f"removed {role.name} from {count} members")

@bot.command()
async def inrole(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    members = [m.mention for m in role.members]
    if not members:
        await ctx.send("no members have that role")
        return
    embed = discord.Embed(title=f"members with {role.name}", color=0xff4500)
    for i in range(0, len(members), 25):
        embed.add_field(name=f"page {i//25 + 1}", value=", ".join(members[i:i+25]), inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def notinrole(ctx, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    members = [m.mention for m in ctx.guild.members if role not in m.roles and not m.bot]
    if not members:
        await ctx.send("everyone has that role")
        return
    await ctx.send(f"members without {role.name}: {len(members)} people")

@bot.command()
async def rolecompare(ctx, role1_name: str, role2_name: str):
    role1 = discord.utils.get(ctx.guild.roles, name=role1_name)
    role2 = discord.utils.get(ctx.guild.roles, name=role2_name)
    if not role1 or not role2:
        await ctx.send("one or both roles not found")
        return
    if role1.position > role2.position:
        await ctx.send(f"{role1.name} is higher than {role2.name}")
    elif role2.position > role1.position:
        await ctx.send(f"{role2.name} is higher than {role1.name}")
    else:
        await ctx.send(f"{role1.name} and {role2.name} are at the same position")

@bot.command()
async def rolehierarchy(ctx):
    roles = sorted(ctx.guild.roles, key=lambda r: r.position, reverse=True)
    embed = discord.Embed(title="role hierarchy", color=0xff4500)
    for i, role in enumerate(roles[:25]):
        if role.name != "@everyone":
            embed.add_field(name=f"#{i+1} {role.name}", value=f"position: {role.position}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def createrolemenu(ctx, *, role_names: str):
    if not has_perm(ctx, "manage_roles"):
        await ctx.send("you need manage roles perms")
        return
    roles = role_names.split(",")
    embed = discord.Embed(title="react for roles", color=0xff4500)
    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, role_name in enumerate(roles[:10]):
        role = discord.utils.get(ctx.guild.roles, name=role_name.strip())
        if role:
            embed.add_field(name=f"{reactions[i]} {role.name}", value="react to get this role", inline=False)
    msg = await ctx.send(embed=embed)
    for i in range(len(roles[:10])):
        await msg.add_reaction(reactions[i])

@bot.command()
async def sticky(ctx, *, message: str):
    if not has_perm(ctx, "manage_messages"):
        await ctx.send("you need manage messages perms")
        return
    if not hasattr(bot, "sticky_messages"):
        bot.sticky_messages = {}
    bot.sticky_messages[ctx.channel.id] = message
    await ctx.send("sticky message set")

@bot.event
async def on_message_sticky(message):
    if message.author.bot:
        return
    if hasattr(bot, "sticky_messages") and message.channel.id in bot.sticky_messages:
        await message.channel.send(bot.sticky_messages[message.channel.id])

@bot.command()
async def unsticky(ctx):
    if not has_perm(ctx, "manage_messages"):
        await ctx.send("you need manage messages perms")
        return
    if hasattr(bot, "sticky_messages") and ctx.channel.id in bot.sticky_messages:
        del bot.sticky_messages[ctx.channel.id]
        await ctx.send("sticky message removed")
    else:
        await ctx.send("no sticky message in this channel")

@bot.command()
async def reactrole(ctx, message_id: int, emoji: str, *, role_name: str):
    if not has_perm(ctx, "manage_roles"):
        await ctx.send("you need manage roles perms")
        return
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("role not found")
        return
    try:
        msg = await ctx.channel.fetch_message(message_id)
        await msg.add_reaction(emoji)
        if not hasattr(bot, "react_roles"):
            bot.react_roles = {}
        bot.react_roles[(msg.id, emoji)] = role.id
        await ctx.send(f"set {emoji} to give {role.name}")
    except:
        await ctx.send("message not found")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    if hasattr(bot, "react_roles"):
        role_id = bot.react_roles.get((payload.message_id, str(payload.emoji)))
        if role_id:
            guild = bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = guild.get_role(role_id)
            if member and role:
                await member.add_roles(role)

@bot.event
async def on_raw_reaction_remove(payload):
    if hasattr(bot, "react_roles"):
        role_id = bot.react_roles.get((payload.message_id, str(payload.emoji)))
        if role_id:
            guild = bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = guild.get_role(role_id)
            if member and role:
                await member.remove_roles(role)

@bot.command()
async def ticket(ctx, *, reason: str = "no reason"):
    if not has_perm(ctx, "manage_channels"):
        await ctx.send("you need manage channels perms")
        return
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.author: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        ctx.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    for role in ctx.guild.roles:
        if role.permissions.manage_channels:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
    channel = await ctx.guild.create_text_channel(f"ticket-{ctx.author.name}", overwrites=overwrites)
    await channel.send(f"ticket created by {ctx.author.mention}. reason: {reason}")
    await ctx.send(f"ticket created: {channel.mention}")

@bot.command()
async def closeticket(ctx, channel: discord.TextChannel = None):
    if not has_perm(ctx, "manage_channels"):
        await ctx.send("you need manage channels perms")
        return
    channel = channel or ctx.channel
    if channel.name.startswith("ticket-"):
        await channel.delete()
        await ctx.send("ticket closed")
    else:
        await ctx.send("this isn't a ticket channel")

@bot.command()
async def transcript(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    messages = []
    async for msg in channel.history(limit=100, oldest_first=True):
        messages.append(f"[{msg.created_at.strftime('%H:%M')}] {msg.author.name}: {msg.content}")
    transcript = "\n".join(messages)
    await ctx.send(f"transcript of {channel.name}:
```{transcript[:1900]}```")

@bot.command()
async def lockdown(ctx):
    if not has_perm(ctx, "manage_channels"):
        await ctx.send("you need manage channels perms")
        return
    for channel in ctx.guild.text_channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("server lockdown initiated. all channels locked.")

@bot.command()
async def unlockdown(ctx):
    if not has_perm(ctx, "manage_channels"):
        await ctx.send("you need manage channels perms")
        return
    for channel in ctx.guild.text_channels:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("server unlocked. all channels open.")

@bot.command()
async def raidmode(ctx):
    if not has_perm(ctx, "manage_guild"):
        await ctx.send("you need manage guild perms")
        return
    bot.server_data[str(ctx.guild.id)]["raid_mode"] = True
    save()
    await ctx.send("raid mode enabled. new members will be auto-muted.")

@bot.command()
async def unraidmode(ctx):
    if not has_perm(ctx, "manage_guild"):
        await ctx.send("you need manage guild perms")
        return
    bot.server_data[str(ctx.guild.id)]["raid_mode"] = False
    save()
    await ctx.send("raid mode disabled.")

@bot.event
async def on_member_join_raid(member):
    guild_id = str(member.guild.id)
    if guild_id in bot.server_data and bot.server_data[guild_id].get("raid_mode"):
        muted_role = discord.utils.get(member.guild.roles, name="Muted")
        if muted_role:
            await member.add_roles(muted_role)

@bot.command()
async def antiraid(ctx, threshold: int = 10):
    if not has_perm(ctx, "manage_guild"):
        await ctx.send("you need manage guild perms")
        return
    bot.server_data[str(ctx.guild.id)]["antiraid_threshold"] = threshold
    save()
    await ctx.send(f"antiraid set to {threshold} joins per minute")

@bot.command()
async def whitelist(ctx, member: discord.Member):
    if not has_perm(ctx, "manage_guild"):
        await ctx.send("you need manage guild perms")
        return
    if "whitelist" not in bot.server_data[str(ctx.guild.id)]:
        bot.server_data[str(ctx.guild.id)]["whitelist"] = []
    bot.server_data[str(ctx.guild.id)]["whitelist"].append(member.id)
    save()
    await ctx.send(f"whitelisted {member.mention}")

@bot.command()
async def unwhitelist(ctx, member: discord.Member):
    if not has_perm(ctx, "manage_guild"):
        await ctx.send("you need manage guild perms")
        return
    if "whitelist" in bot.server_data[str(ctx.guild.id)]:
        if member.id in bot.server_data[str(ctx.guild.id)]["whitelist"]:
            bot.server_data[str(ctx.guild.id)]["whitelist"].remove(member.id)
            save()
    await ctx.send(f"unwhitelisted {member.mention}")

# ========== HELP COMMAND (PAGINATED) ==========

PAGE1_COMMANDS = [
    "economy:", "embers, daily, streak, beg, scam, invest, heist, loan, repay, burn, send",
    "creatures:", "summon, cage, release, feed, neglect, mood, evolve, breed, sacrifice, rename",
    "combat:", "duel, raid, ambush, defend, berserk, bribe, flee, taunt, combo, revive, wager, rank",
    "gambling:", "dice, shells, flip, spin, surge, vault, pick, chase, chamber, rig",
    "social:", "marry, divorce, will, cult, betray, tribute, roast, confess",
    "utility:", "tutorial, stats, server, global_rank, settings, cooldowns, changelog",
    "weird:", "dream, curse, bless, time, weather, oracle, mimic, glitch, lore, quit"
]

PAGE2_COMMANDS = [
    "moderation:", "kick, ban, unban, purge, warn, warns, clearwarns, nick, role, createrole, deleterole",
    "", "slowmode, lock, unlock, hide, unhide, mute, unmute, createchannel, deletechannel, webhook",
    "", "announce, say, embedsay, setprefix, autorole, welcome, goodbye, welcomechannel",
    "fun:", "ping, coinflip, roll, choose, rate, gayrate, simprate, iq, pp, height, weight, age",
    "", "ship, hack, meme, joke, fact, quote, rps, eightball, reverse, uppercase, lowercase",
    "", "len, countwords, avatar, userinfo, botinfo, invite, uptime, reminder, timer, poll, calc",
    "", "randomnum, password, binary, morse, base64, decode64, hexcode, decodehex, md5, sha256"
]

PAGE3_COMMANDS = [
    "advanced economy:", "bankrob, lottery, slots, blackjack, roulette, horse, doubleornothing, highlow",
    "", "mine, fish, chop, farm, hunt, forage, craft, explore, dungeon, boss, quest, work, pay",
    "", "deposit, withdraw, balance, leaderboard, shop, buy, inventory, use, sell",
    "creature management:", "pet, play, train, heal, releaseall, sacrificeall, creatureinfo, strongest, weakest",
    "", "happiest, saddest, creaturecount, totalpower, totalmood, sortpower, sortmood, sorttype",
    "", "dupecheck, releaseweak, releasesad, massfeed, masstrain, massevolve, creatureleaderboard",
    "", "tradeall, clone, merge, releasefav, favoritelist, unfavoriteall, creaturesearch",
    "server info:", "guilds, channels, roleslist, emojislist, stickerslist, banslist, invites, permissions",
    "", "channelinfo, roleinfo, voiceinfo, move, deafen, undeafen, mutevoice, unmutevoice, disconnect",
    "", "deafenall, muteall, undeafenall, unmuteall, moveall, disconnectall, voicekick",
    "admin:", "give, set, remove, wipe, backup, restore, evalcmd, execmd, shutdown, restart, status",
    "", "playing, watching, listening, streaming, setavatar, setname, serverlist, leavserver, nickall",
    "", "unbanall, copyserver, sync, clearsync, guildsync, massdm, announceall"
]

@bot.command()
async def help(ctx, page: int = 1):
    if page == 1:
        embed = discord.Embed(title="flame bot commands - page 1/3", description="core commands from the screenshot + basic fun", color=0xff4500)
        for line in PAGE1_COMMANDS:
            if line.endswith(":"):
                embed.add_field(name=line, value="", inline=False)
            elif line:
                embed.add_field(name="", value=line, inline=False)
        embed.set_footer(text="use f help 2 for page 2, f help 3 for page 3")
    elif page == 2:
        embed = discord.Embed(title="flame bot commands - page 2/3", description="moderation + fun commands", color=0xff4500)
        for line in PAGE2_COMMANDS:
            if line.endswith(":"):
                embed.add_field(name=line, value="", inline=False)
            elif line:
                embed.add_field(name="", value=line, inline=False)
        embed.set_footer(text="use f help 1 for page 1, f help 3 for page 3")
    elif page == 3:
        embed = discord.Embed(title="flame bot commands - page 3/3", description="advanced + admin commands", color=0xff4500)
        for line in PAGE3_COMMANDS:
            if line.endswith(":"):
                embed.add_field(name=line, value="", inline=False)
            elif line:
                embed.add_field(name="", value=line, inline=False)
        embed.set_footer(text="use f help 1 for page 1, f help 2 for page 2")
    else:
        await ctx.send("only pages 1, 2, and 3 exist. pick one of those.")
        return
    await ctx.send(embed=embed)

# ========== RUN THE BOT ==========

token = os.environ.get("DISCORD_TOKEN")
if not token:
    print("error: no discord_token environment variable found")
    print("make sure to set discord_token in your railway environment variables")
else:
    bot.run(token)
