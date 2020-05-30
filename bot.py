import asyncio
import json
import os
import random
import sys
import urllib.request
from datetime import datetime
from datetime import timedelta

import discord
from discord.ext import commands

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

# Custom command cogs

# from botCommands.administrative import Administrative
# from botCommands.regular import Regular
# from botCommands.studyrooms import StudyRooms

# Administrative
class Administrative(commands.Cog, name = 'Administrative'):
	def __init__(self, bot):
		self.bot = bot

		# Not really sure what this does
		self._last_member_ = None

	@commands.Cog.listener()
	async def on_ready(self):
		print(f'{bot.user.name} has connected to Discord!')

	@commands.Cog.listener()
	async def on_member_join(self, member):
		role = discord.utils.get(member.guild.roles, name="Unverified")
		await member.add_roles(role)

	@commands.command()
	async def verify(self, ctx, watid):
		try:

			messageAuthor = ctx.author

			if (redisClient.exists(str(messageAuthor) + ".request")):
				response = "<@" + str(
					messageAuthor.id) + "> There is already a pending verification request for your WatID, \
										please use `!confirm <code>` or do `!cancelverification`"
				await ctx.send(response)
				return
			# Ask UW API for information
			apiResponse = requests.get(WATERLOO_API_URL + watid + ".json?key=" + WATERLOO_API_KEY).json()
			email = apiResponse['data']['email_addresses'][0]
			name = apiResponse['data']['full_name']
			user_id = apiResponse['data']['user_id']
			if (apiResponse['data']['department'] != "ENG/Electrical and Computer"):
				response = "<@" + str(
					messageAuthor.id) + "> You are not an ECE student! \
										Please manually validate by contacting \
										the admin team. The admin team has been \
										notified of this incident. <@&706658128409657366>"
				await ctx.send(response)
				return
			if (len(apiResponse['data']['telephone_numbers']) > 0):
				response = "<@" + str(
					messageAuthor.id) + "> You are a faculty member, and faculty members \
										require manual validation by an administrative team member. \
										Please contact the administration team by messaging them directly, \
										or send an email to k5kumara@uwaterloo.ca."
				await ctx.send(response)
				return;
			if (redisClient.exists(str(messageAuthor) + ".verified")):
				if (int(redisClient.get(str(messageAuthor) + ".verified")) == 1):
					response = "<@" + str(messageAuthor.id) + "> You have already been verified"
					await ctx.send(response)
					return
			if (redisClient.exists(str(user_id))):
				if (int(redisClient.get(str(user_id))) == 1):
					response = "<@" + str(
						messageAuthor.id) + "> This user_id has already been verified. Not you? Contact an admin."
					await ctx.send(response)
					return

			# Mark
			redisClient.set(str(messageAuthor) + ".watid", user_id)
			redisClient.set(str(messageAuthor) + ".verified", 0)
			redisClient.set(str(messageAuthor) + ".name", name)

			# Generate random code
			code = random.randint(1000, 9999)
			redisClient.set(str(messageAuthor), code)

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
				messageAuthor.id) + "> I sent a verification code to " + email + ". Find the code \
									in your email and type `!confirm <code>` in discord to verify \
									your account. Please check your spam and junk folders."
			redisClient.set(str(messageAuthor) + ".request", 1)

			await ctx.send(response)
		except Exception as e:
			print(e)
			response = "<@" + str(
				messageAuthor.id) + "> No WatID provided or invalid watID, please use `!verify <watid>`.\
									 Your WatID is the username in your original email, for example, in \
									 k5kumara@edu.uwaterloo.ca, the watID is k5kumara."
			await ctx.send(response)

	@commands.command()
	async def confirm(self, ctx, *args):
		try:
			messageAuthor = ctx.author

			code = args[0]

			if (redisClient.exists(str(messageAuthor) + ".request")):

				if (int(code) == int(redisClient.get(str(messageAuthor)))):
					response = "<@" + str(messageAuthor.id) + "> You were successfully verified."

					await ctx.send(response)

					nickname = redisClient.get(str(messageAuthor) + ".name")

					await messageAuthor.edit(nick=str(nickname.decode('utf-8')))

					# Mark user and WatID as verified
					redisClient.set(str(messageAuthor) + ".verified", 1)
					redisClient.set(str(redisClient.get(str(mmessageAuthor) + ".watid").decode('utf-8')), 1)
					redisClient.delete(str(messageAuthor) + ".request")
					# 706966831268626464
					role = discord.utils.get(ctx.guild.roles, name="Verified")
					unverifiedRole = discord.utils.get(ctx.guild.roles, name="Unverified")
					await messageAuthor.add_roles(role)

					try:
						messageAuthor.remove_roles(unverifiedRole)
					except:
						print("TODO: handle remove_role exception")
				else:
					response = "<@" + str(messageAuthor.id) + "> Invalid verification code."
					await ctx.send(response)
			else:
				response = "<@" + str(
					messageAuthor.id) + "> You do not have a pending verification request, \
										please use `!verify <WATID>` to start."
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
		if (redisClient.exists(str(messageAuthor) + ".request")):
			response = "<@" + str(
				messageAuthor.id) + "> Cancelled your on-going verification, please try again with `!verify <watid>`"
			await ctx.send(response)
		else:
			response = "<@" + str(messageAuthor.id) + "> You do not have a verification in progress"
			await ctx.send(response)

	@commands.command()
	async def devalidate(self, ctx, *args):

		messageAuthor = ctx.author

		allowed = False
		for role in messageAuthor.roles:
			if role.name == 'Admin':
				allowed = True
		if (allowed):
			try:
				selection = args[0]
				if (selection == "user"):
					user = ctx.message.mentions[0]
					watid = redisClient.get(str(user) + ".watid").decode('utf-8')
					redisClient.delete(watid)
					await ctx.send("Unmarked WatID "+watid)
					redisClient.delete(str(user)+".watid")
					await ctx.send("Purged WatID")
					redisClient.delete(str(user) + ".verified")
					await ctx.send("Purged verified status")
					redisClient.delete(str(user) + ".name")
					await ctx.send("Purged legal name")
					redisClient.delete(str(messageAuthor))
					redisClient.delete(str(user)+".request")
					await ctx.send("Purged request status")
					await ctx.send("Purged user from database successfully.")

				elif (selection == "watid"):
					watid = args[1]
					redisClient.delete(watid)
					await ctx.send("Unmarked WatID "+watid)
				else:
					await ctx.send("<@"+str(messageAuthor.id)+"> Invalid selection! You can choose to devalidate a user or a WatID.")
			except:
				print("<@+"+str(messageAuthor.id)+"> Invalid syntax or selection: `!devalidate <select 'user' or 'watid'> <value>`")

	@commands.command()
	async def correlate(self, ctx, *args):

		messageAuthor = ctx.author

		allowed = False
		for role in messageAuthor.roles:
			if role.name == 'Admin':
				allowed = True
		if (allowed):
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
					await ctx.send("Invalid WatID: "+watid)
					return

				redisClient.set(str(user) + ".watid", watid)
				await ctx.send("WatID "+watid+" has been validated and correlated to <@"+str(user.id)+">")
				if ("Verified" in ranks):
					redisClient.set(str(user) + ".verified", 1)
					await ctx.send("<@" + str(user.id) + "> has been set to Verified status")
				redisClient.set(str(user) + ".name", name)
				await user.edit(nick=name)
				await ctx.send(
					"Name " + name + " has been validated and correlated to <@" + str(user.id) + ">")
				redisClient.set(str(redisClient.get(str(messageAuthor) + ".watid").decode('utf-8')), 1)
				await ctx.send(
					"The WatID " + watid + " has been marked for no further verifications.")


				#Set ranks
				isTeaching = False
				for role in user.roles:
					if role.name == 'Teaching Staff' or role.name == "Professor" or role.name == "Teaching Assistant":
						isTeaching = True
				if (isTeaching):
					if ("Verified" in ranks or "Guest" in ranks):
						await ctx.send("<@"+str(messageAuthor.id)+"> You may not apply your selected roles to this person.")
						return
				try:
					rank_array = ranks.split(",")
					for rank in rank_array:
						if (rank == ""): break
						if ("_" in rank):
							rank = rank.replace("_"," ")
						rankToGive = discord.utils.get(ctx.message.guild.roles, name=rank.strip())

						await user.add_roles(rankToGive)

						await ctx.send("Added " + rank + " role to <@" + str(user.id) + ">")

				except Exception as e:

					await user.add_roles(discord.utils.get(ctx.message.guild.roles,name=ranks.strip()))



				await ctx.send("All tasks completed successfully")
			except Exception as e:
				print(str(e))
				print('t4')
				await ctx.send("<@"+str(messageAuthor.id)+"> You have entered invalid syntax, or the user you are trying to correlate is invalid. `!correlate <USER MENTION> <WatID>`")
	
	@commands.command()
	async def daplookup(self, ctx, *args):

		messageAuthor = ctx.author

		allowed = False
		for role in messageAuthor.roles:
			if role.name == 'Admin' or role.name == 'Professor':
				allowed = True

		if (allowed):
			try:

				watid = args[0]

				if ("@" in args[0]):

					# Find user's discord tag
					for member in ctx.message.mentions:
						discordID = str(member)
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

		messageAuthor = ctx.author

		allowed = False
		for role in messageAuthor.roles:
			if role.name == 'Admin':
				allowed = True
		if (allowed):
			verifiedRole = discord.utils.get(ctx.message.guild.roles, name="Verified")
			unverifiedRole = discord.utils.get(ctx.message.guild.roles, name="Unverified")
			adminRole = discord.utils.get(ctx.message.guild.roles, name="Admin")
			teachingRole = discord.utils.get(ctx.message.guild.roles, name="Teaching Staff")

			memberList = ctx.message.guild.members
			for member in memberList:
				if (verifiedRole in member.roles and unverifiedRole in member.roles):
					await ctx.send("Removed unverified role from " + member.name)
					await member.remove_roles(unverifiedRole)
				elif (
						verifiedRole not in member.roles and unverifiedRole not in member.roles and adminRole not in member.roles and teachingRole not in member.roles):
					await ctx.send("Added unverified role to " + member.name)
					await member.add_roles(unverifiedRole)
			await ctx.send("All role validations completed successfully.")
