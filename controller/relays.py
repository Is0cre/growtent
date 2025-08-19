import RPi.GPIO as GPIO
from time import sleep

class RelayBoard:
    def __init__(self, pin_map: dict[str, int], active_low: bool = True):
        self.pin_map = pin_map
        self.active_low = active_low
        GPIO.setmode(GPIO.BCM)
        for pin in pin_map.values():
            GPIO.setup(pin, GPIO.OUT)
            self.off_pin(pin)

    def _drive(self, pin: int, on: bool):
        if self.active_low:
            GPIO.output(pin, GPIO.LOW if on else GPIO.HIGH)
        else:
            GPIO.output(pin, GPIO.HIGH if on else GPIO.LOW)

    def on(self, name: str):
        self._drive(self.pin_map[name], True)

    def off(self, name: str):
        self._drive(self.pin_map[name], False)

    def state(self, name: str) -> str:
        pin = self.pin_map[name]
        val = GPIO.input(pin)
        if self.active_low:
            return "ON" if val == GPIO.LOW else "OFF"
        else:
            return "ON" if val == GPIO.HIGH else "OFF"

    def off_pin(self, pin: int):
        self._drive(pin, False)

    def cleanup(self):
        GPIO.cleanup()
