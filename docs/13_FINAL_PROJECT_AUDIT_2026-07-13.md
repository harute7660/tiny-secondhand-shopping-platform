# 최종 프로젝트 필수 감사 체크리스트 — 2026-07-13

이 문서는 과제 제출 전 마지막 코드·보안·구조 감사의 단일 요약이다. `[x]`는 현재 작업트리의 코드·문서를 직접 대조하거나 명령으로 확인한 항목, `[~]`는 통제했지만 운영 보완이 필요한 항목, `[ ]`는 외부 환경·사람의 확인이 필요한 항목이다. SEC-048~061 후 현재 확정 결과는 **Django 251/251, coverage 6,922 statements / 385 miss / 94%**다.

## 1. 현재 판정

| 범위 | 판정 | 근거 |
|---|:---:|---|
| PDF 25~29·35페이지 로컬 필수 기능 | **PASS** | `02_REQUIREMENTS_TRACEABILITY.md`, `11_CORE_SUBMISSION_CHECKLIST.md`의 구현 route·model·view·template 대조 |
| 현재 작업트리 코드 감사 | **PASS** | 인증·인가·입력·파일·상태·신고·후기·원장·오류·설정 경계 직접 추적 |
| 현재 작업트리 자동 품질 게이트 | **PASS** | 251 tests, coverage 94%, 정적·공급망·배포·migration·JS·CSS·diff·secret 검사 통과 |
| 과제 제출 준비 | **PENDING** | Public GitHub·원격 CI·clean clone·UAT·PDF·지정 파일명·LMS 미확인 |
| 실제 다중 인스턴스 운영 | **NO-GO** | PostgreSQL·Redis·TLS/reverse proxy·MFA·백업·모니터링·보존정책이 필요 |

- 최종 로컬 commit SHA: **49ca4f4e34d28f406e43c2cd816778ab858a3c71**
- Public Repository URL: **[입력 필요]**
- GitHub Actions·CodeQL URL: **[입력 필요]**

## 2. 반드시 통과해야 하는 로컬 체크리스트

### 요구사항·기능

- [x] 회원가입·로그인·POST 로그아웃과 비밀번호 해시·검증
- [x] 공개 프로필·마이페이지·비밀번호 변경·내 상품
- [x] 상품 등록·검색·상세·수정·상태·숨김과 최대 5장 사진·하자 입력
- [x] 상품별 1대1 대화와 약 2초 polling의 로그인 회원 전체 채팅
- [x] 대화 상대 차단·상품/사용자 신고·관리자 검토·자동 임시조치
- [x] DEMO POINT 조건부 차감·멱등 송금·append-only 복식 원장
- [x] 판매자 요청과 해당 구매자 확인으로만 완료되는 거래와 blind 쌍방 후기
- [x] 관심 검색·가격 하락 알림과 비공개 전환 시 metadata 재검사
- [x] README에 환경 설정·실행·검사·운영 제한 명시

### 보안 불변조건

- [x] 판매자·발신자·신고자·송금자·후기 방향은 POST가 아니라 세션·URL·DB 관계에서 결정
- [x] 상품·대화·알림·저장검색·증거 endpoint는 소유자/참여자/전용 권한 범위로 조회
- [x] Django autoescape·CSRF·POST mutation·ORM·정렬 허용목록 유지, `eval/exec`·raw SQL·shell·`safe/mark_safe` 사용 없음
- [x] 로그인 공통 오류·HMAC 식별자·과대 credential 사전 거부·네트워크 30회 상한 적용
- [x] multipart 21MiB 누적 상한과 상품 upload 10회/시간 사전 admission이 CSRF body parsing 전에 위치
- [x] 이미지 MIME·signature·5MiB·12MP·단일 frame 검증 후 UUID JPEG 재인코딩, 보호 route·`no-store` 사용
- [x] 상품 수정은 정확히 하나의 필수 revision을 요구하고 누락·중복은 400, stale token은 409로 전체 비저장
- [x] 하자 상태·code 허용목록과 중복 code 거부를 클라이언트와 독립적으로 서버에서 검증
- [x] 차단 후 `next`는 Django host·scheme 검증으로 외부·역슬래시 변형을 거부
- [x] 자동 moderation은 가입 7일 경과·활성·미정지인 서로 다른 OPEN 신고자만 집계하고 신규 신고 증거는 보존
- [x] 후기 본문·평점·방향은 불변이며 전용 권한의 hide/제한적 restore action만 감사 로그와 함께 허용
- [x] 판매자 단독 `SOLD` 금지, 완료 요청 경쟁 처리, 완료 뒤 수정·재판매·새 대화 금지
- [x] 완료 상품 숨김 시 거래 참조는 보존하고 사용자 작성 공개 필드·사진·하자 정보는 최소화
- [x] 사용하지 않는 `REVERSAL` 종류·관계를 fail-closed migration으로 제거
- [x] 완료 거래의 분쟁 증거는 공개 상품 숨김과 분리해 불변 snapshot·이미지 SHA-256으로 보존
- [x] legacy `REVERSAL` 관계가 있으면 migration을 중단해 조용한 데이터 손실을 방지
- [x] 후기 restore action은 정확한 쌍방 후기·방향·상태를 잠금 후 검증
- [x] 브라우저 multipart 요청은 Origin·Fetch Metadata를 CSRF body parsing 전에 검사해 외부 컨텍스트 quota 소모를 차단
- [x] 운영 DEBUG·비밀키·Host·HTTPS·프록시 조건은 fail-closed, 일반 오류에 traceback·경로·설정 비노출

