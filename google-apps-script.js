/**
 * 학습지 결과 수신 Google Apps Script
 *
 * 설정 방법:
 * 1. Google 스프레드시트 생성 (이름: "학습지_결과")
 * 2. 확장 프로그램 → Apps Script 클릭
 * 3. 이 코드를 전체 붙여넣기
 * 4. 배포 → 새 배포 → 유형: 웹 앱
 *    - 실행 계정: 본인
 *    - 액세스 권한: "모든 사용자" (구글 로그인 불필요)
 * 5. 배포 후 나오는 URL을 복사
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
      // 헤더 추가
      sheet.getRange(1, 1, 1, 7).setValues([[
        "제출시각", "반", "번호", "이름", "빈칸 점수", "OX 점수", "총점"
      ]]);
      sheet.getRange(1, 1, 1, 7).setFontWeight("bold");
    }

    // 데이터 추가
    sheet.appendRow([
      new Date().toLocaleString("ko-KR", {timeZone: "Asia/Seoul"}),
      data.studentClass || "",
      data.studentNumber || "",
      data.studentName || "",
      data.blankScore || 0,
      data.oxScore || 0,
      data.totalScore || 0
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({status: "ok"}))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({status: "error", message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService
    .createTextOutput("학습지 결과 수신 서버가 작동 중입니다.")
    .setMimeType(ContentService.MimeType.TEXT);
}
