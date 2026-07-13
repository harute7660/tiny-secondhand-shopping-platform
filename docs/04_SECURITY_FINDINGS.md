# 보안약점 발견·조치 대장

보안약점을 보고서 분량을 위해 의도적으로 만들지 않는다. 요구사항 검토, 위협 모델링, 코드리뷰, 자동 검사 또는 수동 테스트에서 실제로 발견된 문제만 기록한다. 수정 전 취약 코드는 최종 브랜치에 남기지 않고 diff, 테스트 실패·성공 결과, 필요한 경우 마스킹한 화면으로 증명한다.

## 상태와 위험도

- 상태: `Open`, `Fixing`, `Fixed`, `Accepted`, `Not Reproducible`
- 위험도: `Critical`, `High`, `Medium`, `Low`, `Informational`
- `Accepted`는 이유, 영향, 보완 통제, 제거 계획이 모두 있어야 한다.

## 발견 현황

| ID | 발견 | 위험도 | 상태 | 검증 결과 |
|---|---|:---:|:---:|---|
| SEC-001 | 신고 대상의 모델 검증 전 서버 바인딩 누락 | Medium | Fixed | 신고 회귀 테스트 통과 |
| SEC-002 | 홈 템플릿의 미정의 GET 변수로 500 발생 | Medium | Fixed | 홈·보안 헤더 테스트 통과 |
| SEC-003 | 운영 HSTS 하위 도메인·preload 정책 미적용 | Medium | Fixed | `check --deploy` 문제 0건 |
| SEC-004 | 설치 도구 `pip`의 알려진 취약점 6건 | Medium | Fixed | 26.1.2 갱신 후 pip-audit 0건 |
| SEC-005 | 모바일에서 로그아웃 버튼이 숨겨짐 | Low | Fixed | CSS 검토, 로그아웃 테스트 통과 |
| SEC-006 | 송금 화면의 지갑 context 누락으로 잔액 0 표시 | Low | Fixed | 잔액 context 테스트 통과 |
| SEC-007 | 폼 도움말·오류 ARIA 참조 불일치 | Low | Fixed | 템플릿 파싱·ARIA ID 대조 |
| SEC-008 | Admin 교차 모델 작업 권한·보호 계정 누락 | High | Fixed | 위조 POST·보호 계정 테스트 통과 |
| SEC-009 | 관리자 로그인 반복시도 제한 부재 | Medium | Fixed | Admin 로그인 제한 테스트 통과 |
| SEC-010 | 정지 계정의 활성 상태·상품 공개 우회 | Medium | Fixed | DB 불변식·공개 범위 테스트 통과 |
| SEC-011 | 가입·상품·메시지·신고 자원 상한 부족 | Medium | Fixed | quota/rate 테스트 통과 |
| SEC-012 | stale 상품 수정 TOCTOU·임의 상태 전이 | High | Fixed | stale update·상태 전이 테스트 통과 |
| SEC-013 | 익명 동적 HTML·상품 이미지 cache와 파일 생명주기 불일치 | Medium | Fixed | no-store·evidence-aware commit 삭제 테스트 통과 |
| SEC-014 | 전달 헤더의 신뢰 proxy 경계 불명확 | High | Fixed | trusted/untrusted proxy 테스트 통과 |
| SEC-015 | 사용자 ID 기반 신고·차단과 비공개 metadata 노출 | High | Fixed | 열거·비공개 placeholder 테스트 통과 |
| SEC-016 | 대화 목록 무제한·N+1 쿼리 | Medium | Fixed | pagination·annotation 테스트 통과 |
| SEC-017 | 게시된 송금·원장의 ORM 변경 가능성 | High | Fixed | instance·QuerySet 불변성 테스트 통과 |
| SEC-018 | 의존성 hash lock·지속 보안 검사 부재 | Medium | Fixed | 로컬 구성 검토, GitHub 실행 예정 |
| SEC-019 | `change_user`를 통한 권한 상승·비밀번호 탈취 | Critical | Fixed | 위조 POST·password URL 회귀 통과 |
| SEC-020 | 기존 세션이 Admin 로그인 성공 판정을 오염 | High | Fixed | staff/nonstaff 사전인증 회귀 통과 |
| SEC-021 | 로그인 제한의 동시성·열거·저장소·CPU DoS | High | Fixed | real/unknown oracle·30회 경계 회귀 통과 |
| SEC-022 | 고비용 Form·이미지 처리 뒤 rate limit 수행 | High | Fixed | sanitizer 선행 차단 회귀 통과 |
| SEC-023 | 신고 증거 일반 수정과 상품 증거 소실 | High | Fixed | 403·snapshot·SHA·파일보존 회귀 |
| SEC-024 | Admin 상품 업로드가 이미지 검증을 우회 | High | Fixed | Admin fake image·파일 수명주기 회귀 통과 |
| SEC-025 | 비공개 상품 대화 목록 metadata 잔존 | Medium | Fixed | 목록 placeholder 회귀 통과 |
| SEC-026 | 보호 계정 신고까지 차단해 내부자 증거 누락 | Medium | Fixed | staff/superuser 신고 회귀 통과 |
| SEC-027 | 개발·CI 의존성 파일과 hash 정책 불일치 | Medium | Fixed | dev lock 클린 hash 설치 통과 |
| SEC-028 | 사용자 행동·증거 Admin 변조와 과도한 purge/block 권한 | High | Fixed | read-only·전용 권한 회귀 통과 |
| SEC-029 | boolean 오타·짧은 운영 SECRET_KEY 허용 | High | Fixed | 격리 settings 7개 회귀 통과 |
| SEC-030 | 동일 대상을 동시에 중복 신고할 경쟁조건 | Medium | Fixed | 조건부 UNIQUE·reporter 잠금 검증 |
| SEC-031 | 상품 이미지 삭제 sentinel을 파일 객체로 오인해 500 발생 | Medium | Open | `image-clear=on`에서 재현, 수정·회귀 필요 |
| SEC-032 | 개발·발표 모드의 기술 오류 페이지 내부정보 노출 | Medium | Open | DEBUG True/False 오류 응답 대조, 배포·테스트 보강 필요 |

