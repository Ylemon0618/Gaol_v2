import os
from math import ceil
import time
import asyncio
from urllib import request, parse
from yt_dlp import YoutubeDL

import discord
from discord import Interaction, ApplicationContext
from discord.ext import commands
from dotenv import load_dotenv

from pymongo.mongo_client import MongoClient

from modules.make_embed import makeEmbed, Color
from modules.messages.embeds import SongEmbed
from modules.song_player import YTDLSource, add_to_queue, SongPlayer
from modules.song_change.change_channel import MoveChannelView

load_dotenv()

client = MongoClient(os.environ.get('MONGO_URI'))

db = client["gaol"]
custom_playlist = db["custom_playlist"]

song_cnt = int(os.environ.get('PAGE_SIZE'))


def insert_song(user_id: int, url: str, title: str):
    return custom_playlist.find_one_and_update({"user_id": user_id}, {"$push": {"playlist": url, "title": title}})


def delete_song(user_id: int, url: str, title: str):
    return custom_playlist.find_one_and_update({"user_id": user_id}, {"$pull": {"playlist": url, "title": title}})


def set_playlist_field(title: list, page: int, title_type: str = "field", selected: str = None):
    embed = makeEmbed(f":notes: Playlist ({page + 1} / {ceil(len(title) / 10)}) :notes:", f"", Color.success)
    for idx in range(page * song_cnt, page * song_cnt + song_cnt):
        if idx >= len(title):
            break

        if title_type == "field":
            embed.add_field(name=title[idx], value="", inline=False)
        elif title_type == "description":
            if selected == title[idx]:
                embed.description += f"**{title[idx]}**\n\n"
            else:
                embed.description += f"{title[idx]}\n\n"

    return embed


def swap(playlist: list, title: list, idx1: int, idx2: int):
    playlist.insert(idx2, playlist.pop(idx1))
    title.insert(idx2, title.pop(idx1))

    return playlist, title


async def join(ctx: ApplicationContext):
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


class SongCustomPlaylistView(discord.ui.View):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict, user_id: int):
        super().__init__(timeout=None)

        self.add_item(SongCustomPlaylistSelect(ctx, bot, players, user_id))


