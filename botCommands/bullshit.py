import discord
from discord.ext import commands


# bullshit
class bullshit(commands.Cog, name='Bullshit'):
    def __init__(self, bot):
        self.bot = bot

        # Not really sure what this does
        self._last_member_ = None

    @commands.command()
    async def trentslate(self, ctx, *args):
        trentDictionary = {}

        trentDictionary["im blue imma be im daie"] = 'https://www.youtube.com/watch?v=HgV1O0X4uXI'
        trentDictionary[
            "HERBO WTFWUA?"] = 'https://open.spotify.com/track/1MAF77bjR5toanBgnsMQ8k?si=kVMlN2tFQbyd3iSQKfGShw'
        trentDictionary["the googs"] = 'http://google.com'

        phrase = " ".join(args)

        if phrase == "?phrases":
            await ctx.send(trentDictionary.keys())

        try:
            await ctx.send(trentDictionary[phrase])
        except KeyError:
            await ctx.send("That isn't a supported Trent phrase")
