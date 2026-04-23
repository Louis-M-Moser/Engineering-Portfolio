import time
import argparse
import sys
import termios
import tty
import RPi.GPIO as GPIO


def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def initializeStepper():
    global IN1, IN2, IN3, IN4, PINS, HALF_STEP_SEQ, FULL_STEP_SEQ, STEPS_PER_REV_FULL, STEPS_PER_REV_HALF
    # --- Pin Configuration ---
    IN1 = 17
    IN2 = 23
    IN3 = 27
    IN4 = 22
    PINS = [IN1, IN2, IN3, IN4]
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, 0)
    # Half-step sequence (8 steps per cycle, smoother motion, higher resolution)
    HALF_STEP_SEQ = [
        [1, 0, 0, 0],
        [1, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 1],
        [0, 0, 0, 1],
        [1, 0, 0, 1],
    ]
    # Full-step sequence (4 steps per cycle, more torque)
    FULL_STEP_SEQ = [
        [1, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 1],
        [1, 0, 0, 1],
    ]
    # 28BYJ-48 specs: 64 steps/rev internally, 63.68:1 gear ratio
    # Half-step: 4096 steps/rev | Full-step: 2048 steps/rev
    STEPS_PER_REV_HALF = 4096
    STEPS_PER_REV_FULL = 2048

def cleanup():
    for pin in PINS:
        GPIO.output(pin, 0)
    GPIO.cleanup()

def step_motor(steps, delay=0.001, mode="full", direction="cw"):
    """
    Rotate the motor a given number of steps.

    Args:
        steps:     Number of steps to take.
        delay:     Seconds between each step (lower = faster, min ~0.001).
        mode:      "half" for half-step, "full" for full-step.
        direction: "cw" for clockwise, "ccw" for counter-clockwise.
    """
    seq = FULL_STEP_SEQ if mode == "full" else HALF_STEP_SEQ
    if direction == "ccw":
        seq = list(reversed(seq))

    seq_len = len(seq)
    for i in range(steps):
        for pin_idx, pin in enumerate(PINS):
            GPIO.output(pin, seq[i % seq_len][pin_idx])
        time.sleep(delay)

    # De-energize coils to prevent heating
    for pin in PINS:
        GPIO.output(pin, 0)

#Rotate stepper the amount of degrees, and the direction specified: "cw" (clockwise) or "ccw"(counter-clockwise)
def rotate_degrees(degrees, direction):
    """Rotate the motor by a specific number of degrees."""
    global delay
    mode="full"
    steps_per_rev = STEPS_PER_REV_FULL if mode == "full" else STEPS_PER_REV_HALF
    steps = int((abs(degrees) / 360) * steps_per_rev)
    step_motor(steps, delay, mode, direction)

#Rotate stepper the amount of revs, and the direction specified: "cw" (clockwise) or "ccw"(counter-clockwise)
def rotate_revolutions(revs, direction):
    global delay
    mode="full"
    """Rotate the motor a given number of full revolutions."""
    steps_per_rev = STEPS_PER_REV_FULL if mode == "full" else STEPS_PER_REV_HALF
    steps = int(revs * steps_per_rev)
    step_motor(steps, delay, mode, direction)


global delay
delay = 0.003

#Initialize Stepper
initializeStepper()

print("Press W to move up, S to move down. \n Press Q to quit.")
while True:
    key = get_key()
    if key == 'w':
        rotate_degrees(5, "cw")
    elif key == "s":
        rotate_degrees(5, "ccw")
    elif key == 'q':
        print("Exiting.")
        break

cleanup()