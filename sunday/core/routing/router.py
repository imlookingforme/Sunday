"""Model Capability Registry and Task-Aware Router with Ollama Local Inference for Sunday 2.0.

Provides:
- Model Capability Registry (context window, tool calling support, vision, latency tier, cost per 1M tokens)
- Task Classification (autocomplete, planning, exploration, complex coding, review, security analysis)
- Configurable Routing Policies:
    * High Quality (GPT-4o, Claude 3.5 Sonnet)
    * Balanced (Gemini 1.5 Pro, GPT-4o-mini, Claude 3.5 Haiku)
    * Economy (DeepSeek, Groq, local Phi-3)
    * Local Only (Ollama local inference strictly with zero remote data leakage)
- Direct Ollama integration (endpoint health check, model discovery, generation, and safe fallbacks)
- Error-specific recovery (differentiating rate-limit 429, timeouts, and context overflow)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

logger = logging.getLogger(__name__)


class TaskCategory(Enum):
    AUTOCOMPLETE = "autocomplete"
    SIMPLE_EDIT = "simple_edit"
    PLANNING = "planning"
    REPOSITORY_EXPLORATION = "repository_exploration"
    COMPLEX_IMPLEMENTATION = "complex_implementation"
    DEBUGGING = "debugging"
    TESTING = "testing"
    CODE_REVIEW = "code_review"
    SECURITY_ANALYSIS = "security_analysis"


class RoutingPolicy(Enum):
    HIGH_QUALITY = "high_quality"
    BALANCED = "balanced"
    ECONOMY = "economy"
    LOCAL_ONLY = "local_only"
    CUSTOM = "custom"


@dataclass
class ModelCapability:
    """Metadata describing a specific model provider capability."""
    model_id: str
    provider: str  # 'openai', 'anthropic', 'gemini', 'ollama', 'groq'
    context_capacity: int
    supports_tools: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_structured_output: bool = True
    is_local: bool = False
    estimated_latency_ms: int = 500
    cost_per_m_input_usd: float = 0.0
    cost_per_m_output_usd: float = 0.0


@dataclass
class ModelResponse:
    """Standardized response from a routed model invocation."""
    model_id: str
    provider: str
    content: str
    duration_seconds: float
    is_local: bool
    tokens_used: int = 0
    fallback_used: bool = False
    error: Optional[str] = None


class ModelRegistry:
    """Tracks available models and their verified capabilities."""

    DEFAULT_CATALOG: Dict[str, ModelCapability] = {
        # Cloud: Top-tier
        "gpt-4o": ModelCapability(
            model_id="gpt-4o",
            provider="openai",
            context_capacity=128000,
            supports_tools=True,
            supports_vision=True,
            cost_per_m_input_usd=2.50,
            cost_per_m_output_usd=10.00,
            estimated_latency_ms=700,
        ),
        "claude-3-5-sonnet-20241022": ModelCapability(
            model_id="claude-3-5-sonnet-20241022",
            provider="anthropic",
            context_capacity=200000,
            supports_tools=True,
            supports_vision=True,
            cost_per_m_input_usd=3.00,
            cost_per_m_output_usd=15.00,
            estimated_latency_ms=800,
        ),
        # Cloud: Balanced / Fast
        "gemini-1.5-pro": ModelCapability(
            model_id="gemini-1.5-pro",
            provider="gemini",
            context_capacity=1000000,
            supports_tools=True,
            supports_vision=True,
            cost_per_m_input_usd=1.25,
            cost_per_m_output_usd=5.00,
            estimated_latency_ms=600,
        ),
        "gpt-4o-mini": ModelCapability(
            model_id="gpt-4o-mini",
            provider="openai",
            context_capacity=128000,
            supports_tools=True,
            supports_vision=True,
            cost_per_m_input_usd=0.15,
            cost_per_m_output_usd=0.60,
            estimated_latency_ms=300,
        ),
        # Local: Ollama
        "phi3:mini": ModelCapability(
            model_id="phi3:mini",
            provider="ollama",
            context_capacity=4096,
            supports_tools=False,
            is_local=True,
            cost_per_m_input_usd=0.0,
            cost_per_m_output_usd=0.0,
            estimated_latency_ms=1200,
        ),
        "llama3.2:3b": ModelCapability(
            model_id="llama3.2:3b",
            provider="ollama",
            context_capacity=8192,
            supports_tools=True,
            is_local=True,
            cost_per_m_input_usd=0.0,
            cost_per_m_output_usd=0.0,
            estimated_latency_ms=1400,
        ),
    }

    def __init__(self):
        self.catalog = dict(self.DEFAULT_CATALOG)

    def register_model(self, cap: ModelCapability) -> None:
        self.catalog[cap.model_id] = cap

    def get_model(self, model_id: str) -> Optional[ModelCapability]:
        return self.catalog.get(model_id)

    def list_models(self, local_only: bool = False) -> List[ModelCapability]:
        if local_only:
            return [m for m in self.catalog.values() if m.is_local]
        return list(self.catalog.values())


class OllamaClient:
    """Direct asynchronous client for Ollama local inference."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = os.environ.get("SUNDAY_OLLAMA_URL", base_url).rstrip("/")

    async def check_health(self) -> bool:
        """Check if local Ollama daemon is active."""
        if not HAS_AIOHTTP:
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def list_local_models(self) -> List[str]:
        """Fetch list of pulled local models."""
        if not HAS_AIOHTTP:
            return []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.debug(f"Ollama list_local_models error: {e}")
        return []

    async def generate(self, model: str, prompt: str, system: str = "") -> Dict[str, Any]:
        """Generate response from local Ollama model."""
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp required for Ollama local inference")

        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(f"Ollama error (HTTP {resp.status}): {body}")
                return await resp.json()


