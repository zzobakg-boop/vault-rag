#!/usr/bin/env python3
"""vault-rag 헬스체크 — 인덱스 상태 확인 및 재구축"""

import os
import sys
import json
import chromadb

from config import CHROMA_DB_PATH, COLLECTION_NAME, VAULT_PATH


def healthcheck():
    """인덱스 상태 확인"""
    issues = []

    # 1. DB 경로 확인
    if not os.path.exists(CHROMA_DB_PATH):
        print("❌ ChromaDB 경로 없음 — 인덱싱이 필요합니다.")
        return False

    # 2. ChromaDB 연결
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    except Exception as e:
        print(f"❌ ChromaDB 연결 실패: {e}")
        issues.append("DB 연결 실패")
        return False

    # 3. 컬렉션 확인
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except ValueError:
        print(f"❌ 컬렉션 '{COLLECTION_NAME}' 없음 — 인덱싱이 필요합니다.")
        return False

    chunk_count = collection.count()

    # 4. 메타데이터 확인
    meta_path = os.path.join(os.path.dirname(__file__), "index_metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            meta = json.load(f)
        indexed_files = len(meta)
    else:
        indexed_files = 0
        issues.append("메타데이터 파일 없음")

    # 5. 볼트 파일 수 확인
    vault_files = 0
    for root, dirs, files in os.walk(VAULT_PATH):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        vault_files += sum(1 for f in files if f.endswith('.md') and not f.startswith('.'))

    # 6. 누락 파일 체크
    missing = vault_files - indexed_files
    if missing > 0:
        issues.append(f"{missing}개 파일 미인덱싱")

    # 결과 출력
    print("📊 vault-rag 헬스체크")
    print(f"{'─' * 40}")
    print(f"  볼트 파일 수: {vault_files}개")
    print(f"  인덱싱된 파일: {indexed_files}개")
    print(f"  총 청크 수: {chunk_count}개")
    print(f"  DB 크기: {get_dir_size(CHROMA_DB_PATH)}")
    print(f"{'─' * 40}")

    if issues:
        print(f"⚠️  문제 발견:")
        for issue in issues:
            print(f"  • {issue}")
        print(f"\n💡 해결: python3 indexer.py (증분) 또는 python3 indexer.py --full (전체 재구축)")
        return False
    else:
        print("✅ 정상!")
        return True


def get_dir_size(path):
    """디렉토리 크기 계산"""
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    if total < 1024:
        return f"{total}B"
    elif total < 1024 * 1024:
        return f"{total / 1024:.1f}KB"
    else:
        return f"{total / (1024 * 1024):.1f}MB"


if __name__ == "__main__":
    ok = healthcheck()
    sys.exit(0 if ok else 1)
