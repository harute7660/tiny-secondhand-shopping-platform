# Changelog

TINY MARKET의 사용자 영향 변경과 보안 결정을 기록합니다. 정식 버전 태그는 아직 없으므로 현재 구현은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식의 `Unreleased`로 관리합니다. `Unreleased`는 검사 미실행을 뜻하지 않으며 아래 Verification에 실제 결과를 기록합니다.

## [Unreleased]

### Added

- Django 서버 렌더링 기반 `accounts`, `market`, `config` 애플리케이션을 추가했습니다.
- 사용자명·비밀번호 가입, 로그인, POST 로그아웃, 계정 정지를 추가했습니다.
- 상품 등록·공개 조회·소유자 수정·soft delete·찜·검색·선택적 이미지를 추가했습니다.
- 판매자의 `ACTIVE`↔`RESERVED` 상태 전이와, 판매자 완료 요청 뒤 해당 구매자 확인으로만 `SOLD`가 되는 거래 완료 흐름을 추가했습니다.
- 상품별 판매자·구매 희망자 1:1 대화와 최근 메시지 조회를 추가했습니다.
- 실제 대화 상대 차단·해제, 공개 상품 신고, 대화 상대 신고를 추가했습니다.
- 신고 상태·처리자·처리시각과 관리자 신고 완료·상품 차단·사용자 정지 action을 추가했습니다.
- 비현금성 DEMO POINT 지갑, 발행, 사용자 송금, 거래 내역, 복식부기 원장을 추가했습니다.
- 일반화된 400/403/404/500 및 CSRF 실패 화면과 보안 이벤트 로그를 추가했습니다.
- 요구사항·설계·보안약점·AI 활용·테스트·KISA 49개 기준 문서를 추가했습니다.

### Changed

- PDF 25~29페이지의 상세 시스템 설계 기능을 다시 추출해 핵심 체크리스트를 14개 기능으로 교체했습니다. 프로필·마이페이지·실시간 전체 채팅·누적 신고 자동조치를 미구현으로 정정했으며 이 변경은 문서·판정만 바로잡고 기능 코드를 추가하지 않습니다.
- 헤더·상품 카드·버튼·폼을 최종 웜톤 디자인으로 통일하고, 1080/900/700/470/360px 경계에서 Grid 열 수와 Flex 배치를 조정했습니다. 첨부 영역은 저채도 세이지 계열로 구분하되 상품 사진은 원색을 유지하고, 주요 조작 컨트롤은 최소 44px, 사용자 입력 텍스트는 강제 가로 넘침이 없도록 보완했습니다.
- 개발·CI는 `requirements-dev.lock`, 런타임은 `requirements.lock`을 `--require-hashes`로 설치하도록 구분했습니다.
- 직접 의존성 입력을 `requirements.in`, `requirements-dev.in`, 해시 잠금 산출물을 `requirements.lock`, `requirements-dev.lock`으로 관리하도록 변경했습니다.
- 기본 고정 `SECRET_KEY`를 제거하고 개발에서는 프로세스별 임시 키, 개발 외 환경에서는 필수 환경변수를 사용하도록 변경했습니다.
- 관리자 URL은 `DJANGO_ENABLE_ADMIN`으로 제어하며 `DEBUG=false`인 운영에서 기본 비활성화했습니다.
- HTTPS 프록시 판단은 `DJANGO_TRUSTED_PROXY_IPS`의 직접 peer만 신뢰하도록 변경했습니다.
- 운영 HSTS는 1년이며 `DJANGO_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_HSTS_PRELOAD`로 단계적 운영이 가능하도록 변경했습니다.
- 상품 삭제를 레코드 보존형 `DELETED` 상태로 처리하면서 연결 이미지 파일은 커밋 후 삭제하도록 변경했습니다.
- 사용자 신고를 임의 사용자 ID가 아닌 참여 대화 UUID 기반 상대방 파생 방식으로 제한했습니다.
- SQLite에서 유효하지 않은 row lock 가정 대신 조건부 잔액 UPDATE와 트랜잭션·DB 제약을 사용하도록 설계했습니다.
- 회원가입·상품 등록·메시지·신고·송금 제한을 Django cache의 원자 `add`/`incr`로 구현했습니다. 개발 기본은 `LocMemCache`이며 운영 다중 인스턴스는 Redis 같은 공유 backend가 전제입니다.
- 쌍방 후기, 관심 검색·가격 하락 알림, 대표 포함 최대 5장 사진과 조건부 하자 체크리스트를 추가했습니다.
- 완료 상품도 거래·후기 참조 행은 보존하면서 공개 설명·지역·사진·하자 정보를 정리해 목록에서 숨길 수 있도록 변경했습니다.
- 사용되지 않는 홈 `?mine=1` 분기를 제거하고 전용 `/listings/mine/` 화면을 단일 경로로 유지했습니다.

