/**
 * 학습지 결과 수신 Google Apps Script (v2 — 재제출 시 덮어쓰기)
 *
 * 설정 방법:
 * 1. Google 스프레드시트 생성 (이름: "학습지_결과")
 * 2. 확장 프로그램 → Apps Script 클릭
 * 3. 이 코드를 전체 붙여넣기
 * 4. 배포 → 새 배포 → 유형: 웹 앱
 *    - 실행 계정: 본인
 *    - 액세스 권한: "모든 사용자" (구글 로그인 불필요)
 * 5. 배포 후 나오는 URL을 복사
 *
 * 재제출: 같은 반+번호+이름이면 기존 행을 덮어씀 (최신 결과만 유지)
 */

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();

    // 학습지별 시트 생성/가져오기
    var sheetName = data.worksheet || "기타";
    var sheet = ss.getSheetByName(sheetName);
    if (!sheet) {
      sheet = ss.insertSheet(sheetName);
      sheet.getRange(1, 1, 1, 7).setValues([[
        "제출시각", "반", "번호", "이름", "빈칸 점수", "OX 점수", "총점"
      ]]);
      sheet.getRange(1, 1, 1, 7).setFontWeight("bold");
    }

    var newRow = [
      new Date().toLocaleString("ko-KR", {timeZone: "Asia/Seoul"}),
      data.studentClass || "",
      data.studentNumber || "",
      data.studentName || "",
      data.blankScore || 0,
      data.oxScore || 0,
      data.totalScore || 0
    ];

    // 같은 반+번호+이름 찾기 → 덮어쓰기
    var lastRow = sheet.getLastRow();
    var found = false;
    if (lastRow > 1) {
      var existing = sheet.getRange(2, 2, lastRow - 1, 3).getValues(); // 반, 번호, 이름
      for (var i = 0; i < existing.length; i++) {
        if (String(existing[i][0]) === String(data.studentClass) &&
            String(existing[i][1]) === String(data.studentNumber) &&
            String(existing[i][2]) === String(data.studentName)) {
          // 기존 행 덮어쓰기
          sheet.getRange(i + 2, 1, 1, 7).setValues([newRow]);
          found = true;
          break;
        }
      }
    }

    if (!found) {
      sheet.appendRow(newRow);
    }

    return ContentService
      .createTextOutput(JSON.stringify({status: "ok", updated: found}))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({status: "error", message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService
    .createTextOutput("학습지 결과 수신 서버가 작동 중입니다. (v2)")
    .setMimeType(ContentService.MimeType.TEXT);
}
