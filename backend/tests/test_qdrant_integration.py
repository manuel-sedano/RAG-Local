"""Tests opcionales contra Qdrant real (upsert, búsqueda, delete por filtro).

Requisitos:

  docker compose up -d qdrant
  export TEST_QDRANT_URL='http://127.0.0.1:6333'

Los tests usan una colección efímera por ejecución y la eliminan al finalizar.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest

from app.core.config import clear_settings_cache, get_settings
from app.models.document import Chunk, Document
from app.services.embeddings.fake import embed_texts_fake
from app.services.qdrant.client import get_qdrant_client
from app.services.qdrant.collection import ensure_collection
from app.services.qdrant.payload import build_chunk_payload, normalize_tags
from app.services.qdrant.store import (
    delete_document_vectors,
    search_chunks,
    upsert_document_vectors,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_QDRANT_URL", "").strip(),
    reason="Define TEST_QDRANT_URL (p. ej. http://127.0.0.1:6333) para tests con Qdrant real.",
)


@pytest.fixture
def qdrant_settings(monkeypatch: pytest.MonkeyPatch):
    url = os.environ["TEST_QDRANT_URL"].strip()
    collection = f"rag_chunks_test_{uuid.uuid4().hex[:10]}"
    monkeypatch.setenv("TEST_QDRANT_URL", url)
    monkeypatch.setenv("QDRANT_COLLECTION", collection)
    monkeypatch.setenv("QDRANT_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "test")
    clear_settings_cache()
    settings = get_settings()
    client = get_qdrant_client(settings)
    try:
        client.get_collections()
    except Exception as exc:
        pytest.skip(
            f"Qdrant no alcanzable ({url}): {exc}. "
            "Levanta el servicio: `docker compose up -d qdrant`."
        )
    yield settings, client
    if client.collection_exists(collection):
        client.delete_collection(collection)
    clear_settings_cache()


def test_normalize_tags_list_and_dict() -> None:
    assert normalize_tags(["a", "b"]) == ["a", "b"]
    assert normalize_tags({"x": 1, "y": 2}) == ["x", "y"]
    assert normalize_tags(None) == []


def _test_settings(**overrides: object):
    clear_settings_cache()
    base: dict[str, object] = {
        "environment": "test",
        "qdrant_snippet_max_chars": 80,
        "embedding_fake_dimension": 32,
    }
    base.update(overrides)
    from app.core.config import Settings

    return Settings(**base)


def test_build_chunk_payload_snippet() -> None:
    settings = _test_settings()
    kb_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        kb_id=kb_id,
        uploaded_by_user_id=owner_id,
        filename_original="manual.pdf",
        storage_path=f"{kb_id}/file.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        sha256="a" * 64,
        language="es",
        source="manual.pdf",
        tags=["finanzas", "viaticos"],
        status="READY",
    )
    chunk = Chunk(
        id=chunk_id,
        document_id=doc_id,
        kb_id=kb_id,
        chunk_index=2,
        text="La política de viáticos establece límites claros para el personal.",
        page_start=3,
        page_end=3,
        embedding_model="bge-m3",
        qdrant_point_id=str(chunk_id),
        created_at=datetime.now(UTC),
    )
    payload = build_chunk_payload(doc, chunk, settings)
    assert payload["kb_id"] == str(kb_id)
    assert payload["doc_id"] == str(doc_id)
    assert payload["chunk_id"] == str(chunk_id)
    assert payload["owner_user_id"] == str(owner_id)
    assert payload["tags"] == ["finanzas", "viaticos"]
    assert payload["chunk_index"] == 2
    assert len(payload["text"]) <= settings.qdrant_snippet_max_chars


def test_upsert_search_and_delete_by_kb_filter(qdrant_settings: tuple) -> None:
    settings, raw_client = qdrant_settings
    kb_a = uuid.uuid4()
    kb_b = uuid.uuid4()
    doc_a = uuid.uuid4()
    doc_b = uuid.uuid4()
    chunk_a = uuid.uuid4()
    chunk_b = uuid.uuid4()

    text_a = "Documento alpha con término único zetaplano"
    text_b = "Documento beta en otra base zetaplano"
    vec_a = embed_texts_fake([text_a], settings)[0]
    vec_b = embed_texts_fake([text_b], settings)[0]
    dim = len(vec_a)
    ensure_collection(raw_client, settings, dim)

    doc_row_a = Document(
        id=doc_a,
        kb_id=kb_a,
        filename_original="a.pdf",
        storage_path=f"{kb_a}/a.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        sha256=uuid.uuid4().hex + uuid.uuid4().hex,
        tags=["alpha"],
        status="READY",
    )
    doc_row_b = Document(
        id=doc_b,
        kb_id=kb_b,
        filename_original="b.pdf",
        storage_path=f"{kb_b}/b.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        sha256=uuid.uuid4().hex + uuid.uuid4().hex,
        tags=["beta"],
        status="READY",
    )
    now = datetime.now(UTC)
    chunk_row_a = Chunk(
        id=chunk_a,
        document_id=doc_a,
        kb_id=kb_a,
        chunk_index=0,
        text=text_a,
        embedding_model="bge-m3",
        qdrant_point_id=str(chunk_a),
        created_at=now,
    )
    chunk_row_b = Chunk(
        id=chunk_b,
        document_id=doc_b,
        kb_id=kb_b,
        chunk_index=0,
        text=text_b,
        embedding_model="bge-m3",
        qdrant_point_id=str(chunk_b),
        created_at=now,
    )

    def _fake_session(chunks: list[Chunk]):
        class _FakeSession:
            def scalars(self, _stmt):
                class _R:
                    def all(inner_self):
                        return chunks

                return _R()

        return _FakeSession()

    metrics_a = upsert_document_vectors(
        _fake_session([chunk_row_a]),  # type: ignore[arg-type]
        doc_row_a,
        [(str(chunk_a), vec_a)],
        settings,
    )
    assert metrics_a["qdrant_status"] == "done"
    assert metrics_a["qdrant_upsert_count"] == 1

    metrics_b = upsert_document_vectors(
        _fake_session([chunk_row_b]),  # type: ignore[arg-type]
        doc_row_b,
        [(str(chunk_b), vec_b)],
        settings,
    )
    assert metrics_b["qdrant_upsert_count"] == 1

    hits_a = search_chunks(settings, query_vector=vec_a, kb_id=kb_a, limit=5)
    assert len(hits_a) >= 1
    assert hits_a[0]["payload"]["doc_id"] == str(doc_a)
    assert all(h["payload"]["kb_id"] == str(kb_a) for h in hits_a)

    hits_b_from_a_query = search_chunks(settings, query_vector=vec_a, kb_id=kb_b, limit=5)
    assert hits_b_from_a_query == [] or all(
        h["payload"]["kb_id"] == str(kb_b) for h in hits_b_from_a_query
    )

    delete_document_vectors(settings, kb_id=kb_a, doc_id=doc_a)
    client = get_qdrant_client(settings)
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    remaining = client.count(
        collection_name=settings.qdrant_collection,
        count_filter=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=str(doc_a)))]
        ),
    )
    assert remaining.count == 0

    still_b = client.count(
        collection_name=settings.qdrant_collection,
        count_filter=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=str(doc_b)))]
        ),
    )
    assert still_b.count == 1
