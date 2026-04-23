import time
import cv2
import argparse
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from libcamera import Transform
from libcamera import controls
from ultralytics import YOLO
from rpi_ws281x import PixelStrip, Color

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

def rotate(frame, angle):
    h, w = frame.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rotated = cv2.warpAffine(frame, matrix, (w, h), borderValue=(114, 114, 114))
    return rotated

def inference(frame):
    global IMAGE_NUM

    # Run YOLO26 inference on the frame, only looking for people
    results = model(frame, verbose=False, classes=[0])

    # Visualize the results on the frame
    annotated_frame = results[0].plot()
    # Write annotated frame to storage
    cv2.imwrite(f"detection_{IMAGE_NUM}.jpg", annotated_frame)
    
    #Parse Results
    r = results[0]
    person_count = 0
    detections = []

    for box in r.boxes:
        conf = float(box.conf[0])      # confidence score

        # Filter: only class 0 (person) above confidence threshold
        if conf >= CONFIDENCE_MIN:
            person_count += 1
            coords = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
            detections.append({
                "confidence": round(conf, 2),
                "bbox": [round(c, 1) for c in coords]
            })

    #Print Results
    inference_ms = r.speed.get("inference", 0)
    print(f"People: {person_count} | "f"Inference: {inference_ms:.0f}ms")
    #Time Elapsed & AF Lens Position
    metadata = picam2.capture_metadata()
    print(f"Elapsed: {(time.time() - start):.3f}  |  AF: {metadata['LensPosition']}")

    for i, d in enumerate(detections, 1):
        print(f"   Person {i}: conf={d['confidence']} "f"bbox={d['bbox']}")

    print(f"Saved detection_{IMAGE_NUM}.jpg")

    
    #AF Settings
    

    
    IMAGE_NUM += 1

def initializeCam():
    global picam2
    picam2= Picamera2()
    #picam2.preview_configuration.main.size = (1920, 1080)
    picam2.preview_configuration.main.size = (2304, 1296)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.preview_configuration.transform = Transform(hflip=True, vflip=True)
    picam2.preview_configuration.align()
    picam2.configure("preview")
    picam2.start()
    #picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous,"AfRange": controls.AfRangeEnum.Macro})
    picam2.set_controls({"LensPosition": LENS_POS})

def ledOn():
    n = 8
    pin = 18
    brightness = 50
    global strip
    strip = PixelStrip(n, pin, brightness=brightness)
    strip.begin()
    for i in range(n):
        strip.setPixelColor(i, Color(255, 255, 255))
    strip.setPixelColor(0, Color(0, 0, 0))
    strip.setPixelColor(1, Color(0, 0, 0))
    strip.show()

def ledOff():
    n = 8
    strip.begin()
    for i in range(n):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

#returns the amount of people in the elevator cab as an int, will take around 800ms to process.
def getCount():
    global IMAGE_NUM
    #store start time
    start = time.time()

    # Capture frame
    frame = picam2.capture_array()

    #Crop Frame
    #frame = frame[0:1080, 292:1687]  
    frame = frame[0:1296, 300:1900]  

    # Run YOLO26 inference on the frame, only looking for people
    results = model(frame, verbose=False, classes=[0])

    # Visualize the results on the frame & save image
    #annotated_frame = results[0].plot()
    #cv2.imwrite(f"detection_{IMAGE_NUM}.jpg", annotated_frame)
    
    #Parse Results
    r = results[0]
    person_count = 0
    detections = []

    for box in r.boxes:
        conf = float(box.conf[0])      # confidence score

        # Filter: only class 0 (person) above confidence threshold
        if conf >= CONFIDENCE_MIN:
            person_count += 1
            coords = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
            detections.append({
                "confidence": round(conf, 2),
                "bbox": [round(c, 1) for c in coords]
            })

    #Print Results
    inference_ms = r.speed.get("inference", 0)
    print(f"People: {person_count} | "f"Inference: {inference_ms:.0f}ms")

    for i, d in enumerate(detections, 1):
        print(f"   Person {i}: conf={d['confidence']} "f"bbox={d['bbox']}")

    #Time Elapsed
    print(f"Elapsed: {(time.time() - start):.3f}")
    #print(f"Saved detection_{IMAGE_NUM}.jpg")

    IMAGE_NUM += 1
    return person_count


