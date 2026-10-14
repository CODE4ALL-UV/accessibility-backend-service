"""El servicio arrancado solo, sin el gateway.

Comprueba que `main.py` monta las mismas rutas que usa el gateway y que el
límite de celdas del teclado Braille se respeta por las dos vías.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from accessibility_service.application.services.braille_translator import (
    MAX_CELLS,
    translate,
)
from accessibility_service.main import app
from accessibility_service.routes import register

client = TestClient(app)


def test_register_mounts_braille_and_youtube():
    gateway = FastAPI()
    register(gateway)

    paths = gateway.openapi()["paths"]
    assert "/api/braille/translate" in paths
    assert "/api/youtube/captions" in paths


def test_translate_endpoint_over_http():
    response = client.post("/api/braille/translate", json={"cells": [[1, 2, 5], [1]]})

    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "ha"
    assert body["unrecognized"] == []
    assert body["cells"][0] == {
        "index": 0,
        "dots": [1, 2, 5],
        "kind": "letter",
        "value": "h",
        "spoken": "h",
    }


def test_translate_endpoint_rejects_dots_out_of_range():
    response = client.post("/api/braille/translate", json={"cells": [[9]]})

    assert response.status_code == 422


def test_endpoint_refuses_more_cells_than_the_limit():
    response = client.post(
        "/api/braille/translate", json={"cells": [[1]] * (MAX_CELLS + 1)}
    )

    assert response.status_code == 413


def test_translator_refuses_more_cells_than_the_limit():
    with pytest.raises(ValueError):
        translate([[1]] * (MAX_CELLS + 1))


def test_cors_allows_the_web_app():
    response = client.options(
        "/api/braille/translate",
        headers={
            "Origin": "http://localhost:5000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
