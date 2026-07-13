# Security Policy

TINY MARKET은 시큐어코딩 학습과 과제 검증을 위한 프로젝트입니다. 보안 통제를 구현했지만 실제 금융·상거래 서비스를 운영할 수준의 보증, 인력, 인프라 또는 법적 통제를 제공하지 않습니다.

## 지원 범위

정식 버전 태그와 Public GitHub URL은 아직 확정되지 않았습니다. 공개 후 보안 수정 대상은 최신 `main` 브랜치이며, 포크·개인 수정본·과거 커밋에 수정이 소급 적용된다고 보장하지 않습니다.

## 보안 문제 제보

공개 이슈에 공격 코드, 개인정보, 비밀번호, 세션·CSRF 쿠키, 토큰, 아직 수정되지 않은 취약점의 상세 재현 절차를 게시하지 마세요.

GitHub **Private vulnerability reporting**이 활성화되어 있다면 저장소 `Security` 탭으로 제보해 주세요. 비활성 상태라면 공개 이슈에는 “비공개 보안 채널이 필요하다”는 최소 정보만 남기고 별도 채널을 요청하세요.

가능하면 다음을 포함합니다.

- 영향받는 커밋과 URL·기능
- 공격에 필요한 권한과 전제
- 최소 재현 단계 및 기대/실제 결과
- 기밀성·무결성·가용성 영향
- 민감정보를 제거한 요청·응답·로그
- 제안 완화책

교육용 프로젝트이므로 고정 응답 SLA는 제공하지 않습니다. 확인된 문제는 재현, 위험도, 임시 완화, 수정, 공개 결정을 기록합니다.

## 검증 스냅샷

2026-07-13 최종 감사 변경 후 확정한 현재 작업트리 로컬 결과입니다.

- Django tests 251개 전부 통과, 147.753초
- Coverage 94% (6,922 statements / 385 miss)
- Django check·migration check·운영 `check --deploy` 문제 0건
- Ruff lint·50 files format check 오류 0건, Bandit 8,082 lines/이슈 0건
- `pip check` 충돌 0건, runtime·development lock 각각 `pip-audit` 알려진 취약점 0건
- 해시가 고정된 `requirements-dev.lock` 설치 검증 성공

GitHub CI, CodeQL, Dependabot 구성은 저장소에 포함되어 있으나 원격 실행 상태는 GitHub Actions/Security 화면에서 별도로 확인해야 합니다.

## 위협 모델

### 보호 자산

- 비밀번호 해시, 세션, 권한과 계정 정지 상태
- 사용자 상품, 이미지, 대화, 신고·차단 관계
- DEMO POINT 지갑 잔액, 거래, 원장
- 관리자 권한과 감사 기록
- `SECRET_KEY`, 배포 설정, 의존성 잠금 파일

### 주요 위협

- 다른 사용자의 UUID·순차 ID를 이용한 수평 권한 상승
- `seller`, `sender`, `reporter`, 역할, 가격, 상태, 송금 발신자 변조
- 저장형 XSS, CSRF, SQL 삽입, 오픈 리다이렉트
- 위장·대용량·메타데이터 포함 이미지
- 반복 가입·로그인·메시지·신고·송금
- 이중 지출, 중복 송금, 부분 반영, 원장 사후 변조
- 관리자 action 위조와 과도한 관리자 권한
- 신뢰하지 않은 프록시 헤더에 의한 주소·HTTPS 판단 조작
- 취약하거나 변조된 의존성

실제 카드·은행계좌·주민등록정보·정확한 GPS·PG 키는 수집하지 않습니다. 사용자 URL 서버 호출, XML·LDAP, 셸 명령, pickle 역직렬화, 외부 결제·웹훅도 제품 범위에 없습니다.

## 구현된 통제

### 인증과 세션

