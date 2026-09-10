#!/usr/bin/env python3
"""마크다운 개념편 → 인터랙티브 HTML 학습지 자동 생성기 v2
정답 파일에서 답을 순서대로 추출하고, 개념편의 빈칸에 순서대로 매칭한다."""

import re
import math
import sys
import os
import json


def _fold_table(rows, inline):
    """접기 블록 안에서 모은 '|…|' 줄들을 <table>로 만든다.
       첫 줄을 헤더로 보되, 구분선(|---|)이 있으면 그 앞까지를 헤더로 친다."""
    cells = []
    for r in rows:
        if set(r.replace('|', '').replace(' ', '')) <= set('-:'):
            continue                      # 구분선은 버린다
        cells.append([c.strip() for c in r.strip().strip('|').split('|')])
    if not cells:
        return ''
    head, body = cells[0], cells[1:]
    th = ''.join(f'<th>{inline(c)}</th>' for c in head)
    tr = ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in row) + '</tr>' for row in body)
    return f'<table class="ws-fold-table"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'


_anim_cache = {}
def _is_animated(src, out_path):
    """발행될 HTML 기준 상대경로로 실제 파일을 열어 애니메이션인지 확인한다.
       ⚠️ 확장자만으로는 정지 WebP와 구분되지 않는다."""
    if not src.lower().endswith(('.webp', '.gif')):
        return False
    key = (src, out_path)
    if key in _anim_cache:
        return _anim_cache[key]
    ok = False
    try:
        from PIL import Image as _Im
        p = os.path.join(os.path.dirname(os.path.abspath(out_path)), src)
        if os.path.exists(p):
            with _Im.open(p) as im:
                ok = getattr(im, 'n_frames', 1) > 1
    except Exception:
        ok = False
    _anim_cache[key] = ok
    return ok


def strip_obsidian_artifacts(text, teacher=False):
    # 2026-08-24: 키워드 카드 섹션은 hero에서만 렌더 → 본문에서는 항상 제거
    text = re.sub(r'^##\s*🔖\s*키워드 카드\s*$.*?(?=^##\s|\Z)', '', text, flags=re.S | re.M)
    """옵시디언 전용 wiki-embed·obsidian:// link 제거.
    teacher=False (학생/복습용) — 교사 전용 섹션도 제거 (defense-in-depth·학생 노출 방지).
    teacher=True  (정답편)      — 교사 전용 섹션을 *유지* (정답편=교사용이므로 해설·모범답안·교사 메타 전부 노출)."""
    text = re.sub(r'!\[\[[^\]]+\]\]', '', text)  # ![[image.png|450]] wiki-embed
    text = re.sub(r'\[[^\]]+\]\(obsidian://[^)]+\)[^\n]*', '', text)  # [확대 보기](obsidian://...)
    text = re.sub(r'📎\s*\n', '', text)  # 외로운 📎 줄
    if not teacher:
        # 교사 전용 섹션 제거 — 학생 개념편에 교사 메타·정답이 남아도 학생 HTML엔 안 나가도록 (defense-in-depth)
        # ⭐ 2026-05-29 일반화: '✅ 교사 기준' 정확 문구만 잡던 것 → 교사·채점·정답 매핑·학생 비공개·배부 금지
        #    마커를 *제목에 포함한 H2 섹션 전부* 제거. + 명시 마커 <!-- teacher-only --> 블록 지원.
        #    (2-2-3 v4 사고: 학생 개념편에 정답 14 박힌 '## ✅ 교사 기준 대조 (학생 비공개)' 섹션 → 통째 렌더 위험)
        text = re.sub(r'<!--\s*teacher-only\s*-->.*?<!--\s*/teacher-only\s*-->', '', text, flags=re.S | re.I)
        # ⭐ 2026-05-30 확장: '## ✅ 교재 기준 대조용 보강 (삭제 금지 포인트)'(2-2-2 누출·설계자 의도/핵심 대비축)도 포획.
        #    5/29 regex가 '교사'만 잡아 '교재'를 놓침 → 학생 발행본에 교사 메타 노출(실측 5건). '교재 기준·대조용·설계자 의도·삭제 금지' 추가.
        text = re.sub(
            r'^##\s+[^\n]*(?:교사|교재\s*기준|대조용|설계자\s*의도|채점\s*가이드|정답\s*매핑|빈칸\s*정답|학생\s*비공개|학생\s*배부\s*금지|삭제\s*금지)[^\n]*\n.*?(?=^##\s|\Z)',
            '', text, flags=re.S | re.M,
        )
    # 학생 자유 작성 칸 마커 → no-score input (정답 매칭 X·수합만)
    # ⭐ 5/27 fix: 활동 input마다 unique data-id (act-1, act-2, ...)
    # 이전엔 모두 data-id="0"이라 collectAnswers()에서 한 키로 덮어씌워져 *마지막 1개만 살아남는* 데이터 손실 버그
    act_counter = [0]
    def _activity_sub(m):
        act_counter[0] += 1
        # [학생작성] = 기본 240px / [학생작성:N] = 폭 N px (짧은 단답 칸용·6/18 추가·하위호환)
        w = m.group(1) if m.group(1) else '240'
        # 2026-06-24: 같은 줄 문맥을 data-label로 — 수합 시 답(JSON) __labels로 동승 → 정리시트가 act-N 대신 문항 텍스트 표시 (doPost 변경/재배포 불요)
        s = m.string
        ls = s.rfind('\n', 0, m.start()) + 1
        le = s.find('\n', m.start()); le = len(s) if le == -1 else le
        lbl = re.sub(r'\[학생작성(?::\d+)?\]', '', s[ls:le])
        lbl = re.sub(r'[*_`|>#]', '', lbl)
        lbl = re.sub(r'\(\s*[　\s]*\)', '', lbl)
        lbl = re.sub(r'\s+', ' ', lbl).strip(' -–—·:|"\'').strip()[:40]
        if not lbl:
            # 표 셀 등 같은 줄이 비면 가장 가까운 앞 heading을 라벨로
            for prev in reversed(s[:ls].split('\n')):
                hm = re.match(r'^\s{0,3}#{2,4}\s+(.*)', prev)
                if hm:
                    lbl = re.sub(r'[*_`#]', '', hm.group(1)).strip()[:40]
                    break
            if not lbl:
                lbl = f'활동{act_counter[0]}'
        lbl = lbl.replace('"', '“')
        return (f'<input type="text" class="blank-input activity-input no-score" '
                f'data-id="act-{act_counter[0]}" data-label="{lbl}" style="width:{w}px" placeholder="">')
    text = re.sub(r'\[학생작성(?::(\d+))?\]', _activity_sub, text)
    return text


def extract_answers(answer_file):
    """정답 파일에서 ( **답** ) 패턴의 답을 순서대로 추출"""
    with open(answer_file, 'r', encoding='utf-8') as f:
        text = f.read()

    answer_pattern = re.compile(r'\(\s*\*\*(.+?)\*\*\s*\)')
    answers = [m.group(1).strip() for m in answer_pattern.finditer(text)]
    return answers


