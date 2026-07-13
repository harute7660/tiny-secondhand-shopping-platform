# TINY MARKET

보안을 우선해 설계한 교육용 초소형 중고거래 플랫폼입니다. Django 서버 렌더링, 세션 인증, SQLite 개발 DB를 사용하며 과제 35페이지의 7개 대기능과 PDF 25~29페이지의 상세 시스템 기능을 구현했습니다. 공개 사용자 프로필, 소개글·비밀번호 변경 마이페이지, 내 상품 목록, 상품별 1:1 대화, 로그인 회원 전체 채팅, 신고 누적 자동조치와 관리자 복구를 제공합니다. 여기에 대표 사진을 포함한 최대 5장의 상품 사진과 하자 체크리스트, 판매자·구매자가 함께 완료를 확인한 거래의 쌍방 후기, 관심 검색 조건의 새 상품 및 찜한 상품의 가격 하락 알림을 추가했습니다. 화면은 검정·흰색·중립 회색 기반의 모노크롬 디자인과 CSS Flexbox·Grid를 사용해 데스크톱부터 모바일까지 반응형으로 구성했습니다. 이미지 첨부 컨트롤 영역만 다른 입력과 부드럽게 구분하기 위해 저채도 세이지를 제한적으로 사용하며, 상품 색상은 거래 판단 정보이므로 업로드 사진 자체는 원색을 유지합니다. 실제 결제, 실명 인증, 배송, 에스크로 또는 대금 정산은 제공하지 않습니다.

> **DEMO POINT는 과제 검증용 가상 값입니다.** 현금·예금·전자지급수단이 아니며 충전, 출금, 환전, 현금화 또는 구매자 보호 기능이 없습니다. 실제 돈이나 금융정보를 입력하지 마세요.

2026-07-13 사용자 QA에서 발견한 이미지 삭제 500 오류(SEC-031)는 Django `FileField.save_form_data()`로 삭제 sentinel을 정규화해 수정했습니다. 개발·발표 중 기술 오류 화면이 내부정보를 노출할 수 있었던 문제(SEC-032)는 `SafeExceptionMiddleware`, 일반 오류 템플릿과 템플릿 렌더링까지 실패할 때 사용하는 정적 fallback으로 수정했습니다. 이후 현재 이미지의 내부 저장명·직접 media 경로를 폼에 노출하지 않고 권한검사 URL로만 미리보기하는 전용 업로드 위젯을 적용했습니다. 세 확장 기능과 보안 보강을 포함한 현재 작업트리는 전체 **206개 테스트와 94% coverage**를 통과했습니다. 실제 브라우저에서는 앞선 이미지 삭제 저장·기존 파일 제거와 DEBUG 404 기술정보 비노출을 재확인했지만, 이번 세 기능의 브라우저 인수는 아직 수행하지 않았습니다. Public GitHub 공개·원격 CI, 실제 키보드/스크린리더 확인, 외부 배포, 최종 보고서 PDF와 LMS 제출은 여전히 제출자가 완료해야 합니다. 정식 버전 태그는 아직 만들지 않아 변경 이력은 `Unreleased`로 관리합니다.

## 검증 결과

다음 표의 206개·94%가 세 기능을 포함한 최신 로컬 품질 게이트입니다. 170개와 2026-07-12 수치는 이전 비교용 스냅샷으로만 보존합니다.