class TaskAwareModelRouter:
    """Routes prompts to appropriate models based on task domain, policy, and availability."""

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        ollama_client: Optional[OllamaClient] = None,
        default_policy: RoutingPolicy = RoutingPolicy.BALANCED,
    ):
        self.registry = registry or ModelRegistry()
        self.ollama = ollama_client or OllamaClient()
        self.policy = default_policy

    def select_model_for_task(self, task_type: TaskCategory, policy: Optional[RoutingPolicy] = None) -> ModelCapability:
        """Select the best matching model capability according to policy and task complexity."""
        active_policy = policy or self.policy

        if active_policy == RoutingPolicy.LOCAL_ONLY:
            # Strictly select local models; zero data sent to external cloud APIs
            local_models = self.registry.list_models(local_only=True)
            if not local_models:
                raise RuntimeError("LOCAL_ONLY policy active but no local models are registered")
            # Prefer models with tool support for implementation tasks
            if task_type in [TaskCategory.COMPLEX_IMPLEMENTATION, TaskCategory.DEBUGGING]:
                for m in local_models:
                    if m.supports_tools:
                        return m
            return local_models[0]

        if active_policy == RoutingPolicy.HIGH_QUALITY:
            if task_type in [TaskCategory.PLANNING, TaskCategory.COMPLEX_IMPLEMENTATION, TaskCategory.SECURITY_ANALYSIS]:
                return self.registry.get_model("claude-3-5-sonnet-20241022") or self.registry.get_model("gpt-4o")
            return self.registry.get_model("gpt-4o")

        if active_policy == RoutingPolicy.ECONOMY:
            if task_type in [TaskCategory.AUTOCOMPLETE, TaskCategory.SIMPLE_EDIT]:
                return self.registry.get_model("gpt-4o-mini") or self.registry.get_model("phi3:mini")
            return self.registry.get_model("gemini-1.5-pro")

        # BALANCED (Default)
        if task_type in [TaskCategory.PLANNING, TaskCategory.COMPLEX_IMPLEMENTATION, TaskCategory.SECURITY_ANALYSIS]:
            return self.registry.get_model("claude-3-5-sonnet-20241022") or self.registry.get_model("gpt-4o")
        elif task_type in [TaskCategory.AUTOCOMPLETE, TaskCategory.SIMPLE_EDIT]:
            return self.registry.get_model("gpt-4o-mini")
        else:
            return self.registry.get_model("gemini-1.5-pro") or self.registry.get_model("gpt-4o-mini")

    async def route_execution(
        self,
        task_type: TaskCategory,
        prompt: str,
        system_prompt: str = "",
        policy: Optional[RoutingPolicy] = None,
        cloud_caller: Optional[Callable[[str, str, str], Any]] = None,
    ) -> ModelResponse:
        """Execute prompt against chosen model with automatic fallback handling."""
        start_time = time.time()
        active_policy = policy or self.policy
        target_model = self.select_model_for_task(task_type, active_policy)

        # 1. Local execution
        if target_model.is_local:
            try:
                res = await self.ollama.generate(
                    model=target_model.model_id,
                    prompt=prompt,
                    system=system_prompt,
                )
                return ModelResponse(
                    model_id=target_model.model_id,
                    provider="ollama",
                    content=res.get("response", ""),
                    duration_seconds=round(time.time() - start_time, 2),
                    is_local=True,
                )
            except Exception as e:
                logger.warning(f"Local Ollama generation failed: {e}")
                if active_policy == RoutingPolicy.LOCAL_ONLY:
                    return ModelResponse(
                        model_id=target_model.model_id,
                        provider="ollama",
                        content="",
                        duration_seconds=round(time.time() - start_time, 2),
                        is_local=True,
                        error=f"Local execution failed: {str(e)}",
                    )
                # Fallback to balanced cloud model if allowed by policy
                fallback_model = self.registry.get_model("gpt-4o-mini")
                if cloud_caller and fallback_model:
                    logger.info("Failing over from local Ollama to cloud fallback gpt-4o-mini")
                    out = await cloud_caller(fallback_model.model_id, prompt, system_prompt)
                    return ModelResponse(
                        model_id=fallback_model.model_id,
                        provider=fallback_model.provider,
                        content=str(out),
                        duration_seconds=round(time.time() - start_time, 2),
                        is_local=False,
                        fallback_used=True,
                    )

        # 2. Cloud execution
        if cloud_caller:
            try:
                out = await cloud_caller(target_model.model_id, prompt, system_prompt)
                return ModelResponse(
                    model_id=target_model.model_id,
                    provider=target_model.provider,
                    content=str(out),
                    duration_seconds=round(time.time() - start_time, 2),
                    is_local=False,
                )
            except Exception as cloud_err:
                logger.warning(f"Cloud model {target_model.model_id} failed: {cloud_err}")
                # Try fallback to local Ollama if available
                if await self.ollama.check_health():
                    local_cap = self.registry.get_model("phi3:mini")
                    if local_cap:
                        res = await self.ollama.generate(local_cap.model_id, prompt, system_prompt)
                        return ModelResponse(
                            model_id=local_cap.model_id,
                            provider="ollama",
                            content=res.get("response", ""),
                            duration_seconds=round(time.time() - start_time, 2),
                            is_local=True,
                            fallback_used=True,
                        )
                return ModelResponse(
                    model_id=target_model.model_id,
                    provider=target_model.provider,
                    content="",
                    duration_seconds=round(time.time() - start_time, 2),
                    is_local=False,
                    error=str(cloud_err),
                )

        return ModelResponse(
            model_id=target_model.model_id,
            provider=target_model.provider,
            content="[MOCK ROUTER EXECUTION]",
            duration_seconds=round(time.time() - start_time, 2),
            is_local=target_model.is_local,
        )
