# 보안약점 발견·조치 대장

보안약점을 보고서 분량을 위해 의도적으로 만들지 않는다. 요구사항 검토, 위협 모델링, 코드리뷰, 자동 검사 또는 수동 테스트에서 실제로 발견된 문제만 기록한다. 수정 전 취약 코드는 최종 브랜치에 남기지 않고 diff, 테스트 실패·성공 결과, 필요한 경우 마스킹한 화면으로 증명한다.

## 상태와 위험도

- 상태: `Open`, `Fixing`, `Fixed`, `Mitigated`, `Accepted`, `Not Reproducible`
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
| SEC-031 | 상품 이미지 삭제 sentinel을 파일 객체로 오인해 500 발생 | Medium | Fixed | `FileField.save_form_data()` 정규화와 삭제·유지·교체·실패 회귀 통과 |
| SEC-032 | 개발·발표 모드의 기술 오류 페이지 내부정보 노출 | Medium | Fixed | SafeExceptionMiddleware·standalone fallback의 DEBUG/운영 비노출 회귀 통과 |
| SEC-033 | 상품 수정 위젯의 내부 이미지 저장명·무효 private media URL 노출 | Low | Fixed | 보호 route 렌더링·저장명/`MEDIA_URL` 비노출 회귀 통과 |
| SEC-034 | 판매자의 단독 `SOLD` 전환을 거래·후기 권한으로 오인 | High | Fixed | 대화에 묶인 `Trade` 쌍방 확인·legacy SOLD 후기 거부 |
| SEC-035 | 완료 상품 직접 수정·삭제·재판매와 사후 차단을 이용한 후기 억압 | High | Fixed | 모든 mutation 재인가·완료 상태 보호·사후 차단 독립 확인 |
| SEC-036 | 후기의 저장형 XSS·연락처 노출·선공개 보복 위험 | Medium | Mitigated | 입력 정규화·PII 패턴 거부·autoescape·쌍방 blind 공개 |
| SEC-037 | 알림 UUID IDOR와 비공개 상품 제목·가격·이벤트 노출 | High | Fixed | 수신자 scope·현재 공개성 재검사·일반 비공개 카드 |
| SEC-038 | 알림 fan-out의 소급 구독·중복·rollback 유령·자원고갈 | Medium | Mitigated | 구조화 이벤트·시각 경계·멱등 UNIQUE·`on_commit`·batch/quota |
| SEC-039 | 다중 이미지의 전체 개수·합계 용량 누락과 stale 삭제 필드 | Medium | Fixed | sanitizer 전 전역 제한·잠근 자식 재검사·대표 승격 |
| SEC-040 | 추가 사진 child IDOR·내부 저장명·rollback orphan | High | Mitigated | 부모-자식 동시 scope·보호 응답·실패 시 신규 파일 정리 |
| SEC-041 | 위조 하자 코드와 신고 다중 증거·관리자 열람 경계 누락 | High | Mitigated | 허용목록·전체 snapshot·report-scoped 무결성 검증 route |
| SEC-042 | `PENDING` 후기가 판매자 공개 평균에 조기 반영 | Medium | Fixed | `PUBLIC` 후기만 목록·개수·평균에 포함 |
| SEC-043 | `/` 구분 전화번호가 후기 개인정보 패턴을 우회 | Medium | Mitigated | 숫자 구분자 허용목록에 slash 추가·회귀 |
| SEC-044 | 오래 열린 Listing Admin 폼이 새 차단 상태를 덮어씀 | High | Fixed | 잠근 최신 행과 보호 필드 비교·허용 필드만 복사 |
| SEC-045 | multipart 전체 body 제한이 view/form 파싱 뒤에만 적용 | Medium | Mitigated | CSRF 전 21MiB 선차단·실제 chunk 누적 handler·안전 400 |
| SEC-046 | 조건부 하자 입력의 stale·모순 상태와 불명확한 오류·제출 피드백 | Low | Fixed | 조건부 활성화·초기화, 서버 독립 검증·정규화, 오류 요약·제출 잠금 |
| SEC-047 | 두 탭 상품 수정의 lost update와 상품 전체 거래·현재 대화 CTA 불일치 | Medium | Mitigated | hidden revision+잠근 `updated_at` 409, 다른 거래 CTA·상대 신원 비공개, 현재 대화 닫힘 기록 |

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
- 검증 보강: 320×800 실제 viewport에서 header의 내부 nav scroll, 업로드·로그아웃 44px target과 문서 가로 overflow 0을 확인했다.
- 잔여 위험: 실제 모바일 기기·200% 확대·키보드·스크린리더는 제출 전 사용자가 확인한다.

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
- 수정 전 보완: 저장 transaction이 rollback되고 commit 후 삭제 callback도 실행되지 않아 재현 시 기존 DB 이미지와 파일은 손실되지 않았다.
- 변경·선택 이유: 잠근 최신 `Listing` 행에 text field는 허용목록으로 복사하되 이미지 값은 `Listing._meta.get_field("image").save_form_data(locked, cleaned_image)`에 전달한다. Django가 정의한 `False`→빈 파일명 정규화를 그대로 사용하므로 framework sentinel 의미를 중복 구현하지 않고, boolean을 FileField descriptor에 직접 대입하지 않는다. transaction·commit callback 기반의 기존 파일 생명주기는 유지했다.
- 검증: `test_update_without_image_input_keeps_existing_image`, `test_update_clear_image_uses_filefield_normalization_and_removes_file`, `test_update_replaces_existing_image_and_removes_superseded_file`, `test_update_rejects_clear_and_upload_contradiction_without_changing_image`, `test_update_rejects_invalid_image_without_changing_existing_image`, 신고 snapshot 증거 보존 테스트를 포함한 표적 회귀에 통과했다. 실제 브라우저에서도 이미지가 있는 임시 상품에서 `비우기`를 선택해 저장한 뒤 상세 placeholder, DB 빈 값, 기존 파일 삭제, traceback 0건을 확인하고 QA 데이터를 제거했다.
- 상태: **Fixed**. 해당 수정 직후인 2026-07-13 관련 87개 표적 테스트와 당시 전체 168개가 통과했고 coverage는 94%였다. 후속 첨부 widget·확장 기능 시점의 통합 기준선과 SEC-042~047 표적 결과는 아래 품질 게이트에 구분해 기록했다.

### SEC-032 - DEBUG 기술 오류 화면의 내부정보 노출

