"""Gateway LLM du dashboard : un seul point d'entrée, trois modes de routage.

L'app envoie une requête au format OpenAI (POST /v1/chat/completions) avec le mode dans « model » :
  auto       → Ollama s'il est disponible, sinon OpenRouter
  ollama     → Ollama uniquement (indisponible = 503, aucun traitement)
  openrouter → OpenRouter directement
Le vrai modèle est fixé par backend (OLLAMA_MODEL, OPENROUTER_MODEL) : l'app ne choisit que le mode.
Seuls les champs de génération courants sont relayés (liste blanche) et max_tokens est plafonné :
l'app ne peut ni choisir un autre modèle OpenRouter (« models », « provider »), ni faire
exploser le coût.
La réponse du backend (streaming compris) est relayée telle quelle, avec l'en-tête X-LLM-Backend.
"""

import asyncio
import json
import logging
import os
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.background import BackgroundTask

MODES = ("auto", "ollama", "openrouter")
# Largement assez pour une conversation : au-delà, 413 plutôt que tout charger en mémoire
MAX_BODY_BYTES = 1_000_000
# Champs relayés au backend ; « model » est remplacé par le vrai modèle, le reste est ignoré
FORWARDED_FIELDS = ("messages", "stream", "temperature", "top_p", "max_tokens", "stop")
log = logging.getLogger("gateway")


@dataclass(frozen=True)
class Settings:
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:0.5b"
    openrouter_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen-2.5-7b-instruct"
    openrouter_key: str = ""
    probe_timeout: float = 1.5
    probe_ttl: float = 30.0
    request_timeout: float = 120.0
    # Plafond de tokens générés par réponse, appliqué aussi quand l'app n'en demande pas
    max_tokens: int = 1024

    @classmethod
    def from_env(cls) -> "Settings":
        def env(name: str, default):
            return os.environ.get(name) or default

        max_tokens = int(env("LLM_MAX_TOKENS", cls.max_tokens))
        if max_tokens < 1:
            # Refus au démarrage : sinon max_tokens=0 partirait vers les backends à chaque requête
            raise ValueError(f"LLM_MAX_TOKENS doit être un entier ≥ 1 (reçu : {max_tokens})")
        return cls(
            ollama_url=env("OLLAMA_URL", cls.ollama_url).rstrip("/"),
            ollama_model=env("OLLAMA_MODEL", cls.ollama_model),
            openrouter_url=env("OPENROUTER_URL", cls.openrouter_url).rstrip("/"),
            openrouter_model=env("OPENROUTER_MODEL", cls.openrouter_model),
            openrouter_key=env("OPENROUTER_API_KEY", cls.openrouter_key),
            probe_timeout=float(env("LLM_PROBE_TIMEOUT", cls.probe_timeout)),
            probe_ttl=float(env("LLM_PROBE_TTL", cls.probe_ttl)),
            request_timeout=float(env("LLM_REQUEST_TIMEOUT", cls.request_timeout)),
            max_tokens=max_tokens,
        )


@dataclass(frozen=True)
class Backend:
    name: str
    base_url: str  # racine compatible OpenAI (…/v1)
    model: str
    headers: dict[str, str]


class OllamaProbe:
    """Ollama est disponible si le serveur répond vite ET que le modèle est installé.

    Le résultat est gardé probe_ttl secondes : en mode auto, un PC éteint ne coûte le
    timeout de connexion qu'une fois par période, pas à chaque requête. Le verrou évite
    que des requêtes simultanées lancent chacune leur sonde.
    """

    def __init__(self, client: httpx.AsyncClient, s: Settings, clock: Callable[[], float]):
        self._client, self._s, self._clock = client, s, clock
        self._checked_at: float | None = None
        self._available = False
        self._lock = asyncio.Lock()

    def _fresh(self) -> bool:
        return self._checked_at is not None and self._clock() - self._checked_at < self._s.probe_ttl

    async def available(self) -> bool:
        if not self._fresh():
            async with self._lock:
                if not self._fresh():
                    self._available = await self._check()
                    self._checked_at = self._clock()
        return self._available

    def invalidate(self) -> None:
        self._checked_at = None

    async def _check(self) -> bool:
        try:
            resp = await self._client.get(
                f"{self._s.ollama_url}/api/tags", timeout=self._s.probe_timeout
            )
            resp.raise_for_status()
            names = {m["name"] for m in resp.json().get("models", [])}
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
            return False
        model = self._s.ollama_model
        return model in names or f"{model}:latest" in names


class NoBackend(Exception):
    """Aucun backend utilisable pour ce mode : 503 avec un message lisible par l'app."""


