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
PLATFORM = "pc"

# Die Seite, auf der Kika zuletzt gefunden wurde.
# Beim ersten Lauf starten wir auf Seite 1.
PAGE_FILE = "kika_page.txt"

MAX_PAGES = 4


# ============================================================
# LETZTE SEITE LADEN
# ============================================================

def load_last_page():

    try:

        with open(PAGE_FILE, "r") as file:

            page = int(
                file.read().strip()
            )

            if 1 <= page <= MAX_PAGES:
                return page

    except (
        FileNotFoundError,
        ValueError
    ):
        pass

    return 1


# ============================================================
# LETZTE SEITE SPEICHERN
# ============================================================

def save_last_page(page):

    with open(PAGE_FILE, "w") as file:

        file.write(
            str(page)
        )


# ============================================================
# KIKA SUCHEN
# ============================================================

async def get_kika():

    headers = {
        "X-API-Key": PARSE_API_KEY,
        "Accept": "application/json",
    }

    last_page = load_last_page()

    # Zuerst die zuletzt erfolgreiche Seite probieren.
    pages_to_check = [last_page]

    # Falls Kika dort nicht mehr ist,
    # die restlichen Seiten durchsuchen.
    for page in range(1, MAX_PAGES + 1):

        if page not in pages_to_check:

            pages_to_check.append(page)

    async with aiohttp.ClientSession() as session:

        for page in pages_to_check:

            print(
                f"🔎 Suche auf Seite {page}..."
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
                f"{len(players)} Karten"
            )

            # ----------------------------------------
            # Kika suchen
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
                        f"Seite: {page}"
                    )

                    print(
                        f"Preis: {price} Coins"
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
                        "================================"
                    )

                    # Seite für den nächsten Lauf merken.
                    save_last_page(page)

                    return player

            # ----------------------------------------
            # Wenn keine weitere Seite existiert
            # ----------------------------------------

            if api_data.get(
                "next_page"
            ) is None:

                break

    print(
        "❌ Kika Nazareth nicht gefunden."
    )

    return None


# ============================================================
# DISCORD NACHRICHT
# ============================================================

def create_message(player):

    current_time = datetime.now(
        timezone.utc
    ).strftime(
        "%d.%m.%Y %H:%M UTC"
    )

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

        # Bestehende Kika-Nachricht suchen.
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
        # Bestehende Nachricht bearbeiten
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
        # Neue Nachricht erstellen
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
        f"Letzte bekannte Seite: "
        f"{load_last_page()}"
    )

    print(
        "========================================"
    )

    player = await get_kika()

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


if __name__ == "__main__":

    asyncio.run(
        main()
    )