#Elevator Functions
#-----------------------------------------------------------------------------------------------


def is_full():
    return people_in_elevator >= MAX_CAPACITY


# --- Time Estimation ---

def revs_for_segment(from_floor, direction):
    """Revolutions needed to move one floor in the given direction (+1 up, -1 down)."""
    if direction == 1:
        return REVS_TERMINAL if from_floor == 1 else REVS_MIDDLE
    else:
        return REVS_TERMINAL if from_floor == 2 else REVS_MIDDLE


def travel_time(from_floor, to_floor):
    """Seconds to travel from from_floor to to_floor, segment by segment."""
    direction = 1 if to_floor > from_floor else -1
    total, pos = 0.0, from_floor
    while pos != to_floor:
        steps = int(revs_for_segment(pos, direction) * STEPS_PER_REV_FULL)
        total += steps * delay
        pos += direction
    return total


def simulate_no_skip(queue, start):
    remaining, pos, total = list(queue), start, 0.0
    while remaining:
        f = min(remaining, key=lambda x: abs(x - pos))
        floors_passed = abs(f - pos)
        total += travel_time(pos, f) + floors_passed * DOOR_TIME
        pos = f
        remaining.remove(f)
    return total


def simulate_nearest(queue, start):
    remaining, pos, total = list(queue), start, 0.0
    while remaining:
        f = min(remaining, key=lambda x: abs(x - pos))
        total += travel_time(pos, f) + DOOR_TIME
        pos = f
        remaining.remove(f)
    return total


# --- Boarding ---

def handle_boarding():
    global people_in_elevator
    print(">> Doors opening...")
    time.sleep(DOOR_OPEN_TIME)
    old = people_in_elevator
    count = getCount()
    people_in_elevator = count
    diff = count - old
    if diff < 0:
        print(f"   {abs(diff)} exited. {people_in_elevator}/{MAX_CAPACITY} remain.")
    elif diff > 0:
        print(f"   {diff} boarded. {people_in_elevator}/{MAX_CAPACITY} in elevator.")
    else:
        print(f"   No change. {people_in_elevator}/{MAX_CAPACITY} in elevator.")
    if is_full():
        print(f"   Elevator full ({MAX_CAPACITY}/{MAX_CAPACITY}).")
    print(">> Doors closing.")
    time.sleep(DOOR_CLOSE_TIME)


# --- Movement ---

def move_to_floor(target):
    global current_floor, current_revs
    if target == current_floor:
        return
    direction = 1 if target > current_floor else -1
    motor_dir = "cw" if direction == 1 else "ccw"
    label = "UP" if direction == 1 else "DOWN"
    print(f"\n>> Moving {label}: Floor {current_floor} -> Floor {target}")
    while current_floor != target:
        revs = revs_for_segment(current_floor, direction)
        rotate_revolutions(revs, motor_dir)
        current_revs  += direction * revs
        current_floor += direction
        print(f"   Passing floor {current_floor}")
    print(f">> Arrived at floor {current_floor}")
    handle_boarding()
    if current_floor in (1, TOTAL_FLOORS) and floor_queue:
        direct  = simulate_nearest(floor_queue, current_floor)
        no_skip = simulate_no_skip(floor_queue, current_floor)
        print(f"\n>> Terminal floor {current_floor} — {len(floor_queue)} stop(s) remaining:")
        print(f"   Accelerated (skip floors)    : {direct:.1f}s")
        print(f"   Unaccelerated (every floor)  : {no_skip:.1f}s")
        if no_skip - direct > 0.05:
            print(f"   Time saved by skipping       : {no_skip - direct:.1f}s")


# --- Queue Management ---

def _add_to_queue(floors, label):
    added, skipped = [], []
    for f in floors:
        if f == current_floor or f in floor_queue:
            skipped.append(f)
        else:
            floor_queue.append(f)
            added.append(f)
    if added:
        print(f">> [{label}] Queued floor(s): {', '.join(map(str, added))}")
    for f in skipped:
        msg = "already here" if f == current_floor else "already queued"
        print(f">> Floor {f} — {msg}.")


def queue_inside(floors):
    _add_to_queue(floors, "Inside")


