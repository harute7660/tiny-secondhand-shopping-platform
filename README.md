# TINY MARKET

보안을 우선해 설계한 교육용 초소형 중고거래 플랫폼입니다. Django 서버 렌더링, 세션 인증, SQLite 개발 DB로 과제의 7개 필수 기능을 구현했습니다. 실제 결제, 실명 인증, 배송, 에스크로 또는 대금 정산은 제공하지 않습니다.

> **DEMO POINT는 과제 검증용 가상 값입니다.** 현금·예금·전자지급수단이 아니며 충전, 출금, 환전, 현금화 또는 구매자 보호 기능이 없습니다. 실제 돈이나 금융정보를 입력하지 마세요.

핵심 구현과 로컬 검증은 완료되었습니다. 정식 버전 태그는 아직 만들지 않아 변경 이력은 `Unreleased`로 관리합니다.

## 검증 결과

2026-07-12 최종 로컬 검증 스냅샷입니다.

| 검사 | 결과 |
|---|---|
| `python manage.py test` | **120개 통과** |
| Coverage | **93%** (3,169 statements / 223 miss) |
| `python manage.py check` | 문제 0건 |
| `python manage.py makemigrations --check --dry-run` | 변경 없음 |
| `ruff check .` / `ruff format --check .` | 오류 0건 |
| Bandit | 이슈 0건 |
| `pip-audit -r requirements.lock --disable-pip` | 알려진 취약점 0건 |
| 운영 환경 `check --deploy` | 문제 0건 |
| `pip install --require-hashes -r requirements-dev.lock --target <빈 디렉터리>` | 해시 검증 설치 성공 |

GitHub Actions CI와 CodeQL은 저장소에 구성되어 있습니다. 위 표는 로컬 검증 결과이며, 원격 워크플로 상태는 실제 GitHub 저장소의 Actions/Security 화면에서 별도로 확인해야 합니다.

## 필수 요구사항 대응

| 필수 요구사항 | 구현 | 주요 보안 통제 |
|---|---|---|
| 사용자 가입 | 사용자명·비밀번호 가입, 로그인, POST 로그아웃 | Django 비밀번호 해시, 최소 12자, 권한 필드 미노출, 로그인 제한 |
| 상품 등록·조회 | 등록·상세·수정·상태 전이·soft delete·이미지·찜 | 판매자 서버 결정, 소유자 권한, 가격 DB 제약, 이미지 재인코딩 |
| 사용자 소통 | 상품별 판매자와 구매 희망자의 1:1 대화 | 참여자 조회, 서버 결정 발신자, 차단 시 전송 금지, 캐시 기반 제한 |
| 악성 사용자·상품 차단 | 대화 상대 차단, 상품 신고, 대화 상대 신고, 관리자 조치 | 임의 사용자 ID 신고 금지, URL 문맥에서 대상 결정, 관리자 권한 분리 |
| 사용자 간 송금 | DEMO POINT 지갑·송금·거래 내역·이중 원장 | 조건부 차감, 원자적 처리, 멱등키, 음수 방지, 원장 ORM 불변성 |
| 상품 검색 | 키워드·카테고리·상태·지역·정렬·페이지네이션 | ORM, 길이 제한, 정렬 허용목록, 비공개 상품 제외 |
| 관리자 관리 | Django Admin에서 플랫폼 요소 검토·조치 | 운영 기본 비활성, 세부 권한 재검사, 보호 계정 제외, 원장 읽기 전용 |

상세 요구사항 추적은 [`docs/02_REQUIREMENTS_TRACEABILITY.md`](docs/02_REQUIREMENTS_TRACEABILITY.md)를 참고하세요.

## 기술 구성

- Python 3.12
- Django 5.2 LTS 계열
- SQLite 개발 DB
- Pillow 이미지 검증·재인코딩
- Django Template, Form, ORM, 세션 인증
- Ruff, Bandit, Coverage, pip-audit

```text
accounts/       사용자, 인증, 사용자 차단, 로그인 시도 제한
market/         상품, 대화, 신고, 지갑·송금·원장
config/         환경 설정, URL, 프록시 신뢰, 오류·보안 헤더
templates/      서버 렌더링 화면과 오류 페이지
static/         정적 CSS
docs/           요구사항·설계·보안·테스트·AI 활용 기록
var/            로컬 DB·업로드·수집 정적 파일(커밋 제외)
```

