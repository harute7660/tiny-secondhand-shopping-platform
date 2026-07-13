# 요구사항 추적표

상태 값은 `설계`, `구현`, `검증`, `완료`, `제외`를 사용한다. 최종 보고서에는 각 요구사항을 구현 파일, 테스트, 결과와 연결한다.

| ID | 요구사항 | 우선순위 | 인수 조건 | 구현/증적 | 테스트 | 상태 |
|---|---|---:|---|---|---|---|
| REQ-001 | 과제 PDF 35페이지의 최소 기능 전체 충족 | P0 | REQ-F001~F007 구현 및 검증 | PDF 35페이지·기능 코드 | 변경 기능 79개와 전체 170개 통과, coverage 94% | 완료 |
| REQ-002 | 요구사항·설계·구현·테스트·유지보수 전 과정 보고 | P0 | 각 단계의 작업, 이유, 결과, 증적 포함 | `docs/`, README, 최종 PDF | DOC-T01 | 구현 |
| REQ-003 | 발견한 보안약점과 수정 내역 기록 | P0 | SEC-ID별 원인·수정·재시험·잔여위험 포함 | `04_SECURITY_FINDINGS.md` | SEC-T01, SEC-031·032 Fixed, 표적·전체 회귀와 브라우저 재검증 완료 | 완료 |
| REQ-004 | GitHub Public 저장소 제공 | P0 | 로그아웃 브라우저에서 열림 | 최종 URL·릴리스 SHA | REL-T01 | 설계 |
| REQ-005 | README에 환경 설정 및 실행 방법 명시 | P0 | 클린 환경에서 README 명령으로 실행 성공 | `README.md` | REL-T02 | 구현 |
| REQ-006 | AI 도구 적극 활용 및 검증 과정 기록 | P0 | 사용 목적·결과·채택 여부·사람 검증 포함 | `05_AI_USAGE_LOG.md` | DOC-T02 | 검증 |
| REQ-007 | KISA 가이드 기반 개발보안 적용 | P0 | 49개 구현단계 항목의 A/N/A 근거와 검증 존재 | `07_KISA_BASELINE.md` | KISA-T01, 오류 응답·정적·공급망·deploy 재검증 통과 | 완료 |
| REQ-008 | 제출 PDF에 GitHub 링크 포함 | P0 | URL 클릭 및 로그아웃 접근 성공 | 최종 PDF | REL-T03 | 설계 |
| REQ-009 | 제출 파일명에 공백 없이 지정 형식 사용 | P0 | `[WHS][secure-coding][XX반]이름(뒷4자리).pdf`와 일치 | 최종 PDF | REL-T04 | 설계 |
| REQ-010 | 개인 작업 목표 2026-07-12~13, 공식 제출 기한 2026-07-24 | P0 | 7월 13일 결과·보고서 초안 완성, 7월 24일 전 제출 | 개발 일지·제출 증적 | REL-T05 | 구현 |

### 현재 미충족 조건과 다음 조치

코드·로컬 보안 검증에서 확인된 미충족은 모두 조치했다. 남은 항목은 이 작업트리만으로 완료하거나 사실을 추정할 수 없는 외부·개인 제출 증적이다.

| 연결 요구사항 | 실제 미충족 조건 | 다음 조치 | 완료 증적 |
|---|---|---|---|
| REQ-004 | Public GitHub URL·제출 SHA·tag와 로그아웃 공개 결과 없음 | 최종 commit 후 Public 저장소에 push하고 시크릿/로그아웃 창에서 열기 | repository URL, SHA, 확인 시각, 화면 캡처 |
| REQ-005 | 새 디렉터리 clean clone에서 README 재현 미실행 | Public 저장소를 새 경로에 clone해 hash 설치·migration·test·server를 README만 보고 실행 | 명령 로그와 대상 SHA |
| REQ-008 | 최종 PDF와 클릭 가능한 GitHub 링크 없음 | 보고서 placeholder에 URL·SHA·원격 CI를 넣고 PDF 렌더링 | PDF에서 클릭한 공개 URL |
| REQ-009 | 반·이름·전화번호 뒷자리 정보가 없어 최종 파일명을 만들 수 없음 | 개인정보를 입력하고 공백 없는 지정 정규식으로 저장 | 최종 파일명과 재열기 결과 |
| REQ-010 | 원격 Actions/CodeQL·LMS 제출 결과 없음 | 제출 SHA의 원격 검사 성공을 확인한 뒤 2026-07-24 23:59:59 전 업로드 | Actions/CodeQL URL, LMS 확인 |
| 수동 접근성·운영 | 실제 키보드·스크린리더·200% 확대와 외부 reverse proxy 검증 미실행 | 사용자 기기에서 인수하고, 외부 배포를 선택할 때 private media·오류 응답 경계를 확인 | 체크리스트·캡처·배포 설정 |

