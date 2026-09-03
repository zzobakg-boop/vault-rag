# 인물 도트 출처·라이선스

**방식 = D안 (LPC 몸체 + PIL 자작 소품)** — 2026-09-03 채택.

## 몸·복장·머리
Liberated Pixel Cup · Universal-LPC-Spritesheet-Character-Generator
https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator

🔴 **다중 라이선스는 택일**이므로 `OGA-BY 3.0` 또는 `CC0` 선택지가 있는 레이어만 쓴다
(ShareAlike 의무 없이 저작자 표시만으로 사용). 사용 레이어:

- `body/bodies/male/idle.png`
- `head/heads/human/male/idle.png`
- `torso/clothes/longsleeve/longsleeve/male/idle.png`
- `legs/pants/male/idle.png`
- `feet/shoes/revised/male/idle.png`
- `hair/plain/adult/idle.png` · `hair/curly_short/adult/idle.png`

## 소품 (자작)
택배상자 · 밀짚모자+카메라 · 노트북+코인 · 안전모+궤짝 · 캐리어+여권 —
**LPC에 현대 소품 레이어가 없어 PIL로 직접 그렸다.**
8/31 역사(중2)가 왕관·낫·도끼를 같은 이유로 직접 그린 것과 같은 처방이다.

유학생 가정의 아이는 **같은 스프라이트를 62% 축소**한 것 — 일관성이 구조적으로 보장된다.

## 왜 이 방식인가 (2026-09-03 4안 비교)
| | 현대소품 | 일관성 | 72px 식별 | 라이선스 | 고유색 |
|---|:--:|:--:|:--:|:--:|---|
| A LPC 단독 | ❌ | ✅✅ | ❌ | ✅ | 34색 |
| B Grok 이미지 | ✅ | 🔶 | ✅✅ | 🔴 | 20,823색 |
| C Grok Build 코드 | ✅ | ✅ | ✅✅ | ✅ | 14색 |
| **D LPC+PIL** | ✅ | ✅✅ | ✅ | ✅ | 32~40색 |

🔴 **B 탈락은 기술이 아니라 라이선스** — xAI ToS가 2026-09-01 개정되어 출처 표기가
권유에서 요구로 바뀐 정황이 있고(원문 확인이 403으로 막혀 불명 구간), 학습지는
공개 GitHub Pages로 나간다.
🔬 부수 발견 — **이미지 모델은 진짜 도트를 못 만든다.** 고유색 2만 개가 넘고 런길이가
격자 배수가 아니다. 도트처럼 보이는 그림일 뿐이다.

⚠️ **생성 스크립트 미보유** — 시스템 레인에 요청함. 받으면 이 폴더에 함께 둔다.
