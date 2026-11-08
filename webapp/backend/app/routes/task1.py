"""Passthrough to the retrieval service's ARQMath Task 1 evaluation API (`/task1/...`).

The responses are forwarded as-is (status code and JSON body), so the frontend
sees exactly the service's API. `/task1/evaluate` blocks for up to ~35 min, so
there is no read timeout on that call.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from ..db import RETRIEVAL_URL

router = APIRouter()

# Per-topic results take ~5-80 s; evaluation of all topics ~25-35 min.
_TIMEOUT_SECONDS = 600
_EVALUATE_TIMEOUT_SECONDS = None


def _forward(path: str, request: Request, timeout: float | None) -> Response:
    # Forward the raw query string so repeated params (topic_ids=A.1&topic_ids=A.2) survive.
    query = request.url.query
    url = f"{RETRIEVAL_URL}/task1/{path}" + (f"?{query}" if query else "")
    try:
        with urlopen(url, timeout=timeout) as res:
            return Response(content=res.read(), status_code=res.status, media_type="application/json")
    except HTTPError as e:
        body = e.read()
        try:
            content = json.loads(body)
        except ValueError:
            content = {"detail": body.decode(errors="replace")}
        return JSONResponse(content=content, status_code=e.code)
    except (URLError, TimeoutError) as e:
        reason = getattr(e, "reason", e)
        return JSONResponse(
            content={"detail": f"Retrieval service unreachable at {RETRIEVAL_URL}: {reason}"}, status_code=502
        )


@router.get("/task1/topics")
def task1_topics(request: Request) -> Response:
    return _forward("topics", request, _TIMEOUT_SECONDS)


@router.get("/task1/evaluate")
def task1_evaluate(request: Request) -> Response:
    return _forward("evaluate", request, _EVALUATE_TIMEOUT_SECONDS)


@router.get("/task1/topics/{topic_id}/results")
def task1_topic_results(topic_id: str, request: Request) -> Response:
    return _forward(f"topics/{quote(topic_id, safe='')}/results", request, _TIMEOUT_SECONDS)