### SEC-001 - 신고 대상의 모델 검증 전 서버 바인딩 누락

- 발견 단계/방법: 신고 통합 테스트에서 정상 POST가 저장되지 않고 200 응답으로 돌아오는 실패를 추적했다.
- KISA/CWE 연결: 입력데이터 검증, 보안기능 결정의 부적절한 입력값, CWE-915.
- 원인과 위험: `ReportForm`은 대상 필드를 공개하지 않지만 `ModelForm.is_valid()` 내부의 모델 `clean()`보다 URL 문맥 대상 할당이 늦었다. 대상 필드를 클라이언트 폼에 추가해 우회하면 공격자가 다른 상품·사용자를 지정할 가능성이 있었다.
- 변경: URL에서 조회한 정확히 하나의 상품 또는 사용자를 `form.instance`에 먼저 바인딩한 후 검증했다. 폼 허용목록에서는 대상을 계속 제외하고 DB XOR 제약도 유지했다.
- 선택 이유: 정상 신고를 복구하면서도 신뢰경계를 클라이언트가 아닌 서버 세션·URL에 유지한다.
- 검증: `test_report_target_is_server_selected_and_duplicate_is_limited`, `test_report_requires_exactly_one_target_at_database_level` 통과.
- 잔여 위험: 중복·일일 제한의 다중 인스턴스 경쟁은 운영 DB와 공유 rate-limit 저장소에서 추가 보강한다.

### SEC-002 - 홈 템플릿의 미정의 GET 변수로 500 발생

- 발견 단계/방법: 전체 테스트가 홈 렌더링에서 `VariableDoesNotExist`로 실패해 확인했다.
- KISA/CWE 연결: 오류상황 대응 부재, CWE-703.
- 원인과 위험: 템플릿 `default` 필터가 존재하지 않을 수 있는 중첩 GET 변수를 직접 평가했다. 비회원 첫 화면에서도 서버 오류를 일으키는 가용성 문제였다.
- 변경: 검색어와 선택 필터를 뷰에서 길이·허용목록 검증한 명시적 context로만 전달하고 템플릿은 그 값만 사용한다.
- 검증: 홈 검색·SQLi 문자열·공개 보안 헤더 테스트와 전체 테스트 통과.
- 잔여 위험: 새 템플릿 변수 추가 시 빈 쿼리와 누락 context 렌더링 테스트를 함께 추가한다.

### SEC-003 - 운영 HSTS 정책 보강

- 발견 단계/방법: 운영 배포 설정 검토와 `manage.py check --deploy` 기준 대조.
- KISA/CWE 연결: 암호화되지 않은 중요정보, CWE-319.
- 원인과 위험: 1년 HSTS는 설정했으나 `includeSubDomains`와 `preload`가 고정 비활성화되어 하위 도메인까지 동일 정책을 강제하지 못했다.
- 변경: 운영 기본값에 1년 HSTS, 하위 도메인 포함, preload를 적용하고 `DJANGO_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_HSTS_PRELOAD` 환경변수로 단계적 운영 전환을 허용했다.
- 선택 이유: 안전한 운영 기본값을 제공하면서 모든 하위 도메인의 HTTPS 준비 상태에 따라 명시적으로 조정할 수 있다.
- 검증: 검증 전용 운영 환경값으로 `manage.py check --deploy` 실행 결과 문제 0건.
- 잔여 위험: 실제 preload 등록 전 모든 하위 도메인의 HTTPS와 인증서 갱신 절차를 운영자가 확인해야 한다.

### SEC-004 - `pip` 공급망 취약점 6건

- 발견 단계/방법: 전체 가상환경 대상 pip-audit.
- KISA/CWE 연결: 취약한 API 사용·무결성 검사 없는 코드 다운로드, CWE-1395.
- 원인과 위험: 번들 환경의 이전 `pip`가 알려진 취약점 6건의 영향 버전에 포함됐다. 애플리케이션 요청 경로는 아니지만 의존성 설치·빌드 경로의 공급망 자산이다.
- 변경: `pip`를 26.1.2로 갱신하고 동일 환경을 다시 검사했다.
- 검증: 최초 6건, 갱신 후 pip-audit 취약점 0건.
- 잔여 위험: 새 의존성 설치와 제출 직전에 검사를 다시 수행한다.

