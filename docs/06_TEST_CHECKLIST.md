# 기능·보안 테스트 체크리스트

`[x]`는 해당 범위의 자동 검사 또는 명시한 코드 검토 완료, `[~]`는 일부만 확인했거나 GitHub·브라우저 등 추가 확인 대상, `[ ]`는 미완료, `N/A`는 이유를 확인한 비적용 항목이다. SEC-048~061 변경 후 현재 작업트리는 **Django 251 / 251 / 147.753초**, Coverage **6,922 statements / 385 miss / 94%**와 정적·공급망·운영 게이트를 통과했다.

## 자동 검사 요약

| 검사 | 명령/범위 | 실제 결과 | 상태 |
|---|---|---|:---:|
| Django 변경 기능 tests | 프로필·마이페이지·전체 채팅·상품·신고 6개 test class | 79개 전부 통과, 53.066초, system check 0건 | 현재 변경 범위 완료 |
| 이미지 첨부 UI tests | `market.tests.ListingSecurityTests` | 26개 전부 통과, 18.104초 | 직접 분기 완료 |
| 세 확장 기능 표적 tests | 후기 9 + 알림 12 + 다중 이미지·하자 12 + 추가 보안 3 | 36개 전부 통과 | 직접 분기 완료 |
| SEC-042~044 표적 tests | `market.test_trade_reviews` + `market.tests.ListingAdminSecurityTests` | 16개 전부 통과, 17.393초, system check 0건 | 직접 분기 완료 |
| SEC-045 multipart tests | `config.tests.MultipartUploadLimitTests` | 7개 전부 통과, 0.023초, system check 0건 | 직접 분기 완료 |
| SEC-042~047 최신 결합 표적 | 다중 이미지·multipart·Listing Admin·거래 후기 4개 class | 40개 전부 통과, 17.697초, system check 0건, Ruff PASS | 최신 직접 분기 완료 |
| 직전 Django 전체 tests | `manage.py test --verbosity 1` | 206개 전부 통과, 114.641초, system check 0건 | 후속 변경 전 기준선 |
| 직전 Coverage | `coverage run --source=accounts,community,config,market manage.py test` | 계측 206개 전부 통과, 115.434초, 5,778 statements / 343 miss / 94% | 후속 변경 전 기준선 |
| SEC-048 이전 전체 Django tests | `manage.py test --verbosity 1` | **219 / 219 통과, 157.165초, system check 0건** | 직전 확정 기준선 |
| SEC-048 이전 Coverage | 전체 suite instrumentation | **219 / 219 통과, 162.533초, 6,037 statements / 354 miss / 94%** | 직전 확정 기준선 |
| SEC-048 이전 정적·공급망·운영 게이트 | Ruff·Bandit·pip-audit·Django check/deploy·migration·Node syntax·diff | **Ruff PASS·46 files formatted; Bandit 0; 알려진 취약점 0; check/deploy 0; migration no changes; Node syntax·diff PASS** | 직전 확정 기준선 |
| 최종 전체 Django tests | `manage.py test --verbosity 1` | **251 / 251 통과, 147.753초, system check 0건** | 완료 |
| 최종 Coverage | 전체 suite instrumentation | **6,922 statements / 385 miss / 94%** | 완료 |
| 최종 정적·공급망·운영 게이트 | Ruff·Bandit·pip check/audit·Django check/deploy·migration·JS·CSS·diff·secret | **Ruff 50 files PASS; Bandit 8,082 lines/0; 두 lock 취약점 0; check/deploy 0; 0007 적용·drift 0; JS 3·CSS 1112/1112·diff PASS; secret 0** | 완료 |
| Ruff | `ruff check .` 및 `ruff format --check .` | lint 오류 0건, 46개 파일 형식 일치 | 완료 |
| Bandit | `bandit -r accounts community config market -c pyproject.toml -q` | 이슈 0건 | 완료 |
| Django·migration | `manage.py check`, `makemigrations --check --dry-run` | system check 0건, 모델 변경 없음 | 완료 |
| CSS 중괄호 | `static/css/site.css` 열림/닫힘 개수 비교 | 1112 / 1112 | 현재 웜톤·하자 오류 UI CSS 균형 확인 |
| pip-audit 최초 | 가상환경 전체 | `pip` 취약점 6건 | 발견 |
| pip-audit 재검사 | 현재 가상환경 전체 | 알려진 취약점 0건 | 조치 완료 |
| Django 배포 검사 | 검증용 운영 환경의 `check --deploy --fail-level WARNING` | 문제 0건 | 완료 |
| 금지 패턴 검색 | Python·HTML의 위험 API·escape 우회 | 일치 0건 | 완료 |
| Runtime lock | SHA-256 포함 `requirements.lock` | `--require-hashes` 설치 검증 | 완료 |
| Dev lock | `requirements-dev.lock` | 빈 대상 디렉터리에 `--require-hashes` 설치 성공 | 완료 |
| CI·CodeQL | push/PR workflow·security-extended | 파일·commit SHA pin 검토 | GitHub 실행 예정 |