| 검사 | 결과 |
|---|---|
| 2026-07-13 표적 회귀 | 프로필·마이페이지·전체 채팅·상품·자동 제재·DEBUG/운영 오류 응답 관련 **87개 통과** |
| 이미지 첨부 UI 표적 회귀 | `ListingSecurityTests` **26개 전부 통과 / 18.104초** |
| 세 기능 표적 회귀 | 다중 사진·하자 12개, 관심 검색·알림 12개, 거래 완료·후기 9개, **합계 33개 통과 / 7.285초 / system check 문제 0건** |
| 추가 보안 표적 회귀 | 관리자 다중 증거, 실패 이벤트 재처리 명령, 완료 거래 자동차단 복구 **3개 통과** |
| 현재 전체 `python manage.py test` | **206개 전부 통과 / 114.641초 / system check 문제 0건** |
| 현재 Coverage | 계측 실행 **206개 전부 통과 / 115.434초 / 5,778 statements / 343 miss / 94%** |
| 세 기능 추가 전 스냅샷 | 170개 통과 / 102.496초, 4,222 statements / 248 miss / 94% |
| 2026-07-12 과거 전체 스냅샷 | 120개 통과, 3,169 statements / 223 miss / 93%; SEC-031·032 분기는 당시 미포함 |
| 변경 후 Ruff·Bandit·pip-audit·deploy check | **Ruff lint 통과·46개 파일 format 일치, Bandit 이슈 0건, 알려진 의존성 취약점 0건, deploy check 문제 0건** |
| DB·migration | `manage.py check` 문제 0건, `makemigrations --check --dry-run` 변경 없음, 신규 migration 적용 완료 |
| CSS 정적 무결성 | 중괄호 **987개 열림 / 987개 닫힘** |
| 실제 브라우저 재검증 | 이미지 비우기 저장 후 placeholder·DB 빈 값·기존 파일 삭제 확인, DEBUG 404 기술정보 비노출, 1440px·320px overflow 0 |

GitHub Actions CI와 CodeQL은 저장소에 구성되어 있습니다. 위 표는 로컬 검증 결과이며, 원격 워크플로 상태는 실제 GitHub 저장소의 Actions/Security 화면에서 별도로 확인해야 합니다.

## 필수 요구사항 대응

| 필수 요구사항 | 구현 | 주요 보안 통제 |
|---|---|---|
| 사용자 가입 | 가입·로그인·POST 로그아웃, 공개 프로필, 소개글·비밀번호 변경 마이페이지 | 공개 필드 `username`·`bio` 허용목록, 현재 비밀번호 확인, Django validators, 입력·시도 제한, 세션 hash 갱신 |
| 상품 등록·조회 | 등록·상세·내 상품 목록·수정·상태 전이·soft delete·이미지·찜 | 판매자 서버 결정, 소유자 권한, 가격 DB 제약, 이미지 재인코딩, 삭제 sentinel 안전 정규화 |
| 사용자 소통 | 상품별 1:1 대화와 로그인 회원 전체 채팅 | 참여자 조회, 서버 결정 발신자, 차단 관계 숨김, 1,000자·송신/조회 제한, 서명 cursor, 2초 단기 polling |
| 악성 사용자·상품 차단 | 신고·관리자 조치, 서로 다른 3명의 OPEN 신고 시 상품 임시 차단·일반 사용자 임시 정지 | 중복 신고 DB 제약, 행 잠금·원자적 집계, 판매자 자기신고 제외, staff/superuser 보호, 감사로그·관리자 복구 |
| 사용자 간 송금 | DEMO POINT 지갑·송금·거래 내역·이중 원장 | 조건부 차감, 원자적 처리, 멱등키, 음수 방지, 원장 ORM 불변성 |
| 상품 검색 | 키워드·카테고리·상태·지역·정렬·페이지네이션 | ORM, 길이 제한, 정렬 허용목록, 비공개 상품 제외 |
| 관리자 관리 | Django Admin에서 플랫폼 요소 검토·조치 | 운영 기본 비활성, 세부 권한 재검사, 보호 계정 제외, 원장 읽기 전용 |

### 추가한 중고거래 기능

