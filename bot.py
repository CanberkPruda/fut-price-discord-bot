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

PARSE_URL = (
    "https://api.parse.bot/"
    "scraper/a1271aad-bcbf-4464-8762-47f1d15efa81/"
    "list_players"
)

DISCORD_API = "https://discord.com/api/v10"

PLAYER_NAME = "Kika Nazareth"
PLAYER_RATING = 83
PLAYER_POSITION = "CM"
PLAYER_CLUB = "FC Barcelona"
PLAYER_CARD_TYPE = "Gold Rare"


# ============================================================
# FUT.GG / PARSE PREIS ABRUFEN
# ============================================================

async def get_kika():

    headers = {
        "X-API-Key": PARSE_API_KEY,
        "Accept": "application/json",
    }

    params = {
        "page": 1,
        "platform": "pc",
        "max_rating": 83,
        "min_rating": 83,
    }

    async with aiohttp.ClientSession() as session:

        async with session.get(
            PARSE_URL,
            headers=headers,
            params=params,
            timeout=30,
        ) as response:

            print(f"Parse API HTTP Status: {response.status}")

            if response.status != 200:
                print(await response.text())
                return None

            data = await response.json()

    players = data.get("data", {}).get("players", [])

    print(f"Gefundene 83er Karten: {len(players)}")

    for player in players:

    name = str(player.get("name", "")).strip()
    rating = player.get("rating")

    if (
        name.lower() == "kika nazareth"
        and int(rating) == 83
    ):
        print(
            f"✅ Kika gefunden: "
            f"{player.get('price')} Coins"
        )

        print(
            f"Karte: {player.get('position')} | "
            f"{player.get('club')} | "
            f"{player.get('card_type')}"
        )

        return player

print("❌ Kika Nazareth nicht gefunden.")

print("Gefundene Spieler auf dieser Seite:")

for player in players:
    print(
        player.get("name"),
        player.get("rating"),
        player.get("price")
    )

return None
    print("❌ Kika Nazareth wurde nicht gefunden.")

    return None


# ============================================================
# DISCORD NACHRICHT
# ============================================================

def create_message(player):

    current_time = datetime.now(
        timezone.utc
    ).strftime("%d.%m.%Y %H:%M UTC")

    if player is None:

        price_text = "❌ Preis nicht verfügbar"

    else:

        price = player.get("price")

        if price is None:
            price_text = "❌ Preis nicht verfügbar"
        else:
            price_text = f"{price:,} Coins".replace(",", ".")

    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🇵🇹 **Kika Nazareth — 83 GES**\n\n"
        "⭐ **CM • Gold Rare**\n"
        "🔵 FC Barcelona\n"
        "💻 **PC Markt**\n\n"
        f"💰 **{price_text}**\n\n"
        f"🔄 Aktualisiert: `{current_time}`\n"
        "⏱️ Automatische Aktualisierung alle **5 Minuten**\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


# ============================================================
# DISCORD NACHRICHT SUCHEN / AKTUALISIEREN
# ============================================================

async def update_discord(message_content):

    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "KikaPriceBot/1.0",
    }

    channel_url = (
        f"{DISCORD_API}/channels/"
        f"{CHANNEL_ID}/messages?limit=100"
    )

    async with aiohttp.ClientSession() as session:

        # ----------------------------------------------------
        # Vorhandene Nachrichten abrufen
        # ----------------------------------------------------

        async with session.get(
            channel_url,
            headers=headers,
        ) as response:

            print(
                f"Discord GET Status: {response.status}"
            )

            if response.status != 200:

                print(await response.text())

                return False

            messages = await response.json()

        # ----------------------------------------------------
        # Unsere Kika-Nachricht suchen
        # ----------------------------------------------------

        existing_message = None

        for message in messages:

            author = message.get("author", {})

            if (
                author.get("bot") is True
                and "Kika Nazareth" in message.get(
                    "content",
                    ""
                )
            ):

                existing_message = message

                break

        # ----------------------------------------------------
        # Vorhandene Nachricht bearbeiten
        # ----------------------------------------------------

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

                print(
                    f"Discord PATCH Status: {response.status}"
                )

                if response.status == 200:

                    print(
                        "✅ Bestehende Discord-Nachricht aktualisiert."
                    )

                    return True

                print(await response.text())

                return False

        # ----------------------------------------------------
        # Noch keine Nachricht vorhanden → neue erstellen
        # ----------------------------------------------------

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

            print(
                f"Discord POST Status: {response.status}"
            )

            if response.status in (200, 201):

                print(
                    "✅ Neue Discord-Nachricht erstellt."
                )

                return True

            print(await response.text())

            return False


# ============================================================
# HAUPTPROGRAMM
# ============================================================

async def main():

    print("========================================")
    print("🇵🇹 Kika Nazareth Price Bot")
    print("========================================")

    print(
        f"Spieler: {PLAYER_NAME}"
    )

    print(
        f"Rating: {PLAYER_RATING}"
    )

    print(
        f"Markt: PC"
    )

    print(
        f"Channel ID: {CHANNEL_ID}"
    )

    print("----------------------------------------")

    # Preis abrufen
    player = await get_kika()

    # Discord Nachricht erstellen
    message = create_message(player)

    print("----------------------------------------")

    print(message)

    print("----------------------------------------")

    # Discord aktualisieren
    success = await update_discord(
        message
    )

    print("----------------------------------------")

    if success:

        print(
            "✅ Preis erfolgreich aktualisiert."
        )

    else:

        print(
            "❌ Discord konnte nicht aktualisiert werden."
        )

    print("========================================")


if __name__ == "__main__":

    asyncio.run(main())
