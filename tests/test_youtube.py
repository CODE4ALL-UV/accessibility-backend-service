"""Subtítulos de YouTube y su traducción opcional.

Ni YouTube ni el traductor se llaman de verdad: se sustituyen por dobles, así
que las pruebas no necesitan red ni claves.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from youtube_transcript_api import TranscriptsDisabled

import accessibility_service.presentation.api.youtube_routes as youtube_routes
from accessibility_service.main import app

client = TestClient(app)


def _cues(count):
    return [
        SimpleNamespace(start=float(i), duration=1.5, text=f"line {i}")
        for i in range(count)
    ]


class FakeTranscriptApi:
    """Devuelve los subtítulos que se le pidan, o falla como se le pida."""

    transcript = []
    error = None
    requested = []

    def fetch(self, video_id, languages):
        FakeTranscriptApi.requested.append((video_id, languages))
        if FakeTranscriptApi.error is not None:
            raise FakeTranscriptApi.error
        return FakeTranscriptApi.transcript


class FakeResponse:
    def __init__(self, payload, error=None):
        self._payload = payload
        self._error = error

    def raise_for_status(self):
        if self._error is not None:
            raise self._error

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def _fake_youtube(monkeypatch):
    FakeTranscriptApi.transcript = _cues(2)
    FakeTranscriptApi.error = None
    FakeTranscriptApi.requested = []
    monkeypatch.setattr(youtube_routes, "YouTubeTranscriptApi", FakeTranscriptApi)
    monkeypatch.delenv("TRANSLATE_PROVIDER", raising=False)
    monkeypatch.delenv("TRANSLATE_API_KEY", raising=False)


@pytest.fixture
def posts(monkeypatch):
    """Guarda cada llamada al traductor y responde con el texto en mayúsculas."""
    calls = []

    def fake_post(url, params=None, data=None, timeout=None):
        calls.append({"url": url, "params": params, "data": data, "timeout": timeout})
        if "deepl" in url:
            texts = data["text"]
            return FakeResponse({"translations": [{"text": t.upper()} for t in texts]})
        texts = [value for key, value in data if key == "q"]
        return FakeResponse(
            {"data": {"translations": [{"translatedText": t.upper()} for t in texts]}}
        )

    monkeypatch.setattr(youtube_routes.requests, "post", fake_post)
    return calls


def test_returns_the_captions_without_translation_by_default(posts):
    response = client.get("/api/youtube/captions", params={"video_id": "abc"})

    assert response.status_code == 200
    assert response.json() == {
        "cues": [
            {"start": 0.0, "duration": 1.5, "text": "line 0"},
            {"start": 1.0, "duration": 1.5, "text": "line 1"},
        ]
    }
    assert FakeTranscriptApi.requested == [("abc", ("en", "es", "fr", "de"))]
    assert posts == []


def test_missing_fields_in_a_cue_get_safe_defaults():
    FakeTranscriptApi.transcript = [SimpleNamespace()]

    response = client.get("/api/youtube/captions", params={"video_id": "abc"})

    assert response.json() == {"cues": [{"start": 0.0, "duration": 0.0, "text": ""}]}


def test_video_without_transcripts_is_a_404():
    FakeTranscriptApi.error = TranscriptsDisabled("abc")

    response = client.get("/api/youtube/captions", params={"video_id": "abc"})

    assert response.status_code == 404


def test_any_other_youtube_error_returns_no_cues():
    # Un video privado o una caída de YouTube no deben romper la lección.
    FakeTranscriptApi.error = RuntimeError("YouTube no responde")

    response = client.get("/api/youtube/captions", params={"video_id": "abc"})

    assert response.status_code == 200
    assert response.json() == {"cues": []}


def test_video_id_is_required():
    assert client.get("/api/youtube/captions").status_code == 422


def test_provider_without_key_does_not_translate(monkeypatch, posts):
    monkeypatch.setenv("TRANSLATE_PROVIDER", "google")

    body = client.get("/api/youtube/captions", params={"video_id": "abc"}).json()

    assert all("translated" not in cue for cue in body["cues"])
    assert posts == []


def test_translates_with_google_by_default(monkeypatch, posts):
    monkeypatch.setenv("TRANSLATE_PROVIDER", "Google")
    monkeypatch.setenv("TRANSLATE_API_KEY", "clave")

    body = client.get(
        "/api/youtube/captions", params={"video_id": "abc", "target": "fr"}
    ).json()

    assert [cue["translated"] for cue in body["cues"]] == ["LINE 0", "LINE 1"]
    assert len(posts) == 1
    assert posts[0]["url"] == "https://translation.googleapis.com/language/translate/v2"
    assert posts[0]["params"] == {"key": "clave", "target": "fr"}
    assert posts[0]["data"] == [("q", "line 0"), ("q", "line 1")]
    assert posts[0]["timeout"] == 15


def test_translates_with_deepl(monkeypatch, posts):
    monkeypatch.setenv("TRANSLATE_PROVIDER", "deepl")
    monkeypatch.setenv("TRANSLATE_API_KEY", "clave")

    body = client.get("/api/youtube/captions", params={"video_id": "abc"}).json()

    assert [cue["translated"] for cue in body["cues"]] == ["LINE 0", "LINE 1"]
    assert posts[0]["url"] == "https://api.deepl.com/v2/translate"
    # DeepL espera el idioma en mayúsculas.
    assert posts[0]["data"] == {
        "auth_key": "clave",
        "target_lang": "ES",
        "text": ["line 0", "line 1"],
    }


def test_long_transcripts_are_translated_in_batches_of_twenty(monkeypatch, posts):
    FakeTranscriptApi.transcript = _cues(45)
    monkeypatch.setenv("TRANSLATE_PROVIDER", "google")
    monkeypatch.setenv("TRANSLATE_API_KEY", "clave")

    body = client.get("/api/youtube/captions", params={"video_id": "abc"}).json()

    assert [len(call["data"]) for call in posts] == [20, 20, 5]
    assert body["cues"][44]["translated"] == "LINE 44"


def test_translation_failure_keeps_the_original_captions(monkeypatch):
    def failing_post(url, params=None, data=None, timeout=None):
        return FakeResponse({}, error=RuntimeError("cuota agotada"))

    monkeypatch.setattr(youtube_routes.requests, "post", failing_post)
    monkeypatch.setenv("TRANSLATE_PROVIDER", "deepl")
    monkeypatch.setenv("TRANSLATE_API_KEY", "clave")

    response = client.get("/api/youtube/captions", params={"video_id": "abc"})

    assert response.status_code == 200
    assert [cue["text"] for cue in response.json()["cues"]] == ["line 0", "line 1"]
    assert all("translated" not in cue for cue in response.json()["cues"])
