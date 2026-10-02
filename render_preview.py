"""Render a static Market Momentum preview from the included processed data."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "market_momentum_preview.png"
NAVY = "#17334A"
MUTED = "#456171"
TEAL = "#0A7F86"
GRID = "#DCE8E8"
BG = "#F7F9F9"
WHITE = "#FFFFFF"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)


def main() -> None:
    with (ROOT / "data" / "processed" / "market_month.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    values = [float(row["reported_volume_mn"]) for row in rows]
    dates = [date.fromisoformat(row["date"]) for row in rows]
    apps = [int(row["listed_apps"]) for row in rows]

    im = Image.new("RGB", (1280, 720), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1280, 695), fill=WHITE)
    d.text((43, 26), "UPI Market Analysis", font=font(36, True), fill=NAVY)
    d.text((45, 82), "UPI app transactions from 2022 to 2025", font=font(17), fill=MUTED)
    d.rounded_rectangle((1040, 29, 1228, 105), radius=4, fill=WHITE, outline=GRID, width=2)
    d.text((1055, 38), "Year", font=font(13), fill=MUTED)
    d.text((1055, 61), "2022  –  2025", font=font(18, True), fill=NAVY)

    cards = [
        (45, "TRANSACTIONS · MILLION", f"{sum(values):,.0f}", "Transactions (Mn)"),
        (445, "PEAK MONTH · MILLION", f"{max(values):,.0f}", "Peak Month (Mn)"),
        (845, "AVERAGE LISTED APPS", f"{sum(apps) / len(apps):,.0f}", "Active Apps"),
    ]
    for x, heading, number, caption in cards:
        d.text((x, 130), heading, font=font(13, True), fill=MUTED)
        d.rounded_rectangle((x, 161, x + 350, 265), radius=4, fill=WHITE, outline=GRID, width=2)
        bbox = d.textbbox((0, 0), number, font=font(39))
        d.text((x + (350 - (bbox[2] - bbox[0])) / 2, 175), number, font=font(39), fill=TEAL)
        bbox = d.textbbox((0, 0), caption, font=font(14))
        d.text((x + (350 - (bbox[2] - bbox[0])) / 2, 235), caption, font=font(14), fill=MUTED)

    d.text((45, 294), "Monthly transactions", font=font(22, True), fill=NAVY)
    d.rounded_rectangle((45, 335, 1205, 655), radius=3, fill=WHITE, outline=GRID, width=2)
    x0, y0, x1, y1 = 115, 380, 1170, 605
    max_axis = 25000
    for tick in range(0, max_axis + 1, 5000):
        y = y1 - tick / max_axis * (y1 - y0)
        d.line((x0, y, x1, y), fill=GRID, width=1)
        d.text((62, y - 8), f"{tick // 1000}K", font=font(13), fill=MUTED)
    points = [(x0 + i / (len(values) - 1) * (x1 - x0), y1 - v / max_axis * (y1 - y0))
              for i, v in enumerate(values)]
    d.polygon(points + [(x1, y1), (x0, y1)], fill="#E1F1F0")
    d.line(points, fill=TEAL, width=4, joint="curve")
    for year in range(2022, 2026):
        i = next(i for i, value in enumerate(dates) if value.year == year)
        x = x0 + i / (len(values) - 1) * (x1 - x0)
        d.text((x - 17, 613), str(year), font=font(13), fill=MUTED)
    d.ellipse((points[-1][0] - 5, points[-1][1] - 5,
               points[-1][0] + 5, points[-1][1] + 5), fill=TEAL)
    d.text((47, 671), "Source: NPCI UPI Apps data  •  Transactions shown in millions", font=font(12), fill=MUTED)
    d.rectangle((0, 695, 1280, 720), fill="#EAF2F1")
    d.text((38, 698), "01 | Market Momentum       02 | Competitive Landscape       03 | App Explorer       04 | Monthly Rhythm",
           font=font(13), fill=NAVY)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
