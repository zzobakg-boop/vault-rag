/**
 * 학습지 제출 서버 v2 (2026-05-27)
 *
 * v1 → v2 변경:
 *   - *활동* 탭 신설 — 학생 활동 답을 펼친 컬럼으로 시각화
 *   - act-N (활동 input) 키만 추출 → 학생당 1 row upsert
 *   - 컬럼은 동적 확장 (새 act-N 키 발견 시 자동 추가)
 *   - 기존 *제출*·*진행* 탭은 그대로 유지 (호환성)
 */
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const tabName = data.type === 'progress' ? '진행' : '제출';
    let tab = ss.getSheetByName(tabName);

    if (!tab) {
      tab = ss.insertSheet(tabName);
      if (tabName === '진행') {
        tab.appendRow(['시각', '학습지', '반', '번호', '답(JSON)', '입력개수']);
      } else {
        tab.appendRow(['시각', '학습지', '반', '번호', '이름', '빈칸', 'OX', '총점', '답(JSON)']);
      }
    }

    const ts = new Date();
    const ws = data.worksheet || '';
    const cls = String(data.studentClass || '');
    const num = String(data.studentNumber || '');

    if (data.type === 'progress') {
      // Upsert: 같은 (학습지·반·번호) 1줄만 유지
      const rows = tab.getDataRange().getValues();
      let foundRow = -1;
      for (let i = 1; i < rows.length; i++) {
        if (rows[i][1] === ws && String(rows[i][2]) === cls && String(rows[i][3]) === num) {
          foundRow = i + 1;
          break;
        }
      }
      const answersJson = JSON.stringify(data.answers || {});
      const answerCount = Object.keys(data.answers || {}).length;
      const row = [ts, ws, cls, num, answersJson, answerCount];
      if (foundRow > 0) {
        tab.getRange(foundRow, 1, 1, row.length).setValues([row]);
      } else {
        tab.appendRow(row);
      }
    } else {
      // 기존 *제출* 탭 (변경 X)
      tab.appendRow([ts, ws, cls, num, data.studentName,
                     data.blankScore, data.oxScore, data.totalScore,
                     JSON.stringify(data.answers || {})]);

      // ⭐ 신규: *활동* 탭에 학생 활동 답 펼치기
      upsertActivityRow(ss, ts, ws, cls, num, data.studentName, data.answers || {});
    }

    return ContentService.createTextOutput(JSON.stringify({ok: true}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok: false, error: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * 학생 활동 답을 *활동* 탭에 펼침 — 학생당 1 row upsert·컬럼 동적 확장
 *
 * @param ss Spreadsheet
 * @param ts 제출 시각
 * @param ws 학습지 제목
 * @param cls 반
 * @param num 번호
 * @param name 학생 이름
 * @param answers collectAnswers() 결과 객체
 */
function upsertActivityRow(ss, ts, ws, cls, num, name, answers) {
  // act-N 키만 추출·번호 순 정렬
  const actEntries = Object.keys(answers)
    .filter(k => k.indexOf('act-') === 0)
    .sort((a, b) => parseInt(a.split('-')[1]) - parseInt(b.split('-')[1]));

  if (actEntries.length === 0) return;  // 활동 input 없는 학습지는 skip

  let actTab = ss.getSheetByName('활동');
  if (!actTab) {
    actTab = ss.insertSheet('활동');
    actTab.appendRow(['시각', '학습지', '반', '번호', '이름']);
  }

  // 현재 header 읽기
  let headers = actTab.getRange(1, 1, 1, actTab.getLastColumn()).getValues()[0];

  // 새 act-N 키가 있으면 header에 추가 (동적 컬럼 확장)
  actEntries.forEach(k => {
    if (headers.indexOf(k) === -1) {
      actTab.getRange(1, headers.length + 1).setValue(k);
      headers.push(k);
    }
  });

  // upsert: 같은 (학습지·반·번호) 1줄 유지
  const rows = actTab.getDataRange().getValues();
  let foundRow = -1;
  for (let i = 1; i < rows.length; i++) {
    if (rows[i][1] === ws && String(rows[i][2]) === cls && String(rows[i][3]) === num) {
      foundRow = i + 1;
      break;
    }
  }

  // row 구성: 시각·학습지·반·번호·이름 + header act-N 컬럼별 값
  const baseRow = [ts, ws, cls, num, name];
  const actRow = headers.slice(5).map(h => answers[h] || '');
  const fullRow = baseRow.concat(actRow);

  if (foundRow > 0) {
    // 기존 row 갱신 — 길이 안 맞으면 빈 값으로 패딩
    while (fullRow.length < headers.length) fullRow.push('');
    actTab.getRange(foundRow, 1, 1, fullRow.length).setValues([fullRow]);
  } else {
    actTab.appendRow(fullRow);
  }
}

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({ok: true, msg: '학습지 제출 서버 v2 정상'}))
    .setMimeType(ContentService.MimeType.JSON);
}