class SongCustomPlaylistSelect(discord.ui.Select):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict, user_id: int):
        super().__init__(
            placeholder="Choose a task",
            options=[
                discord.SelectOption(label="Play | 재생", value="play", emoji="▶️",
                                     description="Add your playlist to the queue | 플레이리스트를 대기열에 추가합니다."),
                discord.SelectOption(label="Add song | 노래 추가", value="add", emoji="➕",
                                     description="Add a song to the playlist | 플레이리스트에 노래를 추가합니다."),
                discord.SelectOption(label="Show playlist | 플레이리스트 조회", value="show", emoji="📜",
                                     description="Show and manage the playlist | 플레이리스트를 조회 및 관리합니다.")
            ]
        )

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        try:
            self.playlist = custom_playlist.find_one({"user_id": user_id})["playlist"]
            self.title = custom_playlist.find_one({"user_id": user_id})["title"]
        except TypeError:
            custom_playlist.insert_one({"user_id": user_id, "playlist": [], "title": []})
            self.playlist = []
            self.title = []

    def get_player(self):
        try:
            player = self.players[self.ctx.guild.id]
        except KeyError:
            player = SongPlayer(self.ctx, self.players)
            self.players[self.ctx.guild.id] = player

        return player

    async def callback(self, interaction: Interaction):
        task = self.values[0]

        if task == "play":
            if not self.playlist:
                return await interaction.response.edit_message(
                    embed=makeEmbed(":cd: Playlist | 플레이리스트 :cd:",
                                    "Playlist is empty.\n플레이리스트가 비어 있습니다.\n\nClick the button to add songs!\n버튼을 클릭하여 노래를 추가하세요!",
                                    Color.warning),
                    view=SongCustomPlaylistAddButton(self.user_id))

            await interaction.response.defer()
            await self.ctx.trigger_typing()

            if not self.ctx.voice_client:
                await join(self.ctx)

            vc = self.ctx.voice_client

            if vc.channel != self.ctx.user.voice.channel:
                return await self.ctx.respond(
                    embed=makeEmbed("Confirm",
                                    f"현재 봇이 {vc.channel.mention}에 접속해 있습니다.\n\n{self.ctx.user.voice.channel.mention}(으)로 옮기시려면 **확인**을 클릭 해 주세요.",
                                    Color.warning),
                    view=MoveChannelView(vc, self.ctx.user.voice.channel))

            downloading = await self.ctx.respond(
                embed=makeEmbed(":arrow_down: Downloading :arrow_down:",
                                "플레이리스트를 다운로드 중입니다...", Color.success))

            player = self.get_player()

            thumbnail = None
            duration = 0
            for url in self.playlist:
                source = await YTDLSource.create_source(self.ctx, url=url, requester=self.ctx.author,
                                                        loop=self.bot.loop, download=True, send_message=False)
                await add_to_queue(player, source)

                if not thumbnail:
                    thumbnail = source.thumbnail
                duration += source.duration

            embed = makeEmbed(":cd: Playlist | 플레이리스트 :cd:",
                              f"Added custom playlist to the queue.\n커스텀 플레이리스트를 대기열에 추가했습니다.",
                              Color.success)

            embed.add_field(name="Owner", value=f"{self.ctx.author.mention}", inline=True)

            if duration >= 3600:
                duration_string = time.strftime('%H:%M:%S', time.gmtime(duration))
            else:
                duration_string = time.strftime('%M:%S', time.gmtime(duration))
            embed.add_field(name="Duration", value=duration_string, inline=True)

            embed.set_thumbnail(url=thumbnail)

            embed.set_footer(text=self.ctx.author.display_name, icon_url=self.ctx.author.display_avatar.url)

            await downloading.edit(embed=embed)
        elif task == "add":
            await interaction.response.send_modal(modal=SongCustomPlaylistAddModal(self.user_id, self.playlist))
        elif task == "show":
            if not self.playlist:
                return await interaction.response.edit_message(
                    embed=makeEmbed(":cd: Playlist | 플레이리스트 :cd:",
                                    "Playlist is empty.\n플레이리스트가 비어 있습니다.\n\nClick the button to add songs!\n버튼을 클릭하여 노래를 추가하세요!",
                                    Color.warning),
                    view=SongCustomPlaylistAddButton(self.user_id))

            await interaction.response.edit_message(
                embed=set_playlist_field(self.title, 0),
                view=SongCustomPlaylistShowView(self.ctx, self.bot, self.players,
                                                self.user_id, self.playlist, self.title))


class SongCustomPlaylistAddButton(discord.ui.Button):
    def __init__(self, user_id: int):
        super().__init__(
            label="Add song", style=discord.ButtonStyle.blurple, emoji="➕"
        )

        self.user_id = user_id

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(modal=SongCustomPlaylistAddModal(self.user_id, []))


class SongCustomPlaylistAddModal(discord.ui.Modal):
    def __init__(self, user_id: int, playlist: list):
        super().__init__(title="Add song | 노래 추가")

        self.user_id = user_id
        self.playlist = playlist

        self.add_item(discord.ui.InputText(label="Please enter url. url을 입력해 주세요.",
                                           placeholder="URL", style=discord.InputTextStyle.short, custom_id="url"))

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()

        url = self.children[0].value

        if request.urlopen(url).getcode() != 200:
            return await interaction.followup.edit_message(message_id=interaction.message.id,
                                                           embed=makeEmbed(":warning: Error :warning:",
                                                                           "Invalid URL.\n올바르지 않은 URL입니다.",
                                                                           Color.error))

        if parse.urlparse(url).netloc not in ["www.youtube.com", "www.youtu.be", "youtube.com", "youtu.be"]:
            return await interaction.followup.edit_message(message_id=interaction.message.id,
                                                           embed=makeEmbed(":warning: Error :warning:",
                                                                           "Invalid URL.\n올바르지 않은 URL입니다.",
                                                                           Color.error))

        if url in self.playlist:
            return await interaction.followup.edit_message(message_id=interaction.message.id,
                                                           embed=makeEmbed(":warning: Error :warning:",
                                                                           "Already in playlist.\n이미 플레이리스트에 있는 노래입니다.",
                                                                           Color.error))

        await interaction.followup.edit_message(message_id=interaction.message.id,
                                                embed=makeEmbed(
                                                    ":arrows_counterclockwise: Loading :arrows_counterclockwise:",
                                                    "Loading...\n로딩 중...",
                                                    Color.warning),
                                                view=None)

        ytdl = YoutubeDL({
            'format': 'bestaudio/best',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0'
        })

        data = ytdl.extract_info(url=url, download=False)
        if 'entries' in data:
            data = data['entries'][0]

        insert_song(self.user_id, f"https://www.youtube.com/watch?v={data['display_id']}", data['title'])

        embed = makeEmbed(":white_check_mark: Success :white_check_mark:",
                          f"Successfully added to playlist.\n플레이리스트에 성공적으로 추가되었습니다.\n\n[**{data['title']}**](<{data['webpage_url']}>)",
                          Color.success)

        channel = data['uploader']
        if 'channel_is_verified' in data:
            channel += "<:verified:1337271571043192893>"
        if data['uploader_id'] and data['uploader_url']:
            channel += f" ([{data['uploader_id']}](<{data['uploader_url']}>))"

        embed.add_field(name="Channel", value=channel, inline=True)
        embed.add_field(name="Duration", value=data['duration_string'], inline=True)

        embed.set_thumbnail(url=data['thumbnail'])

        await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed)


