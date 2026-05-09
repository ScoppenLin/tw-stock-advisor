# tw_stock_advisor

台股投資建議自動化系統 MVP。這個專案先做「建議引擎」，不做自動下單，也不串接券商 API。

## 功能

- 讀取 `data/portfolio.csv` 目前持股
- 讀取 `data/watchlist.csv` 追蹤股票池
- 從本地 CSV 或 mock data 取得每日價格與歷史價格
- 計算市值、損益、權重與台股張數
- 使用簡化版價格動能、估值代理與風險模型評分
- 根據評分、目標權重與風控上限產生 BUY / ADD / HOLD / REDUCE / SELL / WATCH
- 輸出每日建議 CSV 與 Markdown 報告

## 專案結構

```text
tw_stock_advisor/
├── data/
│   ├── portfolio.csv
│   ├── watchlist.csv
│   └── market_data/
│       ├── latest_prices.csv
│       └── price_history.csv
├── reports/
│   └── daily/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── data_loader.py
│   ├── portfolio_manager.py
│   ├── market_regime.py
│   ├── stock_universe.py
│   ├── scoring_model.py
│   ├── risk_manager.py
│   ├── recommendation_engine.py
│   └── report_generator.py
└── requirements.txt
```

## 安裝

```bash
cd tw_stock_advisor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 執行

```bash
python3 src/main.py --mode all
```

可用模式：

- `--mode daily`：產生日報與每日建議 CSV
- `--mode weekly`：產生週報與再平衡計畫 CSV
- `--mode all`：同時產生日報與週報

可用資料來源：

- `--data-source local`：使用本地 CSV，適合每日穩定排程與測試
- `--data-source twse`：嘗試抓取 TWSE 盤後上市個股收盤價，失敗時自動退回本地 CSV

可用輸入/輸出位置：

- `--input-source local`：從 `data/*.csv` 讀取 account、portfolio、watchlist
- `--input-source google`：從 Google Sheet 的 `account`、`portfolio`、`watchlist` 分頁讀取
- `--output-sink local`：只輸出本地報告
- `--output-sink google`：同時把建議與報告寫回 Google Sheet

執行後會輸出：

- `reports/daily/daily_recommendation.csv`
- `reports/daily/daily_report.md`
- `reports/weekly/weekly_rebalance_plan.csv`
- `reports/weekly/weekly_report.md`

## 輸入資料格式

`data/account.csv`

```csv
total_capital,reserve_cash_weight,note
100000,0.05,新手起始資金設定
```

如果你還沒有任何持股，先修改這裡的 `total_capital`，系統會用它估算起始配置與目標股數。

`data/portfolio.csv`

```csv
ticker,name,asset_type,shares,avg_cost,target_weight
0050,元大台灣50,etf,2000,182.5,0.25
```

`asset_type` 建議使用：

- `etf`
- `large_cap`
- `core_stock`
- `satellite`
- `small_mid`

`data/watchlist.csv`

```csv
ticker,name,asset_type,sector
2330,台積電,core_stock,半導體
```

## 價格資料

MVP 預設讀取：

- `data/market_data/latest_prices.csv`
- `data/market_data/price_history.csv`
- `data/market_data/market_indicators.csv`

如果檔案不存在，系統會用 mock data 產生可跑的價格資料。未來可在 `src/data_loader.py` 加入 TWSE OpenAPI、ETFortune 或券商行情來源。

也可以嘗試使用 TWSE 資料：

```bash
python3 src/main.py --mode all --data-source twse
```

使用 Google Sheet：

```bash
python3 src/main.py --mode all --data-source twse --input-source google --output-sink google
```

目前 `twse_client.py` 先支援 TWSE 盤後上市個股日成交資訊，並保留讀取 OpenAPI swagger catalog 的方法，後續可逐步加入法人、估值、月營收與 ETF 資料。

## 投資邏輯

第一版採核心 ETF + 大型權值股 + 衛星成長股的建議引擎：

- ETF 單一上限 30%
- 台積電上限 25%
- 大型股上限 10%
- 衛星股上限 5%
- 中小型股上限 3%

建議引擎只產生投資建議，不會下單。建議先連續執行 4 到 8 週，觀察建議品質與風控效果，再評估是否加入半自動交易流程。

## 市場狀態

`market_indicators.csv` 會用來判斷：

- `Risk-On`
- `Bullish`
- `Neutral`
- `Defensive`
- `Risk-Off`

目前納入加權指數均線位置、20 日報酬、外資買賣超、台幣、美股 Nasdaq / SOX、成交量與 VIX。`Risk-Off` 會禁止新增衛星股，`Defensive` 會提高衛星股減碼傾向。

## Feature 層

`src/feature_builder.py` 會把原始行情轉成模型欄位：

- 20 日與 60 日報酬
- 20 / 60 / 120 日均線
- 是否站上均線
- 量能比
- 與均線乖離
- 從區間高點回落幅度

`src/scoring_model.py` 會依市場狀態套用不同權重。強多市場提高動能權重，偏弱市場提高風險權重。

## Google Sheet 設定

建議 Google Sheet 分頁：

- `帳戶設定`
- `目前持股`
- `觀察清單`
- `每日建議`
- `每週再平衡`
- `每日報告`
- `每週報告`

前三個分頁是輸入，後四個分頁由系統輸出。程式內部仍用英文代號，但實際 Google Sheet 分頁會顯示中文名稱。

### 1. 建立 Google Sheet

新增一份 Google Sheet，名稱例如：

```text
TW Stock Advisor
```

先不用手動建立所有分頁，程式可以初始化。

### 2. 建立 Google Cloud Service Account

1. 到 Google Cloud Console 建立或選擇一個 Project。
2. 啟用 Google Sheets API。
3. 建立 Service Account。
4. 建立 JSON key，下載 JSON。
5. 複製 JSON 裡的 `client_email`。
6. 回到 Google Sheet，按「共用」，把 `client_email` 加進去，權限選「編輯者」。

### 3. 設定環境變數

本機測試可以使用：

```bash
export GOOGLE_SHEET_ID="你的 Google Sheet ID"
export GOOGLE_SERVICE_ACCOUNT_FILE="/path/to/service-account.json"
```

Google Sheet ID 是網址中 `/d/` 和 `/edit` 中間那段。

### 4. 初始化 Google Sheet 分頁

在本機執行：

```bash
python3 src/main.py --bootstrap-google-sheets
```

這會把本地 CSV 寫入 Google Sheet：

- `data/account.csv` -> `帳戶設定`
- `data/portfolio.csv` -> `目前持股`
- `data/watchlist.csv` -> `觀察清單`

### 5. 從 Google Sheet 讀取並寫回結果

```bash
python3 src/main.py --mode all --data-source twse --input-source google --output-sink google
```

執行後會寫回：

- `每日建議`
- `每週再平衡`
- `每日報告`
- `每週報告`

### 6. GitHub Actions Secrets

到 GitHub repo：

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

新增：

```text
GOOGLE_SHEET_ID
GOOGLE_SERVICE_ACCOUNT_JSON_B64
```

建議把 service account JSON 轉成 base64 後放入 `GOOGLE_SERVICE_ACCOUNT_JSON_B64`。如果不想轉 base64，也可以改新增 `GOOGLE_SERVICE_ACCOUNT_JSON`，直接貼上原始 JSON：

```bash
base64 -i service-account.json | pbcopy
```

GitHub Actions 會固定使用 Google Sheet 作為輸入與輸出；如果缺少 `GOOGLE_SHEET_ID` 或 service account secret，排程會明確失敗並顯示缺少哪個設定。

## Email 報告

GitHub Actions 可在每日執行完成後寄出 email。到 GitHub repo：

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

新增：

```text
MAIL_USERNAME
MAIL_PASSWORD
```

系統已預設使用 Gmail SMTP：

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

報告固定寄到 `scoppen.lin@gmail.com`。寄件人會使用 `MAIL_USERNAME`。

Gmail 範例：

```text
MAIL_USERNAME=你的 Gmail
MAIL_PASSWORD=Gmail App Password
```

設定完成後，GitHub Actions 每次成功產生報告後會寄出：

- 每日報告內容
- 每週報告內容
- `daily_recommendation.csv`
- `weekly_rebalance_plan.csv`
