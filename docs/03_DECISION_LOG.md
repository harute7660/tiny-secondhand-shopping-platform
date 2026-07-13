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

- 상태: 대체됨 — 레이아웃·원색 상품 사진 원칙은 유지하고 색상 팔레트는 ADR-020이 대체
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

- 상태: 부분 대체 — 보호 widget·세이지 첨부 경계는 유지하고 전역 팔레트는 ADR-020이 대체
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

## ADR-017 - 상호 확인된 거래만 쌍방 후기를 허용하고 두 후기를 동시에 공개

- 상태: 확정
- 결정: 판매자가 임의의 구매자 ID를 제출하는 대신 자신이 참여한 상품 대화에서 거래 완료를 요청하고, 그 대화의 구매자가 확인한 `Trade.COMPLETED`만 후기의 권한 근거로 사용한다. 후기 방향은 로그인 사용자와 거래 참여자로 서버가 결정하며, 같은 거래·방향에는 한 건만 허용한다.
- 공개 정책: 첫 번째 후기는 `PENDING`으로 보관해 상대에게 내용을 공개하지 않는다. 양쪽 후기가 모두 작성되면 같은 transaction에서 둘을 `PUBLIC`으로 바꿔 동시에 공개한다. 공개 프로필은 공개 후기의 별점·본문·작성일·작성자 역할만 primitive 값으로 전달하고 상품명·가격·지역·거래 UUID는 노출하지 않는다.
- 이유: 기존 `Listing.SOLD`만으로는 실제 구매자를 식별할 수 없고 판매자가 단독으로 상태를 바꿀 수 있어 거래하지 않은 사용자의 후기, 구매자 위조와 보복성 맞후기를 막을 수 없다. 대화로 구매자를 고정한 상호 확인과 blind publication이 권한·공정성 경계를 함께 만든다.
- 통제: 완료 요청·응답은 `transaction.atomic()`과 상품·거래 행 잠금을 사용하고, 상품 및 대화별 진행/완료 거래의 조건부 UNIQUE와 상태별 timestamp CHECK를 둔다. `SOLD` 전환은 구매자 확인 서비스에서만 수행하며 일반 상태 변경은 `ACTIVE`↔`RESERVED`로 제한한다. 진행 거래 중에는 수정·숨김·재판매·새 대화를, 완료 뒤에는 수정·재판매·새 대화를 차단한다. 완료 상품 숨김은 참조 행·거래·후기를 보존하고 사용자 작성 공개 정보·사진·하자만 정리한다.
- 검토한 대안: 판매자의 단독 `SOLD` 변경, POST로 전달된 buyer ID 신뢰, 첫 후기 즉시 공개는 각각 거래 위조·IDOR·보복 후기를 만들기 때문에 채택하지 않았다. 실결제나 대면 증명을 수집하는 방식은 개인정보와 운영 복잡도가 과도해 이번 범위에서 제외했다.
- 잔여 위험: 판매자와 구매자가 공모하면 실제 물품 전달 없이 상호 완료할 수 있고 물리적 거래 분쟁까지 시스템이 증명하지는 못한다. 거절·취소 시 요청 전 상태를 복원하므로 최초 상태가 `RESERVED`였다면 계속 예약 상태로 남는다. 운영에서는 예약 해제 주체·만료시간, 이상 후기 패턴 탐지, 이의제기·숨김 절차와 PostgreSQL 기반 동시성 재검증이 필요하다.
- 증적: `market/models.py`, `market/services.py`, `market/views.py`, `market/forms.py`, `market/test_trade_reviews.py`의 상호 완료·거절/취소 복구·IDOR·legacy SOLD·완료 후 변경 차단·사후 차단 악용·blind 공개·중복·PII·XSS 회귀.

## ADR-018 - 관심 검색과 가격 하락 알림은 구조화 이벤트에서 멱등 fan-out

