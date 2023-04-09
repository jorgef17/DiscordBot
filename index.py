import asyncio
import discord
from discord.ext import commands, tasks
from discord.voice_client import VoiceClient
import yt_dlp as youtube_dl
from discord.utils import get
from random import choice
import datetime
import re
from urllib import parse, request
import openai


intents = discord.Intents.default()
intents.message_content = True
openai.api_key = 'Token Chatgpt'

bot = commands.Bot(command_prefix="!", intents=intents)
status = ['Music!', 'Eating!', 'ZzzzZz!']
queue = []
loop = False

youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.9):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


@bot.command()
async def ping(ctx):
    await ctx.send(f'**Pong!** Latency: {round(bot.latency * 1000)}ms')


@bot.command()
async def sum(ctx, numOne: int, numTwo: int):
    await ctx.send(numOne + numTwo)


@bot.command()
async def div(ctx, numOne: int, numTwo: int):
    await ctx.send(numOne/numTwo)


@bot.command()
async def prod(ctx, numOne: int, numTwo: int):
    await ctx.send(numOne*numTwo)


@bot.command()
async def hello(ctx):
    author = ctx.message.author
    await ctx.send(f'Hello, {author.mention}!')


@bot.command()
async def info(ctx):
    embed = discord.Embed(title=f"{ctx.guild.name}", description="Lorem Ipsum asdasd",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name="Server created at", value=f"{ctx.guild.created_at}")
    embed.add_field(name="Server Owner", value=f"{ctx.guild.owner}")
    embed.add_field(name="Server ID", value=f"{ctx.guild.id}")
    # embed.set_thumbnail(url=f"{ctx.guild.icon}")
    embed.set_thumbnail(
        url="https://pluralsight.imgix.net/paths/python-7be70baaac.png")

    await ctx.send(embed=embed)


@bot.command()
async def p(ctx, *, search):
    query_string = parse.urlencode({'search_query': search})
    html_content = request.urlopen(
        'http://www.youtube.com/results?' + query_string)
    # print(html_content.read().decode())
    search_results = re.findall(
        'watch\?v=(.{11})', html_content.read().decode('utf-8'))
    # I will put just the first result, you can loop the response to show more results
    url = ('https://www.youtube.com/watch?v=' + search_results[0])
    await ctx.send('https://www.youtube.com/watch?v=' + search_results[0])
    await join(ctx)
    await queue_(ctx, url)
    await play(ctx)


@bot.command(pass_context=True)
async def join(ctx):
    canal = ctx.message.author.voice.channel
    voz = get(bot.voice_clients, guild=ctx.guild)
    if voz and voz.is_connected():
        await voz.move_to(canal)
    else:
        voz = await canal.connect()


@bot.command(pass_context=True)
async def exit(ctx):
    canal = ctx.message.author.voice.channel
    voz = get(bot.voice_clients, guild=ctx.guild)
    await voz.disconnect()


@bot.command(name='loop', help='This command toggles loop mode')
async def loop_(ctx):
    global loop

    if loop:
        await ctx.send('Loop mode is now `False!`')
        loop = False

    else:
        await ctx.send('Loop mode is now `True!`')
        loop = True


@bot.command(pass_context=True)
async def play(ctx):
    global queue
    print(queue)
    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel")
        return

    elif len(queue) == 0:
        await ctx.send('Nothing in your queue! Use `!p` to add a song!')

    else:
        try:
            channel = ctx.message.author.voice.channel
            await channel.connect()
        except:
            pass

    server = ctx.message.guild
    voice_channel = server.voice_client
    while queue:
        try:
            while voice_channel.is_playing() or voice_channel.is_paused():
                await asyncio.sleep(2)
                pass

        except AttributeError:
            pass

        try:
            async with ctx.typing():
                player = await YTDLSource.from_url(queue[0], loop=bot.loop)
                voice_channel.play(player, after=lambda e: print(
                    'Player error: %s' % e) if e else None)

                if loop:
                    queue.append(queue[0])
                del (queue[0])
            await ctx.send('**Now playing:** {}'.format(player.title))
        except:
            break



