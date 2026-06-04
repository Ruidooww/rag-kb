import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.models.query import SourceChunk
from app.services import rag_pipeline
from app.services.qdrant_store import get_qdrant_client
from app.services.rag_pipeline import generate_answer, ingest_file, retrieve


def _has_real_llm_api_key() -> bool:
    api_key = settings.llm_api_key.get_secret_value()
    return bool(api_key) and not api_key.startswith("sk-请填入")


requires_real_llm_key = pytest.mark.skipif(
    not _has_real_llm_api_key(),
    reason="需要真实 LLM_API_KEY",
)


@pytest.fixture
def sample_doc() -> Path:
    return Path(__file__).parents[1] / "fixtures" / "sample_docs" / "product_x_manual.md"


@pytest.fixture
def rag_test_collection(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    collection = f"{settings.qdrant_collection}_rag_pytest"
    monkeypatch.setattr(settings, "qdrant_collection", collection)
    client = get_qdrant_client()
    if client.collection_exists(collection):
        client.delete_collection(collection)
    yield collection
    if client.collection_exists(collection):
        client.delete_collection(collection)


@pytest.mark.integration
async def test_ingest_file_creates_chunks(sample_doc: Path, rag_test_collection: str) -> None:
    chunks = await ingest_file(sample_doc, collection=rag_test_collection)

    assert chunks > 0


@pytest.mark.integration
async def test_retrieve_returns_top_n(sample_doc: Path, rag_test_collection: str) -> None:
    await ingest_file(sample_doc, collection=rag_test_collection)

    sources = await retrieve("产品 X 怎么安装？", top_k=5, rerank_n=2)

    assert 0 < len(sources) <= 2
    assert all(source.doc_id == "product_x_manual" for source in sources)


async def test_generate_answer_uses_prompt_template(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_path = tmp_path / "base_qa.txt"
    prompt_path.write_text("资料:\n{sources}\n问题:{query}\n回答:", encoding="utf-8")
    captured: dict[str, str] = {}

    class FakeLLM:
        def complete(self, prompt: str) -> SimpleNamespace:
            captured["prompt"] = prompt
            return SimpleNamespace(text="安装前复制配置文件。[来源: product_x_manual]")

    monkeypatch.setattr(rag_pipeline, "PROMPT_PATH", prompt_path)
    monkeypatch.setattr(rag_pipeline, "get_llm", lambda: FakeLLM())
    sources = [
        SourceChunk(
            doc_id="product_x_manual",
            chunk_id="product_x_manual:0",
            text="安装产品 X 前需要复制配置文件。",
            score=0.91,
            metadata={"chunk_index": 0},
        )
    ]

    answer = await generate_answer("产品 X 怎么安装？", sources)

    assert answer == "安装前复制配置文件。[来源: product_x_manual]"
    assert "--- 文档: product_x_manual ---" in captured["prompt"]
    assert "产品 X 怎么安装？" in captured["prompt"]


@requires_real_llm_key
@pytest.mark.integration
async def test_generate_answer_skipped_without_real_key() -> None:
    sources = [
        SourceChunk(
            doc_id="product_x_manual",
            chunk_id="product_x_manual:0",
            text="产品 X 安装需要复制配置文件并启动 Docker 服务。",
            score=0.9,
            metadata={"chunk_index": 0},
        )
    ]

    answer = await generate_answer("产品 X 怎么安装？", sources)

    assert answer
    assert "来源" in answer


async def test_ingest_unsupported_format_raises(tmp_path: Path) -> None:
    unsupported = tmp_path / "manual.pdf"
    unsupported.write_bytes(b"%PDF-1.4")

    with pytest.raises(ValidationError):
        await ingest_file(unsupported)


def test_ingest_script_resolves_app_when_run_directly() -> None:
    backend_root = Path(__file__).parents[2]
    script_path = backend_root / "scripts" / "ingest_test_docs.py"
    code = f"""
import runpy
import sys
from pathlib import Path

backend_root = Path(r"{backend_root}")
script_path = Path(r"{script_path}")
sys.path = [str(script_path.parent)] + [
    path for path in sys.path
    if path and Path(path).resolve() != backend_root.resolve()
]
runpy.run_path(str(script_path), run_name="not_main")
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=backend_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
