# PDF 25~29페이지 시스템 기능 실제 수행 결과 - 2026-07-13

`11_CORE_SUBMISSION_CHECKLIST.md`의 14개 항목을 PDF 원문, Django route·model·view·template, 관련 자동 테스트와 다시 대조한 결과다. 아래의 현재 판정은 같은 날 앞서 기록한 6 PASS / 3 PARTIAL / 5 FAIL 스냅샷을 대체한다.

## 현재 검사 기준

- 대상: 2026-07-13 작업트리. 최종 commit SHA는 commit 뒤 갱신한다.
- 최초 완료 시각: `2026-07-13 17:43 +09:00`; 후속 문서 재대조: `2026-07-13 21:49 +09:00`
- 코드 확인: `accounts`·`community`·`market`·`config`의 route, model, migration, view, form, template, 정적 JavaScript, Admin, test를 직접 대조했다.
- 자동 증적: 공개 프로필·마이페이지·전체 채팅·상품·신고 변경 범위의 6개 테스트 클래스 **79개**가 53.066초에 통과했다.
- 직전 전체 suite: 세 확장 기능 포함 **206개 전부 통과 / 114.641초**, 당시 Coverage **5,778 statements / 343 miss / 94%**였다. 이후 SEC-047을 포함한 최신 결합 표적 **40개 / 17.697초 / system check 0건 / Ruff PASS**가 통과했다. 최신 변경 뒤 전체 Django suite는 **219 / 219 통과 / 157.165초 / system check 0건**, Coverage는 **219 / 219 / 162.533초 / 6,037 statements / 354 miss / 94%**다. Ruff lint PASS·46 files formatted, Bandit 0, pip-audit 알려진 취약점 0, Django check·deploy warning 0, migration no changes, Node JavaScript syntax·`git diff --check` PASS다.

```powershell
.\.venv\Scripts\python.exe manage.py test `
  accounts.tests.PublicProfileSecurityTests `
  accounts.tests.MyPageSecurityTests `
  community.tests.GlobalChatSecurityTests `
  community.tests.GlobalChatAdminTests `
  market.tests.ListingSecurityTests `
  market.tests.ModerationSecurityTests `
  --verbosity 1
