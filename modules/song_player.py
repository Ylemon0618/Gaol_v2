import asyncio
import shutil
from functools import partial

import discord
from async_timeout import timeout
from discord import ApplicationContext
from discord.ext import commands
from yt_dlp import YoutubeDL

from modules.make_embed import makeEmbed, Color
from modules.song_queue import QueueMainView, set_queue_field

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
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
    async def create_source(cls, ctx: ApplicationContext, url, *, loop, download=False, send_message=True):
        try:
            global ytdl

            ytdl_format_options['outtmpl'] = f'downloads/{ctx.guild.id}/%(extractor)s-%(id)s.%(ext)s'
            ytdl = YoutubeDL(ytdl_format_options)

            loop = loop or asyncio.get_event_loop()

            to_run = partial(ytdl.extract_info, url=url, download=download)
            data = await loop.run_in_executor(None, to_run)

            if 'entries' in data:
                data = data['entries'][0]

            if send_message:
                print(data)

                embed = makeEmbed(":cd: Play :cd:", f"[**{data['title']}**](<{data['webpage_url']}>)", Color.success)

                channel = data['uploader']
                if data['channel_is_verified']:
                    channel += "<:verified:1337271571043192893>"
                channel += f" ([{data['uploader_id']}](<{data['uploader_url']}>))"

                embed.add_field(name="Channel", value=channel, inline=True)
                embed.add_field(name="Duration", value=data['duration_string'], inline=True)

                embed.set_thumbnail(url=data['thumbnail'])

                await ctx.respond(embed=embed)

            if download:
                source = ytdl.prepare_filename(data)
            else:
                return {'url': data['webpage_url'], 'title': data['title']}

            return cls(discord.FFmpegPCMAudio(source), data=data)
        except Exception as e:
            await ctx.respond(embed=makeEmbed(":warning: Error :warning:", f"{e}", Color.error), ephemeral=True)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data)