- 발견 단계/방법: SEC-031의 브라우저 화면과 동적 오류 응답을 `DEBUG=True`와 `DEBUG=False`에서 대조했다.
- KISA/CWE 연결: 오류 메시지를 통한 정보노출, 오류상황 대응 부재, CWE-209.
- 원인·위험: 기본 개발 실행은 `DEBUG=True`여서 처리되지 않은 400·404·500 예외가 Django 기술 화면을 사용한다. 500에는 예외명, traceback, 절대경로, 소스·로컬 변수, Python/Django 버전, 요청·설정 정보가 포함될 수 있고 로그인·가입 처리 중 예외라면 POST 비밀값 노출 위험도 있다.
- 기존 보완: 서버는 `127.0.0.1`에만 bind했고 production에서 `DEBUG=True`이면 시작을 거부했다. 그러나 로컬 발표·화면 공유 중 DEBUG 실수까지 막지는 못했다.
- 변경·선택 이유: `SafeExceptionMiddleware`를 모든 환경의 middleware chain에 추가해 처리되지 않은 예외를 일반 500으로, `SuspiciousOperation`·`PermissionDenied`·`Http404`를 각각 일반 400·403·404로 보낸다. DEBUG의 resolver 404도 URL pattern을 나열하지 않는다. exception 객체·요청 본문·경로는 응답과 로그에 보간하지 않고 `unhandled_request_exception` 같은 고정 event만 남긴다. 정상 validation 400, method 405, rate-limit 429와 resolved view의 JSON 404는 의미를 보존한다.
- 독립 fallback: 공통 base·context processor·static lookup·URL reverse를 사용하는 오류 template조차 실패할 수 있으므로 `_standalone_error_response()`는 요청·예외 데이터 없이 코드 상수의 최소 HTML만 반환한다. 이 응답에도 SecurityHeadersMiddleware가 CSP, `nosniff`, `DENY`, `private, no-store`, `Pragma: no-cache`를 적용한다.
- 검증: DEBUG True의 처리되지 않은 POST 예외에서 제출 비밀번호·예외명·traceback·절대경로·버전·설정이 응답과 로그에 없음을 확인했다. template render 실패 fallback, expected 400/403/404 status, unmatched URL pattern 비노출, resolved JSON 404 보존, DEBUG False 400/403/404/500/CSRF 비노출·보안 헤더, 정상 400/405/429 보존 테스트가 통과했다.
- 상태: **Fixed**. `DebugSafeExceptionTests`·`ProductionErrorResponseTests`를 포함한 87개 표적 테스트가 53.390초에 통과했다. 운영에서는 심층 방어와 별개로 `DJANGO_DEBUG=false`를 계속 강제하며, 외부 reverse proxy의 자체 오류 페이지도 배포 시 점검한다.

### SEC-033 - 상품 수정 위젯의 내부 저장명과 무효 private media URL 노출

- 발견 단계/방법: 이미지 첨부 UI를 모노크롬 디자인과 대조하는 코드리뷰에서 기존 이미지가 있는 상품 수정 Form의 실제 렌더링을 확인했다.
- KISA/CWE 연결: 시스템 정보 노출 최소화, 안전한 오류·인터페이스 설계, CWE-200.
- 원인·위험: Django 기본 `ClearableFileInput`은 현재 `FieldFile`의 문자열 값과 `.url`을 링크로 렌더링한다. private storage를 쓰는 현재 구성에서는 인증된 소유자의 수정 화면에 내부 UUID 저장명이 나타나고 `/_private-media/...` 무효 링크가 만들어졌다. 공개 열람이나 직접 파일 다운로드는 아니어서 위험도는 Low지만, 저장소 구조를 불필요하게 노출하고 reverse proxy가 private media를 잘못 alias할 때 접근통제 우회로 이어질 수 있으며 사용자에게 깨진 링크를 제공했다.
- 변경·선택 이유: 전용 `ProtectedListingImageInput`과 widget template을 추가했다. 위젯은 Listing 객체에서 UUID를 얻어 소유자·상품 공개 범위를 다시 검사하는 기존 `market:listing_image` route만 `reverse()`하고, 내부 저장명 대신 “보호된 이미지가 등록되어 있어요.”라는 일반 안내와 보호된 미리보기·삭제 checkbox를 표시한다. 새 파일 입력의 `accept`·도움말은 사용성 보조로만 두고 실제 형식·크기·픽셀·재인코딩 검증은 서버 sanitizer를 그대로 신뢰 경계로 유지했다.
- 검증: `test_existing_image_widget_uses_guarded_url_without_storage_name`에서 보호된 `listing_image` URL과 삭제 label을 확인하고 내부 저장명 및 `settings.MEDIA_URL` 부재를 검증했다. `test_image_upload_has_scoped_accessible_presentation`은 파일 입력의 허용 MIME·도움말·첨부 영역 scope를 확인했고, `ListingSecurityTests` 26개와 전체 회귀가 통과했다.
- 잔여 위험: 보호 route도 권한검사와 `private, no-store`를 계속 유지해야 하며 reverse proxy는 `MEDIA_ROOT`와 `/_private-media/`를 직접 서빙하면 안 된다. 브라우저 `accept`는 보안 검증이 아니므로 서버 sanitizer를 제거하거나 완화하지 않는다.
- 상태: **Fixed**. 내부 저장명·직접 private media URL을 사용자 HTML에 렌더링하지 않고 보호된 application route만 사용한다.

### SEC-034 - 단독 `SOLD` 상태를 거래·후기 권한으로 오인

- 발견 단계/방법: 거래 완료 사용자만 후기 작성 기능을 설계하며 기존 상태 변경 route와 상품·대화 모델을 역추적했다. 판매자는 상품을 단독으로 `SOLD`로 바꿀 수 있었고, `Listing`에는 실제 구매자 식별자가 없어 `SOLD`만으로 후기 권한을 만들면 임의 대화 상대 또는 비거래 사용자를 구매자로 오인할 수 있음을 확인했다.
- KISA/CWE 연결: 부적절한 인가, 신뢰되지 않은 입력을 보안기능 결정에 사용, CWE-285·CWE-639.
- 영향: 판매자가 거래를 일방 완료하거나 buyer ID를 위조해 거짓 후기를 만들고, 이미 판매된 legacy 상품에 사후 후기를 붙여 평판을 조작할 수 있다.
- 변경: 일반 상품 상태 변경은 `ACTIVE`↔`RESERVED`만 허용했다. 판매자가 자신이 참여한 `Conversation`으로 완료를 요청하고 그 대화의 구매자가 확인한 `Trade.COMPLETED`에서만 `SOLD`가 되며 후기를 허용한다. 상품·대화별 진행/완료 거래 UNIQUE, 상태별 timestamp CHECK, 행 잠금·atomic을 추가하고 legacy `SOLD`만 존재하는 상품은 후기 자격으로 인정하지 않는다.
- 검증: `test_seller_request_then_buyer_confirmation_completes_bound_trade`, `test_third_party_cannot_enumerate_or_mutate_trade_and_review`, `test_legacy_sold_listing_without_verified_trade_cannot_gain_review`가 통과했다.
- 잔여 위험: 쌍방 공모와 물리적 인도 여부는 시스템이 증명하지 못한다. 운영에서는 이상 거래·후기 그래프, 이의제기와 PostgreSQL 동시성 검증이 필요하다.
- 상태: **Fixed**. 후기 인가의 근거를 판매자 단독 상태가 아닌 상호 확인된 거래 객체로 변경했다.

