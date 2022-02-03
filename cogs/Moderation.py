import discord
from discord.ext import commands
from jinja2 import pass_context

class Moderation():
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
    
    # Helper method: checks if a word is in the config's blacklist
    def isBlacklisted(self, message):
        for word in self.word_blacklist:
            if word.lower() in message.content.lower():
                return True
        return False
    
    # Example command: deletes last 50 -> 150 messages in a text channel
    @commands.command(pass_context = True)
    @commands.cooldown(1, 10, commands.BucketType.user) #Can be used 1 time per 10 seconds by each user
    async def clean(self, ctx, max_messages: int = 50):
        if(max_messages >= 150):
            await self.bot.send_message(ctx.message.channel, "You can only delete up to 150 messages at a time")
            return
        
        messages = []
        async for x in self.bot.logs_from(ctx.message.channel, limit=max_messages):
            messages.append(x)
        
        await self.bot.delete_messages(messages)
        await self.bot.send_message(ctx.message.channel, f"=== Deleted {max_messages} messages ===")
    
    # Called on every message sent (by main.py)
    # Will delete messages containing words in the config's blacklist
    async def scrub(self, message):
        isBlocked = self.isBlacklisted(message)
        if (isBlocked):
            """await self.bot.delete_messages([message])"""
            await self.bot.delete_message(message)
            meme = self.getMeme()
            await self.bot.send_message(message.channel, meme + " -Courtesy of Roblox Admin Team")