| 기능 | 사용자 흐름 | 주요 보안 통제 |
|---|---|---|
| 거래 완료 사용자 쌍방 후기 | 판매자가 상품의 1:1 대화에서 완료 확인 요청 → 구매자가 확인·거절 → 완료된 거래의 양측이 각 1회 후기 작성 → 두 후기 제출 뒤 함께 공개 | 대화 참여자와 방향을 서버가 결정, 상품·대화별 활성 거래 UNIQUE, 완료 거래만 허용, 첫 후기 비공개, 1~5점·500자·일 10회, 연락처·이메일·URL 패턴 거부, 공개 프로필에서 상품·가격·지역·대화 ID 제외 |
| 관심 검색·가격 하락 알림 | 홈의 검색어·카테고리·지역 저장 → 이후 등록된 일치 상품 알림, 상품 찜 → 이후 실제 가격 하락 알림 → 내 알림에서 읽음 처리 | 계정당 검색 20개, NFKC 정규화 fingerprint 중복 방지, 구조화 이벤트만 저장, `recipient+event` UNIQUE, 생성 시각 경계, 차단·정지·판매자 자신 제외, 소유자 범위 조회·삭제·읽음, 비공개 상품 상세 숨김 |
| 여러 장의 사진·하자 체크리스트 | 대표 사진과 추가 사진을 합쳐 최대 5장 등록·수정, 하자 확인 상태·허용된 하자 항목·상세 설명 표시 | 파일 5개·합계 20MB 사전 제한, 각 파일 5MB·1,200만 픽셀·JPEG/PNG/WebP 검증 후 UUID JPEG 재인코딩, 추가 사진의 상품 부모 IDOR 검사, DB rollback 고아 파일 정리, 신고 시 모든 사진 SHA-256과 하자 snapshot 보존 |

상세 요구사항 추적은 [`docs/02_REQUIREMENTS_TRACEABILITY.md`](docs/02_REQUIREMENTS_TRACEABILITY.md)를 참고하세요.

제출자가 직접 기능·보안·GitHub·보고서 PDF를 점검하는 표는 [`docs/10_USER_ACCEPTANCE_CHECKLIST.md`](docs/10_USER_ACCEPTANCE_CHECKLIST.md)를 사용하세요.

PDF 25~29페이지의 시스템 설계 기능 14개만 점검하려면 [`docs/11_CORE_SUBMISSION_CHECKLIST.md`](docs/11_CORE_SUBMISSION_CHECKLIST.md)를 사용하세요.

2026-07-13 최초 감사와 구현 후 재판정 증적은 [`docs/12_CORE_CHECKLIST_EXECUTED_2026-07-13.md`](docs/12_CORE_CHECKLIST_EXECUTED_2026-07-13.md)에 있습니다. 최종 제출 판정은 전체 자동검사와 사용자 수동 인수 결과까지 함께 확인해야 합니다.

## 기술 구성

- Python 3.12
- Django 5.2 LTS 계열
- SQLite 개발 DB
- Pillow 이미지 검증·재인코딩
- Django Template, Form, ORM, 세션 인증
- HTML5, CSS Custom Properties, Flexbox, Grid 반응형 UI
- Ruff, Bandit, Coverage, pip-audit

```text
accounts/       사용자, 인증, 사용자 차단, 로그인 시도 제한
market/         상품·다중 사진·하자, 대화·거래 완료·후기, 관심 검색·알림, 신고, 지갑·송금·원장
community/      로그인 회원 전체 채팅, 증분 polling API, 읽기 전용 Admin
config/         환경 설정, URL, 프록시 신뢰, 오류·보안 헤더
templates/      서버 렌더링 화면과 오류 페이지
static/         정적 CSS와 전체 채팅의 안전한 DOM 갱신 JavaScript
docs/           요구사항·설계·보안·테스트·AI 활용 기록
var/            로컬 DB·업로드·수집 정적 파일(커밋 제외)
```

### 주요 화면·경로

| 화면 | 경로 | 접근 |
|---|---|---|
| 홈·검색 | `/` | 공개 |
| 회원가입·로그인 | `/accounts/signup/`, `/accounts/login/` | 공개 |
| 공개 사용자 프로필 | `/accounts/users/<username>/` | 활성 일반 계정만 공개 |
| 마이페이지·비밀번호 변경 | `/accounts/me/`, `/accounts/me/password/` | 로그인 |
| 내 상품 | `/listings/mine/` | 로그인 |
| 상품 등록·상세 | `/listings/new/`, `/listings/<uuid>/` | 등록은 로그인, 상세는 공개 가능 상품 |
| 1:1 대화·전체 채팅 | `/conversations/`, `/community/` | 로그인 |
| 관심 검색·알림 | `/saved-searches/`, `/notifications/` | 로그인, 변경은 POST |
| 거래 완료·후기 | 1:1 대화 화면, `/trades/<uuid>/review/` | 해당 거래의 판매자·구매자만 |
| 지갑 | `/wallet/` | 로그인 |
| 관리자 | `/admin/` | 설정으로 활성화한 staff |

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

