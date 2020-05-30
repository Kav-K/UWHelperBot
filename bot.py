import asyncio
import json
import os
import random
import sys
import urllib.request
from datetime import datetime
from datetime import timedelta

import discord
import pytz
import redis
import requests
from icalendar import Calendar
from pytz import timezone
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

TOKEN = "NzA2Njc4Mzk2MzEwMjU3NzI1.Xq9v2A.iCXfvgwxz4fnmlrRUvTlA_JnSTA"
#testt
roomset = []

client = discord.Client()
WATERLOO_API_KEY = "21573cf6bf679cdfb5eb47b51033daac"
WATERLOO_API_URL = "https://api.uwaterloo.ca/v2/directory/"
redisClient = redis.Redis(host='localhost', port=6379, db=0)
banned_channels = ["general","faculty-general","public-discussion","offtopic"]


async def CheckRoomExpiry():
    guild = discord.utils.get(client.guilds, id=706657592578932797)

    while True:
        SLEEP_TIME = 10
        room_list = redisClient.hgetall('room_list')
        study_channels = discord.utils.get(guild.categories, id=709173209722912779).text_channels

        for channel in study_channels:
            if channel.id != 716100962703376515:
                channel_data = redisClient.hgetall(room_list[channel.name.replace('-text', '').encode()].decode())
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

                    redisClient.delete(room_list[channel.name.replace('-text', '').encode()].decode())
                    await text_channel.delete()
                    await voice_channel.delete()
                    await member_role.delete()
                    await admin_role.delete()

                elif timedelta(seconds=30) < time_difference < timedelta(seconds=30 + SLEEP_TIME):
                    await channel.send(f"{channel.name.replace('-text', '')} will be deleted in 1 minute")

                elif timedelta(minutes=1) < time_difference < timedelta(minutes=1, seconds=SLEEP_TIME):
                    await channel.send(f"{channel.name.replace('-text', '')} will be deleted in 10 minutes")

                elif timedelta(minutes=1, seconds=30) < time_difference < timedelta(minutes=1, seconds=30 + SLEEP_TIME):
                    await channel.send(f"{channel.name.replace('-text', '')} will be deleted in 1 hour")

        await asyncio.sleep(10)


@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord!')

    roomThread = asyncio.get_event_loop().create_task(CheckRoomExpiry())
    await roomThread


@client.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name="Unverified")
    await member.add_roles(role)


