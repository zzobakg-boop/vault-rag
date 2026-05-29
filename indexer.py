#!/usr/bin/env python3
"""Obsidian 볼트 인덱서 — 마크다운 파일을 청킹하여 ChromaDB에 저장"""

import os
import sys
import re
import hashlib
import json
import time
import chromadb
import ollama

from config import (
    VAULT_PATH, CHROMA_DB_PATH, EMBEDDING_MODEL,
    CHUNK_SIZE, CHUNK_OVERLAP, COLLECTION_NAME
)

METADATA_PATH = os.path.join(
    os.path.dirname(__file__),
    os.environ.get("VAULT_RAG_METADATA_FILE", "index_metadata.json")
)


def load_metadata():
    """이전 인덱싱 메타데이터 로드"""
    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH, "r") as f:
            return json.load(f)
    return {}


def save_metadata(meta):
    """인덱싱 메타데이터 저장"""
    with open(METADATA_PATH, "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def get_file_hash(filepath):
    """파일 내용의 MD5 해시"""
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def parse_frontmatter(content):
    """YAML 프론트매터 파싱 (간단 버전)"""
    meta = {}
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if match:
        fm_text = match.group(1)
        body = content[match.end():]
        for line in fm_text.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key in ('type', 'category', 'source', 'date created'):
                    meta[key] = val
                elif key == 'tags':
                    continue  # 멀티라인 태그는 스킵
        # 태그 리스트 수집
        tag_matches = re.findall(r'^\s*-\s+(\S+)', fm_text, re.MULTILINE)
        if tag_matches:
            meta['tags'] = ', '.join(tag_matches)
        return meta, body
    return meta, content


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """텍스트를 겹치는 청크로 분할"""
    chunks = []
    # 빈 줄 기준으로 문단 분할 먼저 시도
    paragraphs = re.split(r'\n\s*\n', text)

    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # 문단 자체가 chunk_size보다 크면 강제 분할
            if len(para) > chunk_size:
                for i in range(0, len(para), chunk_size - overlap):
                    chunks.append(para[i:i + chunk_size])
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [text[:chunk_size]] if text.strip() else []


def get_markdown_files(vault_path):
    """볼트에서 모든 마크다운 파일 수집"""
    md_files = []
    for root, dirs, files in os.walk(vault_path):
        # 숨김 폴더 및 .trash 제외
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if f.endswith('.md') and not f.startswith('.'):
                md_files.append(os.path.join(root, f))
    return md_files


def embed_text(text):
    """ollama로 텍스트 임베딩"""
    response = ollama.embed(model=EMBEDDING_MODEL, input=text)
    return response['embeddings'][0]


def index_vault(full_rebuild=False):
    """볼트 인덱싱 메인 함수"""
    # 2026-05-04: 환경변수로 vault 경로·collection 이름 override 가능 (위성볼트 인덱싱용)
    import os as _os
    global VAULT_PATH, COLLECTION_NAME
    VAULT_PATH = _os.environ.get("VAULT_RAG_VAULT_PATH", VAULT_PATH)
    COLLECTION_NAME = _os.environ.get("VAULT_RAG_COLLECTION", COLLECTION_NAME)
    print(f"📂 볼트 경로: {VAULT_PATH}")
    print(f"💾 DB 경로: {CHROMA_DB_PATH}")
    print(f"📊 Collection: {COLLECTION_NAME}")

    # ChromaDB 클라이언트
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    if full_rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
            print("🗑️  기존 컬렉션 삭제 (전체 재구축)")
        except (ValueError, Exception):
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    # 이전 메타데이터 로드
    prev_meta = {} if full_rebuild else load_metadata()
    new_meta = {}

    # 마크다운 파일 수집
    md_files = get_markdown_files(VAULT_PATH)
    print(f"📄 발견된 파일: {len(md_files)}개")

    indexed = 0
    skipped = 0
    errors = 0

    for i, filepath in enumerate(md_files):
        rel_path = os.path.relpath(filepath, VAULT_PATH)
        file_hash = get_file_hash(filepath)

        # 증분 인덱싱: 해시가 같으면 스킵
        if rel_path in prev_meta and prev_meta[rel_path] == file_hash:
            new_meta[rel_path] = file_hash
            skipped += 1
            continue

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if not content.strip():
                skipped += 1
                continue

            # 프론트매터 파싱
            frontmatter, body = parse_frontmatter(content)

            # 이전 청크 삭제
            existing = collection.get(where={"source_file": rel_path})
            if existing and existing['ids']:
                collection.delete(ids=existing['ids'])

            # 청킹
            chunks = chunk_text(body)
            if not chunks:
                skipped += 1
                continue

            # 임베딩 & 저장
            for j, chunk in enumerate(chunks):
                chunk_id = f"{rel_path}::chunk_{j}"
                embedding = embed_text(chunk)

                metadata = {
                    "source_file": rel_path,
                    "chunk_index": j,
                    "total_chunks": len(chunks),
                    **{k: v for k, v in frontmatter.items() if v}
                }

                collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[metadata]
                )

            new_meta[rel_path] = file_hash
            indexed += 1

            if (i + 1) % 50 == 0:
                print(f"  진행: {i+1}/{len(md_files)} ({indexed} 인덱싱, {skipped} 스킵)")

        except Exception as e:
            print(f"  ❌ 오류 [{rel_path}]: {e}")
            errors += 1

    # 삭제된 파일 처리
    deleted_files = set(prev_meta.keys()) - set(new_meta.keys())
    for del_file in deleted_files:
        existing = collection.get(where={"source_file": del_file})
        if existing and existing['ids']:
            collection.delete(ids=existing['ids'])
            print(f"  🗑️  삭제된 파일 제거: {del_file}")

    save_metadata(new_meta)

    print(f"\n✅ 인덱싱 완료!")
    print(f"  📊 신규/업데이트: {indexed}개")
    print(f"  ⏭️  스킵 (변경 없음): {skipped}개")
    print(f"  ❌ 오류: {errors}개")
    print(f"  🗑️  삭제: {len(deleted_files)}개")
    print(f"  📦 총 문서 수: {collection.count()}개 청크")


if __name__ == "__main__":
    full = "--full" in sys.argv
    if full:
        print("🔄 전체 재구축 모드")
    index_vault(full_rebuild=full)