### 이번 변경 뒤 다시 실행할 게이트

- [x] `python manage.py check` — 문제 0건
- [x] `python manage.py makemigrations --check --dry-run` — 변경 없음, migration `0007`·`0008`·`0008` 로컬 적용 성공
- [x] `python manage.py test --verbosity 1` — **251 / 251 통과, 147.753초, system check 0건**
- [x] `coverage run manage.py test`와 `coverage report -m` — **6,922 statements / 385 miss / 94%**
- [x] `ruff check .`와 `ruff format --check .` — lint PASS, **50 files** format PASS
- [x] `bandit -c pyproject.toml -r accounts community config market -q` — **8,082 lines / 0 issues**
- [x] `pip check`, runtime·development lock 각각 `pip-audit --disable-pip` — dependency conflict 0, 알려진 취약점 각각 0
- [x] 검증용 운영 환경의 `python manage.py check --deploy --fail-level WARNING` — warning 0
- [x] JavaScript **3 files** syntax PASS, CSS 중괄호 **1112/1112**, `git diff --check` PASS
- [x] 현재 파일·Git 이력 high-confidence secret scan — 일치 0건

## 3. 이번 감사에서 바꾼 이유와 전후

| ID | 변경 전 위험 | 변경 후 | 왜 이 방식을 선택했는가 |
|---|---|---|---|
| SEC-048 | 타인이 피해자 사용자명으로 5회 실패해 정상 로그인까지 잠글 수 있음 | 계정 실패는 사후 기록, 네트워크 사전 상한, 성공 요청 예약만 반환 | 계정 존재 oracle을 만들지 않으면서 표적 lockout과 해시 DoS를 함께 줄임 |
| SEC-049 | 새 계정 3개가 즉시 상품 차단·사용자 정지를 만들 수 있음 | 7일 경과·활성·미정지 신고자만 자동조치 집계, 모든 신고는 OPEN 증거로 보존 | 영구 삭제 없이 자동조치 비용을 높이고 관리자 검토 근거를 잃지 않음 |
| SEC-050 | revision 생략 시 lost-update 보호 우회 | update에 정확히 하나의 필수 token, 누락·중복 400 | 브라우저 외 호출도 같은 경쟁조건 통제를 강제 |
| SEC-051 | 중복 하자 code가 DB UNIQUE 예외와 500을 유발 | Form 단계 명시적 중복 오류 | 비정상 입력을 사용자 오류로 닫고 기존 데이터를 보존 |
| SEC-052 | 수동 `/` prefix 검사에 URL 정규화 사각지대 | Django host·scheme 검증 | 프레임워크의 검증된 URL 의미론을 재사용 |
| SEC-053 | 악성 공개 후기를 숨길 경로가 없거나 generic 편집을 열어야 함 | 불변 본문 + hide/제한 restore 전용 action | 증거 무결성과 피해 확산 억제를 동시에 유지 |
| SEC-054 | workflow 없는 원장 반전 상태를 내부에서 만들 수 있음 | 기존 데이터가 있으면 중단하고 종류·관계 제거 | 불완전한 금융 상태를 남기기보다 공격면을 축소 |
| SEC-055 | 완료 상품의 설명·지역·사진·하자가 계속 남음 | 참조 행·거래·후기는 보존하고 공개용 사용자 데이터 정리 | 분쟁·후기 참조와 개인정보 최소화를 분리 |
| SEC-056 | 동시 완료 요청의 UNIQUE 경쟁이 500 가능 | savepoint에서 충돌 후 최신 행 재조회 | 동일 요청은 안전하게 재사용하고 다른 거래는 일반 도메인 오류로 닫음 |
| SEC-057 | view rate limit 전에 CSRF가 multipart body를 파싱 | 인증 뒤·CSRF 전 상품 multipart 10회/시간 admission | 거부 요청의 body·파일 파싱을 시작하지 않으면서 정상 CSRF 검증은 유지 |
| SEC-058 | 완료 상품 공개 숨김이 분쟁에 필요한 당시 사진·하자·본문까지 잃을 수 있음 | 거래 완료 요청 시 불변 `TradeEvidence`와 이미지 hash snapshot 저장 | 개인정보 최소화와 분쟁 증거 보존을 분리 |
| SEC-059 | legacy 원장 반전 관계가 있으면 migration이 조용히 관계를 잃을 수 있음 | `REVERSAL` 종류뿐 아니라 `reversal_of` 관계도 fail-closed 검사 | 손실 변환보다 명시적 중단이 안전 |
| SEC-060 | 후기 복구 action이 한쪽 hidden·상대 pending 조합을 잘못 복구할 수 있음 | 쌍방 후기 방향·상태·선택 수를 row lock 뒤 검증 | 공개 평판 조작과 부분 복구를 막음 |
| SEC-061 | 같은 사이트로 보이는 외부 브라우저 컨텍스트가 pre-CSRF upload quota를 소모할 수 있음 | Origin scheme/host exact match와 `Sec-Fetch-Site` 검사 후 quota 차감 | 브라우저 기반 남용을 body parsing 전에 차단 |

