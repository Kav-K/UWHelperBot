import os
import random
import requests
import asyncio
from datetime import datetime, timedelta
from pytz import timezone
import os
import sys

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from botCommands.utils.utils import *
from botCommands.utils.redisutils import *
from botCommands.utils.tasks import *
from botCommands.utils.ConfigObjects import *

import discord
from discord.ext import commands
global daemon_running
daemon_running = False

WATERLOO_API_KEY = os.getenv("WATERLOO_API_KEY")
WATERLOO_API_URL = os.getenv("WATERLOO_API_URL")

#TODO Move these into configurables
VERBOSE_CHANNEL_NAME = "bot-alerts"
awaiting_sm = {}
THUMBNAIL_LINK = "https://i.imgur.com/Uusxfqa.png"


# Administrative
class Administrative(commands.Cog, name='Administrative'):
    def __init__(self, bot):
        self.bot = bot
        self._last_member_ = None

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild

        getChannel(VERBOSE_CHANNEL_NAME, guild)
        await getChannel(VERBOSE_CHANNEL_NAME, guild).send("A user: <@"+str(member.id)+"> has left the server.")
        db_purgeUser(member,guild)
        getChannel(VERBOSE_CHANNEL_NAME, guild).send("User has been purged from the database successfully.")

    @commands.Cog.listener()
    async def on_ready(self):
        setGuilds(self.bot.guilds)
        print("Set the guilds to" + str(self.bot.guilds))
        print(f'{self.bot.user.name} has connected to Discord!')
        global daemon_running
        if not daemon_running:
            daemon_running = True
            for indv_guild in self.bot.guilds:
                if indv_guild.id == 706657592578932797:
                    asyncio.get_event_loop().create_task(AdministrativeThread(indv_guild))
                    print("Started an Administrative thread for the ECE 2024 server")

                    asyncio.get_event_loop().create_task(StudyRooms(indv_guild))
                    print("Started a Study Room thread for the ECE 2024 server")

                    asyncio.get_event_loop().create_task(RevokationService(indv_guild))
                    print("Started a Revokation Service thread for the ECE 2024 server")


    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        try:
            role = getRole("Unverified",guild)
            await member.add_roles(role)
        except:
            pass

    # A reaction listener that will prevent specific users from reacting to messages.
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # Retrieve the REACTIONLESS_USERS list from the database
        reactionless_users = getConfigurationValue(ConfigObjects.REACTIONLESS_USERS, reaction.message.guild)

        # Transform into a set split by comma
        if not reactionless_users:
            return

        if "," in reactionless_users:
            reactionless_users = set(reactionless_users.split(","))
        else:
            reactionless_users = set(reactionless_users)

        # If the user is in the set, remove the reaction
        if str(user.id) in reactionless_users:
            await reaction.remove(user)


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

            #Check if the user has already been verified
            try:
                if (db_exists("USER."+str(messageAuthor.id)+".verified",guild)):
                    if (int(db_get("USER."+str(messageAuthor.id)+".verified",guild)) == 1):
                        response = "<@" + str(messageAuthor.id) + "> You have already been verified"
                        await ctx.send(response)
                        return
            except:
                pass

            #Check if the attempted WatID has already been verified.
            if (db_exists("WATID." + watid + ".verifiedonguild",guild)):
                if (int(db_get("WATID." + watid + ".verifiedonguild",guild)) == 1):
                    response = "<@" + str(
                        messageAuthor.id) + "> This user_id has already been verified. Not you? Contact an admin."
                    await ctx.send(response)
                    return

            #Check for verifications on another server
            userInfo = search(messageAuthor.id, self.bot.guilds)

            #Not verified on another server, run the normal process
            if not userInfo["status"]:

                # TODO Get their name somehow later (voluntarily)


                db_set_watid_info(watid,guild,"","","","","",0)
                db_set_user_info(str(messageAuthor.id), guild, watid,"","","","","",0)


                # Generate random code
                code = random.randint(1000, 9999)
                db_set(str(messageAuthor.id) + ".code", code, guild)

                mailMessage = Mail(
                    from_email='verification@kaveenk.com',
                    to_emails=watid + "@uwaterloo.ca",
                    subject='Your UWaterlooHelper Verification Code',
                    html_content='Hello, we recently received a request to verify a discord account for your WatID on the server ' + messageAuthor.guild.name + '! <br>If this was you, your verification code is: <strong>' + str(
                        code) + '</strong>. <br>Please go back into discord and type !confirm (your code)<br><br>If this was not you, you can safely ignore this email.')

                try:
                    response = requests.post(
                        "https://api.mailgun.net/v3/kaveenk.com/messages",
                        auth=("api", os.getenv("MAILGUN_API_KEY")),
                        data={"from": "UW HelperBot Verification <verify@kaveenk.com>",
                              "to": [watid + "@uwaterloo.ca"],
                              "subject": "Your UWHelperBot Verification Code",
                              "html": 'Hello, we recently received a request to verify a discord account for your WatID on the server ' + messageAuthor.guild.name + '! <br>If this was you, your verification code is: <strong>' + str(
                        code) + '</strong>. <br>Please go back into discord and type !confirm (your code)<br><br>If this was not you, you can safely ignore this email.'})
                    if response.status_code != 200:
                        raise Exception('Failed to dispatch an email to ' + watid + "@uwaterloo.ca")
                except Exception as e:
                    await getChannel(VERBOSE_CHANNEL_NAME, guild).send("ERROR: " + str(e))

                response = "<@" + str(
                    messageAuthor.id) + "> I sent a verification code to " + watid + "@uwaterloo.ca" + ". Find the code" \
                                                                                     " in your email and type `!confirm <code>` in discord to verify" \
                                                                                     " your account. Please check your spam and junk folders."
                #Mark as a user with a pending request.
                db_set(str(messageAuthor.id) + ".request", 1, guild)

                await ctx.send(response)

            #Verified on another server, automatically verify them here without any action on their part!
            elif userInfo["status"]:
                # Set their records on the current server to the records provided by another server

                db_set_watid_info(userInfo["watID"],guild,userInfo["firstName"],userInfo["lastName"],userInfo["department"],userInfo["commonNames"],userInfo["emails"],1)
                db_set_user_info(str(messageAuthor.id), guild, userInfo["watID"],userInfo["firstName"], userInfo["lastName"],userInfo["department"], userInfo["commonNames"], userInfo["emails"], 1)

                if (forceName(guild) and userInfo["firstName"] is not None):
                    await messageAuthor.edit(nick=str(userInfo["firstName"] + " "+ userInfo["lastName"]))

                # Add Verified role, attempt to remove Unverified Role
                verifiedRole = getRole("Verified", guild)
                await messageAuthor.add_roles(verifiedRole)
                try:
                    unverifiedRole = getRole("Unverified", guild)
                    await messageAuthor.remove_roles(unverifiedRole)
                except:
                    pass

                #Send a DM to tell them what just happened
                await send_dm(messageAuthor, "Hi there" if userInfo["firstName"] is None else userInfo["firstName"]+", you recently tried to verify on the discord server "+messageAuthor.guild.name+", but we found a previous verification for you on the server "+userInfo["guild"]+" so we have automatically verified your account this time :)")
                response = "<@" + str(
                    messageAuthor.id) + "> You have been automatically verified from another server"
                await ctx.send(response)
                return

        except Exception as e:
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
                    if (forceName(guild) and db_get("USER." + str(messageAuthor.id) + ".firstname", guild) is not None):
                        nickname = db_get("USER." + str(messageAuthor.id) + ".firstname", guild) + " " + db_get("USER." + str(messageAuthor.id) + ".lastname", guild)
                        await messageAuthor.edit(nick=str(nickname))

                    # Mark user and WatID as verified
                    db_set("USER." + str(messageAuthor.id) + ".verified", 1,guild)
                    db_set("WATIO."+db_get("USER." + str(messageAuthor.id) + ".watid",guild)+".verifiedonguild", 1,guild)

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

                        watID = db_get("USER." + str(messageAuthor.id) + ".watid",guild)

                        adminChannel = getChannel(VERBOSE_CHANNEL_NAME, guild)
                        await adminChannel.send("New verification on member join, the WatID for user <@" + str(messageAuthor.id) + "> is " + watID)


                    except Exception as e:
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
            await getChannel(VERBOSE_CHANNEL_NAME, guild).send("ERROR: <@&706658128409657366>: " + str(e))
            response = "<@" + str(
                messageAuthor.id) + "> There was an error while verifying your user, or your code was invalid."
            await ctx.send(response)

    """
    Revoke the "Verified" role from a user, and give them the "access-revoked-temp" role. The arguments for 
    this command should be the Mention of a user to revoke and a time in "AdBhCmDs" format.
    """
    @commands.command()
    @commands.has_role("Admin")
    async def revoke(self, ctx, *args):
        author = ctx.author
        guild = author.guild

        try:
            revokee = args[0]
            time = args[1]
            revokee = await commands.MemberConverter().convert(ctx, revokee)
            revokee_expiry = getRole("Verified", guild)
            await revokee.remove_roles(revokee_expiry)
            revokee_expiry = getRole("access-revoked-temp", guild)

            await revokee.add_roles(revokee_expiry)
            await getChannel("admin-chat", guild).send("Access revoked for <@" + str(revokee.id) + "> for " + time)

            # Parse the time string in "AdBhCmDs" format and convert it to seconds, each time unit type can be optional, for
            # example, "1d" is 1 day, "1h" is 1 hour, "1d1h" is 1 day and 1 hour, "1d1h1m" is 1 day, 1 hour and 1 minute, etc.
            time = time.lower()
            time = time.replace(" ", "")
            time = time.replace("d", "d ")
            time = time.replace("h", "h ")
            time = time.replace("m", "m ")
            time = time.replace("s", "s ")
            time = time.split(" ")
            time = [x for x in time if x != ""]

            seconds = 0
            for t in time:
                if "d" in t:
                    seconds += int(t.replace("d", "")) * 86400
                elif "h" in t:
                    seconds += int(t.replace("h", "")) * 3600
                elif "m" in t:
                    seconds += int(t.replace("m", "")) * 60
                elif "s" in t:
                    seconds += int(t.replace("s", ""))


            # Add the user to the redis database
            db_set("USER." + str(revokee.id) + ".revoked", 1, guild)

            # Add the seconds to the current timestamp and save the revokee expiry time in the database for the user
            revokee_expiry = int((datetime.now() + timedelta(seconds=seconds)).timestamp())
            db_set("USER." + str(revokee.id) + ".revoked_expiry", revokee_expiry, guild)

            # Add the revoked ID to a redis list for easy access
            db_list_append("revoked", str(revokee.id), guild)



        except Exception as e:
            await getChannel(VERBOSE_CHANNEL_NAME, guild).send("ERROR: " + str(e))


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

                else:
                    await ctx.send("<@" + str(
                        messageAuthor.id) + "> Invalid selection! You can choose to devalidate a user currently.")

            except Exception as e:
                await ctx.send("<@" + str(
                    messageAuthor.id) + "> Invalid syntax or selection: `!devalidate <select 'user' or 'watid'> <value>`")


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
                    db_set_watid_info(watid,guild, "", "", "", "", "", 1)
                    db_set_user_info(str(messageAuthor.id),guild,watid,"","","","","",1)

                    await ctx.send("WatID " + watid + " has been validated and correlated to <@" + str(user.id) + ">")

                except:
                    await ctx.send("Invalid WatID: " + watid)
                    return

                if ("Verified" in ranks):
                    try:
                        await user.remove_roles(getRole("Unverified",guild))
                    except:
                        pass
                    await ctx.send("<@" + str(user.id) + "> has been set to Verified status")


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
                await getChannel(VERBOSE_CHANNEL_NAME, guild).send("ERROR: " + str(e))
                await ctx.send("<@" + str(
                    messageAuthor.id) + "> You have entered invalid syntax, or the user you are trying to correlate is invalid. `!correlate <USER MENTION> <WatID>`")

    #No longer supports WatID search! Only user search.
    @commands.command()
    async def ldaplookup(self, ctx, *args):

        messageAuthor = ctx.author
        guild = messageAuthor.guild

        if (permittedAdmin(messageAuthor) or permittedStaff(messageAuthor)):
            try:

                if ("@" in args[0]):

                    # Find user's discord tag
                    for member in ctx.message.mentions:
                        discordID = str(member.id)
                        break

                    userInfo = search(discordID, self.bot.guilds)
                    if (userInfo["status"]):
                        firstName = "Unavailable" if userInfo["firstName"] == "" else userInfo["firstName"]
                        lastName = "Unavailable" if userInfo["lastName"] == "" else userInfo["lastName"]
                        department = "Unavailable" if userInfo["department"] == "" else userInfo["department"]
                        commonNames = "Unavailable" if userInfo["commonNames"] == "" else userInfo["commonNames"]
                        emails = "Unavailable" if userInfo["emails"] == "" else userInfo["emails"]
                        watID = "Unavailable" if userInfo["watID"] == "" else userInfo["watID"]
                else:

                    await ctx.send("User not found")
                    return

                embed = discord.Embed(title="LDAP Lookup",
                                      description="Here is an internal lookup by the University of Waterloo",
                                      color=0x800080)
                embed.set_footer(text="https://github.com/Kav-K/Stream4Bot")
                embed.set_thumbnail(url=THUMBNAIL_LINK)
                embed.add_field(name="Status",
                                value="OK",
                                inline=False)
                embed.add_field(name="Full Name",
                                value=firstName +" "+lastName,
                                inline=False)
                embed.add_field(name="Department",
                                value=department,
                                inline=False)
                embed.add_field(name="Common Names",
                                value=commonNames,
                                inline=False)
                embed.add_field(name="Emails",
                                value=emails,
                                inline=False)
                embed.add_field(name="WatID",
                                value=watID,
                                inline=False)

                await ctx.send(embed=embed)
            except Exception as e:
                response = "Invalid WatID or no WatID provided"
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



    # Check that each member in the ECE 2024 guild has at least 5 roles, if not, shoot them a message saying that
    # one might be missing
    async def validaterolecount(self, ctx, *args):
        #ONLY FOR USE ON THE ECE 2024 SERVER!
        if (str(ctx.author.guild.id) != "706657592578932797"):
            return

        messageAuthor = ctx.author
        guild = messageAuthor.guild
        adminChannel = getChannel(VERBOSE_CHANNEL_NAME, guild)
        verifiedRole = getRole("Verified", guild)
        teachingRole = getRole("Teaching Staff", guild) # TODO make these constants lol. wtf.
        bot = getRole("Bot", guild)

        if not permittedAdmin(messageAuthor):
            return

        # Iterate through all verified members on the guild
        courses = ["ece-313", "ece-320", "ece-331", "ece-351", "ece-356", "ece-358", "ece-360", "ece-373","sci-238",
                   "earth-123", "earth-121", "syde-556", "econ-101" ]
        course_roles = [getRole(course, guild) for course in courses]

        for member in stream(ctx.author.guild.members) \
                .filter(lambda x: teachingRole not in x.roles and verifiedRole in x.roles and bot not in x.roles). \
                to_list():
            role_count = sum([1 for role in member.roles if role in course_roles])
            if role_count < 5:
                # Send a DM using send_dm to the member
                await send_dm(member, "You currently have < 5 course roles in the ECE 2024 Discord Server."
                                      "Please visit #get-roles to add more roles to your account so that you can be"
                                      "properly notified for course events.")


    @commands.command()
    async def sm(self,ctx,*args):
        messageAuthor = ctx.author
        guild = messageAuthor.guild
        if permittedAdmin(messageAuthor):
            try:
                if (args[0].lower() == 'confirm'):
                    if (messageAuthor.id in awaiting_sm):
                        await sendSubscriberMessage(awaiting_sm[messageAuthor.id], guild)
                        del awaiting_sm[messageAuthor.id]
                    else:
                        await ctx.send("You do not have a pending subscriber message to send out.")
                elif (args[0].lower() == 'cancel'):
                    if (messageAuthor.id in awaiting_sm):
                        del awaiting_sm[messageAuthor.id]
                        await ctx.send("Deleted your pending subscriber message request")
                    else:
                        await ctx.send("You do not have a pending subscriber message to cancel.")
                else:
                    if (messageAuthor.id not in awaiting_sm):
                        message = " ".join(args)
                        #To make formatting show up on the other end!
                        message = message.replace("\"","'")
                        await ctx.send(message.replace("\\n", "\n"))
                        await ctx.send("This is a preview of the message you are about to send. To send, please type `!sm confirm`")
                        awaiting_sm[messageAuthor.id] = message
                    else:
                        await ctx.send("You already have a pending subscriber message request. Please `!sm confirm` or `!sm cancel`")
            except Exception as e:
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

            subscriberList = getSubscribers(guild)
            if (len(subscriberList) <1):
                await ctx.send("No subscribers")
                return

            for page in paginate(map(str,subscriberList)):
                embed.add_field(name="Subscribed Members",value="\n".join(map(str,page)), inline=False)

            await ctx.send(embed=embed)
            await ctx.send("Total subscribers: "+str(len(subscriberList)))

