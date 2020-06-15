import discord
import redis

#Creates an instance of the redis client
redisClient = redis.Redis(host='localhost', port=6379, db=0)


#Get pubsub instance
def db_get_pubsub():
    return redisClient.pubsub()

#Unmark a WatID
def db_unmarkWatID(watid):
    redisClient.delete(watid)

#Purge a user from database completely
def db_purgeUser(member: discord.Member):
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
def db_get(key):
    return redisClient.get(key).decode('utf-8')

#Sets a value in the redis db
def db_set(key, value):
    redisClient.set(key, value)

#Checks a value exists in the redis db
def db_exists(key):
    return redisClient.exists(key)

#Checks a value exists in the redis db
def db_delete(key):
    return redisClient.delete(key)