## PDF 최소 기능 요구사항

| ID | 원문 요구사항 | 인수 조건 | 핵심 보안 조건 | 구현 | 테스트 | 상태 |
|---|---|---|---|---|---|---|
| REQ-F001 | 사람들이 플랫폼에 가입할 수 있어야 함 | 약한 비밀번호는 거부되고 정상 사용자는 가입·로그인·로그아웃 가능 | 역할 Mass Assignment 금지, 해시 저장, 일반·Admin 로그인 제한, 가입 rate limit, 세션 회전 | `accounts` | 가입 quota·proxy 경계·Admin 로그인·정지 DB 불변식 포함 테스트 | 검증 |
| REQ-F002 | 상품들을 올리고 볼 수 있어야 함 | 본인 상품 CRUD, 판매 상태 변경과 공개 상품 조회 가능 | 판매자 서버 결정, 계정 quota/rate, IDOR·stale update 차단, 이미지 검증·no-store·정리 | `market.Listing`, `/listings/mine/` | 이미지 유지·삭제·교체·모순·불량 업로드 회귀 포함 79-test 변경 기능 묶음 통과; SEC-031 수정 | 검증 |
| REQ-F003 | 플랫폼 사용자끼리 소통 가능 | 상품별 판매자·구매 희망자 1:1 대화와 페이지 목록 가능 | 참여자 외 접근 금지, sender 서버 결정, 차단 후 전송 금지, 30개 페이지·Subquery | `Conversation`, `Message` | 비참여자·발신자·차단·판매완료·N+1 회귀 테스트 | 검증 |
| REQ-F004 | 악성 사용자나 상품 차단 | 사용자는 실제 대화 상대·상품 신고와 개인 차단, 관리자는 계정 정지·상품 숨김 가능 | 대화 기반 대상, 서로 다른 OPEN 신고자 3명 자동조치, `suspend_user`·`block_listing`, read-only snapshot·SHA, 보호 계정·복구·감사 | `UserBlock`, `Report`, 자동 임계치 service, Admin | 유일 신고자·자동 임시 차단/정지·staff/superuser 보호·상품 복구 및 기존 moderation 회귀 | 검증 |
| REQ-F005 | 사용자 간 송금 가능 | DEMO POINT를 잔액 범위 내에서 송금하고 내역 조회 가능 | 실제 금융정보 미수집, 원자적 이중 원장, 음수 방지, 멱등키, append-only 원장 | `WalletAccount`, `Transfer`, `LedgerEntry` | 이중 원장·멱등·롤백·인스턴스/QuerySet 불변성 테스트 | 검증 |
| REQ-F006 | 상품 검색 가능 | 키워드·카테고리·상태·지역 필터와 페이지네이션 | ORM, 길이·정렬 허용목록, 차단 상품 제외 | `market.home` | SQLi 문자열 검색·차단 상품 제외 테스트 | 검증 |
| REQ-F007 | 관리자가 모든 요소 관리 | 각 권한을 가진 staff만 해당 요소 조회·허용된 조치 가능 | 계정 5회·네트워크 30회, 전용 조치 권한, Report·Listing 행 재검사, stale purge 부활 차단, 채팅·증거·원장 read-only | Django Admin | 전용 권한·위조 POST·경합 조치·자동 차단 복구·채팅 증거 불변·원장 불변 테스트 | 검증 |

## PDF 25~29페이지 상세 시스템 설계 추적

35페이지의 7개 대기능과 별개로, 사용자가 지정한 25~29페이지의 세부 기능·화면·DB를 14개로 중복 제거했다. 이 표의 `PASS/PARTIAL/FAIL`은 기능 존재 여부 판정이며, 위 표의 개발 단계 상태와 의미가 다르다. 29페이지의 빨간 항목은 선택이라는 범례가 없어 모두 필수로 본다.