`migrate`는 사용자 소개글을 추가하는 `accounts` migration과 전체 채팅 테이블을 만드는 `community` migration뿐 아니라, `market.0005`의 다중 사진·하자·관심 검색·알림·거래·후기·신고 이미지 증거 구조와 `market.0006`의 후기 공개 상태·DB 제약을 적용합니다. 기존 로컬 DB에서도 새 코드를 실행하기 전에 반드시 수행하세요.

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
- 자동 임계치로 차단된 상품 복구는 `change_report`와 `block_listing`을 모두 요구하며, 해당 상품의 OPEN 신고를 `DISMISSED`로 처리하고 감사로그를 남김
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

회원가입, 상품 등록, 1:1·전체 채팅 메시지, 전체 채팅 조회, 신고, 송금과 비밀번호 변경 시도는 Django cache의 원자적 `add`/`incr`를 사용해 제한합니다. 일반·관리자 로그인은 계정별 5회/15분과 네트워크별 원시도 30회/15분을 cache+DB의 짧은 예약으로 제한합니다. 성공하면 해당 계정 상태만 지우고 네트워크 누적은 유지합니다.

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

상품 판매 상태와 별도로 아래의 “거래 완료 확인” 상태를 기록합니다. 이는 후기 작성 자격을 검증하기 위한 것이며 구매 주문, 실제 결제 승인, 배송, 취소 대금 또는 환불 상태 머신은 아닙니다.

## 거래 완료 확인과 쌍방 후기

1. 판매자가 해당 상품의 1:1 대화에서 구매자를 선택해 거래 완료 확인을 요청합니다.
2. 상품은 필요하면 `RESERVED`가 되고, 구매자는 같은 대화에서 완료를 확인하거나 거절합니다. 확인 전에는 판매자가 요청을 취소할 수 있습니다.
3. 양측 확인이 끝나면 `Trade`가 `COMPLETED`, 상품이 `SOLD`가 되며 그 상품의 일반 수정·삭제·재판매·새 대화를 막습니다.
4. 판매자와 구매자는 각자의 서버 결정 방향으로 후기 1건만 작성할 수 있습니다. 첫 후기는 `PENDING`으로 숨기고 두 후기 모두 제출됐을 때 함께 `PUBLIC`으로 전환합니다.
5. 공개 프로필에는 받은 후기의 평점·본문·작성일·작성자 역할과 평균·개수만 표시하고 상품명·가격·지역·대화·거래 UUID는 전달하지 않습니다.

거래와 후기는 URL UUID만으로 접근할 수 없고 해당 대화의 판매자·구매자여야 합니다. `Trade`의 활성 상품·대화 UNIQUE와 상태별 timestamp CHECK, `Review`의 거래·방향 UNIQUE와 평점·방향·공개상태 CHECK를 함께 사용합니다. 후기 방향·거래·공개 상태는 POST에서 받지 않고 서버가 정하며, 본문은 500자 이하·사용자당 하루 10회로 제한하고 일반적인 전화번호·이메일·URL 패턴을 거부합니다. 자동 패턴 검사는 모든 개인정보를 완벽히 탐지하지 못하므로 운영 신고·숨김 절차와 보존정책은 별도로 필요합니다.

## 관심 검색과 가격 하락 알림

