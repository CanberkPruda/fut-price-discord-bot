import os
import asyncio
from datetime import datetime, timezone

import aiohttp


# ============================================================
# KONFIGURATION
# ============================================================

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
PARSE_API_KEY = os.environ["PARSE_API_KEY"]

DISCORD_API = "https://discord.com/api/v10"

# ------------------------------------------------------------
# FUTBIN / Parse
# ------------------------------------------------------------

FUTBIN_API_URL = (
    "https://api.parse.bot/"
    "scraper/21963078-8a17-40ff-a896-9b0b0ec3e828/"
    "get_player_details"
)

FUTBIN_PLAYER_ID = 506
FUTBIN_YEAR = 27

# ------------------------------------------------------------
# FUT.GG / Parse
# Gleiche API wie in bot.py
# ------------------------------------------------------------

FUTGG_API_URL = (
    "https://api.parse.bot/"
    "scraper/a1271aad-bcbf-4464-8762-47f1d15efa81/"
    "list_players"
)

FUTGG_MAX_PAGES = 4

PLAYER_NAME = "Kika Nazareth"
PLAYER_RATING = 83


# ============================================================
# HILFSFUNKTION: PREIS FORMATIEREN
# ============================================================

def format_price(price):
    if price is None:
        return "❌ Preis nicht verfügbar"

    try:
        # Unterstützt z.B. 75000, "75000" und "75,000"
        value = int(
            str(price)
            .replace(",", "")
            .replace(".", "")
            .strip()
        )
        return f"{value:,}".replace(",", ".") + " Coins"

    except (ValueError, TypeError):
        return "❌ Preis nicht verfügbar"


# ============================================================
# FUTBIN PREIS
# ============================================================

async def get_futbin_price(session):
    headers = {
        "X-API-Key": PARSE_API_KEY,
        "Accept": "application/json",
    }

    params = {
        "player_id": FUTBIN_PLAYER_ID,
        "year": FUTBIN_YEAR,
    }

    async with session.get(
        FUTBIN_API_URL,
        headers=headers,
        params=params,
        timeout=30,
    ) as response:

        print(f"FUTBIN API HTTP Status: {response.status}")

        if response.status != 200:
            print(await response.text())
            return None

        payload = await response.json()

    data = payload.get("data", payload)

    prices = data.get("prices", {})
    pc = prices.get("pc", {})

    price = pc.get("price")

    if price is None:
        price = pc.get("current_price")

    if price is None:
        price = data.get("price_pc")

    updated = pc.get("updated")

    print("--------------------------------")
    print("FUTBIN")
    print(f"Spieler: {data.get('name', PLAYER_NAME)}")
    print(f"Rating: {data.get('rating', PLAYER_RATING)}")
    print(f"Position: {data.get('position', 'CM')}")
    print(f"PC Preis: {price}")
    print(f"FUTBIN Update: {updated}")
    print("--------------------------------")

    return {
        "price": price,
        "updated": updated,
    }


# ============================================================
# FUT.GG PREIS
# ============================================================

async def get_futgg_price(session):
    headers = {
        "X-API-Key": PARSE_API_KEY,
        "Accept": "application/json",
    }

    for page in range(1, FUTGG_MAX_PAGES + 1):

        print(f"🔎 FUT.GG: Suche Kika auf Seite {page}...")

        params = {
            "page": page,
            "platform": "pc",
            "max_rating": PLAYER_RATING,
            "min_rating": PLAYER_RATING,
        }

        async with session.get(
            FUTGG_API_URL,
            headers=headers,
            params=params,
            timeout=30,
        ) as response:

            print(f"FUT.GG API HTTP Status: {response.status}")

            if response.status != 200:
                print(await response.text())
                return None

            data = await response.json()

        api_data = data.get("data", {})
        players = api_data.get("players", [])

        for player in players:

            name = str(player.get("name", "")).strip()

            rating = player.get("rating")

            try:
                rating = int(rating)
            except (ValueError, TypeError):
                continue

            if (
                name.casefold() == PLAYER_NAME.casefold()
                and rating == PLAYER_RATING
            ):
                price = player.get("price")

                print("--------------------------------")
                print("FUT.GG")
                print(f"Spieler: {name}")
                print(f"PC Preis: {price}")
                print("--------------------------------")

                return {
                    "price": price,
                }

        if api_data.get("next_page") is None:
            break

    print("❌ FUT.GG: Kika nicht gefunden.")
    return None


