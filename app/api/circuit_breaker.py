import time
import logging
from typing import Callable, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"       # Healthy, requests flow
    OPEN = "open"           # Failing, requests blocked
    HALF_OPEN = "half_open" # Testing for recovery

class CircuitBreaker:
    """
    Production-grade Circuit Breaker (Martin Fowler pattern).
    Prevents cascading failures when external APIs (data.gov.in) are down.
    """
    def __init__(
        self, 
        name: str, 
        failure_threshold: int = 3, 
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.last_recovery_attempt: Optional[float] = None

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info(f"🔌 Circuit [{self.name}] moving to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
            else:
                logger.warning(f"🔌 Circuit [{self.name}] is OPEN. Blocking request.")
                raise RuntimeError(f"Circuit Breaker [{self.name}] is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(e)
            raise e

    def _on_success(self):
        if self.state != CircuitState.CLOSED:
            logger.info(f"🔌 Circuit [{self.name}] recovered! Moving to CLOSED.")
        self.state = CircuitState.CLOSED
        self.failures = 0

    def _on_failure(self, e: Exception):
        self.failures += 1
        self.last_failure_time = time.time()
        logger.warning(f"🔌 Circuit [{self.name}] failure {self.failures}/{self.failure_threshold}: {e}")
        
        if self.failures >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.error(f"🔌 Circuit [{self.name}] TRIPPED! Moving to OPEN state.")
            self.state = CircuitState.OPEN

    @property
    def current_state(self) -> str:
        return self.state.value
