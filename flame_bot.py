import discord
from discord.ext import commands
import json
import os
import random
from datetime import datetime, timedelta

# Bot configuration
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "f"
OWNER_ID = 1444293963812180120

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Economy data storage
DATA_FILE = "embers_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Load data
embers_data = load_data()

def get_user_data(user_id):
    user_id = str(user_id)
    if user_id not in embers_data:
        embers_data[user_id] = {
            "embers": 0,
            "daily_last": None,
            "inventory": [],
            "rob_last": None,
            "work_last": None
        }
        save_data(embers_data)
    return embers_data[user_id]

def update_user_data(user_id, key, value):
    user_id = str(user_id)
    embers_data[user_id][key] = value
    save_data(embers_data)

# Cooldown tracking
cooldowns = {}

def check_cooldown(user_id, command, seconds):
    key = f"{user_id}_{command}"
    now = datetime.now()
    if key in cooldowns:
        elapsed = (now - cooldowns[key]).total_seconds()
        if elapsed < seconds:
            return False, seconds - int(elapsed)
    cooldowns[key] = now
    return True, 0

# Admin check decorator
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

# ==================== EVENTS ====================

@bot.event
async def on_ready():
    print(f"{bot.user.name} is online and blazing!")
    print(f"Bot ID: {bot.user.id}")
    print(f"Prefix: {PREFIX}")
    print("Ready to burn some embers!")
    await bot.change_presence(activity=discord.Game(name="fhelp | burning embers"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("yo youre missing some arguments there buddy, check fhelp")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("bruh that argument makes no sense, try again lol")
    else:
        print(f"Error: {error}")

# ==================== GENERAL COMMANDS ====================

@bot.command(name="help", aliases=["h"])
async def help_command(ctx):
    embed = discord.Embed(
        title="Flame Bot Commands",
        description="yo heres everything i can do",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Economy",
        value="""
        `fbalance` / `fbal` - check your embers
        `fdaily` - collect daily embers (24h cooldown)
        `fwork` - work for embers (1h cooldown)
        `frob @user` - rob someone (30min cooldown)
        `fshop` - view the shop
        `fbuy <item>` - buy something from shop
        `finventory` / `finv` - check your stuff
        `fleaderboard` / `flb` - richest people
        `fsend <amount> @user` - send embers to someone
        """,
        inline=False
    )

    embed.add_field(
        name="Fun",
        value="""
        `f8ball <question>` - ask the magic 8ball
        `froll <number>` - roll a dice
        `fmeme` - get a random meme
        `frps <rock/paper/scissors>` - rock paper scissors
        `fcoinflip` / `fcf` - flip a coin
        `fjoke` - get a random joke
        `frate <thing>` - rate something 1-10
        """,
        inline=False
    )

    embed.add_field(
        name="User",
        value="""
        `fprofile` / `fp` - your profile card
        `favatar @user` - get someones pfp
        `fuserinfo @user` - info about someone
        `fserverinfo` - server info
        `fping` - bot latency
        `fuptime` - how long ive been on
        """,
        inline=False
    )

    embed.add_field(
        name="Admin (Owner Only)",
        value="""
        `fgive <amount> @user` - give embers to someone
        `fset <amount> @user` - set someones embers
        `fremove <amount> @user` - remove embers from someone
        `fwipe @user` - wipe all their data
        """,
        inline=False
    )

    embed.set_footer(text="prefix is f btw | made by justaflamewithfragz")
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

# ==================== ECONOMY COMMANDS ====================

@bot.command(name="balance", aliases=["bal", "money", "embers"])
async def balance(ctx, user: discord.Member = None):
    user = user or ctx.author
    data = get_user_data(user.id)
    embers = data["embers"]

    embed = discord.Embed(
        title=f"{user.display_name}'s Embers",
        color=discord.Color.orange()
    )
    embed.add_field(name="Balance", value=f"**{embers:,}** embers", inline=False)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text="get rich or die tryin lol")

    await ctx.send(embed=embed)

@bot.command(name="daily")
async def daily(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)

    can_use, remaining = check_cooldown(user_id, "daily", 86400)
    if not can_use:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        await ctx.send(f"chill fam, you already got your daily. come back in {hours}h {minutes}m")
        return

    amount = random.randint(100, 500)
    data["embers"] += amount
    data["daily_last"] = datetime.now().isoformat()
    update_user_data(user_id, "embers", data["embers"])
    update_user_data(user_id, "daily_last", data["daily_last"])

    responses = [
        f"yo you got **{amount}** embers! nice",
        f"heres your **{amount}** embers, dont spend it all in one place lol",
        f"**{amount}** embers added to your stash. youre getting rich fam",
        f"daily dose of **{amount}** embers! come back tomorrow"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="work")
async def work(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)

    can_use, remaining = check_cooldown(user_id, "work", 3600)
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
    update_user_data(user_id, "embers", data["embers"])
    update_user_data(user_id, "work_last", data["work_last"])

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

    can_use, remaining = check_cooldown(user_id, "rob", 1800)
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
        update_user_data(user_id, "embers", robber_data["embers"])
        update_user_data(victim.id, "embers", victim_data["embers"])

        responses = [
            f"yo you robbed {victim.display_name} and got **{stolen}** embers! youre a criminal mastermind lol",
            f"successfully stole **{stolen}** embers from {victim.display_name}. dont tell nobody",
            f"**{stolen}** embers jacked from {victim.display_name}. smooth criminal over here",
            f"you got **{stolen}** embers from {victim.display_name}. crime pays apparently lol"
        ]
    else:
        fine = random.randint(50, 150)
        robber_data["embers"] -= fine
        update_user_data(user_id, "embers", robber_data["embers"])

        responses = [
            f"busted! you got caught and paid **{fine}** embers in fines. crime dont pay fam",
            f"{victim.display_name} caught you lacking and you lost **{fine}** embers. stick to honest work lol",
            f"robbery failed and you got fined **{fine}** embers. shouldve stayed in school",
            f"you tripped the alarm and lost **{fine}** embers. worst heist ever lol"
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

    # Confirmation message
    embed = discord.Embed(
        title="Are You Sure?",
        description=f"You about to send **{amount:,}** embers to {recipient.display_name}?",
        color=discord.Color.yellow()
    )
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
            update_user_data(ctx.author.id, "embers", sender_data["embers"])
            update_user_data(recipient.id, "embers", recipient_data["embers"])

            await ctx.send(f"sent **{amount:,}** embers to {recipient.display_name}! youre a real one")
        else:
            await ctx.send("transaction cancelled. keep your bag fam lol")

    except:
        await ctx.send("you took too long, transaction cancelled. indecisive much?")

@bot.command(name="shop")
async def shop(ctx):
    embed = discord.Embed(
        title="Embers Shop",
        description="spend your hard earned embers here",
        color=discord.Color.orange()
    )

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
    update_user_data(user_id, "embers", data["embers"])
    update_user_data(user_id, "inventory", data["inventory"])

    await ctx.send(f"yo you bought **{item_display}** for **{price:,}** embers! nice cop fam")

@bot.command(name="inventory", aliases=["inv"])
async def inventory(ctx, user: discord.Member = None):
    user = user or ctx.author
    data = get_user_data(user.id)
    items = data["inventory"]

    if not items:
        await ctx.send(f"{user.display_name} got nothing in their bag. broke boy hours lol")
        return

    embed = discord.Embed(
        title=f"{user.display_name}'s Inventory",
        color=discord.Color.orange()
    )

    for item in items:
        embed.add_field(name=item, value="owned", inline=False)

    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb", "rich", "top"])
async def leaderboard(ctx):
    sorted_users = sorted(embers_data.items(), key=lambda x: x[1]["embers"], reverse=True)[:10]

    embed = discord.Embed(
        title="Richest People",
        description="the ones who really got it",
        color=discord.Color.gold()
    )

    for i, (user_id, data) in enumerate(sorted_users, 1):
        user = bot.get_user(int(user_id))
        name = user.display_name if user else f"User {user_id}"
        medal = ["1st", "2nd", "3rd"][i-1] if i <= 3 else f"#{i}"
        embed.add_field(name=f"{medal} {name}", value=f"**{data['embers']:,}** embers", inline=False)

    await ctx.send(embed=embed)

# ==================== FUN COMMANDS ====================

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

    embed = discord.Embed(
        title="Magic 8-Ball",
        color=discord.Color.purple()
    )
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=random.choice(responses), inline=False)

    await ctx.send(embed=embed)

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

# ==================== USER COMMANDS ====================

@bot.command(name="profile", aliases=["p"])
async def profile(ctx, user: discord.Member = None):
    user = user or ctx.author
    data = get_user_data(user.id)

    embed = discord.Embed(
        title=f"{user.display_name}'s Profile",
        color=discord.Color.orange()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Embers", value=f"**{data['embers']:,}**", inline=True)
    embed.add_field(name="Items", value=f"**{len(data['inventory'])}**", inline=True)
    embed.add_field(name="Joined", value=user.joined_at.strftime("%Y-%m-%d") if user.joined_at else "Unknown", inline=True)
    embed.set_footer(text=f"ID: {user.id}")

    await ctx.send(embed=embed)

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

    embed = discord.Embed(
        title=f"{user.display_name} Info",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Username", value=user.name, inline=True)
    embed.add_field(name="ID", value=user.id, inline=True)
    embed.add_field(name="Created", value=user.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d") if user.joined_at else "Unknown", inline=True)
    embed.add_field(name="Top Role", value=user.top_role.mention, inline=True)
    embed.add_field(name="Bot?", value="Yes" if user.bot else "No", inline=True)

    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild

    embed = discord.Embed(
        title=f"{guild.name} Server Info",
        color=discord.Color.orange()
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Boosts", value=guild.premium_subscription_count or 0, inline=True)

    await ctx.send(embed=embed)

# ==================== ADMIN COMMANDS (OWNER ONLY) ====================

@bot.command(name="give")
@is_owner()
async def give(ctx, amount: int, user: discord.Member):
    if amount <= 0:
        await ctx.send("bruh you cant give negative embers. what are you tryna do?")
        return

    data = get_user_data(user.id)
    data["embers"] += amount
    update_user_data(user.id, "embers", data["embers"])

    await ctx.send(f"gave **{amount:,}** embers to {user.display_name}. youre too generous fam")

@bot.command(name="set")
@is_owner()
async def set_embers(ctx, amount: int, user: discord.Member):
    if amount < 0:
        await ctx.send("nah fam cant set negative embers. that dont make sense")
        return

    data = get_user_data(user.id)
    data["embers"] = amount
    update_user_data(user.id, "embers", data["embers"])

    await ctx.send(f"set {user.display_name}'s embers to **{amount:,}**. big boss moves")

@bot.command(name="remove")
@is_owner()
async def remove(ctx, amount: int, user: discord.Member):
    if amount <= 0:
        await ctx.send("bruh you cant remove negative embers. think about it lol")
        return

    data = get_user_data(user.id)
    data["embers"] = max(0, data["embers"] - amount)
    update_user_data(user.id, "embers", data["embers"])

    await ctx.send(f"removed **{amount:,}** embers from {user.display_name}. tax season lol")

@bot.command(name="wipe")
@is_owner()
async def wipe(ctx, user: discord.Member):
    user_id = str(user.id)
    if user_id in embers_data:
        del embers_data[user_id]
        save_data(embers_data)
        await ctx.send(f"wiped all data for {user.display_name}. they starting from zero now lol")
    else:
        await ctx.send(f"{user.display_name} dont even have data to wipe. they never existed apparently")

# ==================== COOL EXTRA COMMANDS ====================

@bot.command(name="beg")
async def beg(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)

    can_use, remaining = check_cooldown(user_id, "beg", 300)
    if not can_use:
        await ctx.send(f"bruh you just begged, have some dignity. wait {remaining}s")
        return

    if random.random() < 0.6:
        amount = random.randint(1, 50)
        data["embers"] += amount
        update_user_data(user_id, "embers", data["embers"])

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
        update_user_data(user_id, "embers", data["embers"])

        responses = [
            f"YO YOU WON! got **{winnings}** embers! youre on fire fam",
            f"**{winnings}** embers! the house lost this time lol",
            f"big W! **{winnings}** embers added. dont get addicted now",
            f"you doubled up to **{winnings}** embers! quit while youre ahead"
        ]
    else:
        data["embers"] -= amount
        update_user_data(user_id, "embers", data["embers"])

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
        update_user_data(user_id, "embers", data["embers"])
        msg = result_str + chr(10) + "**JACKPOT!** You won **" + str(winnings) + "** embers! youre literally rich now"
        await ctx.send(msg)
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        winnings = amount * 2
        data["embers"] += winnings
        update_user_data(user_id, "embers", data["embers"])
        msg = result_str + chr(10) + "Nice! Two matches! You got **" + str(winnings) + "** embers back"
        await ctx.send(msg)
    else:
        update_user_data(user_id, "embers", data["embers"])
        msg = result_str + chr(10) + "Nothing matched. Lost **" + str(amount) + "** embers. better luck next time lol"
        await ctx.send(msg)

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)
