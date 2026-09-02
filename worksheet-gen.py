#!/usr/bin/env python3
"""마크다운 개념편 → 인터랙티브 HTML 학습지 자동 생성기 v2
정답 파일에서 답을 순서대로 추출하고, 개념편의 빈칸에 순서대로 매칭한다."""

import re
import sys
import os


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
            m_fold = re.match(r'> \[!([^\]]+)\]-\s*(.*)', stripped)
            if m_fold:
                if in_fold:
                    html_parts.append('</details>')
                ftype, ftitle = m_fold.group(1), m_fold.group(2)
                html_parts.append(
                    f'<details class="ws-fold ws-fold-{ftype}">'
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
h2 {{ font-size: 1.25em; margin: 18px 0 10px; color: #333; }}
h3 {{ font-size: 1.1em; margin: 14px 0 8px; color: #555; }}
h4 {{ font-size: 1em; margin: 10px 0 6px; color: #666; }}
p {{ margin: 5px 0; font-size: 0.95em; }}
hr {{ border: none; border-top: 1px solid #eee; margin: 16px 0; }}
table {{
  width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 0.9em;
}}
/* ⭐ 6/18: 활동 입력칸이 든 표는 내용 폭으로 (짧은 칸이 넓은 셀에 떠 보이는 비율 깨짐 방지·21-22 사고) */
table.act-table {{ width: auto; max-width: 100%; }}
table.act-table .activity-input {{ max-width: 100%; }}
td {{ border: 1px solid #ddd; padding: 7px 10px; vertical-align: top; }}
tr:first-child td {{ background: #f0f4ff; font-weight: 600; }}
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
  width: 36px; height: 36px; border: 2px solid #007aff; border-radius: 50%;
  background: white; color: #007aff; font-size: 1em; font-weight: 700;
  cursor: pointer; transition: all 0.2s; line-height: 1;
}}
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
  width: 100%; min-height: 60px; border: 1px solid #ccc; border-radius: 8px;
  padding: 10px; font-family: inherit; font-size: 0.93em;
  resize: vertical; margin: 6px 0; outline: none;
}}
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
function saveProgress(){{ _persist(); alert('저장되었습니다! 같은 기기·브라우저에서 다시 열면 그대로 이어집니다. (다른 PC로 옮기면 안 남으니, 끝나면 꼭 📤 제출!)'); }}
let _autosaveT;
function autosave(){{ clearTimeout(_autosaveT); _autosaveT=setTimeout(_persist,1200); }}
function loadProgress(){{
  const key=_wsKey(); if(!key) return;  // 평가 모드: 반·번호 입력 전엔 복원 없음
  _migrateOldKey(key);
  let saved; try{{ saved=localStorage.getItem(key); }}catch(e){{}}
  if(!saved) return;
  let parsed; try{{ parsed=JSON.parse(saved); }}catch(e){{ return; }}
  const info=parsed.info, data=parsed.data;
  if(info&&!EXAM_MODE){{
    if(info.class&&_siEl('si-cls')) _siEl('si-cls').value=info.class;
    if(info.number&&_siEl('si-num')) _siEl('si-num').value=info.number;
    if(info.name&&_siEl('si-name')) _siEl('si-name').value=info.name;
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
function submitResult(){{
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
  fetch(SUBMIT_URL,{{method:'POST',mode:'no-cors',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(data)}})
  .then(()=>{{
    document.getElementById('submitBtn').textContent='✅ 제출 완료';
    document.getElementById('submitBtn').classList.add('btn-submitted');
    setTimeout(()=>{{
      document.getElementById('submitBtn').textContent='📤 재제출';
      document.getElementById('submitBtn').classList.remove('btn-submitted');
    }}, 2000);
  }})
  .catch(e=>alert('제출 실패: '+e));
}}
// 페이지 로드 시 저장된 진행 불러오기
loadProgress();
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
    elif total != len(answers):
        print(f"⚠️  생성된 입력칸({total})과 정답({len(answers)}) 수 불일치")

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