| ID | 상세 요구 | 현재 구현·증적 | 현재 판정 | 완료하려면 |
|---|---|---|:---:|---|
| REQ-SD01 | 가입·로그인·아이디 중복 방지 | `/accounts/signup/`, `/accounts/login/`, `Lower(username)` UNIQUE, Django password hash와 가입·로그인 보안 회귀 | PASS | 전체 170개 회귀 통과 |
| REQ-SD02 | 사용자 조회·프로필 | `/accounts/users/<username>/`, `User.bio`, 활성 일반회원의 username·bio만 primitive allowlist로 공개; email·권한·정지정보 비공개, XSS escape 회귀 | PASS | `PublicProfileSecurityTests` 통과 |
| REQ-SD03 | 마이페이지 소개글·비밀번호 변경 | `/accounts/me/`, `/accounts/me/password/`; `ProfileForm`은 bio만 허용하고 현재 비밀번호·Django 강도 validator·256자 사전상한·사용자당 10회/시간·세션 hash 갱신 적용 | PASS | `MyPageSecurityTests` 통과 |
| REQ-SD04 | 상품 등록 | `ListingForm`·`listing_create`, 제목·설명·가격·사진·판매자를 서버 결정하고 이미지 검증·quota/rate 적용. 첨부 영역은 저채도 세이지로 한정하고 현재 이미지는 guarded URL로만 표시하며 내부 저장명·`MEDIA_URL`을 숨김 | PASS | `ListingSecurityTests` 26개 통과(18.104초): MIME accept/help·보호 URL·저장명 비노출 포함 |
| REQ-SD05 | 내가 등록한 상품 확인·관리 | `/listings/mine/`와 header UI, 세션 사용자의 삭제 제외 목록 20개 pagination, 소유자 수정·상태·soft delete; FileField `save_form_data()`로 SEC-031 수정 | PASS | 내 상품 격리와 이미지 유지·삭제·교체·모순·불량 업로드 회귀 통과 |
| REQ-SD06 | 비회원 공개 상품 목록 | 공개 상태·활성 판매자 필터, 검색·카드·UUID 상세 링크, 차단·삭제 상품 제외 | PASS | `ListingSecurityTests` 및 과거 전체 회귀 |
| REQ-SD07 | 상품 상세 | UUID 상세에 상품명·설명·가격·사진·상태·판매자 정보와 공개 프로필 링크 제공 | PASS | 상세 XSS·비공개 접근·프로필 링크 회귀 통과 |
| REQ-SD08 | 실시간 전체 채팅 | `/community/`, `/community/messages/`, `/community/send/`, `GlobalChatMessage`; 2초 증분 polling·서명 cursor·조회/렌더 상한·visibility pause/backoff | PASS | 인증·CSRF·서버 sender·XSS `textContent`·차단 양방향·rate·cursor·read-only Admin 회귀 통과 |
| REQ-SD09 | 1대1 채팅 | 상품별 `Conversation`·`Message`, 참여자만 조회·전송, 차단·판매완료 정책과 30개 pagination | PASS | `ConversationSecurityTests` 1차 및 과거 전체 회귀 통과 |
| REQ-SD10 | 사용자·상품 신고와 사유 | `Report`·`ReportForm`·`report_create`, reporter·target 서버 결정, OPEN 중복 제약·증거 snapshot/SHA | PASS | `ModerationSecurityTests` 통과 |
| REQ-SD11 | 신고 횟수 기반 상품 차단·삭제 | 서로 다른 OPEN 신고자 3명에서 transaction·행 잠금 후 자동 `BLOCKED` 임시 비공개; 자동 사유 식별, 보안 log, 권한 있는 Admin의 자동 차단만 복구·신고 기각 및 별도 purge | PASS | 2명/중복 미발동·3명 발동·안전 redirect·복구·수동 차단 비복구 회귀 통과 |
| REQ-SD12 | 신고 횟수 기반 사용자 휴면 | 서로 다른 OPEN 신고자 3명에서 일반 사용자 `is_suspended=True`, `is_active=False`; staff/superuser 자동조치 제외, 보안 log, 전용 권한 Admin `unsuspend_selected` 복구 | PASS | 자동 정지·자기 신고 미산입·staff/superuser 보호 회귀 통과; 해제 action은 코드·권한 경계 검토 |
| REQ-SD13 | 27페이지 필수 화면 | 기본·가입·로그인·상품 목록/등록/상세·신고·1대1 대화·프로필·마이페이지·내 상품·전체 채팅이 header 또는 화면 link로 연결 | PASS | URL reverse·template link 및 관련 view 회귀 통과 |
| REQ-SD14 | 28페이지 DB 구조와 기능상 추가 관계 | `User.bio`, `Listing`, `Report`, `Conversation`, `Message`, `GlobalChatMessage(sender FK, body 1000, created_at, time/id index)`와 제약·password hash·migrations | PASS | 모델·migration·DB 제약 및 기능 회귀 통과 |

