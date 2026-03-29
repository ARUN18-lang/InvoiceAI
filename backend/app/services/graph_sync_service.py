import logging
from datetime import date, datetime
from typing import Any

from app.db.neo4j_client import Neo4jManager
from app.schemas.invoice import ParsedInvoiceFields
from app.services.validation_service import _normalize_vendor

logger = logging.getLogger(__name__)


def _date_to_str(d: date | datetime | None) -> str | None:
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date().isoformat()
    return d.isoformat()


class GraphSyncService:
    """Syncs invoice entities into Neo4j for Graph RAG and relational traversal."""

    def __init__(self, neo4j: Neo4jManager) -> None:
        self._neo4j = neo4j

    async def upsert_invoice_graph(
        self,
        mongo_id: str,
        parsed: ParsedInvoiceFields,
        category: str | None,
    ) -> None:
        if not self._neo4j.enabled:
            return

        vendor_key = _normalize_vendor(parsed.vendor_name) or "unknown"
        vendor_name = parsed.vendor_name or "Unknown"
        cat = category or "other"

        async with self._neo4j.session() as session:
            await session.run(
                """
                MERGE (v:Vendor {key: $vendor_key})
                ON CREATE SET v.name = $vendor_name
                ON MATCH SET v.name = coalesce(v.name, $vendor_name)
                MERGE (c:Category {name: $category})
                MERGE (i:Invoice {mongo_id: $mongo_id})
                SET i.number = $number,
                    i.total = $total,
                    i.currency = $currency,
                    i.date = $date,
                    i.vendor_key = $vendor_key
                MERGE (i)-[:FROM_VENDOR]->(v)
                MERGE (i)-[:IN_CATEGORY]->(c)
                """,
                mongo_id=mongo_id,
                vendor_key=vendor_key,
                vendor_name=vendor_name,
                category=cat,
                number=parsed.invoice_number,
                total=parsed.total_amount,
                currency=parsed.currency or "INR",
                date=_date_to_str(parsed.invoice_date),
            )

    async def get_related_invoice_ids(self, mongo_ids: list[str], limit: int = 20) -> list[str]:
        """Expand context via graph neighbors (same vendor / same category)."""
        if not self._neo4j.enabled or not mongo_ids:
            return []
        async with self._neo4j.session() as session:
            result = await session.run(
                """
                MATCH (i:Invoice)
                WHERE i.mongo_id IN $ids
                MATCH (i)-[:FROM_VENDOR|IN_CATEGORY]-(hub)
                MATCH (hub)<-[:FROM_VENDOR|IN_CATEGORY]-(j:Invoice)
                WHERE NOT j.mongo_id IN $ids
                RETURN DISTINCT j.mongo_id AS mid
                LIMIT $limit
                """,
                ids=mongo_ids,
                limit=limit,
            )
            out: list[str] = []
            async for record in result:
                mid = record["mid"]
                if mid:
                    out.append(str(mid))
            return out
