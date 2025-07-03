import os
from dotenv import load_dotenv
import json
from copy import deepcopy
from html import unescape

import discord
from discord import Option, ApplicationContext, Interaction
from discord.ext import commands
from google.cloud import translate_v2 as translate
import google.cloud as cloud

from modules.make_embed import makeEmbed, Color
from modules.messages.embeds import HelpEmbed

load_dotenv()

guild_ids = list(map(int, os.environ.get('GUILDS').split()))

client = cloud.translate.TranslationServiceClient()
rare_supported_langs = client.get_supported_languages(parent="projects/" + os.environ.get('GOOGLE_CLOUD_PROJECT_ID'))
supported_langs = [lang.language_code for lang in rare_supported_langs.languages]


class HelpView(discord.ui.View):
    def __init__(self, bot: discord.Bot):
        super().__init__(timeout=None)

        self.add_item(HelpSelect(bot))


class HelpSelect(discord.ui.Select):
    def __init__(self, bot: discord.Bot):
        super().__init__(
            placeholder="What type of help do you need?",
            options=[
                discord.SelectOption(label="Command List | 명령어 도움말", value="command", emoji="❓",
                                     description="Display the command list"),
                discord.SelectOption(label="Inquiry | 문의", value="inquiry", emoji="🙋",
                                     description="Open an inquiry channel"),
                discord.SelectOption(label="Term of Service | 이용 약관", value="tos", emoji="📜",
                                     description="Display the term of service")
            ]
        )

        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]

        if choice == "command":
            await interaction.response.edit_message(embed=HelpEmbed.choose_command, view=CommandView())
        elif choice == "inquiry":
            await interaction.response.send_modal(modal=InquiryModal(self.bot))
        elif choice == "tos":
            await interaction.response.edit_message(
                embed=makeEmbed("📜 Term of Service | 이용 약관 📜",
                                "Please check the term of service in the link below.\n\n아래 링크에서 이용 약관을 확인해 주세요.\n\nhttps://demo-link.com",
                                Color.success))


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

        self.add_item(CommandPrevButton(lang, page, group, prefix))
        self.add_item(CommandNextButton(lang, page, group, prefix))
        self.add_item(CommandBackButton(lang))
        self.add_item(CommandLangButton(lang, page, group, prefix))
        self.add_item(CommandListSelect(lang, page, group, prefix))


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
            placeholder="Commands",
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


class InquiryModal(discord.ui.Modal):
    def __init__(self, bot: discord.Bot):
        super().__init__(title="Inquiry | 문의")

        self.bot = bot

        self.add_item(discord.ui.InputText(label="Please enter your inquiry. 문의 사항을 입력 해 주세요.",
                                           placeholder="Your inquiry here",
                                           style=discord.InputTextStyle.long, custom_id="inquiry"))

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()

        value = self.children[0].value

        for owner_id in os.environ.get('OWNERS').split():
            owner = self.bot.get_user(int(owner_id))

            dm = await owner.create_dm()
            await dm.send(embed=makeEmbed(f"{interaction.user.id} ({interaction.user.mention})", value, Color.success))

        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=makeEmbed("🙋 Inquiry | 문의 🙋",
                            "Your inquiry has been sent. Thank you!\n\n문의가 전송되었습니다. 감사합니다!",
                            Color.success),
            view=None)


