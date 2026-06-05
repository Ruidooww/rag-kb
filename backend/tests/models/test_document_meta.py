import pytest
from pydantic import ValidationError

from app.models.document_meta import Audience, DocumentMetaSchema, Visibility


def test_defaults_are_safe() -> None:
    """默认值必须是最保守的：仅内部、中等敏感度、无跨部门共享。"""
    schema = DocumentMetaSchema()

    assert schema.audience is Audience.INTERNAL_ONLY
    assert schema.visibility is Visibility.INTERNAL
    assert schema.sensitivity == 3
    assert schema.owner_dept is None
    assert schema.shared_depts == []


def test_sensitivity_range_enforced() -> None:
    with pytest.raises(ValidationError):
        DocumentMetaSchema(sensitivity=0)
    with pytest.raises(ValidationError):
        DocumentMetaSchema(sensitivity=6)


def test_audience_enum_value() -> None:
    schema = DocumentMetaSchema(audience=Audience.PUBLIC)

    assert schema.audience.value == "public"


def test_visibility_rejects_unknown() -> None:
    with pytest.raises(ValidationError):
        DocumentMetaSchema(visibility="secret")  # type: ignore[arg-type]


def test_shared_depts_accepts_dept_list() -> None:
    schema = DocumentMetaSchema(shared_depts=["finance", "commerce"])

    assert schema.shared_depts == ["finance", "commerce"]


def test_shared_depts_default_factory_isolated() -> None:
    """default_factory 必须每次产新列表，避免实例间共享 mutable 默认值。"""
    a = DocumentMetaSchema()
    b = DocumentMetaSchema()
    a.shared_depts.append("tech")

    assert b.shared_depts == []
