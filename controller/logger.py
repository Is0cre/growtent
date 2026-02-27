from __future__ import annotations
from datetime import datetime
from pathlib import Path

HEADERS = [
    "Timestamp","Temperature (°C)","Humidity (%)","Pressure (hPa)","Gas Resistance (Ohms)",
    "Lights State","Fan State","Humidifier State","Heater State","Dehumidifier State","Pump State"
]

def append_csv(path: Path, row: list[str|float|None]):
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        if not exists:
            f.write(",".join(HEADERS) + "\n")
        f.write(",".join("" if v is None else str(v) for v in row) + "\n")

def stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def append_service_line(path: Path, line: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")
