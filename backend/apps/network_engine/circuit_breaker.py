import time
import logging
from enum import Enum
from typing import Dict, Any, Optional

logger = logging.getLogger('netwatch.circuit_breaker')

class CircuitState(str, Enum):
    CLOSED = 'CLOSED'       # Normal operation - probes allowed through
    OPEN = 'OPEN'           # Tripped - probes short-circuited to prevent worker exhaustion
    HALF_OPEN = 'HALF_OPEN' # Testing recovery after cooldown period

class CircuitBreaker:
    """
    Enterprise Circuit Breaker for Network Device Probing.
    Prevents thread/worker exhaustion and network storms when target devices or subnets become unresponsive.
    
    States:
    - CLOSED: Normal state. If consecutive_failures >= failure_threshold -> transitions to OPEN.
    - OPEN: Calls are rejected immediately without network I/O. After recovery_timeout_sec -> transitions to HALF_OPEN.
    - HALF_OPEN: Allows a trial probe. If successful -> resets to CLOSED. If fails -> reverts to OPEN.
    """
    _registry: Dict[str, 'CircuitBreaker'] = {}

    def __init__(self, key: str, failure_threshold: int = 3, recovery_timeout_sec: float = 60.0):
        self.key = key
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.consecutive_failures = 0
        self.state = CircuitState.CLOSED
        self.last_state_change = time.time()
        self.last_failure_time = 0.0

    @classmethod
    def get(cls, key: str, failure_threshold: int = 3, recovery_timeout_sec: float = 60.0) -> 'CircuitBreaker':
        if key not in cls._registry:
            cls._registry[key] = cls(key, failure_threshold, recovery_timeout_sec)
        return cls._registry[key]

    @classmethod
    def get_all_states(cls) -> Dict[str, Dict[str, Any]]:
        return {
            k: {
                'state': cb.state.value,
                'consecutive_failures': cb.consecutive_failures,
                'last_state_change': cb.last_state_change,
                'is_tripped': cb.state == CircuitState.OPEN
            }
            for k, cb in cls._registry.items()
        }

    def can_execute(self) -> bool:
        """Determines if a probe should be attempted."""
        now = time.time()
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if now - self.last_state_change >= self.recovery_timeout_sec:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                logger.info(f"CircuitBreaker [{self.key}]: Cooldown elapsed. Transitioning OPEN -> HALF_OPEN (Trial probe).")
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

        return True

    def record_success(self):
        """Records a successful probe and resets failure counter."""
        if self.state != CircuitState.CLOSED:
            logger.info(f"CircuitBreaker [{self.key}]: Probe succeeded. Resetting state to CLOSED.")
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_state_change = time.time()

    def record_failure(self):
        """Records a failed probe and potentially trips the circuit."""
        self.consecutive_failures += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.CLOSED and self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            logger.warning(
                f"CircuitBreaker [{self.key}]: Tripped to OPEN after {self.consecutive_failures} consecutive failures. "
                f"Short-circuiting probes for {self.recovery_timeout_sec}s."
            )
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            logger.warning(f"CircuitBreaker [{self.key}]: Trial probe failed in HALF_OPEN. Re-tripping to OPEN.")