### SEC-035 - 완료 상품 mutation과 사후 차단을 이용한 후기 억압

- 발견 단계/방법: UI 버튼 노출 조건이 아니라 update·delete·status·conversation POST를 직접 호출하는 악성 흐름과 완료 요청 뒤 `UserBlock`을 추가하는 흐름을 점검했다. 완료 상품의 직접 mutation 경로와 일반 상호작용 판정이 거래 종료에도 그대로 적용되면 판매자가 증거를 삭제·재판매하거나 구매자 확인을 차단할 수 있었다.
- KISA/CWE 연결: 부적절한 인가, 보호 메커니즘 실패, CWE-285·CWE-863.
- 영향: 완료 거래의 상품 내용·상태가 바뀌어 후기와 신고의 문맥이 훼손되고, 판매자가 완료 요청 직후 구매자를 차단해 확인 및 부정적 후기를 억압할 수 있다.
- 변경: 상품 수정·soft delete·상태 변경·새 대화 시작마다 서버에서 `PENDING_BUYER`와 `COMPLETED` 거래를 재조회해 거절한다. 구매자의 완료 응답은 현재 참여자·계정·상품 차단 상태를 확인하되 요청 이후 생성된 `UserBlock`은 권한 박탈 근거로 사용하지 않는다. 거절·판매자 취소는 잠근 상품을 요청 전 상태로 복구한다.
- 검증: `test_completed_trade_blocks_update_delete_reopen_and_new_contact`, `test_seller_block_after_request_cannot_suppress_buyer_confirmation`, `test_reject_and_seller_cancel_restore_initial_listing_status`가 직접 POST 분기를 통과했다.
- 잔여 위험: 관리자 제재로 상품·계정이 차단되면 거래 종료가 중단될 수 있으며, 이 경우의 분쟁 처리와 증거 보존 SLA는 운영 정책이 필요하다.
- 상태: **Fixed**. UI 숨김과 무관하게 모든 관련 mutation 경계에서 완료 거래를 보호한다.

### SEC-036 - 후기 저장형 XSS·개인정보 노출과 선공개 보복

- 발견 단계/방법: 공개 후기 본문을 공격 표면으로 놓고 script markup, 이메일·URL·긴 전화번호 형태와 첫 후기 직후 상대가 내용을 보는 시나리오를 점검했다.
- KISA/CWE 연결: 크로스사이트 스크립트, 개인정보 노출 최소화, CWE-79·CWE-200.
- 영향: escape가 빠진 새 템플릿에서 저장형 XSS로 발전하거나 공개 프로필에 연락처가 노출될 수 있고, 먼저 작성된 평가를 본 상대가 보복성 별점·본문을 작성할 수 있다.
- 변경: `ReviewForm`은 NFKC 정규화와 허용되지 않은 제어문자, 이메일·URL·7자리 이상 숫자열 패턴을 거부하고 별점 1~5·본문 500자를 모델과 DB 제약으로 다시 제한한다. 방향은 서버가 결정하고 첫 후기는 `PENDING`, 두 번째 생성 뒤 두 후기를 동시에 `PUBLIC`으로 바꾼다. 공개 프로필은 공개 후기의 primitive 허용목록만 전달하고 Django autoescape를 유지하며 거래 UUID·상품·가격·지역을 제외한다.
- 검증: `test_reviews_are_server_direction_bound_blind_published_and_unique`, `test_review_rejects_common_public_pii_patterns`, `test_public_profile_escapes_xss_and_hides_trade_metadata`가 통과했다.
- 잔여 위험: 정규식은 모든 우회 표기와 문맥상 개인정보를 판별할 수 없고 정상 문장을 오탐할 수 있다. `HIDDEN` 상태는 있으나 운영자 숨김 action·신고/이의제기 workflow는 아직 완성되지 않아 배포 전 보강해야 한다.
- 상태: **Mitigated**. 현재 알려진 출력·PII·보복 경로를 줄였지만 사람 moderation은 잔여 통제다.

### SEC-037 - 알림 객체 IDOR와 비공개 상품 metadata 노출

- 발견 단계/방법: 저장 검색 삭제·개별 읽음 route의 UUID를 다른 사용자 값으로 바꾸고, 알림 생성 뒤 상품을 `BLOCKED`로 전환해 알림함의 제목·이전/새 가격·이벤트 종류가 남는지 점검했다.
- KISA/CWE 연결: 부적절한 인가, 중요정보 노출, CWE-639·CWE-200.
- 영향: 공격자가 타인의 알림 상태나 저장 검색을 변경하고, 신고 차단·삭제된 상품의 제목과 가격 변동을 알림 snapshot을 통해 계속 열람할 수 있다.
- 변경: 저장 검색 삭제와 알림 읽음은 항상 `(pk, user/recipient=request.user)`로 조회하고 전체 읽음도 recipient filter만 갱신한다. 알림 목록은 요청 시 현재 상품의 공개 가능성을 다시 평가하며 비공개면 제목·가격·`NEW_MATCH`/`PRICE_DROP` 종류를 전달하지 않는 일반 카드만 렌더링한다.
- 검증: `test_saved_search_delete_and_notification_read_are_owner_scoped`, `test_private_listing_hides_title_prices_and_event_kind`가 타인 UUID와 차단 상품 분기를 통과했다.
- 잔여 위험: 알림·저장 검색의 보존기간과 사용자 일괄 삭제 정책은 아직 운영 문서가 필요하며, 신규 템플릿에서도 객체 전체 전달을 다시 도입하지 않도록 회귀를 유지해야 한다.
- 상태: **Fixed**. 객체 소유권과 현재 상품 공개 상태를 각각 서버에서 재검사한다.

### SEC-038 - 알림 fan-out 소급·중복·실패와 자원고갈

