import os
import random
import requests
import asyncio
from datetime import datetime, timedelta
from pytz import timezone

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from botCommands.utils.utils import *
from botCommands.utils.redisutils import *
from botCommands.utils.tasks import *
from botCommands.utils.ConfigObjects import *

import discord
from discord.ext import commands
global daemonRunning
daemonRunning = False

WATERLOO_API_KEY = os.getenv("WATERLOO_API_KEY")
WATERLOO_API_URL = os.getenv("WATERLOO_API_URL")

section2List = ["saaliyan","a9ahluwa","yhahn","kalatras","d22an","n22arora","j24au","g4aujla","s3aulakh","mavolio","e2baek","x53bai","d22baker","nbeilis","j39bi","ebilaver","jbodner","a23bose","j24brar","j6braun","r6bui","gbylykba","achalakk","v5chaudh","ichellad","h596chen","ly23chen","h559chen","ncherish","jchik","jchitkar","skcho","kchoa","e25chu","nchunghu","m24coope","asdhiman","j3enrigh","derisogl","d24ferna","lfournie","n6franci","agabuniy","a57garg","mgionet","sgoodarz","c2gravel","m8guan","a324gupt","wharris","a29he","c55he","chenfrey","e44ho","rhoffman","p23hu","h338huan","l247huan","a73huang","a226jain","z242jian","h56jin","pkachhia","kkalathi","e2koh","k5kumara","jklkundn","k26le","j763lee","d267lee","k323lee","rlevesqu","a284li","r374li","k36liang","j352lu","b49lu","mlysenko","vmago","smanakta","j78marti","rhmayilv","a47mehta","d36mehta","a2mladen","d6moon","a27nadee","b42nguye","dnnnguye","b43nguye","m22niu","snuraniv","t5oliver","motchet","m332pate","v227pate","b36peng","bphu","npotdar","m98rahma","msraihaa","jrintjem","rrouhana","o3salem","apsalvad","s5santhi","hsayedal","tshahjah","s4shahri","r4sim","a553sing","a558sing","ll3smith","j225smit","kb2son","dsribala","tstauffe","a6su","ssubbara","m38syed","w29tam","c46tan","w4tao","s4thapa","ctraxler","etroci","a2vaseeh","j23vuong","d7wan","j23weng","t54wong","yy8wong","y657wu","j478wu","cy2xi","c7xiang","k233yang","j52yoon","i6zhang","cf3zhang","c624zhan","z963zhan"]
stream8List = ["mnabedin","msachuot","dm2adams","jaftab","s55agarw","s3agha","a2ahilan","a2aissao","aialam","talguind","h4altaf","aanavady","jsarbour","carjune","u3asif","js2bedi","m6begum","a4bello","mbenyahy","wbilal","dbown","bcarrion","c268chan","c465chen","sy36chen","s655chen","v22chen","w356chen","n9choi","bcimring","g3clarke","kcofini","mldai","sndave","gdecena","sdharask","cvdioned","y97du","k4dyck","nelgawis","yfahmi","j48fang","s34fang","a43ghosh","y95han","smhanif","s24hao","a39hasan","j223ho","r27ho","a36hu","t53hu","h328huan","y629huan","k25hung","k33huynh","njandala","jhjiao","d35jones","j2kambul","rkassama","s2kelash","h222khan","t54khan","nckhoras","dj6kim","k27le","j38lei","e44li","jy36li","jy26lin","r48lin","a229liu","ndliu","p99liu","sq3liu","z65luo","emach","b3mah","rmah","a3mahto","rmajeed","sdmajumd","a35malho","s73malik","r6mangat","amathise","dmehic","a47mehta","d2naik","sa6naqvi","mnasar","snavajee","h3ngai","j245nguy","s45oh","z2omer","mpanizza","aparasch","hn6patel","s23patha","t2pathan","m3pavlov","spetrevs","ehpropp","y2qie","q3qu","nquintan","a9rajkum","trampura","cj4rober","krogut","y3said","csariyil","f2sarker","ssenthur","a239shah","j36shah","r2shanbh","m85sharm","r43shi","y25singh","w5so","h77song","lxsong","134531.teststudent1","134531.teststudent2","vsudhaka","psurendr","ltahvild","me2tan","c223tang","s224tang","x29tao","dthero","jthota","k7to","etou","a2truong","evlahos","m6waheed","a242wang","s873wang","t384wang","yt24wang","h38wei","wwindhol","lhwu","p66wu","j59xiao","p9xie","y754yang","r22ye","zzyin","a56yu","t98yu","m27zafar","zzakiull","h664zhan","m375zhan","yz8zhang","z958zhan","w246zhao","b54zhu","mh2zhu"]
user_text_channels = [706657592578932800, 706659318883156069, 706659290072743977, 707029428043120721, 707017400226283570, 707028983346364447, 707029364511866890, 706658348522537041, 706658374221299742, 706658405875449868, 706658430819106847, 706658454252552323, 706658481683300383, 707777895745192017, 707777914594132019, 707777928137670666, 710408899336863805, 709975299059875872, 709975393167212614]
user_voice_channels = [706657592578932801,706659058115018863,706663233943109712,706659396146430002,707777965630554123,706658429892296714,706658540709740546,706658731697504286,706658766585724950,706658831437922396,706658925826801684]
whitelist_channel_names = ["faculty-general","create-a-ticket"]
lockdown_chat = ["lockdown-chat"]
ADMIN_CHANNEL_NAME = "bot-alerts"
awaitingSM = {}



