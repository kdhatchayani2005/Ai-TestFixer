import json
import re
import requests

class AIAgent:
    def __init__(self, api_url="http://localhost:11434/api/generate", model="llama3"):
        self.api_url = api_url
        self.model = model

    def run(self, failed_locator, candidates, error_type, page_title):
        """
        Attempts to get an AI suggestion from local Ollama.
        If Ollama is unavailable or times out, falls back to the
        highest-similarity DOM candidate automatically.
        This ensures healing always works regardless of Ollama status.
        """
        # Sort candidates by similarity score descending
        sorted_candidates = sorted(candidates, key=lambda x: x.get("similarity_score", 0), reverse=True)

        # Try Ollama first with a short 30s timeout
        try:
            candidate_list_str = str(sorted_candidates[:5])  # Top 5 only to keep prompt concise

            prompt = (
                "You are an AI test automation expert. A Selenium test failed.\n"
                "Failed locator: " + str(failed_locator) + "\n"
                "Error: " + str(error_type) + "\n"
                "Page: " + str(page_title) + "\n"
                "DOM candidates found: " + candidate_list_str + "\n\n"
                "Return ONLY valid JSON with no extra text:\n"
                "{\n"
                "  \"replacement\": \"<best candidate value>\",\n"
                "  \"confidence\": <integer 0-100>,\n"
                "  \"reason\": \"<one sentence explanation>\"\n"
                "}"
            )

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 100,
                    "temperature": 0.1
                }
            }

            response = requests.post(self.api_url, json=payload, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            raw_text = response_data.get("response", "").strip()

            parsed = self._parse_json_response(raw_text)
            parsed["source"] = "ollama"
            print("[AIAgent] Ollama suggestion: replace '" + str(failed_locator) + "' -> '" + str(parsed.get("replacement")) + "' (confidence: " + str(parsed.get("confidence")) + "%)")
            return parsed

        except Exception as ollama_err:
            # Ollama unavailable or slow — use DOM similarity fallback
            print("[AIAgent] Ollama unavailable (" + type(ollama_err).__name__ + "). Using DOM similarity fallback.")
            return self._dom_fallback(failed_locator, sorted_candidates)

    def _dom_fallback(self, failed_locator, sorted_candidates):
        """
        Smart fallback: picks the highest-scoring DOM candidate
        whose value differs from the failed locator.
        Computes confidence from the similarity score.
        """
        if not sorted_candidates:
            raise ValueError(
                "No DOM candidates found for '" + str(failed_locator) + "'. "
                "Cannot heal without Ollama or DOM candidates."
            )

        # Pick the best candidate that is not identical to the failed locator
        best = None
        for c in sorted_candidates:
            if c.get("value", "").strip() != str(failed_locator).strip():
                best = c
                break

        # If all candidates match the failed locator, pick the top one anyway
        if best is None:
            best = sorted_candidates[0]

        replacement = best["value"]
        similarity  = best.get("similarity_score", 0.5)
        confidence  = int(min(similarity * 100, 95))   # Cap at 95% for DOM-only fixes

        reason = (
            "DOM similarity fallback: '" + str(replacement) + "' found in page source "
            "with similarity score " + str(round(similarity, 2)) + " compared to failed locator '" + str(failed_locator) + "'."
        )

        print("[AIAgent] DOM fallback selected: '" + str(failed_locator) + "' -> '" + str(replacement) + "' (confidence: " + str(confidence) + "%)")

        return {
            "replacement": replacement,
            "confidence": confidence,
            "reason": reason,
            "source": "dom_fallback"
        }

    def _parse_json_response(self, text):
        """Robustly parses a JSON string from LLM output."""
        cleaned = text.strip()

        # Strip markdown code fences
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)
        else:
            start = cleaned.find('{')
            end   = cleaned.rfind('}')
            if start != -1 and end != -1:
                cleaned = cleaned[start:end + 1]

        # Try standard JSON
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Convert Python-style single-quoted dict to JSON
        try:
            converted = re.sub(r"'(\w+)'\s*:", r'"\1":', cleaned)
            converted = re.sub(r":\s*'([^']*)'",  r': "\1"', converted)
            return json.loads(converted)
        except Exception:
            pass

        # Last resort: ast.literal_eval
        try:
            import ast
            return ast.literal_eval(cleaned)
        except Exception as e:
            raise ValueError("Failed to parse AI response: " + str(text)) from e
