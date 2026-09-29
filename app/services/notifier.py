from __future__ import annotations

import os
from datetime import datetime

import requests


class TelegramNotifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, jobs: list[dict]) -> tuple[bool, str | None]:
        if not jobs:
            return True, None
        if not self.configured:
            return False, "Telegram is not configured"
        lines = []
        for job in jobs:
            lines.append(
                f"• <b>{_escape(job['title'])}</b> — {_escape(job['company'])}\n"
                f"  Prioridad {job['priority_score']} · Factibilidad {job['application_feasibility']}\n"
                f"  <a href=\"{job['source_url']}\">Ver oferta</a>"
            )
        text = (
            f"🔎 <b>Job Searcher V2</b> · {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"{len(jobs)} oportunidades priorizadas\n\n" + "\n\n".join(lines)
        )
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={
                    "chat_id": int(self.chat_id),
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            response.raise_for_status()
            return True, None
        except Exception as exc:
            return False, str(exc)


def _escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