- 상태: 확정
- 결정: 관심 검색 조건은 정규화한 검색어·카테고리·지역과 SHA-256 fingerprint로 저장한다. 새 상품 등록은 `NEW_MATCH`, 찜한 상품의 실제 가격 인하는 잠근 수정 전·후 가격으로 `PRICE_DROP` `ListingEvent`를 생성하고, 사용자별 `Notification`으로 fan-out한다.
- 이유: view에서 임의 문자열 알림을 즉시 보내면 rollback된 상품의 유령 알림, 여러 조건에 매칭된 중복, 가격 인상·변조된 이전 가격, 이벤트 뒤 추가한 구독의 소급 알림이 발생할 수 있다. 이벤트 사실과 사용자 전달 상태를 분리하면 재시도·감사·중복 방지가 가능하다.
- 통제: 이벤트 형태 CHECK와 상품별 `NEW_MATCH` UNIQUE, `(recipient, event)` UNIQUE를 두고 `select_for_update()`로 `processed_at`을 직렬화한다. 이벤트 시각 이전에 존재한 저장 검색·찜만 대상으로 하며 판매자 자신, 양방향 차단 사용자, 비활성·정지 계정을 제외한다. 여러 검색 조건은 사용자별 한 건으로 합치고 200건 단위 iterator·bulk insert를 사용한다. fan-out은 상품 transaction의 `on_commit` 뒤 실행하며 실패 시 사용자 상품 변경은 유지하고 `processed_at=NULL`과 고정 보안 로그를 남겨 멱등 재실행할 수 있게 한다.
- 표시·인가: 저장 검색 삭제, 개별 읽음과 전체 읽음은 로그인 사용자 소유 범위로만 조회한다. 알림 열람 시 현재 상품 공개 가능성을 다시 평가하고 비공개 상품은 제목·가격·이벤트 종류 대신 일반 안내만 보여 준다. 검색어·상품명은 템플릿 autoescape 경계를 유지한다.
- 검토한 대안: Django signal에서 동기 발송하거나 알림 본문 전체를 저장하는 방식은 transaction 경계와 현재 공개 상태를 놓치기 쉬워 채택하지 않았다. 현재 규모에서 외부 queue를 새로 도입하는 대신 DB 멱등성과 제한된 batch로 최소 구현했다.
- 잔여 위험: 현재 매칭은 웹 프로세스에서 저장 검색을 선형 탐색하므로 사용자가 늘면 지연과 자원고갈 위험이 있다. 이벤트별 중복은 막지만 판매자가 가격을 반복 인상·인하하면 하락 이벤트가 계속 생길 수 있어 최소 하락폭·cooldown·묶음 알림 정책이 필요하다. 미처리 이벤트를 제한 수만 재실행하는 `process_listing_events` 명령은 제공하지만 자동 worker가 아니므로, 운영 전 PostgreSQL·작업 queue·backoff/지연 지표·알림 보존기간을 추가해야 한다.
- 증적: `market/models.py`, `market/services.py`, `market/views.py`, `market/test_saved_search_notifications.py`의 정규화 중복·20개 quota·소유자 IDOR·시각 경계·사용자별 중복 제거·잠긴 가격 snapshot·차단/정지 제외·비공개 metadata·XSS·멱등·`on_commit` 회귀.

## ADR-019 - 대표 사진 1장과 추가 4장, 하자 허용목록, 신고 시 다중 증거 snapshot