## 설치 방법

### 개발 환경

`requirements-dev.lock`은 런타임 의존성과 Ruff, Bandit, Coverage, pip-audit, pip-tools, 설치 도구까지 버전과 해시로 고정합니다.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements-dev.lock
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

활성화 없이 실행하려면 `python` 대신 `.\.venv\Scripts\python.exe`를 사용합니다.

macOS/Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements-dev.lock
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

브라우저에서 `http://127.0.0.1:8000/`에 접속합니다. `runserver`는 개발 서버이므로 인터넷에 공개하지 마세요.

### 해시 고정 런타임 설치

재현 가능한 런타임 또는 CI에서는 `requirements.lock`을 사용합니다.

```text
python -m pip install --require-hashes -r requirements.lock
python manage.py migrate
```

런타임 직접 의존성은 `requirements.in`, 개발 도구 직접 의존성은 `requirements-dev.in`, 해시 잠금 산출물은 각각 `requirements.lock`, `requirements-dev.lock`입니다. 의존성을 변경했다면 검토된 환경에서 다음 명령으로 잠금 파일을 다시 만들고 diff와 감사 결과를 확인합니다.

```text
python -m piptools compile --generate-hashes --strip-extras --output-file=requirements.lock requirements.in
python -m piptools compile --generate-hashes --allow-unsafe --strip-extras --output-file=requirements-dev.lock requirements-dev.in
pip-audit -r requirements.lock --disable-pip
```

## 관리자 기능

관리자 URL은 개발 환경에서 기본 활성화되지만, `DEBUG=false`인 운영 구성에서는 기본적으로 등록되지 않습니다. 운영에서 관리자가 꼭 필요할 때만 `DJANGO_ENABLE_ADMIN=true`를 명시합니다. 비활성 상태에서는 `/admin/`과 전용 관리자 로그인 URL이 URLconf에 존재하지 않습니다.

로컬 관리자 생성:

