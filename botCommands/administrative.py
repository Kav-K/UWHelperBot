import random
import redis
import requests
import json
import asyncio
from datetime import datetime, timedelta
from pytz import timezone
from lazy_streams import stream

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from botCommands.utils import *

import discord
from discord.ext import commands
import pytz
#We gotta do some bullshit because discord calls are all async and we cant immediately start the daemon thread
#on startup without any context from discord :(
global daemonRunning
daemonRunning = False


WATERLOO_API_KEY = "21573cf6bf679cdfb5eb47b51033daac"
WATERLOO_API_URL = "https://api.uwaterloo.ca/v2/directory/"

redisClient = redis.Redis(host='localhost', port=6379, db=0)

TOKEN = "NzA2Njc4Mzk2MzEwMjU3NzI1.Xq9v2A.iCXfvgwxz4fnmlrRUvTlA_JnSTA"
section2List = ["saaliyan","a9ahluwa","yhahn","kalatras","d22an","n22arora","j24au","g4aujla","s3aulakh","mavolio","e2baek","x53bai","d22baker","nbeilis","j39bi","ebilaver","jbodner","a23bose","j24brar","j6braun","r6bui","gbylykba","achalakk","v5chaudh","ichellad","h596chen","ly23chen","h559chen","ncherish","jchik","jchitkar","skcho","kchoa","e25chu","nchunghu","m24coope","asdhiman","j3enrigh","derisogl","d24ferna","lfournie","n6franci","agabuniy","a57garg","mgionet","sgoodarz","c2gravel","m8guan","a324gupt","wharris","a29he","c55he","chenfrey","e44ho","rhoffman","p23hu","h338huan","l247huan","a73huang","a226jain","z242jian","h56jin","pkachhia","kkalathi","e2koh","k5kumara","jklkundn","k26le","j763lee","d267lee","k323lee","rlevesqu","a284li","r374li","k36liang","j352lu","b49lu","mlysenko","vmago","smanakta","j78marti","rhmayilv","a47mehta","d36mehta","a2mladen","d6moon","a27nadee","b42nguye","dnnnguye","b43nguye","m22niu","snuraniv","t5oliver","motchet","m332pate","v227pate","b36peng","bphu","npotdar","m98rahma","msraihaa","jrintjem","rrouhana","o3salem","apsalvad","s5santhi","hsayedal","tshahjah","s4shahri","r4sim","a553sing","a558sing","ll3smith","j225smit","kb2son","dsribala","tstauffe","a6su","ssubbara","m38syed","w29tam","c46tan","w4tao","s4thapa","ctraxler","etroci","a2vaseeh","j23vuong","d7wan","j23weng","t54wong","yy8wong","y657wu","j478wu","cy2xi","c7xiang","k233yang","j52yoon","i6zhang","cf3zhang","c624zhan","z963zhan"]
user_text_channels = [706657592578932800, 706659318883156069, 706659290072743977, 707029428043120721, 707017400226283570, 707028983346364447, 707029364511866890, 706658348522537041, 706658374221299742, 706658405875449868, 706658430819106847, 706658454252552323, 706658481683300383, 707777895745192017, 707777914594132019, 707777928137670666, 710408899336863805, 709975299059875872, 709975393167212614]
user_voice_channels = [706657592578932801,706659058115018863,706663233943109712,706659396146430002,707777965630554123,706658429892296714,706658540709740546,706658731697504286,706658766585724950,706658831437922396,706658925826801684]
whitelist_channel_names = ["faculty-general","create-a-ticket"]
lockdown_chat = ["lockdown-chat"]


