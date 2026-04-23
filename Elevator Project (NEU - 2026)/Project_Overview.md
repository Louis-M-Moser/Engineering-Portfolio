# 🛗 Elevator Occupancy Detection System

A Raspberry Pi-based embedded system that uses computer vision and a stepper motor to autonomously detect the number of people inside a model elevator cab. Built using a Raspberry Pi 4, Pi Camera Module 3, a 28BYJ-48 stepper motor, and a YOLO-based AI detection model.

---

## 🔧 Hardware

- **Raspberry Pi 5**
- **Raspberry Pi Camera Module 3** (autofocus, 12MP)
- **28BYJ-48 Stepper Motor** + ULN2003 driver board
- **WS281x LED Ring** (8 LEDs, GPIO pin 18) — provides consistent lighting inside the cab
- **Figurines** — used as stand-in occupants for prototype testing

---

## 📁 File Overview

### `elevator2.py` — *Full Prototype · Main Program*
The complete, integrated elevator control program. Combines the Pi Camera 3, YOLO person detection, stepper motor, and LED lighting into a unified pipeline. Automatically counts occupants inside the elevator cab and drives the motor accordingly. This is the primary script that runs on the fully assembled prototype.

---

### `detect2.py` — *Detection Script · Testing & Debugging*
Runs YOLO-based person detection inference on live frames captured from the Pi Camera 3. Annotates each frame with bounding boxes and saves the output as a `.jpg` file for review. Used to test and debug the AI model's performance on the prototype setup. Integrates LED lighting and the stepper motor alongside the camera pipeline.

---

### `step1.py` — *Stepper Motor · CLI Controller*
Command-line utility for manually controlling the 28BYJ-48 stepper motor. Accepts arguments directly from the terminal for precise control over motor behavior.

| Argument | Description |
|----------|-------------|
| `--degrees` | Rotate by a specific number of degrees |
| `--revs` | Rotate by a number of full revolutions |
| `--steps` | Rotate by a raw step count |
| `--delay` | Step delay in seconds (default: `0.003`) |
| `--mode` | Step mode: `half` or `full` (default: `half`) |
| `--dir` | Direction: `cw` or `ccw` (default: `cw`) |

**Example usage:**
```bash
python step1.py --degrees 90 --dir ccw --mode full
python step1.py --revs 2 --delay 0.002 --dir cw
```

---

### `cal.py` — *Stepper Motor · Calibration Tool*
Interactive keyboard-driven calibration script for the stepper motor. Used to fine-tune motor positioning and verify the mechanical alignment of the elevator prototype.

| Key | Action |
|-----|--------|
| `W` | Rotate 5° clockwise |
| `S` | Rotate 5° counter-clockwise |
| `Q` | Quit |

---

### `dataimg.py` — *Dataset · Image Capture Tool*
Capture tool for building a custom AI training dataset. Saves cropped, high-resolution images from the Pi Camera 3 each time `SPACE` is pressed. Designed for photographing elevator cab figurines to generate labeled training data for a future custom YOLO model.

| Key | Action |
|-----|--------|
| `SPACE` | Capture and save image |
| `Q` | Quit |

Images are saved as `img_1.jpg`, `img_2.jpg`, etc.

---

### `detect3.py` — *Experimental · Custom Model Testing*
Early detection script used to test a custom-trained YOLO model. Set aside because the model was trained on real-world human data that did not generalize well to the figurines used in the prototype. Kept for reference and potential future retraining efforts.

---

## 🤖 AI Model

Person detection is handled by a **YOLOv8n** model converted to NCNN format for optimized inference on the Raspberry Pi 5. The model runs at approximately **800ms per frame** end-to-end, including camera capture, cropping, inference, and result parsing.

A custom model was explored (`detect3.py`) but training on real-world imagery did not transfer well to the figurine-scale prototype environment.

---

## 🚀 Running the Prototype

```bash
# Run the full elevator prototype
python elevator2.py

# Test detection and save annotated images
python detect2.py

# Calibrate motor positioning
python cal.py

# Control motor from command line
python step1.py --degrees 180 --dir cw
```

---

## 📦 Dependencies

```bash
pip install opencv-python picamera2 RPi.GPIO ultralytics rpi-ws281x
```

---

*Developed as part of an embedded systems engineering project.*