# Administrative
class Administrative(commands.Cog, name='Administrative'):
    def __init__(self, bot):
        self.bot = bot
        # Not really sure what this does
        self._last_member_ = None



    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild

        adminChannel = getChannel(ADMIN_CHANNEL_NAME,guild)
        await adminChannel.send("A user: <@"+str(member.id)+"> has left the server.")
        db_purgeUser(member,guild)
        adminChannel.send("User has been purged from the database successfully.")


    @commands.Cog.listener()
    async def on_message(self, ctx):
        guild = ctx.author.guild
        pendingRole = getRole("pending",guild)
        pendingChannel = getChannel("pending",guild)

        if (ctx.author == self.bot.user or ctx.channel != pendingChannel or hasRoles(ctx.author,["Admin"],guild)): return

        try:
            watid = str(ctx.content)
            #TODO put in utils
            apiResponse = requests.get(WATERLOO_API_URL + watid + ".json?key=" + WATERLOO_API_KEY).json()
            name = apiResponse['data']['full_name']


            if (ctx.author.nick == name):
                user = ctx.author
                await pendingChannel.send("<@"+str(ctx.author.id)+"> Valid, you are now being re-validated.")
                try:

                    db_set(str(user.id) + ".watid", watid,guild)
                    await pendingChannel.send("WatID " + watid + " has been validated and correlated to <@" + str(user.id) + ">")
                    db_set(str(user) + ".name", name,guild)
                    await pendingChannel.edit(nick=name)
                    await pendingChannel.send(
                        "Name " + name + " has been validated and correlated to <@" + str(user.id) + ">")
                    db_set(watid, 1,guild)
                    await pendingChannel.send(
                        "The WatID " + watid + " has been marked for no further verifications.")


                    await pendingChannel.send("All tasks completed successfully")
                    await user.remove_roles(pendingRole)
                except Exception as e:
                    print(str(e))
                    await pendingChannel.send("There was an error validating you. <@&706658128409657366>")
            else:
                await pendingChannel.send("This is not you! If you think this is a mistake, please contact a member of the admin team.")


        except Exception as e:
            print(str(e))
            await pendingChannel.send("<@"+str(ctx.author.id)+"> That is not a valid WatID!")


    @commands.Cog.listener()
    async def on_ready(self):
        setGuilds(self.bot.guilds)
        print("Set the guilds to" + str(self.bot.guilds))
        print(f'{self.bot.user.name} has connected to Discord!')
        adminChannel = getChannel(ADMIN_CHANNEL_NAME, self.bot.guilds[0])
        global daemonRunning
        if not daemonRunning:
            daemonRunning = True
            for indv_guild in self.bot.guilds:
                asyncio.get_event_loop().create_task(AdministrativeThread(indv_guild))
                await adminChannel.send(str(indv_guild)+": The administrative daemon thread is now running.")
                print('Admin thread start')
                asyncio.get_event_loop().create_task(CommBroker(indv_guild))
                await adminChannel.send(str(indv_guild)+": The communications broker thread is now running.")
                print('Communications broker thread start')


    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        role = getRole("Unverified",guild)
        await member.add_roles(role)

    @commands.command()
    async def lock(self,ctx):
        channel = ctx.channel
        messageAuthor = ctx.author
        guild = ctx.author.guild

        #lol put it into a loop later
        guestRole = getRole("Guest",guild)
        sec1Role = getRole("Section 1",guild)
        sec2Role = getRole("Section 2",guild)
        verifiedRole = getRole("Verified",guild)
        regularRoles = [guestRole,sec1Role,sec2Role,verifiedRole]


        if (permittedAdmin(messageAuthor)):
            if (db_exists(str(channel.id)+".locked",guild)):
                for memberRole in regularRoles:
                    await channel.set_permissions(memberRole, send_messages=True, read_messages=True, read_message_history=True)
                await ctx.send("This channel has been unlocked. Sending messages is enabled again.")
                db_delete(str(channel.id)+".locked",guild)
            else:
                db_set(str(channel.id)+".locked",1,guild)
                for memberRole in regularRoles:
                    await channel.set_permissions(memberRole, send_messages=False, read_messages=True, read_message_history=True)
                await ctx.send("This channel has been locked. Sending messages is disabled.")

    @commands.command()
    async def verify(self, ctx, *args):
        try:
            messageAuthor = ctx.author
            guild = messageAuthor.guild
            watid = args[0]

            if (db_exists(str(messageAuthor) + ".request",guild) or db_exists(str(messageAuthor.id) + ".request",guild)):
                response = "<@" + str(
                    messageAuthor.id) + "> There is already a pending verification request for your WatID," \
                                        " please use `!confirm <code>` or do `!cancelverification`"
                await ctx.send(response)
                return
            # Ask UW API for information
            apiResponse = requests.get(WATERLOO_API_URL + watid + ".json?key=" + WATERLOO_API_KEY).json()
            email = apiResponse['data']['email_addresses'][0]
            name = apiResponse['data']['full_name']
            user_id = apiResponse['data']['user_id']
            # if (apiResponse['data']['department'] != "ENG/Electrical and Computer"):
            #     response = "<@" + str(
            #         messageAuthor.id) + "> You are not an ECE student!" \
            #                             " Please manually validate by contacting" \
            #                             " the admin team. The admin team has been" \
            #                             " notified of this incident. <@&706658128409657366>"
            #     await ctx.send(response)
            #     return
            if (len(apiResponse['data']['telephone_numbers']) > 0):
                response = "<@" + str(
                    messageAuthor.id) + "> You are a faculty member, and faculty members" \
                                        " require manual validation by an administrative team member." \
                                        " Please contact the administration team by messaging them directly," \
                                        " or send an email to k5kumara@uwaterloo.ca."
                await ctx.send(response)
                return

            try:
                if (db_exists(str(messageAuthor) + ".verified",guild) or db_exists(str(messageAuthor.id) + ".verified",guild)):
                    if (int(db_get(str(messageAuthor) + ".verified",guild)) == 1 or int(db_get(str(messageAuthor.id) + ".verified",guild)) == 1):
                        response = "<@" + str(messageAuthor.id) + "> You have already been verified"
                        await ctx.send(response)
                        return
            except:
                print("Lazy nullify error.")
            if (db_exists(str(user_id),guild)):
                if (int(db_get(str(user_id),guild)) == 1):
                    response = "<@" + str(
                        messageAuthor.id) + "> This user_id has already been verified. Not you? Contact an admin."
                    await ctx.send(response)
                    return

            # Mark
            db_set(str(messageAuthor.id) + ".watid", user_id,guild)
            db_set(str(messageAuthor.id) + ".verified", 0,guild)
            db_set(str(messageAuthor) + ".name", name,guild)
            db_set(str(messageAuthor.id) + ".name", name,guild)

            # Generate random code
            code = random.randint(1000, 9999)
            db_set(str(messageAuthor.id) + ".code", code,guild)

            mailMessage = Mail(
                from_email='verification@kaveenk.com',
                to_emails=email,
                subject='UWaterloo Helper Discord Verification Code',
                html_content='<strong>Your verification code is: ' + str(
                    code) + '. Please go back into discord and type !confirm (your code)</strong>')
            try:
                sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
                mailResponse = sg.send(mailMessage)
                # TODO: Validate mail response
            except Exception as e:
                print(str(e))
                await getChannel("bot-alerts", guild).send("ERROR: " + str(e))

            response = "<@" + str(
                messageAuthor.id) + "> I sent a verification code to " + email + ". Find the code" \
                                                                                 " in your email and type `!confirm <code>` in discord to verify" \
                                                                                 " your account. Please check your spam and junk folders."
            db_set(str(messageAuthor.id) + ".request", 1,guild)

            await ctx.send(response)
        except Exception as e:
            print(e)
            response = "<@" + str(
                messageAuthor.id) + "> No WatID provided or invalid watID, please use `!verify <watid>`." \
                                    " Your WatID is the username in your original email, for example, in " \
                                    " k5kumara@edu.uwaterloo.ca, the watID is k5kumara."
            await ctx.send(response)

    @commands.command()
    async def confirm(self, ctx, *args):
        try:
            messageAuthor = ctx.author
            guild = messageAuthor.guild

            code = args[0]

            if (db_exists(str(messageAuthor.id) + ".request",guild)):

                if (int(code) == int(db_get(str(messageAuthor.id)+".code",guild))):
                    response = "<@" + str(messageAuthor.id) + "> You were successfully verified."

                    await ctx.send(response)

                    nickname = db_get(str(messageAuthor.id) + ".name",guild)

                    await messageAuthor.edit(nick=str(nickname))

                    # Mark user and WatID as verified
                    db_set(str(messageAuthor.id) + ".verified", 1,guild)
                    db_set(str(db_get(str(messageAuthor.id) + ".watid",guild)), 1,guild)

                    if (db_exists(str(messageAuthor.id),guild)): db_delete(str(messageAuthor.id) + ".request",guild)
                    if (db_exists(str(messageAuthor),guild)): db_delete(str(messageAuthor) + ".request",guild)
                    # 706966831268626464
                    verifiedRole = getRole("Verified",guild)
                    unverifiedRole = getRole("Unverified",guild)
                    await messageAuthor.add_roles(verifiedRole)
                    await messageAuthor.remove_roles(unverifiedRole)

                    try:

                        sec2Role = getRole("Section 2",guild)
                        sec1Role = getRole("Section 1",guild)
                        stream8Role = getRole("Stream 8",guild)
                        watID = db_get(str(messageAuthor.id) + ".watid",guild)

                        adminChannel = getChannel(ADMIN_CHANNEL_NAME,guild)
                        await adminChannel.send("New verification on member join, the WatID for user <@" + str(messageAuthor.id) + "> is " + watID)
                        if (str(guild.id)  == "706657592578932797"):
                            if (watID in section2List):
                                await messageAuthor.add_roles(sec2Role)
                                await adminChannel.send("Added the Section 2 Role to <@" + str(messageAuthor.id) + ">.")
                            else:
                                try:
                                    await messageAuthor.add_roles(stream8Role)
                                    await adminChannel.send("Added the Section 1 Role to <@" + str(messageAuthor.id) + ">.")
                                except:
                                    print("User verified in non-main server")
                                    #Don't really do anything lol.
                    except Exception as e:
                        print(str(e))
                        await getChannel("bot-alerts", guild).send("ERROR: " + str(e))

                else:
                    response = "<@" + str(messageAuthor.id) + "> Invalid verification code."
                    await ctx.send(response)
            else:
                response = "<@" + str(
                    messageAuthor.id) + "> You do not have a pending verification request, " \
                                        "please use `!verify <WATID>` to start."
                await ctx.send(response)
        except Exception as e:
            print(e)
            await getChannel("bot-alerts", guild).send("ERROR: <@&706658128409657366>: " + str(e))
            response = "<@" + str(
                messageAuthor.id) + "> There was an error while verifying your user, or your code was invalid."
            await ctx.send(response)

    @commands.command()
    async def cancelverification(self, ctx):

        messageAuthor = ctx.author
        guild = messageAuthor.guild

        # 706966831268626464
        if (db_exists(str(messageAuthor.id) + ".request",guild)):
            db_delete(str(messageAuthor.id)+".request",guild)
            response = "<@" + str(
                messageAuthor.id) + "> Cancelled your on-going verification, please try again with `!verify <watid>`"
            await ctx.send(response)
        else:
            response = "<@" + str(messageAuthor.id) + "> You do not have a verification in progress"
            await ctx.send(response)

    @commands.command()
    async def devalidate(self, ctx, *args):

        messageAuthor = ctx.author
        guild = messageAuthor.guild
        if (permittedAdmin(messageAuthor)):
            try:
                selection = args[0]
                if (selection == "user"):
                    user = ctx.message.mentions[0]
                    db_purgeUser(user,guild)
                    await ctx.send("Purged user from database successfully.")

                elif (selection == "watid"):
                    watid = args[1]
                    db_unmarkWatID(watid,guild)
                    await ctx.send("Unmarked WatID " + watid)
                else:
                    await ctx.send("<@" + str(
                        messageAuthor.id) + "> Invalid selection! You can choose to devalidate a user or a WatID.")
            except Exception as e:
                ctx.send("<@" + str(
                    messageAuthor.id) + "> Invalid syntax or selection: `!devalidate <select 'user' or 'watid'> <value>`")

    #TODO This is absolute dogshit code that I wrote at 6am, make this way way better
    @commands.command()
    async def lockdown(self,ctx, *args):

        messageAuthor = ctx.author
        guild = messageAuthor.guild
        verifiedRole = getRole("Verified",guild)

        if (permittedAdmin(messageAuthor)):
            if (db_exists("lockdown",guild) == 0 or db_get("lockdown",guild) == "0"):

                db_set("lockdown", 1,guild)
                propagationMessage = await ctx.send("Cycling lockdown permissions to all text channels... Status: [0/"+str(len(messageAuthor.guild.text_channels))+"]")

                for counter, channel in enumerate(messageAuthor.guild.text_channels):

                    if (channel.name in lockdown_chat):
                        await channel.set_permissions(verifiedRole, send_messages=True,read_messages=True,read_message_history=True)
                        await channel.send(
                            "This server has temporarily gone into lockdown mode. This may be due to maintenance or due to a strict exam period. You may use this chat to chat freely until lockdown mode is lifted. All ticketing functionalities still work.")
                        continue

                    if (channel.id not in user_text_channels or channel.name == "create-a-ticket" or channel.category.name== "Open Tickets" or channel.category.name == "Closed Tickets"):
                        continue
                    await propagationMessage.edit(content="Cycling lockdown permissions to all channels... Status: ["+str(counter)+"/"+str(len(messageAuthor.guild.text_channels))+"]")
                    await channel.set_permissions(verifiedRole, send_messages=False,read_messages=False,read_message_history=False)
                await ctx.send("Finished cycling permissions to all text channels.")


                propagationMessage = await ctx.send(
                    "Cycling lockdown permissions to all voice channels... Status: [0/" + str(
                        len(messageAuthor.guild.voice_channels)) + "]")
                for counter,channel in enumerate(messageAuthor.guild.voice_channels):
                    if (channel.id not in user_voice_channels):
                        continue
                    await channel.set_permissions(verifiedRole, view_channel=False,connect=False)
                    await propagationMessage.edit(
                        content="Cycling lockdown permissions to all channels... Status: [" + str(counter) + "/" + str(
                            len(messageAuthor.guild.voice_channels)) + "]")
                await ctx.send("Cycled lockdown permissions to all voice channels.")
                await ctx.send("Lockdown mode enabled. Bot commands and user text chat has been disabled.")

            else:

                db_set("lockdown", 0,guild)
                propagationMessage = await ctx.send("Cycling to remove lockdown permissions from all text channels... Status: [0/" + str(
                    len(messageAuthor.guild.text_channels))+"]")
                counter = 0
                for channel in messageAuthor.guild.text_channels:
                    counter += 1
                    if (channel.name in lockdown_chat):
                        await channel.set_permissions(verifiedRole, send_messages=False,read_messages=False,read_message_history=False)

                        continue
                    if (channel.id not in user_text_channels or channel.name in whitelist_channel_names or channel.name == "create-a-ticket" or channel.category.name== "Open Tickets" or channel.category.name == "Closed Tickets"):
                        continue
                    await propagationMessage.edit(
                        content="Cycling to remove lockdown permissions from all text channels... Status: [" + str(counter) + "/" + str(
                            len(messageAuthor.guild.text_channels))+"]")
                    await channel.set_permissions(verifiedRole, send_messages=True,read_messages=True,read_message_history=True)
                await ctx.send("Finished cycling permissions to all text channels.")

                counter = 0
                propagationMessage = await ctx.send(
                    "Cycling lockdown permissions to all voice channels... Status: [0/" + str(
                        len(messageAuthor.guild.voice_channels)) + "]")
                for channel in messageAuthor.guild.voice_channels:
                    counter += 1
                    if (channel.id not in user_voice_channels):
                        continue
                    await channel.set_permissions(verifiedRole, view_channel=True,connect=True)
                    await propagationMessage.edit(
                        content="Cycling lockdown permissions to all channels... Status: [" + str(counter) + "/" + str(
                            len(messageAuthor.guild.voice_channels)) + "]")
                await ctx.send("Cycled lockdown permissions to all voice channels.")

                await ctx.send("Lockdown mode disabled. Bot commands and user text chat has been enabled again.")

        else:
            await ctx.send("You are not allowed to use this command!")
    @commands.command()
    async def correlate(self, ctx, *args):

        messageAuthor = ctx.author
        guild = messageAuthor.guild

        if (permittedAdmin(messageAuthor)):
            try:
                user = ctx.message.mentions[0]
                watid = args[1]

                try:
                    ranks = args[2]
                except:
                    await ctx.send("No ranks supplied, not applying any ranks.")
                    ranks = ""

                try:
                    apiResponse = requests.get(WATERLOO_API_URL + watid + ".json?key=" + WATERLOO_API_KEY).json()
                    name = apiResponse['data']['full_name']
                except:
                    await ctx.send("Invalid WatID: " + watid)
                    return

                db_set(str(user.id) + ".watid", watid,guild)
                await ctx.send("WatID " + watid + " has been validated and correlated to <@" + str(user.id) + ">")
                if ("Verified" in ranks):
                    db_set(str(user) + ".verified", 1,guild)
                    await ctx.send("<@" + str(user.id) + "> has been set to Verified status")
                db_set(str(user) + ".name", name,guild)
                await user.edit(nick=name)
                await ctx.send(
                    "Name " + name + " has been validated and correlated to <@" + str(user.id) + ">")
                db_set(watid, 1,guild)
                await ctx.send(
                    "The WatID " + watid + " has been marked for no further verifications.")

                # Set ranks

                if (permittedStaff(user)):
                    if ("Verified" in ranks or "Guest" in ranks):
                        await ctx.send(
                            "<@" + str(messageAuthor.id) + "> You may not apply your selected roles to this person.")
                        return
                try:
                    #TODO better way of doing this shit!
                    rank_array = ranks.split(",")
                    for rank in rank_array:
                        if (rank == ""): break
                        if ("_" in rank):
                            rank = rank.replace("_", " ")
                        rankToGive = discord.utils.get(ctx.message.guild.roles, name=rank.strip())

                        await user.add_roles(rankToGive)

                        await ctx.send("Added " + rank + " role to <@" + str(user.id) + ">")

                except Exception as e:

                    await user.add_roles(discord.utils.get(ctx.message.guild.roles, name=ranks.strip()))

                await ctx.send("All tasks completed successfully")
            except Exception as e:
                print(str(e))
                await getChannel("bot-alerts", guild).send("ERROR: " + str(e))
                await ctx.send("<@" + str(
                    messageAuthor.id) + "> You have entered invalid syntax, or the user you are trying to correlate is invalid. `!correlate <USER MENTION> <WatID>`")

    @commands.command()
    async def ldaplookup(self, ctx, *args):

        messageAuthor = ctx.author
        guild = messageAuthor.guild

        if (permittedAdmin(messageAuthor) or permittedStaff(messageAuthor)):
            try:

                watid = args[0]

                if ("@" in args[0]):

                    # Find user's discord tag
                    for member in ctx.message.mentions:
                        discordID = str(member.id)
                        watid = db_get(discordID + ".watid",guild)
                        break
                apiResponse = requests.get(WATERLOO_API_URL + watid + ".json?key=" + WATERLOO_API_KEY).json()

                embed = discord.Embed(title="LDAP Lookup",
                                      description="Here is an internal lookup by the University of Waterloo",
                                      color=0x800080)
                embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
                embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
                embed.add_field(name="Status",
                                value=apiResponse['meta']['message'],
                                inline=False)
                embed.add_field(name="Full Name",
                                value=apiResponse['data'][
                                    'full_name'],
                                inline=False)
                embed.add_field(name="Department",
                                value=apiResponse['data']['department'],
                                inline=False)
                embed.add_field(name="Common Names",
                                value=str(
                                    apiResponse['data']['common_names']),
                                inline=False)
                embed.add_field(name="Emails",
                                value=str(
                                    apiResponse['data']['email_addresses']),
                                inline=False)
                embed.add_field(name="Offices",
                                value=str(
                                    apiResponse['data']['offices']),
                                inline=False)
                embed.add_field(name="Phone Numbers",
                                value=str(
                                    apiResponse['data']['telephone_numbers']),
                                inline=False)

                if (apiResponse['data']['department'] == "ENG/Electrical and Computer"):
                    embed.add_field(name="Student Status",
                                    value="ECE Student",
                                    inline=False)
                else:
                    embed.add_field(name="Student Status",
                                    value="Not an ECE Student",
                                    inline=False)
                if (len(apiResponse['data']['telephone_numbers']) > 0):
                    embed.add_field(name="Student Status",
                                    value="NOT A STUDENT. MANUAL VALIDATION REQUIRED",
                                    inline=False)
                await ctx.send(embed=embed)
            except Exception as e:
                response = "Invalid WatID or no WatID provided"
                print(str(e))
                await ctx.send(response)
        else:
            response = "You are not allowed to use this command. Local Directory Access Protocol Lookups are restricted to Administrators"
            await ctx.send(response)

    @commands.command()
    async def validateroles(self, ctx):

        messageAuthor = ctx.author
        guild = messageAuthor.guild
        adminChannel = getChannel(ADMIN_CHANNEL_NAME,guild)

        if (permittedAdmin(messageAuthor)):
            section1Role = getRole("Section 1",guild)
            section2Role = getRole("Section 2",guild)
            verifiedRole = getRole("Verified",guild)
            teachingRole = getRole("Teaching Staff",guild)
            s8Role = getRole("Stream 8",guild)
            bot = getRole("Bot",guild)
            pending = getRole("Pending",guild)

            for member in stream(ctx.author.guild.members)\
                    .filter(lambda x: teachingRole not in x.roles and verifiedRole in x.roles and bot not in x.roles).\
                    to_list():

                try:
                    if (db_exists(str(member.id)+".watid",guild)):
                        # if (db_exists(str(member.id) + ".rolevalidated",guild)):
                        #     continue

                        await adminChannel.send("Analyzing user <@"+str(member.id)+">")
                        watID = db_get(str(member.id) + ".watid",guild)
                        await adminChannel.send("The WatID for user <@" + str(member.id) + "> is "+watID)

                        await member.remove_roles(section1Role)
                        await member.remove_roles(section2Role)
                        await member.remove_role(s8Role)
                        if (watID in section2List):
                            await member.add_roles(section2Role)
                            await adminChannel.send("Added the Section 2 Role to <@"+str(member.id)+">.")
                        elif watID in stream8List:
                            await member.add_roles(s8Role)
                            await adminChannel.send("Added the Stream 8 role to <@"+str(member.id)+">.")
                        else:
                            await member.add_roles(section1Role)
                            await adminChannel.send("Added the Section 1 Role to <@" + str(member.id) + ">.")
                        db_set(str(member.id)+".rolevalidated","true",guild)

                    else:
                        await member.add_roles(pending)
                        await adminChannel.send("<@&706658128409657366> There was no WatID for: <@" + str(
                            member.id) + "> please investigate.")

                except:
                    await adminChannel.send("<@&706658128409657366> There was an error retrieving the WatID for: <@"+str(member.id)+"> please investigate.")




            await ctx.send("All role validations completed successfully.")

    @commands.command()
    async def daemon(self, ctx):
        global daemonRunning
        messageAuthor = ctx.author
        if (permittedAdmin(messageAuthor)):
            if (daemonRunning == False):
                adminThread = asyncio.get_event_loop().create_task(AdministrativeThread(messageAuthor.guild))
                await ctx.send("The administrative daemon thread is now running.")
                daemonRunning = True
                await adminThread

            else:
                await ctx.send("The administrative daemon thread is already running!")
    @commands.command()
    async def testformatting(self, ctx, *args):
        messageAuthor = ctx.author
        if permittedAdmin(messageAuthor):

            message = " ".join(args)
            await ctx.send(message.replace("\\n","\n"))
    @commands.command()
    async def sm(self,ctx,*args):
        messageAuthor = ctx.author
        guild = messageAuthor.guild
        if permittedAdmin(messageAuthor):
            try:
                if (args[0].lower() == 'confirm'):
                    if (messageAuthor.id in awaitingSM):
                        await sendSubscriberMessage(awaitingSM[messageAuthor.id],guild)
                        del awaitingSM[messageAuthor.id]
                    else:
                        await ctx.send("You do not have a pending subscriber message to send out.")
                elif (args[0].lower() == 'cancel'):
                    if (messageAuthor.id in awaitingSM):
                        del awaitingSM[messageAuthor.id]
                        await ctx.send("Deleted your pending subscriber message request")
                    else:
                        await ctx.send("You do not have a pending subscriber message to cancel.")
                else:
                    if (messageAuthor.id not in awaitingSM):
                        message = " ".join(args)
                        message = message.replace("\"","'")
                        await ctx.send(message.replace("\\n", "\n"))
                        await ctx.send("This is a preview of the message you are about to send. To send, please type `!sm confirm`")
                        awaitingSM[messageAuthor.id] = message
                    else:
                        await ctx.send("You already have a pending subscriber message request. Please `!sm confirm` or `!sm cancel`")
            except Exception as e:
                print(e)
                await getChannel("bot-alerts", guild).send("ERROR: " + str(e))



    @commands.command()
    async def subscribers(self,ctx):
        messageAuthor = ctx.author
        guild = messageAuthor.guild
        if (permittedAdmin(messageAuthor)):
            embed = discord.Embed(title="Subscribed Members",
                                  description="Here is a list of all subscribed members",
                                  color=0x800080)
            embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
            embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")

            subscriberList = stream(messageAuthor.guild.members).filter(
                lambda x: db_exists(str(x.id) + ".subscribed",guild)
                          and db_get(str(x.id) + ".subscribed",guild) == "true").to_list()

            for page in paginate(map(str,subscriberList)):
                embed.add_field(name="Subscribed Members",value="\n".join(map(str,page)), inline=False)

            await ctx.send(embed=embed)
            await ctx.send("Total subscribers: "+str(len(subscriberList)))

    @commands.command()
    async def guest(self, ctx, *args):
        messageAuthor = ctx.author
        guild = messageAuthor.guild
        if (permittedAdmin(messageAuthor)):
            try:
                user = ctx.message.mentions[0]
                time = args[1]

                convertedTime = float(time) * 3600
                endDate = datetime.now() + timedelta(seconds=convertedTime)
                est = timezone('US/Eastern')
                endDate = endDate.astimezone(est)

                if (db_exists(str(user.id) + ".guestExpiry",guild)):
                    await ctx.send("This user is already a guest on this server!")
                else:

                    db_set(str(user.id) + ".guestExpiry", str(endDate),guild)
                    guestRole = getRole("Guest",guild)
                    verifiedRole = getRole("Verified",guild)
                    await user.add_roles(guestRole)
                    await user.add_roles(verifiedRole)
                    await ctx.send("Granted <@" + str(user.id) + "> temporary membership for " + str(time) + " hours.")
            except Exception as e:
                print(str(e))
                await getChannel("bot-alerts", guild).send("ERROR: " + str(e))
                await ctx.send("<@" + str(
                    messageAuthor.id) + " Invalid usage or an exception has occurred, please use: `!guest @MEMBER <time in hours>`")
