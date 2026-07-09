#!/usr/bin/env python3
"""Vigila un buzón por IMAP y avisa por Telegram de cada correo nuevo.

Pensado para una cuenta de Gmail DEDICADA (suscrita solo al newsletter de
Delhi Watch Company). Revisa los correos sin leer, avisa por Telegram con el
remitente y el asunto, y los marca como leídos para no repetir.

El "estado" de leído/no leído vive en el propio servidor de correo, así que no
hace falta guardarlo aquí; solo se persiste un contador de fallos de conexión
(email_state.json) para no avisar por cortes puntuales.

Usa solo la librería estándar de Python.
"""
import imaplib
import json
import os
import sys
import urllib.error
import urllib.request
from email import message_from_bytes
from email.header import decode_header, make_header

# --- Configuración (variables de entorno) ---
IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
IMAP_USER = os.environ.get("IMAP_USER")
IMAP_PASSWORD = os.environ.get("IMAP_PASSWORD")

# Buzones a revisar. En Gmail el spam es "[Gmail]/Spam" (por si el newsletter
# cae ahí). Los que no existan se ignoran sin fallar.
MAILBOXES = [m.strip() for m in os.environ.get(
    "IMAP_MAILBOXES", "INBOX,[Gmail]/Spam").split(",") if m.strip()]

# Filtro opcional por remitente (subcadena). Vacío = avisar de cualquier correo
# nuevo (recomendado en una cuenta dedicada, para no perderse el aviso aunque el
# newsletter llegue desde un dominio de terceros tipo klaviyomail/shopifyemail).
FROM_FILTER = os.environ.get("EMAIL_FROM_FILTER", "").strip().lower()

STATE_FILE = os.environ.get("EMAIL_STATE_FILE", "email_state.json")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PRODUCT_URL = os.environ.get(
    "PRODUCT_URL",
    "https://delhiwatchcompany.com/collections/mens-watches/products/dwc-terra",
)

try:
    FAIL_THRESHOLD = max(1, int(os.environ.get("EMAIL_FAIL_THRESHOLD", "3")))
except ValueError:
    FAIL_THRESHOLD = 3


def decode_hdr(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:  # noqa: BLE001
        return value


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"fail_streak": 0}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID", file=sys.stderr)
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps(
        {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML",
         "disable_web_page_preview": True}
    ).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        return True
    except urllib.error.HTTPError as e:
        print(f"ERROR Telegram: {e.code} {e.read().decode(errors='replace')}", file=sys.stderr)
        return False


def escape(text):
    """Escapa caracteres especiales de HTML para el mensaje de Telegram."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def check_mailbox(imap, mailbox):
    """Revisa un buzón; devuelve el nº de correos nuevos por los que se avisó."""
    typ, _ = imap.select(mailbox, readonly=False)
    if typ != "OK":
        print(f"(buzón no disponible, se omite: {mailbox})")
        return 0

    typ, data = imap.search(None, "UNSEEN")
    if typ != "OK" or not data or not data[0]:
        return 0

    alerted = 0
    for num in data[0].split():
        typ, msgdata = imap.fetch(num, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        if typ != "OK" or not msgdata or not msgdata[0]:
            continue
        msg = message_from_bytes(msgdata[0][1])
        frm = decode_hdr(msg.get("From"))
        subject = decode_hdr(msg.get("Subject")) or "(sin asunto)"
        date = decode_hdr(msg.get("Date"))

        if FROM_FILTER and FROM_FILTER not in frm.lower():
            # No es lo que buscamos: lo dejamos SIN leer y no avisamos.
            continue

        text = (
            "📧 <b>¡Correo nuevo en el buzón de Delhi Watch!</b>\n\n"
            f"<b>De:</b> {escape(frm)}\n"
            f"<b>Asunto:</b> {escape(subject)}\n"
            f"<b>Fecha:</b> {escape(date)}\n\n"
            "Puede anunciar disponibilidad. Revisa el correo o la web.\n"
            f'👉 <a href="{PRODUCT_URL}">Ver el producto</a>'
        )
        if send_telegram(text):
            alerted += 1
            imap.store(num, "+FLAGS", "\\Seen")  # marcar como leído
    return alerted


def main():
    if not IMAP_USER or not IMAP_PASSWORD:
        print("Vigilancia de correo desactivada (faltan IMAP_USER/IMAP_PASSWORD).")
        return 0

    state = load_state()
    fail_streak = int(state.get("fail_streak", 0) or 0)

    imap = None
    try:
        imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        imap.login(IMAP_USER, IMAP_PASSWORD)
        total = 0
        for mailbox in MAILBOXES:
            try:
                total += check_mailbox(imap, mailbox)
            except Exception as e:  # noqa: BLE001 - un buzón no debe tumbar el resto
                print(f"Aviso al revisar {mailbox}: {e}", file=sys.stderr)
        print(f"Correo revisado. Nuevos avisados: {total}.")
        save_state({"fail_streak": 0})
        return 0
    except Exception as e:  # noqa: BLE001
        fail_streak += 1
        print(f"No se pudo revisar el correo (fallo {fail_streak}): {e}", file=sys.stderr)
        save_state({"fail_streak": fail_streak})
        if fail_streak == FAIL_THRESHOLD:
            send_telegram(
                "⚠️ <b>dwcbot</b>: no consigo revisar el buzón de correo "
                f"({fail_streak} intentos fallidos seguidos). Revisa las credenciales IMAP."
            )
        return 0  # siempre verde: los avisos van por Telegram
    finally:
        if imap is not None:
            try:
                imap.logout()
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    sys.exit(main())
