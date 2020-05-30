import asyncio
import json
import redis

from datetime import datetime
from datetime import timedelta

import discord
from discord.ext import commands

redisClient = redis.Redis(host='localhost', port=6379, db=0)

# Study Rooms
class StudyRooms(commands.Cog, name = 'Study Room Commands'):
	def __init__(self, bot):
		self.bot = bot

		# Not really sure what this does
		self._last_member_ = None

	@commands.command()
	async def closeroom(self, ctx):
		allowed = False
		for role in messageAuthor.roles:
			if role.name == 'Admin':
				allowed = True

		if (allowed):
			if (redisClient.exists(str(ctx.message.channel.id))):
				miniRoom = redisClient.hgetall(str(ctx.message.channel.id))

				text_channel = discord.utils.get(ctx.message.guild.text_channels,
												 id=int(miniRoom[b'text_channel'].decode('utf-8')))
				voice_channel = discord.utils.get(ctx.message.guild.voice_channels,
												  id=int(miniRoom[b'voice_channel'].decode('utf-8')))
				admin_role = discord.utils.get(ctx.message.guild.roles, id=int(miniRoom[b'admin_role'].decode('utf-8')))
				member_role = discord.utils.get(ctx.message.guild.roles, id=int(miniRoom[b'member_role'].decode('utf-8')))
				redisClient.delete(str(ctx.message.channel.id))
				await text_channel.delete()
				await voice_channel.delete()
				await member_role.delete()
				await admin_role.delete()

				redisClient.delete(f"{miniRoom[b'messageAuthor.id'].decode('utf-8')}-study-room")
			else:
				await ctx.send("This is not a study room!")
		else:
			await ctx.send("You are not allowed to use this command, <@" + str(messageAuthor.id) + ">!")


	@commands.command()
	async def reserveroom(self, ctx, *args):
		guild = ctx.message.guild
		room_name = f"{messageAuthor.display_name.replace(' ', '-').lower()}-study-room"
		failed = True

		try:
			time = float(args[0]) * 60

			assert (time > 0.0 and time < 21600)
			failed = False
		except IndexError:
			await ctx.send(
				"You did not provide a time. Format must be '!reserveroom <time in minutes> [list of member mentions]'")
		except ValueError:
			await ctx.send(
				'Time must be a positive number representing the number of minutes to reserve a room for')
		except AssertionError:
			await ctx.send('Time must be between 0 and 360 (0 minutes to 6 hours)')

		if not failed:
			if room_name not in [channel.name for channel in guild.voice_channels]:

				async def ReserveRoom():
					room_admin_role = await guild.create_role(name=f"{room_name}-admin")

					member_role = await guild.create_role(name=f"{room_name}-member")
					everyone_role = discord.utils.get(guild.roles, name='@everyone')
					await messageAuthor.add_roles(room_admin_role)
					for member in ctx.message.mentions:
						if member != messageAuthor:
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
					await ctx.send(
						f"Created {room_name}-text and {room_name}-voice\nReserved for {time / 60} min")
					study_room_data = {
						'name': room_name,
						'voice_id': voice_channel.id,
						'text_id': text_channel.id,
						'admin_id': messageAuthor.id,
						'members_id': json.dumps(
							[member.id for member in ctx.message.mentions if member != messageAuthor]),
						'created': datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
						'time_length': time
					}
					redisClient.hmset(f"{messageAuthor.id}-study-room", study_room_data)

					miniRoomSet = {"admin_role": room_admin_role.id,
								   "member_role": member_role.id,
								   "voice_channel": voice_channel.id,
								   "text_channel": text_channel.id,
								   "messageAuthor.id": messageAuthor.id,
								   }
					redisClient.hmset(str(text_channel.id), miniRoomSet)
					await asyncio.sleep(time)
					await room_admin_role.delete()
					await member_role.delete()
					await voice_channel.delete()
					await text_channel.delete()

					redisClient.delete(f"{messageAuthor.id}-study-room")

				loop = asyncio.get_event_loop()
				roomThread = loop.create_task(ReserveRoom())
				await roomThread
			else:
				await ctx.send(f"You already reserved {room_name}")
	
	@commands.command()
	async def members(self, ctx, *args):
		guild = ctx.message.guild
		failed = True

		try:
			study_room_data = redisClient.hgetall(f"{messageAuthor.id}-study-room")
			room_name = study_room_data[b'name'].decode()
			failed = False
		except KeyError:
			await ctx.send(
				"You do not have any study rooms reserved. You can create one with '!reserveroom <time in minutes> [list of member mentions]'")

		if not failed:
			admin_role = discord.utils.get(guild.roles, name=f"{room_name}-admin")
			member_role = discord.utils.get(guild.roles, name=f"{room_name}-member")

			if len(args) > 1:
				if args[0] == 'add':
					new_members_list = json.loads(study_room_data[b'members_id'])

					if admin_role in messageAuthor.roles:
						for member in ctx.message.mentions:
							if member != messageAuthor:
								await member.add_roles(member_role)
								await ctx.send(
									f"Added {member.display_name} to {room_name}-text and {room_name}-voice")

								new_members_list.append(member.id)

						new_study_room_data = study_room_data
						new_study_room_data[b'members_id'] = json.dumps(new_members_list)
						redisClient.hmset(f"{messageAuthor.id}-study-room", new_study_room_data)
				else:
					await ctx.send(f"{args[0]} is not a valid argument. You can add a member to the room with '!members add [list of member mentions]'")
			else:
				if member_role in messageAuthor.roles or admin_role in messageAuthor.roles:
					members_list = json.loads(study_room_data[b'members_id'])
					response_message = f"Members in {room_name}: "
					for member in members_list:
						response_message = response_message + '\n' + discord.utils.get(ctx.message.guild.members,
																					   id=member).display_name
					if len(members_list) == 0:
						response_message = response_message + 'None'
					await ctx.send(response_message)