### SEC-005 - 모바일 로그아웃 경로 숨김

- 발견 단계/방법: 템플릿·반응형 CSS 접근성 통합 리뷰.
- KISA/CWE 연결: 세션 통제, CWE-613과 관련된 사용성 보완.
- 원인과 위험: 470px 이하 규칙이 POST 로그아웃 버튼을 `display:none`으로 만들었다. 서버 세션은 안전했지만 작은 화면 사용자가 공용 기기에서 종료 동작을 수행할 수 없었다.
- 변경: 숨김 규칙만 제거하고 POST 전용·CSRF 토큰·서버 세션 폐기는 유지했다.
- 검증: CSS 규칙 재검토, `test_logout_is_post_only` 및 전체 테스트 통과.
- 잔여 위험: 최종 브라우저 QA에서 320px 화면의 헤더 줄바꿈과 터치 영역을 확인한다.

### SEC-006 - 송금 화면 잔액 context 누락

- 발견 단계/방법: 템플릿과 view context 매핑 리뷰 후 회귀 테스트 추가.
- KISA/CWE 연결: 보안기능 결정의 부적절한 입력값·무결성, CWE-840.
- 원인과 위험: 송금 뷰가 폼만 전달해 템플릿 기본값 0이 표시됐다. 서버는 실제 원장으로 판단했으므로 초과 송금은 불가능했지만, 사용자에게 잘못된 보안 관련 상태를 제시했다.
- 변경: 인증 사용자 지갑을 `ensure_wallet()`로 조회해 폼과 함께 전달했다.
- 검증: `test_transfer_page_uses_authenticated_wallet_balance`에서 지갑 소유자와 100,000 잔액 확인.
- 잔여 위험: 표시용 캐시 잔액과 원장 합계 일치 테스트를 계속 유지한다.

### SEC-007 - 폼 ARIA 도움말·오류 참조 불일치

- 발견 단계/방법: Django 5.2가 렌더링한 위젯의 `aria-describedby`와 커스텀 템플릿 ID를 대조했다.
- KISA/CWE 연결: 직접적인 보안약점보다는 안전 기능을 사용할 수 있게 하는 접근성 품질 결함이다.
- 원인과 위험: 위젯은 `_helptext`, `_error`를 참조했지만 템플릿은 `_help`를 사용하고 오류 ID를 만들지 않았다. 보조기술 사용자가 비밀번호 조건과 검증 실패를 연결하기 어려웠다.
- 변경: 도움말 ID를 `_helptext`로 통일하고 모든 필드 오류를 하나의 `_error` 컨테이너에 배치했다.
- 검증: 전체 템플릿 파싱 성공, 렌더링 위젯과 대상 ID 일치 확인.
- 잔여 위험: 키보드 탐색·색 대비·스크린리더 브라우저 QA는 7월 13일 릴리스 점검에 포함한다.

### SEC-008 - Admin 교차 모델 권한과 보호 계정

- 이유·위험: 신고 변경 권한만 가진 staff가 신고 작업을 통해 상품 차단이나 사용자 정지를 수행하면 대상 모델 권한을 우회한다. 일괄 작업이 자기 자신·staff·superuser를 정지시키는 것도 관리 권한 복구를 방해한다.
- 변경: 작업 UI 노출뿐 아니라 action 함수 내부에서 신고 변경 권한과 전용 `market.block_listing`/`accounts.suspend_user`를 다시 검사한다. 자기 자신·staff·superuser는 정지 대상에서 제외하고, 비공개 상품 조회도 단순 `is_staff`가 아니라 `market.view_listing` 권한으로 제한했다.
- 테스트: `test_listing_block_action_requires_dedicated_block_permission`, forged Admin POST, `block_listing`·`suspend_user` 전용 권한 성공, `test_user_suspend_action_skips_self_staff_and_superusers`, staff view 권한 테스트 통과.
- 잔여 위험: 객체별 세분 권한은 제공하지 않는다. 운영 역할은 Django Group으로 최소 권한 분리하고 superuser 계정은 별도로 관리해야 한다.

### SEC-009 - 관리자 로그인 반복시도 제한

- 이유·위험: 일반 로그인만 제한하고 `/admin/login/`을 Django 기본 view에 직접 노출하면 고가치 관리자 계정에 대한 brute force 우회 경로가 남는다.
- 변경: Admin 로그인 앞에 계정 5회/15분, 네트워크 원시도 30회/15분의 HMAC 제한을 적용했다. 성공 시 해당 계정 상태만 지우고 네트워크 누적은 유지하며 실패·제한 이벤트는 원문 ID나 IP 대신 해시 prefix로 기록한다.
- 테스트: `test_admin_login_uses_account_and_network_throttling`, `test_successful_admin_login_clears_attempts` 통과.
- 잔여 위험: LocMem cache·SQLite 구성은 다중 인스턴스 전역 제한용이 아니다. 운영에서는 공유 cache, 중앙 감사 로그와 필요 시 MFA·외부 IdP를 추가한다.

