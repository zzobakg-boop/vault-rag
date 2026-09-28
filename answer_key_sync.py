#!/usr/bin/env python3
"""정답편을 공개 repo 밖, 천대현만 여는 iCloud 폴더로 옮겨 둔다 (2026-09-28 천대현 지시).

왜: 공개 GitHub Pages에 정답편 50편이 올라가 있었고 44편에 교과서 원문 인용이 있었다.
저작권법 제25조⑫·시행령 제9조의 접근제한·복제방지를 못 갖춘다. 정답편은 교사 혼자 쓰는 물건이다.

하는 일: ~/vault-rag/worksheets 와 ~/worksheets 의 *정답*.html 을 iCloud
«2026 동성여중/정답편 (교사용)/» 로 복사하고, 그 파일이 쓰는 images/ 만 따라 복사하고,
목록 index.html 을 새로 만든다. 원본은 건드리지 않는다. 발행 뒤마다 다시 돌리면 된다.

사용: python3 ~/vault-rag/answer_key_sync.py            (바뀐 것만 복사)
      python3 ~/vault-rag/answer_key_sync.py --dry-run  (무엇을 옮길지만)
      python3 ~/vault-rag/answer_key_sync.py --force    (원본이 안 바뀌었어도 대조)
"""
import fcntl, filecmp, html, os, re, shutil, sys, unicodedata

N = lambda s: unicodedata.normalize("NFC", s)
SRCS = [os.path.expanduser("~/vault-rag/worksheets"), os.path.expanduser("~/worksheets")]
DST = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/2026 동성여중/정답편 (교사용)")
DRY = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv
CACHE = os.path.expanduser("~/.cache/answer-key-sync")
os.makedirs(CACHE, exist_ok=True)

# 🔴 동시 실행 금지 — 9/28 메인·역사·사회가 몇 분 사이로 돌려 iCloud 충돌 사본 23개(«… 2.html»)가 생겼다.
_lock = open(os.path.join(CACHE, "lock"), "w")
try:
    fcntl.flock(_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print("다른 동기화가 도는 중 — 건너뜀")
    sys.exit(0)


def put(src, dst):
    """내용이 같으면 쓰지 않는다 — iCloud는 같은 파일을 다시 써도 충돌 사본을 만든다."""
    if os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False):
        return False
    tmp = dst + ".tmp-sync"
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)
    return True


def subject(name):
    if re.match(r"\d+-\d+-\d+|E0|S0", name):
        return "역사①"
    if "차시" in name or re.match(r"\d+-\d+차시", name):
        return "사회②"
    return "기타"


def title_of(text, fallback):
    m = re.search(r"<title>(.*?)</title>", text, re.S)
    return html.unescape(m.group(1)).strip() if m else fallback


files, imgs, seen = [], set(), set()
for src in SRCS:  # 🔴 앞의 것이 정본 — 같은 이름이면 뒤(~/worksheets 옛 사본)는 건너뛴다.
    for f in sorted(os.listdir(src)):  # 9/28 첫 실행에서 9/2 사본이 9/23 판을 덮어썼다.
        if "정답" in N(f) and f.endswith(".html") and N(f) not in seen:
            seen.add(N(f))
            p = os.path.join(src, f)
            t = open(p, encoding="utf-8").read()
            files.append((p, N(f), title_of(t, N(f))))
            for m in re.findall(r'src="(images/[^"]+)"', t):
                q = os.path.join(src, m)
                if os.path.exists(q):
                    imgs.add((q, m))

print(f"정답편 {len(files)}편 · 이미지 {len(imgs)}개 → {DST}")
if DRY:
    sys.exit(0)

# 원본이 지난번과 같으면 바로 끝낸다 — 30초 주기 자동 실행이 매번 iCloud를 건드리지 않게.
sig = "\n".join(f"{n}|{os.path.getmtime(p)}|{os.path.getsize(p)}" for p, n, _ in files)
sig_path = os.path.join(CACHE, "sig")
if not FORCE and os.path.exists(sig_path) and open(sig_path).read() == sig:
    print("변화 없음")
    sys.exit(0)

os.makedirs(DST, exist_ok=True)
changed = sum(put(p, os.path.join(DST, name)) for p, name, _ in files)
for q, rel in imgs:
    out = os.path.join(DST, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    changed += put(q, out)

groups = {}
for _, name, title in files:
    groups.setdefault(subject(name), []).append((name, title))
parts = []
for g in ("역사①", "사회②", "기타"):
    if g not in groups:
        continue
    items = "".join(f'<li><a href="{html.escape(n)}">{html.escape(t)}</a></li>' for n, t in sorted(groups[g]))
    parts.append(f"<h2>{g} <small>{len(groups[g])}편</small></h2><ul>{items}</ul>")
page = f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>정답편 (교사용)</title>
<style>body{{font:16px/1.6 -apple-system,"Malgun Gothic",sans-serif;max-width:760px;margin:0 auto;padding:24px 16px;background:#fbfbf8;color:#222}}
h1{{font-size:1.4em}}h2{{margin-top:1.6em;border-bottom:1px solid #ddd}}small{{color:#888;font-weight:normal}}
li{{margin:.25em 0}}a{{color:#1d4f91;text-decoration:none}}a:hover{{text-decoration:underline}}p{{color:#666}}</style>
<h1>정답편 (교사용)</h1>
<p>공개 사이트에서 내린 정답편 사본입니다. 이 폴더는 iCloud로만 동기화되며 링크를 학생에게 주지 않습니다. 발행 뒤 동기화 스크립트를 다시 돌리면 갱신됩니다.</p>
{''.join(parts)}"""
idx = os.path.join(DST, "index.html")
if not os.path.exists(idx) or open(idx, encoding="utf-8").read() != page:
    open(idx + ".tmp-sync", "w", encoding="utf-8").write(page)
    os.replace(idx + ".tmp-sync", idx)
    changed += 1
open(sig_path, "w").write(sig)
print(f"완료 — 바뀐 파일 {changed}개")
