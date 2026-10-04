#!/usr/bin/env python3
"""lesson_verify — 발행 전 차시 검증 (메인 책상이 돌린다 · 2026-10-04 천대현 «세 레인이 검증·검토하며 진행»).

한 차시의 학생용 개념편 HTML 하나를 받아, 지금까지 사고로 정해진 기계 점검을 한 번에 돌린다.
판정은 🔴(규칙 위반·고쳐야 함)과 ⚠️(사람이 볼 것)로 나눈다. 대조표인 lesson_lint 결과는 그대로 붙인다.

  🔴 R3 «교과서 원문»이 학생 화면에 남음(빈칸 든 줄 제외)        — 코어 룰 11
  🔴 키워드 카드가 있는데 채점 전 잠금이 없음                      — 게이트 -1.02
  🔴 정답편 HTML이 git에 추적됨                                    — 게이트 -1.01
  🔴 data-id 중복                                                  — 채점·저장 밀림
  🔴 폰 390px에서 가로 밀림                                         — 게이트 -0.93
  🔴 허브 주소(정답편 카드로 가는 문)가 학생 파일에 있음            — 게이트 -1.0
  ⚠️ 빈칸 답이 그 빈칸보다 앞의 «보이는» 글에 그대로 있음(카드·접기 밖) — 누출 후보
  ⚠️ 정답편이 교사 iCloud 사본에 아직 없음                          — 30초 자동 동기화 대기일 수 있음
  ⚠️ 교과서 슬롯 답의 낱말이 슬롯 뒤 학생 글(입담·카드·OX)에 처음 나옴 — --md 때만 · 판정은 사람

사용: python3 ~/vault-rag/lesson_verify.py worksheets/<id>_개념편.html [--md <개념편.md>]
"""
import html, os, re, subprocess, sys

VR = os.path.expanduser("~/vault-rag")
ICLOUD = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/2026 동성여중/정답편 (교사용)")
args = sys.argv[1:]
if not args:
    print(__doc__); sys.exit(1)
md = None
if "--md" in args:
    i = args.index("--md"); md = args[i + 1]; del args[i:i + 2]
path = args[0] if os.path.isabs(args[0]) else os.path.join(VR, args[0])
s = open(path, encoding="utf-8").read()
body = s.split("<body", 1)[-1]
red, warn, ok = [], [], []

# R3
r3 = [m.group(1) for m in re.finditer(r"<blockquote[^>]*>(.*?)</blockquote>", body, re.S)
      if re.sub(r"<[^>]+>", "", m.group(1)).strip().startswith("(교과서 원문")]
r3_bad = [b for b in r3 if "blank-input" not in b]
(red if r3_bad else ok).append(f"R3 인용 학생 화면 {len(r3_bad)}건" + (f" (빈칸 든 것 {len(r3)-len(r3_bad)}건 별도)" if len(r3) > len(r3_bad) else ""))

# 카드 잠금
has_card = 'class="hero-card"' in body
has_check = 'onclick="check()">채점하기' in body
if has_card and has_check:
    (ok if "window.HERO_LOCK = true" in s else red).append("키워드 카드 채점 전 잠금")

# data-id
ids = re.findall(r'data-id="([^"]+)"', body)
dup = sorted({i for i in ids if ids.count(i) > 1})
(red if dup else ok).append(f"data-id {len(ids)}개 · 중복 {dup or 0}")

# 깨진 그림 — 상대 경로가 실제 파일로 이어지나(10/4 사회 8-1: «images/images/» 이중 경로를 폰 화면에서야 찾았다)
base = os.path.dirname(path)
srcs = re.findall(r'<img[^>]*\bsrc="([^"]+)"', body) + re.findall(r'data-src="([^"]+)"', body)
broken = sorted({x for x in srcs if not re.match(r"(https?:|data:|//)", x)
                 and not os.path.exists(os.path.join(base, html.unescape(x).split("?")[0].split("#")[0]))})
