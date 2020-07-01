import discord
import redis
#Creates an instance of the redis client
DATABASE_HARD_LIMIT = 15
database_instances = {}
redisClient = redis.Redis(host='localhost',port=6379)



def redisSetGuilds(GUILDS):
    for GUILD in GUILDS:
        for x in range(0, DATABASE_HARD_LIMIT):
            try:
                redisClient = redis.Redis(host='localhost', port=6379, db=x)
                if (redisClient.get("SERVER_ID").decode('utf-8') == str(GUILD.id)):
                    database_instances[GUILD.id] = redisClient
                    print("Successfully found a matching database: "+str(x))
            except Exception as e:
                print(str(e))
                continue

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
    return database_instances[guild.id].get(key).decode('utf-8')

#Sets a value in the redis db
def db_set(key, value,guild):
    database_instances[guild.id].set(key, value)

#Checks a value exists in the redis db
def db_exists(key,guild):
    return database_instances[guild.id].exists(key)

#Checks a value exists in the redis db
def db_delete(key,guild):
    return database_instances[guild.id].delete(key)


