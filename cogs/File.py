import os

import discord
from discord import Option, OptionChoice, ApplicationContext
from discord.ext import commands
from dotenv import load_dotenv

from modules.convert_file import ConvertMainView, Convert
from modules.make_embed import makeEmbed, Color

load_dotenv()

guild_ids = list(map(int, os.environ.get('GUILDS').split()))


class File(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    file_commands = discord.SlashCommandGroup(name="file", name_localizations={"ko": "파일"},
                                              description="Commands for managing your files",
                                              description_localizations={"ko": "파일 관리와 관련된 명령어"},
                                              guild_ids=guild_ids)

    @file_commands.command(name="extract", name_localizations={"ko": "추출"},
                           description="Extract audio from video file",
                           description_localizations={"ko": "영상에서 오디오를 추출합니다."})
    async def extract_(self, ctx: ApplicationContext,
                       video: Option(discord.Attachment, name="video", name_localizations={"ko": "영상"},
                                     description="Upload a video file to extract audio",
                                     description_localizations={"ko": "오디오를 추출 할 영상 파일을 업로드 해 주세요."}),
                       ext: Option(str, name="extension", name_localizations={"ko": "확장자"},
                                   description="Choose extension of audio file",
                                   description_localizations={"ko": "오디오 파일의 확장자를 선택 해 주세요."},
                                   choices=[
                                       OptionChoice(name="wav", value="wav"),
                                       OptionChoice(name="mp3", value="mp3")
                                   ])):
        if video.content_type.split('/')[0] != "video":
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "올바른 영상 파일이 아닙니다.", Color.error))

        video_ext = video.content_type.split('/')[1]

        """oauth2로 외부 웹페이지로 리다이렉트 시켜서 파일 업로드 시스템 구축하기"""

    @file_commands.command(name="convert", name_localizations={"ko": "변환"},
                           description="Convert WebP file to image file, or image file to WebP",
                           description_localizations={"ko": "WebP 파일을 이미지 파일로, 이미지 파일을 WebP 파일로 변환합니다."})
    async def convert_(self, ctx: ApplicationContext,
                       file: Option(discord.Attachment, name="file", name_localizations={"ko": "파일"},
                                    description="Upload a WebP or image file to convert",
                                    description_localizations={"ko": "변환할 WebP 또는 이미지 파일을 업로드 해 주세요."})):
        if file.content_type.split('/')[0] != "image":
            return await ctx.respond(embed=makeEmbed(":warning: Error :warning:", "올바른 파일이 아닙니다.", Color.error))

        file_ext = file.content_type.split('/')[1]

        if file_ext == "webp":
            embed = makeEmbed(":arrows_counterclockwise: Convert :arrows_counterclockwise:", "변환 할 확장자를 선택 해 주세요.",
                              Color.success)
            embed.set_image(url=file.url)

            await ctx.respond(embed=embed, view=ConvertMainView(file), ephemeral=True)
        else:
            path = await Convert(file, "webp")

            await ctx.respond(file=discord.File(path), ephemeral=True)

            os.remove(path)


def setup(bot):
    bot.add_cog(File(bot))
