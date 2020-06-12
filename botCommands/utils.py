import discord
from lazy_streams import stream
import redis
#TODO CLEAN THESE DATABASE THINGS UP
redisClient = redis.Redis(host='localhost', port=6379, db=0)
global GUILD
GUILD = None

#TODO PUT THESE INTO A SETTINGS/CONFIG
ADMIN_ROLE_ID = 706658128409657366
TEACHING_STAFF_ROLE_ID = 709977207401087036

#Check if a user has a set of roles
def hasRoles(memberToCheck,roleNames):
    if (len(roleNames)< 2):
        return getRole(roleNames[0]) in memberToCheck.roles
    else:
        mappedRoles = stream(roleNames).map(lambda x: getRole(x)).to_list()
        return set(mappedRoles).issubset(memberToCheck.roles)

#Self explanatory
def isVerified(memberToCheck):
    return getRole("Verified") in memberToCheck.roles

def setGuild(inputGuild):
    global GUILD
    print("Got guild set request to: "+str(inputGuild))
    GUILD = inputGuild

#Return a single role given a name
def getRole(roleName):
    return discord.utils.get(GUILD.roles,name=roleName)

#Get all members or get members with a specific set of roles
def getMembers(roles=[]):
    if (len(roles)<1):
        return GUILD.members
    else:
        mappedRoles = stream(roles).map(lambda x: getRole(x)).to_list()
        membersWithRoles = stream(GUILD.members).filter(lambda x: set(mappedRoles).issubset(x.roles)).to_list()
        return membersWithRoles

#Paginate a list!
def paginate(toPaginate, linesToPaginate=20):
    paginated = []

    for count, line in enumerate(toPaginate):
        if count != 0 and count % linesToPaginate == 0:
            yield paginated
            paginated.clear()
        else:
            paginated.append(str(line))

    yield paginated

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