```powershell
$env:DJANGO_ENABLE_ADMIN = "true"
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

활성화된 관리자는 `/admin/`에서 로그인합니다. 관리자 로그인에도 계정·네트워크 제한이 적용됩니다. 사용자·상품·신고 권한은 분리되어 있으며 다음 조치는 대상 권한을 추가로 검사합니다.

- 신고 상태 처리: `market.change_report`
- 신고 상품 차단: 위 권한과 전용 `market.block_listing`
- 신고 사용자 정지: 위 권한과 전용 `accounts.suspend_user`
- 상품 영구 삭제: `market.delete_listing`과 전용 `market.purge_listing`
- 자신, staff, superuser 계정은 일괄 정지 대상에서 제외
- 신고 원문·snapshot·처리 metadata와 메시지·대화·차단·로그인 시도·지갑·송금·원장은 관리자 화면에서 직접 추가·수정·삭제 불가
- 신고 처리·상품 차단·사용자 정지 action은 선택한 Report 행을 트랜잭션에서 잠그고 `OPEN` 상태를 다시 확인한 뒤 실행
- Admin 상품 변경도 현재 DB 행을 잠가 다시 확인하며, 이미 purge된 상품의 오래된 객체를 저장해 레코드를 되살리는 요청은 거부

관리자 MFA와 관리 네트워크 제한은 구현되어 있지 않으므로 운영 전 별도 적용이 필요합니다.

## 환경변수

설정은 `config/settings.py`가 프로세스 환경변수에서 직접 읽습니다. [`.env.example`](.env.example)은 변수 목록 예시이며 `.env`를 자동 로드하지 않습니다.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `DJANGO_ENV` | `development` | `development`, `test`, `production` 중 하나 |
| `DJANGO_DEBUG` | 개발 환경에서 `true` | 운영에서 `true`이면 시작 거부 |
| `DJANGO_SECRET_KEY` | 개발 DEBUG에서 임시 생성 | 개발 외 환경에서는 필수, 운영에서는 50자 이상·문자 다양성·금지 prefix 검사 |
| `DJANGO_ALLOWED_HOSTS` | 로컬 호스트 목록 | 운영에서 필수이며 `*` 금지 |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | 비어 있음 | 필요한 HTTPS origin만 쉼표로 지정 |
| `DJANGO_ENABLE_ADMIN` | `DEBUG` 값과 동일 | 운영 기본 비활성; 필요할 때만 `true` |
| `DJANGO_TRUSTED_PROXY_IPS` | 비어 있음 | 직접 연결되는 신뢰 프록시 IP만 쉼표로 지정 |
| `DJANGO_BEHIND_HTTPS_PROXY` | `false` | 신뢰 프록시가 TLS를 종료할 때만 `true` |
| `DJANGO_SECURE_SSL_REDIRECT` | `not DEBUG` | HTTP를 HTTPS로 리다이렉트 |
| `DJANGO_HSTS_INCLUDE_SUBDOMAINS` | `not DEBUG` | HSTS를 하위 도메인에 적용 |
| `DJANGO_HSTS_PRELOAD` | `not DEBUG` | HSTS preload 의사 표시 |
| `DJANGO_SECURITY_LOG_LEVEL` | `INFO` | 보안 이벤트 로그 수준 |

`DEBUG=false`이면 HSTS 기간은 31,536,000초(1년)입니다. 하위 도메인과 preload 옵션은 실제 모든 하위 도메인의 HTTPS·인증서 갱신 준비를 확인한 뒤 사용하세요. 준비 전에는 명시적으로 `false`로 단계적 도입해야 합니다.

### 운영 fail-closed 조건

다음 잘못된 구성은 애플리케이션 시작 단계에서 거부됩니다.

- 허용되지 않은 `DJANGO_ENV`
- boolean 환경변수의 오타 또는 지원하지 않는 값
- 운영 환경의 `DJANGO_DEBUG=true`
- 개발 외 환경의 `DJANGO_SECRET_KEY` 누락
- 운영 환경의 50자 미만·낮은 문자 다양성·알려진 비안전 prefix를 가진 `DJANGO_SECRET_KEY`
- 운영 환경의 `DJANGO_ALLOWED_HOSTS` 누락 또는 `*`
- 운영 환경의 `DJANGO_SECURE_SSL_REDIRECT=false`
- `DJANGO_BEHIND_HTTPS_PROXY=true`인데 `DJANGO_TRUSTED_PROXY_IPS`가 비어 있음

신뢰 목록에 없는 직접 연결자의 `X-Forwarded-Proto`는 middleware가 제거합니다. 로그인 네트워크 식별에서 `X-Forwarded-For`를 사용하는 것도 직접 peer가 `DJANGO_TRUSTED_PROXY_IPS`에 있을 때뿐입니다. 신뢰 프록시는 클라이언트가 보낸 전달 헤더를 반드시 덮어써야 합니다.

로그인 여부와 무관하게 익명 공개 페이지를 포함한 모든 동적 애플리케이션 응답은 `Cache-Control: private, no-store`와 `Pragma: no-cache`를 사용합니다. 차단·삭제된 상품 metadata를 브라우저나 공유 프록시가 과거 HTML에서 되살리지 못하게 하기 위한 정책이며, 운영 정적 자산은 별도 immutable cache 정책을 사용할 수 있습니다.

운영 검사 예시:

```powershell
$env:DJANGO_ENV = "production"
$env:DJANGO_DEBUG = "false"
$env:DJANGO_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(64))"
$env:DJANGO_ALLOWED_HOSTS = "market.example.com"
$env:DJANGO_CSRF_TRUSTED_ORIGINS = "https://market.example.com"
$env:DJANGO_ENABLE_ADMIN = "false"
python manage.py check --deploy
python manage.py collectstatic --noinput
```

## 캐시 기반 요청 제한

회원가입, 상품 등록, 메시지, 신고, 송금은 Django cache의 원자적 `add`/`incr`를 사용해 제한합니다. 일반·관리자 로그인은 계정별 5회/15분과 네트워크별 원시도 30회/15분을 cache+DB의 짧은 예약으로 제한합니다. 성공하면 해당 계정 상태만 지우고 네트워크 누적은 유지합니다.

현재 기본 cache는 `LocMemCache`이므로 개발용 단일 프로세스에서만 의미가 있습니다. 다중 프로세스·다중 인스턴스 운영에서는 모든 인스턴스가 공유하고 원자적 증가를 지원하는 Redis 같은 cache backend를 배포 설정에서 구성해야 합니다. 현재 저장소에는 Redis 패키지·접속 설정·장애 시 fail-closed 정책이 포함되어 있지 않으므로, 이를 적용하지 않은 상태를 분산 rate limit으로 간주하면 안 됩니다.

## 상품 상태 전이

판매자가 수행할 수 있는 상태 전이는 서버 허용목록으로 제한됩니다.

```text
ACTIVE   -> RESERVED | SOLD
RESERVED -> ACTIVE   | SOLD
SOLD     -> ACTIVE
```

- 상품 수정은 `ACTIVE`, `RESERVED`에서만 가능
- 새 대화 시작은 `ACTIVE`, `RESERVED`에서만 가능
- 소유자 soft delete는 `BLOCKED`, `DELETED`가 아닌 상품을 `DELETED`로 변경
- 신고 처리 관리자는 별도 권한으로 `BLOCKED` 설정
- `BLOCKED`, `DELETED`에서 판매자 상태 변경 불가
- 잠금 후 상태를 다시 확인해 오래 열린 수정 요청이 관리자 차단을 되돌리지 못하게 함

별도 주문·수락·환불 상태 머신은 구현하지 않았습니다.

## 신고·차단과 권한 경계

- 상품 신고 대상은 공개 상품 URL 문맥에서 서버가 결정합니다.
- 사용자 신고는 자신이 참여한 대화 UUID로만 가능하며 상대방을 서버가 결정합니다.
- 순차 사용자 ID나 임의 POST 필드로 다른 사용자를 신고할 수 없습니다.
- 사용자 차단·해제도 실제 대화 상대에게만 POST로 수행합니다.
- 신고 모델은 대상 사용자와 상품 중 정확히 하나만 허용하는 DB 제약을 가집니다.
- 상품 신고 시점의 제목·설명·가격·분류·상태·이미지 저장명과 SHA-256을 snapshot으로 고정합니다.
- snapshot과 처리 metadata는 읽기 전용이며 일반 Admin 저장·추가·삭제로 바꿀 수 없습니다.
- 보존 이미지 Admin endpoint는 `market.view_report`를 요구하고 읽을 때 SHA-256을 다시 비교합니다. 변조·누락이면 404로 거부하며 정상 응답은 `private, no-store`, `nosniff`이고 열람 actor/report를 보안 로그에 남깁니다.
- 이미지 저장명 snapshot에는 DB index를 두어 교체·삭제 때 증거 참조 여부를 빠르게 확인합니다.
- 관리자 action은 화면 노출 여부와 별개로 실행 시 권한을 다시 검사해 forged POST를 막습니다.

## 이미지 처리와 삭제

- JPEG·PNG·WebP, 최대 5MB·1,200만 픽셀·단일 프레임만 허용
- 실제 바이트 형식과 Content-Type 확인
- EXIF 방향 보정 후 메타데이터 없는 UUID 이름 JPEG로 재인코딩
- 이미지 응답은 `private, no-store`, 고정 `image/jpeg`, `nosniff`
- 이미지 교체 성공 후 신고 증거가 아닌 이전 파일은 삭제하고, DB 롤백 시 새 파일 정리
- 상품 soft delete·Admin purge 시 이미지 필드를 비우되 Report snapshot이 참조한 파일은 공개 route가 없는 private storage에 보존
- 차단 상품 이미지는 공개되지 않으며 인가된 소유자·관리 권한만 guarded endpoint로 접근

운영 reverse proxy/Nginx에서 `MEDIA_ROOT` 또는 `/_private-media/`를 정적 `alias`로 직접 서빙하면 guarded image endpoint와 신고 증거 비공개를 우회합니다. 두 경로는 절대 외부에 직접 노출하지 말고 모든 이미지 요청을 Django의 권한검사 이미지 view로만 전달하세요.

저장소 삭제 실패는 로그로 남지만 호스트 장애 뒤 orphan 파일이 남을 수 있으므로 운영에서는 정기 조정 작업이 필요합니다.

## DEMO POINT 원장

- 가입 시 100,000P 발행
- 사용자 간 정수 포인트 송금, 1회 1~10,000,000P
- 조건부 `UPDATE ... balance >= amount`로 음수 잔액 방지
- 차감·가산·거래·분개를 하나의 DB 트랜잭션으로 처리
- 한 거래당 음수·양수 분개 2건, 합계 0
- 사용자와 멱등키 조합으로 중복 요청 방지
- `Transfer`와 `LedgerEntry`는 생성 후 인스턴스 `save/delete`, QuerySet `update/delete/bulk_update`, upsert형 `bulk_create` 차단

여러 행의 “분개 정확히 2건·합계 0”은 지원 DB 전체에서 이식 가능한 단일 CHECK 제약으로 표현할 수 없습니다. 게시 서비스가 생성 경계이며 운영 reconciliation은 분개 수·합계와 지갑 cache를 원장에서 다시 계산해야 합니다. 직접 SQL과 DB 관리자 권한은 ORM 보호를 우회할 수 있으므로 최소권한 DB 계정과 감사가 별도로 필요합니다.

## 테스트와 보안 검사

개발 의존성을 설치한 프로젝트 루트에서 실행합니다.

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
coverage erase
coverage run manage.py test
coverage report -m
ruff check .
ruff format --check .
bandit -c pyproject.toml -r accounts config market
pip-audit -r requirements.lock --disable-pip
```

