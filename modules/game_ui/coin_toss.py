import random

import discord
from discord import ApplicationContext

from modules.connect_db.balance import *
from modules.make_embed import makeEmbed, Color


async def coin_toss(ctx: ApplicationContext):
    await ctx.send_modal(CoinTossBettingModal())


class CoinTossBettingModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Coin Toss | 동전 던지기")
        self.add_item(discord.ui.InputText(label="Bet Amount | 베팅액",
                                           placeholder="Enter the amount to bet", required=True))

    async def callback(self, interaction: discord.Interaction):
        try:
            bet_amount = int(self.children[0].value)
            balance = get_user_balance(interaction.user.id)

            if bet_amount > balance:
                return await interaction.response.send_message(embed=makeEmbed(":warning: Error :warning:",
                                                                                 "잔액이 부족합니다.", Color.error),
                                                               ephemeral=True)

            update_user_balance(interaction.user.id, -bet_amount)
        except ValueError:
            return await interaction.response.send_message(embed=makeEmbed(":warning: Error :warning:",
                                                                             "베팅액은 숫자여야 합니다.", Color.error),
                                                           ephemeral=True)

        if bet_amount <= 0:
            return await interaction.response.send_message(embed=makeEmbed(":warning: Error :warning:",
                                                                             "베팅액은 0보다 커야 합니다.", Color.error),
                                                           ephemeral=True)

        embed = makeEmbed(":coin: Coin Toss | 동전 던지기 :coin:",
                              f"Please bet on the heads or the tails\n앞면 혹은 뒷면에 베팅 해 주세요.\n\n-# If you do not select anything, all of the amount you bet will disappear.\n-# 아무것도 선택하지 않으면 베팅액 전부가 사라집니다.",
                              Color.success)
        embed.add_field(name="Betting Amount | 베팅액", value=f"{bet_amount}$", inline=False)
        embed.add_field(name="Probability | 확률", value="- Heads | 앞면: 49.99%\n- Tails | 뒷면: 49.99%\n- Side | 옆면: 0.02%", inline=True)
        embed.add_field(name="Dividend Rate | 배당률", value="- Success | 성공: 2.0\n- Fail | 실패: 0.5\n- Side | 옆면: 50.0", inline=True)

        await interaction.response.send_message(embed=embed, view=CoinTossSelectView(bet_amount))


class CoinTossSelectView(discord.ui.View):
    def __init__(self, bet_amount):
        super().__init__(timeout=None)

        self.bet_amount = bet_amount

        self.add_item(CoinTossSelect(bet_amount))


class CoinTossSelect(discord.ui.Select):
    def __init__(self, bet_amount):
        super().__init__(
            placeholder="Choose heads or tails",
            options=[
                discord.SelectOption(label="Heads | 앞면", value="heads", emoji="🪙"),
                discord.SelectOption(label="Tails | 뒷면", value="tails", emoji="🪙")
            ]
        )

        self.bet_amount = bet_amount

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        result_kr = {"heads": "앞면", "tails": "뒷면", "side": "옆면"}

        random_num = random.randint(1, 10000)
        if random_num <= 2:
            result = "side"
        elif random_num <= 5001:
            result = "heads"
        else:
            result = "tails"

        if result == "side":
            dividend = self.bet_amount * 50
        elif result == choice:
            dividend = self.bet_amount * 2
        else:
            dividend = self.bet_amount // 2

        new_balance = update_user_balance(interaction.user.id, dividend)

        embed = makeEmbed(":coin: Coin Toss | 동전 던지기 :coin:","", Color.success)
        embed.add_field(name="Choice | 선택", value=f"{choice.capitalize()} | {result_kr.get(choice)}", inline=True)
        embed.add_field(name="Result | 결과", value=f"{result.capitalize()} | {result_kr.get(result)}", inline=True)
        embed.add_field(name="", value="", inline=False)
        embed.add_field(name="Bet Amount | 베팅액", value=f"{self.bet_amount}$", inline=True)
        embed.add_field(name="Dividend | 배당금", value=f"{dividend}$", inline=True)
        embed.add_field(name="Balance | 잔고", value=f"{new_balance}$", inline=False)

        await interaction.response.edit_message(embed=embed, view=None)