## 최종 감사 필수 재검증

- [x] 코드 대조: 로그인·상품·신고·후기·원장·redirect·거래 완료·삭제 경계와 migration을 직접 추적
- [x] 신규 회귀 존재 확인: 로그인 표적 lockout, 신규 3계정 미발동, revision 누락·중복, 하자 중복, redirect 변형, 후기 hide/restore, 완료 상품 숨김, 거래 요청 경쟁
- [x] 현재 작업트리 신규 회귀 포함 전체 251개 통과
- [x] 현재 작업트리 Django 전체 suite·coverage 통과 — 251개/147.753초, 6,922 statements/385 miss/94%
- [x] 현재 작업트리 Ruff·format·Bandit·pip check·두 lock pip-audit·check/deploy·migration·JS·CSS·diff·secret scan 통과
- [ ] GitHub Actions·CodeQL 성공 URL과 대상 commit SHA 확인

## 사용자 요청 확장 기능

- [x] 판매자 요청과 해당 대화 구매자 확인이 있어야 `Trade.COMPLETED`·`Listing.SOLD`가 됨
- [x] 레거시 `SOLD`만으로 후기 권한이 생기지 않고, 제3자·위조 방향·중복 후기 요청이 차단됨
- [x] 첫 후기는 비공개이며 양측 제출 뒤 함께 공개되고 공개 프로필에 상품·가격·지역·UUID가 노출되지 않음
- [x] `PENDING` 후기는 공개 프로필·상품 상세의 개수와 평균에도 반영되지 않고, 양쪽 `PUBLIC` 전환 뒤에만 집계됨
- [x] 후기 XSS가 escape되고 slash 구분 전화번호를 포함한 전화번호·이메일·URL·긴 숫자 패턴이 거부됨
- [x] 저장 검색 정규화·20개 제한·소유자 IDOR·알림 수신자 IDOR·중복·소급 발송이 방어됨
- [x] 실제 가격 하락만 old/new 값으로 알리고 차단·정지·판매자 자신을 제외함
- [x] 비공개 상품 알림에서 제목·가격·이벤트 종류·링크가 숨겨짐
- [x] 대표 포함 최대 5장·합계 20MB·허용 field가 sanitizer 전에 검사됨
- [x] 추가 이미지 부모 IDOR·위조 삭제 UUID·stale 대표 경로·DB 실패 orphan이 방어됨
- [x] 하자 허용목록·상태 조합·OTHER 상세와 XSS가 검증됨
- [x] `하자 있음`에서만 체크·상세가 표시·활성화되고 비-`PRESENT` 변경 시 브라우저 입력을 비활성화·초기화하며, 서버는 forged 모순을 거부하고 정상 stale 상세를 비움
- [x] `OTHER` 상세의 native required, 서버 오류 전체 요약·필드 링크·포커스, 조건부 오류 그룹 재표시, 유효 제출의 `저장 중…`·중복 제출 잠금이 구현됨
- [x] 신고 시 전 이미지 SHA·순서와 하자 snapshot이 저장되고 삭제 뒤 증거가 보존됨
- [x] 상품의 다른 대화에서 진행 거래가 있으면 현재 대화의 완료·후기 CTA와 상대 신원을 숨기고, 현재 대화의 최근 거절·취소 기록만 표시함
- [x] 관리자 다중 증거는 Report 권한과 부모 관계·SHA를 검증하고 내부 저장명을 숨김
- [x] 미처리 알림 이벤트의 제한형 수동 재처리 명령과 완료 거래 자동차단 복구 회귀 통과
- [x] 오래 열린 Listing Admin 수정은 새 `BLOCKED`·차단 사유·처리 metadata를 덮어쓰지 못함
- [~] 이번 세 기능의 전체 브라우저·키보드·스크린리더 인수와 PostgreSQL 경합·대량 fan-out 부하 검증은 후속 수행
- [~] 신규 3계정은 7일 자동조치 유예를 적용했지만 성숙 계정 공모, 가격 반복 인상·인하 알림 스팸, 전체 채팅 메시지별 신고, `RESERVED` 요청 취소/거절 뒤 예약 해제 정책은 운영 보완 대상

