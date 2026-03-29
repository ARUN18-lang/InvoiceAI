import logging
import math
import re
from typing import Any, Literal, Sequence

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from openai import AsyncOpenAI
from pymongo.errors import PyMongoError

from app.core.config import Settings
from app.schemas.invoice import ChatRequest, ChatResponse, ChatSourceCitation
from app.schemas.mongo_documents import COLLECTION_INVOICES
from app.services.embedding_service import EmbeddingService
from app.services.graph_sync_service import GraphSyncService
from app.services.rag_excerpt import best_excerpt_for_query

logger = logging.getLogger(__name__)


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _split_answer_and_suggestions(text: str) -> tuple[str, list[str]]:
    raw = text.strip()
    patterns = [
        r"\n\s*Suggestions:\s*\n",
        r"\n\s*suggestions:\s*\n",
        r"\n\s*---\s*Suggestions\s*---\s*\n",
    ]
    best_idx = -1
    best_len = 0
    for p in patterns:
        m = re.search(p, raw, flags=re.IGNORECASE)
        if m and m.start() > best_idx:
            best_idx = m.start()
            best_len = len(m.group(0))
    if best_idx == -1:
        return raw, []
    main = raw[:best_idx].strip()
    rest = raw[best_idx + best_len :].strip()
    follow: list[str] = []
    for line in rest.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^[-*•]\s+", line):
            follow.append(re.sub(r"^[-*•]\s+", "", line).strip())
        elif line.startswith('"') and line.endswith('"'):
            follow.append(line[1:-1])
        elif len(follow) < 6 and len(line) < 200:
            follow.append(line)
    return main, follow[:6]


