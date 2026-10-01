"""Arranca solo este microservicio, sin el gateway.

Sirve para desarrollarlo o desplegarlo por separado. En producción lo monta el
API Gateway (repo Back-end) junto a los demás. No usa base de datos ni sesión,
así que no depende de ningún otro repositorio:

    uvicorn accessibility_service.main:app --reload
"""

from dotenv import load_dotenv

# El .env de este repositorio, antes de importar nada que lea variables.
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from accessibility_service.routes import register

app = FastAPI(title="Accessibility Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register(app)
