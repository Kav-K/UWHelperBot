import asyncio
import json
import redis

from datetime import datetime
from datetime import timedelta

import discord
from discord.ext import commands

redisClient = redis.Redis(host='localhost', port=6379, db=0)

# Study Rooms
class StudyRooms(commands.Cog, name='Study Room Commands'):
    def __init__(self, bot):
        self.bot = bot

        # Not really sure what this does
        self._last_member_ = None

    @commands.command()
    async def closeroom(self, ctx):
        author = ctx.message.author
        guild = ctx.message.guild
        allowed = False

        for role in author.roles:
            if role.name == 'Admin':
                allowed = True

        if allowed:
            room_list = redisClient.hgetall('room_list')
            study_room = ctx.message.channel
            if study_room.name.replace('-text', '') in room_list:
                study_room = redisClient.hgetall(room_list[study_room.name.replace('-text', '').encode()].decode())

                text_channel = discord.utils.get(guild.text_channels,
                                                 id=int(study_room[b'text_id'].decode('utf-8')))
                voice_channel = discord.utils.get(guild.voice_channels,
                                                  id=int(study_room[b'voice_id'].decode('utf-8')))
                admin_role = discord.utils.get(guild.roles,
                                               id=int(study_room[b'admin_role_id'].decode('utf-8')))
                member_role = discord.utils.get(guild.roles,
                                                id=int(study_room[b'member_role_id'].decode('utf-8')))
                new_room_list = redisClient.hgetall('room_list')
                del new_room_list[study_room[b'name']]

                if len(new_room_list) == 0:
                    redisClient.delete('room_list')
                else:
                    redisClient.hmset('room_list', new_room_list)

                redisClient.delete(room_list[study_room.name.replace('-text', '').encode()].decode())
                await text_channel.delete()
                await voice_channel.delete()
                await member_role.delete()
                await admin_role.delete()
            else:
                await ctx.send("This is not a study room!")
        else:
            await ctx.send("You are not allowed to use this command, <@" + str(author.id) + ">!")

    @commands.command()
    async def room(self, ctx, *args):
        channel = ctx.message.channel
        guild = ctx.message.guild
        author = ctx.message.author
        room_name = f"{author.display_name.replace(' ', '-').lower()}-study-room"
        failed = True

        if args[0] == 'create':
            try:
                assert redisClient.hgetall(f"{author.id}-study-room") == {}, 'room exists'
                time = float(args[1])
                assert 0 < time <= 720, 'invalid time'
                failed = False
            except IndexError:
                await channel.send('You did not specify a time')
            except ValueError:
                await channel.send('Time must be an integer or decimal number representing time in minutes')
            except AssertionError as e:
                if str(e) == 'invalid time':
                    await channel.send('Time must be between 0 and 720 minutes')
                else:
                    await channel.send(f"You already have a study room created ({room_name})")

            if not failed:
                members = ctx.message.mentions
                room_admin_role = await guild.create_role(name=f"{room_name}-admin")
                member_role = await guild.create_role(name=f"{room_name}-member")
                everyone_role = discord.utils.get(guild.roles, name='@everyone')

                await author.add_roles(room_admin_role)
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
                await channel.send(
                    f"Created {room_name}-text and {room_name}-voice\nReserved for {time} min")

                print((datetime.now() + timedelta(minutes=time)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
                assert (isinstance((datetime.now() + timedelta(minutes=time)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), str))

                study_room_data = {
                    'name': room_name,
                    'voice_id': voice_channel.id,
                    'text_id': text_channel.id,
                    'admin_id': author.id,
                    'admin_role_id': room_admin_role.id,
                    'member_role_id': member_role.id,
                    'members_id': json.dumps(
                        [member.id for member in members if member != author]),
                    'created': datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    'expiry': (datetime.now() + timedelta(minutes=time)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                }
                try:
                    redisClient.hmset(f"{author.id}-study-room", study_room_data)
                    room_list = redisClient.hgetall('room_list')
                    room_list[room_name] = f"{author.id}-study-room"
                    redisClient.hmset('room_list', room_list)
                except Exception as e:
                    print(e)
                    await text_channel.delete()
                    await voice_channel.delete()
                    await member_role.delete()
                    await room_admin_role.delete()

        elif args[0] == 'time':
            try:
                study_room = redisClient.hgetall(f"{author.id}-study-room")
                expiry_time = datetime.strptime(study_room[b'expiry'].decode(), "%Y-%m-%dT%H:%M:%S.%fZ")
                time_remaining = expiry_time - datetime.now()

                await channel.send(f"{study_room[b'name'].decode()} will expire at "
                                   f"{expiry_time.strftime('%H:%M:%S')}.\nYou have "
                                   f"{time_remaining.seconds // 60} min remaining.")

            except KeyError:
                await channel.send(f"You do not have a study room created")

        elif args[0] == 'extend':
            try:
                study_room = redisClient.hgetall(f"{author.id}-study-room")
                created_time = datetime.strptime(study_room[b'created'].decode(), "%Y-%m-%dT%H:%M:%S.%fZ")
                expiry_time = datetime.strptime(study_room[b'expiry'].decode(), "%Y-%m-%dT%H:%M:%S.%fZ")
                time = float(args[1])
                assert 0 < time <= 720, 'invalid time'
                new_time = expiry_time + timedelta(minutes=time)
                assert new_time < created_time + timedelta(days=1), 'max time'

                study_room[b'expiry'] = new_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                redisClient.hmset(f"{author.id}-study-room", study_room)

                await channel.send(f"{room_name}'s lifespan extended by {time} min and will expire at "
                                   f"{new_time.strftime('%H:%M:%S')}.\nYou have "
                                   f"{(new_time - datetime.now()).seconds // 60} min remaining.")

            except KeyError:
                await channel.send(f"You do not have a study room created")
            except IndexError:
                await channel.send('You did not specify a time')
            except ValueError:
                await channel.send('Time must be an integer or decimal number representing time in minutes')
            except AssertionError as e:
                if str(e) == 'invalid time':
                    await channel.send('Time must be between 0 and 720 minutes')
                else:
                    await channel.send(f"{room_name}'s lifespan cannot pass 24 hours and must expire before"
                                       f"{(created_time + timedelta(days=1)).strftime('%H:%M:%S')}")

        elif args[0] == 'add':
            try:
                members = ctx.message.mentions
                study_room = redisClient.hgetall(f"{author.id}-study-room")
                member_role = discord.utils.get(guild.roles,
                                                id=int(study_room[b'member_role_id'].decode('utf-8')))
                new_members_list = json.loads(study_room[b'members_id'])
                assert len(members) > 0

                for member in members:
                    if member != author:
                        if member.id not in new_members_list:
                            await member.add_roles(member_role)
                            await channel.send(f"Added {member.display_name} to {room_name}-text and {room_name}-voice")
                            new_members_list.append(member.id)
                        else:
                            await channel.send(f"{member.display_name} is already a member of {room_name}")

                    new_study_room = study_room
                    new_study_room[b'members_id'] = json.dumps(new_members_list)
                    redisClient.hmset(f"{author.id}-study-room", new_study_room)
            except KeyError:
                await channel.send(f"You do not have a study room created")
            except AssertionError:
                await channel.send(f"You did not have any mention members")

        elif args[0] == 'remove':
            try:
                members = ctx.message.mentions
                study_room = redisClient.hgetall(f"{author.id}-study-room")
                member_role = discord.utils.get(guild.roles,
                                                id=int(study_room[b'member_role_id'].decode('utf-8')))
                new_members_list = json.loads(study_room[b'members_id'])
                assert len(members) > 0

                for member in members:
                    if member != author:
                        if member.id in new_members_list:
                            await member.remove_roles(member_role)
                            await channel.send(
                                f"Removed {member.display_name} from {room_name}-text and {room_name}-voice")
                            new_members_list.remove(member.id)
                        else:
                            await channel.send(
                                f"{member.display_name} is not a member of {room_name}")

                    new_study_room = study_room
                    new_study_room[b'members_id'] = json.dumps(new_members_list)
                    redisClient.hmset(f"{author.id}-study-room", new_study_room)
            except KeyError:
                await channel.send(f"You do not have a study room created")
            except AssertionError:
                await channel.send(f"You did not have any mention members")

        elif args[0] == 'members':
            try:
                study_room = redisClient.hgetall(f"{author.id}-study-room")
                members_list = json.loads(study_room[b'members_id'])
                if len(members_list) > 0:
                    response_message = f"Members in {room_name}: "
                    for member in members_list:
                        response_message = response_message + '\n' + discord.utils.get(guild.members,
                                                                                       id=member).display_name
                else:
                    response_message = f"There are no members in {room_name}"
                await channel.send(response_message)
            except KeyError:
                await channel.send(f"You do not have a study room created")

        elif args[0] == 'help':
            response_message = 'Here are the following commands for study rooms:\n' \
                               '- !room create <time> [mentions]\n' \
                               '- !room time\n' \
                               '- !room extend <time>\n' \
                               '- !room add [mentions]\n' \
                               '- !room remove [mentions]\n' \
                               '- !room members\n\n' \
                               'Example: !room create 60 @Feridun @Math\n\n' \
                               'Note: All commands can be used in any text channel. ' \
                               'When adding members to the room, use #general-bot or any channel that ' \
                               'the members are already a part of.'

            await channel.send(response_message)