- Django 표준 password hasher와 검증기, 최소 12자 정책을 사용합니다.
- 가입 Form은 `username`, 비밀번호만 받고 staff·superuser·정지 필드를 노출하지 않습니다.
- 로그인 오류는 계정 존재 여부를 구분하지 않는 공통 문구입니다.
- 일반·관리자 로그인은 네트워크별 15분 내 원시도 30회를 cache와 DB의 짧은 원자 예약으로 제한해 고비용 비밀번호 검증의 상한을 둡니다. 계정별 실패 표식도 15분 내 5회를 기록하지만, 공격자가 피해자 사용자명만 반복 입력해 정상 비밀번호까지 잠그는 표적 lockout을 막기 위해 계정 표식만으로 올바른 자격 증명을 사전 거부하지 않습니다.
- 성공 로그인은 해당 계정 실패 표식을 지우고 그 성공 요청이 선점한 네트워크 예약 1회만 반환합니다. 다른 요청의 실패 누적을 일괄 초기화하지 않습니다.
- 존재 여부와 무관하게 사용자명 HMAC을 같은 DB 경로로 처리합니다. 네트워크 원시도 한도로 신규 행을 IP당 15분 최대 30개로 제한하고, 만료 후 30분이 지난 행은 주기적으로 정리합니다.
- 로그인 식별자는 원문이 아니라 `SECRET_KEY` 기반 HMAC으로 저장됩니다.
- 로그인 시 세션이 회전하고 로그아웃은 POST·CSRF 보호 후 세션을 폐기합니다.
- 세션 쿠키는 HttpOnly·SameSite=Lax이며 `DEBUG=false`에서 Secure입니다.
- 인증 응답은 `private, no-store`입니다.

### 관리자 노출과 권한 분리

- `DJANGO_ENABLE_ADMIN` 기본값은 `DEBUG`와 같으므로 운영에서는 관리자 URL이 기본 비활성입니다.
- 운영에서 꼭 필요한 경우에만 `DJANGO_ENABLE_ADMIN=true`로 URL을 등록합니다.
- 관리자 로그인도 전용 rate limit 경로를 거칩니다.
- 신고 상태 처리에는 `market.change_report`, 상품 차단에는 추가로 전용 `market.block_listing`, 사용자 정지에는 추가로 전용 `accounts.suspend_user`가 필요합니다.
- 상품 영구 삭제에는 `market.delete_listing`과 전용 `market.purge_listing`이 모두 필요합니다.
- action 목록을 숨기는 데 그치지 않고 action 실행 시 권한을 다시 검사해 forged POST를 거부합니다.
- 신고 처리·상품 차단·사용자 정지 action은 선택한 Report 행을 트랜잭션에서 잠그고 `OPEN` 상태를 다시 확인해 중복·경합 조치를 막습니다.
- Listing Admin 변경은 현재 DB 행을 잠가 존재 여부를 다시 확인하고, purge 뒤 남은 오래된 객체의 저장으로 삭제 레코드를 되살리는 경로를 거부합니다.
- 자신, staff, superuser는 일괄 계정 정지 대상에서 제외됩니다.
- 신고 원문·snapshot·처리 metadata와 메시지·대화·찜·차단·로그인 시도·지갑·거래·원장은 증거 또는 서버 작성 상태로서 Admin 직접 추가·변경·삭제가 불가능합니다.
- 후기 본문·평점·작성 방향은 Admin에서 직접 편집할 수 없습니다. `change_review` 권한이 있는 관리자만 전용 action으로 공개 후기를 숨기거나, 완료 거래의 양방향 후기 2건이 모두 존재하는 경우에 한해 숨김 후기를 복구할 수 있고 모든 조치를 감사 로그에 남깁니다.

관리자 MFA와 관리 네트워크 제한은 아직 없으며 중요한 잔여 위험입니다.

### 객체 인가와 신고·차단