### SEC-010 - 정지 계정 DB 불변식과 판매자 공개 범위

- 이유·위험: 모델 `save()`만으로 정지 사용자를 비활성화하면 QuerySet `update()`나 Admin 경로가 `is_suspended=True, is_active=True` 조합을 만들 수 있다. 기존 세션·상품이 공개되면 정지 효과가 불완전하다.
- 변경: 데이터 마이그레이션으로 기존 정지 계정을 비활성화하고 `is_suspended=False OR is_active=False` DB CHECK를 추가했다. 모델 clean/save도 같은 규칙을 강제하며, 정지·비활성 판매자의 상품은 공개 queryset·이미지·찜·새 대화에서 제외한다.
- 테스트: `test_clean_and_save_force_suspended_user_inactive`, `test_database_rejects_suspended_active_bulk_update`, `test_suspended_seller_products_are_not_public` 통과.
- 잔여 위험: 이미 생성된 대화 기록은 분쟁 증적을 위해 참여자에게 남기되 상품 metadata는 placeholder로 감춘다. 개인정보 보존 기간은 운영 정책이 필요하다.

### SEC-011 - 가입·콘텐츠 자원 상한

- 이유·위험: 회원가입과 상품·메시지·신고 생성이 무제한이면 계정·DB·파일 저장소를 고갈시키는 애플리케이션 계층 DoS가 가능하다.
- 변경: 네트워크당 가입 5회/시간, 사용자당 상품 10회/시간, 활성 50개·전체 이력 500개, 메시지 20회/분·500회/일, 신고 10회/일 상한을 적용했다. 상품 quota는 트랜잭션과 계정 행 잠금 안에서 다시 계산한다.
- 테스트: 가입 rate, 상품 quota, 상품 rate의 애플리케이션 경계 원자성, 메시지·신고 제한 관련 회귀 테스트와 전체 120개 테스트 통과.
- 잔여 위험: SQLite의 행 잠금과 LocMem cache는 단일 프로세스 교육환경 기준이다. 운영에서는 PostgreSQL·Redis와 프록시/인프라 rate limit이 필요하다.

### SEC-012 - stale 상품 수정 TOCTOU와 판매 상태 전이

- 이유·위험: 사용자가 편집 폼을 연 뒤 관리자가 상품을 차단했는데 오래된 POST가 저장되면 차단 상품을 다시 노출하거나 moderation 내용을 덮어쓸 수 있다. 임의 status POST도 거래 표현을 위조한다.
- 변경: 수정·삭제 시 트랜잭션 안에서 `select_for_update()`로 현재 행을 다시 읽고 소유자·현재 상태를 검증한다. 상태 변경은 POST 전용이며 명시된 판매중·예약중·판매완료 전이만 허용한다.
- 테스트: `test_stale_update_cannot_reverse_admin_block`, `test_seller_status_transitions_are_server_validated`, 판매완료 상품 새 대화 거부 테스트 통과.
- 잔여 위험: SQLite의 `select_for_update()`는 실질적 행 잠금을 제공하지 않는다. 운영 경쟁조건 보장은 PostgreSQL 기준으로 재부하 테스트한다.

### SEC-013 - 동적 응답·상품 이미지 cache와 파일 생명주기

- 이유·위험: 익명 공개 HTML이나 안정된 이미지 URL을 브라우저·공유 cache가 보관하면 차단·삭제 후에도 제목·가격·이미지가 재노출될 수 있다. DB rollback·교체·soft delete 뒤 불필요한 파일이 남으면 저장소·개인정보 보존 위험도 생긴다.
- 변경: 정적 자산을 제외한 모든 동적 응답과 이미지 응답을 `private, no-store`로 고정했다. 교체·삭제는 DB commit 후 이전 파일을 evidence-aware 방식으로 제거하고 Report snapshot이 참조한 파일은 private storage에 보존한다. 트랜잭션 실패로 새 파일만 생성되면 예외 경로에서 정리하고 soft delete 시 현재 Listing 이미지 참조를 비운다.
- 테스트: 익명 홈 HTML·이미지 응답 header, 교체 성공/DB 실패, soft delete commit 뒤 일반 파일 제거와 신고 증거 보존 테스트 통과.
- 잔여 위험: 저장소 자체 버전·backup·CDN 정책은 애플리케이션 header만으로 삭제되지 않는다. 운영 보존 정책과 주기적 고아 파일 점검이 필요하다.

### SEC-014 - trusted proxy 경계

- 이유·위험: 모든 요청의 `X-Forwarded-For`와 `X-Forwarded-Proto`를 신뢰하면 공격자가 네트워크 제한 키를 바꾸거나 HTTP 요청을 HTTPS로 오판시킬 수 있다.
- 변경: 직접 연결 peer가 `DJANGO_TRUSTED_PROXY_IPS`에 있을 때만 XFF의 첫 주소를 사용한다. 별도 middleware가 비신뢰 peer의 XFP를 제거하며, HTTPS proxy 모드는 신뢰 IP가 없으면 설정 오류로 시작을 거부한다.
- 테스트: `test_untrusted_peer_cannot_spoof_forwarded_network_address`, `test_trusted_proxy_can_supply_valid_client_address`, `test_forwarded_https_header_is_trusted_only_from_configured_proxy` 통과.
- 잔여 위험: 실제 proxy가 기존 전달 헤더를 삭제하고 신뢰 가능한 값으로 덮어써야 한다. 여러 proxy hop 정책은 배포 토폴로지별로 재설계한다.

