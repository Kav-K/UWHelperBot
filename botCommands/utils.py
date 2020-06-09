import discord
from lazy_streams import stream
import redis

redisClient = redis.Redis(host='localhost', port=6379, db=0)

ADMIN_ROLE_ID = 706658128409657366
TEACHING_STAFF_ROLE_ID = 709977207401087036


#Unmark a WatID
def redisUnmarkWatID(watid):
    redisClient.delete(watid)


#Purge a user from database completely
def redisPurge(member: discord.Member):
    try:
        watid = redisClient.get(str(member.id) + ".watid").decode('utf-8')
        redisClient.delete(watid)
        redisClient.delete(str(member) + ".watid")
        redisClient.delete(str(member.id) + ".watid")
        redisClient.delete(str(member.id) + ".verified")
        redisClient.delete(str(member) + ".verified")
        redisClient.delete(str(member) + ".name")
        redisClient.delete(str(member.id) + ".name")
        redisClient.delete(str(member))
        redisClient.delete(str(member.id) + ".request")
    except Exception as e:
        print(str(e))

#Send a DM
async def send_dm(member: discord.Member, content):
    channel = await member.create_dm()
    await channel.send(content)

#See if a user is permitted to run an admin command
def permittedAdmin(user):
    return ADMIN_ROLE_ID in stream(user.roles).map(lambda x: x.id).to_list()

#See if a user is teaching faculty
def permittedStaff(user):
    return TEACHING_STAFF_ROLE_ID in stream(user.roles).map(lambda x: x.id).to_list()