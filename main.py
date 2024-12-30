from abc import ABC

import discord
from discord import ApplicationContext
from discord.ext import commands

import os
from dotenv import load_dotenv

load_dotenv()

OWNERS = list(map(int, os.environ.get('OWNERS').split()))
intents = discord.Intents.all()


class Bot(commands.Bot, ABC):
    def __init__(self):
        super().__init__(intents=intents, command_prefix="!admin ")

        self.remove_command("help")

        for file in os.listdir("cogs"):
            if file.endswith(".py"):
                self.load_extension("cogs." + file[:-3])

    async def on_ready(self):
        await self.change_presence(status=discord.Status.online)
        print(f"{self.user.id} Successfully turned on")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.respond(embed=discord.Embed(title=":error: 권한 부족 :error:")
                              .add_field(name="부족한 권한", value=f"{error.missing_permissions}"))
        else:
            raise error

bot = Bot()


@bot.command(name="load")
async def load_(ctx: ApplicationContext, extension: str):
    if ctx.author.id in OWNERS:
        bot.load_extension(f"cogs.{extension}")
        await ctx.send("Successfully loaded the Cog.")
    else:
        await ctx.send("레몬 전용임 ㅅㄱ")

@bot.command(name="unload")
async def unload_(ctx: ApplicationContext, extension: str):
    if ctx.author.id in OWNERS:
        bot.unload_extension(f"cogs.{extension}")
        await ctx.send("Successfully unloaded the Cog.")
    else:
        await ctx.send("레몬 전용임 ㅅㄱ")

@bot.command(name="reload")
async def reload_(ctx: ApplicationContext, extension: str):
    if ctx.author.id in OWNERS:
        bot.reload_extension(f"cogs.{extension}")
        await ctx.send("Successfully reloaded the Cog.")
    else:
        await ctx.send("레몬 전용임 ㅅㄱ")


bot.run(os.environ.get('TOKEN'))
