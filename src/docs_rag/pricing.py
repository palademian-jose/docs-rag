"""Cost computation from pricing.json (PLAN.md shared contract 2).

Lookup order for a model id: exact key, vendor prefix stripped, dots normalised to dashes.
Unknown models cost 0 and are reported through ``PriceBook.unknown`` so a trace can flag them.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


class PriceBook:
    def __init__(self, prices: dict[str, dict[str, float]]) -> None:
        self.prices = {k: v for k, v in prices.items() if not k.startswith("_")}
        self.unknown: set[str] = set()

    @classmethod
    def load(cls, path: Path | str) -> PriceBook:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data)

    def _candidates(self, model: str) -> list[str]:
        names = [model]
        if "/" in model:
            names.append(model.split("/", 1)[1])
        names += [n.replace(".", "-") for n in list(names)]
        # Dated snapshots such as claude-sonnet-4-5-20250929 -> claude-sonnet-4-5
        for n in list(names):
            parts = n.rsplit("-", 1)
            if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) >= 6:
                names.append(parts[0])
        return names

    def lookup(self, model: str | None) -> dict[str, float] | None:
        if not model:
            return None
        for name in self._candidates(model):
            if name in self.prices:
                return self.prices[name]
        self.unknown.add(model)
        return None

    def token_cost(self, model: str | None, input_tokens: int, output_tokens: int) -> float:
        price = self.lookup(model)
        if price is None:
            return 0.0
        return round(
            input_tokens / 1_000_000 * price.get("input_per_m", 0.0)
            + output_tokens / 1_000_000 * price.get("output_per_m", 0.0),
            8,
        )

    def call_cost(self, model: str | None, calls: int = 1) -> float:
        price = self.lookup(model)
        if price is None:
            return 0.0
        return round(calls * price.get("per_call", 0.0), 8)


@lru_cache
def load_pricing(path: str = "pricing.json") -> PriceBook:
    p = Path(path)
    if not p.exists():
        # Fall back to the copy shipped next to the package (installed in a container).
        p = Path(__file__).resolve().parents[2] / "pricing.json"
    return PriceBook.load(p) if p.exists() else PriceBook({})