class SongCustomPlaylistShowView(discord.ui.View):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list, page: int = 0):
        super().__init__(timeout=None)

        self.add_item(SongCustomPlaylistShowSelect(ctx, bot, players, user_id, playlist, title, page))

        min_page = 0
        max_page = (len(title) - 1) // song_cnt

        if page == min_page:
            self.add_item(SongCustomPlaylistShowPrevButton(ctx, bot, players, user_id, playlist, title, page, True))
        else:
            self.add_item(SongCustomPlaylistShowPrevButton(ctx, bot, players, user_id, playlist, title, page))

        if page == max_page:
            self.add_item(SongCustomPlaylistShowNextButton(ctx, bot, players, user_id, playlist, title, page, True))
        else:
            self.add_item(SongCustomPlaylistShowNextButton(ctx, bot, players, user_id, playlist, title, page))

        self.add_item(SongCustomPlaylistShowBackButton(ctx, bot, players, user_id))


class SongCustomPlaylistShowSelect(discord.ui.Select):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list, page: int):
        options = []
        for idx in range(page * song_cnt, page * song_cnt + song_cnt):
            if idx >= len(title):
                break

            options.append(discord.SelectOption(label=title[idx], value=f"{idx}"))

        super().__init__(
            placeholder="Choose a song",
            options=options
        )

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.page = page

    async def callback(self, interaction: Interaction):
        choice_num = int(self.values[0])
        url = self.playlist[choice_num]
        title = self.title[choice_num]

        await interaction.response.edit_message(
            embed=makeEmbed(":notes: Playlist - selected :notes:", f"[**{title}**](<{url}>)", Color.success),
            view=SongCustomPlaylistSelectedView(self.ctx, self.bot, self.players,
                                                self.user_id, self.playlist, self.title, choice_num, self.page))


class SongCustomPlaylistShowPrevButton(discord.ui.Button):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list, page: int, disabled: bool = False):
        super().__init__(style=discord.ButtonStyle.primary, label="Prev", emoji="⬅️", disabled=disabled)

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.page = page

    async def callback(self, interaction: Interaction):
        self.page -= 1
        await interaction.response.edit_message(
            embed=set_playlist_field(self.title, self.page),
            view=SongCustomPlaylistShowView(self.ctx, self.bot, self.players,
                                            self.user_id, self.playlist, self.title, self.page))


class SongCustomPlaylistShowNextButton(discord.ui.Button):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list, page: int, disabled: bool = False):
        super().__init__(style=discord.ButtonStyle.primary, label="Next", emoji="➡️", disabled=disabled)

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.page = page

    async def callback(self, interaction: Interaction):
        self.page += 1
        await interaction.response.edit_message(
            embed=set_playlist_field(self.title, self.page),
            view=SongCustomPlaylistShowView(self.ctx, self.bot, self.players,
                                            self.user_id, self.playlist, self.title, self.page))


class SongCustomPlaylistShowBackButton(discord.ui.Button):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict, user_id: int):
        super().__init__(
            label="Back", style=discord.ButtonStyle.green, emoji="🔙"
        )

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(
            embed=makeEmbed(":cd: Playlist | 플레이리스트 :cd:",
                            "Manage custom playlist.\n커스텀 플레이리스트를 관리합니다.",
                            Color.success),
            view=SongCustomPlaylistView(self.ctx, self.bot, self.players, self.user_id))


