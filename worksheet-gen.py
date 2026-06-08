#!/usr/bin/env python3
"""마크다운 개념편 → 인터랙티브 HTML 학습지 자동 생성기 v2
정답 파일에서 답을 순서대로 추출하고, 개념편의 빈칸에 순서대로 매칭한다."""

import re
import sys
import os


def strip_obsidian_artifacts(text, teacher=False):
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
        return (f'<input type="text" class="blank-input activity-input no-score" '
                f'data-id="act-{act_counter[0]}" style="width:240px" placeholder="">')
    text = re.sub(r'\[학생작성\]', _activity_sub, text)
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


def build_html_from_blank(blank_file, answers, ox_answers, answer_file, teacher=False):
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
    in_ox_table = False
    title = "학습지"
    table_idx = -1  # 현재 처리 중인 테이블 인덱스
    table_row_idx = 0  # 현재 테이블 내 행 인덱스
    blank_table_count = 0  # 빈칸 테이블 수
    in_step0 = False  # STEP 0 구간 (채점 제외)
    in_figrow = False  # 가로 비교 figure 행 (:::figrow ... :::)
    figrow_items = []
    essay_count = 0  # 서술형 textarea 수 (제출 수합·세특용 data-id essay-N)

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
            html_parts.append(f'<textarea class="essay-input" data-id="essay-{essay_count}" placeholder="자기 생각을 자유롭게 써 보세요"></textarea>')
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

        # 이미지 ![캡션](src) → figure (2026-05-30: 본문 사료/figure 렌더. wiki-embed ![[..]]는 위에서 이미 제거됨)
        m_img = re.match(r'!\[(.*?)\]\(([^)]+)\)\s*$', stripped)
        if m_img:
            cap, src = m_img.group(1), m_img.group(2)
            fc = f'<figcaption>{inline(cap)}</figcaption>' if cap else ''
            html_parts.append(f'<figure class="ws-fig"><img src="{src}" alt="{cap}" loading="lazy">{fc}</figure>')
            continue

        # 헤딩
        if stripped.startswith('#### '):
            html_parts.append(f'<h4>{inline(stripped[5:])}</h4>')
        elif stripped.startswith('### '):
            html_parts.append(f'<h3>{inline(stripped[4:])}</h3>')
        elif stripped.startswith('## '):
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
            if stripped.startswith('> [!'):
                match = re.match(r'> \[!(\w+)\]\s*(.*)', stripped)
                if match:
                    ctype = match.group(1)
                    ctitle = match.group(2)
                    html_parts.append(f'<div class="callout callout-{ctype}"><strong>{inline(ctitle)}</strong></div>')
            elif stripped.startswith('> '):
                html_parts.append(f'<blockquote>{inline(stripped[2:])}</blockquote>')
            elif stripped == '':
                html_parts.append('<br>')
            elif stripped == '---':
                html_parts.append('<hr>')
            else:
                html_parts.append(f'<p>{inline(stripped)}</p>')

    if in_table:
        html_parts.append('</table>')

    return title, '\n'.join(html_parts), total_blanks, total_ox


def inline(text):
    """인라인 마크다운 → HTML"""
    # input 태그 보호
    parts = re.split(r'(<input[^>]+>)', text)
    result = []
    for part in parts:
        if part.startswith('<input') or part.startswith('<textarea'):
            result.append(part)
        else:
            part = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', part)
            part = re.sub(r'\*([^*\n]+?)\*', r'<em>\1</em>', part)  # 2026-05-30: *이탤릭* 지원 (입담 voice 강조어)
            result.append(part)
    return ''.join(result)


def extract_hero_meta(blank_file):
    """개념편 frontmatter에서 hero 메타 추출 (editorial-noir 톤 master of slide 스타일)"""
    hero = {'image': None, 'keywords': [], 'subtitle': None, 'eyebrow': None, 'hook': None}
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
        mm = re.search(r'^' + key + r':\s*[\"\']?([^\"\'\n]+?)[\"\']?\s*$', fm, re.M)
        return mm.group(1).strip() if mm else None
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
    return hero


def build_hero_html(title, hero):
    if not any([hero.get('keywords'), hero.get('image'), hero.get('hook')]):
        return ''
    eyebrow = f'<div class="hero-eyebrow">{hero["eyebrow"]}</div>' if hero.get('eyebrow') else ''
    sub = f'<p class="hero-subtitle">{hero["subtitle"]}</p>' if hero.get('subtitle') else ''
    kws = ''.join(f'<span class="hero-keyword">{k}</span>' for k in (hero.get('keywords') or [])[:6])
    kws_html = f'<div class="hero-keywords">{kws}</div>' if kws else ''
    img = f'<img class="hero-image" src="{hero["image"]}" alt="">' if hero.get('image') else ''
    hook = f'<div class="hero-hook">{hero["hook"]}</div>' if hero.get('hook') else ''
    return f'<section class="hero-section">{eyebrow}<h1 class="hero-title">{title}</h1>{sub}{kws_html}{img}{hook}</section>'


