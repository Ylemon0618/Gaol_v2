import asyncio
import os

import discord
from discord import Option, ApplicationContext
from discord.ext import commands
from dotenv import load_dotenv

from modules.make_embed import makeEmbed, Color
from modules.song_player import YTDLSource, SongPlayer, cleanup, add_to_queue
from modules.song_button import QueueMainView, set_queue_field, MoveChannelView, ResetQueueView, ChangeRepeatView
from modules.messages import SongEmbed

load_dotenv()

guild_ids = list(map(int, os.environ.get('GUILDS').split()))


class Song(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players = {}
        self.queue = asyncio.Queue()

    song_commands = discord.SlashCommandGroup(name="song", name_localizations={"ko": "노래"},
                                              description="Commands for song",
                                              description_localizations={"ko": "노래와 관련된 명령어"},
                                              guild_ids=guild_ids)

    def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = SongPlayer(ctx, self.players)
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
            return await ctx.respond(embed=SongEmbed.Error.invalid_voice)

        vc = ctx.voice_client

        if vc:
            if vc.channel.id == channel.id:
                return

            try:
                return await ctx.respond(embed=SongEmbed.UI.convert, view=MoveChannelView(vc, channel))
            except asyncio.TimeoutError:
                return await ctx.respond(embed=SongEmbed.Error.timeout)
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                return await ctx.respond(embed=SongEmbed.Error.timeout)

        await ctx.respond(embed=makeEmbed(":musical_note: Joined :musical_note:", channel.mention, Color.success))

    # 음챗 나가기
    # Param: ctx
    @song_commands.command(name="leave", name_localizations={"ko": "퇴장"},
                           description="Let the bot leave",
                           description_localizations={"ko": "봇을 퇴장시킵니다."})
    async def leave_(self, ctx: ApplicationContext):
        if ctx.voice_client is None:
            return await ctx.respond(embed=SongEmbed.Error.not_connected)

        await ctx.voice_client.disconnect()
        return await ctx.respond(embed=SongEmbed.Success.leave)

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
            return await ctx.respond(embed=SongEmbed.Error.not_connected)

        if ctx.voice_client.source is None:
            return await ctx.respond(embed=SongEmbed.Error.not_playing)

        if volume == 0:
            emoji = ":mute:"
        elif volume < 50:
            emoji = ":sound:"
        elif volume < 100:
            emoji = ":loud_sound:"
        elif volume == 100:
            emoji = ":loudspeaker:"
        else:
            return await ctx.respond(embed=SongEmbed.Error.invalid_value)

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
        if ctx.user.voice is None:
            return await ctx.respond(embed=SongEmbed.Error.not_connected)

        await ctx.defer()
        await ctx.trigger_typing()

        if not ctx.voice_client:
            await self.join_(ctx)

        vc = ctx.voice_client

        if vc.channel != ctx.user.voice.channel:
            return await ctx.respond(embed=makeEmbed("Confirm",
                                                     f"현재 봇이 {vc.channel.mention}에 접속해 있습니다.\n\n{ctx.user.voice.channel.mention}(으)로 옮기시려면 **확인**을 클릭 해 주세요.",
                                                     Color.warning),
                                     view=MoveChannelView(vc, ctx.user.voice.channel,
                                                          ResetQueueView(self.bot, ctx, self.players, song)))
        else:
            player = self.get_player(ctx)
            source = await YTDLSource.create_source(ctx, url=song, loop=self.bot.loop, download=True)

            await add_to_queue(player, source)

    # 재생 일시정지
    # Param: ctx
    @song_commands.command(name="pause", name_localizations={"ko": "일시정지"},
                           description="Pause the song playing",
                           description_localizations={"ko": "재생 중인 노래를 일시정지 합니다."})
    async def pause_(self, ctx: ApplicationContext):
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            return await ctx.respond(embed=SongEmbed.Error.not_playing)
        elif vc.is_paused():
            return

        vc.pause()
        await ctx.respond(embed=SongEmbed.Success.pause)

    # 재생 재개
    # Param: ctx
    @song_commands.command(name="resume", name_localizations={"ko": "재개"},
                           description="Resume paused song",
                           description_localizations={"ko": "일시정지 된 노래를 다시 재생합니다."})
    async def resume_(self, ctx: ApplicationContext):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.respond(embed=SongEmbed.Error.not_paused)
        elif not vc.is_paused():
            return

        vc.resume()
        await ctx.respond(embed=SongEmbed.Success.resume)

    # 노래 스킵
    # Param: ctx
    @song_commands.command(name="skip", name_localizations={"ko": "스킵"},
                           description="Skip the song",
                           description_localizations={"ko": "현재 재생 중인 노래를 스킵합니다."})
    async def skip_(self, ctx: ApplicationContext):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.respond(embed=SongEmbed.Error.not_playing)

        if not vc.is_playing() and not vc.is_paused():
            return

        vc.stop()
        await ctx.respond(embed=SongEmbed.Success.skip)

    # 노래 중지
    # Param: ctx
    @song_commands.command(name="stop", name_localizations={"ko": "중지"},
                           description="Stop the song",
                           description_localizations={"ko": "노래 재생을 중지합니다."})
    async def stop_(self, ctx: ApplicationContext):
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return await ctx.respond(embed=SongEmbed.Error.not_playing)

        await cleanup(ctx.guild, self.players)

        await ctx.respond(embed=SongEmbed.Success.stop)

    # 대기열 확인/편집
    # Param: ctx
    @song_commands.command(name="queue", name_localizations={"ko": "대기열"},
                           description="Check the queue",
                           description_localizations={"ko": "대기열을 확인 및 편집합니다."})
    async def queue_(self, ctx: ApplicationContext):
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            return await ctx.respond(embed=SongEmbed.Error.not_playing)

        player = self.get_player(ctx)

        if self.players[ctx.guild.id].queue.empty():
            return await ctx.respond(embed=makeEmbed(":musical_note: Queue :musical_note:",
                                                     f"**Now Playing**\n> {player.current.title}",
                                                     Color.success))

        self.queue = self.players[ctx.guild.id].queue
        queue_list = self.players[ctx.guild.id].queue_list

        embed = makeEmbed(":musical_note: Queue :musical_note:",
                          f"**Now Playing**\n> {player.current.title}",
                          Color.success)

        if player.repeat:
            embed.description += f"\n\n:arrows_counterclockwise: **Repeating** :arrows_counterclockwise:"

            if player.repeat_count_max != -1:
                embed.description += f"\n> {player.repeat_count_max - player.repeat_count} / {player.repeat_count_max}"

        embed = set_queue_field(embed, queue_list, 0)

        await ctx.respond(embed=embed, view=QueueMainView(self.players[ctx.guild.id].queue, queue_list, 0))

    # 대기열 반복
    # Param: ctx, 횟수
    @song_commands.command(name="repeat", name_localizations={"ko": "반복"},
                           description="Repeat the queue",
                           description_localizations={"ko": "대기열을 반복합니다."})
    async def repeat_(self, ctx: ApplicationContext,
                      count: Option(int, name="count", name_localizations={"ko": "횟수"},
                                    description="Enter the count to repeat",
                                    description_localizations={"ko": "반복 횟수를 입력 해 주세요."}) = None):
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            return await ctx.respond(embed=SongEmbed.Error.not_playing)

        if count and count <= 1:
            return await ctx.respond(embed=SongEmbed.Error.invalid_value)

        player = self.get_player(ctx)

        if player.repeat:
            embed = SongEmbed.UI.repeat_confirm.copy()

            if player.repeat_count_max != -1:
                embed.description += f"({player.repeat_count_max - player.repeat_count} / {player.repeat_count_max})"
            embed.description += "\n\n반복 정보를 수정하시려면 **확인**을 클릭 해 주세요."

            return await ctx.respond(embed=embed, view=ChangeRepeatView(ctx, self.bot, self.players, count))

        embed = SongEmbed.Success.repeat

        if count:
            player.repeat_count = count - 1
            player.repeat_count_max = count

            embed.description = f"대기열을 {count}번 반복합니다."
        else:
            player.repeat_count = player.repeat_count_max = -1

        await ctx.respond(embed=embed)

        player.repeat = True
        player.first = player.current
        player.queue_list = [player.first] + list(player.queue._queue)

        source = await YTDLSource.create_source(ctx, url=player.current.url, loop=self.bot.loop, download=True,
                                                send_message=False)
        await player.queue.put(source)

    # 반복 중지
    # Param: ctx
    @song_commands.command(name="stop_repeat", name_localizations={"ko": "반복중지"},
                           description="Stop the repeat",
                           description_localizations={"ko": "반복을 중지합니다."})
    async def stop_repeat_(self, ctx: ApplicationContext):
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            return await ctx.respond(embed=SongEmbed.Error.not_playing)

        player = self.get_player(ctx)

        if not player.repeat:
            return await ctx.respond(embed=SongEmbed.Error.not_repeating)

        player.repeat = False
        player.repeat_count = player.repeat_count_max = 0
        player.first = None
        player.queue_list = list(player.queue._queue)

        await ctx.respond(embed=SongEmbed.Success.stop_repeat)


def setup(bot):
    bot.add_cog(Song(bot))
