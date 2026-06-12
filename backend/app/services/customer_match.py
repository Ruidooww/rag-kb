"""Customer fuzzy matching service."""

from __future__ import annotations

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.customer import Customer, CustomerAlias
from app.models.customer import MatchResult

_COMPANY_SUFFIXES = ("股份有限公司", "有限责任公司", "有限公司", "公司")


def _normalize_for_fuzzy(value: str) -> str:
    normalized = value.strip()
    for suffix in _COMPANY_SUFFIXES:
        if normalized.endswith(suffix):
            return normalized.removesuffix(suffix).strip()
    return normalized


async def match(
    session: AsyncSession,
    query: str,
    *,
    fuzzy_threshold: int | None = None,
    limit: int | None = None,
) -> list[MatchResult]:
    """Match a customer by exact name, exact alias, then fuzzy score."""

    normalized_query = query.strip()
    if not normalized_query:
        return []

    threshold = (
        settings.customer_match_fuzzy_threshold if fuzzy_threshold is None else fuzzy_threshold
    )
    result_limit = settings.customer_match_limit if limit is None else limit
    if result_limit <= 0:
        return []

    rows = (
        await session.execute(
            select(Customer.id, Customer.name, CustomerAlias.alias)
            .outerjoin(CustomerAlias, CustomerAlias.customer_id == Customer.id)
            .order_by(Customer.id, CustomerAlias.id)
        )
    ).all()
    customers: dict[int, str] = {}
    aliases: list[tuple[str, int, str]] = []
    for customer_id, customer_name, alias in rows:
        customers.setdefault(customer_id, customer_name)
        if alias is not None:
            aliases.append((alias, customer_id, customer_name))

    exact = next(
        (
            (customer_id, customer_name)
            for customer_id, customer_name in customers.items()
            if customer_name == normalized_query
        ),
        None,
    )
    if exact is not None:
        customer_id, customer_name = exact
        return [
            MatchResult(
                customer_id=customer_id,
                customer_name=customer_name,
                score=100,
                method="exact",
            )
        ]

    alias_row = next(
        (
            (alias, customer_id, customer_name)
            for alias, customer_id, customer_name in aliases
            if alias == normalized_query
        ),
        None,
    )
    if alias_row is not None:
        alias, customer_id, customer_name = alias_row
        return [
            MatchResult(
                customer_id=customer_id,
                customer_name=customer_name,
                matched_alias=alias,
                score=100,
                method="alias_exact",
            )
        ]

    candidates: dict[str, tuple[int, str, str | None]] = {
        customer_name: (customer_id, customer_name, None)
        for customer_id, customer_name in customers.items()
    }
    for alias, customer_id, customer_name in aliases:
        candidates.setdefault(alias, (customer_id, customer_name, alias))

    candidate_items = list(candidates.items())
    extracted = process.extract(
        _normalize_for_fuzzy(normalized_query),
        [_normalize_for_fuzzy(text) for text, _record in candidate_items],
        scorer=fuzz.token_sort_ratio,
        limit=result_limit,
    )
    matches: list[MatchResult] = []
    seen_customer_ids: set[int] = set()
    for _text, score, index in extracted:
        if score < threshold:
            continue
        _original_text, record = candidate_items[index]
        customer_id, customer_name, matched_alias = record
        if customer_id in seen_customer_ids:
            continue
        seen_customer_ids.add(customer_id)
        matches.append(
            MatchResult(
                customer_id=customer_id,
                customer_name=customer_name,
                matched_alias=matched_alias,
                score=int(round(score)),
                method="fuzzy",
            )
        )
    return matches
