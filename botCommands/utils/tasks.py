
import asyncio
from datetime import datetime, timedelta
from pytz import timezone

from botCommands.utils.utils import *
from botCommands.utils.redisutils import *

import discord

ADMIN_THREAD_SLEEP = 5
COMM_THREAD_SLEEP = 1


async def CommBroker(guild):
    print("Comm Broker started successfully.")

    #Get the subscriber message queue
    smSubscriber = db_get_pubsub()
    smSubscriber.subscribe("smQueue")

    while True:
        db_set("totalUsers",len(guild.members))
        db_set("totalOnline",len(stream(guild.members).filter(lambda x: x.status != discord.Status.offline).to_list()))
        adminRole = getRole("Admin")
        facultyRole = getRole("Teaching Staff")
        botRole = getRole("Bot")

        db_set("facultyOnline",len(stream(guild.members).filter(lambda x: facultyRole in x.roles).filter(lambda x: x.status != discord.Status.offline).to_list()))
        db_set("adminOnline", len(stream(guild.members).filter(lambda x: adminRole in x.roles and botRole not in x.roles).filter(lambda x: x.status != discord.Status.offline).to_list()))
        db_set("openTickets", len(getCategory("Open Tickets").text_channels))

        for textChannel in guild.channels:
            if (db_exists(textChannel.name+".pendingMessages")):
                messageToSend = db_get(textChannel.name+".pendingMessages")
                db_delete(textChannel.name+".pendingMessages")
                await textChannel.send(messageToSend)

        try:
            messageToBroadcast = smSubscriber.get_message()['data'].decode('utf-8')
            print(messageToBroadcast)
            await sendSubscriberMessage(messageToBroadcast)
        except Exception as e:
            error = e










        await asyncio.sleep(COMM_THREAD_SLEEP)

async def AdministrativeThread(guild):
    guestRole = getRole("Guest")
    verifiedRole = getRole("Verified")
    sec2Role = getRole("Section 2")
    sec1Role = getRole("Section 1")
    adminChannel = getChannel("bot-alerts")

    while True:
        est = timezone('US/Eastern')
        currentTime = datetime.now().astimezone(est)

        #Remove verified role for professors!
        for member in guild.members:
            if (hasRoles(member, ["Teaching Staff","Verified"])):
                await member.remove_roles(verifiedRole)
                await adminChannel.send("WARNING: The user <@"+str(member.id)+"> is teaching faculty and was found to have the Verified role. It has been removed.")


        #Remove section roles for guests, remove double section ranks.
        for member in guild.members:
            if (hasRoles(member,["Section 1","Section 2"])):
                await member.remove_roles(sec1Role)
                await adminChannel.send("WARNING: The user <@" + str(
                    member.id) + "> has duplicate roles. The user has been reset to the section 2 role. Section 1 role has been removed.")


            if (hasRoles(member,["Guest","Section 2"]) or hasRoles(member,["Guest","Section 1"])):
                await member.remove_roles(sec2Role) if sec2Role in member.roles else await member.remove_roles(sec1Role)
                await adminChannel.send("WARNING: The user <@" + str(
                    member.id) + "> is a guest and was found to have a sectional rank. It has been removed.")

            #Expire memberships for temporary guests

            if (db_exists(str(id)+".guestExpiry")):
                stringExpiryTime = db_get(str(id)+".guestExpiry")
                print("The user: "+str(member)+" has a pending membership expiry date: "+stringExpiryTime)
                #2020-05-30 09:46:59.610027-04:00
                stringExpiryTime = stringExpiryTime.replace("-04:00","")
                #TODO make this into a function in utils.py
                expiryDate = datetime.strptime(stringExpiryTime,"%Y-%m-%d %H:%M:%S.%f").astimezone(est) + timedelta(hours=4) #fuck timezones

                if (expiryDate <= currentTime):
                    await member.remove_roles(guestRole)
                    await member.remove_roles(verifiedRole)
                    db_delete(str(id)+".guestExpiry")


        # Manage study rooms
        room_list = redisClient.hgetall('room_list')
        unsanitized_study_rooms = getCategory(709173209722912779).text_channels
        study_rooms = stream(unsanitized_study_rooms).filter(lambda x: "private" not in x.name.lower()).to_list()
        for study_room in study_rooms:
            try:
                channel_data = redisClient.hgetall(room_list[study_room.name.replace('-text', '').encode()].decode())
                channel_data = dict((k.decode('utf8'), v.decode('utf8')) for k, v in channel_data.items())

                expiry_time = datetime.strptime(channel_data['expiry'], "%Y-%m-%dT%H:%M:%S.%fZ")
                time_difference = expiry_time - datetime.now()

                if time_difference < timedelta():
                    text_channel = getChannel(int(channel_data['text_id']))
                    voice_channel = getChannel(int(channel_data['voice_id']))

                    admin_role = getRole(int(channel_data['admin_role_id']))

                    member_role = getRole(int(channel_data['member_role_id']))

                    new_room_list = redisClient.hgetall('room_list')

                    del new_room_list[channel_data['name'].encode()]

                    if len(new_room_list) == 0:

                        db_delete('room_list')
                    else:
                        redisClient.hmset('room_list', new_room_list)

                    db_delete(room_list[study_room.name.replace('-text', '').encode()].decode())
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