import discord
from discord import Interaction

import asyncio

from PIL import Image
import requests
import os

from modules.make_embed import makeEmbed, Color


async def convert(file: discord.Attachment, ext: str):
    directory = f"./modules/images/"
    filename = file.filename

    with open(directory + filename, "wb") as handler:
        handler.write(requests.get(file.url).content)

    new = Image.open(directory + filename).convert("RGBA")

    os.remove(directory + filename)
    filename = filename.replace(".webp", f".{ext}")
    new.save(os.path.join(directory, filename))

    return directory + filename

class ConvertMainView(discord.ui.View):
    def __init__(self, file: discord.Attachment):
        super().__init__(timeout=None)

        self.file = file

    async def callback(self, button: discord.Button, interaction: Interaction):
        try:
            path = await convert(self.file, button.custom_id)

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
