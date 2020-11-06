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

# These are only for the ECE 2024 server! The only possible way that we found to automatically assign sections and streams.
section2List = ["saaliyan","a9ahluwa","yhahn","kalatras","d22an","n22arora","j24au","g4aujla","s3aulakh","mavolio","e2baek","x53bai","d22baker","nbeilis","j39bi","ebilaver","jbodner","a23bose","j24brar","j6braun","r6bui","gbylykba","achalakk","v5chaudh","ichellad","h596chen","ly23chen","h559chen","ncherish","jchik","jchitkar","skcho","kchoa","e25chu","nchunghu","m24coope","asdhiman","j3enrigh","derisogl","d24ferna","lfournie","n6franci","agabuniy","a57garg","mgionet","sgoodarz","c2gravel","m8guan","a324gupt","wharris","a29he","c55he","chenfrey","e44ho","rhoffman","p23hu","h338huan","l247huan","a73huang","a226jain","z242jian","h56jin","pkachhia","kkalathi","e2koh","k5kumara","jklkundn","k26le","j763lee","d267lee","k323lee","rlevesqu","a284li","r374li","k36liang","j352lu","b49lu","mlysenko","vmago","smanakta","j78marti","rhmayilv","a47mehta","d36mehta","a2mladen","d6moon","a27nadee","b42nguye","dnnnguye","b43nguye","m22niu","snuraniv","t5oliver","motchet","m332pate","v227pate","b36peng","bphu","npotdar","m98rahma","msraihaa","jrintjem","rrouhana","o3salem","apsalvad","s5santhi","hsayedal","tshahjah","s4shahri","r4sim","a553sing","a558sing","ll3smith","j225smit","kb2son","dsribala","tstauffe","a6su","ssubbara","m38syed","w29tam","c46tan","w4tao","s4thapa","ctraxler","etroci","a2vaseeh","j23vuong","d7wan","j23weng","t54wong","yy8wong","y657wu","j478wu","cy2xi","c7xiang","k233yang","j52yoon","i6zhang","cf3zhang","c624zhan","z963zhan"]
stream8List = ["mnabedin","msachuot","dm2adams","jaftab","s55agarw","s3agha","a2ahilan","a2aissao","aialam","talguind","h4altaf","aanavady","jsarbour","carjune","u3asif","js2bedi","m6begum","a4bello","mbenyahy","wbilal","dbown","bcarrion","c268chan","c465chen","sy36chen","s655chen","v22chen","w356chen","n9choi","bcimring","g3clarke","kcofini","mldai","sndave","gdecena","sdharask","cvdioned","y97du","k4dyck","nelgawis","yfahmi","j48fang","s34fang","a43ghosh","y95han","smhanif","s24hao","a39hasan","j223ho","r27ho","a36hu","t53hu","h328huan","y629huan","k25hung","k33huynh","njandala","jhjiao","d35jones","j2kambul","rkassama","s2kelash","h222khan","t54khan","nckhoras","dj6kim","k27le","j38lei","e44li","jy36li","jy26lin","r48lin","a229liu","ndliu","p99liu","sq3liu","z65luo","emach","b3mah","rmah","a3mahto","rmajeed","sdmajumd","a35malho","s73malik","r6mangat","amathise","dmehic","a47mehta","d2naik","sa6naqvi","mnasar","snavajee","h3ngai","j245nguy","s45oh","z2omer","mpanizza","aparasch","hn6patel","s23patha","t2pathan","m3pavlov","spetrevs","ehpropp","y2qie","q3qu","nquintan","a9rajkum","trampura","cj4rober","krogut","y3said","csariyil","f2sarker","ssenthur","a239shah","j36shah","r2shanbh","m85sharm","r43shi","y25singh","w5so","h77song","lxsong","134531.teststudent1","134531.teststudent2","vsudhaka","psurendr","ltahvild","me2tan","c223tang","s224tang","x29tao","dthero","jthota","k7to","etou","a2truong","evlahos","m6waheed","a242wang","s873wang","t384wang","yt24wang","h38wei","wwindhol","lhwu","p66wu","j59xiao","p9xie","y754yang","r22ye","zzyin","a56yu","t98yu","m27zafar","zzakiull","h664zhan","m375zhan","yz8zhang","z958zhan","w246zhao","b54zhu","mh2zhu"]

