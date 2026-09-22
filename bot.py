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
PLATFORM = "pc"

# 5 Minuten
UPDATE_INTERVAL = 300

message_id = None

intents = discord.Intents.default()
client = discord.Client(intents=intents)


# =========================
# PREIS ABRUFEN
# =========================

async def get_kika_price():

    headers = {
        "X-API-Key": PARSE_API_KEY,
        "Accept": "application/json",
    }

    params = {
        "page": 1,
        "platform": PLATFORM,
        "min_rating": PLAYER_RATING,
        "max_rating": PLAYER_RATING,
    }

    async with aiohttp.ClientSession() as session:

        async with session.get(
            API_URL,
            headers=headers,
            params=params,
            timeout=30,
        ) as response:

            if response.status != 200:
                print(
                    f"API Fehler: HTTP {response.status}"
                )
                print(await response.text())
                return None

            data = await response.json()

    players = data.get("data", {}).get("players", [])

    for player in players:

        if (
            player.get("name") == PLAYER_NAME
            and player.get("rating") == PLAYER_RATING
        ):
            return player.get("price")

    print("Kika Nazareth wurde nicht gefunden.")

    return None


# =========================
# DISCORD NACHRICHT
# =========================

def create_message(price):

    if price is None:

        price_text = "❌ Preis nicht verfügbar"

    else:

        price_text = (
            f"{price:,} Coins"
            .replace(",", ".")
        )

    current_time = datetime.now().strftime(
        "%d.%m.%Y %H:%M"
    )

    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🇵🇹 **Kika Nazareth**\n\n"
        "⭐ **83 GES • CM**\n"
        "🔵 FC Barcelona\n"
        "💻 PC\n\n"
        f"💰 **{price_text}**\n\n"
        f"🔄 Aktualisiert: `{current_time}`\n"
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

        print("❌ Discord Channel nicht gefunden.")

        return

    price = await get_kika_price()

    print(
        f"Kika Nazareth PC Preis: {price}"
    )

    content = create_message(price)

    # Alte Nachricht bearbeiten
    if message_id is not None:

        try:

            message = await channel.fetch_message(
                message_id
            )

            await message.edit(
                content=content
            )

            print("✅ Discord Nachricht aktualisiert.")

            return

        except discord.NotFound:

            print(
                "Alte Nachricht nicht gefunden."
            )

            message_id = None

        except discord.HTTPException as error:

            print(
                f"Discord Fehler: {error}"
            )

    # Falls keine Nachricht existiert:
    message = await channel.send(
        content
    )

    message_id = message.id

    print(
        f"✅ Neue Nachricht erstellt: {message.id}"
    )


# =========================
# BOT START
# =========================

@client.event
async def on_ready():

    print(
        f"🤖 Bot online als {client.user}"
    )

    if not update_price.is_running():

        update_price.start()


client.run(DISCORD_TOKEN)
