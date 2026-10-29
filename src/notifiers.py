"""Gửi cảnh báo mail sang Telegram và/hoặc Teams qua webhook."""
import html
import requests


def _fmt(msg, mailbox):
    frm = (msg.get("from") or {}).get("emailAddress", {})
    sender = frm.get("address") or "?"
    name = frm.get("name") or sender
    subj = msg.get("subject") or "(không tiêu đề)"
    prev = (msg.get("bodyPreview") or "")[:500]
    link = msg.get("webLink") or ""
    return name, sender, subj, prev, link


def send_telegram(token, chat_id, msg, mailbox):
    name, sender, subj, prev, link = _fmt(msg, mailbox)
    text = (
        f"📧 <b>{html.escape(subj)}</b>\n"
        f"Từ: {html.escape(name)} &lt;{html.escape(sender)}&gt;\n"
        f"Tới: {html.escape(mailbox)}\n\n"
        f"{html.escape(prev)}"
    )
    if link:
        text += f'\n\n<a href="{html.escape(link)}">Mở mail</a>'
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text,
              "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=20,
    )
    r.raise_for_status()


def send_teams(webhook_url, msg, mailbox):
    name, sender, subj, prev, link = _fmt(msg, mailbox)
    card = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard", "version": "1.4",
                "body": [
                    {"type": "TextBlock", "text": "📧 Mail mới có từ khóa",
                     "weight": "Bolder", "size": "Medium"},
                    {"type": "FactSet", "facts": [
                        {"title": "Tiêu đề:", "value": subj},
                        {"title": "Người gửi:", "value": f"{name} <{sender}>"},
                        {"title": "Tới:", "value": mailbox},
                    ]},
                    {"type": "TextBlock", "text": prev, "wrap": True,
                     "spacing": "Medium"},
                ],
                "actions": ([{"type": "Action.OpenUrl", "title": "Mở mail",
                              "url": link}] if link else []),
            },
        }],
    }
    r = requests.post(webhook_url, json=card, timeout=20)
    r.raise_for_status()
