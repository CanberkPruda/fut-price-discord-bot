import os
import asyncio
import aiohttp
import discord
from discord.ext import tasks

# ============================================================
# KONFIGURATION
# ============================================================

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

# Discord Channel ID, in dem die Preisnachricht stehen soll
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

# FUT.GG API
FUT_API_URL = os.environ["FUT_API_URL"]
FUT_API_KEY = os.environ["FUT_API_KEY"]

# Kika Nazareth
PLAYER_ID = "261855"
PLAYER_NAME = "Kika Nazareth"
PLAYER_RATING = 83

# ps = PlayStation / Xbox
# pc = PC
PLATFORM = os.getenv("PLATFORM", "ps")

# Alle 5 Minuten
UPDATE_INTERVAL = 300

# Hier speichern wir die Message-ID
message_id = None


# ============================================================
# DISCORD
# ============================================================

intents = discord.Intents.default()

client = discord.Client(intents=intents)


# ============================================================
# PREIS ABRUFEN
# ============================================================

async def get_price():
    headers = {
        "X-API-Key": FUT_API_KEY,
        "Accept": "application/json"
    }

    params = {
        "page": 1,
        "platform": PLATFORM,
        "min_rating": PLAYER_RATING,
        "max_rating": PLAYER_RATING
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            FUT_API_URL,
            headers=headers,
            params=params,
            timeout=30
        ) as response:

            if response.status != 200:
                print(
                    f"API Fehler: HTTP {response.status}"
                )
                return None

            data = await response.json()

    players = data.get("players", [])

    # Kika anhand Name + Rating finden
    for player in players:
        if (
            player.get("name", "").lower() == PLAYER_NAME.lower()
            and player.get("rating") == PLAYER_RATING
        ):
            return player.get("price")

    print("Kika Nazareth 83 wurde in der API nicht gefunden.")
    return None


# ============================================================
# DISCORD NACHRICHT
# ============================================================

def create_message(price):

    if price is None:
        price_text = "❌ Preis momentan nicht verfügbar"
    else:
        price_text = f"💰 **{price:,} Coins**".replace(",", ".")

    platform_text = "PlayStation / Xbox" if PLATFORM == "ps" else "PC"

    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🇵🇹 **Kika Nazareth — 83 GES**\n\n"
        f"{price_text}\n"
        f"🎮 Markt: **{platform_text}**\n\n"
        "🔄 Automatische Aktualisierung: **5 Minuten**\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


# ============================================================
# PREIS AKTUALISIEREN
# ============================================================

@tasks.loop(seconds=UPDATE_INTERVAL)
async def update_price():

    global message_id

    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("Discord Channel nicht gefunden.")
        return

    price = await get_price()

    content = create_message(price)

    # Existierende Nachricht aktualisieren
    if message_id is not None:

        try:
            message = await channel.fetch_message(message_id)
            await message.edit(content=content)

            print(f"Preis aktualisiert: {price}")

            return

        except discord.NotFound:
            print("Alte Nachricht wurde gelöscht. Erstelle eine neue.")

        except discord.HTTPException as error:
            print(f"Discord Fehler: {error}")

    # Neue Nachricht erstellen
    message = await channel.send(content)

    message_id = message.id

    print(f"Neue Preisnachricht erstellt: {message.id}")


# ============================================================
# BOT START
# ============================================================

@client.event
async def on_ready():

    print(f"Eingeloggt als {client.user}")

    if not update_price.is_running():
        update_price.start()


client.run(DISCORD_TOKEN)
