import discord

from modules.make_embed import makeEmbed, Color


def check_winner(choice1, choice2):
    if choice1 == choice2:
        return 0
    elif choice1 == "rock":
        if choice2 == "paper":
            return 2
        else:
            return 1
    elif choice1 == "paper":
        if choice2 == "scissors":
            return 2
        else:
            return 1
    elif choice1 == "scissors":
        if choice2 == "rock":
            return 2
        else:
            return 1
    return None


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
            result = makeEmbed(":fist: :raised_hand: :v:",
                               f"무승부!!\n\n{ctx.author.mention}: {emoji.get(choice)}\n{user.mention}: {emoji.get(choice2)}",
                               Color.success)
        elif check_winner(choice, choice2) == 1:
            result = makeEmbed(":fist: :raised_hand: :v:",
                               f"{ctx.author.mention} 승리!!\n\n{ctx.author.mention}: {emoji.get(choice)}\n{user.mention}: {emoji.get(choice2)}",
                               Color.success)
        else:
            result = makeEmbed(":fist: :raised_hand: :v:",
                               f"{user.mention} 승리!!\n\n{ctx.author.mention}: {emoji.get(choice)}\n{user.mention}: {emoji.get(choice2)}",
                               Color.success)

        await ctx.channel.send(f"{ctx.author.mention} {user.mention}", embed=result)