import os

import discord
from discord import Interaction

from modules.make_embed import makeEmbed, Color
from .convert_file import Convert


class ConvertMainView(discord.ui.View):
    def __init__(self, file: discord.Attachment):
        super().__init__(timeout=None)

        self.file = file

    async def callback(self, button: discord.Button, interaction: Interaction):
        try:
            path = await Convert(self.file, button.custom_id)

            await interaction.response.edit_message(file=discord.File(path), embed=None, view=None)

            os.remove(path)
        except Exception as e:
            await interaction.response.edit_message(embed=makeEmbed(":warning: Error :warning:", f"{e}", Color.error),
                                                    view=None)

    @discord.ui.button(label="png", custom_id="png", style=discord.ButtonStyle.blurple)
    async def png_button_callback(self, button: discord.Button, interaction: Interaction):
        await self.callback(button, interaction)

    @discord.ui.button(label="jpeg", custom_id="jpeg", style=discord.ButtonStyle.green)
    async def jpeg_button_callback(self, button: discord.Button, interaction: Interaction):
        await self.callback(button, interaction)