class SongPlayer(commands.Cog):
    def __init__(self, ctx: ApplicationContext, players):
        self.ctx = ctx
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.queue_list = []
        self.next = asyncio.Event()

        self.now_playing = None
        self.volume = 0.5
        self.current = None

        self.repeat = False
        self.repeat_count = 0
        self.first = None

        self.queue_message = {}

        self.players = players

        ctx.bot.loop.create_task(self.player_loop())

    async def terminate(self):
        for message in self.queue_message.values():
            await message.delete()

        return self.bot.loop.create_task(cleanup(self._guild, self.players))

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                if len(self.ctx.voice_client.channel.members) == 1:
                    await self._channel.send(
                        embed=makeEmbed(":mute: Leave :mute:", "음성 채팅방이 비어 재생을 중지하고 떠납니다.", Color.success))

                    await self.terminate()

                async with timeout(300):
                    source = await self.queue.get()

                    if self.repeat:
                        if source.url == self.first.url:
                            self.repeat_count -= 1

                        if self.repeat_count == 0:
                            self.repeat = False
                            self.first = None
                            self.queue_list = list(self.queue._queue)

                        source_new = await YTDLSource.create_source(self.ctx, url=source.url, loop=self.bot.loop,
                                                                    download=True, send_message=False)
                        await self.queue.put(source_new)
                    else:
                        self.queue_list.pop(0)

                    if self.queue_message:
                        await edit_queue_message(self, source)
            except asyncio.TimeoutError:
                await self.terminate()
            except AttributeError:
                pass

            if not isinstance(source, YTDLSource):
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(embed=makeEmbed(":warning: Error :warning:", f"{e}", Color.error))
                    continue

            source.volume = self.volume
            self.current = source

            try:
                self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))

                class NowPlaying(discord.ui.View):
                    def __init__(self, ctx: ApplicationContext, queue: asyncio.Queue):
                        super().__init__(timeout=None)

                        if ctx.voice_client.is_paused():
                            self.add_item(ResumeButton(ctx, queue))
                        else:
                            self.add_item(PauseButton(ctx, queue))

                        if queue.qsize() > 1:
                            self.add_item(NextButton(ctx, queue))

                class PauseButton(discord.ui.Button):
                    def __init__(self, ctx: ApplicationContext, queue: asyncio.Queue):
                        super().__init__(
                            emoji="⏸️",
                            custom_id="pause",
                            style=discord.ButtonStyle.blurple
                        )

                        self.ctx = ctx
                        self.queue = queue

                    async def callback(self, interaction: discord.Interaction):
                        self.ctx.voice_client.pause()

                        await interaction.response.edit_message(view=NowPlaying(self.ctx, self.queue))

                class ResumeButton(discord.ui.Button):
                    def __init__(self, ctx: ApplicationContext, queue: asyncio.Queue):
                        super().__init__(
                            emoji="⏹️",
                            custom_id="resume",
                            style=discord.ButtonStyle.blurple
                        )

                        self.ctx = ctx
                        self.queue = queue

                    async def callback(self, interaction: discord.Interaction):
                        self.ctx.voice_client.resume()

                        await interaction.response.edit_message(view=NowPlaying(self.ctx, self.queue))

                class NextButton(discord.ui.Button):
                    def __init__(self, ctx: ApplicationContext, queue: asyncio.Queue):
                        super().__init__(
                            emoji="⏭️",
                            custom_id="next",
                            style=discord.ButtonStyle.blurple
                        )

                        self.ctx = ctx
                        self.queue = queue

                    async def callback(self, interaction: discord.Interaction):
                        await interaction.response.defer()
                        self.ctx.voice_client.stop()

                self.now_playing = await self._channel.send(
                    embed=makeEmbed(":musical_note: **Now Playing** :musical_note:",
                                    f"[**{source.title}**](<{source.url}>)", Color.success),
                    view=NowPlaying(self.ctx, self.queue))
            except AttributeError:
                pass

            await self.next.wait()

            source.cleanup()

            try:
                await self.now_playing.delete()
            except discord.HTTPException:
                pass


async def cleanup(guild: discord.Guild, players) -> None:
    try:
        await guild.voice_client.disconnect()
    except AttributeError:
        pass

    try:
        del players[guild.id]
    except KeyError:
        pass

    try:
        shutil.rmtree(f'downloads/{guild.id}')
    except PermissionError:
        pass


async def add_to_queue(player: SongPlayer, source: YTDLSource) -> None:
    if player.repeat:
        if player.queue.qsize() == 1:
            new_queue = asyncio.Queue()

            await new_queue.put(source)
            await new_queue.put(player.queue._queue[0])

            player.queue_list.append(source)

            player.queue = new_queue
        else:
            new_queue = asyncio.Queue()

            for cur in list(player.queue._queue):
                await new_queue.put(cur)

                if cur.url == player.queue_list[-1].url:
                    await new_queue.put(source)
                    player.queue_list.append(source)

            player.queue = new_queue
    else:
        await player.queue.put(source)
        player.queue_list.append(source)

    if player.queue_message:
        await edit_queue_message(player, player.current)


async def edit_queue_message(player: SongPlayer, source: YTDLSource) -> None:
    embed = makeEmbed(":musical_note: Queue :musical_note:",
                      f"**Now Playing**\n> {source.title}",
                      Color.success)

    if player.repeat:
        embed.description += f"\n\n:arrows_counterclockwise: **Repeating** :arrows_counterclockwise:"

        if player.repeat_count_max != -1:
            embed.description += f"\n> {player.repeat_count_max - player.repeat_count} / {player.repeat_count_max}"

    if not player.queue.empty():
        embed = set_queue_field(embed, player.queue_list, 0)

    for message in player.queue_message.values():
        await message.edit_original_response(embed=embed,
                                             view=None if player.queue.empty() else
                                             QueueMainView(player.queue, player.queue_list, 0))
