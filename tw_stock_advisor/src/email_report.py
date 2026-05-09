from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path


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


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


if __name__ == "__main__":
    main()