- 발견 단계/방법: 한 사용자의 여러 저장 검색 동시 매칭, 이벤트 생성 뒤 구독 추가, 가격 인상·인하, 차단·정지 계정, 같은 이벤트 재처리와 transaction commit 전 전달을 적대적으로 조합했다.
- KISA/CWE 연결: 부적절한 자원 관리, 경쟁조건, 신뢰경계 오류, CWE-400·CWE-362.
- 영향: 같은 사건의 알림 폭증, 과거 상품의 소급 알림, rollback된 상품의 유령 알림, 변조된 가격 하락 정보, 차단 관계 우회와 동기 대량 조회로 인한 요청 지연이 발생할 수 있다.
- 변경: `ListingEvent`에 사건 종류·잠근 old/new 가격·시각·처리 시각을 저장하고 이벤트 형태 CHECK와 `(recipient,event)` UNIQUE를 적용했다. 이벤트 이전에 생성된 저장 검색/찜만 대상으로 판매자·양방향 차단·비활성·정지 계정을 제외하고 사용자별 한 건으로 합친다. 20개 검색 quota, 200개 iterator/bulk batch, 이벤트 행 잠금과 멱등 `processed_at`을 사용하며 fan-out은 `transaction.on_commit()` 뒤 시작한다. callback 실패는 상품 write를 rollback하지 않고 이벤트를 미처리로 남긴다.
- 검증: `test_new_listing_matches_multiple_searches_but_creates_one_notification`, `test_subscriptions_created_after_event_are_not_retroactive`, `test_listing_update_notifies_only_on_drop_with_locked_old_and_new_prices`, `test_blocked_suspended_and_seller_accounts_are_excluded`, `test_dispatch_is_idempotent_even_when_pending_state_is_retried`, `test_create_event_dispatches_only_from_on_commit_callback`가 통과했다.
- 잔여 위험: 매칭은 현재 웹 프로세스에서 선형 순회한다. 미처리 이벤트를 `--limit` 범위에서 수동 재처리하는 명령은 추가했지만 자동 worker·backoff는 아니므로 운영 전 queue·dead-letter/지연 지표와 PostgreSQL 잠금·대량 부하 검증이 필요하다.
- 상태: **Mitigated**. 현재 규모의 중복·시각·transaction 경계는 통제했으나 대규모 비동기 운영 통제는 남아 있다.

### SEC-039 - 다중 이미지 전체 제한 누락과 stale 삭제 필드

- 발견 단계/방법: 대표 사진과 추가 사진을 서로 다른 form field에 나눴을 때 각 field만 검사하는 우회, 여섯 장 업로드, 대표를 제외한 합계 계산, 다른 상품의 추가 사진 UUID를 삭제 목록에 넣는 흐름을 점검했다.
- KISA/CWE 연결: 입력데이터 검증, 자원고갈, 신뢰되지 않은 참조, CWE-20·CWE-400.
- 영향: 공격자가 허용 개수·20MB 합계를 우회해 이미지 decode 비용을 키우거나 stale/위조 자식 ID로 다른 상품 사진을 삭제할 수 있다.
- 변경: form/sanitizer보다 먼저 `request.FILES` key를 `image`·`extra_images`로 제한하고 두 field의 모든 파일을 합쳐 최대 5장·20MB를 검사한다. 폼도 기존-삭제+추가 최종 개수를 검증하며 삭제 선택지는 현재 상품 자식만 만든다. 저장 transaction에서 상품과 현재 `ListingImage`를 잠그고 제출 ID가 그 집합의 부분집합인지 다시 확인한다. 대표 삭제 시 첫 추가 사진을 승격하고 위치 1~4 CHECK·상품별 위치 UNIQUE를 유지한다.
- 검증: `test_six_files_are_rejected_before_image_sanitizing`, `test_representative_is_included_in_batch_limit_before_sanitizing`, `test_unexpected_file_field_is_rejected_before_sanitizing`, `test_foreign_listing_extra_image_cannot_be_deleted`, `test_clearing_primary_promotes_first_extra_and_cleans_old_file`가 통과했다.
- 잔여 위험: reverse proxy가 Django 제한 전 body를 받을 수 있으므로 요청 본문 제한이 별도로 필요하고, SQLite의 행 잠금 의미는 운영 PostgreSQL과 같지 않다.
- 상태: **Fixed**. 애플리케이션의 모든 이미지 field를 하나의 batch 경계와 잠근 자식 인가로 묶었다.

### SEC-040 - 추가 사진 child IDOR·내부 경로와 rollback orphan

- 발견 단계/방법: 공개 상품 UUID에 다른 상품의 추가 사진 UUID를 조합하고, 수정/상세 HTML에서 storage name을 검색했으며, 대표와 추가 파일 저장 뒤 DB 예외를 강제로 발생시켰다.
- KISA/CWE 연결: 부적절한 인가, 시스템 정보 노출, 불완전한 cleanup, CWE-639·CWE-200·CWE-459.
- 영향: 비공개 또는 다른 상품의 사진 열람, 내부 object key 노출, 실패 요청 반복으로 orphan 파일과 저장 비용이 누적될 수 있다.
- 변경: 추가 사진 route는 먼저 공개 가능한 부모 상품을 조회한 뒤 `(pk=image_pk, listing=parent)`로 자식을 제한하고 `private, no-store`·`nosniff`를 적용한다. 템플릿은 application route만 사용해 내부 저장명과 `MEDIA_URL`을 출력하지 않는다. 생성·수정 중 새로 쓴 `FieldFile`을 추적해 transaction 예외 시 해당 상품 prefix의 요청 생성 파일만 삭제하고 기존 교체 파일 삭제는 commit 뒤 수행한다.
- 검증: `test_extra_image_route_enforces_parent_visibility_and_no_store`, `test_listing_pages_do_not_expose_internal_storage_names`, `test_database_failure_after_file_write_cleans_all_orphans`가 forged parent, HTML 비노출과 저장 후 강제 실패를 통과했다.
- 잔여 위험: cloud object storage 삭제는 best-effort·eventual consistency일 수 있다. 운영에서는 주기적 DB-reference/orphan 대사와 삭제 실패 지표가 필요하다.
- 상태: **Mitigated**. 확인한 route와 요청 rollback 경로는 방어했으며 외부 저장소 운영 대사가 잔여 통제다.

### SEC-041 - 하자·신고 다중 증거와 관리자 열람 경계 누락

