"""
========================================
  🌤️  WeatherWise CLI - Weather App
  Local Dataset Edition (No APIs)
========================================
Author  : WeatherWise
Version : 1.0.0
Usage   : python weather_cli.py
========================================
"""

import json
import os
import datetime
from difflib import get_close_matches


# ─────────────────────────────────────────
#  CONSTANTS & FILE PATHS
# ─────────────────────────────────────────
DATA_FILE    = os.path.join(os.path.dirname(__file__), "weather_data.json")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "search_history.json")
MAX_HISTORY  = 10   # max entries kept in history


# ─────────────────────────────────────────
#  CONDITION ICONS (Unicode)
# ─────────────────────────────────────────
CONDITION_ICONS = {
    "sunny":          "☀️ ",
    "clear":          "🌞",
    "partly cloudy":  "⛅",
    "cloudy":         "☁️ ",
    "overcast":       "🌥️ ",
    "rainy":          "🌧️ ",
    "thunderstorm":   "⛈️ ",
    "snowy":          "❄️ ",
    "windy":          "💨",
    "hazy":           "🌫️ ",
    "humid":          "💦",
}

def get_condition_icon(condition: str) -> str:
    """Return a Unicode icon that matches the weather condition."""
    return CONDITION_ICONS.get(condition.lower(), "🌡️")


# ─────────────────────────────────────────
#  DATA LOADING
# ─────────────────────────────────────────
def load_weather_data() -> list[dict]:
    """Load city weather records from the local JSON dataset."""
    if not os.path.exists(DATA_FILE):
        print(f"❌ Dataset not found: {DATA_FILE}")
        raise SystemExit(1)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("cities", [])


# ─────────────────────────────────────────
#  SEARCH & FILTER
# ─────────────────────────────────────────
def search_city(cities: list[dict], query: str) -> dict | None:
    """
    Exact (case-insensitive) search first.
    Returns the city dict or None.
    """
    query = query.strip().lower()
    for city in cities:
        if city["city"].lower() == query:
            return city
    return None


def suggest_cities(cities: list[dict], query: str, n: int = 3) -> list[str]:
    """Return up to n close-match city names using difflib."""
    all_names = [c["city"] for c in cities]
    return get_close_matches(query.strip(), all_names, n=n, cutoff=0.4)


