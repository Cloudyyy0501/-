# -Smart Dorm Door/Window Alert System (Raspberry Pi + LINE Bot)

專題簡介

本專題為智慧宿舍安全門窗通知系統，使用 Raspberry Pi 5 讀取門磁/窗磁與 PIR 感測器狀態，當判定房內無人且門或窗未關閉時，透過 LINE Bot 推播警示訊息。

1. 功能

門磁/窗磁偵測門窗是否開啟

PIR 偵測房內是否有人（近期活動）

異常規則：無人且門/窗開啟 → LINE 推播警示

LINE 指令查詢：status / door / window / pir / help

2. 硬體需求

Raspberry Pi 5

磁簧開關 x2（門/窗）

PIR 感測器 x1

杜邦線、電阻（依接法）

3. GPIO 接線（依本專題設定）

Door Reed Switch：GPIO 17

Window Reed Switch：GPIO 27

PIR：GPIO 5

程式設定請見 src/winsdoor.py。
