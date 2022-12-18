import os
import sys
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands

# Custom command cogs
from botCommands.administrative import Administrative
from botCommands.regular import Regular
from botCommands.studyrooms import StudyRooms
	
command_prefix = os.getenv("COMMAND_PREFIX", '!') if os.getenv("DEV_MODE") is not None else os.getenv("DEV_PREFIX", '>')

def main():
	if os.getenv("DISCORD_TOKEN") is None: sys.exit("Discord API token not specified, use DISCORD_TOKEN environmnet variable")
	intents = discord.Intents.default()
	intents.members = True
	intents.message_content = True
	bot = commands.Bot(command_prefix=command_prefix, intents=intents)
	bot.remove_command('help')
	bot.add_cog(Administrative(bot))
	bot.add_cog(Regular(bot))
	bot.add_cog(StudyRooms(bot))
	bot.run(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
	main()
