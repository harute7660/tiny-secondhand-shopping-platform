# 설계·구현 의사결정 기록

## ADR-001 - 서버 렌더링 Django 모놀리스 우선

- 상태: 제안, 최소 요구사항 확인 후 확정
- 결정: REST API·SPA·JWT 없이 Django 템플릿, 세션, Form, ORM을 사용한다.
- 이유: 이틀 일정에서 인증·CSRF·CORS·토큰 저장을 별도로 설계하는 공격표면을 줄이고, 권한 검사를 한 서버에서 일관되게 수행할 수 있다.
- 방어 대상: 부적절한 인증·인가, CSRF, XSS, SQL 삽입, 잘못된 세션 처리.
- 대안: React + REST API. 기능 분리 이점보다 구현·검증 비용이 커서 제외한다.
- 검증: CSRF 강제 테스트, 객체 단위 권한 테스트, Django 배포 설정 검사.

## ADR-002 - SQLite 우선, PostgreSQL 전환 조건 명시

- 상태: 제안, 최소 요구사항 확인 후 확정
- 결정: 별도 DB 요구가 없으면 SQLite를 사용하고 DB 파일은 커밋하지 않는다.
- 이유: Docker 엔진이 실행 중이지 않고 시스템 Python도 없어 별도 DB 서버까지 구성하면 이틀 일정의 재현성과 검증 시간이 줄어든다.
- 보안 영향: DB 포트·계정·컨테이너·초기 비밀번호 설정을 제거해 구성 위험을 줄인다.
- 동시성 보완: `select_for_update()`에 의존하지 않고, 거래 상태 조건부 UPDATE와 `transaction.atomic()`, DB 제약조건으로 단일 성공을 보장한다.
- 전환 조건: 과제 요구, 실제 다중 사용자 배포, 다중 프로세스 동시성이 필요하면 PostgreSQL로 변경한다.
- 잔여 위험: SQLite는 고부하 운영용이 아니므로 보고서 제한사항에 명시한다.

## ADR-003 - 외부 서비스와 개인정보 최소화

- 상태: 부분 대체 - 전체 채팅 제외 결정은 ADR-010·011에서 정정, 나머지는 유지
- 결정: 요구되지 않으면 결제·배송·지도·소셜 로그인·외부 이미지 URL을 구현하지 않고 전화번호와 주소도 수집하지 않는다. 전체 채팅은 PDF 상세 요구로 확인되어 개인정보 추가 수집 없는 인증 회원 기능으로 구현한다.
- 이유: 비밀키, SSRF, 웹훅 위조, 결제 금액 변조, 개인정보 노출, 스팸·콘텐츠 신고 등 추가 보안 요구를 피한다.
- 원칙: 기능 부재 자체도 보안 통제로 기록하되, 요구사항이 바뀌면 위협 모델과 KISA 적용성 판단을 다시 수행한다.

## ADR-004 - KISA 49개 항목 전수 판정

- 상태: 확정
- 결정: 구현단계 보안약점 49개를 `A(적용)`, `N/A(기능·언어상 미적용)`, `Pending`으로 분류한다.
- 이유: N/A 항목도 단순 생략하지 않고 기능 부재, 금지 API 검색, 변경 시 재검토 조건을 증명하기 위해서다.
- 증적: `07_KISA_BASELINE.md`, 정적 검색 결과, 자동·수동 테스트.

## ADR-005 - 실제 금융 대신 교육용 이중 원장

- 상태: 확정
- 결정: 송금은 현금화할 수 없는 `DEMO POINT`로 구현하고 은행·카드·PG와 연결하지 않는다.
- 이유: PDF의 사용자 간 송금 요구는 충족하면서 금융정보, 외부 비밀키, 웹훅, 환불·정산 규제 범위를 제거한다.
- 무결성: 한 Transfer마다 송신·수신 LedgerEntry를 만들고 합계가 0인지 서비스와 테스트에서 검증한다.
- 경쟁조건: 송신자 잔액을 `balance >= amount` 조건부 UPDATE로 차감한 경우에만 나머지 원장을 같은 트랜잭션에서 생성한다.
- 중복 방지: 사용자와 idempotency key 조합을 유일하게 저장한다.
- 사용자 고지: 실제 화폐·예금·전자지급수단이 아니며 충전·출금·환전되지 않음을 화면과 README에 표시한다.