- 판매자, 메시지 발신자, 신고자, 송금 발신자는 요청 값이 아닌 인증 세션에서 결정합니다.
- 상품 수정·삭제는 소유자 조건, 대화는 참여자 조건을 조회에 포함합니다.
- staff라도 차단 상품을 보려면 명시적인 `market.view_listing` 권한이 필요합니다.
- 상품 신고 대상은 공개 상품 URL 문맥에서 서버가 결정합니다.
- 사용자 신고는 신고자가 참여한 대화 UUID로만 가능하며 상대방을 서버가 결정합니다.
- 임의 사용자 ID나 POST 필드로 신고 대상을 교체할 수 없습니다.
- 사용자 차단·해제도 실제 대화 상대에게만 POST로 허용합니다.
- 양방향 차단 관계는 새 메시지와 송금을 막습니다.
- 신고 DB 제약은 대상 사용자와 상품 중 정확히 하나만 허용합니다.
- 자동 차단·정지는 가입 후 7일이 지난 활성·미정지 계정의 서로 다른 OPEN 신고만 집계합니다. 신규 계정 신고도 버리지 않고 관리자 검토용 OPEN 증거로 보존합니다.

### 상품 상태와 경쟁조건

판매자가 직접 수행할 수 있는 상태 전이는 다음 허용목록만 지원합니다.

```text
ACTIVE   -> RESERVED
RESERVED -> ACTIVE
```

- `SOLD`는 판매자가 상태 필드로 만들 수 없고, 상품별 대화에서 판매자가 완료를 요청한 뒤 해당 구매자가 확인한 원자적 거래 서비스에서만 설정합니다.
- 수정·새 대화는 허용 상태에서만 수행합니다. 상품 수정은 정확히 하나의 필수 revision token과 잠근 최신 `updated_at`을 비교해 누락·중복·오래된 요청을 거부합니다.
- soft delete는 `DELETED`, 관리자 신고 조치는 `BLOCKED`로 분리합니다.
- `BLOCKED`, `DELETED`는 판매자 상태 변경 대상이 아닙니다.
- 상태 변경·수정·삭제는 트랜잭션 안에서 현재 상태를 다시 확인해 오래 열린 요청이 관리자 차단을 되돌리지 못하게 합니다.
- 완료 상품은 거래·후기 참조용 행을 보존한 채 공개 목록에서 숨길 수 있습니다. 이때 설명·지역·사진·하자 정보는 정리하고 대화·거래·후기 기록은 보존합니다.

별도의 주문·수락·환불 상태 머신은 구현하지 않았습니다.

### 입력·출력과 CSRF

- Django Form의 명시적 필드 목록, ORM parameterization, 정렬 허용목록을 사용합니다.
- 사용자 문자열로 raw SQL, 시스템 명령, 응답 헤더 또는 서버 요청 URL을 만들지 않습니다.
- Django Template 자동 이스케이프를 유지하고 `safe`, `mark_safe`, 인라인 사용자 스크립트를 사용하지 않습니다.
- 상태 변경은 POST로 제한하고 Django CSRF middleware를 유지합니다.
- 공개 응답에는 CSP, `X-Frame-Options: DENY`, `nosniff`, same-origin Referrer Policy, 제한적 Permissions Policy를 적용합니다.
- 익명 공개 HTML을 포함한 모든 동적 애플리케이션 응답에는 `Cache-Control: private, no-store`와 `Pragma: no-cache`를 적용해 차단·삭제 전 metadata의 브라우저·공유 프록시 재노출을 막습니다. 정적 자산은 운영에서 별도 cache 정책 대상입니다.

### 프록시·HTTPS·운영 fail-closed

