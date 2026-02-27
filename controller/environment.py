from __future__ import annotations
import threading, time
from datetime import datetime, time as dtime
from .config import *
from .relays import RelayBoard
from .sensors import read_bme680
from .logger import append_csv, append_service_line, stamp

def in_light_period(now: datetime) -> bool:
    t = now.time()
    if LIGHTS_OFF <= t < LIGHTS_ON:
        return False
    return True

class Controller:
    def __init__(self):
        self.rb = RelayBoard(RELAYS, ACTIVE_LOW)
        self.last_air_out_day = None
        self.air_out_runs_done = 0
        self._stop = threading.Event()

    def stop(self): self._stop.set()

    def set_state(self, name: str, on: bool):
        (self.rb.on if on else self.rb.off)(name)

    def log_states(self, temp, hum, pres, gas):
        row = [
            stamp(), temp, hum, pres, gas,
            self.rb.state("Lights"),
            self.rb.state("Exhaust Fan"),
            self.rb.state("Humidifier"),
            self.rb.state("Heater"),
            self.rb.state("Dehumidifier"),
            self.rb.state("Pump"),
        ]
        append_csv(CSV_FILE, row)
        line = f"[{row[0]}] " + " ".join(
            f"{k}={self.rb.state(k)}" for k in ["Lights","Exhaust Fan","Circulatory Fans","Humidifier","Heater","Dehumidifier","Pump"]
        )
        append_service_line(SERVICE_LOG, line)

    def maybe_daily_reset(self, now: datetime):
        if self.last_air_out_day != now.date():
            self.last_air_out_day = now.date()
            self.air_out_runs_done = 0

    def run(self):
        next_burst_time = 0.0
        try:
            while not self._stop.is_set():
                now = datetime.now()
                self.maybe_daily_reset(now)

                # Lights
                lights_on = in_light_period(now)
                self.set_state("Lights", lights_on)

                # Circulatory fans follow lights
                if CIRC_FANS_FOLLOW_LIGHTS:
                    self.set_state("Circulatory Fans", lights_on)

                # Temp & exhaust logic
                temp, hum, pres, gas = read_bme680()
                now_s = time.time()

                need_temp_burst = temp is not None and temp >= TEMP_THRESHOLD_C
                need_schedule_burst = now_s >= next_burst_time
                need_air_out = self.air_out_runs_done < AIR_OUT_RUNS_PER_DAY and now.hour in (9, 14, 20)

                if (need_temp_burst or need_schedule_burst or need_air_out) and lights_on:
                    self.set_state("Exhaust Fan", True)
                    time.sleep(BURST_SEC)
                    self.set_state("Exhaust Fan", False)
                    next_burst_time = time.time() + IDLE_BETWEEN_BURSTS_MIN * 60
                    if need_air_out:
                        self.air_out_runs_done += 1

                # Log every loop (~5s)
                self.log_states(temp, hum, pres, gas)
                self._stop.wait(5)
        finally:
            self.rb.cleanup()
