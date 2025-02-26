import os

import discord
from discord import Option, OptionChoice, ApplicationContext
from discord.ext import commands
from dotenv import load_dotenv

from modules.make_embed import makeEmbed, Color

load_dotenv()

guild_ids = list(map(int, os.environ.get('GUILDS').split()))


class Utils(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    file_commands = discord.SlashCommandGroup(name="utils", name_localizations={"ko": "유틸리티"},
                                              description="Commands of utility",
                                              description_localizations={"ko": "각종 기능들을 사용할 수 있는 명령어"},
                                              guild_ids=guild_ids)

    @file_commands.command(name="ping", name_localizations={"ko": "핑"},
                           description="Check the bot's response time",
                           description_localizations={"ko": "봇의 응답 시간을 확인합니다."})
    async def ping_(self, ctx: ApplicationContext):
        await ctx.respond(embed=makeEmbed(":ping_pong: Pong! :ping_pong:",
                                          f"{round(self.bot.latency * 1000)}ms", Color.success))

    # @file_commands.command(name="help", name_localizations={"ko": "도움"},
    #                        description="Show the list of commands",
    #                        description_localizations={"ko": "명령어 목록을 보여줍니다."})
    # async def help_(self, ctx: ApplicationContext):
    #     embed = makeEmbed()


def setup(bot):
    bot.add_cog(Utils(bot))
