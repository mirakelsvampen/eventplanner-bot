#! /usr/bin/env python3s

import discord
import random
import logging
import re
import json
import os
import inspect

from discord.ext import commands

from db_handler import MyDatabase
from db_handler import DataForm

""" 
    If your bot tracks server members or downloads the entire member list, 
    you may need the server members intent to receive member events and the member list.
    NOTE: Once your bot reaches 100 or more servers, this will require Verification and whitelisting. Read more here
"""
# required permissions for discord bot
intents = discord.Intents.all()

client = commands.Bot(                                   # Create a new bot
    command_prefix='--',                                 # Set the prefix
    description='A bot used for creating raid lobbies',  # Set a description for the bot
    case_insensitive=True,                               # Make the commands case insensitive
    intents=intents
)

WORKING_DIR = os.path.abspath(os.curdir)
logging.basicConfig(
        level=logging.DEBUG, 
        filename=os.path.join(WORKING_DIR, 'backend_logs.log'), 
        format='%(asctime)s - %(process)s - %(module)s -  %(levelname)s - %(message)s'
    )

settings_file = open(os.path.join(WORKING_DIR, 'settings.json'), 'r')
settings = json.loads(settings_file.read())
settings_file.close()

logging.debug('Starting with the following settings : %s' % (settings))

db_connections = dict()

cogs = ['cogs.lobbies']
@client.event
async def on_ready():
    """
        Performs instructions inside this function when the bot(user) has logged in to the servers.
    """
    logging.debug('Logged on as {0}!'.format(client.user.name))
    logging.debug('I am active in the following servers:')
    logging.debug('Name:'.ljust(20, '_') + 'ID')

    for cog in cogs:
        client.load_extension(cog)

    for guild in client.guilds:
        logging.debug('{0.name}'.format(guild).ljust(20, '_') + '{0.id}'.format(guild))
        con = MyDatabase(
                    **{**settings['database'], "db_name": re.sub(r' ', '', guild.name)}
                )

        print(guild.members)
        for member in guild.members:
            logging.debug('Adding %s to database %s' % (member.name, guild.name))

            memid = member.id
            member_name = member.name.encode('utf-8') # some people use weird names which fuck up my database

            create_settings = DataForm(method='create')
            create_settings.member = member_name
            create_settings.memid = memid
            data = create_settings.render()

            con.transact(data)

client.run(settings['client']['bot_token'], bot=True)