VERBOSE_CHANNEL_NAME = "bot-alerts"
awaitingSM = {}
THUMBNAIL_LINK = "https://i.imgur.com/Uusxfqa.png"



# Administrative
class Administrative(commands.Cog, name='Administrative'):
    def __init__(self, bot):
        self.bot = bot
        self._last_member_ = None

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild

        adminChannel = getChannel(VERBOSE_CHANNEL_NAME, guild)
        await adminChannel.send("A user: <@"+str(member.id)+"> has left the server.")
        db_purgeUser(member,guild)
        adminChannel.send("User has been purged from the database successfully.")

    @commands.Cog.listener()
    async def on_ready(self):
        setGuilds(self.bot.guilds)
        print("Set the guilds to" + str(self.bot.guilds))
        print(f'{self.bot.user.name} has connected to Discord!')
        global daemonRunning
        if not daemonRunning:
            daemonRunning = True
            for indv_guild in self.bot.guilds:
                adminChannel = getChannel(VERBOSE_CHANNEL_NAME, indv_guild)
                asyncio.get_event_loop().create_task(AdministrativeThread(indv_guild))
                await adminChannel.send(str(indv_guild)+": The administrative daemon thread is now running.")
                print('Admin thread start')
                asyncio.get_event_loop().create_task(CommBroker(indv_guild))
                await adminChannel.send(str(indv_guild)+": The communications broker thread is now running.")
                print('Communications broker thread start')


    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        try:
            role = getRole("Unverified",guild)
            await member.add_roles(role)
        except:
            pass


    @commands.command()
    async def lock(self,ctx):
        channel = ctx.channel
        messageAuthor = ctx.author
        guild = ctx.author.guild

        verifiedRole = getRole("Verified",guild)
        regularRoles = [verifiedRole]

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

            #Check if there exists a pending verification request already
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

            #If a WatID has a phone number associated with it, they are most likely a member of faculty. Deny auto-verification in that case.
            if (len(apiResponse['data']['telephone_numbers']) > 0):
                response = "<@" + str(
                    messageAuthor.id) + "> You are a faculty member, and faculty members" \
                                        " require manual validation by an administrative team member." \
                                        " Please contact the administration team by messaging them directly," \
                                        " or send an email to k5kumara@uwaterloo.ca."
                await ctx.send(response)
                return

            #Check if the user has already been verified
            try:
                if (db_exists(str(messageAuthor) + ".verified",guild) or db_exists(str(messageAuthor.id) + ".verified",guild)):
                    if (int(db_get(str(messageAuthor) + ".verified",guild)) == 1 or int(db_get(str(messageAuthor.id) + ".verified",guild)) == 1):
                        response = "<@" + str(messageAuthor.id) + "> You have already been verified"
                        await ctx.send(response)
                        return
            except:
                pass


            #Check if the attempted WatID has already been verified.
            if (db_exists(str(user_id),guild)):
                if (int(db_get(str(user_id),guild)) == 1):
                    response = "<@" + str(
                        messageAuthor.id) + "> This user_id has already been verified. Not you? Contact an admin."
                    await ctx.send(response)
                    return

            #Check for verifications on another server
            userInfo = search(messageAuthor.id, self.bot.guilds)
            print(str(userInfo))

            #Not verified on another server, run the normal process
            if not userInfo["status"]:
                # Mark
                db_set(str(messageAuthor.id) + ".watid", user_id, guild)
                db_set(str(messageAuthor.id) + ".verified", 0, guild)
                db_set(str(messageAuthor) + ".name", name, guild)
                db_set(str(messageAuthor.id) + ".name", name, guild)

                # Generate random code
                code = random.randint(1000, 9999)
                db_set(str(messageAuthor.id) + ".code", code, guild)

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
                    await getChannel(VERBOSE_CHANNEL_NAME, guild).send("ERROR: " + str(e))

                response = "<@" + str(
                    messageAuthor.id) + "> I sent a verification code to " + email + ". Find the code" \
                                                                                     " in your email and type `!confirm <code>` in discord to verify" \
                                                                                     " your account. Please check your spam and junk folders."
                db_set(str(messageAuthor.id) + ".request", 1, guild)

                await ctx.send(response)

            #Verified on another server, automatically verify them here without any action on their part!
            elif userInfo["status"]:
                # Set their records on the current server to the records provided by another server
                db_set(str(messageAuthor.id) + ".verified", 1, guild)
                db_set(userInfo["watID"], 1, guild)
                db_set(str(messageAuthor.id) + ".watid", userInfo["watID"], guild)
                db_set(str(messageAuthor) + ".name", userInfo["name"], guild)
                db_set(str(messageAuthor.id) + ".name", userInfo["name"], guild)
                if (forceName(guild)):
                    await messageAuthor.edit(nick=str(userInfo["name"]))

                # Add Verified role, attempt to remove Unverified Role
                verifiedRole = getRole("Verified", guild)
                await messageAuthor.add_roles(verifiedRole)
                try:
                    unverifiedRole = getRole("Unverified", guild)
                    await messageAuthor.remove_roles(unverifiedRole)
                except:
                    pass

                await send_dm(messageAuthor, "Hi there, "+userInfo["name"]+", you recently tried to verify on the discord server "+messageAuthor.guild.name+", but we found a previous verification for you on the server "+userInfo["guild"]+" so we have automatically verified your account this time :)")
                response = "<@" + str(
                    messageAuthor.id) + "> You have been automatically verified from another server"
                await ctx.send(response)
                return

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

                #Check if entered code matches code stored in redis
                if (int(code) == int(db_get(str(messageAuthor.id)+".code",guild))):

                    response = "<@" + str(messageAuthor.id) + "> You were successfully verified."
                    await ctx.send(response)

                    #Set user's nickname to real name on file
                    if (forceName(guild)):
                        nickname = db_get(str(messageAuthor.id) + ".name", guild)
                        await messageAuthor.edit(nick=str(nickname))

                    # Mark user and WatID as verified
                    db_set(str(messageAuthor.id) + ".verified", 1,guild)
                    db_set(str(db_get(str(messageAuthor.id) + ".watid",guild)), 1,guild)

                    #Unmark them as in-progress
                    if (db_exists(str(messageAuthor.id),guild)): db_delete(str(messageAuthor.id) + ".request",guild)
                    if (db_exists(str(messageAuthor),guild)): db_delete(str(messageAuthor) + ".request",guild)

                    #Add Verified role, attempt to remove Unverified Role
                    verifiedRole = getRole("Verified",guild)
                    await messageAuthor.add_roles(verifiedRole)
                    try:
                        unverifiedRole = getRole("Unverified",guild)
                        await messageAuthor.remove_roles(unverifiedRole)
                    except:
                        pass

                    try:

                        sec2Role = getRole("Section 2",guild)
                        sec1Role = getRole("Section 1",guild)
                        stream8Role = getRole("Stream 8",guild)
                        watID = db_get(str(messageAuthor.id) + ".watid",guild)

                        adminChannel = getChannel(VERBOSE_CHANNEL_NAME, guild)
                        await adminChannel.send("New verification on member join, the WatID for user <@" + str(messageAuthor.id) + "> is " + watID)

                        #This is only for the BUGS server, add a verified-science role if they are in science!
                        if (str(guild.id) == "707632982961160282"):
                            apiResponse = requests.get(WATERLOO_API_URL + watID + ".json?key=" + WATERLOO_API_KEY).json()
                            if (apiResponse['data']['department'] == "SCI/Science"):
                                await messageAuthor.add_roles(getRole("Verified-Science",guild))
                                await adminChannel.send("Added the Verified-Science Role to <@" + str(messageAuthor.id) + ">.")

                        #Only add sections if the server is the ECE 2024 server!
                        if (str(guild.id)  == "706657592578932797"):
                            if (watID in section2List):
                                await messageAuthor.add_roles(sec2Role)
                                await adminChannel.send("Added the Section 2 Role to <@" + str(messageAuthor.id) + ">.")
                            else:
                                await messageAuthor.add_roles(stream8Role)
                                await adminChannel.send("Added the Section 1 Role to <@" + str(messageAuthor.id) + ">.")


                    except Exception as e:
                        print(str(e))
                        await getChannel(VERBOSE_CHANNEL_NAME, guild).send("ERROR: " + str(e))

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
            await getChannel(VERBOSE_CHANNEL_NAME, guild).send("ERROR: <@&706658128409657366>: " + str(e))
            response = "<@" + str(
                messageAuthor.id) + "> There was an error while verifying your user, or your code was invalid."
            await ctx.send(response)

    @commands.command()
    async def cancelverification(self, ctx):

        messageAuthor = ctx.author
        guild = messageAuthor.guild

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

    @commands.command()
    async def lockdown(self,ctx, *args):
        print("TODO: TO BE REWRITTEN")

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
                    try:
                        await user.remove_roles(getRole("Unverified",guild))
                    except:
                        pass
                    await ctx.send("<@" + str(user.id) + "> has been set to Verified status")

                db_set(str(user) + ".name", name,guild)
                await user.edit(nick=name)
                await ctx.send(
                    "Name " + name + " has been validated and correlated to <@" + str(user.id) + ">")
                db_set(watid, 1,guild)
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
                await getChannel(VERBOSE_CHANNEL_NAME, guild).send("ERROR: " + str(e))
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
                embed.set_footer(text="https://github.com/Kav-K/Stream4Bot")
                embed.set_thumbnail(url=THUMBNAIL_LINK)
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
        #ONLY FOR USE ON THE ECE 2024 SERVER!
        if (str(ctx.author.guild.id) != "706657592578932797"):
            return

        messageAuthor = ctx.author
        guild = messageAuthor.guild
        adminChannel = getChannel(VERBOSE_CHANNEL_NAME, guild)

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
                        try:
                            await member.remove_roles(section1Role)
                            await member.remove_roles(section2Role)
                            await member.remove_role(s8Role)
                        except:
                            pass
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
                await getChannel(VERBOSE_CHANNEL_NAME, guild).send("ERROR: " + str(e))

    @commands.command()
    async def subscribers(self,ctx):
        messageAuthor = ctx.author
        guild = messageAuthor.guild
        if (permittedAdmin(messageAuthor)):
            embed = discord.Embed(title="Subscribed Members",
                                  description="Here is a list of all subscribed members",
                                  color=0x800080)
            embed.set_footer(text="https://github.com/Kav-K/Stream4Bot")
            embed.set_thumbnail(url=THUMBNAIL_LINK)

            subscriberList = stream(messageAuthor.guild.members).filter(
                lambda x: db_exists(str(x.id) + ".subscribed",guild)
                          and db_get(str(x.id) + ".subscribed",guild) == "true").to_list()
            print(str(subscriberList))
            for page in paginate(map(str,subscriberList)):
                print(str(page))
                embed.add_field(name="Subscribed Members",value="\n".join(map(str,page)), inline=False)

            await ctx.send(embed=embed)
            await ctx.send("Total subscribers: "+str(len(subscriberList)))

