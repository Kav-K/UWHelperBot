import discord
from discord.ext import commands

# bullshit
class bullshit(commands.Cog, name = 'Bullshit'):
	def __init__(self, bot):
		self.bot = bot

		# Not really sure what this does
		self._last_member_ = None

	@commands.command()
	async def trentslate(self, ctx, *args):

		phrase = " ".join(args)

		trentDictionary = {}

		trentDictionary["im blue imma be im daie"] = 'https://www.youtube.com/watch?v=HgV1O0X4uXI'

		try:
			print(phrase)
			await ctx.send(trentDictionary[phrase])
		except:
			await ctx.send("That isn't a supported Trent phrase")



