import discord
from aiohttp.web_routedef import delete
from discord import Option, ApplicationContext
from discord.ext import commands

import asyncio
from async_timeout import timeout

from yt_dlp import YoutubeDL

from functools import partial

from modules.make_embed import makeEmbed, Field, Color
from modules.song_queue_button import QueueMainView


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
    def __init__(self, ctx: ApplicationContext):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.now_playing = None
        self.volume = 0.5
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                async with timeout(300):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

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

    def destroy(self, guild):
        # return self.bot.loop.create_task(self._cog.cleanup(guild))
        return self.bot.loop.create_task(Song(self.bot).cleanup(guild))


class Song(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players = {}
        self.queue = asyncio.Queue()
        self.queue_listed = []

    song_commands = discord.SlashCommandGroup(name="song", name_localizations={"ko": "노래"},
                                              description="Commands for song",
                                              description_localizations={"ko": "노래와 관련된 명령어"},
                                              guild_ids=[1278195924203601930])

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = SongPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    # 음챗 접속
    @song_commands.command(name="join", name_localizations={"ko": "접속"},
                           description="Join the voice room",
                           description_localizations={"ko": "음성 채팅방에 접속합니다."})
    async def join_(self, ctx: ApplicationContext):
        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "유효하지 않은 음성 채팅방입니다.", Color.error))

        vc = ctx.voice_client

        if vc:
            if vc.channel.id == channel.id:
                return

            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                return await ctx.respond(
                    embed=makeEmbed(":warning: Error :warning:", "시간초과\n\n다시 시도하여 주세요.", Color.error))
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                return await ctx.respond(
                    embed=makeEmbed(":warning: Error :warning:", "시간초과\n\n다시 시도하여 주세요.", Color.error))

    # 음챗 나가기
    # Param: ctx
    @song_commands.command(name="leave", name_localizations={"ko": "나가"},
                           description="Let the bot leave",
                           description_localizations={"ko": "봇을 퇴장시킵니다."})
    async def leave_(self, ctx: ApplicationContext):
        if ctx.voice_client is None:
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "음성 채팅방에 접속해야 합니다.", Color.error))

        return await ctx.voice_client.disconnect()

    # 볼륨 조절
    # Param: ctx, volume
    @song_commands.command(name="volume", name_localizations={"ko": "볼륨"},
                           description="Change the volume",
                           description_localizations={"ko": "볼륨을 조정합니다."})
    async def volume_(self, ctx: ApplicationContext,
                      volume: Option(int, name="volume", name_localizations={"ko": "크기"},
                                     description="Enter the volume (with percentage)",
                                     description_localizations={"ko": "볼륨 값을 입력 해 주세요. (1~100)"})):
        if ctx.voice_client is None:
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "음성 채팅방에 접속해야 합니다.", Color.error))

        if ctx.voice_client.source is None:
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "노래가 재생중이어야 합니다.", Color.error))

        if volume == 0:
            emoji = ":mute:"
        elif volume < 50:
            emoji = ":sound:"
        elif volume < 100:
            emoji = ":loud_sound:"
        elif volume == 100:
            emoji = ":loudspeaker:"
        else:
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "유효하지 않은 값입니다.", Color.error))

        ctx.voice_client.source.volume = volume / 100

        return await ctx.respond(embed=makeEmbed(f"{emoji} Success {emoji}", f"볼륨이 {volume}%로 조정되었습니다.", Color.success))

    # 노래 재생
    # Param: ctx, url/제목
    @song_commands.command(name="play", name_localizations={"ko": "재생"},
                           description="Play song with url or title",
                           description_localizations={"ko": "노래를 재생합니다."})
    async def play_(self, ctx: ApplicationContext,
                    *, song: Option(str, name="song", name_localizations={"ko": "노래"},
                                    description="Enter the song to play",
                                    description_localizations={"ko": "재생 할 노래의 url이나 제목을 입력 해 주세요."})):
        await ctx.defer()
        await ctx.trigger_typing()

        vc = ctx.voice_client

        if not vc:
            await self.join_(ctx)

        player = self.get_player(ctx)

        source = await YTDLSource.create_source(ctx, url=song, loop=self.bot.loop, download=True)

        await player.queue.put(source)

    # 재생 일시정지
    # Param: ctx
    @song_commands.command(name="pause", name_localizations={"ko": "일시정지"},
                           description="Pause the song playing",
                           description_localizations={"ko": "재생 중인 노래를 일시정지 합니다."})
    async def pause_(self, ctx: ApplicationContext):
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "현재 재생 중인 노래가 없습니다.", Color.error))
        elif vc.is_paused():
            return

        vc.pause()
        await ctx.respond(embed=makeEmbed(":no_entry: Paused :no_entry:", "재생 중인 노래를 일시정지 했습니다.", Color.success))

    # 재생 재개
    # Param: ctx
    @song_commands.command(name="resume", name_localizations={"ko": "재개"},
                           description="Resume paused song",
                           description_localizations={"ko": "일시정지 된 노래를 다시 재생합니다."})
    async def resume_(self, ctx: ApplicationContext):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "현재 재생이 중지된 노래가 없습니다.", Color.error))
        elif not vc.is_paused():
            return

        vc.resume()
        await ctx.respond(embed=makeEmbed(":musical_note: Resumed :musical_note:",
                                          "일시정지 된 노래를 다시 재생했습니다.", Color.success))

    # 노래 스킵
    # Param: ctx
    @song_commands.command(name="skip", name_localizations={"ko": "스킵"},
                           description="Skip the song",
                           description_localizations={"ko": "현재 재생 중인 노래를 스킵합니다."})
    async def skip_(self, ctx: ApplicationContext):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "현재 재생 중인 노래가 없습니다.", Color.error))

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        vc.stop()
        await ctx.respond(embed=makeEmbed(":musical_note: Skipped :musical_note:",
                                          "노래를 스킵했습니다.", Color.success))

    # 노래 중지
    # Param: ctx
    @song_commands.command(name="stop", name_localizations={"ko": "중지"},
                           description="Stop the song",
                           description_localizations={"ko": "노래 재생을 중지합니다."})
    async def stop_(self, ctx: ApplicationContext):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "현재 재생 중인 노래가 없습니다.", Color.error))

        await self.cleanup(ctx.guild)

        await ctx.respond(embed=makeEmbed(":no_entry: Paused :no_entry:", "노래 재생을 중지했습니다.", Color.success))

    # 대기열
    # Param: ctx
    @song_commands.command(name="queue", name_localizations={"ko": "대기열"},
                           description="Check the queue",
                           description_localizations={"ko": "대기열을 확인 및 편집합니다."})
    async def queue_(self, ctx: ApplicationContext):
        if self.players.get(ctx.guild.id) is None:
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "현재 대기열이 비어있습니다.", Color.error))

        self.queue = self.players[ctx.guild.id].queue
        self.queue_listed = list(self.players[ctx.guild.id].queue._queue)
        title = []

        embed=makeEmbed(":musical_note: Queue :musical_note:", "", Color.success)
        for i in range(min(10, len(self.queue_listed))):
            embed.add_field(name=self.queue_listed[i].title, value="", inline=False)
            title.append(self.queue_listed[i].title)

        await ctx.respond(embed=embed, view=QueueMainView(self.players[ctx.guild.id].queue, self.queue_listed, title))


def setup(bot):
    bot.add_cog(Song(bot))
