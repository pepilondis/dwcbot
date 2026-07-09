# dwcbot

Bot de Telegram que te avisa cuando un producto de [Delhi Watch Company](https://delhiwatchcompany.com)
(tienda Shopify) vuelve a estar **disponible**.

Producto vigilado por defecto:
[**DWC Terra**](https://delhiwatchcompany.com/collections/mens-watches/products/dwc-terra).

Funciona con **GitHub Actions** (gratis): un cron revisa la web cada 15 minutos y,
**solo cuando el producto pasa de agotado a disponible**, te envía un mensaje por
Telegram. No hay que dejar nada encendido en tu ordenador.

---

## Cómo funciona

- `checker.py` consulta el JSON del producto (`.../dwc-terra.js`), que Shopify
  expone con el campo `available` de cada variante. Usa solo la librería estándar
  de Python (sin dependencias que instalar).
- Compara con el estado guardado en `state.json`. Si antes estaba agotado y ahora
  está disponible, envía el aviso por Telegram y actualiza `state.json`.
- El workflow `.github/workflows/watch.yml` lo ejecuta con un cron cada 15 min.

---

## Configuración (una sola vez)

### 1. Crea tu bot de Telegram y consigue el token

1. Abre Telegram y habla con [**@BotFather**](https://t.me/BotFather).
2. Envía `/newbot` y sigue los pasos (nombre y usuario del bot).
3. BotFather te dará un **token** parecido a `123456789:AAE...`. Guárdalo.

### 2. Consigue tu Chat ID

1. Abre un chat con tu bot recién creado y envíale cualquier mensaje (p. ej. `hola`).
   > Esto es imprescindible: un bot no puede escribirte hasta que tú le escribas primero.
2. En el navegador, abre esta URL (sustituyendo `<TOKEN>` por tu token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Busca en la respuesta `"chat":{"id":123456789,...}`. Ese número es tu **Chat ID**.

### 3. Añade los secretos al repositorio

En GitHub: **Settings → Secrets and variables → Actions → New repository secret**.
Crea estos dos:

| Nombre                | Valor                          |
| --------------------- | ------------------------------ |
| `TELEGRAM_BOT_TOKEN`  | El token de BotFather          |
| `TELEGRAM_CHAT_ID`    | Tu Chat ID (solo el número)    |

### 4. Activa el cron (fusiona a la rama principal)

⚠️ **Importante:** GitHub solo ejecuta los cron programados desde la rama
**por defecto** (`main`). Este código está en la rama `claude/telegram-watch-bot-1i94t1`,
así que para que el aviso automático funcione debes **fusionar esta rama a `main`**
(por ejemplo, mediante un Pull Request).

### 5. Pruébalo manualmente

En la pestaña **Actions** del repositorio, elige el workflow
_"Vigilar disponibilidad (DWC Terra)"_ y pulsa **Run workflow**.
- Si el producto está agotado, no recibirás nada (correcto).
- Para probar el envío de Telegram, edita temporalmente `state.json` poniendo
  `"available": false` y, si el producto estuviera disponible, recibirías el aviso.

---

## Personalización

Puedes cambiar el producto o el intervalo sin tocar la lógica:

- **Otro producto**: edita las variables `PRODUCT_JS_URL` y `PRODUCT_URL` al
  principio de `checker.py` (o pásalas como variables de entorno en el workflow).
  Regla general: la URL del producto Shopify + `.js` es el endpoint JSON.
- **Otra frecuencia**: cambia la línea `cron: "*/15 * * * *"` en
  `.github/workflows/watch.yml`. Ejemplos: `*/30 * * * *` (cada 30 min),
  `0 * * * *` (cada hora). El mínimo que permite GitHub es 5 minutos.

---

## Ejecutarlo en tu propio ordenador (opcional)

Si prefieres no usar GitHub Actions:

```bash
export TELEGRAM_BOT_TOKEN="tu_token"
export TELEGRAM_CHAT_ID="tu_chat_id"
python checker.py   # ejecútalo con cron/Task Scheduler cada X minutos
```

El estado se guarda en `state.json` en el mismo directorio.