#TODO Start this with context without needing an on_message event to pass context through to it.!!!!!!!!!!!!!!!!!!!!!!!!!!!
# Used for daemon tasks, such as removing temporary membership and etc.
async def AdministrativeThread(guild):
    guestRole = discord.utils.get(guild.roles, name="Guest")
    verifiedRole = discord.utils.get(guild.roles, name="Verified")
    sec2Role = discord.utils.get(guild.roles, name="Section 2")
    sec1Role = discord.utils.get(guild.roles, name="Section 1")
    teachingStaffRole = discord.utils.get(guild.roles, name="Teaching Staff")
    adminChannel = discord.utils.get(guild.channels, id=716954090495541248)
    while True:
        est = timezone('US/Eastern')
        currentTime = datetime.now().astimezone(est)
        SLEEP_TIME = 5

        #Remove verified role for professors!
        for member in guild.members:
            id = member.id
            if (teachingStaffRole in member.roles and verifiedRole in member.roles):
                await member.remove_roles(verifiedRole)
                await adminChannel.send("WARNING: The user <@"+str(id)+"> is teaching faculty and was found to have the Verified role. It has been removed.")


        #Remove section roles for guests, remove double section ranks.
        for member in guild.members:
            id = member.id

            if (sec1Role in member.roles and sec2Role in member.roles):
                await member.remove_roles(sec1Role)
                await adminChannel.send("WARNING: The user <@" + str(
                    id) + "> has duplicate roles. The user has been reset to the section 2 role. Section 1 role has been removed.")


            if (guestRole in member.roles):
                if (sec2Role in member.roles):
                    await member.remove_roles(sec2Role)
                    await adminChannel.send("WARNING: The user <@" + str(
                        id) + "> is a guest and was found to have a sectional rank. It has been removed.")

                if (sec1Role in member.roles):
                    await member.remove_roles(sec1Role)
                    await adminChannel.send("WARNING: The user <@" + str(
                        id) + "> is a guest and was found to have a sectional rank. It has been removed.")


            #Expire memberships for temporary guests
            if (redisClient.exists(str(id)+".guestExpiry")):
                stringExpiryTime = redisClient.get(str(id)+".guestExpiry").decode("utf-8")
                print("The user: "+str(member)+" has a pending membership expiry date: "+stringExpiryTime)
                #2020-05-30 09:46:59.610027-04:00
                stringExpiryTime = stringExpiryTime.replace("-04:00","")
                #TODO sanitize bullshit timezones
                expiryDate = datetime.strptime(stringExpiryTime,"%Y-%m-%d %H:%M:%S.%f").astimezone(est) + timedelta(hours=4) #fuck timezones

                if (expiryDate <= currentTime):
                    print("User "+str(member)+"'s membership has expired, removing roles")
                    await member.remove_roles(guestRole)
                    await member.remove_roles(verifiedRole)
                    redisClient.delete(str(id)+".guestExpiry")


        # Manage study rooms
        room_list = redisClient.hgetall('room_list')
        study_rooms = discord.utils.get(guild.categories, id=709173209722912779).text_channels
        for study_room in study_rooms:
            try:
                channel_data = redisClient.hgetall(room_list[study_room.name.replace('-text', '').encode()].decode())
                expiry_time = datetime.strptime(channel_data[b'expiry'].decode(), "%Y-%m-%dT%H:%M:%S.%fZ")
                time_difference = expiry_time - datetime.now()

                if time_difference < timedelta():
                    text_channel = discord.utils.get(guild.text_channels,
                                                     id=int(channel_data[b'text_id'].decode('utf-8')))
                    voice_channel = discord.utils.get(guild.voice_channels,
                                                      id=int(channel_data[b'voice_id'].decode('utf-8')))
                    admin_role = discord.utils.get(guild.roles,
                                                   id=int(channel_data[b'admin_role_id'].decode('utf-8')))
                    member_role = discord.utils.get(guild.roles,
                                                    id=int(channel_data[b'member_role_id'].decode('utf-8')))
                    new_room_list = redisClient.hgetall('room_list')
                    del new_room_list[channel_data[b'name']]

                    if len(new_room_list) == 0:
                        redisClient.delete('room_list')
                    else:
                        redisClient.hmset('room_list', new_room_list)

                    redisClient.delete(room_list[study_room.name.replace('-text', '').encode()].decode())
                    await text_channel.delete()
                    await voice_channel.delete()
                    await member_role.delete()
                    await admin_role.delete()

                elif timedelta(minutes=1) < time_difference < timedelta(minutes=1, seconds=SLEEP_TIME):
                    await study_room.send(f"{study_room.name.replace('-text', '')} will be deleted in 1 minute")

                elif timedelta(minutes=10) < time_difference < timedelta(minutes=10, seconds=SLEEP_TIME):
                    await study_room.send(f"{study_room.name.replace('-text', '')} will be deleted in 10 minutes")

                elif timedelta(hours=1) < time_difference < timedelta(hours=1, seconds=SLEEP_TIME):
                    await study_room.send(f"{study_room.name.replace('-text', '')} will be deleted in 1 hour")

            except Exception as e:
                print(e)

        await asyncio.sleep(SLEEP_TIME)





