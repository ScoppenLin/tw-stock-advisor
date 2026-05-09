from __future__ import annotations

from html import escape
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DAILY_REPORT = PROJECT_ROOT / "reports" / "daily" / "daily_report.md"
WEEKLY_REPORT = PROJECT_ROOT / "reports" / "weekly" / "weekly_report.md"
DAILY_CSV = PROJECT_ROOT / "reports" / "daily" / "daily_recommendation.csv"
WEEKLY_CSV = PROJECT_ROOT / "reports" / "weekly" / "weekly_rebalance_plan.csv"


def main() -> None:
    smtp_host = _required_env("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_username = _required_env("SMTP_USERNAME")
    smtp_password = _required_env("SMTP_PASSWORD")
    email_to = os.environ.get("EMAIL_TO", "scoppen.lin@gmail.com")
    email_from = os.environ.get("EMAIL_FROM", smtp_username)

    message = EmailMessage()
    message["Subject"] = os.environ.get("EMAIL_SUBJECT", "台股投資建議報告")
    message["From"] = email_from
    message["To"] = email_to
    message.set_content(_build_body())
    message.add_alternative(_build_html_body(), subtype="html")

    for attachment in [DAILY_CSV, WEEKLY_CSV]:
        if attachment.exists():
            message.add_attachment(
                attachment.read_bytes(),
                maintype="text",
                subtype="csv",
                filename=attachment.name,
            )

    if smtp_port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as smtp:
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)

    print(f"Email report sent to {email_to}")


def _build_body() -> str:
    sections = ["台股投資建議系統已完成今日自動執行。"]
    if DAILY_REPORT.exists():
        sections.extend(["", "===== 每日報告 =====", DAILY_REPORT.read_text(encoding="utf-8")])
    if WEEKLY_REPORT.exists():
        sections.extend(["", "===== 每週報告 =====", WEEKLY_REPORT.read_text(encoding="utf-8")])
    return "\n".join(sections)