@client.event
async def on_message(message):
    if (message.author == client.user):
        return

    content_array = message.content.split(" ")

    if content_array[0] == 'test':
        await message.channel.send('You are ugly DreBot')

    elif content_array[0] == '!clearroom':
        study_room = redisClient.hgetall(f"{message.author.id}-study-room")

        text_channel = discord.utils.get(message.guild.text_channels,
                                         id=int(study_room[b'text_id'].decode('utf-8')))
        voice_channel = discord.utils.get(message.guild.voice_channels,
                                          id=int(study_room[b'voice_id'].decode('utf-8')))
        admin_role = discord.utils.get(message.guild.roles, id=int(study_room[b'admin_role_id'].decode('utf-8')))
        member_role = discord.utils.get(message.guild.roles, id=int(study_room[b'member_role_id'].decode('utf-8')))
        new_room_list = redisClient.hgetall('room_list')
        del new_room_list[study_room[b'name']]

        if len(new_room_list) == 0:
            redisClient.delete('room_list')
        else:
            redisClient.hmset('room_list', new_room_list)

        redisClient.delete(f"{message.author.id}-study-room")
        await text_channel.delete()
        await voice_channel.delete()
        await member_role.delete()
        await admin_role.delete()

    elif content_array[0] == '!room':
        guild = message.guild
        author = message.author
        room_name = f"{author.display_name.replace(' ', '-').lower()}-study-room"
        failed = True

        if content_array[1] == 'create':
            try:
                assert redisClient.hgetall(f"{message.author.id}-study-room") == {}, 'room exists'
                time = float(content_array[2])
                assert 0 < time <= 720, 'invalid time'
                failed = False
            except IndexError:
                await message.channel.send('You did not specify a time')
            except ValueError:
                await message.channel.send('Time must be an integer or decimal number representing time in minutes')
            except AssertionError as e:
                if str(e) == 'invalid time':
                    await message.channel.send('Time must be between 0 and 720 minutes')
                else:
                    await message.channel.send(f"You already have a study room created ({room_name})")

            if not failed:
                members = message.mentions
                room_admin_role = await guild.create_role(name=f"{room_name}-admin")
                member_role = await guild.create_role(name=f"{room_name}-member")
                everyone_role = discord.utils.get(guild.roles, name='@everyone')

                await message.author.add_roles(room_admin_role)
                for member in members:
                    if member != author:
                        await member.add_roles(member_role)

                voice_overwrites = {
                    everyone_role: discord.PermissionOverwrite(view_channel=False),
                    member_role: discord.PermissionOverwrite(view_channel=True),
                    room_admin_role: discord.PermissionOverwrite(view_channel=True, kick_members=True,
                                                                 mute_members=True,
                                                                 deafen_members=True)
                }

                text_overwrites = {
                    everyone_role: discord.PermissionOverwrite(view_channel=False),
                    member_role: discord.PermissionOverwrite(view_channel=True),
                    room_admin_role: discord.PermissionOverwrite(view_channel=True, kick_members=True)
                }

                voice_channel = await guild.create_voice_channel(f"{room_name}-voice", overwrites=voice_overwrites,
                                                                 category=discord.utils.get(guild.categories,
                                                                                            id=709173209722912779))
                text_channel = await guild.create_text_channel(f"{room_name}-text", overwrites=text_overwrites,
                                                               category=discord.utils.get(guild.categories,
                                                                                          id=709173209722912779))
                await message.channel.send(
                    f"Created {room_name}-text and {room_name}-voice\nReserved for {time} min")

                print((datetime.now() + timedelta(minutes=time)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
                assert(isinstance((datetime.now() + timedelta(minutes=time)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), str))

                study_room_data = {
                    'name': room_name,
                    'voice_id': voice_channel.id,
                    'text_id': text_channel.id,
                    'admin_id': message.author.id,
                    'admin_role_id': room_admin_role.id,
                    'member_role_id': member_role.id,
                    'members_id': json.dumps(
                        [member.id for member in message.mentions if member != message.author]),
                    'created': datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    'expiry': (datetime.now() + timedelta(minutes=time)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                }
                try:
                    redisClient.hmset(f"{message.author.id}-study-room", study_room_data)
                    room_list = redisClient.hgetall('room_list')
                    room_list[room_name] = f"{message.author.id}-study-room"
                    redisClient.hmset('room_list', room_list)
                except Exception as e:
                    print(e)
                    await text_channel.delete()
                    await voice_channel.delete()
                    await member_role.delete()
                    await room_admin_role.delete()

        elif content_array[1] == 'time':
            try:
                study_room = redisClient.hgetall(f"{message.author.id}-study-room")
                expiry_time = datetime.strptime(study_room[b'expiry'].decode(), "%Y-%m-%dT%H:%M:%S.%fZ")
                time_remaining = expiry_time - datetime.now()

                await message.channel.send(f"{study_room[b'name'].decode()} will expire at "
                                           f"{expiry_time.strftime('%H:%M:%S')}.\nYou have "
                                           f"{time_remaining.seconds // 60} min remaining.")

            except KeyError:
                await message.channel.send(f"You do not have a study room created")

        elif content_array[1] == 'extend':
            try:
                study_room = redisClient.hgetall(f"{message.author.id}-study-room")
                created_time = datetime.strptime(study_room[b'created'].decode(), "%Y-%m-%dT%H:%M:%S.%fZ")
                expiry_time = datetime.strptime(study_room[b'expiry'].decode(), "%Y-%m-%dT%H:%M:%S.%fZ")
                time = float(content_array[2])
                assert 0 < time <= 720, 'invalid time'
                new_time = expiry_time + timedelta(minutes=time)
                assert new_time < created_time + timedelta(days=1), 'max time'

                study_room[b'expiry'] = new_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                redisClient.hmset(f"{message.author.id}-study-room", study_room)

                await message.channel.send(f"{room_name}'s lifespan extended by {time} min and will expire at "
                                           f"{new_time.strftime('%H:%M:%S')}.\nYou have "
                                           f"{(new_time - datetime.now()).seconds // 60} min remaining.")

            except KeyError:
                await message.channel.send(f"You do not have a study room created")
            except IndexError:
                await message.channel.send('You did not specify a time')
            except ValueError:
                await message.channel.send('Time must be an integer or decimal number representing time in minutes')
            except AssertionError as e:
                if str(e) == 'invalid time':
                    await message.channel.send('Time must be between 0 and 720 minutes')
                else:
                    await message.channel.send(f"{room_name}'s lifespan cannot pass 24 hours and must expire before"
                                               f"{(created_time + timedelta(days=1)).strftime('%H:%M:%S')}")

        elif content_array[1] == 'add':
            try:
                study_room = redisClient.hgetall(f"{message.author.id}-study-room")
                member_role = discord.utils.get(message.guild.roles, id=int(study_room[b'member_role_id'].decode('utf-8')))
                new_members_list = json.loads(study_room[b'members_id'])
                assert len(message.mentions) > 0

                for member in message.mentions:
                    if member != message.author:
                        if member.id not in new_members_list:
                            await member.add_roles(member_role)
                            await message.channel.send(
                                f"Added {member.display_name} to {room_name}-text and {room_name}-voice")
                            new_members_list.append(member.id)
                        else:
                            await message.channel.send(
                                f"{member.display_name} is already a member of {room_name}")

                    new_study_room = study_room
                    new_study_room[b'members_id'] = json.dumps(new_members_list)
                    redisClient.hmset(f"{message.author.id}-study-room", new_study_room)
            except KeyError:
                await message.channel.send(f"You do not have a study room created")
            except AssertionError:
                await message.channel.send(f"You did not have any mention members")

        elif content_array[1] == 'remove':
            try:
                study_room = redisClient.hgetall(f"{message.author.id}-study-room")
                member_role = discord.utils.get(message.guild.roles, id=int(study_room[b'member_role_id'].decode('utf-8')))
                new_members_list = json.loads(study_room[b'members_id'])
                assert len(message.mentions) > 0

                for member in message.mentions:
                    if member != message.author:
                        if member.id in new_members_list:
                            await member.remove_roles(member_role)
                            await message.channel.send(
                                f"Removed {member.display_name} from {room_name}-text and {room_name}-voice")
                            new_members_list.remove(member.id)
                        else:
                            await message.channel.send(
                                f"{member.display_name} is not a member of {room_name}")

                    new_study_room = study_room
                    new_study_room[b'members_id'] = json.dumps(new_members_list)
                    redisClient.hmset(f"{message.author.id}-study-room", new_study_room)
            except KeyError:
                await message.channel.send(f"You do not have a study room created")
            except AssertionError:
                await message.channel.send(f"You did not have any mention members")

    # if content_array[0] == '!upcoming':
    #     if (message.channel.name in banned_channels):
    #         await message.channel.send("To keep chat clean, you can't use this command in here! Please go to <#707029428043120721>")
    #         return
    #
    #     dateMap = {}
    #     dateList = []
    #
    #     # Get the icalendar and stuff
    #     g = urllib.request.urlopen(
    #         'https://calendar.google.com/calendar/ical/k5kumara%40edu.uwaterloo.ca/public/basic.ics')
    #     gcal = Calendar.from_ical(g.read())
    #     dateRangeEnd = datetime.now() + timedelta(days=7)
    #
    #     for component in gcal.walk():
    #         if component.name == "VEVENT":
    #
    #             summary = component.get('summary')
    #             print(summary)
    #             startdate = component.get('dtstart').dt
    #             enddate = component.get('dtend').dt
    #
    #             # Initialize timezone
    #             est = timezone('US/Eastern')
    #
    #             finalStartDate, finalEndDate = None, None
    #             try:
    #                 finalStartDate = startdate.replace(tzinfo=pytz.utc).astimezone(est)
    #                 finalEndDate = enddate.replace(tzinfo=pytz.utc).astimezone(est)
    #             except:
    #                 finalStartDate = datetime(year=startdate.year, month=startdate.month, day=startdate.day, hour=4,
    #                                           minute=0).astimezone(est)
    #                 finalEndDate = datetime(year=enddate.year, month=enddate.month, day=enddate.day, hour=4,
    #                                         minute=0).astimezone(est)
    #
    #             finalMessage = str(
    #                 finalStartDate.strftime("%A, %B %d at %-I:%M %p")) + " to " + str(
    #                 finalEndDate.strftime("%A, %B %d at %-I:%M %p") + ";" + summary)
    #
    #             # Create a sorted mapping between date and message
    #             if (datetime.now().date() <= finalStartDate.date() <= dateRangeEnd.date()):
    #                 if (finalStartDate not in dateMap):
    #                     dateMap[finalStartDate] = []
    #                 if (finalStartDate not in dateList):
    #                     dateList.append(finalStartDate)
    #                 dateMap[finalStartDate].append(finalMessage)
    #     dateList.sort()
    #     embed = discord.Embed(title="Upcoming Important Dates",
    #                           description="These are all upcoming quizzes, due dates, and other important dates. Please contact the admin team if there are any issues.",
    #                           color=0x800080)
    #     embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
    #     embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
    #
    #     for idate in dateList:
    #         for messageToSend in dateMap[idate]:
    #             messageArray = messageToSend.split(";")
    #             embed.add_field(name=messageArray[0], value=messageArray[1], inline=False)
    #     await message.channel.send(embed=embed)
    #     g.close()
    #
    #
    #
    # elif content_array[0] == '!textbooks':
    #     embed = discord.Embed(title="Textbooks & Resources",
    #                           description="Here is a dropbox link for our collective resources. Feel free to contact the admin team if you'd like to add to it.",
    #                           color=0x800080)
    #     embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
    #     embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
    #     embed.add_field(name="Link", value="https://www.dropbox.com/sh/tg1se0xab9c9cfc/AAAdJJZXi1bkkHUoW5oYT_EAa?dl=0",
    #                     inline=False)
    #     await message.channel.send(embed=embed)
    #
    # elif message.content == '!help':
    #     embed = discord.Embed(title="Commands", description="Here are a list of commands for the stream 4 bot",
    #                           color=0x800080)
    #     embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
    #     embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
    #     embed.add_field(name="!textbooks", value="Get a link to the textbooks and shared resources", inline=False)
    #     embed.add_field(name="!upcoming", value="Get a list of upcoming due dates for the next 7 days", inline=False)
    #     embed.add_field(name="!verify <watid>", value="Verify your account to use this discord", inline=False)
    #     embed.add_field(name="!piazza", value="Get our relevant piazza links", inline=False)
    #     embed.add_field(name="!schedule <OPTIONAL (course number)>", value="View a continuously updating class/lab schedule, or specify a course code for a more specific content/labs/etc schedule.", inline=False)
    #     embed.add_field(name="!importantdates", value="Get a full calendar with important dates and due dates",
    #                     inline=False)
    #     embed.add_field(name="=help", value="Activate the MathBot", inline=False)
    #     embed.add_field(name="=tex <LATEX>", value="Create a LaTeX equation", inline=False)
    #     embed.add_field(name="=wolf <QUERY>", value="Use the wolfram engine to search something up or calculate", inline=False)
    #     embed.add_field(name="!assignments <140 OR 124>", value="View assignment questions for 124 and 140 from the textbook", inline=False)
    #     embed.add_field(name="!breakdown <course number>", value="View the grading scheme breakdown for a course", inline=False)
    #     await message.channel.send(embed=embed)
    #
    # elif content_array[0] == '!verify':
    #     try:
    #         watid = content_array[1]
    #         if (redisClient.exists(str(message.author) + ".request")):
    #             response = "<@" + str(
    #                 message.author.id) + "> There is already a pending verification request for your WatID, please use `!confirm <code>` or do `!cancelverification`"
    #             await message.channel.send(response)
    #             return
    #         # Ask UW API for information
    #         apiResponse = requests.get(WATERLOO_API_URL + watid + ".json?key=" + WATERLOO_API_KEY).json()
    #         email = apiResponse['data']['email_addresses'][0]
    #         name = apiResponse['data']['full_name']
    #         user_id = apiResponse['data']['user_id']
    #         if (apiResponse['data']['department'] != "ENG/Electrical and Computer"):
    #             response = "<@" + str(
    #                 message.author.id) + "> You are not an ECE student! Please manually validate by contacting the admin team. The admin team has been notified of this incident. <@&706658128409657366>"
    #             await message.channel.send(response)
    #             return
    #         if (len(apiResponse['data']['telephone_numbers']) > 0):
    #             response = "<@" + str(
    #                 message.author.id) + "> You are a faculty member, and faculty members require manual validation by an administrative team member. Please contact the administration team by messaging them directly, or send an email to k5kumara@uwaterloo.ca."
    #             await message.channel.send(response)
    #             return;
    #         if (redisClient.exists(str(message.author) + ".verified")):
    #             if (int(redisClient.get(str(message.author) + ".verified")) == 1):
    #                 response = "<@" + str(message.author.id) + "> You have already been verified"
    #                 await message.channel.send(response)
    #                 return
    #         if (redisClient.exists(str(user_id))):
    #             if (int(redisClient.get(str(user_id))) == 1):
    #                 response = "<@" + str(
    #                     message.author.id) + "> This user_id has already been verified. Not you? Contact an admin."
    #                 await message.channel.send(response)
    #                 return
    #
    #         # Mark
    #         redisClient.set(str(message.author) + ".watid", user_id)
    #         redisClient.set(str(message.author) + ".verified", 0)
    #         redisClient.set(str(message.author) + ".name", name)
    #
    #         # Generate random code
    #         code = random.randint(1000, 9999)
    #         redisClient.set(str(message.author), code)
    #
    #         mailMessage = Mail(
    #             from_email='verification@kaveenk.com',
    #             to_emails=email,
    #             subject='ECE 2024 Section 2 Discord Verification Code',
    #             html_content='<strong>Your verification code is: ' + str(
    #                 code) + '. Please go back into discord and type !confirm (your code)</strong>')
    #         try:
    #             sg = SendGridAPIClient('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')
    #             mailResponse = sg.send(mailMessage)
    #             # TODO: Validate mail response
    #         except Exception as e:
    #             print(e.message)
    #
    #         response = "<@" + str(
    #             message.author.id) + "> I sent a verification code to " + email + ". Find the code in your email and type `!confirm <code>` in discord to verify your account. Please check your spam and junk folders."
    #         redisClient.set(str(message.author) + ".request", 1)
    #
    #         await message.channel.send(response)
    #     except Exception as e:
    #         print(e)
    #         response = "<@" + str(
    #             message.author.id) + "> No WatID provided or invalid watID, please use `!verify <watid>`. Your WatID is the username in your original email, for example, in k5kumara@edu.uwaterloo.ca, the watID is k5kumara."
    #         await message.channel.send(response)
    #
    # elif content_array[0] == "!confirm":
    #     try:
    #         code = content_array[1]
    #
    #         if (redisClient.exists(str(message.author) + ".request")):
    #
    #             if (int(code) == int(redisClient.get(str(message.author)))):
    #                 response = "<@" + str(message.author.id) + "> You were successfully verified."
    #
    #                 await message.channel.send(response)
    #
    #                 nickname = redisClient.get(str(message.author) + ".name")
    #
    #                 await message.author.edit(nick=str(nickname.decode('utf-8')))
    #
    #                 # Mark user and WatID as verified
    #                 redisClient.set(str(message.author) + ".verified", 1)
    #                 redisClient.set(str(redisClient.get(str(message.author) + ".watid").decode('utf-8')), 1)
    #                 redisClient.delete(str(message.author) + ".request")
    #                 # 706966831268626464
    #                 role = discord.utils.get(message.guild.roles, name="Verified")
    #                 unverifiedRole = discord.utils.get(message.guild.roles, name="Unverified")
    #                 await message.author.add_roles(role)
    #
    #                 try:
    #                     message.author.remove_roles(unverifiedRole)
    #                 except:
    #                     print("TODO: handle remove_role exception")
    #             else:
    #                 response = "<@" + str(message.author.id) + "> Invalid verification code."
    #                 await message.channel.send(response)
    #         else:
    #             response = "<@" + str(
    #                 message.author.id) + "> You do not have a pending verification request, please use `!verify <WATID>` to start."
    #             await message.channel.send(response)
    #
    #     except Exception as e:
    #         print(e)
    #         response = "<@" + str(
    #             message.author.id) + "> There was an error while verifying your user, or your code was invalid."
    #         await message.channel.send(response)
    #
    # elif content_array[0] == '!cancelverification':
    #     # 706966831268626464
    #     if (redisClient.exists(str(message.author) + ".request")):
    #         response = "<@" + str(
    #             message.author.id) + "> Cancelled your on-going verification, please try again with `!verify <watid>`"
    #         await message.channel.send(response)
    #     else:
    #         response = "<@" + str(message.author.id) + "> You do not have a verification in progress"
    #         await message.channel.send(response)
    #
    # elif content_array[0] == '!devalidate':
    #     allowed = False
    #     for role in message.author.roles:
    #         if role.name == 'Admin':
    #             allowed = True
    #     if (allowed):
    #         try:
    #             selection = content_array[1]
    #             if (selection == "user"):
    #                 user = message.mentions[0]
    #                 watid = redisClient.get(str(user) + ".watid").decode('utf-8')
    #                 redisClient.delete(watid)
    #                 await message.channel.send("Unmarked WatID "+watid)
    #                 redisClient.delete(str(user)+".watid")
    #                 await message.channel.send("Purged WatID")
    #                 redisClient.delete(str(user) + ".verified")
    #                 await message.channel.send("Purged verified status")
    #                 redisClient.delete(str(user) + ".name")
    #                 await message.channel.send("Purged legal name")
    #                 redisClient.delete(str(message.author))
    #                 redisClient.delete(str(user)+".request")
    #                 await message.channel.send("Purged request status")
    #                 await message.channel.send("Purged user from database successfully.")
    #
    #             elif (selection == "watid"):
    #                 watid = content_array[2]
    #                 redisClient.delete(watid)
    #                 await message.channel.send("Unmarked WatID "+watid)
    #             else:
    #                 await message.channel.send("<@"+str(message.author.id)+"> Invalid selection! You can choose to devalidate a user or a WatID.")
    #         except:
    #             print("<@+"+str(message.author.id)+"> Invalid syntax or selection: `!devalidate <select 'user' or 'watid'> <value>`")
    #
    #
    #
    # elif (content_array[0] == '!correlate'):
    #     allowed = False
    #     for role in message.author.roles:
    #         if role.name == 'Admin':
    #             allowed = True
    #     if (allowed):
    #         try:
    #             user = message.mentions[0]
    #             watid = content_array[2]
    #
    #             try:
    #                 ranks = content_array[3]
    #             except:
    #                 await message.channel.send("No ranks supplied, not applying any ranks.")
    #                 ranks = ""
    #
    #             try:
    #                 apiResponse = requests.get(WATERLOO_API_URL + watid + ".json?key=" + WATERLOO_API_KEY).json()
    #                 name = apiResponse['data']['full_name']
    #             except:
    #                 await message.channel.send("Invalid WatID: "+watid)
    #                 return
    #
    #             redisClient.set(str(user) + ".watid", watid)
    #             await message.channel.send("WatID "+watid+" has been validated and correlated to <@"+str(user.id)+">")
    #             if ("Verified" in ranks):
    #                 redisClient.set(str(user) + ".verified", 1)
    #                 await message.channel.send("<@" + str(user.id) + "> has been set to Verified status")
    #             redisClient.set(str(user) + ".name", name)
    #             await user.edit(nick=name)
    #             await message.channel.send(
    #                 "Name " + name + " has been validated and correlated to <@" + str(user.id) + ">")
    #             redisClient.set(str(redisClient.get(str(message.author) + ".watid").decode('utf-8')), 1)
    #             await message.channel.send(
    #                 "The WatID " + watid + " has been marked for no further verifications.")
    #
    #
    #             #Set ranks
    #             isTeaching = False
    #             for role in user.roles:
    #                 if role.name == 'Teaching Staff' or role.name == "Professor" or role.name == "Teaching Assistant":
    #                     isTeaching = True
    #             if (isTeaching):
    #                 if ("Verified" in ranks or "Guest" in ranks):
    #                     await message.channel.send("<@"+str(message.author.id)+"> You may not apply your selected roles to this person.")
    #                     return
    #             try:
    #                 rank_array = ranks.split(",")
    #                 for rank in rank_array:
    #                     if (rank == ""): break
    #                     if ("_" in rank):
    #                         rank = rank.replace("_"," ")
    #                     rankToGive = discord.utils.get(message.guild.roles, name=rank.strip())
    #
    #                     await user.add_roles(rankToGive)
    #
    #                     await message.channel.send("Added " + rank + " role to <@" + str(user.id) + ">")
    #
    #             except Exception as e:
    #
    #                 await user.add_roles(discord.utils.get(message.guild.roles,name=ranks.strip()))
    #
    #
    #
    #             await message.channel.send("All tasks completed successfully")
    #         except Exception as e:
    #             print(str(e))
    #             print('t4')
    #             await message.channel.send("<@"+str(message.author.id)+"> You have entered invalid syntax, or the user you are trying to correlate is invalid. `!correlate <USER MENTION> <WatID>`")
    # elif content_array[0] == '!breakdown':
    #     try:
    #         selection = content_array[1]
    #         if (selection == "140"):
    #             embed = discord.Embed()
    #             embed.add_field(name="ECE 140",
    #                             value="Here is a marking scheme breakdown for ECE 140",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/g2BVcrv.png")
    #             await message.channel.send(embed=embed)
    #         elif (selection == "124"):
    #             embed = discord.Embed()
    #             embed.add_field(name="ECE 124",
    #                             value="Here is a marking scheme breakdown for ECE 124",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/0ivd7nu.png")
    #             await message.channel.send(embed=embed)
    #         elif (selection == "106"):
    #             embed = discord.Embed()
    #             embed.add_field(name="ECE 106",
    #                             value="Here is a marking scheme breakdown for ECE 106",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/mX5DQGf.png")
    #             await message.channel.send(embed=embed)
    #         elif (selection == "108"):
    #             embed = discord.Embed()
    #             embed.add_field(name="ECE 108",
    #                             value="Here is a marking scheme breakdown for ECE 108",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/yXTkxiO.png")
    #             await message.channel.send(embed=embed)
    #         elif (selection == "192"):
    #             embed = discord.Embed()
    #             embed.add_field(name="ECE 192",
    #                             value="Here is a marking scheme breakdown for ECE 192",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/RZrHshS.png")
    #             await message.channel.send(embed=embed)
    #         elif (selection == "119"):
    #             embed = discord.Embed()
    #             embed.add_field(name="MATH 119",
    #                             value="Here is a marking scheme breakdown for MATH 119",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/lOXxjlo.png")
    #             await message.channel.send(embed=embed)
    #         else:
    #
    #             await message.channel.send("<@" + str(message.author.id) + "> You must enter a valid course to view a course marking scheme breakdown, valid entries are `140`, `124`, `106`, `119`, `192`, and `108`")
    #
    #
    #
    #
    #     except:
    #         await message.channel.send("<@" + str(message.author.id) + "> You must enter a course to view a course marking scheme breakdown, valid entries are `140`, `124`, `106`, `119`, `192`, and `108`")
    # elif content_array[0] == '!assignments':
    #     if (message.channel.name in banned_channels):
    #         await message.channel.send("To keep chat clean, you can't use this command in here! Please go to <#707029428043120721>")
    #         return
    #     try:
    #         selection = content_array[1]
    #
    #         if (selection == "140"):
    #             embed = discord.Embed()
    #             embed.add_field(name="ECE 140",
    #                             value="Here are the week-based assignment questions for ECE 140",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/H9X2rru.png")
    #             await message.channel.send(embed=embed)
    #         elif (selection =="124"):
    #             embed = discord.Embed()
    #             embed.add_field(name="ECE 124",
    #                             value="Here are the week-based assignment questions for ECE 124",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/ipSz35S.png")
    #             await message.channel.send(embed=embed)
    #         else:
    #             await message.channel.send("<@"+str(message.author.id)+"> you've made an invalid selection! The available courses to view assignments for are `140` and `124`")
    #
    #     except:
    #         await message.channel.send("<@"+str(message.author.id)+"> You must enter a course to view assignment sets for, valid entries are `140` and `124`")
    # elif content_array[0] == '!ldaplookup':
    #     allowed = False
    #     for role in message.author.roles:
    #         if role.name == 'Admin' or role.name == 'Professor':
    #             allowed = True
    #
    #     if (allowed):
    #         try:
    #
    #             watid = content_array[1]
    #
    #             if ("@" in content_array[1]):
    #
    #                 # Find user's discord tag
    #                 for member in message.mentions:
    #                     discordID = str(member)
    #                     watid = redisClient.get(discordID + ".watid").decode('utf-8')
    #                     break
    #             apiResponse = requests.get(WATERLOO_API_URL + watid + ".json?key=" + WATERLOO_API_KEY).json()
    #
    #             embed = discord.Embed(title="LDAP Lookup",
    #                                   description="Here is an internal lookup by the University of Waterloo",
    #                                   color=0x800080)
    #             embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
    #             embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
    #             embed.add_field(name="Status",
    #                             value=apiResponse['meta']['message'],
    #                             inline=False)
    #             embed.add_field(name="Full Name",
    #                             value=apiResponse['data'][
    #                                 'full_name'],
    #                             inline=False)
    #             embed.add_field(name="Department",
    #                             value=apiResponse['data']['department'],
    #                             inline=False)
    #             embed.add_field(name="Common Names",
    #                             value=str(
    #                                 apiResponse['data']['common_names']),
    #                             inline=False)
    #             embed.add_field(name="Emails",
    #                             value=str(
    #                                 apiResponse['data']['email_addresses']),
    #                             inline=False)
    #             embed.add_field(name="Offices",
    #                             value=str(
    #                                 apiResponse['data']['offices']),
    #                             inline=False)
    #             embed.add_field(name="Phone Numbers",
    #                             value=str(
    #                                 apiResponse['data']['telephone_numbers']),
    #                             inline=False)
    #
    #             if (apiResponse['data']['department'] == "ENG/Electrical and Computer"):
    #                 embed.add_field(name="Student Status",
    #                                 value="ECE Student",
    #                                 inline=False)
    #             else:
    #                 embed.add_field(name="Student Status",
    #                                 value="Not an ECE Student",
    #                                 inline=False)
    #             if (len(apiResponse['data']['telephone_numbers']) > 0):
    #                 embed.add_field(name="Student Status",
    #                                 value="NOT A STUDENT. MANUAL VALIDATION REQUIRED",
    #                                 inline=False)
    #             await message.channel.send(embed=embed)
    #         except Exception as e:
    #             response = "Invalid WatID or no WatID provided"
    #             print(str(e))
    #             await message.channel.send(response)
    #     else:
    #         response = "You are not allowed to use this command. Local Directory Access Protocol Lookups are restricted to Administrators"
    #         await message.channel.send(response)
    #
    # elif content_array[0] == '!validateroles':
    #     allowed = False
    #     for role in message.author.roles:
    #         if role.name == 'Admin':
    #             allowed = True
    #     if (allowed):
    #         verifiedRole = discord.utils.get(message.guild.roles, name="Verified")
    #         unverifiedRole = discord.utils.get(message.guild.roles, name="Unverified")
    #         adminRole = discord.utils.get(message.guild.roles, name="Admin")
    #         teachingRole = discord.utils.get(message.guild.roles, name="Teaching Staff")
    #
    #         memberList = message.guild.members
    #         for member in memberList:
    #             if (verifiedRole in member.roles and unverifiedRole in member.roles):
    #                 await message.channel.send("Removed unverified role from " + member.name)
    #                 await member.remove_roles(unverifiedRole)
    #             elif (
    #                     verifiedRole not in member.roles and unverifiedRole not in member.roles and adminRole not in member.roles and teachingRole not in member.roles):
    #                 await message.channel.send("Added unverified role to " + member.name)
    #                 await member.add_roles(unverifiedRole)
    #         await message.channel.send("All role validations completed successfully.")
    #
    # elif content_array[0] == '!piazza':
    #     embed = discord.Embed(title="Piazza Links", description="Here are our relevant piazza links.", color=0x800080)
    #     embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
    #     embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
    #     embed.add_field(name="FYE", value="https://piazza.com/class/k9rmr76sakf74o", inline=False)
    #     embed.add_field(name="ECE 140", value="https://piazza.com/class/k9u2in2foal48e", inline=False)
    #     embed.add_field(name="MATH 119", value="https://piazza.com/class/k8ykzmozh5241x", inline=False)
    #     embed.add_field(name="ECE 124", value="https://piazza.com/class/k9eqk9mfo1qy3?cid=1", inline=False)
    #     await message.channel.send(embed=embed)
    #
    # elif content_array[0] == '!importantdates':
    #     embed = discord.Embed(title="Due/Important Dates",
    #                           description="Here is a link to a calendar with important dates. Please contact the admin team if there is anything missing",
    #                           color=0x800080)
    #     embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
    #     embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
    #     embed.add_field(name="Link",
    #                     value="https://calendar.google.com/calendar/embed?src=k5kumara%40edu.uwaterloo.ca&ctz=America%2FToronto",
    #                     inline=False)
    #     await message.channel.send(embed=embed)
    # elif content_array[0] == '!schedule':
    #
    #     try:
    #         selection = content_array[1]
    #         if (message.channel.name in banned_channels):
    #             await message.channel.send(
    #                 "To keep chat clean, you can't use this command in here! Please go to <#707029428043120721>")
    #             return
    #         if (selection == "119"):
    #             embed = discord.Embed()
    #             embed.add_field(name="MATH 119",
    #                             value="Here is a schedule of topics, tests, quizzes, and assignments for MATH 119",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/fd56XUE.png")
    #             await message.channel.send(embed=embed)
    #             embed2 = discord.Embed()
    #             embed2.set_image(url="https://i.imgur.com/FgRAdMt.png")
    #             await message.channel.send(embed=embed2)
    #         elif (selection == "106"):
    #             embed = discord.Embed()
    #             embed.add_field(name="ECE 106",
    #                             value="Here is a schedule of topics, labs, tests, quizzes, and assignments for ECE 106",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/BPhpXxp.png")
    #             await message.channel.send(embed=embed)
    #             embed2 = discord.Embed()
    #             embed2.set_image(url="https://i.imgur.com/3HbKvvf.png")
    #             await message.channel.send(embed=embed2)
    #             embed3 = discord.Embed()
    #             embed3.set_image(url="https://i.imgur.com/cw9S7GY.png")
    #             await message.channel.send(embed=embed3)
    #             embed4 = discord.Embed()
    #             embed4.add_field(name="Quizzes",
    #                             value="Quizzes are every monday from 12AM to midnight.",
    #                             inline=False)
    #             await message.channel.send(embed=embed4)
    #         elif (selection == "140"):
    #             embed = discord.Embed()
    #             embed.add_field(name="ECE 140",
    #                             value="Here is a schedule of topics, labs, tests, quizzes, and assignments for ECE 140",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/YCJQw41.png")
    #             await message.channel.send(embed=embed)
    #         elif (selection == "124"):
    #             embed = discord.Embed()
    #             embed.add_field(name="ECE 124",
    #                             value="Here is a schedule of topics, labs, tests, quizzes, and assignments for ECE 124",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/mHRB3Cs.png")
    #             await message.channel.send(embed=embed)
    #         elif (selection == "108"):
    #             embed = discord.Embed()
    #             embed.add_field(name="ECE 108",
    #                             value="Here is a schedule of topics, labs, tests, quizzes, and assignments for ECE 108",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/rMqY50F.png")
    #             await message.channel.send(embed=embed)
    #         elif (selection == "192"):
    #             embed = discord.Embed()
    #             embed.add_field(name="ECE 192",
    #                             value="Here is a schedule of topics, labs, tests, quizzes, and assignments for ECE 192",
    #                             inline=False)
    #             embed.set_image(url="https://i.imgur.com/icdO1m5.png")
    #             await message.channel.send(embed=embed)
    #         else:
    #             await message.channel.send("<@" + str(
    #                 message.author.id) + "> You must enter a valid course to view a specific course schedule, valid entries are `140`, `124`, `106`, `119`, `192`, and `108`. Type the command without any options to get a lecture and live session calendar.")
    #
    #     except:
    #         embed = discord.Embed(title="Class Schedule",
    #                               description="Here is a link to a calendar with class schedules for live lectures and Q&A Sessions. Please contact the admin team if there is anything missing.",
    #                               color=0x800080)
    #         embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
    #         embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
    #         embed.add_field(name="Link",
    #                         value="https://calendar.google.com/calendar/embed?src=ag2veuvcsc5k4kaqpsv7sp7e04%40group.calendar.google.com&ctz=America%2FToronto",
    #                         inline=False)
    #         await message.channel.send(embed=embed)
    # elif content_array[0] == '!closeroom':
    #     allowed = False
    #     for role in message.author.roles:
    #         if role.name == 'Admin':
    #             allowed = True
    #
    #     if (allowed):
    #         if (redisClient.exists(str(message.channel.id))):
    #             miniRoom = redisClient.hgetall(str(message.channel.id))
    #
    #             text_channel = discord.utils.get(message.guild.text_channels,
    #                                              id=int(miniRoom[b'text_channel'].decode('utf-8')))
    #             voice_channel = discord.utils.get(message.guild.voice_channels,
    #                                               id=int(miniRoom[b'voice_channel'].decode('utf-8')))
    #             admin_role = discord.utils.get(message.guild.roles, id=int(miniRoom[b'admin_role'].decode('utf-8')))
    #             member_role = discord.utils.get(message.guild.roles, id=int(miniRoom[b'member_role'].decode('utf-8')))
    #             redisClient.delete(str(message.channel.id))
    #             await text_channel.delete()
    #             await voice_channel.delete()
    #             await member_role.delete()
    #             await admin_role.delete()
    #
    #             redisClient.delete(f"{miniRoom[b'message.author.id'].decode('utf-8')}-study-room")
    #         else:
    #             await message.channel.send("This is not a study room!")
    #     else:
    #         await message.channel.send("You are not allowed to use this command, <@" + str(message.author.id) + ">!")
    #
    #
    #
    # elif content_array[0] == '!reserveroom':
    #     guild = message.guild
    #     room_name = f"{message.author.display_name.replace(' ', '-').lower()}-study-room"
    #     failed = True
    #
    #     try:
    #         time = float(content_array[1]) * 60
    #
    #         assert (time > 0.0 and time < 21600)
    #         failed = False
    #     except IndexError:
    #         await message.channel.send(
    #             "You did not provide a time. Format must be '!reserveroom <time in minutes> [list of member mentions]'")
    #     except ValueError:
    #         await message.channel.send(
    #             'Time must be a positive number representing the number of minutes to reserve a room for')
    #     except AssertionError:
    #         await message.channel.send('Time must be between 0 and 360 (0 minutes to 6 hours)')
    #
    #     if not failed:
    #         if room_name not in [channel.name for channel in guild.voice_channels]:
    #
    #             async def ReserveRoom():
    #                 room_admin_role = await guild.create_role(name=f"{room_name}-admin")
    #
    #                 member_role = await guild.create_role(name=f"{room_name}-member")
    #                 everyone_role = discord.utils.get(guild.roles, name='@everyone')
    #                 await message.author.add_roles(room_admin_role)
    #                 for member in message.mentions:
    #                     if member != message.author:
    #                         await member.add_roles(member_role)
    #
    #                 voice_overwrites = {
    #                     everyone_role: discord.PermissionOverwrite(view_channel=False),
    #                     member_role: discord.PermissionOverwrite(view_channel=True),
    #                     room_admin_role: discord.PermissionOverwrite(view_channel=True, kick_members=True,
    #                                                                  mute_members=True,
    #                                                                  deafen_members=True)
    #                 }
    #
    #                 text_overwrites = {
    #                     everyone_role: discord.PermissionOverwrite(view_channel=False),
    #                     member_role: discord.PermissionOverwrite(view_channel=True),
    #                     room_admin_role: discord.PermissionOverwrite(view_channel=True, kick_members=True)
    #                 }
    #
    #                 voice_channel = await guild.create_voice_channel(f"{room_name}-voice", overwrites=voice_overwrites,
    #                                                                  category=discord.utils.get(guild.categories,
    #                                                                                             id=709173209722912779))
    #                 text_channel = await guild.create_text_channel(f"{room_name}-text", overwrites=text_overwrites,
    #                                                                category=discord.utils.get(guild.categories,
    #                                                                                           id=709173209722912779))
    #                 await message.channel.send(
    #                     f"Created {room_name}-text and {room_name}-voice\nReserved for {time / 60} min")
    #                 study_room_data = {
    #                     'name': room_name,
    #                     'voice_id': voice_channel.id,
    #                     'text_id': text_channel.id,
    #                     'admin_id': message.author.id,
    #                     'members_id': json.dumps(
    #                         [member.id for member in message.mentions if member != message.author]),
    #                     'created': datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    #                     'time_length': time
    #                 }
    #                 redisClient.hmset(f"{message.author.id}-study-room", study_room_data)
    #
    #                 miniRoomSet = {"admin_role": room_admin_role.id,
    #                                "member_role": member_role.id,
    #                                "voice_channel": voice_channel.id,
    #                                "text_channel": text_channel.id,
    #                                "message.author.id": message.author.id,
    #                                }
    #                 redisClient.hmset(str(text_channel.id), miniRoomSet)
    #                 await asyncio.sleep(time)
    #                 await room_admin_role.delete()
    #                 await member_role.delete()
    #                 await voice_channel.delete()
    #                 await text_channel.delete()
    #
    #                 redisClient.delete(f"{message.author.id}-study-room")
    #
    #             loop = asyncio.get_event_loop()
    #             roomThread = loop.create_task(ReserveRoom())
    #             await roomThread
    #         else:
    #             await message.channel.send(f"You already reserved {room_name}")
    # elif content_array[0] == '!members':
    #     guild = message.guild
    #     failed = True
    #
    #     try:
    #         study_room_data = redisClient.hgetall(f"{message.author.id}-study-room")
    #         room_name = study_room_data[b'name'].decode()
    #         failed = False
    #     except KeyError:
    #         await message.channel.send(
    #             "You do not have any study rooms reserved. You can create one with '!reserveroom <time in minutes> [list of member mentions]'")
    #
    #     if not failed:
    #         admin_role = discord.utils.get(guild.roles, name=f"{room_name}-admin")
    #         member_role = discord.utils.get(guild.roles, name=f"{room_name}-member")
    #
    #         if len(content_array) > 1:
    #             if content_array[1] == 'add':
    #                 new_members_list = json.loads(study_room_data[b'members_id'])
    #
    #                 if admin_role in message.author.roles:
    #                     for member in message.mentions:
    #                         if member != message.author:
    #                             await member.add_roles(member_role)
    #                             await message.channel.send(
    #                                 f"Added {member.display_name} to {room_name}-text and {room_name}-voice")
    #
    #                             new_members_list.append(member.id)
    #
    #                     new_study_room_data = study_room_data
    #                     new_study_room_data[b'members_id'] = json.dumps(new_members_list)
    #                     redisClient.hmset(f"{message.author.id}-study-room", new_study_room_data)
    #             else:
    #                 await message.channel.send(f"{content_array[1]} is not a valid argument. You can add a member to the room with '!members add [list of member mentions]'")
    #         else:
    #             if member_role in message.author.roles or admin_role in message.author.roles:
    #                 members_list = json.loads(study_room_data[b'members_id'])
    #                 response_message = f"Members in {room_name}: "
    #                 for member in members_list:
    #                     response_message = response_message + '\n' + discord.utils.get(message.guild.members,
    #                                                                                    id=member).display_name
    #                 if len(members_list) == 0:
    #                     response_message = response_message + 'None'
    #                 await message.channel.send(response_message)

#Write PID
pid = str(os.getpid())
pidfile = "bot.pid"

def writePID():
    print('writing file')
    f = open(pidfile, 'w')
    f.write(pid)
    f.close()

if os.path.isfile(pidfile):
    print("Process ID file already exists")
    sys.exit(1)
else:
    writePID()






#run
try:
    client.run(TOKEN)
except KeyboardInterrupt:
    print("Caught keyboard interrupt, killing and removing PID")
    os.remove(pidfile)
except:
    print("Removing PID file")
    os.remove(pidfile)
finally:
    sys.exit(0)