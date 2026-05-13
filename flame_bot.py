
import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta

TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = 'f'
OWNER_ID = 1444293963812180120

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

DATA_FILE = 'embers_data.json'
CREATURE_FILE = 'creatures_data.json'
MARRIAGE_FILE = 'marriage_data.json'
COOLDOWN_FILE = 'cooldowns.json'
SETTINGS_FILE = 'settings.json'
AUCTION_FILE = 'auctions.json'
HEIST_FILE = 'heists.json'

def load_data(filepath, default=None):
    if default is None:
        default = {}
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return default

def save_data(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

embers_data = load_data(DATA_FILE)
creatures_data = load_data(CREATURE_FILE)
marriage_data = load_data(MARRIAGE_FILE)
cooldowns_data = load_data(COOLDOWN_FILE)
settings_data = load_data(SETTINGS_FILE)
auctions_data = load_data(AUCTION_FILE)
heists_data = load_data(HEIST_FILE)

def get_user_data(user_id):
    user_id = str(user_id)
    if user_id not in embers_data:
        embers_data[user_id] = {
            'embers': 0, 'daily_last': None, 'inventory': [], 'rob_last': None,
            'work_last': None, 'streak': 0, 'loan': 0, 'loan_due': None,
            'burned': 0, 'scammed': 0, 'invested': 0, 'xp': 0, 'level': 1,
            'wins': 0, 'losses': 0, 'duels': 0, 'raids': 0, 'married_to': None,
            'cult': None, 'will': None, 'tribute_last': None, 'creatures': [],
            'favorite_creature': None, 'combat_rank': 'Bronze', 'blessed': False,
            'cursed': False, 'dream_last': None, 'tutorial_seen': False,
            'settings': {'notifications': True, 'dm_offers': True}, 'heist_joined': False
        }
        save_data(DATA_FILE, embers_data)
    return embers_data[user_id]

def update_user(user_id, key, value):
    user_id = str(user_id)
    embers_data[user_id][key] = value
    save_data(DATA_FILE, embers_data)

def check_cd(user_id, cmd, seconds):
    key = f"{user_id}_{cmd}"
    now = datetime.now().timestamp()
    if key in cooldowns_data:
        elapsed = now - cooldowns_data[key]
        if elapsed < seconds:
            return False, int(seconds - elapsed)
    cooldowns_data[key] = now
    save_data(COOLDOWN_FILE, cooldowns_data)
    return True, 0

def is_owner():
    async def predicate(ctx):
        if ctx.author.id != OWNER_ID:
            embed = discord.Embed(
                title="Nah fam",
                description="You can't use this command as ur not the bot owner.",
                color=discord.Color.red()
            )
            embed.set_footer(text="only justaflamewithfragz can do this stuff lol")
            await ctx.send(embed=embed)
            return False
        return True
    return commands.check(predicate)

# ============ EVENTS ============
@bot.event
async def on_ready():
    print(f"{bot.user.name} is online and blazing!")
    print(f"Bot ID: {bot.user.id}")
    print("Ready to burn some embers!")
    await bot.change_presence(activity=discord.Game(name="fhelp | burning embers"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("yo youre missing some arguments, check fhelp for how to use it")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("bruh that argument dont make sense. check fhelp for the right way to use it")
    else:
        print(f"Error: {error}")


# ============ HELP SYSTEM ============
@bot.command(name="help", aliases=["h"])
async def help_cmd(ctx, category=None):
    if not category:
        embed = discord.Embed(
            title="Flame Bot Commands",
            description="yo heres everything i can do. use `fhelp <category>` for details on each section",
            color=discord.Color.orange()
        )
        embed.add_field(name="Economy", value="`embers` `daily` `streak` `beg` `scam` `invest` `heist` `loan` `repay` `burn` `send` `work` `rob` `shop` `buy` `inventory` `leaderboard` `balance` `gamble` `slots`", inline=False)
        embed.add_field(name="Creatures", value="`summon` `cage` `release` `feed` `neglect` `mood` `evolve` `breed` `sacrifice` `rename` `favorite` `trade` `auction` `bid` `inspect` `adopt` `kidnap`", inline=False)
        embed.add_field(name="Combat", value="`duel` `raid` `ambush` `defend` `berserk` `bribe` `flee` `taunt` `combo` `revive` `wager` `rank`", inline=False)
        embed.add_field(name="Gambling", value="`dice` `shells` `flip` `spin` `surge` `vault` `pick` `chase` `chamber` `rig` `coinflip` `roll` `8ball` `rate`", inline=False)
        embed.add_field(name="Social", value="`marry` `divorce` `will` `cult` `betray` `tribute` `roast` `confess` `meme` `joke` `avatar` `userinfo` `profile`", inline=False)
        embed.add_field(name="Utility", value="`tutorial` `stats` `server` `global` `settings` `cooldowns` `changelog` `serverinfo` `ping` `uptime` `help`", inline=False)
        embed.add_field(name="Weird", value="`dream` `curse` `bless` `time` `weather` `oracle` `mimic` `glitch` `lore` `quit` `rps`", inline=False)
        embed.add_field(name="Admin (Owner Only)", value="`give` `set` `remove` `wipe`", inline=False)
        embed.set_footer(text="prefix is f or flame | made by justaflamewithfragz")
        await ctx.send(embed=embed)
        return

    cat = category.lower()
    if cat in ["economy", "econ", "money"]:
        embed = discord.Embed(title="Economy Commands", description="get rich or die tryin", color=discord.Color.green())
        embed.add_field(name="fembers", value="check how many embers you got. aliases: fbalance, fbal, fmoney", inline=False)
        embed.add_field(name="fdaily", value="collect your daily embers. 24h cooldown. streak increases reward!", inline=False)
        embed.add_field(name="fstreak", value="check your daily login streak. dont break it!", inline=False)
        embed.add_field(name="fbeg", value="beg for embers like a bum. 5min cooldown. sometimes people feel bad for you", inline=False)
        embed.add_field(name="fscam <@user> <amount>", value="try to scam someone out of their embers. risky but profitable", inline=False)
        embed.add_field(name="finvest <amount>", value="invest embers and hope the market goes up. check back later", inline=False)
        embed.add_field(name="fheist", value="start a server heist. everyone can join to steal from the bank", inline=False)
        embed.add_field(name="floan <amount>", value="take out a loan. gotta repay it tho or bad things happen", inline=False)
        embed.add_field(name="frepay <amount>", value="pay back your loan. do it before its too late fam", inline=False)
        embed.add_field(name="fburn <amount>", value="burn embers just because you can. literally set money on fire", inline=False)
        embed.add_field(name="fsend <amount> <@user>", value="send embers to someone. has confirmation so you dont mess up", inline=False)
        embed.add_field(name="fwork", value="work a job for embers. 1h cooldown. various jobs available", inline=False)
        embed.add_field(name="frob <@user>", value="rob another user. 30min cooldown. 40% success rate", inline=False)
        embed.add_field(name="fshop", value="view items you can buy with embers", inline=False)
        embed.add_field(name="fbuy <item>", value="buy something from the shop", inline=False)
        embed.add_field(name="finventory / finv", value="check your items and badges", inline=False)
        embed.add_field(name="fleaderboard / flb", value="see whos the richest in the server", inline=False)
        embed.add_field(name="fgamble <amount>", value="gamble your embers. 45% win chance, double your money", inline=False)
        embed.add_field(name="fslots <amount>", value="play the slot machine. match symbols to win big", inline=False)
    elif cat in ["creatures", "creature", "pets"]:
        embed = discord.Embed(title="Creatures Commands", description="summon, train, and battle creatures", color=discord.Color.purple())
        embed.add_field(name="fsummon", value="summon a random creature to be your companion", inline=False)
        embed.add_field(name="fcage", value="check your captured creatures", inline=False)
        embed.add_field(name="frelease <creature>", value="release a creature back into the wild", inline=False)
        embed.add_field(name="ffeed <creature>", value="feed your creature to keep it happy and strong", inline=False)
        embed.add_field(name="fneglect <creature>", value="neglect your creature. it might run away or get mad", inline=False)
        embed.add_field(name="fmood <creature>", value="check how your creature is feeling", inline=False)
        embed.add_field(name="fevolve <creature>", value="evolve your creature to the next stage", inline=False)
        embed.add_field(name="fbreed <creature1> <creature2>", value="breed two creatures together", inline=False)
        embed.add_field(name="fsacrifice <creature>", value="sacrifice a creature for embers. dark but profitable", inline=False)
        embed.add_field(name="frename <creature> <name>", value="give your creature a custom name", inline=False)
        embed.add_field(name="ffavorite <creature>", value="set your favorite creature", inline=False)
        embed.add_field(name="ftrade <@user> <creature>", value="trade a creature with another user", inline=False)
        embed.add_field(name="fauction <creature> <price>", value="put your creature up for auction", inline=False)
        embed.add_field(name="fbid <auction_id> <amount>", value="bid on a creature in the auction house", inline=False)
        embed.add_field(name="finspect <creature>", value="get detailed info about a creature", inline=False)
        embed.add_field(name="fadopt <creature>", value="adopt a creature from the shelter", inline=False)
        embed.add_field(name="fkidnap <@user> <creature>", value="try to kidnap someone elses creature. very illegal lol", inline=False)
    elif cat in ["combat", "fight", "battle"]:
        embed = discord.Embed(title="Combat Commands", description="fight for glory and embers", color=discord.Color.red())
        embed.add_field(name="fduel <@user>", value="challenge someone to a duel. winner takes embers", inline=False)
        embed.add_field(name="fraid", value="start a raid on a dungeon. team up with others", inline=False)
        embed.add_field(name="fambush <@user>", value="ambush a user when they least expect it", inline=False)
        embed.add_field(name="fdefend", value="go into defensive mode. reduces damage taken", inline=False)
        embed.add_field(name="fberserk", value="enter berserk mode. high damage but risky", inline=False)
        embed.add_field(name="fbribe <amount>", value="bribe your way out of a fight", inline=False)
        embed.add_field(name="fflee", value="run away from combat like a coward", inline=False)
        embed.add_field(name="ftaunt <@user>", value="taunt someone into fighting you", inline=False)
        embed.add_field(name="fcombo <@user>", value="unleash a combo attack", inline=False)
        embed.add_field(name="frevive", value="revive yourself after losing. costs embers", inline=False)
        embed.add_field(name="fwager <amount> <@user>", value="wager embers on a fight outcome", inline=False)
        embed.add_field(name="frank", value="check your combat rank and stats", inline=False)
    elif cat in ["gambling", "gamble", "bet"]:
        embed = discord.Embed(title="Gambling Commands", description="risk it for the biscuit", color=discord.Color.gold())
        embed.add_field(name="fdice <sides>", value="roll a dice with custom sides. default is 6", inline=False)
        embed.add_field(name="fshells", value="play the shell game. find the ball under the cup", inline=False)
        embed.add_field(name="fflip", value="flip a coin. heads or tails", inline=False)
        embed.add_field(name="fspin", value="spin the wheel of fortune", inline=False)
        embed.add_field(name="fsurge <amount>", value="surge bet. all or nothing multiplier", inline=False)
        embed.add_field(name="fvault", value="crack the vault. mini game for embers", inline=False)
        embed.add_field(name="fpick", value="pick a card. high card wins", inline=False)
        embed.add_field(name="fchase", value="chase game. run from the cops for embers", inline=False)
        embed.add_field(name="fchamber", value="play russian roulette. 1 in 6 chance to lose big", inline=False)
        embed.add_field(name="frig", value="rig the odds in your favor. risky cheat", inline=False)
        embed.add_field(name="fcoinflip / fcf", value="simple coin flip", inline=False)
        embed.add_field(name="froll <number>", value="roll a number", inline=False)
        embed.add_field(name="f8ball <question>", value="ask the magic 8ball", inline=False)
        embed.add_field(name="frate <thing>", value="rate something 1-10", inline=False)
    elif cat in ["social", "chat", "fun"]:
        embed = discord.Embed(title="Social Commands", description="interact with the homies", color=discord.Color.pink())
        embed.add_field(name="fmarry <@user>", value="propose to someone. if they say yes youre married", inline=False)
        embed.add_field(name="fdivorce", value="divorce your current partner. rip the love", inline=False)
        embed.add_field(name="fwill <@user>", value="set who gets your embers when you quit", inline=False)
        embed.add_field(name="fcult <name>", value="start or join a cult. cult leader gets tribute embers", inline=False)
        embed.add_field(name="fbetray <@user>", value="betray a cult member. drama incoming", inline=False)
        embed.add_field(name="ftribute <amount>", value="pay tribute to your cult leader", inline=False)
        embed.add_field(name="froast <@user>", value="roast someone with a random insult", inline=False)
        embed.add_field(name="fconfess <@user> <message>", value="confess your feelings anonymously", inline=False)
        embed.add_field(name="fmeme", value="get a random meme", inline=False)
        embed.add_field(name="fjoke", value="get a random joke", inline=False)
        embed.add_field(name="favatar <@user>", value="get someones profile picture", inline=False)
        embed.add_field(name="fuserinfo <@user>", value="get info about a user", inline=False)
        embed.add_field(name="fprofile / fp", value="view your profile card", inline=False)
    elif cat in ["utility", "util", "tools"]:
        embed = discord.Embed(title="Utility Commands", description="useful stuff", color=discord.Color.blue())
        embed.add_field(name="ftutorial", value="get a tutorial on how to use the bot", inline=False)
        embed.add_field(name="fstats", value="view your detailed stats", inline=False)
        embed.add_field(name="fserver", value="get server info", inline=False)
        embed.add_field(name="fglobal", value="view global leaderboard across all servers", inline=False)
        embed.add_field(name="fsettings", value="change your personal settings", inline=False)
        embed.add_field(name="fcooldowns", value="check all your active cooldowns", inline=False)
        embed.add_field(name="fchangelog", value="see whats new in the bot", inline=False)
        embed.add_field(name="fserverinfo", value="detailed server statistics", inline=False)
        embed.add_field(name="fping", value="check bot latency", inline=False)
        embed.add_field(name="fuptime", value="how long the bot has been running", inline=False)
        embed.add_field(name="fhelp / fh", value="shows this help menu", inline=False)
    elif cat in ["weird", "random", "misc"]:
        embed = discord.Embed(title="Weird Commands", description="strange but fun", color=discord.Color.dark_purple())
        embed.add_field(name="fdream", value="get a random dream interpretation", inline=False)
        embed.add_field(name="fcurse <@user>", value="curse someone with bad luck", inline=False)
        embed.add_field(name="fbless <@user>", value="bless someone with good luck", inline=False)
        embed.add_field(name="ftime", value="check the current time", inline=False)
        embed.add_field(name="fweather <location>", value="get weather info", inline=False)
        embed.add_field(name="foracle", value="ask the oracle for wisdom", inline=False)
        embed.add_field(name="fmimic <@user>", value="mimic someones last message", inline=False)
        embed.add_field(name="fglitch", value="experience a glitch in the matrix", inline=False)
        embed.add_field(name="flore", value="get a piece of bot lore", inline=False)
        embed.add_field(name="fquit", value="quit the bot. gives your embers to your will beneficiary", inline=False)
        embed.add_field(name="frps <rock/paper/scissors>", value="play rock paper scissors", inline=False)
    else:
        await ctx.send("bruh thats not a category. use fhelp to see the list of categories")
        return
    embed.set_footer(text="prefix is f or flame | made by justaflamewithfragz")
    await ctx.send(embed=embed)


# ============ ECONOMY COMMANDS ============
@bot.command(name="embers", aliases=["balance", "bal", "money"])
async def embers_cmd(ctx, user: discord.Member = None):
    user = user or ctx.author
    data = get_user_data(user.id)
    embed = discord.Embed(title=f"{user.display_name}'s Embers", color=discord.Color.orange())
    embed.add_field(name="Balance", value=f"**{data['embers']:,}** embers", inline=False)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text="get rich or die tryin lol")
    await ctx.send(embed=embed)

@bot.command(name="daily")
async def daily(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "daily", 86400)
    if not can_use:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        await ctx.send(f"chill fam, you already got your daily. come back in {hours}h {minutes}m")
        return
    streak = data.get("streak", 0)
    last_daily = data.get("daily_last")
    if last_daily:
        try:
            last = datetime.fromisoformat(last_daily)
            if (datetime.now() - last).total_seconds() < 172800:
                streak += 1
            else:
                streak = 1
        except:
            streak = 1
    else:
        streak = 1
    base = random.randint(100, 500)
    bonus = min(streak * 50, 1000)
    amount = base + bonus
    data["embers"] += amount
    data["streak"] = streak
    data["daily_last"] = datetime.now().isoformat()
    update_user(user_id, "embers", data["embers"])
    update_user(user_id, "streak", streak)
    update_user(user_id, "daily_last", data["daily_last"])
    if streak > 1:
        await ctx.send(f"yo you got **{amount}** embers! streak: **{streak}** days! keep it up fam")
    else:
        await ctx.send(f"yo you got **{amount}** embers! streak reset. dont miss tomorrow lol")

@bot.command(name="streak")
async def streak_cmd(ctx):
    data = get_user_data(ctx.author.id)
    streak = data.get("streak", 0)
    await ctx.send(f"your daily streak is **{streak}** days. miss one day and it resets fam")

@bot.command(name="beg")
async def beg(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "beg", 300)
    if not can_use:
        await ctx.send(f"bruh you just begged, have some dignity. wait {remaining}s")
        return
    if random.random() < 0.6:
        amount = random.randint(1, 50)
        data["embers"] += amount
        update_user(user_id, "embers", data["embers"])
        responses = [
            f"someone felt bad and gave you **{amount}** embers. shameless but effective",
            f"you begged and got **{amount}** embers. no dignity but hey, money is money",
            f"a stranger tossed you **{amount}** embers. get a job lol",
            f"**{amount}** embers from begging. your parents would be so proud"
        ]
    else:
        responses = [
            "nobody gave you anything. maybe try not looking so desperate",
            "you got ignored. tough crowd today lol",
            "a dog barked at you instead. even animals know youre broke",
            "someone told you to get a job. harsh but fair"
        ]
    await ctx.send(random.choice(responses))

@bot.command(name="scam")
async def scam(ctx, victim: discord.Member, amount: int):
    if victim.id == ctx.author.id:
        await ctx.send("bro you cant scam yourself. thats just giving away money lol")
        return
    if amount <= 0:
        await ctx.send("nah fam cant scam for negative embers. what are you tryna pull?")
        return
    user_id = ctx.author.id
    victim_data = get_user_data(victim.id)
    if victim_data["embers"] < amount:
        await ctx.send(f"{victim.display_name} is broke af, they dont even have **{amount}** embers lol")
        return
    can_use, remaining = check_cd(user_id, "scam", 600)
    if not can_use:
        await ctx.send(f"chill scammer, you just tried to scam someone. wait {remaining}s")
        return
    if random.random() < 0.35:
        victim_data["embers"] -= amount
        data = get_user_data(user_id)
        data["embers"] += amount
        data["scammed"] = data.get("scammed", 0) + amount
        update_user(victim.id, "embers", victim_data["embers"])
        update_user(user_id, "embers", data["embers"])
        update_user(user_id, "scammed", data["scammed"])
        await ctx.send(f"yo you scammed **{amount}** embers from {victim.display_name}! youre a terrible person lol")
    else:
        fine = random.randint(50, 200)
        data = get_user_data(user_id)
        data["embers"] = max(0, data["embers"] - fine)
        update_user(user_id, "embers", data["embers"])
        await ctx.send(f"busted! {victim.display_name} caught your scam and you got fined **{fine}** embers. stick to honest work lol")

@bot.command(name="invest")
async def invest(ctx, amount: int):
    if amount <= 0:
        await ctx.send("bruh you cant invest nothing. put some embers on the line")
        return
    user_id = ctx.author.id
    data = get_user_data(user_id)
    if data["embers"] < amount:
        await ctx.send(f"you broke fam, you only got **{data['embers']}** embers. cant invest **{amount}**")
        return
    data["embers"] -= amount
    data["invested"] = data.get("invested", 0) + amount
    update_user(user_id, "embers", data["embers"])
    update_user(user_id, "invested", data["invested"])
    await ctx.send(f"you invested **{amount}** embers. the market is volatile, check back later to see if you made bank or lost it all lol")

@bot.command(name="heist")
async def heist(ctx):
    user_id = ctx.author.id
    can_use, remaining = check_cd(user_id, "heist", 3600)
    if not can_use:
        await ctx.send(f"the cops are still investigating the last heist. wait {remaining // 60}m")
        return
    guild_id = str(ctx.guild.id)
    if guild_id in heists_data and heists_data[guild_id].get("active"):
        await ctx.send("theres already a heist going on fam. join that one or wait")
        return
    heists_data[guild_id] = {"active": True, "participants": [ctx.author.id], "started": datetime.now().timestamp()}
    save_data(HEIST_FILE, heists_data)
    await ctx.send("**HEIST STARTED!** type `fheist` in the next 30 seconds to join the crew!")
    await asyncio.sleep(30)
    heist_data = heists_data.get(guild_id, {})
    participants_ids = heist_data.get("participants", [ctx.author.id])
    participants = []
    for pid in participants_ids:
        member = ctx.guild.get_member(pid)
        if member:
            participants.append(member)
    if len(participants) < 2:
        heists_data[guild_id]["active"] = False
        save_data(HEIST_FILE, heists_data)
        await ctx.send("heist cancelled. you need at least 2 people to rob a bank fam")
        return
    success = random.random() < 0.5
    if success:
        total = random.randint(500, 2000) * len(participants)
        share = total // len(participants)
        for p in participants:
            pdata = get_user_data(p.id)
            pdata["embers"] += share
            update_user(p.id, "embers", pdata["embers"])
        heists_data[guild_id]["active"] = False
        save_data(HEIST_FILE, heists_data)
        await ctx.send(f"**HEIST SUCCESSFUL!** the crew of {len(participants)} stole **{total}** embers! each person got **{share}** embers!")
    else:
        for p in participants:
            pdata = get_user_data(p.id)
            fine = random.randint(50, 150)
            pdata["embers"] = max(0, pdata["embers"] - fine)
            update_user(p.id, "embers", pdata["embers"])
        heists_data[guild_id]["active"] = False
        save_data(HEIST_FILE, heists_data)
        await ctx.send("**HEIST FAILED!** the alarm went off and everyone got arrested. fines paid for everyone lol")

@bot.command(name="loan")
async def loan(ctx, amount: int):
    if amount <= 0:
        await ctx.send("bruh you cant loan nothing. how does that work?")
        return
    user_id = ctx.author.id
    data = get_user_data(user_id)
    if data.get("loan", 0) > 0:
        await ctx.send(f"you already owe **{data['loan']}** embers. pay that back first fam")
        return
    data["loan"] = amount
    data["embers"] += amount
    data["loan_due"] = (datetime.now() + timedelta(hours=24)).isoformat()
    update_user(user_id, "loan", amount)
    update_user(user_id, "embers", data["embers"])
    update_user(user_id, "loan_due", data["loan_due"])
    await ctx.send(f"you took out a **{amount}** ember loan. you got 24 hours to repay it with `frepay` or bad things happen lol")

@bot.command(name="repay")
async def repay(ctx, amount: int = None):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    owed = data.get("loan", 0)
    if owed <= 0:
        await ctx.send("you dont owe anything fam. living debt free, nice")
        return
    if amount is None:
        amount = owed
    if amount <= 0:
        await ctx.send("bruh you cant repay negative embers. think about it lol")
        return
    if data["embers"] < amount:
        await ctx.send(f"you broke, only got **{data['embers']}** embers. need **{amount}** to repay")
        return
    payback = min(amount, owed)
    data["embers"] -= payback
    data["loan"] -= payback
    if data["loan"] <= 0:
        data["loan"] = 0
        data["loan_due"] = None
    update_user(user_id, "embers", data["embers"])
    update_user(user_id, "loan", data["loan"])
    update_user(user_id, "loan_due", data["loan_due"])
    await ctx.send(f"you repaid **{payback}** embers. loan balance: **{data['loan']}**")

@bot.command(name="burn")
async def burn(ctx, amount: int):
    if amount <= 0:
        await ctx.send("nah fam you cant burn negative embers. that would be creating money lol")
        return
    user_id = ctx.author.id
    data = get_user_data(user_id)
    if data["embers"] < amount:
        await ctx.send(f"you only got **{data['embers']}** embers. cant burn **{amount}** fam")
        return
    data["embers"] -= amount
    data["burned"] = data.get("burned", 0) + amount
    update_user(user_id, "embers", data["embers"])
    update_user(user_id, "burned", data["burned"])
    responses = [
        f"you burned **{amount}** embers. why? just why?",
        f"**{amount}** embers up in flames. you really hate money huh",
        f"burned **{amount}** embers. at least it kept you warm lol",
        f"**{amount}** embers turned to ash. rich people problems i guess"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="send")
async def send(ctx, amount: int, recipient: discord.Member):
    if recipient.id == ctx.author.id:
        await ctx.send("bro why you sending money to yourself? thats just moving it around lol")
        return
    if amount <= 0:
        await ctx.send("nah fam you cant send negative or zero embers. what are you tryna pull?")
        return
    sender_data = get_user_data(ctx.author.id)
    if sender_data["embers"] < amount:
        await ctx.send(f"you broke fam, you only got **{sender_data['embers']}** embers. cant send **{amount}**")
        return
    embed = discord.Embed(title="Are You Sure?", description=f"You about to send **{amount:,}** embers to {recipient.display_name}?", color=discord.Color.yellow())
    embed.set_footer(text="React with checkmark to confirm or X to cancel")
    confirm_msg = await ctx.send(embed=embed)
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "✅":
            sender_data = get_user_data(ctx.author.id)
            recipient_data = get_user_data(recipient.id)
            if sender_data["embers"] < amount:
                await ctx.send("ayo you spent that money already? cant send it now lol")
                return
            sender_data["embers"] -= amount
            recipient_data["embers"] += amount
            update_user(ctx.author.id, "embers", sender_data["embers"])
            update_user(recipient.id, "embers", recipient_data["embers"])
            await ctx.send(f"sent **{amount:,}** embers to {recipient.display_name}! youre a real one")
        else:
            await ctx.send("transaction cancelled. keep your bag fam lol")
    except:
        await ctx.send("you took too long, transaction cancelled. indecisive much?")

@bot.command(name="work")
async def work(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "work", 3600)
    if not can_use:
        minutes = remaining // 60
        await ctx.send(f"bro you just worked, take a break. come back in {minutes}m")
        return
    jobs = [
        ("flipped burgers", 50, 150),
        ("delivered pizza", 75, 200),
        ("walked some dogs", 60, 180),
        ("did some coding", 100, 300),
        ("streamed on twitch", 80, 250),
        ("sold some merch", 90, 220),
        ("did a photoshoot", 70, 190)
    ]
    job, min_pay, max_pay = random.choice(jobs)
    amount = random.randint(min_pay, max_pay)
    data["embers"] += amount
    data["work_last"] = datetime.now().isoformat()
    update_user(user_id, "embers", data["embers"])
    update_user(user_id, "work_last", data["work_last"])
    responses = [
        f"you {job} and earned **{amount}** embers. grind dont stop",
        f"after {job}, you got paid **{amount}** embers. respect the hustle",
        f"**{amount}** embers for {job}? not bad fam",
        f"you {job} like a boss and made **{amount}** embers"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="rob")
async def rob(ctx, victim: discord.Member):
    if victim.id == ctx.author.id:
        await ctx.send("bro you cant rob yourself, thats just sad lol")
        return
    if victim.id == bot.user.id:
        await ctx.send("nah fam you aint robbing me, i got security lol")
        return
    user_id = ctx.author.id
    robber_data = get_user_data(user_id)
    victim_data = get_user_data(victim.id)
    can_use, remaining = check_cd(user_id, "rob", 1800)
    if not can_use:
        minutes = remaining // 60
        await ctx.send(f"chill out criminal, you robbed someone recently. wait {minutes}m")
        return
    if victim_data["embers"] < 100:
        await ctx.send(f"bro {victim.display_name} is broke af, they got nothing to steal lol")
        return
    if robber_data["embers"] < 100:
        await ctx.send("you need at least 100 embers to rob someone (for bail money if you get caught lol)")
        return
    success = random.random() < 0.4
    if success:
        stolen = random.randint(50, min(500, victim_data["embers"] // 2))
        robber_data["embers"] += stolen
        victim_data["embers"] -= stolen
        update_user(user_id, "embers", robber_data["embers"])
        update_user(victim.id, "embers", victim_data["embers"])
        responses = [
            f"yo you robbed {victim.display_name} and got **{stolen}** embers! youre a criminal mastermind lol",
            f"successfully stole **{stolen}** embers from {victim.display_name}. dont tell nobody",
            f"**{stolen}** embers jacked from {victim.display_name}. smooth criminal over here",
            f"you got **{stolen}** embers from {victim.display_name}. crime pays apparently lol"
        ]
    else:
        fine = random.randint(50, 150)
        robber_data["embers"] -= fine
        update_user(user_id, "embers", robber_data["embers"])
        responses = [
            f"busted! you got caught and paid **{fine}** embers in fines. crime dont pay fam",
            f"{victim.display_name} caught you lacking and you lost **{fine}** embers. stick to honest work lol",
            f"robbery failed and you got fined **{fine}** embers. shouldve stayed in school",
            f"you tripped the alarm and lost **{fine}** embers. worst heist ever lol"
        ]
    await ctx.send(random.choice(responses))

@bot.command(name="shop")
async def shop(ctx):
    embed = discord.Embed(title="Embers Shop", description="spend your hard earned embers here", color=discord.Color.orange())
    items = [
        ("Flame Badge", 1000, "show everyone youre a real one"),
        ("Diamond Role", 5000, "flex on everyone with this"),
        ("Crown", 10000, "king/queen of the server"),
        ("Lottery Ticket", 500, "try your luck"),
        ("Shield", 2000, "protect yourself from robberies")
    ]
    for name, price, desc in items:
        embed.add_field(name=f"{name} - {price:,} embers", value=desc, inline=False)
    embed.set_footer(text="use fbuy <item> to purchase")
    await ctx.send(embed=embed)

@bot.command(name="buy")
async def buy(ctx, *, item_name: str):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    items = {
        "flame badge": ("Flame Badge", 1000),
        "diamond role": ("Diamond Role", 5000),
        "crown": ("Crown", 10000),
        "lottery ticket": ("Lottery Ticket", 500),
        "shield": ("Shield", 2000)
    }
    item_key = item_name.lower()
    if item_key not in items:
        await ctx.send("bruh we dont sell that here. check fshop for what we got")
        return
    item_display, price = items[item_key]
    if data["embers"] < price:
        await ctx.send(f"you broke fam, need **{price:,}** embers for that. you got **{data['embers']:,}**")
        return
    data["embers"] -= price
    data["inventory"].append(item_display)
    update_user(user_id, "embers", data["embers"])
    update_user(user_id, "inventory", data["inventory"])
    await ctx.send(f"yo you bought **{item_display}** for **{price:,}** embers! nice cop fam")

@bot.command(name="inventory", aliases=["inv"])
async def inventory(ctx, user: discord.Member = None):
    user = user or ctx.author
    data = get_user_data(user.id)
    items = data["inventory"]
    if not items:
        await ctx.send(f"{user.display_name} got nothing in their bag. broke boy hours lol")
        return
    embed = discord.Embed(title=f"{user.display_name}'s Inventory", color=discord.Color.orange())
    for item in items:
        embed.add_field(name=item, value="owned", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb", "rich", "top"])
async def leaderboard(ctx):
    sorted_users = sorted(embers_data.items(), key=lambda x: x[1]["embers"], reverse=True)[:10]
    embed = discord.Embed(title="Richest People", description="the ones who really got it", color=discord.Color.gold())
    for i, (user_id, data) in enumerate(sorted_users, 1):
        user = bot.get_user(int(user_id))
        name = user.display_name if user else f"User {user_id}"
        medal = ["1st", "2nd", "3rd"][i-1] if i <= 3 else f"#{i}"
        embed.add_field(name=f"{medal} {name}", value=f"**{data['embers']:,}** embers", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="gamble")
async def gamble(ctx, amount: int):
    if amount <= 0:
        await ctx.send("bruh you cant gamble nothing. put some embers on the line")
        return
    user_id = ctx.author.id
    data = get_user_data(user_id)
    if data["embers"] < amount:
        await ctx.send(f"you only got **{data['embers']}** embers, cant gamble **{amount}**. check your balance lol")
        return
    if random.random() < 0.45:
        winnings = amount * 2
        data["embers"] += amount
        update_user(user_id, "embers", data["embers"])
        responses = [
            f"YO YOU WON! got **{winnings}** embers! youre on fire fam",
            f"**{winnings}** embers! the house lost this time lol",
            f"big W! **{winnings}** embers added. dont get addicted now",
            f"you doubled up to **{winnings}** embers! quit while youre ahead"
        ]
    else:
        data["embers"] -= amount
        update_user(user_id, "embers", data["embers"])
        responses = [
            f"you lost **{amount}** embers. the house always wins fam",
            f"**{amount}** embers down the drain. gambling addiction is real lol",
            f"tough luck, lost **{amount}** embers. maybe stick to honest work",
            f"**{amount}** embers lost. shouldve listened to your mom about gambling"
        ]
    await ctx.send(random.choice(responses))

@bot.command(name="slots")
async def slots(ctx, amount: int = 10):
    if amount <= 0:
        await ctx.send("nah fam minimum bet is 1 ember")
        return
    user_id = ctx.author.id
    data = get_user_data(user_id)
    if data["embers"] < amount:
        await ctx.send(f"you broke, need **{amount}** embers to play. you got **{data['embers']}**")
        return
    symbols = ["fire", "diamond", "clover", "star", "money", "seven"]
    result = [random.choice(symbols) for _ in range(3)]
    result_str = " | ".join(result)
    data["embers"] -= amount
    if result[0] == result[1] == result[2]:
        winnings = amount * 10
        data["embers"] += winnings
        update_user(user_id, "embers", data["embers"])
        msg = result_str + chr(10) + "**JACKPOT!** You won **" + str(winnings) + "** embers! youre literally rich now"
        await ctx.send(msg)
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        winnings = amount * 2
        data["embers"] += winnings
        update_user(user_id, "embers", data["embers"])
        msg = result_str + chr(10) + "Nice! Two matches! You got **" + str(winnings) + "** embers back"
        await ctx.send(msg)
    else:
        update_user(user_id, "embers", data["embers"])
        msg = result_str + chr(10) + "Nothing matched. Lost **" + str(amount) + "** embers. better luck next time lol"
        await ctx.send(msg)


# ============ CREATURES COMMANDS ============
CREATURE_TYPES = [
    "Phoenix", "Dragon", "Wolf", "Tiger", "Eagle", "Snake", "Bear", "Lion",
    "Fox", "Raven", "Spider", "Scorpion", "Hydra", "Griffin", "Unicorn"
]

CREATURE_MOODS = ["happy", "angry", "sad", "excited", "sleepy", "hungry", "playful"]

@bot.command(name="summon")
async def summon(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "summon", 1800)
    if not can_use:
        await ctx.send(f"your summoning circle is still recharging. wait {remaining // 60}m")
        return
    creature_type = random.choice(CREATURE_TYPES)
    creature_name = f"{creature_type} #{random.randint(1000, 9999)}"
    creature = {
        "name": creature_name,
        "type": creature_type,
        "level": 1,
        "xp": 0,
        "mood": "neutral",
        "hunger": 50,
        "health": 100,
        "strength": random.randint(10, 30),
        "speed": random.randint(10, 30),
        "intelligence": random.randint(10, 30),
        "favorite": False,
        "custom_name": None
    }
    if "creatures" not in data:
        data["creatures"] = []
    data["creatures"].append(creature)
    update_user(user_id, "creatures", data["creatures"])
    await ctx.send(f"you summoned a **{creature_name}**! its a {creature_type} with {creature['strength']} strength, {creature['speed']} speed, and {creature['intelligence']} intelligence. take care of it fam!")

@bot.command(name="cage")
async def cage(ctx, user: discord.Member = None):
    user = user or ctx.author
    data = get_user_data(user.id)
    creatures = data.get("creatures", [])
    if not creatures:
        await ctx.send(f"{user.display_name} got no creatures. empty cage vibes lol")
        return
    embed = discord.Embed(title=f"{user.display_name}'s Creature Cage", color=discord.Color.purple())
    for i, c in enumerate(creatures[:10]):
        name = c.get("custom_name") or c["name"]
        embed.add_field(name=f"{i+1}. {name} (Lvl {c['level']})", value=f"Type: {c['type']} | Mood: {c['mood']} | HP: {c['health']}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="release")
async def release(ctx, *, creature_name: str):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    creatures = data.get("creatures", [])
    if not creatures:
        await ctx.send("you got no creatures to release. go summon one first lol")
        return
    for i, c in enumerate(creatures):
        if creature_name.lower() in (c.get("custom_name") or c["name"]).lower():
            released = creatures.pop(i)
            update_user(user_id, "creatures", creatures)
            await ctx.send(f"you released **{released.get('custom_name') or released['name']}** back into the wild. it looked back at you one last time... kinda sad ngl")
            return
    await ctx.send("bruh you dont have a creature with that name. check fcage to see what you got")

@bot.command(name="feed")
async def feed(ctx, *, creature_name: str):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    creatures = data.get("creatures", [])
    if not creatures:
        await ctx.send("you got no creatures to feed. go summon one first fam")
        return
    for c in creatures:
        if creature_name.lower() in (c.get("custom_name") or c["name"]).lower():
            cost = random.randint(10, 50)
            if data["embers"] < cost:
                await ctx.send(f"you broke, need **{cost}** embers to feed your creature. you got **{data['embers']}**")
                return
            data["embers"] -= cost
            c["hunger"] = min(100, c["hunger"] + random.randint(20, 40))
            c["health"] = min(100, c["health"] + random.randint(5, 15))
            c["mood"] = random.choice(["happy", "excited", "playful"])
            c["xp"] += random.randint(5, 15)
            if c["xp"] >= c["level"] * 100:
                c["level"] += 1
                c["xp"] = 0
                c["strength"] += random.randint(2, 5)
                c["speed"] += random.randint(2, 5)
                c["intelligence"] += random.randint(2, 5)
                update_user(user_id, "embers", data["embers"])
                update_user(user_id, "creatures", creatures)
                await ctx.send(f"**LEVEL UP!** {c.get('custom_name') or c['name']} is now level **{c['level']}**! it ate good for **{cost}** embers and got stronger!")
                return
            update_user(user_id, "embers", data["embers"])
            update_user(user_id, "creatures", creatures)
            await ctx.send(f"you fed **{c.get('custom_name') or c['name']}** for **{cost}** embers. its looking happy and full now lol")
            return
    await ctx.send("bruh you dont have a creature with that name. check fcage to see what you got")

@bot.command(name="neglect")
async def neglect(ctx, *, creature_name: str):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    creatures = data.get("creatures", [])
    if not creatures:
        await ctx.send("you got no creatures to neglect. go summon one first fam")
        return
    for c in creatures:
        if creature_name.lower() in (c.get("custom_name") or c["name"]).lower():
            c["hunger"] = max(0, c["hunger"] - random.randint(20, 40))
            c["health"] = max(0, c["health"] - random.randint(5, 15))
            c["mood"] = random.choice(["angry", "sad", "hungry"])
            if c["health"] <= 0:
                creatures.remove(c)
                update_user(user_id, "creatures", creatures)
                await ctx.send(f"**{c.get('custom_name') or c['name']}** died from neglect... youre a monster fam. it trusted you")
                return
            update_user(user_id, "creatures", creatures)
            await ctx.send(f"you neglected **{c.get('custom_name') or c['name']}**. its now {c['mood']} and losing health. youre a terrible owner lol")
            return
    await ctx.send("bruh you dont have a creature with that name. check fcage to see what you got")

@bot.command(name="mood")
async def mood(ctx, *, creature_name: str):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    creatures = data.get("creatures", [])
    if not creatures:
        await ctx.send("you got no creatures. go summon one first fam")
        return
    for c in creatures:
        if creature_name.lower() in (c.get("custom_name") or c["name"]).lower():
            embed = discord.Embed(title=f"{c.get('custom_name') or c['name']}'s Mood", color=discord.Color.purple())
            embed.add_field(name="Mood", value=c["mood"], inline=True)
            embed.add_field(name="Hunger", value=f"{c['hunger']}/100", inline=True)
            embed.add_field(name="Health", value=f"{c['health']}/100", inline=True)
            embed.add_field(name="Level", value=c["level"], inline=True)
            embed.add_field(name="XP", value=c["xp"], inline=True)
            embed.add_field(name="Strength", value=c["strength"], inline=True)
            await ctx.send(embed=embed)
            return
    await ctx.send("bruh you dont have a creature with that name. check fcage to see what you got")

@bot.command(name="evolve")
async def evolve(ctx, *, creature_name: str):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    creatures = data.get("creatures", [])
    if not creatures:
        await ctx.send("you got no creatures to evolve. go summon one first fam")
        return
    for c in creatures:
        if creature_name.lower() in (c.get("custom_name") or c["name"]).lower():
            if c["level"] < 5:
                await ctx.send(f"**{c.get('custom_name') or c['name']}** needs to be at least level 5 to evolve. its only level {c['level']} right now. keep feeding it!")
                return
            cost = c["level"] * 200
            if data["embers"] < cost:
                await ctx.send(f"evolution costs **{cost}** embers. you only got **{data['embers']}**. grind more fam")
                return
            data["embers"] -= cost
            c["level"] += 1
            c["strength"] += random.randint(10, 20)
            c["speed"] += random.randint(10, 20)
            c["intelligence"] += random.randint(10, 20)
            c["health"] = 100
            c["mood"] = "excited"
            update_user(user_id, "embers", data["embers"])
            update_user(user_id, "creatures", creatures)
            await ctx.send(f"**EVOLUTION!** {c.get('custom_name') or c['name']} evolved into a stronger form! its now level **{c['level']}** with boosted stats! cost you **{cost}** embers but worth it fam!")
            return
    await ctx.send("bruh you dont have a creature with that name. check fcage to see what you got")

@bot.command(name="breed")
async def breed(ctx, creature1: str, creature2: str):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    creatures = data.get("creatures", [])
    if len(creatures) < 2:
        await ctx.send("you need at least 2 creatures to breed. go summon more fam")
        return
    c1 = None
    c2 = None
    for c in creatures:
        if creature1.lower() in (c.get("custom_name") or c["name"]).lower():
            c1 = c
        if creature2.lower() in (c.get("custom_name") or c["name"]).lower():
            c2 = c
    if not c1 or not c2:
        await ctx.send("bruh one or both of those creatures dont exist. check fcage")
        return
    if c1 == c2:
        await ctx.send("bro you cant breed a creature with itself. thats not how biology works lol")
        return
    can_use, remaining = check_cd(user_id, "breed", 3600)
    if not can_use:
        await ctx.send(f"your creatures are still recovering from last time. wait {remaining // 60}m")
        return
    baby_type = random.choice([c1["type"], c2["type"]])
    baby_name = f"Baby {baby_type} #{random.randint(1000, 9999)}"
    baby = {
        "name": baby_name,
        "type": baby_type,
        "level": 1,
        "xp": 0,
        "mood": "happy",
        "hunger": 50,
        "health": 100,
        "strength": (c1["strength"] + c2["strength"]) // 2 + random.randint(-5, 5),
        "speed": (c1["speed"] + c2["speed"]) // 2 + random.randint(-5, 5),
        "intelligence": (c1["intelligence"] + c2["intelligence"]) // 2 + random.randint(-5, 5),
        "favorite": False,
        "custom_name": None
    }
    creatures.append(baby)
    update_user(user_id, "creatures", creatures)
    await ctx.send(f"**BABY BORN!** {c1.get('custom_name') or c1['name']} and {c2.get('custom_name') or c2['name']} had a baby! its a **{baby_name}**! so cute fam!")

@bot.command(name="sacrifice")
async def sacrifice(ctx, *, creature_name: str):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    creatures = data.get("creatures", [])
    if not creatures:
        await ctx.send("you got no creatures to sacrifice. go summon one first fam")
        return
    for i, c in enumerate(creatures):
        if creature_name.lower() in (c.get("custom_name") or c["name"]).lower():
            embers_gained = c["level"] * random.randint(100, 300)
            data["embers"] += embers_gained
            sacrificed = creatures.pop(i)
            update_user(user_id, "embers", data["embers"])
            update_user(user_id, "creatures", creatures)
            await ctx.send(f"you sacrificed **{sacrificed.get('custom_name') or sacrificed['name']}** to the flame gods and got **{embers_gained}** embers. dark but profitable lol")
            return
    await ctx.send("bruh you dont have a creature with that name. check fcage to see what you got")

@bot.command(name="rename")
async def rename(ctx, creature_name: str, *, new_name: str):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    creatures = data.get("creatures", [])
    if not creatures:
        await ctx.send("you got no creatures to rename. go summon one first fam")
        return
    for c in creatures:
        if creature_name.lower() in (c.get("custom_name") or c["name"]).lower():
            old_name = c.get("custom_name") or c["name"]
            c["custom_name"] = new_name
            update_user(user_id, "creatures", creatures)
            await ctx.send(f"renamed **{old_name}** to **{new_name}**! much better name fam")
            return
    await ctx.send("bruh you dont have a creature with that name. check fcage to see what you got")

@bot.command(name="favorite")
async def favorite(ctx, *, creature_name: str):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    creatures = data.get("creatures", [])
    if not creatures:
        await ctx.send("you got no creatures. go summon one first fam")
        return
    for c in creatures:
        if creature_name.lower() in (c.get("custom_name") or c["name"]).lower():
            for other in creatures:
                other["favorite"] = False
            c["favorite"] = True
            update_user(user_id, "creatures", creatures)
            update_user(user_id, "favorite_creature", c.get("custom_name") or c["name"])
            await ctx.send(f"**{c.get('custom_name') or c['name']}** is now your favorite creature! it looks extra happy lol")
            return
    await ctx.send("bruh you dont have a creature with that name. check fcage to see what you got")

@bot.command(name="trade")
async def trade(ctx, target: discord.Member, *, creature_name: str):
    if target.id == ctx.author.id:
        await ctx.send("bro you cant trade with yourself. thats just renaming lol")
        return
    user_id = ctx.author.id
    data = get_user_data(user_id)
    target_data = get_user_data(target.id)
    creatures = data.get("creatures", [])
    if not creatures:
        await ctx.send("you got no creatures to trade. go summon one first fam")
        return
    for i, c in enumerate(creatures):
        if creature_name.lower() in (c.get("custom_name") or c["name"]).lower():
            embed = discord.Embed(title="Trade Offer", description=f"{ctx.author.display_name} wants to trade **{c.get('custom_name') or c['name']}** to you!", color=discord.Color.purple())
            embed.set_footer(text="React with ✅ to accept or ❌ to decline")
            trade_msg = await ctx.send(embed=embed)
            await trade_msg.add_reaction("✅")
            await trade_msg.add_reaction("❌")
            def check(reaction, user):
                return user == target and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == trade_msg.id
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
                if str(reaction.emoji) == "✅":
                    traded_creature = creatures.pop(i)
                    if "creatures" not in target_data:
                        target_data["creatures"] = []
                    target_data["creatures"].append(traded_creature)
                    update_user(user_id, "creatures", creatures)
                    update_user(target.id, "creatures", target_data["creatures"])
                    await ctx.send(f"trade complete! **{traded_creature.get('custom_name') or traded_creature['name']}** now belongs to {target.display_name}!")
                else:
                    await ctx.send(f"{target.display_name} declined the trade. rejected lol")
            except:
                await ctx.send("trade expired. nobody reacted in time")
            return
    await ctx.send("bruh you dont have a creature with that name. check fcage to see what you got")

@bot.command(name="auction")
async def auction(ctx, creature_name: str, price: int):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    creatures = data.get("creatures", [])
    if not creatures:
        await ctx.send("you got no creatures to auction. go summon one first fam")
        return
    for i, c in enumerate(creatures):
        if creature_name.lower() in (c.get("custom_name") or c["name"]).lower():
            auction_id = f"AUC{random.randint(10000, 99999)}"
            auctions_data[auction_id] = {
                "seller": ctx.author.id,
                "creature": c,
                "price": price,
                "highest_bid": price,
                "highest_bidder": None,
                "created": datetime.now().timestamp()
            }
            save_data(AUCTION_FILE, auctions_data)
            await ctx.send(f"**AUCTION STARTED!** {c.get('custom_name') or c['name']} is up for auction! Starting bid: **{price}** embers! ID: `{auction_id}`")
            return
    await ctx.send("bruh you dont have a creature with that name. check fcage to see what you got")

@bot.command(name="bid")
async def bid(ctx, auction_id: str, amount: int):
    auction_id = auction_id.upper()
    if auction_id not in auctions_data:
        await ctx.send("bruh that auction dont exist. check active auctions or something lol")
        return
    auction = auctions_data[auction_id]
    if auction["seller"] == ctx.author.id:
        await ctx.send("bro you cant bid on your own auction. thats cheating lol")
        return
    if amount <= auction["highest_bid"]:
        await ctx.send(f"bid must be higher than **{auction['highest_bid']}** embers. step it up fam")
        return
    user_data = get_user_data(ctx.author.id)
    if user_data["embers"] < amount:
        await ctx.send(f"you broke, only got **{user_data['embers']}** embers. cant bid **{amount}**")
        return
    auction["highest_bid"] = amount
    auction["highest_bidder"] = ctx.author.id
    save_data(AUCTION_FILE, auctions_data)
    await ctx.send(f"you bid **{amount}** embers on auction `{auction_id}`! youre the highest bidder now!")

@bot.command(name="inspect")
async def inspect(ctx, *, creature_name: str):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    creatures = data.get("creatures", [])
    if not creatures:
        await ctx.send("you got no creatures to inspect. go summon one first fam")
        return
    for c in creatures:
        if creature_name.lower() in (c.get("custom_name") or c["name"]).lower():
            embed = discord.Embed(title=f"Inspecting {c.get('custom_name') or c['name']}", color=discord.Color.purple())
            embed.add_field(name="Type", value=c["type"], inline=True)
            embed.add_field(name="Level", value=c["level"], inline=True)
            embed.add_field(name="XP", value=f"{c['xp']}/{c['level'] * 100}", inline=True)
            embed.add_field(name="Mood", value=c["mood"], inline=True)
            embed.add_field(name="Hunger", value=f"{c['hunger']}/100", inline=True)
            embed.add_field(name="Health", value=f"{c['health']}/100", inline=True)
            embed.add_field(name="Strength", value=c["strength"], inline=True)
            embed.add_field(name="Speed", value=c["speed"], inline=True)
            embed.add_field(name="Intelligence", value=c["intelligence"], inline=True)
            embed.add_field(name="Favorite", value="Yes" if c["favorite"] else "No", inline=True)
            await ctx.send(embed=embed)
            return
    await ctx.send("bruh you dont have a creature with that name. check fcage to see what you got")

@bot.command(name="adopt")
async def adopt(ctx, *, creature_type: str = None):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "adopt", 3600)
    if not can_use:
        await ctx.send(f"the shelter is closed for cleaning. come back in {remaining // 60}m")
        return
    if creature_type:
        creature_type = creature_type.title()
        if creature_type not in CREATURE_TYPES:
            await ctx.send(f"bruh we dont have {creature_type} at the shelter. available types: {', '.join(CREATURE_TYPES)}")
            return
    else:
        creature_type = random.choice(CREATURE_TYPES)
    cost = random.randint(200, 500)
    if data["embers"] < cost:
        await ctx.send(f"adoption fee is **{cost}** embers. you only got **{data['embers']}**. broke af lol")
        return
    data["embers"] -= cost
    creature_name = f"Adopted {creature_type} #{random.randint(1000, 9999)}"
    creature = {
        "name": creature_name,
        "type": creature_type,
        "level": random.randint(1, 3),
        "xp": 0,
        "mood": "grateful",
        "hunger": 60,
        "health": 100,
        "strength": random.randint(5, 20),
        "speed": random.randint(5, 20),
        "intelligence": random.randint(5, 20),
        "favorite": False,
        "custom_name": None
    }
    if "creatures" not in data:
        data["creatures"] = []
    data["creatures"].append(creature)
    update_user(user_id, "embers", data["embers"])
    update_user(user_id, "creatures", data["creatures"])
    await ctx.send(f"you adopted **{creature_name}** from the shelter for **{cost}** embers! it looks so grateful fam!")

@bot.command(name="kidnap")
async def kidnap(ctx, target: discord.Member, *, creature_name: str):
    if target.id == ctx.author.id:
        await ctx.send("bro you cant kidnap your own creature. thats just moving it lol")
        return
    user_id = ctx.author.id
    data = get_user_data(user_id)
    target_data = get_user_data(target.id)
    target_creatures = target_data.get("creatures", [])
    if not target_creatures:
        await ctx.send(f"{target.display_name} got no creatures to kidnap. they broke even in the creature game lol")
        return
    can_use, remaining = check_cd(user_id, "kidnap", 3600)
    if not can_use:
        await ctx.send(f"the cops are watching you after the last kidnapping attempt. wait {remaining // 60}m")
        return
    for i, c in enumerate(target_creatures):
        if creature_name.lower() in (c.get("custom_name") or c["name"]).lower():
            if random.random() < 0.25:
                kidnapped = target_creatures.pop(i)
                if "creatures" not in data:
                    data["creatures"] = []
                data["creatures"].append(kidnapped)
                update_user(target.id, "creatures", target_creatures)
                update_user(user_id, "creatures", data["creatures"])
                await ctx.send(f"**KIDNAP SUCCESSFUL!** you stole **{kidnapped.get('custom_name') or kidnapped['name']}** from {target.display_name}! youre a criminal mastermind lol")
            else:
                fine = random.randint(100, 300)
                data["embers"] = max(0, data["embers"] - fine)
                update_user(user_id, "embers", data["embers"])
                await ctx.send(f"**BUSTED!** {target.display_name} caught you trying to kidnap their creature and you got fined **{fine}** embers. stick to legal methods fam")
            return
    await ctx.send(f"bruh {target.display_name} dont have a creature with that name")


# ============ COMBAT COMMANDS ============
COMBAT_RANKS = ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master", "Grandmaster", "Legend"]

@bot.command(name="duel")
async def duel(ctx, opponent: discord.Member):
    if opponent.id == ctx.author.id:
        await ctx.send("bro you cant duel yourself. thats just shadow boxing lol")
        return
    if opponent.id == bot.user.id:
        await ctx.send("nah fam i dont fight users. im a peaceful bot lol")
        return
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    opp_data = get_user_data(opponent.id)
    can_use, remaining = check_cd(user_id, "duel", 300)
    if not can_use:
        await ctx.send(f"chill warrior, you just fought someone. wait {remaining}s")
        return
    user_creatures = user_data.get("creatures", [])
    opp_creatures = opp_data.get("creatures", [])
    if not user_creatures:
        await ctx.send("you got no creatures to duel with. go summon one first fam")
        return
    if not opp_creatures:
        await ctx.send(f"{opponent.display_name} got no creatures. they cant fight lol")
        return
    user_creature = user_creatures[0]
    opp_creature = opp_creatures[0]
    embed = discord.Embed(title="DUEL CHALLENGE!", description=f"{ctx.author.display_name} challenges {opponent.display_name} to a duel!", color=discord.Color.red())
    embed.add_field(name=f"{ctx.author.display_name}'s Fighter", value=f"{user_creature.get('custom_name') or user_creature['name']} (Lvl {user_creature['level']})", inline=True)
    embed.add_field(name=f"{opponent.display_name}'s Fighter", value=f"{opp_creature.get('custom_name') or opp_creature['name']} (Lvl {opp_creature['level']})", inline=True)
    embed.set_footer(text=f"{opponent.display_name}, react with ⚔️ to accept or 🏳️ to decline")
    duel_msg = await ctx.send(embed=embed)
    await duel_msg.add_reaction("⚔️")
    await duel_msg.add_reaction("🏳️")
    def check(reaction, user):
        return user == opponent and str(reaction.emoji) in ["⚔️", "🏳️"] and reaction.message.id == duel_msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        if str(reaction.emoji) == "🏳️":
            await ctx.send(f"{opponent.display_name} declined the duel. coward lol")
            return
    except:
        await ctx.send("duel expired. nobody reacted in time")
        return
    user_power = user_creature["strength"] + user_creature["speed"] + user_creature["intelligence"] + user_creature["level"] * 10
    opp_power = opp_creature["strength"] + opp_creature["speed"] + opp_creature["intelligence"] + opp_creature["level"] * 10
    user_power += random.randint(-20, 20)
    opp_power += random.randint(-20, 20)
    if user_power > opp_power:
        winnings = random.randint(50, 200)
        user_data["embers"] += winnings
        user_data["wins"] = user_data.get("wins", 0) + 1
        user_data["duels"] = user_data.get("duels", 0) + 1
        opp_data["losses"] = opp_data.get("losses", 0) + 1
        opp_data["duels"] = opp_data.get("duels", 0) + 1
        user_creature["xp"] += random.randint(20, 50)
        update_user(user_id, "embers", user_data["embers"])
        update_user(user_id, "wins", user_data["wins"])
        update_user(user_id, "duels", user_data["duels"])
        update_user(opponent.id, "losses", opp_data["losses"])
        update_user(opponent.id, "duels", opp_data["duels"])
        update_user(user_id, "creatures", user_data["creatures"])
        await ctx.send(f"**{ctx.author.display_name} WINS!** {user_creature.get('custom_name') or user_creature['name']} defeated {opp_creature.get('custom_name') or opp_creature['name']}! won **{winnings}** embers!")
    elif opp_power > user_power:
        winnings = random.randint(50, 200)
        opp_data["embers"] += winnings
        opp_data["wins"] = opp_data.get("wins", 0) + 1
        opp_data["duels"] = opp_data.get("duels", 0) + 1
        user_data["losses"] = user_data.get("losses", 0) + 1
        user_data["duels"] = user_data.get("duels", 0) + 1
        opp_creature["xp"] += random.randint(20, 50)
        update_user(opponent.id, "embers", opp_data["embers"])
        update_user(opponent.id, "wins", opp_data["wins"])
        update_user(opponent.id, "duels", opp_data["duels"])
        update_user(user_id, "losses", user_data["losses"])
        update_user(user_id, "duels", user_data["duels"])
        update_user(opponent.id, "creatures", opp_data["creatures"])
        await ctx.send(f"**{opponent.display_name} WINS!** {opp_creature.get('custom_name') or opp_creature['name']} defeated {user_creature.get('custom_name') or user_creature['name']}! {opponent.display_name} won **{winnings}** embers!")
    else:
        user_data["duels"] = user_data.get("duels", 0) + 1
        opp_data["duels"] = opp_data.get("duels", 0) + 1
        update_user(user_id, "duels", user_data["duels"])
        update_user(opponent.id, "duels", opp_data["duels"])
        await ctx.send("**DRAW!** both creatures are equally matched. nobody wins, nobody loses. anticlimactic lol")

@bot.command(name="raid")
async def raid(ctx):
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "raid", 7200)
    if not can_use:
        await ctx.send(f"your raid party is still recovering. wait {remaining // 60}m")
        return
    user_creatures = user_data.get("creatures", [])
    if not user_creatures:
        await ctx.send("you got no creatures for a raid. go summon one first fam")
        return
    dungeon_level = random.randint(1, 10)
    boss_health = dungeon_level * 100
    boss_name = random.choice(["Fire Demon", "Shadow Beast", "Ice Golem", "Thunder Dragon", "Void Walker"])
    await ctx.send(f"**RAID STARTED!** Dungeon Level {dungeon_level}: {boss_name} appears! HP: {boss_health}")
    await asyncio.sleep(2)
    total_damage = 0
    for c in user_creatures[:3]:
        damage = c["strength"] + c["speed"] + random.randint(-10, 20)
        total_damage += damage
        await ctx.send(f"{c.get('custom_name') or c['name']} attacks for **{damage}** damage!")
        await asyncio.sleep(1)
    if total_damage >= boss_health:
        reward = dungeon_level * random.randint(100, 300)
        user_data["embers"] += reward
        user_data["raids"] = user_data.get("raids", 0) + 1
        for c in user_creatures[:3]:
            c["xp"] += random.randint(30, 60)
        update_user(user_id, "embers", user_data["embers"])
        update_user(user_id, "raids", user_data["raids"])
        update_user(user_id, "creatures", user_data["creatures"])
        await ctx.send(f"**RAID SUCCESSFUL!** you defeated {boss_name} and got **{reward}** embers! your creatures gained XP!")
    else:
        await ctx.send(f"**RAID FAILED!** {boss_name} was too strong. your creatures dealt {total_damage} damage but needed {boss_health}. train harder fam!")

@bot.command(name="ambush")
async def ambush(ctx, target: discord.Member):
    if target.id == ctx.author.id:
        await ctx.send("bro you cant ambush yourself. thats just jumping out at a mirror lol")
        return
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    target_data = get_user_data(target.id)
    can_use, remaining = check_cd(user_id, "ambush", 1800)
    if not can_use:
        await ctx.send(f"your ambush spot is still hot. wait {remaining // 60}m")
        return
    if random.random() < 0.4:
        stolen = random.randint(50, 300)
        stolen = min(stolen, target_data["embers"] // 2)
        if stolen > 0:
            target_data["embers"] -= stolen
            user_data["embers"] += stolen
            update_user(target.id, "embers", target_data["embers"])
            update_user(user_id, "embers", user_data["embers"])
            await ctx.send(f"**AMBUSH SUCCESSFUL!** you jumped {target.display_name} and stole **{stolen}** embers! ninja moves fam!")
        else:
            await ctx.send(f"you ambushed {target.display_name} but they broke af. got nothing lol")
    else:
        fine = random.randint(50, 150)
        user_data["embers"] = max(0, user_data["embers"] - fine)
        update_user(user_id, "embers", user_data["embers"])
        await ctx.send(f"**AMBUSH FAILED!** {target.display_name} saw you coming and you tripped. lost **{fine}** embers in medical bills lol")

@bot.command(name="defend")
async def defend(ctx):
    user_id = ctx.author.id
    can_use, remaining = check_cd(user_id, "defend", 600)
    if not can_use:
        await ctx.send(f"youre still in defensive stance. wait {remaining}s")
        return
    await ctx.send("you entered **DEFENSIVE MODE**! for the next 10 minutes you take reduced damage from robberies and ambushes. turtle up fam!")

@bot.command(name="berserk")
async def berserk(ctx):
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "berserk", 1800)
    if not can_use:
        await ctx.send(f"your rage is still cooling down. wait {remaining // 60}m")
        return
    cost = random.randint(50, 150)
    if user_data["embers"] < cost:
        await ctx.send(f"berserk mode costs **{cost}** embers to activate. you only got **{user_data['embers']}**. too broke to be angry lol")
        return
    user_data["embers"] -= cost
    update_user(user_id, "embers", user_data["embers"])
    await ctx.send(f"**BERSERK MODE ACTIVATED!** you spent **{cost}** embers to enter a rage! your next duel/raid does double damage but you might hurt yourself too lol")

@bot.command(name="bribe")
async def bribe(ctx, amount: int):
    if amount <= 0:
        await ctx.send("bruh you cant bribe with nothing. cops dont work for free lol")
        return
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    if user_data["embers"] < amount:
        await ctx.send(f"you broke, only got **{user_data['embers']}** embers. cant bribe with **{amount}**")
        return
    user_data["embers"] -= amount
    update_user(user_id, "embers", user_data["embers"])
    await ctx.send(f"you bribed the guards with **{amount}** embers. they look the other way for now. corruption at its finest lol")

@bot.command(name="flee")
async def flee(ctx):
    user_id = ctx.author.id
    can_use, remaining = check_cd(user_id, "flee", 300)
    if not can_use:
        await ctx.send(f"your legs are still tired from the last escape. wait {remaining}s")
        return
    responses = [
        "you ran away like a coward. at least youre alive lol",
        "you fled the scene. nobody saw you... probably",
        "escape successful! you left everyone behind. selfish but smart",
        "you disappeared in a cloud of smoke. ninja vanish!"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="taunt")
async def taunt(ctx, target: discord.Member):
    if target.id == ctx.author.id:
        await ctx.send("bro you cant taunt yourself. thats just talking to a mirror lol")
        return
    taunts = [
        f"yo {target.display_name}, you fight like a baby phoenix! weak af!",
        f"{target.display_name} probably loses to slimes in raids. trash lol",
        f"ive seen better combat from a potato than {target.display_name}",
        f"{target.display_name} is so bad at fighting, their creatures pity them",
        f"yo {target.display_name}, your combat rank is participation trophy level"
    ]
    await ctx.send(random.choice(taunts))

@bot.command(name="combo")
async def combo(ctx, target: discord.Member):
    if target.id == ctx.author.id:
        await ctx.send("bro you cant combo yourself. thats just hitting yourself lol")
        return
    user_id = ctx.author.id
    can_use, remaining = check_cd(user_id, "combo", 600)
    if not can_use:
        await ctx.send(f"your combo meter is recharging. wait {remaining}s")
        return
    hits = random.randint(2, 5)
    total_damage = 0
    for i in range(hits):
        damage = random.randint(10, 50)
        total_damage += damage
    await ctx.send(f"**COMBO ATTACK!** you hit {target.display_name} **{hits}** times for **{total_damage}** total damage! theyre seeing stars lol")

@bot.command(name="revive")
async def revive(ctx):
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    cost = random.randint(100, 300)
    if user_data["embers"] < cost:
        await ctx.send(f"revival costs **{cost}** embers. you only got **{user_data['embers']}**. even death is pay to win lol")
        return
    user_data["embers"] -= cost
    update_user(user_id, "embers", user_data["embers"])
    await ctx.send(f"you paid **{cost}** embers to revive. back from the dead! zombie hours lol")

@bot.command(name="wager")
async def wager(ctx, amount: int, target: discord.Member):
    if target.id == ctx.author.id:
        await ctx.send("bro you cant wager against yourself. thats just giving away money lol")
        return
    if amount <= 0:
        await ctx.send("nah fam cant wager negative embers. what are you tryna pull?")
        return
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    target_data = get_user_data(target.id)
    if user_data["embers"] < amount:
        await ctx.send(f"you broke, only got **{user_data['embers']}** embers. cant wager **{amount}**")
        return
    if target_data["embers"] < amount:
        await ctx.send(f"{target.display_name} is too broke to match your **{amount}** ember wager. find a richer opponent lol")
        return
    embed = discord.Embed(title="Wager Challenge!", description=f"{ctx.author.display_name} wants to wager **{amount}** embers against {target.display_name}!", color=discord.Color.gold())
    embed.set_footer(text=f"{target.display_name}, react with ✅ to accept or ❌ to decline")
    wager_msg = await ctx.send(embed=embed)
    await wager_msg.add_reaction("✅")
    await wager_msg.add_reaction("❌")
    def check(reaction, user):
        return user == target and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == wager_msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        if str(reaction.emoji) == "❌":
            await ctx.send(f"{target.display_name} declined the wager. scared of losing lol")
            return
    except:
        await ctx.send("wager expired. nobody reacted in time")
        return
    if random.random() < 0.5:
        user_data["embers"] += amount
        target_data["embers"] -= amount
        update_user(user_id, "embers", user_data["embers"])
        update_user(target.id, "embers", target_data["embers"])
        await ctx.send(f"**{ctx.author.display_name} WINS THE WAGER!** took **{amount}** embers from {target.display_name}! easy money fam!")
    else:
        user_data["embers"] -= amount
        target_data["embers"] += amount
        update_user(user_id, "embers", user_data["embers"])
        update_user(target.id, "embers", target_data["embers"])
        await ctx.send(f"**{target.display_name} WINS THE WAGER!** took **{amount}** embers from {ctx.author.display_name}! better luck next time lol")

@bot.command(name="rank")
async def rank(ctx, user: discord.Member = None):
    user = user or ctx.author
    data = get_user_data(user.id)
    wins = data.get("wins", 0)
    losses = data.get("losses", 0)
    duels = data.get("duels", 0)
    raids = data.get("raids", 0)
    rank_index = min(wins // 10, len(COMBAT_RANKS) - 1)
    combat_rank = COMBAT_RANKS[rank_index]
    embed = discord.Embed(title=f"{user.display_name}'s Combat Rank", color=discord.Color.red())
    embed.add_field(name="Rank", value=f"**{combat_rank}**", inline=True)
    embed.add_field(name="Wins", value=wins, inline=True)
    embed.add_field(name="Losses", value=losses, inline=True)
    embed.add_field(name="Duels", value=duels, inline=True)
    embed.add_field(name="Raids", value=raids, inline=True)
    embed.add_field(name="Win Rate", value=f"{wins/max(1, duels)*100:.1f}%" if duels > 0 else "N/A", inline=True)
    embed.set_footer(text="keep fighting to rank up fam!")
    await ctx.send(embed=embed)


# ============ GAMBLING COMMANDS ============
@bot.command(name="dice")
async def dice(ctx, sides: int = 6):
    if sides < 2:
        await ctx.send("bruh a dice needs at least 2 sides. use your brain lol")
        return
    result = random.randint(1, sides)
    responses = [
        f"rolled a **{result}** on a {sides}-sided dice. nice",
        f"you got **{result}**! lucky number maybe?",
        f"**{result}**! could be better could be worse lol",
        f"the dice says **{result}**. dont gamble with that luck"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="shells")
async def shells(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "shells", 300)
    if not can_use:
        await ctx.send(f"the shells are still spinning. wait {remaining}s")
        return
    cost = 25
    if data["embers"] < cost:
        await ctx.send(f"shell game costs **{cost}** embers. you only got **{data['embers']}**. too broke to play lol")
        return
    data["embers"] -= cost
    update_user(user_id, "embers", data["embers"])
    ball_position = random.randint(1, 3)
    await ctx.send("**SHELL GAME!** im hiding a ball under one of 3 cups! type `1`, `2`, or `3` to guess!")
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content in ["1", "2", "3"]
    try:
        msg = await bot.wait_for("message", timeout=30.0, check=check)
        guess = int(msg.content)
        if guess == ball_position:
            winnings = cost * 3
            data["embers"] += winnings
            update_user(user_id, "embers", data["embers"])
            await ctx.send(f"**CORRECT!** the ball was under cup **{ball_position}**! you won **{winnings}** embers! sharp eyes fam!")
        else:
            await ctx.send(f"**WRONG!** the ball was under cup **{ball_position}**! you lost your **{cost}** embers. better luck next time lol")
    except:
        await ctx.send("you took too long to guess. ball disappeared. magic i guess lol")

@bot.command(name="flip")
async def flip(ctx):
    result = random.choice(["Heads", "Tails"])
    responses = [
        f"its **{result}**! you win... nothing lol",
        f"**{result}**! go buy a lottery ticket maybe",
        f"landed on **{result}**. what are you gonna do with that info?",
        f"**{result}**! dont spend it all in one place"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="spin")
async def spin(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "spin", 600)
    if not can_use:
        await ctx.send(f"the wheel is still spinning from last time. wait {remaining}s")
        return
    cost = 50
    if data["embers"] < cost:
        await ctx.send(f"spin costs **{cost}** embers. you only got **{data['embers']}**. too broke to spin lol")
        return
    data["embers"] -= cost
    update_user(user_id, "embers", data["embers"])
    outcomes = [
        ("Bankrupt", -100, "red"),
        ("Small Win", 50, "green"),
        ("Jackpot", 500, "gold"),
        ("Nothing", 0, "gray"),
        ("Double", cost * 2, "blue"),
        ("Lose Half", -cost // 2, "orange")
    ]
    outcome, amount, color = random.choice(outcomes)
    data["embers"] += amount
    update_user(user_id, "embers", data["embers"])
    if amount > 0:
        await ctx.send(f"**{outcome}!** the wheel landed on **{color.upper()}**! you won **{amount}** embers! lets go fam!")
    elif amount < 0:
        await ctx.send(f"**{outcome}!** the wheel landed on **{color.upper()}**! you lost **{abs(amount)}** embers! ouch lol")
    else:
        await ctx.send(f"**{outcome}!** the wheel landed on **{color.upper()}**! you broke even. boring lol")

@bot.command(name="surge")
async def surge(ctx, amount: int):
    if amount <= 0:
        await ctx.send("bruh you cant surge bet nothing. put some embers on the line")
        return
    user_id = ctx.author.id
    data = get_user_data(user_id)
    if data["embers"] < amount:
        await ctx.send(f"you only got **{data['embers']}** embers, cant surge **{amount}**. check your balance lol")
        return
    data["embers"] -= amount
    update_user(user_id, "embers", data["embers"])
    multiplier = random.choice([0, 0.5, 1, 2, 3, 5, 10])
    winnings = int(amount * multiplier)
    if winnings > 0:
        data["embers"] += winnings
        update_user(user_id, "embers", data["embers"])
        await ctx.send(f"**SURGE!** multiplier: **{multiplier}x**! you turned **{amount}** into **{winnings}** embers! insane luck fam!")
    else:
        await ctx.send(f"**SURGE FAILED!** multiplier: **{multiplier}x**! you lost all **{amount}** embers! thats the risk you take lol")

@bot.command(name="vault")
async def vault(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "vault", 1800)
    if not can_use:
        await ctx.send(f"the vault is on lockdown after your last attempt. wait {remaining // 60}m")
        return
    cost = 100
    if data["embers"] < cost:
        await ctx.send(f"vault cracking costs **{cost}** embers for tools. you only got **{data['embers']}**. too broke to be a thief lol")
        return
    data["embers"] -= cost
    update_user(user_id, "embers", data["embers"])
    code = str(random.randint(1000, 9999))
    attempts = 3
    await ctx.send(f"**VAULT CRACKING!** guess the 4-digit code! you got **{attempts}** attempts! type a 4-digit number!")
    while attempts > 0:
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit() and len(m.content) == 4
        try:
            msg = await bot.wait_for("message", timeout=30.0, check=check)
            guess = msg.content
            if guess == code:
                winnings = random.randint(200, 1000)
                data["embers"] += winnings
                update_user(user_id, "embers", data["embers"])
                await ctx.send(f"**VAULT CRACKED!** code was **{code}**! you stole **{winnings}** embers! master thief fam!")
                return
            else:
                attempts -= 1
                if attempts > 0:
                    hint = ""
                    correct_digits = sum(1 for a, b in zip(guess, code) if a == b)
                    hint = f"{correct_digits} digits in the right place!"
                    await ctx.send(f"wrong code! {hint} **{attempts}** attempts left!")
                else:
                    await ctx.send(f"**VAULT LOCKED!** the code was **{code}**! you got caught by security and lost your **{cost}** embers! failed heist lol")
        except:
            await ctx.send(f"you took too long! the vault locked itself. code was **{code}**! amateur hour lol")
            return

@bot.command(name="pick")
async def pick(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "pick", 300)
    if not can_use:
        await ctx.send(f"the deck is still being shuffled. wait {remaining}s")
        return
    cost = 25
    if data["embers"] < cost:
        await ctx.send(f"picking a card costs **{cost}** embers. you only got **{data['embers']}**. too broke to play cards lol")
        return
    data["embers"] -= cost
    update_user(user_id, "embers", data["embers"])
    suits = ["Hearts", "Diamonds", "Clubs", "Spades"]
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    card = f"{random.choice(ranks)} of {random.choice(suits)}"
    value = ranks.index(card.split(" of ")[0]) + 2
    bot_card = f"{random.choice(ranks)} of {random.choice(suits)}"
    bot_value = ranks.index(bot_card.split(" of ")[0]) + 2
    if value > bot_value:
        winnings = cost * 2
        data["embers"] += winnings
        update_user(user_id, "embers", data["embers"])
        await ctx.send(f"you picked **{card}** (value {value}) vs my **{bot_card}** (value {bot_value})! **YOU WIN!** got **{winnings}** embers!")
    elif value < bot_value:
        await ctx.send(f"you picked **{card}** (value {value}) vs my **{bot_card}** (value {bot_value})! **YOU LOSE!** lost your **{cost}** embers!")
    else:
        data["embers"] += cost
        update_user(user_id, "embers", data["embers"])
        await ctx.send(f"you picked **{card}** vs my **{bot_card}**! **TIE!** you get your **{cost}** embers back!")

@bot.command(name="chase")
async def chase(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "chase", 600)
    if not can_use:
        await ctx.send(f"the cops are still looking for you from the last chase. wait {remaining}s")
        return
    cost = 50
    if data["embers"] < cost:
        await ctx.send(f"you need **{cost}** embers to start a chase. you only got **{data['embers']}**. too broke to run from the law lol")
        return
    data["embers"] -= cost
    update_user(user_id, "embers", data["embers"])
    await ctx.send("**CHASE STARTED!** the cops are after you! type `left`, `right`, `jump`, or `hide` to escape!")
    moves = ["left", "right", "jump", "hide"]
    correct_moves = 0
    for round_num in range(1, 6):
        correct_move = random.choice(moves)
        await ctx.send(f"Round {round_num}/5: cops approaching! what do you do? (`left`/`right`/`jump`/`hide`)")
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in moves
        try:
            msg = await bot.wait_for("message", timeout=10.0, check=check)
            if msg.content.lower() == correct_move:
                correct_moves += 1
                await ctx.send("good move! you evaded them!")
            else:
                await ctx.send(f"bad move! they cornered you! correct was `{correct_move}`!")
        except:
            await ctx.send("you froze! they caught you! game over lol")
            break
    if correct_moves >= 3:
        winnings = cost * correct_moves
        data["embers"] += winnings
        update_user(user_id, "embers", data["embers"])
        await ctx.send(f"**ESCAPE SUCCESSFUL!** you evaded the cops **{correct_moves}/5** times! won **{winnings}** embers! criminal legend!")
    else:
        await ctx.send(f"**CAUGHT!** you only evaded them **{correct_moves}/5** times! lost your **{cost}** embers and got a criminal record lol")

@bot.command(name="chamber")
async def chamber(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "chamber", 1800)
    if not can_use:
        await ctx.send(f"the gun is still being cleaned after last time. wait {remaining // 60}m")
        return
    cost = 100
    if data["embers"] < cost:
        await ctx.send(f"russian roulette costs **{cost}** embers. you only got **{data['embers']}**. too broke to risk your life lol")
        return
    data["embers"] -= cost
    update_user(user_id, "embers", data["embers"])
    await ctx.send("**RUSSIAN ROULETTE!** 1 in 6 chance to lose EVERYTHING! type `pull` to pull the trigger or `chicken` to chicken out!")
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["pull", "chicken"]
    try:
        msg = await bot.wait_for("message", timeout=30.0, check=check)
        if msg.content.lower() == "chicken":
            data["embers"] += cost // 2
            update_user(user_id, "embers", data["embers"])
            await ctx.send(f"you chickened out and got **{cost // 2}** embers back. smart move probably lol")
            return
        bullet = random.randint(1, 6)
        if bullet == 1:
            data["embers"] = 0
            update_user(user_id, "embers", 0)
            await ctx.send("**BANG!** you lost ALL your embers! shouldve chickened out lol")
        else:
            winnings = cost * 3
            data["embers"] += winnings
            update_user(user_id, "embers", data["embers"])
            await ctx.send(f"**CLICK!** chamber {bullet}/6 was empty! you survived and won **{winnings}** embers! adrenaline junkie fam!")
    except:
        await ctx.send("you took too long! the gun went off by itself! ...just kidding, you chickened out by default lol")

@bot.command(name="rig")
async def rig(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, remaining = check_cd(user_id, "rig", 3600)
    if not can_use:
        await ctx.send(f"your rigging tools are still cooling down. wait {remaining // 60}m")
        return
    cost = 200
    if data["embers"] < cost:
        await ctx.send(f"rigging costs **{cost}** embers. you only got **{data['embers']}**. too broke to cheat lol")
        return
    data["embers"] -= cost
    update_user(user_id, "embers", data["embers"])
    if random.random() < 0.3:
        await ctx.send("**RIG SUCCESSFUL!** the odds are in your favor for the next 10 minutes! but if you get caught... lol")
    else:
        fine = random.randint(100, 500)
        data["embers"] = max(0, data["embers"] - fine)
        update_user(user_id, "embers", data["embers"])
        await ctx.send(f"**CAUGHT RIGGING!** security saw you and fined you **{fine}** embers! cheaters never prosper lol")

@bot.command(name="coinflip", aliases=["cf"])
async def coinflip(ctx):
    result = random.choice(["Heads", "Tails"])
    responses = [
        f"its **{result}**! you win... nothing lol",
        f"**{result}**! go buy a lottery ticket maybe",
        f"landed on **{result}**. what are you gonna do with that info?",
        f"**{result}**! dont spend it all in one place"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="roll")
async def roll(ctx, max_num: int = 6):
    if max_num < 1:
        await ctx.send("bruh you cant roll a 0 or negative number. use your brain lol")
        return
    result = random.randint(1, max_num)
    responses = [
        f"rolled a **{result}** out of {max_num}. nice",
        f"you got **{result}**! lucky number maybe?",
        f"**{result}**! could be better could be worse lol",
        f"the dice says **{result}**. dont gamble with that luck"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="8ball")
async def eight_ball(ctx, *, question: str):
    responses = [
        "nah fam, thats not happening",
        "yeah probably, idk im just a bot",
        "definitely yes, trust me bro",
        "no shot, keep dreaming lol",
        "maybe? im not psychic",
        "ask again later im busy",
        "signs point to yes but also no",
        "absolutely not, sorry",
        "yo thats actually gonna happen",
        "idk man flip a coin or something",
        "100% yes, bet on it",
        "bruh no, just no"
    ]
    embed = discord.Embed(title="Magic 8-Ball", color=discord.Color.purple())
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=random.choice(responses), inline=False)
    await ctx.send(embed=embed)

@bot.command(name="rate")
async def rate(ctx, *, thing: str):
    score = random.randint(1, 10)
    responses = [
        f"i rate **{thing}** a solid **{score}/10**. could be worse",
        f"**{thing}** gets a **{score}/10** from me. take it or leave it",
        f"honestly **{thing}** is like a **{score}/10**. my opinion matters lol",
        f"**{score}/10** for **{thing}**. im a harsh critic what can i say"
    ]
    await ctx.send(random.choice(responses))


# ============ SOCIAL COMMANDS ============
@bot.command(name="marry")
async def marry(ctx, partner: discord.Member):
    if partner.id == ctx.author.id:
        await ctx.send("bro you cant marry yourself. thats just self-love taken too far lol")
        return
    if partner.id == bot.user.id:
        await ctx.send("nah fam im already married to the grind. cant marry users lol")
        return
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    partner_data = get_user_data(partner.id)
    if user_data.get("married_to"):
        await ctx.send("bruh youre already married. divorce first before proposing again lol")
        return
    if partner_data.get("married_to"):
        await ctx.send(f"{partner.display_name} is already married. homewrecker much? lol")
        return
    embed = discord.Embed(title="Marriage Proposal!", description=f"{ctx.author.display_name} wants to marry you!", color=discord.Color.pink())
    embed.set_footer(text=f"{partner.display_name}, react with 💍 to accept or 🚫 to decline")
    proposal_msg = await ctx.send(embed=embed)
    await proposal_msg.add_reaction("💍")
    await proposal_msg.add_reaction("🚫")
    def check(reaction, user):
        return user == partner and str(reaction.emoji) in ["💍", "🚫"] and reaction.message.id == proposal_msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=120.0, check=check)
        if str(reaction.emoji) == "🚫":
            await ctx.send(f"{partner.display_name} declined your proposal. rejected lol")
            return
    except:
        await ctx.send("proposal expired. they ghosted you lol")
        return
    user_data["married_to"] = partner.id
    partner_data["married_to"] = ctx.author.id
    marriage_data[f"{ctx.author.id}_{partner.id}"] = {"married": datetime.now().isoformat(), "divorces": 0}
    update_user(user_id, "married_to", partner.id)
    update_user(partner.id, "married_to", ctx.author.id)
    save_data(MARRIAGE_FILE, marriage_data)
    await ctx.send(f"**CONGRATS!** {ctx.author.display_name} and {partner.display_name} are now married! love is in the air fam! 💕")

@bot.command(name="divorce")
async def divorce(ctx):
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    partner_id = user_data.get("married_to")
    if not partner_id:
        await ctx.send("bruh youre not even married. cant divorce air lol")
        return
    partner_data = get_user_data(partner_id)
    user_data["married_to"] = None
    partner_data["married_to"] = None
    update_user(user_id, "married_to", None)
    update_user(partner_id, "married_to", None)
    await ctx.send(f"**DIVORCED!** you and <@{partner_id}> are no longer married. rip the love. time to hit the gym and get rich lol")

@bot.command(name="will")
async def will_cmd(ctx, beneficiary: discord.Member):
    if beneficiary.id == ctx.author.id:
        await ctx.send("bro you cant will your embers to yourself. thats just keeping them lol")
        return
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    user_data["will"] = beneficiary.id
    update_user(user_id, "will", beneficiary.id)
    await ctx.send(f"your will has been updated! **{beneficiary.display_name}** will inherit your embers when you quit. morbid but practical lol")

@bot.command(name="cult")
async def cult(ctx, *, cult_name: str = None):
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    if cult_name:
        # Join or create cult
        if user_data.get("cult"):
            await ctx.send(f"youre already in the **{user_data['cult']}** cult. leave first to join another lol")
            return
        cult_name = cult_name.title()
        if cult_name not in settings_data.get("cults", {}):
            if "cults" not in settings_data:
                settings_data["cults"] = {}
            settings_data["cults"][cult_name] = {"leader": ctx.author.id, "members": [ctx.author.id], "embers": 0}
            user_data["cult"] = cult_name
            update_user(user_id, "cult", cult_name)
            save_data(SETTINGS_FILE, settings_data)
            await ctx.send(f"**CULT CREATED!** welcome to **{cult_name}**! you are the cult leader now. start recruiting fam!")
        else:
            settings_data["cults"][cult_name]["members"].append(ctx.author.id)
            user_data["cult"] = cult_name
            update_user(user_id, "cult", cult_name)
            save_data(SETTINGS_FILE, settings_data)
            await ctx.send(f"you joined the **{cult_name}** cult! praise the leader! cult life baby!")
    else:
        # Show cult info
        if user_data.get("cult"):
            cult_info = settings_data.get("cults", {}).get(user_data["cult"], {})
            leader = bot.get_user(cult_info.get("leader", 0))
            leader_name = leader.display_name if leader else "Unknown"
            embed = discord.Embed(title=f"{user_data['cult']} Cult", color=discord.Color.dark_purple())
            embed.add_field(name="Leader", value=leader_name, inline=True)
            embed.add_field(name="Members", value=len(cult_info.get("members", [])), inline=True)
            embed.add_field(name="Cult Embers", value=cult_info.get("embers", 0), inline=True)
            await ctx.send(embed=embed)
        else:
            await ctx.send("youre not in a cult. use `fcult <name>` to create or join one. cult life is calling lol")

@bot.command(name="betray")
async def betray(ctx, target: discord.Member):
    if target.id == ctx.author.id:
        await ctx.send("bro you cant betray yourself. thats just self-sabotage lol")
        return
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    target_data = get_user_data(target.id)
    if not user_data.get("cult") or not target_data.get("cult"):
        await ctx.send("both of you need to be in a cult to betray each other. join one first lol")
        return
    if user_data["cult"] != target_data["cult"]:
        await ctx.send("bruh you can only betray people in YOUR cult. cant betray outsiders lol")
        return
    can_use, remaining = check_cd(user_id, "betray", 3600)
    if not can_use:
        await ctx.send(f"your betrayal knife is still bloody. wait {remaining // 60}m")
        return
    if random.random() < 0.4:
        stolen = random.randint(50, 200)
        stolen = min(stolen, target_data["embers"] // 2)
        if stolen > 0:
            target_data["embers"] -= stolen
            user_data["embers"] += stolen
            update_user(target.id, "embers", target_data["embers"])
            update_user(user_id, "embers", user_data["embers"])
            await ctx.send(f"**BETRAYAL!** you backstabbed {target.display_name} and stole **{stolen}** embers! cold blooded fam!")
        else:
            await ctx.send(f"you tried to betray {target.display_name} but they broke af. nothing to steal lol")
    else:
        fine = random.randint(50, 150)
        user_data["embers"] = max(0, user_data["embers"] - fine)
        update_user(user_id, "embers", user_data["embers"])
        await ctx.send(f"**EXPOSED!** {target.display_name} caught your betrayal attempt! the cult fined you **{fine}** embers! traitor lol")

@bot.command(name="tribute")
async def tribute(ctx, amount: int):
    if amount <= 0:
        await ctx.send("bruh you cant tribute nothing. the cult leader wants real embers lol")
        return
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    cult_name = user_data.get("cult")
    if not cult_name:
        await ctx.send("bruh youre not in a cult. join one first with `fcult <name>` lol")
        return
    if user_data["embers"] < amount:
        await ctx.send(f"you broke, only got **{user_data['embers']}** embers. cant tribute **{amount}**")
        return
    cult_info = settings_data.get("cults", {}).get(cult_name, {})
    leader_id = cult_info.get("leader")
    if leader_id == ctx.author.id:
        await ctx.send("bruh youre the cult leader. you cant tribute to yourself. thats just taxes lol")
        return
    user_data["embers"] -= amount
    cult_info["embers"] = cult_info.get("embers", 0) + amount
    leader_data = get_user_data(leader_id)
    leader_data["embers"] += amount // 2
    cult_info["embers"] -= amount // 2
    update_user(user_id, "embers", user_data["embers"])
    update_user(leader_id, "embers", leader_data["embers"])
    settings_data["cults"][cult_name] = cult_info
    save_data(SETTINGS_FILE, settings_data)
    await ctx.send(f"you paid **{amount}** embers in tribute to the **{cult_name}** cult! the leader takes their cut. cult tax baby!")

@bot.command(name="roast")
async def roast(ctx, target: discord.Member = None):
    target = target or ctx.author
    roasts = [
        f"{target.display_name} is so broke, they make beggars look rich",
        f"{target.display_name}'s combat rank is 'participation trophy'",
        f"{target.display_name} probably loses rock paper scissors to a wall",
        f"{target.display_name} is like a cloud. when they disappear, its a beautiful day",
        f"{target.display_name} is so slow, they got lapped by a snail in a race",
        f"{target.display_name}'s luck is so bad, theyd lose a 1-person raffle",
        f"{target.display_name} is the reason the gene pool needs a lifeguard",
        f"{target.display_name} probably thinks a heist is a type of sandwich",
        f"{target.display_name} is so bad at gambling, the house feels sorry for them",
        f"{target.display_name}'s creatures probably ask to be sacrificed"
    ]
    await ctx.send(random.choice(roasts))

@bot.command(name="confess")
async def confess(ctx, target: discord.Member, *, message: str):
    if target.id == ctx.author.id:
        await ctx.send("bro you cant confess to yourself. thats just journaling lol")
        return
    try:
        await target.send(f"**Anonymous Confession!** someone has a message for you: *{message}*")
        await ctx.send("confession sent anonymously! theyll never know it was you... unless they guess lol")
    except:
        await ctx.send("bruh their DMs are closed. cant confess if they wont listen lol")

@bot.command(name="meme")
async def meme(ctx):
    memes = [
        "https://i.imgur.com/1X2Y3Z4.jpg",
        "https://i.imgur.com/5A6B7C8.jpg",
        "https://i.imgur.com/9D0E1F2.jpg",
        "https://i.imgur.com/3G4H5I6.jpg",
        "https://i.imgur.com/7J8K9L0.jpg"
    ]
    embed = discord.Embed(title="Random Meme", color=discord.Color.random())
    embed.set_image(url=random.choice(memes))
    embed.set_footer(text="meme courtesy of the internet lol")
    await ctx.send(embed=embed)

@bot.command(name="joke")
async def joke(ctx):
    jokes = [
        "why did the programmer quit his job? because he didnt get arrays lol",
        "what do you call a fake noodle? an impasta",
        "why dont scientists trust atoms? because they make up everything",
        "i told my wife she was drawing her eyebrows too high. she looked surprised",
        "why do programmers prefer dark mode? because light attracts bugs",
        "what did the ocean say to the beach? nothing it just waved",
        "why did the scarecrow win an award? because he was outstanding in his field",
        "im reading a book about anti-gravity. its impossible to put down",
        "why dont skeletons fight each other? they dont have the guts",
        "what do you call a bear with no teeth? a gummy bear"
    ]
    await ctx.send(random.choice(jokes))

@bot.command(name="avatar")
async def avatar(ctx, user: discord.Member = None):
    user = user or ctx.author
    embed = discord.Embed(title=f"{user.display_name}'s Avatar", color=discord.Color.random())
    embed.set_image(url=user.display_avatar.url)
    embed.set_footer(text="nice pfp fam")
    await ctx.send(embed=embed)

@bot.command(name="userinfo")
async def userinfo(ctx, user: discord.Member = None):
    user = user or ctx.author
    embed = discord.Embed(title=f"{user.display_name} Info", color=discord.Color.blue())
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Username", value=user.name, inline=True)
    embed.add_field(name="ID", value=user.id, inline=True)
    embed.add_field(name="Created", value=user.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d") if user.joined_at else "Unknown", inline=True)
    embed.add_field(name="Top Role", value=user.top_role.mention, inline=True)
    embed.add_field(name="Bot?", value="Yes" if user.bot else "No", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="profile", aliases=["p"])
async def profile(ctx, user: discord.Member = None):
    user = user or ctx.author
    data = get_user_data(user.id)
    embed = discord.Embed(title=f"{user.display_name}'s Profile", color=discord.Color.orange())
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Embers", value=f"**{data['embers']:,}**", inline=True)
    embed.add_field(name="Items", value=f"**{len(data['inventory'])}**", inline=True)
    embed.add_field(name="Creatures", value=f"**{len(data.get('creatures', []))}**", inline=True)
    embed.add_field(name="Level", value=f"**{data.get('level', 1)}**", inline=True)
    embed.add_field(name="XP", value=f"**{data.get('xp', 0)}**", inline=True)
    embed.add_field(name="Combat Rank", value=f"**{data.get('combat_rank', 'Bronze')}**", inline=True)
    embed.add_field(name="Wins", value=f"**{data.get('wins', 0)}**", inline=True)
    embed.add_field(name="Losses", value=f"**{data.get('losses', 0)}**", inline=True)
    embed.add_field(name="Streak", value=f"**{data.get('streak', 0)}** days", inline=True)
    married_to = data.get("married_to")
    if married_to:
        partner = bot.get_user(married_to)
        partner_name = partner.display_name if partner else "Unknown"
        embed.add_field(name="Married To", value=partner_name, inline=True)
    cult = data.get("cult")
    if cult:
        embed.add_field(name="Cult", value=cult, inline=True)
    embed.set_footer(text=f"ID: {user.id}")
    await ctx.send(embed=embed)


# ============ UTILITY COMMANDS ============
@bot.command(name="tutorial")
async def tutorial(ctx):
    embed = discord.Embed(title="Flame Bot Tutorial", description="welcome to the flame fam! heres how to get started", color=discord.Color.blue())
    embed.add_field(name="Step 1: Get Embers", value="use `fdaily` every day to collect embers. dont break your streak!", inline=False)
    embed.add_field(name="Step 2: Work", value="use `fwork` to earn more embers through jobs", inline=False)
    embed.add_field(name="Step 3: Gamble", value="use `fgamble` or `fslots` to try to double your money (risky!)", inline=False)
    embed.add_field(name="Step 4: Creatures", value="use `fsummon` to get a creature, then `ffeed` it to keep it alive", inline=False)
    embed.add_field(name="Step 5: Combat", value="use `fduel` to fight other users and win embers", inline=False)
    embed.add_field(name="Step 6: Social", value="use `fmarry` to find love, `fcult` to join a group", inline=False)
    embed.add_field(name="Pro Tips", value="check `fhelp <category>` for detailed command info. use `fcooldowns` to see whats available", inline=False)
    embed.set_footer(text="good luck fam! get rich or die tryin")
    await ctx.send(embed=embed)
    user_data = get_user_data(ctx.author.id)
    user_data["tutorial_seen"] = True
    update_user(ctx.author.id, "tutorial_seen", True)

@bot.command(name="stats")
async def stats(ctx, user: discord.Member = None):
    user = user or ctx.author
    data = get_user_data(user.id)
    embed = discord.Embed(title=f"{user.display_name}'s Detailed Stats", color=discord.Color.blue())
    embed.add_field(name="Economy", value=f"Embers: {data['embers']:,} | Burned: {data.get('burned', 0):,} | Scammed: {data.get('scammed', 0):,} | Invested: {data.get('invested', 0):,} | Loan: {data.get('loan', 0):,}", inline=False)
    embed.add_field(name="Combat", value=f"Wins: {data.get('wins', 0)} | Losses: {data.get('losses', 0)} | Duels: {data.get('duels', 0)} | Raids: {data.get('raids', 0)} | Rank: {data.get('combat_rank', 'Bronze')}", inline=False)
    embed.add_field(name="Progression", value=f"Level: {data.get('level', 1)} | XP: {data.get('xp', 0)} | Streak: {data.get('streak', 0)} days", inline=False)
    married = "Yes" if data.get("married_to") else "No"
    embed.add_field(name="Social", value=f"Married: {married} | Cult: {data.get('cult', 'None')} | Will Set: {'Yes' if data.get('will') else 'No'}", inline=False)
    embed.add_field(name="Creatures", value=f"Owned: {len(data.get('creatures', []))} | Favorite: {data.get('favorite_creature', 'None')}", inline=False)
    embed.set_footer(text="grind dont stop fam!")
    await ctx.send(embed=embed)

@bot.command(name="server")
async def server(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"{guild.name} Server Info", color=discord.Color.orange())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Boosts", value=guild.premium_subscription_count or 0, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="global")
async def global_lb(ctx):
    sorted_users = sorted(embers_data.items(), key=lambda x: x[1]["embers"], reverse=True)[:20]
    embed = discord.Embed(title="Global Leaderboard", description="richest people across ALL servers", color=discord.Color.gold())
    for i, (user_id, data) in enumerate(sorted_users, 1):
        user = bot.get_user(int(user_id))
        name = user.display_name if user else f"User {user_id}"
        embed.add_field(name=f"#{i} {name}", value=f"**{data['embers']:,}** embers", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="settings")
async def settings_cmd(ctx, setting: str = None, value: str = None):
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    if not setting:
        embed = discord.Embed(title="Your Settings", color=discord.Color.blue())
        settings = user_data.get("settings", {"notifications": True, "dm_offers": True})
        embed.add_field(name="Notifications", value="On" if settings.get("notifications") else "Off", inline=True)
        embed.add_field(name="DM Offers", value="On" if settings.get("dm_offers") else "Off", inline=True)
        embed.set_footer(text="use `fsettings <setting> <on/off>` to change")
        await ctx.send(embed=embed)
        return
    setting = setting.lower()
    if setting not in ["notifications", "dm_offers"]:
        await ctx.send("bruh thats not a setting. available: `notifications`, `dm_offers`")
        return
    if value:
        value = value.lower()
        if value in ["on", "true", "yes"]:
            user_data["settings"][setting] = True
        elif value in ["off", "false", "no"]:
            user_data["settings"][setting] = False
        else:
            await ctx.send("bruh use `on` or `off`. not that hard lol")
            return
        update_user(user_id, "settings", user_data["settings"])
        await ctx.send(f"setting `{setting}` is now **{'On' if user_data['settings'][setting] else 'Off'}**!")
    else:
        current = user_data["settings"].get(setting, True)
        await ctx.send(f"`{setting}` is currently **{'On' if current else 'Off'}**")

@bot.command(name="cooldowns")
async def cooldowns_cmd(ctx):
    user_id = ctx.author.id
    now = datetime.now().timestamp()
    active_cds = []
    for key, timestamp in cooldowns_data.items():
        if key.startswith(f"{user_id}_"):
            cmd = key.replace(f"{user_id}_", "")
            elapsed = now - timestamp
            if elapsed < 86400:
                remaining = int(86400 - elapsed)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                active_cds.append(f"`{cmd}`: {hours}h {minutes}m")
    if not active_cds:
        await ctx.send("no active cooldowns! youre free to do everything fam!")
        return
    embed = discord.Embed(title="Your Cooldowns", description="heres what you gotta wait for", color=discord.Color.yellow())
    for cd in active_cds[:20]:
        parts = cd.split(": ")
        embed.add_field(name=parts[0], value=parts[1], inline=True)
    await ctx.send(embed=embed)

@bot.command(name="changelog")
async def changelog(ctx):
    embed = discord.Embed(title="Flame Bot Changelog", description="whats new in the latest update", color=discord.Color.green())
    embed.add_field(name="v2.0 - The Big One", value="Added ALL commands from the screenshot! New sections: Creatures, Combat, Gambling, Social, Utility, Weird. Heist system, Creature breeding, Combat ranking, Marriage and cult systems, Russian roulette, Vault cracking, Much more!", inline=False)
    embed.add_field(name="v1.5", value="Added gambling and slots. Added creature system. Added admin commands.", inline=False)
    embed.add_field(name="v1.0", value="Initial release with basic economy and fun commands.", inline=False)
    embed.set_footer(text="made by justaflamewithfragz")
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"{guild.name} Server Info", color=discord.Color.orange())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Boosts", value=guild.premium_subscription_count or 0, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    responses = [
        f"pong! {latency}ms - im fast asf boi",
        f"yo im here, {latency}ms response time",
        f"pong! {latency}ms - faster than your wifi probably lol",
        f"im awake fam, {latency}ms"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="uptime")
async def uptime(ctx):
    await ctx.send("ive been running for a while now, cant complain lol")


# ============ WEIRD COMMANDS ============
DREAMS = [
    "flying means you want freedom from your responsibilities",
    "falling means youre afraid of losing control",
    "being chased means youre avoiding something in real life",
    "teeth falling out means youre worried about your appearance",
    "being naked in public means you feel vulnerable",
    "finding money means good luck is coming",
    "dying means a new beginning is coming",
    "water means your emotions are flowing",
    "fire means passion or anger is burning inside",
    "animals mean your instincts are calling"
]

ORACLE_RESPONSES = [
    "the stars align in your favor today",
    "beware the ides of march... or any day really",
    "fortune favors the bold, but bankruptcy favors the gambler",
    "your future is cloudy, like your browser history",
    "great wealth awaits you... probably not tho",
    "love is around the corner. literally, check behind you",
    "a surprise visitor will bring news. probably just spam mail",
    "trust no one, especially not bots giving advice",
    "the answer you seek is 42. or maybe just 'try harder'",
    "your lucky number is the amount of embers you have"
]

LORE_PIECES = [
    "long ago, the first ember was forged in the fires of creation",
    "the flame bot was born from a single line of buggy code",
    "legend says the richest user will gain immortality... or just bragging rights",
    "creatures were once gods, now theyre just pets for embers",
    "the first cult was formed by users who kept losing at gambling",
    "some say the oracle is just random.randint in disguise",
    "the vault contains the secrets of the universe... and some spare change",
    "marriage was added because someone was lonely coding this",
    "the heist system exists because robbing one person wasnt enough",
    "dream interpretations are 100% accurate* (*not actually accurate)"
]

@bot.command(name="dream")
async def dream(ctx):
    user_id = ctx.author.id
    can_use, remaining = check_cd(user_id, "dream", 3600)
    if not can_use:
        await ctx.send(f"your dream crystal is still recharging. wait {remaining // 60}m")
        return
    dream_meaning = random.choice(DREAMS)
    await ctx.send(f"last night you dreamed of something... **{dream_meaning}**. deep stuff fam!")

@bot.command(name="curse")
async def curse(ctx, target: discord.Member):
    if target.id == ctx.author.id:
        await ctx.send("bro you cant curse yourself. thats just negative self-talk lol")
        return
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    target_data = get_user_data(target.id)
    can_use, remaining = check_cd(user_id, "curse", 3600)
    if not can_use:
        await ctx.send(f"your curse energy is depleted. wait {remaining // 60}m")
        return
    cost = 50
    if user_data["embers"] < cost:
        await ctx.send(f"cursing costs **{cost}** embers. you only got **{user_data['embers']}**. too broke to be evil lol")
        return
    user_data["embers"] -= cost
    target_data["cursed"] = True
    update_user(user_id, "embers", user_data["embers"])
    update_user(target.id, "cursed", True)
    curses = [
        f"**CURSED!** {target.display_name} has been cursed! their next gamble will definitely fail!",
        f"**DARK MAGIC!** {target.display_name} is now cursed! may their creatures rebel!",
        f"**HEX APPLIED!** {target.display_name} has been hexed! bad luck incoming!",
        f"**CURSE CAST!** {target.display_name} is cursed! their embers will mysteriously disappear!"
    ]
    await ctx.send(random.choice(curses))

@bot.command(name="bless")
async def bless(ctx, target: discord.Member):
    if target.id == ctx.author.id:
        await ctx.send("bro you cant bless yourself. thats just self-care lol")
        return
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    target_data = get_user_data(target.id)
    can_use, remaining = check_cd(user_id, "bless", 3600)
    if not can_use:
        await ctx.send(f"your blessing power is recharging. wait {remaining // 60}m")
        return
    cost = 50
    if user_data["embers"] < cost:
        await ctx.send(f"blessing costs **{cost}** embers. you only got **{user_data['embers']}**. too broke to be nice lol")
        return
    user_data["embers"] -= cost
    target_data["blessed"] = True
    target_data["cursed"] = False
    update_user(user_id, "embers", user_data["embers"])
    update_user(target.id, "blessed", True)
    update_user(target.id, "cursed", False)
    blessings = [
        f"**BLESSED!** {target.display_name} has been blessed! good luck on their next gamble!",
        f"**DIVINE FAVOR!** {target.display_name} is now blessed! may their creatures thrive!",
        f"**HOLY LIGHT!** {target.display_name} has been blessed! embers will flow to them!",
        f"**BLESSING GIVEN!** {target.display_name} is blessed! their heists will succeed!"
    ]
    await ctx.send(random.choice(blessings))

@bot.command(name="time")
async def time_cmd(ctx):
    now = datetime.now()
    await ctx.send(f"its **{now.strftime('%I:%M %p')}** right now. time to grind some embers fam!")

@bot.command(name="weather")
async def weather(ctx, *, location: str = "your location"):
    weathers = ["sunny", "rainy", "cloudy", "stormy", "snowy", "foggy", "windy", "perfect"]
    temp = random.randint(-10, 40)
    condition = random.choice(weathers)
    await ctx.send(f"weather in **{location}**: **{condition}** with **{temp}°C**. perfect day to stay inside and grind embers lol")

@bot.command(name="oracle")
async def oracle(ctx):
    user_id = ctx.author.id
    can_use, remaining = check_cd(user_id, "oracle", 1800)
    if not can_use:
        await ctx.send(f"the oracle is meditating. come back in {remaining // 60}m")
        return
    response = random.choice(ORACLE_RESPONSES)
    embed = discord.Embed(title="The Oracle Speaks", description=f"*{response}*", color=discord.Color.purple())
    embed.set_footer(text="the oracle is never wrong... usually")
    await ctx.send(embed=embed)

@bot.command(name="mimic")
async def mimic(ctx, target: discord.Member):
    if target.id == ctx.author.id:
        await ctx.send("bro you cant mimic yourself. thats just talking normally lol")
        return
    async for message in ctx.channel.history(limit=50):
        if message.author.id == target.id and message.content and not message.content.startswith("f"):
            await ctx.send(f"**{ctx.author.display_name} mimics {target.display_name}:** {message.content}")
            return
    await ctx.send(f"bruh {target.display_name} hasnt said anything recently. cant mimic silence lol")

@bot.command(name="glitch")
async def glitch(ctx):
    glitches = [
        "ERROR_404: reality not found",
        "SYSTEM_FAILURE: embers corrupted... just kidding lol",
        "GLITCH_DETECTED: you found a secret! ...nah just kidding",
        "MATRIX_BREACH: the simulation is breaking!",
        "DATA_CORRUPTION: your inventory has been... wait no its fine",
        "TIMELINE_ERROR: you werent supposed to see this command",
        "REALITY_GLITCH: everything is fine. everything is fine. everything is fine.",
        "CODE_OVERFLOW: too much awesomeness detected"
    ]
    await ctx.send(random.choice(glitches))

@bot.command(name="lore")
async def lore(ctx):
    piece = random.choice(LORE_PIECES)
    embed = discord.Embed(title="Bot Lore", description=f"*{piece}*", color=discord.Color.dark_purple())
    embed.set_footer(text="ancient wisdom from the flame archives")
    await ctx.send(embed=embed)

@bot.command(name="quit")
async def quit_cmd(ctx):
    user_id = ctx.author.id
    user_data = get_user_data(user_id)
    beneficiary_id = user_data.get("will")
    if beneficiary_id:
        beneficiary_data = get_user_data(beneficiary_id)
        inheritance = user_data["embers"]
        beneficiary_data["embers"] += inheritance
        user_data["embers"] = 0
        update_user(beneficiary_id, "embers", beneficiary_data["embers"])
        update_user(user_id, "embers", 0)
        beneficiary = bot.get_user(beneficiary_id)
        b_name = beneficiary.display_name if beneficiary else "Unknown"
        await ctx.send(f"**YOU QUIT!** you gave all your **{inheritance}** embers to **{b_name}**! thanks for playing fam! come back anytime!")
    else:
        await ctx.send("bruh you didnt set a will. use `fwill <@user>` first so someone gets your embers when you quit lol")

@bot.command(name="rps")
async def rps(ctx, choice: str):
    choice = choice.lower()
    if choice not in ["rock", "paper", "scissors"]:
        await ctx.send("bruh pick rock, paper, or scissors. those are the rules lol")
        return
    bot_choice = random.choice(["rock", "paper", "scissors"])
    beats = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
    if choice == bot_choice:
        result = "its a tie! boring"
    elif beats[choice] == bot_choice:
        result = "you win! nice one fam"
    else:
        result = "you lose! i got you lol"
    await ctx.send(f"you chose **{choice}**, i chose **{bot_choice}**. {result}")

# ============ ADMIN COMMANDS (OWNER ONLY) ============
@bot.command(name="give")
@is_owner()
async def give(ctx, amount: int, user: discord.Member):
    if amount <= 0:
        await ctx.send("bruh you cant give negative embers. what are you tryna do?")
        return
    data = get_user_data(user.id)
    data["embers"] += amount
    update_user(user.id, "embers", data["embers"])
    await ctx.send(f"gave **{amount:,}** embers to {user.display_name}. youre too generous fam")

@bot.command(name="set")
@is_owner()
async def set_embers(ctx, amount: int, user: discord.Member):
    if amount < 0:
        await ctx.send("nah fam cant set negative embers. that dont make sense")
        return
    data = get_user_data(user.id)
    data["embers"] = amount
    update_user(user.id, "embers", data["embers"])
    await ctx.send(f"set {user.display_name}'s embers to **{amount:,}**. big boss moves")

@bot.command(name="remove")
@is_owner()
async def remove(ctx, amount: int, user: discord.Member):
    if amount <= 0:
        await ctx.send("bruh you cant remove negative embers. think about it lol")
        return
    data = get_user_data(user.id)
    data["embers"] = max(0, data["embers"] - amount)
    update_user(user.id, "embers", data["embers"])
    await ctx.send(f"removed **{amount:,}** embers from {user.display_name}. tax season lol")

@bot.command(name="wipe")
@is_owner()
async def wipe(ctx, user: discord.Member):
    user_id = str(user.id)
    if user_id in embers_data:
        del embers_data[user_id]
        save_data(DATA_FILE, embers_data)
        await ctx.send(f"wiped all data for {user.display_name}. they starting from zero now lol")
    else:
        await ctx.send(f"{user.display_name} dont even have data to wipe. they never existed apparently")

# ============ RUN BOT ============
if __name__ == "__main__":
    bot.run(TOKEN)