### Security

- 공개 Form에서 staff, superuser, 정지 상태, 판매자, 메시지 발신자, 신고자, 신고 대상, 송금 발신자를 제외하고 서버 세션·URL 문맥에서 결정합니다.
- 사용자명을 정규화하고 대소문자 무관 고유성을 DB에서 강제합니다.
- 최소 12자 비밀번호와 Django 유사성·흔한 값·숫자 전용 검증을 적용했습니다.
- 일반·관리자 로그인에 계정별 15분 내 5회 실패 표식과 네트워크별 30회 원시도 상한, HMAC 식별자, 짧은 원자 예약을 적용했습니다. 계정 표식만으로 정상 자격 증명을 사전 거부하지 않습니다.
- 성공 로그인은 해당 계정 상태만 지우고 네트워크 원시도 누적은 유지하도록 했습니다.
- 계정 이름만 반복해 정상 사용자를 잠그는 표적 로그인 DoS를 줄이기 위해 계정 실패 표식은 기록하되 올바른 자격 증명을 사전 차단하지 않고, 네트워크 30회 상한으로 고비용 검증을 제한하도록 변경했습니다.
- 같은 호스트의 안전한 `next`만 허용해 오픈 리다이렉트를 제한합니다.
- 사용자 차단 후 이동은 Django의 host·scheme 검증을 사용해 `//`, 역슬래시, 외부 scheme 변형을 거부합니다.
- 객체 조회에 상품 소유자·대화 참여자·명시적 관리 권한 조건을 포함했습니다.
- 사용자 차단과 신고를 실제 대화 관계에 묶고 임의 순차 사용자 ID 신고를 거부합니다.
- 관리자 action은 UI 노출과 별개로 실행 시 신고 상태 `change_report`, 상품 차단 전용 `block_listing`, 사용자 정지 전용 `suspend_user` 권한을 다시 확인합니다.
- 상품 영구 삭제는 `delete_listing`과 전용 `purge_listing`을 모두 요구하고, 서버 작성·사용자 행동·신고 증거 모델은 read-only로 제한했습니다.
- 자신, staff, superuser 계정은 bulk suspension에서 보호합니다.
- 상품 상태 변경은 서버 허용목록과 트랜잭션 내 최신 상태 확인으로 제한합니다.
- 공개 화면에 엄격한 CSP, 클릭재킹·MIME 스니핑 방지, Referrer·Permissions Policy를 적용했습니다.
- 익명 공개 HTML을 포함한 모든 동적 애플리케이션 응답과 이미지 응답에 `private, no-store`를 적용했습니다.
- JPEG·PNG·WebP를 크기·픽셀·프레임·MIME·바이트 형식으로 확인하고 UUID JPEG로 재인코딩해 메타데이터를 제거합니다.
- 이미지 교체·rollback·soft delete 경로에서 신고 증거가 아닌 저장소 파일을 정리합니다.
- 상품 신고 시점의 텍스트·가격·분류·상태·이미지 저장명과 SHA-256을 snapshot하고 참조 이미지는 공개 route 없는 private storage에 보존합니다.
- 보존 이미지 열람은 `view_report` 권한, 매 요청 SHA-256 재검증, `no-store`·`nosniff`, actor 감사 로그를 적용하고 증거 저장명에는 조회 index를 추가했습니다.
- 신고 처리·상품 차단·사용자 정지 action은 Report 행을 잠그고 `OPEN` 상태를 재검사하도록 보강했습니다.
- Listing Admin은 변경 직전 현재 행을 잠가 다시 읽고, 이미 purge된 상품의 stale 객체가 레코드를 되살리는 저장을 거부합니다.
- DEMO POINT 송금을 조건부 차감, 원자적 양쪽 반영, 합계 0의 원장 2건, 멱등키로 보호합니다.
- `Transfer`, `LedgerEntry` 생성 후 ORM 인스턴스·QuerySet 수정/삭제와 upsert 변경을 차단했습니다.
- 지갑·송금·원장을 Django Admin에서 추가·변경·삭제할 수 없게 했습니다.
- 운영 구성 오류는 DEBUG, 50자·문자 다양성·금지 prefix를 검사한 비밀키, Host, HTTPS, 프록시 신뢰 조건을 검사해 시작 단계에서 거부합니다.
- 해시 잠금 의존성 설치, lock 대상 pip-audit, 최소 workflow 권한과 commit SHA 고정을 적용했습니다.
- 상품 수정 revision을 필수 단일 값으로 만들고 누락·공백·중복 token을 폼·파일 처리 전에 400으로 거부합니다.
- 위조 multipart의 중복 하자 code를 폼 오류로 처리해 DB UNIQUE 예외와 500을 방지합니다.
- 자동 moderation은 가입 후 7일이 지난 활성·미정지 신고자만 집계하되 신규 계정 신고 원문과 증거는 OPEN 상태로 보존합니다.
- 후기 본문·평점은 불변으로 유지하면서 권한 있는 관리자가 공개 후기 숨김·제한적 복구만 수행하는 감사 action을 추가했습니다.
- 구현되지 않은 `REVERSAL` 원장 종류와 자기참조 필드를 안전한 중단 migration과 함께 제거했습니다.
- 상품 등록·수정 multipart에 인증 뒤·CSRF 전 사용자별 10회/시간 admission을 추가해 제한 초과·익명 요청의 body와 파일을 파싱하지 않도록 했습니다.

