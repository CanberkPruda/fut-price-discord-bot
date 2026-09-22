import os
import aiohttp
import discord
from discord.ext import tasks
from datetime import datetime

# =========================
# KONFIGURATION
# =========================

DISCORD_TOKEN = os.environ["MTU1MjAyODEzMTYxODIwMTY0Mg.Ge1-Cr.piFEdIET3ZZlkVU6OdJDIj2i7xJ4dK2ZahQHzc"]
CHANNEL_ID = int(os.environ["1552027336323629236"])
PARSE_API_KEY = os.environ["pmx_c82bcd7a"]

API_URL = (
    "https://api.parse.bot/"
    "scraper/a1271aad-bcbf-4464-8762-47f1d15efa81/"
    "list_players"
)

PLAYER_NAME = "Kika Nazareth"
PLAYER_RATING = 83

UPDATE_INTERVAL = 300  # 5 Minuten

intents = discord.Intents.default()
client = discord.Client(intents=intents)

message_id = None


# =========================
# KIKA PREIS ABRUFEN
# =========================

async def get_kika():

    headers = {
        "X-API-Key": PARSE_API_KEY,
        "Accept": "application/json"
    }

    params = {
        "page": 1,
        "platform": "pc",
        "max_rating": 83,
        "min_rating": 83
    }

    async with aiohttp.ClientSession() as session:

        async with session.get(
            API_URL,
            headers=headers,
            params=params,
            timeout=30
        ) as response:

            if response.status != 200:
                print("API Fehler:", response.status)
                print(await response.text())
                return None

            data = await response.json()

    players = data.get("data", {}).get("players", [])

    for player in players:

        if (
            player.get("name") == "Kika Nazareth"
            and player.get("rating") == 83
            and player.get("position") == "CM"
            and player.get("club") == "FC Barcelona"
            and player.get("card_type") == "Gold Rare"
        ):
            return player

    print("Kika Nazareth nicht gefunden.")
    return None


# =========================
# DISCORD NACHRICHT
# =========================

def make_message(player):

    if player is None:

        price_text = "❌ Preis nicht verfügbar"
        update_text = "Fehler beim Abrufen"

    else:

        price = player["price"]

        price_text = f"{price:,} Coins".replace(",", ".")
        update_text = datetime.now().strftime("%d.%m.%Y %H:%M")

    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🇵🇹 **Kika Nazareth — 83 GES**\n\n"
        "⭐ **CM • Gold Rare**\n"
        "🔵 FC Barcelona\n"
        "💻 PC\n\n"
        f"💰 **{price_text}**\n\n"
        f"🔄 Aktualisiert: `{update_text}`\n"
        "⏱️ Update alle **5 Minuten**\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


# =========================
# PREIS AKTUALISIEREN
# =========================

@tasks.loop(seconds=UPDATE_INTERVAL)
async def update_price():

    global message_id

    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("❌ Channel nicht gefunden.")
        return

    player = await get_kika()

    content = make_message(player)

    # Bestehende Nachricht aktualisieren
    if message_id is not None:

        try:

            message = await channel.fetch_message(message_id)

            await message.edit(content=content)

            print("✅ Preis aktualisiert.")

            return

        except discord.NotFound:

            message_id = None

    # Neue Nachricht erstellen
    message = await channel.send(content)

    message_id = message.id

    print("✅ Preisnachricht erstellt.")


# =========================
# BOT START
# =========================

@client.event
async def on_ready():

    print(f"🤖 Bot online: {client.user}")

    if not update_price.is_running():
        update_price.start()


client.run(DISCORD_TOKEN)