class Utils(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    utils_commands = discord.SlashCommandGroup(name="utils", name_localizations={"ko": "유틸리티"},
                                               description="Commands of utility",
                                               description_localizations={"ko": "각종 기능들을 사용할 수 있는 명령어"},
                                               guild_ids=guild_ids)

    @utils_commands.command(name="ping", name_localizations={"ko": "핑"},
                            description="Check the bot's response time",
                            description_localizations={"ko": "봇의 응답 시간을 확인합니다."})
    async def ping_(self, ctx: ApplicationContext):
        container = discord.ui.Container()
        container.add_text(":ping_pong: Pong! :ping_pong:")
        container.add_separator()
        container.add_text(f"{round(self.bot.latency * 1000)}ms")

        view = discord.ui.View(timeout=None)
        view.add_item(container)

        await ctx.respond(view=view)

    @utils_commands.command(name="help", name_localizations={"ko": "도움"},
                            description="Do you need some help? Use this command to get help!",
                            description_localizations={"ko": "도움이 필요하신가요? 이 명령어를 사용해 도움을 받으세요!"})
    async def help_(self, ctx: ApplicationContext):
        embed = HelpEmbed.choose_item
        await ctx.respond(embed=embed, view=HelpView(ctx.bot), ephemeral=True)

    @utils_commands.command(name="info", name_localizations={"ko": "정보"},
                            description="Get the bot's information",
                            description_localizations={"ko": "봇의 정보를 확인합니다."})
    async def info_(self, ctx: ApplicationContext):
        embed = makeEmbed(f"For More Convenience: {self.bot.user.name}", "", Color.success)

        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url)

        # embed.add_field(name="Version | 버전", value="v1.0.0", inline=False)
        embed.add_field(name="Ping | 핑", value=f"{round(self.bot.latency * 1000)}ms", inline=False)
        embed.add_field(name="Guilds | 서버 수", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Users | 유저 수", value=len(self.bot.users), inline=True)
        embed.add_field(name="Commands | 명령어", value="Enter `/utils help`!\n/`유틸리티 도움`을 입력해 보세요!", inline=False)

        await ctx.respond(embed=embed)

    # @utils_commands.command(name="calendar", name_localizations={"ko": "달력"},
    #                         description="Manage and view your calendar and events",
    #                         description_localizations={"ko": "달력과 이벤트를 관리하고 확인합니다."})
    # async def calendar_(self, ctx: ApplicationContext):
    #     pass

    @utils_commands.command(name="translate", name_localizations={"ko": "번역"},
                            description="Translate text to another language",
                            description_localizations={"ko": "텍스트를 다른 언어로 번역합니다."})
    async def translate_(self, ctx: ApplicationContext,
                         text: Option(str, name="text", name_localizations={"ko": "텍스트"},
                                      description="Enter the text to translate",
                                      description_localizations={"ko": "번역할 텍스트를 입력해 주세요."}),
                         target_lang: Option(str, name="target_language", name_localizations={"ko": "목표언어"},
                                             description="Enter the target language",
                                             description_localizations={"ko": "번역할 목표 언어를 입력해 주세요."}),
                         source_lang: Option(str, name="source_language", name_localizations={"ko": "원본언어"},
                                             description="Enter the source language",
                                             description_localizations={"ko": "번역할 원본 언어를 입력해 주세요."}) = None
                         ):
        if target_lang not in supported_langs:
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:",
                                                     f"{target_lang} is not supported language\n{target_lang}은(는) 지원하지 않는 언어입니다.\n\n[Supported languages / 지원하는 언어 목록](<https://cloud.google.com/translate/docs/languages>)",
                                                     Color.error))
        if source_lang and source_lang not in supported_langs:
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:",
                                                     f"{source_lang} is not supported language\n{source_lang}은(는) 지원하지 않는 언어입니다.\n\n[Supported languages / 지원하는 언어 목록](<https://cloud.google.com/translate/docs/languages>)",
                                                     Color.error))

        translate_client = translate.Client()
        try:
            if source_lang:
                translated = translate_client.translate(
                    text,
                    target_language=target_lang,
                    source_language=source_lang
                )
            else:
                translated = translate_client.translate(
                    text,
                    target_language=target_lang
                )
                source_lang = translated['detectedSourceLanguage']

            translated_text = unescape(translated['translatedText'])

            embed = makeEmbed(f"Translate | 번역 ({source_lang} → {target_lang})",
                              f"-# Original Text ({source_lang})\n{text}\n\n-# Translated Text ({target_lang})\n{translated_text}",
                              Color.success)
            embed.set_footer(text="Powered by Google Translate API")
            return await ctx.respond(embed=embed)
        except Exception as e:
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", str(e), Color.error))


def setup(bot):
    bot.add_cog(Utils(bot))
