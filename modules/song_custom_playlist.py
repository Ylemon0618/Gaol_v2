import os
from math import ceil
from urllib import request, parse
from yt_dlp import YoutubeDL

import discord
from discord import Interaction
from dotenv import load_dotenv

from pymongo.mongo_client import MongoClient

from modules.make_embed import makeEmbed, Color

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
    playlist[idx1], playlist[idx2] = playlist[idx2], playlist[idx1]
    title[idx1], title[idx2] = title[idx2], title[idx1]

    return playlist, title


class SongCustomPlaylistView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)

        self.user_id = user_id

        self.add_item(SongCustomPlaylistSelect(user_id))


class SongCustomPlaylistSelect(discord.ui.Select):
    def __init__(self, user_id: int):
        super().__init__(
            placeholder="Choose a task",
            options=[
                discord.SelectOption(label="Add song | 노래 추가", value="add", emoji="➕",
                                     description="Add a song to the playlist | 플레이리스트에 노래를 추가합니다."),
                discord.SelectOption(label="Show playlist | 플레이리스트 조회", value="show", emoji="📜",
                                     description="Show and manage the playlist | 플레이리스트를 조회 및 관리합니다.")
            ]
        )

        self.user_id = user_id
        try:
            self.playlist = custom_playlist.find_one({"user_id": user_id})["playlist"]
            self.title = custom_playlist.find_one({"user_id": user_id})["title"]
        except TypeError:
            custom_playlist.insert_one({"user_id": user_id, "playlist": [], "title": []})
            self.playlist = []
            self.title = []

    async def callback(self, interaction: Interaction):
        task = self.values[0]

        if task == "add":
            await interaction.response.send_modal(modal=SongCustomPlaylistAddModal(self.user_id, self.playlist))
        elif task == "show":
            await interaction.response.edit_message(embed=set_playlist_field(self.title, 0),
                                                    view=SongCustomPlaylistShowView(self.user_id, self.playlist,
                                                                                    self.title))


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

        insert_song(self.user_id, url, data['title'])

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
    def __init__(self, user_id: int, playlist: list, title: list, page: int = 0):
        super().__init__(timeout=None)

        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.page = page

        self.add_item(SongCustomPlaylistShowSelect(user_id, playlist, title, page))

        min_page = 0
        max_page = (len(title) - 1) // song_cnt

        if page == min_page:
            self.add_item(SongCustomPlaylistShowPrevButton(user_id, playlist, title, page, True))
        else:
            self.add_item(SongCustomPlaylistShowPrevButton(user_id, playlist, title, page))

        if page == max_page:
            self.add_item(SongCustomPlaylistShowNextButton(user_id, playlist, title, page, True))
        else:
            self.add_item(SongCustomPlaylistShowNextButton(user_id, playlist, title, page))

        self.add_item(SongCustomPlaylistShowBackButton(user_id))


class SongCustomPlaylistShowSelect(discord.ui.Select):
    def __init__(self, user_id: int, playlist: list, title: list, page: int):
        options = []
        for idx in range(page * song_cnt, page * song_cnt + song_cnt):
            if idx >= len(title):
                break

            options.append(discord.SelectOption(label=title[idx], value=f"{idx}"))

        super().__init__(
            placeholder="Choose a song",
            options=options
        )

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
            view=SongCustomPlaylistSelectedView(self.user_id, self.playlist,
                                                self.title, choice_num, self.page))


class SongCustomPlaylistShowPrevButton(discord.ui.Button):
    def __init__(self, user_id: int, playlist: list, title: list, page: int, disabled: bool = False):
        super().__init__(style=discord.ButtonStyle.primary, label="Prev", emoji="⬅️", disabled=disabled)

        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.page = page

    async def callback(self, interaction: Interaction):
        self.page -= 1
        await interaction.response.edit_message(
            embed=set_playlist_field(self.title, self.page),
            view=SongCustomPlaylistShowView(self.user_id, self.playlist, self.title, self.page))


