
import asyncio
from datetime import datetime, timedelta
from pytz import timezone

from botCommands.utils.utils import *
from botCommands.utils.redisutils import *
import requests
import random

import discord

ADMIN_THREAD_SLEEP = 5
COMM_THREAD_SLEEP = 1

# THESE FUNCTIONALITIES ARE A WORK IN PROGRESS CURRENTLY!
async def CommBroker(guild):
    print("Comm Broker started successfully.")

    #Get the subscriber message queue
    smSubscriber = db_get_pubsub(guild)
    smSubscriber.subscribe("smQueue")

    while True:
        db_set("totalUsers",len(guild.members),guild)
        db_set("totalOnline",len(stream(guild.members).filter(lambda x: x.status != discord.Status.offline).to_list()),guild)
        adminRole = getRole("Admin",guild)
        facultyRole = getRole("Teaching Staff",guild)
        botRole = getRole("Bot",guild)

        db_set("facultyOnline",len(stream(guild.members).filter(lambda x: facultyRole in x.roles).filter(lambda x: x.status != discord.Status.offline).to_list()),guild)
        db_set("adminOnline", len(stream(guild.members).filter(lambda x: adminRole in x.roles and botRole not in x.roles).filter(lambda x: x.status != discord.Status.offline).to_list()),guild)
        try:
            db_set("openTickets", len(getCategory("Open Tickets",guild).text_channels),guild)
        except Exception as e:
            pass


        for textChannel in guild.channels:
            if (db_exists(textChannel.name+".pendingMessages",guild)):
                messageToSend = db_get(textChannel.name+".pendingMessages",guild)
                db_delete(textChannel.name+".pendingMessages",guild)
                await textChannel.send(messageToSend)

        try:
            messageToBroadcast = smSubscriber.get_message()['data'].decode('utf-8')
            print(messageToBroadcast)
            await sendSubscriberMessage(messageToBroadcast,guild)
        except Exception as e:
            pass



        await asyncio.sleep(COMM_THREAD_SLEEP)

async def AdministrativeThread(guild):
    # ONLY FOR THE ECE 2024 SERVER!
    if (str(guild.id) != "706657592578932797"):
        return

    try:
        guestRole = getRole("Guest",guild)
        verifiedRole = getRole("Verified",guild)
        sec2Role = getRole("Section 2",guild)
        sec1Role = getRole("Section 1",guild)
        s8Role = getRole("Stream 8",guild)
        adminChannel = getChannel("bot-alerts",guild)

        while True:
            est = timezone('US/Eastern')
            currentTime = datetime.now().astimezone(est)

            #Remove verified role for professors!
            for member in guild.members:
                if (hasRoles(member, ["Teaching Staff","Verified"],guild)):
                    await member.remove_roles(verifiedRole)
                    await adminChannel.send("WARNING: The user <@"+str(member.id)+"> is teaching faculty and was found to have the Verified role. It has been removed.")


            #Remove section roles for guests, remove double section ranks.
            for member in guild.members:
                if (hasRoles(member,["Section 1","Stream 8"],guild) or hasRoles(member,["Section 2","Stream 8"],guild)):

                    await member.remove_roles(s8Role)
                    await adminChannel.send("WARNING: The user <@" + str(
                        member.id) + "> has duplicate roles. The user has been reset to the section 1 or 2 role. Stream 8 role has been removed.")


                if (hasRoles(member,["Section 1","Section 2"],guild)):
                    await member.remove_roles(sec1Role)
                    await adminChannel.send("WARNING: The user <@" + str(
                        member.id) + "> has duplicate roles. The user has been reset to the section 2 role. Section 1 role has been removed.")


                if (hasRoles(member,["Guest","Section 2"],guild) or hasRoles(member,["Guest","Section 1"],guild)):
                    print("Yeet")
                    await member.remove_roles(sec2Role) if sec2Role in member.roles else await member.remove_roles(sec1Role)
                    await adminChannel.send("WARNING: The user <@" + str(
                        member.id) + "> is a guest and was found to have a sectional rank. It has been removed.")


            # Manage study rooms
            room_list = redisClient.hgetall('room_list')
            unsanitized_study_rooms = getCategory("Study Rooms",guild).text_channels
            study_rooms = stream(unsanitized_study_rooms).filter(lambda x: "private" not in x.name.lower()).to_list()
            for study_room in study_rooms:
                try:
                    channel_data = redisClient.hgetall(room_list[study_room.name.replace('-text', '').encode()].decode())
                    channel_data = dict((k.decode('utf8'), v.decode('utf8')) for k, v in channel_data.items())

                    expiry_time = datetime.strptime(channel_data['expiry'], "%Y-%m-%dT%H:%M:%S.%fZ")
                    time_difference = expiry_time - datetime.now()

                    if time_difference < timedelta():
                        text_channel = getChannel(int(channel_data['text_id']),guild)
                        voice_channel = getChannel(int(channel_data['voice_id']),guild)

                        admin_role = getRole(int(channel_data['admin_role_id']),guild)

                        member_role = getRole(int(channel_data['member_role_id']),guild)

                        new_room_list = redisClient.hgetall('room_list')

                        del new_room_list[channel_data['name'].encode()]

                        if len(new_room_list) == 0:

                            db_delete('room_list',guild)
                        else:
                            redisClient.hmset('room_list', new_room_list)

                        db_delete(room_list[study_room.name.replace('-text', '').encode()].decode(),guild)
                        await text_channel.delete()
                        await voice_channel.delete()
                        await member_role.delete()
                        await admin_role.delete()


                    elif timedelta(minutes=1) < time_difference < timedelta(minutes=1, seconds=ADMIN_THREAD_SLEEP):
                        await study_room.send(f"{study_room.name.replace('-text', '')} will be deleted in 1 minute")

                    elif timedelta(minutes=10) < time_difference < timedelta(minutes=10, seconds=ADMIN_THREAD_SLEEP):
                        await study_room.send(f"{study_room.name.replace('-text', '')} will be deleted in 10 minutes")

                    elif timedelta(hours=1) < time_difference < timedelta(hours=1, seconds=ADMIN_THREAD_SLEEP):
                        await study_room.send(f"{study_room.name.replace('-text', '')} will be deleted in 1 hour")

                except Exception as e:
                    print(e)

            await asyncio.sleep(ADMIN_THREAD_SLEEP)
    except Exception as e:
        print(str(e))
        await getChannel("admin-chat",guild).send("ERROR: " + str(e))


