import os
import sys

import discord
from discord.ext import commands

# Bot Token
TOKEN = "NzA2Njc4Mzk2MzEwMjU3NzI1.Xq9v2A.iCXfvgwxz4fnmlrRUvTlA_JnSTA"

# Custom command cogs
from botCommands.administrative import Administrative
from botCommands.regular import Regular
from botCommands.studyrooms import StudyRooms

from botCommands.wtf import wtf

# Write PID
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

def main():
	bot = commands.Bot(command_prefix='!')
	bot.remove_command('help')
	bot.add_cog(Administrative(bot))
	bot.add_cog(Regular(bot))
	bot.add_cog(StudyRooms(bot))
	bot.add_cog(wtf(bot))
	bot.run(TOKEN)


if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		print("Caught keyboard interrupt, killing and removing PID")
		os.remove(pidfile)
	except:
		print("Removing PID file")
		os.remove(pidfile)
	finally:
		sys.exit(0)