@bot.command()
async def queue_(ctx, url):
    global queue

    queue.append(url)
    await ctx.send(f'`{url}` added to queue!')


@bot.command()
async def remove(ctx, number):
    global queue

    try:
        del (queue[int(number)])
        await ctx.send(f'Your queue is now `{queue}!`')

    except:
        await ctx.send('Your queue is either **empty** or the index is **out of range**')


@bot.command(pass_context=True)
async def pause(ctx):
    voz = get(bot.voice_clients, guild=ctx.guild)
    if voz and voz.is_playing():
        print("Musica pausada")
        voz.pause()
        await ctx.send("Musica Pausada")
    else:
        print("No se esta Reproduciendo,Pausa erronea")
        await ctx.send("Pausa Erronea, no se esta Reproduciendo")


@bot.command(pass_context=True)
async def resume(ctx):
    voz = get(bot.voice_clients, guild=ctx.guild)
    if voz and voz.is_paused():
        print("Reproduciendo Nuevamente")
        voz.resume()
        await ctx.send("Reproduciendo Nuevamente")
    else:
        print("No se encuentra pausada")
        await ctx.send("No se encuentra pausada")


@bot.command(pass_context=True)
async def stop(ctx):
    voz = get(bot.voice_clients, guild=ctx.guild)
    if voz and voz.is_playing():
        print("Musica detenida")
        voz.stop()
        await ctx.send("Musica detenida")
    else:
        print("No se esta reproduciendo")
        await ctx.send("No se esta reproduciendo")


@bot.command()
async def volume(ctx, volume: int):
    if ctx.voice_client is None:
        return await ctx.send("Not connected to a voice channel.")

    ctx.voice_client.source.volume = volume / 100
    await ctx.send(f"Volume cambiado a {volume}%")


class NoMoreTracks(Exception):
    pass


@bot.command()
async def next(ctx):
    voz = get(bot.voice_clients, guild=ctx.guild)

    if not voz.is_playing():
        raise NoMoreTracks

    voz.stop()
    await ctx.send("Siguiente cancion")


@bot.command()
async def coinflip(ctx):
    if choice(["cara", "cruz"]) == "cara":
        await ctx.send("Salió cara! :orange_circle:")
    else:
        await ctx.send("Salió cruz! :yellow_circle:")


@bot.command()
async def clear(ctx, amount=10000):
    await ctx.channel.purge(limit=amount)
    await ctx.send("Messages have been cleared")


@bot.command()
async def view(ctx):
    await ctx.send(f' `{queue}` agregada a la lista')


# Events
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(choice(status)))
    print('Estoy en linea my friend')

@tasks.loop(seconds=20)
async def change_status():
    await bot.change_presence(activity=discord.Game(choice(status)))


@bot.event
async def on_member_join(member):
    await member.create_dm()
    await member.dm_channel.send(
        f'Hi {member.name}, Welcome to Chofus!'
    )


#CHAT GPT
@bot.command()
async def chat(ctx, *, message: str):
    # Limpia el mensaje de cualquier ruido y detención de palabras
    message = message.lower()

    # Envía el mensaje al modelo de GPT-3 y obtén la respuesta
    response = openai.Completion.create(model="text-davinci-002", prompt=message, max_tokens=2032, n=1, stop=None, temperature=0.2)


    # Filtra la respuesta para asegurarse de que sea coherente
    answer = re.sub('[^A-Za-z0-9áéíóúñ¿?¡!.,;: ]+', '', response.choices[0].text)
    if len(answer) > 2000:
        answer = answer[:2000] # Limita la respuesta a los primeros 2000 caracteres

    # Envía la respuesta al canal de Discord
    await ctx.send(answer)




bot.run('Token Discord')