- 홈에서 검색어·카테고리·지역 중 하나 이상을 적용한 뒤 관심 검색으로 저장합니다. 상태·정렬·페이지 번호는 저장하지 않으며 계정당 최대 20개입니다.
- 저장 조건은 NFKC·공백·대소문자를 정규화한 SHA-256 fingerprint로 중복을 막습니다. 저장 이후 등록된 `ACTIVE` 상품만 새 상품 이벤트 대상입니다.
- 가격 하락은 상품 수정 트랜잭션에서 잠근 최신 `old_price`보다 새 가격이 실제로 낮을 때만 이벤트로 기록합니다. 이벤트 전에 존재한 찜만 알림을 받습니다.
- 알림에는 자유 HTML 문구 대신 종류·상품·이전/현재 가격 같은 구조화된 값만 저장합니다. `recipient+event` UNIQUE로 재시도 중복을 막고, 차단 관계·정지 계정·판매자 자신은 대상에서 제외합니다.
- 저장 검색 삭제와 알림 조회·읽음은 인증 사용자 소유 범위로 제한합니다. 차단·삭제 상품이나 비활성 판매자의 알림은 제목·가격·이벤트 종류·링크 대신 일반 비공개 문구만 표시합니다.

`ListingEvent`는 상품 트랜잭션 안에 저장하지만 fan-out은 `transaction.on_commit()` 뒤 수행해 알림 오류가 정상 상품 저장을 되돌리지 않게 했습니다. 실패해 `processed_at`이 비어 있는 이벤트는 `python manage.py process_listing_events --limit 200`으로 제한된 수만 수동 재처리할 수 있습니다. 현재 callback과 재처리 명령은 별도 queue가 아니라 웹·관리 프로세스에서 동기 실행되므로, 운영에서는 worker queue와 자동 backoff·모니터링·보존기간·정리 작업으로 전환해야 합니다.

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
- 같은 대상에 대한 서로 다른 신고자 3명의 `OPEN` 신고가 쌓이면 transaction 안에서 대상 행을 잠그고 상품을 임시 `BLOCKED`, 일반 사용자를 `is_suspended=True`·`is_active=False`로 전환합니다.
- 상품 판매자의 자기신고와 사용자 자기신고는 자동 임계치에서 제외하고 staff·superuser 계정은 자동 정지하지 않습니다. 자동 결과는 보안 로그에 남고, 오탐·공모 가능성 때문에 영구 삭제는 하지 않습니다.
- 자동 차단 상품은 권한 있는 관리자가 신고를 검토한 뒤 복구할 수 있습니다. 사용자 정지는 기존 관리자 해제 절차를 사용하며, 정식 이의제기 workflow는 운영 전 추가해야 합니다.

## 이미지 처리와 삭제

- 대표 사진 1장과 추가 사진 4장, 합계 최대 5장·요청 전체 20MB로 제한하고 허용하지 않은 파일 field는 이미지 디코딩 전에 거부
- JPEG·PNG·WebP, 최대 5MB·1,200만 픽셀·단일 프레임만 허용
- 실제 바이트 형식과 Content-Type 확인
- EXIF 방향 보정 후 메타데이터 없는 UUID 이름 JPEG로 재인코딩
- 대표·추가 이미지 응답은 상품 부모와 공개 범위를 함께 검사하며 `private, no-store`, 고정 `image/jpeg`, `nosniff`
- 추가 사진 삭제 UUID가 현재 상품 소유가 아니면 거부하고, 대표 사진을 비울 때 남은 첫 추가 사진을 대표로 승격
- 이미지 교체 성공 후 신고 증거가 아닌 이전 파일은 삭제하고, DB 롤백·파일 저장 뒤 SQL 실패 시 요청에서 만든 모든 파일 정리
- 기존 이미지 삭제의 `False` sentinel은 `FileField.save_form_data()`에 전달해 빈 파일값으로 정규화하고, boolean을 파일 객체로 저장하지 않음
- 하자 공개 상태는 `확인한 하자 없음`·`하자 있음`·`확인하지 못함` 중 하나이며, 하자 있음은 허용된 체크리스트 항목을 요구하고 기타 항목은 상세 설명을 요구
- 하자 상세는 1,000자 이하로 저장하고 Django template auto-escape로 출력
- 상품 신고 시 대표·추가 사진 전체의 저장명·SHA-256·순서와 하자 상태·항목·설명을 snapshot으로 고정
- 상품 soft delete·Admin purge 시 이미지 필드를 비우되 Report snapshot이 참조한 모든 파일은 공개 route가 없는 private storage에 보존
- 차단 상품 이미지는 공개되지 않으며 인가된 소유자·관리 권한만 guarded endpoint로 접근
- 상품 수정 폼의 현재 이미지도 guarded endpoint만 사용하고 내부 저장명과 `MEDIA_URL`을 HTML에 노출하지 않음