## ADR-006 - 경쟁사 장점의 선택적 결합

- 상태: 확정
- 당근에서 채택: 간단한 상품 등록, 지역 텍스트, 앱 내 대화, 사용자 차단·신고, 최소한의 신뢰 단서.
- 번개장터에서 채택: 전국 검색에 적합한 카테고리·상태 필터, 거래/송금 기록, 관리자 처리 상태.
- 보완: 매너점수 하나를 신뢰 보증처럼 제시하지 않고 가입일·완료 기록처럼 설명 가능한 정보만 사용한다.
- 보완: 안전결제 의무화의 비용·정산 지연을 재현하지 않고 수수료 0의 교육용 원장으로 범위를 제한한다.
- 보완: 신고를 제출로 끝내지 않고 OPEN/RESOLVED/DISMISSED 상태와 처리자를 남긴다.

## ADR-007 - Sites starter 미사용

- 상태: 확정
- 결정: Sites capability starter 대신 Django를 사용한다.
- 이유: starter 인증 지침은 공개 app-owned 회원가입을 직접 구성하지 않도록 제한하지만 PDF는 누구나 가입할 수 있어야 한다고 명시한다.
- 보안 대안: Django의 검증된 User, password hasher, session, CSRF, admin을 사용하고 별도 JWT/OAuth를 만들지 않는다.

## ADR-008 - 외부 UI 프레임워크 없이 기존 Flexbox·Grid 확장

- 상태: 확정
- 결정: 새 Tailwind 런타임·CDN을 추가하지 않고 기존 semantic HTML, CSS Custom Properties, Flexbox, Grid를 확장해 `#1E3A8A` 기반 반응형 디자인을 구현한다.
- 이유: 로컬 Tailwind CLI/PostCSS는 Node 빌드·lock·CI 감사 범위를 늘리고, Play CDN은 외부 script와 CSP 예외를 요구한다. 이미 완성된 Django 템플릿과 이틀 일정에서는 둘 다 회귀 범위를 키우며 요구한 디자인은 Flexbox·Grid만으로 충분하다.
- 접근성: 키보드 focus, reduced motion, 주요 조작 컨트롤의 최소 44px 터치 영역, 1080/900/700/470/360px 경계, 긴 사용자 입력 줄바꿈을 공통 규칙으로 둔다.
- 보안 영향: 외부 script·font·CSS CDN과 inline style을 추가하지 않아 기존 strict CSP와 공급망 경계를 유지한다.
- 증적: `static/css/site.css`, `templates/base.html`, `docs/06_TEST_CHECKLIST.md` TEST-R009.

## ADR-009 - 모노크롬 인터페이스와 상품 사진 원색 유지

- 상태: 확정
- 결정: 기존 semantic HTML·Flexbox·Grid와 보안 경계는 유지하고, UI chrome만 검정·흰색·중립 회색으로 전환한다. 상품 사진과 안전 의미의 오류·성공 상태색은 원색을 유지한다.
- 이유: 단순한 색 체계로 정보 위계를 강화하면서 새 외부 asset·라이브러리·CSP 예외를 추가하지 않기 위해서다. 상품 사진을 흑백으로 바꾸면 구매자가 색상·상태를 오인할 수 있다.
- 접근성: 흰색 안쪽·검정 바깥쪽 focus ring, 44px touch target, 상태 텍스트·테두리, reduced motion, 320px 무가로 overflow 원칙을 유지한다.
- 검토한 대안: 전역 `filter: grayscale(1)`과 템플릿 전면 재작성은 각각 상품 정보 왜곡과 기능·접근성 회귀 때문에 거절했다.
- 증적: `static/css/site.css`, `templates/base.html`, TEST-R010, 1440×1000·320×800 브라우저 실측.

## ADR-010 - PDF 상세 시스템 기능과 제출 검사를 분리

