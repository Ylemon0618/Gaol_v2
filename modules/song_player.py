import discord
from discord import ApplicationContext
from discord.ext import commands

import asyncio
from async_timeout import timeout

from yt_dlp import YoutubeDL

from functools import partial

from modules.make_embed import makeEmbed, Field, Color


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data):
        super().__init__(source)

        self.title = data.get('title')
        self.url = data.get('webpage_url')

    def __getitem__(self, item: str):
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, url, *, loop, download=False):
        try:
            loop = loop or asyncio.get_event_loop()

            to_run = partial(ytdl.extract_info, url=url, download=download)
            data = await loop.run_in_executor(None, to_run)

            if 'entries' in data:
                data = data['entries'][0]

            await ctx.respond(f"**{data['title']}** successfully added to queue")

            if download:
                source = ytdl.prepare_filename(data)
            else:
                return {'url': data['webpage_url'], 'title': data['title']}

            return cls(discord.FFmpegPCMAudio(source), data=data)
        except Exception as e:
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", f"{e}", Color.error), ephemeral=True)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data)


class SongPlayer(commands.Cog):
    def __init__(self, ctx: ApplicationContext, players):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.now_playing = None
        self.volume = 0.5
        self.current = None

        self.players = players

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                async with timeout(300):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.bot.loop.create_task(cleanup(self._guild, self.players))

            if not isinstance(source, YTDLSource):
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(embed=makeEmbed(":warning: Error :warning:", f"{e}", Color.error))
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.now_playing = await self._channel.send(embed=makeEmbed(":musical_note: **Now Playing** :musical_note:",
                                                                        f"**{source.title}**", Color.success))
            await self.next.wait()

            source.cleanup()
            self.current = None

            try:
                await self.now_playing.delete()
            except discord.HTTPException:
                pass


async def cleanup(guild, players):
    try:
        await guild.voice_client.disconnect()
    except AttributeError:
        pass

    try:
        del players[guild.id]
    except KeyError:
        pass