import os, re
from datetime import datetime
import logging
import logging.handlers

import discord
from dotenv import load_dotenv

from steam import Steam

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
STEAM_TOKEN = os.getenv('STEAM_API_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents = intents)

steam = Steam(STEAM_TOKEN)

logger = logging.getLogger('logger')
logger.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler("log/errors.log", maxBytes=1024, backupCount=2)
logger.addHandler(handler)

#From: https://gist.github.com/bcahue/4eae86ae1d10364bb66d
steamid64ident = 76561197960265728
def commid_to_steamid(commid):
  steamid = []
  steamid.append('STEAM_0:')
  steamidacct = int(commid) - steamid64ident
  
  if steamidacct % 2 == 0:
      steamid.append('0:')
  else:
      steamid.append('1:')
  
  steamid.append(str(steamidacct // 2))
  
  return ''.join(steamid)

async def send_message(msg, original_msg):
    channel = discord.utils.get(client.get_all_channels(), name = 'tag-output')
    await channel.send(msg)
    await original_msg.add_reaction('✅')

@client.event
async def on_message(message):
    try:
        if(message.author.id == client.user.id):
            return
        
        new_message = None

        if("https://steamcommunity.com/" in message.content and message.channel.name == 'tag-request'):
            lines = str(message.content).splitlines()
            tag = color = steam_url = None
            comments = []

            #Parse message
            for line in lines:
                lower_line = line.lower()
                if('tag' in lower_line):
                    tag = line.split(':')[-1].lstrip(' ')
                elif('color' in lower_line):
                    if re.search('[A-Fa-f0-9]{6}', line) != None:
                        color = line.split(':')[-1].replace('#', '').replace(' ','')
                elif('steam' in lower_line):
                    steam_url = line.split(':')[-1].replace(' ','')
                else:
                    comments.append(line)
                
            #ERROR CHECK
            if(tag == None or color == None or steam_url == None):
                await message.add_reaction('❌')
                return

            assert tag != None
            assert color != None
            assert steam_url != None

            #Get steam id info
            steam_url_id = steam_url.split('/')[-2]
            steam_id_64 = steam_url_id if str(steam_url_id).isnumeric() else steam.users.get_steamid(steam_url_id)['steamid']
            steam_id = commid_to_steamid(steam_id_64)

            #Construct config entry
            first_line = '```\"' + steam_id + '\"\t// ' + str(message.author).replace('_','') +'\n{\n'
            tag_line = '\t\"tag\"\t\t\"[' + tag + '] \"\n'
            namecolor_line = '\t\"namecolor\"\t\t\"\"\n'
            tagcolor_line = '\t\"tagcolor\"\t\t\"' + color + '\"\n}```'

            new_message = first_line + tag_line + namecolor_line + tagcolor_line

            #Comments
            if len(comments) != 0:
                new_message += "COMMENTS\n------------------\n"

                for comment in comments:
                    new_message += comment + '\n'
        
        if new_message:
            await send_message(new_message, message)
                
    except Exception as e:
        logger.error(f"{datetime.now()}: {e}\t{message}")
        
client.run(DISCORD_TOKEN)
