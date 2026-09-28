from dataclasses import dataclass, field
from typing import Any, Literal


HookDecision = Literal["allow", "deny", "sanitize", "warn"]


@dataclass
class HookResult:
    decision: HookDecision = "allow"
    content: str = ""
    signals: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


async def pre_input_hook(content: str) -> HookResult:
    """V1 extension point. V2 can add prompt-injection detection here."""
    return HookResult(content=content)


async def post_output_hook(content: str) -> HookResult:
    """V1 extension point. V2 can add output filtering here."""
    return HookResult(content=content)

