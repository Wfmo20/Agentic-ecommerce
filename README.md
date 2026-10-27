# Ecommerce Router · agente + API + Telegram

Chat de una tienda online. Cada mensaje del cliente pasa por un **router** (LangGraph + Gemini con salida
estructurada) que decide a qué agente va y por qué:

| Ruta | Cuándo | Nodo |
|---|---|---|
| `preventa` | Quiere comprar o pregunta por productos, precios, tallas, stock, promociones, envío o formas de pago. | `agente_preventa` |
| `postventa` | Ya compró: reclamo, seguimiento de un pedido, devolución, cambio, garantía o producto dañado. | `agente_postventa` |
| `generica` | No tiene que ver con la tienda (clima, chistes, hora…) o es un saludo sin pedido. | `respuesta_generica` |

Preventa y postventa responden con Gemini, cada uno con su propio prompt, sin inventar stock, precios ni estados de pedido.
El router se expone como API (FastAPI), se despliega en **Render** y se conecta a un bot de **Telegram**.
Reglas del proyecto en [AGENTS.md](AGENTS.md).

**En vivo:**
- API: https://agentic-ecommerce-elvj.onrender.com/docs
- Bot de Telegram: [@wilf_mo_bot](https://t.me/wilf_mo_bot)

> Se usa Render (plan gratis) en vez de Heroku, que ya no tiene plan gratis y no acepta tarjetas prepago.
> En el plan gratis la app se duerme tras ~15 min sin uso: la primera respuesta puede tardar ~50 s.

```
src/router/        graph.py · prompts.py · tools.py     ← el agente
api/app.py         API FastAPI (/health, /chat, /telegram)
main.py            ejecutar agentes por consola
scripts/           probar_router.py · test_router.py
tests/             pytest + casos_router.json (15 casos)
bruno/             colección de requests (local ↔ Render)
Procfile · .python-version · requirements.txt        ← despliegue
```

## 1. Preparar

Requisitos: Python 3.12 y una clave de Gemini.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env              # macOS/Linux: cp .env.example .env
```

Completa `.env` (nunca lo subas al repositorio):

| Variable | Para qué | Cuándo |
|---|---|---|
| `GOOGLE_API_KEY` | Clave de Gemini (la lee `langchain-google-genai`) | Desde el inicio |
| `MODELO` | Modelo del router (`gemini-3.5-flash-lite`) | Desde el inicio |
| `TELEGRAM_TOKEN` | Token del bot, lo entrega BotFather | Paso de Telegram |
| `TELEGRAM_SECRET` | Secreto que Telegram envía en cada webhook para que la API lo verifique | Paso de Telegram |
| `PUBLIC_URL` | URL https pública de la app (la de Render) | Después de desplegar |

## 2. Correr el router en local (consola)

```powershell
python main.py router "mi pedido 4521 llegó roto"              # ruta, motivo y respuesta
python main.py router "mi pedido 4521 llegó roto" --saltos     # además: router → <nodo> y el motivo
python main.py router --diagrama                               # diagrama Mermaid, sin ejecutar
```

## 3. Levantar la API

```powershell
uvicorn api.app:app --reload --port 8000
```

- Swagger: <http://localhost:8000/docs> → abre un endpoint → **Try it out** → **Execute**.
- Salud: <http://localhost:8000/health>

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/health` | `{"ok": true, "modelo": "..."}` |
| POST | `/chat` | Recibe `{"user_id", "texto"}` y devuelve `{"ruta", "motivo", "respuesta"}`. Memoria por `user_id`. |
| POST | `/telegram` | Webhook de Telegram (no aparece en el Swagger). |

Errores de `/chat`: **422** si falta `user_id` o `texto` (o vienen vacíos) · **502** si el modelo falla
(el detalle queda en el log del servidor, nunca en la respuesta).

Ejemplo con curl (Git Bash / macOS / Linux):

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "cliente-123", "texto": "¿tienen la polera azul en talla M?"}'
```

Ejemplo en PowerShell (Windows):

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat -ContentType "application/json; charset=utf-8" `
  -Body '{"user_id": "cliente-123", "texto": "¿tienen la polera azul en talla M?"}'
