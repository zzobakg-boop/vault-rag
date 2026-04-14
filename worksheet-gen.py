#!/usr/bin/env python3
"""마크다운 개념편 → 인터랙티브 HTML 학습지 자동 생성기 v2
정답 파일에서 답을 순서대로 추출하고, 개념편의 빈칸에 순서대로 매칭한다."""

import re
import sys
import os


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


def build_html_from_blank(blank_file, answers, ox_answers, answer_file):
    """개념편 파일을 읽고, 빈칸을 input으로 교체하여 HTML 생성"""
    with open(blank_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

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

    for line in lines:
        stripped = line.strip()

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
            html_parts.append(line.rstrip() + '\n')
            continue

        # 빈 div (서술형 답안 칸) → 서술형 textarea로 변환
        if '<div style="height:' in stripped:
            html_parts.append('<textarea class="essay-input" placeholder="서술형 답안을 작성하세요"></textarea>')
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
                    input_html = (
                        f'<input type="text" class="blank-input" '
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
                    total_blanks += 1
            line = new_line

        # 마크다운 → HTML
        stripped = line.strip()

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
                    cells[-1] = f'<input type="text" class="ox-input" data-answer="{ox_answer}" placeholder="O/X" style="width:40px;text-align:center">'

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
            result.append(part)
    return ''.join(result)


def generate_html(title, content, total, total_ox, submit_url=''):
    grand_total = total + total_ox
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
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
.ox-input {{
  border: 1px solid #ddd; padding: 3px; font-size: 0.93em;
  font-family: inherit; border-radius: 4px; outline: none;
  transition: all 0.3s;
}}
.ox-input.correct {{ border-color: #34c759; background: #e8f8e8; color: #1a7a2e; }}
.ox-input.wrong {{ border-color: #ff3b30; background: #fff0f0; }}
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
}}
</style>
</head>
<body>
<div class="container">
  <div class="control-bar">
    <div class="score">
      빈칸: <span id="score">0</span>/{total} · OX: <span id="ox-score">0</span>/{total_ox}
      · 총: <span id="total-score">0</span>/{grand_total} (<span id="pct">0</span>%)
    </div>
    <div>
      <button class="btn btn-primary" onclick="check()">채점하기</button>
      <button class="btn btn-secondary" onclick="reveal()">정답 보기</button>
      <button class="btn btn-danger" onclick="reset()">초기화</button>
      <button class="btn btn-secondary" onclick="saveProgress()">💾 저장</button>
      <button class="btn btn-primary" onclick="submitResult()" id="submitBtn">📤 제출</button>
    </div>
  </div>
  <div class="student-info">
    <input type="text" placeholder="반">
    <input type="text" placeholder="번호">
    <input type="text" placeholder="이름">
  </div>
  {content}
</div>
<script>
const TB={total}, TOX={total_ox}, GT={grand_total};
function selectChoice(btn, val){{
  const grp=btn.parentElement;
  grp.querySelectorAll('.choice-btn').forEach(b=>b.classList.remove('selected'));
  btn.classList.add('selected');
  grp.dataset.selected=val;
}}
function norm(s){{return s.replace(/\\s+/g,'').replace(/[·,.()（）\\[\\]]/g,'').toLowerCase();}}
function check(){{
  let bc=0, oxc=0;
  document.querySelectorAll('.blank-input').forEach(el=>{{
    const a=norm(el.dataset.answer), u=norm(el.value);
    if(!u){{el.classList.remove('correct','wrong');return;}}
    if(u===a||a.includes(u)&&u.length>=a.length*0.6){{
      el.classList.add('correct');el.classList.remove('wrong');bc++;
    }}else{{el.classList.add('wrong');el.classList.remove('correct');}}
  }});
  document.querySelectorAll('.ox-input').forEach(el=>{{
    const a=el.dataset.answer, u=el.value.trim().toUpperCase();
    if(!u){{el.classList.remove('correct','wrong');return;}}
    if(u===a){{
      el.classList.add('correct');el.classList.remove('wrong');oxc++;
    }}else{{el.classList.add('wrong');el.classList.remove('correct');}}
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
  document.querySelectorAll('.blank-input').forEach(el=>{{
    el.value=el.dataset.answer;el.classList.add('correct');el.classList.remove('wrong');
  }});
  document.querySelectorAll('.ox-input').forEach(el=>{{
    el.value=el.dataset.answer;el.classList.add('correct');el.classList.remove('wrong');
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
  document.querySelectorAll('.blank-input,.ox-input').forEach(el=>{{
    el.value='';el.classList.remove('correct','wrong');
  }});
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
function saveProgress(){{
  const data={{}};
  document.querySelectorAll('.blank-input,.ox-input').forEach(el=>{{
    data[el.dataset.id||el.dataset.answer]=el.value;
  }});
  const info={{
    class:document.querySelector('.student-info input:nth-child(1)').value,
    number:document.querySelector('.student-info input:nth-child(2)').value,
    name:document.querySelector('.student-info input:nth-child(3)').value
  }};
  localStorage.setItem('ws_'+document.title, JSON.stringify({{info,data,ts:Date.now()}}));
  alert('저장되었습니다! 다음에 이 페이지를 열면 자동으로 불러옵니다.');
}}
function loadProgress(){{
  const saved=localStorage.getItem('ws_'+document.title);
  if(!saved) return;
  const {{info,data}}=JSON.parse(saved);
  if(info){{
    const inputs=document.querySelectorAll('.student-info input');
    if(info.class) inputs[0].value=info.class;
    if(info.number) inputs[1].value=info.number;
    if(info.name) inputs[2].value=info.name;
  }}
  if(data){{
    document.querySelectorAll('.blank-input,.ox-input').forEach(el=>{{
      const key=el.dataset.id||el.dataset.answer;
      if(data[key]) el.value=data[key];
    }});
  }}
}}
// 모든 입력칸에서 Enter→다음칸 이동
const allInputs=[...document.querySelectorAll('.blank-input,.ox-input')];
allInputs.forEach((el,i)=>{{
  el.addEventListener('keydown',e=>{{
    if(e.key==='Enter'){{e.preventDefault();if(i+1<allInputs.length)allInputs[i+1].focus();else check();}}
  }});
}});
// 제출
const SUBMIT_URL='{submit_url}';
function submitResult(){{
  if(!SUBMIT_URL){{alert('제출 URL이 설정되지 않았습니다.');return;}}
  const cls=document.querySelector('.student-info input:nth-child(1)').value.trim();
  const num=document.querySelector('.student-info input:nth-child(2)').value.trim();
  const name=document.querySelector('.student-info input:nth-child(3)').value.trim();
  if(!cls||!num||!name){{alert('반, 번호, 이름을 모두 입력해주세요.');return;}}
  check(); // 먼저 채점
  const bs=parseInt(document.getElementById('score').textContent);
  const os=parseInt(document.getElementById('ox-score').textContent);
  const ts=parseInt(document.getElementById('total-score').textContent);
  const data={{
    worksheet:document.title,
    studentClass:cls,studentNumber:num,studentName:name,
    blankScore:bs,oxScore:os,totalScore:ts
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

    submit_url = sys.argv[4] if len(sys.argv) > 4 else ''
    html = generate_html(title, content, total, total_ox, submit_url)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ 생성 완료: {output_file}")


if __name__ == '__main__':
    main()