def _build_html_body() -> str:
    daily = _read_csv(DAILY_CSV)
    weekly = _read_csv(WEEKLY_CSV)
    highlights = _daily_highlights(daily)

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <style>
    body {{ margin: 0; padding: 24px; background: #f6f8fb; color: #172033; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .wrap {{ max-width: 1080px; margin: 0 auto; background: #ffffff; border: 1px solid #dde3ec; border-radius: 10px; overflow: hidden; }}
    .header {{ padding: 22px 24px; background: #10233f; color: #ffffff; }}
    .header h1 {{ margin: 0 0 6px; font-size: 22px; font-weight: 700; }}
    .header p {{ margin: 0; color: #d6dfec; font-size: 14px; }}
    .content {{ padding: 22px 24px 28px; }}
    h2 {{ margin: 22px 0 10px; color: #10233f; font-size: 18px; }}
    .summary {{ display: table; width: 100%; border-spacing: 0 8px; margin: 8px 0 12px; }}
    .summary-row {{ display: table-row; }}
    .summary-key, .summary-value {{ display: table-cell; padding: 8px 10px; border-bottom: 1px solid #edf1f6; font-size: 14px; }}
    .summary-key {{ width: 150px; color: #5c6980; font-weight: 700; }}
    .summary-value {{ color: #172033; }}
    table {{ border-collapse: collapse; width: 100%; margin: 8px 0 18px; font-size: 13px; }}
    th {{ background: #eef3f9; color: #24344d; text-align: left; font-weight: 700; border: 1px solid #d8e0eb; padding: 8px; white-space: nowrap; }}
    td {{ border: 1px solid #e1e7f0; padding: 8px; vertical-align: top; }}
    tr:nth-child(even) td {{ background: #fbfcfe; }}
    .action {{ font-weight: 700; }}
    .BUY, .ADD {{ color: #087443; }}
    .REDUCE, .SELL {{ color: #b42318; }}
    .WATCH {{ color: #8a5a00; }}
    .footer {{ padding: 14px 24px; color: #6b7485; background: #f3f6fa; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <h1>台股投資建議報告</h1>
      <p>系統已完成自動執行，以下表格為本次產出的投資建議摘要。</p>
    </div>
    <div class="content">
      <h2>重點摘要</h2>
      {highlights}
      <h2>每日投資建議</h2>
      {_dataframe_to_html(daily, "daily")}
      <h2>每週再平衡建議</h2>
      {_dataframe_to_html(weekly, "weekly")}
    </div>
    <div class="footer">
      此報告為投資決策輔助，不代表自動下單訊號；完整 CSV 已附在信件中。
    </div>
  </div>
</body>
</html>"""


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"ticker": str})


def _daily_highlights(df: pd.DataFrame) -> str:
    if df.empty:
        return "<p>本次沒有每日建議資料。</p>"

    action_counts = df["action"].value_counts().to_dict() if "action" in df.columns else {}
    trade_df = df[df["action"].isin(["BUY", "ADD", "REDUCE", "SELL"])] if "action" in df.columns else pd.DataFrame()
    first_date = str(df["date"].iloc[0]) if "date" in df.columns and not df.empty else ""
    rows = [
        ("報告日期", first_date),
        ("買進/加碼/減碼/賣出", "、".join(f"{key}: {value}" for key, value in action_counts.items()) or "無"),
        ("本次需處理標的數", str(len(trade_df))),
    ]
    html_rows = "\n".join(
        f'<div class="summary-row"><div class="summary-key">{escape(key)}</div><div class="summary-value">{escape(value)}</div></div>'
        for key, value in rows
    )
    return f'<div class="summary">{html_rows}</div>'


def _dataframe_to_html(df: pd.DataFrame, table_type: str) -> str:
    if df.empty:
        return "<p>本次沒有資料。</p>"

    display = _format_dataframe(df, table_type)
    header = "".join(f"<th>{escape(str(column))}</th>" for column in display.columns)
    rows = []
    for _, row in display.iterrows():
        cells = []
        action = str(row.get("建議", row.get("action", "")))
        action_class = escape(action)
        for column, value in row.items():
            class_attr = f' class="action {action_class}"' if column in {"建議", "action"} else ""
            cells.append(f"<td{class_attr}>{escape(str(value))}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _format_dataframe(df: pd.DataFrame, table_type: str) -> pd.DataFrame:
    display = df.copy()
    if table_type == "daily":
        columns = [
            "date",
            "ticker",
            "name",
            "action",
            "current_shares",
            "target_shares",
            "trade_shares",
            "current_weight",
            "target_weight",
            "reason",
            "confidence",
        ]
        rename = {
            "date": "日期",
            "ticker": "代號",
            "name": "名稱",
            "action": "建議",
            "current_shares": "目前股數",
            "target_shares": "目標股數",
            "trade_shares": "建議股數",
            "current_weight": "目前權重",
            "target_weight": "目標權重",
            "reason": "原因",
            "confidence": "信心",
        }
    else:
        columns = [
            "ticker",
            "name",
            "action",
            "current_shares",
            "target_shares",
            "trade_shares",
            "estimated_trade_value",
            "reason",
        ]
        rename = {
            "ticker": "代號",
            "name": "名稱",
            "action": "建議",
            "current_shares": "目前股數",
            "target_shares": "目標股數",
            "trade_shares": "建議股數",
            "estimated_trade_value": "預估交易金額",
            "reason": "原因",
        }

    display = display[[column for column in columns if column in display.columns]].rename(columns=rename)
    for column in ["目前權重", "目標權重", "信心"]:
        if column in display.columns:
            display[column] = display[column].apply(_format_pct)
    if "預估交易金額" in display.columns:
        display["預估交易金額"] = display["預估交易金額"].apply(_format_money)
    for column in ["目前股數", "目標股數", "建議股數"]:
        if column in display.columns:
            display[column] = display[column].apply(_format_integer)
    return display.fillna("")


def _format_pct(value) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(value)


def _format_money(value) -> str:
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def _format_integer(value) -> str:
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


if __name__ == "__main__":
    main()
