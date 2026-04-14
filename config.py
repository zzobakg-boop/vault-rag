"""vault-rag 설정"""

import os

# Obsidian 볼트 경로
VAULT_PATH = os.path.expanduser(
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Geo-Teacher"
)

# ChromaDB 저장 경로 (영구 저장)
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")

# ollama 임베딩 모델
EMBEDDING_MODEL = "bge-m3"

# 청킹 설정
CHUNK_SIZE = 800  # 문자 수
CHUNK_OVERLAP = 100  # 오버랩 문자 수

# 검색 설정
DEFAULT_TOP_K = 5

# ChromaDB 컬렉션 이름
COLLECTION_NAME = "geo_teacher_vault"
