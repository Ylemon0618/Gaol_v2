from abc import ABC

import discord
from discord import slash_command, Option, ApplicationContext
from discord.ext import commands

import asyncio

import os
from dotenv import load_dotenv

load_dotenv()


intents = discord.Intents.all()


class Bot(commands.Bot, ABC):
    def __init__(self):
        super().__init__(intents=intents)

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

bot.run(os.environ.get('TOKEN'))
