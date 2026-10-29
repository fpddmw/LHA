import os

from vlm.litellm_vlm import LiteLLMVisionModel, use_litellm_vlm

__all__ = [
    "LiteLLMVisionModel",
    "LocalQwenPlannerModel",
    "OpenRouterVisionModel",
    "extract_frames",
    "resolve_vision_model",
    "use_litellm_vlm",
]


def __getattr__(name):
    """Load GPU-specific dependencies only when that backend is requested."""
    if name in {"LocalQwenPlannerModel", "extract_frames"}:
        from vlm import local_qwen
        return getattr(local_qwen, name)
    if name == "OpenRouterVisionModel":
        from vlm.openrouter import OpenRouterVisionModel
        return OpenRouterVisionModel
    raise AttributeError(name)


def resolve_vision_model(role: str = "planner"):
    """Return the VLM backend selected by environment.

    ``LOW_HIGH_AGENT_USE_LITELLM_VLM=1`` routes reasoning to the hosted litellm
    gateway; otherwise the local Qwen3-VL checkpoint is used.

    ``role`` lets the critic run on a different hosted model from the planner
    without touching the planner: ``LOW_HIGH_AGENT_LITELLM_<ROLE>_MODEL`` and
    ``LOW_HIGH_AGENT_LITELLM_<ROLE>_REASONING_EFFORT`` take precedence over the
    shared ``LOW_HIGH_AGENT_LITELLM_MODEL`` / ``..._REASONING_EFFORT``, so an
    unset role variable leaves behaviour exactly as before.
    """
    backend = os.environ.get("LOW_HIGH_AGENT_VLM_BACKEND", "").strip().lower()
    if backend == "codex":
        from vlm.codex_vlm import CodexVisionModel
        return CodexVisionModel(role=role)
    if backend not in {"", "litellm", "local_qwen"}:
        raise ValueError(f"Unknown LOW_HIGH_AGENT_VLM_BACKEND: {backend}")
    if backend == "local_qwen" or (backend != "litellm" and not use_litellm_vlm()):
        from vlm.local_qwen import LocalQwenPlannerModel
        return LocalQwenPlannerModel()
    prefix = f"LOW_HIGH_AGENT_LITELLM_{role.strip().upper()}_"
    model = os.environ.get(prefix + "MODEL", "").strip()
    effort = os.environ.get(prefix + "REASONING_EFFORT", "").strip()
    return LiteLLMVisionModel(model=model, reasoning_effort=effort, role=role)
