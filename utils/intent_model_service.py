"""Lightweight intent model service for assistant chat."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class IntentModelService:
    """A tiny TF-IDF cosine similarity intent classifier."""

    def __init__(self, training_path: Path):
        self.training_path = training_path
        self.samples: List[Tuple[str, str]] = []
        self.idf: Dict[str, float] = {}
        self.min_confidence: float = 0.2
        self._load_and_train()

    def _load_and_train(self) -> None:
        payload = self._load_payload()
        intents = payload.get("intents", []) if isinstance(payload, dict) else []
        self.min_confidence = float(payload.get("min_confidence", 0.2)) if isinstance(payload, dict) else 0.2

        loaded_samples: List[Tuple[str, str]] = []
        for intent in intents:
            name = str(intent.get("name", "")).strip()
            if not name:
                continue
            for sample in intent.get("samples", []):
                text = str(sample or "").strip()
                if text:
                    loaded_samples.append((name, text))

        self.samples = loaded_samples
        self.idf = self._build_idf([text for _, text in self.samples])

    def _load_payload(self) -> dict:
        if not self.training_path.exists():
            return {"intents": []}
        try:
            return json.loads(self.training_path.read_text(encoding="utf-8"))
        except Exception:
            return {"intents": []}

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return _TOKEN_PATTERN.findall((text or "").lower())

    def _build_idf(self, corpus: List[str]) -> Dict[str, float]:
        doc_count = max(len(corpus), 1)
        doc_freq: Dict[str, int] = {}
        for text in corpus:
            unique = set(self._tokenize(text))
            for token in unique:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        idf_map: Dict[str, float] = {}
        for token, freq in doc_freq.items():
            idf_map[token] = math.log((1 + doc_count) / (1 + freq)) + 1
        return idf_map

    def _vectorize(self, text: str) -> Dict[str, float]:
        tokens = self._tokenize(text)
        if not tokens:
            return {}

        tf: Dict[str, float] = {}
        total = len(tokens)
        for token in tokens:
            tf[token] = tf.get(token, 0.0) + 1.0

        vector: Dict[str, float] = {}
        for token, count in tf.items():
            idf = self.idf.get(token)
            if idf is None:
                continue
            vector[token] = (count / total) * idf

        norm = math.sqrt(sum(value * value for value in vector.values()))
        if norm <= 0:
            return {}

        for token in list(vector.keys()):
            vector[token] = vector[token] / norm
        return vector

    @staticmethod
    def _cosine(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        if len(vec_a) > len(vec_b):
            vec_a, vec_b = vec_b, vec_a
        return sum(value * vec_b.get(token, 0.0) for token, value in vec_a.items())

    def predict(self, text: str) -> Dict[str, object]:
        query = str(text or "").strip()
        if not query or not self.samples:
            return {"intent": "unknown", "confidence": 0.0}

        query_vec = self._vectorize(query)
        if not query_vec:
            return {"intent": "unknown", "confidence": 0.0}

        best_intent = "unknown"
        best_score = 0.0
        best_sample = ""

        for intent_name, sample_text in self.samples:
            sample_vec = self._vectorize(sample_text)
            score = self._cosine(query_vec, sample_vec)
            if score > best_score:
                best_score = score
                best_intent = intent_name
                best_sample = sample_text

        if best_score < self.min_confidence:
            return {
                "intent": "unknown",
                "confidence": round(best_score, 4),
                "matched_sample": best_sample,
            }

        return {
            "intent": best_intent,
            "confidence": round(best_score, 4),
            "matched_sample": best_sample,
        }


_INTENT_MODEL: Optional[IntentModelService] = None


def get_intent_model() -> IntentModelService:
    """Return a singleton instance of intent model service."""
    global _INTENT_MODEL
    if _INTENT_MODEL is None:
        root = Path(__file__).resolve().parent.parent
        training_path = root / "data" / "assistant_intents.json"
        _INTENT_MODEL = IntentModelService(training_path)
    return _INTENT_MODEL