### Fixed

- 신고 대상을 모델 검증 전에 서버가 바인딩하지 않아 정상 신고가 실패하던 문제를 수정했습니다.
- 홈 템플릿이 누락된 GET context에서 500을 반환하던 문제를 수정했습니다.
- 송금 화면이 실제 지갑 대신 잔액 0을 표시하던 context 문제를 수정했습니다.
- 작은 화면에서 POST 로그아웃 경로가 숨겨지던 CSS 문제를 수정했습니다.
- 폼 도움말·오류의 ARIA 참조 ID 불일치를 수정했습니다.
- 이미지 교체·삭제 뒤 이전 저장소 파일이 남을 수 있는 정상 경로를 정리했습니다.
- 오래 열린 상품 수정 요청이 관리자 차단 상태를 되돌릴 수 있는 상태 경쟁 경로를 차단했습니다.
- 관리자 action 숨김만 우회한 forged POST가 대상 권한 없이 실행될 수 있는 경로를 실행 시 재검사하도록 보강했습니다.

### Automation

- `.github/workflows/ci.yml`에 hash-locked 설치, Django·migration·운영 검사, Ruff·format, Bandit, 85% coverage gate, pip-audit를 구성했습니다.
- `.github/workflows/codeql.yml`에 Python `security-extended` 분석을 main push/PR와 주간 일정으로 구성했습니다.
- `.github/dependabot.yml`에 Python·GitHub Actions 주간 업데이트를 구성했습니다.
- GitHub Actions 참조를 commit SHA로 고정하고 workflow 권한을 최소화했습니다.

### Verification

2026-07-13 최종 감사 변경 후 현재 작업트리 로컬 결과:

- Django tests: **251개 통과 / 147.753초**
- Coverage: **94%** (6,922 statements / 385 miss)
- Django system check: 문제 0건
- Migration check: 변경 없음
- Production `check --deploy`: 문제 0건
- Ruff lint·50 files format check: 오류 0건
- Bandit: 8,082 lines / 이슈 0건
- `pip check`: 충돌 0건; runtime·development lock `pip-audit`: 각각 알려진 취약점 0건
- 빈 대상 디렉터리의 `--require-hashes -r requirements-dev.lock`: 설치 성공

GitHub CI·CodeQL·Dependabot의 원격 상태는 실제 공개 저장소의 Actions/Security 화면에서 별도로 확인해야 합니다.

JavaScript 3개 파일 syntax, CSS 중괄호 1112/1112, `git diff --check`, 현재 파일·Git 이력 high-confidence secret scan도 통과했습니다. 최종 SHA와 원격 GitHub 증적은 아직 확정하지 않았습니다.

### Known limitations

- 운영 WSGI, TLS 종료, PostgreSQL, Redis, 백업·복구, 중앙 로그·모니터링 구성은 포함되어 있지 않습니다.
- SQLite와 `LocMemCache`는 고동시성·다중 인스턴스 운영용이 아닙니다.
- 관리자 MFA·관리 네트워크 제한은 없고 Admin CSP에는 inline style/script 예외가 있습니다.
- 실제 결제·에스크로·배송·환불·정산·현금화 기능은 없습니다.
- 이메일·전화번호·실명·GPS 신원 확인과 비밀번호 재설정은 없습니다.
- 대화는 종단간 암호화가 아니며 moderation은 수동 관리자 절차입니다.
- 원장 ORM 불변성은 직접 SQL·DB 관리자 변경을 막지 못하며 운영 reconciliation이 아직 구현되지 않았습니다.
- 이미지 저장소 callback 실패 뒤 orphan 파일을 정리하는 정기 작업은 포함되어 있지 않습니다.
- 사용자 취소·관리자 원장 보정 workflow는 제공하지 않습니다. 미완성 반전 필드는 제거했으며, 추후 구현 시 이중 승인·멱등성·대사·감사 정책을 새로 설계해야 합니다.
- 신고 증거의 보존·파기 기간과 자동 purge, 알림 fan-out의 외부 queue·worker, 성숙 계정 신고 공모·상호확인 거래 평판 조작 탐지는 운영 보완 대상입니다.
