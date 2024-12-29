import discord
from discord import Option, ApplicationContext
from discord.ext import commands

import asyncio

from modules.make_embed import makeEmbed, Field, Color
from modules.song_queue_button import QueueMainView
from modules.song_player import YTDLSource, SongPlayer


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
                return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "시간초과\n\n다시 시도하여 주세요.", Color.error))
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "시간초과\n\n다시 시도하여 주세요.", Color.error))

    # 음챗 나가기
    # Param: ctx
    @song_commands.command(name="leave", name_localizations={"ko": "나가"},
                           description="Let the bot leave",
                           description_localizations={"ko": "봇을 퇴장시킵니다."})
    async def leave_(self, ctx: ApplicationContext):
        if ctx.voice_client is None:
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "음성 채팅방에 접속해야 합니다.", Color.error))

        await ctx.voice_client.disconnect()
        return await ctx.respond("힝")

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
