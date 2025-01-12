import discord
from discord import Interaction

import asyncio

from PIL import Image
import requests
import os

from modules.make_embed import makeEmbed, Color


class ConvertMainView(discord.ui.View):
    def __init__(self, file: discord.Attachment):
        super().__init__(timeout=None)

        self.file = file

    async def convert_webp(self, ext: str, interaction: Interaction):
        try:
            directory = f"./modules/images/"
            filename = self.file.filename

            with open(directory + filename, "wb") as handler:
                handler.write(requests.get(self.file.url).content)

            new = Image.open(directory + filename).convert("RGBA")

            os.remove(directory + filename)
            filename = filename.replace(".webp", f".{ext}")
            new.save(os.path.join(directory, filename))

            await interaction.response.edit_message(file=discord.File(directory + filename), embed=None, view=None)

            os.remove(directory + filename)
        except Exception as e:
            return await interaction.response.edit_message(embed=makeEmbed(":warning: Error :warning:", f"{e}", Color.error), view=None)

    @discord.ui.button(label="png", custom_id="png", style=discord.ButtonStyle.blurple)
    async def png_button_callback(self, button: discord.Button, interaction: Interaction):
        await self.convert_webp(button.custom_id, interaction)

    @discord.ui.button(label="jpeg", custom_id="jpeg", style=discord.ButtonStyle.green)
    async def jpeg_button_callback(self, button: discord.Button, interaction: Interaction):
        await self.convert_webp(button.custom_id, interaction)
