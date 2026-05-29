#!/usr/bin/env python3
"""위성볼트 (Geo-Teacher-Wiki) 별도 인덱싱.

메인 indexer.py의 VAULT_PATH·COLLECTION·METADATA를 환경변수로 override.
별도 ChromaDB collection (geo_teacher_wiki) + 별도 metadata 파일.
"""
import os
import sys

os.environ["VAULT_RAG_VAULT_PATH"] = os.path.expanduser(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Geo-Teacher-Wiki"
)
os.environ["VAULT_RAG_COLLECTION"] = "geo_teacher_wiki"
os.environ["VAULT_RAG_METADATA_FILE"] = "index_metadata_wiki.json"

# indexer.py를 그대로 실행 (env override가 모든 글로벌 변수에 적용)
import indexer

if __name__ == "__main__":
    full = "--full" in sys.argv
    if full:
        print("🔄 전체 재구축 모드")
    indexer.index_vault(full_rebuild=full)
