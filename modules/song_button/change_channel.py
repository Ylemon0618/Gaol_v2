import asyncio
import os

import discord
from discord import Option, ApplicationContext
from discord.ext import commands

from modules.make_embed import makeEmbed, Color
from modules.song_player import YTDLSource


class MoveChannelView(discord.ui.View):
    def __init__(self, vc, channel, confirm_view=None):
        super().__init__(timeout=None)

        self.vc = vc
        self.confirm_view = confirm_view

        self.now = vc.channel
        self.new = channel

    @discord.ui.button(
        label="확인",
        custom_id="move_channel_confirm",
        style=discord.ButtonStyle.green
    )
    async def confirm_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.vc.move_to(self.new)

        return await interaction.response.edit_message(
            embed=makeEmbed(":musical_note: Joined :musical_note:", self.new.mention, Color.success),
            view=self.confirm_view)

    @discord.ui.button(
        label="취소",
        custom_id="move_channel_cancel",
        style=discord.ButtonStyle.red
    )
    async def cancel_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        return await interaction.delete_original_message()


class ResetQueueView(discord.ui.View):
    def __init__(self, bot, ctx, players: dict, song=None):
        super().__init__(timeout=None)

        self.bot = bot
        self.ctx = ctx
        self.players = players
        self.song = song

        self.guild = ctx.guild

    @discord.ui.button(
        label="대기열에 추가",
        custom_id="add_queue",
        style=discord.ButtonStyle.green,
        row=1
    )
    async def add_queue_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        embed.description += "\n\n대기열을 초기화하지 않고 유지합니다."

        await interaction.response.edit_message(embed=embed, view=None)

        player = self.players[self.guild.id]

        source = await YTDLSource.create_source(self.ctx, url=self.song, loop=self.bot.loop, download=True)

        return await player.queue.put(source)

    @discord.ui.button(
        label="대기열 초기화 및 재생",
        custom_id="reset_queue",
        style=discord.ButtonStyle.red,
        row=2
    )
    async def reset_queue_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embed=makeEmbed(":no_entry: Reset :no_entry:", "대기열을 초기화했습니다.", Color.success), view=None)

        while self.ctx.voice_client.is_playing():
            self.ctx.voice_client.stop()

        player = self.players[self.guild.id]

        source = await YTDLSource.create_source(self.ctx, url=self.song, loop=self.bot.loop, download=True)

        return await player.queue.put(source)
