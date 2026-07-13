# 요구사항 추적표

상태 값은 `설계`, `구현`, `검증`, `완료`, `제외`를 사용한다. 최종 보고서에는 각 요구사항을 구현 파일, 테스트, 결과와 연결한다.

| ID | 요구사항 | 우선순위 | 인수 조건 | 구현/증적 | 테스트 | 상태 |
|---|---|---:|---|---|---|---|
| REQ-001 | 과제 PDF 35페이지의 최소 기능 전체 충족 | P0 | REQ-F001~F007 구현 및 검증 | PDF 35페이지·기능 코드 | 120-test 과거 스냅샷, F002 수동 QA 실패 | 구현 |
| REQ-002 | 요구사항·설계·구현·테스트·유지보수 전 과정 보고 | P0 | 각 단계의 작업, 이유, 결과, 증적 포함 | `docs/`, README, 최종 PDF | DOC-T01 | 구현 |
| REQ-003 | 발견한 보안약점과 수정 내역 기록 | P0 | SEC-ID별 원인·수정·재시험·잔여위험 포함 | `04_SECURITY_FINDINGS.md` | SEC-T01, SEC-031·032 Open | 구현 |
| REQ-004 | GitHub Public 저장소 제공 | P0 | 로그아웃 브라우저에서 열림 | 최종 URL·릴리스 SHA | REL-T01 | 설계 |
| REQ-005 | README에 환경 설정 및 실행 방법 명시 | P0 | 클린 환경에서 README 명령으로 실행 성공 | `README.md` | REL-T02 | 구현 |
| REQ-006 | AI 도구 적극 활용 및 검증 과정 기록 | P0 | 사용 목적·결과·채택 여부·사람 검증 포함 | `05_AI_USAGE_LOG.md` | DOC-T02 | 검증 |
| REQ-007 | KISA 가이드 기반 개발보안 적용 | P0 | 49개 구현단계 항목의 A/N/A 근거와 검증 존재 | `07_KISA_BASELINE.md` | KISA-T01, 에러처리 재검증 필요 | 구현 |
| REQ-008 | 제출 PDF에 GitHub 링크 포함 | P0 | URL 클릭 및 로그아웃 접근 성공 | 최종 PDF | REL-T03 | 설계 |
| REQ-009 | 제출 파일명에 공백 없이 지정 형식 사용 | P0 | `[WHS][secure-coding][XX반]이름(뒷4자리).pdf`와 일치 | 최종 PDF | REL-T04 | 설계 |
| REQ-010 | 개인 작업 목표 2026-07-12~13, 공식 제출 기한 2026-07-24 | P0 | 7월 13일 결과·보고서 초안 완성, 7월 24일 전 제출 | 개발 일지·제출 증적 | REL-T05 | 구현 |

## PDF 최소 기능 요구사항

| ID | 원문 요구사항 | 인수 조건 | 핵심 보안 조건 | 구현 | 테스트 | 상태 |
|---|---|---|---|---|---|---|
| REQ-F001 | 사람들이 플랫폼에 가입할 수 있어야 함 | 약한 비밀번호는 거부되고 정상 사용자는 가입·로그인·로그아웃 가능 | 역할 Mass Assignment 금지, 해시 저장, 일반·Admin 로그인 제한, 가입 rate limit, 세션 회전 | `accounts` | 가입 quota·proxy 경계·Admin 로그인·정지 DB 불변식 포함 테스트 | 검증 |
| REQ-F002 | 상품들을 올리고 볼 수 있어야 함 | 본인 상품 CRUD, 판매 상태 변경과 공개 상품 조회 가능 | 판매자 서버 결정, 계정 quota/rate, IDOR·stale update 차단, 이미지 검증·no-store·정리 | `market.Listing` | 기존 120 tests에 이미지 삭제 sentinel 분기 누락; SEC-031 Open | 구현 |
| REQ-F003 | 플랫폼 사용자끼리 소통 가능 | 상품별 판매자·구매 희망자 1:1 대화와 페이지 목록 가능 | 참여자 외 접근 금지, sender 서버 결정, 차단 후 전송 금지, 30개 페이지·Subquery | `Conversation`, `Message` | 비참여자·발신자·차단·판매완료·N+1 회귀 테스트 | 검증 |
| REQ-F004 | 악성 사용자나 상품 차단 | 사용자는 실제 대화 상대·상품 신고와 개인 차단, 관리자는 계정 정지·상품 숨김 가능 | 대화 기반 대상, `suspend_user`·`block_listing`, read-only snapshot·SHA, `view_report` 증거 endpoint, 보호 계정·비공개 placeholder | `UserBlock`, `Report`, Admin | 열거 거부·위조 POST·보호 계정·snapshot/이미지 보존·SHA 재검증·비공개 metadata 테스트 | 검증 |
| REQ-F005 | 사용자 간 송금 가능 | DEMO POINT를 잔액 범위 내에서 송금하고 내역 조회 가능 | 실제 금융정보 미수집, 원자적 이중 원장, 음수 방지, 멱등키, append-only 원장 | `WalletAccount`, `Transfer`, `LedgerEntry` | 이중 원장·멱등·롤백·인스턴스/QuerySet 불변성 테스트 | 검증 |
| REQ-F006 | 상품 검색 가능 | 키워드·카테고리·상태·지역 필터와 페이지네이션 | ORM, 길이·정렬 허용목록, 차단 상품 제외 | `market.home` | SQLi 문자열 검색·차단 상품 제외 테스트 | 검증 |
| REQ-F007 | 관리자가 모든 요소 관리 | 각 권한을 가진 staff만 해당 요소 조회·허용된 조치 가능 | 계정 5회·네트워크 30회, 전용 조치 권한, Report·Listing 행 재검사, stale purge 부활 차단, read-only 증거·원장 | Django Admin | 전용 권한·위조 POST·경합 조치·stale resurrection·증거/원장 불변 테스트 | 검증 |

## 2026-07-12 검증 스냅샷

이 표는 당시 실제 실행 결과를 보존한 **과거 스냅샷**이다. 2026-07-13 사용자 QA에서 기존 이미지 삭제 500과 DEBUG 기술 화면 노출 위험을 발견했으므로, SEC-031·032 수정과 신규 회귀가 끝날 때까지 최종 합격 근거로 사용하지 않는다.

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
| 운영 fail-closed 비밀 | 짧거나 예측 가능한 키와 설정 오타를 안전한 구성으로 오인하지 않도록 함 | 운영 key 50자·문자 다양성·금지 prefix, 엄격 boolean·HTTPS·host negative tests |

## 명시적 N/A 및 향후 범위

- 별도 주문의 요청·수락·거절·취소·완료 상태 머신은 PDF 35페이지의 최소 기능이 아니며 현재 모델·URL에 존재하지 않는다.
- 현재 구현은 판매자가 변경하는 상품 상태, 1:1 대화, DEMO POINT 송금과 감사 원장을 각각 제공한다. 이를 별도 주문의 구매 요청·승인·환불 워크플로로 표현하거나 테스트 완료로 주장하지 않는다.
- 향후 실제 거래 중개 기능을 확장할 때 주문 상태 전이 허용목록, 동시 수락 방지, 취소·환불 원장과 상태 롤백을 별도 위협 모델 및 테스트 대상으로 추가한다.
