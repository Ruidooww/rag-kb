"""Document metadata schema anchor.

Used by:
- #24 (document_meta PG table): mirror these fields in SQLAlchemy ORM.
- #25 (Omni metadata extraction): prompt must produce these 5 ACL fields.
- #28 (dual-track ingest): persist these into Qdrant chunk payload.
- #42 (Phase 2 ACL middleware): read these fields to enforce filter.

Schema-only anchor. Does not build PG tables, write alembic migrations,
or touch Qdrant / business logic. The point is to lock field names,
types, enum values, and default values **before** 400 documents land
in storage so downstream tasks do not need to back-fill.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Audience(StrEnum):
    """文档受众边界。决定能否被对外渠道（公众号客服等）召回。

    - internal_only:    仅内部员工
    - customer_facing:  可推送给已签约客户（企微客户群、客户专属档案）
    - public:           完全公开（公众号匿名访问、官网知识库）
    """

    INTERNAL_ONLY = "internal_only"
    CUSTOMER_FACING = "customer_facing"
    PUBLIC = "public"


class Visibility(StrEnum):
    """敏感度等级。决定跨部门可见性。

    - public:        所有内部员工可见 + 可对外（若 audience 允许）
    - internal:      所有内部员工可见，跨部门可读
    - confidential:  仅 owner_dept ∪ shared_depts 可见
    """

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


class DocumentMetaSchema(BaseModel):
    """文档元数据 schema 锚点。

    字段语义：
    - audience: 文档能流向的最远边界（内部/客户/公开）
    - owner_dept: 文档归属部门 internal_code（如 tech / sales / finance），
      空表示通用文档。需配合 dept_mapping 表使用。
    - visibility: 敏感度等级，与 user.max_visibility 联合决定可见性。
    - sensitivity: 1-5 数值化敏感度，用于细粒度策略（如 5 级仅高管 + HR）。
    - shared_depts: 跨部门白名单。除 owner_dept 外明确授权可读的部门列表。
      仅在 visibility=confidential 时生效；空列表表示遵循默认 visibility 规则。
    """

    audience: Audience = Audience.INTERNAL_ONLY
    owner_dept: str | None = None
    visibility: Visibility = Visibility.INTERNAL
    sensitivity: int = Field(default=3, ge=1, le=5)
    shared_depts: list[str] = Field(
        default_factory=list,
        description=(
            "跨部门白名单。除 owner_dept 外，明确授权可读的部门 internal_code 列表。"
            "仅在 visibility=confidential 时生效；空列表表示遵循默认 visibility 规则。"
        ),
    )
