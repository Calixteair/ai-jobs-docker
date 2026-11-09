"""Gateway LLM : routage des trois modes, bascule et cache de disponibilité (backends simulés)."""

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from gateway import OllamaProbe, Settings, create_app

OLLAMA = "http://pc:11434"
OPENROUTER = "https://or.test/api/v1"
MESSAGES = [{"role": "user", "content": "bonjour"}]


class FakeBackends:
    """Ollama et OpenRouter simulés ; chaque appel est enregistré."""

    def __init__(self, ollama_up=True, model_installed=True, ollama_chat_status=200):
        self.ollama_up = ollama_up
        self.model_installed = model_installed
        self.ollama_chat_status = ollama_chat_status
        self.sent: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.sent.append(request)
        if url.startswith(OLLAMA):
            return self.ollama(url)
        return httpx.Response(200, json={"backend": "openrouter"})

    def ollama(self, url: str) -> httpx.Response:
        if not self.ollama_up:
            raise httpx.ConnectTimeout("PC éteint")
        if url.endswith("/api/tags"):
            models = [{"name": "qwen3:8b"}] if self.model_installed else []
            return httpx.Response(200, json={"models": models})
        return httpx.Response(self.ollama_chat_status, json={"backend": "ollama"})

    @property
    def calls(self) -> list[str]:
        return [str(r.url) for r in self.sent]

    def count(self, suffix: str) -> int:
        return sum(url.endswith(suffix) for url in self.calls)


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def make_client(backends: FakeBackends, key="sk-test", clock=None) -> TestClient:
    settings = Settings(
        ollama_url=OLLAMA,
        ollama_model="qwen3:8b",
        openrouter_url=OPENROUTER,
        openrouter_model="vendor/model",
        openrouter_key=key,
    )
    app = create_app(settings, transport=httpx.MockTransport(backends), clock=clock or Clock())
    return TestClient(app)


def chat(client: TestClient, mode: str | None, **extra) -> httpx.Response:
    body = {"messages": MESSAGES, **extra}
    if mode is not None:
        body["model"] = mode
    return client.post("/v1/chat/completions", json=body)


@pytest.mark.parametrize("mode", ["auto", None])
def test_auto_uses_ollama_when_available(mode):
    resp = chat(make_client(FakeBackends()), mode)
    assert resp.status_code == 200
    assert resp.headers["X-LLM-Backend"] == "ollama"


@pytest.mark.parametrize(
    "backends",
    [FakeBackends(ollama_up=False), FakeBackends(model_installed=False)],
    ids=["pc-eteint", "modele-absent"],
)
def test_auto_falls_back_to_openrouter(backends):
    resp = chat(make_client(backends), "auto")
    assert resp.headers["X-LLM-Backend"] == "openrouter"
    assert resp.json() == {"backend": "openrouter"}


def test_auto_falls_back_when_ollama_fails_after_probe():
    backends = FakeBackends(ollama_chat_status=500)
    resp = chat(make_client(backends), "auto")
    assert resp.headers["X-LLM-Backend"] == "openrouter"
    assert backends.calls.count(f"{OLLAMA}/v1/chat/completions") == 1  # pas de nouvel essai


def test_auto_without_key_and_without_ollama_is_503():
    resp = chat(make_client(FakeBackends(ollama_up=False), key=""), "auto")
    assert resp.status_code == 503


def test_ollama_mode_never_uses_openrouter():
    backends = FakeBackends(ollama_up=False)
    resp = chat(make_client(backends), "ollama")
    assert resp.status_code == 503
    assert "indisponible" in resp.json()["error"]["message"]
    assert not any(url.startswith(OPENROUTER) for url in backends.calls)


def test_ollama_mode_relays_ollama_error_without_fallback():
    resp = chat(make_client(FakeBackends(ollama_chat_status=500)), "ollama")
    assert resp.status_code == 500
    assert resp.headers["X-LLM-Backend"] == "ollama"


def test_openrouter_mode_skips_ollama():
    backends = FakeBackends()
    resp = chat(make_client(backends), "openrouter")
    assert resp.headers["X-LLM-Backend"] == "openrouter"
    assert backends.calls == [f"{OPENROUTER}/chat/completions"]


def test_openrouter_mode_without_key_is_503():
    assert chat(make_client(FakeBackends(), key=""), "openrouter").status_code == 503


def test_real_model_and_key_are_set_by_the_gateway():
    backends = FakeBackends()
    chat(make_client(backends), "openrouter", temperature=0.2)
    sent = backends.sent[-1]
    assert sent.headers["Authorization"] == "Bearer sk-test"
    assert b'"model":"vendor/model"' in sent.content
    assert b'"temperature":0.2' in sent.content


def test_probe_result_is_cached_until_ttl():
    backends, clock = FakeBackends(ollama_up=False), Clock()
    client = make_client(backends, clock=clock)
    chat(client, "auto")
    chat(client, "auto")
    assert backends.count("/api/tags") == 1
    clock.now = 31
    backends.ollama_up = True
    assert chat(client, "auto").headers["X-LLM-Backend"] == "ollama"


@pytest.mark.parametrize(
    "body",
    [{"model": "auto"}, {"model": "inconnu", "messages": MESSAGES}],
    ids=["sans-messages", "mode-inconnu"],
)
def test_invalid_requests_are_400(body):
    resp = make_client(FakeBackends()).post("/v1/chat/completions", json=body)
    assert resp.status_code == 400


def test_health_and_backends_status():
    client = make_client(FakeBackends(ollama_up=False), key="")
    assert client.get("/health").json() == {"status": "ok"}
    status = client.get("/v1/backends").json()
    assert status["ollama"] == {"available": False, "model": "qwen3:8b"}
    assert status["openrouter"]["configured"] is False


def test_concurrent_requests_share_one_probe():
    backends = FakeBackends()
    client = httpx.AsyncClient(transport=httpx.MockTransport(backends))
    probe = OllamaProbe(client, Settings(ollama_url=OLLAMA, ollama_model="qwen3:8b"), Clock())

    async def burst():
        return await asyncio.gather(*(probe.available() for _ in range(5)))

    assert asyncio.run(burst()) == [True] * 5
    assert backends.count("/api/tags") == 1