운영 환경변수를 설정한 뒤 다음도 실행합니다.

```text
python manage.py check --deploy
```

## GitHub 자동화

- `.github/workflows/ci.yml`: 해시 잠금 설치, Django·migration·운영 검사, Ruff, Bandit, 85% coverage gate, lock 대상 pip-audit
- `.github/workflows/codeql.yml`: Python `security-extended` CodeQL, main push/PR와 매주 실행
- `.github/dependabot.yml`: Python과 GitHub Actions 의존성 주간 업데이트
- 외부 GitHub Actions는 commit SHA로 고정
- workflow 권한은 CI `contents: read`, CodeQL에 필요한 `security-events: write`로 제한

## 알려진 제약과 운영 전제

- SQLite, `LocMemCache`, 로컬 파일 저장소와 `runserver`는 단일 인스턴스 개발용입니다.
- 운영 WSGI 서버, TLS 종료, Redis, PostgreSQL, 백업·복구, 중앙 로그·모니터링은 포함되어 있지 않습니다.
- 관리자 MFA·관리 네트워크 제한은 구현되지 않았습니다.
- Django Admin 호환을 위해 `/admin/` CSP에 inline style/script 예외가 있습니다.
- 이메일·전화번호·실명·GPS 확인, 비밀번호 재설정, 실제 결제·배송·에스크로는 없습니다.
- 대화는 참여자 접근통제를 적용하지만 종단간 암호화가 아닙니다.
- 신고와 금지 상품 판정은 수동 관리자 절차입니다.
- 원장 반전 필드는 있으나 사용자 취소·관리자 반전 workflow는 제공하지 않습니다.

보안 제보와 전체 잔여 위험은 [`SECURITY.md`](SECURITY.md), KISA 49개 항목 판정은 [`docs/07_KISA_BASELINE.md`](docs/07_KISA_BASELINE.md)를 참고하세요.

## 공개 저장소 전 확인

- `.env`, `var/`, SQLite DB, 업로드, 로그, coverage, 개인정보가 추적되지 않는지 확인
- 현재 파일과 Git 전체 이력에 비밀값이 없는지 검사하고 노출된 키는 폐기·교체
- `requirements.lock`과 `requirements-dev.lock` 해시 설치를 빈 대상 디렉터리에서 재현하고 전체 검사를 새 환경에서 재확인
- GitHub Actions, CodeQL, Dependabot 실행·경고 상태 확인
- README 실행 방법을 로그아웃 환경에서 재현
- 최종 보고서에 공개 URL과 제출 커밋 SHA 기록

개발 전 과정 문서는 [`docs/`](docs/)에 있습니다. 보안 기준은 KISA **소프트웨어 개발보안 가이드(2021.12.29)**와 **Python 시큐어코딩 가이드(2023년 개정본)**입니다.
