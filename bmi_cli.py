"""
BMI Calculator - Command Line Version
======================================
Prompts for weight and height, calculates BMI,
and classifies it with health advice.
"""


def get_float_input(prompt: str, min_val: float, max_val: float) -> float:
    """Prompt user for a float within a valid range, retry on bad input."""
    while True:
        try:
            value = float(input(prompt))
            if min_val <= value <= max_val:
                return value
            print(f"  ⚠  Please enter a value between {min_val} and {max_val}.")
        except ValueError:
            print("  ⚠  Invalid input. Please enter a numeric value.")


def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """Return BMI rounded to two decimal places."""
    return round(weight_kg / (height_m ** 2), 2)


def classify_bmi(bmi: float) -> dict:
    """Return category, emoji, and a short health note for a given BMI."""
    if bmi < 18.5:
        return {
            "category": "Underweight",
            "emoji": "🔵",
            "note": "Consider consulting a dietitian to gain weight healthily.",
        }
    elif bmi < 25.0:
        return {
            "category": "Normal weight",
            "emoji": "🟢",
            "note": "Great! Maintain your healthy lifestyle.",
        }
    elif bmi < 30.0:
        return {
            "category": "Overweight",
            "emoji": "🟡",
            "note": "A balanced diet and regular exercise can help.",
        }
    elif bmi < 35.0:
        return {
            "category": "Obese (Class I)",
            "emoji": "🟠",
            "note": "Consider speaking with a healthcare provider.",
        }
    elif bmi < 40.0:
        return {
            "category": "Obese (Class II)",
            "emoji": "🔴",
            "note": "Medical guidance is strongly recommended.",
        }
    else:
        return {
            "category": "Obese (Class III)",
            "emoji": "🔴",
            "note": "Please seek immediate medical advice.",
        }


def draw_bmi_bar(bmi: float) -> str:
    """Return a simple ASCII bar showing where the BMI falls (10–45 scale)."""
    low, high = 10.0, 45.0
    bar_width = 40
    position = int((min(bmi, high) - low) / (high - low) * bar_width)
    bar = ["-"] * bar_width
    bar[position] = "▲"
    segments = "".join(bar)
    return (
        f"  Underweight|Normal|Overweight|Obese\n"
        f"  [{segments}]\n"
        f"  10{' ' * (bar_width - 4)}45"
    )


def main():
    print("=" * 50)
    print("        🏃  BMI CALCULATOR  🏃")
    print("=" * 50)

    # ── collect inputs ──────────────────────────────
    weight = get_float_input("\nEnter your weight (kg) [1 – 300]: ", 1, 300)
    height = get_float_input("Enter your height  (m)  [0.5 – 2.5]: ", 0.5, 2.5)

    # ── compute & classify ──────────────────────────
    bmi = calculate_bmi(weight, height)
    info = classify_bmi(bmi)

    # ── display result ──────────────────────────────
    print("\n" + "=" * 50)
    print(f"  Your BMI : {bmi}")
    print(f"  Category : {info['emoji']}  {info['category']}")
    print(f"  Advice   : {info['note']}")
    print()
    print(draw_bmi_bar(bmi))
    print("=" * 50)

    # ── BMI reference table ─────────────────────────
    print("\n  📋  BMI Reference Table")
    print("  ─" * 25)
    rows = [
        ("< 18.5", "Underweight"),
        ("18.5 – 24.9", "Normal weight"),
        ("25.0 – 29.9", "Overweight"),
        ("30.0 – 34.9", "Obese (Class I)"),
        ("35.0 – 39.9", "Obese (Class II)"),
        ("≥ 40.0", "Obese (Class III)"),
    ]
    for rng, cat in rows:
        marker = " ◀  YOU" if cat == info["category"] else ""
        print(f"  {rng:<14}  {cat}{marker}")

    print("\n  Stay healthy! 💪\n")


if __name__ == "__main__":
    main()
