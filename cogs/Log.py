import os

import discord
from discord import ApplicationContext
from discord.ext import commands
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient

from modules.make_embed import makeEmbed, Color, makeView

load_dotenv()

guild_ids = list(map(int, os.environ.get('GUILDS').split()))
client = MongoClient(os.environ.get('MONGO_URI'))

db = client["gaol"]["log"]


# # Test decorator
# def log_message_task(func):
#     async def wrapper(self, message, *args, **kwargs):
#         guild = message.guild
#         channel = message.channel
#
#         if guild.id not in self.guilds:
#             return
#         if not self.status[guild.id]["enabled"]:
#             return
#         if channel.id in self.status[guild.id]["excludedChannelIds"]:
#             return
#
#         if message.author.bot and not self.status[guild.id]["logBotMessage"]:
#             return
#
#         try:
#             await func(self, message, *args, **kwargs)
#         except Exception as e:
#             print(f"Error logging message: {e}")
#     return wrapper


class Log(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        db_all = db.find()
        self.status = {}
        self.guilds = []
        for doc in db_all:
            del doc["_id"]
            guild_id = doc.pop("guild_id")
            self.status[guild_id] = doc
            self.guilds.append(guild_id)

        @bot.listen(once=True)
        async def on_ready():
            print(f"Log ready")

        @bot.listen()
        async def on_message(message: discord.Message):
            guild = message.guild
            channel = message.channel

            if guild.id not in self.guilds:
                return
            if not self.status[guild.id]["enabled"]:
                return
            if channel.id in self.status[guild.id]["excludedChannelIds"]:
                return

            if message.author.bot and not self.status[guild.id]["logBotMessage"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Message sent\nAuthor: {message.author.mention} | {message.author.id}\nTime: {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}\nChannel: {channel.mention} | {channel.id}\nContent: {message.content}")
                if message.attachments:
                    container.add_text("Attachments:")
                    for attachment in message.attachments:
                        container.add_text(f"- {attachment.url}")
                if message.stickers:
                    container.add_text("Stickers:")
                    for sticker in message.stickers:
                        container.add_text(f"- {sticker.name} | {sticker.id}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging message: {e}")


    log_commands = discord.SlashCommandGroup(name="log", name_localizations={"ko": "로그"},
                                             description="Commands of managing logs",
                                             description_localizations={"ko": "로그 관리 명령어"},
                                             guild_ids=guild_ids)

    @log_commands.command(name="init", name_localizations={"ko": "초기화"},
                          description="Initialize the log system",
                          description_localizations={"ko": "로그 시스템을 초기화합니다."})
    async def init_(self, ctx: ApplicationContext):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.respond(embed=makeEmbed("Permission Denied", "", Color.error))

        guild = db.find_one({"guild_id": ctx.guild.id})

        if not guild:
            data = {"guild_id": ctx.guild.id,
                    "channel_id": 0,
                    "enabled": False,
                    "logBotMessage": False,
                    "logMemberJoin": True,
                    "logMemberLeave": True,
                    "logPunishment": True,
                    "logMessageEdit": True,
                    "logMessageDelete": True,
                    "logMessageReactionAdd": False,
                    "logMessageReactionRemove": False,
                    "logGuildUpdate": True,
                    "logChannelUpdate": True,
                    "logRoleUpdate": True,
                    "logEmojiUpdate": True,
                    "logInviteCreate": True,
                    "logInviteDelete": False,
                    "logThreadUpdate": True,
                    "logMemberUpdate": True,
                    "excludedChannelIds": []
                    }
            db.insert_one(data)
            self.status[ctx.guild.id] = data

        class ChannelIdModal(discord.ui.Modal):
            def __init__(self, bot, status):
                super().__init__(title="Log Channel ID")
                self.channel_id = discord.ui.InputText(label="Channel ID", placeholder="Enter the channel ID",
                                                       required=True, max_length=20)
                self.add_item(self.channel_id)

                self.bot = bot
                self.status = status

            async def callback(self, interaction: discord.Interaction):
                channel = self.bot.get_channel(int(self.children[0].value))
                if not channel or not isinstance(channel, discord.TextChannel):
                    return await interaction.response.send_message(
                        embed=makeEmbed("Invalid Channel ID", "Please enter a valid text channel ID.", Color.error),
                        ephemeral=True)

                db.update_one({"guild_id": ctx.guild.id}, {"$set": {"channel_id": channel.id, "enabled": True}})
                self.status[interaction.guild.id]["channel_id"] = channel.id
                self.status[interaction.guild.id]["enabled"] = True

                return await interaction.response.send_message(embed=makeEmbed("Log Channel Set",
                                                                        f"Log channel has been set to {channel.mention}",
                                                                        Color.success), ephemeral=True)

        return await ctx.send_modal(ChannelIdModal(self.bot, self.status))


def setup(bot):
    bot.add_cog(Log(bot))
