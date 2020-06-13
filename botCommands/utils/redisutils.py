import discord
import redis

#Creates an instance of the redis client
redisClient = redis.Redis(host='localhost', port=6379, db=0)

#Unmark a WatID
def redisUnmarkWatID(watid):
    redisClient.delete(watid)

#Purge a user from database completely
def redisPurgeUser(member: discord.Member):
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

#Performs a get request and decodes
def redisGet(key):
    return redisClient.get(key).decode('utf-8')

def redisSet(key, value):
