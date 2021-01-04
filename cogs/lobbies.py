import os
import re
import json
import random
import discord

from db_handler import DataForm
from discord.ext import commands, tasks
from db_handler import MyDatabase
from timemachine import TimeMachine

from pprint import pprint
import emojis

import logging

logging.basicConfig(
        level=logging.DEBUG,
        filename='backend_logs.log', 
        format='%(asctime)s - %(process)s - %(module)s -  %(levelname)s - %(message)s'
    )

# New - The Cog class must extend the commands.Cog class
class Lobbies(commands.Cog):
    # TODO: a member cannot partake in more than 10 lobbies
    # TODO: a lobby cannot have a timedelta more than 6 hours
    # TODO: a lobby must be destroyed if no members partake in it.
        
    def __init__(self, bot):
        self.bot = bot

        WORKING_DIR = os.path.abspath(os.curdir)
        settings_file = open(os.path.join(WORKING_DIR, 'settings.json'), 'r')
        self.settings = json.loads(settings_file.read())
        settings_file.close()
        self.task_clean_lobbies.start(guilds=self.bot.guilds)

    def connect_to_db(self, ctx):
        # TODO: Maybe this is not an optimal way of communicating with the database
        # Because this way has a tendancy of creating maaany connections; one for each method command.
        """
            Use ctx object to connect to database and return connection object
        """
        try:
            guild_name = re.sub(r' ', '', ctx.message.channel.guild.name) # remove whitespaces from database names
        except AttributeError:
            guild_name = ctx
        con = MyDatabase(
            **{**self.settings['database'], "db_name": guild_name}
        )
        return con

    # @commands.Cog.listener()
    # async def on_command_error(self, ctx, err):
    #     await ctx.message.channel.send(err)

    #----- background tasks -----
    @tasks.loop(seconds=60)
    async def task_clean_lobbies(self, guilds):
        """
            Delete empty lobbies if no leader is found
        """
        for guild in guilds:
            con = self.connect_to_db(guild.name)
            lobbies = con.select_lobbies()
            for lobby_id in lobbies.keys():
                if con.has_no_leader(lobby_id):
                    con.delete_lobby(lobby_id)
        con.session.close()
    
    #----- helper functions -----
    def render_lobby_layout(self, lobby_objects):
        render_text = [
                '```javascript\n', 
            ]
        for lobby in lobby_objects.values():
            lobby_layout_slots = dict((x,y) for x,y in ((z, '-') for z in range(1,lobby['size']+1)))

            if 'leave_id' in lobby:
                render_text.append(
                    '\n< ID: %s - %s at %s has the following members >\n' % (lobby['leave_id'], lobby['name'], lobby['date'])
                )
            else:
                render_text.append(
                    '\n< %s at %s has the following members >\n' % (lobby['name'], lobby['date'])
                )
            for index, participant in enumerate(lobby['participant']):
                if participant == lobby['leader']:
                    participant = '%s 👑' % (participant) # love that unicode babeeeeey
                lobby_layout_slots[index + 1] = '%s' % (participant)

            for slot_number, slot_value in lobby_layout_slots.items():
                render_text.append(' - %s. %s\n' % (slot_number, slot_value))
        render_text.append('```')
        return render_text

    def render_message_attributes(self, name, date, size, server):
        return [
            '```javascript\n',
            'Lobby name'.ljust(20, ' ') + '%s\n' % (name),
            'Lobby Size'.ljust(20, ' ') + '%s\n' % (size),
            'Server'.ljust(20, ' ') + '%s\n' % (server),
            'Due-date'.ljust(20, ' ') + '%s\n' % (date),
            '```'
        ]

    #----- command functions -----
    @commands.command(
        name='create',
        description='The lobby creation command',
        aliases=['c']
    )
    async def create(self, ctx, lobby_name, date, size):
        date = TimeMachine(date).convert() # will raise and error if invalid format

        con = self.connect_to_db(ctx)
        lobby_id = random.getrandbits(64)
        create_settings = DataForm(method='create')
        create_settings.lobbyid = lobby_id
        create_settings.lobby = lobby_name
        create_settings.lobby_size = int(size)
        create_settings.date = date
        create_settings.participation_member = ctx.message.author.id
        create_settings.participation_lobby = lobby_id
        data = create_settings.render()
        
        con.transact(data)

        message_to_render = self.render_message_attributes(
            **{
                'name':lobby_name,
                'date':date,
                'size':size,
                'server':ctx.message.channel.guild.name
            }
        )

        await ctx.message.author.send(
            ":space_invader: I created a lobby for you, Have fun! :space_invader:\n %s" % (
                ''.join(message_to_render)
            )
        )
        return

    @commands.command(
        name='list',
        description='list existing lobbies a player partakes in. Defaults to listing all existing lobbies.',
        aliases=['l']
    )
    async def list_lobbies(self, ctx, scope='[ membername ] | me'):
        con = self.connect_to_db(ctx)

        existing_lobbies = list()

        if scope == '[ membername ] | me':
            existing_lobbies = con.select_lobbies()
        elif scope == 'me':
            existing_lobbies = con.select_lobbies(ctx.message.author.id)
        elif scope:
            member = con.select_member(scope)
            if member:
                existing_lobbies = con.select_lobbies(member.id)            

        if existing_lobbies:
            render_text = self.render_lobby_layout(existing_lobbies)
            render_text.insert(0, ':space_invader: I have gathered the following information for you! :space_invader:')
            await ctx.message.channel.send(content=''.join(render_text))
        else:
            await ctx.message.channel.send('```Well actually nothing was found :(```')

    @commands.command(
        name='leave',
        description='Leave a lobby. If lobby is left without any participants it will be removed.',
        aliases=['d']
    )
    async def leave_lobby(self, ctx, lobby_name):
        """
            Leave a lobby which the member is partaking in. If more than one lobby is found
            then the user will get the choice of leaving one of the lobbies in a list. The bot directly
            communicates the with the member through direct messaging.
        """
        def create_lobby_attrs_as_dict(lobby):
            attr_dict = {
                'name':lobby['name'],
                'date':lobby['date'],
                'size':lobby['size'],
                'server':ctx.message.channel.guild.name
            }
            return attr_dict

        con = self.connect_to_db(ctx)
        # See if any lobby matches the user
        existing_lobbies = con.select_lobbies(member=ctx.message.author.id, name=lobby_name)
        if existing_lobbies:
            if len(list(existing_lobbies.keys())) > 1:  # more than one lobby is found
                
                leave_lobby_index = dict()
                for id_num, lobby in enumerate(existing_lobbies.items()):
                    leave_lobby_index[id_num] = lobby[0]
                    lobby[1]['leave_id'] = id_num
                    existing_lobbies[lobby[0]] = lobby[1]

                render_text = self.render_lobby_layout(existing_lobbies)
                render_text.insert(0, 'Use the reactions to answer.')
                render_text.insert(0, ':space_invader: Found multiple matches, which one would you like to leave? :space_invader:')

                bot_answer = await ctx.message.author.send(''.join(render_text))
                for id_num in leave_lobby_index: # Add an equal amount of emojis as to the matched lobbies; limit = 10
                    await bot_answer.add_reaction(emojis.numbers[id_num])

                def check(reaction, user):
                    """
                        Check if the reactions match the same lobby as the latest rendered one. And if the 
                        reacted emoji only is part of the ones the bot added. Returns a boolean.
                    """
                    print('checking reaction')
                    result = reaction.message.id == bot_answer.id and str(reaction.emoji) in emojis.numbers.values() and user.id != bot_answer.author.id
                    return result
                    
                reaction, user = await self.bot.wait_for('reaction_add', check=check)
                if reaction and user:
                    lobby_index_key = next(key for key, value in emojis.numbers.items() if value == reaction.emoji)

                    lobby_id=leave_lobby_index[lobby_index_key]
                    member_id=user.id
                    if con.delete_particiant_from_lobby(lobby_id, member_id): # perform deletion here
                        lobby_attrs = create_lobby_attrs_as_dict(existing_lobbies[lobby_id])
                        message_to_render = self.render_message_attributes(
                            **lobby_attrs
                        )
                        message_to_render.insert(0, ':space_invader: I deleted you from the following lobby: :space_invader:')
                        await bot_answer.edit(
                            content=''.join(message_to_render)
                        ) # then edit the message that the bot rendered earlier
            else:
                lobby_id = list(existing_lobbies.keys())[0]
                member_id = ctx.message.author.id
                lobby_attrs = create_lobby_attrs_as_dict(list(existing_lobbies.values())[0])
                message_to_render = self.render_message_attributes(
                        **lobby_attrs
                    )

                con.delete_particiant_from_lobby(
                    lobby_id, member_id
                )
                message_to_render.insert(0, ':space_invader: I deleted you from the following lobby: :space_invader:')
                await ctx.message.author.send(''.join(message_to_render))
        else:
            await ctx.message.author.send('```Sorry guardian, I could not find any matches for %s in server %s```'
                % (lobby_name, ctx.message.channel.guild.name)
            )

        # await ctx.message.author.send(ctx, existing_lobbies)
        # print(list(existing_lobbies.keys()))
        
def setup(bot):
    bot.add_cog(Lobbies(bot))
    # Adds the Basic commands to the bot
    # Note: The "setup" function has to be there in every cog file