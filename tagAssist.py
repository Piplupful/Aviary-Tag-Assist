import os, re
from datetime import datetime
from contextlib import suppress
import logging
import logging.handlers

import discord
from dotenv import load_dotenv

from steam_web_api import Steam

from sftp_update_tags import *

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
STEAM_TOKEN = os.getenv('STEAM_API_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents = intents)

steam = Steam(STEAM_TOKEN)

MAX_TAG_LEN = int(os.getenv('MAX_TAG_LEN'))

logger = logging.getLogger('logger')
logger.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler(os.getenv('LOG_PATH'), maxBytes=1024, backupCount=2)
logger.addHandler(handler)

#RegEx
re_steam_64 = re.compile('[0-9]{17}')

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
            if message.channel.name == 'tag-output':
                await message.add_reaction('👍')
            return
        
        new_message = None

        if("https://steamcommunity.com/" in message.content and message.channel.name == 'tag-request'):
            lines = str(message.content).splitlines()
            tag = color = steam_url = None
            comments = []

            #Parse message
            for line in lines:
                lower_line = line.lower()
                if('tag:' in lower_line):
                    tag = line.split(':')[-1].lstrip(' ').strip('[]')
                elif('color:' in lower_line or 'colour:' in lower_line):
                    if re.search('[A-Fa-f0-9]{6}', line) != None:
                        color = line.split(':')[-1].replace('#', '').replace(' ','')
                elif('steam:' in lower_line):
                    steam_url = line.split(':')[-1].replace(' ','')
                elif line and not line.isspace():
                    comments.append(line)
                
            #INPUT ERROR CHECK
            if(tag == None or color == None
               or steam_url == None
               or len(tag) > MAX_TAG_LEN):
                await message.add_reaction('❌')
                return
            
            assert tag != None
            assert color != None
            assert steam_url != None

            steam_url_id = steam_id_64 = steam_id = None

            #Get steam id info
            steam_url_id = steam_url.split('/')[-1] if steam_url[-1] != '/' else steam_url.split('/')[-2]

            #Incomplete Steam URL Error Check
            if steam_url_id == 'id' or steam_url_id == 'profiles':
                await message.add_reaction('❌')
                return

            with suppress(KeyError):
                steam_id_64 = steam_url_id if re_steam_64.fullmatch(steam_url_id) else steam.users.get_steamid(steam_url_id)['steamid']

            if steam_id_64 == None:
                await message.add_reaction('❌')
                return

            steam_id = commid_to_steamid(steam_id_64)

            #Construct config entry
            first_line = '```\"' + steam_id + '\"\t// ' + str(message.author).replace('_','') +'\n{\n'
            tag_line = '\t\"tag\"\t\t\"[' + tag.rstrip().lstrip() + '] \"\n'
            namecolor_line = '\t\"namecolor\"\t\t\"\"\n'
            tagcolor_line = '\t\"tagcolor\"\t\t\"' + color + '\"\n}```'

            new_message = first_line + tag_line + namecolor_line + tagcolor_line

            #Comments
            if len(comments) != 0:
                new_message += "**COMMENTS**\n===========\n"
                for comment in comments:
                    new_message += comment + '\n'
        
        if new_message:
            await send_message(new_message, message)
                
    except Exception as e:
        logger.error(f"{datetime.now()}: {e}\t{message}")
        
@client.event
async def on_raw_reaction_add(payload):
    try:
        channel = discord.utils.get(client.get_all_channels(), name = 'tag-output')
        
        if payload.channel_id != channel.id:
            return
        
        if(payload.user_id == client.user.id):
            return
        
        if payload.emoji.name == '👍':
            msg = await channel.fetch_message(payload.message_id)

            if('STEAM_0:0:' not in msg.content) and ('STEAM_0:1:' not in msg.content):
                return

            to_insert = msg.content.split('```')[1]
            update_tags(to_insert)
        else:
            return
    except Exception as e:
        logger.error('ON REACTION TO ADD TO TAGS:\t' + str(e))

client.run(DISCORD_TOKEN)
