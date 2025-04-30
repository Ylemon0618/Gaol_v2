from abc import ABC

from modules import *

load_dotenv()

OWNERS = list(map(int, os.environ.get('OWNERS').split()))
intents = discord.Intents.all()


class Bot(commands.Bot, ABC):
    def __init__(self):
        super().__init__(intents=intents, command_prefix="!", owner_ids=OWNERS)

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


@bot.command(name="eval")
async def eval_(ctx, *, code: str):
    if ctx.author.id not in OWNERS:
        return

    try:
        for l in code.split("<br>"):
            if l.startswith("await "):
                await eval(l[6:])
            else:
                eval(l)
    except Exception as e:
        dm = await ctx.author.create_dm()
        await dm.send(e)

bot.run(os.environ.get('TOKEN'))
