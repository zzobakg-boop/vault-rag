#!/usr/bin/env python3
"""위성볼트 (Geo-Teacher-Wiki) 별도 인덱싱. — 🔴 2026-06-27 폐기됨·호출 금지

⚠️ 이 스크립트는 더 이상 쓰지 않는다. 실행하면 chromadb 1.5.7 rust bindings가
옛 geo_teacher_wiki HNSW 세그먼트를 로드하다 **SIGSEGV(exit 139)** 로 죽는다.
출력이 4줄에서 끊기므로 "멈춘 것처럼" 보이지만 크래시다.

배경(memory/reference_vault_rag.md 6/27 사고):
· brew chromadb 업그레이드로 옛 대형 HNSW 로드 시 segfault. cheap 복구 3종 전부 실패
  (HNSW 재구축=hollow / embeddings_queue pruned / collection.get 불일치).
· 정공법은 --full 재임베딩(수시간)뿐인데 **가치 낮음으로 판정**
  — 위성볼트 검색 주력이 qmd(`geo-teacher-wiki` 컬렉션)이고 정상이기 때문.
· 천대현 승인 하에 chromadb geo_teacher_wiki = **폐기**, search_wiki.py는 qmd 셤으로 전환.

👉 위성볼트를 재인덱싱하려면 **qmd를 쓴다**:  qmd update && qmd embed
👉 위성볼트 검색:  python3 search_wiki.py "<쿼리>"  (내부적으로 qmd vsearch 위임)

그래도 굳이 chromadb 재임베딩을 하려면(수시간·권장 안 함):
  VAULT_RAG_FORCE_WIKI_CHROMA=1 python3 indexer_wiki.py --full
"""
import os
import sys

if not os.environ.get("VAULT_RAG_FORCE_WIKI_CHROMA"):
    sys.exit(
        "🛑 indexer_wiki.py는 2026-06-27 폐기된 경로입니다 (실행 시 chromadb segfault).\n"
        "   위성볼트 인덱싱은 qmd를 쓰세요:  qmd update && qmd embed\n"
        "   근거: memory/reference_vault_rag.md 6/27 사고 · search_wiki.py는 이미 qmd 셤.\n"
        "   (정말 재임베딩하려면 VAULT_RAG_FORCE_WIKI_CHROMA=1 · 수시간 소요·권장 안 함)"
    )

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
