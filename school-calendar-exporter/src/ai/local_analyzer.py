"""Local LLM analyzer using OpenAI-compatible API (Ollama / LM Studio / llama.cpp)."""
from __future__ import annotations

import json
import re
import time

from src.ai.prompts import SYSTEM_PROMPT, build_extraction_prompt
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "qwen2.5:7b"
MAX_RETRIES = 3
MAX_TEXT_CHARS = 80_000


class LocalAnalyzer:
    """Analyze calendar text using a locally running LLM via OpenAI-compatible API.

    Supports Ollama, LM Studio, llama.cpp server, and any other service that
    exposes the OpenAI Chat Completions endpoint.

    Usage (Ollama example):
        # 1. Install Ollama: https://ollama.com/
        # 2. Pull a model with good Japanese support:
        #      ollama pull qwen2.5:7b
        # 3. Run with --local flag:
        #      python main.py --local
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        api_key: str = "ollama",  # dummy key required by openai client
    ):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "openai パッケージが必要です。`pip install openai` を実行してください。"
            ) from e

        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        logger.info(f"LocalAnalyzer initialized: model={model}, base_url={base_url}")

    def analyze(self, text: str, categories: list[dict]) -> list[dict]:
        """Send *text* to local LLM and return a list of event dicts."""
        if len(text) > MAX_TEXT_CHARS:
            logger.warning(
                f"Text too long ({len(text)} chars), splitting into chunks"
            )
            return self._analyze_chunked(text, categories)
        return self._call_api(text, categories)

    def _analyze_chunked(self, text: str, categories: list[dict]) -> list[dict]:
        chunks = self._split_text(text, MAX_TEXT_CHARS)
        all_events: list[dict] = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Analyzing chunk {i + 1}/{len(chunks)}")
            events = self._call_api(chunk, categories)
            all_events.extend(events)
        return all_events

    def _split_text(self, text: str, max_chars: int) -> list[str]:
        lines = text.splitlines(keepends=True)
        chunks, current, current_len = [], [], 0
        for line in lines:
            if current_len + len(line) > max_chars and current:
                chunks.append("".join(current))
                current, current_len = [], 0
            current.append(line)
            current_len += len(line)
        if current:
            chunks.append("".join(current))
        return chunks

    def _call_api(self, text: str, categories: list[dict]) -> list[dict]:
        prompt = build_extraction_prompt(text, categories)
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"Local LLM API call attempt {attempt} (model={self.model})")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                )
                raw = response.choices[0].message.content or ""
                return self._parse_response(raw)
            except Exception as e:
                logger.warning(f"Local LLM error on attempt {attempt}: {e}")
                last_error = e
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)

        raise RuntimeError(
            f"Local LLM failed after {MAX_RETRIES} attempts: {last_error}"
        )

    def _parse_response(self, raw: str) -> list[dict]:
        """Extract JSON from the model response and return events list."""
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                json_str = match.group(0)
            else:
                raise ValueError(f"No JSON found in response:\n{raw[:500]}")

        data = json.loads(json_str)
        events = data.get("events", [])
        logger.info(f"Extracted {len(events)} events from local LLM response")
        return events
