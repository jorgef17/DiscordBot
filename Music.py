import discord
from discord.ext import commands
import asyncio
import yt_dlp
from decouple import config
import os
import random
import pickle

# Intents and settings
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
YDL_OPTIONS = {
    'format': 'bestaudio',
    'noplaylist': 'True',
    'extractaudio': True,
    'audioformat': 'mp3',
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0'
}

QUEUE_FILE = "queue.pkl"

class MusicBot(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.queue = self.load_queue()
        self.current_song = None
        print("MusicBot initialized")

    def save_queue(self):
        """Guarda la cola en un archivo para persistencia."""
        with open(QUEUE_FILE, "wb") as f:
            pickle.dump(self.queue, f)

    def load_queue(self):
        """Carga la cola desde un archivo si existe."""
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, "rb") as f:
                return pickle.load(f)
        return []

    async def play_next(self, ctx):
        if ctx.voice_client is None:
            return  # No hay cliente de voz disponible

        if self.queue:
            url, title = self.queue.pop(0)
            self.save_queue()  # Guardar la cola después de reproducir una canción
            try:
                source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
                if ctx.voice_client:
                    ctx.voice_client.play(
                        source,
                        after=lambda _: self.client.loop.create_task(self.play_next(ctx))
                    )
                    self.current_song = (url, title)  # Actualizar canción actual
                    await ctx.send(f'Now playing **{title}**')
                    print(f'Now playing **{title}**')
                else:
                    print("No voice client available to play the audio.")
            except Exception as e:
                print(f"Error playing audio: {str(e)}")
                await ctx.send(f"Error playing audio: {str(e)}")
        elif not ctx.voice_client.is_playing():
            await ctx.send("Queue is empty!")
            print("Queue is empty!")
            await ctx.voice_client.disconnect()

    @commands.command()
    async def play(self, ctx, *, search):
        print("Received play command")
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not voice_channel:
            return await ctx.send("You're not in a voice channel!")
        if not ctx.voice_client:
            await voice_channel.connect()

        async with ctx.typing():
            try:
                with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                    info = ydl.extract_info(f"ytsearch:{search}", download=False)
                    if 'entries' in info:
                        info = info['entries'][0]
                    url = info['url']
                    title = info['title']
                    self.queue.append((url, title))
                    self.save_queue()  # Guardar la cola después de agregar una canción
                    await ctx.send(f'Added to queue: **{title}**')
                    print(f'Added to queue: **{title}**')
            except Exception as e:
                print(f"Error fetching video: {str(e)}")
                return await ctx.send(f"Error fetching video: {str(e)}")

        if not ctx.voice_client.is_playing():
            await self.play_next(ctx)

    @commands.command()
    async def queue(self, ctx):
        """Muestra la cola de reproducción actual."""
        if self.queue:
            embed = discord.Embed(title="Cola de reproducción", color=discord.Color.green())
            for i, (url, title) in enumerate(self.queue, 1):
                embed.add_field(name=f"{i}.", value=title, inline=False)
            await ctx.send(embed=embed)
            print("Queue:", self.queue)
        else:
            await ctx.send("La cola está vacía.")

    @commands.command()
    async def shuffle(self, ctx):
        """Mezcla la cola de reproducción."""
        if self.queue:
            random.shuffle(self.queue)
            self.save_queue()  # Guardar la cola después de mezclarla
            await ctx.send("La cola ha sido mezclada.")
            print("Queue shuffled")
        else:
            await ctx.send("No hay canciones en la cola para mezclar.")

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Skipped")
            print("Skipped")

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Music paused")
            print("Music paused")

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Music resumed")
            print("Music resumed")

    @commands.command()
    async def exit(self, ctx):
        """Desconecta el bot y guarda la cola de reproducción."""
        if ctx.voice_client:
            # Añadir una canción ficticia al principio de la cola
            dummy_song = ("https://www.example.com/fake.mp3", "Dummy Song")
            self.queue.insert(0, dummy_song)

            # Si hay una canción en reproducción, añádela después de la canción ficticia
            if ctx.voice_client.is_playing() and self.current_song:
                # Asegurarse de que la canción actual no se agregue si ya está en la cola
                if self.current_song not in self.queue:
                    self.queue.insert(1, self.current_song)  # Añadir la canción actual al segundo lugar

            # Guardar la cola antes de desconectar
            self.save_queue()
            await ctx.voice_client.disconnect()
            await ctx.send("Disconnected and saved the queue")
            print("Disconnected and saved the queue")

            # Eliminar la canción ficticia después de guardar la cola
            if self.queue and self.queue[0] == dummy_song:
                self.queue.pop(0)
                self.save_queue()
                print("Removed dummy song from queue")

    @commands.command()
    async def clearq(self, ctx):
        """Limpia la cola de reproducción sin detener la música."""
        self.queue.clear()
        self.save_queue()  # Guardar la cola después de limpiarla
        await ctx.send("La cola de reproducción ha sido limpiada.")
        print("Queue cleared")

    @commands.command()
    async def ping(self, ctx):
        latency = round(self.client.latency * 1000)
        await ctx.send(f'**Pong!** Latency: {latency}ms')

    @commands.command()
    async def clear(self, ctx, amount: int = 100):
        """Borra un número específico de mensajes del chat, hasta 1000."""
        if amount < 1 or amount > 1000:
            await ctx.send("El número de mensajes a borrar debe estar entre 1 y 1000.")
            return
        
        await ctx.channel.purge(limit=amount)
        await ctx.send("Messages have been cleared", delete_after=5)

client = commands.Bot(command_prefix="!", intents=intents)

async def main():
    print("Starting bot...")
    await client.add_cog(MusicBot(client))
    await client.start(config('BOT_TOKEN1'))

asyncio.run(main())

