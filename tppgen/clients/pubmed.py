"""PubMed E-utilities. 3 requests/second without a key, 10 with one (NCBI_API_KEY)."""
from __future__ import annotations

import os

from ._http import request
from .. import cache

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
INTERVAL = 0.34  # keeps the keyless 3/sec limit


def _common() -> dict:
    params = {"db": "pubmed", "retmode": "json", "tool": "tppgen"}
    key = os.environ.get("NCBI_API_KEY")
    if key:
        params["api_key"] = key
    return params


def search(term: str, retmax: int = 20) -> list[str]:
    payload = {"term": term, "retmax": retmax}
    cached = cache.get("pubmed_search", payload)
    if cached is not None:
        return cached
    params = {**_common(), "term": term, "retmax": retmax, "sort": "relevance"}
    data = request("GET", f"{BASE}/esearch.fcgi", params=params, min_interval=INTERVAL)
    ids = data.get("esearchresult", {}).get("idlist", []) or []
    cache.put("pubmed_search", payload, ids)
    return ids


def summaries(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    payload = {"ids": sorted(pmids)}
    cached = cache.get("pubmed_summary", payload)
    if cached is not None:
        return cached
    params = {**_common(), "id": ",".join(pmids)}
    data = request("GET", f"{BASE}/esummary.fcgi", params=params, min_interval=INTERVAL)
    result = data.get("result", {})
    out = []
    for pmid in result.get("uids", []):
        rec = result.get(pmid, {})
        out.append(
            {
                "pmid": pmid,
                "title": rec.get("title"),
                "journal": rec.get("source"),
                "year": (rec.get("pubdate") or "")[:4],
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
        )
    cache.put("pubmed_summary", payload, out)
    return out


def mechanism_references(disease: str, target: str | None, limit: int = 8) -> list[dict]:
    """Literature supporting the mechanism, used to cite the MoA field."""
    term = f'"{disease}"[Title/Abstract]'
    if target:
        term += f' AND "{target}"[Title/Abstract]'
    term += " AND (mechanism[Title/Abstract] OR pathogenesis[Title/Abstract])"
    return summaries(search(term, limit))
