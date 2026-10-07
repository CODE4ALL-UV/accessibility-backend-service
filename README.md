# accessibility-backend-service · Accesibilidad y adaptación

Este es el microservicio de **accesibilidad y adaptación** de Code4All. Tiene
dos trabajos concretos, pensados para que el curso de Python lo pueda seguir
alguien que no ve la pantalla o que no oye el audio de los videos:

1. **Pasar de Braille a texto.** La app tiene un teclado Braille de seis
   puntos. Cuando el estudiante confirma una celda, la app manda los puntos a
   este servicio y recibe de vuelta la letra y la forma de decirla en voz alta.
2. **Traer los subtítulos de los videos de YouTube.** Los videos del curso
   están en YouTube. El servicio descarga sus subtítulos con el tiempo de cada
   frase y, si hay un traductor configurado, los pasa al español.

No guarda nada. No usa base de datos ni sesión y no depende de ningún otro
repositorio para funcionar.

## A quién le sirve

- **Estudiantes ciegos o con baja visión**, que escriben con el teclado
  Braille. El teclado aparece también en la pantalla de inicio de sesión, para
  que puedan escribir su correo y su contraseña sin ayuda de nadie.
- **Estudiantes sordos o con hipoacusia**, y cualquiera que no entienda el
  idioma del video, que siguen la clase leyendo los subtítulos.

## 1. Braille a texto: `POST /api/braille/translate`

La app no traduce nada por su cuenta: manda las celdas tal como las escribió la
persona y aquí se decide qué significan. Así la tabla Braille vive en un solo
lugar y se puede probar.

### Qué se le manda

Una lista de celdas. Cada celda es la lista de puntos levantados, numerados del
1 al 6 como en la regleta:

```
1 ● ● 4
2 ● ● 5
3 ● ● 6
```

```json
{ "cells": [[1, 2, 5], [1, 3, 5], [1, 2, 3], [1]] }
```

- Una celda vacía, `[]`, es un espacio.
- El orden y las repeticiones dentro de una celda dan igual: `[5, 2, 1, 1]` es
  lo mismo que `[1, 2, 5]`.
- Se pueden mandar hasta **2000 celdas** por petición.

### Qué devuelve

El texto completo y, celda por celda, qué se entendió y cómo leerlo en voz
alta. Esto último es lo importante: quien escribe en Braille con la app
normalmente no ve la pantalla, y necesita oír qué acaba de confirmar.

```json
{
  "text": "Hola",
  "cells": [
    { "index": 0, "dots": [4, 6],    "kind": "capital_sign", "value": "",  "spoken": "mayúscula" },
    { "index": 1, "dots": [1, 2, 5], "kind": "letter",       "value": "H", "spoken": "H mayúscula" },
    { "index": 2, "dots": [1, 3, 5], "kind": "letter",       "value": "o", "spoken": "o" },
    { "index": 3, "dots": [1, 2, 3], "kind": "letter",       "value": "l", "spoken": "l" },
    { "index": 4, "dots": [1],       "kind": "letter",       "value": "a", "spoken": "a" }
  ],
  "unrecognized": []
}
```

- `kind` puede ser `letter`, `digit`, `punctuation`, `capital_sign`,
  `number_sign`, `space` o `unknown`.
- `value` es lo que la celda aporta al texto. Va vacío en los signos que solo
  cambian lo que viene después (mayúscula y número) y en las celdas que no se
  reconocen.
- `unrecognized` son los índices de las celdas que no corresponden a nada. No
  se inventa una letra: se avisa con `"combinación no reconocida, puntos 4, 5"`
  para que la persona la corrija.

### Qué Braille entiende

Es **Braille español de grado 1** (sin contracciones), con la signografía de la
Comisión Braille Española, que es la que se usa en América Latina. La tabla
está escrita a mano en
`accessibility_service/application/services/braille_translator.py`; no usa
ninguna librería externa.

