# Ecommerce Router · agente + API + Telegram

Chat de una tienda online. Cada mensaje del cliente pasa por un **router** (LangGraph + Gemini con salida
estructurada) que decide a qué agente va y por qué:

| Ruta | Cuándo | Nodo |
|---|---|---|
| `preventa` | Quiere comprar o pregunta por productos, precios, tallas, stock, promociones, envío o formas de pago. | `agente_preventa` |
| `postventa` | Ya compró: reclamo, seguimiento de un pedido, devolución, cambio, garantía o producto dañado. | `agente_postventa` |
| `generica` | No tiene que ver con la tienda (clima, chistes, hora…) o es un saludo sin pedido. | `respuesta_generica` |

Por ahora los agentes destino son **cascarones** (confirman que el mensaje llegó al lugar correcto).
El router se expone como API (FastAPI), se despliega en **Heroku** y se conecta a un bot de **Telegram**.
Reglas del proyecto en [AGENTS.md](AGENTS.md).

```
src/router/        graph.py · prompts.py · tools.py     ← el agente
api/app.py         API FastAPI (/health, /chat, /telegram)
main.py            ejecutar agentes por consola
scripts/           probar_router.py · test_router.py
tests/             pytest + casos_router.json (15 casos)
bruno/             colección de requests (local ↔ Heroku)
Procfile · .python-version · requirements.txt        ← Heroku
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
| `PUBLIC_URL` | URL https pública de la app (la de Heroku) | Después de desplegar |

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
  "respuesta": "Soy el agente de preventa. Recibí: ¿tienen la polera azul en talla M?. Pronto podré ayudarte con productos y compras."
}
```

**Bruno (opcional):** Open Collection → carpeta `bruno/`; entorno `local` o `heroku` (arriba a la derecha).

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

## 5. Desplegar en Heroku

Requisitos: cuenta en Heroku y [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) instalada.
Heroku usa el `Procfile` (`web: uvicorn api.app:app --host 0.0.0.0 --port $PORT`), `.python-version` (`3.12`)
y `requirements.txt`. Después de instalar un paquete nuevo: `pip freeze > requirements.txt`.

```powershell
heroku login
heroku create NOMBRE-DE-TU-APP
heroku config:set GOOGLE_API_KEY=tu_clave MODELO=gemini-3.5-flash-lite TELEGRAM_SECRET=un_secreto_largo
git push heroku main
heroku apps:info                    # copia la "Web URL" (https://...herokuapp.com)
heroku config:set PUBLIC_URL=https://LA-WEB-URL-DE-TU-APP.herokuapp.com
heroku logs --tail                  # ver el log en vivo (Ctrl + C para salir)
```

Prueba: `https://LA-WEB-URL-DE-TU-APP.herokuapp.com/health` y `/docs`.
En Bruno, cambia `TU-APP` en `bruno/environments/heroku.bru` y elige el entorno `heroku`.

## 6. Conectar Telegram

1. En Telegram, habla con **@BotFather** → `/newbot` → elige nombre y usuario → copia el **token**.
2. Guárdalo en Heroku (y en tu `.env` si pruebas en local):
   ```powershell
   heroku config:set TELEGRAM_TOKEN=el_token_de_botfather
   ```
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

> **Estado actual:** `/telegram` recibe el webhook y responde `{"ok": true}`. Verificar el secreto,
> pasar el texto por el router y contestarle al usuario en Telegram se completa en la **parte 5**.
