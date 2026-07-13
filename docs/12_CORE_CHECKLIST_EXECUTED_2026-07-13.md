# PDF 25~29페이지 시스템 기능 실제 수행 결과 - 2026-07-13

`11_CORE_SUBMISSION_CHECKLIST.md`의 14개 항목을 PDF 원문, Django route·model·view·template, 관련 자동 테스트와 다시 대조한 결과다. 아래의 현재 판정은 같은 날 앞서 기록한 6 PASS / 3 PARTIAL / 5 FAIL 스냅샷을 대체한다.

## 현재 검사 기준

- 대상: 2026-07-13 작업트리. 최종 commit SHA는 commit 뒤 갱신한다.
- 완료 시각: `2026-07-13 17:43 +09:00`
- 코드 확인: `accounts`·`community`·`market`·`config`의 route, model, migration, view, form, template, 정적 JavaScript, Admin, test를 직접 대조했다.
- 자동 증적: 공개 프로필·마이페이지·전체 채팅·상품·신고 변경 범위의 6개 테스트 클래스 **79개**가 53.066초에 통과했다.
- 전체 suite: **170개 전부 통과 / 102.496초**. Coverage 계측 실행도 **170개 전부 통과 / 103.560초 / 4,222 statements / 248 miss / 94%**였다. 아래 79개는 PDF 기능 변경의 직접 분기 증적이고, 이미지 첨부 UI는 `ListingSecurityTests` 26개, 170개는 전체 통합 영향 증적이다.

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
| F-01 | **PASS** | `/accounts/signup/`·`/accounts/login/`; 정규화한 사용자명의 대소문자 무관 UNIQUE, Django password hash, 공개 privilege 필드 배제 | 기존 `SignupSecurityTests`·`LoginSecurityTests`, 79개 변경 기능 묶음과 최종 전체 170개 회귀 통과 |
| F-02 | **PASS** | `/accounts/users/<username>/`; `User.bio` 최대 500자. 활성 일반회원의 username·bio primitive만 template에 전달해 email·권한·정지정보를 공개하지 않음 | `PublicProfileSecurityTests`: 대소문자 조회, XSS escape, inactive/suspended/staff/superuser 404, POST 405 |
| F-03 | **PASS** | `/accounts/me/`에서 bio만 allowlist 수정. `/accounts/me/password/`는 현재 비밀번호, Django 강도 validator, 256자 사전상한, 사용자당 10회/시간, `update_session_auth_hash` 적용 | `MyPageSecurityTests`: 인증·no-store, mass assignment 거부, 500자, 현재 비밀번호, 강도, 과대입력, rate, 세션 회전·유지, 정지 세션 거부 |
| F-04 | **PASS** | `ListingForm`·`listing_create`가 제목·설명·가격·사진을 검증하고 seller·초기 상태를 서버 세션에서 결정. 첨부 컨트롤만 저채도 세이지를 쓰고 MIME accept/help를 명시 | `ListingSecurityTests` 26개: seller/status 위조, 가격, quota/rate, MIME·시그니처·재인코딩, 첨부 UI 회귀 |
| F-05 | **PASS** | `/listings/mine/`와 header의 `내 상품` 링크, 세션 소유자의 삭제 전 상품만 20개 pagination. 수정·상태·soft delete는 소유자만 가능. 현재 이미지는 guarded URL로만 표시 | 소유자 격리·위조 query 무시 테스트. SEC-031 삭제 sentinel과 유지·삭제·교체·모순·불량 이미지, 내부 저장명·`MEDIA_URL` 비노출 회귀 통과 |
| F-06 | **PASS** | 비회원 홈은 공개 상태이면서 활성·비정지 판매자의 상품만 노출하고 차단·삭제 상품을 제외 | 공개 목록·ORM 검색·차단 제외·private image 회귀 통과 |
| F-07 | **PASS** | UUID 상품 상세에 상품명·설명·가격·사진·상태·판매자 정보와 공개 프로필 링크 제공 | 상세 XSS escape, 비공개 접근 통제, 판매자 프로필 link 회귀 통과 |
| F-08 | **PASS** | `/community/` 전체 채팅, `/messages/` 증분 JSON, `/send/` POST. `GlobalChatMessage(sender FK, body 1000, created_at, time/id index)`와 2초 polling 적용 | 인증·CSRF·서버 sender·XSS·signed cursor·요청 상한·양방향 차단·rate·no-store·read-only Admin 테스트 통과 |
| F-09 | **PASS** | 상품별 `Conversation`·`Message`; buyer/seller 두 참여자만 조회·전송하며 sender는 서버 결정 | `ConversationSecurityTests` 1차 67개 묶음 및 과거 전체 회귀에서 비참여자·차단·판매완료·pagination·N+1 통과 |
| F-10 | **PASS** | 상품 또는 실제 대화 상대를 `Report`에 서버 바인딩하고 사유·증거 snapshot/SHA 저장. OPEN 중복은 DB 제약으로 차단 | `ModerationSecurityTests`: target/reporter 위조, 중복, 비공개 metadata, snapshot·증거 보존 회귀 통과 |
| F-11 | **PASS** | 대상 상품의 **서로 다른 OPEN 신고자 3명**에서 transaction·행 잠금 후 자동 임시 `BLOCKED`. 자동 사유와 보안 log를 남기며 자동 영구삭제는 하지 않음 | 2명·동일인 중복 미발동, 3명 발동, 차단 상세 404·안전 redirect, 권한 Admin 자동 차단만 복구·OPEN 신고 기각, 수동 차단 비복구 테스트 통과 |
| F-12 | **PASS** | 대상 사용자의 **서로 다른 OPEN 신고자 3명**에서 일반 계정을 자동 임시 정지(`is_suspended=True`, `is_active=False`). staff/superuser는 자동조치하지 않음 | 자동 정지·자기 신고 미산입·staff/superuser 보호 테스트 통과. 전용 `suspend_user` 권한의 `unsuspend_selected`는 행 잠금·보호 계정 필터·Admin log를 코드 검토 |
| F-13 | **PASS** | 홈·가입·로그인·상품 목록/등록/상세·신고·1대1 대화·공개 프로필·마이페이지·내 상품·전체 채팅 화면이 header 또는 상세 화면 link로 연결됨 | URL reverse와 template link, 각 view 인증·인가 회귀 통과 |
| F-14 | **PASS** | `User.bio` migration과 `GlobalChatMessage` migration을 추가하고 사용자·상품·신고·사진·1대1/전체 채팅 관계에 FK·index·제약·password hash 적용 | 모델·migration 정적 대조 및 79개 변경 기능 테스트의 test DB 생성·system check 통과 |

