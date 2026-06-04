"""入库 5 份测试文档。

用法：
    cd backend
    uv run python scripts/ingest_test_docs.py
"""

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.rag_pipeline import ingest_file  # noqa: E402


async def main() -> None:
    fixtures_dir = Path(__file__).parents[1] / "tests" / "fixtures" / "sample_docs"
    total_chunks = 0
    for file in sorted(fixtures_dir.glob("*.md")):
        chunks = await ingest_file(file)
        print(f"  入库 {file.name}: {chunks} chunks")  # noqa: T201
        total_chunks += chunks
    print(f"\n总计：{total_chunks} chunks")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