### SEC-015 - 대화 기반 신고·차단과 비공개 placeholder

- 이유·위험: 순차 사용자 ID를 URL에 넣어 누구나 신고·차단할 수 있으면 계정 열거와 무관한 사용자 괴롭힘이 가능하다. 차단·삭제 상품의 UUID를 기존 대화에서 재사용하면 제목·가격·이미지를 다시 볼 수도 있다.
- 변경: 사용자 신고는 참여 대화 UUID에서 상대방을 서버가 파생하고, 차단도 두 사용자 사이 실제 대화가 있어야 한다. 상품 신고는 현재 공개 상품만 허용한다. 비공개 상품은 대화 목록·상세에서 링크와 metadata 대신 “비공개 상품”을 표시한다.
- 테스트: 대화 상대 신고, 순차 사용자 ID 신고·차단 거부, 비공개 상품 신고 재개방 거부, `test_blocked_listing_metadata_is_hidden_from_buyer_conversation` 통과.
- 잔여 위험: 악성 사용자가 먼저 정상 대화를 만들면 신고·차단 대상은 될 수 있다. 이는 실제 상호작용 이후 보호 기능을 제공하기 위한 허용된 범위다.

### SEC-016 - 대화 목록 pagination과 N+1 제거

- 이유·위험: 모든 대화를 한 번에 렌더링하고 각 행에서 마지막 메시지를 별도 조회하면 대화 수만큼 쿼리·HTML 비용이 증가해 응답 지연과 자원 고갈을 일으킨다.
- 변경: 대화 목록을 30개씩 페이지네이션하고 마지막 메시지 본문·발신자를 상관 Subquery로 annotation해 템플릿의 행별 조회를 제거했다.
- 테스트: `test_conversation_list_uses_annotated_last_message`와 페이지 context 검토, 전체 테스트 통과.
- 잔여 위험: SQLite와 PostgreSQL의 query plan 차이를 운영 데이터 규모에서 측정하고 필요한 복합 index를 조정한다.

### SEC-017 - append-only 송금·원장

- 이유·위험: Admin read-only만으로는 내부 코드나 shell에서 기존 `Transfer`·`LedgerEntry`를 update/delete해 감사 이력을 변조하는 것을 막지 못한다.
- 변경: 공통 불변 모델·QuerySet으로 저장 후 instance save/delete, QuerySet update/delete/bulk_update와 conflict update를 거부했다. 정상 최초 INSERT·bulk create만 허용하고 정정은 별도 반전 거래로 표현한다.
- 테스트: Transfer·LedgerEntry의 instance와 QuerySet 변경·삭제 거부 4개 테스트, 모든 게시 송금의 원장 정확히 2건·합계 0 테스트 통과.
- 잔여 위험: DB 관리자 직접 SQL은 애플리케이션 방어 범위 밖이다. 운영 DB 권한 분리, append-only 감사 저장소와 backup 검증이 필요하다.

### SEC-018 - hash lock·CI·CodeQL

- 이유·위험: 버전만 고정하면 패키지 저장소의 아티팩트 치환을 설치 시점에 탐지하지 못하고, 로컬 검사를 수동으로만 실행하면 보안 회귀가 main에 들어갈 수 있다.
- 변경: `pip-compile --generate-hashes`로 런타임 `requirements.lock`과 설치 도구까지 포함한 `requirements-dev.lock`을 만들고 CI는 dev lock을 `--require-hashes`로 설치한다. GitHub Actions는 최소 권한·timeout·concurrency를 사용해 migration, deploy check, Ruff, Bandit, 85% coverage gate, lock 대상 pip-audit를 실행한다. 별도 CodeQL security-extended와 주간 Dependabot을 추가하고 Actions를 commit SHA로 고정했다.
- 테스트: lock·workflow YAML과 pin을 로컬 검토하고 전체 회귀·coverage·Ruff·Bandit을 재실행했다. 빈 대상 디렉터리에는 `requirements-dev.lock`을 `--require-hashes`로 설치했다.
- 잔여 위험: GitHub 저장소가 아직 공개·push되지 않았으므로 Actions·CodeQL 실행 성공은 확인하지 않았다. 첫 push 뒤 결과 링크와 SHA를 릴리스 증적으로 남긴다.

### SEC-019 - 사용자 관리 권한 상승과 자격증명 탈취

- 발견 단계/방법: 최종 Django Admin 권한 경계 코드리뷰와 실제 위조 change/password POST.
- 원인·위험: `accounts.change_user`를 가진 비-superuser가 특권·정지 필드를 보내거나 전용 password URL에서 일반 사용자의 비밀번호를 재설정하면 staff/superuser 상승 또는 대화·지갑 세션 탈취가 가능했다.
- 변경·이유: 특권·계정 상태 필드를 비-superuser에게 readonly로 만들고 staff/superuser 대상 변경을 거부했다. 정지는 `accounts.suspend_user`로 분리하고 password reset은 복구 절차를 수행할 superuser에게만 허용했다.
- 검증: 실제 forged change POST, 보호 계정 변경, 비-superuser password reset 403·hash 불변, superuser 정상 reset·새 비밀번호 로그인 회귀.
- 잔여 위험: superuser 자격증명 자체는 고위험이다. 운영에서는 MFA·재인증·변경 통지·2인 승인을 추가한다.