- 상태: 확정
- 결정: 기존 `Listing.image`를 대표 사진으로 유지하고 `ListingImage`에 위치 1~4의 추가 사진을 두어 총 5장까지 순서를 보존한다. 하자는 `NONE_KNOWN`·`PRESENT`·`UNKNOWN` 공개 상태와 8개 `ListingDefect.Code` 허용목록으로 저장하며 `OTHER`는 상세 설명을 요구한다. 상품 신고 시 대표·추가 사진 각각의 내부 저장명과 SHA-256, 하자 상태·코드·설명을 `Report`와 `ReportImageEvidence`에 snapshot한다.
- 이유: 대표 사진 한 장만으로는 상품 상태를 충분히 설명하기 어렵고 자유입력 하자 코드는 위조·불일치가 쉽다. 반대로 사진을 단순 공개 media URL로 늘리면 IDOR·저장 경로 노출·대용량 처리·삭제 뒤 신고 증거 소실이라는 공격면이 커지므로 사진 수명주기와 증거 경계를 함께 설계해야 한다.
- 통제: 요청의 모든 파일 필드를 sanitizer 전에 허용목록 검사하고 대표를 포함해 최대 5장·합계 20MB를 제한한다. 각 파일은 기존 JPEG/PNG/WebP·5MB·12MP·재인코딩 검사를 거친다. 수정 폼의 삭제 ID는 현재 상품의 선택지로만 만들고 transaction 안에서 잠근 자식 집합을 다시 확인하며, 대표 삭제 시 첫 추가 사진을 승격한다. DB 실패 뒤 요청에서 새로 쓴 `FieldFile`만 정리하고 기존 파일 삭제는 commit 뒤 수행한다. 추가 사진 route는 공개 가능한 부모와 `(listing, image_pk)`를 함께 조회하고 `private, no-store`·`nosniff`를 적용한다.
- 증거 통제: 신고 증거 파일은 상품 삭제 뒤에도 참조 여부를 확인해 보존한다. 관리자 다중 증거 route는 독립 목록으로 등록하지 않고 `ReportAdmin`의 조회 권한을 다시 검사하며 `(report, evidence_id)`로 자식을 한정한다. 파일은 5MB+1byte만 읽고 초과를 거절한 뒤 `hmac.compare_digest()`로 snapshot digest를 검증하며 내부 저장명을 HTML에 노출하지 않는다.
- 검토한 대안: 다중 `<input>` 값을 그대로 모델에 저장하거나 자유 문자열 하자 태그를 허용하는 방식은 개수·형식·도메인 불변식을 보장하지 못해 거절했다. 외부 공개 object URL은 현재 private media 정책과 맞지 않아 보호 application route를 확장했다.
- 잔여 위험: ADR-021로 애플리케이션 parser 전 21MiB 상한을 추가했지만 reverse proxy가 애플리케이션보다 먼저 전체 body를 수신할 수 있으므로 운영 body/time/connection limit도 필요하다. object storage rollback 정리는 best-effort이며 주기적 orphan 대사가 필요하고, 신고 증거의 법적 보존기간·삭제 승인·접근 감사 정책은 운영자가 확정해야 한다.
- 증적: `market/models.py`, `market/forms.py`, `market/views.py`, `market/admin.py`, `market/storage.py`, `market/test_multi_image_defects.py`, `market/test_admin_image_evidence.py`의 5장·합계 제한·예상 밖 field·child IDOR·stale 삭제 ID·대표 승격·하자 허용목록·XSS·다중 snapshot·삭제 뒤 보존·orphan 정리·관리자 report scope 회귀.

## ADR-020 - 웜톤 전역 팔레트와 기존 보안·접근성 경계 유지

- 상태: 확정
- 결정: 모노크롬 전역 팔레트는 크림 canvas `#f7f3ec`, warm-white surface `#fffdfc`, 짙은 갈색 text `#211d19`, 테라코타 primary `#8b3e2a` 중심의 웜톤으로 교체한다. 상품 사진은 원색, 파일 첨부 영역은 기존 저채도 세이지, 성공·경고·위험 상태는 색과 텍스트를 함께 유지한다.
- 이유: 중고거래 화면의 장시간 탐색에서 순수 흑백의 강한 대비를 완화하면서 카드·폼·상태·주요 행동의 위계를 일관되게 만들기 위해서다. 외부 UI library·font·image asset 없이 CSS 변수와 마지막 cascade만 바꿔 CSP와 공급망 경계를 늘리지 않는다.
- 접근성·반응형: `:focus-visible`의 3px focus와 보조 ring, 주요 조작 최소 44px, `prefers-reduced-motion`, 긴 입력 줄바꿈과 기존 1080/900/700/470/360px 경계를 유지한다. 브라우저에서 1440×1000과 320×800의 문서 가로 overflow가 0이고 주요 조작이 44px 이상임을 확인했다. 실제 키보드·스크린리더·200% 확대는 별도 사용자 인수로 남긴다.
- 보안 영향: 템플릿·route·인가·업로드 처리는 바꾸지 않고 외부 asset·inline script를 추가하지 않는다. 색은 상태의 유일한 표현 수단으로 사용하지 않는다.
- 증적: `static/css/site.css`의 final warm cascade, `templates/base.html` cachebuster, `docs/06_TEST_CHECKLIST.md` TEST-R013.