| Qué | Cómo se escribe |
|---|---|
| Letras de la a a la z | Tabla estándar. La `ñ` (12456) y la `w` (2456) van aparte, como en el Braille español. |
| Vocales con tilde y ü | `á` 12356, `é` 2346, `í` 34, `ó` 346, `ú` 23456, `ü` 1256 |
| Mayúscula | Signo 46 antes de la letra. Dos 46 seguidos ponen en mayúscula toda la palabra, hasta el siguiente espacio o signo de puntuación. |
| Números | Signo 3456 y después las letras de la `a` a la `j`, que pasan a ser 1‑9 y 0. Siguen siendo números hasta un espacio, una letra que no sea de la a a la j o un signo. El punto y la coma dentro del número (`1.000`, `3,5`) no lo cortan. |
| Puntuación | `.` 3, `,` 2, `;` 23, `:` 25, `?` 26, `!` 235, `"` 236, `(` 126, `)` 345, `-` 36 |
| Arroba | `@` en el punto 5. La añadimos para poder escribir el correo en el login. |

En Braille, la interrogación y la exclamación sirven para abrir y para cerrar.
Aquí se escribe siempre la de cierre (`?`, `!`), que es la que se entiende sin
contexto.

Solo va en un sentido, de Braille a texto. No hay conversión de texto a
Braille.

### Errores

| Código | Cuándo |
|---|---|
| 413 | Llegaron más de 2000 celdas. |
| 422 | Algún punto está fuera del 1 al 6 (`"Los puntos van del 1 al 6; llegó [7]."`) o el cuerpo no tiene la forma esperada. |

## 2. Subtítulos de YouTube: `GET /api/youtube/captions`

```
GET /api/youtube/captions?video_id=dQw4w9WgXcQ&target=es
```

- `video_id` es obligatorio y es **solo el identificador** del video, no la URL
  completa.
- `target` es el idioma al que se traducen los subtítulos. Por defecto, `es`.

Devuelve una lista de frases con su tiempo, que es lo que el reproductor de la
app va mostrando debajo del video:

```json
{
  "cues": [
    { "start": 0.0, "duration": 3.2, "text": "Welcome to the course", "translated": "Bienvenidos al curso" },
    { "start": 3.2, "duration": 2.8, "text": "Let's start with variables", "translated": "Empecemos con las variables" }
  ]
}
```

### Cómo consigue los subtítulos

