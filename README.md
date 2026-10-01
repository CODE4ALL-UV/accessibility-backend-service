# accessibility-backend-service
Repositorio Back-end para el módulo Accesibilidad y Adaptación.

| Ruta | Para qué |
|---|---|
| `POST /api/braille/translate` | Convierte celdas Braille (Braille español, grado 1) en texto, celda a celda y con lo que hay que decir en voz alta. |
| `GET /api/youtube/captions` | Los subtítulos de un video de YouTube, traducidos si hay proveedor configurado. |

No usa base de datos ni sesión: traducir Braille no expone datos de nadie, y
exigir sesión dejaría sin teclado justo a quien tiene problemas para iniciarla.

La traducción de subtítulos es opcional: `TRANSLATE_PROVIDER` (`google` o
`deepl`) y `TRANSLATE_API_KEY`. Sin ellas los subtítulos salen en su idioma.

## Cómo lo monta el gateway

`accessibility_service/routes.py` tiene `register(app)`, que añade las rutas de este
servicio a una aplicación de FastAPI. El gateway lo llama para cada servicio, y
`accessibility_service/main.py` hace lo mismo para arrancarlo solo.

## Correrlo

Lo normal es correrlo dentro del gateway (repo `Back-end`), que monta todos
los servicios juntos. Este no usa base de datos ni sesión, así que también
arranca solo, sin ningún otro repositorio:

```powershell
pip install -r requirements.txt
uvicorn accessibility_service.main:app --reload
```

## Pruebas

```bash
pytest tests
```
