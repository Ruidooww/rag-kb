"""CLI for matching a customer name or alias."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.base import SessionLocal  # noqa: E402
from app.services.customer_match import match  # noqa: E402


async def _main(query: str) -> int:
    async with SessionLocal() as session:
        results = await match(session, query)
        if not results:
            print(f"NO_MATCH: {query!r}")  # noqa: T201 - CLI stdout is intentional
            return 1
        for result in results:
            print(  # noqa: T201 - CLI stdout is intentional
                f"[{result.method:11s}] score={result.score:3d} "
                f"id={result.customer_id} name={result.customer_name} "
                f"alias={result.matched_alias or '-'}"
            )
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: match_customer.py <query>")  # noqa: T201 - CLI stdout is intentional
        sys.exit(2)
    sys.exit(asyncio.run(_main(sys.argv[1])))
