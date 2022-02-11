import discord, toml, os
from discord.ext import tasks, commands

class DiscordBot(commands.Bot):
    def __init__(self, command_prefix = '!', intents = discord.Intents.default(), config = None, cogs = []):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.config = config
        # Load cogs
        for cog in cogs:
            try:
                self.load_extension(cog)
            except Exception as e:
                print('Failed to load module {0}\n{1} : {2}'.format(cog, type(e).__name__, e))
    
    # Event: on_ready
    async def on_ready(self):
        print(f"Loading bot: {self.user.id}")

    # Event: on_message
    async def on_message(self, message):
        await self.get_cog("Moderation").handle(message) # Send the message to a specific cog to use
        await self.process_commands(message) # Still have discord process the potential command normally
    
    # Event: on_command_error
    async def on_command_error(self, error, ctx):
        if isinstance(error, commands.CommandOnCooldown):
            await self.send_message(ctx.message.channel, content='This command is on a %.2fs cooldown' % error.retry_after)
            return
        if isinstance(error, commands.CommandNotFound):
            return
        raise error
    
# Debugging
os.chdir("FULL PATH ADDRESS... /DiscordBotTemplate/")

# Load config file
with open('config.toml', 'r') as file:
    data = file.read()
config = toml.loads(data)

# Start bot
intents = discord.Intents.default()
intents.members = True
client = DiscordBot(command_prefix='!', intents=intents, config=config, cogs=config['Bot']['cogs'])
client.run(config['Bot']['Token'])