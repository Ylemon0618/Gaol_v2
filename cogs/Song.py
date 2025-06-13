import asyncio
import time
import os
from dotenv import load_dotenv

import discord
from discord import Option, ApplicationContext
from discord.ext import commands
from pytube import Playlist

from modules.make_embed import *
from modules.song_player import YTDLSource, SongPlayer, cleanup, add_to_queue, edit_queue_message
from modules.song_change import MoveChannelView, ResetQueueView, ChangeRepeatView
from modules.song_queue import QueueMainView, set_queue_field
from modules.messages import SongEmbed
from modules.song_custom_playlist import SongCustomPlaylistView

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
                return None

            try:
                return await ctx.respond(embed=SongEmbed.UI.convert, view=MoveChannelView(vc, channel))
            except asyncio.TimeoutError:
                return await ctx.respond(embed=SongEmbed.Error.timeout)
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                return await ctx.respond(embed=SongEmbed.Error.timeout)

        container = discord.ui.Container()
        container.add_text(f"## Joined\n\n{channel.mention}")
        return await ctx.respond(view=makeView(container))

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

        player = self.get_player(ctx)

        if "list=" in song:
            pl = Playlist(song)

            songs = pl.video_urls if len(pl.video_urls) <= 20 else pl.video_urls[:20]
            if not pl.video_urls:
                source = await YTDLSource.create_source(ctx, url=song, requester=ctx.author, loop=self.bot.loop,
                                                        download=True)
                return await add_to_queue(player, source)

            downloading = await ctx.respond(embed=makeEmbed(":arrow_down: Downloading :arrow_down:",
                                                            "플레이리스트를 다운로드 중입니다...", Color.success))

            thumbnail = None
            duration = 0
            for url in songs:
                source = await YTDLSource.create_source(ctx, url=url, requester=ctx.author, loop=self.bot.loop,
                                                        download=True,
                                                        send_message=False)
                await add_to_queue(player, source)

                if not thumbnail:
                    thumbnail = source.thumbnail
                duration += source.duration

            embed = makeEmbed(":cd: Play | 재생 :cd:", f"[**{pl.title}**](<{pl.playlist_url}>)", Color.success)

            embed.add_field(name="Owner", value=f"[{pl.owner}](<{pl.owner_url}>)", inline=True)

            if duration >= 3600:
                duration_string = time.strftime('%H:%M:%S', time.gmtime(duration))
            else:
                duration_string = time.strftime('%M:%S', time.gmtime(duration))
            embed.add_field(name="Duration", value=duration_string, inline=True)

            embed.set_thumbnail(url=thumbnail)

            embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

            return await downloading.edit(embed=embed)
        else:
            source = await YTDLSource.create_source(ctx, url=song, requester=ctx.author, loop=self.bot.loop,
                                                    download=True)

            return await add_to_queue(player, source)

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
            return None

        vc.pause()
        return await ctx.respond(embed=SongEmbed.Success.pause)

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
            return None

        vc.resume()
        return await ctx.respond(embed=SongEmbed.Success.resume)

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
            return None

        vc.stop()
        return await ctx.respond(embed=SongEmbed.Success.skip)

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

        return await ctx.respond(embed=SongEmbed.Success.stop)

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

        embed = makeEmbed(":musical_note: Queue :musical_note:",
                          f"**Now Playing**\n> {player.current.title}",
                          Color.success)

        self.queue = player.queue
        queue_list = player.queue_list

        if player.repeat:
            embed.description += f"\n\n:arrows_counterclockwise: **Repeating** :arrows_counterclockwise:"

            if player.repeat_count_max != -1:
                embed.description += f"\n> {player.repeat_count_max - player.repeat_count} / {player.repeat_count_max}"

        if not player.queue.empty():
            embed = set_queue_field(embed, queue_list, 0)

        try:
            if ctx.channel.id in player.queue_message:
                await player.queue_message[ctx.channel.id].delete_original_response()

            message = await ctx.respond(embed=embed,
                                        view=None if player.queue.empty() else
                                        QueueMainView(player.queue, queue_list, 0))

            player.queue_message[ctx.channel.id] = message
            return message
        except:
            return None

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

        source = await YTDLSource.create_source(ctx, url=player.current.url, requester=player.current.requester,
                                                loop=self.bot.loop, download=True, send_message=False)
        await player.queue.put(source)

        if player.queue_message:
            await edit_queue_message(player, player.current)

        return None

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

        return await ctx.respond(embed=SongEmbed.Success.stop_repeat)

    # 커스텀 플레이리스트
    # Param: ctx
    @song_commands.command(name="playlist", name_localizations={"ko": "플레이리스트"},
                           description="Manage custom playlist",
                           description_localizations={"ko": "커스텀 플레이리스트를 관리합니다."})
    async def playlist_(self, ctx: ApplicationContext):
        return await ctx.respond(embed=makeEmbed(":cd: Playlist | 플레이리스트 :cd:",
                                                 "Manage custom playlist.\n커스텀 플레이리스트를 관리합니다.", Color.success),
                                 view=SongCustomPlaylistView(ctx, self.bot, self.players, ctx.author.id),
                                 ephemeral=True)


def setup(bot):
    bot.add_cog(Song(bot))
