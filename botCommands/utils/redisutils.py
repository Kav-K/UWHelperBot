import os
import discord
import redis

redisClient = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0)
#Creates an instance of the redis client
DATABASE_HARD_LIMIT = 50
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
                if db_exists("USER." + userID + ".verified",_guild) and db_get("USER." + userID + ".verified",_guild) == "1":
                    userInfo["firstName"] = db_get("USER." + userID + ".firstname",_guild)
                    userInfo["lastName"] = db_get("USER." + userID + ".lastname", _guild)
                    userInfo["department"] = db_get("USER." + userID + ".department", _guild)
                    userInfo["commonNames"] = db_get("USER." + userID + ".commonnames", _guild)
                    userInfo["emails"] = db_get("USER." + userID + ".emails", _guild)
                    userInfo["watID"] = db_get("USER." + userID + ".watid", _guild)
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

def db_set_watid_info(watID, guild, firstName, lastName, department, commonNames, emails, verifiedonguild):
    db_set("WATID." + watID + ".firstname", firstName, guild)
    db_set("WATID." + watID + ".lastname", lastName, guild)
    db_set("WATID." + watID + ".department", department, guild)
    db_set("WATID." + watID + ".commonnames", commonNames, guild)
    db_set("WATID." + watID + ".emails", emails, guild)
    db_set("WATID." + watID + ".verifiedonguild", verifiedonguild, guild)

def db_set_user_info(userID, guild, watID, firstName, lastName, department, commonNames, emails, verified):
    db_set("USER." + userID + ".watid", watID, guild)
    db_set("USER." + userID + ".firstname", firstName, guild)
    db_set("USER." + userID + ".lastname", lastName, guild)
    db_set("USER." + userID + ".department", department, guild)
    db_set("USER." + userID + ".commonnames", commonNames, guild)
    db_set("USER." + userID + ".emails", emails, guild)
    db_set("USER." + userID + ".verified", verified, guild)


#Purge a user from database completely
def db_purgeUser(member: discord.Member,guild):
    try:
        watid = database_instances[guild.id].get("USER." + str(member.id) + ".watid").decode('utf-8')

        #Delete User Data
        database_instances[guild.id].delete("USER." + str(member.id) + ".watid")
        database_instances[guild.id].delete("USER." + str(member.id) + ".firstname")
        database_instances[guild.id].delete("USER." + str(member.id) + ".lastname")
        database_instances[guild.id].delete("USER." + str(member.id) + ".department")
        database_instances[guild.id].delete("USER." + str(member.id) + ".commonnames")
        database_instances[guild.id].delete("USER." + str(member.id) + ".emails")
        database_instances[guild.id].delete("USER." + str(member.id) + ".verified")

        #Delete WatID Datta
        database_instances[guild.id].delete("WATID." + watid + ".firstname")
        database_instances[guild.id].delete("WATID." + watid + ".lastname")
        database_instances[guild.id].delete("WATID." + watid + ".department")
        database_instances[guild.id].delete("WATID." + watid + ".commonnames")
        database_instances[guild.id].delete("WATID." + watid + ".emails")
        database_instances[guild.id].delete("WATID." + watid + ".verifiedonguild")


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

# Append a value to a key in the database, comma separated
def db_append(key, value,guild):
    if db_exists(key, guild):
        previous_value = db_get(key, guild)
        db_set(key, previous_value + "," + value,guild)
    else:
        db_set(key, value,guild)

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


