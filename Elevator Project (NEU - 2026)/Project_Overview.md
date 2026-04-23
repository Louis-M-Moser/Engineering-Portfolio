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
