# 교사 노트 프로퍼티 표준 (2026-04-20)

## 목적
395개 노트 중 다수에 프로퍼티가 있지만 **운영 규칙이 없어 최신본 식별 실패**.
이 문서는 모든 `600_Specialties/**` 노트의 프론트매터 표준이다.

---

## 필수 5필드 (모든 수업용 노트)

| 키 | 타입 | 설명 | 예시 |
|---|---|---|---|
| `lesson_id` | string | 차시 고유 식별자 (파일 rename 무관 영속) | `E05b`, `S01`, `G01-03` |
| `note_role` | enum | 노트 용도 (아래 표준값만) | `concept-sheet` |
| `canonical` | bool | **같은 (lesson_id, note_role) 쌍에 단 1개만 true** | `true` |
| `status` | enum | `active` / `draft` / `archived` / `deprecated` | `active` |
| `updated` | ISO datetime | 최근 수정 시각 (수정 시마다 갱신) | `2026-04-20T13:14` |

## 권장 4필드

| 키 | 타입 | 설명 |
|---|---|---|
| `subject` | string | `역사①`, `사회②` 등 교과 |
| `unit_id` | string | 대단원 식별자 `history1-02` |
| `교과서` | string | `비상교육 역사①(이병인)` |
| `성취기준` | string | `[9역02-03]` |

## 선택 필드
`담당교사`, `차시`, `version`, `aliases`, `related`, `sources`, `tags`

---

## `note_role` 표준 enum (13→7개로 축소)

| 표준값 | 용도 | 이전값(흡수) |
|---|---|---|
| `concept-sheet` | 학생용 개념편 (빈칸 포함) | — |
| `answer-key` | 개념편 정답 | `concept-sheet` 정답 파일 포함 금지 (별도) |
| `materials-pack` | 자료편·보조자료 | — |
| `teacher-guide` | 교사용 해설·진행 가이드 | — |
| `student-handout` | 인쇄 배포용 학습지 | `gamma-export` 흡수 |
| `quiz` | 띵커벨·카훗·퀴즈 | `thinkerbell-quiz` 통합 |
| `assessment` | 평가용 문항·루브릭 | — |

비표준값 (`note`, `planning`, `template`, `auto-research`, `slides`, `operations-rule`)은 수업용 아님 → `600_Specialties/` 외부로 이동 권장.

---

## `canonical` 운영 규칙

1. **unique(lesson_id, note_role)** = canonical:true 는 **쌍당 1개**
2. 새 버전 작성 시 자동 절차:
   - 이전 canonical → `canonical: false`, `status: archived`
   - 새 파일 → `canonical: true`, `status: active`
3. 파일명 `_v2`, `_v3` suffix는 **보조 표기일 뿐 공식 구분자 아님**. canonical/updated가 진실.

---

## `updated` 필수화
모든 수업용 노트는 수정 시마다 `updated: YYYY-MM-DDTHH:MM` 갱신.  
누락된 기존 노트는 **파일 mtime으로 보정** 가능 (lint 스크립트 제공 예정).

---

## Archive 정책
- `status: archived` + `canonical: false` 만 붙이고 파일은 **삭제하지 않음** (추적성)
- 폴더 이동도 기본 하지 않음 — 같은 단원 폴더 내에 같이 둠
- 단, 3개월 이상 archived 상태면 연 1회 `900_Archive/` 로 이동 검토

---

## Lint 체크리스트 (자동 검증)
- [ ] 필수 5필드 모두 존재
- [ ] `canonical:true` 유일성
- [ ] `note_role` 표준 enum
- [ ] `updated` 갱신 여부 (파일 mtime과 격차 ≤ 7일)
- [ ] `status` 유효값
