from collections import defaultdict
from threading import Lock


_lock = Lock()
_requests: dict[tuple[str, str, str], int] = defaultdict(int)
_duration_sum: dict[tuple[str, str, str], float] = defaultdict(float)


def record_http_request(method: str, route: str, status_code: int, duration_seconds: float) -> None:
    key = (method, route, str(status_code))
    with _lock:
        _requests[key] += 1
        _duration_sum[key] += max(0.0, duration_seconds)


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def render_prometheus_metrics() -> str:
    with _lock:
        requests = dict(_requests)
        durations = dict(_duration_sum)

    lines = [
        "# HELP oracle_http_requests_total Total HTTP requests handled by the ORACLE API.",
        "# TYPE oracle_http_requests_total counter",
    ]
    for (method, route, status_code), count in sorted(requests.items()):
        labels = (
            f'method="{_escape_label(method)}",'
            f'route="{_escape_label(route)}",'
            f'status="{_escape_label(status_code)}"'
        )
        lines.append(f"oracle_http_requests_total{{{labels}}} {count}")

    lines.extend([
        "# HELP oracle_http_request_duration_seconds HTTP request duration in seconds.",
        "# TYPE oracle_http_request_duration_seconds summary",
    ])
    for (method, route, status_code), total in sorted(durations.items()):
        count = requests[(method, route, status_code)]
        labels = (
            f'method="{_escape_label(method)}",'
            f'route="{_escape_label(route)}",'
            f'status="{_escape_label(status_code)}"'
        )
        lines.append(f"oracle_http_request_duration_seconds_count{{{labels}}} {count}")
        lines.append(f"oracle_http_request_duration_seconds_sum{{{labels}}} {total:.9f}")

    return "\n".join(lines) + "\n"
