import discord
from discord import slash_command, Option, ApplicationContext
from discord.ext import commands

import asyncio


OWNERS = [656059360882982912, 822445708467503114]


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    admin_commands = discord.SlashCommandGroup(name="admin", description="Commands for maintenance (Only for owners)",
                                               guild_ids=[1278195924203601930])

    @admin_commands.command(name="load", description="Load Cog")
    async def load_(self, ctx, extension):
        if ctx.author.id in OWNERS:
            self.bot.load_extension(f"cogs.{extension}")
            await ctx.respond("Successfully loaded the Cog.")
        else:
            await ctx.respond("레몬 전용임 ㅅㄱ")

    @admin_commands.command(name="unload", description="Unload Cog")
    async def unload_(self, ctx, extension):
        if ctx.author.id in OWNERS:
            self.bot.unload_extension(f"cogs.{extension}")
            await ctx.respond("Successfully unloaded the Cog.")
        else:
            await ctx.respond("레몬 전용임 ㅅㄱ")

    @admin_commands.command(name="reload", description="Reload Cog")
    async def reload_(self, ctx, extension):
        if ctx.author.id in OWNERS:
            self.bot.reload_extension(f"cogs.{extension}")
            await ctx.respond("Successfully reloaded the Cog.")
        else:
            await ctx.respond("레몬 전용임 ㅅㄱ")


def setup(bot):
    bot.add_cog(Admin(bot))
