import time
import sys
import termios
import tty
import cv2
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from libcamera import Transform
from libcamera import controls
#from ultralytics import YOLO
from rpi_ws281x import PixelStrip, Color


def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def initializeCam():
    global picam2
    picam2= Picamera2()
    picam2.preview_configuration.main.size = (2304, 1296)
    #picam2.preview_configuration.main.size = (1920, 1080)
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
    brightness = 100
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


global IMAGE_NUM
IMAGE_NUM = 1
LENS_POS = 6.5

ledOn()
initializeCam()
time.sleep(1.5)

print("Press SPACE to capture, q to quit.")
while True:
    key = get_key()
    if key == ' ':
        frame = picam2.capture_array()
        #Crop Frame
        frame = frame[0:1296, 300:1900]  # 1296×1296
        #frame = frame[0:1080, 292:1687]
        cv2.imwrite(f"img_{IMAGE_NUM}.jpg", frame)
        print(f"Saved img_{IMAGE_NUM}.jpg")
        IMAGE_NUM += 1
    elif key == 'q':
        print("Exiting.")
        break

ledOff()
cv2.destroyAllWindows()