import discord
import json
import asyncio
import re


class PneumaClient(discord.Client):
    """Child discord client class for managing Pneuma Bot"""

    def __init__(self, configs):
        super().__init__()
        self.configs = configs
        self.token = self.configs["Token"]
        self.admin_chan = None
        self.command_chan = None
        self.core_message = None
        self.emoji_to_channel = {}
        loop = asyncio.get_event_loop()
        loop.create_task(self.start(self.token))
        try:
            loop.run_forever()
        finally:
            loop.stop()
            print('Bot has Disconnected')


    async def update_data(self):
        self.emoji_update()
        await self.update_core()
        msg = '<@!93172449562066944> update the configs on heroku'
        await self.admin_chan.send(msg)


    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.channel.id == self.configs["Admin Channel"]:

            if message.content.startswith('!add'):
                # Adds new role and emoji pairing
                # !add Name #Channel :emoji:
                msg = message.content
                channel_block = re.search(r'!add [a-zA-Z0-9]+', msg)
                role_block = re.search(r'<@&[0-9]+>', msg)
                emoji_block = re.search(r'<:[a-zA-Z0-9_]+:[0-9]+>', msg)

                if channel_block is None: 
                    await self.admin_chan.send('Cant find name')
                    return
                if role_block is None:
                    await self.admin_chan.send('Cant find role')
                    return
                if emoji_block is None:
                    await self.admin_chan.send('Cant find Emoji')
                    return

                channel = channel_block.group().replace('!add ', '')
                role_id = re.search('[0-9]+', role_block.group()).group()
                emoji_id = re.search(':[0-9]+>', emoji_block.group()).group()
                emoji_id = emoji_id.replace(':', '').replace('>', '')

                try:
                    await message.guild.fetch_emoji(emoji_id)
                except (discord.errors.NotFound):
                    await self.admin_chan.send('Emoji not found on this server')
                    return

                msg = 'Add Channel {0} for role {1} using emoji {2}?'.format(
                    channel_block.group(), 
                    role_block.group(),
                    emoji_block.group()
                )
                msg += '\nType !YES to continue...'
                await self.admin_chan.send(msg)

                def check(msg):
                    return msg.author.id == message.author.id
                ret = await self.wait_for('message', check=check, timeout=30)

                if ret.content == '!YES':
                    IDs = [int(role_id), int(emoji_id)]
                    self.configs['Channels'][channel] = IDs
                    await self.admin_chan.send('Added Role')
                    await self.update_data()
                else:
                    await self.admin_chan.send('Doing nothing')

                
            if message.content.startswith('!update'):
                await self.update_core()

            if message.content.startswith('!configs'):
                cs = json.dumps(self.configs, indent=4, sort_keys=True)
                if len(cs) > 2000:
                    for i in range(len(cs) // 2000):
                        await self.admin_chan.send(
                            cs[i * 2000: min(
                                i * 2000 + 1999, 
                                len(cs))])
                else:
                    await self.admin_chan.send(cs)
                
            if message.content.startswith('!test'):
                await self.admin_chan.send('test message')

            if message.content.startswith('!exit'):
                await message.channel.send('Leaving')
                await self.logout()
                loop = asyncio.get_running_loop()
                loop.stop()


    async def on_raw_reaction_add(self, payload):
        result = self.role_from_react(payload)
        if result is not None:
            role, user = result
            await user.add_roles(role)


    async def on_raw_reaction_remove(self, payload):
        result = self.role_from_react(payload)
        if result is not None:
            role, user = result
            await user.remove_roles(role)


    def role_from_react(self, payload):
        user_ID = payload.user_id
        message = payload.message_id
        emoji_ID = payload.emoji.id

        if user_ID == self.user.id:
            return

        if message == self.core_message.id:
            if emoji_ID in self.emoji_to_channel:
                chan_name = self.emoji_to_channel[emoji_ID]
                role_ID = self.configs['Channels'][chan_name][0]
                guild = self.get_emoji(emoji_ID).guild
                role = guild.get_role(role_ID)
                member = guild.get_member(user_ID)
                return role, member


    async def find_core(self):
        try:
            # Gets the main message and deletes the rest
            self.core_message = await self.command_chan.fetch_message(
                self.configs['Main Message ID']
            )
            
        except discord.NotFound:
            # Creates message if not found
            core = await self.command_chan.send('<temp>')
            self.configs['Main Message ID'] = core.id
            msg = '<@!93172449562066944> update the configs on heroku'
            await self.admin_chan.send(msg)
            self.core_message = core

        # Deletes all extra messages
        def check_msg(m):
            return m.id != msg.id
        await self.command_chan.purge(limit=100, check=check_msg)

        # Update core
        await self.update_core()


    async def update_core(self):
        # Edits core message with new embeds
        msg = self.configs['MSGs']['Core Message']
        embed = discord.Embed(
            title='**Hello!**', 
            description=msg, 
            color=0x17f0d6
        )

        emojis = []
        embed_count = 0

        for chan, IDs in self.configs['Channels'].items():
            if chan != 'AAAAA':
                emoji_ID = IDs[1]
                target_emoji = self.get_emoji(emoji_ID)
                emojis.append(target_emoji)
                embed.add_field(
                    name=chan, 
                    value=f'<:{target_emoji.name}:{target_emoji.id}>', 
                    inline=True
                )
                embed_count += 1
        
        pad_count = (3 - embed_count % 3) % 3

        for i in range(pad_count):
            embed.add_field(name='-', value='-', inline=True)

        embed.set_footer(text=self.configs['MSGs']['Core Footer'])
        await self.core_message.edit(content='', embed=embed)

        for emoji in emojis:
            await self.core_message.add_reaction(emoji)


    def emoji_update(self):
        # Update internal emoji list
        for chan, IDs in self.configs['Channels'].items():
            self.emoji_to_channel[IDs[1]] = chan


    async def on_ready(self):
        self.admin_chan = self.get_channel(self.configs["Admin Channel"])
        self.command_chan = self.get_channel(self.configs["Command Channel"])
        await self.admin_chan.send('Loaded...')
        await self.find_core()
        self.emoji_update()

        print('Ready!')
        print(self.user.name)
        print(self.user.id)
        print('=' * 5)


    async def on_error(self, event, *args, **kwargs):
        # Pings me in admin channel there was an error
        await super().on_error(event, *args, **kwargs)
        msg = '<@!93172449562066944> there was an error!'
        await self.admin_chan.send(msg)


configs = {}
with open('configs.json', 'r') as file:
    configs = json.loads(file.read())

print('Loading Bot')
bot = PneumaClient(configs)
print('Shut down')
