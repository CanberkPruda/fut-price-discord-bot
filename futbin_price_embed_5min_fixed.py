import os
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp
import discord


# ============================================================
# KONFIGURATION
# ============================================================

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
SLUG = "player"

BANNER_URL = (
    "https://raw.githubusercontent.com/"
    "CanberkPruda/fut-price-discord-bot/"
    "main/bannereafc27.png"
)

BERLIN_TZ = ZoneInfo("Europe/Berlin")

# Datei für die 12-Stunden-Preishistorie
HISTORY_FILE = "price_history.json"

# 12 Stunden in Sekunden
HISTORY_SECONDS = 12 * 60 * 60


# ============================================================
# FUTBIN PREIS ABFRAGEN
# ============================================================

async def get_futbin_price(session):

    headers = {
        "X-API-Key": PARSE_API_KEY
    }

    params = {
        "slug": SLUG,
        "player_id": PLAYER_ID,
        "year": YEAR
    }

    print("🔎 Frage FUTBIN ab...")
    print(f"   Player ID: {PLAYER_ID}")
    print(f"   Year: {YEAR}")

    try:

        async with session.get(
            FUTBIN_URL,
            headers=headers,
            params=params
        ) as response:

            print(f"🌐 FUTBIN HTTP Status: {response.status}")

            if response.status != 200:

                error_text = await response.text()

                print(
                    f"❌ FUTBIN API Fehler: "
                    f"HTTP {response.status}"
                )

                print(error_text)

                return None, None

            data = await response.json()

            print("✅ FUTBIN API Antwort erhalten")

    except Exception as e:

        print(
            f"❌ Fehler bei der FUTBIN-Anfrage: {e}"
        )

        return None, None

    # ========================================================
    # RESPONSE AUSLESEN
    # ========================================================

    player_data = data.get("data", {})

    if not player_data:

        print("❌ 'data' wurde nicht gefunden.")
        print(data)

        return None, None

    print("📦 Player Data gefunden")

    prices = player_data.get("prices", {})

    if not prices:

        print("❌ 'prices' wurde nicht gefunden.")
        print(player_data)

        return None, None

    print("💰 Prices gefunden")

    pc_data = prices.get("pc", {})

    if not pc_data:

        print("❌ 'pc' wurde nicht gefunden.")
        print(prices)

        return None, None

    print(f"💻 PC Daten: {pc_data}")

    price = pc_data.get("price")

    update_age = pc_data.get(
        "updated",
        "Unbekannt"
    )

    print(f"💻 FUTBIN PC Preis: {price}")
    print(f"🕒 FUTBIN Update: {update_age}")

    if price is None:

        print("❌ Kein PC-Preis gefunden.")

        return None, None

    # ========================================================
    # PREIS IN ZAHL UMWANDELN
    # ========================================================

    try:

        price_string = str(price)

        price_string = (
            price_string
            .replace(",", "")
            .replace(".", "")
            .replace(" ", "")
        )

        price = int(price_string)

    except (ValueError, TypeError):

        print(
            f"❌ Preis konnte nicht verarbeitet werden: "
            f"{price}"
        )

        return None, None

    print(
        f"✅ Preis erfolgreich verarbeitet: "
        f"{price} Coins"
    )

    return price, update_age


# ============================================================
# PREIS FORMATIEREN
# ============================================================

def format_price(price):

    return f"{price:,}".replace(",", ".")


# ============================================================
# 12-STUNDEN-HISTORIE LADEN
# ============================================================

def load_price_history():

    if not os.path.exists(HISTORY_FILE):

        print(
            "ℹ️ Noch keine Preishistorie vorhanden."
        )

        return []

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            history = json.load(file)

        if not isinstance(history, list):

            return []

        print(
            f"📚 {len(history)} historische "
            f"Preise geladen."
        )

        return history

    except Exception as e:

        print(
            f"⚠️ Historie konnte nicht geladen "
            f"werden: {e}"
        )

        return []


