
# Stream4Bot

A user verification system and online instruction utility for the University of Waterloo. Used by 5,000+ students and various official courses.


# UWaterloo API V2 Deprecation Notice and Changes

As of the end of 2020, the UWaterloo API v2 was meant to be deprecated. This deprecation means that the user directory feature will not work. The bot will not be able to retrieve a full name, verify a WatID, or retrieve departments/email addresses from UWaterloo.

The bot has been adjusted for these changes and a v3 version is ready to merge as soon as the v2 api fully shuts down. Verification will still be seamless and automatic, but the bot will not be able to verify that input WatIDs are correct, so users are encouraged to pay attention to their verification process and make sure they enter the correct WatID.

Apart from the latter, most other bot features remain unchanged (with the exception of !ldaplookup and the ability to automatically change someone's discord nickname to their full name).

I've tried my best to create a solution that retains as many features from before the deprecation as possible, and the bot will still fully support the v2 features up until the day the endpoint is shut down.

# Overview

The Stream4Bot (Now renamed to UWaterloo Helper) was originally created as a way to verify Discord users with the University of Waterloo. The bot takes in a WatID and will connect to the UWaterloo Open Data Initiative to obtain information about the WatID, send a verification email to the email belonging to the WatID, and when the user types the verification code back into discord, they will be verified and given access to all of the channels, and their discord name will be changed to the one on file by the University of Waterloo

The bot was also created with more features in mind, such as a system for showing students upcoming due dates and live lectures (using google calendars), a reminder and announcement system that people can subscribe to, and features that provide students with information about course syllabi and assignments, making this a fully fledged online instruction tool for Discord.

# User Commands
<b>!verify [WATID]</b> - Send a verification code to the specified WatID

<b>!confirm <CODE></b> - Confirm the verification code

<b>!textbooks</b> - Get a link to the textbooks relevant to the term

<b>!upcoming</b> - Show the upcoming due dates and important dates for the next 7 days from the current time (reads from a google calendar that an administrative team would contribute to

<b>!schedule [COURSE CODE]</b> - Show a schedule for a specific course based on provided course outlines. Provide no course code and receive a general schedule for everything

<b>!importantdates </b> - Show a schedule for important dates such as due dates, lab start/end dates, and etc

<b>!breakdown [COURSE CODE]</b> - Show a course marking scheme for the specified course code

<b>!examinfo</b> - Show midterm and final exam information for the term

<b>!room create [TIME]</b> - Create a temporary study room (a pair of personalized voice and text channels for the specified amount of time

<b>!closeroom</b> - Close the study room

<b>!members</b> - View members of the study room

<b>!members add @[USER]</b> - Add a member to the study room

<b>!members remove @[USER]</b> - Remove a member from the study room

# Admin Commands
<b>!correlate @[USER] [WATID] [STRING LIST OF RANKS]</b> - Associate a discord user to a 		  WatID, and provide them with specific roles. This command will correlate the user to the WatID in the database, mark their WatID as verified, and set their discord name to the one on file by the University of Waterloo

<b>!daemon</b> - Force a manual start of the administrative daemon threads

<b>!validateroles</b> - Iterate through all the users of the discord server and do role validations (remove duplicate roles, ensure role-locking, make sure every verified user has an associated WatID)

<b>!guest @[USER] [TIME IN SECONDS]</b> - Provide a user with temporary guest access to the server for the specified amount of time

<b>!subscribers</b> - List everybnody currently subscribed to notifications

<b>!sm [MESSAGE]</b> Send a subscriber message to everybody subscribed to notifications

<b>!ldaplookup @[USER/WatID]</b> - Ask the UW API for information on a specific discord user or WatID

<b>!lockdown</b> - Restrict all channels, create a new lockdown chat and allow users to only chat in there. This was used for examination periods

<b>!lock</b> - Temporarily make the channel that you run this command on read-only

<b>!devalidate [user/watid] [USER/WATID]</b> - Remove a WatID or a user verification from the system


# Architecture
There are three main parts to this system:

### Communications Broker
The communications broker handles communication with the PHP-driven web interface. It regularly uploads data about online users, online teaching staff, etc into redis, which the web interface reads when needed. It will also listen for pending subscriber messages that were dispatched from the web interface and will send them out to users on the server when detected. The communications broker is in a very elementary stage currently and will have lots of additions as the web interface grows in complexity and functionality. **There is one communications broker per guild**

### Administrative Thread
The administrative thread is a interval-driven process that performs various checks on the server to make sure everything is functioning smoothly. Here are some of the things that it will check for;

 - Duplicate roles
 - Role-lock failures (e.g teaching staff having access to student channels and vice versa)
 - Guest timers (it will check that online guests are valid and their memberships haven't expired, if they have expired, it will remove the guest role and devalidate them again
 - Keeps track of study rooms, sends expiry reminders, deletes them on expiry, and does cleanup

### Main Discord Bot
The bread and butter of the program, handles all commands, startup functionality, and exit functionality. 

### General Information
The way that this bot functions independently of the server that it's operating on is with Redis. There is a separate Redis database for each server, before a server can be used with the bot, the server must be activated and registered with the Redis system on the host machine of the bot. Each redis database has a SERVER_ID identifying key. For example, redis database 0 would have SERVER_ID = "706657592578932797", the ID of the ECE 2024 server.

Upon startup, the bot initializes a connection handler to each of these databases and saves them in a mapping for quick access later and to prevent the need for re-connection in the middle of command executions. It will also check that the guilds that the bot is on are already registered with Redis, if not, it won't initialize a connection;

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
Redis is also used as a connection gateway and a message broker to the web interface. 

# Requirements
To run this bot, you need SendGrid, Redis, and discord.py, UW Open Data API, a discord bot token. and the respective python libraries installed for them.

### Sendgrid
Sendgrid is used to dispatch emails to users, you will need to register for an account and obtain an API key

### UW Open Data API
You will need to request an UW open data initiative API key from the university to be able to access their LDAP API (which this bot uses)

### Redis
You will need the redis python library and an instance of redis server running on your host machine

### Discord.py
Discord.py is a python library which you can install, but you will also need to create a discord bot token through the discord developer portal in order to create and use discord bots. 

# Setup
Because this bot was primarily created for the ECE 2024 server to support us and the other stream in online-studies, there will be quite a bit of reconfiguring to do if you wish to use this for your own server. My recommendation would be to extract the functionalities that you need from this bot's source code and integrate it into your own bot.

The secrets for things like Sendgrid, UW, and discord.py are already in an environment file which you can directly change. 

The links for textbooks, the important dates calendar (which feeds into !upcoming) and the schedule calendar are also directly configurable within <b>Redis</b> under the variable names of SCHEDULE_LINK,IMPORTANT_DATES_LINK,TEXTBOOKS_LINK. This is in redis so that each different server can easily have different links for these and can change in real time without needing to edit an environment file or a text-based configuration file. 

We still have work underway to make this much more configurable and easy to start without any major code refactoring, and this repository will be updated when that is done.

In the meanwhile, if you are interested in using this bot on your own server, I can allocate a partition on my own host and set it up for you on your server for free, just reach out to me on Discord (Kaveen#0001) or by email at k5kumara@uwaterloo.ca

  
