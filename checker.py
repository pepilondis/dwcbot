#!/usr/bin/env python3
"""Vigila la disponibilidad de un producto Shopify y avisa por Telegram.

Consulta el endpoint JSON del producto (`<url-producto>.js`), que expone un
campo `available` por variante. Solo envía notificación cuando el producto
pasa de "agotado" a "disponible" (comparando con el estado guardado).
"""
import json
import os
import sys
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
    """Envía un mensaje de prueba para comprobar que las notificaciones llegan."""
    text = (
        "🔔 <b>Mensaje de prueba de dwcbot</b>\n\n"
        "Si estás leyendo esto, ¡las notificaciones funcionan! ✅\n"
        "Te avisaré aquí en cuanto el reloj vuelva a estar disponible.\n\n"
        f'👉 <a href="{PRODUCT_URL}">Ver el producto</a>'
    )
    if send_telegram(text):
        print("Mensaje de prueba enviado.")
        return 0
    print("No se pudo enviar el mensaje de prueba.", file=sys.stderr)
    return 1


def main():
    if os.environ.get("SEND_TEST", "").strip().lower() in ("1", "true", "yes"):
        return send_test_message()

    try:
        product = fetch_product()
    except Exception as e:  # noqa: BLE001 - queremos reintentar en la próxima ejecución
        print(f"No se pudo consultar el producto: {e}", file=sys.stderr)
        return 0  # no tocamos el estado; se reintenta en la siguiente ejecución

    available = bool(product.get("available"))
    title = product.get("title", "Producto")
    available_variants = [v for v in product.get("variants", []) if v.get("available")]

    prev = bool(load_state().get("available", False))
    print(
        f"Estado anterior: {'disponible' if prev else 'agotado'} | "
        f"ahora: {'disponible' if available else 'agotado'}"
    )

    if available and not prev:
        lines = [f"🟢 <b>¡{title} ya está disponible!</b>", ""]
        for v in available_variants:
            lines.append(f"• {v.get('title', 'Variante')} — {format_price(v.get('price', 0))}")
        if available_variants:
            lines.append("")
        lines.append(f'👉 <a href="{PRODUCT_URL}">Comprar ahora</a>')
        if send_telegram("\n".join(lines)):
            print("Notificación enviada.")

    save_state({"available": available, "title": title})
    return 0


if __name__ == "__main__":
    sys.exit(main())