async def WellnessFriend(guild):
    if (str(guild.id) != "706657592578932797"):
        return

    try:
        while True:
            messagesArray = requests.get("https://type.fit/api/quotes").json()
            selectedMessage = messagesArray[random.randint(0, len(messagesArray) - 1)]
            inspirationalMessage = str(selectedMessage["text"]) + "\n - " + str(selectedMessage["author"])

            # Using this as a reference: https://uwaterloo.ca/registrar/important-dates/entry?id=180
            finalExamDate = datetime.strptime("2021-04-26", "%Y-%m-%d")
            encouragingMessage = "Don't forget, we've got " + str(
                (finalExamDate - datetime.now()).days) + " days until this is all over."

            wellnessMessage = "Hey ECE peeps!!\n\nHere's your inspirational QOTD: \n\n" + "" if inspirationalMessage is None else inspirationalMessage + \
                                                                                                                                  "\n\nPlease know that if you need any support, people are there for you: \n" \
                                                                                                                                  "Counselling Services - 519-888-4567 ext. 32655\n" \
                                                                                                                                  "Mates - mates@wusa.ca\n" \
                                                                                                                                  "Here 24/7 - 1-844-437-3247\n" \
                                                                                                                                  "Health Services - Student Medical Clinic - 519-888-4096\n" \
                                                                                                                                  "Grand River Hospital - 519-749-4300\n" \
                                                                                                                                  "St. Mary's Hospital - 519-744-3311\n" \
                                                                                                                                  "Good2Talk - 1-866-925-5454\n" \
                                                                                                                                  "Crisis Services Canada - 1-833-456-4566 or by text 45645\n\n"
            await getChannel("wellness", guild).send(wellnessMessage + encouragingMessage)

            # Interval in seconds
            if db_get("WELLNESS_INTERVAL", guild) is not None:
                await asyncio.sleep(int(db_get("WELLNESS_INTERVAL", guild)))

    except Exception as e:
        print(str(e))
        await getChannel("admin-chat", guild).send("ERROR: " + str(e))