class SongCustomPlaylistSelectedView(discord.ui.View):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list, choice_num: int, page: int):
        super().__init__(timeout=None)

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.choice_num = choice_num
        self.page = page
        self.selected_url = playlist[choice_num]
        self.selected_title = title[choice_num]

        self.add_item(SongCustomPlaylistSelectedSelect(
            ctx, bot, players, user_id, playlist, title, choice_num, page, self.selected_url, self.selected_title))
        self.add_item(SongCustomPlaylistSelectedBackButton(ctx, bot, players, user_id, playlist, title))


class SongCustomPlaylistSelectedSelect(discord.ui.Select):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list, choice_num: int, page: int,
                 selected_url: str, selected_title: str):
        super().__init__(
            placeholder="Choose a task",
            options=[
                discord.SelectOption(label="Delete song | 노래 삭제", value="delete", emoji="❌",
                                     description="Delete the selected song | 선택한 노래를 삭제합니다."),
                discord.SelectOption(label="Change order | 순서 변경", value="change", emoji="🔄",
                                     description="Change the order of the selected song | 선택한 노래의 순서를 변경합니다.")
            ]
        )

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.choice_num = choice_num
        self.page = page
        self.selected_url = selected_url
        self.selected_title = selected_title

    async def callback(self, interaction: Interaction):
        task = self.values[0]

        if task == "delete":
            delete_song(self.user_id, self.selected_url, self.selected_title)
            self.playlist.remove(self.selected_url)
            self.title.remove(self.selected_title)

            await interaction.response.edit_message(
                embed=makeEmbed(":white_check_mark: Success :white_check_mark:",
                                "Successfully deleted from playlist.\n플레이리스트에서 성공적으로 삭제되었습니다.",
                                Color.success),
                view=SongCustomPlaylistDeletedView(self.ctx, self.bot, self.players,
                                                   self.user_id, self.playlist, self.title, self.choice_num,
                                                   self.selected_url, self.selected_title))
        elif task == "change":
            await interaction.response.edit_message(
                embed=set_playlist_field(self.title, self.page, "description", self.selected_title),
                view=SongCustomPlaylistChangeOrderView(
                    self.ctx, self.bot, self.players,
                    self.user_id, self.playlist, self.title, self.choice_num, self.page,
                    self.selected_url, self.selected_title))


class SongCustomPlaylistSelectedBackButton(discord.ui.Button):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list):
        super().__init__(
            label="Back", style=discord.ButtonStyle.green, emoji="🔙"
        )

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        self.playlist = playlist
        self.title = title

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(
            embed=set_playlist_field(self.title, 0),
            view=SongCustomPlaylistShowView(self.ctx, self.bot, self.players,
                                            self.user_id, self.playlist, self.title))


class SongCustomPlaylistDeletedView(discord.ui.View):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list, choice_num: int,
                 selected_url: str, selected_title: str):
        super().__init__(timeout=None)

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.choice_num = choice_num
        self.selected_url = selected_url
        self.selected_title = selected_title

        self.add_item(
            SongCustomPlaylistDeletedCancelButton(
                ctx, bot, players, user_id, playlist, title, choice_num, selected_url, selected_title))
        self.add_item(SongCustomPlaylistDeletedBackButton(ctx, bot, players, user_id, playlist, title))


class SongCustomPlaylistDeletedCancelButton(discord.ui.Button):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list, choice_num: int,
                 selected_url: str, selected_title: str):
        super().__init__(
            label="Cancel", style=discord.ButtonStyle.red, emoji="✖"
        )

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.choice_num = choice_num
        self.selected_url = selected_url
        self.selected_title = selected_title

    async def callback(self, interaction: Interaction):
        self.playlist.insert(self.choice_num, self.selected_url)
        self.title.insert(self.choice_num, self.selected_title)

        custom_playlist.update_one({"user_id": self.user_id}, {"$set": {"playlist": self.playlist}})
        custom_playlist.update_one({"user_id": self.user_id}, {"$set": {"title": self.title}})

        return await interaction.response.edit_message(
            embed=set_playlist_field(self.title, 0),
            view=SongCustomPlaylistShowView(self.ctx, self.bot, self.players, self.user_id, self.playlist, self.title))