현재 집계는 **14 PASS / 0 PARTIAL / 0 FAIL**이며 PDF 25~29페이지의 상세 시스템 기능 범위는 `READY`다. 변경 기능 6개 테스트 클래스 79개가 53.066초에 통과했고, 이미지 첨부 UI 직접 분기 26개가 18.104초에 통과했다. 최종 전체 170개는 102.496초에 통과했고 coverage 계측 실행도 170개/103.560초, 4,222 statements / 248 miss / 94%로 통과했다. 수행 증적은 `12_CORE_CHECKLIST_EXECUTED_2026-07-13.md`에 기록한다.

## 2026-07-12 검증 스냅샷

이 표는 당시 실제 실행 결과를 보존한 **과거 스냅샷**이다. 이후 SEC-031·032를 수정하고 변경 기능 79개 및 최신 최종 전체 170개를 재검증했으므로 상세 시스템 기능 판정과 최신 품질 수치는 위 현재 표와 12번 수행 문서가 대체한다.

| 검증 | 결과 | 요구사항 연결 |
|---|---|---|
| Django tests | 120개 통과 | SEC-001~030 회귀; 이미지 삭제·오류 본문 비노출 분기는 미포함 |
| Coverage | 120-test instrumentation 3,169 statements / 223 miss / 93% | 핵심 계정·인가·업로드·신고·원장·운영설정 분기 |
| Ruff | 오류 0건 | 코드오류·유지보수성 |
| Bandit | 이슈 0건 | 위험 API·보안 구현 패턴 |
| pip-audit 최초 | `pip` 취약점 6건 | 공급망 위험 발견 |
| `pip` 26.1.2 갱신 후 pip-audit | 취약점 0건 | 공급망 위험 조치 완료 |
| `manage.py check --deploy` | 문제 0건 | 운영 HSTS·쿠키·HTTPS 설정 |
| Runtime hash lock | SHA-256 포함 `requirements.lock` | 다운로드 아티팩트 무결성 |
| Dev hash lock | 빈 대상에 `--require-hashes -r requirements-dev.lock` 설치 성공 | 개발·CI 도구와 설치 아티팩트 재현성 |
| CI·CodeQL·Dependabot | workflow·설정 파일 추가 | push/PR·주간 지속 검증, 실행 결과는 GitHub 공개 후 확인 |

## 2차 보안 통제 추적

