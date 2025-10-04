import os
from datetime import datetime

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
            try:
                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
            except Error as e:
                await message.channel.send(e)
            
            if not guild or not channel:
                return
            if guild.id not in self.guilds or not self.status[guild.id]["enabled"] or channel.id in self.status[guild.id]["excludedChannelIds"]:
                return
            if message.author.bot and not self.status[guild.id]["logBotMessage"]:
                return
            if self.status[guild.id]["logBotMessage"] and message.author.bot and channel == log_channel:
                return
            if not self.status[guild.id]["logMessageSend"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Message sent\nAuthor: {message.author.mention} | {message.author.id}\nTime: {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}\nChannel: {channel.mention} | {channel.id}\nContent: {message.content}")
                if messageattachments:
                    container.add_text("Attachments:")
                    for attachment in message.attachments:
                        container.add_text(f"- {attachment.url}")
                if message.stickers:
                    container.add_text("Stickers:")
                    for sticker in message.stickers:
                        container.add_text(f"- {sticker.name} | {sticker.id}")

                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging message: {e}")

        @bot.listen()
        async def on_message_edit(before: discord.Message, after: discord.Message):
            guild = before.guild
            channel = before.channel

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"] or channel.id in self.status[guild.id]["excludedChannelIds"]:
                return
            if before.author.bot and not self.status[guild.id]["logBotMessage"]:
                return
            if not self.status[guild.id]["logMessageEdit"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Message edited\nAuthor: {before.author.mention} | {before.author.id}\nTime: {after.edited_at.strftime('%Y-%m-%d %H:%M:%S')}\nChannel: {channel.mention} | {channel.id}\nBefore: {before.content}\nAfter: {after.content}")
                if before.attachments:
                    container.add_text("Attachments before edit:")
                    for attachment in before.attachments:
                        container.add_text(f"- {attachment.url}")
                if after.attachments:
                    container.add_text("Attachments after edit:")
                    for attachment in after.attachments:
                        container.add_text(f"- {attachment.url}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging message edit: {e}")

        @bot.listen()
        async def on_message_delete(message: discord.Message):
            guild = message.guild
            channel = message.channel

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"] or channel.id in self.status[guild.id]["excludedChannelIds"]:
                return
            if message.author.bot and not self.status[guild.id]["logBotMessage"]:
                return
            if not self.status[guild.id]["logMessageDelete"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Message deleted\nAuthor: {message.author.mention} | {message.author.id}\nTime: {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}\nChannel: {channel.mention} | {channel.id}\nContent: {message.content}")
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
                print(f"Error logging message delete: {e}")

        @bot.listen()
        async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
            guild = reaction.message.guild
            channel = reaction.message.channel

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"] or channel.id in self.status[guild.id]["excludedChannelIds"]:
                return
            if user.bot and not self.status[guild.id]["logBotMessage"]:
                return
            if not self.status[guild.id]["logMessageReactionAdd"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Reaction added\nUser: {user.mention} | {user.id}\nTime: {reaction.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}\nChannel: {channel.mention} | {channel.id}\nMessage: {reaction.message.content}\nReaction: {reaction.emoji}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging reaction add: {e}")

        @bot.listen()
        async def on_reaction_remove(reaction: discord.Reaction, user: discord.User):
            guild = reaction.message.guild
            channel = reaction.message.channel

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"] or channel.id in self.status[guild.id]["excludedChannelIds"]:
                return
            if user.bot and not self.status[guild.id]["logBotMessage"]:
                return
            if not self.status[guild.id]["logMessageReactionRemove"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Reaction removed\nUser: {user.mention} | {user.id}\nTime: {reaction.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}\nChannel: {channel.mention} | {channel.id}\nMessage: {reaction.message.content}\nReaction: {reaction.emoji}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging reaction remove: {e}")

        @bot.listen()
        async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
            guild = member.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logVoiceChatUpdate"]:
                return
            if member.bot and not self.status[guild.id]["logBotJoin"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Voice state update\n"
                                   f"Member: {member.mention} | {member.id}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                   f"-# Before\nChannel: {before.channel.name if before.channel else 'None'} | {before.channel.id if before.channel else 'None'}\n"
                                   f"Deaf: {before.self_deaf}\nMute: {before.self_mute}\nVideo: {before.self_video}\nStream: {before.self_stream}\n\n"
                                   f"-# After\nChannel: {after.channel.name if after.channel else 'None'} | {after.channel.id if after.channel else 'None'}\n"
                                   f"Deaf: {after.self_deaf}\nMute: {after.self_mute}\nVideo: {after.self_video}\nStream: {after.self_stream}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging voice state update: {e}")

        @bot.listen()
        async def on_member_join(member: discord.Member):
            guild = member.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logMemberJoin"]:
                return
            if member.bot and not self.status[guild.id]["logBotJoin"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Member joined\nMember: {member.mention} | {member.id}\nTime: {member.joined_at.strftime('%Y-%m-%d %H:%M:%S')}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging member join: {e}")

        @bot.listen()
        async def on_member_remove(member: discord.Member):
            guild = member.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logMemberLeave"]:
                return
            if member.bot and not self.status[guild.id]["logBotJoin"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Member left\nMember: {member.mention} | {member.id}\nTime: {member.joined_at.strftime('%Y-%m-%d %H:%M:%S')}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging member leave: {e}")

        @bot.listen()
        async def on_member_update(before: discord.Member, after: discord.Member):
            guild = before.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logMemberUpdate"]:
                return
            if before.bot and not self.status[guild.id]["logBotUpdate"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Member updated\nMember: {before.mention} | {before.id}\nTime: {after.joined_at.strftime('%Y-%m-%d %H:%M:%S')}")

                changes = []
                if before.nick != after.nick:
                    changes.append(f"Nickname changed from `{before.nick}` to `{after.nick}`")
                if before.roles != after.roles:
                    changes.append(f"Roles changed from `{', '.join([role.name for role in before.roles])}` to `{', '.join([role.name for role in after.roles])}`")

                if changes:
                    container.add_text("Changes:\n" + "\n".join(changes))

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging member update: {e}")

        @bot.listen()
        async def on_guild_update(before: discord.Guild, after: discord.Guild):
            guild = before

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logGuildUpdate"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Guild updated\nGuild: {guild.name} | {guild.id}\nTime: {after.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                changes = []
                if before.name != after.name:
                    changes.append(f"Name changed from `{before.name}` to `{after.name}`")
                if before.icon != after.icon:
                    changes.append("Icon changed")
                if before.banner != after.banner:
                    changes.append("Banner changed")

                if changes:
                    container.add_text("Changes:\n" + "\n".join(changes))

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging guild update: {e}")

        @bot.listen()
        async def on_channel_create(channel: discord.abc.GuildChannel):
            guild = channel.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logChannelUpdate"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Channel created\nChannel: {channel.name} | {channel.id}\nTime: {channel.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging channel creation: {e}")

        @bot.listen()
        async def on_channel_delete(channel: discord.abc.GuildChannel):
            guild = channel.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logChannelUpdate"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Channel deleted\nChannel: {channel.name} | {channel.id}\nTime: {channel.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging channel deletion: {e}")

        @bot.listen()
        async def on_channel_update(before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
            guild = before.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logChannelUpdate"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Channel updated\nChannel: {before.name} | {before.id}\nTime: {after.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                changes = []
                if before.name != after.name:
                    changes.append(f"Name changed from `{before.name}` to `{after.name}`")
                if before.category != after.category:
                    changes.append(f"Category changed from `{before.category.name if before.category else 'None'}` to `{after.category.name if after.category else 'None'}`")

                if changes:
                    container.add_text("Changes:\n" + "\n".join(changes))

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging channel update: {e}")

        @bot.listen()
        async def on_role_create(role: discord.Role):
            guild = role.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logRoleUpdate"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Role created\nRole: {role.name} | {role.id}\nTime: {role.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging role creation: {e}")

        @bot.listen()
        async def on_role_delete(role: discord.Role):
            guild = role.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logRoleUpdate"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Role deleted\nRole: {role.name} | {role.id}\nTime: {role.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging role deletion: {e}")

        @bot.listen()
        async def on_role_update(before: discord.Role, after: discord.Role):
            guild = before.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logRoleUpdate"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Role updated\nRole: {before.name} | {before.id}\nTime: {after.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                changes = []
                if before.name != after.name:
                    changes.append(f"Name changed from `{before.name}` to `{after.name}`")
                if before.color != after.color:
                    changes.append(f"Color changed from `{before.color}` to `{after.color}`")
                if before.permissions != after.permissions:
                    changes.append(f"Permissions changed from `{before.permissions}` to `{after.permissions}`")

                if changes:
                    container.add_text("Changes:\n" + "\n".join(changes))

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging role update: {e}")

        @bot.listen()
        async def on_invite_create(invite: discord.Invite):
            guild = invite.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logInviteCreate"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Invite created\nInvite: {invite.code} | {invite.id}\nChannel: {invite.channel.mention} | {invite.channel.id}\nTime: {invite.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging invite creation: {e}")

        @bot.listen()
        async def on_invite_delete(invite: discord.Invite):
            guild = invite.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logInviteDelete"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Invite deleted\nInvite: {invite.code} | {invite.id}\nChannel: {invite.channel.mention} | {invite.channel.id}\nTime: {invite.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging invite deletion: {e}")

        @bot.listen()
        async def on_thread_create(thread: discord.Thread):
            guild = thread.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logThreadUpdate"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Thread created\nThread: {thread.name} | {thread.id}\nTime: {thread.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging thread creation: {e}")

        @bot.listen()
        async def on_thread_delete(thread: discord.Thread):
            guild = thread.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logThreadUpdate"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Thread deleted\nThread: {thread.name} | {thread.id}\nTime: {thread.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging thread deletion: {e}")

        @bot.listen()
        async def on_thread_update(before: discord.Thread, after: discord.Thread):
            guild = before.guild

            if guild.id not in self.guilds or not self.status[guild.id]["enabled"]:
                return
            if not self.status[guild.id]["logThreadUpdate"]:
                return

            try:
                container = discord.ui.Container()
                container.add_text(f"### Thread updated\nThread: {before.name} | {before.id}\nTime: {after.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                changes = []
                if before.name != after.name:
                    changes.append(f"Name changed from `{before.name}` to `{after.name}`")
                if before.archived != after.archived:
                    changes.append(f"Archived status changed from `{before.archived}` to `{after.archived}`")

                if changes:
                    container.add_text("Changes:\n" + "\n".join(changes))

                log_channel = self.bot.get_channel(self.status[guild.id]["channel_id"])
                await log_channel.send(view=makeView(container), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                print(f"Error logging thread update: {e}")


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

                guild = db.find_one({"guild_id": ctx.guild.id})

                data = {"guild_id": ctx.guild.id,
                        "channel_id": channel.id,
                        "enabled": True,
                        "excludedChannelIds": [],

                        "logMessageSend": True,
                        "logMessageEdit": True,
                        "logMessageDelete": True,
                        "logMessageReactionAdd": False,
                        "logMessageReactionRemove": False,
                        "logBotMessage": False,

                        "logVoiceChatUpdate": True,
                        "logBotVoiceChat": False,

                        "logMemberJoin": True,
                        "logMemberLeave": True,
                        "logBotJoin": True,

                        "logPunishment": True,

                        "logGuildUpdate": True,
                        "logChannelUpdate": True,
                        "logRoleUpdate": True,
                        "logEmojiUpdate": True,
                        "logThreadUpdate": True,
                        "logMemberUpdate": True,
                        "logBotUpdate": True,

                        "logInviteCreate": True,
                        "logInviteDelete": False,
                        }

                if guild:
                    db.update_one({"guild_id": ctx.guild.id}, {"$set": data})
                else:
                    db.insert_one(data)

                self.status[ctx.guild.id] = data

                return await interaction.response.send_message(embed=makeEmbed("Log Setting Initialized",
                                                                        f"Log channel has been set to {channel.mention}",
                                                                        Color.success), ephemeral=True)

        return await ctx.send_modal(ChannelIdModal(self.bot, self.status))


def setup(bot):
    bot.add_cog(Log(bot))
