# vault-rag

Obsidian Geo-Teacher 볼트용 로컬 RAG 시맨틱 검색 시스템.

## 구성
- **임베딩 모델**: BGE-M3 (ollama, 한국어 최적화)
- **벡터DB**: ChromaDB (로컬 영구 저장)
- **대상**: Obsidian Geo-Teacher 볼트 (~930개 파일)

## 사용법

```bash
# 인덱싱
./vault-index          # 증분 (변경분만)
./vault-index --full   # 전체 재구축

# 검색
./vault-search "민주주의와 시민 참여"
./vault-search "조선시대 신분제도" -k 10
./vault-search "수업 활동지" -j  # JSON 출력

# 헬스체크
./vault-health
```

## 요구사항
- Python 3.9+
- ollama (bge-m3 모델)
- chromadb (`pip3 install chromadb ollama`)
