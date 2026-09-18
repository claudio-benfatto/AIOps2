from __future__ import annotations

import asyncio
import itertools
import random
import time

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest

from llm_sim import model, policy
from llm_sim.config import Settings
from llm_sim.metrics import SimulationCollector
from llm_sim.schemas import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Usage,
)
from llm_sim.state import SimulationState


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    state = SimulationState(kv_cache_budget_tokens=settings.kv_cache_budget_tokens)
    rng = random.Random(settings.seed)
    request_counter = itertools.count(1)

    registry = CollectorRegistry()
    registry.register(SimulationCollector(state))

    app = FastAPI(title="llm-sim")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    @app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
    async def chat_completions(chat_request: ChatCompletionRequest) -> ChatCompletionResponse:
        start = time.monotonic()
        prompt_tokens = model.estimate_prompt_tokens(chat_request.messages, chat_request.tools)
        output_tokens = model.compute_output_tokens(
            chat_request.max_tokens,
            rng,
            settings.default_min_output_tokens,
            settings.default_max_output_tokens,
        )

        await state.admit(prompt_tokens)
        queue_wait_seconds = time.monotonic() - start

        prefill_seconds = model.compute_prefill_seconds(
            prompt_tokens, settings.prefill_tokens_per_second
        )
        await asyncio.sleep(prefill_seconds)
        ttft_seconds = queue_wait_seconds + prefill_seconds

        running = await state.running_count()
        itl_seconds = model.compute_inter_token_latency_seconds(
            running, settings.decode_tokens_per_second_total
        )
        decode_seconds = itl_seconds * output_tokens
        await asyncio.sleep(decode_seconds)

        request_id = next(request_counter)
        result = policy.decide_response(
            chat_request.messages, chat_request.tools, request_id=request_id
        )

        await state.release(prompt_tokens)
        e2e_seconds = time.monotonic() - start
        await state.record_completion(
            prompt_tokens=prompt_tokens,
            generation_tokens=output_tokens,
            ttft_seconds=ttft_seconds,
            inter_token_latency_seconds=itl_seconds,
            e2e_seconds=e2e_seconds,
        )

        return ChatCompletionResponse(
            id=f"chatcmpl-{request_id}",
            created=int(time.time()),
            model=chat_request.model,
            choices=[
                ChatCompletionChoice(
                    index=0, message=result.message, finish_reason=result.finish_reason
                )
            ],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=output_tokens,
                total_tokens=prompt_tokens + output_tokens,
            ),
        )

    return app


app = create_app()