### SEC-020 - 사전 인증 Admin 세션 혼동

- 발견 단계/방법: 로그인 상태별 `/admin/login/` POST 흐름 코드리뷰.
- 원인·위험: 이미 인증된 staff 세션이 제출 계정과 무관하게 성공으로 해석되면 공격 대상의 제한 기록을 지울 수 있었다.
- 변경·이유: 인증된 staff는 Admin index로만 이동하고 인증된 nonstaff는 403으로 거부한다. 새 성공은 제출한 정규화 사용자명, 실제 인증 사용자, staff 상태가 모두 일치할 때만 인정한다.
- 검증: 로그인된 staff의 위조 POST 뒤 타 계정 잠금 불변, nonstaff 403 회귀.
- 잔여 위험: 관리자 세션 탈취는 별도 MFA·관리 네트워크 제한이 필요하다.

### SEC-021 - 로그인 제한의 동시성·열거·자원 고갈

- 발견 단계/방법: PBKDF2 실행 위치, SQLite transaction, cache/DB 순서, 실제·미존재 계정 경로를 적대적으로 재검토했다.
- 원인·위험: 해시 중 DB lock, 성공 시 네트워크 counter 초기화, 미존재 이름별 무제한 행, 과대 credential, 실제/미존재 분기 차이는 쓰기 lock·CPU/DB DoS와 계정 존재 oracle을 만들 수 있었다.
- 변경·이유: 해시 전에 짧은 원자 예약만 수행하고 계정 5회·네트워크 원시도 30회를 분리했다. 성공은 계정만 초기화하고, 존재 여부와 무관하게 같은 HMAC/DB 경로를 사용한다. username 150·password 256 사전 상한, 30분 만료 정리와 `window_started` index를 추가했다.
- 검증: 30회 real/unknown 후보 공격 후 자기 정상 로그인 결과 동일, 쿼리 연산 경로 동일, IP당 신규 ACCOUNT 행 30개 경계, 만료 정리, oversized credential 회귀.
- 잔여 위험: 타인이 특정 계정을 5회 실패시켜 일시 잠그는 표적 DoS는 brute-force 방어의 trade-off다. 운영 공유 Redis·인프라 rate limit·MFA·위험기반 지연이 필요하며 inline 정리는 대규모 DB에서 배치 작업으로 분리한다.

### SEC-022 - 제한 이전의 고비용 검증

- 발견 단계/방법: 상품·메시지·신고·송금 POST의 호출 순서 리뷰.
- 원인·위험: Form 검증·이미지 디코딩 뒤 제한을 소비하면 공격자가 제한에 잡히기 전에 CPU·메모리 비용을 반복시킬 수 있었다.
- 변경·이유: 원시 길이·UUID 형식·원자 rate gate를 Form과 sanitizer 앞에 두고 유효하지 않은 요청도 시도량에 포함했다.
- 검증: 제한이 소진된 상품 등록·수정에서 image sanitizer 미호출과 429, 잘못된 신고 UUID 404 회귀.
- 잔여 위험: 웹서버가 요청 body를 받는 비용은 애플리케이션 이전 계층의 body/rate limit으로 보완한다.

### SEC-023 - 신고 증거 불변성과 상품 증거 보존

- 발견 단계/방법: Report Admin change POST와 신고 직후 판매자 수정·이미지 삭제 시나리오.
- 원인·위험: 신고 내용·처리 metadata를 일반 Admin 저장으로 바꾸거나 판매자가 원 상품과 이미지를 교체·삭제하면 관리자가 신고 시점 증거를 확인하기 어려웠다.
- 변경·이유: Report는 모든 증거 필드를 readonly, add/delete 금지, direct save 403으로 만들었다. 신고 transaction에서 상품 행을 잠그고 제목·설명·가격·분류·상태·이미지 저장명과 SHA-256을 snapshot한다. 증거 저장명에는 참조 조회 index를 두고 이전 이미지는 공개 route 없이 private storage에 보존한다. 전용 Admin endpoint는 `view_report`를 재검사하고 파일 SHA-256을 매 요청 상수시간 비교하며, 정상 응답에 `private, no-store`·`nosniff`를 설정하고 actor/report 열람 로그를 남긴다.
- 검증: forged report POST에서 `updated_at` 포함 전체 불변, snapshot/hash 일치, seller/Admin 교체·삭제 후 증거 파일 보존과 공개 접근 불가, 권한 있는 열람·무권한/변조 거부·응답 header 회귀.
- 잔여 위험: 증거 이미지는 명시적 보존기간과 audited purge가 필요하다. 운영 reverse proxy가 `MEDIA_ROOT`나 `/_private-media/`를 정적 alias로 직접 서빙하면 보호를 우회하므로 절대 노출하지 않고 Django의 권한검사 이미지 view만 사용해야 하며, SQLite 경쟁 의미는 운영 PostgreSQL에서 다시 검증한다.