## PDF 35페이지 최소 기능

- [x] TEST-F001 회원가입, 비밀번호 해시·검증, 로그인, POST 로그아웃
- [x] TEST-F002 공개 상품 목록·검색·상세 조회와 차단 상품 제외
- [x] TEST-F003 상품 등록, 판매 상태 허용 전이, stale 수정 방지, soft delete·이미지 정리 - SEC-031 `FileField.save_form_data()` 수정과 이미지 전 흐름 회귀 통과
- [x] TEST-F004 상품별 1:1 대화, 참여자 제한, 30개 페이지 목록·마지막 메시지 annotation
- [x] TEST-F005 대화 상대 차단·신고, 상품 신고, 비공개 placeholder, Admin 조치
- [x] TEST-F006 DEMO POINT 송금, 지갑·내역 조회, 서버 잔액 판단
- [x] TEST-F007 Django Admin의 교차 모델 최소 권한·보호 계정과 원장 ORM 불변성

## PDF 25~29페이지 상세 시스템 기능 재대조

- 25~29페이지의 기능·화면·DB를 14개로 중복 제거한 최종 기능표는 `11_CORE_SUBMISSION_CHECKLIST.md`에 둔다.
- 1차 **6 PASS / 3 PARTIAL / 5 FAIL**은 기능 추가 전 역사적 스냅샷이며 현재 판정은 `12_CORE_CHECKLIST_EXECUTED_2026-07-13.md`의 **14 PASS / 0 PARTIAL / 0 FAIL**이다.
- 공개 프로필·마이페이지·전체 채팅·상품·신고 6개 테스트 클래스 79개가 53.066초에 통과했다. 이후 이미지 첨부 UI 26개, 확장 기능·보안 표적 36개, SEC-042~047 결합 40개와 전체 219개·coverage 94%를 확인했다. 이는 SEC-048~061 전 역사적 기준선이며 현재 재실행 결과와 구분한다.
- [x] TEST-SD001 공개 사용자 프로필과 소개글 조회 - username·bio allowlist, inactive/suspended/staff/superuser 비공개, XSS escape, read-only
- [x] TEST-SD002 본인 소개글·비밀번호 변경 마이페이지 - bio mass assignment 방지, 현재 비밀번호·강도 validator·256자 사전상한·10회/시간·세션 회전
- [x] TEST-SD003 실시간 전체 채팅 - 인증·CSRF·서버 발신자·XSS `textContent`·양방향 차단·signed cursor·요청/렌더 상한·rate·hidden pause/backoff·read-only Admin
- [x] TEST-SD004 가입 7일 경과·활성·미정지인 서로 다른 OPEN 신고자 3명 임계치 - 신규 계정 신고는 증거만 보존, 자격 계정은 상품 자동 임시 차단·일반 사용자 자동 정지, staff/superuser 보호·Admin 해제와 감사 log
- [x] TEST-SD005 `/listings/mine/` UI와 세션 소유자 격리, 수정·상태·삭제·이미지 유지/삭제/교체/모순/불량 업로드 전 흐름 - SEC-031 신규 회귀 통과