def extract_ox_answers(answer_file):
    """정답 파일에서 OX 문항 정답 추출"""
    with open(answer_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    ox_answers = []
    for line in lines:
        # | 번호 | 문항 | **O** | 또는 | **X** (해설) |
        match = re.match(r'^\|\s*(\d+)\s*\|.*\|\s*\*\*([OX])\*\*', line)
        if match:
            ox_answers.append({'num': match.group(1), 'answer': match.group(2)})
    return ox_answers


def extract_table_answers(answer_file):
    """정답 파일에서 테이블 셀 안 **답** 패턴을 행/열 단위로 추출"""
    with open(answer_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    tables = []  # list of list of rows, each row is list of cells
    current_table = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|'):
            if re.match(r'^\|[\s\-:|]+\|$', stripped):
                continue  # separator
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            current_table.append(cells)
        else:
            if current_table:
                tables.append(current_table)
                current_table = []
    if current_table:
        tables.append(current_table)
    return tables


def build_html_from_blank(blank_file, answers, ox_answers, answer_file, teacher=False, out_path='worksheet.html'):
    """개념편 파일을 읽고, 빈칸을 input으로 교체하여 HTML 생성.
    teacher=True — blank_file로 *정답.md*를 넘긴다. 빈칸이 ( **답** )로 차 있어 input이 안 생기고
    교사 섹션도 보존되어 *완전한 교사 정답본* 본문이 된다 (정답.md 해설·모범답안 그대로 노출)."""
    with open(blank_file, 'r', encoding='utf-8') as f:
        raw = f.read()
    raw = strip_obsidian_artifacts(raw, teacher=teacher)  # 학생용은 교사섹션 strip·정답편은 유지
    if teacher:
        # 정답본: ①( **답** ) → 채워진 빈칸(초록 박스) 스팬 — 이전 정답본 reveal 느낌 그대로.
        # 학생 제출용과 같은 레이아웃에 답만 기입된 모습. 모범답안·OX해설·사료이미지는 정답.md 본문에서 그대로 노출.
        raw = re.sub(r'\(\s*\*\*([^*]+?)\*\*\s*\)', r'<span class="blank-filled">\1</span>', raw)
    lines = raw.splitlines(keepends=True)

    # 정답 파일의 테이블들도 읽기
    answer_tables = extract_table_answers(answer_file)

    blank_pattern = re.compile(r'\(\s*[　\s]+\)')
    answer_idx = 0
    ox_idx = 0
    total_blanks = 0
    total_ox = 0
    html_parts = []

    in_frontmatter = False
    fm_count = 0
    in_code = False
    in_table = False
    in_voc = False; voc_rows = []; voc_key = ''   # 2026-09-04: :::낱말 아코디언
    in_vcd = False; vcd_rows = []; vcd_head = ''  # 2026-09-07: :::낱말카드 (한자 카드·가로)
    in_fold = False   # 2026-08-31: 접힌 콜아웃 '> [!타입]- 제목' → <details>
    in_ox_table = False
    title = "학습지"
    table_idx = -1  # 현재 처리 중인 테이블 인덱스
    table_row_idx = 0  # 현재 테이블 내 행 인덱스
    blank_table_count = 0  # 빈칸 테이블 수
    in_step0 = False  # STEP 0 구간 (채점 제외)
    in_figrow = False  # 가로 비교 figure 행 (:::figrow ... :::)
    fold_tbl = []             # 접기 블록 안에 누적되는 표 줄 (2026-09-02)
    in_gallery = False        # 2026-08-31: 한 장씩 넘겨 보는 큐레이션 (:::gallery ... :::)
    gallery_items = []
    gallery_title = ''
    in_pick = False; pick_q = ''; pick_rows = []   # 2026-09-03: 인물 선택 활동
    in_read = False           # 2026-09-03: 표·도식을 '읽는' 자리 (:::해설 ... :::)
    read_lines = []           #   빈칸 본문(쓰는 곳)과 같은 모양이라 학생이 구분을 못 했다.
    in_cmp = False            # 2026-09-03: 좌우 비교 넘기기 (:::비교 A | B ... :::)
    in_seat = False           # 2026-09-07: 좌석 구성 눌러 보기 (:::좌석표 ... :::)
    in_tl = False; tl_head = ''; tl_rows = []; tl_spr = ('', '')   # 2026-09-09: 연표 시소 (:::연표시소 ... :::)
    in_pk = False             # 2026-09-07: 카드 골라 쓰기 (:::카드선택 ... :::)
    pk_title, pk_rows, pk_ask, pk_cred = '', [], '', ''
    seat_title, seat_rows, seat_note = '', [], ''
    seat_bg, seat_cap = '', ''
    cmp_left = cmp_right = ''
    cmp_slides = []           # [(제목, [(캡션,경로), (캡션,경로)]), ...]
    in_flip = False           # 2026-09-03: 뒤집는 카드 (:::플립 ... :::)
    flip_items = []
    in_tb = False             # 2026-09-02: 교과서를 펴는 자리 (:::교과서 <라벨> ... :::)
    tb_label = ''             #   학습지 안(파랑)과 교과서 밖(황토)을 색으로 갈라 놓는다.
    tb_lines = []
    figrow_items = []
    essay_count = 0  # 서술형 textarea 수 (제출 수합·세특용 data-id essay-N)
    last_heading = ''  # 가장 최근 heading (essay data-label용·2026-06-24)
    def _hlabel(t):
        return t.replace('*', '').replace('`', '').replace('#', '').replace('"', '').replace('_', '').strip()[:40]

    for line in lines:
        stripped = line.strip()

        # STEP 0 구간 감지 (채점 제외 영역)
        if re.match(r'^##\s+STEP\s*0', stripped):
            in_step0 = True
        elif in_step0 and re.match(r'^##\s+\d', stripped):
            in_step0 = False  # 다음 ## 섹션이 시작되면 STEP 0 종료

        # 프론트매터
        if stripped == '---':
            fm_count += 1
            if fm_count <= 2:
                in_frontmatter = not in_frontmatter
                continue
        if in_frontmatter:
            continue

        # 타이틀 추출
        if stripped.startswith('# ') and title == "학습지":
            title = stripped[2:]

        # 코드 블록
        if stripped.startswith('```'):
            in_code = not in_code
            if in_code:
                html_parts.append('<pre class="code-block">')
            else:
                html_parts.append('</pre>')
            continue
        if in_code:
            # 코드블록 안 빈칸도 학생이 입력할 수 있도록 input 생성 (한나라 학습지 패턴)
            blanks_in_code = list(blank_pattern.finditer(line))
            if blanks_in_code:
                new_line = line
                offset = 0
                for b in blanks_in_code:
                    if answer_idx < len(answers):
                        answer = answers[answer_idx]
                        width = max(60, len(answer) * 14)
                        answer_text = (
                            f'<input type="text" class="blank-input code-blank" '
                            f'data-answer="{answer}" data-id="{answer_idx+1}" '
                            f'style="width:{width}px" placeholder="">'
                        )
                        answer_idx += 1
                    else:
                        # 정답 없는 코드블록 빈칸도 입력만 가능 (채점 제외)
                        answer_text = (
                            f'<input type="text" class="blank-input code-blank no-score" '
                            f'data-id="0" style="width:80px" placeholder="">'
                        )
                    start = b.start() + offset
                    end = b.end() + offset
                    new_line = new_line[:start] + answer_text + new_line[end:]
                    offset += len(answer_text) - (b.end() - b.start())
                html_parts.append(new_line.rstrip() + '\n')
            else:
                html_parts.append(line.rstrip() + '\n')
            continue

        # 가로 비교 figure 행 (:::figrow ... :::) — 이미지 N장을 나란히 비교 (1단계 그리스→간다라→한국 등)
        # 2026-08-31: ':::gallery' — 한 장씩 넘겨 보는 큐레이션 블록.
        #   교과서 p.94 「세계사×미술」처럼 *여러 장을 차례로 비교*하는 자료용.
        #   figrow(나란히)와 달리 한 번에 한 장만 보여 준다 — 12달을 늘어놓으면 아무도 안 본다.
        # 📕 교과서를 펴는 자리 (:::교과서 <쪽·자료명> ... :::)  — 2026-09-02 천대현
        #   학습지 안에서 답이 나오는 파란 계열(빈칸·설명 blockquote)과 *색부터* 갈라 놓는다.
        #   학생이 화면을 훑을 때 "여기는 책을 펴야 하는 자리"가 한눈에 잡혀야 하기 때문이다.
        #   본문 규약 — '?' 로 시작하는 줄 = 쓰는 질문 / 나머지 = 무엇을 보는지 안내(쓰지 않는다).
        #   ⚠️ 안내 줄에 [학생작성]을 넣지 말 것. "굳이 적지 않아도 될 것은 묻지 않는다"가 이 블록의 규칙이다.
        # 🃏 카드 골라 쓰기 (:::카드선택 <안내> ... :::) — 2026-09-07 천대현
        #   "1단계를 관련 이미지를 넣어 카드 형식으로. 세 개 카드 중 하나를 골라
        #    그 이미지가 보여 주는 장면이 무엇인지 쓰도록. 포켓몬 카드 스타일로."
        #   교과서 삽화를 글로 지시하던 자리를 실제 그림 카드로 바꾼다.
        #   행 규약: | 타입 | 카드 이름 | 이미지파일 | 한 줄 설명 |
        #   '? …[학생작성:N]' = 답 쓰는 줄 · '= …' = 출처 표기(선택)
        if stripped.startswith(':::카드선택'):
            in_pk = True
            pk_title = stripped[len(':::카드선택'):].strip()
            pk_rows, pk_ask, pk_cred = [], '', ''
            continue
        if in_pk:
            if stripped == ':::':
                if pk_rows:
                    kid = 'pk3%d' % len(html_parts)
                    cards = []
                    for i, (ty, nm, img, fl) in enumerate(pk_rows):
                        cards.append(
                            '<button type="button" class="pk3-card pk3-t%d" data-i="%d" aria-pressed="false">'
                            '<span class="pk3-in">'
                            '<span class="pk3-top"><span class="pk3-name">%s</span>'
                            '<span class="pk3-badge">%s</span></span>'
                            '<span class="pk3-win"><img src="images/%s" alt="%s" loading="lazy">'
                            '<span class="pk3-holo"></span></span>'
                            '<span class="pk3-cap">%s</span>'
                            '<span class="pk3-flavor">%s</span>'
                            '<span class="pk3-foot">이 카드로 고르기</span>'
                            '</span></button>'
                            % (i % 3, i, inline(ty), inline(ty),
                               img, re.sub(r'<[^>]+>', '', inline(nm)), inline(nm), inline(fl)))
                    ask = ('<div class="pk3-ask"><div class="pk3-pick">아직 고르지 않았다</div>%s</div>'
                           % inline(pk_ask)) if pk_ask else ''
                    cred = ('<div class="pk3-cred">%s</div>' % inline(pk_cred)) if pk_cred else ''
                    names = json.dumps([r[0] for r in pk_rows], ensure_ascii=False)
                    html_parts.append(
                        '<div class="ws-pk3" id="%s">'
                        '<div class="pk3-head">%s</div>'
                        '<div class="pk3-deck">%s</div>%s%s</div>'
                        '<script>(function(){var w=document.getElementById("%s");'
                        'var NM=%s,cs=w.querySelectorAll(".pk3-card"),'
                        'pk=w.querySelector(".pk3-pick"),'
                        'inp=w.querySelector(".pk3-ask input,.pk3-ask textarea");'
                        'function tag(v,t){v=String(v||"").replace(/^\[[^\]]*\]\s*/,"");'
                        'return t?("["+t+"] "+v):v;}'
                        'cs.forEach(function(c){c.addEventListener("click",function(){'
                        'var off=c.classList.contains("on");'
                        'cs.forEach(function(x){x.classList.remove("on","dim");'
                        'x.setAttribute("aria-pressed","false");});'
                        'if(off){if(pk)pk.textContent="아직 고르지 않았다";'
                        'if(inp){inp.value=tag(inp.value,null);'
                        'inp.dispatchEvent(new Event("input",{bubbles:true}));}return;}'
                        'c.classList.add("on");c.setAttribute("aria-pressed","true");'
                        'cs.forEach(function(x){if(x!==c)x.classList.add("dim");});'
                        'var t=NM[+c.dataset.i];'
                        'if(pk)pk.textContent="고른 카드 — "+t;'
                        'if(inp){inp.value=tag(inp.value,t);'
                        'inp.dispatchEvent(new Event("input",{bubbles:true}));inp.focus();}'
                        '});});})();</script>'
                        % (kid, inline(pk_title), ''.join(cards), ask, cred, kid, names))
                in_pk = False
                pk_rows, pk_ask, pk_cred = [], '', ''
                continue
            if stripped.startswith('?'):
                pk_ask = stripped[1:].strip()
                continue
            if stripped.startswith('= '):
                pk_cred = stripped[2:].strip()
                continue
            if stripped.startswith('|'):
                c = [x.strip() for x in stripped.strip('|').split('|')]
                if len(c) >= 4:
                    pk_rows.append((c[0], c[1], c[2], c[3]))
                continue
            continue

        # 🪑 좌석 구성 눌러 보기 (:::좌석표 <제목> ... :::) — 2026-09-07 천대현
        #   "카드식으로 넘겨 보게. 5개 10개 클릭할 때 효과 좀 넣자."
        #   한 장의 큰 그림에 설명을 다 얹으면 호흡이 길어 학생이 안 읽는다.
        #   → 자리 그림만 먼저 보여 주고, 그룹을 누를 때 그 자리들만 살아나며 설명 카드가 뜬다.
        #   행 규약: | 그룹명 | 자리수 | red|blue | 항목(쉼표) | 한 줄 성격 |
        #   '+ ' 줄 = 두 그룹을 다 본 뒤 드러나는 결론.
        if stripped.startswith(':::좌석표'):
            in_seat = True
            seat_title = stripped[len(':::좌석표'):].strip()
            seat_rows, seat_note = [], ''
            seat_bg, seat_cap = '', ''
            continue
        if in_seat:
            if stripped == ':::':
                if seat_rows:
                    sid = 'seat%d' % len(html_parts)
                    tot = sum(r[1] for r in seat_rows)
                    CX, CY, R = 260, 208, 132
                    seats, gi, idx = [], 0, 0
                    for gi, (nm, cnt, col, items, desc) in enumerate(seat_rows):
                        for _ in range(cnt):
                            a = math.radians(-90 + idx * (360.0 / tot))
                            seats.append(
                                '<circle class="st-seat" data-g="%d" r="15" cx="%.1f" cy="%.1f"/>'
                                % (gi, CX + R * math.cos(a), CY + R * math.sin(a)))
                            idx += 1
                    btns = ''.join(
                        '<button type="button" class="st-btn st-%s" data-g="%d">%s <b>%d</b></button>'
                        % (r[2], i, inline(r[0]), r[1]) for i, r in enumerate(seat_rows))
                    cards = ''.join(
                        '<div class="st-card st-%s" data-g="%d" hidden>'
                        '<div class="st-card-h">%s <span>%d자리</span></div>'
                        '<div class="st-card-i">%s</div><div class="st-card-d">%s</div></div>'
                        % (r[2], i, inline(r[0]), r[1], inline(r[3]), inline(r[4]))
                        for i, r in enumerate(seat_rows))
                    note = ('<div class="st-note" hidden>%s</div>' % inline(seat_note)) if seat_note else ''
                    html_parts.append(
                        '<div class="ws-seat" id="%s" data-n="%d">'
                        '<div class="st-title">%s</div>'
                        '<div class="st-hint">아래 단추를 눌러 보자. 누른 쪽 자리만 살아난다.</div>'
                        '<div class="st-btns">%s</div>'
                        '<div class="st-stage%s"%s>%s'
                        '<svg class="st-svg" viewBox="0 0 520 366" role="img" aria-label="%s">'
                        '<circle class="st-hub" cx="%d" cy="%d" r="62"/>'
                        '<text class="st-hub-n" x="%d" y="%d" text-anchor="middle">%d</text>'
                        '<text class="st-hub-t" x="%d" y="%d" text-anchor="middle">자리</text>'
                        '%s</svg></div>%s'
                        '<div class="st-cards">%s</div>%s</div>'
                        '<script>(function(){var w=document.getElementById("%s");'
                        'var seen={},n=%d;'
                        'w.querySelectorAll(".st-btn").forEach(function(b){b.addEventListener("click",function(){'
                        'var g=b.dataset.g,off=b.classList.contains("on");'
                        'w.querySelectorAll(".st-btn").forEach(function(x){x.classList.remove("on")});'
                        'w.querySelectorAll(".st-card").forEach(function(x){x.hidden=true});'
                        'w.querySelectorAll(".st-seat").forEach(function(s){s.classList.remove("on","dim")});'
                        'if(off){return;}'
                        'b.classList.add("on");seen[g]=1;'
                        'w.querySelector(\'.st-card[data-g="\'+g+\'"]\').hidden=false;'
                        'w.querySelectorAll(".st-seat").forEach(function(s){'
                        's.classList.add(s.dataset.g===g?"on":"dim");});'
                        'var nt=w.querySelector(".st-note");'
                        'if(nt&&Object.keys(seen).length>=n){nt.hidden=false;}'
                        '});});})();</script>'
                        % (sid, len(seat_rows), inline(seat_title), btns,
                           ' has-bg' if seat_bg else '',
                           (' style="background-image:url(images/%s)"' % seat_bg) if seat_bg else '',
                           '<span class="st-veil"></span>' if seat_bg else '',
                           re.sub(r'<[^>]+>', '', inline(seat_title)),
                           CX, CY, CX, CY + 2, tot, CX, CY + 30, ''.join(seats),
                           ('<div class="st-cap">%s</div>' % inline(seat_cap)) if seat_cap else '',
                           cards, note, sid, len(seat_rows)))
                in_seat = False
                seat_rows, seat_note = [], ''
                continue
            if stripped.startswith('@ '):
                _b = [x.strip() for x in stripped[2:].split('|')]
                seat_bg = _b[0]
                seat_cap = _b[1] if len(_b) > 1 else ''
                continue
            if stripped.startswith('+ '):
                seat_note = stripped[2:].strip()
                continue
            if stripped.startswith('|'):
                c = [x.strip() for x in stripped.strip('|').split('|')]
                if len(c) >= 5 and c[1].isdigit():
                    seat_rows.append((c[0], int(c[1]),
                                      'red' if c[2] not in ('red', 'blue') else c[2], c[3], c[4]))
                continue
            continue

        # ⚖️ 좌우 비교 넘기기 (:::비교 왼쪽이름 | 오른쪽이름 ... :::) — 2026-09-03 천대현
        #   "양쪽에 카드 형식으로 해서 넘기도록" — figrow(나란히)를 여러 벌 쌓으면 세로로 길어져
        #   스크롤 없이 못 본다. 좌우 라벨은 **고정**하고 비교 항목만 넘긴다.
        #   본문 규약: '### 슬라이드 제목' 뒤에 이미지 2장(왼쪽·오른쪽 순).
        if stripped.startswith(':::비교'):
            in_cmp = True
            _hdr = stripped[len(':::비교'):].strip()
            _lr = [x.strip() for x in _hdr.split('|')]
            cmp_left  = _lr[0] if _lr else ''
            cmp_right = _lr[1] if len(_lr) > 1 else ''
            cmp_slides = []
            continue
        if in_cmp:
            if stripped == ':::':
                if cmp_slides:
                    cid = 'cmp%d' % len(html_parts)
                    _sl = []
                    for _i, (_ttl, _pair) in enumerate(cmp_slides):
                        _figs = ''.join(
                            '<figure><img src="%s" alt="%s"><figcaption>%s</figcaption></figure>'
                            % (_src, re.sub(r'<[^>]+>', '', inline(_cap)), inline(_cap))
                            for _cap, _src in _pair)
                        _sl.append('<div class="ws-cmp-slide" data-i="%d"%s>%s</div>'
                                   % (_i, '' if _i == 0 else ' hidden', _figs))
                    _tabs = ''.join(
                        '<button type="button" class="ws-cmp-tab%s" onclick="cmpGo(\'%s\',%d)">%s</button>'
                        % (' on' if _i == 0 else '', cid, _i, inline(_t))
                        for _i, (_t, _) in enumerate(cmp_slides))
                    html_parts.append(
                        '<div class="ws-cmp" id="%s" data-n="%d" data-cur="0">'
                        '<div class="ws-cmp-head"><span>%s</span><span>%s</span></div>'
                        '<div class="ws-cmp-tabs">%s</div>'
                        '<div class="ws-cmp-stage">%s</div>'
                        '<div class="ws-cmp-nav"><button type="button" onclick="cmpStep(\'%s\',-1)">‹ 이전</button>'
                        '<span class="ws-cmp-count"><b>1</b> / %d</span>'
                        '<button type="button" onclick="cmpStep(\'%s\',1)">다음 ›</button></div></div>'
                        % (cid, len(cmp_slides), inline(cmp_left), inline(cmp_right),
                           _tabs, ''.join(_sl), cid, len(cmp_slides), cid))
                in_cmp = False
                cmp_slides = []
                continue
            m_h = re.match(r'#{2,4}\s+(.*)', stripped)
            if m_h:
                cmp_slides.append((m_h.group(1).strip(), []))
                continue
            m_ci = re.match(r'!\[(.*?)\]\(([^)]+)\)\s*$', stripped)
            if m_ci and cmp_slides:
                cmp_slides[-1][1].append((m_ci.group(1), m_ci.group(2)))
            continue

        # 🃏 뒤집는 카드 (:::플립 ... :::) — 2026-09-03 천대현
        #   "각 요소를 클릭하면 카드처럼 뒤집히면서 관련 인물이나 사진을 넣으면"
        #   앞면 = 개념(글) · 뒷면 = 그 개념의 **얼굴**(실제 인물·사료).
        #   도식이 구조를 말하고 카드가 얼굴을 붙인다 — 도식을 대체하지 않고 그 아래에 둔다.
        #   ⚠️ 뒷면은 **새 정보**여야 한다. 앞면을 반복하면 뒤집을 이유가 없다.
        #   본문 규약: ![앞면 제목|앞면 부제|뒷면 설명](이미지)
        if stripped.startswith(':::플립'):
            in_flip = True
            flip_items = []
            continue
        if in_flip:
            if stripped == ':::':
                if flip_items:
                    _c = []
                    for _t, _sub, _back, _src in flip_items:
                        _c.append(
                            '<button class="ws-flip" type="button" aria-label="%s 카드 뒤집기" '
                            'onclick="this.classList.toggle(\'on\')">'
                            '<span class="ws-flip-in">'
                            '<span class="ws-flip-f"><b>%s</b><i>%s</i><u>눌러서 뒤집기</u></span>'
                            '<span class="ws-flip-b"><img src="%s" alt="%s"><i>%s</i></span>'
                            '</span></button>'
                            # 🔴 loading="lazy" 금지 — 뒷면은 초기에 rotateY(180deg)로 화면 뒤에 있어
                            #    브라우저가 "안 보인다"고 판단해 로드를 미룬다(뒤집어도 빈 칸).
                            #    alt는 태그를 뺀 순수 텍스트로(inline()은 마크다운을 HTML로 바꾼다).
                            % (inline(_t), inline(_t), inline(_sub), _src,
                               re.sub(r'<[^>]+>', '', inline(_back)), inline(_back)))
                    html_parts.append('<div class="ws-flip-row">%s</div>' % ''.join(_c))
                in_flip = False
                flip_items = []
                continue
            m_fl = re.match(r'!\[(.*?)\]\(([^)]+)\)\s*$', stripped)
            if m_fl:
                _cap, _src = m_fl.group(1), m_fl.group(2)
                _p = [x.strip() for x in _cap.split('|')]
                while len(_p) < 3: _p.append('')
                flip_items.append((_p[0], _p[1], _p[2], _src))
            continue

        if stripped.startswith(':::교과서'):
            in_tb = True
            tb_label = stripped[len(':::교과서'):].strip()
            tb_lines = []
            continue
        if in_tb:
            if stripped == ':::':
                # 🔴 data-label 규약 — 제출 시트·판별식이 "이 칸이 교과서 슬롯인가"를 라벨로 가른다.
                #   질문 줄을 '?'로 시작하게 바꾸면서 라벨이 '? …'로 시작해 규약을 깰 뻔했다
                #   (5-1-1 에서 라벨 규약 미준수로 판별식이 0칸을 통과시킨 전례가 있다).
                #   → 블록 태그를 라벨 앞에 되박아 '교과서 N쪽 — 질문' 형태를 보장한다.
                #   판별식(teaching-textbook-workflow §교과서 슬롯 라벨 규약):
                #     ^\s*(교과서\s*\d+\s*쪽에서\s*찾기\s*—|원문에서\s*확인\s*—)
                #   → 태그에서 첫 쪽수를 뽑아 그 접두어를 **그대로** 만든다.
                #     '94~95쪽'처럼 범위면 앞 숫자만 쓴다(정규식이 `\d+쪽`만 받는다).
                _pg = re.search(r'(\d+)\s*[~-]?\s*\d*\s*쪽', tb_label)
                _pre = f'교과서 {_pg.group(1)}쪽에서 찾기 — ' if _pg else '원문에서 확인 — '
                def _relabel(h):
                    def s(m):
                        cur = re.sub(r'^\?\s*', '', m.group(1)).strip()
                        return 'data-label="%s"' % (_pre + cur)[:70]
                    return re.sub(r'data-label="([^"]*)"', s, h)
                body = []
                for ln in tb_lines:
                    if ln.startswith('?'):
                        body.append(f'<div class="ws-tb-ask">{_relabel(inline(ln[1:].strip()))}</div>')
                    else:
                        body.append(f'<div class="ws-tb-see">{inline(ln)}</div>')
                html_parts.append(
                    f'<div class="ws-tb"><div class="ws-tb-tag">📕 교과서 {inline(tb_label)}</div>'
                    f'{"".join(body)}</div>')
                in_tb = False
                tb_lines = []
                continue
            if stripped:
                tb_lines.append(stripped)
            continue

        # 📖 고급 단어 아코디언 (:::낱말 [핵심낱말] / 행 | 뜯기 | 문장  +  '+ 뜻 | 가족낱말')
        #   2026-09-04 천대현: "표 스타일에서 낱말을 클릭하면 그 칸 바로 밑으로 뜻이랑
        #   가족 낱말이 열리고, 다시 클릭하면 닫히게."
        #   🔴 왜 전용 블록인가 — 마크다운 접기(> [!타입]-)를 표 셀에 넣으면 평문으로 샌다.
        #      그러나 그것이 '표를 버리라'는 뜻은 아니다. 이 블록은 <table>과 토글 JS를
        #      직접 생성하므로 마크다운 파서를 거치지 않는다(:::인물선택·:::시소와 같은 경로).
        #      2026-09-04에 마크다운 접기로만 재보고 "표는 불가"라고 결론 낸 것은 허수아비 비교였다.
        #   🔴 입력칸 0 — act 인덱스가 안 밀리므로 기수업 차시에도 넣을 수 있다.
        #   ♿ 여는 것은 <button> + aria-expanded — <td> onclick만 달면 키보드로 못 연다.
        # 🀄 고급 단어 한자 카드 (:::낱말카드 [머리말] / 낱말|뜯어보기|문장|이미지  + 뜻|가족낱말)
        #   2026-09-07 천대현: "한자 카드 스타일로 정보는 그대로 담으면서 이미지까지.
        #   클릭하면 뒤집히는 스타일로. 단어가 많으면 아래로 내리지 말고 옆으로 넘기는 방식."
        #   앞면 = 이미지 + 한자 + 한글(무엇인지 추측) / 뒷면 = 뜯어보기·뜻·문장·가족 낱말.
        #   :::낱말(표 아코디언)과 정보량은 같다 — 형태만 다르다. 표가 나은 차시는 표를 쓴다.
        #   🔴 이 검사는 반드시 ':::낱말'보다 **앞**에 온다 — startswith(':::낱말')이
        #      ':::낱말카드'도 삼켜서, 뒤에 두면 카드가 조용히 표로 렌더된다.
        #   🔴 lazy 금지 — 앞면이라 지금은 보이지만, 캐러셀에서 화면 밖 카드는
        #      브라우저가 "안 보인다"고 판단해 넘겨도 빈 칸이 뜬다(:::플립 뒷면과 같은 함정).
        #   🔴 입력칸 0 — act 인덱스 불변이라 기수업 차시에도 넣을 수 있다.
        #   ♿ 카드는 <button>(키보드 Enter/Space로 뒤집힘) · 넘기기는 스크롤 + ◀▶ 버튼 둘 다.
        if stripped.startswith(':::낱말카드'):
            in_vcd = True; vcd_rows = []
            _h = stripped[len(':::낱말카드'):].strip()
            vcd_head = _h[1:_h.index(']')].strip() if _h.startswith('[') and ']' in _h else ''
            continue
        if in_vcd:
            if stripped == ':::':
                cid = f'vd{len(html_parts)}'
                cards = []
                for name, extra in vcd_rows:
                    cells = [x.strip() for x in name.strip('|').split('|')]
                    while len(cells) < 4: cells.append('')
                    raw = cells[0].replace('**', '').strip()
                    # 🔴 괄호는 이름 '끝'에만 오지 않는다 — `주종(主從) 관계`처럼 뒤에 말이 붙는다.
                    #   끝에서만 찾던 정규식이 이 경우를 놓쳐 한자가 안 커졌다(2026-09-07 실측).
                    #   → 한자 괄호를 위치 무관하게 찾고, 남은 글자를 한글 이름으로 쓴다.
                    #   한자가 없는 낱말(성직 매매)은 매치가 안 되므로 종전대로 한글만 크게 선다.
                    mh = re.search(r'\(\s*([一-鿿]+)\s*\)', raw)
                    hanja = mh.group(1) if mh else ''
                    ko = (raw[:mh.start()] + raw[mh.end():] if mh else raw).strip()
                    ko = re.sub(r'\s{2,}', ' ', ko)
                    img = cells[3].strip()
                    face = (f'<span class="vcd-hanja">{hanja}</span>' if hanja else '')
                    # 한자가 없는 낱말(예: 성직 매매)은 한글을 크게 세워 카드가 비지 않게 한다.
                    face += f'<span class="vcd-ko{"" if hanja else " vcd-ko-solo"}">{ko}</span>'
                    back = f'<span class="vcd-split">{inline(cells[1])}</span>' if cells[1] else ''
                    if extra:
                        back += f'<span class="vcd-mean">{inline(extra[0])}</span>'
                    if cells[2]:
                        back += f'<span class="vcd-sent">{inline(cells[2])}</span>'
                    if len(extra) > 1:
                        back += f'<span class="vcd-fam">{inline(extra[1])}</span>'
                    cards.append(
                        f'<button type="button" class="ws-vcard" aria-label="{ko} 카드 뒤집기" '
                        'onclick="this.classList.toggle(\'on\')">'
                        '<span class="vcd-in">'
                        '<span class="vcd-f">'
                        + (f'<img src="images/{img}" alt="">' if img else
                           '<span class="vcd-noimg">🀄</span>')
                        + face + '<span class="vcd-turn">눌러서 뒤집기</span></span>'
                        f'<span class="vcd-b"><span class="vcd-bko">{ko}</span>{back}</span>'
                        '</span></button>')
                html_parts.append(
                    f'<div class="ws-vcd" id="{cid}">'
                    + (f'<div class="ws-vcd-head">{inline(vcd_head)}</div>' if vcd_head else '')
                    + f'<div class="ws-vcd-track">{"".join(cards)}</div>'
                    '<div class="ws-vcd-nav">'
                    f'<button type="button" class="vcd-prev" aria-label="이전 낱말">◀</button>'
                    f'<span class="vcd-count"><b>1</b> / {len(cards)}</span>'
                    f'<button type="button" class="vcd-next" aria-label="다음 낱말">▶</button>'
                    '</div></div>'
                    f'<script>(function(){{var r=document.getElementById("{cid}");'
                    'var t=r.querySelector(".ws-vcd-track"),c=r.querySelector(".vcd-count b");'
                    'var cs=[].slice.call(t.querySelectorAll(".ws-vcard"));'
                    # step = 카드 폭 + gap. 카드가 1장뿐이면 0으로 나누게 되므로 방어한다.
                    'function step(){return cs.length>1?cs[1].offsetLeft-cs[0].offsetLeft:1;}'
                    'function idx(){return Math.max(0,Math.min(cs.length-1,'
                    'Math.round(t.scrollLeft/step())));}'
                    # 🔴 끝에 닿으면 마지막 번호를 보이고 버튼을 잠근다 — 안 그러면
                    #    "▶를 눌렀는데 아무 일도 안 난다"(마지막 카드가 이미 보이는 상태)로 읽힌다.
                    'var P=r.querySelector(".vcd-prev"),N=r.querySelector(".vcd-next");'
                    'function sync(){var m=t.scrollWidth-t.clientWidth,e=t.scrollLeft>=m-2;'
                    'c.textContent=e?cs.length:idx()+1;'
                    'P.disabled=t.scrollLeft<=2;N.disabled=e;}'
                    'function go(d){t.scrollTo({left:(idx()+d)*step(),behavior:"smooth"});}'
                    'P.addEventListener("click",function(){go(-1);});'
                    'N.addEventListener("click",function(){go(1);});'
                    't.addEventListener("scroll",function(){clearTimeout(t._z);'
                    't._z=setTimeout(sync,90);});'
                    # 🔴 낱말이 적어 한 줄에 다 들어오면 ◀▶는 눌러도 안 움직인다 —
                    #    작동하지 않는 버튼을 보여 주느니 감춘다. 폰에서 좁아지면 다시 나온다.
                    'function navfit(){var s=t.scrollWidth-t.clientWidth;'
                    'r.querySelector(".ws-vcd-nav").style.display=s>step()/2?"":"none";}'
                    'navfit();sync();addEventListener("resize",function(){navfit();sync();});'
                    '})();</script>')
                in_vcd = False; vcd_rows = []
                continue
            if stripped.startswith('+'):
                if vcd_rows: vcd_rows[-1][1].extend(
                    [x.strip() for x in stripped[1:].split('|') if x.strip()])
                continue
            if stripped.startswith('|') and not set(stripped.replace('|','').replace(' ','')) <= set('-:'):
                vcd_rows.append([stripped, []])
            continue

        if stripped.startswith(':::낱말'):
            in_voc = True; voc_rows = []
            _h = stripped[len(':::낱말'):].strip()
            voc_key = _h[1:_h.index(']')].strip() if _h.startswith('[') and ']' in _h else ''
            continue
        if in_voc:
            if stripped == ':::':
                vid = f'vc{len(html_parts)}'
                trs = ''
                for i, (head, body) in enumerate(voc_rows):
                    cells = [x.strip() for x in head.strip('|').split('|')]
                    name = cells[0] if cells else ''
                    rest = ''.join(f'<td>{inline(c)}</td>' for c in cells[1:])
                    opened = bool(voc_key) and voc_key in name
                    trs += (
                      f'<tr class="vc-head">'
                      f'<td><button type="button" class="vc-btn" aria-expanded="{"true" if opened else "false"}" '
                      f'aria-controls="{vid}-{i}">{inline(name)}</button></td>{rest}</tr>'
                      f'<tr class="vc-body" id="{vid}-{i}"{"" if opened else " hidden"}>'
                      f'<td colspan="{max(1,len(cells))}">'
                      + ''.join(f'<p>{inline(x)}</p>' for x in body) + '</td></tr>')
                html_parts.append(
                  f'<table class="ws-voc" id="{vid}">'
                  f'<thead><tr><th>낱말</th><th>한자 뜯어보기</th><th>문장 속에서</th></tr></thead>'
                  f'<tbody>{trs}</tbody></table>'
                  f'<script>(function(){{var t=document.getElementById("{vid}");'
                  't.querySelectorAll(".vc-btn").forEach(function(b){'
                  'b.addEventListener("click",function(){'
                  'var r=document.getElementById(b.getAttribute("aria-controls"));'
                  'var open=b.getAttribute("aria-expanded")==="true";'
                  'b.setAttribute("aria-expanded",open?"false":"true");r.hidden=open;});});})();</script>')
                in_voc = False; voc_rows = []
                continue
            if stripped.startswith('+'):
                if voc_rows: voc_rows[-1][1].extend(
                    [x.strip() for x in stripped[1:].split('|') if x.strip()])
                continue
            if stripped.startswith('|') and not set(stripped.replace('|','').replace(' ','')) <= set('-:'):
                voc_rows.append([stripped, []])
            continue

        # 🎮 인물 선택 활동 (:::인물선택 <발문> / 이름 | 상황 | 웃음|울음 | 이유 ... :::)
        #   2026-09-03 천대현: "표로 바로 제시하지 말고 캐릭터 선택 화면처럼 고르게 하고,
        #   다 고르면 구분된 표가 나타나게." 교과서 107쪽도 같은 내용을 역할놀이로 낸다 —
        #   우리가 활동을 표로 눌러놨던 것이다.
        #   🔴 제출에 넣지 않는다(입력칸 0) — 평가가 아니라 판단을 흔드는 자리다. act 인덱스 불변.
        #   정답은 **다 고른 뒤에만** 공개한다(하나씩 즉시 채점하면 찍기로 넘어간다).
        #   ⭐ 2026-09-04 일반화 — 옵션을 대괄호로 주면 N지선다가 된다.
        #      `:::인물선택 발문`                    → 웃음/울음 2지선다(종전과 동일·5-5 무영향)
        #      `:::인물선택 [자국 이익|힘의 논리|협력] 발문` → 3갈래 분류, 기분 표정 없음
        #      이미지명을 비우면 <img>를 넣지 않는다 — 실재 사건은 생성 이미지를 쓰지 않으므로.
        if stripped.startswith(':::인물선택'):
            in_pick = True
            _h = stripped[len(':::인물선택'):].strip()
            # 2026-09-07: ':::인물선택카드' = 포켓몬 카드 결(금테·창·풋터).
            #   별도 이름으로 둔 이유 — .pk-card 자체에 금테를 주면 5-5 등
            #   기존 인물선택 차시가 재발행 순간 같이 바뀐다. 옛 차시는 그대로 둔다.
            pick_gold = _h.startswith('카드')
            if pick_gold:
                _h = _h[2:].strip()
            pick_opts, pick_mood = ['웃음', '울음'], True
            if _h.startswith('[') and ']' in _h:
                _o, _h = _h[1:_h.index(']')], _h[_h.index(']') + 1:].strip()
                pick_opts = [x.strip() for x in _o.split('|') if x.strip()]
                pick_mood = (pick_opts == ['웃음', '울음'])
            pick_q = _h
            pick_rows = []
            continue
        if in_pick:
            if stripped == ':::':
                pid = f'pk{len(html_parts)}'
                cards = ''
                _face = {'웃음': '😀 웃는다', '울음': '😢 운다'}
                for i, (nm, sit, ans, why, img) in enumerate(pick_rows):
                    assert ans in pick_opts, f'❌ 정답 "{ans}"가 옵션 {pick_opts}에 없다 — {nm}'
                    btns = ''.join(
                        f'<button type="button" class="pk-b" data-v="{o}">'
                        f'{_face.get(o, o) if pick_mood else o}</button>' for o in pick_opts)
                    # 확장자가 붙어 있으면 images/ 바로 아래, 아니면 옛 people 규약 유지
                    _src = f'images/{img}' if '.' in img else f'images/people/{img}.png'
                    # 🔴 래퍼는 카드형일 때만 — 옛 인물선택 차시(5-5 등)의 출력이
                    #    글자 하나까지 같아야 "재발행해도 안전"이 성립한다.
                    if not img:
                        im = ''
                    elif pick_gold:
                        _alt = re.sub(r'<[^>]+>', '', inline(nm))
                        im = f'<span class="pk-win"><img src="{_src}" alt="{_alt}" loading="lazy"></span>'
                    else:
                        im = f'<img src="{_src}" alt="" loading="lazy">' 
                    cards += (
                      f'<div class="pk-card{"" if img else " pk-noimg"}" data-i="{i}" data-ans="{ans}">'
                      f'{im}<div class="pk-name">{inline(nm)}</div>'
                      f'<div class="pk-sit">{inline(sit)}</div>'
                      f'<div class="pk-btns{"" if len(pick_opts) < 3 else " pk-btns-col"}">{btns}</div>'
                      f'<div class="pk-why" hidden>{inline(why)}</div></div>')
                html_parts.append(
                  f'<div class="ws-pick" id="{pid}">'
                  f'<div class="pk-head"><span>{inline(pick_q)}</span>'
                  f'<b class="pk-count">0 / {len(pick_rows)}</b></div>'
                  f'<div class="pk-grid{" pk-gold" if pick_gold else ""}">{cards}</div>'
                  f'<div class="pk-result" hidden></div></div>'
                  f'<script>(function(){{var w=document.getElementById("{pid}");'
                  f'var cs=[].slice.call(w.querySelectorAll(".pk-card")),N=cs.length;'
                  f'var OPTS={json.dumps(pick_opts, ensure_ascii=False)},MOOD={"true" if pick_mood else "false"};'
                  'function done(){return cs.filter(function(c){return c.dataset.pick}).length}'
                  'function reveal(){var ok=0;cs.forEach(function(c){'
                  'var right=c.dataset.pick===c.dataset.ans;if(right)ok++;'
                  'c.classList.add(right?"pk-ok":"pk-no");'
                  # 틀렸으면 실제 정답의 기분으로 뒤집는다 — 표정이 바뀌는 것이 곧 피드백이다
                  'if(!right&&MOOD){c.classList.remove("pk-happy","pk-sad");'
                  'c.classList.add(c.dataset.ans==="웃음"?"pk-happy":"pk-sad");}'
                  'if(!right)c.querySelector(".pk-why").hidden=false;});'
                  'var r=w.querySelector(".pk-result");r.hidden=false;'
                  'r.innerHTML="<b>"+ok+" / "+N+"</b> 맞혔어. 틀린 카드에만 이유가 펼쳐졌어 — 거기부터 보자.'
                  '<div class=\'pk-sum\'>"+OPTS.map(function(o,oi){'
                  'var head=MOOD?(o==="웃음"?"웃는 사람":"우는 사람"):o;'
                  'var cls=MOOD?(o==="웃음"?"pk-up":"pk-down"):("pk-c"+oi);'
                  'return "<div class=\'pk-col "+cls+"\'><b>"+head+"</b>"'
                  '+cs.filter(function(c){return c.dataset.ans===o}).map(function(c){'
                  'return "<span>"+c.querySelector(".pk-name").textContent+"</span>"}).join("")'
                  '+"</div>"}).join("")'
                  '+"</div>";r.scrollIntoView({block:"nearest",behavior:"smooth"});}'
                  'cs.forEach(function(c){c.querySelectorAll(".pk-b").forEach(function(b){'
                  'b.addEventListener("click",function(){if(w.classList.contains("pk-done"))return;'
                  'c.dataset.pick=b.dataset.v;c.classList.add("pk-set");'
                  # 🙂 기분 상태 — 고른 순간 카드가 웃거나 운다 (2026-09-03 천대현)
                  'if(MOOD){c.classList.remove("pk-happy","pk-sad");'
                  'c.classList.add(b.dataset.v==="웃음"?"pk-happy":"pk-sad");}'
                  'c.querySelectorAll(".pk-b").forEach(function(x){x.classList.toggle("on",x===b)});'
                  'w.querySelector(".pk-count").textContent=done()+" / "+N;'
                  'if(done()===N){w.classList.add("pk-done");reveal();}});});});'
                  '})();</script>')
                in_pick = False
                pick_rows = []
            elif stripped and '|' in stripped:
                parts = [x.strip() for x in stripped.split('|')]
                while len(parts) < 5: parts.append('')
                pick_rows.append(tuple(parts[:5]))
            continue

        # ⚖️ 움직이는 시소 (:::시소) — 2026-09-03 천대현 "표의 시소를 움직이게 할 수 있나?"
        #   정지 도식은 '환율↑이면 원화 가치↓'를 *보여만* 준다. 학생이 직접 밀어 보면
        #   둘이 같이 올라가는 일이 없다는 것을 손으로 확인한다.
        #   🔴 원화 가치를 '%'로 쓰지 않는다(2026-09-03 천대현 지적) — 기준(1,100원=100%)이
        #   화면에 없어 무엇 대비인지 알 수 없고, 기준을 달러 쪽으로 바꾸면 값이 달라진다
        #   (달러 9.1% 하락 vs 원화 10% 상승). 교과서도 %로 재지 않는다.
        #   대신 '1,000원으로 살 수 있는 달러'로 쓴다 — 그게 돈의 가치의 정의이고 기준이 문구에 있다.
        if stripped == ':::시소':
            sid = f'ss{len(html_parts)}'
            html_parts.append(f'''<div class="ws-seesaw" id="{sid}">
  <div class="ws-seesaw-head">환율을 직접 움직여 보자 — 둘이 같이 올라가는 일이 있는지</div>
  <input class="ws-seesaw-range" type="range" min="1000" max="1500" step="10" value="1100"
         aria-label="환율 조절">
  <div class="ws-seesaw-stage">
    <div class="ws-seesaw-beam"></div>
    <div class="ws-seesaw-pivot"></div>
    <div class="ws-seesaw-chip ws-l"><b>환율</b><span class="v">1,100원</span></div>
    <div class="ws-seesaw-chip ws-r"><b>1,000원으로</b><span class="v">$0.91</span></div>
  </div>
  <div class="ws-seesaw-note">원화 가치 = <b>1,000원으로 살 수 있는 달러</b>. 환율이 오를수록 줄어든다.</div>
  <div class="ws-seesaw-out">100달러짜리 굿즈 = <b>110,000원</b></div>
</div>
<script>(function(){{
  var w=document.getElementById('{sid}');
  var r=w.querySelector('.ws-seesaw-range'), beam=w.querySelector('.ws-seesaw-beam');
  var L=w.querySelector('.ws-l'), R=w.querySelector('.ws-r'), out=w.querySelector('.ws-seesaw-out');
  function draw(){{
    var fx=+r.value;
    // 🔴 회전 중심은 슬라이더 한가운데(1,250)가 아니라 **기준 환율 1,100원**이다 (2026-09-03 천대현).
    //   전엔 1,250을 수평으로 잡아 기본값에서부터 -5.4°로 기울어 있었다. 기준은 교과서 값이어야 한다.
    var deg=Math.max(-9,Math.min(9,(fx-1100)/400*9));
    var half=beam.offsetWidth/2;                   // 폰 분기(300px)에서도 끝점이 맞도록 실측
    var dy=-Math.sin(deg*Math.PI/180)*half;        // 왼쪽(환율) 끝의 세로 변위
    beam.style.transform='rotate('+deg+'deg)';
    // 칩 아래끝을 빔 끝에 얹는다 — 높이에 안 기대도록 calc(-100%)로 잡는다
    L.style.transform='translateY(calc(-100% - 8px + '+dy+'px))';
    R.style.transform='translateY(calc(-100% - 8px + '+(-dy)+'px))';
    L.querySelector('.v').textContent=fx.toLocaleString()+'원';
    R.querySelector('.v').textContent='$'+(1000/fx).toFixed(2);   // 원화 가치 = 1,000원으로 살 수 있는 달러
    L.classList.toggle('up',deg>0.5); R.classList.toggle('up',deg<-0.5);
    out.innerHTML='100달러짜리 굿즈 = <b>'+(fx*100).toLocaleString()+'원</b>';
  }}
  r.addEventListener('input',draw); draw();
}})();</script>''')
            continue

        # 🕰 연표 시소 (:::연표시소 <머리말>  /  <라벨> | <기울기> | <왼쪽> | <오른쪽> | <설명>)
        #   2026-09-09. 정지 도식(3-3-2_232년역전.webp)을 대체한다. 그 그림은
        #   (a) 폰 배율 0.266에서 연도 글자가 4.8px라 안 읽히고(-0.83 Images of Text)
        #   (b) 좌우 칩이 '교황권/왕권' 한 낱말이라 그 차시의 줄거리인 **상대의 교체**를 지웠으며
        #   (c) 교과서 밖 단정 두 개("왕의 힘은 땅·군대·돈에서" / "한때 셋")가 글자로 구워져 있었다.
        #   ⚠️ :::시소(환율)와 클래스를 공유하지 않는다 — 그쪽은 좌=빨강/우=파랑과 초록 결과 상자가
        #      하드코딩이라 재사용하면 환율 색이 딸려 온다. 기하(half/dy) 식만 같다.
        #   ⚠️ 이산 사건이라 슬라이더가 아니라 버튼이다. 슬라이더는 '사이 값'을 약속하는데
        #      1200년쯤의 중간 기울기는 교과서에 없는 사실이다.
        #   ⚠️ 입력칸을 만들지 않는다 → act 인덱스 불변(-0.81).
        #   ⚠️ 형제 파서의 선행 파이프 함정: .strip('|') 로 첫 필드 밀림을 막는다.
        if stripped.startswith(':::연표시소'):
            in_tl = True
            tl_head = stripped[len(':::연표시소'):].strip()
            tl_spr = ('', '')
            # [왼쪽 스프라이트 | 오른쪽 스프라이트] 접두 옵션 — :::낱말카드 와 같은 규약
            if tl_head.startswith('[') and ']' in tl_head:
                _in = tl_head[1:tl_head.index(']')]
                _pp = [x.strip() for x in _in.split('|')]
                tl_spr = (_pp[0] if _pp else '', _pp[1] if len(_pp) > 1 else '')
                tl_head = tl_head[tl_head.index(']') + 1:].strip()
            tl_rows = []
            continue
        if in_tl:
            if stripped != ':::':
                if stripped:
                    tl_rows.append(stripped)
                continue
            rows = []
            for _r in tl_rows:
                _p = [x.strip() for x in _r.strip().strip('|').split('|')]
                while len(_p) < 5:
                    _p.append('')
                _lab, _deg, _ln, _rn, _say = _p[:5]
                _l0, _, _l1 = _ln.partition('/')
                _r0, _, _r1 = _rn.partition('/')
                try:
                    _d = float(_deg)
                except ValueError:
                    _d = 0.0
                rows.append({'lab': _lab, 'deg': _d,
                             'l0': _l0.strip(), 'l1': _l1.strip(),
                             'r0': _r0.strip(), 'r1': _r1.strip(), 'say': _say})
            if rows:
                tid = f'tl{len(html_parts)}'
                btns = ''.join(
                    f'<button type="button" role="tab" class="tl-tab" data-i="{i}" '
                    f'aria-selected="{"true" if i == 0 else "false"}">{inline(r["lab"])}</button>'
                    for i, r in enumerate(rows))
                prow = ''.join(
                    '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
                        inline(r['lab']),
                        inline(r['l0'] if r['deg'] < 0 else (r['r0'] if r['deg'] > 0 else '―')),
                        inline(r['r0'] + (' · ' + r['r1'] if r['r1'] else '')),
                        inline(r['say'])) for r in rows)
                _sl = f'<img class="tl-spr" src="{tl_spr[0]}" alt="">' if tl_spr[0] else ''
                _sr = f'<img class="tl-spr" src="{tl_spr[1]}" alt="">' if tl_spr[1] else ''
                html_parts.append(
                    f'<div class="ws-tl" id="{tid}">'
                    f'<div class="ws-tl-head">{inline(tl_head)}</div>'
                    f'<div class="ws-tl-stage"><div class="ws-tl-beam"></div>'
                    f'<div class="ws-tl-pivot"></div><div class="ws-tl-base"></div>'
                    f'<div class="ws-tl-chip tl-l"><span class="rope"></span>'
                    f'<span class="box">{_sl}<b></b><span class="s"></span></span>'
                    f'<span class="win">▲ 우세</span></div>'
                    f'<div class="ws-tl-chip tl-r"><span class="rope"></span>'
                    f'<span class="box">{_sr}<b></b><span class="s"></span></span>'
                    f'<span class="win">▲ 우세</span></div></div>'
                    f'<div class="ws-tl-say"></div>'
                    f'<div class="ws-tl-tabs" role="tablist">{btns}</div>'
                    f'<table class="tl-print"><tr><td>시점</td><td>내려간 쪽</td>'
                    f'<td>교황의 상대</td><td>무슨 일이 있었나</td></tr>{prow}</table></div>'
                    f'<script>(function(){{'
                    f'var D={json.dumps(rows, ensure_ascii=False)};'
                    f'var w=document.getElementById("{tid}");'
                    'var beam=w.querySelector(".ws-tl-beam"),L=w.querySelector(".tl-l"),'
                    'R=w.querySelector(".tl-r"),'
                    'say=w.querySelector(".ws-tl-say");'
                    'var tabs=[].slice.call(w.querySelectorAll(".tl-tab"));'
                    'function draw(i){var d=D[i],deg=d.deg,half=beam.offsetWidth/2;'
                    'var dy=-Math.sin(deg*Math.PI/180)*half;'
                    'beam.style.transform="rotate("+deg+"deg)";'
                    'L.style.transform="translateY("+dy+"px)";'
                    'R.style.transform="translateY("+(-dy)+"px)";'
                    'L.querySelector("b").textContent=d.l0;L.querySelector(".s").textContent=d.l1;'
                    'R.querySelector("b").textContent=d.r0;R.querySelector(".s").textContent=d.r1;'
                    'L.classList.toggle("dn",deg<0);L.classList.toggle("up",deg>0);'
                    'R.classList.toggle("dn",deg>0);R.classList.toggle("up",deg<0);'
                    'L.querySelector(".win").style.visibility=(deg<-0.2?"visible":"hidden");'
                    'R.querySelector(".win").style.visibility=(deg>0.2?"visible":"hidden");'
                    'say.textContent=d.say;'
                    'tabs.forEach(function(b,j){b.setAttribute("aria-selected",j===i?"true":"false");});}'
                    'tabs.forEach(function(b,j){b.addEventListener("click",function(){draw(j);});});'
                    'w.addEventListener("keydown",function(e){var i=0;'
                    'tabs.forEach(function(b,j){if(b.getAttribute("aria-selected")==="true")i=j;});'
                    'if(e.key==="ArrowRight"&&i<tabs.length-1){draw(i+1);tabs[i+1].focus();}'
                    'if(e.key==="ArrowLeft"&&i>0){draw(i-1);tabs[i-1].focus();}});'
                    'draw(0);})();</script>')
            in_tl = False
            tl_rows = []
            continue

        # 📖 표·도식을 읽는 자리 (:::해설 ... :::) — 2026-09-03 천대현
        #   계열이 셋이 된다: 파랑=쓰는 곳(빈칸) · 황토=교과서를 펴는 곳 · 회색=읽는 곳.
        #   표 아래 해설이 본문 문단과 같은 모양이라 "여기도 빈칸이 있나" 하고 보게 됐다.
        #   입력칸을 만들지 않는다 — 이 블록은 읽기 전용이다.
        if stripped.startswith(':::해설'):
            in_read = True
            read_lines = []
            continue
        if in_read:
            if stripped == ':::':
                body = ''.join(f'<p>{inline(x)}</p>' for x in read_lines)
                html_parts.append(
                    '<div class="ws-read"><div class="ws-read-tag">읽고 넘어가는 곳</div>'
                    + body + '</div>')
                in_read = False
                read_lines = []
            elif stripped:
                read_lines.append(stripped)
            continue

        if stripped.startswith(':::gallery'):
            in_gallery = True
            gallery_items = []
            gallery_title = stripped[len(':::gallery'):].strip()
            continue
        if in_gallery:
            if stripped == ':::':
                if gallery_items:
                    gid = f'gal{len(html_parts)}'
                    slides = ''.join(
                        f'<figure class="ws-gal-slide" data-i="{i}"{"" if i==0 else " hidden"}>'
                        f'<img src="{src}" alt="{cap}" loading="lazy">'
                        f'<figcaption><b>{inline(tag)}</b> {inline(cap)}</figcaption></figure>'
                        for i,(tag,cap,src) in enumerate(gallery_items))
                    dots = ''.join(
                        f'<button class="ws-gal-dot{" on" if i==0 else ""}" '
                        f'onclick="galGo(\'{gid}\',{i})">{inline(t)}</button>'
                        for i,(t,_,_) in enumerate(gallery_items))
                    html_parts.append(
                        f'<div class="ws-gal" id="{gid}" data-n="{len(gallery_items)}">'
                        f'<div class="ws-gal-head">{inline(gallery_title)}</div>'
                        f'<div class="ws-gal-tabs">{dots}</div>'
                        f'<div class="ws-gal-stage">{slides}</div>'
                        f'<div class="ws-gal-nav">'
                        f'<button onclick="galStep(\'{gid}\',-1)">‹ 이전</button>'
                        f'<span class="ws-gal-count"><b>1</b> / {len(gallery_items)}</span>'
                        f'<button onclick="galStep(\'{gid}\',1)">다음 ›</button></div></div>')
                in_gallery = False
                gallery_items = []
                continue
            m_g = re.match(r'!\[(.*?)\]\(([^)]+)\)\s*$', stripped)
            if m_g:
                cap, src = m_g.group(1), m_g.group(2)
                tag, _, rest = cap.partition('|')      # "1월 · 귀족|새해 잔치…" 형식
                gallery_items.append((tag.strip(), rest.strip() or tag.strip(), src))
            continue

        if stripped == ':::figrow':
            in_figrow = True
            figrow_items = []
            continue
        if in_figrow:
            if stripped == ':::':
                if figrow_items:
                    html_parts.append(f'<div class="ws-figrow">{"".join(figrow_items)}</div>')
                in_figrow = False
                figrow_items = []
                continue
            m_ri = re.match(r'!\[(.*?)\]\(([^)]+)\)\s*$', stripped)
            if m_ri:
                cap, src = m_ri.group(1), m_ri.group(2)
                fc = f'<figcaption>{inline(cap)}</figcaption>' if cap else ''
                figrow_items.append(
                    f'<figure class="ws-figrow-item"><img src="{src}" alt="{cap}" loading="lazy">{fc}</figure>'
                )
            continue

        # 빈 div (서술형 답안 칸) → 서술형 textarea로 변환 (제출 수합·세특용 data-id essay-N)
        if '<div style="height:' in stripped:
            essay_count += 1
            elbl = last_heading or f'서술{essay_count}'
            html_parts.append(f'<textarea class="essay-input" data-id="essay-{essay_count}" data-label="{elbl}" placeholder="자기 생각을 자유롭게 써 보세요"></textarea>')
            continue

        # 반/번/이름 줄은 학생 정보라 빈칸 매칭 스킵
        if re.search(r'\*\*반:\*\*.*\*\*번:\*\*.*\*\*이름:\*\*', line):
            # 이미 상단에 student-info 입력란이 있으므로 이 줄 자체를 스킵
            continue

        # 빈칸을 input으로 교체
        blanks = list(blank_pattern.finditer(line))
        if blanks:
            new_line = line
            offset = 0
            for b in blanks:
                if answer_idx < len(answers):
                    answer = answers[answer_idx]
                    input_width = max(len(answer) * 16 + 20, 60)
                    extra_class = ' no-score' if in_step0 else ''
                    input_html = (
                        f'<input type="text" class="blank-input{extra_class}" '
                        f'data-answer="{answer}" '
                        f'data-id="{answer_idx + 1}" '
                        f'style="width:{input_width}px" '
                        f'placeholder="">'
                    )
                    start = b.start() + offset
                    end = b.end() + offset
                    new_line = new_line[:start] + input_html + new_line[end:]
                    offset += len(input_html) - (b.end() - b.start())
                    answer_idx += 1
                    if not in_step0:
                        total_blanks += 1
            line = new_line

        # 마크다운 → HTML
        stripped = line.strip()

        # 2026-08-31: 접힌 블록은 '>' 줄이 이어지는 동안만 유효. 헤딩·표·이미지·빈 줄이
        #   오면 여기서 한 번에 닫는다(닫기를 여러 분기에 흩뿌리면 반드시 하나를 빠뜨린다).
        if in_fold and not stripped.startswith('>'):
            if fold_tbl:
                html_parts.append(_fold_table(fold_tbl, inline)); fold_tbl = []
            html_parts.append('</div></details>')
            in_fold = False

        # 이미지/영상 ![캡션](src) → figure (2026-05-30: 본문 사료/figure 렌더. wiki-embed ![[..]]는 위에서 이미 제거됨)
        # 2026-06-15: src가 .mp4/.webm 이면 <video> 렌더 (대운하 설명 영상 등 학습지 임베드)
        m_img = re.match(r'!\[(.*?)\]\(([^)]+)\)\s*$', stripped)
        if m_img:
            cap, src = m_img.group(1), m_img.group(2)
            fc = f'<figcaption>{inline(cap)}</figcaption>' if cap else ''
            if re.search(r'\.(mp4|webm|mov)(\?|$)', src, re.I):
                vtype = 'video/webm' if re.search(r'\.webm', src, re.I) else 'video/mp4'
                html_parts.append(
                    f'<figure class="ws-fig"><video class="ws-fig-video" controls preload="metadata" '
                    f'playsinline><source src="{src}" type="{vtype}">동영상을 재생할 수 없습니다.</video>{fc}</figure>')
            else:
                # 2026-09-02: 애니메이션 이미지에는 '다시 보기' 버튼을 단다.
                #   WCAG 2.2.2를 지키려 loop=1로 구웠더니(룰 -0.82) 한 번 지나가면 다시 못 본다.
                #   재생 버튼은 사용자에게 제어를 주므로 접근성과 재시청을 동시에 만족한다.
                if _is_animated(src, out_path):
                    aid = f'anim{len(html_parts)}'
                    html_parts.append(
                        f'<figure class="ws-fig ws-anim"><img id="{aid}" src="{src}" alt="{cap}" '
                        f'data-src="{src}" loading="lazy">'
                        f'<div class="ws-anim-ctl"><button type="button" onclick="replayAnim(\'{aid}\')">'
                        f'▶ 다시 보기</button><span>한 번 재생됩니다</span></div>{fc}</figure>')
                else:
                    html_parts.append(f'<figure class="ws-fig"><img src="{src}" alt="{cap}" loading="lazy">{fc}</figure>')
            continue

        # 헤딩
        if stripped.startswith('#### '):
            last_heading = _hlabel(stripped[5:])
            html_parts.append(f'<h4>{inline(stripped[5:])}</h4>')
        elif stripped.startswith('### '):
            last_heading = _hlabel(stripped[4:])
            html_parts.append(f'<h3>{inline(stripped[4:])}</h3>')
        elif stripped.startswith('## '):
            last_heading = _hlabel(stripped[3:])
            html_parts.append(f'<h2>{inline(stripped[3:])}</h2>')
        elif stripped.startswith('# '):
            html_parts.append(f'<h1>{inline(stripped[2:])}</h1>')
        # 테이블
        elif stripped.startswith('|'):
            if not in_table:
                html_parts.append('<table>')
                in_table = True
                table_idx += 1
                table_row_idx = 0
            if re.match(r'^\|[\s\-:|]+\|$', stripped):
                continue
            cells = [c.strip() for c in stripped.split('|')[1:-1]]

            # 셀 내 전각 공백만 있는 칸 감지 (\u3000 = 전각 공백)
            # strip 전 원본으로 빈칸 감지 (strip()이 전각 공백을 제거하므로)
            cells_raw = stripped.split('|')[1:-1]

            def is_blank_cell_raw(c):
                """전각 공백이나 일반 공백만으로 구성된 셀 (원본 기준)"""
                return bool(re.match(r'^[\u3000\s]+$', c)) and len(c.strip('\u3000').strip()) == 0 and len(c) > 1

            has_blank_cells = any(is_blank_cell_raw(c) for c in cells_raw[1:])  # 첫 셀 제외
            # OX 판별: 마지막 셀만 비어있고, 다른 셀에 문장이 있으면 OX
            is_ox = (len(cells_raw) >= 3
                     and is_blank_cell_raw(cells_raw[-1])
                     and not is_blank_cell_raw(cells_raw[1])
                     and len(cells[1]) > 10)

            if is_ox:
                # OX 테이블 (먼저 체크)
                if is_blank_cell_raw(cells_raw[-1]):
                    ox_answer = ''
                    if ox_idx < len(ox_answers):
                        ox_answer = ox_answers[ox_idx]['answer']
                        ox_idx += 1
                        total_ox += 1
                    cells[-1] = (
                        f'<div class="ox-group" data-answer="{ox_answer}">'
                        f'<button class="ox-btn" onclick="selectOX(this,\'O\')">O</button>'
                        f'<button class="ox-btn" onclick="selectOX(this,\'X\')">X</button>'
                        f'</div>'
                    )

            elif has_blank_cells:
                # 보기 버튼 테이블: 정답 파일에서 같은 테이블/행의 정답 가져오기
                answer_row = None
                if table_idx < len(answer_tables) and table_row_idx < len(answer_tables[table_idx]):
                    answer_row = answer_tables[table_idx][table_row_idx]

                for ci in range(len(cells)):
                    cell = cells[ci]
                    if ci > 0 and ci < len(cells_raw) and is_blank_cell_raw(cells_raw[ci]):
                        # 이 셀은 빈칸 → 보기 버튼으로 변환
                        correct_answer = ''
                        if answer_row and ci < len(answer_row):
                            # 정답에서 **답** 추출
                            m = re.search(r'\*\*(.+?)\*\*', answer_row[ci])
                            if m:
                                correct_answer = m.group(1)

                        if correct_answer:
                            # 같은 열의 모든 정답을 보기 옵션으로 수집
                            options = set()
                            for row in answer_tables[table_idx][1:]:  # 헤더 제외
                                if ci < len(row):
                                    m2 = re.search(r'\*\*(.+?)\*\*', row[ci])
                                    if m2:
                                        options.add(m2.group(1))
                            options = list(options)
                            import random
                            random.shuffle(options)

                            blank_table_count += 1
                            btns = ''.join(
                                f'<button class="choice-btn" onclick="selectChoice(this,\'{opt}\')" '
                                f'data-answer="{correct_answer}">{opt}</button>'
                                for opt in options
                            )
                            cells[ci] = f'<div class="choice-group" data-id="tbl-{blank_table_count}">{btns}</div>'
                            total_blanks += 1

            table_row_idx += 1
            html_parts.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in cells) + '</tr>')
        else:
            if in_table:
                html_parts.append('</table>')
                in_table = False
                table_row_idx = 0
            # 콜아웃
            # 2026-08-31: '> [!타입]- 제목' (뒤에 하이픈) = 접힌 블록 → <details>.
            #   빈칸 답이 바로 아래 R3 인용에 그대로 보여 학생이 교과서를 안 펴던 문제(실측 56%,
            #   최근 차시는 100%)를 풀기 위해 도입. 원문을 '채운 뒤 펼쳐 확인'하는 자리로 옮긴다.
            #   Obsidian 표준 접기 문법과 같아 볼트에서도 접힌 상태로 보인다.
            # 🔴 2026-09-04: '+' 도 받는다(옵시디언 표준과 동일 — '+' = 처음부터 펼침).
            #   §15 카드 목록에서 '핵심 낱말 하나만 펼쳐 둔다'를 쓰려면 필요하다.
            #   ⚠️ 같이 고친 것: 접기가 연달아 올 때 이전 블록의 '</div>'를 안 닫아
            #   div가 어긋나던 버그. 카드를 줄줄이 놓는 순간 바로 드러난다.
            m_fold = re.match(r'> \[!([^\]]+)\]([-+])\s*(.*)', stripped)
            if m_fold:
                if in_fold:
                    html_parts.append('</div></details>')
                ftype, fmark, ftitle = m_fold.group(1), m_fold.group(2), m_fold.group(3)
                html_parts.append(
                    f'<details class="ws-fold ws-fold-{ftype}"{" open" if fmark == "+" else ""}>'
                    f'<summary>{inline(ftitle) or "펼쳐 보기"}</summary>'
                    f'<div class="ws-fold-body">')
                in_fold = True
            elif in_fold and stripped.startswith('>'):
                body = stripped[2:] if stripped.startswith('> ') else stripped[1:]
                # 🔴 2026-09-02: 접기 블록 안의 표도 렌더한다.
                #   룰 -0.77(blockquote 안 표는 파이프가 그대로 노출)이 접기에도 그대로 적용됐다.
                #   '|'로 시작하는 줄을 모아 <table>로 낸다. 구분선(|---|)은 헤더 경계로만 쓴다.
                if body.startswith('|'):
                    fold_tbl.append(body)
                    continue
                if fold_tbl:
                    html_parts.append(_fold_table(fold_tbl, inline)); fold_tbl = []
                # 🔴 2026-09-04: 접기 블록 안의 이미지도 렌더한다 — 룰 -0.77의 네 번째 재현.
                #   8/28 blockquote 이미지 → 8/31 blockquote 표 → 9/2 접기 안 표까지 고쳤는데
                #   '접기 안 이미지'만 남아 있었다. 그래서 3-3-1 장원 평면도가 접기 밖에 놓여
                #   "눌러서 펼치기"인데 이미 보이는 상태였다(천대현 발견).
                _mi = re.match(r'!\[(.*?)\]\((.+?)\)\s*$', body.strip())
                if _mi:
                    _cap, _src = _mi.group(1), _mi.group(2)
                    html_parts.append(
                        f'<figure class="ws-fig"><img src="{_src}" alt="{_cap}" loading="lazy">'
                        + (f'<figcaption>{inline(_cap)}</figcaption>' if _cap else '')
                        + '</figure>')
                    continue
                if body.strip():
                    html_parts.append(f'<p>{inline(body)}</p>')
            elif stripped.startswith('> [!'):
                if in_fold:
                    html_parts.append('</div></details>'); in_fold = False
                match = re.match(r'> \[!(\w+)\]\s*(.*)', stripped)
                if match:
                    ctype = match.group(1)
                    ctitle = match.group(2)
                    html_parts.append(f'<div class="callout callout-{ctype}"><strong>{inline(ctitle)}</strong></div>')
            elif stripped.startswith('> '):
                if in_fold:
                    html_parts.append('</div></details>'); in_fold = False
                html_parts.append(f'<blockquote>{inline(stripped[2:])}</blockquote>')
            elif stripped == '':
                html_parts.append('<br>')
            elif stripped == '---':
                if in_fold:
                    html_parts.append('</div></details>'); in_fold = False
                html_parts.append('<hr>')
            else:
                if in_fold:
                    html_parts.append('</div></details>'); in_fold = False
                html_parts.append(f'<p>{inline(stripped)}</p>')

    if in_table:
        html_parts.append('</table>')

    content = '\n'.join(html_parts)
    # ⭐ 6/18: 활동 입력칸(activity-input)이 든 표는 폭 100% 강제 대신 내용 폭(auto)으로.
    #    짧은 단답 칸(120px)이 넓은 셀에 떠 보이는 비율 깨짐 방지 (21-22 학습지 사고).
    def _mark_act_table(m):
        block = m.group(0)
        if 'activity-input' in block:
            return block.replace('<table>', '<table class="act-table">', 1)
        return block
    content = re.sub(r'<table>.*?</table>', _mark_act_table, content, flags=re.S)

    return title, content, total_blanks, total_ox


