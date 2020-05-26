import asyncio

import discord
import redis
import requests

TOKEN = "NzA2Njc4Mzk2MzEwMjU3NzI1.Xq9v2A.iCXfvgwxz4fnmlrRUvTlA_JnSTA"

client = discord.Client()
WATERLOO_API_KEY = "21573cf6bf679cdfb5eb47b51033daac"
WATERLOO_API_URL = "https://api.uwaterloo.ca/v2/directory/"
redisClient = redis.Redis(host='localhost', port=6379, db=0)

monitoredPhrases = ["What is the answer for", "How do you do the",
                    "Can someone help me with ", "What did you get for", "The answer is"]

toDelete = []


def getScore(phrase):
    url = "https://twinword-text-similarity-v1.p.rapidapi.com/similarity/"
    headers = {
        'x-rapidapi-host': "twinword-text-similarity-v1.p.rapidapi.com",
        'x-rapidapi-key': "2SsaMuQuizmshYf12uWzSIYMmOT3p1SS99BjsnMFkWGp7yyafH"
    }
    for monitorPhrase in monitoredPhrases:
        querystring = {"text1": phrase, "text2": monitorPhrase}
        response = requests.request("GET", url, headers=headers, params=querystring).json()
        print(response['similarity'])
        if (float(response['similarity']) >= 0.6): return True

    return False


@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord!')


@client.event
async def on_join(member):
    role = discord.utils.get(member.guild.roles, name="Unverified")
    await member.add_roles(role)


@client.event
async def on_message(message):
    content_array = message.content.split(" ")
    if (message.author == client.user):
        return
    # Test for policy violation
    if (redisClient.exists(str(message.channel.id))):
        async def startDeleteLoop():
            if (getScore(message.content)):
                await message.channel.send("<@" + str(
                    message.author.id) + "> Your message has been removed due to a possible policy violation.")
                await client.http.delete_message(message.channel.id, message.id)

        loop = asyncio.get_event_loop()
        deleteThread = loop.create_task(startDeleteLoop())
        await deleteThread


    elif content_array[0] == '!monitor':
        allowed = False
        for role in message.author.roles:
            if role.name == 'Admin':
                allowed = True
        if (allowed):
            if (redisClient.exists(str(message.channel.id))):
                redisClient.delete(str(message.channel.id))
                await message.channel.send("This channel is now no longer being monitored for policy violations.")
                return

            response = "This channel is being monitored for policy violations."
            await message.channel.send(response)
            redisClient.set(str(message.channel.id), "true")
    elif content_array[0] == '!ismonitored':
        try:
            if (redisClient.get(str(message.channel.id)).decode('utf-8')):
                await message.channel.send("This channel is currently being monitored for policy violations.")
            else:
                await message.channel.send("This channel is not currently being monitored for policy violations.")
        except:
            await message.channel.send("This channel is not currently being monitored for policy violations.")


client.run(TOKEN)
