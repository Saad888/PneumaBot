import discord
import json
import asyncio

class PneumaClient(discord.Client):

    def __init__(self, configs):
        super().__init__()
        self.configs = configs
        self.token = self.configs["Token"]
        self.admin_chan = None
        self.command_chan = None
        self.core_message = None
        loop = asyncio.get_event_loop()
        loop.create_task(self.start(self.token))
        try:
            loop.run_forever()
        finally:
            loop.stop()
            print('Bot has Disconnected')

    async def on_message(self, message):
        if message.author == self.user:
            return


        if message.channel.id == self.configs["Admin Channel"]:
            if message.content.startswith('!update'):
                await self.update_core()

            if message.content.startswith('!configs'):
                configs_string = json.dumps(self.configs, indent=4, sort_keys=True)
                if len(configs_string) > 2000:
                    for i in range(len(configs_string) // 2000):
                        await self.admin_chan.send(
                            configs_string[i * 2000: min(
                                i * 2000 + 1999, 
                                len(configs_string))])
                else:
                    await self.admin_chan.send(configs_string)
                
            if message.content.startswith('!clear'):
                await self.admin_chan.purge()

            if message.content.startswith('!test'):
                await self.admin_chan.send('Sending message to admins <:rayeban:575175949356892192>')

            if message.content.startswith('!exit'):
                await message.channel.send('Leaving')
                await self.logout()
                loop = asyncio.get_running_loop()
                loop.stop()


    async def find_core(self):
        try:
            # Gets the main message and deletes the rest
            msg = await self.command_chan.fetch_message(
                self.configs['Main Message ID']
            )
            
            # Deletes all extra messages
            def check_msg(m):
                return m.id != msg.id
            await self.command_chan.purge(limit=100, check=check_msg)

            # Saves core message
            self.core_message = msg

        except discord.NotFound:
            await self.start_core()


    async def start_core(self):
        # Sends the core message and assigns it on internal values
        core = await self.command_chan.send('IM')
        self.configs['Main Message ID'] = core.id
        self.core_message = core


    async def update_core(self):
        msg = self.configs['MSGs']['Core Message']
        emojis = []
        for chan, IDs in self.configs['Channels'].items():
            if chan != 'AAAAA':
                emoji_ID = IDs[2]
                target_emoji = self.get_emoji(emoji_ID)
                emojis.append(target_emoji)
                msg += f'<:{target_emoji.name}:{target_emoji.id}> - {chan}\n' 
        await self.core_message.edit(content=msg)
        for emoji in emojis:
            await self.core_message.add_reaction(emoji)




    async def on_ready(self):
        print('Ready!')
        self.admin_chan = self.get_channel(self.configs["Admin Channel"])
        self.command_chan = self.get_channel(self.configs["Command Channel"])
        await self.admin_chan.send('Loaded...')
        await self.find_core()
        print(self.user.name)
        print(self.user.id)
        print('=' * 5)


configs = {}
with open('configs.json', 'r') as file:
    configs = json.loads(file.read())

print('Loading Bot')
bot = PneumaClient(configs)
print('Shut down')
