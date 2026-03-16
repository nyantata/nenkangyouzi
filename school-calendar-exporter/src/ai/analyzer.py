import json
import re
import time

import anthropic

from src.ai.prompts import SYSTEM_PROMPT, build_extraction_prompt
from src.utils.logger import get_logger

logger = get_logger(__name__)

MODEL = "claude-sonnet-4-20250514"
MAX_RETRIES = 3
# Claude's context window is large, but chunk if text exceeds this threshold
MAX_TEXT_CHARS = 80_000


class Analyzer:
    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key)

    def analyze(self, text: str, categories: list[dict]) -> list[dict]:
        """Send *text* to Claude and return a list of event dicts."""
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
                logger.info(f"Claude API call attempt {attempt}")
                response = self.client.messages.create(
                    model=MODEL,
                    max_tokens=8192,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = response.content[0].text
                return self._parse_response(raw)
            except anthropic.APIError as e:
                logger.warning(f"API error on attempt {attempt}: {e}")
                last_error = e
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)

        raise RuntimeError(
            f"Claude API failed after {MAX_RETRIES} attempts: {last_error}"
        )

    def _parse_response(self, raw: str) -> list[dict]:
        """Extract JSON from the model response and return events list."""
        # Strip markdown code fences if present
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Try to find raw JSON object
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                json_str = match.group(0)
            else:
                raise ValueError(f"No JSON found in response:\n{raw[:500]}")

        data = json.loads(json_str)
        events = data.get("events", [])
        logger.info(f"Extracted {len(events)} events from API response")
        return events