1. Los descarga con la librería
   [`youtube-transcript-api`](https://pypi.org/project/youtube-transcript-api/)
   (versión 1.x). Busca en este orden: inglés, español, francés y alemán. En
   cada idioma prefiere los subtítulos escritos por una persona a los
   automáticos. El parámetro `target` no cambia qué idioma se descarga.
2. Si están configuradas `TRANSLATE_PROVIDER` y `TRANSLATE_API_KEY`, traduce
   las frases en grupos de 20 y añade el campo `translated`. Con `deepl` usa
   DeepL; con cualquier otro valor (normalmente `google`) usa Google Translate
   v2. Cada llamada espera como mucho 15 segundos.
3. Si la traducción de un grupo falla, esas frases salen sin `translated` y el
   resto sigue. La app muestra `translated` cuando existe y si no, el texto
   original.

### Errores

- Si el video tiene los subtítulos desactivados, responde **404**.
- Cualquier otro problema (el video no existe, no hay subtítulos en ninguno de
  esos cuatro idiomas, YouTube bloquea la petición, falla la red) responde
  **200 con `{"cues": []}`** y el detalle queda en el log del servidor. Para la
  app, en ese caso, el video simplemente no tiene subtítulos.

## Por qué no pide sesión

Ninguna de las dos rutas pide token. Traducir Braille no expone datos de nadie,
y exigir sesión dejaría sin teclado justo a quien tiene problemas para iniciar
sesión. Los subtítulos tampoco son información privada.

## Dónde lo usa la app

En el repositorio [Front-end](https://github.com/CODE4ALL-UV/Front-end):

- `lib/data/services/braille_translation_service.dart` llama a la traducción
  Braille (espera como mucho 8 segundos). La usan el teclado
  (`lib/ui/core/ui/braille_keyboard_screen.dart`), la pantalla de login y el
  menú de perfil.
- `lib/youtube_translator_player.dart` pide los subtítulos con `target: 'es'`.
  Lo usan el reproductor de video y las secciones de video del curso.

## Cómo lo monta el gateway

Todos los servicios de Code4All siguen el mismo contrato:
`accessibility_service/routes.py` tiene una función `register(app)` que añade
las rutas de este servicio a una aplicación de FastAPI. El
[gateway](https://github.com/CODE4ALL-UV/Back-end) trae este repositorio como
submódulo en `services/` y llama a esa función al arrancar.
`accessibility_service/main.py` hace lo mismo para correrlo solo.

## Estructura

```
accessibility_service/
├── routes.py                     register(app): lo único que llama el gateway
├── main.py                       arranque independiente (lee el .env)
├── application/services/
│   └── braille_translator.py     tabla Braille y reglas de mayúscula y número
└── presentation/api/
    ├── braille_routes.py         POST /api/braille/translate
    └── youtube_routes.py         GET /api/youtube/captions y la traducción
tests/
├── conftest.py
└── test_braille.py
```

## Variables de entorno

| Variable | Para qué | ¿Obligatoria? |
|---|---|---|
| `TRANSLATE_PROVIDER` | `deepl` o `google`. Sin ella, los subtítulos salen en su idioma original. | No |
| `TRANSLATE_API_KEY` | La clave del proveedor anterior. Hacen falta las dos para traducir. | No |

Están en `.env.example`. En Render hay que añadirlas a mano en el servicio del
gateway: el `render.yaml` no las declara, así que si no se ponen, los
subtítulos no se traducen.

## Correrlo

Lo normal es correrlo dentro del gateway (repo `Back-end`), que monta todos
los servicios juntos. Como este no usa base de datos ni sesión, también
arranca solo, sin ningún otro repositorio:

```powershell
pip install -r requirements.txt
copy .env.example .env
uvicorn accessibility_service.main:app --reload
```

La documentación interactiva queda en `http://127.0.0.1:8000/docs`.

## Pruebas

```powershell
pytest tests
```

`tests/test_braille.py` tiene 16 pruebas del traductor: palabras, la celda
vacía como espacio, ñ y tildes, el orden de los puntos, la mayúscula de una
letra y de toda la palabra, los números con su separador decimal, la
puntuación, las combinaciones que no existen, lo que se lee en voz alta, los
puntos fuera de rango y un correo completo con arroba y números. Los
subtítulos no tienen pruebas, porque dependerían de YouTube.

En GitHub, cada push o pull request a `main` corre las pruebas con cobertura y
la sube a Codacy (`.github/workflows/codacy-coverage.yml`).

## Cosas a tener en cuenta

- Con el signo de número activo, las letras de la a a la j siguen siendo
  dígitos hasta que llegue un espacio o un signo. Para escribir `1a` hay que
  separarlos.
- Los signos que no están en la tabla (`/`, `*`, `+`, `=`, `¿`, `¡`…) salen
  como `unknown`.
- Las dependencias de `requirements.txt` no tienen versión fija. El código de
  subtítulos usa la forma de `youtube-transcript-api` 1.x
  (`YouTubeTranscriptApi().fetch(...)`); con una versión anterior no funciona.
- El `main.py` independiente abre CORS a cualquier origen. Es solo para
  desarrollo; en producción manda la configuración del gateway.

## Los repositorios de Code4All

| Parte | Repositorio |
|---|---|
| App (Flutter) | [Front-end](https://github.com/CODE4ALL-UV/Front-end) |
| API Gateway | [Back-end](https://github.com/CODE4ALL-UV/Back-end) |
| Gestión de usuarios | [user-management-backend-service](https://github.com/CODE4ALL-UV/user-management-backend-service) |
| Curso y contenidos de Python | [course-content-backend-service](https://github.com/CODE4ALL-UV/course-content-backend-service) |
| Ejercicios y evaluación | [assessment-backend-service](https://github.com/CODE4ALL-UV/assessment-backend-service) |
| Progreso y seguimiento | [progress-tracking-backend-service](https://github.com/CODE4ALL-UV/progress-tracking-backend-service) |
| **Accesibilidad y adaptación** | **este repositorio** |
| Interacción multimodal | [multimodal-interaction-backend-service](https://github.com/CODE4ALL-UV/multimodal-interaction-backend-service) |
| Infraestructura y dispositivos | [device-management-backend-service](https://github.com/CODE4ALL-UV/device-management-backend-service) |
| Capa de datos compartida (Neon) | [neon-storage-backend-service](https://github.com/CODE4ALL-UV/neon-storage-backend-service) |
