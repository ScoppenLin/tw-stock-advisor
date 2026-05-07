# Core Universe Update Notes

更新日期：2026-05-07

## 核心配置方向

- 核心 ETF 以 0050 為主要大盤部位，搭配 00878 作為高股息穩定器。
- 權值核心保留台積電，並把台達電、聯發科納入核心股票池。
- 鴻海保留為大型權值股，但目標權重低於台積電與核心 ETF。
- 廣達保留為 AI 伺服器衛星持股，因衛星股仍需受 5% 單檔上限控管。

## 觀察清單方向

- ETF：市值型、高股息、科技型三類。
- 核心權值：半導體、電源散熱、IC 設計、電子代工。
- 防禦與金融：電信、金控。
- 衛星主題：AI 伺服器、散熱、重電、PCB、高速傳輸材料。

## 注意

`portfolio.csv` 只調整 target_weight，不改 shares 與 avg_cost。
新增 watchlist 標的若本地沒有價格資料，系統會先列 WATCH，待 `latest_prices.csv`、`price_history.csv` 或 TWSE 資料源更新後才進入完整評分。