class Router:
    """Choisit les backends d'un mode et relaie la requête au premier qui répond."""

    def __init__(self, client: httpx.AsyncClient, s: Settings, probe: OllamaProbe):
        self.client, self.probe = client, probe
        self.ollama = Backend("ollama", f"{s.ollama_url}/v1", s.ollama_model, {})
        self.openrouter = None
        if s.openrouter_key:
            headers = {"Authorization": f"Bearer {s.openrouter_key}", "X-Title": "ai-jobs-docker"}
            self.openrouter = Backend("openrouter", s.openrouter_url, s.openrouter_model, headers)

    async def plan(self, mode: str) -> list[Backend]:
        """Backends à essayer, dans l'ordre, pour un mode donné."""
        if mode == "openrouter":
            if not self.openrouter:
                raise NoBackend("OpenRouter n'est pas configuré (OPENROUTER_API_KEY absente)")
            return [self.openrouter]
        ollama_ok = await self.probe.available()
        if mode == "ollama":
            if not ollama_ok:
                raise NoBackend("Ollama est indisponible : la requête n'est pas traitée")
            return [self.ollama]
        backends = [b for b in (self.ollama if ollama_ok else None, self.openrouter) if b]
        if not backends:
            raise NoBackend("Ollama est indisponible et OpenRouter n'est pas configuré")
        return backends

    async def forward(self, backends: list[Backend], body: dict) -> Response:
        """Bascule sur le backend suivant tant que rien n'a été relayé à l'app."""
        *fallbacks, final = backends
        for backend in fallbacks:
            resp = await self._send(backend, body)
            if resp is not None and resp.is_success:
                return relay(resp, backend.name)
            if resp is not None:
                log.warning("%s a répondu %s, bascule", backend.name, resp.status_code)
                await resp.aclose()
        resp = await self._send(final, body)
        if resp is None:
            return error(502, f"{final.name} injoignable")
        return relay(resp, final.name)

    async def _send(self, backend: Backend, body: dict) -> httpx.Response | None:
        request = self.client.build_request(
            "POST",
            f"{backend.base_url}/chat/completions",
            json={**body, "model": backend.model},
            headers=backend.headers,
        )
        try:
            return await self.client.send(request, stream=True)
        except httpx.HTTPError as exc:
            log.warning("%s injoignable : %s", backend.name, type(exc).__name__)
            if backend is self.ollama:
                self.probe.invalidate()
            return None


class BadRequest(Exception):
    """Requête refusée avant tout appel à un backend : status + message lisible par l'app."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": {"message": message}}, status_code=status)


async def read_body(request: Request) -> bytes:
    """Corps brut, refusé dès qu'il dépasse MAX_BODY_BYTES (annoncé ou réel)."""
    try:
        announced = int(request.headers.get("content-length") or 0)
    except ValueError:
        raise BadRequest(400, "en-tête content-length invalide") from None
    if announced > MAX_BODY_BYTES:
        raise BadRequest(413, "requête trop volumineuse")
    raw = b""
    async for chunk in request.stream():
        raw += chunk
        if len(raw) > MAX_BODY_BYTES:
            raise BadRequest(413, "requête trop volumineuse")
    return raw


def parse_chat(raw: bytes, max_tokens: int) -> tuple[str, dict]:
    """Mode demandé et corps à relayer (FORWARDED_FIELDS seulement, max_tokens plafonné)."""
    try:
        body = json.loads(raw)
    except ValueError:
        raise BadRequest(400, "corps JSON invalide") from None
    if not isinstance(body, dict) or not isinstance(body.get("messages"), list):
        raise BadRequest(400, "« messages » (liste) est obligatoire")
    mode = body.get("model") or "auto"
    if mode not in MODES:
        raise BadRequest(400, f"mode inconnu « {mode} » : {', '.join(MODES)}")
    asked = body.get("max_tokens", max_tokens)
    if isinstance(asked, bool) or not isinstance(asked, int) or asked < 1:
        raise BadRequest(400, "« max_tokens » doit être un entier positif")
    forwarded = {k: body[k] for k in FORWARDED_FIELDS if k in body}
    return mode, {**forwarded, "max_tokens": min(asked, max_tokens)}


def relay(resp: httpx.Response, backend: str) -> StreamingResponse:
    log.info("réponse de %s (%s)", backend, resp.status_code)
    return StreamingResponse(
        # Contenu décodé (gzip éventuel retiré) : seul content-type est relayé, pas content-encoding
        resp.aiter_bytes(),
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
        headers={"X-LLM-Backend": backend},
        background=BackgroundTask(resp.aclose),
    )


def create_app(
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> FastAPI:
    s = settings or Settings.from_env()
    timeout = httpx.Timeout(s.request_timeout, connect=5.0)
    client = httpx.AsyncClient(transport=transport, timeout=timeout)
    probe = OllamaProbe(client, s, clock)
    router = Router(client, s, probe)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await client.aclose()

    app = FastAPI(title="ai-jobs llm-gateway", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/v1/backends")
    async def backends() -> dict:
        return {
            "modes": list(MODES),
            "ollama": {"available": await probe.available(), "model": s.ollama_model},
            "openrouter": {
                "configured": router.openrouter is not None,
                "model": s.openrouter_model,
            },
        }

    @app.post("/v1/chat/completions")
    async def chat(request: Request):
        try:
            mode, body = parse_chat(await read_body(request), s.max_tokens)
        except BadRequest as exc:
            return error(exc.status, str(exc))
        try:
            chosen = await router.plan(mode)
        except NoBackend as exc:
            return error(503, str(exc))
        return await router.forward(chosen, body)

    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = create_app()
