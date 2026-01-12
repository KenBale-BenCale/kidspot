import threading
import time
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# LED configuration
blink_rate = 0.5  # seconds
default_duration = 2  # seconds
colours = {
    "red": 17,
    "green": 27,
    "blue": 22,
    "yellow": 23,
    "white": 24
}

for pin in colours.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# Internal state
led_states = {}  # {led_name: "off"/"on"/"blinking"}
stop_event = threading.Event()


def init_leds():
    GPIO.setmode(GPIO.BCM)
    for led_name, pin in colours.items():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
        led_states[led_name] = "off"


def turn_on_led(led_name):
    pin = colours[led_name]
    GPIO.output(pin, GPIO.HIGH)
    led_states[led_name] = "on"


def turn_off_led(led_name):
    pin = colours[led_name]
    GPIO.output(pin, GPIO.LOW)
    led_states[led_name] = "off"


def blink_led(led_name, duration=None):
    if duration is None:
        duration = default_duration

    def _blink():
        end_time = time.time() + duration
        while time.time() < end_time and not stop_event.is_set():
            turn_on_led(led_name)
            time.sleep(blink_rate)
            turn_off_led(led_name)
            time.sleep(blink_rate)
        led_states[led_name] = "off"

    threading.Thread(target=_blink, daemon=True).start()


def test_all_leds():
    for led_name in colours:
        turn_on_led(led_name)
    time.sleep(1)
    for led_name in colours:
        turn_off_led(led_name)


def shutdown_leds():
    stop_event.set()
    for led_name in colours:
        try:
            GPIO.output(pin, GPIO.LOW)
        except RuntimeError:
            # If GPIO not initialized, skip
            pass
    GPIO.cleanup()
