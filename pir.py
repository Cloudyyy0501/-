from gpiozero import DigitalInputDevice
from time import sleep

pir = DigitalInputDevice(5, pull_up=False)

print("PIR 暖機 60 秒，先不要動...")
sleep(3)

while True:
    print("PIR raw:", pir.value)  # 0 或 1
    sleep(1)