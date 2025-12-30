#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gpiozero import Button
from time import sleep

door = Button(17, pull_up=True)

print("測試開始，請慢慢吸/分磁鐵")
while True:
    print("is_pressed =", door.is_pressed)
    sleep(1)