- 발견 단계/방법: 임의 하자 code와 상태/코드 불일치를 제출하고, 대표 외 추가 사진이 신고 뒤 삭제되는 흐름과 관리자 증거 URL의 report/evidence ID 조합을 점검했다.
- KISA/CWE 연결: 입력데이터 검증, 증거 무결성, 부적절한 인가, CWE-20·CWE-639.
- 영향: 판매자가 정의되지 않은 하자 값을 저장해 필터·표시를 우회하고, 신고 후 추가 사진이나 하자 설명을 바꿔 조사 증거가 소실되며, 관리자가 권한 없는 report의 child evidence를 열람하거나 큰 파일을 메모리에 읽을 수 있다.
- 변경: 하자 상태를 3개, 코드를 8개 `TextChoices` 허용목록으로 제한하고 `PRESENT`에는 하나 이상, `OTHER`에는 상세 설명을 요구한다. 신고 transaction에서 모든 사진의 위치·저장명·SHA-256과 하자 상태·코드·설명을 snapshot하며 참조된 파일은 상품 삭제 뒤에도 보존한다. `ReportImageEvidence`는 독립 Admin에 등록하지 않고 report change 화면에서만 링크한다. 열람 route는 report 조회 권한과 `(report,evidence_id)`를 재검사하고 최대 5MB+1byte만 읽으며 `hmac.compare_digest()` 무결성 검증, `private, no-store`·`nosniff`, 고정 파일명을 적용한다.
- 검증: `test_defect_disclosure_code_and_other_detail_rules`, `test_defect_details_are_escaped_on_detail_page`, `test_report_snapshots_all_images_and_defects_then_retains_files_on_delete`, `test_all_report_images_use_report_scoped_verified_endpoint`가 위조 코드·XSS·삭제 뒤 3장 보존·내부명 비노출·잘못된 parent 404를 통과했다.
- 잔여 위험: 증거 보존기간·법적 삭제·승인자 분리와 접근로그 보관 기준은 아직 운영 정책이 필요하다. 현재 관리자 표적 회귀는 report-scope를 검증했으며 oversized·digest mismatch 다중 증거 분기는 기존 단일 증거 검사와 공유하지만 별도 회귀를 추가할 가치가 있다.
- 상태: **Mitigated**. 입력·snapshot·관리자 조회의 기술 경계는 적용했고 증거 lifecycle 정책은 남아 있다.

### SEC-042 - 비공개 후기가 판매자 공개 평균에 조기 반영

- 발견 단계/방법: 쌍방 blind 후기의 첫 번째 제출 직후 공개 프로필 본문은 숨겨졌지만 상품 상세의 판매자 평균과 공개 프로필 집계가 변하는지 적대적으로 점검했다.
- KISA/CWE 연결: 중요정보 노출, 잘못된 공개 상태 처리, CWE-200.
- 영향: 첫 후기 본문을 직접 공개하지 않아도 평균·개수 변화로 제출 여부와 평점을 추론할 수 있어 blind publication이 약해지고 상대의 보복성 후기 판단에 단서가 된다.
- 변경: 공개 프로필의 받은 후기 queryset과 판매자 평점 집계 모두 `Review.Visibility.PUBLIC`만 포함하도록 통일했다. 첫 후기가 `PENDING`인 동안 공개 개수는 0, 평균은 `None`으로 유지하고 양쪽 제출 뒤 두 후기가 `PUBLIC`이 된 뒤에만 반영한다.
- 검증: `test_reviews_are_server_direction_bound_blind_published_and_unique`가 첫 제출 직후 프로필 `review_count=0`, 상품 상세 `seller_average_rating=None`, 평균 문구 비노출과 쌍방 제출 뒤 동시 공개를 확인했다.
- 잔여 위험: 운영자나 DB 관리자는 비공개 후기를 열람할 수 있으므로 최소권한·접근로그와 후기 숨김/이의제기 정책이 필요하다.
- 상태: **Fixed**. 공개 본문과 집계가 같은 visibility 경계를 사용한다.

### SEC-043 - slash 구분 전화번호의 후기 개인정보 필터 우회

- 발견 단계/방법: 전화번호를 `010-1234-5678`뿐 아니라 `010/1234/5678`처럼 흔한 구분자로 바꿔 후기 입력 검사를 우회할 수 있는지 확인했다.
- KISA/CWE 연결: 입력데이터 검증, 개인정보 노출 최소화, CWE-20·CWE-200.
- 영향: 공개 후기에 전화번호가 저장되어 연락처 노출·외부 유도·스팸에 악용될 수 있다.
- 변경: 7자리 이상 숫자열을 탐지하는 구분자 허용목록에 `/`를 포함해 공백·괄호·점·밑줄·하이픈·slash로 나눈 숫자도 거부한다. 이메일·URL과 길이 제한은 그대로 유지한다.
- 검증: `test_review_rejects_common_public_pii_patterns`에 `010/1234/5678`을 추가했고 개인정보 오류 400과 후기 미생성을 확인했다.
- 잔여 위험: 정규식은 문자 치환·한글 숫자·이미지 속 연락처·문맥상 개인정보를 완전히 판별하지 못하고 정상 숫자를 오탐할 수 있다. 신고·숨김·이의제기 절차는 여전히 필요하다.
- 상태: **Mitigated**. 확인한 slash 우회는 막았지만 자동 PII 탐지 자체는 보조 통제다.

### SEC-044 - 오래 열린 Listing Admin 수정의 moderation 상태 덮어쓰기

- 발견 단계/방법: 관리자가 상품 수정 폼을 연 뒤 다른 관리자 또는 자동 신고 임계치가 같은 상품을 `BLOCKED`로 바꾸고, 오래 열린 폼을 저장하는 TOCTOU 시나리오를 재현했다.
- KISA/CWE 연결: 경쟁조건, 부적절한 인가·상태 검증, CWE-362·CWE-285.
- 영향: stale Admin 객체가 최신 `status`, 차단 사유·처리자·시각을 덮어써 차단 상품을 다시 노출하거나 감사 근거를 소실할 수 있다.
- 변경: `ListingAdmin.save_model()`에서 현재 행을 `select_for_update()`로 다시 읽고 seller·status·차단 처리자·사유·시각을 폼 instance와 비교한다. 불일치나 form 없는 변경은 거부하고, 일치하는 경우에도 명시한 편집 가능 필드만 잠긴 최신 객체로 복사해 저장한다.
- 검증: `test_stale_admin_change_cannot_overwrite_new_blocked_state`가 `PermissionDenied`, 최신 `BLOCKED`·차단 사유 유지, 오래된 제목 미반영을 확인했다. `TradeReviewSecurityTests`와 `ListingAdminSecurityTests` 합계 **16개 / 17.393초 / system check 0건**도 통과했다.
- 잔여 위험: SQLite의 `select_for_update()`는 실질적인 행 잠금을 제공하지 않는다. 다중 사용자 운영 전 PostgreSQL에서 두 Admin·자동 moderation 동시 저장 부하를 다시 검증해야 한다.
- 상태: **Fixed**. 애플리케이션의 stale overwrite 경계는 거부하지만 운영 동시성 보장은 PostgreSQL 전환을 전제로 한다.

### SEC-045 - multipart 요청 전체 크기의 파싱 전 자원고갈 경계 누락