# ─────────────────────────────────────────
#  UNIT CONVERSION
# ─────────────────────────────────────────
def c_to_f(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return round(celsius * 9 / 5 + 32, 1)

def kmh_to_mph(kmh: float) -> float:
    """Convert km/h to mph."""
    return round(kmh * 0.621371, 1)


# ─────────────────────────────────────────
#  SEARCH HISTORY  (JSON file)
# ─────────────────────────────────────────
def load_history() -> list[dict]:
    """Load the recent-search history from disk."""
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history: list[dict]) -> None:
    """Persist the history list (capped at MAX_HISTORY)."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-MAX_HISTORY:], f, indent=2)


def add_to_history(city_name: str, history: list[dict]) -> list[dict]:
    """Prepend a new entry; remove duplicates."""
    history = [h for h in history if h["city"].lower() != city_name.lower()]
    history.insert(0, {
        "city":      city_name,
        "searched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    return history


# ─────────────────────────────────────────
#  DISPLAY HELPERS
# ─────────────────────────────────────────
SEPARATOR = "─" * 46

def print_header() -> None:
    print("\n" + "═" * 46)
    print("  🌤️   W E A T H E R W I S E   C L I  🌤️")
    print("  📂  Offline · Local Dataset · No API")
    print("═" * 46)


def print_weather(data: dict, unit: str = "C") -> None:
    """Render a formatted weather card in the terminal."""
    icon = get_condition_icon(data["condition"])
    city = data["city"]
    country = data["country"]

    # Choose correct units
    if unit == "F":
        temp      = c_to_f(data["temperature_c"])
        feels     = c_to_f(data["feels_like_c"])
        temp_unit = "°F"
        wind      = kmh_to_mph(data["wind_speed_kmh"])
        wind_unit = "mph"
    else:
        temp      = data["temperature_c"]
        feels     = data["feels_like_c"]
        temp_unit = "°C"
        wind      = data["wind_speed_kmh"]
        wind_unit = "km/h"

    print(f"\n  {SEPARATOR}")
    print(f"  📍  {city}, {country}")
    print(f"  {SEPARATOR}")
    print(f"  {icon}  Condition   : {data['condition']}")
    print(f"  🌡️   Temperature : {temp}{temp_unit}  (Feels like {feels}{temp_unit})")
    print(f"  💧  Humidity    : {data['humidity']}%")
    print(f"  🌬️   Wind Speed  : {wind} {wind_unit}")
    print(f"  📊  Pressure    : {data['pressure_hpa']} hPa")
    print(f"  👁️   Visibility  : {data['visibility_km']} km")
    print(f"  {SEPARATOR}\n")


def print_history(history: list[dict]) -> None:
    """Display the recent search history."""
    if not history:
        print("\n  ℹ️  No search history yet.\n")
        return
    print(f"\n  🕘  Recent Searches  ({len(history)} entries)")
    print(f"  {SEPARATOR}")
    for i, h in enumerate(history, 1):
        print(f"  {i:>2}. {h['city']:<22}  🕐 {h['searched_at']}")
    print(f"  {SEPARATOR}\n")


# ─────────────────────────────────────────
#  ADD / UPDATE CITY (manual edit)
# ─────────────────────────────────────────
def add_city_interactive(cities: list[dict]) -> list[dict]:
    """Prompt the user to add or update a city entry."""
    print(f"\n  {SEPARATOR}")
    print("  ✏️   Add / Update City Data")
    print(f"  {SEPARATOR}")
    name = input("  City name       : ").strip().title()
    if not name:
        print("  ⚠️  City name cannot be empty.")
        return cities

    # Check if city already exists → offer update
    existing = search_city(cities, name)
    if existing:
        print(f"  ⚠️  '{name}' already exists. Its values will be updated.")
        cities = [c for c in cities if c["city"].lower() != name.lower()]

    try:
        entry = {
            "city":            name,
            "country":         input("  Country         : ").strip().title() or "Unknown",
            "temperature_c":   float(input("  Temperature (°C): ")),
            "humidity":        int(input("  Humidity (%)    : ")),
            "condition":       input("  Condition       : ").strip().title(),
            "wind_speed_kmh":  float(input("  Wind Speed km/h : ")),
            "feels_like_c":    float(input("  Feels Like (°C) : ")),
            "pressure_hpa":    int(input("  Pressure (hPa)  : ")),
            "visibility_km":   float(input("  Visibility (km) : ")),
        }
    except ValueError:
        print("  ❌  Invalid input — city not added.")
        return cities

    cities.append(entry)

    # Persist to the JSON dataset
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)
    payload["cities"] = cities
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"  ✅  '{name}' saved to dataset!\n")
    return cities


# ─────────────────────────────────────────
#  MAIN APPLICATION LOOP
# ─────────────────────────────────────────
def main() -> None:
    cities  = load_weather_data()
    history = load_history()
    unit    = "C"   # default temperature unit

    print_header()

    while True:
        print("  Options: [S]earch  [H]istory  [U]nit  [A]dd city  [Q]uit")
        choice = input("  ➤ Your choice: ").strip().upper()

        # ── SEARCH ────────────────────────────
        if choice == "S":
            query = input("\n  🔍 Enter city name: ").strip()
            if not query:
                print("  ⚠️  Please enter a city name.\n")
                continue

            result = search_city(cities, query)

            if result:
                print_weather(result, unit)
                history = add_to_history(result["city"], history)
                save_history(history)
            else:
                print(f"\n  ❌  City '{query}' not found in the dataset.")
                suggestions = suggest_cities(cities, query)
                if suggestions:
                    print(f"  💡  Did you mean: {', '.join(suggestions)} ?")
                print()

        # ── HISTORY ───────────────────────────
        elif choice == "H":
            print_history(history)

        # ── UNIT TOGGLE ───────────────────────
        elif choice == "U":
            unit = "F" if unit == "C" else "C"
            symbol = "°F  (Fahrenheit)" if unit == "F" else "°C  (Celsius)"
            print(f"\n  🌡️   Unit switched to {symbol}\n")

        # ── ADD CITY ──────────────────────────
        elif choice == "A":
            cities = add_city_interactive(cities)

        # ── QUIT ──────────────────────────────
        elif choice == "Q":
            print("\n  👋  Thanks for using WeatherWise CLI. Stay dry!\n")
            break

        else:
            print("  ⚠️  Invalid option. Please choose S / H / U / A / Q.\n")


if __name__ == "__main__":
    main()
