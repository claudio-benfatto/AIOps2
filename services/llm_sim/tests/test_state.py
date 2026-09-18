from __future__ import annotations

import asyncio

from llm_sim.state import SimulationState


def test_admit_reserves_budget_and_increments_running() -> None:
    async def run() -> None:
        state = SimulationState(kv_cache_budget_tokens=100)
        await state.admit(40)
        assert state.kv_cache_used_tokens == 40
        assert state.num_requests_running == 1
        assert state.num_requests_waiting == 0

    asyncio.run(run())


def test_release_frees_budget_and_decrements_running() -> None:
    async def run() -> None:
        state = SimulationState(kv_cache_budget_tokens=100)
        await state.admit(40)
        await state.release(40)
        assert state.kv_cache_used_tokens == 0
        assert state.num_requests_running == 0

    asyncio.run(run())


def test_second_request_queues_until_budget_frees() -> None:
    async def run() -> None:
        state = SimulationState(kv_cache_budget_tokens=50)
        await state.admit(50)  # fills the budget entirely

        second_admitted = asyncio.Event()

        async def second() -> None:
            await state.admit(10)
            second_admitted.set()

        task = asyncio.create_task(second())
        await asyncio.sleep(0.05)  # let the second request register as waiting
        assert state.num_requests_waiting == 1
        assert not second_admitted.is_set()

        await state.release(50)
        await asyncio.wait_for(second_admitted.wait(), timeout=1.0)
        assert state.num_requests_waiting == 0
        assert state.num_requests_running == 1
        assert state.kv_cache_used_tokens == 10

        await task  # ensure task completes cleanly

    asyncio.run(run())