```

Respuesta:

```json
{
  "ruta": "preventa",
  "motivo": "El cliente pregunta por la disponibilidad de un producto y su talla antes de comprar.",
  "respuesta": "¡Hola! Déjame consultar el stock de la polera azul en talla M. ¿Buscas algún modelo en particular?"
}
```

**Bruno (opcional):** Open Collection → carpeta `bruno/`; entorno `local` o `render` (arriba a la derecha).

## 4. Correr las pruebas

```powershell
pytest -v                           # todas las pruebas (tests/)
python scripts/test_router.py       # tabla de los 15 casos: esperado vs obtenido, ✔/✘ y motivo
python scripts/probar_router.py     # los 6 mensajes de ejemplo con su ruta
```

- `tests/test_router.py`: los 15 casos de `tests/casos_router.json`; exige **al menos 13 de 15**
  (el modelo no es determinista; un caso fallado se muestra como `XFAIL`).
- `tests/test_api.py`: `/health`, 422, 502 sin filtrar secretos, `/telegram` y un `/chat` real.
- Las pruebas que llaman al modelo se saltan si no hay `GOOGLE_API_KEY`.

## 5. Desplegar en Render

Todo se hace desde el panel web de [Render](https://render.com) (plan **Free**, no pide tarjeta). Render instala
`requirements.txt` con Python `3.12` (lo lee de `.python-version`). Después de instalar un paquete nuevo:
`pip freeze > requirements.txt`.

1. Entra con **Sign in with GitHub** → **+ New** → **Web Service** → elige este repositorio.
2. Configura:

   | Campo | Valor |
   |---|---|
   | Language | `Python 3` |
   | Branch | `main` |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn api.app:app --host 0.0.0.0 --port $PORT` (el mismo del `Procfile`) |
   | Instance Type | **Free** |

3. En **Environment Variables** agrega `GOOGLE_API_KEY` y `MODELO` (el nombre en **KEY** y el valor en
   **VALUE**) → **Deploy Web Service**.
4. Cuando diga **Live**, copia la URL (`https://NOMBRE-xxxx.onrender.com`, debajo del nombre del servicio)
   y agrégala como `PUBLIC_URL` en **Environment**.

Prueba: `https://NOMBRE-xxxx.onrender.com/health` y `/docs`. En Bruno, elige el entorno `render`.
Cada `git push` a `main` vuelve a desplegar solo; los errores se ven en **Logs**.

> La memoria de las conversaciones (`MemorySaver`) vive en la RAM del servidor: se borra cuando Render
> duerme la app o la vuelve a desplegar.

## 6. Conectar Telegram

1. En Telegram, habla con **@BotFather** → `/newbot` → elige nombre y usuario → copia el **token**.
2. Guárdalo en tu `.env` y en Render (**Environment**) junto con el secreto: `TELEGRAM_TOKEN` y
   `TELEGRAM_SECRET` (una frase larga con letras, números, `-` o `_`). Guarda con **Save, rebuild, and deploy**.
3. Registra el webhook: Telegram enviará cada mensaje a `PUBLIC_URL/telegram`, con el header
   `X-Telegram-Bot-Api-Secret-Token` igual a `TELEGRAM_SECRET`, para que la API verifique que viene de Telegram.
   Git Bash / macOS / Linux:
   ```bash
   curl "https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook" \
     -d "url=<PUBLIC_URL>/telegram" \
     -d "secret_token=<TELEGRAM_SECRET>"
   ```
   PowerShell:
   ```powershell
   Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook" `
     -Body @{ url = "<PUBLIC_URL>/telegram"; secret_token = "<TELEGRAM_SECRET>" }
   ```
4. Revisa que quedó registrado: `https://api.telegram.org/bot<TELEGRAM_TOKEN>/getWebhookInfo`.

> **Cómo funciona `/telegram`:** rechaza con **403** si el header `X-Telegram-Bot-Api-Secret-Token` no
> coincide con `TELEGRAM_SECRET`; si el mensaje trae texto, lo pasa por el router (hilo `telegram-<chat_id>`)
> y le contesta al usuario con `sendMessage`. Stickers, fotos y otros mensajes sin texto se ignoran.