### SEC-024 - Admin 이미지 검증 우회

- 발견 단계/방법: 공개 등록 Form과 Django Admin ModelForm 비교.
- 원인·위험: Admin 기본 업로드가 공개 경로의 디코딩·형식·크기·재인코딩을 우회하고 상태·차단 metadata까지 직접 덮을 수 있었다. purge 뒤 오래된 Listing 객체를 저장하면 삭제 레코드가 다시 생성될 위험도 있었다.
- 변경·이유: `ListingAdminForm`이 동일 `ListingForm` sanitizer를 재사용하고 add를 막았다. seller·상태·차단 필드는 readonly이며 이미지 교체·삭제는 commit 후 공용 evidence-aware 정리를 사용한다. 변경 직전 현재 Listing 행을 잠가 다시 읽고 존재하지 않으면 403으로 거부한다.
- 검증: 가짜 이미지 거부, 교체·단일·일괄 삭제 파일 수명주기, purge 뒤 stale Admin 저장의 레코드 부활 거부 회귀.
- 잔여 위험: `change_listing`은 본문을 편집할 수 있는 고위험 역할로 제한 배정한다.

### SEC-025 - 비공개 상품 대화 metadata

- 발견 단계/방법: 차단·삭제 상품이 연결된 대화 목록/상세 템플릿 비교.
- 원인·위험: 제목·가격을 숨겨도 등록시각·상태·이미지 경로가 남으면 활동을 추론할 수 있었다.
- 변경·이유: `listing_visible`일 때만 모든 상품 metadata를 렌더링하고 그 외에는 고정 placeholder만 표시한다.
- 검증: BLOCKED/DELETED 두 상태의 목록·상세 metadata 부재 회귀.
- 잔여 위험: 대화 본문 자체의 개인정보 보존기간은 별도 정책이 필요하다.

### SEC-026 - 보호 계정 신고 증거 누락

- 발견 단계/방법: staff/superuser 상대 대화 신고 흐름 리뷰.
- 원인·위험: 보호 계정을 자동 정지하지 않는 정책을 신고 제출 차단으로 구현하면 내부자 악용 증거까지 수집하지 못한다.
- 변경·이유: 대화 상대가 staff/superuser여도 신고는 OPEN으로 접수하되 bulk suspension만 보호 계정을 건너뛴다.
- 검증: staff·superuser 상대 신고 접수, 계정 활성·신고 OPEN 유지 회귀.
- 잔여 위험: 보호 계정 사건은 더 높은 권한의 별도 조사 절차가 필요하다.

### SEC-027 - 개발/CI 공급망 경로 불일치

- 발견 단계/방법: 삭제된 dev requirements 참조, CI 설치 명령, lock 생성 경로 대조.
- 원인·위험: 개발과 CI가 서로 다른 파일 또는 hash 없는 선행 pip upgrade를 사용하면 검사 도구와 설치 artifact가 재현되지 않는다.
- 변경·이유: `requirements-dev.in`→`requirements-dev.lock`으로 일원화하고 pip/setuptools까지 `--allow-unsafe`로 hash 고정했다. CI의 hash 없는 선행 upgrade를 제거했다.
- 검증: 빈 대상 디렉터리에 `--require-hashes -r requirements-dev.lock` 전체 설치 성공.
- 잔여 위험: lock 갱신은 신뢰된 환경에서 diff·pip-audit·CI를 함께 검토한다.

### SEC-028 - Admin 증거/사용자 행동 변조와 과도한 권한

- 발견 단계/방법: 등록된 모든 ModelAdmin의 add/change/delete permission 전수검토.
- 원인·위험: Message·Conversation·Favorite·UserBlock·LoginAttempt를 generic Admin으로 바꾸면 분쟁 증거·사용자 의사·보안 제한 기록을 위조할 수 있다. `change_listing`/`delete_listing`만으로 차단·영구삭제까지 허용하는 것도 과도했다.
- 변경·이유: 서버 작성·사용자 행동 기록은 전 필드 read-only와 add/change/delete 금지를 적용했다. 신고 상품 차단은 `block_listing`, 영구삭제는 `delete_listing`+`purge_listing` 전용 권한으로 분리했다. 신고 처리·차단·정지 action은 선택 Report 행을 `select_for_update()`로 잠그고 `OPEN`을 다시 검사한다.
- 검증: forged Message/UserBlock/LoginAttempt POST 불변, 전용 권한 조합별 action·purge 허용/거부, Report action 행 잠금 회귀.
- 잔여 위험: 영구삭제는 법적 요청·불법 콘텐츠 등 문서화된 audited 절차에서만 사용한다.

### SEC-029 - 운영 환경변수 fail-closed 검증 부족

