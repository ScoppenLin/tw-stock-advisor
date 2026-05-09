from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Iterable

import gspread
import pandas as pd
from gspread.exceptions import WorksheetNotFound


WORKSHEET_NAMES = {
    "account": "帳戶設定",
    "portfolio": "目前持股",
    "watchlist": "觀察清單",
    "daily_recommendation": "每日建議",
    "weekly_rebalance_plan": "每週再平衡",
    "daily_report": "每日報告",
    "weekly_report": "每週報告",
}


@dataclass
class GoogleSheetsClient:
    spreadsheet_id: str
    client: gspread.Client

    @classmethod
    def from_env(cls) -> "GoogleSheetsClient":
        spreadsheet_id = os.environ.get("GOOGLE_SHEET_ID")
        if not spreadsheet_id:
            raise RuntimeError("GOOGLE_SHEET_ID is required for Google Sheets mode")

        credentials = cls._credentials_from_env()
        client = gspread.service_account_from_dict(credentials)
        return cls(spreadsheet_id=spreadsheet_id, client=client)

    @staticmethod
    def _credentials_from_env() -> dict:
        raw_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        raw_b64 = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_B64")
        file_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")

        if raw_b64:
            try:
                return json.loads(base64.b64decode(raw_b64).decode("utf-8"))
            except (ValueError, json.JSONDecodeError):
                return json.loads(raw_b64)
        if raw_json:
            return json.loads(raw_json)
        if file_path:
            with open(file_path, encoding="utf-8") as handle:
                return json.load(handle)
        raise RuntimeError(
            "Set GOOGLE_SERVICE_ACCOUNT_JSON_B64, GOOGLE_SERVICE_ACCOUNT_JSON, or GOOGLE_SERVICE_ACCOUNT_FILE"
        )

    def read_dataframe(self, worksheet_name: str) -> pd.DataFrame:
        worksheet = self._worksheet(worksheet_name)
        records = worksheet.get_all_records()
        return pd.DataFrame(records)

    def write_dataframe(self, worksheet_name: str, df: pd.DataFrame) -> None:
        worksheet = self._worksheet(worksheet_name, create=True)
        worksheet.clear()
        clean = df.fillna("")
        values = [clean.columns.tolist(), *clean.astype(str).values.tolist()]
        if values:
            worksheet.update(values, "A1")

    def write_lines(self, worksheet_name: str, lines: Iterable[str]) -> None:
        worksheet = self._worksheet(worksheet_name, create=True)
        worksheet.clear()
        values = [["line_no", "text"]]
        values.extend([[index, line] for index, line in enumerate(lines, start=1)])
        worksheet.update(values, "A1")

    def write_sections(self, worksheet_name: str, sections: list[tuple[str, pd.DataFrame]]) -> None:
        worksheet = self._worksheet(worksheet_name, create=True)
        worksheet.clear()
        values: list[list[str]] = []
        for title, df in sections:
            values.append([title])
            if df.empty:
                values.append(["無資料"])
                values.append([])
                continue
            clean = df.fillna("")
            values.append(clean.columns.tolist())
            values.extend(clean.astype(str).values.tolist())
            values.append([])
        worksheet.update(values, "A1")

    def bootstrap_from_csv(self, account: pd.DataFrame, portfolio: pd.DataFrame, watchlist: pd.DataFrame) -> None:
        self.write_dataframe("account", account)
        self.write_dataframe("portfolio", portfolio)
        self.write_dataframe("watchlist", watchlist)

    def _worksheet(self, worksheet_name: str, create: bool = False):
        worksheet_name = WORKSHEET_NAMES.get(worksheet_name, worksheet_name)
        spreadsheet = self.client.open_by_key(self.spreadsheet_id)
        try:
            return spreadsheet.worksheet(worksheet_name)
        except WorksheetNotFound:
            if not create:
                raise
            return spreadsheet.add_worksheet(title=worksheet_name, rows=200, cols=30)