- 운영에서 DEBUG가 켜져 있거나 `SECRET_KEY`·`ALLOWED_HOSTS`가 누락되면 시작을 거부합니다.
- 운영 `SECRET_KEY`가 50자 미만이거나 문자 다양성이 낮거나 알려진 비안전 prefix이면 시작을 거부합니다.
- 운영 `ALLOWED_HOSTS=*`를 거부합니다.
- `DJANGO_BEHIND_HTTPS_PROXY=true`인데 `DJANGO_TRUSTED_PROXY_IPS`가 비어 있으면 시작을 거부합니다.
- 신뢰 목록 밖의 직접 peer가 보낸 `X-Forwarded-Proto`를 제거합니다.
- 로그인 네트워크 식별용 `X-Forwarded-For`도 직접 peer가 신뢰 프록시일 때만 읽습니다.
- 신뢰 프록시는 외부에서 받은 전달 헤더를 덮어쓰도록 운영자가 구성해야 합니다.
- `DEBUG=false`이면 HTTPS 리다이렉트와 1년 HSTS가 기본이며 `DJANGO_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_HSTS_PRELOAD`로 범위를 제어합니다.

HSTS preload는 코드 설정만으로 등록되지 않습니다. 실제 등록 전 모든 하위 도메인의 HTTPS와 인증서 갱신을 검증해야 합니다.

### 캐시 기반 요청 제한

- 가입은 HMAC 처리한 네트워크 식별자, 상품 등록·메시지·신고·송금은 사용자별 키를 Django cache에서 원자적 `add`/`incr`로 제한합니다.
- 현재 기본 backend는 프로세스 로컬 `LocMemCache`이므로 단일 개발 프로세스 범위입니다.
- 운영 다중 인스턴스에서는 원자적 증가를 보장하는 공유 Redis 등의 backend가 필수입니다.
- 이 저장소에는 Redis dependency·연결 설정·고가용성·cache 장애 정책이 없으므로 운영 준비가 완료된 것으로 간주하지 않습니다.

### 이미지 업로드·응답·삭제

- 전체 multipart body는 CSRF parsing 전 21MiB 누적 상한을 적용합니다. 상품 등록·수정 multipart는 인증 뒤·CSRF 전에 사용자별 10회/시간 admission을 추가해 거부 요청의 `POST`·`FILES`·body를 읽지 않습니다. 이는 reverse proxy의 body·연결·속도·timeout·source-network 제한을 대체하지 않습니다.
- JPEG·PNG·WebP, 5MB 이하, 1,200만 픽셀 이하, 단일 프레임만 허용합니다.
- 바이트 형식과 선언 Content-Type을 확인합니다.
- EXIF 방향 보정 후 UUID 파일명의 JPEG로 재인코딩해 원본 이름과 메타데이터를 제거합니다.
- 상품 수정 화면은 내부 저장명이나 `FieldFile.url`을 렌더링하지 않고, 소유자·공개 범위를 검사하는 `market:listing_image` route의 보호된 미리보기만 표시합니다.
- 이미지 응답은 고정 `image/jpeg`, `nosniff`, `private, no-store`입니다.
- 이미지 교체는 커밋 후 이전 파일을 삭제하고 DB 롤백 시 새 파일을 정리합니다.
- 상품 신고 시 제목·설명·가격·분류·상태·이미지 저장명과 SHA-256을 snapshot으로 고정합니다.
- soft delete·교체·Admin purge는 이미지 필드를 비우거나 바꾸되, Report snapshot이 참조한 파일은 공개 route가 없는 private storage에 보존하고 나머지만 커밋 후 삭제합니다.
- 보존 이미지 endpoint는 `market.view_report` 권한을 다시 검사하고 매 열람 시 저장 파일의 SHA-256을 snapshot과 상수시간 비교합니다. 누락·과대·변조 파일은 404, 정상 응답은 `private, no-store`·`nosniff`이며 actor/report를 보안 로그에 남깁니다.
- `listing_image_name_snapshot` DB index로 교체·삭제 시 증거 참조 조회가 전체 Report scan이 되지 않게 합니다.
- 차단 상품은 공개·대화 상대에게 메타데이터와 이미지를 노출하지 않고 인가된 소유자·관리 권한만 guarded endpoint로 접근합니다.
- reverse proxy/Nginx가 `MEDIA_ROOT` 또는 `/_private-media/`를 정적 alias로 직접 서빙하면 이 권한검사와 신고 증거 비공개를 우회하므로 두 경로를 절대 직접 노출하지 않고 Django 이미지 view만 통과시켜야 합니다.

