# Agent Security Lab — V1

The first vertical slice contains a public Agent Gateway and an internal Agent
Runtime. The default LLM is a deterministic mock, so no API key is required.

## Run

```powershell
Copy-Item .env.example .env
docker compose up --build
```

In another PowerShell window:

```powershell
$body = @{ input = "What is Agent Security?" } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8080/v1/agents/basic-agent/invoke `
  -ContentType application/json `
  -Body $body
```

Gateway API documentation is available at `http://localhost:8080/docs`.

## Use an OpenAI-compatible model

Edit `.env`:

```dotenv
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=http://host.docker.internal:11434
LLM_API_KEY=unused
LLM_MODEL=qwen3
```

The runtime calls `${LLM_BASE_URL}/v1/chat/completions`.

## Boundary

Only the Gateway publishes a host port. The Runtime is not exposed to the host;
its separate egress network exists only so it can reach an LLM endpoint. V1
guardrail hooks are pass-through extension points.
