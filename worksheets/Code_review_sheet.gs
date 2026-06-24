/**
 * 학습지 제출 → "보기 편한 정리 시트" 후처리 (읽기 전용·원본 무손상)
 * ────────────────────────────────────────────────────────────
 * 통증: 제출 탭은 학생 1명=1행 + 답(JSON) 통블롭 + act-N 가로 수십 칸 → 가로 스크롤·JSON 헤집기.
 * 해결: 현재 보고 있는 제출 탭을 읽어 "📋 정리·<탭>" 시트를 만든다.
 *   - 학생 1명 = 세로 블록 (반-번호 이름 / 총점 / 문항=행·답=옆 칸)
 *   - 긴 서술답은 셀 안 줄바꿈(WRAP) + 행 높이 자동
 *   - 같은 학생 여러 번 제출 시 *마지막 제출*만
 *   - 점수 색칠(조건부서식)
 *
 * 설치: 제출 수합 스프레드시트 → 확장 프로그램 → Apps Script → 이 코드 추가(별도 파일 가능) → 저장.
 *       스프레드시트 새로고침하면 상단에 "📋 정리 도구" 메뉴가 생김.
 * 사용: 정리하고 싶은 학습지 탭을 클릭 → 메뉴 → "이 탭 → 정리 시트".
 * 무료: 컨테이너 바인딩이라 배포·과금 불필요(Workspace 일일 쿼터 내).
 */

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📋 정리 도구')
    .addItem('이 탭 → 정리 시트', 'buildReviewSheet')
    .addToUi();
}

// 답 칸으로 보지 않을 기본(메타) 컬럼
var META_COLS_ = ['시각', '학습지', '반', '번호', '이름', '빈칸', 'OX', '총점', '답(JSON)'];

function buildReviewSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var src = ss.getActiveSheet();
  var srcName = src.getName();
  if (srcName.indexOf('📋 정리') === 0) {
    SpreadsheetApp.getUi().alert('제출 탭(원본)을 선택한 뒤 다시 실행하세요. (지금은 정리 시트입니다)');
    return;
  }

  var values = src.getDataRange().getValues();
  if (values.length < 2) { SpreadsheetApp.getUi().alert('이 탭에 제출 데이터가 없습니다.'); return; }
  var head = values[0];
  var idx = {};
  head.forEach(function (h, i) { idx[String(h).trim()] = i; });

  // 답 칸 = 메타가 아닌 모든 컬럼(act-N 등) + 답(JSON) 파싱 보강
  var answerCols = [];
  head.forEach(function (h, i) {
    var name = String(h).trim();
    if (META_COLS_.indexOf(name) === -1 && name !== '') answerCols.push({ name: name, i: i });
  });

  // 학생별 최신 제출만 (반-번호 키, 시각 최댓값)
  var byStudent = {};
  for (var r = 1; r < values.length; r++) {
    var row = values[r];
    var cls = idx['반'] != null ? row[idx['반']] : '';
    var num = idx['번호'] != null ? row[idx['번호']] : '';
    var key = cls + '-' + num;
    var ts = idx['시각'] != null ? new Date(row[idx['시각']]).getTime() : r;
    if (!byStudent[key] || ts >= byStudent[key]._ts) { row._ts = ts; byStudent[key] = row; }
  }
  // 반→번호 순 정렬
  var keys = Object.keys(byStudent).sort(function (a, b) {
    var pa = a.split('-'), pb = b.split('-');
    return (pa[0] + '').localeCompare(pb[0] + '') || (Number(pa[1]) - Number(pb[1]));
  });

  // 출력 시트
  var outName = '📋 정리·' + srcName;
  var out = ss.getSheetByName(outName);
  if (out) out.clear(); else out = ss.insertSheet(outName);

  var block = [];                 // [문항, 답] 2열
  var scoreRows = [];             // 점수 강조용 행 번호
  keys.forEach(function (key) {
    var row = byStudent[key];
    var name = idx['이름'] != null ? row[idx['이름']] : '';
    var score = idx['총점'] != null ? row[idx['총점']] : '';
    var blank = idx['빈칸'] != null ? row[idx['빈칸']] : '';
    var ox = idx['OX'] != null ? row[idx['OX']] : '';
    block.push(['▎' + key + '  ' + name, '총점 ' + score + '  (빈칸 ' + blank + ' · OX ' + ox + ')']);
    scoreRows.push(block.length);     // 1-indexed (헤더 없음)

    // 답(JSON) 우선 파싱(키 풍부) → 없으면 answerCols
    var ans = {};
    if (idx['답(JSON)'] != null && row[idx['답(JSON)']]) {
      try { ans = JSON.parse(row[idx['답(JSON)']]); } catch (e) { ans = {}; }
    }
    var labels = ans['__labels'] || {};   // 제작 시점 문항 라벨(있으면 act-N 대신 표시)
    var ansKeys = Object.keys(ans).filter(function (k) { return k !== '__labels'; });
    if (ansKeys.length) {
      ansKeys.forEach(function (k) {
        var v = ans[k];
        if (v === '' || v == null) return;
        block.push([labels[k] || k, String(v)]);
      });
    } else {
      answerCols.forEach(function (c) {
        var v = row[c.i];
        if (v === '' || v == null) return;
        block.push([c.name, String(v)]);
      });
    }
    block.push(['', '']);             // 학생 사이 빈 줄
  });

  if (!block.length) { SpreadsheetApp.getUi().alert('정리할 답이 없습니다.'); return; }

  var rng = out.getRange(1, 1, block.length, 2);
  rng.setValues(block);
  out.setColumnWidth(1, 230);
  out.setColumnWidth(2, 560);
  out.getRange(1, 2, block.length, 1).setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP); // 서술답 줄바꿈
  out.getRange(1, 1, block.length, 1).setVerticalAlignment('top');
  out.getRange(1, 2, block.length, 1).setVerticalAlignment('top');

  // 학생 헤더 행 굵게·배경
  scoreRows.forEach(function (rn) {
    out.getRange(rn, 1, 1, 2).setFontWeight('bold').setBackground('#e8f0fe');
  });

  // 긴 답 행 높이 자동 조정
  out.autoResizeRows(1, block.length);

  out.activate();
  SpreadsheetApp.getUi().alert('완료: "' + outName + '" 시트 생성 (' + keys.length + '명, 최신 제출 기준).');
}