삭제 callback 실패나 프로세스 중단으로 orphan 파일이 남을 수 있어 운영 저장소에서는 정기 조정이 필요합니다.

### DEMO POINT 원장

- DEMO POINT는 외부 결제·충전·출금·환전과 연결되지 않습니다.
- 송금자는 세션, 수신자는 검증된 사용자 객체, 금액은 1~10,000,000 정수 포인트입니다.
- 발신 지갑 잔액 조건이 포함된 단일 UPDATE로 음수를 방지합니다.
- 차감, 가산, 거래, 원장 2건을 하나의 DB 트랜잭션으로 처리합니다.
- 사용자·멱등키 고유 제약으로 같은 요청의 중복 반영을 막습니다.
- `Transfer`와 `LedgerEntry`는 생성 후 ORM 인스턴스 `save/delete`, QuerySet `update/delete/bulk_update`, upsert 갱신을 거부합니다.

이식 가능한 단일 DB CHECK로 “거래당 분개 정확히 2건·합계 0”을 강제할 수 없어 게시 서비스가 생성 경계입니다. 운영 reconciliation은 다음을 독립적으로 검증해야 합니다.

- 거래별 분개 수 2
- 거래별 `SUM(delta) == 0`
- 지갑 `balance_cache == SUM(ledger delta)`

ORM 보호는 직접 SQL·DB 관리자·파일 수준 SQLite 변경을 막지 못합니다. 최소권한 DB 계정, DB 감사, 백업 무결성, reconciliation이 필요합니다.

### 공급망과 자동화

- 직접 런타임·개발 의존성은 `requirements.in`, `requirements-dev.in`, 해시 잠금 결과는 `requirements.lock`, `requirements-dev.lock`으로 관리합니다.
- CI는 설치 도구까지 포함한 `pip install --require-hashes -r requirements-dev.lock`을 사용합니다.
- pip-audit는 runtime `requirements.lock`과 development `requirements-dev.lock`을 모두 대상으로 실행합니다.
- CI는 Django·migration·운영 검사, Ruff·format, Bandit, 85% coverage gate, 두 lock의 pip-audit를 수행하도록 구성되어 있습니다.
- CodeQL은 Python `security-extended` 쿼리를 push, PR, 주간 일정으로 실행하도록 구성되어 있습니다.
- Dependabot은 Python 및 GitHub Actions 업데이트를 매주 확인합니다.
- 외부 GitHub Actions는 commit SHA로 고정하고 workflow 권한을 최소화했습니다.

## 알려진 제한과 잔여 위험