| 통제 | 이유 | 구현·검증 |
|---|---|---|
| 관리자 전용 조치 권한·보호 계정 | 신고 변경 권한이나 일반 모델 편집 권한으로 차단·정지·영구삭제하는 권한 상승 방지 | `block_listing`, `suspend_user`, `delete_listing`+`purge_listing` 재검사, self/staff/superuser 정지 제외, 위조 POST 테스트 |
| Admin 로그인 제한·정지 DB 불변식 | 관리 로그인 brute force, 성공 계정을 이용한 네트워크 제한 초기화, 우회 저장 방지 | 계정 5회·network 30회 짧은 예약, 성공 시 account만 clear, `acct_user_suspended_inactive` CHECK, 로그인·bulk update 테스트 |
| quota/rate·정지 판매자 숨김 | 저장소 고갈과 정지 계정 콘텐츠 재노출 방지 | 가입·상품·메시지·신고 상한, 공개 queryset 필터, rate/quota 테스트 |
| staff view permission | 단순 staff 플래그의 과도한 비공개 열람 방지 | `market.view_listing` 객체 조회 분기, 권한 없는 staff 테스트 |
| stale update·판매 상태 전이 | 관리자 차단 덮어쓰기와 임의 상태 변조 방지 | row lock 후 상태 재검증, POST 허용 전이, TOCTOU·전이 테스트 |
| 동적 응답·이미지 no-store·commit 정리 | moderation 뒤 익명 HTML·이미지의 공유 cache 재노출과 고아 파일 잔존 방지 | 모든 동적 응답 `private, no-store`, 이미지 `nosniff`, `on_commit` evidence-aware 정리 테스트 |
| trusted proxy 경계 | 전달 헤더 위조로 rate/HTTPS 판단 우회 방지 | 신뢰 peer만 XFF/XFP 허용, 설정 fail-closed, proxy 테스트 |
| 대화 기반 신고·차단 | 순차 사용자 ID 열거·무관 사용자 괴롭힘 방지 | 참여 대화에서 상대 파생, 비공개 placeholder·열거 거부 테스트 |
| 대화 pagination·N+1 제거 | 대량 목록 요청의 DB·응답 자원 고갈 완화 | 30개 페이지, 마지막 메시지 Subquery, annotation 테스트 |
| append-only 원장 | Admin 밖 ORM 경로의 과거 거래 변조 방지 | instance/QuerySet update·delete·upsert 거부, 불변성 테스트 |
| hash lock·CI·CodeQL | 의존성 치환과 회귀의 조기 탐지 | `--require-hashes`, 최소 권한 CI, CodeQL security-extended, Dependabot |
| 신고 증거와 private 이미지 보존 | 판매자가 신고 직후 원문·이미지를 바꾸거나 삭제·변조하는 증거 소실 방지 | read-only Report, snapshot·SHA-256, 증거명 index, `view_report` endpoint의 매 요청 hash·no-store·nosniff·actor log, private 보존 테스트 |
| 상품 수정 폼의 이미지 경로 최소노출 | 기본 파일 위젯이 내부 저장명이나 직접 media 경로를 HTML에 노출해 저장 구조를 추측하게 하는 위험 방지 | 전용 위젯의 guarded image URL·일반화된 현재 이미지 문구, 내부 저장명·`MEDIA_URL` 부재 회귀 테스트 |
| 운영 fail-closed 비밀 | 짧거나 예측 가능한 키와 설정 오타를 안전한 구성으로 오인하지 않도록 함 | 운영 key 50자·문자 다양성·금지 prefix, 엄격 boolean·HTTPS·host negative tests |
| 공개 프로필·마이페이지 최소권한 | 프로필 공개로 email·권한·정지 사유가 새거나 자기소개 수정으로 privilege mass assignment가 발생하는 것을 방지 | 공개 primitive username·bio allowlist, 활성 일반회원만 조회, `ProfileForm.fields=("bio",)`, XSS·위조 필드 회귀 |
| 비밀번호 변경 재인증·자원 상한 | 탈취 세션의 자격증명 변경과 과대 입력의 password hashing 자원 고갈 방지 | 현재 비밀번호, Django validator, 입력 256자 사전 거부, 사용자당 10회/시간, 성공 후 `update_session_auth_hash` 세션 회전 |
| 전체 채팅 bounded polling | WebSocket/SSE 상시 연결의 운영 복잡도·연결 고갈을 피하면서 짧은 구현 기간에 새 메시지를 자동 반영 | 2초 증분 polling, 서명 cursor, 요청당 최대 100·초기 50·DOM 200, poll 40/분·send 10/분, hidden pause·지수 backoff, `textContent` |
| 자동 신고 임계치와 복구 | 한 사용자의 중복 신고로 자동제재하거나 자동 영구삭제해 증거·정상 콘텐츠를 잃는 위험 방지 | 서로 다른 OPEN 신고자 3명, transaction·대상 행 잠금, 상품 임시 차단·일반 사용자 임시 정지, staff/superuser 보호, Admin 수동 복구/해제와 보안 log |

## 명시적 N/A 및 향후 범위

- 별도 주문의 요청·수락·거절·취소·완료 상태 머신은 PDF 35페이지의 최소 기능이 아니며 현재 모델·URL에 존재하지 않는다.
- 현재 구현은 판매자가 변경하는 상품 상태, 1:1 대화, DEMO POINT 송금과 감사 원장을 각각 제공한다. 이를 별도 주문의 구매 요청·승인·환불 워크플로로 표현하거나 테스트 완료로 주장하지 않는다.
- 향후 실제 거래 중개 기능을 확장할 때 주문 상태 전이 허용목록, 동시 수락 방지, 취소·환불 원장과 상태 롤백을 별도 위협 모델 및 테스트 대상으로 추가한다.
- 판매자·구매자의 정확한 실시간 GPS 상호 공유와 대중교통·자차 ETA는 PDF 최소 요구사항이 아니며 현재 구현하지 않았다. 향후에는 위치정보 동의·보존 최소화·참여자 인가·외부 지도 API 키와 호출 제한을 별도 위협 모델로 설계한 뒤, 정확한 상대 좌표 대신 약속 장소와 각자의 ETA 범위를 우선 검토한다.