운영 reverse proxy/Nginx에서 `MEDIA_ROOT` 또는 `/_private-media/`를 정적 `alias`로 직접 서빙하면 guarded image endpoint와 신고 증거 비공개를 우회합니다. 두 경로는 절대 외부에 직접 노출하지 말고 모든 이미지 요청을 Django의 권한검사 이미지 view로만 전달하세요.

저장소 삭제 실패는 로그로 남지만 호스트 장애 뒤 orphan 파일이 남을 수 있으므로 운영에서는 정기 조정 작업이 필요합니다.

## 오류 응답의 정보 비노출

`SafeExceptionMiddleware`는 개발·운영 모드 모두에서 처리되지 않은 예외를 사용자용 400·403·404·500 응답으로 바꾸며 예외 문자열, 요청 본문, 경로를 응답이나 보안 로그에 넣지 않습니다. DEBUG 모드의 미일치 URL도 URL pattern 목록 대신 일반 404를 반환합니다. 오류 템플릿 렌더링 자체가 실패하면 template engine·context processor·URL reverse에 의존하지 않는 정적 HTML fallback을 사용합니다. 운영에서는 이 방어와 별개로 반드시 `DJANGO_DEBUG=false`를 유지해야 합니다.

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
python manage.py test market.test_multi_image_defects market.test_saved_search_notifications market.test_trade_reviews
python manage.py test
coverage erase
coverage run manage.py test
coverage report -m
ruff check .
ruff format --check .
bandit -c pyproject.toml -r accounts community config market
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
- 운영 WSGI 서버, TLS 종료, Redis, PostgreSQL, 백업·복구, 중앙 로그·모니터링은 포함되어 있지 않습니다. 다중 사용자 운영 전 SQLite는 PostgreSQL로, 프로세스별 `LocMemCache`는 원자적 공유 Redis로 전환해야 합니다.
- SQLite에서는 `select_for_update()`가 실질적인 행 잠금을 제공하지 않으므로 관심 검색 20개 quota와 거래·상품 상태 전이의 동시성 통제는 개발 환경의 최선 노력입니다. 운영에서는 PostgreSQL 행 잠금과 경합 회귀·부하 시험으로 다시 검증해야 합니다.
- 상품 이벤트의 알림 fan-out은 DB commit 뒤 `transaction.on_commit()` 콜백에서 현재 요청 프로세스가 동기 실행합니다. 제한형 수동 재처리 명령은 있지만 작업 큐·예약 실행·알림 보존/파기 자동화는 없으므로 운영 전 worker 기반 비동기 처리, backoff·모니터링과 보존 정책을 추가해야 합니다.
- 관리자 MFA·관리 네트워크 제한은 구현되지 않았습니다.
- Django Admin 호환을 위해 `/admin/` CSP에 inline style/script 예외가 있습니다.
- 이메일·전화번호·실명 확인, 비밀번호 재설정, 실제 결제·배송·에스크로는 없습니다. 판매자·구매자의 정확한 실시간 GPS 상호 공유와 교통수단별 ETA도 위치 개인정보·동의·외부 지도 API 운영 범위가 필요해 현재는 의도적으로 구현하지 않았습니다.
- 대화는 참여자 접근통제를 적용하지만 종단간 암호화가 아닙니다.
- 전체 채팅은 WebSocket/SSE가 아니라 2초 간격의 제한된 polling이므로 최대 약 2초 지연이 있고, 사용자·인스턴스가 늘면 연결·쿼리 부하 시험과 WebSocket/채널 계층 전환 검토가 필요합니다.
- 신고 임계치는 임시 가시성·계정 조치일 뿐 금지 상품의 진위를 자동 확정하지 않습니다. 신고 공모·오탐 이의제기, 사용자 복구 승인, 메시지·신고 증거 보존·파기 기간은 운영 정책으로 확정해야 합니다.
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