## ADR-021 - multipart 전체 요청은 CSRF 파싱 전에 21MiB로 제한

- 상태: 확정
- 결정: 이미지 Form의 20MB batch 검사와 별도로 모든 multipart POST·PUT·PATCH에 21MiB request-wide 상한을 적용한다. 알려진 `Content-Length`는 body read 전에 거부하고, 누락·chunked·축소된 길이는 첫 upload handler가 여러 파일의 실제 chunk를 누적해 제한한다.
- 이유: CSRF middleware가 view보다 먼저 `request.POST`를 파싱할 수 있어 Form 검사는 parser·임시 저장소·worker 자원 소비를 막는 첫 경계가 될 수 없다. 반대로 `Content-Length`만 신뢰하면 공격자가 헤더를 누락·축소해 조기 거부를 우회할 수 있다.
- 배치 이유: 이미지 합계 허용값 20MiB에 multipart boundary·정상 text field 여유 1MiB를 더했다. 기존 `DATA_UPLOAD_MAX_MEMORY_SIZE=6MiB`, 파일별 memory 5MiB, 최대 5파일과 이미지 sanitizer는 심층 방어로 유지한다.
- 오류·보안 경계: middleware는 CSRF 앞에 두되 response-only security header middleware 안쪽에 배치해 초과 응답도 일반 400, CSP, `nosniff`, frame `DENY`, `private, no-store`를 받는다. 내부 예외명과 limit 문자열은 응답에 포함하지 않는다.
- 잔여 위험: reverse proxy의 선수신·slow upload·연결 고갈은 application middleware가 막지 못한다. 운영 proxy에 같거나 더 작은 body limit, read timeout, connection/rate limit을 설정하고 부하 시험해야 한다.
- 증적: `config/middleware.py`, `config/settings.py`, `config/tests.py`의 `MultipartUploadLimitTests` 7개.

## ADR-022 - 하자 입력은 조건부 공개하되 서버 불변조건을 신뢰 경계로 유지

- 상태: 확정
- 결정: `하자 있음(PRESENT)`을 선택했을 때만 하자 체크리스트와 상세 입력을 표시·활성화한다. `하자 없음` 또는 `확인하지 못함`으로 바꾸면 브라우저에서 숨길 뿐 아니라 관련 checkbox와 상세를 비활성화·초기화한다. `기타(OTHER)`를 고르면 상세 입력에 native `required`를 동적으로 적용한다.
- 서버 경계: JavaScript는 사용성 보조이며 보안 근거로 신뢰하지 않는다. `ListingForm.clean()`은 `PRESENT`에 하나 이상의 허용 code를 요구하고 비-`PRESENT`에 code를 보낸 위조 요청을 계속 거부한다. 정상 비-`PRESENT` 요청에 브라우저·과거 데이터의 stale 상세가 남아 있으면 빈 값으로 정규화해 화면 상태와 저장 상태를 일치시킨다.
- 오류·제출 상태: 서버 오류는 페이지 상단 요약에 모든 필드 오류와 해당 입력 링크를 제공하고 요약에 포커스·스크롤한다. 조건부 필드에 오류가 있으면 숨기지 않아 사용자가 원인을 고칠 수 있게 한다. 폼의 `novalidate`를 제거해 기본 HTML 검증을 복구하고, 유효한 제출 뒤 버튼을 `저장 중…`·`aria-busy`·disabled 상태로 바꿔 응답 지연을 새로고침 실패로 오인하거나 중복 제출하는 일을 줄인다.
- 이유: 항상 보이는 하자 상세는 `하자 없음`·`미확인`에서도 무엇을 입력해야 하는지 혼동시키며, 숨기기만 하고 값을 남기면 stale 문구가 잘못 저장될 수 있다. 반대로 클라이언트 제어만 사용하면 crafted POST로 상태·code 조합을 위조할 수 있으므로 UI와 서버 불변조건을 분리한다.
- 접근성 경계: 오류 요약은 키보드 사용자가 곧바로 인지하고 링크로 이동할 수 있게 하며, 숨은 컨트롤은 disabled와 `aria-hidden`을 함께 사용한다. 실제 스크린리더·키보드·200% 확대 인수는 여전히 제출 전 수동 항목이다.
- 증적: `market/forms.py`, `templates/market/listing_form.html`, `static/js/listing_form.js`, `static/css/site.css`; `MultiImageDefectSecurityTests`·`MultipartUploadLimitTests`·`ListingAdminSecurityTests`·`TradeReviewSecurityTests` 최신 결합 **40개 / 17.697초 / system check 0건 / Ruff PASS**.