def inline(text):
    """인라인 마크다운 → HTML"""
    # input 태그 보호
    parts = re.split(r'(<input[^>]+>)', text)
    result = []
    for part in parts:
        if part.startswith('<input') or part.startswith('<textarea'):
            result.append(part)
        else:
            # 2026-08-20: [제목](http…) 링크 지원 — 영상 자료 삽입용. 볼드·이탤릭보다 먼저 처리해 URL이 훼손되지 않게.
            part = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)',
                          r'<a href="\2" target="_blank" rel="noopener">\1</a>', part)
            # 2026-09-04: `인라인 코드` 지원. 종전엔 처리가 없어 **백틱이 학생 화면에 글자로 나갔다**
            #   (실측: 발행본 120개 중 41개에 미변환 백틱 — 34%). 볼드·이탤릭보다 먼저 처리해
            #   코드 안의 별표가 강조로 먹히지 않게 한다.
            part = re.sub(r'`([^`\n]+?)`', lambda m: '<code>' + m.group(1)
                          .replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</code>', part)
            part = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', part)
            part = re.sub(r'\*([^*\n]+?)\*', r'<em>\1</em>', part)  # 2026-05-30: *이탤릭* 지원 (입담 voice 강조어)
            result.append(part)
    return ''.join(result)


def md_to_html(md):
    """키워드 카드 전용 미니 변환기 (표·이미지·불릿·문단만). 2026-08-24.
    기존 본문 파이프라인과 분리 — 카드가 없으면 호출되지 않으므로 회귀 0."""
    out, rows, buf = [], [], []
    def flush_p():
        if buf:
            out.append('<p>' + inline(' '.join(buf)) + '</p>'); buf.clear()
    def flush_tbl():
        if not rows: return
        body = [r for r in rows if not re.match(r'^[\s|:-]+$', r)]
        cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in body]
        if cells:
            h = ''.join(f'<th>{inline(c)}</th>' for c in cells[0])
            b = ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>' for r in cells[1:])
            out.append(f'<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>')
        rows.clear()
    for line in md.split('\n'):
        t = line.strip()
        if t.startswith('|'):
            flush_p(); rows.append(t); continue
        flush_tbl()
        if not t:
            flush_p(); continue
        im = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)$', t)
        if im:
            flush_p(); out.append(f'<img src="{im.group(2)}" alt="{im.group(1)}">'); continue
        if t.startswith('>'):
            # 2026-08-24: 카드 안 blockquote 지원. 없으면 '>'가 글자로 노출됐다(역사 세션 지적).
            flush_p(); out.append('<div class="card-quote">' + inline(t.lstrip('> ').strip()) + '</div>'); continue
        if t.startswith('- '):
            flush_p(); out.append('<p>• ' + inline(t[2:]) + '</p>'); continue
        buf.append(t)
    flush_p(); flush_tbl()
    return ''.join(out)


