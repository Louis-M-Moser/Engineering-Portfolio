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
    start = time.time()

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
    # frame = frame[0:1080, 292:1687]
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

# Load the YOLO26 model
model = YOLO("/home/lucas/yolo26n_ncnn_model")

#Presets
PERSON_THRESHOLD = 1
CONFIDENCE_MIN = .20
global IMAGE_NUM
IMAGE_NUM = 1
LENS_POS = 6.5

#Presets Stepper
global delay
delay = 0.003


#MAIN CODE
#-----------------------------------------------------------------------------------------------
#Start the PiCam3
initializeCam()
#Turn on elevator light
ledOn()
#Initialize Stepper
initializeStepper()
time.sleep(2)

#Inference with Save:
while IMAGE_NUM<=15:
    #Capture Frame
    frame = picam2.capture_array()

    #Crop Frame
    frame = frame[0:1296, 300:1900]

    inference(frame)

print("\n\n\nShutting Down...\n\n\n")

#cleanup stepper motor
cleanup()
#turn off LED
ledOff()
# Release resources and close windows
cv2.destroyAllWindows()