# Administrative
class Administrative(commands.Cog, name='Administrative'):
    def __init__(self, bot):
        self.bot = bot

        # Not really sure what this does
        self._last_member_ = None



    @commands.Cog.listener()
    async def on_member_remove(self, member):
        adminChannel = discord.utils.get(member.guild.channels, id=716954090495541248)
        await adminChannel.send("A user: <@"+str(member.id)+"> has left the server.")

        redisPurge(member)
        adminChannel.send("User has been purged from the database successfully.")



    @commands.Cog.listener()
    async def on_message(self, ctx):

        bot = discord.utils.get(ctx.guild.roles, name="Bot")
        adminRole = discord.utils.get(ctx.guild.roles, name="Admin")
        pendingRole = discord.utils.get(ctx.guild.roles, name="pending")
        global daemonRunning
        if (daemonRunning == False):
            daemonRunning = True
            #TODO How can we do this on startup without needing an on_message event to pass context???
            adminThread = asyncio.get_event_loop().create_task(AdministrativeThread(ctx.guild))
            adminChannel = discord.utils.get(ctx.guild.channels, id=716954090495541248)
            await adminChannel.send("The administrative daemon thread is now running.")

            await adminThread

        pendingChannel = discord.utils.get(ctx.guild.channels, id=717655708098756640)

        if (bot in ctx.author.roles or ctx.channel != pendingChannel or adminRole in ctx.author.roles): return

        try:
            watid = str(ctx.content)
            apiResponse = requests.get(WATERLOO_API_URL + watid + ".json?key=" + WATERLOO_API_KEY).json()
            name = apiResponse['data']['full_name']


            if (ctx.author.nick == name):
                user = ctx.author
                await pendingChannel.send("<@"+str(ctx.author.id)+"> Valid, you are now being re-validated.")
                try:

                    # redisClient.set(str(user) + ".watid", watid)
                    redisClient.set(str(user.id) + ".watid", watid)
                    await pendingChannel.send("WatID " + watid + " has been validated and correlated to <@" + str(user.id) + ">")
                    redisClient.set(str(user) + ".name", name)
                    await pendingChannel.edit(nick=name)
                    await pendingChannel.send(
                        "Name " + name + " has been validated and correlated to <@" + str(user.id) + ">")
                    redisClient.set(watid, 1)
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
        print(f'{self.bot.user.name} has connected to Discord!')

        global daemonRunning
        if not daemonRunning:
            daemonRunning = True
            adminThread = asyncio.get_event_loop().create_task(AdministrativeThread(self.bot.guilds[0]))
            adminChannel = discord.utils.get(self.bot.guilds[0].channels, id=716954090495541248)
            await adminChannel.send("The administrative daemon thread is now running.")
            print('Admin thread start')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        role = discord.utils.get(member.guild.roles, name="Unverified")
        await member.add_roles(role)

    @commands.command()
    async def lock(self,ctx):
        channel = ctx.channel
        messageAuthor = ctx.author

        #lol put it into a loop later
        guestRole = discord.utils.get(messageAuthor.guild.roles, name="Guest")
        sec1Role = discord.utils.get(messageAuthor.guild.roles, name="Section 1")
        sec2Role = discord.utils.get(messageAuthor.guild.roles, name="Section 2")
        regularRoles = [guestRole,sec1Role,sec2Role]


        if (permittedAdmin(messageAuthor)):
            if (redisClient.exists(str(channel.id)+".locked")):
                for memberRole in regularRoles:
                    await channel.set_permissions(memberRole, send_messages=True, read_messages=True, read_message_history=True)
                await ctx.send("This channel has been unlocked. Sending messages is enabled again.")
                redisClient.delete(str(channel.id)+".locked")
            else:
                redisClient.set(str(channel.id)+".locked",1)
                for memberRole in regularRoles:
                    await channel.set_permissions(memberRole, send_messages=False, read_messages=True, read_message_history=True)
                await ctx.send("This channel has been locked. Sending messages is disabled.")



    @commands.command()
    async def verify(self, ctx, *args):
        try:
            messageAuthor = ctx.author
            watid = args[0]

            if (redisClient.exists(str(messageAuthor) + ".request") or redisClient.exists(str(messageAuthor.id) + ".request")):
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
            if (apiResponse['data']['department'] != "ENG/Electrical and Computer"):
                response = "<@" + str(
                    messageAuthor.id) + "> You are not an ECE student!" \
                                        " Please manually validate by contacting" \
                                        " the admin team. The admin team has been" \
                                        " notified of this incident. <@&706658128409657366>"
                await ctx.send(response)
                return
            if (len(apiResponse['data']['telephone_numbers']) > 0):
                response = "<@" + str(
                    messageAuthor.id) + "> You are a faculty member, and faculty members" \
                                        " require manual validation by an administrative team member." \
                                        " Please contact the administration team by messaging them directly," \
                                        " or send an email to k5kumara@uwaterloo.ca."
                await ctx.send(response)
                return

            try:
                if (redisClient.exists(str(messageAuthor) + ".verified") or redisClient.exists(str(messageAuthor.id) + ".verified")):
                    if (int(redisClient.get(str(messageAuthor) + ".verified")) == 1 or int(redisClient.get(str(messageAuthor.id) + ".verified")) == 1):
                        response = "<@" + str(messageAuthor.id) + "> You have already been verified"
                        await ctx.send(response)
                        return
            except:
                print("Lazy nullify error.")
            if (redisClient.exists(str(user_id))):
                if (int(redisClient.get(str(user_id))) == 1):
                    response = "<@" + str(
                        messageAuthor.id) + "> This user_id has already been verified. Not you? Contact an admin."
                    await ctx.send(response)
                    return

            # Mark
            #redisClient.set(str(messageAuthor) + ".watid", user_id)
            redisClient.set(str(messageAuthor.id) + ".watid", user_id)
            redisClient.set(str(messageAuthor.id) + ".verified", 0)
            redisClient.set(str(messageAuthor) + ".name", name)
            redisClient.set(str(messageAuthor.id) + ".name", name)

            # Generate random code
            code = random.randint(1000, 9999)
            redisClient.set(str(messageAuthor.id) + ".code", code)

            mailMessage = Mail(
                from_email='verification@kaveenk.com',
                to_emails=email,
                subject='ECE 2024 Section 2 Discord Verification Code',
                html_content='<strong>Your verification code is: ' + str(
                    code) + '. Please go back into discord and type !confirm (your code)</strong>')
            try:
                sg = SendGridAPIClient('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')
                mailResponse = sg.send(mailMessage)
                # TODO: Validate mail response
            except Exception as e:
                print(e.message)

            response = "<@" + str(
                messageAuthor.id) + "> I sent a verification code to " + email + ". Find the code" \
                                                                                 " in your email and type `!confirm <code>` in discord to verify" \
                                                                                 " your account. Please check your spam and junk folders."
            redisClient.set(str(messageAuthor.id) + ".request", 1)

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

            code = args[0]

            if (redisClient.exists(str(messageAuthor.id) + ".request")):

                if (int(code) == int(redisClient.get(str(messageAuthor.id)+".code"))):
                    response = "<@" + str(messageAuthor.id) + "> You were successfully verified."

                    await ctx.send(response)

                    nickname = redisClient.get(str(messageAuthor.id) + ".name")

                    await messageAuthor.edit(nick=str(nickname.decode('utf-8')))

                    # Mark user and WatID as verified
                    redisClient.set(str(messageAuthor.id) + ".verified", 1)
                    #redisClient.set(str(redisClient.get(str(messageAuthor) + ".watid").decode('utf-8')), 1)
                    redisClient.set(str(redisClient.get(str(messageAuthor.id) + ".watid").decode('utf-8')), 1)

                    if (redisClient.exists(str(messageAuthor.id))): redisClient.delete(str(messageAuthor.id) + ".request")
                    if (redisClient.exists(str(messageAuthor))): redisClient.delete(str(messageAuthor) + ".request")
                    # 706966831268626464
                    verifiedRole = discord.utils.get(ctx.guild.roles, name="Verified")
                    unverifiedRole = discord.utils.get(ctx.guild.roles, name="Unverified")
                    await messageAuthor.add_roles(verifiedRole)
                    await messageAuthor.remove_roles(unverifiedRole)

                    try:
                        watID = redisClient.get(str(messageAuthor.id) + ".watid").decode("utf-8")
                        sec2Role = discord.utils.get(messageAuthor.guild.roles, name="Section 2")
                        sec1Role = discord.utils.get(messageAuthor.guild.roles, name="Section 1")

                        adminChannel = discord.utils.get(messageAuthor.guild.channels, id=716954090495541248)
                        await adminChannel.send("New verification on member join, the WatID for user <@" + str(messageAuthor.id) + "> is " + watID)
                        if (watID in section2List):
                            await messageAuthor.add_roles(sec2Role)
                            await adminChannel.send("Added the Section 2 Role to <@" + str(messageAuthor.id) + ">.")
                        else:
                            await messageAuthor.add_roles(sec1Role)
                            await adminChannel.send("Added the Section 1 Role to <@" + str(messageAuthor.id) + ">.")
                    except Exception as e:
                        print(str(e))

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
            response = "<@" + str(
                messageAuthor.id) + "> There was an error while verifying your user, or your code was invalid."
            await ctx.send(response)

    @commands.command()
    async def cancelverification(self, ctx):

        messageAuthor = ctx.author

        # 706966831268626464
        if (redisClient.exists(str(messageAuthor.id) + ".request")):
            redisClient.delete(str(messageAuthor.id)+".request")
            response = "<@" + str(
                messageAuthor.id) + "> Cancelled your on-going verification, please try again with `!verify <watid>`"
            await ctx.send(response)
        else:
            response = "<@" + str(messageAuthor.id) + "> You do not have a verification in progress"
            await ctx.send(response)

    @commands.command()
    async def devalidate(self, ctx, *args):

        messageAuthor = ctx.author
        if (permittedAdmin(messageAuthor)):
            try:
                selection = args[0]
                if (selection == "user"):
                    user = ctx.message.mentions[0]
                    redisPurge(user)
                    await ctx.send("Purged user from database successfully.")

                elif (selection == "watid"):
                    watid = args[1]
                    redisUnmarkWatID(watid)
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
        verifiedRole = discord.utils.get(messageAuthor.guild.roles, name="Verified")

        if (permittedAdmin(messageAuthor)):
            if (not redisClient.exists("lockdown") or redisClient.get("lockdown").decode('utf-8') == "0"):

                redisClient.set("lockdown", 1)
                propagationMessage = await ctx.send("Cycling lockdown permissions to all text channels... Status: [0/"+str(len(messageAuthor.guild.text_channels))+"]")
                counter = 0
                for channel in messageAuthor.guild.text_channels:
                    counter += 1
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

                counter = 0
                propagationMessage = await ctx.send(
                    "Cycling lockdown permissions to all voice channels... Status: [0/" + str(
                        len(messageAuthor.guild.voice_channels)) + "]")
                for channel in messageAuthor.guild.voice_channels:
                    counter += 1
                    if (channel.id not in user_voice_channels):
                        continue
                    await channel.set_permissions(verifiedRole, view_channel=False,connect=False)
                    await propagationMessage.edit(
                        content="Cycling lockdown permissions to all channels... Status: [" + str(counter) + "/" + str(
                            len(messageAuthor.guild.voice_channels)) + "]")
                await ctx.send("Cycled lockdown permissions to all voice channels.")


                await ctx.send("Lockdown mode enabled. Bot commands and user text chat has been disabled.")
            else:

                redisClient.set("lockdown", 0)
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

                #redisClient.set(str(user) + ".watid", watid)
                redisClient.set(str(user.id) + ".watid", watid)
                await ctx.send("WatID " + watid + " has been validated and correlated to <@" + str(user.id) + ">")
                if ("Verified" in ranks):
                    redisClient.set(str(user) + ".verified", 1)
                    await ctx.send("<@" + str(user.id) + "> has been set to Verified status")
                redisClient.set(str(user) + ".name", name)
                await user.edit(nick=name)
                await ctx.send(
                    "Name " + name + " has been validated and correlated to <@" + str(user.id) + ">")
                redisClient.set(watid, 1)
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
                await ctx.send("<@" + str(
                    messageAuthor.id) + "> You have entered invalid syntax, or the user you are trying to correlate is invalid. `!correlate <USER MENTION> <WatID>`")

    @commands.command()
    async def ldaplookup(self, ctx, *args):

        messageAuthor = ctx.author

        if (permittedAdmin(messageAuthor) or permittedStaff(messageAuthor)):
            try:

                watid = args[0]

                if ("@" in args[0]):

                    # Find user's discord tag
                    for member in ctx.message.mentions:
                        discordID = str(member.id)
                        watid = redisClient.get(discordID + ".watid").decode('utf-8')
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
        adminChannel = discord.utils.get(ctx.author.guild.channels, id=716954090495541248)

        messageAuthor = ctx.author

        if (permittedAdmin(messageAuthor)):
            section1Role = discord.utils.get(ctx.message.guild.roles, name="Section 1")
            section2Role = discord.utils.get(ctx.message.guild.roles, name="Section 2")
            verifiedRole = discord.utils.get(ctx.message.guild.roles, name="Verified")
            guestRole = discord.utils.get(ctx.message.guild.roles, name="Guest")
            teachingRole = discord.utils.get(ctx.message.guild.roles, name="Teaching Staff")
            bot = discord.utils.get(ctx.message.guild.roles, name="Bot")
            pending = discord.utils.get(ctx.message.guild.roles, name="pending")

            for member in ctx.author.guild.members:
                if (teachingRole in member.roles or verifiedRole not in member.roles or bot in member.roles):
                    continue

                try:
                    if (redisClient.exists(str(member.id)+".watid")):
                        if (redisClient.exists(str(member.id) + ".rolevalidated")):
                            continue


                        await adminChannel.send("Analyzing user <@"+str(member.id)+">")
                        watID = redisClient.get(str(member.id) + ".watid").decode("utf-8")
                        await adminChannel.send("The WatID for user <@" + str(member.id) + "> is "+watID)

                        await member.remove_roles(section1Role)
                        await member.remove_roles(section2Role)
                        if (watID in section2List):
                            await member.add_roles(section2Role)
                            await adminChannel.send("Added the Section 2 Role to <@"+str(member.id)+">.")
                        else:
                            await member.add_roles(section1Role)
                            await adminChannel.send("Added the Section 1 Role to <@" + str(member.id) + ">.")
                        redisClient.set(str(member.id)+".rolevalidated","true")

                    else:
                        await member.add_roles(pending)
                        await adminChannel.send("<@&706658128409657366> There was no WatID for: <@" + str(
                            member.id) + "> please investigate.")

                except:
                    await adminChannel.send("<@&706658128409657366> There was an error retriving the WatID for: <@"+str(member.id)+"> please investigate.")




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
    async def eatass(self,ctx):
        await ctx.send("https://gyazo.com/38cbda993854e66a5833284186279ce8")
        await ctx.send("You got your ass ate.")
    @commands.command()
    async def testformatting(self, ctx, *args):
        messageAuthor = ctx.author
        if permittedAdmin(messageAuthor):

            message = " ".join(args)
            await ctx.send(message.replace("\\n","\n"))
    @commands.command()
    async def subscribermessage(self,ctx,*args):
        messageAuthor = ctx.author
        if permittedAdmin(messageAuthor):
            subscriberList = stream(messageAuthor.guild.members).filter(lambda x: redisClient.exists(str(x.id)+".subscribed") and redisClient.get(str(x.id)+".subscribed").decode('utf-8')=="true").to_list()

            message = " ".join(args).replace("\\n","\n")
            messageToEdit = await ctx.send("Sending notifications to subscribed members. Status: [0/"+str(len(subscriberList))+"]")
            for x, subscriber in enumerate(subscriberList):
                await messageToEdit.edit(content="Sending notifications to subscribed members. Status: ["+str(x)+"/"+str(len(subscriberList))+"]")
                try:
                    await send_dm(subscriber,message)
                except Exception as e:
                    await ctx.send("Could not send a message to <@"+str(subscriber.id)+">: "+str(e))


    @commands.command()
    async def subscribers(self,ctx):
        messageAuthor = ctx.author
        if (permittedAdmin(messageAuthor)):
            embed = discord.Embed(title="Subscribed Members",
                                  description="Here is a list of all subscribed members",
                                  color=0x800080)
            embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
            embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
            subscriberList = stream(messageAuthor.guild.members).filter(
                lambda x: redisClient.exists(str(x.id) + ".subscribed")
                          and redisClient.get(str(x.id) + ".subscribed").decode('utf-8') == "true").to_list()


            embed.add_field(name="Subscribed Members",value="\n".join(map(str,subscriberList)), inline=False)
            await ctx.send(embed=embed)
            await ctx.send("Total subscribers: "+str(len(subscriberList)))


    @commands.command()
    async def guest(self, ctx, *args):
        messageAuthor = ctx.author
        if (permittedAdmin(messageAuthor)):
            try:
                user = ctx.message.mentions[0]
                time = args[1]

                convertedTime = float(time) * 3600
                endDate = datetime.now() + timedelta(seconds=convertedTime)
                est = timezone('US/Eastern')
                endDate = endDate.astimezone(est)

                if (redisClient.exists(str(user.id) + ".guestExpiry")):
                    await ctx.send("This user is already a guest on this server!")
                else:
                    redisClient.set(str(user.id) + ".guestExpiry", str(endDate))
                    guestRole = discord.utils.get(ctx.message.guild.roles, name="Guest")
                    verifiedRole = discord.utils.get(ctx.message.guild.roles, name="Verified")
                    await user.add_roles(guestRole)
                    await user.add_roles(verifiedRole)
                    await ctx.send("Granted <@" + str(user.id) + "> temporary membership for " + str(time) + " hours.")
            except Exception as e:
                print(str(e))
                await ctx.send("<@" + str(
                    messageAuthor.id) + " Invalid usage or an exception has occurred, please use: `!guest @MEMBER <time in hours>`")
