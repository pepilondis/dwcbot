# dwcbot

Bot de Telegram que te avisa cuando un producto de [Delhi Watch Company](https://delhiwatchcompany.com)
(tienda Shopify) vuelve a estar **disponible**.

Producto vigilado por defecto:
[**DWC Terra**](https://delhiwatchcompany.com/collections/mens-watches/products/dwc-terra).

Funciona con **GitHub Actions** (gratis): un cron revisa la web cada 5 minutos y,
**mientras el producto esté disponible**, te envía 10 mensajes seguidos por
Telegram en cada comprobación (hasta que se agote). No hay que dejar nada
encendido en tu ordenador.

---

## Cómo funciona

- `checker.py` consulta el JSON del producto (`.../dwc-terra.js`), que Shopify
  expone con el campo `available` de cada variante. Usa solo la librería estándar
  de Python (sin dependencias que instalar).
- Mientras esté disponible, en **cada** comprobación envía `NOTIFY_REPEAT` mensajes
  (10 por defecto) y deja de avisar cuando vuelve a agotarse.
- El workflow `.github/workflows/watch.yml` lo ejecuta con un cron cada 5 min.

### Salvaguardas de fiabilidad

- **🫀 Latido diario**: cada día a las **10:00 (hora de España)** te llega un
  mensaje confirmando que el bot sigue vivo e indicando el estado actual. Si un día
  no llega, es señal de que algo va mal. También mantiene activo el cron (GitHub
  desactiva los workflows programados tras 60 días sin actividad en el repo).
- **🚨 Aviso de error**: si la web falla `FAIL_THRESHOLD` veces seguidas (3 por
  defecto, ~15 min), te avisa por Telegram de que no puede consultarla.
- **📧 Email de GitHub**: ante ese fallo persistente el workflow termina en rojo,
  y GitHub te envía un email automático (revisa que tengas activadas las
  notificaciones de Actions en *Settings → Notifications*).

> Nota sobre la hora: el cron de GitHub va en UTC y no ajusta el cambio de hora,
> así que el latido llega a las 10:00 en horario de verano y a las 09:00 en
> invierno.

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
