"""Experimental frozen contextual encoder via an existing local Ollama service."""
import httpx
import numpy as np


class OllamaEncoder:
    def __init__(self, url="http://127.0.0.1:11434", model="nomic-embed-text:latest"):
        parsed = httpx.URL(url)
        if parsed.host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Experiments require a loopback encoder")
        self.url, self.model = url, model

    def metadata(self):
        with httpx.Client(base_url=self.url, timeout=10, trust_env=False) as client:
            response = client.get("/api/tags")
            response.raise_for_status()
            match = next((row for row in response.json()["models"] if row["name"] == self.model), None)
            if not match:
                raise ValueError("Required encoder is not installed")
            return {"model": self.model, "digest": match["digest"], "model_bytes": match["size"]}

    def encode(self, texts, batch_size=16):
        batches = []
        with httpx.Client(base_url=self.url, timeout=120, trust_env=False) as client:
            for offset in range(0, len(texts), batch_size):
                response = client.post("/api/embed", json={"model": self.model,
                    "input": ["classification: " + text for text in texts[offset:offset + batch_size]],
                    "truncate": False, "keep_alive": "5m"})
                response.raise_for_status()
                values = np.asarray(response.json()["embeddings"], dtype=float)
                if (values.ndim != 2 or len(values) != len(texts[offset:offset + batch_size])
                        or not np.isfinite(values).all()):
                    raise ValueError("Invalid encoder response")
                batches.append(values)
        return np.concatenate(batches) if batches else np.empty((0, 0))
