import os

__all__ = [
    "LiteLLMVisionModel",
    "LocalQwenPlannerModel",
    "OpenRouterVisionModel",
    "ChatGPTSubscriptionVisionModel",
    "extract_frames",
    "resolve_vision_model",
    "use_litellm_vlm",
]


def __getattr__(name):
    """Load optional backends only when explicitly requested."""
    if name in {"LiteLLMVisionModel", "use_litellm_vlm"}:
        from vlm import litellm_vlm

        return getattr(litellm_vlm, name)
    if name in {"LocalQwenPlannerModel", "extract_frames"}:
        from vlm import local_qwen

        return getattr(local_qwen, name)
    if name == "OpenRouterVisionModel":
        from vlm.openrouter import OpenRouterVisionModel

        return OpenRouterVisionModel
    if name == "ChatGPTSubscriptionVisionModel":
        from vlm.chatgpt_subscription import ChatGPTSubscriptionVisionModel

        return ChatGPTSubscriptionVisionModel
    raise AttributeError(name)


def resolve_vision_model(role: str = "planner"):
    """Use the key-authenticated OpenRouter API by default, or an explicit backend."""
    backend = os.environ.get("LOW_HIGH_AGENT_VLM_BACKEND", "openrouter").strip().lower()
    if backend == "chatgpt_subscription":
        from vlm.chatgpt_subscription import ChatGPTSubscriptionVisionModel

        return ChatGPTSubscriptionVisionModel(role=role)
    if backend in {"", "api", "openrouter"}:
        from vlm.openrouter import OpenRouterVisionModel

        return OpenRouterVisionModel(role=role)
    if backend not in {"litellm", "local_qwen"}:
        raise ValueError(f"Unknown LOW_HIGH_AGENT_VLM_BACKEND: {backend}")
    if backend == "local_qwen":
        from vlm.local_qwen import LocalQwenPlannerModel

        return LocalQwenPlannerModel()
    prefix = f"LOW_HIGH_AGENT_LITELLM_{role.strip().upper()}_"
    model = os.environ.get(prefix + "MODEL", "").strip()
    effort = os.environ.get(prefix + "REASONING_EFFORT", "").strip()
    from vlm.litellm_vlm import LiteLLMVisionModel

    return LiteLLMVisionModel(model=model, reasoning_effort=effort, role=role)