from discord.ext import commands

# Regular
class Regular(commands.Cog, name = 'Regular'):
	def __init__(self, bot):
		self.bot = bot

		# Not really sure what this does
		self._last_member_ = None

	@commands.command()
	async def helpme(self, ctx):
		embed = discord.Embed(title="Commands", description="Here are a list of commands for the stream 4 bot",
							  color=0x800080)
		embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
		embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
		embed.add_field(name="!textbooks", value="Get a link to the textbooks and shared resources", inline=False)
		embed.add_field(name="!upcoming", value="Get a list of upcoming due dates for the next 7 days", inline=False)
		embed.add_field(name="!verify <watid>", value="Verify your account to use this discord", inline=False)
		embed.add_field(name="!piazza", value="Get our relevant piazza links", inline=False)
		embed.add_field(name="!schedule <OPTIONAL (course number)>", value="View a continuously updating class/lab schedule, or specify a course code for a more specific content/labs/etc schedule.", inline=False)
		embed.add_field(name="!importantdates", value="Get a full calendar with important dates and due dates",
						inline=False)
		embed.add_field(name="=help", value="Activate the MathBot", inline=False)
		embed.add_field(name="=tex <LATEX>", value="Create a LaTeX equation", inline=False)
		embed.add_field(name="=wolf <QUERY>", value="Use the wolfram engine to search something up or calculate", inline=False)
		embed.add_field(name="!assignments <140 OR 124>", value="View assignment questions for 124 and 140 from the textbook", inline=False)
		embed.add_field(name="!breakdown <course number>", value="View the grading scheme breakdown for a course", inline=False)
		await ctx.send(embed=embed)
	
	@commands.command()
	async def textbooks(self, ctx):
		embed = discord.Embed(title="Textbooks & Resources",
							  description="Here is a dropbox link for our collective resources. Feel free to contact the admin team if you'd like to add to it.",
							  color=0x800080)
		embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
		embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
		embed.add_field(name="Link", value="https://www.dropbox.com/sh/tg1se0xab9c9cfc/AAAdJJZXi1bkkHUoW5oYT_EAa?dl=0",
						inline=False)
		await ctx.send(embed=embed)

	@commands.command()
	async def upcoming(self, ctx):
		if (ctx.channel.name in banned_channels):
			await ctx.channel.send("To keep chat clean, you can't use this command in here! Please go to <#707029428043120721>")
			return

		dateMap = {}
		dateList = []

		# Opens the URL
		calendar = urllib.request.urlopen(
			'https://calendar.google.com/calendar/ical/k5kumara%40edu.uwaterloo.ca/public/basic.ics')
		gcal = Calendar.from_ical(calendar.read())
		dateRangeEnd = datetime.now() + timedelta(days=7)

		# Iterate through components inside of the calendar
		for component in gcal.walk():
			# Checks the event type
			if component.name == "VEVENT":

				# Populates info
				summary = component.get('summary')
				startdate = component.get('dtstart').dt
				enddate = component.get('dtend').dt
				# print(summary)

				# Initialize timezone
				est = timezone('US/Eastern')

				finalStartDate, finalEndDate = None, None
				try:
					finalStartDate = startdate.replace(tzinfo=pytz.utc).astimezone(est)
					finalEndDate = enddate.replace(tzinfo=pytz.utc).astimezone(est)
				except:
					finalStartDate = datetime(year=startdate.year, month=startdate.month, day=startdate.day, hour=4,
											  minute=0).astimezone(est)
					finalEndDate = datetime(year=enddate.year, month=enddate.month, day=enddate.day, hour=4,
											minute=0).astimezone(est)

				# Configures the message with the dates
				finalMessage = str(
					finalStartDate.strftime("%A, %B %d at %-I:%M %p")) + " to " + str(
					finalEndDate.strftime("%A, %B %d at %-I:%M %p") + ";" + summary)

				# Create a sorted mapping between date and message
				if (datetime.now().date() <= finalStartDate.date() <= dateRangeEnd.date()):
					if (finalStartDate not in dateMap):
						dateMap[finalStartDate] = []
					if (finalStartDate not in dateList):
						dateList.append(finalStartDate)
					dateMap[finalStartDate].append(finalMessage)
		dateList.sort()
		embed = discord.Embed(title="Upcoming Important Dates",
							  description="These are all upcoming quizzes, due dates, and other important dates. Please contact the admin team if there are any issues.",
							  color=0x800080)
		embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
		embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")

		for idate in dateList:
			for messageToSend in dateMap[idate]:
				messageArray = messageToSend.split(";")
				embed.add_field(name=messageArray[0], value=messageArray[1], inline=False)
		await ctx.send(embed=embed)

		# Closes the page
		calendar.close()

	@commands.command()
	async def schedule(self, ctx, *args):
		try:
			selection = args[0]
			if (ctx.message.channel.name in banned_channels):
				await ctx.send(
					"To keep chat clean, you can't use this command in here! Please go to <#707029428043120721>")
				return
			if (selection == "119"):
				embed = discord.Embed()
				embed.add_field(name="MATH 119",
								value="Here is a schedule of topics, tests, quizzes, and assignments for MATH 119",
								inline=False)
				embed.set_image(url="https://i.imgur.com/fd56XUE.png")
				await ctx.send(embed=embed)
				embed2 = discord.Embed()
				embed2.set_image(url="https://i.imgur.com/FgRAdMt.png")
				await ctx.send(embed=embed2)
			elif (selection == "106"):
				embed = discord.Embed()
				embed.add_field(name="ECE 106",
								value="Here is a schedule of topics, labs, tests, quizzes, and assignments for ECE 106",
								inline=False)
				embed.set_image(url="https://i.imgur.com/BPhpXxp.png")
				await ctx.send(embed=embed)
				embed2 = discord.Embed()
				embed2.set_image(url="https://i.imgur.com/3HbKvvf.png")
				await ctx.send(embed=embed2)
				embed3 = discord.Embed()
				embed3.set_image(url="https://i.imgur.com/cw9S7GY.png")
				await ctx.send(embed=embed3)
				embed4 = discord.Embed()
				embed4.add_field(name="Quizzes",
								value="Quizzes are every monday from 12AM to midnight.",
								inline=False)
				await ctx.send(embed=embed4)
			elif (selection == "140"):
				embed = discord.Embed()
				embed.add_field(name="ECE 140",
								value="Here is a schedule of topics, labs, tests, quizzes, and assignments for ECE 140",
								inline=False)
				embed.set_image(url="https://i.imgur.com/YCJQw41.png")
				await ctx.send(embed=embed)
			elif (selection == "124"):
				embed = discord.Embed()
				embed.add_field(name="ECE 124",
								value="Here is a schedule of topics, labs, tests, quizzes, and assignments for ECE 124",
								inline=False)
				embed.set_image(url="https://i.imgur.com/mHRB3Cs.png")
				await ctx.send(embed=embed)
			elif (selection == "108"):
				embed = discord.Embed()
				embed.add_field(name="ECE 108",
								value="Here is a schedule of topics, labs, tests, quizzes, and assignments for ECE 108",
								inline=False)
				embed.set_image(url="https://i.imgur.com/rMqY50F.png")
				await ctx.send(embed=embed)
			elif (selection == "192"):
				embed = discord.Embed()
				embed.add_field(name="ECE 192",
								value="Here is a schedule of topics, labs, tests, quizzes, and assignments for ECE 192",
								inline=False)
				embed.set_image(url="https://i.imgur.com/icdO1m5.png")
				await ctx.send(embed=embed)
			else:
				await ctx.send("<@" + str(
					messageAuthor.id) + "> You must enter a valid course to view a specific course schedule, valid entries are `140`, `124`, `106`, `119`, `192`, and `108`. Type the command without any options to get a lecture and live session calendar.")

		except:
			embed = discord.Embed(title="Class Schedule",
								  description="Here is a link to a calendar with class schedules for live lectures and Q&A Sessions. Please contact the admin team if there is anything missing.",
								  color=0x800080)
			embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
			embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
			embed.add_field(name="Link",
							value="https://calendar.google.com/calendar/embed?src=ag2veuvcsc5k4kaqpsv7sp7e04%40group.calendar.google.com&ctz=America%2FToronto",
							inline=False)
			await ctx.send(embed=embed)

	@commands.command()
	async def breakdown(self, ctx, *args):
		messageAuthor = ctx.author
		try:
			selection = args[0]
			if (selection == "140"):
				embed = discord.Embed()
				embed.add_field(name="ECE 140",
								value="Here is a marking scheme breakdown for ECE 140",
								inline=False)
				embed.set_image(url="https://i.imgur.com/g2BVcrv.png")
				await ctx.send(embed=embed)
			elif (selection == "124"):
				embed = discord.Embed()
				embed.add_field(name="ECE 124",
								value="Here is a marking scheme breakdown for ECE 124",
								inline=False)
				embed.set_image(url="https://i.imgur.com/0ivd7nu.png")
				await ctx.send(embed=embed)
			elif (selection == "106"):
				embed = discord.Embed()
				embed.add_field(name="ECE 106",
								value="Here is a marking scheme breakdown for ECE 106",
								inline=False)
				embed.set_image(url="https://i.imgur.com/mX5DQGf.png")
				await ctx.send(embed=embed)
			elif (selection == "108"):
				embed = discord.Embed()
				embed.add_field(name="ECE 108",
								value="Here is a marking scheme breakdown for ECE 108",
								inline=False)
				embed.set_image(url="https://i.imgur.com/yXTkxiO.png")
				await ctx.send(embed=embed)
			elif (selection == "192"):
				embed = discord.Embed()
				embed.add_field(name="ECE 192",
								value="Here is a marking scheme breakdown for ECE 192",
								inline=False)
				embed.set_image(url="https://i.imgur.com/RZrHshS.png")
				await ctx.send(embed=embed)
			elif (selection == "119"):
				embed = discord.Embed()
				embed.add_field(name="MATH 119",
								value="Here is a marking scheme breakdown for MATH 119",
								inline=False)
				embed.set_image(url="https://i.imgur.com/lOXxjlo.png")
				await ctx.send(embed=embed)
			else:

				await ctx.send("<@" + str(messageAuthor.id) + "> You must enter a valid course to view a course marking scheme breakdown, valid entries are `140`, `124`, `106`, `119`, `192`, and `108`")
		except:
			await ctx.send("<@" + str(messageAuthor.id) + "> You must enter a course to view a course marking scheme breakdown, valid entries are `140`, `124`, `106`, `119`, `192`, and `108`")
	
	@commands.command()
	async def assignments(self, ctx, *args):
		if (ctx.message.channel.name in banned_channels):
			await ctx.send("To keep chat clean, you can't use this command in here! Please go to <#707029428043120721>")
			return
		try:
			selection = args[0]

			if (selection == "140"):
				embed = discord.Embed()
				embed.add_field(name="ECE 140",
								value="Here are the week-based assignment questions for ECE 140",
								inline=False)
				embed.set_image(url="https://i.imgur.com/H9X2rru.png")
				await ctx.send(embed=embed)
			elif (selection =="124"):
				embed = discord.Embed()
				embed.add_field(name="ECE 124",
								value="Here are the week-based assignment questions for ECE 124",
								inline=False)
				embed.set_image(url="https://i.imgur.com/ipSz35S.png")
				await ctx.send(embed=embed)
			else:
				await ctx.send("<@"+str(messageAuthor.id)+"> you've made an invalid selection! The available courses to view assignments for are `140` and `124`")

		except:
			await ctx.send("<@"+str(messageAuthor.id)+"> You must enter a course to view assignment sets for, valid entries are `140` and `124`")
	
	@commands.command()
	async def piazza(self, ctx):
		embed = discord.Embed(title="Piazza Links", description="Here are our relevant piazza links.", color=0x800080)
		embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
		embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
		embed.add_field(name="FYE", value="https://piazza.com/class/k9rmr76sakf74o", inline=False)
		embed.add_field(name="ECE 140", value="https://piazza.com/class/k9u2in2foal48e", inline=False)
		embed.add_field(name="MATH 119", value="https://piazza.com/class/k8ykzmozh5241x", inline=False)
		embed.add_field(name="ECE 124", value="https://piazza.com/class/k9eqk9mfo1qy3?cid=1", inline=False)
		await ctx.send(embed=embed)

	@commands.command()
	async def importantdates(self, ctx):
		embed = discord.Embed(title="Due/Important Dates",
							  description="Here is a link to a calendar with important dates. Please contact the admin team if there is anything missing",
							  color=0x800080)
		embed.set_footer(text="An ECE 2024 Stream 4 bot :)")
		embed.set_thumbnail(url="https://i.imgur.com/UWyVzwu.png")
		embed.add_field(name="Link",
						value="https://calendar.google.com/calendar/embed?src=k5kumara%40edu.uwaterloo.ca&ctz=America%2FToronto",
						inline=False)
		await ctx.send(embed=embed)

from discord.ext import commands

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


#Write PID
#pid = str(os.getpid())
#pidfile = "bot.pid"
#
#def writePID():
#	print('writing file')
#	f = open(pidfile, 'w')
#	f.write(pid)
#	f.close()
#if os.path.isfile(pidfile):
#	print("Process ID file already exists")
#	sys.exit(1)
#else:
#	writePID()



#run
#try:
	# client.run(TOKEN)
	# Defines the command portion of the bot
bot = commands.Bot(command_prefix='!')
bot.add_cog(Administrative(bot))
bot.add_cog(Regular(bot))
bot.add_cog(StudyRooms(bot))
bot.run(TOKEN)
#except KeyboardInterrupt:
#	print("Caught keyboard interrupt, killing and removing PID")
#	os.remove(pidfile)
#except:
#	print("Removing PID file")
#	os.remove(pidfile)
#finally:
#	sys.exit(0)