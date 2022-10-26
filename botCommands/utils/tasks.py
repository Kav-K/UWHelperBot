
import asyncio
from datetime import datetime, timedelta

from discord.ext import commands
from pytz import timezone

from botCommands.utils.utils import *
from botCommands.utils.redisutils import *
import requests
import random

import discord

ADMIN_THREAD_SLEEP = 10
STUDYROOMS_SLEEP = 10
REVOKATION_SLEEP = 10

# Periodically check if the users in the guild are temporarily revoked, if their revokation time has passed,
# give them access back again
async def RevokationService(guild):
    try:
        while True:

            # Retrieve the list of revoked user IDs for this guild
            revoked = db_list_get("revoked", guild)

            # For every member of the guild, check if the member has a active revokation
            for revoked_id in revoked:
                revoked_status = int(db_get("USER." + str(revoked_id) + ".revoked", guild).decode("utf-8"))

                if revoked_status is None or revoked_status != 1:
                    continue

                # If the revokation is active, check if the revokation time has passed
                revokation_time = int(db_get("USER." + revoked_id + ".revoked_expiry", guild))

                # Compare the current time timestamp to the revokation time
                if int(datetime.now().timestamp()) > int(revokation_time):
                    # If the revokation time has passed, give the user access back
                    db_set("USER." + revoked_id + ".revoked", 0, guild)
                    db_set("USER." + revoked_id + ".revoked_expiry", 0, guild)
                    await getChannel("admin-chat", guild).send("Revoked user <@" + revoked_id + "> has been given access back.")

                    # Get the member object using the MemberConverter and the revoked_id
                    member = await commands.MemberConverter().convert(guild, revoked_id)

                    # Give the user access back
                    await member.add_roles(getRole("Verified", guild))
                    await member.remove_roles(getRole("access-revoked-temp", guild))

                    # Send a DM to the user
                    await member.send("Your access to the server has been restored. Please read the rules and follow them.")

                    # Remove the ID from the list of revoked users
                    db_list_remove("revoked", revoked_id, guild)

            await asyncio.sleep(REVOKATION_SLEEP)
    except Exception as e:
        print("Error in RevokationService: " + str(e))
        await getChannel("admin-chat", guild).send("Error in RevokationService: " + str(e))



async def AdministrativeThread(guild):

    try:
        guestRole = getRole("Guest",guild)
        verifiedRole = getRole("Verified",guild)
        sec2Role = getRole("Section 2",guild)
        sec1Role = getRole("Section 1",guild)
        s8Role = getRole("Stream 8",guild)
        adminChannel = getChannel("admin-chat",guild)

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

            await asyncio.sleep(ADMIN_THREAD_SLEEP)

    except Exception as e:
        print("Error in AdministrativeThread: " + str(e))
        await getChannel("admin-chat",guild).send("Error in AdministrativeThread: " + str(e))


async def StudyRooms(guild):

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

            await asyncio.sleep(STUDYROOMS_SLEEP)
    except Exception as e:
        print(str(e))
        await getChannel("admin-chat",guild).send("ERROR: " + str(e))