#Toggle if a server should force name changes or not
    @commands.command()
    async def config(self,ctx, *args):
        try:
            configOption = ConfigObjects[args[0]]
            configValue = args[1]

        except Exception as e:
            await ctx.send("Invalid syntax or configuration object: "+str(e))

        try:
            setConfigurationValue(configOption,configValue,ctx.author.guild)
            await ctx.send("Configuration value changed successfully")
        except Exception as e:
            await ctx.send("Internal error while changing configuration value: "+str(e))


#https://api.github.com/repos/Kav-K/Stream4Bot/commits
    @commands.command()
    async def dev(self,ctx):
        if (permittedAdmin(ctx.author)):
            import requests
            #Get information about last commit
            res = requests.get("https://api.github.com/repos/Kav-K/Stream4Bot/commits").json()
            commitAuthor = res[0]["commit"]["author"]["name"]
            commitMessage = res[0]["commit"]["message"]
            commitURL = res[0]["commit"]["url"]
            embed = discord.Embed(title="Developer Information",
                                      description="Internal information",
                                      color=0x800080)
            embed.set_footer(text="https://github.com/Kav-K/Stream4Bot")
            embed.set_thumbnail(url=THUMBNAIL_LINK)
            embed.add_field(name="Redis Instance",
                            value=str(getCorrespondingDatabase(ctx.author.guild)),
                            inline=False)
            embed.add_field(name="Last Commit",
                            value=commitURL,
                            inline=False)
            embed.add_field(name="Last Commit Author",
                            value=commitAuthor,
                            inline=False)
            embed.add_field(name="Last Commit Message",
                            value=commitMessage,
                            inline=False)
            await ctx.send(embed=embed)



