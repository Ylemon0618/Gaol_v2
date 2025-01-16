import discord
from discord import Option, OptionChoice, ApplicationContext
from discord.ext import commands

from modules.chord_finder import get_chord

import os
from dotenv import load_dotenv

load_dotenv()

guild_ids = list(map(int, os.environ.get('GUILDS').split()))


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    music_commands = discord.SlashCommandGroup(name="music", name_localizations={"ko": "음악"},
                                              description="Commands for music\n\nThese commands do not play songs.\nTo play music, please use /Song instead.",
                                              description_localizations={"ko": "음악과 관련된 명령어\n\n이 명령어는 노래를 재생하는 명령어가 아닙니다.\n음악 재생은 /노래 를 이용해 주세요."},
                                              guild_ids=guild_ids)

    @music_commands.command(name="chord", name_localizations={"ko": "코드"},
                            description="Search a chord of piano or guitar",
                            description_localizations={"ko": "피아노나 기타의 코드를 검색합니다."})
    async def chord_(self, ctx: ApplicationContext,
                       chord: Option(str, name="chord", name_localizations={"ko": "코드"},
                                     description="Enter the name of chord you are searching",
                                     description_localizations={"ko": "검색 할 코드의 이름을 입력 해 주세요."}),
                       inst: Option(str, name="instrument", name_localizations={"ko": "악기"},
                                    description="Choose a instrument",
                                    description_localizations={"ko": "악기를 선택 해 주세요."},
                                    choices=[
                                        OptionChoice(name="piano", name_localizations={"ko": "피아노"},
                                                     value="piano"),
                                        OptionChoice(name="guitar", name_localizations={"ko": "기타"},
                                                     value="guitar")
                                    ]) = "piano"):
        name, notes = get_chord(chord)

        await ctx.respond(f"{name}, {notes}")


def setup(bot):
    bot.add_cog(Music(bot))
