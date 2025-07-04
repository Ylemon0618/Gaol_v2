import os

import asyncio
import discord
from discord import Interaction
from dotenv import load_dotenv

from modules.make_embed import makeEmbed, Color

load_dotenv()

song_cnt = int(os.environ.get('PAGE_SIZE'))


class Title:
    normal = ":musical_note: Queue :musical_note:"
    selected = ":musical_note: Queue - selected :musical_note:"
    deleted = ":musical_note: Queue - deleted :musical_note:"
    back_to_main = ":musical_note: Queue - back to main :musical_note:"

    error = ":warning: Error :warning:"


class QueueMainView(discord.ui.View):
    def __init__(self, queue: asyncio.Queue, queue_listed: list, current, page: int):
        super().__init__(timeout=None)

        self.queue = queue
        self.queue_listed = queue_listed
        self.current = current
        self.page = page

        self.add_item(QueueMainSelect(queue, queue_listed, current, page))

        min_page = 0
        max_page = (len(queue_listed) - 1) // song_cnt

        if page == min_page:
            self.add_item(QueueMainPagePrevButton(queue, queue_listed, current, page, True))
        else:
            self.add_item(QueueMainPagePrevButton(queue, queue_listed, current, page))

        if page == max_page:
            self.add_item(QueueMainPageNextButton(queue, queue_listed, current, page, True))
        else:
            self.add_item(QueueMainPageNextButton(queue, queue_listed, current, page))


class QueueMainSelect(discord.ui.Select):
    def __init__(self, queue: asyncio.Queue, queue_listed: list, current, page: int):
        options = []
        for idx in range(page * song_cnt, page * song_cnt + song_cnt):
            if idx >= len(queue_listed):
                break

            options.append(discord.SelectOption(label=queue_listed[idx].title, value=f"{idx}"))

        super().__init__(
            placeholder="Choose a song",
            options=options
        )

        self.queue = queue
        self.queue_listed = queue_listed
        self.current = current
        self.page = page

    async def callback(self, interaction: Interaction):
        choice_num = int(self.values[0])
        choice = self.queue_listed[choice_num]

        embed = makeEmbed(Title.selected, f"**{choice.title}**", Color.success)
        await interaction.response.edit_message(embed=embed,
                                                view=QueueSelectedView(self.queue, self.queue_listed, self.current,
                                                                       self.page * song_cnt + choice_num))


def set_queue_field(embed: discord.Embed, queue_listed: list, page: int):
    for idx in range(page * song_cnt, page * song_cnt + song_cnt):
        if idx >= len(queue_listed):
            break

        embed.add_field(name=queue_listed[idx].title, value="", inline=False)

    return embed


class QueueMainPageNextButton(discord.ui.Button):
    def __init__(self, queue: asyncio.Queue, queue_listed: list, current, page: int, disabled=False):
        super().__init__(
            label="Next",
            emoji="➡️",
            custom_id="Queue page_next",
            style=discord.ButtonStyle.blurple,
            disabled=disabled
        )

        self.queue = queue
        self.queue_listed = queue_listed
        self.current = current
        self.page = page

    async def callback(self, interaction: Interaction):
        self.page += 1

        embed = set_queue_field(makeEmbed(Title.normal, f"**Now Playing**\n> {self.current.title}", Color.success),
                                self.queue_listed, self.page)

        await interaction.response.edit_message(embed=embed,
                                                view=QueueMainView(self.queue, self.queue_listed, self.current, self.page))


class QueueMainPagePrevButton(discord.ui.Button):
    def __init__(self, queue: asyncio.Queue, queue_listed: list, current, page: int, disabled=False):
        super().__init__(
            label="Prev",
            emoji="⬅️",
            custom_id="Queue page_prev",
            style=discord.ButtonStyle.blurple,
            disabled=disabled
        )

        self.queue = queue
        self.queue_listed = queue_listed
        self.current = current
        self.page = page

    async def callback(self, interaction: Interaction):
        self.page -= 1

        embed = set_queue_field(makeEmbed(Title.normal, f"**Now Playing**\n> {self.current.title}", Color.success),
                                self.queue_listed, self.page)

        await interaction.response.edit_message(embed=embed,
                                                view=QueueMainView(self.queue, self.queue_listed, self.current, self.page))


class QueueSelectedView(discord.ui.View):
    def __init__(self, queue: asyncio.Queue, queue_listed: list, current, selected: int):
        super().__init__(timeout=None)

        self.queue = queue
        self.queue_listed = queue_listed
        self.current = current
        self.selected = selected
        self.title = self.queue_listed[selected].title

    @discord.ui.button(
        label="삭제",
        custom_id="Queue delete",
        style=discord.ButtonStyle.red
    )
    async def queue_delete_button_callback(self, button: discord.ui.Button, interaction: Interaction):
        try:
            selected_source = self.queue_listed.pop(self.selected)

            for i in range(len(self.queue_listed)):
                source = await self.queue.get()

                if source == selected_source:
                    continue
                await self.queue.put(source)
            await self.queue.get()

            embed = makeEmbed(Title.deleted,
                              f"**{self.title}**을(를) 성공적으로 대기열에서 삭제했습니다.", Color.success)
        except Exception as e:
            embed = makeEmbed(Title.error, f"{e}", Color.error)

        await interaction.response.edit_message(embed=embed,
                                                view=QueueBackToMainView(self.queue, self.queue_listed, self.current))

    @discord.ui.button(
        label="취소",
        custom_id="Queue cancel",
        style=discord.ButtonStyle.gray
    )
    async def queue_cancel_button_callback(self, button: discord.ui.Button, interaction: Interaction):
        embed = set_queue_field(makeEmbed(Title.back_to_main, "", Color.success),
                                self.queue_listed, 0)

        await interaction.response.edit_message(embed=embed,
                                                view=QueueMainView(self.queue, self.queue_listed, self.current, 0))


class QueueBackToMainView(discord.ui.View):
    def __init__(self, queue: asyncio.Queue, queue_listed: list, current):
        super().__init__(timeout=None)

        self.queue = queue
        self.queue_listed = queue_listed
        self.current = current

    @discord.ui.button(
        label="대기열로 돌아가기",
        custom_id="Queue back_to_main",
        style=discord.ButtonStyle.blurple
    )
    async def queue_back_to_main_button_callback(self, button: discord.ui.Button, interaction: Interaction):
        embed = set_queue_field(makeEmbed(Title.back_to_main, "", Color.success),
                                self.queue_listed, 0)

        await interaction.response.edit_message(embed=embed,
                                                view=QueueMainView(self.queue, self.queue_listed, self.current, 0))
