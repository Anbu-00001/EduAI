from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import time, json, logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int   = 3
    cooldown_seconds: int    = 1800
    state: CircuitState      = CircuitState.CLOSED
    failure_count: int       = 0
    last_failure_time: float = 0.0
    state_file: Path         = None

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.cooldown_seconds:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit [{self.name}] OPEN → HALF_OPEN")
                self._persist()
                return True
            return False
        return True  # HALF_OPEN: allow one probe

    def record_success(self) -> None:
        if self.state != CircuitState.CLOSED:
            logger.info(f"Circuit [{self.name}] → CLOSED (recovered)")
        self.state        = CircuitState.CLOSED
        self.failure_count = 0
        self._persist()

    def record_failure(self) -> None:
        self.failure_count    += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.warning(
                    f"Circuit [{self.name}] → OPEN after {self.failure_count} failures. "
                    f"Cooldown: {self.cooldown_seconds // 60} min."
                )
            self.state = CircuitState.OPEN
        self._persist()

    def _persist(self) -> None:
        if self.state_file is None:
            return
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps({
            "name":              self.name,
            "state":             self.state.value,
            "failure_count":     self.failure_count,
            "last_failure_time": self.last_failure_time,
        }))

    @classmethod
    def load(cls, name: str, state_file: Path, **kwargs) -> "CircuitBreaker":
        if state_file.exists():
            try:
                data  = json.loads(state_file.read_text())
                cb    = cls(name=name, state_file=state_file, **kwargs)
                cb.state             = CircuitState(data["state"])
                cb.failure_count     = data["failure_count"]
                cb.last_failure_time = data["last_failure_time"]
                return cb
            except Exception as e:
                logger.warning(f"Could not load circuit [{name}]: {e} — resetting")
        return cls(name=name, state_file=state_file, **kwargs)