(red if broken else ok).append(f"그림 경로 {len(srcs)}개 · 깨짐 {len(broken)}" + (f" {broken[:3]}" if broken else ""))

# 허브 주소
(red if 'github.io/worksheets/"' in s and "복습용" not in path else ok).append("허브 주소 없음" if 'github.io/worksheets/"' not in s else "허브 주소 있음")

# 정답편 추적·사본
ak = os.path.basename(path).replace(".html", "_정답.html")
tracked = subprocess.run(["git", "-C", VR, "ls-files", "--error-unmatch", f"worksheets/{ak}"], capture_output=True).returncode == 0
(red if tracked else ok).append(f"정답편 git 추적 {'됨' if tracked else '안 됨'}")
if os.path.exists(os.path.join(VR, "worksheets", ak)):
    (ok if os.path.exists(os.path.join(ICLOUD, ak)) else warn).append(f"교사 iCloud 사본 {'있음' if os.path.exists(os.path.join(ICLOUD, ak)) else '아직 없음'}")

# 누출 후보 — 카드·접기·스크립트 밖의 보이는 글에서, 빈칸보다 앞에 답이 그대로
vis = re.sub(r'<div class="hero-card".*?</div></div>', "", body, flags=re.S)
vis = re.sub(r"<details.*?</details>|<script.*?</script>|<style.*?</style>", "", vis, flags=re.S)
leaks = []
for m in re.finditer(r'<input[^>]*data-answer="([^"]+)"[^>]*data-id="(\d+)"', vis):
    a = html.unescape(m.group(1)).strip()
    if len(a) < 2:
        continue
    before = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r'data-answer="[^"]*"', "", vis[:m.start()])))
    if a in before:
        k = before.rfind(a)
        leaks.append(f"빈칸 {m.group(2)}={a} ← «…{before[max(0,k-18):k+len(a)].strip()}»")
(warn if leaks else ok).append(f"누출 후보 {len(leaks)}건")

# 폰 390
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 390, "height": 800})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:80]))
        pg.goto("file://" + path); pg.wait_for_timeout(300)
        sw = pg.evaluate("document.documentElement.scrollWidth")
        b.close()
    (red if sw > 392 else ok).append(f"폰 390 문서폭 {sw}px")
    (red if errs else ok).append(f"JS 오류 {len(errs)}건" + (f" {errs[:1]}" if errs else ""))
except Exception as e:
    warn.append(f"폰 폭 측정 못 함({str(e)[:40]})")

# 카드 블록 머리말 숫자 ↔ 실제 카드 수 (10/4 사회 요청 — 하루에 세 번 어긋남: 9-1 «여섯 장면»인데 다섯 장)
if md and os.path.exists(md):
    NUM = {"한": 1, "하나": 1, "두": 2, "둘": 2, "세": 3, "셋": 3, "네": 4, "넷": 4, "다섯": 5, "여섯": 6,
           "일곱": 7, "여덟": 8, "아홉": 9, "열": 10}
    lines = open(md, encoding="utf-8").read().split("\n")
    mism, nblk = [], 0
    for i, l in enumerate(lines):
        mm = re.match(r"^:::(인물선택카드|카드선택|인물선택)\b(.*)$", l.strip())
        if not mm:
            continue
        nblk += 1
        head = mm.group(2)
        rows = 0
        for l2 in lines[i + 1:]:
            if l2.strip() == ":::":
                break
            if l2.count("|") >= 4:
                rows += 1
        hm = re.search(r"(?<![가-힣0-9])(\d+|한|하나|두|둘|세|셋|네|넷|다섯|여섯|일곱|여덟|아홉|열)\s*(장면|사람|명|카드|장|가지|곳)", head)  # 앞이 한글이면 숫자 아님(«맞이한 곳» 오탐·10/4 사회)
        if hm:
            n = int(hm.group(1)) if hm.group(1).isdigit() else NUM[hm.group(1)]
            if n != rows:
                mism.append(f"{i+1}행 «{hm.group(0)}» ↔ 카드 {rows}장")
    if nblk:
        (red if mism else ok).append(f"카드 블록 {nblk}개 · 머리말 숫자 어긋남 {len(mism)}" + (f" {mism}" if mism else ""))