- 상태: 확정
- 결정: PDF 25~29페이지의 시스템 기능은 14개 전용표에서 판정하고, 자동 보안검사와 GitHub·보고서·LMS 제출은 기존 06·10번 문서에서 따로 관리한다.
- 이유: 기능 존재 여부와 배포·제출 준비를 한 점수로 합치면 테스트가 많은 구현을 기능 완료로 오인할 수 있다. 특히 프로필·마이페이지·전체 채팅·누적 신고 자동조치는 기존 18개 표에서 독립 항목이 아니었다.
- 원문 처리: 29페이지의 빨간 글씨에는 선택이라는 범례가 없으므로 전 항목을 필수로 본다. 27페이지의 상품·채팅 화면은 분리할 수 있지만 사용자가 UI에서 모두 찾을 수 있어야 한다.
- 기존 결정 정정: ADR-003의 실시간 채팅 제외는 이전의 35페이지 대기능 중심 범위 판단이다. 사용자가 25~29페이지를 시스템 기능 기준으로 지정했으므로 전체 채팅은 더 이상 N/A가 아니며 ADR-011의 통제로 구현한다.
- 보안 조건: 전체 채팅에는 인증·발신자 서버결정·출력 escaping·메시지 길이/속도 제한·페이지/보존 상한이 필요하다. 신고 임계치 자동조치는 중복·공모 신고와 보호 계정 DoS를 막는 유일 신고자 집계·관리자 복구·감사기록을 먼저 설계한다.
- 증적: `11_CORE_SUBMISSION_CHECKLIST.md`, `12_CORE_CHECKLIST_EXECUTED_2026-07-13.md`, 최초 67개 감사 테스트와 구현 후 표적 회귀 87개.

## ADR-011 - 전체 채팅은 제한된 2초 HTTP polling

- 상태: 확정
- 결정: 로그인 회원 전체 채팅은 WebSocket이나 SSE 장기 연결 대신 2초 간격의 짧은 증분 HTTP polling으로 구현한다.
- 이유: 현재 시스템은 동기식 Django 모놀리스이며 channel layer·connection coordinator가 없다. 단기 요청은 기존 세션 인증, CSRF, 보안 헤더, cache rate limit과 테스트 도구를 그대로 사용해 이틀 일정에서 검증 가능한 공격면을 유지한다.
- 보안·자원 통제: sender는 세션에서 결정하고 본문은 1,000자로 제한한다. 송신은 사용자별 분당 10회, 조회는 분당 40회이며 서명 cursor와 응답 최대 100건으로 DB·응답 크기를 제한한다. 차단 관계 양방향 메시지와 정지 발신자는 조회에서 제외한다. 브라우저는 hidden tab에서 poll을 멈추고 오류 시 backoff하며 중복 poll을 만들지 않고 렌더 노드를 200개로 제한한다.
- XSS·접근성: JSON 본문을 `innerHTML`에 넣지 않고 `textContent`로 새 노드만 `aria-live` 로그에 추가해 스크립트 실행과 반복 낭독을 막는다.
- 검토한 대안: WebSocket은 ASGI·channel layer·연결 수명·origin·분산 fan-out·새 의존성을 추가하고, SSE도 장기 연결과 worker 점유·재연결 정책이 필요해 현재 검증 범위를 넘는다.
- trade-off와 전환 조건: 전달 지연은 최대 약 2초이고 사용자 수에 비례해 요청이 증가한다. 실제 다중 인스턴스 운영에서는 PostgreSQL·Redis를 도입해 부하 시험하고, polling 비용이 기준을 넘으면 인증·origin·rate limit을 유지하는 WebSocket/channel layer로 전환한다.
- 증적: `community/views.py`, `static/js/global_chat.js`, `community/tests.py`, `community/README.md`.

## ADR-012 - 공개 프로필은 최소 필드, 계정 변경은 별도 경계

- 상태: 확정
- 결정: 공개 프로필은 활성 일반 사용자의 `username`과 최대 500자 `bio`만 보여 주고, 마이페이지 소개글과 비밀번호 변경을 별도 POST 경계로 분리한다.
- 이유: PDF의 사용자 정보·소개글 요구를 충족하되 이메일, 권한, staff/superuser, 정지 사유 같은 내부 계정 상태가 템플릿 확장으로 우발 노출되거나 Mass Assignment되는 일을 막는다.
- 통제: 공개 view는 필요한 두 column만 조회해 `User` 객체 대신 두 primitive 값을 전달한다. `ProfileForm`은 `bio`만 허용하고 저장도 `update_fields=("bio",)`로 제한한다. 비밀번호 변경은 현재 비밀번호를 요구하는 Django `PasswordChangeForm`과 validators, 256자 사전 길이 제한, 시간당 10회 제한, `sensitive_post_parameters`, 성공 후 `update_session_auth_hash()`를 사용한다.
- 검토한 대안: 범용 `UserChangeForm`은 권한·계정 상태 필드를 과도하게 노출할 수 있어 거절했고, 비밀번호를 자체 비교·hash하는 구현은 검증된 Django 흐름을 우회하므로 거절했다.
- 증적: `accounts/forms.py`, `accounts/views.py`, `accounts/tests.py`의 공개 허용목록·XSS·privileged 404·Mass Assignment·현재 비밀번호·길이·rate·세션 회귀.

