#!/usr/bin/env python3
"""EIC 전사 정리 스킬 — 전사 원문을 구조화된 요약 노트로 변환

사용법:
  python3 eic-transcription.py <전사파일.md> <출력파일.md>
  python3 eic-transcription.py <전사파일.md>  # 같은 폴더에 _정리.md 생성

EIC = Extract(핵심 추출) → Interpret(해석/구조화) → Compose(노트 작성)
"""

import sys
import os
import re


def extract_metadata(content):
    """전사 파일에서 메타데이터 추출"""
    meta = {}
    # 제목
    title_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
    if title_match:
        meta['title'] = title_match.group(1).strip()

    # 전사량
    char_match = re.search(r'전사량[:\s]*(\d[\d,]+)자', content)
    if char_match:
        meta['char_count'] = char_match.group(1)

    # 강의 번호
    num_match = re.search(r'강의\s*번호[:\s]*(\S+)', content)
    if num_match:
        meta['lecture_num'] = num_match.group(1)

    return meta


def chunk_text(text, chunk_size=3000):
    """텍스트를 청크로 분할 (문단 기준)"""
    paragraphs = text.split('\n\n')
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current)
            current = para
        else:
            current = current + "\n\n" + para if current else para

    if current:
        chunks.append(current)

    return chunks


def generate_summary_prompt(content, meta):
    """요약 프롬프트 생성 (Claude Code에서 직접 실행할 때 사용)"""
    title = meta.get('title', '강의')

    prompt = f"""아래 전사 원문을 읽고 구조화된 요약 노트를 작성해주세요.

## 형식

### 1. 강의 개요 (2~3줄)
### 2. 핵심 내용 (섹션별 구분, 상세하게)
### 3. 실전 적용 포인트 (우리 시스템에 도입 가능한 것)
### 4. 소개된 도구/기술 목록 (표)
### 5. 핵심 인사이트 (3~5개)

## 원칙
- 원문에 있는 내용만 정리 (추측 금지)
- 구체적 수치, 이름, 명령어 등은 정확히 기재
- 현재 우리 시스템(Claude Code 올인원, vault-rag, Obsidian Geo-Teacher)에 적용 가능한 것에 표시

## 전사 원문:

{content[:50000]}
"""
    return prompt


def create_output_template(meta):
    """출력 마크다운 템플릿 생성"""
    title = meta.get('title', '강의')
    lecture_num = meta.get('lecture_num', '')
    char_count = meta.get('char_count', '')

    return f"""---
type: note
aliases:
  - "{title} 정리"
author:
  - "[[제이콥]]"
date created: {{date}}
date modified: {{date}}
tags:
  - 강의정리
  - EIC
source: "전사본"
status: completed
---

# {title} — EIC 정리

> 강의 번호: {lecture_num}
> 원본 전사량: {char_count}자
> 정리 방식: EIC (Extract→Interpret→Compose)

---

{{content}}
"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 eic-transcription.py <전사파일.md> [출력파일.md]")
        print("\n전사 원문을 구조화된 요약 노트로 변환합니다.")
        print("Claude Code에서 직접 실행하면 AI가 요약을 생성합니다.")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.md', '_정리.md')

    if not os.path.exists(input_file):
        print(f"❌ 파일 없음: {input_file}")
        sys.exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    meta = extract_metadata(content)
    print(f"📄 입력: {os.path.basename(input_file)}")
    print(f"📊 전사량: {meta.get('char_count', '?')}자")
    print(f"📋 제목: {meta.get('title', '?')}")

    # 프롬프트 생성 (Claude Code에서 사용)
    prompt = generate_summary_prompt(content, meta)

    # 프롬프트를 임시 파일로 저장
    prompt_file = output_file.replace('.md', '_prompt.txt')
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)

    print(f"\n✅ 프롬프트 생성: {prompt_file}")
    print(f"📝 출력 예정: {output_file}")
    print(f"\n💡 다음 단계:")
    print(f"   claude -p \"$(cat {prompt_file})\" > {output_file}")
    print(f"   또는 제이콥에게 '이 전사본 정리해줘'라고 요청하세요.")


if __name__ == '__main__':
    main()