## 인증·인가

- [x] TEST-A001 `login_required` 중요 기능과 비회원 리다이렉트 코드 검토
- [x] TEST-A002 사용자 A가 사용자 B의 상품 수정·삭제 시 404
- [x] TEST-A003 대화 비참여자의 상세 접근 404
- [x] TEST-A004 일반 사용자의 `/admin/` 접근 거부
- [x] TEST-A005 자기 자신과 대화·송금 불가 서비스 검증
- [x] TEST-A006 요청의 `seller`, `sender`, 권한·상태 필드가 서버 결정을 바꾸지 못함
- [x] TEST-A007 로그인 오류를 일반화해 계정 존재 여부 구분 방지
- [x] TEST-A008 계정별 실패 표식 5회/15분과 네트워크 원시도 30회/15분 제한, 계정 표식만으로 정상 자격 증명을 사전 잠그지 않고 성공 요청의 network 예약 1회만 반환
- [x] TEST-A009 정지 계정 로그인 거부
- [x] TEST-A010 신고 대상은 URL 문맥에서 검증 전에 서버 바인딩하고 DB는 대상 하나만 허용
- [x] TEST-A011 Admin 로그인도 같은 표적 lockout 방지·network 30회 상한을 적용하고 성공 요청만 예약 반환
- [x] TEST-A012 신고 action은 `change_report`와 전용 `block_listing`/`suspend_user` 권한을 내부에서 재검사
- [x] TEST-A013 forged Admin POST로 숨겨진 상품 차단·계정 정지 action 실행 불가
- [x] TEST-A014 관리자 본인·staff·superuser 일괄 정지 제외
- [x] TEST-A015 단순 staff는 `market.view_listing` 없이 차단 상품 조회 불가
- [x] TEST-A016 정지 계정은 모델·DB 모두 active 상태가 될 수 없고 판매 상품도 비공개
- [x] TEST-A017 비-superuser의 User privilege·정지 필드와 password reset 위조 변경 거부
- [x] TEST-A018 Admin 사전 인증 staff POST는 타 계정 제한을 지우지 않고 nonstaff는 403
- [x] TEST-A019 실제·미존재 ACCOUNT HMAC의 동일 DB 경로, IP당 15분 신규 행 최대 30개·30분 retention cleanup, 과대 credential 사전 거부
- [x] TEST-A020 `block_listing`, `suspend_user`, `delete_listing`+`purge_listing` 전용 권한 조합별 허용·거부
- [x] TEST-A021 Message·Conversation·Favorite·UserBlock·LoginAttempt의 Admin 직접 추가·변경·삭제 거부
- [x] TEST-A022 신고 처리·차단·정지 action은 Report 행 잠금과 `OPEN` 재검사 뒤 실행
- [x] TEST-A023 purge된 상품의 stale Listing Admin 저장은 레코드를 다시 생성하지 못함
- [x] TEST-A024 오래 열린 Listing Admin 수정은 새 `BLOCKED` 상태·사유·처리자·시각을 덮어쓰지 못함
- [x] TEST-A025 후기 본문·평점·방향 직접 편집은 거부하고 `change_review` 전용 hide/양방향 완료 후기 restore action만 감사 로그와 함께 허용

## 입력 검증 및 표현

