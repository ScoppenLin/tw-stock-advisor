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
