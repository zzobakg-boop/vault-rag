#!/usr/bin/env python3
"""위성볼트 (Geo-Teacher-Wiki) 별도 검색.

메인 search.py의 COLLECTION만 override.
"""
import os
import sys

os.environ["VAULT_RAG_VAULT_PATH"] = os.path.expanduser(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Geo-Teacher-Wiki"
)
os.environ["VAULT_RAG_COLLECTION"] = "geo_teacher_wiki"

import search

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 search_wiki.py <query> [top_k]")
        sys.exit(1)
    query = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    search.search(query, top_k=top_k)