- [x] TEST-I001 SQL 삽입 형태 검색어가 ORM의 일반 문자열로 처리됨
- [x] TEST-I002 상품·메시지 XSS 페이로드가 템플릿에서 이스케이프됨
- [x] TEST-I003 0·음수·상한 초과 상품 가격 거부
- [x] TEST-I004 Django host·scheme 검증으로 외부 URL·`//evil.example`·역슬래시 변형을 거부하고 정상 same-host 경로만 허용
- [x] TEST-I005 신고 대상·송금 발신자 추가 POST 필드 무시
- [x] TEST-I006 사용자 입력을 헤더·파일 경로·서버 URL로 사용하지 않는 데이터 흐름 검토
- [x] TEST-I007 순차 사용자 ID만으로 신고·차단 불가, 참여 대화에서 상대방을 서버가 파생
- [x] TEST-I008 비공개 상품 UUID를 신고 URL로 재사용해 metadata를 다시 열 수 없음

## CSRF·세션·쿠키·응답 헤더

- [x] TEST-S001 로그아웃·찜·대화 시작·차단 등 상태 변경은 POST 전용
- [x] TEST-S002 로그인·상품 등록의 CSRF 토큰 누락 요청 403
- [x] TEST-S003 로그인 시 세션 키 회전, POST 로그아웃 시 세션 폐기
- [x] TEST-S004 운영 쿠키 Secure·HttpOnly·SameSite와 HTTPS 리다이렉트 설정
- [x] TEST-S005 공개 응답 CSP·Permissions-Policy·DENY frame·nosniff·same-origin referrer
- [x] TEST-S006 인증·익명 공개 HTML을 포함한 모든 동적 응답 `private, no-store`·`Pragma: no-cache`
- [x] TEST-S007 운영 1년 HSTS·includeSubDomains·preload 설정과 배포 검사
- [x] TEST-S008 비신뢰 peer의 XFF·XFP 무시, 설정된 proxy에서만 client IP·HTTPS 전달 허용

## DEMO POINT 무결성과 경쟁조건

- [x] TEST-T001 한 송금에 부호가 반대인 원장 2건이 생성되고 합계가 0
- [x] TEST-T002 잔액 부족 시 송금·원장·잔액 변경 전체 롤백
- [x] TEST-T003 같은 멱등키·같은 요청은 한 번만 반영
- [x] TEST-T004 같은 멱등키를 다른 금액에 재사용하면 거부
- [x] TEST-T005 조건부 잔액 차감으로 음수 방지, 캐시 잔액과 전체 원장 합계 일치
- [x] TEST-T006 차단 사용자 송금 거부, 클라이언트의 발신자 변조 무시
- [x] TEST-T007 송금 화면이 인증 사용자의 실제 지갑 context를 표시
- [x] TEST-T008 모든 게시 송금은 원장 정확히 2건이고 delta 합계 0
- [x] TEST-T009 Transfer instance·QuerySet update/delete/bulk_update 거부
- [x] TEST-T010 LedgerEntry instance·QuerySet update/delete/bulk_update 거부
- [x] TEST-T011 불변조건·workflow 없는 미완성 `REVERSAL` 종류·관계 제거 migration이 기존 반전 행을 fail-closed로 거부

## 상품 상태·자원·목록 성능

- [x] TEST-Q001 네트워크당 회원가입 5회/시간 제한과 원문 IP 대신 HMAC 키 저장
- [x] TEST-Q002 사용자당 상품 등록 10회/시간 제한
- [x] TEST-Q003 활성 상품 50개·전체 이력 500개 계정 quota를 계정 잠금 경계에서 검사
- [x] TEST-Q004 메시지 분당 20·일 500, 신고 일 10 상한 코드·회귀 검토
- [x] TEST-Q005 판매자 POST는 `ACTIVE`↔`RESERVED`만 허용하고, `SOLD`는 판매자 요청 뒤 해당 구매자가 완료 확인한 경우에만 서비스에서 설정
- [x] TEST-Q006 관리자 차단 뒤 stale 수정 POST가 차단 상태를 되돌리지 못함
- [x] TEST-Q007 판매완료 상품에는 새 대화를 시작할 수 없음
- [x] TEST-Q008 대화 목록 30개 페이지네이션과 Subquery 마지막 메시지로 N+1 제거
- [x] TEST-Q009 전체 채팅 초기 50·요청 최대 100·DOM 최대 200, poll 40회/분·send 10회/분, signed cursor와 탭 hidden pause·오류 backoff
- [x] TEST-Q010 수정 폼의 정확히 하나인 필수 hidden revision을 검사하고 누락·공백·중복은 파일 처리 전 400, 잠근 최신 `updated_at` 불일치는 409로 거부해 제목·가격·하자·파일·가격 하락 알림 근거를 덮어쓰지 않음
- [x] TEST-Q011 동시 거래 완료 요청의 조건부 UNIQUE 경쟁은 savepoint에서 처리해 동일 대화 요청은 기존 행을 재사용하고 다른 거래는 일반 오류로 종료

