#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import threading
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from gpiozero import Button

# ------------------ GPIO 設定 ------------------ #
PIN_DOOR   = 17   # 門磁
PIN_WINDOW = 27   # 窗磁
PIN_PIR    = 5    # PIR

POLL_SEC = 0.3
DEBOUNCE_SEC = 1.0        # ★門窗狀態需穩定 1 秒才採用
ALERT_COOLDOWN = 30
PIR_ACTIVE_SEC = 15

# ---------------------------------------------- #

# 讀取 .env
load_dotenv()
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_USER_ID = os.getenv("LINE_USER_ID")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise SystemExit("請在 .env 設定 LINE_CHANNEL_ACCESS_TOKEN / LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
app = Flask(__name__)

# 感測器初始化
door_sw   = Button(PIN_DOOR, pull_up=True)
window_sw = Button(PIN_WINDOW, pull_up=True)
pir       = Button(PIN_PIR, pull_up=False)

# 全域狀態
state_lock = threading.Lock()
STATE = {
    "door_open": False,
    "window_open": False,
    "occupied": False,
    "pir_raw": False,
    "alert": False,
    "last_motion": None,
    "last_change": None,
}

_last_alert_time = 0
_last_motion_ts = 0.0

# ★ 去彈跳用
_last_door_raw = None
_last_window_raw = None
_door_stable_ts = 0.0
_window_stable_ts = 0.0

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def format_status():
    with state_lock:
        return (
            f"門：{'開' if STATE['door_open'] else '關'}\n"
            f"窗：{'開' if STATE['window_open'] else '關'}\n"
            f"房內狀態：{'有人（近期活動）' if STATE['occupied'] else '無人'}\n"
            f"最近活動時間：{STATE['last_motion'] or '-'}\n"
            f"系統狀態：{'⚠️異常' if STATE['alert'] else '正常'}\n"
            f"更新時間：{STATE['last_change'] or '-'}"
        )

def push_message(text):
    if LINE_USER_ID:
        line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=text))

def monitor_loop():
    global _last_alert_time, _last_motion_ts
    global _last_door_raw, _last_window_raw, _door_stable_ts, _window_stable_ts

    print("⚠️ PIR 上電後請等待 30–60 秒暖機")

    while True:
        now = time.time()

        # ---------- 門磁（依實測：True=關，False=開） ----------
        door_raw = door_sw.is_pressed
        if door_raw != _last_door_raw:
            _last_door_raw = door_raw
            _door_stable_ts = now

        door_open = STATE["door_open"]
        if now - _door_stable_ts >= DEBOUNCE_SEC:
            door_open = (door_raw == False)

        # ---------- 窗磁 ----------
        window_raw = window_sw.is_pressed
        if window_raw != _last_window_raw:
            _last_window_raw = window_raw
            _window_stable_ts = now

        window_open = STATE["window_open"]
        if now - _window_stable_ts >= DEBOUNCE_SEC:
            window_open = (window_raw == False)

        # ---------- PIR ----------
        pir_raw = pir.is_pressed
        if pir_raw:
            _last_motion_ts = now

        occupied = (now - _last_motion_ts) < PIR_ACTIVE_SEC

        # 異常規則
        alert = (not occupied) and (door_open or window_open)

        with state_lock:
            STATE.update({
                "door_open": door_open,
                "window_open": window_open,
                "occupied": occupied,
                "pir_raw": pir_raw,
                "alert": alert,
                "last_motion": datetime.fromtimestamp(_last_motion_ts).strftime("%Y-%m-%d %H:%M:%S")
                if _last_motion_ts else None,
                "last_change": now_str()
            })

        if alert and now - _last_alert_time >= ALERT_COOLDOWN:
            _last_alert_time = now
            push_message("⚠️宿舍警示：判定無人但門/窗仍開啟！\n\n" + format_status())

        time.sleep(POLL_SEC)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = (event.message.text or "").strip().lower()

    if text in ["help", "指令"]:
        reply = "可用指令：\nstatus / door / window / pir / help"
    elif text in ["status", "狀態"]:
        reply = format_status()
    elif text == "door":
        reply = "門：" + ("開" if STATE["door_open"] else "關")
    elif text == "window":
        reply = "窗：" + ("開" if STATE["window_open"] else "關")
    elif text == "pir":
        reply = "房內狀態：" + ("有人（近期活動）" if STATE["occupied"] else "無人")
    else:
        reply = "我看不懂 😅\n輸入 help 看指令"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000)
