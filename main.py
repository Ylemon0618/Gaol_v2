from abc import ABC
from google.cloud import translate_v2 as translate
from html import unescape

from modules import *

load_dotenv()

bot_id = int(os.environ.get('ID'))
OWNERS = list(map(int, os.environ.get('OWNERS').split()))
intents = discord.Intents.all()


class Bot(commands.Bot, ABC):
    def __init__(self):
        super().__init__(intents=intents, command_prefix=f"<@{bot_id}> ", owner_ids=OWNERS)

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


@bot.command(name="korean", aliases=["ko", "한국어"])
async def korean(ctx: ApplicationContext):
    try:
        reply = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        content = reply.content

        translate_client = translate.Client()
        translated = translate_client.translate(content, target_language="ko")

        await ctx.send(translated['translatedText'])
    except AttributeError:
        await ctx.send("Please reply on message")


@bot.command(name="translate", aliases=["trans", "tr", "번역"])
async def translate_(ctx: ApplicationContext, dest: str):
    try:
        reply = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        content = reply.content

        translate_client = translate.Client()
        translated = translate_client.translate(content, target_language=dest)

        text = unescape(translated['translatedText'])
        await ctx.send(text)
    except AttributeError:
        await ctx.send("Please reply on message")
    except Exception as e:
        await ctx.send(str(e))


bot.run(os.environ.get('TOKEN'))