class InvoiceRAGService:
    """
    Retrieval: Atlas $vectorSearch when configured, else in-app cosine similarity + graph expansion.

    Generation: multi-turn aware OpenAI chat with invoice context on the latest user turn.
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase[Any],
        client: AsyncOpenAI,
        settings: Settings,
        graph: GraphSyncService,
    ) -> None:
        self._db = db
        self._client = client
        self._settings = settings
        self._embeddings = EmbeddingService(client, settings)
        self._graph = graph
        self._inv = db[COLLECTION_INVOICES]

    async def answer(self, request: ChatRequest, *, workspace_id: ObjectId) -> ChatResponse:
        user_message = request.message.strip()
        invoice_ids = request.invoice_ids
        history = request.normalized_history()

        query_vec = await self._embeddings.embed_text(user_message)
        top = await self._retrieve(workspace_id, query_vec, invoice_ids)
        source_ids = [str(d["_id"]) for d in top]

        graph_extra: list[str] = []
        if source_ids:
            graph_extra = await self._graph.get_related_invoice_ids(source_ids, limit=12)

        extra_docs: list[dict[str, Any]] = []
        if graph_extra:
            oids: list[ObjectId] = []
            for x in graph_extra:
                try:
                    oids.append(ObjectId(x))
                except Exception:
                    continue
            if oids:
                cursor = self._inv.find(
                    {"_id": {"$in": oids}, "workspace_id": workspace_id},
                    {
                        "vendor_name": 1,
                        "invoice_number": 1,
                        "total_amount": 1,
                        "category": 1,
                        "raw_text_preview": 1,
                        "raw_text": 1,
                    },
                )
                extra_docs = await cursor.to_list(length=20)

        # Batch-load text for excerpts (query-relevant slices, not only fixed preview head)
        all_for_context = top + extra_docs
        excerpt_by_id = await self._excerpts_for_docs(workspace_id, all_for_context, user_message)

        context_blocks: list[str] = []
        for d in all_for_context:
            iid = str(d.get("_id", ""))
            excerpt = excerpt_by_id.get(iid) or ""
            block = (
                f"Invoice id={d.get('_id')}; vendor={d.get('vendor_name')}; "
                f"number={d.get('invoice_number')}; total={d.get('total_amount')}; "
                f"category={d.get('category')}\n"
                f"Relevant excerpt: {excerpt}"
            )
            context_blocks.append(block)

        context = "\n\n---\n\n".join(context_blocks) if context_blocks else "(no invoices retrieved)"

        system = (
            "You are a finance assistant for invoice data. Use only the invoice context provided for facts. "
            "The context may include related invoices from the knowledge graph (same vendor or category). "
            "If facts are missing, say what is missing.\n"
            "Structure answers clearly: short summary first, then bullet details when helpful. "
            "Format the main answer with Markdown (headings, **bold** for key numbers, bullet lists). "
            "Use plain language; use INR when currency is unspecified.\n"
            "After your main answer, add a blank line, then a line exactly 'Suggestions:' then 2–4 lines, "
            "each starting with '- ' followed by a concise follow-up question the user might ask next."
        )

        user_turn = f"Context:\n{context}\n\nQuestion:\n{user_message}"

        msg_payload: list[dict[str, str]] = [{"role": "system", "content": system}]
        for m in history:
            msg_payload.append({"role": m.role, "content": m.content.strip()[:12000]})
        msg_payload.append({"role": "user", "content": user_turn})

        completion = await self._client.chat.completions.create(
            model=self._settings.openai_model,
            messages=msg_payload,
        )
        raw_answer = completion.choices[0].message.content or ""
        answer, follow = _split_answer_and_suggestions(raw_answer)
        if not answer:
            answer = raw_answer.strip()

        merged_sources = list(dict.fromkeys(source_ids + graph_extra))

        citations: list[ChatSourceCitation] = []
        seen_cit: set[str] = set()
        excerpt_cap = 1500
        no_preview_msg = "(No text stored for this invoice — open it for full extracted text.)"

        def _cite(d: dict[str, Any], via: Literal["semantic_search", "knowledge_graph"]) -> None:
            iid = str(d.get("_id", ""))
            if not iid or iid in seen_cit:
                return
            seen_cit.add(iid)
            excerpt = (excerpt_by_id.get(iid) or "")[:excerpt_cap].strip()
            if not excerpt:
                excerpt = no_preview_msg
            citations.append(
                ChatSourceCitation(
                    invoice_id=iid,
                    vendor_name=d.get("vendor_name"),
                    invoice_number=d.get("invoice_number"),
                    total_amount=d.get("total_amount"),
                    category=d.get("category"),
                    text_excerpt=excerpt,
                    via=via,
                )
            )

        for d in top:
            _cite(d, "semantic_search")
        for d in extra_docs:
            _cite(d, "knowledge_graph")

        enrich_oids: list[ObjectId] = []
        for c in citations:
            if c.text_excerpt != no_preview_msg:
                continue
            try:
                enrich_oids.append(ObjectId(c.invoice_id))
            except Exception:
                continue
        if enrich_oids:
            try:
                cur = self._inv.aggregate(
                    [
                        {
                            "$match": {
                                "_id": {"$in": enrich_oids},
                                "workspace_id": workspace_id,
                            }
                        },
                        {
                            "$project": {
                                "_id": 1,
                                "snippet": {
                                    "$substrCP": [
                                        {"$ifNull": ["$raw_text", ""]},
                                        0,
                                        excerpt_cap,
                                    ]
                                },
                            }
                        },
                    ]
                )
                rows = await cur.to_list(length=len(enrich_oids))
                snips = {str(r["_id"]): (r.get("snippet") or "").strip() for r in rows}
                citations = [
                    c.model_copy(
                        update={
                            "text_excerpt": best_excerpt_for_query(
                                text=snips[c.invoice_id], query=user_message, cap=excerpt_cap
                            )
                            or c.text_excerpt
                        }
                    )
                    if snips.get(c.invoice_id)
                    else c
                    for c in citations
                ]
            except Exception:
                logger.exception("Could not enrich citations from raw_text")

        return ChatResponse(
            answer=answer.strip(),
            source_invoice_ids=merged_sources,
            source_citations=citations,
            suggested_follow_ups=follow,
        )

    async def _excerpts_for_docs(
        self,
        workspace_id: ObjectId,
        docs: list[dict[str, Any]],
        query: str,
    ) -> dict[str, str]:
        oids: list[ObjectId] = []
        for d in docs:
            try:
                oids.append(ObjectId(str(d["_id"])))
            except Exception:
                continue
        if not oids:
            return {}
        cursor = self._inv.find(
            {"workspace_id": workspace_id, "_id": {"$in": oids}},
            {"raw_text": 1, "raw_text_preview": 1},
        )
        loaded = await cursor.to_list(length=len(oids))
        out: dict[str, str] = {}
        for row in loaded:
            iid = str(row["_id"])
            full = (row.get("raw_text") or "").strip()
            prev = (row.get("raw_text_preview") or "").strip()
            base = full if len(full) >= len(prev) else (full or prev)
            out[iid] = best_excerpt_for_query(text=base, query=query, cap=1200)
        return out

    async def _retrieve(
        self,
        workspace_id: ObjectId,
        query_vec: list[float],
        invoice_ids: list[str] | None,
    ) -> list[dict[str, Any]]:
        index_name = self._settings.atlas_vector_index_name.strip()
        if index_name and query_vec:
            atlas_docs = await self._try_atlas_vector_search(workspace_id, query_vec, invoice_ids, index_name)
            if atlas_docs is not None:
                return atlas_docs
        return await self._retrieve_cosine(workspace_id, query_vec, invoice_ids)

    async def _try_atlas_vector_search(
        self,
        workspace_id: ObjectId,
        query_vec: list[float],
        invoice_ids: list[str] | None,
        index_name: str,
    ) -> list[dict[str, Any]] | None:
        filt: dict[str, Any] = {"workspace_id": workspace_id}
        if invoice_ids:
            oids: list[ObjectId] = []
            for x in invoice_ids:
                try:
                    oids.append(ObjectId(x))
                except Exception:
                    continue
            if not oids:
                return []
            filt = {"$and": [filt, {"_id": {"$in": oids}}]}

        pipeline: list[dict[str, Any]] = [
            {
                "$vectorSearch": {
                    "index": index_name,
                    "path": "embedding",
                    "queryVector": query_vec,
                    "numCandidates": max(50, self._settings.atlas_vector_num_candidates),
                    "limit": 8,
                    "filter": filt,
                }
            },
            {
                "$project": {
                    "embedding": 0,
                    "raw_text": 0,
                }
            },
        ]
        try:
            cur = self._db[COLLECTION_INVOICES].aggregate(pipeline)
            out = await cur.to_list(length=20)
            return out
        except PyMongoError as e:
            logger.warning("Atlas vector search unavailable or misconfigured (%s); using cosine fallback", e)
            return None

    async def _retrieve_cosine(
        self,
        workspace_id: ObjectId,
        query_vec: list[float],
        invoice_ids: list[str] | None,
    ) -> list[dict[str, Any]]:
        candidates = await self._inv.find(
            {
                "workspace_id": workspace_id,
                "embedding": {"$exists": True, "$ne": None},
            },
            {
                "embedding": 1,
                "vendor_name": 1,
                "invoice_number": 1,
                "total_amount": 1,
                "invoice_date": 1,
                "category": 1,
                "raw_text_preview": 1,
            },
        ).to_list(length=500)

        scored: list[tuple[float, str, dict[str, Any]]] = []
        for doc in candidates:
            emb = doc.get("embedding") or []
            if not emb:
                continue
            if invoice_ids:
                sid = str(doc.get("_id"))
                if sid not in invoice_ids:
                    continue
            score = _cosine_similarity(query_vec, emb)
            scored.append((score, str(doc.get("_id", "")), doc))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [d for _, _, d in scored[:8]]
