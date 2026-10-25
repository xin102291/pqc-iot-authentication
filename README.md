# PQC IoT Authentication

A lattice-based (LWE) post-quantum authentication system: a Raspberry Pi reads heart rate and SpO2 from a MAX30102 sensor, authenticates with the server using an LWE signature scheme, negotiates a session key, and streams encrypted readings into MySQL; a Flask web app lets patients log in with the same LWE scheme and view their records and live vitals.

## 簡介

大學畢業專題。以格密碼（Lattice，LWE）實作一套不依賴 RSA／ECC 的身分驗證與加密傳輸流程，並套用在醫療 IoT 情境：

1. **IoT 端**（Raspberry Pi）：讀取 MAX30102 的心跳與血氧，先用 LWE 簽章向伺服器證明身分，再協商出 session key，之後所有感測資料都用對稱式 LWE 加密後送出。
2. **伺服器端**：驗證 IoT 裝置簽章、產生並加密 session key、解密感測資料並寫入 MySQL。
3. **網站端**（Flask）：病患以身分證字號＋密碼登入，登入流程同樣走 LWE 簽章驗證（並即時顯示每一步），登入後可查看個人資料、病歷、用藥、檢查結果與心跳／血氧折線圖。

### 核心數學

```
公鑰 pk = (A, B)，B = A·sk + e      A：由 ID 的 ASCII 組成的 n×n 矩陣
私鑰 sk：由 SHA-224(ID + 密碼) 取前三段導出的 n 維向量
```

| 用途 | 類別（`asym.py`／`symm.py`） | 參數 |
|---|---|---|
| 身分驗證（簽章／驗章） | `authentication`：私鑰 `encrypt` 產生簽章，公鑰 `decrypt` 還原訊息，相等即通過 | n=3，q=999999937，scale=10000，bound=5 |
| session key 交換（公鑰加密） | `LWEasym`：伺服器用 IoT 公鑰加密 5 個隨機數，IoT 用私鑰解密，各拆成兩段得到 10 個數字 | 同上 |
| 感測資料加密（對稱式） | `LEWSymmetric`：以 session key 為 s，每次隨機產生 A 並計算 c = A·s + e + m | n=10，q=100003，scale=1000，bound=5 |

## 專案背景

- 性質：大學畢業專題（Capstone Project）
- 團隊：〔請補成員與分工，或只寫一句協作〕

## 架構

```
Capstone_Project/
├─ IoT/                      # Raspberry Pi 端與伺服器端（純 socket）
│  ├─ main.py                # IoT 主程式：驗證 → 取得 session key → 讀 MAX30102 並加密送出
│  ├─ heartrate_monitor.py   # MAX30102 讀取執行緒，算出心跳／血氧後加密送給伺服器
│  ├─ max30102.py, hrcalc.py # 感測器驅動與心率／血氧演算法
│  ├─ Server.py              # 伺服器：驗章、發 session key、解密並寫入 MySQL
│  ├─ Client.py              # 不接感測器的測試用 client（手動輸入訊息）
│  ├─ IoT.py                 # 舊版：DHT11 溫濕度版本的 IoT 主程式
│  ├─ key_main.py            # 產生裝置公私鑰，寫入 Send_message/items.json
│  ├─ key.py, asym.py, symm.py, binary.py, utils.py   # LWE 金鑰、簽章、加密與編碼工具
│  ├─ callvalue.py           # 在模組間共用 session key 與 socket
│  ├─ items.json             # 示範用的裝置／伺服器金鑰
│  └─ requirements.txt
├─ Web/                      # 病患網站（Flask）
│  ├─ main.py                # 進入點（Flask-SocketIO，預設 port 5000）
│  ├─ requirements.txt
│  └─ App/
│     ├─ route.py            # 路由：登入／註冊／各病患頁面／即時加密步驟（SocketIO）
│     ├─ SQL.py              # SQLAlchemy 模型（patients、medical_records、sensor_readings…）
│     ├─ patient_full_info.py# 查詢病患資料的函式
│     ├─ key.py, asym.py, binary.py, utils.py          # 與 IoT/ 相同的 LWE 實作（Web 版 key.py 直接吃前端算好的雜湊）
│     ├─ id_card.py          # 身分證字號檢查碼
│     ├─ templates/          # login、signup、home、patient_*、realtime_encryption
│     └─ static/
├─ experiments/authentication/   # 命令列示範：check.py（檢查碼）→ key_main.py（產生金鑰）→ asym_main.py（簽章驗證）／session_key.py（會議金鑰）
├─ creat_sql.sql             # 建庫、建表與示範資料
└─ .env.example
```