## 파일 업로드

- [x] TEST-U001 JPEG·PNG·WebP 디코딩 가능 이미지와 MIME/시그니처 검증
- [x] TEST-U002 HTML·SVG·실행 파일과 위장 이미지 거부
- [x] TEST-U003 5MB·12MP·단일 프레임 상한 적용
- [x] TEST-U004 원본 이름을 버리고 UUID JPEG 경로 사용
- [x] TEST-U005 EXIF 방향 보정 후 JPEG 재인코딩으로 메타데이터 제거
- [x] TEST-U006 삭제·비공개 상품 이미지의 직접 접근 제한과 타 사용자 상품 변경 거부
- [x] TEST-U007 공개 이미지도 `private, no-store`이며 soft delete commit 뒤 파일 제거
- [x] TEST-U008 이미지 교체 DB 실패 시 새 고아 파일, 성공 시 이전 파일을 정리하는 경로 검토
- [x] TEST-U009 상품 신고 시 텍스트·가격·분류·상태·이미지 저장명 snapshot과 SHA-256 일치
- [x] TEST-U010 교체·soft delete·Admin purge 뒤에도 Report가 참조한 이미지는 private storage에 보존되고 공개 route로 접근 불가
- [x] TEST-U011 제한 소진 시 상품 Form·이미지 sanitizer 실행 전 429
- [x] TEST-U012 증거 endpoint의 `view_report` 권한, 매 요청 SHA-256 재검증, 변조 404, `no-store`·`nosniff`, actor log와 증거명 index
- [x] TEST-U013 기존 이미지 삭제 체크가 302·DB 빈 이미지·commit 후 파일 삭제이며 500이 발생하지 않음 - `FileField.save_form_data()` SEC-031 회귀 통과
- [x] TEST-U014 완료 상품 숨김은 거래·후기 참조 행을 보존하면서 설명·지역·대표/추가 사진·하자 공개 정보를 정리하고 `DELETED`로 비공개 처리
- [x] TEST-U015 인증 뒤·CSRF 전 상품 multipart admission은 사용자별 10회/시간을 원자 집계하고 익명·초과 요청의 `POST`·`FILES`·body를 파싱하지 않음; reverse proxy body·연결·속도·동시성 제한은 별도 운영 항목
- [x] TEST-U014 이미지 미변경·교체·삭제+업로드 동시 선택·잘못된 이미지에서 기존/신규 파일 생명주기와 기존 증거 보존 회귀 통과
- [x] TEST-U015 multipart POST·PUT·PATCH 전체 21MiB를 CSRF·폼 파싱 전에 제한하고 known length는 body read 전, 누락·chunked·축소 length는 여러 파일 실제 chunk 누적으로 거부; 정상 upload·안전 400·보안 헤더 유지
- [x] TEST-U016 하자 조건부 UI는 비-`PRESENT`에서 입력을 숨김·disabled·초기화하고 `OTHER` 상세를 native required로 표시; 서버는 forged 상태/code 모순을 거부하고 add→clear 수정의 stale 상세·code를 제거하며 오류 요약·링크·포커스와 제출 잠금을 제공
- [x] TEST-U017 업로드 preflight 오류는 거부 파일 객체를 폼에 bind·디코딩하지 않고 제한을 통과한 텍스트만 유지하며 사진 재선택을 안내; 6파일 위조는 sanitizer 호출 전 Django parser의 진단 없는 일반 400
- [x] TEST-U018 브라우저가 기존·삭제·신규를 합친 최종 5장, 신규 장당 5MiB·합계 20MiB를 사전 검증하고, 추가 사진 썸네일·연속 번호·삭제 checkbox를 직접 결합하며 대표 삭제 시 첫 추가 사진 승격을 안내

