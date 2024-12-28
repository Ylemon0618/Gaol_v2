import discord
from discord import Option, ApplicationContext, Interaction
from discord.ext import commands

import asyncio

import datetime

from modules.make_embed import makeEmbed, Field, Color


class QueueMainSelect(discord.ui.Select):
    def __init__(self, options: list[str]):
        super().__init__(
            placeholder="Choose a song",
            options=[discord.SelectOption(label=options[i]) for i in range(min(10, len(options)))]
        )

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()

        choice = self.values[0]

        embed = makeEmbed(":musical_note: Queue - selected :musical_note:", f"**{choice}**", Color.success)
        await interaction.message.edit(embed=embed)


class QueueMainView(discord.ui.View):
    def __init__(self, options: list[str]):
        super().__init__(timeout=None)

        self.add_item(QueueMainSelect(options))
