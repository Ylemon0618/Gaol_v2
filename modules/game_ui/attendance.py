import random
from datetime import datetime

import discord
from discord import ApplicationContext

from modules.make_embed import makeEmbed, Color
from modules.connect_db.balance import *
from modules.connect_db.attendance import *


class AttendanceView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)

        self.user_id = user_id

        self.add_item(AttendanceGetMoneyButton(user_id))
        self.add_item(AttendanceRandomButton(user_id))


class AttendanceGetMoneyButton(discord.ui.Button):
    def __init__(self, user_id):
        super().__init__(label="Get 10000$ | 10000$ 받기", style=discord.ButtonStyle.primary)

        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                embed=makeEmbed(":warning: Error :warning:", "You are not the sender of this message.", Color.error),
                ephemeral=True)

        new_balance = update_user_balance(self.user_id, 10000)

        embed = makeEmbed(":moneybag: Attendance Money | 출석 보상 :moneybag:", "", Color.success)
        embed.add_field(name="Money Received | 받은 돈", value=f"{10000}$", inline=False)
        embed.add_field(name="New Balance | 잔고", value=f"{new_balance}$", inline=False)

        return await interaction.response.edit_message(embed=embed, view=None)


class AttendanceRandomButton(discord.ui.Button):
    def __init__(self, user_id):
        super().__init__(label="Random money | 랜덤으로 받기", style=discord.ButtonStyle.primary)

        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                embed=makeEmbed(":warning: Error :warning:", "You are not the sender of this message.", Color.error),
                ephemeral=True)

        embed = makeEmbed(":moneybag: Random Money | 랜덤 출석 보상 :moneybag:",
                          "Please select one of the buttons below.\n아래의 버튼 중 하나를 선택 해 주세요.", Color.success)

        return await interaction.response.edit_message(embed=embed, view=AttendanceRandomChooseView(self.user_id))


class AttendanceRandomChooseView(discord.ui.View):
    def __init__(self, user_id, disabled=False, colors=[discord.ButtonStyle.gray] * 5, moneys=None):
        super().__init__(timeout=None)

        self.user_id = user_id

        if not moneys:
            moneys = [100, 1000, 5000, 10000, 20000]
            random.shuffle(moneys)

        for idx in range(5):
            self.add_item(AttendanceRandomMoneyButton(user_id, moneys[idx], moneys, disabled, colors[idx], idx))


class AttendanceRandomMoneyButton(discord.ui.Button):
    def __init__(self, user_id, amount, moneys, disabled, color, idx):
        super().__init__(label=f"{amount} $" if disabled else "? $", style=color, disabled=disabled)

        self.user_id = user_id
        self.amount = amount
        self.moneys = moneys
        self.idx = idx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                embed=makeEmbed(":warning: Error :warning:", "You are not the sender of this message.", Color.error),
                ephemeral=True)

        new_balance = update_user_balance(self.user_id, self.amount)

        embed = makeEmbed(":moneybag: Random Money | 랜덤 출석 보상 :moneybag:", "", Color.success)
        embed.add_field(name="Money Received | 받은 돈", value=f"{self.amount}$", inline=False)
        embed.add_field(name="New Balance | 잔고", value=f"{new_balance}$", inline=False)

        colors = [discord.ButtonStyle.red] * 5
        colors[self.idx] = discord.ButtonStyle.green
        return await interaction.response.edit_message(embed=embed,
                                                       view=AttendanceRandomChooseView(self.user_id, True, colors, self.moneys))