#Generate usage metrics for the bot
    @commands.command()
    async def metrics(self,ctx):
        if (permittedDeveloper(ctx.author)):
            totalUsers = 0
            totalVerified = 0
            for guild in self.bot.guilds:
                totalUsers += len(guild.members)
                verifiedRole = getRole("Verified",guild)
                totalVerified += len(stream(guild.members).filter(lambda x: verifiedRole in x.roles).to_list())
            embed = discord.Embed(title="Usage Metrics",
                                  description="Here are some usage metrics for the UWaterloo Helper Bot",
                                  color=0x800080)
            embed.add_field(name="Total Users",value=totalUsers,inline=False)
            embed.add_field(name="Total Verified Users",value=totalVerified,inline=False)
            embed.add_field(name="Registered Servers", value=len(self.bot.guilds), inline=False)
            await ctx.send(embed=embed)


#Toggle if a server should force name changes or not
    @commands.command()
    async def config(self,ctx, *args):
        if not permittedAdmin(ctx.author):
            return

        if (args[0] == "VIEW"):
            try:
                configOption = ConfigObjects[args[1]]
                await ctx.send("Value for :"+str(configOption)+" is: "+getConfigurationValue(configOption,ctx.author.guild))
                return
            except Exception as e:
                await ctx.send("Invalid syntax or configuration object: "+str(e))
                return
        elif (args[0] == "APPEND"):
            try:
                configOption = ConfigObjects[args[1]]
                value = args[2]
                appendConfigurationValue(configOption,value,ctx.author.guild)
                await ctx.send("Value for :"+str(configOption)+" is: "+getConfigurationValue(configOption,ctx.author.guild))
                return
            except Exception as e:
                await ctx.send("Invalid syntax or configuration object: "+str(e))
                return
        elif (args[0] == "SET"):
            try:
                configOption = ConfigObjects[args[1]]
                value = args[2]
                setConfigurationValue(configOption,value, ctx.author.guild)
                await ctx.send("Value for :"+str(configOption)+" is set to: "+getConfigurationValue(configOption,ctx.author.guild))
                return
            except Exception as e:
                await ctx.send("Invalid syntax or configuration object: "+str(e))
                return


