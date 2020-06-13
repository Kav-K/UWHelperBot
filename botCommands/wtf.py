import asyncio
import random

import discord
from discord.ext import commands

from botCommands.utils.utils import *

# Regular
class wtf(commands.Cog, name = 'wtf'):
    def __init__(self, bot):
        self.bot = bot

        # Not really sure what this does
        self._last_member_ = None

    @commands.command()
    async def throttle(self, ctx, member:discord.Member=None):
        if (permittedAdmin(ctx.author)):
            cycle = 0
            muteState = False

            while cycle < 20:
                state = random.randint(0, 20)
                if state <= 15:
                    if muteState:
                        await member.edit(mute = False)
                        await member.edit(deafen = True)
                        await asyncio.sleep(0.5)
                        muteState = False
                    else:
                        await member.edit(mute = True)
                        await member.edit(deafen = False)
                        await asyncio.sleep(0.5)
                        muteState = True
                cycle += 1


    @commands.command()
    async def roulette(self, ctx):

        # Get voice channel currently in
        if ctx.author.voice and ctx.author.voice.channel:
            currChannel = ctx.author.voice.channel

        maxInt = len(ctx.guild.voice_channels)
        channelIndex = random.randint(0, maxInt)

        await ctx.author.move_to(ctx.guild.voice_channels[channelIndex])
        await ctx.send("Good luck!")

    @commands.command()
    async def elevate(self, ctx, member:discord.Member=None):
        if (permittedAdmin(ctx.author)):
            # Get voice channel currently in
            if member.voice and member.voice.channel:
                currChannel = member.voice.channel

            # Get index in list (since it's ordered by UI)
            channelIdx = 0

            state = random.randint(0, 5)
            if state <= 3:
                await ctx.send("Hey, what does Grace's mom sell?")
                await asyncio.sleep(1)
                await ctx.send("What?")
                await asyncio.sleep(1)
                await ctx.send("Elevators :)")
            elif state == 4:
                await ctx.send("Hey Kaveen, what is a rhombus?")
                await asyncio.sleep(1)
                await ctx.send("No clue")
            elif state == 5:
                await ctx.send("Vroom vroom")
                await asyncio.sleep(1)
                await ctx.send("I'm Trent and I love car games")
                await asyncio.sleep(1)
                await ctx.send("Time for you to take a ride")
            
            # Get the index of the current channel
            for idx, channel in enumerate(ctx.guild.voice_channels):
                if channel == currChannel:
                    channelIdx = idx
                    break
            try:
                # Use the index to climb up the elevator
                for i in range(channelIdx, 0, -1):
                    await asyncio.sleep(0.5)
                    await member.move_to(ctx.guild.voice_channels[i])

                # Use the index to climb back down the elevator
                for i in range(0, channelIdx+1):
                    await asyncio.sleep(0.5)
                    await member.move_to(ctx.guild.voice_channels[i])
            except:
                return

            await ctx.send("Welcome Back!")