- 발견 단계/방법: 다중 이미지의 5장·20MB Form 검사를 재검토하면서 CSRF middleware가 view보다 먼저 `request.POST`를 파싱하고, `Content-Length`가 없거나 축소된 chunked 요청은 view의 합계 검사 전에 Django upload handler까지 도달하는 경로를 확인했다.
- KISA/CWE 연결: 시스템 자원 접근·입력데이터 크기 검증, CWE-400.
- 영향: 공격자가 큰 multipart POST·PUT·PATCH 또는 여러 파일의 누적 body를 반복 전송해 폼의 20MB 검사 전에 네트워크·parser·임시 저장소·worker 자원을 소비할 수 있다. `Content-Length`만 신뢰하면 축소·누락 헤더로 조기 제한을 우회할 수 있다.
- 변경: `MultipartUploadLimitMiddleware`를 CSRF보다 앞에 두고 알려진 `Content-Length`가 21MiB를 넘으면 downstream·body read 전에 거부한다. 길이가 누락·chunked·축소된 경우에는 가장 앞의 `CumulativeUploadLimitHandler`가 파일마다 reset되는 `start` 대신 요청 전체 실제 chunk byte를 누적해 같은 상한을 적용한다. POST·PUT·PATCH만 대상으로 하며 초과 응답은 내부 예외명·limit 문구 없이 기존 일반 400과 CSP·`nosniff`·frame `DENY`·`private, no-store`를 사용한다. 기존 6MiB data memory, 5MiB file memory, 최대 5파일과 이미지 합계 20MB 검사는 심층 경계로 유지한다.
- 검증: `MultipartUploadLimitTests` **7개 / 0.023초**가 middleware 순서·기존 정책, 세 write method의 known-length 조기 거부와 downstream 미호출, 여러 파일 누적, 축소·누락·chunked 길이, 정상 multipart 통과, 오류 진단정보 비노출·보안 헤더를 확인했다.
- 잔여 위험: 이 제한은 Django에 도달한 요청을 보호한다. reverse proxy가 application보다 먼저 큰 body를 수신하는 비용, 느린 업로드와 연결 수 고갈은 proxy의 body/time/connection limit과 실제 부하 시험으로 별도 통제해야 한다.
- 상태: **Mitigated**. 애플리케이션 pre-parser 경계는 적용했으며 upstream 인프라 자원 통제가 남아 있다.

### SEC-046 - 조건부 하자 입력의 stale·모순 상태와 불명확한 오류·제출 피드백

- 발견 단계/방법: 상품 등록·수정 사용성 검토에서 `하자 없음`·`확인하지 못함`에도 하자 체크와 상세가 항상 보여 입력 관계가 불명확하고, 상태 변경 뒤 숨겨야 할 상세 문구가 브라우저나 요청에 남을 수 있는 흐름을 점검했다. 서버 오류 뒤 화면이 다시 렌더링되어도 전체 원인·오류 위치·처리 중 상태가 충분히 드러나지 않아 사용자가 새로고침 실패로 오인하거나 제출을 반복할 가능성도 확인했다.
- KISA/CWE 연결: 입력데이터 검증·보안기능 결정의 신뢰 경계·오류 처리, CWE-20. 접근성·중복 제출 피드백은 직접 권한 우회라기보다 안전한 입력 검증을 사용자가 올바르게 수행하게 하는 품질 통제다.
- 영향: 하자 상태와 체크·상세가 모순된 고지가 저장되거나 오래된 상세가 의도와 다르게 남을 수 있고, 클라이언트 동작만 신뢰하면 crafted POST로 조건을 우회할 수 있다. 오류를 인지하지 못한 반복 제출은 불필요한 요청·파일 처리와 사용자 혼동을 만든다.
- 변경: `PRESENT`에서만 관련 그룹을 표시·활성화하고, 비-`PRESENT`로 바꿀 때 checkbox·상세를 비활성화·초기화한다. `OTHER` 선택 시 상세에 native `required`를 적용하고 폼의 기본 HTML 검증을 복구했다. 서버 `ListingForm.clean()`은 JavaScript와 무관하게 `PRESENT`의 항목 필수, 비-`PRESENT`의 항목 거부, code 허용목록을 유지하며 정상 비-`PRESENT` 요청의 stale 상세를 빈 값으로 정규화한다. 서버 오류는 전체 필드 요약·입력 링크에 모아 포커스·스크롤하고, 오류가 있는 조건부 그룹은 펼친다. 유효한 제출 뒤 버튼은 `aria-busy`·disabled·`저장 중…` 상태로 바꾼다.
- 검증: `MultiImageDefectSecurityTests`의 하자 추가→비-`PRESENT` 수정·stale 상세 제거 회귀를 포함해 `MultiImageDefectSecurityTests`·`MultipartUploadLimitTests`·`ListingAdminSecurityTests`·`TradeReviewSecurityTests` 최신 결합 **40개 / 17.697초 / system check 0건 / Ruff PASS**가 통과했다. 템플릿·스크립트에서 오류 요약 링크, `novalidate` 부재, 조건부 disabled/clear, `OTHER` required, 제출 잠금도 함께 확인했다.
- 잔여 위험: JavaScript가 꺼진 환경에서는 모든 조건부 입력의 점진적 UX 대신 서버 오류에 의존하지만 서버 불변조건은 유지된다. 실제 키보드·스크린리더·200% 확대에서 오류 요약 이동과 동적 required 안내는 제출 전 수동 인수가 필요하다.
- 상태: **Fixed**. 저장 무결성은 서버에서 보장하고 조건부 입력·오류·중복 제출 피드백을 보강했으며 실제 보조기술 인수는 별도 품질 게이트로 남긴다.

### SEC-047 - 두 탭 상품 수정의 lost update와 거래 상태·CTA 불일치

