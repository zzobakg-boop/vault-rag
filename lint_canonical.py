#!/usr/bin/env python3
"""노트 프로퍼티 lint + fix — canonical 중복·role 오분류·필수필드 누락 자동 교정.

기본 동작: dry-run (진단만 출력, 파일 수정 없음).
`--apply` 옵션: 실제 수정.

사용:
    python3 lint_canonical.py                    # 전체 진단
    python3 lint_canonical.py E05                # lesson_id=E05 진단
    python3 lint_canonical.py E05 --fix          # E05 수정 시안 dry-run
    python3 lint_canonical.py E05 --fix --apply  # 실제 수정
    python3 lint_canonical.py --folder 역사①    # 폴더 필터
"""

from __future__ import annotations

import argparse
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

VAULT = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/Geo-Teacher/600_Specialties"

STANDARD_ROLES = {
    "concept-sheet", "answer-key", "materials-pack", "teacher-guide",
    "student-handout", "quiz", "assessment",
}
VALID_STATUS = {"active", "draft", "archived", "deprecated"}
REQUIRED_FIELDS = ["lesson_id", "note_role", "canonical", "status", "updated"]

ROLE_MAPPING = {
    "gamma-export": "student-handout",
    "thinkerbell-quiz": "quiz",
}
STATUS_MAPPING = {
    "inProgress": "draft",
    "in-progress": "draft",
    # ready/completed는 판단 유보 — 수동
}


