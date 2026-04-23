import RPi.GPIO as GPIO
import time
import argparse

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


def setup():
    global PINS
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, 0)


def cleanup():
    for pin in PINS:
        GPIO.output(pin, 0)
    GPIO.cleanup()


def step_motor(steps, delay=0.003, mode="full", direction="cw"):
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


def rotate_degrees(degrees):
    """Rotate the motor by a specific number of degrees."""
    delay=0.003
    mode="full"
    direction="cw"
    steps_per_rev = STEPS_PER_REV_FULL if mode == "full" else STEPS_PER_REV_HALF
    steps = int((abs(degrees) / 360) * steps_per_rev)
    step_motor(steps, delay, mode, direction)

def rotate_revolutions(revs):
    delay=0.003
    mode="full"
    direction="cw"
    """Rotate the motor a given number of full revolutions."""
    steps_per_rev = STEPS_PER_REV_FULL if mode == "full" else STEPS_PER_REV_HALF
    steps = int(revs * steps_per_rev)
    step_motor(steps, delay, mode, direction)

#MAIN
parser = argparse.ArgumentParser(description="ULN2003 Stepper Motor Control")
parser.add_argument("--degrees", type=float, help="Degrees to rotate")
parser.add_argument("--revs", type=float, help="Full revolutions to rotate")
parser.add_argument("--steps", type=int, help="Raw steps to take")
parser.add_argument("--delay", type=float, default=0.003, help="Step delay in seconds (default: 0.001)")
parser.add_argument("--mode", choices=["half", "full"], default="half", help="Step mode (default: half)")
parser.add_argument("--dir", choices=["cw", "ccw"], default="cw", help="Direction (default: cw)")
args = parser.parse_args()
initializeStepper()
try:
    if args.degrees:
        steps_per_rev = STEPS_PER_REV_FULL if args.mode == "full" else STEPS_PER_REV_HALF
        steps = int((abs(args.degrees) / 360) * steps_per_rev)
        step_motor(steps, args.delay, args.mode, args.dir)

    elif args.revs:
        steps_per_rev = STEPS_PER_REV_FULL if args.mode == "full" else STEPS_PER_REV_HALF
        steps = int(args.revs * steps_per_rev)
        step_motor(steps, args.delay, args.mode, args.dir)

    elif args.steps:
        step_motor(args.steps, args.delay, args.mode, args.dir)

    else:
        parser.print_help()
except KeyboardInterrupt:
        print("\nStopped by user.")

#write the elevator code here

cleanup()