class SongCustomPlaylistShowNextButton(discord.ui.Button):
    def __init__(self, user_id: int, playlist: list, title: list, page: int, disabled: bool = False):
        super().__init__(style=discord.ButtonStyle.primary, label="Next", emoji="➡️", disabled=disabled)

        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.page = page

    async def callback(self, interaction: Interaction):
        self.page += 1
        await interaction.response.edit_message(
            embed=set_playlist_field(self.title, self.page),
            view=SongCustomPlaylistShowView(self.user_id, self.playlist, self.title, self.page))


class SongCustomPlaylistShowBackButton(discord.ui.Button):
    def __init__(self, user_id: int):
        super().__init__(
            label="Back", style=discord.ButtonStyle.green, emoji="🔙"
        )

        self.user_id = user_id

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(embed=makeEmbed(":cd: Playlist | 플레이리스트 :cd:",
                                                                "Manage custom playlist.\n커스텀 플레이리스트를 관리합니다.",
                                                                Color.success),
                                                view=SongCustomPlaylistView(self.user_id))


class SongCustomPlaylistSelectedView(discord.ui.View):
    def __init__(self, user_id: int, playlist: list, title: list, choice_num: int, page: int):
        super().__init__(timeout=None)

        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.choice_num = choice_num
        self.page = page
        self.selected_url = playlist[choice_num]
        self.selected_title = title[choice_num]

        self.add_item(SongCustomPlaylistSelectedSelect(user_id, playlist, title, choice_num, page, self.selected_url,
                                                       self.selected_title))
        self.add_item(SongCustomPlaylistSelectedBackButton(user_id, playlist, title))


class SongCustomPlaylistSelectedSelect(discord.ui.Select):
    def __init__(self, user_id: int, playlist: list, title: list, choice_num: int, page: int, selected_url: str,
                 selected_title: str):
        super().__init__(
            placeholder="Choose a task",
            options=[
                discord.SelectOption(label="Delete song | 노래 삭제", value="delete", emoji="❌",
                                     description="Delete the selected song | 선택한 노래를 삭제합니다."),
                discord.SelectOption(label="Change order | 순서 변경", value="change", emoji="🔄",
                                     description="Change the order of the selected song | 선택한 노래의 순서를 변경합니다.")
            ]
        )

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
                view=SongCustomPlaylistDeletedView(self.user_id, self.playlist, self.title, self.choice_num,
                                                   self.selected_url, self.selected_title))
        elif task == "change":
            await interaction.response.edit_message(
                embed=set_playlist_field(self.title, self.page, "description", self.selected_title),
                view=SongCustomPlaylistChangeOrderView(self.user_id, self.playlist, self.title, self.choice_num,
                                                       self.page, self.selected_url, self.selected_title))


class SongCustomPlaylistSelectedBackButton(discord.ui.Button):
    def __init__(self, user_id: int, playlist: list, title: list):
        super().__init__(
            label="Back", style=discord.ButtonStyle.green, emoji="🔙"
        )

        self.user_id = user_id
        self.playlist = playlist
        self.title = title

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(
            embed=set_playlist_field(self.title, 0),
            view=SongCustomPlaylistShowView(self.user_id, self.playlist, self.title, 0))


class SongCustomPlaylistDeletedView(discord.ui.View):
    def __init__(self, user_id: int, playlist: list, title: list, choice_num: int, selected_url: str,
                 selected_title: str):
        super().__init__(timeout=None)

        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.choice_num = choice_num
        self.selected_url = selected_url
        self.selected_title = selected_title

        self.add_item(
            SongCustomPlaylistDeletedCancelButton(user_id, playlist, title, choice_num, selected_url, selected_title))
        self.add_item(SongCustomPlaylistDeletedBackButton(user_id, playlist, title))


class SongCustomPlaylistDeletedCancelButton(discord.ui.Button):
    def __init__(self, user_id: int, playlist: list, title: list, choice_num: int, selected_url: str,
                 selected_title: str):
        super().__init__(
            label="Cancel", style=discord.ButtonStyle.red, emoji="✖"
        )

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
            view=SongCustomPlaylistShowView(self.user_id, self.playlist, self.title))