- 발견 단계/방법: 상품 수정 화면을 두 탭에서 연 뒤 한 탭이 먼저 가격·하자·제목을 저장하고 다른 탭이 오래된 폼을 제출하는 흐름, 한 상품의 여러 구매자 대화 중 한 대화에서 완료 확인이 진행될 때 나머지 대화 화면을 대조했다.
- KISA/CWE 연결: 경쟁조건·데이터 무결성·인가 결정의 최신 상태 검증, CWE-362·CWE-367. 다른 거래 상대의 식별정보 최소화는 개인정보 노출 경계와도 연결된다.
- 영향: 마지막 요청이 조용히 이기면 먼저 저장한 가격·하자·제목이 사라지고 가격 하락 알림 event의 근거도 사용자의 의도와 어긋날 수 있다. 상품 전체의 활성 거래와 현재 대화의 거래를 구분하지 않으면 무관한 대화에 완료 CTA가 나타나 잘못된 요청을 유도하거나 진행 상대를 추론하게 할 수 있다.
- 변경: 수정 GET에서 `updated_at` microseconds 값을 hidden `revision`으로 제공한다. POST transaction 안에서 상품 행을 잠근 뒤 최신 revision과 비교하고 다르면 어느 편집 필드·파일·하자·알림도 저장하지 않은 채 409와 일반 오류 요약·사진 재선택 안내를 반환한다. 거래 대화는 상품 전체 활성 거래를 한 번 조회한 뒤 현재 conversation과 일치하는 경우만 `active_trade`로 전달하며, 다른 대화의 활성 거래는 boolean 안내만 제공해 완료·후기 CTA와 상대 식별정보를 숨긴다. 현재 대화에 최근 `REJECTED`·`CANCELLED`가 있으면 그 상태·시각만 표시한다.
- 검증: `test_stale_browser_revision_returns_conflict_without_overwrite`가 409·최신 제목 유지와 비저장을 확인했다. 거래 후기 회귀는 다른 대화의 진행 안내·CTA 비노출·신원 비공개와 현재 대화의 거절·취소 기록을 확인한다. 관련 네 테스트 class의 최신 결합 결과는 **40개 / 17.697초 / system check 0건**, Ruff PASS이며 변경 후 전체 Django tests도 **219 / 219 / 157.165초 / system check 0건**으로 통과했다.
- 잔여 위험: 브라우저 폼은 revision을 항상 보내지만 기존 호환을 위해 revision이 없는 인증 소유자 요청까지 강제 거부하지 않는다. SQLite의 `select_for_update()`도 실질 행 잠금을 제공하지 않는다. 운영 API에서는 revision 또는 `If-Match`를 필수화하고 PostgreSQL에서 두 요청의 실제 경합을 재시험해야 한다.
- 상태: **Mitigated**. 일반 브라우저의 lost update와 잘못된 CTA·상대 노출은 통제했지만 revision 누락 호환과 개발 DB 동시성 한계가 남는다.

### UX-001 - 업로드 대상·오류·처리 중 피드백의 불일치

- 발견: preflight에서 거부된 파일을 같은 bound form에 다시 넣으면 재디코딩 비용과 중복 오류 가능성이 있고, 파일 input은 브라우저 보안상 복원되지 않는데도 텍스트와 사진의 유지 여부가 분명하지 않았다. 추가 사진 썸네일·삭제 checkbox·번호가 시각적으로 느슨했고 대표 삭제 뒤 승격 규칙도 예측하기 어려웠다. 상품·메시지·후기 폼의 오류 요약·포커스·native validation·submit lock도 일관되지 않았다.
- 변경: preflight 오류 시 거부 파일 객체를 bind·디코딩하지 않고 제한을 통과한 텍스트만 유지하며 사진 재선택을 명시한다. 브라우저는 5장·5MiB/장·20MiB를 사전 안내하고, 6파일 위조는 Django parser의 진단 없는 일반 400으로 처리한다. 추가 사진은 보호 썸네일·연속 번호·삭제 checkbox를 같은 label로 결합하고 대표 승격 안내를 추가했다. 세 폼은 공통 오류 summary partial과 focus, native validation, 유효 제출 중 버튼 잠금을 공유한다.
- 보안 경계: 클라이언트 크기 검사와 submit lock은 보조 UX이며 서버의 5파일 parser, 21MiB middleware, preflight·sanitizer·Form·CSRF·rate limit을 대체하지 않는다. 오류 응답은 거부 파일명 외 내부 저장명·예외·limit 구현을 노출하지 않는다.
- 증적: 최신 결합 **40개 / 17.697초 / system check 0건 / Ruff PASS**. 실제 키보드·스크린리더·200% 확대와 브라우저 파일 선택 조합 전수 인수는 제출 전 수동 항목으로 남긴다.

## 2026-07-13 신규 기능의 위협 검토와 예방 통제

기능을 의도적으로 취약하게 만든 뒤 고친 것은 아니다. SEC-034~047은 기존 직접 상태 변경 경로와 신규 기능의 구현·적대적 테스트·후속 UI 감사에서 실제로 확인한 공격 경계를 기록했고, 아래 표는 구현 전에 식별해 같은 변경에서 예방한 추가 통제를 별도로 정리한다.

| 기능 | 식별한 위험 | 적용한 통제 | 표적 증적 |
|---|---|---|---|
| 공개 프로필·소개글 | 이메일·권한·정지 사유 노출, Mass Assignment, 저장형 XSS | 활성 일반 사용자만, `username`·`bio` primitive 허용목록, 500자, Django autoescape, read-only 공개 route | 공개 허용목록·privileged 404·XSS·POST 405·forged privilege 필드 불변 |
| 비밀번호 변경 | 현재 비밀번호 없이 탈취, 약한 비밀번호, oversized hash DoS, brute force, 변경 후 세션 혼동 | Django `PasswordChangeForm`·validators, 256자 사전 제한, 시간당 10회, sensitive POST, `update_session_auth_hash` | 현재 비밀번호·강도·사전 길이·rate·세션 회전 회귀 |
| 로그인 회원 전체 채팅 | sender 위조, CSRF, XSS, 무제한 본문·조회·DOM, cursor 변조, 차단 우회 | session sender, POST+CSRF, 1,000자, 송신 10/분·조회 40/분, 서명 cursor·100건, `textContent`, DOM 200개, 양방향 차단 필터 | 인증·CSRF·sender·XSS·cursor tamper·limit·block·Admin read-only 회귀 |
| 신고 누적 자동조치 | 중복·자기신고·공모에 의한 서비스거부, 관리자 lockout, 경합, 영구삭제 오탐 | 서로 다른 3 OPEN reporter, 조건부 UNIQUE, 자기/판매자 제외, target row lock·atomic, staff/superuser 보호, 임시 제재·감사로그·권한 복구 | 중복 미집계·3인 threshold·safe redirect·보호계정·자동복구·수동차단 불변 회귀 |
| 쌍방 후기 | 단독 완료·buyer 위조·IDOR·보복 후기·PII/XSS | conversation-bound Trade, buyer confirm, server direction, blind publication, primitive 공개 허용목록 | 완료/거절·legacy SOLD·제3자·완료 mutation·사후 block·blind/unique·PII/XSS 회귀 |
| 관심 검색·가격 하락 알림 | IDOR·비공개 metadata·소급·중복·rollback 유령·fan-out DoS | owner scope, 현재 공개성, 구조화 event, created-at 경계, recipient UNIQUE, on-commit, quota/batch | 소유자·private card·중복 조건·late subscription·locked price·exclude·idempotence 회귀 |
| 다중 사진·하자·신고 증거 | multipart 파싱 전 자원고갈·파일 수/합계 우회·stale child/revision·orphan·상태/상세 모순·XSS·증거 소실·Admin child IDOR | CSRF 전 21MiB+실제 chunk 누적, client 5장/5MiB/20MiB 보조 검사, 거부 파일 미결합, locked child+revision scope, protected route, rollback cleanup, 조건부 UI+서버 defect allowlist·stale 정규화, multi-hash snapshot, report-scoped Admin | 최신 결합 표적 40개에서 preflight·multipart·foreign child·대표 승격·두 탭 409·하자 add→clear·XSS·삭제 보존·Admin scope 회귀 |
| 거래 대화 상태·공통 폼 피드백 | 상품 전체 거래와 현재 대화 혼동, 다른 상대 추론, 오류 위치 미인지·중복 제출 | current/other trade 분리, 다른 거래 CTA·상대 비공개, 현재 대화 닫힘 기록, 공통 오류 summary/focus/native validation/submit lock | 최신 거래 후기·템플릿 표적에서 다른 거래·거절·취소·폼 피드백 회귀 |