```

실제 출력은 `Found 79 test(s)`, `System check identified no issues (0 silenced)`, `Ran 79 tests in 53.066s`, `OK`, exit code 0이었다.

## 현재 수행 결과

| ID | 상태 | 직접 확인한 구현·보안 통제 | 자동·코드 증적 |
|---|:---:|---|---|
| F-01 | **PASS** | `/accounts/signup/`·`/accounts/login/`; 정규화한 사용자명의 대소문자 무관 UNIQUE, Django password hash, 공개 privilege 필드 배제 | 기존 `SignupSecurityTests`·`LoginSecurityTests`, 79개 변경 기능 묶음과 직전 전체 206개 회귀 통과 |
| F-02 | **PASS** | `/accounts/users/<username>/`; `User.bio` 최대 500자. 활성 일반회원의 username·bio primitive만 template에 전달해 email·권한·정지정보를 공개하지 않음 | `PublicProfileSecurityTests`: 대소문자 조회, XSS escape, inactive/suspended/staff/superuser 404, POST 405 |
| F-03 | **PASS** | `/accounts/me/`에서 bio만 allowlist 수정. `/accounts/me/password/`는 현재 비밀번호, Django 강도 validator, 256자 사전상한, 사용자당 10회/시간, `update_session_auth_hash` 적용 | `MyPageSecurityTests`: 인증·no-store, mass assignment 거부, 500자, 현재 비밀번호, 강도, 과대입력, rate, 세션 회전·유지, 정지 세션 거부 |
| F-04 | **PASS** | CSRF 전 `MultipartUploadLimitMiddleware`가 POST·PUT·PATCH 전체 21MiB와 누적 실제 chunk를 제한한다. 브라우저는 최종 5장·장당 5MiB·신규 합계 20MiB를 사전 검증하고, 서버 preflight는 거부 파일을 폼에 bind·디코딩하지 않은 채 텍스트만 유지·사진 재선택을 안내한다. 6파일 위조는 parser의 일반 400이다. `PRESENT`에서만 하자 체크·상세를 표시하되 서버가 모순 입력을 독립 거부하고 정상 비-`PRESENT` stale 상세를 정규화한다. | 최신 결합 표적 40개: 조기 자원 제한·preflight 파일 미결합·6파일 400·MIME·재인코딩·하자 add→clear·모순 거부 회귀 |
| F-05 | **PASS** | `/listings/mine/`와 header의 `내 상품` 링크, 세션 소유자의 삭제 전 상품만 20개 pagination. 판매자 상태 POST는 `ACTIVE`↔`RESERVED`만 가능하고 `SOLD`는 구매자 완료 확인 서비스에서만 설정. 추가 사진 썸네일·연속 번호·삭제 checkbox를 직접 결합하고 대표 승격을 안내한다. hidden revision과 잠근 최신 `updated_at`이 다르면 409로 전체 비저장 | 소유자 격리·임의 `SOLD`·완료 후 mutation 거부, 이미지 유지·삭제·승격, 두 탭 stale 제목·가격·하자·알림 덮어쓰기 방지 회귀 통과 |
| F-06 | **PASS** | 비회원 홈은 공개 상태이면서 활성·비정지 판매자의 상품만 노출하고 차단·삭제 상품을 제외 | 공개 목록·ORM 검색·차단 제외·private image 회귀 통과 |
| F-07 | **PASS** | UUID 상품 상세에 상품명·설명·가격·대표/추가 사진·하자·상태·판매자 정보와 공개 프로필 링크 제공. 판매자 평균은 `PUBLIC` 후기만 집계 | 상세 XSS·비공개 접근·추가 이미지 부모 IDOR와 후기 aggregate 표적 회귀 통과 |
| F-08 | **PASS** | `/community/` 전체 채팅, `/messages/` 증분 JSON, `/send/` POST. `GlobalChatMessage(sender FK, body 1000, created_at, time/id index)`와 최대 약 2초 지연의 near-real-time polling 적용 | 인증·CSRF·서버 sender·XSS·signed cursor·요청 상한·양방향 차단·rate·no-store·read-only Admin 테스트 통과 |
| F-09 | **PASS** | 특정 상품·buyer·seller 조합에 묶인 `Conversation`·`Message`; 두 참여자만 조회·전송하며 sender는 서버 결정. 같은 대화의 판매자 요청+구매자 확인으로만 거래 완료·후기 자격 생성. 다른 대화의 진행 거래는 CTA·상대 신원을 숨기고 현재 대화의 거절·취소 기록만 표시 | `ConversationSecurityTests`와 `TradeReviewSecurityTests`에서 비참여자·차단·다른 거래 CTA·신원 비공개·거절/취소·blind 후기 통과 |
| F-10 | **PASS** | 상품 또는 실제 대화 상대를 `Report`에 서버 바인딩하고 사유·증거 snapshot/SHA 저장. OPEN 중복은 DB 제약으로 차단 | `ModerationSecurityTests`: target/reporter 위조, 중복, 비공개 metadata, snapshot·증거 보존 회귀 통과 |
| F-11 | **PASS** | 대상 상품의 **서로 다른 OPEN 신고자 3명**에서 transaction·행 잠금 후 자동 임시 `BLOCKED`. 자동 사유와 보안 log를 남기며 자동 영구삭제는 하지 않음 | 2명·동일인 중복 미발동, 3명 발동, 차단 상세 404·안전 redirect, 권한 Admin 자동 차단만 복구·OPEN 신고 기각, 수동 차단 비복구 테스트 통과 |
| F-12 | **PASS** | 대상 사용자의 **서로 다른 OPEN 신고자 3명**에서 일반 계정을 자동 임시 정지(`is_suspended=True`, `is_active=False`). staff/superuser는 자동조치하지 않음 | 자동 정지·자기 신고 미산입·staff/superuser 보호 테스트 통과. 전용 `suspend_user` 권한의 `unsuspend_selected`는 행 잠금·보호 계정 필터·Admin log를 코드 검토 |
| F-13 | **PASS** | 홈·가입·로그인·상품 목록/등록/상세·신고·1대1 대화·공개 프로필·마이페이지·내 상품·전체 채팅 화면이 연결되고, 거래·후기·관심 검색·알림은 관련 화면에서 접근 가능 | URL reverse·template link, 저장 검색/알림 소유자 범위와 거래 참여자 view 회귀 통과 |
| F-14 | **PASS** | 기존 사용자·상품·신고·1대1/전체 채팅에 `Trade`, `Review`, `SavedSearch`, `ListingEvent`, `Notification`, `ListingImage`, `ListingDefect`, `ReportImageEvidence` 관계·FK·index·CHECK·UNIQUE를 migration으로 추가 | 모델·migration 정적 대조, 역사적 확장 표적 36개와 최신 전체 219개 test DB system check 통과 |

## 설계 선택과 이유

### 전체 채팅은 2초 증분 polling을 선택

- PDF의 실시간 요구는 사용자가 새로고침하지 않아도 최대 약 2초 안에 새 메시지를 받는 near-real-time 동작으로 충족했다. WebSocket식 즉시 전달이라고 표현하지 않는다.
- 이틀 개발 범위에서 WebSocket/Channels 또는 장시간 SSE 연결을 추가하면 별도 broker·ASGI 운영 구성과 연결 고갈 방어가 함께 필요하다. 기존 Django 배포 구조를 유지하고 공격 표면을 줄이기 위해 짧고 bounded한 동일 출처 polling을 선택했다.
- 초기 50건, 요청당 최대 100건, DOM 최대 200건, poll 40회/분, send 10회/분, signed cursor, 탭 hidden 시 pause, 오류·429 backoff를 적용했다. 수신 JavaScript는 `innerHTML` 없이 `textContent`로 node를 구성한다.

### 신고 임계치는 서로 다른 OPEN 신고자 3명

- 한 사용자의 반복 신고를 세지 않고 현재 검토할 미처리 신고만 세어 단순 중복·처리 완료 이력을 자동제재 근거에서 제외했다.
- 세 번째 신고 저장과 임계치 계산·대상 상태 변경을 같은 transaction에서 수행하고 대상 행을 잠가 동시 요청의 중복조치를 줄였다.
- 오탐·신고 담합 가능성이 있으므로 상품은 자동 영구삭제하지 않고 임시 비공개 처리한다. 권한 있는 관리자가 증거를 검토한 뒤 자동 차단 상품만 복구하거나 별도 purge할 수 있다.
- 사용자는 일반 계정만 임시 정지하고 staff/superuser는 자동조치에서 보호한다. 관리자는 전용 권한으로 정지를 해제할 수 있으며 조치·복구를 Admin/security log에 남긴다.
- 서로 다른 신고자만 세지만 공격자가 만든 세 계정의 Sybil/공모까지 판별하지는 못한다. 계정 신뢰도·단계적 제재·이의제기 SLA는 운영 보완 대상이다.

### 확장 기능의 공개·상태 경계

- 첫 후기는 `PENDING`이며 공개 본문뿐 아니라 개수·평균에서도 제외한다. 양쪽 제출 뒤 `PUBLIC` 전환 이후에만 집계한다.
- 가격 알림은 이벤트별 중복을 막지만 반복 인상·인하 스팸의 cooldown·최소 하락폭은 운영 보완 대상이다.
- 전체 채팅에는 특정 메시지에 묶인 신고 route가 없고, 현재 사용자 신고는 상품별 1:1 대화 상대를 근거로 한다.
- 거절·취소가 요청 전 `RESERVED` 상태를 복원하면 예약이 계속 유지되므로 예약 해제 주체·기한 정책이 필요하다.

## 현재 집계와 결론

- PASS: **14 / 14**
- PARTIAL: **0 / 14**
- FAIL: **0 / 14**
- PDF 25~29페이지 로컬 시스템 기능: **14개 PASS**
- 최종 제출 전체 판정: **아직 아님** — 로컬 전체 품질 게이트는 PASS지만 GitHub Public·원격 CI, clean clone, 확장 기능 전체 브라우저 UAT, 최종 PDF·지정 파일명·LMS, 실제 키보드·스크린리더·200% 확대를 별도 완료해야 한다.

## 최종 통합·브라우저 증적

- `market.tests.ListingSecurityTests`: **26개 통과 / 18.104초** — 저채도 세이지 첨부 범위, MIME accept/help, guarded 현재 이미지 URL, 내부 저장명·`MEDIA_URL` 비노출, 모바일 CSS 검증
- 세 확장 기능과 추가 보안 표적: **36개 통과**
- 직전 `manage.py test --verbosity 1`: **206개 통과 / 114.641초 / system check 문제 0건** — 후속 변경 전 기준선
- 직전 Coverage: **206개 통과 / 115.434초 / 5,778 statements / 343 miss / 94%**
- SEC-042~044 표적: `market.test_trade_reviews` + `market.tests.ListingAdminSecurityTests` **16개 통과 / 17.393초 / system check 문제 0건**
- SEC-045 표적: `config.tests.MultipartUploadLimitTests` **7개 통과 / 0.023초 / system check 문제 0건**
- SEC-042~047 최신 결합 표적: 다중 이미지·multipart·Listing Admin·거래 후기 4개 class **40개 통과 / 17.697초 / system check 문제 0건 / Ruff PASS** — preflight·사진 UI·하자 add→clear·revision 409·거래 CTA·공통 폼 피드백 포함
- 변경 후 전체 Django tests: **219 / 219 통과 / 157.165초 / system check 문제 0건**
- 변경 후 Coverage: **219 / 219 통과 / 162.533초 / 6,037 statements / 354 miss / 94%**
- 변경 후 기타 게이트: **Ruff lint PASS·46 files formatted, Bandit 0, pip-audit 알려진 취약점 0, Django check·deploy warning 0, migration no changes, Node JavaScript syntax·`git diff --check` PASS**
- 현재 웜톤·하자 오류 UI CSS 중괄호 1112/1112
- 실제 브라우저: 이미지가 있는 상품의 `비우기` 저장 → 정상 redirect·성공 메시지·placeholder·DB 빈 값·기존 파일 삭제·AttributeError/Traceback 0건
- 실제 브라우저: DEBUG 미등록 URL의 일반 404에서 URL pattern·Django 버전·traceback 비노출; 1440px·320px 점검 페이지의 문서 overflow 0, 외부 asset 0, console 오류 0
- 최종 웜톤 브라우저 spot-check: 1440×1000·320×800 문서 가로 overflow 0, 주요 조작 44px 이상. 실제 키보드·스크린리더·200% 확대와 확장 기능 전체 흐름은 미완료

## 1차 수행 결과 — 보존용 역사적 스냅샷

아래는 기능 추가 전 `bb890761a7998a015bcf36ab9c62a8daea46d7db`을 2026-07-13 16:53:49 +09:00에 검사한 당시의 판정이다. 관련 5개 테스트 클래스 67개는 46.119초에 통과했지만 누락 기능 자체를 검증한 결과가 아니었다. 이 표는 변경 전 문제 발견 증적으로만 보존하며 현재 상태를 나타내지 않는다.

| ID | 당시 상태 | 당시 확인 결과 / 미충족 조건 |
|---|:---:|---|
| F-01 | PASS | 가입·로그인·case-insensitive UNIQUE·password hash 존재 |
| F-02 | FAIL | 공개 profile route·template와 소개글 필드 없음 |
| F-03 | FAIL | 마이페이지·본인 소개글·비밀번호 변경 route 없음 |
| F-04 | PASS | 상품 등록 구현 |
| F-05 | PARTIAL | `?mine=1`은 있었으나 UI 접근 경로와 SEC-031 이미지 삭제 수정 없음 |
| F-06 | PASS | 비회원 공개 목록과 차단 상품 제외 |
| F-07 | PASS | UUID 상품 상세와 판매자 요약 |
| F-08 | FAIL | 전체 채팅 model·route·화면·자동 갱신 없음 |
| F-09 | PASS | 상품별 1대1 대화와 참여자 인가 |
| F-10 | PASS | 서버 결정 대상의 상품·사용자 신고 |
| F-11 | FAIL | 관리자 수동 block/purge만 있고 누적 신고 자동조치 없음 |
| F-12 | FAIL | 관리자 수동 suspension만 있고 누적 신고 자동정지 없음 |
| F-13 | PARTIAL | 프로필·마이페이지·전체 채팅 화면과 UI 접근 경로 없음 |
| F-14 | PARTIAL | User 소개글과 전체 채팅 데이터 구조 없음 |

당시 집계는 **6 PASS / 3 PARTIAL / 5 FAIL, NOT READY**였다. 위의 현재 14 PASS 결과가 이 역사적 판정을 명시적으로 대체한다.