# ============================================================
# 12-STUNDEN-HISTORIE SPEICHERN
# ============================================================

def save_price_history(history):

    try:

        with open(
            HISTORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                history,
                file,
                ensure_ascii=False,
                indent=2
            )

        print(
            f"💾 Preishistorie gespeichert: "
            f"{len(history)} Einträge"
        )

    except Exception as e:

        print(
            f"⚠️ Historie konnte nicht gespeichert "
            f"werden: {e}"
        )


# ============================================================
# PREIS ZUR HISTORIE HINZUFÜGEN
# ============================================================

def update_price_history(current_price):

    now = int(time.time())

    history = load_price_history()

    # aktuellen Preis hinzufügen
    history.append({
        "timestamp": now,
        "price": current_price
    })

    # Nur die letzten 12 Stunden behalten
    cutoff = now - HISTORY_SECONDS

    history = [
        entry
        for entry in history
        if (
            isinstance(entry, dict)
            and entry.get("timestamp", 0) >= cutoff
            and isinstance(entry.get("price"), (int, float))
        )
    ]

    save_price_history(history)

    return history


# ============================================================
# 12-STUNDEN-HÖCHSTPREIS
# ============================================================

def get_12h_high(history, current_price):

    prices = []

    for entry in history:

        price = entry.get("price")

        if isinstance(price, (int, float)):

            prices.append(int(price))

    # Falls noch keine Historie existiert
    if not prices:

        return current_price

    highest = max(prices)

    return highest


# ============================================================
# DISCORD
# ============================================================

intents = discord.Intents.default()

client = discord.Client(
    intents=intents
)


# ============================================================
# BOT START
# ============================================================

