import datetime

import discord


class Color:
    # 성공(초록색)
    success = 0x00FF00

    # 실패(빨간색)
    error = 0xFF0000

    # 경고(노란색)
    # 확인 창에 사용
    warning = 0xFFFF00


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
