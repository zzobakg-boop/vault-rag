#!/usr/bin/python3
# 🔴 2026-09-17 — env python3(PATH 의존)에서 /usr/bin/python3 고정으로.
#   chromadb가 /usr/bin/python3 에만 설치돼 있는데 morning_briefing.sh가
#   PATH 앞에 /opt/homebrew/bin 을 두어, 브리핑 안에서만 «chromadb 없음»이 떠
#   「되새김질 — vault 연결」이 매일 qmd 대체검색으로 열등하게 돌았다.
#   인덱스는 멀쩡했다(17,658청크·rc=0). 도구가 아니라 호출자 PATH 문제.
"""위성볼트 (Geo-Teacher-Wiki) 검색 — qmd 셤 (2026-06-27 전환).

⚠️ 2026-06-27: chromadb geo_teacher_wiki 컬렉션이 brew 업그레이드(chromadb 1.5.7)로
HNSW segfault → 복구 불가(재임베딩 수시간·가치낮음). **위성볼트 검색 주력은 qmd**라
(geo-teacher-wiki 컬렉션·정상) search_wiki.py를 *qmd 위임 셤*으로 전환한다.
호출처(curriculum_brief.sh·grok-vault-inject.py·grok-hybrid-search.py)는 stdout만
소비하므로 CLI(`search_wiki.py <query> [top_k]`)·출력 형태 유지 → 무수정 호환.

이전 chromadb 경로는 `search.py`(메인볼트)만 사용. 상세: memory/reference_vault_rag (6/27).
"""
import os
import subprocess
import sys

COLLECTION = "geo-teacher-wiki"  # qmd 컬렉션명(하이픈)


def search_wiki(query, top_k=5):
    # qmd는 NODE_OPTIONS 설정 시 MODULE_NOT_FOUND → 비우고 실행(메모리 reference_qmd)
    env = dict(os.environ)
    env.pop("NODE_OPTIONS", None)
    try:
        out = subprocess.run(
            ["qmd", "vsearch", query, "-c", COLLECTION, "-n", str(top_k)],
            capture_output=True, text=True, env=env, timeout=90,
        )
        if out.stdout.strip():
            print(out.stdout.rstrip())
        if out.returncode != 0 and out.stderr.strip():
            print(f"(qmd stderr) {out.stderr.strip()[:200]}", file=sys.stderr)
    except FileNotFoundError:
        print("⚠️ qmd 미설치 — 위성볼트 검색 불가(search_wiki는 qmd 위임)", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("⚠️ qmd 검색 타임아웃", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 search_wiki.py <query> [top_k]")
        sys.exit(1)
    q = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    search_wiki(q, top_k=k)
