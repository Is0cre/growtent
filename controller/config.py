from pathlib import Path
import os
from datetime import time

# === Paths ===
ROOT = Path(os.getenv("GROWTENT_ROOT", Path(__file__).resolve().parents[1]))
DATA_DIR = ROOT / "graphs"          # where CSV/images live
LOG_DIR = ROOT / "controller"
CSV_FILE = Path(os.getenv("CSV_FILE", str(ROOT / "grow_tent_data.csv")))  # keep simple
SERVICE_LOG = LOG_DIR / "service.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# === GPIO / Relays (active LOW hats are common) ===
ACTIVE_LOW = True
RELAYS = {
    "Lights":            5,
    "Exhaust Fan":       6,
    "Circulatory Fans": 13,
    "Humidifier":       16,
    "Heater":           19,
    "Dehumidifier":     20,
    "Pump":             21,
    "Aux":              26,
}

# === Schedules / Behavior ===
LIGHTS_ON  = time(6, 0)    # 06:00
LIGHTS_OFF = time(0, 0)    # 00:00 (midnight) -> stay off until 06:00

# Circulatory fans follow lights
CIRC_FANS_FOLLOW_LIGHTS = True

# Exhaust fan policy
TEMP_THRESHOLD_C = float(os.getenv("TEMP_THRESHOLD_C", "28.5"))
BURST_SEC        = int(os.getenv("BURST_SEC", "18"))            # 15–20s
IDLE_BETWEEN_BURSTS_MIN = int(os.getenv("IDLE_BETWEEN_BURSTS_MIN", "7"))
AIR_OUT_RUNS_PER_DAY    = int(os.getenv("AIR_OUT_RUNS_PER_DAY", "3"))
AIR_OUT_BURST_SEC       = int(os.getenv("AIR_OUT_BURST_SEC", str(BURST_SEC)))

# Sensor (BME680)
I2C_SCL = "board.SCL"
I2C_SDA = "board.SDA"
