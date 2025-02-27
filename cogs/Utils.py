import os
import json
from copy import deepcopy

import discord
from discord import Option, OptionChoice, ApplicationContext, Interaction
from discord.ext import commands
from dotenv import load_dotenv

from modules.make_embed import makeEmbed, Color
from modules.messages.embeds import HelpEmbed

load_dotenv()

guild_ids = list(map(int, os.environ.get('GUILDS').split()))


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(HelpSelect())


class HelpSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="What type of help do you need?",
            options=[
                discord.SelectOption(label="Command List | 명령어 도움말", value="command", emoji="❓",
                                     description="Display the command list"),
                discord.SelectOption(label="Inquiry | 문의", value="inquiry", emoji="🙋",
                                     description="Open an inquiry channel")
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]

        if choice == "command":
            embed = HelpEmbed.choose_command
            await interaction.response.edit_message(embed=embed, view=CommandView())


with open("./modules/help.json", "r", encoding="UTF8") as file:
    help_json = json.load(file)


def get_command(lang: str, page: int, group: str, prefix: str):
    command = help_json[group][lang][str(page)]

    name = f"/{prefix} {command['name']}"
    if command.get("args"):
        for arg in command["args"]:
            name += f" {arg}"

    return name, command["description"]


prefix_dict = {
    "song": {
        "ko": "노래",
        "en": "Song"
    },
    "file": {
        "ko": "파일",
        "en": "File"
    },
    "music": {
        "ko": "음악",
        "en": "Music"
    },
    "game": {
        "ko": "게임",
        "en": "Game"
    },
    "utils": {
        "ko": "유틸리티",
        "en": "Utils"
    }
}


class CommandView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(CommandSelect())


class CommandSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="What command do you need help with?",
            options=[
                discord.SelectOption(label="Song | 노래", value="song", emoji="🎵",
                                     description="Commands for song"),
                discord.SelectOption(label="File | 파일", value="file", emoji="📁",
                                     description="Commands for managing files"),
                discord.SelectOption(label="Music | 음악", value="music", emoji="🎹",
                                     description="Commands for music (not for playing song)"),
                discord.SelectOption(label="Game | 게임", value="game", emoji="🎮",
                                     description="Commands for plaing games"),
                discord.SelectOption(label="Utils | 유틸리티", value="utils", emoji="❔",
                                     description="Commands of utility")
            ]
        )

    async def callback(self, interaction: Interaction):
        choice = self.values[0]

        lang = "ko"
        page = 1
        prefix = prefix_dict[choice][lang]

        embed = deepcopy(HelpEmbed.commands[choice][lang])

        name, value = get_command(lang, page, choice, prefix)
        embed.add_field(name=name, value=value, inline=False)

        await interaction.response.edit_message(embed=embed, view=CommandListView(lang, page, choice, prefix))


class CommandListView(discord.ui.View):
    def __init__(self, lang: str, page: int, group: str, prefix: str):
        super().__init__(timeout=None)

        self.lang = lang
        self.page = page
        self.group = group
        self.prefix = prefix

        self.add_item(CommandPrevButton(self.lang, self.page, self.group, self.prefix))
        self.add_item(CommandNextButton(self.lang, self.page, self.group, self.prefix))
        self.add_item(CommandBackButton(self.lang))
        self.add_item(CommandLangButton(self.lang, self.page, self.group, self.prefix))
        self.add_item(CommandListSelect(self.lang, self.page, self.group, self.prefix))


class CommandNextButton(discord.ui.Button):
    def __init__(self, lang: str, page: int, group: str, prefix: str):
        super().__init__(
            label="Next",
            emoji="➡️",
            custom_id="help cmd page_next",
            style=discord.ButtonStyle.blurple
        )

        self.lang = lang
        self.page = page
        self.group = group
        self.prefix = prefix

    async def callback(self, interaction: Interaction):
        self.page += 1
        if not str(self.page) in help_json[self.group][self.lang]:
            self.page = 1

        embed = deepcopy(HelpEmbed.commands[self.group][self.lang])

        name, value = get_command(self.lang, self.page, self.group, self.prefix)
        embed.add_field(name=name, value=value)

        await interaction.response.edit_message(embed=embed,
                                                view=CommandListView(self.lang, self.page, self.group, self.prefix))