- 발견 단계/방법: production startup negative configuration 리뷰.
- 원인·위험: boolean 오타가 조용히 false가 되고 한 글자 SECRET_KEY도 통과하면 운영자가 보안 설정을 했다고 오인할 수 있었다.
- 변경·이유: boolean은 명시된 true/false 토큰 외 모두 설정 오류로 거부하고, production SECRET_KEY의 50자 미만·낮은 문자 다양성·알려진 비안전 prefix와 SSL redirect false도 시작 단계에서 거부한다.
- 검증: 격리 settings 모듈의 허용값·오타·짧은 key·낮은 엔트로피·비안전 prefix·SSL false·정상 deploy check 회귀.
- 잔여 위험: 길이는 엔트로피의 완전한 증명이 아니므로 운영 비밀 저장소에서 CSPRNG 키를 생성·회전한다.

### SEC-030 - 동시 중복 신고

- 발견 단계/방법: application `exists()` 후 `save()` 사이 경쟁조건 검토.
- 원인·위험: 같은 사용자의 병렬 요청이 모두 사전검사를 통과하면 동일 대상 OPEN 신고가 중복 저장될 수 있었다.
- 변경·이유: reporter 행 잠금과 함께 `(reporter, listing)` 및 `(reporter, target_user)`의 OPEN 상태 조건부 UNIQUE 제약을 추가하고 충돌은 공통 중복 안내로 처리한다.
- 검증: 모델 제약·중복 웹 요청 회귀와 migration drift 검사.
- 잔여 위험: 일일 총량 제한은 운영 DB 격리 수준과 공유 cache에서 부하 검증한다.

### SEC-031 - 상품 이미지 삭제 sentinel 처리 오류

- 발견 단계/방법: 사용자가 기존 이미지가 있는 상품 수정 화면에서 파일을 변경·삭제하던 중 `AttributeError: 'bool' object has no attribute 'name'` 화면을 제보해 실제 `image-clear=on` POST와 코드 경로를 재현했다.
- KISA/CWE 연결: 오류상황 대응 부재, 입력데이터 검증 및 표현 변환, CWE-703.
- 원인·위험: Django `ClearableFileInput`은 기존 파일 삭제를 `False` sentinel로 표현한다. `ListingForm` 검증은 정상이나 `listing_update`가 ModelForm의 `FileField.save_form_data()` 변환을 우회하고 `setattr(locked, "image", False)`를 수행해 FileField 저장 시 `.name` 접근에서 500이 발생한다. 상품 수정 가용성을 깨고 DEBUG 환경에서는 SEC-032의 정보노출로 이어진다.
- 현재 보완: 저장 transaction이 rollback되고 commit 후 삭제 callback도 실행되지 않아 재현 시 기존 DB 이미지와 파일은 손실되지 않았다.
- 수정 계획: 각 모델 필드의 `save_form_data()`를 통해 정규화하거나 image의 `False`를 빈 파일명으로 변환한다. 기존 이미지 삭제·미변경·교체·삭제와 업로드 동시 선택·잘못된 이미지·신고 증거 보존 회귀를 추가한다.
- 상태: **Open**. 수정과 전체 회귀 전에는 제출 완료로 표시하지 않는다.

### SEC-032 - DEBUG 기술 오류 화면의 내부정보 노출

- 발견 단계/방법: SEC-031의 브라우저 화면과 동적 오류 응답을 `DEBUG=True`와 `DEBUG=False`에서 대조했다.
- KISA/CWE 연결: 오류 메시지를 통한 정보노출, 오류상황 대응 부재, CWE-209.
- 원인·위험: 기본 개발 실행은 `DEBUG=True`여서 처리되지 않은 400·404·500 예외가 Django 기술 화면을 사용한다. 500에는 예외명, traceback, 절대경로, 소스·로컬 변수, Python/Django 버전, 요청·설정 정보가 포함될 수 있고 로그인·가입 처리 중 예외라면 POST 비밀값 노출 위험도 있다.
- 현재 보완: 서버는 `127.0.0.1`에만 bind했고 production에서 `DEBUG=True`이면 시작을 거부한다. `DEBUG=False` 동적 검증에서는 커스텀 400·403·404·500·CSRF 화면에 진단 문자열이 없고 보안 헤더가 유지됐다.
- 수정 계획: 발표·배포용 DEBUG false 절차를 명시하고 400·403·404·500·CSRF 템플릿·진단정보 비노출·CSP·no-store 자동 테스트를 추가한다. 500은 공통 base·세션·URL reverse에 의존하지 않는 standalone 응답으로 보강하고 plain 400·429·기본 405 UI도 검토한다.
- 상태: **Open**. 개발 기술 화면을 인터넷 또는 발표 환경에 노출하지 않는다.

## 2026-07-12 공통 자동검사 스냅샷

- Django tests: 120개 통과 - `image-clear`·오류 본문 비노출 분기 미포함
- Coverage: 120-test instrumentation 3,169 statements / 223 miss / 93%
- Ruff: 오류 0건
- Bandit: 이슈 0건
- pip-audit: 조치 후 취약점 0건
- 금지 API·템플릿 패턴 검색: 일치 0건
- CI·CodeQL: 구성 완료, GitHub 최초 실행 결과는 아직 미확인
- 알려진 테스트 공백: 기존 120개는 `image-clear`와 DEBUG false 오류 본문 비노출을 포함하지 않아 SEC-031·032를 발견하지 못했다.
