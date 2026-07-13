# KISA 소프트웨어 개발보안 기준 적용표

## 기준과 적용 방법

- 2026-07-13 재확인한 KISA [가이드라인 목록](https://www.kisa.or.kr/2060204)은 목록 페이지 자체의 최종수정일이 2026-07-06일 뿐, 별도 **“2026 시큐어코딩 가이드” 판본명**을 뜻하지 않는다.
- 공통 기준 문서: [소프트웨어 개발보안 가이드(2021.12.29, postSeq=5)](https://www.kisa.or.kr/2060204/form?lang_type=KO&page=1&postSeq=5)
- Python 보조 문서: [Python 시큐어코딩 가이드(2023년 개정본, postSeq=13)](https://www.kisa.or.kr/2060204/form?lang_type=KO&menuSeq=4135&page=&postSeq=13)
- 구현단계 기준: 7개 영역, 49개 보안약점
- Python 가이드 상세 설명 제외 3개: 메모리 버퍼 오버플로우, 해제된 자원 사용, 초기화되지 않은 변수 사용

`A`는 현재 구현에 적용할 통제, `N/A`는 기능·언어상 미적용이다. PDF 35페이지와 25~29페이지의 기능을 확정했으므로 보류 판정은 남기지 않았다. N/A도 금지 API 검색과 아키텍처 검토로 기능 부재를 검증하며, 기능이 추가되면 즉시 A로 재분류한다. SEC-048~061 뒤 전체 Django tests **251개/147.753초**, Coverage **6,922 statements / 385 miss / 94%**와 정적·공급망·운영 게이트를 통과했다. 존재하지 않는 2026 판본이나 실행하지 않은 외부 검사를 인용하지 않는다.

## 1. 입력데이터 검증 및 표현 - 17개

| 번호 | 항목 | 판정 | 핵심 통제 | 검증 |
|---:|---|:---:|---|---|
| 1 | SQL 삽입 | A | Django ORM, raw SQL 금지, 정렬 허용목록 | SQLi 테스트·정적 검색 |
| 2 | 코드 삽입 | N/A | `eval/exec/compile` 금지 | 금지 API 검색 |
| 3 | 경로 조작 및 자원 삽입 | A | 요청 파일명을 버리고 UUID JPEG 경로 사용, commit 후 교체·삭제 정리 | 위장 파일·직접 접근·파일 삭제 테스트 |
| 4 | 크로스사이트 스크립트 | A | template autoescape, HTML 입력 금지, `safe` 금지, 전체 채팅 DOM은 `textContent`로만 생성 | 상품·프로필·채팅 저장형 및 검색 반사형 XSS |
| 5 | 운영체제 명령어 삽입 | N/A | 셸·subprocess 호출 금지 | 금지 API 검색 |
| 6 | 위험한 형식 파일 업로드 | A | JPEG·PNG·WebP 디코딩, 5MB·12MP·단일 프레임 상한, JPEG 재인코딩 | 정상·위장·대용량 이미지 테스트 |
| 7 | 신뢰되지 않은 URL 자동접속 | A | named URL, 외부 `next` 검증 | 오픈 리다이렉트 테스트 |
| 8 | 부적절한 XML 외부 개체 참조 | N/A | XML 기능 없음 | XML 파서 검색 |
| 9 | XML 삽입 | N/A | XPath/XQuery 없음 | 관련 코드 검색 |
| 10 | LDAP 삽입 | N/A | DB 인증만 사용 | LDAP 의존성 검색 |
| 11 | 크로스사이트 요청 위조 | A | CSRF middleware, POST 변경, `csrf_exempt` 금지 | 강제 CSRF 테스트 |
| 12 | 서버사이드 요청 위조 | N/A | 사용자 URL 서버 호출 기능 없음 | HTTP 호출 데이터 흐름 검색 |
| 13 | HTTP 응답분할 | A | 헤더 고정, CR/LF 거부 | `%0d%0a` 테스트 |
| 14 | 정수형 오버플로우 | A | 가격·페이지·크기·가입·상품·소개글·채팅·신고 상한, DB 제약 | 경계값·quota/rate 테스트 |
| 15 | 보안기능 결정의 부적절한 입력값 | A | 사용자·발신자는 세션, 신고·차단 대상은 참여 대화, 프로필 필드 allowlist, 하자 상태/code는 서버 allowlist·조합 검증과 stale 상세 정규화, Admin은 대상 모델 권한 재검사 | Mass Assignment·sender 위조·열거·하자 forged 조합·add→clear·forged Admin POST 테스트 |
| 16 | 메모리 버퍼 오버플로우 | N/A | 자체 C 확장 없음 | FFI·바이너리 확장 검색 |
| 17 | 포맷 스트링 삽입 | A | 포맷 문자열은 코드 상수, 입력은 값 인자 | 사용자 제어 format 검색 |

## 2. 보안기능 - 16개

| 번호 | 항목 | 판정 | 핵심 통제 | 검증 |
|---:|---|:---:|---|---|
| 1 | 적절한 인증 없는 중요 기능 허용 | A | 마이페이지·비밀번호·내 상품·대화·전체 채팅·송금 로그인 강제, 일반·Admin 로그인 반복시도 제한 | 익명 URL·비밀번호 current-password·Admin throttle 테스트 |
| 2 | 부적절한 인가 | A | 소유자·대화 참여자·`view_listing`·교차 모델 change 권한, 보호 계정 | IDOR·staff view·forged Admin POST 테스트 |
| 3 | 중요한 자원의 잘못된 권한 설정 | A | `.env`·DB·미디어 최소권한, 원장 ORM 불변성, CI 최소 권한 | 원장 변경 거부·workflow 권한 검토 |
| 4 | 취약한 암호화 알고리즘 사용 | A | 자체 암호 금지, Django 표준 사용 | 취약 알고리즘 검색 |
| 5 | 암호화되지 않은 중요정보 | A | 비밀번호 해시, 운영 HTTPS 리다이렉트, 1년 HSTS·하위 도메인·preload, 로그 제외 | 저장·전송·배포 설정 검사 |
| 6 | 하드코드된 중요정보 | A | 환경변수, `.env` 제외, GitHub Actions commit SHA 고정 | 시크릿·workflow pin 검사 |
| 7 | 충분하지 않은 키 길이 | A | 충분한 엔트로피의 SECRET_KEY | 설정 검증 |
| 8 | 적절하지 않은 난수값 | A | `secrets`, Django 토큰, UUID4 | 보안 흐름 `random` 검색 |
| 9 | 취약한 비밀번호 허용 | A | 가입·변경 모두 Django validators, 현재 비밀번호 확인, 길이·흔한 값 제한, 변경 시도·입력 크기 제한 | 약한 비밀번호·변경 current password·oversized/rate 테스트 |
| 10 | 부적절한 전자서명 확인 | N/A | 전자서명·웹훅·결제 없음 | 기능·코드 부재 확인 |
| 11 | 부적절한 인증서 유효성 검증 | N/A | 외부 TLS 요청 기능 없음, 향후 추가 시 검증 비활성화 금지 | `verify=False`·HTTP 클라이언트 검색 |
| 12 | 쿠키를 통한 정보노출 | A | 세션 ID만 저장, Secure·HttpOnly·SameSite, POST 로그아웃·no-store | 쿠키·세션·로그아웃 테스트 |
| 13 | 주석문 안의 시스템 주요정보 | A | 실제 계정·키·내부 주소 금지 | 시크릿 검사·리뷰 |
| 14 | 솔트 없는 일방향 해시 | A | Django password hasher만 사용 | 동일 비밀번호 해시 비교 |
| 15 | 무결성 검사 없는 코드 다운로드 | A | SHA-256 runtime lock, `--require-hashes`, 런타임 다운로드 금지 | lock·CI 설치·의존성 검사 |
| 16 | 반복 인증시도 제한 부재 | A | 일반·Admin 계정+네트워크 제한, 가입 rate와 해시 감사 로그 | 반복 로그인·가입 테스트 |

## 3. 시간 및 상태 - 2개

| 번호 | 항목 | 판정 | 핵심 통제 | 검증 |
|---:|---|:---:|---|---|
| 1 | 경쟁조건: 검사시점과 사용시점 | A | 조건부 지갑 차감, append-only 원장, 상품·신고 대상 row lock·현재 상태 재검증, 원자적 3인 신고 임계치 | 중복키·stale update·상태 전이·자동조치 테스트 |
| 2 | 종료되지 않는 반복문·재귀함수 | A | 상품·대화 페이지, 가입·콘텐츠 quota/rate, 업로드 상한, 전체 채팅 증분 100건·hidden 중단·backoff·DOM 200개 | 대형 입력·quota·pagination·polling 테스트 |

## 4. 에러처리 - 3개

| 번호 | 항목 | 판정 | 핵심 통제 | 검증 |
|---:|---|:---:|---|---|
| 1 | 오류 메시지 정보노출 | A | 운영 `DEBUG=False` fail-closed, `SafeExceptionMiddleware`, 일반 오류 페이지, 고정 event 로그, 독립 fallback | SEC-032 DEBUG/운영 400/403/404/500/CSRF·template 실패 비노출 회귀 통과 |
| 2 | 오류상황 대응 부재 | A | fail-closed, standalone 오류 fallback, 송금 롤백, 이미지 `save_form_data()` 정규화·commit 정리 | SEC-031 삭제·유지·교체·실패와 SEC-032 fallback 회귀 통과 |
| 3 | 부적절한 예외처리 | A | 구체 예외, 반환값 검사, bare except 금지 | 정적 검색·예외 테스트 |

## 5. 코드오류 - 5개

| 번호 | 항목 | 판정 | 핵심 통제 | 검증 |
|---:|---|:---:|---|---|
| 1 | Null Pointer 역참조 | A | `None`·삭제 객체·익명 사용자·비공개 대화 상품 placeholder 처리 | 존재하지 않는 객체·비공개 metadata 테스트 |
| 2 | 부적절한 자원 해제 | A | Pillow context manager, FileResponse 종료, commit 후 이전 파일·예외 시 신규 파일 정리 | 이미지 예외·soft delete 파일 테스트 |
| 3 | 해제된 자원 사용 | N/A | 수동 메모리 해제 없음 | FFI 코드 부재 확인 |
| 4 | 초기화되지 않은 변수 사용 | N/A | Python 언어상 즉시 예외, 린트로 보조 | Ruff·분기 테스트 |
| 5 | 신뢰할 수 없는 데이터 역직렬화 | A | JSON만 사용, pickle/marshal 금지 | 금지 API 검색 |

## 6. 캡슐화 - 4개

| 번호 | 항목 | 판정 | 핵심 통제 | 검증 |
|---:|---|:---:|---|---|
| 1 | 잘못된 세션의 데이터 정보노출 | A | 사용자 데이터를 전역에 저장하지 않고 정지 판매자 콘텐츠 비공개·인증 응답 no-store | 병렬 사용자·정지 판매자 테스트 |
| 2 | 제거되지 않은 디버그 코드 | A | 운영 DEBUG·Admin 기본 비활성화, CI deploy check·CodeQL | 배포 설정·workflow 검색 |
| 3 | Public 메소드가 Private 배열 반환 | A | 불변값 또는 defensive copy | 내부 상태 변조 테스트 |
| 4 | Private 배열에 Public 데이터 할당 | A | 검증 후 복사·불변화 | 원본 변경 영향 테스트 |

## 7. API 오용 - 2개

| 번호 | 항목 | 판정 | 핵심 통제 | 검증 |
|---:|---|:---:|---|---|
| 1 | DNS lookup에 의존한 보안결정 | N/A | DNS를 인증·인가에 사용하지 않음 | 소켓/DNS 호출 검색 |
| 2 | 취약한 API 사용 | A | 지원 버전·hash lock, 위험 API 금지, CI Bandit·pip-audit·CodeQL | Bandit 0, pip-audit 6→0, workflow 검토 |

## 검증 결과

### 2026-07-13 수정·신규 기능 표적 회귀

| 증적 | 결과 | 주요 KISA 연결 |
|---|---|---|
| 관련 8개 테스트 클래스 | **87개 통과 / 53.390초** | 공개 allowlist·XSS, 현재 비밀번호·rate, 채팅 sender·CSRF·cursor·limit, 자동조치 경합·보호·복구, 이미지 sentinel, 오류 비노출·fallback |
| 이미지 첨부 UI 직접 분기 | `ListingSecurityTests` **26개 통과 / 18.104초** | 저채도 세이지 범위, MIME accept/help, guarded 현재 이미지 URL, 내부 저장명·`MEDIA_URL` 비노출, 모바일 CSS |
| Django system check | 문제 0건 | 설정·모델 기본 일관성 |
| 확장 기능 직접 분기 | **36개 통과** | 상호확인 후기·알림·다중 이미지·하자·증거·재처리·완료 거래 복구 |
| 직전 전체 suite | **206개 통과 / 114.641초 / system check 문제 0건** | SEC-031~041과 세 확장 기능 포함; 후속 변경 전 기준선 |
| 직전 Coverage | 계측 실행 **206개 / 115.434초**, **5,778 statements / 343 miss / 94%** | 후속 변경 전 전체 계측 |
| SEC-042~044 직접 분기 | **16개 통과 / 17.393초 / system check 문제 0건** | 공개 후기 visibility 집계, slash PII 입력검증, Admin stale 상태 경합 |
| SEC-045 직접 분기 | `MultipartUploadLimitTests` **7개 통과 / 0.023초** | CSRF 전 요청 크기, 실제 chunk 누적, 시스템 자원 접근·안전 오류 응답 |
| SEC-042~047 최신 결합 직접 분기 | **40개 통과 / 17.697초 / system check 문제 0건** | 후기 공개·PII, Admin stale, multipart 자원, 하자 조건부 UI·서버 모순 거부·stale 정규화, 거래 CTA 정합성 |
| SEC-048 전 전체 suite·Coverage | **219 / 219 / 157.165초**, 계측 **219 / 219 / 162.533초·6,037 statements / 354 miss / 94%** | 직전 확정 로컬 통합 기준선 |
| SEC-048 전 정적·공급망·운영 | **Ruff lint 통과·46개 파일 format 일치, Bandit 0건, pip-audit 0건, Django check·deploy warning 0건, migration 변경 없음, Node syntax·diff PASS** | 직전 확정 로컬 게이트 |
| 현재 최종 감사 작업트리 | **251 / 251 / 147.753초**, Coverage **6,922 statements / 385 miss / 94%** | SEC-048~061 신규 회귀 포함 |
| 현재 정적·공급망·운영 | Ruff 50 files PASS, Bandit 8,082 lines/0, pip check·두 lock audit PASS, check/deploy·migration·JS·CSS·diff·secret PASS | 로컬 최종 게이트 |
| 현재 구조·CSS | **웜톤·하자 오류 UI CSS 중괄호 1112/1112** | 1440×1000·320×800 overflow 0, 주요 조작 44px 이상, 브라우저 console warning/error 0건 |

### 2026-07-12 SEC-031·032 발견 전 스냅샷

| 증적 | 결과 | 주요 KISA 연결 |
|---|---|---|
| Django tests | 120개 전부 통과 | 입력검증, Admin 권한, quota, proxy, 업로드, 시간·상태, 원장·증거 불변성; 이미지 삭제·오류 본문 분기는 미포함 |
| Coverage | 93% | 보안 분기의 회귀 범위 확인 |
| Ruff | 오류 0건 | 코드오류·예외·유지보수성 |
| Bandit | 이슈 0건 | 위험 API·명령·역직렬화·암호 사용 |
| pip-audit 최초 | `pip` 취약점 6건 | 취약한 API·공급망 위험 발견 |
| `pip` 26.1.2 후 pip-audit | 취약점 0건 | 발견 위험 조치 확인 |
| `manage.py check --deploy` | 문제 0건 | HTTPS·HSTS·쿠키·운영 설정 |
| Python·HTML 금지 패턴 검색 | 일치 0건 | N/A 기능 부재와 escape·CSRF 우회 없음 |
| SHA-256 runtime lock | `requirements.lock` 생성·CI `--require-hashes` | 코드 다운로드 무결성 |
| CI·CodeQL·Dependabot | 구성·commit SHA pin 로컬 검토 | 실제 GitHub 실행 결과는 최초 push 후 확인 |

이 과거 결과는 보존용 실행 기록이다. 이후 SEC-031~047의 직접 분기와 이미지 첨부 UI, 확장 기능 표적을 거쳐 전체 219개·94% coverage와 정적·공급망·운영 게이트를 확인했다. 이 결과는 SEC-048~061 전 기준선이며 현재 후속 변경의 재실행 결과로 갱신해야 한다.

판매자의 `ACTIVE`↔`RESERVED`, 판매자 완료 요청 뒤 구매자 확인에 의한 `SOLD`, 완료 거래 후 수정·재판매·새 대화 차단, 필수 revision과 참조 보존형 공개정보 정리는 구현했다. 그러나 결제·배송·환불까지 포함한 별도 `Order` 상태 머신은 PDF 최소 요구사항이 아니며 구현되지 않았으므로 “동일 주문 동시 수락”을 검증했다고 주장하지 않는다. 실제 시간·상태 증적은 후기 자격용 `Trade`, 상품 최신 상태 재검사와 DEMO POINT 조건부 차감·append-only 이중 원장·멱등성 테스트로 한정한다.

## 설계단계 핵심 적용

KISA 설계단계 기준은 구현 체크리스트와 별개로 다음 영역을 산출물에 반영한다.

- 입력데이터·DB 조회·시스템 자원·웹 요청·HTTP·업로드 파일 검증
- 인증 대상과 방식, 반복 인증 제한, 비밀번호, 중요자원 접근통제
- 암호키·암호연산·중요정보 저장·전송
- 예외처리와 세션통제

각 A 항목은 구현 코드와 `06_TEST_CHECKLIST.md`의 실제 증적에 연결했다. 2026-07-13 릴리스 점검에서는 클린 설치, Git 전체 이력 시크릿, 실제 배포 도메인의 HTTPS·HSTS 준비 상태를 추가 확인한다.

## PDF 25~29페이지 신규 구현 재검토 결과

- 프로필·마이페이지: 활성 일반 사용자의 `username`·`bio`만 공개하고 `ProfileForm`은 `bio`만 허용한다. 소개글 500자·autoescape, 현재 비밀번호를 요구하는 Django `PasswordChangeForm`, validators, 256자 사전 제한, 시간당 10회, `update_session_auth_hash()`를 적용해 인가·Mass Assignment·XSS·hash DoS를 검토했다.
- 전체 채팅: 동기식 Django·채널 계층 부재에서 WebSocket/SSE 연결 고갈과 새 의존성을 피하기 위해 제한된 2초 polling을 사용한다. 세션 sender, POST CSRF, 서명 cursor, 응답 100건, 본문 1,000자, 조회 40/분·송신 10/분, `textContent`, 양방향 차단 필터, hidden 중단·backoff·DOM 200개를 적용했다.
- 신고 임계치 자동조치: 가입 7일 경과·활성·미정지인 서로 다른 3명의 OPEN 신고만 원자 집계하고 신규 신고도 증거로 보존한다. 자기·판매자 신고를 제외하고 staff·superuser를 보호하며 상품은 영구삭제 대신 임시 차단하고 감사로그·관리자 복구를 제공한다.
- 운영 잔여 위험: SQLite·`LocMemCache`는 각각 PostgreSQL·공유 원자적 Redis로 전환해야 한다. polling 규모·cache 장애를 부하 시험하고 신고 공모·오탐 이의제기, 사용자 정지 복구 승인, 메시지·신고 증거 보존·파기 기간을 정책으로 확정해야 한다.
