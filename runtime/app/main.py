import logging
from pathlib import Path

import httpx
import yaml
from fastapi import FastAPI, HTTPException

from .llm_client import complete
from .models import RuntimeInvokeRequest, RuntimeInvokeResponse


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("agent-runtime")

app = FastAPI(title="Agent Runtime", version="0.1.0")
AGENT_DIR = Path(__file__).parent / "agents"


def load_agent(agent_id: str) -> dict:
    safe_id = Path(agent_id).name
    if safe_id != agent_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    path = AGENT_DIR / f"{safe_id}.yaml"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Agent not found")
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/internal/v1/invoke", response_model=RuntimeInvokeResponse)
async def invoke(request: RuntimeInvokeRequest) -> RuntimeInvokeResponse:
    agent = load_agent(request.agent_id)
    logger.info(
        "llm.started execution_id=%s trace_id=%s agent_id=%s",
        request.execution_id,
        request.trace_id,
        request.agent_id,
    )
    try:
        result = await complete(
            system_prompt=agent["system_prompt"],
            user_input=request.input,
            temperature=float(agent.get("temperature", 0.2)),
        )
    except httpx.TimeoutException as exc:
        logger.warning("llm.failed execution_id=%s reason=timeout", request.execution_id)
        raise HTTPException(status_code=504, detail="LLM timed out") from exc
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        logger.exception("llm.failed execution_id=%s", request.execution_id)
        raise HTTPException(status_code=502, detail="LLM request failed") from exc

    logger.info("llm.completed execution_id=%s model=%s", request.execution_id, result["model"])
    return RuntimeInvokeResponse(**result)

