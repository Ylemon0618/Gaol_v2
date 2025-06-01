import datetime

import discord


class Color:
    success = 0x00C6FF
    error = 0xD5C7FF
    warning = 0xFFD9FF


# 필드(임베드) 클래스
class Field:
    def __init__(self, name: str, value: str, inline: bool = False):
        self.name = name
        self.value = value
        self.inline = inline


def makeEmbed(title: str, description: str, color: int, *fields: list[Field]):
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.now())

    if fields:
        for field in fields:
            embed.add_field(name=field.name, value=field.value, inline=field.inline)

    return embed


def makeView(container: discord.ui.Container):
    view = discord.ui.View(timeout=None)
    view.add_item(container)

    return view
