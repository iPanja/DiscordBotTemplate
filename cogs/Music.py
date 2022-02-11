from __future__ import annotations
import discord
from discord.ext import commands
import pafy, urllib, re, enum, random
from typing import List, Union

def setup(bot):
    try:
        bot.add_cog(Music(bot))
        print("[Music* Module Loaded]")
    except Exception as e:
        print(" >> Music* Module: {0}".format(e))

class SourceType(enum.Enum):
    youtube = 1
    local = 2

class Source:
    def __init__(self, address: str, source_type: SourceType, name: str):
        self.address = address
        self.source_type = source_type
        self.name = name
    def isYoutube(self) -> bool:
        return self.source_type is SourceType.youtube
    def isLocal(self) -> bool:
        return self.source_type is SourceType.local
    def get_playable_source(self, ffmpeg_settings, volume: float) -> discord.AudioSource:
        if self.source_type == SourceType.local:
            return discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(source=f"files/{self.address}"), volume)
        elif self.source_type == SourceType.youtube:
            best_quality_audio_url = pafy.new(self.address).getbestaudio().url
            return discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(best_quality_audio_url, **ffmpeg_settings), volume)
    @staticmethod
    def from_youtube_link(address: str) -> Source:
        if 'youtube.com/watch?v=' in address:
            video_id = re.findall(r"watch\?v=(\S{11})", address)[0]
            address = f"https://youtube.com/watch?v={video_id}"
            return Source(address=address, source_type=SourceType.youtube, name=pafy.new(address).title)
        return None
    @staticmethod
    def from_address(address: str) -> Source:
        # Any url should be longer than 2, local files at least appended by './'
        if len(address) < 2:
            return None
        if address[0:2] == './': # Local file
            return Source(address[2::], SourceType.local, '.'.join(address.split('.')[::-1]))
        elif 'youtube.com/watch?v=' in address: # YouTube video
            return Source.from_youtube_link(address)
        else:
            return None
    

    

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = self.bot.config
        # Settings
        self.volume = self.config['Music']['volume']
        self.voice_client = None
        # Queue
        self.music_queue: List[Source] = []
        self.is_playing = False
        # Check if bot is currently connected to any voice channels
        # TODO
    
    # /// COMMANDS
    @commands.command(aliases=['join'])
    async def connect(self, ctx: commands.Context):
        self.voice_client: discord.VoiceClient = self.get_voice_client(ctx)
        # Don't join if bot is already connected to a vc
        if self.voice_client and self.voice_client.is_connected():
            await ctx.send("I'm currently busy")
            return
        # Author must be in a vc
        if ctx.author.voice is None:
            await ctx.send('You must be in a voice channel!')
            return
        # Join vc
        self.voice_client = await ctx.author.voice.channel.connect()
    
    @commands.command(aliases=['leave', 'stop'])
    async def disconnect(self, ctx: commands.Context):
        self.voice_client: discord.VoiceClient = self.get_voice_client(ctx)
        # Disconnect if in a vc
        if not self.voice_client is None:
            await self.voice_client.disconnect()
            self.voice_client = None
        self.is_playing = False
    
    @commands.command(aliases=['queue'])
    async def play(self, ctx: commands.Context):
        #https://stackoverflow.com/questions/66115216/discord-py-play-audio-from-url
        source = Source.from_address(address=ctx.message.content)
        self.queue(source)
        await self.react_with_random_emoji(ctx)
    
    @play.before_invoke
    async def ensure_vc(self, ctx: commands.Context):
        if ctx.voice_client is None: # Bot not in vc, it must connect
            await self.connect(ctx)
    
    @commands.command()
    async def skip(self, ctx: commands.Context):
        if not self.voice_client is None:
            self.voice_client.stop() # Stop current audio
            self.on_source_completion(error=None) # Proceed normally, play next audio if applicable
    
    @commands.command()
    async def pause(self, ctx: commands.Context):
        self.voice_client.pause()
    
    @commands.command()
    async def resume(self, ctx: commands.Context):
        self.voice_client.resume()
    
    @commands.command()
    async def clear(self, ctx: commands.Context):
        self.music_queue.clear()
        await ctx.send(f"Queue cleared")
    
    @commands.command()
    async def volume(self, ctx: commands.Context, volume: float):
        self.volume = volume
        await ctx.send(f"Volume set to {self.volume}")
    
    # /// HELPERS
    async def react_with_random_emoji(self, ctx: commands.Context):
        await ctx.message.add_reaction(random.choice(ctx.guild.emojis))
    
    def get_voice_client(self, ctx: commands.Context) -> discord.VoiceClient:
        return discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
    
    # Have the bot physically play audio through its mic from the given Source
    def play_source(self, source: Source):
        self.is_playing = True
        self.voice_client.play(source.get_playable_source(self.config['Music']['ffmpeg_settings'], self.volume), after=self.on_source_completion)

    # When the bot finishes playing an audio
    def on_source_completion(self, error):
        if len(self.music_queue) > 0: # Queue up next audio
            self.play_source(self.music_queue.pop(0))
        else: # Queue is empty, mark that bot is not currently playing anything
            self.is_playing = False

    # Add source to queue of audios to play
    def queue(self, source: Source):
        if len(self.music_queue) == 0 and not self.is_playing:
            self.play_source(source)
        elif len(self.music_queue) + 1 <= self.config['Music']['queue_size']:
            self.music_queue.append(source)