#Announce a message to a channel on all servers (Usually should be admin-chat or bot-alerts, or bot-updates)
    @commands.command()
    async def announce(self, ctx,*args):
        #Restricted only to me (Kaveen) for now for important updates about the bot
        if (ctx.author.id != 213045272048041984) or len(args[1:]) < 1:
            await ctx.send("No permission or invalid message.")
            return
        try:
            channelName = args[0]
            message = " ".join(args[1:])
            message = message.replace("\"", "'")
            message = message.replace("\\n", "\n")
        except Exception as e:
            await ctx.send("Error while composing announcement: "+str(e))
            return

        for guild in self.bot.guilds:
            try:
                await getChannel(channelName,guild).send(message)
                await ctx.send("Sent announcement to "+guild.name)
            except Exception as e:
                await ctx.send("Error while sending announcement to "+guild.name+": "+str(e))

    @commands.command()
    async def reinstantiate(self, ctx):
        if (permittedDeveloper(ctx.author)):
            for guild in self.bot.guilds:
                await getChannel("admin-chat",guild).send("The bot is now restarting all instances, the reboot process should take approximately 5-8 minutes. During this time, bot functions may not be available, or faulty.")
                await getChannel("admin-chat",guild).send("Verification currently unavailable for the next 10 minutes.")

            db_disconnect_all()
            restart()


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

