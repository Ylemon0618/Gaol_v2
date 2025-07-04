import discord

from modules.messages.embeds import SongEmbed
from modules.song_player import YTDLSource, SongPlayer


class ChangeRepeatView(discord.ui.View):
    def __init__(self, ctx, bot, players, count):
        super().__init__(timeout=None)

        self.ctx = ctx
        self.bot = bot
        self.players = players
        self.count = count

        self.player = self.players[self.ctx.guild.id]

    @discord.ui.button(
        label="확인",
        custom_id="change_repeat_confirm",
        style=discord.ButtonStyle.green
    )
    async def confirm_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        embed = SongEmbed.Success.repeat

        if self.count:
            self.player.repeat_count = self.count - 1
            self.player.repeat_count_max = self.count

            embed.description = f"대기열을 {self.count}번 반복합니다."
        else:
            self.player.repeat_count = self.player.repeat_count_max = -1

        await interaction.response.edit_message(embed=embed, view=None)

        queue_list = self.player.queue_list.copy()

        self.player.queue.task_done()

        del self.players[self.ctx.guild.id]
        self.player = SongPlayer(self.ctx, self.players)
        self.players[self.ctx.guild.id] = self.player

        self.player.repeat = True
        self.player.first = self.player.queue_list[0]
        self.player.queue_list = queue_list

        for song in queue_list + [queue_list[0]]:
            source = await YTDLSource.create_source(self.ctx, url=song.url, loop=self.bot.loop, requester=song.requester,
                                                    download=True, send_message=False)
            await self.player.queue.put(source)

    @discord.ui.button(
        label="취소",
        custom_id="change_repeat_cancel",
        style=discord.ButtonStyle.red
    )
    async def cancel_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        return await interaction.delete_original_response()
