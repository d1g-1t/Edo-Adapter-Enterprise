from __future__ import annotations

import time

import redis.asyncio as aioredis

from src.core.config import get_settings
from src.core.logging import get_logger
from src.domain.exceptions.domain_exceptions import CircuitOpenError
from src.domain.value_objects.delivery_status import CircuitState

logger = get_logger(__name__)

_PREFIX = "circuit:"


class CircuitBreaker:

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client
        s = get_settings()
        self._failure_threshold = s.circuit_failure_threshold
        self._recovery_timeout = s.circuit_recovery_timeout_seconds
        self._half_open_max = s.circuit_half_open_max_calls

    def _key(self, account_id: str) -> str:
        return f"{_PREFIX}{account_id}"

    async def get_state(self, account_id: str) -> CircuitState:
        data: dict[bytes, bytes] = await self._redis.hgetall(self._key(account_id))
        if not data:
            return CircuitState.CLOSED

        state = data.get(b"state", b"CLOSED").decode()
        if state == CircuitState.OPEN:
            opened_at = float(data.get(b"opened_at", 0))
            if time.time() - opened_at >= self._recovery_timeout:
                await self._transition(account_id, CircuitState.HALF_OPEN)
                return CircuitState.HALF_OPEN
        return CircuitState(state)

    async def record_success(self, account_id: str) -> None:
        state = await self.get_state(account_id)
        if state == CircuitState.HALF_OPEN:
            half_open_count = int(
                (await self._redis.hget(self._key(account_id), "half_open_successes")) or 0
            )
            half_open_count += 1
            await self._redis.hset(
                self._key(account_id), "half_open_successes", half_open_count
            )
            if half_open_count >= self._half_open_max:
                await self._transition(account_id, CircuitState.CLOSED)
                logger.info("circuit_breaker.closed", account_id=account_id)
        elif state == CircuitState.CLOSED:
            await self._redis.hset(self._key(account_id), "failures", 0)

    async def record_failure(self, account_id: str) -> None:
        pipe = self._redis.pipeline()
        key = self._key(account_id)
        await pipe.hincrby(key, "failures", 1)
        await pipe.hset(key, "state", CircuitState.CLOSED.value)
        results = await pipe.execute()
        failures = results[0]

        if failures >= self._failure_threshold:
            await self._transition(account_id, CircuitState.OPEN)
            logger.warning(
                "circuit_breaker.opened",
                account_id=account_id,
                failures=failures,
            )

    async def _transition(self, account_id: str, state: CircuitState) -> None:
        pipe = self._redis.pipeline()
        key = self._key(account_id)
        await pipe.hset(key, "state", state.value)
        if state == CircuitState.OPEN:
            await pipe.hset(key, "opened_at", time.time())
            await pipe.hset(key, "failures", 0)
        if state == CircuitState.CLOSED:
            await pipe.hset(key, "failures", 0)
            await pipe.hset(key, "half_open_successes", 0)
        await pipe.execute()

    async def guard(self, account_id: str) -> None:
        state = await self.get_state(account_id)
        if state == CircuitState.OPEN:
            raise CircuitOpenError(account_id)