## 4. 구조 감사

- [x] 앱 경계는 `accounts`(계정), `community`(전체 채팅), `market`(거래), `config`(설정·middleware)로 분리되어 있다.
- [x] 쓰기 경로는 Form/service/transaction을 사용하고, 보호 대상은 DB CHECK·UNIQUE·행 최신 상태 재검사로 보강되어 있다.
- [x] 미사용 홈 `?mine=1` 분기를 제거하고 전용 내 상품 route로 단일화했다.
- [x] migration은 기존 `REVERSAL` 행이 있으면 손실 변환 대신 중단하도록 설계했다.
- [~] `market/views.py` 1,562줄, `services.py` 842줄, `admin.py` 955줄, `market/models.py` 1,053줄, `market/tests.py` 2,397줄, `accounts/tests.py` 1,301줄로 도메인 간 논리 의존이 크다. 제출 직전 대규모 분할은 회귀 위험 때문에 보류하고 다음 유지보수에서 listing/trade/moderation/notification/evidence service와 test 모듈을 분리한다.
- [~] `static/css/site.css` 7,314줄에는 감청·흑백·웜톤 전환 과정의 cascade가 누적되어 있다. 최종 웜톤이 우선하지만 다음 단계에서 dead rule을 제거하고 component 단위로 분리한다.
- [~] 알림 fan-out이 commit 뒤 같은 요청 프로세스에서 동기 실행되어 구독자 수에 비례한다. 운영 전 queue·retry worker·처리 지표가 필요하다.

## 5. 코드만으로 완료할 수 없는 필수 항목

- [x] 브라우저 spot-check: 1440×900·375×812 홈의 html/body overflow 0, 웜톤 배경 정상, Django 진단 문구 없음; 로그인 password·CSRF 존재/overflow 0; 무작위 URL custom 404와 traceback·내부 경로 비노출

- [x] 로컬 clean clone에서 README 기준 핵심 재현 확인: `check`, `makemigrations --check --dry-run`, `migrate --noinput` 통과
- [ ] Git 전체 이력 secret/개인정보 검사, Public 저장소 push, 로그아웃 접근 확인
- [ ] 원격 GitHub Actions·CodeQL·Dependabot 성공과 동일 SHA 확인
- [ ] 판매자·구매자 두 세션으로 후기·알림·다중사진·하자·완료 상품 숨김 전체 UAT
- [ ] 320px·200% 확대, 키보드 전용, 실제 스크린리더, 주요 색 대비 수동 확인
- [ ] 보고서의 반·이름·전화번호 뒷자리·GitHub URL·최종 SHA 입력
- [ ] PDF 렌더링 후 한글·표·코드·페이지 잘림·링크를 육안 검수
- [ ] 공백 없는 `[WHS][secure-coding][XX반]이름(뒷4자리).pdf` 파일명과 LMS 제출 재확인

## 6. 생산 배포 전 차단 조건

다음 항목이 끝나기 전에는 이 프로젝트를 실제 중고거래 서비스로 배포하지 않는다.

- [ ] SQLite를 PostgreSQL로 전환하고 거래·신고·수정 경쟁 부하 시험
- [ ] LocMemCache를 원자적 공유 Redis로 전환하고 fail-open/fail-closed 정책 결정
- [ ] TLS 종료 reverse proxy에 request body·연결 수·속도·timeout·source-network 제한 적용; `MEDIA_ROOT` 직접 alias 금지
- [ ] 관리자 MFA·관리 네트워크 제한·최소권한 계정·중앙 감사 로그·경보
- [ ] 백업·복구 훈련, 원장 reconciliation, 저장소 orphan 조정
- [ ] 신고 원문·이미지·대화의 보존·파기·legal hold·사용자 삭제 요청 정책과 purge 작업
- [ ] 알림 durable queue·재시도 worker와 성숙 계정 신고 공모·평판 조작 대응

## 7. 제출 직전 최종 판정 규칙

현재 작업트리 전체 로컬 게이트는 통과했다. 5절의 GitHub·UAT·PDF 항목을 사람이 확인한 뒤에만 **SUBMISSION READY**로 바꾼다. 로컬 코드 PASS는 외부 제출 완료나 생산 운영 안전을 뜻하지 않는다. 세부 증적은 `04_SECURITY_FINDINGS.md`, `06_TEST_CHECKLIST.md`, `09_REPORT_DRAFT.md`, `10_USER_ACCEPTANCE_CHECKLIST.md`와 함께 보관한다.
