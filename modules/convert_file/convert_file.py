import os

import discord
import requests
from PIL import Image


async def Convert(file: discord.Attachment, ext: str):
    directory = "./images/"
    filename = file.filename

    with open(directory + filename, "wb") as handler:
        handler.write(requests.get(file.url).content)

    new = Image.open(directory + filename).convert("RGBA" if ext == "png" else "RGB")

    os.remove(directory + filename)
    filename = '.'.join(filename.split('.')[:-1]) + f".{ext}"
    new.save(os.path.join(directory, filename))

    return directory + filename