class CommandPrevButton(discord.ui.Button):
    def __init__(self, lang: str, page: int, group: str, prefix: str):
        super().__init__(
            label="Prev",
            emoji="⬅️",
            custom_id="help cmd page_prev",
            style=discord.ButtonStyle.blurple
        )

        self.lang = lang
        self.page = page
        self.group = group
        self.prefix = prefix

    async def callback(self, interaction: Interaction):
        self.page -= 1
        if not str(self.page) in help_json[self.group][self.lang]:
            self.page = int(list(help_json[self.group][self.lang].keys())[-1])

        embed = deepcopy(HelpEmbed.commands[self.group][self.lang])

        name, value = get_command(self.lang, self.page, self.group, self.prefix)
        embed.add_field(name=name, value=value)

        await interaction.response.edit_message(embed=embed,
                                                view=CommandListView(self.lang, self.page, self.group, self.prefix))


class CommandLangButton(discord.ui.Button):
    def __init__(self, lang: str, page: int, group: str, prefix: str):
        super().__init__(
            label="Change to English" if lang == "ko" else "한국어로 변경",
            custom_id="help cmd lang",
            style=discord.ButtonStyle.gray
        )

        self.lang = lang
        self.page = page
        self.group = group
        self.prefix = prefix

    async def callback(self, interaction: Interaction):
        self.lang = "en" if self.lang == "ko" else "ko"
        self.prefix = prefix_dict[self.group][self.lang]

        embed = deepcopy(HelpEmbed.commands[self.group][self.lang])

        name, value = get_command(self.lang, self.page, self.group, self.prefix)
        embed.add_field(name=name, value=value)

        await interaction.response.edit_message(embed=embed,
                                                view=CommandListView(self.lang, self.page, self.group, self.prefix))


class CommandBackButton(discord.ui.Button):
    def __init__(self, lang: str):
        super().__init__(
            label="이전으로" if lang == "ko" else "Back",
            custom_id="help cmd back",
            style=discord.ButtonStyle.green
        )

    async def callback(self, interaction: Interaction):
        embed = HelpEmbed.choose_command
        await interaction.response.edit_message(embed=embed, view=CommandView())


class CommandListSelect(discord.ui.Select):
    def __init__(self, lang: str, page: int, group: str, prefix: str):
        options = []
        for idx in list(help_json[group][lang].keys()):
            options.append(discord.SelectOption(label=help_json[group][lang][idx]["name"], value=idx))

        super().__init__(
            placeholder=group,
            options=options
        )

        self.lang = lang
        self.page = page
        self.group = group
        self.prefix = prefix

    async def callback(self, interaction: Interaction):
        self.page = int(self.values[0])

        embed = deepcopy(HelpEmbed.commands[self.group][self.lang])

        name, value = get_command(self.lang, self.page, self.group, self.prefix)
        embed.add_field(name=name, value=value)

        await interaction.response.edit_message(embed=embed,
                                                view=CommandListView(self.lang, self.page, self.group, self.prefix))


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

    @file_commands.command(name="help", name_localizations={"ko": "도움"},
                           description="Do you need some help? Use this command to get help!",
                           description_localizations={"ko": "도움이 필요하신가요? 이 명령어를 사용해 도움을 받으세요!"})
    async def help_(self, ctx: ApplicationContext):
        embed = HelpEmbed.choose_item
        await ctx.respond(embed=embed, view=HelpView(), ephemeral=True)


def setup(bot):
    bot.add_cog(Utils(bot))
