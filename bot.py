import os
import aiohttp
from datetime import datetime, timezone

# =========================
# KONFIGURATION
# =========================

DISCORD_TOKEN = os.environ["MTU1MjAyODEzMTYxODIwMTY0Mg.Ge1-Cr.piFEdIET3ZZlkVU6OdJDIj2i7xJ4dK2ZahQHzc"]
CHANNEL_ID = os.environ["1552027336323629236"]
PARSE_API_KEY = os.environ["pmx_c82bcd7a"]

PARSE_URL = (
    "https://api.parse.bot/"
    "scraper/a1271aad-bcbf-4464-8762-47f1d15efa81/"
    "list_players"
)

DISCORD_API = "https://discord.com/api/v10"

# =========================
# KIKA ABRUFEN
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
            PARSE_URL,
            headers=headers,
            params=params,
            timeout=30
        ) as response:

            if response.status != 200:
                print("Parse API Fehler:", response.status)
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

    now = datetime.now(timezone.utc)

    if player is None:
        price_text = "❌ Preis nicht verfügbar"
    else:
        price = player["price"]
        price_text = f"{price:,} Coins".replace(",", ".")

    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🇵🇹 **Kika Nazareth — 83 GES**\n\n"
        "⭐ **CM • Gold Rare**\n"
        "🔵 FC Barcelona\n"
        "💻 PC\n\n"
        f"💰 **{price_text}**\n\n"
        f"🔄 Aktualisiert: `{now.strftime('%d.%m.%Y %H:%M')} UTC`\n"
        "⏱️ Update alle **5 Minuten**\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


# =========================
# DISCORD
# =========================

async def update_discord(message):

    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:

        # Letzte 100 Nachrichten des Channels holen
        url = (
            f"{DISCORD_API}/channels/"
            f"{CHANNEL_ID}/messages?limit=100"
        )

        async with session.get(
            url,
            headers=headers
        ) as response:

            if response.status != 200:
                print("Discord Fehler beim Lesen:", response.status)
                print(await response.text())
                return

            messages = await response.json()

        # Unsere bestehende Bot-Nachricht suchen
        existing_message = None

        for msg in messages:

            if (
                msg.get("author", {}).get("bot") is True
                and "Kika Nazareth" in msg.get("content", "")
            ):
                existing_message = msg
                break

        # Nachricht bearbeiten
        if existing_message:

            message_id = existing_message["id"]

            url = (
                f"{DISCORD_API}/channels/"
                f"{CHANNEL_ID}/messages/{message_id}"
            )

            async with session.patch(
                url,
                headers=headers,
                json={"content": message}
            ) as response:

                if response.status == 200:
                    print("✅ Discord Nachricht aktualisiert.")
                else:
                    print("Discord Fehler beim Bearbeiten:")
                    print(response.status)
                    print(await response.text())

        # Falls noch keine Nachricht existiert
        else:

            url = (
                f"{DISCORD_API}/channels/"
                f"{CHANNEL_ID}/messages"
            )

            async with session.post(
                url,
                headers=headers,
                json={"content": message}
            ) as response:

                if response.status in (200, 201):
                    print("✅ Neue Discord Nachricht erstellt.")
                else:
                    print("Discord Fehler beim Erstellen:")
                    print(response.status)
                    print(await response.text())


# =========================
# START
# =========================

async def main():

    player = await get_kika()

    if player:
        print(
            f"Kika Nazareth PC Preis: "
            f"{player['price']} Coins"
        )
    else:
        print("Preis konnte nicht abgerufen werden.")

    message = make_message(player)

    await update_discord(message)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
