from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import ARRAY, CheckConstraint, Integer
from sqlalchemy.exc import IntegrityError

from app.db.base import Base, SessionLocal, engine
from app.db.models.document_meta import DocumentMeta
from app.models.customer import DocumentMetaCreate
from app.models.document_meta import DocumentMetaSchema


@pytest_asyncio.fixture(scope="module", loop_scope="module", autouse=True)
async def ensure_document_meta_table() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


def _check_constraint_names() -> set[str]:
    return {
        constraint.name
        for constraint in DocumentMeta.__table__.constraints
        if isinstance(constraint, CheckConstraint) and constraint.name is not None
    }


def test_audience_default_is_internal_only() -> None:
    default = DocumentMeta.__table__.columns["audience"].default

    assert default is not None
    assert default.arg == "internal_only"
    assert "ck_document_meta_audience" in _check_constraint_names()


def test_owner_dept_can_be_null() -> None:
    assert DocumentMeta.__table__.columns["owner_dept"].nullable is True


@pytest.mark.asyncio(loop_scope="module")
async def test_visibility_check_constraint_rejects_unknown() -> None:
    assert "ck_document_meta_visibility" in _check_constraint_names()

    async with SessionLocal() as session:
        session.add(
            DocumentMeta(
                doc_id="doc-invalid-visibility",
                doc_type="manual",
                title="Invalid visibility",
                storage_key="documents/doc-invalid-visibility",
                visibility="restricted",
            )
        )

        with pytest.raises(IntegrityError):
            await session.flush()


def test_sensitivity_is_int_range_1_to_5() -> None:
    column = DocumentMeta.__table__.columns["sensitivity"]

    assert isinstance(column.type, Integer)
    assert column.default is not None
    assert column.default.arg == 3
    assert "ck_document_meta_sensitivity" in _check_constraint_names()


@pytest.mark.parametrize("sensitivity", [0, 6])
@pytest.mark.asyncio(loop_scope="module")
async def test_sensitivity_check_constraint_rejects_0_and_6(sensitivity: int) -> None:
    async with SessionLocal() as session:
        session.add(
            DocumentMeta(
                doc_id=f"doc-invalid-sensitivity-{sensitivity}",
                doc_type="manual",
                title="Invalid sensitivity",
                storage_key=f"documents/doc-invalid-sensitivity-{sensitivity}",
                sensitivity=sensitivity,
            )
        )

        with pytest.raises(IntegrityError):
            await session.flush()


def test_shared_depts_stays_array_of_string_32() -> None:
    column_type = DocumentMeta.__table__.columns["shared_depts"].type

    assert isinstance(column_type, ARRAY)
    assert column_type.item_type.length == 32


@pytest.mark.asyncio(loop_scope="module")
async def test_orm_matches_pydantic_schema() -> None:
    acl_values = DocumentMetaSchema().model_dump(mode="json")

    async with SessionLocal() as session:
        document = DocumentMeta(
            doc_id="doc-anchor-contract",
            doc_type="manual",
            title="Anchor contract",
            storage_key="documents/doc-anchor-contract",
            **acl_values,
        )
        session.add(document)
        await session.flush()

        assert document.audience == "internal_only"
        assert document.owner_dept is None
        assert document.visibility == "internal"
        assert document.sensitivity == 3
        assert document.shared_depts == []


def test_document_meta_create_matches_anchor_defaults() -> None:
    data = DocumentMetaCreate(
        doc_id="doc-create-contract",
        doc_type="manual",
        title="Create contract",
        storage_key="documents/doc-create-contract",
    )

    assert data.audience == "internal_only"
    assert data.owner_dept is None
    assert data.visibility == "internal"
    assert data.sensitivity == 3
    assert data.shared_depts == []
