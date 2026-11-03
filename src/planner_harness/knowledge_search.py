"""Deterministic retrieval over the permitted frozen corpus, with source excerpts."""

from collections import Counter
import math
import re

STOP = set("the a an and or to for of in how what with is can this that it as on by from into use".split())
STYLE_KINDS = {"entries", "domain_references", "guides"}
EXPERIENCE_KINDS = {"experience", "experience_evidence", "model_experience", "experience_contribution", "experience_case"}
ALIASES = {
    "lost face": "face identity person rebuilt source input",
    "same room": "original place every plane rebuild",
    "wording": "construction restated prompt",
    "budget": "attempts spend remaining generations",
    "omission": "plane counterpart missing",
    "camera turn": "first last second inspect",
    "人脸": "face identity person", "输入": "input continue restart source",
    "光照": "light medium logic", "改写": "construction restated prompt",
    "场景": "original place every plane", "水彩": "watercolor paper wash",
    "版画": "printmaking engraving woodcut", "丛林": "jungle forest vegetation roots",
    "粉彩": "pastel", "对称": "symmetry", "遗迹": "ruins weathered stone",
}


def terms(text):
    words = re.findall(r"[a-z0-9]+|[\u3400-\u9fff]+", text.casefold())
    result = []
    for word in words:
        if word in STOP:
            continue
        if re.fullmatch(r"[\u3400-\u9fff]+", word):
            result.extend(word[i:i+2] for i in range(max(1, len(word)-1)))
        else:
            result.append(word[:-1] if len(word) > 4 and word.endswith("s") and not word.endswith("ss") else word)
    return result


def normalized(text):
    return " ".join(re.findall(r"[\w]+", text.casefold()))


def contains_name(text, name):
    return f" {normalized(name)} " in f" {normalized(text)} "


def named_reference(query):
    quoted = re.search(r'["“]([^"”]+)["”]', query)
    if quoted:
        return quoted[1]
    # Capitalized multiword references are common in task/style queries. Report
    # their literal coverage; never turn a shared word into a matching work.
    match = re.search(r"\b(?:[A-Z][\w'-]+\s+)+[A-Z][\w'-]+\b", query)
    return match.group().strip() if match else None


def search(knowledge, query, limit=8, scope="all"):
    if scope not in {"all", "style", "experience"}:
        raise ValueError("Search scope is all, style or experience")
    if not knowledge.enabled:
        return {"query": query, "matches": [], "scope": "Knowledge disabled"}
    expanded = query + " " + " ".join(v for k, v in ALIASES.items() if k in query.casefold())
    requested = set(terms(query))
    tokens = set(terms(expanded))
    if not tokens:
        raise ValueError("Search needs substantive terms")
    name = named_reference(query)
    documents = []
    seen = set()
    for row in knowledge.items.values():
        if row["path"] in seen or row["kind"] == "original_source" or not row["path"].endswith(".md"):
            continue
        if scope == "style" and row["kind"] not in STYLE_KINDS:
            continue
        if scope == "experience" and row["kind"] not in EXPERIENCE_KINDS:
            continue
        seen.add(row["path"])
        text = knowledge.document(row)["text"]
        metadata = " ".join([row["title"], row.get("summary", ""), *row.get("questions", []), *row.get("aliases", []),
                             row.get("layer", ""), *row.get("tracks", []), *row.get("families", []),
                             *row.get("stages", []), *row.get("renderers", [])])
        counts = Counter(terms(text))
        meta = set(terms(metadata))
        documents.append((row, text, counts, meta))
    frequency = Counter(t for _, _, counts, meta in documents for t in set(counts) | meta)
    count = len(documents)
    average = sum(sum(c.values()) for _, _, c, _ in documents) / max(1, count)
    name_found = bool(name and any(contains_name(row["title"] + " " + text, name) for row, text, _, _ in documents))
    # When the requested work is absent, search its descriptive features. Shared
    # words in another work's title must not dominate this fallback ranking.
    feature_tokens = tokens - set(terms(name or ""))
    if name and not name_found and feature_tokens:
        tokens = feature_tokens
    weights = {t: math.log(1 + (count - frequency[t] + .5) / (frequency[t] + .5)) for t in tokens}
    results = []
    for row, text, counts, meta in documents:
        matched = tokens & (set(counts) | meta)
        if not matched:
            continue
        length = sum(counts.values())
        score = sum(weights[t] * (counts[t] * 2.2 / (counts[t] + 1.2 * (.25 + .75 * length / max(1, average))) + 1.5 * (t in meta)) for t in matched)
        exact_name = bool(name and contains_name(row["title"] + " " + text, name))
        if exact_name:
            score += 3 * sum(weights.values())
        # Reward coherent multiword matches, rather than independent generic
        # words in a navigation directory. Excerpts come from actual body prose.
        sequence = terms(query)
        body_sequence = " " + " ".join(terms(text)) + " "
        score += sum((weights.get(a, 0) + weights.get(b, 0)) * .3 for a, b in zip(sequence, sequence[1:]) if f" {a} {b} " in body_sequence)
        prose, fallback = [], []
        for line_number, line in enumerate(text.splitlines(), 1):
            hits = tokens & set(terms(line))
            if not hits:
                continue
            hit = (sum(weights[t] for t in hits), line_number, line)
            fallback.append(hit)
            if len(line.strip()) >= 60 and not line.lstrip().startswith(("#", "|", "![", '"', "```")):
                prose.append(hit)
        excerpts = sorted(prose or fallback, reverse=True)[:2]
        results.append({
            **row, "score": round(score, 6),
            "match_type": "named_reference" if exact_name else "related_reference" if name else "term_match",
            "matched_terms": sorted(requested & (set(counts) | meta)),
            "matches": [{"line": n, "excerpt": line[:1000], "excerpt_shortened": len(line) > 1000} for _, n, line in excerpts],
            "open": {"action": "read", "arguments": {"targets": [{"id": row["id"]}]}},
        })
    results.sort(key=lambda r: (-r["score"], r["id"]))
    return {
        "query": query, "expanded_query": expanded.strip(), "scope": scope,
        "method": "BM25 with title/metadata and phrase weighting over permitted local sources",
        "named_reference": {"text": name, "found_in_corpus": name_found} if name else None,
        "terms_absent_from_corpus": sorted(t for t in requested if not frequency[t]),
        "matches": results[:max(1, min(int(limit), 15))],
        "guidance": "Excerpts are source text. Open useful entries for their design relationships and references; search individual visual features or browse theme/media guides to explore alternatives.",
    }
