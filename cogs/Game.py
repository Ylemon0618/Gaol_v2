from discord import Option, OptionChoice
from discord.ext import commands

from modules.game_ui import *
from modules.connect_db.balance import *
from modules.connect_db.attendance import *

load_dotenv()

guild_ids = list(map(int, os.environ.get('GUILDS').split()))


class Game(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    game_commands = discord.SlashCommandGroup(name="game", name_localizations={"ko": "게임"},
                                              description="Commands for playing games",
                                              description_localizations={"ko": "게임을 플레이 할 수 있는 명령어"},
                                              guild_ids=guild_ids)

    @game_commands.command(name="rock-paper-scissors", name_localizations={"ko": "가위바위보"},
                           description="Play rock-paper-scissors game",
                           description_localizations={"ko": "유저 또는 봇과 가위바위보 게임을 플레이합니다."})
    async def rps_(self, ctx: ApplicationContext,
                   choice: Option(str, name="choice", name_localizations={"ko": "선택"},
                                  description="Choose rock, paper, or scissors",
                                  description_localizations={"ko": "가위, 바위, 보 중 하나를 선택해 주세요."},
                                  choices=[
                                      OptionChoice(name="Rock", value="rock",
                                                   name_localizations={"ko": "바위"}),
                                      OptionChoice(name="Paper", value="paper",
                                                   name_localizations={"ko": "보"}),
                                      OptionChoice(name="Scissors", value="scissors",
                                                   name_localizations={"ko": "가위"})
                                  ]),
                   user: Option(discord.Member, name="user", name_localizations={"ko": "유저"},
                                description="Choose user to play",
                                description_localizations={"ko": "게임을 진행할 유저를 선택해 주세요."}) = None):
        emoji = {"rock": "👊", "paper": "✋", "scissors": "✌️"}

        if not user:
            choice_list = ["rock", "paper", "scissors"]
            bot_choice = random.choice(choice_list)

            if not check_winner(choice, bot_choice):
                return await ctx.respond(embed=makeEmbed(":fist: :raised_hand: :v:",
                                                         f"무승부!!\n\n{ctx.author.mention}: {emoji.get(choice)}\n{ctx.bot.user.mention}: {emoji.get(bot_choice)}",
                                                         Color.success))
            elif check_winner(choice, bot_choice) == 1:
                return await ctx.respond(embed=makeEmbed(":fist: :raised_hand: :v:",
                                                         f"승리!!\n\n{ctx.author.mention}: {emoji.get(choice)}\n{ctx.bot.user.mention}: {emoji.get(bot_choice)}",
                                                         Color.success))
            else:
                return await ctx.respond(embed=makeEmbed(":fist: :raised_hand: :v:",
                                                         f"패배!!\n\n{ctx.author.mention}: {emoji.get(choice)}\n{ctx.bot.user.mention}: {emoji.get(bot_choice)}",
                                                         Color.success))
        else:
            if user == ctx.author:
                return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "잘못된 선택입니다.", Color.error),
                                         ephemeral=True)

            embed = makeEmbed(":fist: :raised_hand: :v:", f"{user.mention}님의 답을 기다리고 있습니다...", Color.warning)
            await ctx.respond(embed=embed)

            embed = makeEmbed(":fist: :raised_hand: :v:", f"{ctx.user.mention}님이 가위바위보를 신청했습니다!", Color.success)
            dm = await user.create_dm()
            await dm.send(embed=embed, view=RPSView())

    @game_commands.command(name="gamble", name_localizations={"ko": "도박"},
                           description="Play a gambling game",
                           description_localizations={"ko": "도박 게임을 플레이합니다."})
    async def gamble_(self, ctx: ApplicationContext,
                      option: Option(str, name="game", name_localizations={"ko": "게임"},
                                     description="Choose a game to play",
                                     description_localizations={"ko": "플레이 할 게임을 선택 해 주세요."},
                                     choices=[
                                         OptionChoice(name="Coin toss", value="coin",
                                                      name_localizations={"ko": "동전 던지기"}),
                                         OptionChoice(name="Blackjack", value="blackjack",
                                                      name_localizations={"ko": "블랙잭"}),
                                         OptionChoice(name="Slot machine", value="slot",
                                                      name_localizations={"ko": "슬롯 머신"}),
                                     ])):
        if option == "coin":
            await coin_toss(ctx)

    @game_commands.command(name="balance", name_localizations={"ko": "잔고"},
                           description="Check your balance",
                           description_localizations={"ko": "잔고를 확인합니다."})
    async def balance_(self, ctx: ApplicationContext):
        balance = get_user_balance(ctx.author.id)

        embed = makeEmbed(":moneybag: Balance | 잔고 :moneybag:", f"**{balance}$**", Color.success)
        await ctx.respond(embed=embed)

    @game_commands.command(name="attendance", name_localizations={"ko": "출석"},
                           description="Get reward through attendance check",
                           description_localizations={"ko": "출석 체크를 통해 보상을 받습니다."})
    async def attendance_(self, ctx: ApplicationContext):
        user = update_attendance(ctx.author.id)

        if "error" in user:
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", user["error"], Color.error),
                                     ephemeral=True)

        embed = makeEmbed(":calendar: Attendance | 출석 :calendar:",
                          f"**{ctx.author.mention}**님, 출석 체크를 완료했습니다!\n\n현재 출석 일수: **{user["streak"]}일**",
                          Color.success)

        streak = user["streak"]
        if streak % 7 == 0:
            update_user_balance(ctx.author.id, 10000)
            embed.description += f"\n\n**출석 보상:** 10000$ (7일 연속 출석)"

        await ctx.respond(embed=embed, view=AttendanceView(ctx.author.id))


def setup(bot):
    bot.add_cog(Game(bot))