def generate_html(title, content, total, total_ox, submit_url='', mode='class', hero=None):
    """mode: 'class' = 수업용(제출O, 정답보기X), 'review' = 복습용(제출X, 정답보기O)"""
    grand_total = total + total_ox
    hero_html = build_hero_html(title, hero or {})
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
        top_bar = f'''<div class="control-bar">
    <div class="score">
      빈칸: <span id="score">0</span>/{total} · OX: <span id="ox-score">0</span>/{total_ox}
      · 총: <span id="total-score">0</span>/{grand_total} (<span id="pct">0</span>%)
    </div>
    <div>
      {list_btn}
      <button class="btn btn-primary" onclick="check()">채점하기</button>
      {reveal_btn}
      <button class="btn btn-danger" onclick="reset()">초기화</button>
      <button class="btn btn-secondary" onclick="saveProgress()">💾 저장</button>
      {submit_btn}
    </div>
  </div>
  <div class="student-info">
    <input type="text" placeholder="반">
    <input type="text" placeholder="번호">
    <input type="text" placeholder="이름">
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
  max-width: 1040px; margin: 0 auto; background: white;
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
td {{ border: 1px solid #ddd; padding: 7px 10px; vertical-align: top; }}
tr:first-child td {{ background: #f0f4ff; font-weight: 600; }}
blockquote {{
  border-left: 3px solid #007aff; padding: 6px 14px; margin: 6px 0;
  background: #f8f9ff; border-radius: 0 8px 8px 0; font-size: 0.93em;
}}
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
.student-info input {{
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
.hero-keyword {{
  padding: 6px 14px; border: 1px solid #555; border-radius: 20px;
  font-size: 12.5px; color: #d4d4cf; background: rgba(255,255,255,0.05);
  letter-spacing: 0.3px;
}}
.hero-image {{ width: 100%; max-height: 280px; margin-top: 24px; border-radius: 10px; object-fit: cover; }}
.ws-fig {{ max-width: 880px; margin: 22px auto; text-align: center; }}
.ws-fig img {{ max-width: 100%; max-height: 440px; height: auto; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.12); }}
.ws-fig img[src*="comic"] {{ max-height: 820px; max-width: 600px; }}
.ws-fig figcaption {{ margin-top: 8px; font-size: 13px; color: #6b6b6b; line-height: 1.5; padding: 0 8px; }}
.ws-figrow {{ display: flex; gap: 16px; justify-content: center; align-items: flex-start; flex-wrap: wrap; max-width: 1000px; margin: 22px auto; }}
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
  document.getElementById('score').textContent=bc;
  document.getElementById('ox-score').textContent=oxc;
  document.getElementById('total-score').textContent=bc+oxc;
  document.getElementById('pct').textContent=Math.round((bc+oxc)/GT*100);
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
  document.getElementById('score').textContent=0;
  document.getElementById('ox-score').textContent=0;
  document.getElementById('total-score').textContent=0;
  document.getElementById('pct').textContent=0;
}}
// 저장/복원 — 빈칸·OX·서술형(essay)·보기버튼 *전부* localStorage에 보존 (6/8 확장)
function _persist(){{
  const data={{}};
  document.querySelectorAll('.blank-input,.ox-input,.essay-input').forEach((el,i)=>{{
    data[el.dataset.id||el.dataset.answer||('input_'+i)]=el.value;
  }});
  document.querySelectorAll('.ox-group').forEach((g,i)=>{{ data['__sel_'+(g.dataset.id||('ox_'+i))]=g.dataset.selected||''; }});
  document.querySelectorAll('.choice-group').forEach((g,i)=>{{ data['__sel_'+(g.dataset.id||('choice_'+i))]=g.dataset.selected||''; }});
  const si=document.querySelectorAll('.student-info input');
  const info={{class:si[0]?si[0].value:'',number:si[1]?si[1].value:'',name:si[2]?si[2].value:''}};
  try{{ localStorage.setItem('ws_'+document.title, JSON.stringify({{info,data,ts:Date.now()}})); }}catch(e){{}}
}}
function saveProgress(){{ _persist(); alert('저장되었습니다! 같은 기기·브라우저에서 다시 열면 그대로 이어집니다. (다른 PC로 옮기면 안 남으니, 끝나면 꼭 📤 제출!)'); }}
let _autosaveT;
function autosave(){{ clearTimeout(_autosaveT); _autosaveT=setTimeout(_persist,1200); }}
function loadProgress(){{
  let saved; try{{ saved=localStorage.getItem('ws_'+document.title); }}catch(e){{}}
  if(!saved) return;
  let parsed; try{{ parsed=JSON.parse(saved); }}catch(e){{ return; }}
  const info=parsed.info, data=parsed.data;
  if(info){{
    const inputs=document.querySelectorAll('.student-info input');
    if(info.class&&inputs[0]) inputs[0].value=info.class;
    if(info.number&&inputs[1]) inputs[1].value=info.number;
    if(info.name&&inputs[2]) inputs[2].value=info.name;
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
  return ans;
}}
// 진행 탭 — 5/27 비활성화 (제출 학생만 수집·진행 탭 noise 차단)
// 함수 자체는 NO-OP으로 유지 (이벤트 리스너 호환성)
function scheduleProgress(){{ /* disabled — 제출 시점에만 데이터 전송 */ }}
function submitResult(){{
  if(!SUBMIT_URL){{alert('제출 URL이 설정되지 않았습니다.');return;}}
  const cls=document.querySelector('.student-info input:nth-child(1)').value.trim();
  const num=document.querySelector('.student-info input:nth-child(2)').value.trim();
  const name=document.querySelector('.student-info input:nth-child(3)').value.trim();
  if(!cls||!num||!name){{alert('반, 번호, 이름을 모두 입력해주세요. (빈칸은 일부만 채워도 OK)');return;}}
  if(usedReveal){{alert('⚠️ 정답 보기를 사용했기 때문에 제출할 수 없습니다. 초기화 후 다시 풀어주세요.');return;}}
  check(); // 먼저 채점
  const bs=parseInt(document.getElementById('score').textContent);
  const os=parseInt(document.getElementById('ox-score').textContent);
  const ts=parseInt(document.getElementById('total-score').textContent);
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
document.querySelectorAll('.student-info input').forEach(el=>{{
  el.addEventListener('input',scheduleProgress);
}});
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

    title, content, total, total_ox = build_html_from_blank(blank_file, answers, ox_answers, answer_file)
    print(f"🔍 매칭된 빈칸: {total}개, OX: {total_ox}개")

    if total != len(answers):
        print(f"⚠️  빈칸({total})과 정답({len(answers)}) 수 불일치")

    DEFAULT_SUBMIT_URL = os.environ.get('WORKSHEET_SUBMIT_URL', 'https://script.google.com/macros/s/AKfycbwh0_ECTCNjuIq_hOhP_51XpEg2UWlu_nOI5EEpnK_QZBAYEAb6pVUpr3OcKim4m6OSqg/exec')
    submit_url = sys.argv[4] if len(sys.argv) > 4 else DEFAULT_SUBMIT_URL

    hero = extract_hero_meta(blank_file)
    if any([hero.get('keywords'), hero.get('image'), hero.get('hook')]):
        print(f"🎨 hero 섹션: image={'O' if hero.get('image') else 'X'}, keywords={len(hero.get('keywords') or [])}, hook={'O' if hero.get('hook') else 'X'}")

    # 수업용 (제출O, 정답보기X)
    html_class = generate_html(title, content, total, total_ox, submit_url, mode='class', hero=hero)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_class)
    print(f"✅ 수업용 생성: {output_file}")

    # 복습용 (제출X, 정답보기O)
    review_file = output_file.replace('.html', '_복습용.html')
    html_review = generate_html(title, content, total, total_ox, submit_url, mode='review', hero=hero)
    with open(review_file, 'w', encoding='utf-8') as f:
        f.write(html_review)
    print(f"✅ 복습용 생성: {review_file}")

    # 정답편 (교사용·제출X·채점X) — 정답.md를 *본문*으로 렌더(교사섹션 유지) → 빈칸 볼드 정답+OX 해설+모범답안+교사 메타 전부 노출.
    # 2026-06-03: 기존 정답편은 개념편 본문에 답만 보여줘 '정답만' 나가는 문제(로마 사고) → 정답.md 본문 직접 렌더로 교정.
    teacher_file = output_file.replace('.html', '_정답.html')
    t_title, t_content, t_total, t_total_ox = build_html_from_blank(answer_file, [], [], answer_file, teacher=True)
    html_teacher = generate_html(t_title, t_content, t_total, t_total_ox, submit_url, mode='teacher', hero=hero)
    with open(teacher_file, 'w', encoding='utf-8') as f:
        f.write(html_teacher)
    print(f"✅ 정답편(교사용) 생성: {teacher_file}")


if __name__ == '__main__':
    main()
