import os
import random

import discord
from discord import Option, OptionChoice, ApplicationContext
from discord.ext import commands
from dotenv import load_dotenv

from modules.convert_file import ConvertMainView, Convert
from modules.make_embed import makeEmbed, Color
from modules.messages import SongEmbed

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
        await ctx.respond(
            embed=makeEmbed(":ping_pong: Pong! :ping_pong:", f"{round(self.bot.latency * 1000)}ms", Color.success))

    # @file_commands.command(name="help", name_localizations={"ko": "도움"},
    #                        description="Show the list of commands",
    #                        description_localizations={"ko": "명령어 목록을 보여줍니다."})
    # async def help_(self, ctx: ApplicationContext):
    #     embed = makeEmbed()

    @file_commands.command(name="rock-paper-scissors", name_localizations={"ko": "가위바위보"},
                           description="Play rock-paper-scissors game",
                           description_localizations={"ko": "유저 또는 봇과 가위바위보 게임을 플레이합니다."})
    async def rps_(self, ctx: ApplicationContext,
                   choice: Option(str, name="choice", name_localizations={"ko": "선택"},
                                  description="Choose rock, paper, or scissors",
                                  description_localizations={"ko": "가위, 바위, 보 중 하나를 선택해 주세요."},
                                  choices=[
                                      OptionChoice(name="rock", value="rock"),
                                      OptionChoice(name="paper", value="paper"),
                                      OptionChoice(name="scissors", value="scissors")
                                  ]),
                   user: Option(discord.Member, name="user", name_localizations={"ko": "유저"},
                                description="Choose user to play",
                                description_localizations={"ko": "게임을 진행할 유저를 선택해 주세요."}) = None):
        emoji = {"rock": "👊", "paper": "✋", "scissors": "✌️"}

        def check_winner(choice1, choice2):
            if choice1 == choice2:
                return 0
            elif choice1 == "rock":
                if choice2 == "paper":
                    return 1
                else:
                    return 2
            elif choice1 == "paper":
                if choice2 == "scissors":
                    return 1
                else:
                    return 2
            elif choice1 == "scissors":
                if choice2 == "rock":
                    return 1
                else:
                    return 2

        class RPSView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)

                self.add_item(RPSSelect())

        class RPSSelect(discord.ui.Select):
            def __init__(self):
                super().__init__(
                    placeholder="Choose a hand",
                    options=[
                        discord.SelectOption(label="Rock", value="rock", emoji="👊"),
                        discord.SelectOption(label="Paper", value="paper", emoji="✋"),
                        discord.SelectOption(label="Scissors", value="scissors", emoji="✌️")
                    ]
                )

            async def callback(self, interaction: discord.Interaction):
                choice2 = self.values[0]

                await interaction.response.edit_message(embed=makeEmbed(":fist: :raised_hand: :v:",
                                                                        f"{ctx.user.mention}님이 가위바위보를 신청했습니다!\n\n나의 선택: {emoji.get(choice2)}",
                                                                        Color.success),
                                                        view=None)

                if not check_winner(choice, choice2):
                    result = makeEmbed(":no_entry: Draw :no_entry:",
                                       f"무승부!!\n\n{ctx.author.mention}: {emoji.get(choice)}\n{user.mention}: {emoji.get(choice2)}",
                                       Color.success)
                elif check_winner(choice, choice2) == 1:
                    result = makeEmbed(":white_check_mark: Win :white_check_mark:",
                                       f"{ctx.author.mention} 승리!!\n\n{ctx.author.mention}: {emoji.get(choice)}\n{user.mention}: {emoji.get(choice2)}",
                                       Color.success)
                else:
                    result = makeEmbed(":x: Lose :x:",
                                       f"{user.mention} 승리!!\n\n{ctx.author.mention}: {emoji.get(choice)}\n{user.mention}: {emoji.get(choice2)}",
                                       Color.success)

                await ctx.channel.send(f"{ctx.author.mention} {user.mention}", embed=result)

        if not user:
            choice_list = ["rock", "paper", "scissors"]
            bot_choice = random.choice(choice_list)

            if not check_winner(choice, bot_choice):
                return await ctx.respond(embed=makeEmbed(":no_entry: Draw :no_entry:",
                                                         f"무승부!!\n\n{ctx.author.mention}: {emoji.get(choice)}\n{ctx.bot.user.mention}: {emoji.get(bot_choice)}",
                                                         Color.success))
            elif check_winner(choice, bot_choice) == 1:
                return await ctx.respond(embed=makeEmbed(":white_check_mark: Win :white_check_mark:",
                                                         f"승리!!\n\n{ctx.author.mention}: {emoji.get(choice)}\n{ctx.bot.user.mention}: {emoji.get(bot_choice)}",
                                                         Color.success))
            else:
                return await ctx.respond(embed=makeEmbed(":x: Lose :x:",
                                                         f"패배!!\n\n{ctx.author.mention}: {emoji.get(choice)}\n{ctx.bot.user.mention}: {emoji.get(bot_choice)}",
                                                         Color.success))
        else:
            if user == ctx.author:
                return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "잘못된 선택입니다.", Color.error))

            embed = makeEmbed(":fist: :raised_hand: :v:", f"{user.mention}님의 답을 기다리고 있습니다...", Color.warning)
            await ctx.respond(embed=embed)

            embed = makeEmbed(":fist: :raised_hand: :v:", f"{ctx.user.mention}님이 가위바위보를 신청했습니다!", Color.success)
            dm = await user.create_dm()
            await dm.send(embed=embed, view=RPSView())


def setup(bot):
    bot.add_cog(Utils(bot))
