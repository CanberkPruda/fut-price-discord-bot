import os
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp


# ============================================================
# KONFIGURATION
# ============================================================

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
PARSE_API_KEY = os.environ["PARSE_API_KEY"]

DISCORD_API = "https://discord.com/api/v10"

FUTBIN_API_URL = (
    "https://api.parse.bot/"
    "scraper/21963078-8a17-40ff-a896-9b0b0ec3e828/"
    "get_player_details"
)

FUTGG_API_URL = (
    "https://api.parse.bot/"
    "scraper/a1271aad-bcbf-4464-8762-47f1d15efa81/"
    "list_players"
)

FUTBIN_PLAYER_ID = 506
FUTBIN_YEAR = 27

PLAYER_NAME = "Kika Nazareth"
PLAYER_RATING = 83

FUTGG_MAX_PAGES = 4

# Deutsche Zeit inkl. Sommer-/Winterzeit
BERLIN_TZ = ZoneInfo("Europe/Berlin")


# ============================================================
# PREIS FORMATIEREN
# ============================================================

def format_price(price):
    if price is None:
        return "Preis nicht verfügbar"

    try:
        value = int(
            str(price)
            .replace(",", "")
            .replace(".", "")
            .strip()
        )
        return f"{value:,}".replace(",", ".") + " Coins"
    except (ValueError, TypeError):
        return "Preis nicht verfügbar"


# ============================================================
# FUTBIN
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

    print(f"FUTBIN PC Preis: {price}")
    print(f"FUTBIN Update: {updated}")

    return {
        "price": price,
        "updated": updated,
    }


# ============================================================
# FUT.GG
# ============================================================

async def get_futgg_price(session):
    headers = {
        "X-API-Key": PARSE_API_KEY,
        "Accept": "application/json",
    }

    for page in range(1, FUTGG_MAX_PAGES + 1):

        print(f"FUT.GG: Suche Seite {page}...")

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

            try:
                rating = int(player.get("rating"))
            except (ValueError, TypeError):
                continue

            if (
                name.casefold() == PLAYER_NAME.casefold()
                and rating == PLAYER_RATING
            ):
                price = player.get("price")

                print(f"FUT.GG PC Preis: {price}")

                return {
                    "price": price,
                }

        if api_data.get("next_page") is None:
            break

    print("FUT.GG: Kika nicht gefunden.")
    return None


# ============================================================
# DISCORD EMBED
# ============================================================

def create_embed(futgg, futbin):

    now_berlin = datetime.now(
        BERLIN_TZ
    )

    current_time = now_berlin.strftime(
        "%d.%m.%Y %H:%M Uhr"
    )

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

    return {
        "title": "🇵🇹 Kika Nazareth — 83 GES",
        "description": (
            "⭐ **CM • Gold Rare**\n"
            "🔵 **FC Barcelona**\n"
            "💻 **PC Markt**"
        ),
        "color": 0x00C878,
        "fields": [
            {
                "name": "💰 FUT.GG",
                "value": f"**{futgg_price}**",
                "inline": True,
            },
            {
                "name": "💜 FUTBIN",
                "value": f"**{futbin_price}**",
                "inline": True,
            },
            {
                "name": "🕒 FUTBIN Daten",
                "value": f"`{futbin_updated}`",
                "inline": False,
            },
            {
                "name": "🔄 Letzte Aktualisierung",
                "value": f"`{current_time}`",
                "inline": False,
            },
            {
                "name": "⏱️ Automatik",
                "value": "**Alle 5 Minuten**",
                "inline": False,
            },
        ],
        "footer": {
            "text": "FUT Price Bot • PC Markt"
        },
        "timestamp": now_berlin.isoformat(),
    }
    
"image": {
    "url": "https://raw.githubusercontent.com/CanberkPruda/fut-price-discord-bot/main/bannereafc27.png"
},

# ============================================================
# DISCORD AKTUALISIEREN
# ============================================================

async def update_discord(embed):

    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "KikaCombinedPriceBot/2.0",
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

        # Bestehende Kika-Nachricht suchen.
        for message in messages:

            author = message.get("author", {})
            content = message.get("content", "")

            if (
                author.get("bot") is True
                and "Kika Nazareth" in content
            ):
                existing_message = message
                break

            # Auch bereits vorhandene Embed-Nachricht erkennen
            for old_embed in message.get("embeds", []):
                if "Kika Nazareth" in old_embed.get("title", ""):
                    existing_message = message
                    break

            if existing_message:
                break

        payload = {
            "content": "",
            "embeds": [embed],
        }

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
                json=payload,
            ) as response:

                print(f"Discord PATCH Status: {response.status}")

                if response.status == 200:
                    print("Discord Embed aktualisiert.")
                    return True

                print(await response.text())
                return False

        # Falls keine Nachricht existiert
        create_url = (
            f"{DISCORD_API}/channels/"
            f"{CHANNEL_ID}/messages"
        )

        async with session.post(
            create_url,
            headers=headers,
            json=payload,
        ) as response:

            print(f"Discord POST Status: {response.status}")

            if response.status in (200, 201):
                print("Discord Embed erstellt.")
                return True

            print(await response.text())
            return False


# ============================================================
# MAIN
# ============================================================

async def main():

    print("========================================")
    print("Kika Nazareth • FUT.GG + FUTBIN")
    print("========================================")

    async with aiohttp.ClientSession() as session:

        futgg = await get_futgg_price(session)
        futbin = await get_futbin_price(session)

    embed = create_embed(
        futgg,
        futbin,
    )

    success = await update_discord(embed)

    if success:
        print("OK: Discord erfolgreich aktualisiert.")
    else:
        print("FEHLER: Discord konnte nicht aktualisiert werden.")


if __name__ == "__main__":
    asyncio.run(main())