def parse_frontmatter(path: Path) -> tuple[dict, str, str, str] | None:
    """프론트매터 key-value 딕셔너리 + 원본 블록 + 본문 반환. 리스트 값은 원문자열로."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm_block = text[3:end]
    body = text[end + 4:]
    data = {}
    for line in fm_block.splitlines():
        m = re.match(r"^([A-Za-z_가-힣][\w가-힣]*):\s*(.*)$", line.rstrip())
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        if val.lower() in ("true", "false"):
            val = val.lower() == "true"
        data[key] = val
    return data, fm_block, body, text


def write_frontmatter(path: Path, fm_block: str, body: str) -> None:
    """수정된 프론트매터 블록으로 재기록."""
    new_text = f"---{fm_block}\n---{body}"
    path.write_text(new_text, encoding="utf-8")


def set_fm_field(fm_block: str, key: str, value) -> str:
    """프론트매터 블록 내 key 값 치환 또는 추가. 리스트·복잡 값 보존."""
    if isinstance(value, bool):
        value_str = "true" if value else "false"
    else:
        value_str = str(value)
    pattern = re.compile(rf"^({re.escape(key)}:)\s*.*$", re.MULTILINE)
    if pattern.search(fm_block):
        return pattern.sub(rf"\1 {value_str}", fm_block)
    # 새 키 추가: 블록 끝에
    sep = "\n" if fm_block.endswith("\n") else "\n"
    return fm_block + f"{sep}{key}: {value_str}"


def mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%dT%H:%M")


def scan(filter_lesson: str | None = None, filter_folder: str | None = None):
    notes = []  # (path, fm, fm_block, body, raw_text)
    for path in VAULT.rglob("*.md"):
        parsed = parse_frontmatter(path)
        if parsed is None:
            continue
        fm, fm_block, body, raw = parsed
        if filter_lesson and fm.get("lesson_id") != filter_lesson:
            continue
        if filter_folder and filter_folder not in str(path):
            continue
        notes.append((path, fm, fm_block, body, raw))
    return notes


def detect_issues(notes):
    findings = {
        "role_misclass_answer": [],
        "duplicate_canonical": [],
        "missing_required": [],
        "nonstandard_role": [],
        "invalid_status": [],
        "missing_updated": [],
    }
    canonical_groups = defaultdict(list)

    for path, fm, *_ in notes:
        name = path.name
        role = fm.get("note_role")
        lid = fm.get("lesson_id")

        # 정답 파일이 concept-sheet으로 오분류
        if "정답" in name and role == "concept-sheet":
            findings["role_misclass_answer"].append(path)

        # 비표준 role
        if role and role not in STANDARD_ROLES:
            findings["nonstandard_role"].append((path, role))

        # 비표준 status
        st = fm.get("status")
        if st and st not in VALID_STATUS:
            findings["invalid_status"].append((path, st))

        # 필수 누락
        missing = [k for k in REQUIRED_FIELDS if k not in fm]
        if missing:
            findings["missing_required"].append((path, missing))

        # updated 없음
        if "updated" not in fm:
            findings["missing_updated"].append(path)

        # canonical 그룹핑 (실제 role 보정 반영)
        effective_role = "answer-key" if "정답" in name and role == "concept-sheet" else (ROLE_MAPPING.get(role, role) if role else role)
        if fm.get("canonical") is True and lid and effective_role:
            canonical_groups[(lid, effective_role)].append(path)

    for key, paths in canonical_groups.items():
        if len(paths) > 1:
            findings["duplicate_canonical"].append((key, paths))

    return findings


def plan_fixes(notes, findings):
    """각 파일별로 적용할 수정안 목록 생성."""
    plan = defaultdict(list)  # path -> [(action, detail)]

    # 1. 정답 파일 role 수정
    for p in findings["role_misclass_answer"]:
        plan[p].append(("set_role", "answer-key"))

    # 2. canonical 중복 — mtime 최신만 유지
    for (lid, role), paths in findings["duplicate_canonical"]:
        paths_sorted = sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
        keep = paths_sorted[0]
        for p in paths_sorted[1:]:
            plan[p].append(("canonical_false", f"최신={keep.name}"))
            plan[p].append(("status_archived", None))

    # 3. 비표준 role 매핑
    for p, role in findings["nonstandard_role"]:
        if role in ROLE_MAPPING:
            plan[p].append(("set_role", ROLE_MAPPING[role]))

    # 4. 비표준 status 매핑
    for p, st in findings["invalid_status"]:
        if st in STATUS_MAPPING:
            plan[p].append(("set_status", STATUS_MAPPING[st]))

    # 5. updated 없으면 mtime으로 추가
    for p in findings["missing_updated"]:
        plan[p].append(("set_updated", mtime_iso(p)))

    return plan


def apply_plan(plan, notes_by_path, apply=False):
    """dry-run 또는 실제 적용."""
    changed = 0
    for path, actions in plan.items():
        if path not in notes_by_path:
            continue
        fm, fm_block, body, raw = notes_by_path[path]
        new_block = fm_block
        details = []
        for action, detail in actions:
            if action == "set_role":
                new_block = set_fm_field(new_block, "note_role", detail)
                details.append(f"note_role→{detail}")
            elif action == "canonical_false":
                new_block = set_fm_field(new_block, "canonical", False)
                details.append(f"canonical→false ({detail})")
            elif action == "status_archived":
                new_block = set_fm_field(new_block, "status", "archived")
                details.append("status→archived")
            elif action == "set_status":
                new_block = set_fm_field(new_block, "status", detail)
                details.append(f"status→{detail}")
            elif action == "set_updated":
                new_block = set_fm_field(new_block, "updated", detail)
                details.append(f"updated={detail}")

        print(f"  {'🔧' if apply else '📋'} {path.relative_to(VAULT)}")
        for d in details:
            print(f"      - {d}")

        if apply and new_block != fm_block:
            # 백업
            backup = path.with_suffix(path.suffix + f".bak-{datetime.now():%Y%m%d-%H%M%S}")
            shutil.copy2(path, backup)
            write_frontmatter(path, new_block, body)
            changed += 1

    print(f"\n{'적용' if apply else 'dry-run'} 완료. {'수정' if apply else '예정'} 파일: {len(plan)}건{' (실적용=' + str(changed) + ')' if apply else ''}")


def report(notes, findings):
    print(f"=== Lint 결과 (대상 {len(notes)}건) ===\n")
    if findings["role_misclass_answer"]:
        print(f"❌ 정답편이 concept-sheet로 오분류 ({len(findings['role_misclass_answer'])})")
        for p in findings["role_misclass_answer"][:10]:
            print(f"  - {p.relative_to(VAULT)}")
        print()
    if findings["duplicate_canonical"]:
        print(f"❌ canonical:true 중복 ({len(findings['duplicate_canonical'])}그룹)")
        for (lid, role), paths in findings["duplicate_canonical"]:
            print(f"  [{lid} / {role}]")
            for p in sorted(paths, key=lambda x: x.stat().st_mtime, reverse=True):
                ts = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                print(f"    - {p.name}  ({ts})")
        print()
    if findings["nonstandard_role"]:
        roles = defaultdict(int)
        for _, r in findings["nonstandard_role"]:
            roles[r] += 1
        print(f"⚠️  비표준 note_role ({len(findings['nonstandard_role'])}건)")
        for r, n in sorted(roles.items(), key=lambda x: -x[1]):
            mapped = ROLE_MAPPING.get(r, "수동 판단 필요")
            print(f"  {r}: {n}건 → {mapped}")
        print()
    if findings["invalid_status"]:
        print(f"⚠️  비표준 status ({len(findings['invalid_status'])}건)")
        sts = defaultdict(int)
        for _, s in findings["invalid_status"]:
            sts[s] += 1
        for s, n in sorted(sts.items(), key=lambda x: -x[1]):
            mapped = STATUS_MAPPING.get(s, "수동 판단 필요")
            print(f"  {s}: {n}건 → {mapped}")
        print()
    if findings["missing_required"]:
        print(f"⚠️  필수 필드 누락 ({len(findings['missing_required'])}건, 상위 10개)")
        for p, m in findings["missing_required"][:10]:
            print(f"  - {p.name}: {m}")
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lesson", nargs="?", help="lesson_id 필터")
    ap.add_argument("--folder", help="폴더 필터")
    ap.add_argument("--fix", action="store_true", help="수정 시안 출력")
    ap.add_argument("--apply", action="store_true", help="실제 수정 (--fix 필수)")
    args = ap.parse_args()

    notes = scan(filter_lesson=args.lesson, filter_folder=args.folder)
    findings = detect_issues(notes)
    report(notes, findings)

    if args.fix:
        print("=" * 50)
        print(f"🔧 수정 시안{'  (실적용)' if args.apply else '  (dry-run)'}")
        print("=" * 50)
        notes_by_path = {p: (fm, fmb, body, raw) for p, fm, fmb, body, raw in notes}
        plan = plan_fixes(notes, findings)
        apply_plan(plan, notes_by_path, apply=args.apply)


if __name__ == "__main__":
    main()