### 流程

```
IoT（Raspberry Pi）                         Server.py                              MySQL / Web
─────────────────                          ─────────                              ───────────
                     ◀── 隨機訊息 m ──────
私鑰對 m 簽章 ────────── 簽章 + 隨機數 m' ──▶ 用 IoT 公鑰驗章，m 相符即通過
                     ◀── 對 m' 的簽章 ────  用伺服器私鑰對 m' 簽章
用伺服器公鑰驗章
                     ◀── LWEasym 加密的 5 個隨機數 ──  產生 session key
私鑰解密 → session key
讀 MAX30102 → 心跳,血氧 ── LEWSymmetric 加密 ──▶ 解密 → INSERT sensor_readings ──▶ 病患儀表板折線圖
```

網站登入：前端以 CryptoJS 計算 SHA-224(身分證字號 + 密碼) 後才送出；後端用它導出 sk，與資料庫中的 pk 做一次簽章／驗章，通過才建立 session。`/realtime_encryption` 頁面會透過 SocketIO 即時顯示每一步。

## 安裝

```bash
# 1. 建立資料庫（含兩位示範病患與病歷資料）
mysql -u root -p < creat_sql.sql

# 2. 環境變數
cp .env.example .env      # 填入 DATABASE_URL 與 DB_* 的密碼

# 3. 網站
pip install -r Web/requirements.txt

# 4. IoT（在 Raspberry Pi 上）
pip install -r IoT/requirements.txt
```

示範病患帳號（`creat_sql.sql`）：身分證字號 `A123456789`、`A223456781`，密碼皆為 `demo1234`。

## 使用方式

### 網站

```bash
cd Web
python main.py            # http://localhost:5000
```

- `/signup`：輸入身分證字號（會檢查檢查碼）、密碼與基本資料，系統以 LWE 產生公鑰存入資料庫（不存密碼）。
- `/login`：登入；`/realtime_encryption` 可看到簽章與驗章的每個步驟。
- 登入後：`/home`、`/patient_personal_info`、`/patient_medical_records`、`/patient_medications`、`/patient_test_results`、`/patient_medical_documents`、`/patient_dashboard`（心跳／血氧折線圖）。

### IoT 與伺服器

```bash
# 產生裝置金鑰（ID 為 10 碼、最後一碼是 ISBN-10 式檢查碼，例如 IOT1234561）
python IoT/key_main.py

# 伺服器（先把 Server.py 的 ADDRESS 改成本機 IP）
python IoT/Server.py

# Raspberry Pi（先把 main.py 的 ADDRESS 改成伺服器 IP；-t 為讀取秒數）
python IoT/main.py -t 30

# 沒有感測器時可用 Client.py 手動輸入訊息測試
python IoT/Client.py
```

### 命令列示範（experiments/authentication/）

```bash
python check.py        # 由 9 碼算出第 10 碼檢查碼
python key_main.py     # 輸入 ID 與密碼，產生 pk／sk
python asym_main.py    # 貼上 pk／sk，對一個數字簽章並驗證
python session_key.py  # 貼上 pk／sk，模擬 session key 交換
```

## 注意事項

- `creat_sql.sql` 的病患、醫師與病歷皆為虛構示範資料。
- IoT 與伺服器之間是明文 socket 加自製 LWE 加密，屬於專題展示，未經安全性審查，請勿用於真實醫療資料。
- `IoT/items.json` 內的金鑰僅供示範；實際使用請以 `key_main.py` 重新產生，輸出會寫到被 `.gitignore` 忽略的 `Send_message/`。
