#!/usr/bin/env python3
"""
vault-lint — 볼트 건강 검진 (LLM Wiki의 Lint 워크플로우)

검사 항목:
  1. 고아 노트 — 백링크·포워드링크 모두 없는 파일
  2. 깨진 위키링크 — [[존재하지 않는 페이지]]
  3. 프론트매터 누락 — type / author / date created 필수 필드
  4. 유사 제목 — 레벤슈타인 거리 기반 중복 후보

결과: 40. Docs/Lint_Report_YYYY-MM-DD.md
"""

import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from config import VAULT_PATH

# 제외 디렉토리 (플러그인, 설정, 캐시 등)
EXCLUDE_DIRS = {
    ".obsidian",
    ".smart-env",
    ".trash",
    ".claude",
    "node_modules",
    ".git",
    "90. Settings",  # 템플릿 등 자동 생성물
    "_레인 인박스",  # 인박스 메시지가 lint 후보를 인용 → 오탐 루프 (2026-08-10 fix)
}

# 제외 파일 패턴
EXCLUDE_FILES = {
    "CLAUDE.md",
    "README.md",
}

# 제외 파일 접두사 — 린트 리포트 자신을 스캔하면 인용된 깨진 링크를
# 매주 재생산하는 오탐 루프가 됨 (2026-07-09 fix)
EXCLUDE_FILE_PREFIXES = ("Lint_Report_", "Lint Report ")  # 구형식(공백) 리포트도 동일 오탐 루프 (2026-08-10)

# 코드 영역 제거 — 펜스드 코드블록·인라인 코드 안의 [[...]]는
# 위키링크가 아니라 코드 조각 (2026-07-09 fix)
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

# 프론트매터 필수 필드
REQUIRED_FRONTMATTER = ["type", "author", "date created"]

