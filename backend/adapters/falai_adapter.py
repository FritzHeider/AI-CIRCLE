"""FalAIAdapter — fal.ai media generation via fal-client."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from adapters.base import AgentAdapter, AdapterResponse
from adapters.registry import register_adapter
from websocket.protocol import ArtifactInfo

logger = logging.getLogger(__name__)

# Model catalog: keyword → (fal_model_id, description)
FALAI_MODELS: Dict[str, Tuple[str, str]] = {
    "flux":        ("fal-ai/flux/schnell",       "Fast image generation (FLUX Schnell)"),
    "flux_pro":    ("fal-ai/flux-pro",            "High-quality image generation (FLUX Pro)"),
    "sdxl":        ("fal-ai/stable-diffusion-xl", "Stable Diffusion XL"),
    "video":       ("fal-ai/fast-svd",            "Video generation from image"),
    "lora":        ("fal-ai/flux/dev/image-to-image", "FLUX image-to-image with LoRA"),
    "face_swap":   ("fal-ai/face-swap",           "Face swap"),
    "upscale":     ("fal-ai/real-esrgan",         "Image upscaling"),
}

# Cost estimates per request (USD)
FALAI_COST_ESTIMATES: Dict[str, float] = {
    "fal-ai/flux/schnell":            0.003,
    "fal-ai/flux-pro":                0.05,
    "fal-ai/stable-diffusion-xl":     0.01,
    "fal-ai/fast-svd":                0.10,
    "fal-ai/flux/dev/image-to-image": 0.025,
    "fal-ai/face-swap":               0.015,
    "fal-ai/real-esrgan":             0.005,
    "default":                        0.01,
}

DEFAULT_MODEL_KEY = "flux"
POLL_INTERVAL = 2.0      # seconds between status polls
POLL_TIMEOUT  = 120.0    # seconds before giving up


def _parse_media_request(text: str) -> Tuple[str, str]:
    """
    Heuristically extract the fal.ai model key and prompt from a message.

    Returns (model_key, prompt_text).
    """
    lower = text.lower()
    detected_key = DEFAULT_MODEL_KEY

    for key in FALAI_MODELS:
        if key.replace("_", " ") in lower or key in lower:
            detected_key = key
            break

    # Strip known model keywords to isolate the prompt
    prompt = text
    for kw in ["generate", "create", "make", "draw", "image of", "picture of", "video of"]:
        prompt = re.sub(rf"\b{kw}\b", "", prompt, flags=re.IGNORECASE).strip()

    return detected_key, prompt.strip() or text


@register_adapter("falai")
class FalAIAdapter(AgentAdapter):
    """Adapter for fal.ai media generation workflows."""

    adapter_type = "falai"
    capabilities = ["image_generation", "video_generation", "image_editing", "upscaling"]

    async def respond(
        self,
        session_id: str,
        agent_config: Dict[str, Any],
        user_message: str,
        history: List[Dict[str, Any]],
        redis: Any,
        supabase: Any,
    ) -> Optional[AdapterResponse]:
        from core.config import get_settings
        settings = get_settings()

        api_key = settings.falai_api_key
        if not api_key:
            logger.warning("FALAI_API_KEY not configured — FalAIAdapter skipping")
            return None

        try:
            import fal_client
        except ImportError:
            logger.error("fal-client package not installed (pip install fal-client)")
            return None

        model_key, prompt = _parse_media_request(user_message)
        model_id, model_desc = FALAI_MODELS.get(model_key, FALAI_MODELS[DEFAULT_MODEL_KEY])

        extra = agent_config.get("extra_config", {})
        arguments = {
            "prompt": prompt,
            "num_images": extra.get("num_images", 1),
            "image_size": extra.get("image_size", "landscape_4_3"),
            "num_inference_steps": extra.get("num_inference_steps", 4),
        }

        try:
            result = await self._poll_for_result(fal_client, api_key, model_id, arguments)
        except asyncio.TimeoutError:
            return AdapterResponse(
                content=f"[fal.ai] Request timed out after {POLL_TIMEOUT}s for model {model_id}.",
                model=model_id,
            )
        except Exception as exc:
            logger.exception("fal.ai error: %s", exc)
            return AdapterResponse(content=f"[fal.ai error: {exc}]", model=model_id)

        # Extract image URLs from result
        images = result.get("images", [])
        artifacts = []
        for img in images:
            url = img.get("url", "") if isinstance(img, dict) else str(img)
            if url:
                artifacts.append(ArtifactInfo(type="image", url=url))

        cost = FALAI_COST_ESTIMATES.get(model_id, FALAI_COST_ESTIMATES["default"])

        if artifacts:
            content = f"Generated {len(artifacts)} image(s) using {model_desc} for prompt: *{prompt}*"
        else:
            content = f"[fal.ai] {model_desc} completed but returned no images."

        return AdapterResponse(
            content=content,
            model=model_id,
            cost_usd=cost,
            artifacts=artifacts,
            metadata={"fal_result": result},
        )

    async def _poll_for_result(
        self,
        fal_client: Any,
        api_key: str,
        model_id: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Submit a request and poll until complete."""
        import os
        os.environ.setdefault("FAL_KEY", api_key)

        handler = await fal_client.submit_async(model_id, arguments=arguments)
        elapsed = 0.0
        while elapsed < POLL_TIMEOUT:
            status = await handler.status()
            if hasattr(status, "completed") and status.completed:
                return await handler.get()
            if hasattr(status, "status") and status.status in ("COMPLETED", "completed"):
                return await handler.get()
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

        raise asyncio.TimeoutError()

    async def should_volunteer(
        self,
        session_id: str,
        message_content: str,
        agent_config: Dict[str, Any],
    ) -> bool:
        volunteer_keywords = {
            "image", "picture", "photo", "draw", "generate",
            "artwork", "illustration", "render", "video clip",
            "upscale", "flux", "sdxl", "stable diffusion",
        }
        lower = message_content.lower()
        return any(kw in lower for kw in volunteer_keywords)
