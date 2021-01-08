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
        #TODO Change guilds back to everything lol.
        setGuilds(self.bot.guilds)
        print("Set the guilds to" + str(self.bot.guilds))
        print(f'{self.bot.user.name} has connected to Discord!')
        global daemon_running
        if not daemon_running:
            daemon_running = True
            for indv_guild in self.bot.guilds:
                verbose_channel = getChannel(VERBOSE_CHANNEL_NAME, indv_guild)
                asyncio.get_event_loop().create_task(AdministrativeThread(indv_guild))
                await verbose_channel.send(str(indv_guild)+": The administrative daemon thread is now running.")
                await verbose_channel.send("Verification is now available.")
                print('Admin thread start')
                asyncio.get_event_loop().create_task(CommBroker(indv_guild))
                await verbose_channel.send(str(indv_guild)+": The communications broker thread is now running.")
                print('Communications broker thread start')
                break


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
    async def verifyv2(self, ctx, *args):
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

            # We cannot ask the UW API for information anymore.. We have to trust the user to enter their WatID correctly
            # through more information sharing.

            # apiResponse = requests.get(WATERLOO_API_URL + watid + ".json?key=" + WATERLOO_API_KEY).json()
            # email = apiResponse['data']['email_addresses'][0]
            # name = apiResponse['data']['full_name']
            # user_id = apiResponse['data']['user_id']

            #We cannot ensure if anybody is a faculty member or not anymore..

            # if (len(apiResponse['data']['telephone_numbers']) > 0):
            #     response = "<@" + str(
            #         messageAuthor.id) + "> You are a faculty member, and faculty members" \
            #                             " require manual validation by an administrative team member." \
            #                             " Please contact the administration team by messaging them directly," \
            #                             " or send an email to k5kumara@uwaterloo.ca."
            #     await ctx.send(response)
            #     return

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
            if (db_exists(str(watid),guild)):
                if (int(db_get(str(watid),guild)) == 1):
                    response = "<@" + str(
                        messageAuthor.id) + "> This WatID has already been verified. Not you? Contact an admin."
                    await ctx.send(response)
                    return

            #Check for verifications on another server
            userInfo = search(messageAuthor.id, self.bot.guilds)
            print(str(userInfo))

            #Not verified on another server, run the normal process
            if not userInfo["status"]:
                # Mark
                db_set(str(messageAuthor.id) + ".watid", watid, guild)
                db_set(str(messageAuthor.id) + ".verified", 0, guild)

                # db_set(str(messageAuthor) + ".name", name, guild)
                # db_set(str(messageAuthor.id) + ".name", name, guild)

                # Generate random code
                code = random.randint(1000, 9999)
                db_set(str(messageAuthor.id) + ".code", code, guild)

                mailMessage = Mail(
                    from_email='verification@kaveenk.com',
                    to_emails=watid+"@uwaterloo.ca",
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
                    messageAuthor.id) + "> I sent a verification code to " + watid+"@uwaterloo.ca" + ". Find the code" \
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

                #Temporarily remove the force name change until an alternative system is found.
                # db_set(str(messageAuthor) + ".name", userInfo["name"], guild)
                # db_set(str(messageAuthor.id) + ".name", userInfo["name"], guild)
                #
                # if (forceName(guild)):
                #     await messageAuthor.edit(nick=str(userInfo["name"]))

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
    async def confirmv2(self, ctx, *args):
        try:
            messageAuthor = ctx.author
            guild = messageAuthor.guild
            code = args[0]

            if (db_exists(str(messageAuthor.id) + ".request",guild)):

                #Check if entered code matches code stored in redis
                if (int(code) == int(db_get(str(messageAuthor.id)+".code",guild))):

                    response = "<@" + str(messageAuthor.id) + "> You were successfully verified."
                    await ctx.send(response)

                    #Temporarily disable the forcing of a user's name
                    # if (forceName(guild)):
                    #     nickname = db_get(str(messageAuthor.id) + ".name", guild)
                    #     await messageAuthor.edit(nick=str(nickname))

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

                        watID = db_get(str(messageAuthor.id) + ".watid",guild)

                        adminChannel = getChannel(VERBOSE_CHANNEL_NAME, guild)
                        await adminChannel.send("New verification on member join, the WatID for user <@" + str(messageAuthor.id) + "> is " + watID)

                        #This is only for the BUGS server, add a verified-science role if they are in science!  Temporarily disabled
                        # if (str(guild.id) == "707632982961160282"):
                        #     apiResponse = requests.get(WATERLOO_API_URL + watID + ".json?key=" + WATERLOO_API_KEY).json()
                        #     if (apiResponse['data']['department'] == "SCI/Science"):
                        #         await messageAuthor.add_roles(getRole("Verified-Science",guild))
                        #         await adminChannel.send("Added the Verified-Science Role to <@" + str(messageAuthor.id) + ">.")


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
    async def cancelverificationv2(self, ctx):

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
    async def devalidatev2(self, ctx, *args):

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
    async def correlatev2(self, ctx, *args):

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

                #Temporarily disable the use of the API for correlate :(
                # try:
                #     apiResponse = requests.get(WATERLOO_API_URL + watid + ".json?key=" + WATERLOO_API_KEY).json()
                #     name = apiResponse['data']['full_name']
                # except:
                #     await ctx.send("Invalid WatID: " + watid)
                #     return

                db_set(str(user.id) + ".watid", watid,guild)
                await ctx.send("WatID " + watid + " has been validated and correlated to <@" + str(user.id) + ">")

                if ("Verified" in ranks):
                    db_set(str(user) + ".verified", 1,guild)
                    try:
                        await user.remove_roles(getRole("Unverified",guild))
                    except:
                        pass
                    await ctx.send("<@" + str(user.id) + "> has been set to Verified status")

                # db_set(str(user) + ".name", name,guild)
                # await user.edit(nick=name)
                # await ctx.send(
                #     "Name " + name + " has been validated and correlated to <@" + str(user.id) + ">")


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

            subscriberList = getSubscribers(guild)
            if (len(subscriberList) <1):
                await ctx.send("No subscribers")
                return

            for page in paginate(map(str,subscriberList)):
                print(str(page))
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
            await ctx.send(embed=embed)


#Toggle if a server should force name changes or not
    @commands.command()
    async def config(self,ctx, *args):
        if not permittedAdmin(ctx.author):
            return
        #View a config object
        if (args[0] == "VIEW"):
            try:
                configOption = ConfigObjects[args[1]]
                await ctx.send("Value for :"+str(configOption)+" is: "+getConfigurationValue(configOption,ctx.author.guild))
                return
            except Exception as e:
                await ctx.send("Invalid syntax or configuration object: "+str(e))
                return
        #Set a config object
        try:
            configOption = ConfigObjects[args[0]]
            configValue = args[1]

        except Exception as e:
            await ctx.send("Invalid syntax or configuration object: "+str(e))
            return
        try:
            setConfigurationValue(configOption,configValue,ctx.author.guild)
            await ctx.send("Configuration value changed successfully")
        except Exception as e:
            await ctx.send("Internal error while changing configuration value: "+str(e))


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