WIKILINK_RE = re.compile(r"\[\[([^\]|#^]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def iter_md_files(root: Path):
    """볼트 내 모든 .md 파일 반복자"""
    for dirpath, dirnames, filenames in os.walk(root):
        # 제외 디렉토리 필터
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if (fn.endswith(".md") and fn not in EXCLUDE_FILES
                    and not fn.startswith(EXCLUDE_FILE_PREFIXES)):
                yield Path(dirpath) / fn


def parse_frontmatter(content: str) -> dict:
    """간이 YAML 프론트매터 파서 (line 기반, 중첩 미지원)"""
    m = FRONTMATTER_RE.match(content)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split("\n"):
        if ":" in line and not line.startswith(" ") and not line.startswith("-"):
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm


def extract_wikilinks(content: str) -> set[str]:
    """본문에서 [[wikilinks]] 추출 (alias·heading·block 제외한 타겟만).
    코드블록·인라인 코드 안의 [[...]]는 링크가 아니므로 먼저 제거."""
    content = CODE_FENCE_RE.sub("", content)
    content = INLINE_CODE_RE.sub("", content)
    # 표 안 별칭 링크 [[타겟\|별칭]]의 이스케이프 백슬래시가 타겟에 붙는 오탐 제거
    return {m.group(1).strip().rstrip("\\").strip() for m in WIKILINK_RE.finditer(content)}


def name_stem(path: Path) -> str:
    """파일명에서 확장자·경로 제외한 기본 이름"""
    return path.stem


def similar(a: str, b: str, threshold: float = 0.85) -> bool:
    if abs(len(a) - len(b)) / max(len(a), len(b)) > 0.3:
        return False
    return SequenceMatcher(None, a, b).ratio() >= threshold


def main():
    root = Path(VAULT_PATH)
    print(f"🔍 볼트 Lint: {root}")

    # 전체 수집
    files = list(iter_md_files(root))
    print(f"📄 대상 파일: {len(files)}개")

    # 이름 → 경로 매핑 (같은 이름이 여러 개일 수 있음)
    name_to_paths = defaultdict(list)
    for p in files:
        name_to_paths[name_stem(p)].append(p)

    orphans = []
    broken_links = []  # (source_file, target_name)
    missing_fm = []  # (file, missing_fields)
    temporal_unlabeled = []  # 시점성 문서(계획·초안·기획) description 라벨 누락 (2026-08-10 규약)
    outgoing = defaultdict(set)  # stem -> set of target stems
    incoming = defaultdict(set)  # stem -> set of source stems

    for p in files:
        try:
            content = p.read_text(encoding="utf-8")
        except Exception as e:
            print(f"⚠️  읽기 실패 {p}: {e}")
            continue

        # 프론트매터 체크
        fm = parse_frontmatter(content)
        missing = [f for f in REQUIRED_FRONTMATTER if f not in fm]
        if missing:
            missing_fm.append((p, missing))

        # 시점성 라벨 체크 — 계획·초안·기획 문서는 description 선두 [라벨] 의무
        # (frontmatter-standard §시점성 규약 2026-08-10·stale-read 오보 사고 방어)
        rel_str = str(p.relative_to(root))
        if re.search(r"계획|기획|초안", rel_str):
            desc = (fm.get("description") or "").strip().strip('"')
            if desc and not desc.startswith("["):
                temporal_unlabeled.append(p)

        # 위키링크 수집
        targets = extract_wikilinks(content)
        src_stem = name_stem(p)
        for t in targets:
            outgoing[src_stem].add(t)
            incoming[t].add(src_stem)
            if t not in name_to_paths:
                broken_links.append((p, t))

    # 고아 노트: 자기 포워드링크 없고, 누구도 자신을 링크 안 함
    for p in files:
        stem = name_stem(p)
        if not outgoing.get(stem) and not incoming.get(stem):
            orphans.append(p)

    # 유사 제목
    similar_pairs = []
    stems = list(name_to_paths.keys())
    for i, a in enumerate(stems):
        for b in stems[i + 1:]:
            if similar(a, b):
                similar_pairs.append((a, b))

    # 액션 후보 — 깨진 링크 중 기존 노트와 근접(≥0.9)한 타이포 교정 후보를
    # 참조 수 순으로 top 10 (2026-07-09 소비 루프 도입)
    from difflib import get_close_matches
    broken_agg_pre = defaultdict(list)
    for src, tgt in broken_links:
        broken_agg_pre[tgt].append(src)
    fixable = []
    for tgt, srcs in broken_agg_pre.items():
        match = get_close_matches(tgt, stems, n=1, cutoff=0.9)
        if match:
            fixable.append((tgt, match[0], len(srcs)))
    fixable.sort(key=lambda x: -x[2])
    top_actions = fixable[:10]

    # 리포트 작성
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = root / "40. Docs" / f"Lint_Report_{today}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "---",
        "type: note",
        f"aliases:",
        f'  - "Lint Report {today}"',
        "author:",
        '  - "[[제이콥]]"',
        f"date created: {today}",
        f"date modified: {today}",
        "tags:",
        "  - lint",
        "  - report",
        "  - LLM-Wiki",
        "---",
        "",
        f"# 🔍 볼트 Lint 리포트 — {today}",
        "",
        f"- 스캔 파일: **{len(files)}개**",
        f"- 고아 노트: **{len(orphans)}개**",
        f"- 깨진 위키링크: **{len(broken_links)}개**",
        f"- 프론트매터 누락: **{len(missing_fm)}개**",
        f"- 유사 제목 페어: **{len(similar_pairs)}개**",
        "",
        "---",
        "",
        f"## 1. 고아 노트 ({len(orphans)}개)",
        "",
        "> 백링크·포워드링크 모두 없는 파일. 고립된 지식은 죽은 지식.",
        "",
    ]
    for p in sorted(orphans)[:100]:
        rel = p.relative_to(root)
        lines.append(f"- [[{p.stem}]] — `{rel}`")
    if len(orphans) > 100:
        lines.append(f"- ... (외 {len(orphans) - 100}개 생략)")

    lines += [
        "",
        "---",
        "",
        f"## 2. 깨진 위키링크 ({len(broken_links)}개)",
        "",
        "> `[[존재하지 않는 페이지]]`. 타이포 또는 삭제된 노트.",
        "",
    ]
    broken_agg = defaultdict(list)
    for src, tgt in broken_links:
        broken_agg[tgt].append(src)
    for tgt in sorted(broken_agg.keys())[:100]:
        srcs = broken_agg[tgt]
        lines.append(f"- `[[{tgt}]]` — 참조한 곳 {len(srcs)}개")
        for s in srcs[:3]:
            lines.append(f"  - `{s.relative_to(root)}`")
        if len(srcs) > 3:
            lines.append(f"  - ... 외 {len(srcs) - 3}개")
    if len(broken_agg) > 100:
        lines.append(f"- ... (외 {len(broken_agg) - 100}개 생략)")

    lines += [
        "",
        "---",
        "",
        f"## 3. 프론트매터 누락 ({len(missing_fm)}개)",
        "",
        f"> 필수 필드: `{', '.join(REQUIRED_FRONTMATTER)}`",
        "",
    ]
    for p, missing in sorted(missing_fm)[:100]:
        rel = p.relative_to(root)
        lines.append(f"- `{rel}` — 누락: {', '.join(missing)}")
    if len(missing_fm) > 100:
        lines.append(f"- ... (외 {len(missing_fm) - 100}개 생략)")

    lines += [
        "",
        "---",
        "",
        f"## 4. 유사 제목 페어 ({len(similar_pairs)}개)",
        "",
        "> 레벤슈타인 유사도 ≥ 0.85. 중복·통합 검토 대상.",
        "",
    ]
    for a, b in similar_pairs[:100]:
        lines.append(f"- `{a}` ↔ `{b}`")
    if len(similar_pairs) > 100:
        lines.append(f"- ... (외 {len(similar_pairs) - 100}개 생략)")

    lines += [
        "",
        "---",
        "",
        f"## 5. 🎯 액션 후보 top {len(top_actions)} (타이포 교정 — 자동 선별)",
        "",
        "> 깨진 링크 중 기존 노트와 유사도 ≥ 0.9인 것. `[[깨진 타겟]]` → `[[제안]]`로 바꾸면 해소.",
        "",
    ]
    if top_actions:
        for tgt, suggestion, n_ref in top_actions:
            lines.append(f"- `[[{tgt}]]` → `[[{suggestion}]]` (참조 {n_ref}곳)")
    else:
        lines.append("✅ 자동 교정 후보 없음")

    lines += [
        "",
        f"## 6. ⏳ 시점성 라벨 누락 ({len(temporal_unlabeled)}개)",
        "",
        "> 계획·초안·기획 문서인데 description 선두 `[N월 계획]`류 라벨 없음 — stale-read 오보 위험. 규약: frontmatter-standard §시점성 (2026-08-10).",
        "",
    ]
    if temporal_unlabeled:
        for p in temporal_unlabeled[:30]:
            lines.append(f"- `{p.relative_to(root)}`")
        if len(temporal_unlabeled) > 30:
            lines.append(f"- …외 {len(temporal_unlabeled)-30}개")
    else:
        lines.append("✅ 누락 없음")

    lines += [
        "",
        "---",
        "",
        "## 제외 설정",
        f"- 디렉토리: {sorted(EXCLUDE_DIRS)}",
        f"- 파일: {sorted(EXCLUDE_FILES)}",
        "",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n✅ 리포트 저장: {report_path}")
    print(f"  📊 고아 {len(orphans)} | 깨진링크 {len(broken_links)} | "
          f"프론트매터누락 {len(missing_fm)} | 유사제목 {len(similar_pairs)} | "
          f"액션후보 {len(top_actions)}")

    # 소비 루프: 액션 후보가 있으면 시스템 레인 인박스에 1건 push (2026-07-09)
    if top_actions:
        import subprocess
        msg = (f"[주간 lint 소비] 타이포 교정 후보 {len(top_actions)}건 — "
               f"'40. Docs/Lint_Report_{today}.md' §5 확인 후 일괄 교정. "
               f"1순위: [[{top_actions[0][0]}]]→[[{top_actions[0][1]}]] (참조 {top_actions[0][2]}곳)")
        try:
            subprocess.run(
                ["python3", str(Path.home() / "scripts" / "lane_inbox.py"),
                 "send", "시스템", msg, "--from", "자동(lint)"],
                check=True, capture_output=True, timeout=30)
            print("  📥 시스템 레인 인박스 push 완료")
        except Exception as e:
            print(f"  ⚠️ 인박스 push 실패(리포트는 정상): {e}")


if __name__ == "__main__":
    main()