## ADR-023 - 업로드 오류는 파일을 재결합하지 않고, 수정·거래 UI는 최신 상태를 명시적으로 비교

- 상태: 확정
- 업로드 결정: 파일 field·개수·합계 preflight 오류가 나면 거부 파일 객체를 `ListingForm`에 다시 bind하거나 디코딩하지 않는다. 길이 제한을 통과한 텍스트 입력만 유지하고 사진 재선택을 안내한다. 브라우저는 기존·삭제·신규 선택을 합친 최종 5장, 신규 파일 장당 5MiB와 합계 20MiB를 사전 검증하지만, 보안 판정은 서버 preflight·Django 5파일 parser 상한·이미지 sanitizer·21MiB middleware가 독립 수행한다.
- 사진 편집 결정: 추가 사진의 보호된 썸네일, 대표부터 이어지는 번호, 삭제 checkbox를 동일 label로 결합한다. 대표 삭제 시 남은 첫 추가 사진이 승격됨을 도움말에 명시한다. 화면 결합은 오선택을 줄이는 UX 통제이며, 서버는 제출 UUID가 잠근 현재 상품 자식 집합의 부분집합인지 계속 검증한다.
- 동시 수정 결정: 수정 GET에 `updated_at` microseconds 기반 hidden `revision`을 제공하고, POST는 정확히 하나의 비공백 token을 파일 처리 전에 요구한다. 누락·공백·중복은 400, 잠근 최신 행과 불일치는 409로 전체 비저장한다. 공개 API로 확장할 때도 같은 필수 `If-Match` 의미론을 유지한다.
- 거래 UI 결정: 상품 전체에서 진행·완료 중인 거래와 현재 대화의 거래를 별도로 조회한다. 다른 대화의 활성 거래가 있으면 현재 대화에는 완료 CTA를 보이지 않고 상대 구매자 식별정보도 공개하지 않는다. 현재 대화에서 닫힌 최신 요청이 거절 또는 취소라면 해당 상태·시각을 표시한다.
- 공통 오류 결정: 상품·메시지·후기 Form은 같은 오류 요약 partial, 오류 포커스 이동, native validation, 유효 제출의 `aria-busy`·disabled·진행 문구를 사용한다. JavaScript는 중복 제출과 탐색 비용을 줄이는 보조 계층이며 CSRF·Form·인가·rate limit을 대체하지 않는다.
- 이유: 거부 파일을 다시 처리하는 비용·혼동, 썸네일과 삭제 선택의 오연결, 두 탭의 lost update, 상품 전체 거래 상태와 개별 대화 CTA의 불일치는 각각 가용성·데이터 무결성·상대 최소공개를 훼손한다. 사용자 피드백과 서버 상태 검증을 같은 변경에서 일치시켜야 “저장된 사실”과 “화면이 약속한 결과”가 어긋나지 않는다.
- 검토한 대안: 오류 후 파일 input 값을 복원하는 방식은 브라우저 보안상 신뢰할 수 없고 파일 객체 재사용 위험이 있어 채택하지 않았다. 마지막 저장 승리 방식은 가격·하자·알림 근거를 조용히 덮으므로 거절했다. 모든 대화에 상품의 진행 거래 상대를 표시하는 방식은 개인정보 최소화에 어긋난다.
- 증적: `market/forms.py`, `market/views.py`, `templates/includes/form_error_summary.html`, `templates/market/listing_form.html`, `templates/market/conversation_detail.html`, `templates/market/review_form.html`, `static/js/listing_form.js`, `static/js/secure_form.js`; 최신 결합 **40개 / 17.697초 / system check 0건**, 전체 tests **219 / 219 / 157.165초**, Coverage **219 / 219 / 162.533초·6,037 statements / 354 miss / 94%**, Ruff·Bandit·pip-audit·check/deploy·migration·Node syntax·diff PASS.
