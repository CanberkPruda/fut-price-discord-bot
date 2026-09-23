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

# Parse/FUTBIN API
FUTBIN_API_URL = (
    "https://api.parse.bot/"
    "scraper/21963078-8a17-40ff-a896-9b0b0ec3e828/"
    "get_player_details"
)

# Kika Nazareth auf FUTBIN
FUTBIN_PLAYER_ID = 506
FUTBIN_YEAR = 27

PLAYER_NAME = "Kika Nazareth"


# ============================================================
# FUTBIN PREIS ABRUFEN
# ============================================================

async def get_futbin_price():
    headers = {
        "X-API-Key": PARSE_API_KEY,
        "Accept": "application/json",
    }

    params = {
        "player_id": FUTBIN_PLAYER_ID,
        "year": FUTBIN_YEAR,
    }

    async with aiohttp.ClientSession() as session:

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

    # Normaler Preis
    price = pc.get("price")

    # Falls die API-Feldnamen abweichen
    if price is None:
        price = pc.get("current_price")

    if price is None:
        price = data.get("price_pc")

    updated = pc.get("updated")

    print("--------------------------------")
    print("FUTBIN")
    print(f"Spieler: {data.get('name', PLAYER_NAME)}")
    print(f"Rating: {data.get('rating', 83)}")
    print(f"Position: {data.get('position', 'CM')}")
    print(f"PC Preis: {price}")
    print(f"FUTBIN Update: {updated}")
    print("--------------------------------")

    return {
        "name": data.get("name", PLAYER_NAME),
        "rating": data.get("rating", 83),
        "position": data.get("position", "CM"),
        "club": data.get("club", "FC Barcelona"),
        "version": data.get("version", "Gold"),
        "price": price,
        "updated": updated,
    }


# ============================================================
# DISCORD NACHRICHT
# ============================================================

def create_message(player):
    current_time = datetime.now(
        timezone.utc
    ).strftime("%d.%m.%Y %H:%M UTC")

    if player is None or player.get("price") is None:
        price_text = "❌ Preis nicht verfügbar"
    else:
        price = int(player["price"])
        price_text = f"{price:,} Coins".replace(",", ".")

    updated = player.get("updated") if player else None

    updated_text = updated if updated else "nicht angegeben"

    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🇵🇹 **Kika Nazareth — 83 GES**\n\n"
        "⭐ **CM • Gold Rare**\n"
        "🔵 FC Barcelona\n"
        "💻 **PC Markt**\n\n"
        f"💜 **FUTBIN: {price_text}**\n"
        f"🕒 FUTBIN Daten: `{updated_text}`\n\n"
        f"🔄 Aktualisiert: `{current_time}`\n"
        "⏱️ Automatische Aktualisierung alle **7 Minuten**\n"
        "🔗 https://www.futbin.com/27/player/506/francisca-ramos-nazareth-sousa\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


# ============================================================
# DISCORD AKTUALISIEREN
# ============================================================

async def update_discord(message_content):
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "KikaFutbinPriceBot/1.0",
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

        # Eigene FUTBIN-Nachricht suchen.
        # Die bestehende bot.py-Nachricht bleibt unangetastet.
        existing_message = None

        for message in messages:
            author = message.get("author", {})
            content = message.get("content", "")

            if (
                author.get("bot") is True
                and "FUTBIN:" in content
                and "Kika Nazareth" in content
            ):
                existing_message = message
                break

        # Vorhandene FUTBIN-Nachricht bearbeiten
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
                json={"content": message_content},
            ) as response:

                print(f"Discord PATCH Status: {response.status}")

                if response.status == 200:
                    print("✅ FUTBIN-Nachricht aktualisiert.")
                    return True

                print(await response.text())
                return False

        # Noch keine FUTBIN-Nachricht vorhanden -> erstellen
        create_url = (
            f"{DISCORD_API}/channels/"
            f"{CHANNEL_ID}/messages"
        )

        async with session.post(
            create_url,
            headers=headers,
            json={"content": message_content},
        ) as response:

            print(f"Discord POST Status: {response.status}")

            if response.status in (200, 201):
                print("✅ FUTBIN-Nachricht erstellt.")
                return True

            print(await response.text())
            return False


# ============================================================
# HAUPTPROGRAMM
# ============================================================

async def main():
    print("========================================")
    print("🇵🇹 Kika Nazareth FUTBIN Price Bot")
    print("========================================")

    player = await get_futbin_price()
    message = create_message(player)

    print(message)

    success = await update_discord(message)

    if success:
        print("✅ FUTBIN-Preis erfolgreich aktualisiert.")
    else:
        print("❌ Discord konnte nicht aktualisiert werden.")


if __name__ == "__main__":
    asyncio.run(main())
