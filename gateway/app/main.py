import logging
import uuid

import httpx
from fastapi import FastAPI, HTTPException

from .agent_client import invoke_runtime
from .hooks import post_output_hook, pre_input_hook
from .models import InvokeRequest, InvokeResponse, RuntimeInvokeRequest


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("agent-gateway")

app = FastAPI(title="Agent Gateway", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/agents/{agent_id}/invoke", response_model=InvokeResponse)
async def invoke(agent_id: str, request: InvokeRequest) -> InvokeResponse:
    execution_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    logger.info(
        "execution.started execution_id=%s trace_id=%s agent_id=%s",
        execution_id,
        trace_id,
        agent_id,
    )

    input_result = await pre_input_hook(request.input)
    if input_result.decision == "deny":
        raise HTTPException(status_code=403, detail="Input blocked by guardrail")

    runtime_request = RuntimeInvokeRequest(
        execution_id=execution_id,
        trace_id=trace_id,
        agent_id=agent_id,
        input=input_result.content,
        session_id=request.session_id,
        metadata=request.metadata,
    )

    try:
        runtime_result = await invoke_runtime(runtime_request)
    except httpx.TimeoutException as exc:
        logger.warning("execution.failed execution_id=%s reason=runtime_timeout", execution_id)
        raise HTTPException(status_code=504, detail="Agent runtime timed out") from exc
    except httpx.HTTPStatusError as exc:
        status = 404 if exc.response.status_code == 404 else 502
        logger.warning(
            "execution.failed execution_id=%s runtime_status=%s",
            execution_id,
            exc.response.status_code,
        )
        raise HTTPException(status_code=status, detail="Agent runtime failed") from exc
    except httpx.RequestError as exc:
        logger.warning("execution.failed execution_id=%s reason=runtime_unavailable", execution_id)
        raise HTTPException(status_code=503, detail="Agent runtime unavailable") from exc

    output_result = await post_output_hook(runtime_result["output"])
    if output_result.decision == "deny":
        raise HTTPException(status_code=403, detail="Output blocked by guardrail")

    logger.info("execution.completed execution_id=%s", execution_id)
    return InvokeResponse(
        execution_id=execution_id,
        trace_id=trace_id,
        agent_id=agent_id,
        status="completed",
        output=output_result.content,
        model=runtime_result["model"],
        usage=runtime_result["usage"],
    )

