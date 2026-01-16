"""In-memory metrics collection."""

import time
from dataclasses import dataclass, field


@dataclass
class Metrics:
    """In-memory metrics collector."""

    total_requests: int = 0
    total_latency: float = 0.0
    safety_blocks: int = 0
    start_time: float = field(default_factory=time.time)

    def record_request(self, latency: float, safety_blocked: bool = False):
        """Record a request."""
        self.total_requests += 1
        self.total_latency += latency
        if safety_blocked:
            self.safety_blocks += 1

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if self.total_requests == 0:
            return 0.0
        return (self.total_latency / self.total_requests) * 1000

    @property
    def uptime_seconds(self) -> float:
        """Calculate uptime in seconds."""
        return time.time() - self.start_time


_metrics: Metrics | None = None


def get_metrics() -> Metrics:
    """Get or create metrics singleton."""
    global _metrics
    if _metrics is None:
        _metrics = Metrics()
    return _metrics
