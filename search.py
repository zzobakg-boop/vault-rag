#!/usr/bin/env python3
"""vault-search — Obsidian 볼트 시맨틱 검색 CLI"""

import sys
import os
import json
import argparse
import chromadb
import ollama

from config import (
    CHROMA_DB_PATH, EMBEDDING_MODEL,
    COLLECTION_NAME, DEFAULT_TOP_K
)


def search(query, top_k=DEFAULT_TOP_K, output_format="text"):
    """시맨틱 검색 수행"""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    try:
        collection = client.get_collection(COLLECTION_NAME)
    except ValueError:
        print("❌ 인덱스가 없습니다. 먼저 indexer.py를 실행하세요.")
        sys.exit(1)

    # 쿼리 임베딩
    response = ollama.embed(model=EMBEDDING_MODEL, input=query)
    query_embedding = response['embeddings'][0]

    # 검색
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    if output_format == "json":
        output = []
        for i in range(len(results['ids'][0])):
            output.append({
                "rank": i + 1,
                "file": results['metadatas'][0][i].get('source_file', ''),
                "score": round(1 - results['distances'][0][i], 4),
                "chunk": results['documents'][0][i][:500],
                "metadata": results['metadatas'][0][i]
            })
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"🔍 검색: \"{query}\" (상위 {top_k}건)\n")
        for i in range(len(results['ids'][0])):
            score = 1 - results['distances'][0][i]  # cosine similarity
            meta = results['metadatas'][0][i]
            doc = results['documents'][0][i]
            file_path = meta.get('source_file', 'unknown')

            print(f"{'─' * 60}")
            print(f"#{i+1} [{score:.4f}] 📄 {file_path}")
            if meta.get('tags'):
                print(f"   🏷️  {meta['tags']}")
            print(f"   {doc[:300]}{'...' if len(doc) > 300 else ''}")
            print()

        print(f"{'─' * 60}")
        print(f"📦 총 인덱스: {collection.count()}개 청크")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Obsidian 볼트 시맨틱 검색")
    parser.add_argument("query", help="검색 쿼리")
    parser.add_argument("-k", "--top-k", type=int, default=DEFAULT_TOP_K, help="반환 결과 수")
    parser.add_argument("-j", "--json", action="store_true", help="JSON 출력")

    args = parser.parse_args()
    search(args.query, top_k=args.top_k, output_format="json" if args.json else "text")
