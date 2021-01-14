import os
import sys
import logging
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands


# Custom command cogs
from botCommands.administrative import Administrative
from botCommands.regular import Regular
from botCommands.studyrooms import StudyRooms

# Write PID
pid = str(os.getpid())
pidfile = os.getenv("PID_FILE")

# Logfile customization
logging.basicConfig(filename='bot.log', filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


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


def main():
	bot = commands.Bot(command_prefix=os.getenv("PROD_PREFIX") if os.getenv("MODE") == "prod" else os.getenv("DEV_PREFIX"))
	bot.remove_command('help')
	bot.add_cog(Administrative(bot))
	bot.add_cog(Regular(bot))
	bot.add_cog(StudyRooms(bot))
	bot.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		print("Caught keyboard interrupt, killing and removing PID")
		os.remove(pidfile)
	except Exception as e:
		logging.error(str(e))
		print(str(e))
		print("Removing PID file")
		os.remove(pidfile)
	finally:
		sys.exit(0)