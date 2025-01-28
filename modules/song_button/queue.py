import asyncio

import discord
from discord import Interaction

from modules.make_embed import makeEmbed, Color
from modules.song_player import YTDLSource

song_cnt = 10  # The max number of songs in one page


class Title:
    normal = ":musical_note: Queue :musical_note:"
    selected = ":musical_note: Queue - selected :musical_note:"
    deleted = ":musical_note: Queue - deleted :musical_note:"
    back_to_main = ":musical_note: Queue - back to main :musical_note:"

    error = ":warning: Error :warning:"


class QueueMainView(discord.ui.View):
    def __init__(self, queue: asyncio.Queue, queue_listed: list[YTDLSource], page: int):
        super().__init__(timeout=None)

        self.queue = queue
        self.queue_listed = queue_listed
        self.page = page

        self.add_item(QueueMainSelect(queue, queue_listed, page))

        min_page = 0
        max_page = (len(queue_listed) - 1) // song_cnt

        if page == min_page:
            self.add_item(QueueMainPagePrevButton(queue, queue_listed, page, True))
        else:
            self.add_item(QueueMainPagePrevButton(queue, queue_listed, page))

        if page == max_page:
            self.add_item(QueueMainPageNextButton(queue, queue_listed, page, True))
        else:
            self.add_item(QueueMainPageNextButton(queue, queue_listed, page))


class QueueMainSelect(discord.ui.Select):
    def __init__(self, queue: asyncio.Queue, queue_listed: list[YTDLSource], page: int):
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
        self.page = page
        self.options = options

    async def callback(self, interaction: Interaction):
        choice_num = int(self.values[0])
        choice = self.options[choice_num]

        embed = makeEmbed(Title.selected, f"**{choice}**", Color.success)
        await interaction.response.edit_message(embed=embed,
                                                view=QueueSelectedView(self.queue, self.queue_listed,
                                                                       self.page * song_cnt + choice_num))


def set_queue_field(embed: discord.Embed, queue_listed: list[YTDLSource], page: int):
    for idx in range(page * song_cnt, page * song_cnt + song_cnt):
        if idx >= len(queue_listed):
            break

        embed.add_field(name=queue_listed[idx].title, value="", inline=False)

    return embed


class QueueMainPageNextButton(discord.ui.Button):
    def __init__(self, queue: asyncio.Queue, queue_listed: list[YTDLSource], page: int, disabled=False):
        super().__init__(
            label="Next",
            emoji="➡️",
            custom_id="Queue page_next",
            style=discord.ButtonStyle.blurple,
            disabled=disabled
        )

        self.queue = queue
        self.queue_listed = queue_listed
        self.page = page

    async def callback(self, interaction: Interaction):
        self.page += 1

        embed = set_queue_field(makeEmbed(Title.normal, "", Color.success),
                                self.queue_listed, self.page)

        await interaction.response.edit_message(embed=embed,
                                                view=QueueMainView(self.queue, self.queue_listed, self.page))


class QueueMainPagePrevButton(discord.ui.Button):
    def __init__(self, queue: asyncio.Queue, queue_listed: list[YTDLSource], page: int, disabled=False):
        super().__init__(
            label="Prev",
            emoji="⬅️",
            custom_id="Queue page_prev",
            style=discord.ButtonStyle.blurple,
            disabled=disabled
        )

        self.queue = queue
        self.queue_listed = queue_listed
        self.page = page

    async def callback(self, interaction: Interaction):
        self.page -= 1

        embed = set_queue_field(makeEmbed(Title.normal, "", Color.success),
                                self.queue_listed, self.page)

        await interaction.response.edit_message(embed=embed,
                                                view=QueueMainView(self.queue, self.queue_listed, self.page))


class QueueSelectedView(discord.ui.View):
    def __init__(self, queue: asyncio.Queue, queue_listed: list[YTDLSource], selected: int):
        super().__init__(timeout=None)

        self.queue = queue
        self.queue_listed = queue_listed
        self.selected = selected
        self.title = self.queue_listed[selected].title

    @discord.ui.button(
        label="삭제",
        custom_id="Queue delete",
        style=discord.ButtonStyle.red
    )
    async def queue_delete_button_callback(self, button: discord.ui.Button, interaction: Interaction):
        try:
            self.queue_listed.pop(self.selected)

            for i in range(len(self.queue_listed)):
                await self.queue.get()
                await self.queue.put(self.queue_listed[i])
            await self.queue.get()

            embed = makeEmbed(Title.deleted,
                              f"**{self.title}**을(를) 성공적으로 대기열에서 삭제했습니다.", Color.success)
        except Exception as e:
            embed = makeEmbed(Title.error, f"{e}", Color.error)

        await interaction.response.edit_message(embed=embed, view=QueueBackToMainView(self.queue, self.queue_listed))


class QueueBackToMainView(discord.ui.View):
    def __init__(self, queue: asyncio.Queue, queue_listed: list[YTDLSource]):
        super().__init__(timeout=None)

        self.queue = queue
        self.queue_listed = queue_listed

    @discord.ui.button(
        label="대기열로 돌아가기",
        custom_id="Queue back_to_main",
        style=discord.ButtonStyle.blurple
    )
    async def queue_back_to_main_button_callback(self, button: discord.ui.Button, interaction: Interaction):
        embed = set_queue_field(makeEmbed(Title.back_to_main, "", Color.success),
                                self.queue_listed, 0)

        await interaction.response.edit_message(embed=embed, view=QueueMainView(self.queue, self.queue_listed, 0))