## ADR-013 - 신고 자동조치는 세 명의 고유 OPEN 신고와 임시 제재

- 상태: 확정
- 결정: 같은 대상에 대한 서로 다른 신고자 3명의 `OPEN` 신고가 쌓이면 상품은 임시 `BLOCKED`, 일반 사용자는 `is_suspended=True`·`is_active=False`로 자동 전환한다.
- 이유: PDF의 신고 횟수 기반 자동조치를 충족하면서 한 사용자의 중복 제출로 제재가 발동하거나 공모 신고가 곧바로 영구 삭제를 만드는 서비스거부를 줄인다.
- 통제: 기존 조건부 UNIQUE와 reporter 잠금 위에 대상 행 `select_for_update()`와 `transaction.atomic()`을 사용한다. 상품 판매자·사용자 자신의 신고는 집계에서 제외하고, staff·superuser는 자동 정지하지 않는다. 자동 사유·시각과 보안 로그를 남긴다.
- 복구: 상품은 영구 삭제하지 않는다. `change_report`와 `block_listing` 권한을 가진 관리자가 자동 차단만 복구할 수 있고 관련 OPEN 신고를 `DISMISSED`로 바꾸며 Admin·보안 로그를 남긴다. 사용자 정지는 기존 보호된 관리자 해제 절차를 사용한다.
- 잔여 위험: 신고 계정의 연령·신뢰도 가중치, 공모 탐지, 이용자 이의제기·복구 SLA와 증거 보존기간은 운영 정책이 필요하다.
- 증적: `market/services.py`, `market/admin.py`, `market/tests.py`의 고유 집계·중복 제외·보호 계정·safe redirect·복구 권한 회귀.

## ADR-014 - DEBUG에서도 비진단 오류 응답과 독립 fallback

- 상태: 확정
- 결정: `SafeExceptionMiddleware`를 운영·개발 모두에 두어 처리되지 않은 예외와 DEBUG resolver 404를 일반 400·403·404·500 응답으로 바꾼다. 오류 템플릿 렌더링 실패 시 정적 standalone HTML을 반환한다.
- 이유: 운영 `DEBUG=false` fail-closed만으로는 로컬 발표·화면공유 중 예외가 traceback, 절대경로, 버전, source/local vars, POST 값을 노출하는 SEC-032를 막지 못했다. 오류 처리 자체의 template·context·URL 의존 실패도 기술 화면으로 재귀할 수 있었다.
- 통제: 응답과 보안 로그에 exception 객체, 요청 본문, 경로를 보간하지 않는다. 정상 validation 400, 405, 429와 resolved JSON 404는 재작성하지 않는다. SecurityHeadersMiddleware가 CSP·`nosniff`·`DENY`·`private, no-store`를 오류 응답에도 적용한다.
- 검토한 대안: 발표할 때만 환경변수를 기억하는 절차는 사람 실수에 취약해 단독 통제로 거절했다. 모든 오류를 500으로 바꾸는 middleware는 정상 상태·API 의미를 손상하므로 예상된 HTTP 예외의 status를 보존한다.
- 증적: `config/middleware.py`, `config/views.py`, `config/tests.py`의 DEBUG/production·POST 비밀값·404 pattern·template failure·헤더 회귀.

## ADR-015 - 모노크롬 UI의 세이지 업로드 예외와 보호된 현재 이미지 위젯

