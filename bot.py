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

# Wir suchen auf dem PC-Markt
PLATFORM = "pc"

# Bis zu 4 Seiten durchsuchen
# 30 Karten pro Seite
MAX_PAGES = 4


# ============================================================
# KIKA NAZARETH SUCHEN
# ============================================================

async def get_kika():

    headers = {
        "X-API-Key": PARSE_API_KEY,
        "Accept": "application/json",
    }

    async with aiohttp.ClientSession() as session:

        for page in range(1, MAX_PAGES + 1):

            print(
                f"🔎 Suche Kika auf Seite {page}..."
            )

            params = {
                "page": page,
                "platform": PLATFORM,
                "max_rating": PLAYER_RATING,
                "min_rating": PLAYER_RATING,
            }

            async with session.get(
                PARSE_URL,
                headers=headers,
                params=params,
                timeout=30,
            ) as response:

                print(
                    f"Parse API HTTP Status: "
                    f"{response.status}"
                )

                # API-Fehler
                if response.status != 200:

                    print(
                        await response.text()
                    )

                    return None

                data = await response.json()

            api_data = data.get(
                "data",
                {}
            )

            players = api_data.get(
                "players",
                []
            )

            print(
                f"Seite {page}: "
                f"{len(players)} Karten gefunden."
            )

            # ----------------------------------------
            # Spieler durchsuchen
            # ----------------------------------------

            for player in players:

                name = str(
                    player.get(
                        "name",
                        ""
                    )
                ).strip()

                rating = player.get(
                    "rating"
                )

                # Kika gefunden
                if (
                    name.casefold()
                    == PLAYER_NAME.casefold()
                    and int(rating)
                    == PLAYER_RATING
                ):

                    price = player.get(
                        "price"
                    )

                    print(
                        "================================"
                    )

                    print(
                        "✅ KIKA GEFUNDEN!"
                    )

                    print(
                        f"Name: {name}"
                    )

                    print(
                        f"Rating: {rating}"
                    )

                    print(
                        f"Position: "
                        f"{player.get('position')}"
                    )

                    print(
                        f"Club: "
                        f"{player.get('club')}"
                    )

                    print(
                        f"Card Type: "
                        f"{player.get('card_type')}"
                    )

                    print(
                        f"PC Preis: {price}"
                    )

                    print(
                        "================================"
                    )

                    return player

            # ----------------------------------------
            # Prüfen, ob weitere Seiten existieren
            # ----------------------------------------

            next_page = api_data.get(
                "next_page"
            )

            if next_page is None:

                print(
                    "Keine weiteren Seiten vorhanden."
                )

                break

    print(
        "❌ Kika Nazareth wurde "
        "nicht gefunden."
    )

    return None


# ============================================================
# DISCORD NACHRICHT ERSTELLEN
# ============================================================

def create_message(player):

    current_time = datetime.now(
        timezone.utc
    ).strftime(
        "%d.%m.%Y %H:%M UTC"
    )

    # ----------------------------------------
    # Preis
    # ----------------------------------------

    if player is None:

        price_text = (
            "❌ Preis nicht verfügbar"
        )

    else:

        price = player.get(
            "price"
        )

        if price is None:

            price_text = (
                "❌ Preis nicht verfügbar"
            )

        else:

            price_text = (
                f"{price:,} Coins"
                .replace(",", ".")
            )

    # ----------------------------------------
    # Discord Nachricht
    # ----------------------------------------

    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🇵🇹 **Kika Nazareth — 83 GES**\n\n"
        "⭐ **CM • Gold Rare**\n"
        "🔵 FC Barcelona\n"
        "💻 **PC Markt**\n\n"
        f"💰 **{price_text}**\n\n"
        f"🔄 Aktualisiert: "
        f"`{current_time}`\n"
        "⏱️ Automatische Aktualisierung "
        "alle **5 Minuten**\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


# ============================================================
# DISCORD AKTUALISIEREN
# ============================================================

async def update_discord(
    message_content
):

    headers = {
        "Authorization":
            f"Bot {DISCORD_TOKEN}",

        "Content-Type":
            "application/json",

        "User-Agent":
            "KikaPriceBot/1.0",
    }

    # ----------------------------------------
    # Channel-Nachrichten abrufen
    # ----------------------------------------

    messages_url = (
        f"{DISCORD_API}/channels/"
        f"{CHANNEL_ID}/messages?limit=100"
    )

    async with aiohttp.ClientSession() as session:

        async with session.get(
            messages_url,
            headers=headers,
        ) as response:

            print(
                f"Discord GET Status: "
                f"{response.status}"
            )

            if response.status != 200:

                print(
                    await response.text()
                )

                return False

            messages = await response.json()

        # ----------------------------------------
        # Vorhandene Kika-Nachricht suchen
        # ----------------------------------------

        existing_message = None

        for message in messages:

            author = message.get(
                "author",
                {}
            )

            content = message.get(
                "content",
                ""
            )

            if (
                author.get("bot") is True
                and "Kika Nazareth"
                in content
            ):

                existing_message = message

                break

        # ----------------------------------------
        # Nachricht bearbeiten
        # ----------------------------------------

        if existing_message:

            message_id = (
                existing_message["id"]
            )

            edit_url = (
                f"{DISCORD_API}/channels/"
                f"{CHANNEL_ID}/messages/"
                f"{message_id}"
            )

            async with session.patch(
                edit_url,
                headers=headers,
                json={
                    "content":
                        message_content
                },
            ) as response:

                print(
                    f"Discord PATCH Status: "
                    f"{response.status}"
                )

                if response.status == 200:

                    print(
                        "✅ Discord-Nachricht "
                        "aktualisiert."
                    )

                    return True

                print(
                    await response.text()
                )

                return False

        # ----------------------------------------
        # Noch keine Nachricht vorhanden
        # ----------------------------------------

        create_url = (
            f"{DISCORD_API}/channels/"
            f"{CHANNEL_ID}/messages"
        )

        async with session.post(
            create_url,
            headers=headers,
            json={
                "content":
                    message_content
            },
        ) as response:

            print(
                f"Discord POST Status: "
                f"{response.status}"
            )

            if response.status in (
                200,
                201
            ):

                print(
                    "✅ Discord-Nachricht "
                    "erstellt."
                )

                return True

            print(
                await response.text()
            )

            return False


# ============================================================
# HAUPTPROGRAMM
# ============================================================

async def main():

    print(
        "========================================"
    )

    print(
        "🇵🇹 Kika Nazareth Price Bot"
    )

    print(
        "========================================"
    )

    print(
        f"Spieler: {PLAYER_NAME}"
    )

    print(
        f"Rating: {PLAYER_RATING}"
    )

    print(
        f"Markt: {PLATFORM.upper()}"
    )

    print(
        "========================================"
    )

    # ----------------------------------------
    # Kika abrufen
    # ----------------------------------------

    player = await get_kika()

    # ----------------------------------------
    # Discord Nachricht erstellen
    # ----------------------------------------

    message = create_message(
        player
    )

    print(
        "----------------------------------------"
    )

    print(message)

    print(
        "----------------------------------------"
    )

    # ----------------------------------------
    # Discord aktualisieren
    # ----------------------------------------

    success = await update_discord(
        message
    )

    print(
        "----------------------------------------"
    )

    if success:

        print(
            "✅ Preis erfolgreich "
            "aktualisiert."
        )

    else:

        print(
            "❌ Discord konnte nicht "
            "aktualisiert werden."
        )

    print(
        "========================================"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
