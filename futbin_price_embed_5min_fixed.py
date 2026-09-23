import os
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp
import discord


# =========================
# KONFIGURATION
# =========================

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
PARSE_API_KEY = os.environ["PARSE_API_KEY"]

FUTBIN_URL = (
    "https://api.parse.bot/scraper/"
    "21963078-8a17-40ff-a896-9b0b0ec3e828/"
    "get_player_details"
)

PLAYER_ID = "506"
YEAR = "27"

BANNER_URL = (
    "https://raw.githubusercontent.com/"
    "CanberkPruda/fut-price-discord-bot/"
    "main/bannereafc27.png"
)

BERLIN_TZ = ZoneInfo("Europe/Berlin")


# =========================
# FUTBIN PREIS HOLEN
# =========================

async def get_futbin_price(session):
    headers = {
        "X-API-Key": PARSE_API_KEY
    }

    params = {
        "player_id": PLAYER_ID,
        "year": YEAR
    }

    async with session.get(
        FUTBIN_URL,
        headers=headers,
        params=params
    ) as response:

        if response.status != 200:
            print(f"❌ FUTBIN API Fehler: HTTP {response.status}")
            print(await response.text())
            return None, None

        data = await response.json()

        print("✅ FUTBIN Daten erhalten")

        player = data

        if isinstance(data, dict) and isinstance(data.get("player"), dict):
            player = data["player"]

        price = player.get("price")

        if price is None:
            print("❌ Kein FUTBIN Preis gefunden.")
            print(data)
            return None, None

        try:
            price = int(
                str(price)
                .replace(",", "")
                .replace(".", "")
                .replace(" ", "")
            )
        except ValueError:
            print(f"❌ Preis konnte nicht gelesen werden: {price}")
            return None, None

        update_age = (
            player.get("updated")
            or player.get("update")
            or player.get("last_updated")
            or player.get("updated_at")
            or "Unbekannt"
        )

        return price, update_age


# =========================
# PREIS FORMATIEREN
# =========================

def format_price(price):
    return f"{price:,}".replace(",", ".")


# =========================
# DISCORD BOT
# =========================

intents = discord.Intents.default()
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"🤖 Eingeloggt als {client.user}")

    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("❌ Discord Channel nicht gefunden.")
        await client.close()
        return

    async with aiohttp.ClientSession() as session:
        futbin_price, update_age = await get_futbin_price(session)

    if futbin_price is None:
        print("❌ FUTBIN Preis konnte nicht geladen werden.")
        await client.close()
        return

    # =========================
    # BERLIN ZEIT
    # =========================

    now_berlin = datetime.now(BERLIN_TZ)

    formatted_time = now_berlin.strftime("%d.%m.%Y %H:%M")
    footer_time = now_berlin.strftime("%H:%M")

    # =========================
    # EMBED
    # =========================

    embed = discord.Embed(
        title="🇵🇹 Kika Nazareth — 83 GES",
        description=(
            "⭐ **CM • Gold Rare**\n"
            "🔵 **FC Barcelona**\n"
            "💻 **PC Markt**"
        ),
        color=0x00FF7F,
        timestamp=now_berlin
    )

    embed.add_field(
        name="💜 FUTBIN",
        value=f"**{format_price(futbin_price)} Coins**",
        inline=False
    )

    embed.add_field(
        name="🕒 FUTBIN Daten",
        value=f"**{update_age}**",
        inline=True
    )

    embed.add_field(
        name="🔄 Letzte Aktualisierung",
        value=f"**{formatted_time} Uhr**",
        inline=True
    )

    embed.add_field(
        name="⏱️ Automatik",
        value="**Alle 15 Minuten**",
        inline=False
    )

    embed.set_footer(
        text=f"FUT Price Bot • PC Markt • heute um {footer_time} Uhr"
    )

    embed.set_image(url=BANNER_URL)

    # =========================
    # ALTE KIKA-NACHRICHT SUCHEN
    # =========================

    existing_message = None

    try:
        async for message in channel.history(limit=50):

            if message.author == client.user:

                if message.embeds:

                    embed_title = message.embeds[0].title or ""

                    if "Kika Nazareth" in embed_title:
                        existing_message = message
                        break

    except Exception as e:
        print(f"⚠️ Fehler beim Durchsuchen des Channels: {e}")

    # =========================
    # NACHRICHT AKTUALISIEREN
    # =========================

    if existing_message:

        await existing_message.edit(embed=embed)

        print(
            f"✅ Kika Preis aktualisiert: "
            f"{format_price(futbin_price)} Coins"
        )

    else:

        await channel.send(embed=embed)

        print(
            f"✅ Neue Kika Nachricht erstellt: "
            f"{format_price(futbin_price)} Coins"
        )

    await client.close()


client.run(DISCORD_TOKEN)
