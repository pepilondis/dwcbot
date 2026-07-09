#!/usr/bin/env python3
"""Vigila la disponibilidad de un producto Shopify y avisa por Telegram.

Consulta el endpoint JSON del producto (`<url-producto>.js`), que expone un
campo `available` por variante. Mientras el producto esté disponible, en cada
comprobación envía NOTIFY_REPEAT mensajes seguidos por Telegram (10 por defecto),
y deja de avisar cuando vuelve a agotarse.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

# --- Configuración (se puede sobrescribir con variables de entorno) ---

# Endpoint JSON de Shopify (añade .js a la URL del producto).
PRODUCT_JS_URL = os.environ.get(
    "PRODUCT_JS_URL",
    "https://delhiwatchcompany.com/products/dwc-terra.js",
)

# URL "bonita" que se incluye en el mensaje de aviso.
PRODUCT_URL = os.environ.get(
    "PRODUCT_URL",
    "https://delhiwatchcompany.com/collections/mens-watches/products/dwc-terra",
)

STATE_FILE = os.environ.get("STATE_FILE", "state.json")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Cuántos mensajes seguidos enviar en cada comprobación mientras esté disponible.
try:
    NOTIFY_REPEAT = max(1, int(os.environ.get("NOTIFY_REPEAT", "10")))
except ValueError:
    NOTIFY_REPEAT = 10

# Tras cuántos fallos SEGUIDOS al consultar la web avisamos y ponemos el job en
# rojo (para que GitHub mande email). 3 fallos ≈ 15 min de web caída/bloqueada.
try:
    FAIL_THRESHOLD = max(1, int(os.environ.get("FAIL_THRESHOLD", "3")))
except ValueError:
    FAIL_THRESHOLD = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; dwcbot/1.0)",
    "Accept": "application/json",
}


def fetch_product():
    """Descarga y parsea el JSON del producto."""
    req = urllib.request.Request(PRODUCT_JS_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_state():
    """Lee el estado previo; si no existe, asume 'agotado'."""
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"available": False}


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
        {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        return True
    except urllib.error.HTTPError as e:
        print(f"ERROR Telegram: {e.code} {e.read().decode(errors='replace')}", file=sys.stderr)
        return False


def format_price(cents):
    try:
        return f"${int(cents) / 100:,.2f}"
    except (TypeError, ValueError):
        return "precio n/d"


def send_test_message():
    """Envía NOTIFY_REPEAT mensajes de prueba (como el aviso real) para
    comprobar que llegan y que el móvil suena lo suficiente."""
    body = (
        "🔔 <b>Prueba de dwcbot</b>\n\n"
        "Si recibes esto, ¡las notificaciones funcionan! ✅\n"
        "Cuando el reloj esté disponible te llegarán así, 10 seguidas.\n\n"
        f'👉 <a href="{PRODUCT_URL}">Ver el producto</a>'
    )
    sent = 0
    for i in range(1, NOTIFY_REPEAT + 1):
        if send_telegram(f"({i}/{NOTIFY_REPEAT})\n{body}"):
            sent += 1
        if i < NOTIFY_REPEAT:
            time.sleep(1)
    print(f"Prueba: enviados {sent}/{NOTIFY_REPEAT} mensajes.")
    return 0 if sent == NOTIFY_REPEAT else 1


def notify_available(title, available_variants):
    """Envía NOTIFY_REPEAT mensajes seguidos anunciando que está disponible."""
    base = [f"🟢 <b>¡{title} ya está disponible!</b>", ""]
    for v in available_variants:
        base.append(f"• {v.get('title', 'Variante')} — {format_price(v.get('price', 0))}")
    if available_variants:
        base.append("")
    base.append(f'👉 <a href="{PRODUCT_URL}">Comprar ahora</a>')
    body = "\n".join(base)

    sent = 0
    for i in range(1, NOTIFY_REPEAT + 1):
        # Numeramos cada mensaje para que Telegram no los agrupe y se distingan.
        if send_telegram(f"({i}/{NOTIFY_REPEAT})\n{body}"):
            sent += 1
        if i < NOTIFY_REPEAT:
            time.sleep(1)  # pequeña pausa para no saturar la API de Telegram
    print(f"Disponible: enviados {sent}/{NOTIFY_REPEAT} mensajes.")


def main():
    if os.environ.get("SEND_TEST", "").strip().lower() in ("1", "true", "yes"):
        return send_test_message()

    heartbeat = os.environ.get("HEARTBEAT", "").strip().lower() in ("1", "true", "yes")
    state = load_state()
    prev = bool(state.get("available", False))
    fail_streak = int(state.get("fail_streak", 0) or 0)

    try:
        product = fetch_product()
    except Exception as e:  # noqa: BLE001
        fail_streak += 1
        print(f"No se pudo consultar la web (fallo {fail_streak}): {e}", file=sys.stderr)
        # Guardamos el contador y conservamos el último estado conocido.
        save_state({"available": prev, "title": state.get("title", ""), "fail_streak": fail_streak})
        # Al alcanzar el umbral, avisamos por Telegram (una vez) y ponemos el job
        # en rojo para que GitHub mande el email de fallo.
        if fail_streak == FAIL_THRESHOLD:
            send_telegram(
                "⚠️ <b>dwcbot</b>: no consigo consultar la web "
                f"({fail_streak} intentos fallidos seguidos). Puede ser un problema "
                "temporal, pero conviene revisar el bot."
            )
        return 1 if fail_streak >= FAIL_THRESHOLD else 0

    # Consulta correcta → reiniciamos el contador de fallos.
    available = bool(product.get("available"))
    title = product.get("title", "Producto")
    available_variants = [v for v in product.get("variants", []) if v.get("available")]

    print(
        f"Estado anterior: {'disponible' if prev else 'agotado'} | "
        f"ahora: {'disponible' if available else 'agotado'} | latido: {heartbeat}"
    )

    # Latido diario: confirma que el bot sigue vivo e informa del estado actual.
    if heartbeat:
        estado = "🟢 <b>disponible</b>" if available else "🔴 agotado"
        send_telegram(
            f"🫀 <b>dwcbot sigue vigilando.</b>\nEstado actual: {estado}.\n\n"
            f'👉 <a href="{PRODUCT_URL}">Ver el producto</a>'
        )
        print("Latido diario enviado.")

    # Mientras esté disponible, avisamos en CADA comprobación (no solo al cambiar).
    if available:
        notify_available(title, available_variants)

    save_state({"available": available, "title": title, "fail_streak": 0})
    return 0


if __name__ == "__main__":
    sys.exit(main())