def extract_hero_meta(blank_file):
    """개념편 frontmatter에서 hero 메타 추출 (editorial-noir 톤 master of slide 스타일)"""
    hero = {'image': None, 'keywords': [], 'subtitle': None, 'eyebrow': None, 'hook': None, 'cards': {}}
    try:
        with open(blank_file, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception:
        return hero
    m = re.match(r'^---\n(.*?)\n---', text, re.S)
    if not m:
        return hero
    fm = m.group(1)
    def get(key):
        # 전체 라인 값을 잡고 바깥쪽 따옴표만 벗긴다 (값 안의 작은따옴표 보존 — hero_hook 등)
        mm = re.search(r'^' + key + r':[ \t]*(.+?)[ \t]*$', fm, re.M)
        if not mm:
            return None
        v = mm.group(1).strip()
        if len(v) >= 2 and v[0] in '"\'' and v[-1] == v[0]:
            quote = v[0]
            v = v[1:-1].strip()
            # ⚠️ 2026-08-28: 큰따옴표로 감싼 YAML 값 안의 \" 를 안 풀어
            #    학생 화면에 백슬래시가 그대로 노출됐다(3-3-1 부제·훅).
            #    바깥 따옴표만 벗기고 끝내면 안 된다.
            if quote == '"':
                v = v.replace('\\"', '"').replace('\\\\', '\\')
        return v or None
    hero['image'] = get('hero_image')
    hero['subtitle'] = get('hero_subtitle') or get('교과서')
    hero['eyebrow'] = get('hero_eyebrow') or get('subject')
    hero['hook'] = get('hero_hook')
    mm = re.search(r'^hero_keywords:\s*\[([^\]]+)\]', fm, re.M)
    if mm:
        hero['keywords'] = [k.strip().strip('"\'') for k in mm.group(1).split(',')]
    else:
        mm = re.search(r'^hero_keywords:\s*\n((?:\s+-\s+.+\n)+)', fm, re.M)
        if mm:
            hero['keywords'] = [l.strip().lstrip('- ').strip().strip('"\'') for l in mm.group(1).strip().split('\n')][:5]
    # 2026-08-24: 본문 '## 🔖 키워드 카드' 섹션 → 칩별 개념 카드(아코디언).
    # 형식: '### 1' ~ '### 6' (hero_keywords 순번과 1:1). 없으면 조용히 skip.
    cm = re.search(r'^##\s*🔖\s*키워드 카드\s*$(.*?)(?=^##\s|\Z)', text, re.S | re.M)
    if cm:
        for bm in re.finditer(r'^###\s*(\d)\s*$\n(.*?)(?=^###\s*\d\s*$|\Z)', cm.group(1), re.S | re.M):
            md = bm.group(2).strip()
            if md:
                hero['cards'][bm.group(1)] = md_to_html(md)

    return hero


def build_hero_html(title, hero):
    if not any([hero.get('keywords'), hero.get('image'), hero.get('hook')]):
        return ''
    eyebrow = f'<div class="hero-eyebrow">{hero["eyebrow"]}</div>' if hero.get('eyebrow') else ''
    sub = f'<p class="hero-subtitle">{hero["subtitle"]}</p>' if hero.get('subtitle') else ''
    # 2026-08-24: 키워드 칩 클릭 → 개념 카드 펼침(아코디언).
    # 카드가 없으면 이전과 100% 동일한 <span>을 낸다(회귀 0).
    cards = hero.get('cards') or {}
    _kw = []
    for i, k in enumerate(list(hero.get('keywords') or [])[:6], 1):
        if str(i) in cards:
            _kw.append(f'<button type="button" class="hero-keyword has-card" data-card="{i}" aria-expanded="false">{k}<span class="kw-caret">＋</span></button>')
        else:
            _kw.append(f'<span class="hero-keyword">{k}</span>')
    kws = ''.join(_kw)
    card_html = ''.join(
        f'<div class="hero-card" id="hero-card-{i}" hidden><div class="hero-card-inner">{h}</div></div>'
        for i, h in sorted(cards.items(), key=lambda kv: int(kv[0])))
    kws_html = f'<div class="hero-keywords">{kws}</div>{card_html}' if kws else ''
    img = f'<img class="hero-image" src="{hero["image"]}" alt="">' if hero.get('image') else ''
    hook = f'<div class="hero-hook">{hero["hook"]}</div>' if hero.get('hook') else ''
    return f'<section class="hero-section">{eyebrow}<h1 class="hero-title">{title}</h1>{sub}{kws_html}{img}{hook}</section>'


def generate_html(title, content, total, total_ox, submit_url='', mode='class', hero=None, exam=False,
                  n_classes=6, n_numbers=35):
    # ⭐ 2026-08-27: 반·번호를 자유 입력 → 드롭다운으로. 오기(誤記)를 원천 차단한다.
    #   근거: 6/25 채점 로그 — "온라인 0건" 15명이 실제로는 12명(3명이 남의 번호로 오기 제출),
    #         번호 오기 4건, 3-3반 1번에 두 명, 이름 칸에 "23" 입력. roster_match.py는 사후 교정이라
    #         *미제출 명단이 부풀어* 있는 상태로 대장에 한 번 올라간다.
    #   ⚠️ 이름은 자유 입력 유지 — 명렬표를 공개 HTML에 넣으면 학생 실명이 GitHub Pages에 노출된다.
    cls_opts = ''.join(f'<option value="{i}">{i}반</option>' for i in range(1, n_classes + 1))
    num_opts = ''.join(f'<option value="{i}">{i}번</option>' for i in range(1, n_numbers + 1))
    """mode: 'class' = 수업용(제출O, 정답보기X), 'review' = 복습용(제출X, 정답보기O)
    exam: 평가지 모드 — localStorage 키를 반-번호에 묶음 (공용 노트북 잔존 방지·6/12)"""
    exam_js = 'true' if exam else 'false'
    grand_total = total + total_ox
    hero_html = build_hero_html(title, hero or {})
    # ⚠️ 2026-08-28: hero(표지)가 있으면 본문 첫 <h1>이 같은 제목을 한 번 더 찍는다.
    #    표지 이미지 안에도 제목이 그려져 있어 학생 화면에서 제목이 최대 세 번 나왔다.
    #    hero가 있을 때만, 그리고 hero 제목과 내용이 같을 때만 본문 h1을 접는다(다른 제목은 보존).
    if hero_html:
        def _plain(x):
            return re.sub(r'\s+', '', re.sub(r'<[^>]+>', '', x))
        m_h1 = re.search(r'<h1>(.*?)</h1>\s*', content, re.S)
        if m_h1 and _plain(m_h1.group(1)) == _plain(title):
            content = content[:m_h1.start()] + content[m_h1.end():]
    if mode == 'teacher':
        # 정답본: 학생 제출용과 같은 레이아웃에 답이 빈칸에 기입된 모습(reveal 느낌) + 모범답안·해설·이미지 포함.
        # 수업 중 이걸 띄워놓고 학생은 제출용을 작성. '교사용 정답본' 같은 명명·경고 라벨 X (v3.2).
        top_bar = ('<div class="control-bar"><div></div>'
                   '<div><a href="https://zzobakg-boop.github.io/worksheets/" class="btn btn-secondary" style="text-decoration:none;">📋 목록</a></div></div>')
    else:
        reveal_btn = '<button class="btn btn-secondary" onclick="reveal()">정답 보기</button>' if mode == 'review' else ''
        submit_btn = '<button class="btn btn-primary" onclick="submitResult()" id="submitBtn">📤 제출</button>' if mode == 'class' else ''
        # 📋 목록(허브) 링크 — 학생 제출용(class)엔 X (이탈·딴 학습지 답 열람 방지·6/8 천대현). 복습용엔 유지.
        list_btn = '' if mode == 'class' else '<a href="https://zzobakg-boop.github.io/worksheets/" class="btn btn-secondary" style="text-decoration:none;">📋 목록</a>'
        # 자동 채점 대상(빈칸·OX)이 없으면(서술형 수행평가 등) 점수칸·채점 버튼 숨김 — NaN% 방지 (6/8)
        scorable = grand_total > 0
        score_block = (f'''<div class="score">
      빈칸: <span id="score">0</span>/{total} · OX: <span id="ox-score">0</span>/{total_ox}
      · 총: <span id="total-score">0</span>/{grand_total} (<span id="pct">0</span>%)
    </div>''' if scorable else '<div></div>')
        check_btn = '<button class="btn btn-primary" onclick="check()">채점하기</button>' if scorable else ''
        top_bar = f'''<div class="control-bar">
    {score_block}
    <div>
      {list_btn}
      {check_btn}
      {reveal_btn}
      <button class="btn btn-danger" onclick="reset()">초기화</button>
      <button class="btn btn-secondary" onclick="saveProgress()">💾 저장</button>
      {submit_btn}
    </div>
  </div>
  <div class="student-info">
    <select id="si-cls"><option value="">반</option>{cls_opts}</select>
    <select id="si-num"><option value="">번호</option>{num_opts}</select>
    <input type="text" id="si-name" placeholder="이름">
  </div>'''
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}{' (복습용)' if mode == 'review' else ''}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: 'Pretendard', -apple-system, 'Noto Sans KR', sans-serif;
  background: #f5f5f7; color: #1d1d1f; line-height: 1.7; padding: 16px;
}}
.container {{
  max-width: 800px; margin: 0 auto; background: white;
  border-radius: 16px; padding: 32px;
  box-shadow: 0 2px 20px rgba(0,0,0,0.08);
}}
h1 {{ font-size: 1.5em; margin: 20px 0 12px; color: #1d1d1f; border-bottom: 2px solid #007aff; padding-bottom: 8px; }}
h2 {{
  font-size: 1.3em; margin: 30px 0 12px; color: #1d1d1f; font-weight: 800;
  letter-spacing: -0.01em; padding: 8px 0 8px 14px; border-left: 6px solid #007aff;
  background: linear-gradient(90deg, #f2f6ff, rgba(255,255,255,0));
  border-radius: 0 8px 8px 0;
}}
h2:first-of-type {{ margin-top: 14px; }}
h3 {{
  font-size: 1.09em; margin: 22px 0 8px; color: #2b3240; font-weight: 750;
  padding-left: 11px; border-left: 3px solid #b6c4dc;
}}
h4 {{ font-size: 1em; margin: 10px 0 6px; color: #666; }}
p {{ margin: 5px 0; font-size: 0.95em; }}
hr {{ border: none; border-top: 1px solid #eee; margin: 16px 0; }}
table {{
  width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 0.9em;
}}
/* ⭐ 6/18: 활동 입력칸이 든 표는 내용 폭으로 (짧은 칸이 넓은 셀에 떠 보이는 비율 깨짐 방지·21-22 사고) */
table.act-table {{ width: auto; max-width: 100%; }}
table.act-table .activity-input {{ max-width: 100%; }}
td {{ border: 1px solid #e2e6ec; padding: 10px 12px; vertical-align: middle; line-height: 1.6; }}
tr:first-child td {{
  background: #e8eefb; font-weight: 750; color: #22314e; vertical-align: middle;
  border-color: #cfd9ec; font-size: 0.96em;
}}
tbody tr:nth-child(even):not(:first-child) td {{ background: #fcfdff; }}
table {{ border-radius: 10px; overflow: hidden; }}
.ws-fold {{
  margin: 12px 0; border: 1px solid #d8d2c4; border-left: 4px solid #7a8f6a;
  border-radius: 8px; background: #fbfaf6; overflow: hidden;
}}
.ws-fold > summary {{
  cursor: pointer; padding: 11px 14px; font-weight: 700; color: #4a5c40;
  background: #f1efe6; list-style: none; user-select: none; font-size: 0.95em;
}}
.ws-fold > summary::-webkit-details-marker {{ display: none; }}
.ws-fold > summary::before {{ content: "▸ "; color: #7a8f6a; }}
.ws-fold[open] > summary::before {{ content: "▾ "; }}
.ws-fold[open] > summary {{ border-bottom: 1px solid #e2ddd0; }}
.ws-fold-body {{ padding: 10px 16px 14px; }}
.ws-fold-body p {{ margin: 6px 0; color: #3a352c; font-size: 0.94em; line-height: 1.7; }}
blockquote {{
  border-left: 3px solid #007aff; padding: 6px 14px; margin: 6px 0;
  background: #f8f9ff; border-radius: 0 8px 8px 0; font-size: 0.93em;
}}
/* 🎮 인물 선택 활동 — 2026-09-03. 표를 정답으로 주지 않고 학생이 고르게 한다.
   캐릭터 선택 화면의 결: 고르기 전엔 흐리고, 고르면 색이 들어온다. */
.ws-pick {{ border: 1px solid #dfe3e8; border-radius: 14px; background: #fbfcfd; padding: 16px; margin: 18px 0; }}
.pk-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 10px;
  font-size: 0.94em; font-weight: 700; color: #3d4552; margin-bottom: 12px; }}
.pk-count {{ color: #c62c3c; white-space: nowrap; }}
.pk-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }}
@media (max-width: 640px) {{ .pk-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
.ws-voc {{ width:100%; border-collapse:collapse; margin:10px 0; font-size:0.94em; }}
.ws-voc th {{ background:#f2f4f8; color:#42505f; font-weight:700; padding:9px 12px;
              border:1px solid #dfe4ea; text-align:left; font-size:0.9em; }}
.ws-voc td {{ padding:9px 12px; border:1px solid #dfe4ea; vertical-align:top; }}
.vc-btn {{ background:none; border:0; padding:0; font:inherit; font-weight:700; color:#1c2b3a;
           cursor:pointer; text-align:left; }}
.vc-btn::before {{ content:"▸ "; color:#7a8f6a; }}
.vc-btn[aria-expanded="true"]::before {{ content:"▾ "; }}
.vc-btn:hover {{ color:#0b57d0; }}
.vc-btn:focus-visible {{ outline:2px solid #0b57d0; outline-offset:2px; border-radius:3px; }}
.vc-body td {{ background:#fbfaf5; }}
.vc-body p {{ margin:4px 0; color:#3a352c; line-height:1.65; }}
.pk-card {{ border: 2px solid #e2e6ec; border-radius: 12px; background: #fff; padding: 10px 8px;
  text-align: center; transition: transform .22s ease-out, box-shadow .22s, background .22s, border-color .15s; }}
.pk-card img {{ transition: filter .22s; }}
.pk-card img {{ width: 72px; height: 72px; image-rendering: pixelated;
  filter: grayscale(1) opacity(.45); transition: .15s; }}
.pk-card.pk-set img {{ filter: none; }}
.pk-card.pk-set {{ border-color: #9aa4b2; background: #fdfdfe; }}
.pk-name {{ font-weight: 800; font-size: 0.9em; margin-top: 2px; color: #1c242f; }}
.pk-sit {{ font-size: 0.78em; color: #6b7482; line-height: 1.5; margin: 3px 0 8px; min-height: 2.2em; }}
.pk-btns {{ display: flex; gap: 5px; }}
.pk-b {{ flex: 1; border: 1.5px solid #d5dae1; background: #fff; border-radius: 8px;
  padding: 6px 2px; font: inherit; font-size: 0.78em; font-weight: 700; color: #55607a; cursor: pointer; }}
.pk-b:hover {{ background: #f3f6fa; }}
.pk-b.on {{ background: #1c242f; border-color: #1c242f; color: #fff; }}
/* 🙂 기분 상태 — 고르면 캐릭터가 웃거나 운다 (2026-09-03).
   새 그림을 그리지 않는다: 카드가 뜨거나 내려앉고, 색온도와 채도가 바뀌고, 배지가 붙는다.
   정답 공개 때 틀린 카드는 '진짜 기분'으로 뒤집히므로 표정 변화 자체가 피드백이 된다. */
.pk-card {{ position: relative; }}
.pk-card.pk-happy {{
  transform: translateY(-10px) scale(1.04);
  border-color: #e0b13a;
  box-shadow: 0 12px 22px rgba(200,150,30,.28), 0 0 0 3px rgba(255,214,102,.35);
  background: linear-gradient(180deg, #fff9e2, #fff);
  animation: pkHop .5s cubic-bezier(.34,1.56,.64,1);
}}
.pk-card.pk-happy img {{ filter: brightness(1.16) saturate(1.45) contrast(1.06); transform: scale(1.1); }}
.pk-card.pk-sad {{
  transform: translateY(9px) scale(.95) rotate(1.6deg);
  border-color: #93a3bb;
  box-shadow: 0 1px 3px rgba(60,70,90,.10);
  background: linear-gradient(180deg, #eef1f6, #f8fafc);
  animation: pkSlump .45s ease-out;
}}
.pk-card.pk-sad img {{
  filter: saturate(.22) brightness(.84) contrast(.92) hue-rotate(-14deg);
  transform: scale(.9) rotate(-2deg);
}}
.pk-card.pk-sad .pk-name, .pk-card.pk-sad .pk-sit {{ opacity: .62; }}
@keyframes pkHop {{
  0%   {{ transform: translateY(0) scale(1); }}
  45%  {{ transform: translateY(-20px) scale(1.09); }}
  100% {{ transform: translateY(-10px) scale(1.04); }}
}}
@keyframes pkSlump {{
  0%   {{ transform: translateY(0) scale(1) rotate(0); }}
  60%  {{ transform: translateY(13px) scale(.93) rotate(2.4deg); }}
  100% {{ transform: translateY(9px) scale(.95) rotate(1.6deg); }}
}}
.pk-card.pk-happy::after, .pk-card.pk-sad::after {{
  position: absolute; top: -12px; right: -8px; font-size: 1.9em; line-height: 1;
  filter: drop-shadow(0 2px 3px rgba(0,0,0,.22));
}}
.pk-card.pk-happy::after {{ content: "😀"; animation: pkPop .45s cubic-bezier(.34,1.8,.64,1); }}
.pk-card.pk-sad::after {{ content: "😢"; animation: pkDrip .45s ease-out; }}
@keyframes pkPop {{ 0% {{ transform: scale(0) rotate(-30deg); }} 100% {{ transform: scale(1) rotate(0); }} }}
@keyframes pkDrip {{ 0% {{ transform: translateY(-10px) scale(.4); opacity: 0; }} 100% {{ transform: none; opacity: 1; }} }}
@media (prefers-reduced-motion: reduce) {{
  .pk-card.pk-happy, .pk-card.pk-sad {{ transform: none; animation: none; }}
  .pk-card.pk-happy::after, .pk-card.pk-sad::after {{ animation: none; }}
}}
@media print {{
  .pk-card.pk-happy, .pk-card.pk-sad {{ transform: none; box-shadow: none; animation: none; }}
  .pk-card.pk-happy img, .pk-card.pk-sad img {{ transform: none; }}
}}

.pk-card.pk-ok {{ border-color: #1a7a60; background: #f2fbf7; }}
.pk-card.pk-no {{ border-color: #c62c3c; background: #fef5f6; }}
.pk-why {{ font-size: 0.78em; color: #b3242f; margin-top: 7px; line-height: 1.55; text-align: left; }}
.pk-result {{ margin-top: 14px; padding: 13px 15px; border: 1px solid #1a7a60;
  background: #e4f4ee; border-radius: 12px; font-size: 0.9em; color: #15705a; }}
.pk-sum {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(148px, 1fr)); gap: 10px; margin-top: 10px; }}
@media (max-width: 520px) {{ .pk-sum {{ grid-template-columns: 1fr; }} }}
.pk-col {{ background: #fff; border-radius: 10px; padding: 9px 11px; border: 1.5px solid; }}
.pk-col b {{ display: block; margin-bottom: 5px; font-size: 0.95em; }}
.pk-col span {{ display: block; font-size: 0.9em; color: #3d4552; padding: 1px 0; }}
.pk-up {{ border-color: #1a7a60; color: #15705a; }}
.pk-down {{ border-color: #c62c3c; color: #b3242f; }}
/* N지선다(기분 없음) 요약 열 — 옵션 순서대로 색이 갈린다 */
code {{ background: #f1f3f7; border: 1px solid #e2e6ec; border-radius: 5px;
  padding: 1px 5px; font-size: .92em; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: #384a63; }}
.pk-c0 {{ border-color: #1f6feb; color: #1a5fc8; }}
.pk-c1 {{ border-color: #b8862b; color: #9a6f1e; }}
.pk-c2 {{ border-color: #6b4fbb; color: #5b41a4; }}
.pk-c3 {{ border-color: #1a7a60; color: #15705a; }}
/* 옵션이 3개 이상이면 버튼을 세로로 — 가로로 늘어놓으면 폰에서 글자가 잘린다 */
.pk-btns-col {{ flex-direction: column; gap: 4px; }}
.pk-btns-col .pk-b {{ width: 100%; text-align: center; }}
/* 이미지 없는 카드(실재 사건 등 — 생성 이미지를 쓰지 않는 자리) */
/* 인물선택 '카드' 결 (2026-09-07) — :::인물선택카드 일 때만. 옛 차시는 그대로 */
.pk-gold .pk-card {{ padding: 7px; border: 0; border-radius: 15px;
  background: linear-gradient(150deg, #fbe9a8 0%, #e7c257 34%, #c9992e 62%, #f3dc98 100%);
  box-shadow: 0 3px 9px rgba(0,0,0,.18); }}
.pk-gold .pk-card {{ display: flex; flex-direction: column; gap: 0; }}
.pk-gold .pk-win {{ display: block; overflow: hidden; border-radius: 5px 5px 0 0;
  border: 4px solid #d9c98e; border-bottom: 0; background: #efe7cf; margin: 0; }}
/* 도트 스프라이트용 규칙(72px·pixelated·grayscale)이 사진 카드에 걸리면
   고르기 전에는 사진이 안 보인다 — 사진에는 단서가 있어야 한다. */
.pk-gold .pk-win img {{ image-rendering: auto; filter: none; height: auto; }}
.pk-gold .pk-win img {{ display: block; width: 100%; aspect-ratio: 4/3; object-fit: cover; }}
.pk-gold .pk-name {{ background: #fdf7e6; margin: 0; padding: 10px 10px 0;
  font-size: 1.06em; font-weight: 800; color: #2c2419; }}
.pk-gold .pk-sit {{ background: #fdf7e6; margin: 0; padding: 5px 10px 8px;
  font-size: .87em; line-height: 1.5; color: #574d3c; font-style: italic; }}
.pk-gold .pk-btns {{ background: #fdf7e6; margin: 0; padding: 0 10px 10px;
  border-radius: 0 0 10px 10px; }}
.pk-gold .pk-why {{ background: #fdf7e6; margin: 0; padding: 0 10px 10px;
  border-radius: 0 0 10px 10px; }}
.pk-gold .pk-card.pk-ok {{ box-shadow: 0 0 0 4px #4a9d5f, 0 10px 22px rgba(74,157,95,.4); }}
.pk-gold .pk-card.pk-no {{ box-shadow: 0 0 0 4px #c9584f, 0 10px 22px rgba(201,88,79,.4); }}
.pk-card.pk-noimg {{ padding-top: 14px; }}
.pk-card.pk-noimg .pk-name {{ font-size: 1.02em; }}
@media print {{ .pk-b {{ display: none; }} .pk-card img {{ filter: none; }} }}

/* ⚖️ 움직이는 시소 — 2026-09-03. 정지 도식이 못 주는 것: 학생이 직접 밀어 보는 것. */
.ws-seesaw {{
  border: 1px solid #dfe3e8; border-radius: 14px; background: #fbfcfd;
  padding: 16px 18px 18px; margin: 18px 0;
}}
.ws-seesaw-head {{ font-size: 0.9em; font-weight: 700; color: #4a5361; margin-bottom: 10px; }}
.ws-seesaw-range {{ width: 100%; accent-color: #c62c3c; margin-bottom: 6px; }}
.ws-seesaw-stage {{ position: relative; height: 190px; }}
.ws-seesaw-beam {{
  position: absolute; left: 50%; top: 50%; width: 500px; height: 10px;
  margin-left: -250px; margin-top: -5px; background: #7b8494; border-radius: 5px;
  transition: transform .18s ease-out;
}}
.ws-seesaw-pivot {{
  position: absolute; left: 50%; top: 50%; margin-left: -26px;
  border-left: 26px solid transparent; border-right: 26px solid transparent;
  border-top: 52px solid #96a0ae;
}}
.ws-seesaw-chip {{
  position: absolute; top: 50%; width: 168px; padding: 9px 6px;
  text-align: center; border-radius: 12px; border: 3px solid; background: #fff;
  transition: transform .18s ease-out; font-size: 0.88em;
}}
.ws-seesaw-chip b {{ display: block; font-size: 0.95em; }}
.ws-seesaw-chip .v {{ display: block; font-size: 1.45em; font-weight: 800; margin-top: 2px; }}
.ws-seesaw-chip.ws-l {{ left: 50%; margin-left: -334px; border-color: #c62c3c; color: #c62c3c; }}
.ws-seesaw-chip.ws-r {{ left: 50%; margin-left: 166px; border-color: #1e5ca8; color: #1e5ca8; }}
.ws-seesaw-note {{
  text-align: center; font-size: 0.84em; color: #6b7482; margin: 0 0 8px;
}}
.ws-seesaw-out {{
  text-align: center; font-size: 1.02em; font-weight: 700; color: #15705a;
  background: #e0f3ec; border: 1px solid #1a7a60; border-radius: 10px; padding: 9px;
}}
@media (max-width: 560px) {{
  .ws-seesaw-beam {{ width: 300px; margin-left: -150px; }}
  .ws-seesaw-chip {{ width: 124px; font-size: 0.8em; }}
  .ws-seesaw-chip.ws-l {{ margin-left: -206px; }}
  .ws-seesaw-chip.ws-r {{ margin-left: 82px; }}
}}
@media print {{ .ws-seesaw-range {{ display: none; }} }}

/* 🕰 연표 시소 (:::연표시소) — 2026-09-09.
   🔴 기존 정지 도식(fig_232_reversal_anim.py)의 «결»을 그대로 옮긴다 —
      크림 바탕 · 교황 보라(#7a4a84) · 상대 적갈(#964e2c) · 도트 스프라이트 ·
      줄에 매단 접시 · 사다리꼴 기둥 · **저울 아래 연표 트랙**.
      새로 만든 회색·남색 UI로 갈아엎었더니 학습지 결에서 튀었다(천대현 2026-09-09). */
.ws-tl {{ border: 1px solid #e4dcc9; border-radius: 14px; background: #faf7f0;
  padding: 16px 18px 14px; margin: 18px 0; }}
.ws-tl-head {{ font-size: 0.9em; font-weight: 700; color: #786c5c; margin-bottom: 6px; }}
.ws-tl-stage {{ position: relative; height: 300px; }}
.ws-tl-beam {{ position: absolute; left: 50%; top: 70px; width: 460px; height: 12px;
  margin-left: -230px; background: #8c8070; border-radius: 6px;
  transition: transform .28s ease-out; }}
.ws-tl-pivot {{ position: absolute; left: 50%; top: 74px; margin-left: -14px;
  border-left: 14px solid transparent; border-right: 14px solid transparent;
  border-top: 122px solid #c6bAaa; }}
.ws-tl-base {{ position: absolute; left: 50%; top: 192px; width: 200px; margin-left: -100px;
  height: 8px; background: #b2a694; border-radius: 4px; }}
/* 🔴 칩 top = 빔top + 최대하강(sin9°×half≈36) — 그래야 접시가 «항상 빔 아래»에 있다.
   빔top에 두면 위로 기운 쪽 접시가 빔 위로 떠올라 저울로 안 보인다(2026-09-09 실측). */
.ws-tl-chip {{ position: absolute; left: 50%; top: 106px; width: 190px; text-align: center;
  transition: transform .28s ease-out; }}
.ws-tl-chip .rope {{ display: block; width: 3px; height: 40px; margin: 0 auto; background: #b9ad9b; }}
.ws-tl-chip .box {{ display: block; background: #fff; border: 3px solid #b9ad9b; border-radius: 12px;
  padding: 6px 8px 8px; }}
.ws-tl-chip .tl-spr {{ display: block; height: 52px; width: auto; margin: 0 auto 2px;
  image-rendering: pixelated; }}
.ws-tl-chip b {{ display: block; font-size: 0.95em; font-weight: 800; }}
.ws-tl-chip .s {{ display: block; font-size: 0.78em; color: #9a9284; margin-top: 1px; }}
.ws-tl-chip .win {{ display: block; margin-top: 4px; font-size: 0.8em; font-weight: 800;
  visibility: hidden; }}
.ws-tl-chip.tl-l {{ margin-left: -300px; }}
.ws-tl-chip.tl-r {{ margin-left: 110px; }}
/* 교황 = 보라 · 상대 = 적갈 (기존 도식 CH·KING 그대로) */
.ws-tl-chip.tl-l .box {{ border-color: #7a4a84; }} .ws-tl-chip.tl-l b, .ws-tl-chip.tl-l .win {{ color: #7a4a84; }}
.ws-tl-chip.tl-l .rope {{ background: #7a4a84; }}
.ws-tl-chip.tl-r .box {{ border-color: #964e2c; }} .ws-tl-chip.tl-r b, .ws-tl-chip.tl-r .win {{ color: #964e2c; }}
.ws-tl-chip.tl-r .rope {{ background: #964e2c; }}
.ws-tl-chip.up .box {{ opacity: .6; }}
.ws-tl-say {{ min-height: 2.6em; margin: 2px 0 10px; font-size: 0.94em; color: #4a4136;
  line-height: 1.7; text-align: center; font-weight: 600; }}
/* 시간축 — 기존 도식처럼 «저울 아래»에 둔다(천대현 원 요청: "밑에 표시한 연도를 클릭") */
.ws-tl-tabs {{ display: flex; align-items: flex-start; justify-content: space-between;
  gap: 4px; border-top: 3px solid #e0d6c2; padding-top: 0; margin-top: 4px; }}
.tl-tab {{ flex: 1 1 0; border: 0; background: none; cursor: pointer; font-family: inherit;
  font-size: 0.84em; color: #9a9284; padding: 0; position: relative; }}
.tl-tab::before {{ content: ""; display: block; width: 13px; height: 13px; border-radius: 50%;
  background: #d8cdb8; margin: -8px auto 5px; border: 3px solid #faf7f0; }}
.tl-tab[aria-selected="true"] {{ color: #262018; font-weight: 800; }}
.tl-tab[aria-selected="true"]::before {{ background: #b07e1a; }}
.tl-print {{ display: none; }}
@media (max-width: 560px) {{
  .ws-tl {{ padding: 14px 10px 12px; }}
  .ws-tl-stage {{ height: 250px; }}
  .ws-tl-beam {{ width: 216px; margin-left: -108px; top: 56px; height: 9px; }}
  .ws-tl-pivot {{ top: 60px; margin-left: -11px; border-left-width: 11px; border-right-width: 11px;
    border-top-width: 100px; }}
  .ws-tl-base {{ top: 156px; width: 58px; margin-left: -29px; height: 6px; }}
  .ws-tl-chip {{ width: 122px; top: 73px; }}
  .ws-tl-chip.tl-l {{ margin-left: -152px; }}
  .ws-tl-chip.tl-r {{ margin-left: 30px; }}
  .ws-tl-chip .rope {{ height: 30px; }}
  .ws-tl-chip .tl-spr {{ height: 40px; }}
  .ws-tl-chip b {{ font-size: 0.8em; }} .ws-tl-chip .s {{ font-size: 0.68em; }}
  .ws-tl-say {{ min-height: 4.8em; font-size: 0.88em; }}
  .tl-tab {{ font-size: 0.72em; }}
}}
@media print {{
  .ws-tl-tabs, .ws-tl-stage, .ws-tl-say {{ display: none; }}
  .tl-print {{ display: table; width: 100%; }}
}}

/* 📖 표·도식을 읽는 자리 — 2026-09-03.
   빈칸 본문(파랑 입력)과도, 곁말 콜아웃(왼쪽 파란 띠)과도 갈라야 하는 세 번째 계열.
   표 바로 아래 붙여 '표의 일부'로 읽히게 한다(위 모서리를 각지게·음수 마진). */
/* 🔴 2026-09-10 재설계 — 두 가지가 틀려 있었다.
   ① 이 블록의 CSS가 «죽어 있었다» — 바로 위 :::연표시소 CSS에 여분의 `}}`가 하나 있어
      파서가 .ws-read 본체 규칙을 버렸다(자식 규칙 3개는 살아남아 더 안 보였다).
      computed backgroundColor 가 rgba(0,0,0,0) 이었다. 천대현: "일반 설명과 다르게 디자인을 가져가자"
      — 디자인이 약한 게 아니라 **없었다.**
   ② «표 바로 아래 붙는다»는 원 설계(2026-09-03)가 실사용과 달랐다. 실측하니 사회② 8차시
      16개 블록의 직전 형제가 전부 h2 또는 br 이고 **표 뒤인 경우가 0**이었다.
      음수 마진과 각진 위 모서리가 근거를 잃었으므로 단독형으로 바로잡는다.
   계열: 파랑=답이 나오는 곳 · 황토=교과서 · **슬레이트=손 안 대고 읽는 곳**.
   태그는 :::교과서와 같은 알약형으로 올려 «일반 문단이 아님»이 한눈에 보이게 한다. */
.ws-read {{
  background: #eceef2; border: 1px solid #cfd5de; border-left: 6px solid #64748b;
  border-radius: 0 10px 10px 0; padding: 12px 18px 15px; margin: 16px 0 20px;
  color: #3a4351; font-size: 0.93em; line-height: 1.78;
}}
.ws-read .ws-read-tag {{
  display: inline-block; background: #64748b; color: #fff;
  font-size: 0.76em; font-weight: 700; letter-spacing: 0.02em;
  padding: 3px 11px; border-radius: 999px; margin-bottom: 9px;
}}
.ws-read p {{ margin: 0 0 7px; font-size: 1em; }}
.ws-read p:last-child {{ margin-bottom: 0; }}
@media print {{ .ws-read {{ background: #fff; border-left-color: #999; }} }}

/* ⚖️ 좌우 비교 넘기기 — 2026-09-03. 좌우 라벨은 고정, 비교 항목만 넘긴다 */
/* 사진 위에 좌석을 얹는다 (2026-09-07) — 사진과 도식을 따로 두면 세로만 길어진다 */
.st-stage {{ position: relative; border-radius: 10px; overflow: hidden; margin: 2px 0 6px; }}
.st-stage.has-bg {{ background-size: cover; background-position: center 42%;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.25); }}
.st-veil {{ position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(ellipse at 50% 52%, rgba(12,10,8,.42) 0%,
    rgba(12,10,8,.68) 55%, rgba(12,10,8,.82) 100%); }}
.st-stage.has-bg .st-svg {{ position: relative; }}
.st-stage.has-bg .st-seat {{ fill: rgba(255,255,255,.30); stroke: rgba(255,255,255,.72);
  filter: drop-shadow(0 3px 4px rgba(0,0,0,.55)); }}
.st-stage.has-bg .st-seat.dim {{ opacity: .3; }}
.st-stage.has-bg .st-seat[data-g="0"].on {{ fill: #d64b42; stroke: #ffd9d5;
  filter: drop-shadow(0 0 9px rgba(255,90,78,.95)) drop-shadow(0 4px 6px rgba(0,0,0,.6)); }}
.st-stage.has-bg .st-seat[data-g="1"].on {{ fill: #7fb4ee; stroke: #e6f2ff;
  filter: drop-shadow(0 0 9px rgba(126,180,238,.95)) drop-shadow(0 4px 6px rgba(0,0,0,.6)); }}
.st-stage.has-bg .st-hub {{ fill: rgba(10,9,8,.55); stroke: rgba(255,255,255,.45); }}
.st-stage.has-bg .st-hub-n {{ fill: #fff; }}
.st-stage.has-bg .st-hub-t {{ fill: rgba(255,255,255,.8); }}
.st-cap {{ font-size: .76em; color: #8a857c; line-height: 1.55; margin: 0 0 10px; }}
/* 🃏 카드 골라 쓰기 (2026-09-07) — 포켓몬 카드 결: 금테 + 이름표 + 창 + 홀로 */
.ws-pk3 {{ margin: 18px 0; }}
.pk3-head {{ font-size: 1.06em; font-weight: 700; color: #22201e; margin-bottom: 10px; }}
.pk3-deck {{ display: grid; gap: 14px;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); }}
.pk3-card {{ display: block; width: 100%; text-align: left; cursor: pointer;
  padding: 7px; border: 0; border-radius: 15px; font: inherit;
  background: linear-gradient(150deg, #fbe9a8 0%, #e7c257 34%, #c9992e 62%, #f3dc98 100%);
  box-shadow: 0 3px 9px rgba(0,0,0,.18);
  transition: transform .18s ease, box-shadow .18s ease, filter .25s ease; }}
.pk3-card:hover {{ transform: translateY(-6px) rotate(-.7deg);
  box-shadow: 0 12px 24px rgba(0,0,0,.24); }}
.pk3-card:focus-visible {{ outline: 3px solid #2b6cb0; outline-offset: 3px; }}
.pk3-in {{ display: block; background: #fdf7e6; border-radius: 10px; padding: 9px 9px 10px; }}
.pk3-top {{ display: flex; align-items: center; justify-content: space-between; gap: 6px;
  margin-bottom: 7px; }}
.pk3-name {{ font-size: 1.14em; font-weight: 800; color: #2c2419; letter-spacing: -.01em; }}
.pk3-badge {{ font-size: .74em; font-weight: 800; color: #fff; padding: 3px 9px;
  border-radius: 999px; white-space: nowrap; }}
.pk3-t0 .pk3-badge {{ background: #a9683c; }}
.pk3-t1 .pk3-badge {{ background: #3f7fc4; }}
.pk3-t2 .pk3-badge {{ background: #c99a12; }}
.pk3-win {{ position: relative; display: block; overflow: hidden; border-radius: 5px;
  border: 4px solid #d9c98e; background: #efe7cf; }}
.pk3-win img {{ display: block; width: 100%; aspect-ratio: 4/3; object-fit: cover; }}
.pk3-holo {{ position: absolute; inset: 0; opacity: 0; pointer-events: none;
  background: repeating-linear-gradient(115deg, rgba(255,90,140,.55) 0 12px,
    rgba(255,220,90,.55) 12px 24px, rgba(110,240,190,.55) 24px 36px,
    rgba(120,170,255,.55) 36px 48px);
  background-size: 240% 240%; mix-blend-mode: color-dodge; transition: opacity .3s; }}
.pk3-cap {{ display: block; margin-top: 8px; font-size: .96em; font-weight: 700; color: #2c2419; }}
.pk3-flavor {{ display: block; margin-top: 5px; font-size: .87em; line-height: 1.5;
  color: #574d3c; font-style: italic; border-top: 1px solid #e2d5ad; padding-top: 6px; }}
.pk3-foot {{ display: block; margin-top: 8px; text-align: center; font-size: .82em;
  font-weight: 800; color: #7a6636; background: #f2e7c4; border-radius: 6px; padding: 5px; }}
.pk3-card.on {{ transform: translateY(-6px) scale(1.03); box-shadow: 0 0 0 4px #e7b625,
  0 14px 30px rgba(201,153,46,.45); }}
.pk3-card.on .pk3-holo {{ opacity: .42; animation: pk3sheen 3.4s linear infinite; }}
.pk3-card.on .pk3-foot {{ background: #c9992e; color: #fff; }}
.pk3-card.dim {{ filter: grayscale(.8); opacity: .45; transform: none; }}
@keyframes pk3sheen {{ 0% {{ background-position: 0% 0%; }} 100% {{ background-position: 240% 0%; }} }}
@media (prefers-reduced-motion: reduce) {{
  .pk3-card, .pk3-card:hover, .pk3-card.on {{ transition: none; transform: none; }}
  .pk3-card.on .pk3-holo {{ animation: none; }} }}
.pk3-ask {{ margin-top: 14px; padding: 13px 15px; border-radius: 10px;
  background: #fbf5e4; border: 2px solid #d9c98e; }}
.pk3-pick {{ font-size: .87em; font-weight: 800; color: #8a7434; margin-bottom: 7px; }}
.pk3-cred {{ margin-top: 8px; font-size: .76em; color: #8a857c; line-height: 1.55; }}
/* 🪑 좌석 구성 눌러 보기 (2026-09-07) — 그림 먼저, 설명은 누를 때만 */
.ws-seat {{ border: 2px solid #cfc4ae; border-radius: 12px; margin: 18px 0;
  padding: 16px 14px 14px; background: #fdfbf7; }}
.st-title {{ font-size: 1.16em; font-weight: 700; color: #22201e; }}
.st-hint {{ font-size: .88em; color: #6e6862; margin: 4px 0 12px; }}
.st-btns {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }}
.st-btn {{ flex: 1 1 180px; padding: 11px 14px; border-radius: 10px; cursor: pointer;
  font-size: 1em; font-weight: 700; background: #fff; transition: transform .12s, box-shadow .12s; }}
.st-btn b {{ font-size: 1.24em; margin-left: 4px; }}
.st-btn.st-red {{ border: 2px solid #b03a34; color: #b03a34; }}
.st-btn.st-blue {{ border: 2px solid #3c608a; color: #3c608a; }}
.st-btn:hover {{ transform: translateY(-2px); }}
.st-btn.st-red.on {{ background: #b03a34; color: #fff; box-shadow: 0 4px 12px rgba(176,58,52,.35); }}
.st-btn.st-blue.on {{ background: #3c608a; color: #fff; box-shadow: 0 4px 12px rgba(60,96,138,.35); }}
.st-svg {{ display: block; width: 100%; max-width: 520px; margin: 2px auto 6px; }}
.st-hub {{ fill: #f0ebe4; stroke: #cec6bc; stroke-width: 2; }}
.st-hub-n {{ font-size: 34px; font-weight: 700; fill: #22201e; }}
.st-hub-t {{ font-size: 16px; fill: #6e6862; }}
.st-seat {{ fill: #e6e1d9; stroke: #b9b1a6; stroke-width: 2.5;
  transition: fill .28s, stroke .28s, opacity .28s, r .28s; }}
.st-seat.dim {{ opacity: .22; }}
.st-seat[data-g="0"].on {{ fill: #b03a34; stroke: #8d2a25; r: 18; }}
.st-seat[data-g="1"].on {{ fill: #d8e2ee; stroke: #3c608a; r: 18; }}
.st-cards {{ min-height: 108px; }}
.st-card {{ border-radius: 10px; padding: 13px 15px; }}
.st-card.st-red {{ background: #f6eeec; border: 2px solid #b03a34; }}
.st-card.st-blue {{ background: #eaf0f7; border: 2px solid #3c608a; }}
.st-card-h {{ font-size: 1.1em; font-weight: 700; margin-bottom: 7px; }}
.st-card.st-red .st-card-h {{ color: #b03a34; }}
.st-card.st-blue .st-card-h {{ color: #3c608a; }}
.st-card-h span {{ float: right; font-weight: 700; }}
.st-card-i {{ font-size: 1em; color: #22201e; margin-bottom: 5px; }}
.st-card-d {{ font-size: .95em; color: #55504a; }}
.st-note {{ margin-top: 12px; padding: 12px 15px; border-radius: 10px;
  background: #fff4e8; border: 2px solid #c98a3c; font-weight: 700; color: #22201e; }}
@media (max-width: 640px) {{ .st-btn {{ flex: 1 1 100%; }} }}
.ws-cmp {{ border: 2px solid #cfc4ae; border-radius: 12px; margin: 18px 0;
  background: #fbf9f4; overflow: hidden; }}
.ws-cmp-head {{ display: flex; }}
.ws-cmp-head span {{ flex: 1; text-align: center; padding: 9px 6px; font-weight: 700;
  font-size: .95em; color: #fff; background: #8a7a5c; }}
.ws-cmp-head span:first-child {{ background: #9a7b3c; }}
.ws-cmp-head span:last-child {{ background: #5b6b8a; }}
.ws-cmp-tabs {{ display: flex; gap: 6px; flex-wrap: wrap; padding: 9px 10px 4px; }}
.ws-cmp-tab {{ border: 1px solid #cfc4ae; background: #fff; color: #6b5a3a;
  border-radius: 999px; padding: 4px 12px; font-size: .82em; cursor: pointer; font-family: inherit; }}
.ws-cmp-tab.on {{ background: #6b5a3a; color: #fff; border-color: #6b5a3a; }}
.ws-cmp-stage {{ padding: 4px 10px 0; }}
.ws-cmp-slide {{ display: flex; gap: 12px; align-items: flex-start; }}
/* 🔴 CSS display가 HTML hidden 속성을 이긴다 — 이 한 줄이 없으면 모든 슬라이드가 한꺼번에 보인다.
   (gallery는 slide에 display를 안 줘서 이 문제가 없었다) */
.ws-cmp-slide[hidden] {{ display: none; }}
.ws-cmp-slide figure {{ flex: 1 1 0; min-width: 0; margin: 0; text-align: center; }}
.ws-cmp-slide img {{ width: 100%; max-height: 300px; height: auto; object-fit: contain;
  border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,.12); }}
.ws-cmp-slide figcaption {{ margin-top: 6px; font-size: .76em; color: #5b5040; line-height: 1.45; }}
.ws-cmp-nav {{ display: flex; align-items: center; justify-content: center; gap: 14px;
  padding: 8px 0 10px; }}
.ws-cmp-nav button {{ border: 1px solid #cfc4ae; background: #fff; color: #6b5a3a;
  border-radius: 8px; padding: 4px 12px; font-size: .84em; cursor: pointer; font-family: inherit; }}
.ws-cmp-count {{ font-size: .8em; color: #8a7a5c; }}
@media (max-width: 520px) {{ .ws-cmp-slide img {{ max-height: 190px; }} }}
@media print {{ .ws-cmp-slide[hidden] {{ display: flex !important; }} }}  /* 인쇄엔 전부 편다 */

/* 🃏 뒤집는 카드 — 2026-09-03. 앞면=개념 / 뒷면=그 개념의 얼굴(실제 인물·사료) */
.ws-flip-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 18px 0; }}
.ws-flip {{ flex: 1 1 160px; min-width: 150px; max-width: 260px; height: 232px;
  perspective: 900px; background: none; border: 0; padding: 0; cursor: pointer;
  font-family: inherit; -webkit-tap-highlight-color: transparent; }}
.ws-flip-in {{ position: relative; display: block; width: 100%; height: 100%;
  transition: transform .55s cubic-bezier(.4,.2,.2,1); transform-style: preserve-3d; }}
.ws-flip.on .ws-flip-in {{ transform: rotateY(180deg); }}
.ws-flip:focus-visible .ws-flip-in {{ outline: 3px solid #8a5f12; outline-offset: 3px; }}
.ws-flip-f, .ws-flip-b {{ position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 6px; padding: 12px;
  border-radius: 12px; backface-visibility: hidden; -webkit-backface-visibility: hidden;
  box-sizing: border-box; overflow: hidden; }}
.ws-flip-f {{ background: #f3f0e8; border: 2px solid #cfc4ae; }}
.ws-flip-f b {{ font-size: 1.15em; color: #3d3116; }}
.ws-flip-f i {{ font-style: normal; font-size: .84em; color: #6b5a3a; text-align: center; line-height: 1.4; }}
.ws-flip-f u {{ text-decoration: none; font-size: .74em; color: #a08a5c; margin-top: 6px; }}
.ws-flip-b {{ background: #fffdf6; border: 2px solid #b8862b; transform: rotateY(180deg); justify-content: flex-start; }}
.ws-flip-b img {{ width: 100%; height: 136px; object-fit: cover; border-radius: 7px; }}
.ws-flip-b i {{ font-style: normal; font-size: .76em; color: #4a3f2a; text-align: center; line-height: 1.42; margin-top: 7px; }}
@media (prefers-reduced-motion: reduce) {{ .ws-flip-in {{ transition: none; }} }}

/* 🀄 한자 카드 — 2026-09-07. 「오늘의 고급 단어」를 표 대신 카드로.
   앞면=이미지+한자 / 뒷면=뜯어보기·뜻·문장·가족 낱말. 세로로 안 늘리고 옆으로 넘긴다. */
.ws-vcd {{ margin: 18px 0 22px; }}
.ws-vcd-head {{ font-size: .88em; color: #7a6a4a; margin: 0 2px 8px; }}
/* 🔴 카드 폭·간격은 "낱말 4개가 한 줄에 딱 들어가는" 값이다(실측 1040 폭 → 트랙 736).
   4×174 + 3×10 = 726. 이보다 키우면 4번째가 반쯤 잘린 채 ▶로는 한 칸도 못 넘어간다
   (196px일 때 넘길 여지가 94px뿐이라 카운터가 1에서 안 움직였다). */
.ws-vcd-track {{ display: flex; gap: 10px; overflow-x: auto; scroll-snap-type: x mandatory;
  /* 카드 그림자가 잘리지 않도록 위아래 여백 · 스크롤바는 얇게 */
  padding: 6px 2px 12px; scrollbar-width: thin; -webkit-overflow-scrolling: touch; }}
.ws-vcd-track::-webkit-scrollbar {{ height: 6px; }}
.ws-vcd-track::-webkit-scrollbar-thumb {{ background: #d8cfb8; border-radius: 3px; }}
.ws-vcard {{ flex: 0 0 174px; width: 174px; height: 268px; scroll-snap-align: start;
  perspective: 1000px; background: none; border: 0; padding: 0; cursor: pointer;
  font-family: inherit; -webkit-tap-highlight-color: transparent; }}
.vcd-in {{ position: relative; display: block; width: 100%; height: 100%;
  transition: transform .55s cubic-bezier(.4,.2,.2,1); transform-style: preserve-3d; }}
.ws-vcard.on .vcd-in {{ transform: rotateY(180deg); }}
.ws-vcard:focus-visible .vcd-in {{ outline: 3px solid #8a5f12; outline-offset: 3px; }}
.vcd-f, .vcd-b {{ position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; border-radius: 13px; backface-visibility: hidden;
  -webkit-backface-visibility: hidden; box-sizing: border-box; overflow: hidden;
  box-shadow: 0 3px 10px rgba(60,48,20,.13); }}
.vcd-f {{ background: #f6f2e7; border: 2px solid #cfc4ae; justify-content: flex-start; padding: 0 0 10px; }}
.vcd-f img {{ width: 100%; height: 132px; object-fit: cover; border-bottom: 1px solid #ddd3ba; }}
.vcd-noimg {{ width: 100%; height: 132px; display: flex; align-items: center; justify-content: center;
  font-size: 2.4em; background: #ece6d6; border-bottom: 1px solid #ddd3ba; opacity: .5; }}
/* 위아래 auto 둘이 남는 공간을 나눠 가져 글자 묶음이 이미지 아래 가운데 선다.
   (hanja에 고정 margin을 주면 글자가 위에 붙고 카드 아래가 텅 빈다) */
.vcd-hanja {{ font-size: 1.62em; letter-spacing: .06em; color: #6b4f14; margin-top: auto;
  font-weight: 700; line-height: 1.15; text-align: center; }}
.vcd-ko {{ font-size: .92em; color: #3d3116; margin-top: 4px; font-weight: 700; text-align: center; }}
.vcd-ko-solo {{ font-size: 1.22em; margin-top: auto; color: #6b4f14; }}
.vcd-turn {{ font-size: .7em; color: #a08a5c; margin-top: auto; padding-top: 4px; }}
.vcd-b {{ background: #fffdf6; border: 2px solid #b8862b; transform: rotateY(180deg);
  justify-content: flex-start; padding: 13px 13px 11px; gap: 6px; text-align: center;
  /* 뒷면은 글이 많다 — 넘치면 카드 안에서만 스크롤한다(카드 키가 들쭉날쭉해지지 않게) */
  overflow-y: auto; }}
.vcd-bko {{ font-size: 1.02em; font-weight: 700; color: #6b4f14;
  border-bottom: 1px solid #ead9b4; padding-bottom: 6px; width: 100%; }}
.vcd-split {{ font-size: .8em; color: #7a6134; }}
.vcd-mean {{ font-size: .84em; color: #2f2a1e; font-weight: 600; }}
.vcd-sent {{ font-size: .78em; color: #4a3f2a; font-style: italic; line-height: 1.45; }}
.vcd-fam {{ font-size: .74em; color: #6b5a3a; line-height: 1.5; margin-top: auto;
  border-top: 1px dashed #e3d7ba; padding-top: 6px; width: 100%; }}
.ws-vcd-nav {{ display: flex; align-items: center; justify-content: center; gap: 14px; }}
.ws-vcd-nav button {{ border: 1px solid #cfc4ae; background: #fff; color: #6b5a3a;
  border-radius: 8px; padding: 3px 13px; font-size: .84em; cursor: pointer; font-family: inherit; }}
.ws-vcd-nav button:disabled {{ opacity: .32; cursor: default; }}
.vcd-count {{ font-size: .82em; color: #8a7a5c; font-variant-numeric: tabular-nums; }}
@media (prefers-reduced-motion: reduce) {{
  .vcd-in {{ transition: none; }}
  .ws-vcd-track {{ scroll-behavior: auto; }}
}}
@media print {{
  /* 인쇄는 넘길 수 없다 — 카드를 펼쳐 앞뒤를 나란히 둔다 */
  .ws-vcd-track {{ display: flex; flex-wrap: wrap; overflow: visible; }}
  .ws-vcard {{ height: auto; }}
  .vcd-in {{ transform: none !important; }}
  .vcd-f, .vcd-b {{ position: static; transform: none; backface-visibility: visible; }}
  .ws-vcd-nav {{ display: none; }}
}}

@media print {{
  .ws-flip {{ height: auto; }}
  .ws-flip-in {{ transform: none !important; }}
  .ws-flip-f, .ws-flip-b {{ position: static; transform: none; backface-visibility: visible; }}
}}

/* 📕 교과서를 펴는 자리 — 2026-09-02.
   학습지 안에서 답이 나오는 것들(빈칸·설명 blockquote)은 전부 파랑(#007aff)이라
   교과서 슬롯도 같은 파랑이면 화면상 구분이 안 됐다. 황토/크림으로 계열을 통째로 분리한다. */
.ws-tb {{
  background: #fdf8ed; border: 1px solid #e8d9b4; border-left: 6px solid #b8862b;
  border-radius: 0 10px 10px 0; padding: 12px 16px 14px; margin: 14px 0;
}}
.ws-tb-tag {{
  display: inline-block; background: #b8862b; color: #fff;
  font-size: 0.78em; font-weight: 700; letter-spacing: 0.02em;
  padding: 3px 10px; border-radius: 999px; margin-bottom: 8px;
}}
.ws-tb-see {{ font-size: 0.9em; color: #7a6742; margin: 2px 0 6px; }}
.ws-tb-ask {{ font-size: 0.95em; color: #3d3116; font-weight: 600; line-height: 2.1; }}
.ws-tb-ask strong {{ color: #8a5f12; }}
.ws-tb input.activity-input {{
  border-bottom: 2px solid #b8862b; background: #fffdf5; color: #3d3116;
  text-align: left; padding-left: 8px;
}}
.ws-tb input.activity-input:focus {{ border-bottom-color: #8a5f12; background: #fff8e4; }}
@media print {{ .ws-tb {{ background: #fff; border-left-color: #999; }} }}

.callout {{
  padding: 10px 14px; margin: 10px 0; border-radius: 8px; font-size: 0.9em;
}}
.callout-info {{ background: #e8f4fd; border-left: 4px solid #007aff; }}
.callout-warning {{ background: #fff8e1; border-left: 4px solid #ff9500; }}
.callout-tip {{ background: #e8f8e8; border-left: 4px solid #34c759; }}
.callout-question {{ background: #f3e8fd; border-left: 4px solid #af52de; }}
.code-block {{
  background: #1e1e1e; color: #d4d4d4; padding: 14px; border-radius: 8px;
  font-family: 'SF Mono', monospace; font-size: 0.82em;
  overflow-x: auto; margin: 10px 0; white-space: pre;
}}
.blank-input {{
  border: none; border-bottom: 2px solid #007aff; background: #f8f9ff;
  padding: 3px 6px; font-size: 0.93em; font-family: inherit;
  text-align: center; border-radius: 4px 4px 0 0; outline: none;
  transition: all 0.3s;
}}
.blank-input:focus {{ border-bottom-color: #5856d6; background: #f0f0ff; }}
.blank-input.correct {{ border-bottom-color: #34c759; background: #e8f8e8; color: #1a7a2e; }}
.blank-input.wrong {{ border-bottom-color: #ff3b30; background: #fff0f0; }}
.blank-input.no-score {{ border-bottom-color: #aaa; }}
/* 🔴 활동 입력칸은 [학생작성:400] 처럼 inline width 가 박힌다. 데스크톱 트랙(736px)에서는
   문제없지만 폰 트랙(330px)에서는 그대로 **페이지 전체를 옆으로 민다**.
   2026-09-09 실측: 3-3-1·3-3-2·3-3-3 모두 문서폭 452 / 뷰포트 390 = 62px 초과.
   ⚠️ 처음에 «낱말카드 트랙의 부작용»으로 오진했다 — 트랙은 overflow-x:auto 로 정상
      흡수하고 있었고(clientW 330 = 부모 330), 범인은 :::교과서 안의 이 칸이었다.
   max-width 는 «넘칠 때만» 작동하므로 데스크톱 회귀 0. */
.blank-input.activity-input {{ max-width: 100%; }}
/* 🔴 표가 폰에서 페이지를 민다 — 셀 padding(좌우 24px)+테두리가 열마다 고정이라
   3열이면 78px이 먼저 먹히고 남는 폭으로 최소폭을 못 맞춘다.
   2026-09-09 실측: 표를 숨기면 문서폭 417→392(뷰포트 390). 폰에서만 조인다. */
@media (max-width: 560px) {{
  table {{ font-size: 0.84em; table-layout: fixed; }}
  td, th {{ padding: 7px 6px; line-height: 1.5; word-break: break-word; }}
  tr:first-child td {{ font-size: 0.94em; }}
  /* 활동 표(act-table)는 «내용 폭»이라 inline width 가 든 입력칸이 그대로 민다.
     폰에서는 셀 폭에 맞춘다 — inline style 을 이겨야 해서 !important. */
  table.act-table {{ width: 100%; }}
  table.act-table .activity-input {{ width: 100% !important; }}
}}
.blank-input.code-blank {{ background: #2a2a2a; color: #e0e0e0; border-bottom-color: #5856d6; }}
.blank-input.no-score.correct {{ border-bottom-color: #34c759; }}
.blank-input.no-score.wrong {{ border-bottom-color: #ff9500; }}
.ox-input {{
  border: 1px solid #ddd; padding: 3px; font-size: 0.93em;
  font-family: inherit; border-radius: 4px; outline: none;
  transition: all 0.3s;
}}
.ox-group {{ display: inline-flex; gap: 6px; }}
.ox-btn {{
  width: 44px; height: 44px; border: 2px solid #007aff; border-radius: 50%;
  background: white; color: #007aff; font-size: 1.12em; font-weight: 800;
  cursor: pointer; transition: all 0.2s; line-height: 1;
}}
.ox-group {{ gap: 9px; }}
/* OX 표 — 문장 칸은 넓게, 버튼 칸은 좁고 가운데 (2026-09-03) */
table:has(.ox-group) td:last-child {{ width: 118px; text-align: center; }}
table:has(.ox-group) td:first-child {{ width: 46px; text-align: center; color: #6b7482; }}
.ox-btn:hover {{ background: #f0f4ff; }}
.ox-btn.selected {{ background: #007aff; color: white; }}
.ox-btn.correct {{ background: #34c759; color: white; border-color: #34c759; }}
.ox-btn.wrong {{ background: #ff3b30; color: white; border-color: #ff3b30; }}
.choice-group {{ display: flex; flex-wrap: wrap; gap: 4px; }}
.choice-btn {{
  padding: 4px 10px; border: 1px solid #007aff; border-radius: 6px;
  background: white; color: #007aff; font-size: 0.82em; cursor: pointer;
  transition: all 0.2s;
}}
.choice-btn:hover {{ background: #f0f4ff; }}
.choice-btn.selected {{ background: #007aff; color: white; }}
.choice-btn.correct {{ background: #34c759; color: white; border-color: #34c759; }}
.choice-btn.wrong {{ background: #ff3b30; color: white; border-color: #ff3b30; }}
.btn-submitted {{ background: #34c759 !important; cursor: default; }}
.submit-msg {{ text-align: center; padding: 8px; color: #34c759; font-weight: 600; display: none; }}
.essay-input {{
  width: 100%; min-height: 104px; border: 1.5px solid #ccd4de; border-radius: 10px;
  padding: 12px 14px; font-family: inherit; font-size: 0.95em; line-height: 1.9;
  resize: vertical; margin: 8px 0; outline: none; background: #fcfdff;
  transition: border-color .15s, background .15s;
}}
.essay-input:focus {{ border-color: #007aff; background: #fff; }}
.essay-input:focus {{ border-color: #007aff; }}
.control-bar {{
  position: sticky; top: 0; background: white; padding: 10px 0;
  border-bottom: 1px solid #eee; margin: -16px 0 16px; z-index: 100;
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 8px;
}}
.score {{ font-size: 1.1em; font-weight: 600; color: #007aff; }}
.btn {{
  padding: 7px 16px; border: none; border-radius: 8px;
  font-size: 0.88em; font-weight: 600; cursor: pointer;
}}
.btn-primary {{ background: #007aff; color: white; }}
.btn-secondary {{ background: #f0f0f5; color: #333; }}
.btn-danger {{ background: #ff3b30; color: white; }}
.student-info {{
  display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap;
}}
.student-info select {{ background:#fff; cursor:pointer; }}
.student-info input, .student-info select {{
  border: 1px solid #ddd; padding: 5px 10px; border-radius: 6px; font-size: 0.9em;
}}
@media (max-width: 600px) {{
  .container {{ padding: 14px; }}
  .control-bar {{ flex-direction: column; text-align: center; }}
  table {{ font-size: 0.82em; }}
  .hero-title {{ font-size: 26px !important; }}
  .hero-section {{ padding: 36px 20px !important; }}
}}
.hero-section {{
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
  color: #f5f5f0; padding: 56px 36px; margin: -32px -32px 28px;
  font-family: 'Pretendard', 'Noto Serif KR', serif;
  border-radius: 16px 16px 0 0;
  position: relative; overflow: hidden;
}}
.hero-section::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, #d4af37 0%, #f5f5f0 50%, #d4af37 100%);
}}
.hero-eyebrow {{ font-size: 12px; letter-spacing: 2px; color: #d4af37; text-transform: uppercase; margin-bottom: 12px; font-weight: 600; }}
.hero-title {{ font-size: 32px; font-weight: 700; margin: 0 0 14px; letter-spacing: -0.5px; line-height: 1.25; color: #f5f5f0; border: none; padding: 0; }}
.hero-subtitle {{ font-size: 15px; color: #a8a89e; margin: 0 0 22px; line-height: 1.5; }}
.hero-keywords {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px; }}
.hero-keyword.has-card {{ cursor: pointer; font-family: inherit; }}
.hero-keyword.has-card:hover {{ background: rgba(255,255,255,0.14); border-color: #8a8a80; }}
.hero-keyword.has-card[aria-expanded="true"] {{ background: rgba(255,255,255,0.18); border-color: #c9c9c0; color: #fff; }}
.kw-caret {{ margin-left: 7px; font-size: 11px; opacity: 0.75; }}
.hero-card {{ margin-top: 12px; }}
.hero-card-inner {{ background: rgba(255,255,255,0.96); color: #23272e; border-radius: 10px; padding: 16px 18px; font-size: 14px; line-height: 1.65; }}
.hero-card-inner table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 13px; }}
.hero-card-inner th, .hero-card-inner td {{ border: 1px solid #d6dae0; padding: 7px 9px; text-align: left; }}
.hero-card-inner th {{ background: #eef1f5; font-weight: 700; }}
.hero-card-inner img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 6px 0; }}
.hero-card-inner p {{ margin: 6px 0; }}
.hero-card-inner strong {{ color: #0d47a1; }}
.card-quote {{ border-left: 3px solid #6b9ac4; background: #f2f6fb; padding: 8px 12px; margin: 8px 0; border-radius: 0 6px 6px 0; }}
@media print {{ .hero-card[hidden] {{ display: none; }} .kw-caret {{ display: none; }} }}
.hero-keyword {{
  padding: 6px 14px; border: 1px solid #555; border-radius: 20px;
  font-size: 12.5px; color: #d4d4cf; background: rgba(255,255,255,0.05);
  letter-spacing: 0.3px;
}}
.hero-image {{ width: 100%; max-height: 420px; margin-top: 24px; border-radius: 10px; object-fit: contain; }}
.ws-fig {{ max-width: 100%; margin: 22px auto; text-align: center; }}
.ws-fig img {{ max-width: 100%; max-height: 440px; height: auto; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.12); }}
.ws-fig-video {{ max-width: 100%; width: 760px; height: auto; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.12); background: #000; }}
.ws-fig img[src*="comic"] {{ max-height: 820px; max-width: 600px; }}
.ws-fig figcaption {{ margin-top: 8px; font-size: 13px; color: #6b6b6b; line-height: 1.5; padding: 0 8px; }}
.ws-fold-table {{ width:100%; border-collapse:collapse; margin:8px 0; font-size:0.9em; }}
.ws-fold-table th, .ws-fold-table td {{ border:1px solid #ddd7c8; padding:7px 9px; text-align:left; vertical-align:top; }}
.ws-fold-table thead th {{ background:#eee9dc; font-weight:700; }}
.ws-anim-ctl {{ display:flex; align-items:center; justify-content:center; gap:10px; margin:8px 0 2px; }}
.ws-anim-ctl button {{ border:1px solid #cfc8b6; background:#fff; border-radius:8px; padding:6px 16px;
  cursor:pointer; font-family:inherit; font-size:0.9em; color:#4a5c40; font-weight:700; }}
.ws-anim-ctl button:hover {{ background:#f1efe6; }}
.ws-anim-ctl span {{ font-size:0.8em; color:#9a9284; }}
.ws-gal {{ margin: 22px auto; max-width: 100%; border: 1px solid #ddd7c8; border-radius: 12px;
  background: #fbfaf6; overflow: hidden; }}
.ws-gal-head {{ padding: 12px 16px 0; font-weight: 700; color: #3a4a34; font-size: 0.98em; }}
.ws-gal-tabs {{ display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 14px; }}
.ws-gal-dot {{ border: 1px solid #cfc8b6; background: #fff; color: #5a5344; border-radius: 999px;
  padding: 5px 12px; font-size: 0.84em; cursor: pointer; font-family: inherit; }}
.ws-gal-dot.on {{ background: #4a5c40; border-color: #4a5c40; color: #fff; font-weight: 700; }}
.ws-gal-stage {{ text-align: center; padding: 4px 14px 0; }}
.ws-gal-slide img {{ max-width: 100%; max-height: 430px; height: auto; border-radius: 6px;
  box-shadow: 0 2px 10px rgba(0,0,0,.14); }}
.ws-gal-slide figcaption {{ margin: 8px auto 0; max-width: 640px; font-size: 0.86em;
  color: #5a5344; line-height: 1.55; }}
.ws-gal-nav {{ display: flex; align-items: center; justify-content: center; gap: 14px; padding: 10px 0 14px; }}
.ws-gal-nav button {{ border: 1px solid #cfc8b6; background: #fff; border-radius: 8px;
  padding: 6px 14px; cursor: pointer; font-family: inherit; font-size: 0.9em; color: #4a5c40; }}
.ws-gal-count {{ font-size: 0.86em; color: #8a8272; font-variant-numeric: tabular-nums; }}
.ws-figrow {{ display: flex; gap: 16px; justify-content: center; align-items: flex-start; flex-wrap: wrap; max-width: 100%; margin: 22px auto; }}
.ws-figrow-item {{ flex: 1 1 0; min-width: 200px; max-width: 320px; margin: 0; text-align: center; }}
.ws-figrow-item img {{ width: 100%; max-height: 340px; height: auto; object-fit: contain; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.12); }}
.ws-figrow-item figcaption {{ margin-top: 6px; font-size: 12px; color: #6b6b6b; line-height: 1.45; }}
.hero-hook {{ margin-top: 22px; padding-top: 18px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 14px; color: #c4c4ba; line-height: 1.6; font-style: italic; }}
.blank-filled {{ display: inline-block; border-bottom: 2px solid #34c759; background: #e8f8e8; color: #1a7a2e; font-weight: 700; padding: 2px 8px; border-radius: 4px 4px 0 0; margin: 0 2px; }}
</style>
</head>
<body>
<div class="container">
  {hero_html}
  {top_bar}
  {content}
</div>
<script>
const TB={total}, TOX={total_ox}, GT={grand_total};
let usedReveal=false;
function selectOX(btn, val){{
  const grp=btn.parentElement;
  grp.querySelectorAll('.ox-btn').forEach(b=>b.classList.remove('selected'));
  btn.classList.add('selected');
  grp.dataset.selected=val;
}}
function selectChoice(btn, val){{
  const grp=btn.parentElement;
  grp.querySelectorAll('.choice-btn').forEach(b=>b.classList.remove('selected'));
  btn.classList.add('selected');
  grp.dataset.selected=val;
}}
document.addEventListener('click', function(e){{
  var b = e.target.closest ? e.target.closest('.hero-keyword.has-card') : null;
  if (!b) return;
  var card = document.getElementById('hero-card-' + b.dataset.card);
  if (!card) return;
  var open = card.hasAttribute('hidden');
  if (open) {{ card.removeAttribute('hidden'); }} else {{ card.setAttribute('hidden',''); }}
  b.setAttribute('aria-expanded', open ? 'true' : 'false');
  b.querySelector('.kw-caret').textContent = open ? '\u2212' : '\uFF0B';
}});
function replayAnim(id){{
  // 애니메이션 WebP/GIF는 loop=1로 구워져 한 번만 재생된다(WCAG 2.2.2).
  // src를 캐시버스터와 함께 갈아 끼우면 처음부터 다시 돈다.
  const im=document.getElementById(id); if(!im) return;
  const base=im.dataset.src||im.src.split('?')[0];
  im.src='';
  setTimeout(()=>{{ im.src = base + '?r=' + Date.now(); }}, 30);
}}
function galGo(id,i){{
  const g=document.getElementById(id); if(!g) return;
  const n=+g.dataset.n;
  i=((i%n)+n)%n;
  g.querySelectorAll('.ws-gal-slide').forEach(e=>{{ e.hidden = (+e.dataset.i !== i); }});
  g.querySelectorAll('.ws-gal-dot').forEach((e,k)=>e.classList.toggle('on',k===i));
  const c=g.querySelector('.ws-gal-count b'); if(c) c.textContent = i+1;
  g.dataset.cur = i;
}}
function galStep(id,d){{
  const g=document.getElementById(id); if(!g) return;
  galGo(id, (+(g.dataset.cur||0)) + d);
}}
function cmpGo(id,i){{
  const g=document.getElementById(id); if(!g) return;
  const n=+g.dataset.n; i=((i%n)+n)%n;
  g.querySelectorAll('.ws-cmp-slide').forEach(e=>{{ e.hidden = (+e.dataset.i !== i); }});
  g.querySelectorAll('.ws-cmp-tab').forEach((e,k)=>e.classList.toggle('on',k===i));
  const c=g.querySelector('.ws-cmp-count b'); if(c) c.textContent = i+1;
  g.dataset.cur = i;
}}
function cmpStep(id,d){{
  const g=document.getElementById(id); if(!g) return;
  cmpGo(id, (+(g.dataset.cur||0)) + d);
}}
function norm(s){{return (s||'').replace(/\\s+/g,'').replace(/[·,.()（）\\[\\]]/g,'').toLowerCase();}}
function check(){{
  let bc=0, oxc=0;
  document.querySelectorAll('.blank-input').forEach(el=>{{
    const a=norm(el.dataset.answer), u=norm(el.value);
    if(!u){{el.classList.remove('correct','wrong');return;}}
    // ⭐ 5/27 fix: no-score(활동·코드블록) input은 채점 시각 표시 제외
    if(el.classList.contains('no-score')){{el.classList.remove('correct','wrong');return;}}
    const isCorrect=u===a||a.includes(u)&&u.length>=a.length*0.6;
    if(isCorrect){{
      el.classList.add('correct');el.classList.remove('wrong');
      bc++;
    }}else{{el.classList.add('wrong');el.classList.remove('correct');}}
  }});
  document.querySelectorAll('.ox-group').forEach(grp=>{{
    const sel=grp.dataset.selected, ans=grp.dataset.answer;
    if(!sel) return;
    grp.querySelectorAll('.ox-btn').forEach(btn=>{{
      btn.classList.remove('correct','wrong');
      if(btn.classList.contains('selected')){{
        if(sel===ans){{btn.classList.add('correct');oxc++;}}
        else{{btn.classList.add('wrong');}}
      }}
    }});
  }});
  document.querySelectorAll('.choice-group').forEach(grp=>{{
    const sel=grp.dataset.selected;
    if(!sel) return;
    const ans=grp.querySelector('.choice-btn').dataset.answer;
    grp.querySelectorAll('.choice-btn').forEach(btn=>{{
      btn.classList.remove('correct','wrong');
      if(btn.classList.contains('selected')){{
        if(sel===ans){{btn.classList.add('correct');bc++;}}
        else{{btn.classList.add('wrong');}}
      }}
    }});
  }});
  const _sc=document.getElementById('score');
  if(_sc){{
    _sc.textContent=bc;
    document.getElementById('ox-score').textContent=oxc;
    document.getElementById('total-score').textContent=bc+oxc;
    document.getElementById('pct').textContent=GT?Math.round((bc+oxc)/GT*100):0;
  }}
}}
function reveal(){{
  usedReveal=true;
  document.querySelectorAll('.blank-input').forEach(el=>{{
    el.value=el.dataset.answer;el.classList.add('correct');el.classList.remove('wrong');
  }});
  document.querySelectorAll('.ox-group').forEach(grp=>{{
    const ans=grp.dataset.answer;
    grp.querySelectorAll('.ox-btn').forEach(btn=>{{
      btn.classList.remove('selected','wrong');
      if(btn.textContent===ans){{btn.classList.add('selected','correct');}}
    }});
    grp.dataset.selected=ans;
  }});
  document.querySelectorAll('.choice-group').forEach(grp=>{{
    const ans=grp.querySelector('.choice-btn').dataset.answer;
    grp.querySelectorAll('.choice-btn').forEach(btn=>{{
      btn.classList.remove('selected','wrong');
      if(btn.textContent===ans){{btn.classList.add('selected','correct');}}
    }});
    grp.dataset.selected=ans;
  }});
  document.getElementById('score').textContent=TB;
  document.getElementById('ox-score').textContent=TOX;
  document.getElementById('total-score').textContent=GT;
  document.getElementById('pct').textContent=100;
}}
function reset(){{
  usedReveal=false;
  document.querySelectorAll('.blank-input').forEach(el=>{{
    el.value='';el.classList.remove('correct','wrong');
  }});
  document.querySelectorAll('.ox-btn').forEach(b=>{{
    b.classList.remove('selected','correct','wrong');
  }});
  document.querySelectorAll('.ox-group').forEach(g=>{{delete g.dataset.selected;}});
  document.querySelectorAll('.choice-btn').forEach(b=>{{
    b.classList.remove('selected','correct','wrong');
  }});
  document.querySelectorAll('.choice-group').forEach(g=>{{delete g.dataset.selected;}});
  document.querySelectorAll('.essay-input').forEach(el=>{{el.value='';}});
  const _sc=document.getElementById('score');
  if(_sc){{
    _sc.textContent=0;
    document.getElementById('ox-score').textContent=0;
    document.getElementById('total-score').textContent=0;
    document.getElementById('pct').textContent=0;
  }}
}}
// 저장/복원 — 빈칸·OX·서술형(essay)·보기버튼 *전부* localStorage에 보존 (6/8 확장)
// ⭐ EXAM_MODE (6/12·공용 노트북 잔존 사고): 평가지는 저장 키에 반-번호를 묶는다.
//    신원 입력 전 = 저장/복원 없음 → 다른 학생이 같은 노트북·같은 URL을 열어도 이전 답이 안 보임.
//    본인 반·번호를 입력하면 *자기 키*만 복원 (새로고침 안전망 유지).
const EXAM_MODE={exam_js};
// 학생정보 3필드 접근 — 2026-08-27부터 반·번호는 <select>, 이름만 <input>.
// nth-child 셀렉터는 필드 순서가 바뀌면 조용히 깨지므로 id로 고정한다.
function _siEl(id){{ return document.getElementById(id); }}
function _siv(id){{ const e=_siEl(id); return e?e.value.trim():''; }}
// 🔴 2026-08-31: 저장 키에 '정답 체계 지문'을 붙인다.
//   사고 — 3-3-1의 빈칸을 21→15로 줄이자, v1 때 채워 둔 답이 v2 번호로 복원되며
//   ⑤부터 한 칸씩 밀렸다(⑤에 '봉신', ⑥에 '주종 관계'). 화면만 보면 "답이 노출되고
//   매칭이 틀린" 것처럼 보이는데, 실제로는 옛 입력이 새 번호에 얹힌 것이다.
//   빈칸 개수·정답 문자열이 바뀌면 지문이 달라져 옛 답이 붙지 않는다.
function _wsFp(){{
  let sig='';
  document.querySelectorAll('.blank-input:not(.activity-input),.ox-group').forEach(el=>{{
    sig += (el.dataset.answer||'') + '|';
  }});
  let h=5381;
  for(let i=0;i<sig.length;i++){{ h=((h*33)^sig.charCodeAt(i))>>>0; }}
  return h.toString(36);
}}
function _wsKey(){{
  const fp='::v'+_wsFp();
  if(!EXAM_MODE) return 'ws_'+document.title+fp;
  const c=_siv('si-cls'), n=_siv('si-num');
  if(!c||!n) return null;
  return 'ws_'+document.title+fp+'::'+c+'-'+n;
}}
// 지문 도입 이전(=구키)에 저장된 답은, 빈칸 개수가 그대로일 때만 이어받는다.
//   같으면 단순 재발행이므로 학생이 쓰던 답을 살리고, 다르면 구조가 바뀐 것이므로 버린다.
function _migrateOldKey(newKey){{
  const oldKey = EXAM_MODE
    ? 'ws_'+document.title+'::'+_siv('si-cls')+'-'+_siv('si-num')
    : 'ws_'+document.title;
  let raw; try{{ raw=localStorage.getItem(oldKey); }}catch(e){{ return; }}
  if(!raw) return;
  try{{
    const p=JSON.parse(raw), d=p.data||{{}};
    const nowN=document.querySelectorAll('.blank-input:not(.activity-input)').length;
    const oldN=Object.keys(d).filter(k=>/^\d+$/.test(k)).length;
    if(oldN===nowN) localStorage.setItem(newKey, raw);   // 구조 동일 → 이어받기
  }}catch(e){{}}
  try{{ localStorage.removeItem(oldKey); }}catch(e){{}}  // 구키는 어느 쪽이든 정리
}}
function _persist(){{
  const key=_wsKey(); if(!key) return;
  const data={{}};
  document.querySelectorAll('.blank-input,.ox-input,.essay-input').forEach((el,i)=>{{
    data[el.dataset.id||el.dataset.answer||('input_'+i)]=el.value;
  }});
  document.querySelectorAll('.ox-group').forEach((g,i)=>{{ data['__sel_'+(g.dataset.id||('ox_'+i))]=g.dataset.selected||''; }});
  document.querySelectorAll('.choice-group').forEach((g,i)=>{{ data['__sel_'+(g.dataset.id||('choice_'+i))]=g.dataset.selected||''; }});
  const info={{class:_siv('si-cls'),number:_siv('si-num'),name:_siv('si-name')}};
  try{{ localStorage.setItem(key, JSON.stringify({{info,data,ts:Date.now()}})); }}catch(e){{}}
}}
function saveProgress(){{ _persist(); alert('저장되었습니다! 같은 기기에서 반·번호를 고르면 이어서 쓸 수 있어요.\\n※ 제출을 마치면 이 기기에 남긴 답은 지워집니다.'); }}
let _autosaveT;
function autosave(){{ clearTimeout(_autosaveT); _autosaveT=setTimeout(_persist,1200); }}
function loadProgress(){{
  const key=_wsKey(); if(!key) return;  // 평가 모드: 반·번호 입력 전엔 복원 없음
  _migrateOldKey(key);
  let saved; try{{ saved=localStorage.getItem(key); }}catch(e){{}}
  if(!saved) return;
  let parsed; try{{ parsed=JSON.parse(saved); }}catch(e){{ return; }}
  const info=parsed.info, data=parsed.data;
  // 🔒 2026-09-04 — 복원 전에 **신원을 대조한다**.
  //   종전에는 저장된 반·번호·이름을 화면에 그대로 채워 넣었다. 그래서 친구 노트북을 빌린 학생이
  //   열면 **남의 답과 남의 이름이 이미 적혀 있었고, 이름만 바꾸면 그대로 제출**됐다(천대현 관찰).
  //   이제 저장된 주인과 지금 앉은 사람이 같을 때만 복원한다.
  if(info && (info.class||info.number)){{
    const c=_siv('si-cls'), n=_siv('si-num');
    if(!c || !n) return;                                  // 아직 신원을 안 넣었다 → 보류(넣으면 리스너가 다시 부른다)
    if(String(info.class)!==String(c) || String(info.number)!==String(n)) return;  // 주인이 다르다 → 복원 안 함
  }}
  if(!data) return;
  document.querySelectorAll('.blank-input,.ox-input,.essay-input').forEach((el,i)=>{{
    const k=el.dataset.id||el.dataset.answer||('input_'+i);
    if(data[k]!==undefined&&data[k]!=='') el.value=data[k];
  }});
  document.querySelectorAll('.ox-group').forEach((g,i)=>{{
    const v=data['__sel_'+(g.dataset.id||('ox_'+i))];
    if(v){{ const b=[...g.querySelectorAll('.ox-btn')].find(x=>x.textContent.trim()===v); if(b) selectOX(b,v); }}
  }});
  document.querySelectorAll('.choice-group').forEach((g,i)=>{{
    const v=data['__sel_'+(g.dataset.id||('choice_'+i))];
    if(v){{ const b=[...g.querySelectorAll('.choice-btn')].find(x=>x.textContent.trim()===v); if(b) selectChoice(b,v); }}
  }});
}}
// 모든 입력칸에서 Enter→다음칸 이동
const allInputs=[...document.querySelectorAll('.blank-input')];
allInputs.forEach((el,i)=>{{
  el.addEventListener('keydown',e=>{{
    if(e.key==='Enter'){{e.preventDefault();if(i+1<allInputs.length)allInputs[i+1].focus();else check();}}
  }});
}});
// 제출
const SUBMIT_URL='{submit_url}';
// 모든 입력값 수집 — 빈칸·OX·서술형·활동·choice 통합 (5/21 patch)
function collectAnswers(){{
  const ans={{}};
  document.querySelectorAll('.blank-input,.ox-input,.essay-input').forEach((el,i)=>{{
    const k=el.dataset.id||el.dataset.answer||('input_'+i);
    ans[k]=(el.value||'').trim();
  }});
  document.querySelectorAll('.ox-group,.choice-group').forEach((g,i)=>{{
    const k=g.dataset.id||('group_'+i);
    ans[k]=g.dataset.selected||'';
  }});
  // 2026-06-24: data-label을 __labels로 동승 → 정리시트가 act-N 대신 문항 텍스트 표시 (doPost 변경 불요·답(JSON)에 라이드)
  const lbl={{}};
  document.querySelectorAll('[data-label]').forEach(el=>{{
    const k=el.dataset.id; if(k && el.dataset.label) lbl[k]=el.dataset.label;
  }});
  if(Object.keys(lbl).length) ans['__labels']=lbl;
  return ans;
}}
// 진행 탭 — 5/27 비활성화 (제출 학생만 수집·진행 탭 noise 차단)
// 함수 자체는 NO-OP으로 유지 (이벤트 리스너 호환성)
function scheduleProgress(){{ /* disabled — 제출 시점에만 데이터 전송 */ }}
// 🔴 전송 중 재진입 가드 (2026-09-02) — 사회(중3) 세션이 시트에서 발견한 중복 제출의 원인.
//   종전엔 버튼이 한 번도 disabled 되지 않았고, 텍스트는 fetch **응답 후**에야 바뀌었다.
//   그 왕복 사이에 한 번 더 누르면 그대로 두 번 전송된다 — mode:'no-cors'라 실패해도 조용하다.
//   실측 중복: 사회 125=126행(8/31 08:16·6반23번) · 역사 21=23행(8/31 14:12·1반18번).
//   시각·점수·답이 전부 같아 재제출이 아니라 '버튼 두 번'이다. 집계에서 인원이 부푼다.
let _submitting = false;
function submitResult(){{
  if(_submitting) return;                     // 전송 중 두 번째 클릭은 무시
  if(!SUBMIT_URL){{alert('제출 URL이 설정되지 않았습니다.');return;}}
  const cls=_siv('si-cls'), num=_siv('si-num'), name=_siv('si-name');
  if(!cls||!num||!name){{alert('반, 번호를 고르고 이름을 적어주세요. (학습지 빈칸은 일부만 채워도 OK)');return;}}
  // 이름 칸에 번호를 적는 오기 차단 (6/25 채점 로그: 3-3반 3번 이름이 "23"으로 들어옴)
  if(/^[0-9\s]+$/.test(name)){{alert('이름 칸에 숫자가 들어갔어요. 이름을 적어주세요.');return;}}
  if(usedReveal){{alert('⚠️ 정답 보기를 사용했기 때문에 제출할 수 없습니다. 초기화 후 다시 풀어주세요.');return;}}
  check(); // 먼저 채점
  const _g=id=>{{const e=document.getElementById(id);return e?parseInt(e.textContent)||0:0;}};
  const bs=_g('score');
  const os=_g('ox-score');
  const ts=_g('total-score');
  const answers=collectAnswers();
  const data={{
    type:'final',
    worksheet:document.title,
    studentClass:cls,studentNumber:num,studentName:name,
    blankScore:bs,oxScore:os,totalScore:ts,
    answers:answers
  }};
  // 여기서부터 실제 전송 — 잠그고 버튼도 즉시 비활성화한다(응답을 기다리지 않는다).
  _submitting = true;
  const _btn=document.getElementById('submitBtn');
  _btn.disabled = true; _btn.textContent = '전송 중…';
  fetch(SUBMIT_URL,{{method:'POST',mode:'no-cors',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(data)}})
  .then(()=>{{
    // 🔒 제출이 끝나면 **이 기기에 남긴 답을 지운다**(2026-09-04 천대현 요청).
    //   화면의 답은 그대로라 재제출은 되지만, 새로 열면 남지 않는다 → 빌려준 노트북에 답이 안 남는다.
    try{{ const k=_wsKey(); if(k) localStorage.removeItem(k); }}catch(e){{}}
    _btn.textContent='✅ 제출 완료';
    _btn.classList.add('btn-submitted');
    setTimeout(()=>{{
      _btn.textContent='📤 재제출';
      _btn.classList.remove('btn-submitted');
    }}, 2000);
  }})
  .catch(e=>alert('제출 실패: '+e))
  .finally(()=>{{                              // 성공·실패 모두 반드시 푼다 — 안 그러면 재제출이 영영 막힌다
    _submitting = false;
    _btn.disabled = false;
  }});
}}
// 페이지 로드 시 저장된 진행 불러오기
loadProgress();
// 신원(반·번호)을 넣거나 바꾸면 다시 복원을 시도한다.
//   위 대조 때문에 처음엔 보류될 수 있고, 본인이 반·번호를 고른 순간 자기 답이 돌아와야 한다.
['si-cls','si-num'].forEach(id=>{{
  const el=_siEl(id);
  if(el) el.addEventListener('change', ()=>{{ try{{ loadProgress(); }}catch(e){{}} }});
}});
// 자동저장 — 입력/선택 시 1.2초 후 자동 보존(저장 버튼 안 눌러도 껐다 켜면 그대로). 6/8
document.addEventListener('input', autosave, true);
document.addEventListener('click', e=>{{ if(e.target.closest && e.target.closest('.ox-group,.choice-group')) autosave(); }}, true);
// 입력 이벤트 → 진행 탭 실시간 누적 (5/21 patch)
document.querySelectorAll('.blank-input,.ox-input,.essay-input').forEach(el=>{{
  el.addEventListener('input',scheduleProgress);
}});
document.querySelectorAll('.ox-btn,.choice-btn').forEach(b=>{{
  b.addEventListener('click',()=>setTimeout(scheduleProgress,100));
}});
['si-cls','si-num','si-name'].forEach(id=>{{
  const el=_siEl(id); if(!el) return;
  el.addEventListener('input',scheduleProgress);
  el.addEventListener('change',scheduleProgress);   // <select>는 input 대신 change가 확실
}});
// 평가 모드: 반·번호를 다 입력한 시점에 *본인 키*의 저장본만 복원 (이어쓰기)
if(EXAM_MODE){{
  ['si-cls','si-num','si-name'].forEach(id=>{{
    const el=_siEl(id); if(!el) return;
    el.addEventListener('change',()=>{{ if(_wsKey()) loadProgress(); }});
  }});
}}
</script>
</body>
</html>'''


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 worksheet-gen.py <개념편.md> <개념편_정답.md> [output.html] [submit_url]")
        sys.exit(1)

    blank_file = sys.argv[1]
    answer_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'worksheet.html'

    print(f"📄 빈칸 파일: {os.path.basename(blank_file)}")
    print(f"📝 정답 파일: {os.path.basename(answer_file)}")

    answers = extract_answers(answer_file)
    ox_answers = extract_ox_answers(answer_file)
    print(f"📋 추출된 정답: 빈칸 {len(answers)}개, OX {len(ox_answers)}개")

    title, content, total, total_ox = build_html_from_blank(blank_file, answers, ox_answers, answer_file, out_path=output_file)
    print(f"🔍 매칭된 빈칸: {total}개, OX: {total_ox}개")

    # 2026-08-27: 원문 빈칸을 직접 세어 대조한다.
    # 종전 검사는 `total`(=실제로 만든 input 수)을 비교했는데, 정답이 모자라면
    # 그만큼만 만들고 그만큼만 세므로 **항상 일치**했다 → 남는 빈칸이 괄호로
    # 방치돼도 경고가 안 떴다(5-4 ⑩ 입력 불가 사고). 이제 소스에서 직접 센다.
    _bp = re.compile(r'\(\s*[　\s]+\)')   # build_html_from_blank의 blank_pattern과 동일 (그쪽은 지역 변수라 여기서 안 보임)
    _skip = re.compile(r'\*\*반:\*\*.*\*\*번:\*\*.*\*\*이름:\*\*')
    _raw = open(blank_file, encoding='utf-8').read()
    src_blanks = sum(len(_bp.findall(l)) for l in _raw.split('\n') if not _skip.search(l))

    if src_blanks != len(answers):
        gap = src_blanks - len(answers)
        print(f"🔴 빈칸/정답 불일치 — 개념편 빈칸 {src_blanks}개 vs 정답 {len(answers)}개")
        if gap > 0:
            print(f"   ⚠️  빈칸 {gap}개가 입력칸이 되지 못하고 괄호로 남습니다(학생이 답을 쓸 수 없음).")
            print(f"   → 개념편에 번호가 중복된 빈칸이 있는지, 정답편에 빠진 항목이 있는지 확인하세요.")
        else:
            print(f"   ⚠️  정답 {-gap}개가 쓰이지 않습니다(정답편 prose의 ( **굵게** ) 오검출 가능).")
    else:
        # 🔴 2026-09-03: 종전엔 build_html_from_blank가 돌려준 `total`을 비교했는데,
        #   그 값이 *실제로 생성된 채점 input 수와 달라* 3건(3-3-3·3-3-5·2-2-2)에서
        #   멀쩡한 발행본에 경고가 떴다. 오탐이 상시로 뜨면 "경고가 뜨면 멈춘다"는 룰이
        #   무력해진다(늑대소년). → 생성 결과물에서 직접 센다.
        _made = len(re.findall(r'class="blank-input(?![^"]*no-score)', content))
        if _made != len(answers):
            print(f"⚠️  생성된 채점 입력칸({_made})과 정답({len(answers)}) 수 불일치")

    DEFAULT_SUBMIT_URL = os.environ.get('WORKSHEET_SUBMIT_URL', 'https://script.google.com/macros/s/AKfycbwh0_ECTCNjuIq_hOhP_51XpEg2UWlu_nOI5EEpnK_QZBAYEAb6pVUpr3OcKim4m6OSqg/exec')
    submit_url = sys.argv[4] if len(sys.argv) > 4 else DEFAULT_SUBMIT_URL

    hero = extract_hero_meta(blank_file)
    # 평가지 모드 (frontmatter exam_mode: true) — 공용 노트북 이전 답 잔존 방지
    with open(blank_file, 'r', encoding='utf-8') as _f:
        exam_mode = bool(re.search(r'^exam_mode:\s*true', _f.read()[:3000], re.M | re.I))
    if exam_mode:
        print('🔒 평가지 모드(exam_mode): 저장/복원 키를 반-번호에 묶음')
    if any([hero.get('keywords'), hero.get('image'), hero.get('hook')]):
        print(f"🎨 hero 섹션: image={'O' if hero.get('image') else 'X'}, keywords={len(hero.get('keywords') or [])}, hook={'O' if hero.get('hook') else 'X'}")

    # 수업용 (제출O, 정답보기X)
    html_class = generate_html(title, content, total, total_ox, submit_url, mode='class', hero=hero, exam=exam_mode)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_class)
    print(f"✅ 수업용 생성: {output_file}")

    # 복습용 (제출X, 정답보기O)
    review_file = output_file.replace('.html', '_복습용.html')
    html_review = generate_html(title, content, total, total_ox, submit_url, mode='review', hero=hero, exam=exam_mode)
    with open(review_file, 'w', encoding='utf-8') as f:
        f.write(html_review)
    print(f"✅ 복습용 생성: {review_file}")

    # 정답편 (교사용·제출X·채점X) — 정답.md를 *본문*으로 렌더(교사섹션 유지) → 빈칸 볼드 정답+OX 해설+모범답안+교사 메타 전부 노출.
    # 2026-06-03: 기존 정답편은 개념편 본문에 답만 보여줘 '정답만' 나가는 문제(로마 사고) → 정답.md 본문 직접 렌더로 교정.
    teacher_file = output_file.replace('.html', '_정답.html')
    t_title, t_content, t_total, t_total_ox = build_html_from_blank(answer_file, [], [], answer_file, teacher=True, out_path=output_file)
    html_teacher = generate_html(t_title, t_content, t_total, t_total_ox, submit_url, mode='teacher', hero=hero, exam=exam_mode)
    with open(teacher_file, 'w', encoding='utf-8') as f:
        f.write(html_teacher)
    print(f"✅ 정답편(교사용) 생성: {teacher_file}")


if __name__ == '__main__':
    main()