- 상태: 확정
- 결정: 전체 UI chrome은 ADR-009의 검정·흰색·중립 회색을 유지하되, 상품 등록·수정의 이미지 첨부 영역만 저채도 세이지 배경 `#edf4ef`와 짙은 녹색 조작색 `#335c45`를 사용한다. 업로드한 상품 사진은 상품 정보 왜곡을 막기 위해 원색으로 표시한다.
- 이유: 파일 선택은 일반 텍스트 입력과 성격이 다른 고위험 조작이므로 색과 경계로 범위를 명확히 구분할 필요가 있다. 저채도 색을 좁은 영역에만 적용해 시각적 부담을 낮추되, 특정 색이 의학적으로 눈의 피로를 줄인다고 단정하지 않고 텍스트·테두리·focus 상태로도 의미를 전달한다.
- 보안 결정: Django 기본 `ClearableFileInput`의 현재 파일명과 `FieldFile.url`을 그대로 렌더링하지 않는다. `ProtectedListingImageInput`은 소유자 검사를 수행하는 `market:listing_image` URL만 만들고, 일반화한 현재 이미지 안내·미리보기·삭제 checkbox만 표시해 내부 저장명과 무효 `/_private-media/` 링크 노출을 제거한다.
- 검증 경계: 브라우저 `accept`와 도움말은 사용성 보조일 뿐 신뢰하지 않는다. JPEG·PNG·WebP, 크기·픽셀·단일 프레임·실제 바이트 형식 검사는 기존 서버 sanitizer가 계속 수행한다.
- 검토한 대안: 업로드 영역까지 완전한 흑백으로 유지하면 파일 선택 경계를 알아보기 어렵고, 기본 위젯을 CSS로만 꾸미면 내부 저장명·직접 URL 출력 문제는 남는다.
- 증적: `market/forms.py`, `market/templates/market/widgets/protected_listing_image_input.html`, `templates/market/listing_form.html`, `static/css/site.css`, `test_image_upload_has_scoped_accessible_presentation`, `test_existing_image_widget_uses_guarded_url_without_storage_name`.

## ADR-016 - 정확한 양측 GPS 대신 공공 약속장소와 각자 ETA 범위

- 상태: 제안·구현 보류
- 제안: `거래하기`를 누르면 판매자·구매자의 정확한 좌표를 서로 표시하는 방식은 채택하지 않는다. 먼저 대화 참여자만 접근할 수 있는 거래 약속에서 공공장소·시간을 제안하고 상대가 수락한 뒤, 각 사용자가 자신의 현재 위치에서 약속장소까지 자차·대중교통 경로를 개별 조회한다. 상대에게는 원좌표나 이동 궤적 대신 선택적으로 갱신한 도착예정 범위만 보여 준다.
- 이유: 정확한 상호 위치 공유는 집·직장·생활 동선 추론, 스토킹, 강압적 동의, 오래된 위치의 오인과 제3자 API 전송이라는 새 고위험 공격면을 만든다. 과제의 중고거래 편의는 공공장소 합의와 ETA 범위만으로도 대부분 달성할 수 있다.
- 현재 경계: 위치 기능과 외부 지도 호출은 구현하지 않았으며 `Permissions-Policy: geolocation=()`와 CSP `connect-src 'self'`를 그대로 유지한다. 따라서 현재 사이트는 브라우저 위치 권한을 요청하거나 좌표를 수집·저장·전송하지 않는다.
- 후보와 선행조건: 자차·대중교통을 한 공급자에서 제공하는 TMAP API를 후보로 검토했지만 확정하지 않았다. 구현 전 API 키의 서버 비밀 관리, HTTPS와 동작 시점의 명시적 동의, 대화 참여자 객체 인가, 목적·보존기간·삭제 방법 고지, 원좌표 비저장 또는 짧은 TTL, 로그 마스킹, 철회·만료·재사용 방지, 공급자 약관·할당량과 국내 위치정보 관련 법률 검토가 필요하다.
- 구현 전환 조건: 공급자와 비용·할당량을 확정하고 개인정보·위치정보 처리방침과 테스트 계정을 준비한 뒤 별도 위협 모델·마이그레이션·인가·rate limit·보존 삭제 테스트를 통과할 때만 `geolocation`과 외부 `connect-src`를 필요한 거래 약속 화면에 한정해 연다.
- 참고: [TMAP API](https://tmapapi.tmapmobility.com/), [TMAP 대중교통 API](https://transit.tmapmobility.com/docs/routes), [W3C Geolocation](https://www.w3.org/TR/geolocation/).