# 슬롯 답 ↔ 그 뒤 학생 글 (10/4 사회 제안 — «슬롯 답을 바로 아래 입담이 말한다»가 체크리스트에 올린 뒤에도 여섯 번 나왔다)
# 교과서 슬롯의 정답편 «답»에 든 낱말이, 같은 단계의 슬롯 뒤 학생 글(입담·카드)과 OX에 그대로 있으면 나란히 보여 준다. 판정은 사람.
pairs = []
ak_md = md.replace(" 개념편.md", " 개념편 정답.md") if md else None
if ak_md and os.path.exists(ak_md):
    JOSA = ("으로써", "으로서", "에서는", "이라는", "에게", "에서", "으로", "이다", "하는", "하고", "라는", "이며", "까지",
            "부터", "보다", "처럼", "은", "는", "이", "가", "을", "를", "의", "에", "도", "와", "과", "로", "만", "고", "다")
    STOP = {"교사용", "예시", "답안", "교과서", "사회", "톡톡톡", "생각", "열기", "까닭", "위해서", "위해", "때문", "있다", "한다", "된다", "모두", "여러", "나라", "우리나라", "우리", "실제", "경제", "어려움"}
    def words(t):
        out = set()
        for w in re.findall(r"[가-힣]{2,}", t):
            for j in JOSA:
                if w.endswith(j) and len(w) - len(j) >= 2:
                    w = w[:-len(j)]; break
            # 동사·형용사 활용형(않는·많은·좋아·받지…)은 답의 핵심이 아니라 빼고, 이름·개념어만 남긴다
            if w not in STOP and not re.search(r"(는|은|고|지|게|라|아|어|해|었|았|었|기|할|된|하|져|올|낸다|없다)$", w):
                out.add(w)
        return out
    akl = open(ak_md, encoding="utf-8").read().split("\n")
    stu = open(md, encoding="utf-8").read()
    ox = stu.split("## ❓", 1)[1].split("\n## ", 1)[0] if "## ❓" in stu else ""
    for i, l in enumerate(akl):
        mm = re.match(r"^:::교과서\s*(.*)$", l.strip())
        if not mm:
            continue
        ans = next((x for x in akl[i + 1:i + 15] if x.startswith("> **답")), None)
        if not ans:
            continue
        ans = re.sub(r"—\s*(교사용|교과서).*$", "", ans)
        sl = stu.find(l.strip())
        if sl < 0:
            continue
        rest = stu[sl + len(l.strip()):]
        rest = rest[rest.find("\n:::\n") + 5 if "\n:::\n" in rest else 0:]
        step = rest.split("\n## ", 1)[0] + "\n" + ox
        before = stu[:sl]  # 슬롯 앞에서 이미 나온 낱말은 주제어라 빼고, 슬롯 뒤에 처음 나오는 답 낱말만 본다
        hit = sorted(w for w in words(ans) if w in step and w not in before)
        if hit:
            pairs.append(f"«{mm.group(1)[:30]}» 답 낱말이 뒤에 보임: {', '.join(hit[:8])}")
    if pairs:
        warn.append(f"슬롯 답 ↔ 뒤 학생 글 겹침 {len(pairs)}곳 (사람이 판정)")

print(f"■ {os.path.basename(path)}")
for x in red: print("  🔴", x)
for x in warn: print("  ⚠️", x)
for x in ok: print("  ✓", x)
for l in leaks[:8]: print("     ·", l)
for l in pairs: print("     ·", l)
if md:
    print("■ lesson_lint (대조표)")
    r = subprocess.run([sys.executable, os.path.expanduser("~/scripts/curriculum-designer/lesson_lint.py"), md], capture_output=True, text=True)
    print("  " + (r.stdout or r.stderr).strip().replace("\n", "\n  ")[:1500])
sys.exit(1 if red else 0)
