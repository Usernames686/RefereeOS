from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BetaReviewConfig:
    model: str
    api_key: str
    base_url: str | None = None


def _env_or_default(name: str, default: str) -> str:
    return os.getenv(name, "").strip() or default


def detect_beta_config() -> BetaReviewConfig | None:
    """Return an OpenAI-compatible config for AG2 Beta, or None without a key."""
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()

    if deepseek_key:
        return BetaReviewConfig(
            model=_env_or_default("AG2_MODEL", "deepseek-chat"),
            api_key=deepseek_key,
            base_url=_env_or_default("AG2_BASE_URL", "https://api.deepseek.com/v1"),
        )
    if openrouter_key:
        return BetaReviewConfig(
            model=_env_or_default("AG2_MODEL", "google/gemini-3-flash-preview"),
            api_key=openrouter_key,
            base_url=_env_or_default("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        )
    if openai_key:
        return BetaReviewConfig(model=_env_or_default("AG2_MODEL", "gpt-4o-mini"), api_key=openai_key)
    if gemini_key:
        return BetaReviewConfig(model=_env_or_default("AG2_MODEL", "gemini-2.5-flash"), api_key=gemini_key)
    return None


def create_beta_agents(config: BetaReviewConfig):
    """Create claim_extractor, method_critic, and area_chair AG2 Beta agents."""
    try:
        from autogen.beta import Agent
        from autogen.beta.config import GeminiConfig, OpenAIConfig
    except Exception as exc:  # pragma: no cover - dependency availability varies
        raise RuntimeError("AG2 Beta is not installed. Install ag2[openai]>=0.9.0.") from exc

    if config.model.startswith("gemini-") and config.base_url is None:
        model_config = GeminiConfig(model=config.model, api_key=config.api_key, temperature=0.2)
    else:
        kwargs: dict[str, Any] = {
            "model": config.model,
            "api_key": config.api_key,
            "temperature": 0.2,
        }
        if config.base_url:
            kwargs["base_url"] = config.base_url
        if "deepseek" in config.model.lower():
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        model_config = OpenAIConfig(**kwargs)

    claim_extractor = Agent(
        "claim_extractor",
        prompt=(
            "Extract 3-6 central scientific claims from a manuscript. "
            "Return one concise bullet per claim. Avoid judging the paper."
        ),
        config=model_config,
    )
    method_critic = Agent(
        "method_critic",
        prompt=(
            "You are a skeptical methods reviewer. Given claims and manuscript context, "
            "identify methodological, statistical, reproducibility, and integrity concerns. "
            "Keep concerns concrete and useful for a human editor."
        ),
        config=model_config,
    )
    area_chair = Agent(
        "area_chair",
        prompt=(
            "You are an area chair preparing a reviewer packet for human peer review. "
            "Call critique_methods before finalizing. Do not accept or reject the paper; "
            "produce summary, major concerns, minor issues, and suggested reviewer expertise."
        ),
        config=model_config,
        tools=[
            method_critic.as_tool(
                name="critique_methods",
                description="Ask the method critic to review claims and manuscript context.",
            )
        ],
    )
    return claim_extractor, method_critic, area_chair


async def beta_review_text(paper_text: str, title: str = "Untitled manuscript") -> dict[str, Any]:
    """Run the AG2 Beta reviewer chain and return a compact structured result."""
    config = detect_beta_config()
    if config is None:
        raise RuntimeError("No LLM key found. Set DEEPSEEK_API_KEY, OPENROUTER_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY.")

    claim_extractor, _method_critic, area_chair = create_beta_agents(config)
    claims_reply = await claim_extractor.ask(
        f"Title: {title}\n\nManuscript excerpt:\n{paper_text[:5000]}"
    )
    claims = claims_reply.body if hasattr(claims_reply, "body") else str(claims_reply)
    chair_reply = await area_chair.ask(
        "Prepare a reviewer packet.\n\n"
        f"Title: {title}\n\n"
        f"Claims:\n{claims}\n\n"
        f"Manuscript excerpt:\n{paper_text[:5000]}"
    )
    review = chair_reply.body if hasattr(chair_reply, "body") else str(chair_reply)
    return {
        "engine": "AG2 Beta",
        "model": config.model,
        "agents": ["claim_extractor", "method_critic", "area_chair"],
        "collaboration": "area_chair uses method_critic via Agent.as_tool(name='critique_methods')",
        "claims": claims,
        "review": review,
    }


def parse_json_or_text(text: str, model: str) -> dict[str, str]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"source": f"AG2 Beta + {model}", "summary": text.strip()[:1200]}
    if isinstance(parsed, dict):
        return {str(key): str(value) for key, value in parsed.items()}
    return {"source": f"AG2 Beta + {model}", "summary": str(parsed)}