## 오류 응답과 정보노출

- [x] TEST-E001 `DEBUG=False` BadRequest·PermissionDenied·404·예상하지 못한 예외·CSRF가 각각 400/403/404/500/403 안전 응답 사용
- [x] TEST-E002 오류 본문에 `Traceback`, `Exception Value`, 절대경로, Python/Django 버전, settings, POST 비밀값 없음
- [x] TEST-E003 오류 응답에도 CSP·`nosniff`·`DENY`·`private, no-store` 적용
- [x] TEST-E004 standalone 500이 URL reverse·공통 템플릿 렌더링 장애에도 최소 응답 반환
- [x] TEST-E005 정상 form/JSON 400·resolved 404·405·429 의미와 429 `Retry-After` 보존

## 회귀·접근성 점검

- [x] TEST-R001 홈의 빈 검색·누락 GET context가 500을 만들지 않음
- [x] TEST-R002 Django 5.2 위젯 `aria-describedby`와 `_helptext`, `_error` ID 일치
- [x] TEST-R003 470px 이하에서도 POST 로그아웃 컨트롤을 숨기지 않음
- [x] TEST-R004 전체 템플릿 파싱 성공, 인라인 script/style과 escape 우회 없음
- [x] TEST-R005 차단·삭제 상품 대화는 제목·가격·이미지 링크 대신 비공개 placeholder 표시
- [x] TEST-R006 가입 포인트 발행 내역은 빈 사용자명이 아니라 시스템 지급으로 표시
- [x] TEST-R007 Report 원문·snapshot·처리 metadata는 read-only이고 forged Admin POST에도 불변
- [~] TEST-R008 320px·200% 확대, 키보드 전용, 색 대비와 실제 스크린리더 브라우저 QA
- [x] TEST-R009 과거 감청색 UI 1440×1000 실화면에서 sticky header·hero·4열 Grid·문서 가로 overflow 0 확인; 1080/900/700/470/360px cascade, header·검색·CTA·상태 변경·페이지네이션·신고 컨트롤 최소 44px, 회원 nav 내부 overflow와 긴 입력 줄바꿈 정적 감사
- [x] TEST-R010 과거 블랙·화이트 UI에서 1440×1000 홈 4열·overflow 0, 320×800 홈 1열·overflow 0·primary button 44px, 로그인·안전 화면 overflow 0·외부 asset 0 확인; 상품 사진 `filter: none`
- [x] TEST-R011 실제 브라우저에서 SEC-031 이미지 비우기 저장·상세 placeholder·DB 빈 값·기존 파일 삭제와 DEBUG 404 기술정보 비노출을 재검증; 1440px 마이페이지와 320px 마이페이지·전체 채팅·내 상품의 문서 overflow 0 확인
- [x] TEST-R012 첨부 영역만 저채도 세이지로 한정하고 업로드 사진은 원색 유지; JPEG·PNG·WebP MIME accept와 5MB·1,200만 픽셀 help, guarded URL 현재 이미지, 내부 저장명·`MEDIA_URL` 비노출, 470px 이하 모바일 CSS를 `ListingSecurityTests` 26개로 검증. 당시 색 조합의 명암비 계산은 과거 팔레트 증적으로 보존
- [x] TEST-R013 최종 웜톤 UI를 1440×1000 데스크톱과 320×800 모바일에서 확인해 문서 가로 overflow 0, 주요 조작 최소 44px, 상품 사진 원색과 외부 asset 미추가를 확인; 최신 CSS 중괄호 1112/1112. 실제 키보드·스크린리더·200% 확대는 TEST-R008로 계속 대기
- [x] TEST-R014 상품·메시지·후기 폼이 공통 오류 요약 partial·요약 포커스·native validation·유효 제출 submit lock을 사용하고, 거래 대화는 상품 전체 활성 거래와 현재 대화를 분리해 잘못된 CTA·상대 신원을 공개하지 않음
- [x] TEST-R015 1440×900·375×812 홈 html/body overflow 0·웜톤 배경·Django 진단문구 없음, 로그인 password+CSRF·overflow 0, 무작위 URL custom 404·traceback/경로 비노출