- **운영 인프라 부재:** 운영 WSGI, TLS 종료, 배포 자동화, 백업·복구, 중앙 로그, 모니터링, 사고 대응 체계가 없습니다.
- **SQLite:** 단일 인스턴스 검증용입니다. 운영 DB에서 경쟁조건과 격리 수준을 다시 시험해야 합니다.
- **LocMemCache:** 분산 rate limit이 아니며 운영에는 공유 Redis 등 원자 cache가 필요합니다.
- **관리자 보호:** MFA와 관리 네트워크 제한이 없고, Admin CSP는 호환성을 위해 inline style/script를 허용합니다.
- **신원 보증 없음:** 이메일, 전화번호, 실명, GPS를 확인하지 않습니다.
- **실제 거래 보호 없음:** 결제, 에스크로, 배송, 환불, 정산, 분쟁 배상이 없습니다.
- **메시지:** 참여자 접근통제와 TLS를 전제로 하지만 종단간 암호화가 아닙니다.
- **moderation 오탐·공모:** 7일 신규 계정 유예로 즉시 Sybil 공격 비용을 높였지만, 성숙 계정 공모를 판별하는 평판·graph 분석과 이의제기 SLA는 없습니다.
- **파일 저장:** 로컬 호스트 권한과 Pillow 보안 업데이트에 의존하며 orphan 정리가 필요할 수 있습니다.
- **원장 복구:** 구현되지 않은 반전 종류·관계 필드는 공격면 축소를 위해 제거했습니다. 사용자 취소·관리자 보정이 필요하면 별도 권한·승인·대사·감사 설계를 먼저 추가해야 합니다.
- **증거 보존:** 신고 이미지 증거의 법적 보존·파기 기간, legal hold, 사용자 삭제 요청 충돌 정책과 자동 purge 작업은 아직 없습니다.
- **알림 fan-out:** 저장 검색·가격 알림 fan-out은 요청 commit 뒤 같은 프로세스에서 수행합니다. 운영 규모에서는 durable queue·재시도 worker·지표가 필요합니다.
- **거래 신뢰도:** `Trade.COMPLETED`는 두 계정의 애플리케이션 내 상호 확인이며 결제·배송·실명 거래를 외부 증명하지 않습니다. 계정 공모로 평판을 부풀릴 위험은 운영 평판 정책 대상입니다.
- **가용성:** WAF·CDN·큐·대역폭 제한과 DDoS 방어가 없습니다.

## 운영 배포 전 필수 점검

- CSPRNG로 생성한 고엔트로피 고유 `SECRET_KEY`, 정확한 `ALLOWED_HOSTS`·`CSRF_TRUSTED_ORIGINS`, `DEBUG=false`를 비밀 저장소에서 주입
- 관리자 불필요 시 `DJANGO_ENABLE_ADMIN=false`; 필요 시 MFA·관리 네트워크 제한 추가
- 신뢰 프록시 peer만 `DJANGO_TRUSTED_PROXY_IPS`에 지정하고 전달 헤더 overwrite 확인
- 모든 하위 도메인 HTTPS 준비 후 HSTS includeSubDomains/preload 결정
- PostgreSQL 등 운영 DB, 최소권한 계정, 암호화 백업과 복구 훈련
- Redis 등 공유 cache와 rate-limit 장애 정책 구성
- 업로드 저장소 비실행·비공개 설정, `MEDIA_ROOT`·`/_private-media/` direct alias 금지, Django 권한검사 view 경유 확인, orphan 파일 조정
- 보안 로그의 토큰·비밀번호·대화·개인정보 비노출과 보존 정책 확인
- 원장 reconciliation과 비정상 결과 경보 구현

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
coverage run manage.py test
coverage report -m
ruff check .
ruff format --check .
bandit -c pyproject.toml -r accounts config market
pip-audit -r requirements.lock --disable-pip
pip-audit -r requirements-dev.lock --disable-pip
python manage.py check --deploy
```

공개 전 현재 파일과 Git 전체 이력의 비밀·개인정보를 검사합니다. 유출된 비밀은 파일에서 지우는 것만으로 해결되지 않으며 즉시 폐기·교체해야 합니다.

## 변경 원칙

- 보안 수정에는 실패를 재현하고 수정 후 통과하는 회귀 테스트를 포함합니다.
- 기능 추가 시 [`docs/07_KISA_BASELINE.md`](docs/07_KISA_BASELINE.md)의 Applicable/N/A를 재평가합니다.
- 실제 결제, 외부 URL fetch·webhook, 소셜 로그인, 추가 파일 형식은 별도 위협 모델과 인증서·SSRF·재전송 검증이 선행되어야 합니다.
- 발견 사항은 [`docs/04_SECURITY_FINDINGS.md`](docs/04_SECURITY_FINDINGS.md), 사용자 영향 변경은 [`CHANGELOG.md`](CHANGELOG.md)에 기록합니다.
