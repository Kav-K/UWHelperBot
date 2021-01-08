import os
import discord
import redis

redisClient = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0)
#Creates an instance of the redis client
DATABASE_HARD_LIMIT = 25
database_instances = {}
database_instances_identifier = {}


def redisSetGuilds(GUILDS):
    for GUILD in GUILDS:
        for x in range(0, DATABASE_HARD_LIMIT):
            try:
                redisClient = redis.Redis(host='localhost', port=6379, db=x)
                if (redisClient.get("SERVER_ID").decode('utf-8') == str(GUILD.id)):
                    database_instances[GUILD.id] = redisClient
                    database_instances_identifier[GUILD.id] = x
                    print("Successfully found a matching database: "+str(x))
            except Exception as e:
                print(str(e))
                continue

def search(userID, GUILDS):
    userID = str(userID)
    userInfo = {}
    userInfo["status"] = False
    for x in range(0,DATABASE_HARD_LIMIT):
        try:
            for _guild in GUILDS:
                if db_exists(userID+".verified",_guild) and db_get(userID+".verified",_guild) == "1":
                    userInfo["name"] = db_get(userID+".name",_guild)

                    userInfo["watID"] = db_get(userID+".watid",_guild)
                    userInfo["guild"] = _guild.name
                    userInfo["status"] = True

                    break
        except Exception as e:
            userInfo["status"] = False
            print(str(e))
    return userInfo


def getCorrespondingDatabase(guild):
    return database_instances_identifier[guild.id]

#Get pubsub instance
def db_get_pubsub(guild):
    return database_instances[guild.id].pubsub()

#Unmark a WatID
def db_unmarkWatID(watid,guild):
    database_instances[guild.id].delete(watid)

#Purge a user from database completely
def db_purgeUser(member: discord.Member,guild):
    try:
        watid = database_instances[guild.id].get(str(member.id) + ".watid").decode('utf-8')
        database_instances[guild.id].delete(watid)
        database_instances[guild.id].delete(str(member) + ".watid")
        database_instances[guild.id].delete(str(member.id) + ".watid")
        database_instances[guild.id].delete(str(member.id) + ".verified")
        database_instances[guild.id].delete(str(member) + ".verified")
        database_instances[guild.id].delete(str(member) + ".name")
        database_instances[guild.id].delete(str(member.id) + ".name")
        database_instances[guild.id].delete(str(member))
        database_instances[guild.id].delete(str(member.id) + ".request")
    except Exception as e:
        print(str(e))


#Performs a get request and decodes
def db_get(key,guild):
    if (db_exists(key,guild)):
        return database_instances[guild.id].get(key).decode('utf-8')
    else:
        print("Unable to find the database key: "+key+" for the guild "+guild.name)
        return None

#Sets a value in the redis db
def db_set(key, value,guild):
    database_instances[guild.id].set(key, value)

#Checks a value exists in the redis db
def db_exists(key,guild):
    return database_instances[guild.id].exists(key)

#Checks a value exists in the redis db
def db_delete(key,guild):
    return database_instances[guild.id].delete(key)

def db_disconnect(guild):
    database_instances[guild.id].quit()

def db_disconnect_all():
    for x in range(DATABASE_HARD_LIMIT):
        redisClient = redis.Redis(host='localhost', port=6379, db=x)
        try:
            redisClient.close()
        except:
            pass


