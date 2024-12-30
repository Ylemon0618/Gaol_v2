import discord
from discord import Interaction

import asyncio

from modules.make_embed import makeEmbed, Color


class QueueMainView(discord.ui.View):
    def __init__(self, queue: asyncio.Queue, queue_listed: list, options: list[str]):
        super().__init__(timeout=None)

        self.queue = queue
        self.queue_listed = queue_listed

        self.add_item(QueueMainSelect(queue, queue_listed, options))


class QueueMainSelect(discord.ui.Select):
    def __init__(self, queue: asyncio.Queue, queue_listed: list, options: list[str],):
        super().__init__(
            placeholder="Choose a song",
            options=[discord.SelectOption(label=options[i], value=str(i)) for i in range(min(10, len(options)))]
        )

        self.queue = queue
        self.queue_listed = queue_listed

    async def callback(self, interaction: Interaction):
        choice_num = int(self.values[0])
        choice = self.options[choice_num]

        embed = makeEmbed(":musical_note: Queue - selected :musical_note:", f"**{choice}**", Color.success)
        await interaction.response.edit_message(embed=embed, view=QueueSelectedView(self.queue, self.queue_listed, choice_num))


class QueueSelectedView(discord.ui.View):
    def __init__(self, queue: asyncio.Queue, queue_listed: list, selected: int):
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

            embed = makeEmbed(":musical_note: Queue - deleted :musical_note:",
                              f"**{self.title}**을(를) 성공적으로 대기열에서 삭제했습니다.", Color.success)
        except Exception as e:
            embed = makeEmbed(":warning: Error :warning:", f"{e}", Color.error)

        await interaction.response.edit_message(embed=embed, view=QueueBackToMainView(self.queue, self.queue_listed))

class QueueBackToMainView(discord.ui.View):
    def __init__(self, queue: asyncio.Queue, queue_listed: list):
        super().__init__(timeout=None)

        self.queue = queue
        self.queue_listed = queue_listed

    @discord.ui.button(
        label="대기열로 돌아가기",
        custom_id="Queue back_to_main",
        style=discord.ButtonStyle.blurple
    )
    async def queue_back_to_main_button_callback(self, button: discord.ui.Button, interaction: Interaction):
        title = []

        embed = makeEmbed(":musical_note: Queue :musical_note:", "", Color.success)
        for i in range(min(10, len(self.queue_listed))):
            embed.add_field(name=self.queue_listed[i].title, value="", inline=False)
            title.append(self.queue_listed[i].title)

        await interaction.response.edit_message(embed=embed, view=QueueMainView(self.queue, self.queue_listed, title))
