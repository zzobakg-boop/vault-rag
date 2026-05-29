#!/usr/bin/env python3
"""vault-search — Obsidian 볼트 시맨틱 검색 CLI

2026-05-01 #3: bge-reranker-v2-m3 옵션 추가 (Pinecone 가이드 차용).
- 휴리스틱 reranker (default): 키워드 매칭·메타 정합·최신성 — 비용 0
- cross-encoder (--rerank=cross): BAAI/bge-reranker-v2-m3 — FlagEmbedding 설치 필요
"""

import sys
import os
import json
import re
import argparse
from datetime import datetime, timedelta
import chromadb
import ollama

from config import (
    CHROMA_DB_PATH, EMBEDDING_MODEL,
    COLLECTION_NAME, DEFAULT_TOP_K
)

# 2026-05-04: 환경변수로 collection override 가능 (위성볼트 검색용)
COLLECTION_NAME = os.environ.get("VAULT_RAG_COLLECTION", COLLECTION_NAME)

# 검색 → top RETRIEVE_K → reranker → top top_k 반환
RETRIEVE_K_MULTIPLIER = 4  # top_k의 4배 retrieve 후 rerank로 압축


def _heuristic_rerank(query, items):
    """비용 0 reranker. 키워드·메타·최신성 가중치.
    items: [{rank, score, doc, metadata, file}, ...]
    Returns: 같은 형식 + reranked_score
    """
    today = datetime.now().date()
    q_tokens = set(re.findall(r"[가-힣A-Za-z0-9]{2,}", query.lower()))
    if not q_tokens:
        return items

    for it in items:
        doc_lower = it["doc"].lower()
        meta = it.get("metadata") or {}
        # 1. 키워드 매칭 — 본문에 쿼리 토큰 빈도
        kw_hits = sum(doc_lower.count(t) for t in q_tokens)
        kw_score = min(kw_hits / max(len(q_tokens), 1), 5.0) / 5.0  # 0~1
        # 2. 메타 매칭 — tags·file_path에 토큰 포함
        meta_text = f"{meta.get('tags', '')} {meta.get('source_file', '')}".lower()
        meta_hits = sum(1 for t in q_tokens if t in meta_text)
        meta_score = min(meta_hits / max(len(q_tokens), 1), 1.0)
        # 3. 최신성 — date modified 가중 (없으면 0.5)
        recency_score = 0.5
        for date_field in ("date_modified", "date_created", "modified"):
            if date_field in meta:
                try:
                    d = datetime.strptime(str(meta[date_field])[:10], "%Y-%m-%d").date()
                    days_ago = (today - d).days
                    if days_ago <= 7: recency_score = 1.0
                    elif days_ago <= 30: recency_score = 0.8
                    elif days_ago <= 90: recency_score = 0.6
                    elif days_ago <= 365: recency_score = 0.4
                    else: recency_score = 0.2
                    break
                except Exception:
                    continue
        # 4. 길이 페널티 — 너무 짧은 청크
        length_score = 1.0 if len(it["doc"]) >= 200 else 0.5
        # 종합 (vector 60% + heuristic 40%)
        h_score = 0.4 * kw_score + 0.3 * meta_score + 0.2 * recency_score + 0.1 * length_score
        it["reranked_score"] = round(0.6 * it["score"] + 0.4 * h_score, 4)
    items.sort(key=lambda x: -x["reranked_score"])
    return items


def _cross_encoder_rerank(query, items):
    """BAAI/bge-reranker-v2-m3 cross-encoder. FlagEmbedding 설치 필요.
    설치 안 됐으면 휴리스틱 폴백."""
    try:
        from FlagEmbedding import FlagReranker
        reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
        pairs = [[query, it["doc"]] for it in items]
        scores = reranker.compute_score(pairs, normalize=True)
        for it, s in zip(items, scores):
            it["reranked_score"] = round(float(s), 4)
        items.sort(key=lambda x: -x["reranked_score"])
        return items
    except ImportError:
        return _heuristic_rerank(query, items)


def search(query, top_k=DEFAULT_TOP_K, output_format="text", rerank="heuristic"):
    """시맨틱 검색 수행 (+ reranker 1단)"""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    try:
        collection = client.get_collection(COLLECTION_NAME)
    except ValueError:
        print("❌ 인덱스가 없습니다. 먼저 indexer.py를 실행하세요.")
        sys.exit(1)

    # 쿼리 임베딩
    response = ollama.embed(model=EMBEDDING_MODEL, input=query)
    query_embedding = response['embeddings'][0]

    # 검색 — top_k의 4배 우선 retrieve (rerank 마진)
    retrieve_k = top_k * RETRIEVE_K_MULTIPLIER if rerank != "off" else top_k
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=retrieve_k,
        include=["documents", "metadatas", "distances"]
    )

    # raw items 구성
    items = []
    for i in range(len(results['ids'][0])):
        items.append({
            "rank": i + 1,
            "file": results['metadatas'][0][i].get('source_file', ''),
            "score": round(1 - results['distances'][0][i], 4),
            "doc": results['documents'][0][i],
            "metadata": results['metadatas'][0][i],
        })

    # rerank 1단
    if rerank == "cross":
        items = _cross_encoder_rerank(query, items)
    elif rerank == "heuristic":
        items = _heuristic_rerank(query, items)
    # off는 그대로

    items = items[:top_k]

    if output_format == "json":
        out = []
        for j, it in enumerate(items):
            out.append({
                "rank": j + 1,
                "file": it["file"],
                "score": it["score"],
                "reranked_score": it.get("reranked_score", it["score"]),
                "chunk": it["doc"][:500],
                "metadata": it["metadata"],
            })
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        rerank_label = f" + rerank({rerank})" if rerank != "off" else ""
        print(f"🔍 검색: \"{query}\" (상위 {top_k}건{rerank_label})\n")
        for j, it in enumerate(items):
            score = it.get("reranked_score", it["score"])
            print(f"{'─' * 60}")
            print(f"#{j+1} [{score:.4f}] 📄 {it['file']}")
            if it["metadata"].get("tags"):
                print(f"   🏷️  {it['metadata']['tags']}")
            doc = it["doc"]
            print(f"   {doc[:300]}{'...' if len(doc) > 300 else ''}")
            print()

        print(f"{'─' * 60}")
        print(f"📦 총 인덱스: {collection.count()}개 청크")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Obsidian 볼트 시맨틱 검색 (+ reranker)")
    parser.add_argument("query", help="검색 쿼리")
    parser.add_argument("-k", "--top-k", type=int, default=DEFAULT_TOP_K, help="반환 결과 수")
    parser.add_argument("-j", "--json", action="store_true", help="JSON 출력")
    parser.add_argument("--rerank", choices=["heuristic", "cross", "off"],
                        default="heuristic",
                        help="reranker (heuristic 기본·비용0 / cross BAAI/bge-reranker-v2-m3 / off)")

    args = parser.parse_args()
    search(args.query, top_k=args.top_k,
           output_format="json" if args.json else "text",
           rerank=args.rerank)
