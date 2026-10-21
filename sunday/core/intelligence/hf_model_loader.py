"""HuggingFace Model Loader - Unified lazy-loading model manager for local HF inference."""

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


class HFModelLoader:
    """Singleton lazy-loader for HuggingFace neural models."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._models: dict[str, Any] = {}
                cls._instance._pipelines: dict[str, Any] = {}
        return cls._instance

    def get_embedding_model(self, model_name: str = "all-MiniLM-L6-v2") -> Any | None:
        """Lazy-load sentence-transformers model for semantic embeddings."""
        if model_name in self._models:
            return self._models[model_name]

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {model_name}")
            model = SentenceTransformer(model_name)
            self._models[model_name] = model
            return model
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer '{model_name}': {e}")
            return None

    def get_zero_shot_pipeline(self, model_name: str = "facebook/bart-large-mnli") -> Any | None:
        """Lazy-load zero-shot classification pipeline for fluid intent routing."""
        key = f"zero-shot:{model_name}"
        if key in self._pipelines:
            return self._pipelines[key]

        try:
            from transformers import pipeline

            logger.info(f"Loading zero-shot classification pipeline: {model_name}")
            # device = -1 (CPU default) or 0 if cuda is active
            pipe = pipeline("zero-shot-classification", model=model_name, device=-1)
            self._pipelines[key] = pipe
            return pipe
        except Exception as e:
            logger.warning(f"Could not load zero-shot pipeline '{model_name}': {e}")
            return None

    def get_ner_pipeline(self, model_name: str = "dslim/bert-base-NER") -> Any | None:
        """Lazy-load token classification / NER pipeline."""
        key = f"ner:{model_name}"
        if key in self._pipelines:
            return self._pipelines[key]

        try:
            from transformers import pipeline

            logger.info(f"Loading NER pipeline: {model_name}")
            pipe = pipeline("ner", model=model_name, aggregation_strategy="simple", device=-1)
            self._pipelines[key] = pipe
            return pipe
        except Exception as e:
            logger.warning(f"Could not load NER pipeline '{model_name}': {e}")
            return None

    def get_sentiment_pipeline(
        self, model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    ) -> Any | None:
        """Lazy-load sentiment analysis pipeline for mood detection."""
        key = f"sentiment:{model_name}"
        if key in self._pipelines:
            return self._pipelines[key]

        try:
            from transformers import pipeline

            logger.info(f"Loading sentiment pipeline: {model_name}")
            pipe = pipeline("sentiment-analysis", model=model_name, device=-1)
            self._pipelines[key] = pipe
            return pipe
        except Exception as e:
            logger.warning(f"Could not load sentiment pipeline '{model_name}': {e}")
            return None

    def get_loaded_models_info(self) -> dict[str, Any]:
        """Returns details on currently loaded in-memory HF pipelines."""
        return {
            "embedding_models": list(self._models.keys()),
            "pipelines": list(self._pipelines.keys()),
            "count": len(self._models) + len(self._pipelines),
        }