class SongCustomPlaylistDeletedBackButton(discord.ui.Button):
    def __init__(self, user_id: int, playlist: list, title: list):
        super().__init__(
            label="Back", style=discord.ButtonStyle.green, emoji="🔙"
        )

        self.user_id = user_id
        self.playlist = playlist
        self.title = title

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(
            embed=set_playlist_field(self.title, 0),
            view=SongCustomPlaylistShowView(self.user_id, self.playlist, self.title))


class SongCustomPlaylistChangeOrderView(discord.ui.View):
    def __init__(self, user_id: int, playlist: list, title: list, choice_num: int, page: int, selected_url: str,
                 selected_title: str):
        super().__init__(timeout=None)

        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.choice_num = choice_num
        self.page = page
        self.selected_url = selected_url
        self.selected_title = selected_title

        self.add_item(SongCustomPlaylistChangeOrderUpButton(user_id, playlist, title, choice_num, page, selected_url,
                                                            selected_title))
        self.add_item(SongCustomPlaylistChangeOrderDownButton(user_id, playlist, title, choice_num, page, selected_url,
                                                              selected_title))
        self.add_item(SongCustomPlaylistChangeOrderBackButton(user_id, playlist, title, choice_num, page, selected_url,
                                                              selected_title))


class SongCustomPlaylistChangeOrderUpButton(discord.ui.Button):
    def __init__(self, user_id: int, playlist: list, title: list, choice_num: int, page: int, selected_url: str,
                 selected_title: str):
        super().__init__(
            label="", style=discord.ButtonStyle.primary, emoji="⬆️",
        )

        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.choice_num = choice_num
        self.page = page
        self.selected_url = selected_url
        self.selected_title = selected_title

    async def callback(self, interaction: Interaction):
        self.playlist, self.title = swap(self.playlist, self.title, self.choice_num,
                                         (self.choice_num - 1) % len(self.playlist))

        self.choice_num = (self.choice_num - 1) % len(self.playlist)
        self.page = self.choice_num // song_cnt

        custom_playlist.update_one({"user_id": self.user_id}, {"$set": {"playlist": self.playlist}})
        custom_playlist.update_one({"user_id": self.user_id}, {"$set": {"title": self.title}})

        await interaction.response.edit_message(
            embed=set_playlist_field(self.title, self.page, "description", self.selected_title),
            view=SongCustomPlaylistChangeOrderView(self.user_id, self.playlist, self.title, self.choice_num, self.page,
                                                   self.selected_url, self.selected_title))


class SongCustomPlaylistChangeOrderDownButton(discord.ui.Button):
    def __init__(self, user_id: int, playlist: list, title: list, choice_num: int, page: int, selected_url: str,
                 selected_title: str):
        super().__init__(
            label="", style=discord.ButtonStyle.primary, emoji="⬇️",
        )

        self.user_id = user_id
        self.playlist = playlist
        self.title = title
        self.choice_num = choice_num
        self.page = page
        self.selected_url = selected_url
        self.selected_title = selected_title

    async def callback(self, interaction: Interaction):
        self.playlist, self.title = swap(self.playlist, self.title, self.choice_num,
                                         (self.choice_num + 1) % len(self.playlist))

        self.choice_num = (self.choice_num + 1) % len(self.playlist)
        self.page = self.choice_num // song_cnt

        custom_playlist.update_one({"user_id": self.user_id}, {"$set": {"playlist": self.playlist}})
        custom_playlist.update_one({"user_id": self.user_id}, {"$set": {"title": self.title}})

        await interaction.response.edit_message(
            embed=set_playlist_field(self.title, self.page, "description", self.selected_title),
            view=SongCustomPlaylistChangeOrderView(self.user_id, self.playlist, self.title, self.choice_num, self.page,
                                                   self.selected_url, self.selected_title))


class SongCustomPlaylistChangeOrderBackButton(discord.ui.Button):
    def __init__(self, user_id: int, playlist: list, title: list, choice_num: int, page: int, selected_url: str,
                 selected_title: str):
        super().__init__(
            label="Back", style=discord.ButtonStyle.green, emoji="🔙"
        )

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
            view=SongCustomPlaylistSelectedView(self.user_id, self.playlist,
                                                self.title, self.choice_num, self.page))