class SongCustomPlaylistDeletedBackButton(discord.ui.Button):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list):
        super().__init__(
            label="Back", style=discord.ButtonStyle.green, emoji="🔙"
        )

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        self.playlist = playlist
        self.title = title

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(
            embed=set_playlist_field(self.title, 0),
            view=SongCustomPlaylistShowView(self.ctx, self.bot, self.players, self.user_id, self.playlist, self.title))


class SongCustomPlaylistChangeOrderView(discord.ui.View):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list, choice_num: int, page: int,
                 selected_url: str, selected_title: str):
        super().__init__(timeout=None)

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.choice_num = choice_num
        self.page = page
        self.selected_url = selected_url
        self.selected_title = selected_title

        self.add_item(SongCustomPlaylistChangeOrderUpButton(
            ctx, bot, players, user_id, playlist, title, choice_num, page, selected_url, selected_title))
        self.add_item(SongCustomPlaylistChangeOrderDownButton(
            ctx, bot, players, user_id, playlist, title, choice_num, page, selected_url, selected_title))
        self.add_item(SongCustomPlaylistChangeOrderBackButton(
            ctx, bot, players, user_id, playlist, title, choice_num, page, selected_url, selected_title))


class SongCustomPlaylistChangeOrderUpButton(discord.ui.Button):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list, choice_num: int, page: int,
                 selected_url: str, selected_title: str):
        super().__init__(
            label="", style=discord.ButtonStyle.primary, emoji="⬆️",
        )

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.choice_num = choice_num
        self.page = page
        self.selected_url = selected_url
        self.selected_title = selected_title

    async def callback(self, interaction: Interaction):
        self.playlist, self.title = swap(self.playlist, self.title,
                                         self.choice_num, (self.choice_num - 1) % len(self.playlist))

        self.choice_num = (self.choice_num - 1) % len(self.playlist)
        self.page = self.choice_num // song_cnt

        custom_playlist.update_one({"user_id": self.user_id}, {"$set": {"playlist": self.playlist}})
        custom_playlist.update_one({"user_id": self.user_id}, {"$set": {"title": self.title}})

        await interaction.response.edit_message(
            embed=set_playlist_field(self.title, self.page, "description", self.selected_title),
            view=SongCustomPlaylistChangeOrderView(self.ctx, self.bot, self.players,
                                                   self.user_id, self.playlist, self.title, self.choice_num, self.page,
                                                   self.selected_url, self.selected_title))


class SongCustomPlaylistChangeOrderDownButton(discord.ui.Button):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list, choice_num: int, page: int,
                 selected_url: str, selected_title: str):
        super().__init__(
            label="", style=discord.ButtonStyle.primary, emoji="⬇️",
        )

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.choice_num = choice_num
        self.page = page
        self.selected_url = selected_url
        self.selected_title = selected_title

    async def callback(self, interaction: Interaction):
        self.playlist, self.title = swap(self.playlist, self.title,
                                         self.choice_num, (self.choice_num + 1) % len(self.playlist))

        self.choice_num = (self.choice_num + 1) % len(self.playlist)
        self.page = self.choice_num // song_cnt

        custom_playlist.update_one({"user_id": self.user_id}, {"$set": {"playlist": self.playlist}})
        custom_playlist.update_one({"user_id": self.user_id}, {"$set": {"title": self.title}})

        await interaction.response.edit_message(
            embed=set_playlist_field(self.title, self.page, "description", self.selected_title),
            view=SongCustomPlaylistChangeOrderView(self.ctx, self.bot, self.players,
                                                   self.user_id, self.playlist, self.title, self.choice_num, self.page,
                                                   self.selected_url, self.selected_title))


class SongCustomPlaylistChangeOrderBackButton(discord.ui.Button):
    def __init__(self, ctx: ApplicationContext, bot: commands.Bot, players: dict,
                 user_id: int, playlist: list, title: list, choice_num: int, page: int,
                 selected_url: str, selected_title: str):
        super().__init__(
            label="Back", style=discord.ButtonStyle.green, emoji="🔙"
        )

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.choice_num = choice_num
        self.page = page
        self.selected_url = selected_url
        self.selected_title = selected_title

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(
            embed=makeEmbed(":notes: Playlist - selected :notes:",
                            f"[**{self.selected_title}**](<{self.selected_url}>)", Color.success),
            view=SongCustomPlaylistSelectedView(self.ctx, self.bot, self.players,
                                                self.user_id, self.playlist, self.title, self.choice_num, self.page))
