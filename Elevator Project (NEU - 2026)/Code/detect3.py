import cv2
from picamera2 import Picamera2
from libcamera import Transform
from libcamera import controls
from ultralytics import YOLO
import time

# Initialize the Picamera2
picam2 = Picamera2()
picam2.preview_configuration.main.size = (1920, 1080)
picam2.preview_configuration.main.format = "RGB888"
picam2.preview_configuration.transform = Transform(hflip=True, vflip=True)
picam2.preview_configuration.align()
picam2.configure("preview")
picam2.start()
#picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous,"AfRange": controls.AfRangeEnum.Macro})

# Load the YOLO26 model
model = YOLO("/home/lucas/best_ncnn_model")

#Presets
PERSON_THRESHOLD = 1
CONFIDENCE_MIN = 0.2
IMAGE_NUM = 1
LENS_POS = 5

while True:
    picam2.set_controls({"LensPosition": LENS_POS})
    time.sleep(0.5)
    #check time
    start = time.time()

    # Capture frame-by-frame
    frame = picam2.capture_array()
    frame3 = frame[0:1080, 292:1687]

    #Resize Frame
    #frame_small = cv2.resize(frame, (640, 640), interpolation=cv2.INTER_AREA)

    # Run YOLO26 inference on the frame, only looking for people
    results = model(frame3, verbose=False, classes=[0])

    # Visualize the results on the frame
    annotated_frame = results[0].plot()

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
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] People: {person_count} | "
            f"Inference: {inference_ms:.0f}ms", end="")

    if person_count >= PERSON_THRESHOLD:
        print(f" | *** ALERT: {person_count} people detected! ***", end="")
        filename = f"detection_{IMAGE_NUM}.jpg"
        cv2.imwrite(filename, annotated_frame)
        print(f"Saved {filename}")
        IMAGE_NUM += 1

    print()

    for i, d in enumerate(detections, 1):
        print(f"   Person {i}: conf={d['confidence']} "
                f"bbox={d['bbox']}")

    print(f"Elapsed: {(time.time() - start):.3f} seconds")
    metadata = picam2.capture_metadata()
    print(f"AF settled on LensPosition: {metadata['LensPosition']}\n\n")
    LENS_POS += 0.5

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) == ord("q"):
        break

# Release resources and close windows
cv2.destroyAllWindows()