## 명시적 N/A

- N/A-001 결제·배송·환불까지 포함한 별도 주문 상태 머신: PDF 최소 요구사항이 아니며 현재 `Order` 모델·주문 접수·결제 승인·배송·환불 URL은 없다. `Trade`는 쌍방 후기 자격을 위한 완료 요청·확인·거절·취소만 기록하며 이를 실제 주문 승인으로 주장하지 않는다.
- N/A-002 실제 결제·은행계좌·카드·환전·출금: DEMO POINT만 사용하며 금융정보를 수집하지 않는다.
- N/A-003 XML, LDAP, DNS 기반 권한 결정, 사용자 URL 서버 호출, 전자서명·웹훅: 해당 기능과 의존성이 없다.
- N/A-004 자체 C 확장·수동 메모리 해제: Python/Django 애플리케이션 범위에 없다.
- N/A-005 판매자·구매자의 정확한 실시간 GPS 상호 공유와 대중교통·자차 ETA: PDF 최소 요구사항이 아니며 위치 개인정보 동의·보존정책과 외부 지도 API가 필요한 별도 기능이라 현재 구현하지 않았다.

## 2026-07-13 릴리스 확인

- [~] REL-T01 README만 사용한 새 환경 설치·마이그레이션·실행·테스트
- [~] REL-T02 현재 파일과 Git 전체 이력에서 비밀·개인정보 0건
- [~] REL-T03 GitHub Public URL을 로그아웃 브라우저에서 열고 릴리스 SHA 기록
- [~] REL-T04 보고서 PDF 렌더링, 페이지 잘림·링크·GitHub URL 확인
- [~] REL-T05 공백 없는 지정 파일명과 공식 기한 2026-07-24 확인
- [~] REL-T06 최초 GitHub Actions CI·CodeQL·Dependabot 실행 결과와 대상 commit SHA 기록
- [~] REL-T07 운영 reverse proxy가 `MEDIA_ROOT`·`/_private-media/`를 직접 alias로 노출하지 않고 모든 이미지 요청이 Django 권한검사 view를 통과하는지 배포 설정 검증
- [x] REL-T08 README와 `docs/00~13` strict UTF-8 decode 오류 0건, 로컬 Markdown 링크 오류 0건 확인. 현재형 수치·완료 표현을 최종 감사 결과로 동기화하고 과거 기준선은 명시적으로 라벨링
- [x] REL-T09 SEC-031~041 직접 분기, 확장 기능 표적 36개, 직전 전체 206개, coverage 5,778 statements / 343 miss / 94%, Ruff·Bandit·pip-audit·deploy check 통합 검증 완료
- [x] REL-T10 SEC-042~047 최신 결합 40개, 전체 tests 219개, coverage 94%, Ruff·Bandit·pip-audit·check/deploy·migration·Node syntax·diff 로컬 게이트 통과 — SEC-048~061 전 기준선
- [x] REL-T11 SEC-048~061와 완료 상품 숨김 변경 뒤 전체 251 tests·coverage 94%·Ruff·Bandit·pip check·두 lock pip-audit·check/deploy·migration·JS·CSS·diff·secret scan 통과
