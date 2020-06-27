import discord
from lazy_streams import stream
global GUILD
from botCommands.utils.redisutils import *
GUILD = None

#TODO PUT THESE INTO A SETTINGS/CONFIG
ADMIN_ROLE_NAME = "Admin"
TEACHING_STAFF_ROLE_NAME = "Teaching Staff"


#Get all subscribed members to notifications
def getSubscribers():
    return stream(GUILD.members).filter(lambda x: db_exists(str(x.id) + ".subscribed") and db_get(str(x.id) + ".subscribed") == "true").to_list()

#Send a subscriber message
async def sendSubscriberMessage(message):
    subscriberList = getSubscribers()
    message = message.replace("\\n", "\n")
    messageToEdit = await getChannel("admin-chat").send(
        "Sending notifications to subscribed members. Status: [0/" + str(len(subscriberList)) + "]")
    await getChannel("admin-chat").send("The message was: \n"+message)
    for x, subscriber in enumerate(subscriberList):
        await messageToEdit.edit(content="Sending notifications to subscribed members. Status: [" + str(x) + "/" + str(
            len(subscriberList)) + "]")
        try:
            await send_dm(subscriber, message)
        except Exception as e:
            await getChannel("admin-chat").send("Could not send a message to <@" + str(subscriber.id) + ">: " + str(e))

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


#Return the global GUILD object
def getGuild():
    global GUILD
    return GUILD
def setGuild(inputGuild):
    global GUILD
    print("Got guild set request to: "+str(inputGuild))
    GUILD = inputGuild


#Get a category by identifier
def getCategory(categoryIdentifier):
    if (type(categoryIdentifier) == int):
        return discord.utils.get(GUILD.categories,id=categoryIdentifier)
    else:
        return discord.utils.get(GUILD.categories,name=categoryIdentifier)

#Get channel by identifier
def getChannel(channelIdentifier):
    if (type(channelIdentifier) == int):
        return discord.utils.get(GUILD.channels,id=channelIdentifier)
    else:
        return discord.utils.get(GUILD.channels,name=channelIdentifier)

#Return a single role given a identifier
def getRole(roleIdentifier):
    if (type(roleIdentifier) == int):
        return discord.utils.get(GUILD.roles, id=roleIdentifier)
    else:
        return discord.utils.get(GUILD.roles, name=roleIdentifier)


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

#Send a DM
async def send_dm(member: discord.Member, content):
    channel = await member.create_dm()
    await channel.send(content)

#See if a user is permitted to run an admin command
def permittedAdmin(user):
    return ADMIN_ROLE_NAME in stream(user.roles).map(lambda x: x.name).to_list()

#See if a user is teaching faculty
def permittedStaff(user):
    return TEACHING_STAFF_ROLE_NAME in stream(user.roles).map(lambda x: x.name).to_list()