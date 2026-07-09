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

### Los tres tipos de aviso (todos por Telegram)

1. **🟢 Disponible → 10 mensajes**: mientras el reloj esté disponible, en cada
   comprobación (cada 5 min) envía 10 notificaciones seguidas para que no pase
   desapercibido. Se detiene cuando vuelve a agotarse.
2. **🫀 Latido diario → 1 mensaje**: cada día a las **10:00 (hora de España)**
   confirma que el bot sigue vivo e indica el estado actual. Si un día no llega,
   es señal de que algo va mal. También mantiene activo el cron (GitHub desactiva
   los workflows programados tras 60 días sin actividad en el repo).
3. **⚠️ Error → 1 mensaje**: si la web falla `FAIL_THRESHOLD` veces seguidas
   (3 por defecto, ~15 min), avisa una vez de que no puede consultarla. El job
   siempre termina en verde: todos los avisos van por Telegram (sin emails).

> Nota sobre la hora: el cron de GitHub va en UTC y no ajusta el cambio de hora,
> así que el latido llega a las 10:00 en horario de verano y a las 09:00 en
> invierno.

---

## Vigilancia del newsletter por correo (opcional)

Además de la web, el bot puede vigilar un **buzón de correo** y avisarte por
Telegram cuando llega un email (por ejemplo, el newsletter de Delhi Watch
anunciando disponibilidad). Lo gestiona `email_checker.py` vía IMAP.

Queda **inactivo** hasta que añadas los secretos `IMAP_USER` e `IMAP_PASSWORD`;
sin ellos, el paso no hace nada (no falla). Funciona con **cualquier proveedor
IMAP** (Gmail, Outlook, Yahoo, iCloud, Zoho, GMX…), no solo Gmail.

### Configuración (usa una cuenta DEDICADA — recomendado)

1. **Crea una cuenta de correo nueva** usada solo para esto (no tu correo
   personal). Así, aunque la contraseña se filtrara, no afecta a tu correo real.
2. **Suscríbete al newsletter** de Delhi Watch Company con esa cuenta.
3. Consigue una **contraseña para IMAP**. En casi todos los proveedores conviene
   activar la verificación en 2 pasos y generar una **contraseña de aplicación**
   (no tu contraseña normal). En algunos (GMX, Zoho) basta con activar IMAP.
4. En GitHub → *Settings → Secrets and variables → Actions*, añade:

   | Secreto         | Valor                                                   |
   | --------------- | ------------------------------------------------------- |
   | `IMAP_USER`     | la dirección de correo dedicada                         |
   | `IMAP_PASSWORD` | la contraseña de aplicación / IMAP                      |
   | `IMAP_HOST`     | el servidor IMAP del proveedor (ver tabla; Gmail no lo necesita) |

A partir de ahí, cada 5 minutos el bot revisa el buzón y te avisa por Telegram
de cada correo nuevo con su remitente y asunto, marcándolo como leído.

### Servidor IMAP según proveedor (`IMAP_HOST`)

| Proveedor        | `IMAP_HOST`               | Carpeta de spam (`IMAP_MAILBOXES`) |
| ---------------- | ------------------------- | ---------------------------------- |
| Gmail (defecto)  | `imap.gmail.com`          | `INBOX,[Gmail]/Spam`               |
| Outlook / Hotmail| `outlook.office365.com`   | `INBOX,Junk`                       |
| Yahoo            | `imap.mail.yahoo.com`     | `INBOX,Bulk Mail`                  |
| iCloud           | `imap.mail.me.com`        | `INBOX,Junk`                       |
| Zoho             | `imap.zoho.com` (o `.eu`) | `INBOX,Spam`                       |
| GMX              | `imap.gmx.com`            | `INBOX,Spam`                       |

### Ajustes opcionales (variables de entorno / secretos)

- `IMAP_HOST`: servidor IMAP (por defecto `imap.gmail.com`).
- `IMAP_MAILBOXES`: buzones a revisar (por defecto `INBOX,[Gmail]/Spam`). Para
  otros proveedores usa la carpeta de spam de la tabla.
- `EMAIL_FROM_FILTER`: si recibes ruido, ponlo a `delhiwatch` para avisar solo de
  correos de ese remitente. Por defecto (vacío) avisa de cualquier correo nuevo.

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
