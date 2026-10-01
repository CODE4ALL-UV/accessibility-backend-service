"""Lo que este microservicio aporta al API Gateway.

El gateway (repo Back-end) llama a `register(app)` de cada servicio, y el
`main.py` de este paquete hace lo mismo para arrancarlo solo. Así las rutas se
declaran una sola vez, se arranque como se arranque.
"""

from fastapi import FastAPI

from accessibility_service.presentation.api.braille_routes import router as braille_router
from accessibility_service.presentation.api.youtube_routes import router as youtube_router


def register(app: FastAPI) -> None:
    app.include_router(braille_router)
    app.include_router(youtube_router)