def queue_outside(floors):
    if is_full():
        print(f"!! Elevator full ({MAX_CAPACITY}/{MAX_CAPACITY}). "
              f"Outside call(s) ignored: {', '.join(map(str, floors))}")
        return
    _add_to_queue(floors, "Outside")


def show_time_comparison():
    if not floor_queue:
        return
    no_skip = simulate_no_skip(floor_queue, current_floor)
    direct  = simulate_nearest(floor_queue, current_floor)
    saving  = no_skip - direct
    print(f"\n>> Route Time Estimate ({len(floor_queue)} pending stop(s)):")
    print(f"   No-skip (stop every floor)   : {no_skip:.1f}s")
    print(f"   Direct  (requested floors)   : {direct:.1f}s")
    if saving > 0.05:
        print(f"   Time saved by going direct   : {saving:.1f}s")
    else:
        print(f"   No time difference for this queue.")


def print_status():
    full_tag = " [FULL]" if is_full() else ""
    pending  = ', '.join(map(str, floor_queue)) if floor_queue else 'none'
    print(f"\n=== Status ===========================")
    print(f"  Current floor : {current_floor}")
    print(f"  People inside : {people_in_elevator}/{MAX_CAPACITY}{full_tag}")
    print(f"  Pending queue : {pending}")
    print(f"======================================")
    print("  Enter both [i] inside destinations and [o] outside calls each turn.")


def parse_floors(raw):
    floors, error = [], False
    for p in [p.strip() for p in raw.split(',')]:
        if p.isdigit():
            f = int(p)
            if 1 <= f <= TOTAL_FLOORS:
                floors.append(f)
            else:
                print(f"!! Floor {f} is out of range (1-{TOTAL_FLOORS}).")
                error = True
        else:
            print(f"!! '{p}' is not valid. Enter numbers 1-{TOTAL_FLOORS}.")
            error = True
    return floors, error


def main():
    print("=" * 42)
    print("  ElevMove - 4 Floor Elevator Controller")
    print("=" * 42)
    print(f"  Floors: 1-{TOTAL_FLOORS}  |  Capacity: {MAX_CAPACITY} people")
    print("  Separate multiple floors with commas.")
    print("  e.g. '3' or '1,3,4'")
    print(f"\n>> Starting at floor {current_floor}.")
    handle_boarding()
    print_status()

    while True:
        try:
            raw_i = input("\n[i] Inside  floors (Enter to skip): ").strip()
            raw_o = input("[o] Outside floors (Enter to skip): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nShutting down.")
            break

        if not raw_i and not raw_o:
            print_status()
            continue

        any_error = False
        if raw_i:
            floors_i, err = parse_floors(raw_i)
            any_error |= err
            if floors_i:
                queue_inside(floors_i)
        if raw_o:
            floors_o, err = parse_floors(raw_o)
            any_error |= err
            if floors_o:
                queue_outside(floors_o)

        if any_error:
            continue

        if floor_queue:
            show_time_comparison()
            while floor_queue:
                target = min(floor_queue, key=lambda f: abs(f - current_floor))
                floor_queue.remove(target)
                move_to_floor(target)

        print_status()


#Presets
PERSON_THRESHOLD = 1
CONFIDENCE_MIN = .20
global IMAGE_NUM
IMAGE_NUM = 1
LENS_POS = 6.5

#Presets Stepper
global delay
delay = 0.003


# --- Elevator Configuration ---
TOTAL_FLOORS    = 4
MAX_CAPACITY    = 2
REVS_TERMINAL   = 0.9*1.39   # leaving floor 1 going up, or floor 4 going down
REVS_MIDDLE     = 0.8*1.39   # all other segments
DOOR_OPEN_TIME  = 2
DOOR_CLOSE_TIME = 1
DOOR_TIME       = DOOR_OPEN_TIME + DOOR_CLOSE_TIME

# --- Elevator State ---
current_floor      = 1
current_revs       = 0.0
floor_queue        = []
people_in_elevator = 0


#MAIN CODE
#-----------------------------------------------------------------------------------------------
# Load the YOLO26 model
model = YOLO("/home/lucas/yolo26n_ncnn_model")
initializeCam()
ledOn()
initializeStepper()


try:
    main()
finally:
    cleanup()
    ledOff()
    cv2.destroyAllWindows()