## 설계 선택과 이유

### 전체 채팅은 2초 증분 polling을 선택

- PDF의 실시간 요구는 사용자가 새로고침하지 않아도 새 메시지를 받는 동작으로 충족했다.
- 이틀 개발 범위에서 WebSocket/Channels 또는 장시간 SSE 연결을 추가하면 별도 broker·ASGI 운영 구성과 연결 고갈 방어가 함께 필요하다. 기존 Django 배포 구조를 유지하고 공격 표면을 줄이기 위해 짧고 bounded한 동일 출처 polling을 선택했다.
- 초기 50건, 요청당 최대 100건, DOM 최대 200건, poll 40회/분, send 10회/분, signed cursor, 탭 hidden 시 pause, 오류·429 backoff를 적용했다. 수신 JavaScript는 `innerHTML` 없이 `textContent`로 node를 구성한다.

### 신고 임계치는 서로 다른 OPEN 신고자 3명

- 한 사용자의 반복 신고를 세지 않고 현재 검토할 미처리 신고만 세어 단순 중복·처리 완료 이력을 자동제재 근거에서 제외했다.
- 세 번째 신고 저장과 임계치 계산·대상 상태 변경을 같은 transaction에서 수행하고 대상 행을 잠가 동시 요청의 중복조치를 줄였다.
- 오탐·신고 담합 가능성이 있으므로 상품은 자동 영구삭제하지 않고 임시 비공개 처리한다. 권한 있는 관리자가 증거를 검토한 뒤 자동 차단 상품만 복구하거나 별도 purge할 수 있다.
- 사용자는 일반 계정만 임시 정지하고 staff/superuser는 자동조치에서 보호한다. 관리자는 전용 권한으로 정지를 해제할 수 있으며 조치·복구를 Admin/security log에 남긴다.

## 현재 집계와 결론

- PASS: **14 / 14**
- PARTIAL: **0 / 14**
- FAIL: **0 / 14**
- PDF 25~29페이지 시스템 기능: **READY**
- 최종 제출 전체 판정: **아직 아님** — 시스템 기능·SEC-031·032·전체 suite·coverage·정적·공급망·deploy·핵심 브라우저 보안 흐름은 완료했다. GitHub Public·원격 CI, clean clone, PDF와 파일명, 실제 키보드·스크린리더·200% 확대는 별도 완료해야 한다.

## 최종 통합·브라우저 증적

- `market.tests.ListingSecurityTests`: **26개 통과 / 18.104초** — 저채도 세이지 첨부 범위, MIME accept/help, guarded 현재 이미지 URL, 내부 저장명·`MEDIA_URL` 비노출, 모바일 CSS 검증
- `manage.py test --verbosity 1`: **170개 통과 / 102.496초 / system check 문제 0건**
- Coverage: 계측 실행 **170개 통과 / 103.560초 / 4,222 statements / 248 miss / 94%**
- Ruff lint·37개 파일 format, Bandit(`community` 포함), pip-audit, `check --deploy --fail-level WARNING`: 문제 0건
- `manage.py check`: 문제 0건; `makemigrations --check --dry-run`: 변경 없음; `accounts.0005`·`community.0001` 적용 완료; CSS 중괄호 935/935
- 실제 브라우저: 이미지가 있는 상품의 `비우기` 저장 → 정상 redirect·성공 메시지·placeholder·DB 빈 값·기존 파일 삭제·AttributeError/Traceback 0건
- 실제 브라우저: DEBUG 미등록 URL의 일반 404에서 URL pattern·Django 버전·traceback 비노출; 1440px·320px 점검 페이지의 문서 overflow 0, 외부 asset 0, console 오류 0

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