## 자동검사 증적

### 2026-07-13 수정 분기 표적 회귀

- 실행 대상: 공개 프로필, 마이페이지, 전체 채팅·Admin, 상품, 신고 자동조치, DEBUG/운영 오류 응답 관련 8개 테스트 클래스
- 결과: **87개 통과 / 53.390초 / system check 문제 0건**
- 해석: 이 실행은 SEC-031·032와 새 기능 통제의 직접 분기 증적이며, 아래 최종 통합 품질 게이트로 전체 영향도 별도 확인했다.

### 2026-07-13 쌍방 후기·알림·다중 이미지 표적 회귀

- 실행 1: `market.test_trade_reviews`, `market.test_saved_search_notifications`, `market.test_multi_image_defects` **33개 통과 / 7.263초 / system check 문제 0건**
- 실행 2: `market.test_admin_image_evidence` **1개 통과 / 0.314초 / system check 문제 0건**
- 실행 3: 실패 이벤트 재처리 명령과 완료 거래 자동차단 복구 **2개 통과**
- 해석: SEC-034~041과 ADR-017~019의 직접 분기 36개 증적이다. 실운영 PostgreSQL 부하·브라우저 UX를 검증한 결과는 아니며, 전체 영향은 아래 최신 통합 품질 게이트로 별도 확인했다.

### 2026-07-13 후속 보안 변경 직전 통합 품질 게이트

- Django 비계측 전체 tests: **206개 통과 / 114.641초 / system check 문제 0건**
- Coverage 계측 실행: **206개 통과 / 115.434초 / 5,778 statements / 343 miss / 94%**
- Ruff: lint 오류 0건, 46개 파일 format 일치
- Bandit·pip-audit·deploy check: 이슈·알려진 취약점·경고 0건
- migration drift·`git diff --check`: 문제 0건, 당시 CSS 중괄호 987/987

### 2026-07-13 SEC-042~044 후속 표적 회귀

- 실행: `python manage.py test market.test_trade_reviews market.tests.ListingAdminSecurityTests --verbosity 1`
- 결과: **16개 통과 / 17.393초 / system check 문제 0건**
- UI 정적 확인: 웜톤 최종 cascade 적용 후 CSS 중괄호 열림/닫힘 균형 확인
- 판정 경계: 위 16개는 세 후속 보안 분기의 직접 증적이다. 이후 최종 전체 219개·Coverage 94%와 정적·공급망·deploy·migration·Node syntax·diff 게이트도 통과했으며, 직전 206개 결과는 역사적 기준선으로만 보존한다.

### 2026-07-13 SEC-045 multipart 요청 상한 표적 회귀

- 실행: `python manage.py test config.tests.MultipartUploadLimitTests --verbosity 1`
- 결과: **7개 통과 / 0.023초 / system check 문제 0건**
- 판정 경계: pre-parser application 제한의 직접 증적이며 reverse proxy·slow upload 부하 시험과 변경 후 전체 품질 게이트를 대신하지 않는다.

### 2026-07-13 SEC-042~047 최신 결합 표적 회귀

- 실행 대상: `MultiImageDefectSecurityTests`, `MultipartUploadLimitTests`, `ListingAdminSecurityTests`, `TradeReviewSecurityTests`
- 결과: **40개 통과 / 17.697초 / system check 문제 0건**, Ruff PASS
- 포함 분기: `PUBLIC` 후기 집계, slash PII, stale Admin 보호, multipart 요청 상한, 거부 파일 미결합·사진 재선택, 6파일 generic 400, client 5장·5MiB·20MiB 검증, 썸네일-삭제 직접 결합·대표 승격 안내, 하자 add→clear, 두 탭 revision 409, 다른 거래 CTA·신원 비공개, 현재 대화 거절·취소 기록, 상품·메시지·후기 공통 오류·submit lock.
- 후속 전체 Django tests: **219 / 219 통과 / 157.165초 / system check 문제 0건**
- 후속 Coverage: **219 / 219 통과 / 162.533초 / 6,037 statements / 354 miss / 94%**
- 후속 기타 게이트: **Ruff lint PASS·46 files formatted, Bandit 0, pip-audit 알려진 취약점 0, Django check·deploy warning 0, migration no changes, Node JavaScript syntax·`git diff --check` PASS**
- 판정 경계: 로컬 자동 품질 게이트는 통과했지만 실제 키보드·스크린리더 인수와 운영 PostgreSQL·proxy 부하 시험을 대신하지 않는다.

### 2026-07-13 신규 세 기능 추가 전 통합 품질 게이트

- Django 비계측 전체 tests: **170개 통과 / 102.496초 / system check 문제 0건**
- Coverage 계측 실행: **170개 통과 / 103.560초 / 4,222 statements / 248 miss / 94%**
- Ruff: lint 오류 0건, 37개 파일 format 일치
- Bandit: 이슈 0건 (`community` 포함)
- pip-audit: 알려진 취약점 0건
- `check --deploy --fail-level WARNING`: 문제 0건
- migration: `makemigrations --check --dry-run` 변경 없음, 신규 migration 적용 완료

### 2026-07-12 공통 자동검사 스냅샷

- Django tests: 120개 통과 - `image-clear`·오류 본문 비노출 분기 미포함
- Coverage: 120-test instrumentation 3,169 statements / 223 miss / 93%
- Ruff: 오류 0건
- Bandit: 이슈 0건
- pip-audit: 조치 후 취약점 0건
- 금지 API·템플릿 패턴 검색: 일치 0건
- CI·CodeQL: 구성 완료, GitHub 최초 실행 결과는 아직 미확인
- 당시 테스트 공백: 기존 120개는 `image-clear`와 DEBUG false 오류 본문 비노출을 포함하지 않아 SEC-031·032를 발견하지 못했다. 해당 분기는 2026-07-13 표적 회귀에 추가되어 통과했다.
