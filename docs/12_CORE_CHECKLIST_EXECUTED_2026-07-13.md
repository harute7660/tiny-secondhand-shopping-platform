# PDF 25~29페이지 시스템 기능 실제 수행 결과 - 2026-07-13

`11_CORE_SUBMISSION_CHECKLIST.md`의 14개 항목을 PDF 원문, Django route·model·view·template, 관련 자동 테스트와 대조한 결과다. 기능 일부만 존재하면 `PASS`로 올리지 않았다.

## 검사 기준

- 대상 commit: `bb890761a7998a015bcf36ab9c62a8daea46d7db` (`3467642` 이후 Python·template·CSS·workflow·lock 기능 파일 diff 0건)
- 완료 시각: `2026-07-13 16:53:49 +09:00`
- 원문 확인: PDF 25~29페이지를 PNG 렌더링과 텍스트 추출로 교차검토
- 코드 확인: `accounts`·`market` route 목록, User·Listing·Report 필드, view·template·테스트 정적 대조
- 자동 증적: 아래 관련 5개 테스트 클래스 67개가 46.119초에 통과; 전체 120개 통과 스냅샷은 SEC-031 분기가 빠졌으므로 보조 증적으로만 사용
- 판정: `PASS` / `PARTIAL` / `FAIL`

```powershell
.\.venv\Scripts\python.exe manage.py test `
  accounts.tests.SignupSecurityTests `
  accounts.tests.LoginSecurityTests `
  market.tests.ListingSecurityTests `
  market.tests.ConversationSecurityTests `
  market.tests.ModerationSecurityTests `
  --verbosity 1
```

실제 출력은 `Found 67 test(s)`, `System check identified no issues`, `Ran 67 tests in 46.119s`, `OK`, exit code 0이었다.

## 수행 결과

| ID | 상태 | 직접 확인한 구현·증적 | 미충족 조건 / 다음 조치 |
|---|:---:|---|---|
| F-01 | **PASS** | `signup`, `login`, `logout` route와 가입·로그인 회귀가 있음. 사용자명은 정규화·대소문자 무관 UNIQUE이며 Django password hash로 저장됨 | 최종 기능 변경 뒤 재회귀 |
| F-02 | **FAIL** | 상품 상세에 판매자 이름·가입일·완료 건수 요약만 표시됨 | 공개 profile route·template와 소개글 필드가 없음 |
| F-03 | **FAIL** | User 필드와 account route를 직접 조회함 | User에 소개글이 없고 마이페이지·본인 소개글 수정·본인 비밀번호 변경 route가 없음. Admin 비밀번호 reset은 대체 기능이 아님 |
| F-04 | **PASS** | `listing_create`, `ListingForm`, Listing의 제목·설명·가격·이미지·판매자 필드와 상품 등록 회귀가 있음 | 사진 필수 여부는 원문 해석을 보고서에 명시; 이미지 변경 결함은 F-05에서 별도 판정 |
| F-05 | **PARTIAL** | `?mine=1` queryset과 소유자 전용 수정·상태변경·soft delete가 있음 | 내 상품 목록으로 가는 노출 UI가 없고 기존 이미지 삭제는 SEC-031 500이 발생함 |
| F-06 | **PASS** | 홈에서 익명 사용자에게 공개 상품을 보여주고 차단·삭제·정지 판매자의 상품을 제외함 | 최종 샘플 데이터로 수동 확인 권장 |
| F-07 | **PASS** | UUID 상세 route와 상품명·설명·가격·사진·판매자 요약 화면이 있음 | 타인 비공개 상품 접근거부 유지 |
| F-08 | **FAIL** | route·model·설치 앱을 직접 조회함 | 전체 채팅 모델·route·화면이 없고 Channels/WebSocket·SSE·polling 같은 실시간 갱신 방식도 없음 |
| F-09 | **PASS** | 상품별 buyer/seller `Conversation`·`Message`, 참여자 조회·전송 제한과 차단 회귀가 있음 | 실시간 push는 아니지만 PDF는 1대1 항목에 별도로 실시간을 명시하지 않음 |
| F-10 | **PASS** | 상품과 실제 대화 상대 신고, 필수 `details`, 서버 결정 reporter·target, 증거 snapshot과 관련 회귀가 있음 | 신고 누적 자동조치는 F-11·12에서 별도 판정 |
| F-11 | **FAIL** | 관리자의 수동 상품 block·purge action은 존재함 | 대상별 신고 횟수 임계치와 도달 시 자동 차단·삭제가 없음 |
| F-12 | **FAIL** | 관리자의 수동 사용자 정지 action과 정지 계정 로그인 차단은 존재함 | 신고 횟수 임계치 기반 자동 휴면·정지가 없고 별도 휴면 상태도 없음 |
| F-13 | **PARTIAL** | 홈·가입·로그인·상품 목록·등록·상세·신고·1대1 대화 화면은 존재함 | 사용자 프로필·마이페이지·실시간 전체 채팅 화면과 UI 접근 경로가 없음 |
| F-14 | **PARTIAL** | Listing과 Report는 원문 필드보다 강한 FK·제약과 신고 대상을 분리한 구조를 가짐. 비밀번호는 해시 저장됨 | User 소개글과 전체 채팅용 데이터 구조가 없음 |

## 집계와 결론

- PASS: **6 / 14**
- PARTIAL: **3 / 14**
- FAIL: **5 / 14**
- 시스템 기능 완료: **NOT READY**

우선 구현 순서는 사용자 프로필·마이페이지, 실시간 전체 채팅, 누적 신고 정책, 내 상품 관리 접근성·SEC-031 수정이다. 이후 F-01~14를 전부 다시 실행해야 한다. 기존의 `11 PASS / 5 FAIL / 2 BLOCKED`는 제출·보안 항목이 섞인 다른 범위였으므로 이 시스템 기능 완료 판정으로 사용하지 않는다.
