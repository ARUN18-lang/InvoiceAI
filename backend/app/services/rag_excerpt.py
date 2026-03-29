"""Pick a query-relevant slice of invoice text so sources vary per question (not only the fixed preview head)."""

from __future__ import annotations

import re

_STOP = frozenset(
    "the a an is are was were be been being have has had do does did will would could should may might must "
    "shall can need ought used to of in for on with at by from as into through during before after above below "
    "between under again further then once here there when where why how all each few more most other some such "
    "no nor not only own same so than too very just and but if or because until while about against i you he she "
    "it we they what which who this that these those am".split()
)

# Headings alone (e.g. "## Bioplex", "## 16.12.2021") often win term overlap but are useless as the only excerpt.
_MIN_SUBSTANCE_LEN = 140


def _query_terms(query: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9]+", query.lower())
    return {w for w in words if len(w) > 1 and w not in _STOP}


def _is_low_substance_chunk(chunk: str) -> bool:
    s = chunk.strip()
    if len(s) < 12:
        return True
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    if not lines:
        return True
    if len(lines) == 1 and lines[0].startswith("#") and len(s) < 160:
        return True
    head_lines = sum(1 for ln in lines if ln.startswith("#"))
    if head_lines == len(lines) and len(s) < 220:
        return True
    return False


def _split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    if len(parts) <= 1:
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    return parts


def _expand_from_paragraphs(paragraphs: list[str], start_idx: int, cap: int) -> str:
    """Append following paragraphs until excerpt is substantive or cap is reached."""
    if start_idx < 0 or start_idx >= len(paragraphs):
        return ""
    pieces: list[str] = []
    n = 0
    for j in range(start_idx, len(paragraphs)):
        p = paragraphs[j].strip()
        if not p:
            continue
        sep = 2 if pieces else 0
        if n + sep + len(p) > cap:
            if not pieces:
                return p[:cap] + ("…" if len(p) > cap else "")
            break
        if pieces:
            n += 2
        pieces.append(p)
        n += len(p)
        if n >= _MIN_SUBSTANCE_LEN:
            break
    out = "\n\n".join(pieces)
    if len(out) > cap:
        return out[: cap - 1] + "…"
    return out


def best_excerpt_for_query(*, text: str, query: str, cap: int = 1200) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    terms = _query_terms(query)
    if not terms:
        out = text[:cap] + ("…" if len(text) > cap else "")
        return out

    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return ""

    scored: list[tuple[int, int, int, str]] = []
    for i, para in enumerate(paragraphs):
        if len(para) < 8:
            continue
        low = para.lower()
        term_score = sum(low.count(t) for t in terms)
        scored.append((term_score, len(para), i, para))

    if not scored:
        return text[:cap] + ("…" if len(text) > cap else "")

    max_score = max(s[0] for s in scored)

    def pick_among(cands: list[tuple[int, int, int, str]]) -> tuple[int, str]:
        """Return (paragraph_index, paragraph_text) — prefer longer chunk on tie, de-prioritize low-substance when tied."""
        non_weak = [s for s in cands if not _is_low_substance_chunk(s[3])]
        pool = non_weak if non_weak else cands
        best = max(pool, key=lambda s: (s[0], s[1]))
        return best[2], best[3]

    matching = [s for s in scored if s[0] == max_score]
    start_idx, _ = pick_among(matching)

    if max_score == 0:
        non_weak_all = [s for s in scored if not _is_low_substance_chunk(s[3])]
        if non_weak_all:
            start_idx, _ = pick_among(non_weak_all)
        else:
            start_idx = max(scored, key=lambda s: s[1])[2]

    excerpt = _expand_from_paragraphs(paragraphs, start_idx, cap)
    if excerpt.strip():
        return excerpt

    return text[:cap] + ("…" if len(text) > cap else "")
