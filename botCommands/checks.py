from discord.ext import commands

banned_channels = ["faculty-general", "public-discussion", "offtopic", "general", "ece-109","ece-250","ece-204","ece-240","ece-222","co-op-general","interview-help","resume-help"]


def channel_check():
    """
    Checking if user is using bot in the right channels
    """
    async def predicate(ctx):
        if ctx.channel.name in banned_channels:
            await ctx.channel.send("To keep chat clean, you can't use this command in here! Please go to <#707029428043120721>")
            return False
        return True
    return commands.check(predicate)