@client.event
async def on_ready():

    print("")
    print("========================================")
    print("🤖 FUT PRICE BOT GESTARTET")
    print("========================================")
    print(f"👤 Bot: {client.user}")
    print("🎯 Player: Kika Nazareth")
    print("💻 Plattform: PC")
    print("🟣 Quelle: FUTBIN")
    print("📈 12h Höchstpreis aktiviert")
    print("========================================")
    print("")

    # ========================================================
    # DISCORD CHANNEL
    # ========================================================

    channel = client.get_channel(CHANNEL_ID)

    if channel is None:

        print(
            "❌ Discord Channel nicht gefunden."
        )

        await client.close()

        return

    print(
        f"✅ Discord Channel gefunden: "
        f"{channel.name}"
    )

    # ========================================================
    # FUTBIN ABFRAGEN
    # ========================================================

    async with aiohttp.ClientSession() as session:

        futbin_price, update_age = (
            await get_futbin_price(session)
        )

    # ========================================================
    # FEHLER
    # ========================================================

    if futbin_price is None:

        print("")
        print(
            "❌ FUTBIN Preis konnte nicht geladen werden."
        )
        print(
            "❌ Discord Nachricht wird NICHT verändert."
        )
        print("")

        await client.close()

        return

    # ========================================================
    # PREISHISTORIE AKTUALISIEREN
    # ========================================================

    history = update_price_history(
        futbin_price
    )

    # ========================================================
    # 12H HÖCHSTPREIS BERECHNEN
    # ========================================================

    high_12h = get_12h_high(
        history,
        futbin_price
    )

    print(
        f"📈 12h Höchstpreis: "
        f"{format_price(high_12h)} Coins"
    )

    # ========================================================
    # BERLIN ZEIT
    # ========================================================

    now_berlin = datetime.now(
        BERLIN_TZ
    )

    formatted_time = now_berlin.strftime(
        "%d.%m.%Y %H:%M"
    )

    footer_time = now_berlin.strftime(
        "%H:%M"
    )

    # ========================================================
    # DISCORD EMBED
    # ========================================================

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

    # ========================================================
    # FUTBIN PREIS
    # ========================================================

    embed.add_field(

        name="💜 FUTBIN",

        value=(
            f"**{format_price(futbin_price)} Coins**"
        ),

        inline=False
    )

    # ========================================================
    # 12H HÖCHSTPREIS
    # ========================================================

    embed.add_field(

        name="📈 12h Höchstpreis",

        value=(
            f"**{format_price(high_12h)} Coins**"
        ),

        inline=False
    )

    # ========================================================
    # FUTBIN DATENALTER
    # ========================================================

    embed.add_field(

        name="🕒 FUTBIN Daten",

        value=f"**{update_age}**",

        inline=True
    )

    # ========================================================
    # LETZTE AKTUALISIERUNG
    # ========================================================

    embed.add_field(

        name="🔄 Letzte Aktualisierung",

        value=(
            f"**{formatted_time} Uhr**"
        ),

        inline=True
    )

    # ========================================================
    # AUTOMATIK
    # ========================================================

    embed.add_field(

        name="⏱️ Automatik",

        value="**Alle 15 Minuten**",

        inline=False
    )

    # ========================================================
    # FOOTER
    # ========================================================

    embed.set_footer(

        text=(
            f"FUT Price Bot • PC Markt • "
            f"heute um {footer_time} Uhr"
        )
    )

    # ========================================================
    # BANNER
    # ========================================================

    embed.set_image(
        url=BANNER_URL
    )

    # ========================================================
    # ALTE KIKA-NACHRICHT SUCHEN
    # ========================================================

    existing_message = None

    print("")
    print(
        "🔎 Suche bestehende Kika-Nachricht..."
    )

    try:

        async for message in channel.history(
            limit=50
        ):

            if message.author != client.user:
                continue

            if not message.embeds:
                continue

            message_embed = message.embeds[0]

            message_title = (
                message_embed.title
                or ""
            )

            if "Kika Nazareth" in message_title:

                existing_message = message

                print(
                    f"✅ Bestehende Nachricht "
                    f"gefunden: {message.id}"
                )

                break

    except Exception as e:

        print(
            f"❌ Fehler bei der Nachrichtensuche: "
            f"{e}"
        )

    # ========================================================
    # DISCORD NACHRICHT AKTUALISIEREN
    # ========================================================

    if existing_message:

        try:

            await existing_message.edit(
                embed=embed
            )

            print("")
            print("========================================")
            print("✅ DISCORD NACHRICHT AKTUALISIERT")
            print("========================================")
            print(
                f"💰 FUTBIN PC: "
                f"{format_price(futbin_price)} Coins"
            )
            print(
                f"📈 12h Hoch: "
                f"{format_price(high_12h)} Coins"
            )
            print(
                f"🕒 FUTBIN: "
                f"{update_age}"
            )
            print(
                f"🔄 Update: "
                f"{formatted_time} Uhr"
            )
            print("========================================")
            print("")

        except Exception as e:

            print(
                f"❌ Discord Nachricht konnte "
                f"nicht bearbeitet werden: {e}"
            )

    # ========================================================
    # NEUE NACHRICHT ERSTELLEN
    # ========================================================

    else:

        try:

            await channel.send(
                embed=embed
            )

            print("")
            print("========================================")
            print("✅ NEUE DISCORD NACHRICHT ERSTELLT")
            print("========================================")
            print(
                f"💰 FUTBIN PC: "
                f"{format_price(futbin_price)} Coins"
            )
            print(
                f"📈 12h Hoch: "
                f"{format_price(high_12h)} Coins"
            )
            print("========================================")
            print("")

        except Exception as e:

            print(
                f"❌ Discord Nachricht konnte "
                f"nicht erstellt werden: {e}"
            )

    # ========================================================
    # BOT BEENDEN
    # ========================================================

    await client.close()


# ============================================================
# START
# ============================================================

client.run(DISCORD_TOKEN)