# ============================================================
# EINE GEMEINSAME DISCORD-NACHRICHT
# ============================================================

def create_message(futgg, futbin):
    current_time = datetime.now(
        timezone.utc
    ).strftime("%d.%m.%Y %H:%M UTC")

    futgg_price = format_price(
        futgg.get("price") if futgg else None
    )

    futbin_price = format_price(
        futbin.get("price") if futbin else None
    )

    futbin_updated = (
        futbin.get("updated")
        if futbin and futbin.get("updated")
        else "nicht angegeben"
    )

    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🇵🇹 **Kika Nazareth — 83 GES**\n\n"
        "⭐ **CM • Gold Rare**\n"
        "🔵 FC Barcelona\n"
        "💻 **PC Markt**\n\n"
        f"💰 **FUT.GG: {futgg_price}**\n"
        f"💜 **FUTBIN: {futbin_price}**\n"
        f"🕒 FUTBIN Daten: `{futbin_updated}`\n\n"
        f"🔄 Aktualisiert: `{current_time}`\n"
        "⏱️ Automatische Aktualisierung alle **7 Minuten**\n"
        "🔗 https://www.futbin.com/27/player/506/francisca-ramos-nazareth-sousa\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


# ============================================================
# DISCORD: VORHANDENE KIKA-NACHRICHT BEARBEITEN
# ============================================================

async def update_discord(message_content):
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "KikaCombinedPriceBot/1.0",
    }

    messages_url = (
        f"{DISCORD_API}/channels/"
        f"{CHANNEL_ID}/messages?limit=100"
    )

    async with aiohttp.ClientSession() as session:

        async with session.get(
            messages_url,
            headers=headers,
        ) as response:

            print(f"Discord GET Status: {response.status}")

            if response.status != 200:
                print(await response.text())
                return False

            messages = await response.json()

        existing_message = None

        # Die von bot.py erstellte Kika-Nachricht suchen.
        # FUTBIN-Nachrichten mit eigenem Link werden ignoriert.
        for message in messages:

            author = message.get("author", {})
            content = message.get("content", "")

            if (
                author.get("bot") is True
                and "Kika Nazareth" in content
                and "FC Barcelona" in content
            ):
                existing_message = message
                break

        if existing_message:

            message_id = existing_message["id"]

            edit_url = (
                f"{DISCORD_API}/channels/"
                f"{CHANNEL_ID}/messages/"
                f"{message_id}"
            )

            async with session.patch(
                edit_url,
                headers=headers,
                json={
                    "content": message_content
                },
            ) as response:

                print(f"Discord PATCH Status: {response.status}")

                if response.status == 200:
                    print("✅ Gemeinsame Kika-Nachricht aktualisiert.")
                    return True

                print(await response.text())
                return False

        # Falls keine Kika-Nachricht vorhanden ist, erstellen.
        create_url = (
            f"{DISCORD_API}/channels/"
            f"{CHANNEL_ID}/messages"
        )

        async with session.post(
            create_url,
            headers=headers,
            json={
                "content": message_content
            },
        ) as response:

            print(f"Discord POST Status: {response.status}")

            if response.status in (200, 201):
                print("✅ Gemeinsame Kika-Nachricht erstellt.")
                return True

            print(await response.text())
            return False


# ============================================================
# HAUPTPROGRAMM
# ============================================================

async def main():

    print("========================================")
    print("🇵🇹 Kika Nazareth Combined Price Bot")
    print("========================================")

    async with aiohttp.ClientSession() as session:

        # Beide Quellen abrufen
        futgg = await get_futgg_price(session)
        futbin = await get_futbin_price(session)

    message = create_message(
        futgg,
        futbin,
    )

    print("----------------------------------------")
    print(message)
    print("----------------------------------------")

    success = await update_discord(
        message
    )

    if success:
        print("✅ Beide Preise in einer Nachricht aktualisiert.")
    else:
        print("❌ Discord konnte nicht aktualisiert werden.")

    print("========================================")


if __name__ == "__main__":
    asyncio.run(main())
