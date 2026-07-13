# TINY MARKET 개발 전 과정 및 시큐어코딩 보고서

> **제출용 통합 초안 — 개인정보·Public GitHub URL·원격 검사·최종 PDF 증적을 입력하기 전에는 제출하지 않는다.**
> 대괄호로 표시한 `[입력 필요: ...]`와 `[최종 확인 필요]`는 PDF 생성 전에 실제 증적으로 교체한다.

## 표지 정보

| 항목 | 내용 |
|---|---|
| 과제명 | Tiny Second-hand Shopping Platform |
| 프로젝트명 | TINY MARKET |
| 반 | `[입력 필요: XX반]` |
| 이름 | `[입력 필요: 이름]` |
| 전화번호 뒷자리 | `[입력 필요: 4자리]` |
| GitHub Public Repository | `[입력 필요: https://github.com/OWNER/REPOSITORY]` |
| 제출 대상 commit | `[입력 필요: 최종 commit SHA]` |
| release/tag | `[입력 필요: 예: v1.0.0]` |
| 공식 제출 기한 | **2026-07-24(금) 23:59:59** |
| 개인 작업 목표 | **2026-07-13까지 개발 결과와 보고서 초안 완성** |

최종 제출 파일명은 공백 없이 다음 형식을 사용한다.

```text
[WHS][secure-coding][XX반]이름(전화번호뒷자리).pdf
```

공식 제출 기한은 강의 슬라이드의 7월 23일 표기가 아니라 과제 공지에서 정정된 **2026년 7월 24일**이다. 7월 13일은 제출 기한이 아니라, 이틀로 압축한 개인 개발·문서화 목표일이다.

---

## 1. 요약

TINY MARKET은 Django 기반의 교육용 초소형 중고거래 플랫폼이다. 강의 PDF 35페이지의 최소 기능인 회원가입, 상품 등록·조회, 사용자 간 소통, 악성 사용자·상품 차단, 사용자 간 송금, 상품 검색, 관리자 관리를 모두 구현 대상으로 삼았다. 당근의 간단한 지역 거래·앱 내 대화·신고 경험과 번개장터의 전국 검색·세분 필터·거래 기록 장점을 선택적으로 결합했다.

2026-07-13에 사용자가 체크리스트 범위를 PDF 25~29페이지의 상세 시스템 설계 기능으로 정정했다. 해당 페이지를 다시 렌더링·추출하고 코드와 대조한 최초 감사 결과는 14개 중 6 PASS, 3 PARTIAL, 5 FAIL이었다. 이에 공개 사용자 프로필, 소개글·비밀번호 변경 마이페이지, 내 상품 화면, 로그인 회원 전체 채팅, 신고 횟수 기반 상품·사용자 자동조치를 구현했다. 기능 존재 여부와 제출 완료는 구분한다. 현재 로컬 기능 14개는 PASS지만 Public GitHub·clean clone·원격 CI·확장 기능 전체 브라우저 인수·보고서 PDF·지정 파일명·LMS 제출을 마치기 전에는 최종 제출 준비 완료로 표현하지 않는다.

보안은 기능 구현 뒤 덧붙이는 항목이 아니라 요구사항과 설계 단계부터 불변조건으로 정의했다. Django의 세션·CSRF·Form·ORM을 활용해 자체 인증·토큰 구현을 피했고, 객체 소유권·대화 참여자·관리자 세부 권한을 서버에서 다시 검사했다. 상품 이미지는 디코딩 후 메타데이터 없는 JPEG로 재인코딩하며, 송금 요구는 현금화할 수 없는 **DEMO POINT**와 원자적 이중 원장으로 제한했다.

보안 기준은 KISA 공식 게시물에서 확인한 **소프트웨어 개발보안 가이드(2021.12.29)**와 **Python 시큐어코딩 가이드(2023년 개정본)**이다. 사용자 요청의 “2026 시큐어코딩 가이드”라는 표현은 개발 기준연도를 뜻하는 것으로 해석하되, 존재를 확인하지 못한 2026 판본을 임의로 인용하지 않았다. 구현단계 7개 영역·49개 보안약점을 전수 판정했으며 현재 범위에서 37개는 적용, 12개는 기능·언어상 N/A로 분류했다. N/A도 단순 생략하지 않고 관련 기능과 위험 API가 없음을 확인하고, 향후 기능 추가 시 재평가하도록 했다.

마지막 보안 감사에서 인증 시도 동시성, 관리자 권한 상승, 신고 증거 변경, 관리자 이미지 처리 우회, 검증 전 자원 소모 같은 문제를 추가로 발견해 코드를 변경했다. 이후 2026-07-13 사용자 수동 QA에서 이미지 삭제 500과 DEBUG 기술 화면 정보노출을 추가 발견해 SEC-031·032로 등록했다. SEC-031은 `FileField.save_form_data()` 정규화로, SEC-032는 모든 환경의 `SafeExceptionMiddleware`와 오류 template 실패에도 동작하는 standalone fallback으로 수정했다. 이어 기본 이미지 widget이 편집 HTML에 내부 storage filename과 무효 `/_private-media/` 링크를 표시하는 약점을 찾아 `ProtectedListingImageInput`·권한검사 이미지 URL·일반 문구로 바꿨다. 후속 감사에서는 비공개 `PENDING` 후기의 판매자 평균 조기 반영(SEC-042), `/` 구분 전화번호 PII 필터 우회(SEC-043), 오래 열린 Listing Admin 폼의 새 차단 상태 덮어쓰기(SEC-044), multipart 전체 body가 Form 검사 전에 자원을 소비하는 경계(SEC-045)를 추가로 수정·완화했다. 하자 조건부 입력의 stale·모순 상태와 오류·처리 중 피드백 부족(SEC-046)은 조건부 UI, 서버 독립 검증·정규화, 오류 요약·포커스와 제출 잠금으로 보완했다. 마지막 완성도 감사에서는 두 탭 상품 수정의 lost update와 상품 전체 거래·현재 대화 CTA 불일치(SEC-047)를 발견해 hidden revision과 잠근 `updated_at` 비교·409, 다른 거래 CTA·상대 신원 비공개로 완화했다. 업로드 preflight는 거부 파일 객체를 재결합·디코딩하지 않고 안전한 텍스트만 유지하며 사진 재선택을 안내하고, 추가 사진 썸네일·삭제 선택·번호와 대표 승격 안내를 일치시켰다. 상품·메시지·후기 폼도 같은 오류 요약·포커스·native validation·submit lock을 사용한다.

- 2026-07-13 수정 분기 표적 회귀: **관련 8개 테스트 클래스 87개 전부 통과 / 53.390초 / system check 문제 0건**
- 세 확장 기능까지의 직전 비계측 전체 Django tests: **206개 전부 통과 / 114.641초 / system check 문제 0건**
- 직전 Coverage·정적 검사: **206개 / 115.434초, 5,778 statements / 343 miss / 94%, migration drift 없음, Ruff·Bandit·`git diff --check` 문제 0건**
- SEC-042~044 후속 직접 회귀: `market.test_trade_reviews` + `market.tests.ListingAdminSecurityTests` **16개 전부 통과 / 17.393초 / system check 문제 0건**
- SEC-045 multipart 직접 회귀: `config.tests.MultipartUploadLimitTests` **7개 전부 통과 / 0.023초 / system check 문제 0건**
- SEC-042~047 최신 결합 직접 회귀: 다중 이미지·multipart·Listing Admin·거래 후기 4개 class **40개 전부 통과 / 17.697초 / system check 문제 0건 / Ruff PASS**
- 변경 후 전체 Django tests: **219 / 219 전부 통과 / 157.165초 / system check 문제 0건**
- 변경 후 최종 품질 게이트: **coverage 계측 219 / 219 통과 / 162.533초 / 6,037 statements / 354 miss / 94%; Ruff lint PASS·46 files formatted; Bandit 0; pip-audit 알려진 취약점 0; Django check·deploy warning 0; migration 변경 없음; Node JavaScript 구문·`git diff --check` PASS**
- 보존용 2026-07-12 스냅샷: **120개 통과, 3,169 statements / 223 miss / 93%, Ruff/Bandit/pip-audit/deploy 문제 0건**. SEC-031·032와 신규 기능 분기를 포함하지 않은 과거 수치다.

---

## 2. 개발 범위와 진행 방법

### 2.1 개발 원칙

이틀 일정에서 기능 수를 늘리기보다 다음 우선순위를 고정했다.

1. 강의 PDF의 필수 기능과 인수 조건을 먼저 확정한다.
2. 인증·인가·입력검증·데이터 무결성을 기능과 동시에 구현한다.
3. 정상 동작뿐 아니라 악성 입력, 위조 요청, 동시 요청, 실패 후 상태를 시험한다.
4. 실제로 발견한 보안약점만 원인·수정·재시험·잔여위험과 함께 기록한다.
5. 공개 저장소에 비밀정보·DB·업로드·개인정보가 들어가지 않도록 릴리스 단계에서 다시 검사한다.

이 원칙을 택한 이유는 짧은 일정에서 화려한 부가기능을 늘리면 검증하지 못한 공격면이 급격히 커지기 때문이다. 실제 결제, 배송, 지도, 소셜 로그인, 외부 이미지 URL, 전화번호·정확한 주소 수집은 의도적으로 제외했다. 반면 PDF 25~29페이지가 요구한 전체 채팅은 부가기능이 아니라 필수 기능으로 재분류해 제한된 2초 polling으로 구현했다.

### 2.2 이틀 압축 일정

| 일자 | 단계 | 수행 내용 | 완료 기준 |
|---|---|---|---|
| 2026-07-12 | 요구사항 분석 | 첨부 PDF 34~36페이지 확인, 7개 필수 기능과 인수 조건 정의, 당근·번개장터 조사 | REQ-ID와 보안조건 연결 |
| 2026-07-12 | 시스템 설계 | Django 모놀리스, ERD, 권한표, 상태전이, 위협모델, KISA 적용성 판정 | 설계 결정과 선택 이유 기록 |
| 2026-07-12 | 구현 | 계정, 상품, 이미지, 대화, 신고·차단, DEMO POINT, Admin, 보안설정 구현 | 기능별 정상·실패·인가 테스트 작성 |
| 2026-07-12 | UI 재설계 | `#1E3A8A` 디자인 토큰, Flexbox·Grid, 반응형 header·card·button·form 구현 | 외부 UI 의존성 없이 접근성·CSP 유지 |
| 2026-07-13 | 모노크롬 UI 전환·체크리스트 정정 | 검정·흰색·중립 회색 UI, 원색 상품 사진, PDF 25~29페이지 14개 시스템 기능표 | 1440×1000·320×800 실측, 5페이지 원문 대조, 현재 코드 실제 수행본 |
| 2026-07-13 | 상세 기능·보안 보강 | 프로필·마이페이지·내 상품·전체 채팅·3인 신고 임계치, SEC-031·032 수정 | 관련 8개 클래스 87개 표적 회귀와 당시 전체 168개·94% coverage·정적·공급망·deploy 통과 |
| 2026-07-13 | 첨부 UI·보호 widget 보강 | 당시 모노크롬을 유지하고 첨부 영역만 저채도 세이지로 구분, 내부 저장명·무효 링크 비노출 | 당시 `ListingSecurityTests` 26개와 전체 170개·94% 통과; 이후 확장 기능 시점 기준선은 206개·94% |
| 2026-07-13 | 후기·알림·다중 사진·하자 확장 | 실제 거래 신뢰, 탐색 비용, 하자·증거 품질 강화 | 표적 36개, 전체 206개, coverage 94%, SEC-034~041 기록 |
| 2026-07-13 | 웜톤 UI·후속 보안·작성·거래 UX 감사 | 크림·warm-white·테라코타 팔레트, 공개 후기 집계·slash PII·Admin stale overwrite·multipart pre-parser 상한, 조건부 하자, 안전한 upload preflight, 썸네일-삭제 결합, 두 탭 revision 409, 거래 CTA 정합성, 공통 오류·제출 상태 보완 | 1440×1000·320×800 overflow 0·주요 조작 44px, 최신 결합 40개 / 17.697초, 전체 219개 / 157.165초, 최신 coverage 94%와 정적·공급망·deploy·migration 게이트 PASS |
| 2026-07-12~13 | 검토·수정 | 병렬 코드리뷰, 브라우저 QA, 정적·의존성 검사, 발견 약점 수정 | 미조치 Critical/High 0건 목표 |
| 2026-07-13 | 최종 로컬 검증 | 전체 회귀, coverage, lint, Bandit, pip-audit, deploy check, migration·JavaScript·diff·브라우저 보안 흐름 | 전체 219개, coverage 94%, Ruff·Bandit·pip-audit·check/deploy·migration·Node syntax·diff 전부 PASS |
| 2026-07-13 | 릴리스·문서 | clean clone README 재현, Public GitHub, SHA/tag, 보고서 PDF 렌더링 | 로그아웃 공개 확인과 PDF 육안검수 필요 |
| 2026-07-24 이전 | 제출 | 지정 파일명, PDF 링크·내용, 업로드 결과 재확인 | 23:59:59 전 제출 완료 |

---

## 3. 요구사항 분석

### 3.1 과제 필수 기능

| ID | PDF 요구사항 | 인수 조건 | 구현 요소 | 핵심 보안조건 |
|---|---|---|---|---|
| REQ-F001 | 사람들이 플랫폼에 가입 | 정상 가입·로그인·POST 로그아웃, 공개 프로필, 소개글·비밀번호 변경 | `accounts.User`, 가입·로그인·프로필·마이페이지 view | 비밀번호 해시·validators, 공개 필드 allowlist, 현재 비밀번호, 입력·반복시도 제한, 세션 hash 갱신 |
| REQ-F002 | 상품 등록·조회 | 본인 상품 목록·등록·수정·상태 변경·soft delete, 공개 상세 | `Listing`, 내 상품 view, 이미지 guarded endpoint | 판매자 서버 결정, IDOR 차단, 가격·상태 제약, 안전한 이미지 처리·삭제 sentinel 정규화, revision stale 저장 409 |
| REQ-F003 | 사용자끼리 소통 | 상품별 1:1 대화와 로그인 회원 전체 채팅 | `Conversation`, `Message`, `GlobalChatMessage` | 참여자·인증 접근, 발신자 서버 결정, 차단 필터, CSRF·XSS·길이·속도·증분 조회 제한 |
| REQ-F004 | 악성 사용자·상품 차단 | 대화 상대 차단·신고, 상품 신고, 3인 OPEN 신고 자동조치, 관리자 검토·복구 | `UserBlock`, `Report`, moderation service, Admin action | 실제 대화에서 대상 파생, 고유 신고자 원자 집계, 보호 계정, 임시 제재·증거 불변·감사로그 |
| REQ-F005 | 사용자 간 송금 | 잔액 범위 내 DEMO POINT 송금과 거래내역 | `WalletAccount`, `Transfer`, `LedgerEntry` | 원자적 조건부 차감, 멱등키, 이중 원장, append-only |
| REQ-F006 | 상품 검색 | 키워드·카테고리·상태·지역·정렬·페이지 | ORM 검색 view | 길이 상한, 정렬 허용목록, 차단·삭제·정지 판매자 상품 제외 |
| REQ-F007 | 관리자가 모든 요소 관리 | 권한 있는 staff의 조회·신고 처리·차단·정지 | Django Admin | 운영 기본 비활성, 세부 권한, 보호 계정, 원장 읽기 전용 |

#### 3.1.1 PDF 25~29페이지 상세 시스템 기능 감사

25페이지 상세 요구, 26페이지 기능 요약, 27페이지 화면, 28페이지 DB 필드, 29페이지 코드 확인을 14개로 통합했다. 29페이지의 빨간 항목에는 선택이라는 범례가 없으므로 모두 필수로 판정했다.

| 영역 | 최초 감사에서 확인한 공백 | 구현 후 상태·보안 통제 |
|---|---|---|
| 회원 | 공개 프로필, 소개글·비밀번호 변경 마이페이지 | 활성 일반 사용자의 `username`·`bio`만 공개, bio allowlist·500자·escape, 현재 비밀번호·validators·rate·session hash |
| 상품 | 내 상품 UI, 이미지 삭제 500 | `/listings/mine/` 추가, `FileField.save_form_data()`로 유지·삭제·교체 정규화 |
| 소통 | 전체 채팅 | 인증 회원 2초 증분 polling, session sender, CSRF, signed cursor, 길이·송신·조회·DOM 상한, 차단 필터 |
| 신고·제재 | 신고 횟수 기반 자동조치 | 서로 다른 3 OPEN reporter를 원자 집계해 임시 차단·정지, 보호 계정·감사로그·관리자 복구 |
| 화면·DB | 프로필·마이페이지·내 상품·전체 채팅 route와 필드 | `User.bio`, `GlobalChatMessage` migration·화면·Admin 읽기 전용 추가 |

최초 판정 **6 PASS / 3 PARTIAL / 5 FAIL**은 발견 당시 기준선으로 보존한다. 구현 후 관련 8개 테스트 클래스 **87개가 53.390초에 통과**했고, 후속 확장 기능까지 포함한 전체 **206개와 94% coverage**로 통합 영향도 재확인했다. 상세 항목은 `docs/11_CORE_SUBMISSION_CHECKLIST.md`, 실제 수행 증적은 12번 문서에 둔다. Public GitHub와 최종 사용자 인수·PDF 전에는 제출 완료 판정을 내리지 않는다.

### 3.2 문서·제출 요구사항

| ID | 요구사항 | 반영 위치 | 최종 확인 |
|---|---|---|---|
| REQ-D001 | 요구사항 분석부터 유지보수까지 전 과정 보고 | 본 문서와 `docs/00~12` | `[최종 확인 필요]` |
| REQ-D002 | 발견한 보안약점과 변경 내용 설명 | 본 문서 9장, `docs/04_SECURITY_FINDINGS.md` | SEC-001~047·UX-001 동기화; 최신 결합 40개·전체 219개·최종 품질 게이트 통과 |
| REQ-D003 | GitHub Public 저장소 | 표지·15장 | `[공개 URL 입력 및 로그아웃 확인 필요]` |
| REQ-D004 | README 환경 설정·실행 방법 | `README.md` | `[클린 환경 재현 결과 입력 필요]` |
| REQ-D005 | AI 도구 적극 활용 | 본 문서 13장, `docs/05_AI_USAGE_LOG.md` | `[최종 AI 사용 건 갱신 필요]` |
| REQ-D006 | 지정 PDF 파일명과 기한 준수 | 표지·최종 체크리스트 | `[제출 직전 확인 필요]` |

### 3.3 비기능 요구사항

- **보안:** KISA 49개 항목 판정, 최소권한, fail-closed 운영설정, 공급망 무결성.
- **무결성:** 가격·상태·신고 대상·송금 발신자를 클라이언트가 결정하지 못하게 한다.
- **가용성:** 업로드·입력·페이지·계정별 콘텐츠·반복 요청에 상한을 둔다.
- **개인정보 최소화:** 사용자명과 비밀번호 외 전화번호·실명·정확한 위치·금융정보를 수집하지 않는다.
- **재현성:** Python·의존성 버전과 해시를 잠그고 README 명령만으로 설치할 수 있게 한다.
- **감사 가능성:** 신고 처리자·상태·시간과 DEMO POINT 원장을 남기고 사후 수정 경로를 제한한다.
- **접근성·반응형:** 명시적 label, 오류·도움말 ARIA 연결, 모바일에서도 로그아웃 등 안전 기능을 사용할 수 있게 한다.

### 3.4 의도적으로 제외한 범위

- 실제 원화 결제, 카드·은행계좌, 충전·출금·환전, PG·웹훅·에스크로
- 배송사·지도·GPS 동네인증, 전화번호·실명 인증
- 외부 URL 이미지 가져오기, 소셜 로그인, 푸시 알림
- AI 가격추천·정품검수·사기판정
- 별도 주문의 구매요청·승인·거절·취소·환불 상태 머신

이 제외는 최소 요구사항을 축소하기 위한 것이 아니라 검증할 수 없는 외부 비밀키, SSRF, 웹훅 위조, 개인정보, 금융규제, 환불 상태 경쟁조건을 현재 버전에 추가하지 않기 위한 보안 결정이다. 판매자의 `ACTIVE`↔`RESERVED`와 쌍방 후기 자격용 `Trade`에서 구매자 확인에 따른 `SOLD`는 구현했지만, 결제·배송·환불을 포함한 별도 `Order` 시스템을 구현했다고 주장하지 않는다. 전체 채팅은 제외 목록에 포함하지 않고 인증 회원 기능으로 구현했다.

---

## 4. 당근·번개장터 분석과 제품 반영

### 4.1 비교 결과

| 관점 | 당근의 장점 | 번개장터의 장점 | 구조적 단점·주의점 | TINY MARKET 결정 |
|---|---|---|---|---|
| 탐색 | 지역 중심의 간단한 발견 | 전국 단위 카테고리·상세 검색 | 지역만 쓰면 희귀 상품 범위가 좁고, 전국 거래는 비대면 위험이 커짐 | 지역은 선택 텍스트 필터로 제공하고 전체 검색도 허용 |
| 신뢰 | 동네인증·매너 단서·앱 내 대화 | 후기·안전결제·이상거래 탐지·검수 | 평판·인증도 계정 탈취와 선입금 사기를 보증하지 못함 | 불투명 점수 대신 권한, 상태, 신고 증거, 원장 같은 설명 가능한 통제 우선 |
| 소통 | 연락처 노출을 줄이는 앱 내 채팅 | 상품 문의와 거래 흐름 연결 | 외부 메신저·피싱 링크 유도, 제3자 대화 열람 위험 | 상품별 1:1 대화, 참여자 접근통제, sender 서버 결정 |
| 결제 | 채팅 흐름 안 송금 | 에스크로로 선입금 위험 완화 | 수수료·정산 대기·환불 분쟁, 실제 금융정보 부담 | 현금화 불가 DEMO POINT, 수수료 0, 원자적 이중 원장 |
| 운영 | 신고·금지상품 탐지·분쟁조정 | 위해상품 차단·검수·제재 | 자동 필터만으로 금지 상품과 설명 불일치 해결 불가 | 개인 차단+신고+관리자 soft block+처리 상태 기록 결합 |

### 4.2 장점을 선택한 이유

당근에서 가져온 핵심은 “등록과 대화의 마찰이 낮다”는 점이다. 제목, 설명, 가격, 상태, 카테고리, 지역, 선택 이미지로 상품을 등록하고 같은 서비스 안에서 대화하도록 해 연락처 노출을 줄였다. 번개장터에서는 전국 검색에 적합한 카테고리·상태·지역·정렬 필터와 거래 기록의 추적성을 가져왔다.

두 서비스의 기능을 그대로 복제하지 않은 이유는 과제 범위와 보안 보증이 다르기 때문이다. 동네인증이나 안전결제라는 표현은 실제 전화번호·위치 검증과 금융 인프라가 없으면 오해를 만든다. 따라서 지역은 “사용자가 입력한 검색 단서”일 뿐 인증된 위치라고 표시하지 않고, 포인트는 실제 돈이 아니라는 경고를 README와 화면에 반복 표시했다.

### 4.3 단점 보완 방식

- 평판 숫자가 안전을 보장하는 것처럼 보이지 않도록 매너점수 알고리즘을 제외했다.
- 순차 사용자 ID로 아무나 신고·차단하지 못하게 실제 참여 대화에서 상대를 서버가 파생한다.
- 차단·삭제 상품은 기존 대화에서도 제목·가격·이미지·등록시각을 다시 노출하지 않고 비공개 placeholder를 사용한다.
- 상품 설명과 실제 상태 차이는 자동 판정하지 않고 상태·하자 설명, 신고 증거, 관리자 처리 상태를 남긴다.
- 실제 안전결제의 효과를 흉내 내지 않고, DEMO POINT의 무결성과 중복 방지 범위만 명확히 보증한다.

조사 출처와 해석상 주의는 `docs/08_COMPETITOR_ANALYSIS.md`에 기록했다. 회사 자체 발표 수치는 독립 검증된 수치처럼 사용하지 않았고, 소비자원 자료는 특정 회사의 현재 피해율이 아니라 C2C 거래의 구조적 위험을 설명하는 데만 사용했다.

---

## 5. 시스템 설계

### 5.1 아키텍처 선택

REST API·SPA·JWT 대신 Django 서버 렌더링 모놀리스를 선택했다. 이틀 일정에서 브라우저 토큰 저장, CORS, 별도 API 권한 계층을 새로 만들지 않고 Django의 검증된 세션, CSRF middleware, Form, ORM, Admin을 일관되게 사용할 수 있기 때문이다.

```mermaid
flowchart LR
    U["브라우저 사용자"] --> H["HTTPS / 신뢰 프록시 경계"]
    A["관리자 브라우저"] --> H
    H --> M["Security · Session · CSRF Middleware"]
    M --> V["URL / View 객체 권한검사"]
    V --> F["Django Form 입력 허용목록"]
    V --> S["Domain Service / transaction"]
    F --> S
    S --> O["Django ORM + DB 제약"]
    O --> D[("SQLite 개발 DB")]
    S --> P["Private Media 저장소"]
    V --> T["Auto-escaped Django Template"]
    T --> U
    V --> C["Cache 기반 요청 제한"]
    V --> L["마스킹된 보안 로그"]
```

현재 SQLite, LocMemCache, 로컬 파일 저장소는 단일 인스턴스 개발·검증용이다. 실제 운영 전에는 PostgreSQL, 모든 인스턴스가 공유하는 원자 Redis, WSGI/ASGI 서버, TLS 프록시, 백업·모니터링으로 전환해야 한다. 특히 전체 채팅 polling과 신고 임계치가 다중 worker에서도 같은 rate counter·일관된 transaction 경계를 사용하도록 전환 후 부하·경쟁 시험이 필요하다.

### 5.2 모듈 구조

| 영역 | 책임 | 주요 파일 |
|---|---|---|
| `accounts` | 사용자, 가입·로그인·로그아웃, 공개 프로필·마이페이지·비밀번호 변경, 정지, 사용자 차단, 로그인 시도 제한 | `models.py`, `forms.py`, `views.py`, `admin.py` |
| `market` | 상품·검색·이미지, 대화·메시지, 신고, 지갑·송금·원장 | `models.py`, `forms.py`, `views.py`, `services.py`, `admin.py` |
| `community` | 인증 회원 전체 채팅, 증분 polling JSON, 읽기 전용 메시지 Admin | `models.py`, `forms.py`, `views.py`, `admin.py` |
| `config` | 환경설정, URL, 오류 응답, 프록시 신뢰, 보안 헤더 | `settings.py`, `middleware.py`, `views.py` |
| `templates/static` | 서버 렌더링 UI, 접근성·반응형 CSS, 안전한 전체 채팅 DOM 갱신 | `templates/`, `static/css/`, `static/js/` |
| `.github` | CI, CodeQL, Dependabot | workflow와 설정 파일 |
| `docs` | 요구사항·결정·발견 약점·AI·테스트·KISA 증적 | `docs/00~12` |

UI는 새 Tailwind 대신 기존 semantic HTML, CSS Custom Properties, Flexbox와 Grid를 사용했다. 로컬 Tailwind CLI/PostCSS는 Node 빌드·lock·CI 감사 범위를 늘리고, Play CDN은 외부 script와 CSP 예외를 요구하므로 현재 일정에는 둘 다 채택하지 않았다. 초기 감청색과 후속 모노크롬 실험을 거쳐 최종 UI는 크림 canvas `#f7f3ec`, warm-white surface `#fffdfc`, 짙은 갈색 text `#211d19`, 테라코타 primary `#8b3e2a`를 사용하는 웜톤으로 정리했다. 파일을 선택하는 첨부 영역은 저채도 세이지 배경과 짙은 녹색 조작 요소로 범위를 한정해 입력 맥락을 구분한다. 이는 특정 색의 의학적 효능을 단정한 것이 아니라 낮은 채도와 충분한 전경·배경 대비를 선택한 것이다. 상품 색상은 구매 판단 정보이므로 업로드 사진 자체는 원색을 유지하고 오류·성공 상태색도 색과 텍스트를 함께 사용한다. 상품 Grid는 데스크톱 4열에서 900px 3열, 700px 2열, 470px 1열로 바뀌며 주요 form·detail·wallet·chat은 700px 이하에서 1열이 된다.

### 5.3 데이터 모델

```mermaid
erDiagram
    USER ||--o{ LISTING : sells
    USER ||--o{ USER_BLOCK : blocks
    LISTING ||--o{ FAVORITE : receives
    USER ||--o{ FAVORITE : creates
    LISTING ||--o{ CONVERSATION : has
    USER ||--o{ CONVERSATION : buyer_or_seller
    CONVERSATION ||--o{ MESSAGE : contains
    USER ||--o{ MESSAGE : sends
    USER ||--o{ GLOBAL_CHAT_MESSAGE : sends
    USER ||--o{ REPORT : reports
    LISTING o|--o{ REPORT : target
    USER o|--o{ REPORT : target
    USER ||--|| WALLET_ACCOUNT : owns
    WALLET_ACCOUNT ||--o{ TRANSFER : sends_or_receives
    TRANSFER ||--|{ LEDGER_ENTRY : posts
    WALLET_ACCOUNT ||--o{ LEDGER_ENTRY : records
```

`LoginAttempt`는 계정·네트워크 제한 상태를 저장하지만 User 외래키나 원문 사용자명·IP를 저장하지 않고 HMAC 식별자만 보관하므로 ERD의 사용자 관계선에서 의도적으로 제외했다.

핵심 DB 불변조건은 다음과 같다.

- 사용자명은 소문자 정규화 후 대소문자 무관 유일하다.
- 공개 소개글은 최대 500자이며 공개 view는 사용자명·소개글만 조회한다.
- 정지 사용자는 동시에 활성 상태일 수 없다.
- 자기 자신 차단·대화, 동일 사용자 차단 중복을 허용하지 않는다.
- 상품 가격은 100~100,000,000 범위다.
- 신고 대상은 사용자와 상품 중 정확히 하나다.
- 같은 reporter와 대상의 OPEN 신고는 조건부 유일하고 자동 임계치는 서로 다른 reporter만 센다.
- 전체 채팅 메시지는 인증된 sender와 최대 1,000자 body를 가지며 일반 update/delete route가 없다.
- 사용자 지갑은 사용자당 하나이며 발행 지갑과 구분된다.
- 송금 계정은 서로 달라야 하고 멱등키 조합은 유일하다.
- 한 송금의 같은 계정 분개 중복을 막고 0 delta를 허용하지 않는다.

“한 송금에 정확히 두 분개이며 합계가 0”이라는 다중 행 조건은 이식 가능한 단일 CHECK로 표현하기 어렵다. 따라서 원자적 게시 service를 유일한 생성 경계로 두고, 운영 시 reconciliation이 분개 수·합계·지갑 cache를 독립 검증하도록 설계했다.

### 5.4 권한 매트릭스

| 기능 | 비회원 | 일반 사용자 | 소유자/참여자 | 권한 있는 staff | superuser |
|---|:---:|:---:|:---:|:---:|:---:|
| 공개 상품 검색·상세 | 허용 | 허용 | 허용 | 허용 | 허용 |
| 공개 일반 사용자 프로필 | 허용 | 허용 | 허용 | 허용 | 허용 |
| 마이페이지·비밀번호·내 상품 | 거부 | 본인만 허용 | 본인만 허용 | 일반 사용자 규칙 | 일반 사용자 규칙 |
| 상품 등록 | 거부 | 허용 | 허용 | 일반 사용자 규칙 | 허용 |
| 상품 수정·삭제·상태 | 거부 | 타인 상품 거부 | 판매자만 허용 | Admin의 별도 제한 | 허용 |
| 대화 열람·메시지 | 거부 | 무관 대화 거부 | 구매자·판매자만 허용 | 참가자가 아니면 거부 | 참가자가 아니면 거부 |
| 전체 채팅 열람·송신 | 거부 | 허용 | 허용 | 활성 계정이면 허용 | 활성 계정이면 허용 |
| 사용자 신고·차단 | 거부 | 실제 대화 상대만 | 허용 | 동일 규칙 | 동일 규칙 |
| 비공개 상품 열람 | 거부 | 거부 | 판매자만 제한 허용 | `market.view_listing` 필요 | 허용 |
| 신고 처리 | 거부 | 거부 | 거부 | `market.change_report` 필요 | 허용 |
| 상품 차단 action | 거부 | 거부 | 거부 | 위 권한 + `market.block_listing` | 허용 |
| 사용자 정지 action | 거부 | 거부 | 거부 | 위 권한 + `accounts.suspend_user` | 허용 |
| 상품 영구 삭제 | 거부 | 거부 | 거부 | `market.delete_listing` + `market.purge_listing` | 허용 |
| 원장 수정·삭제 | 거부 | 거부 | 거부 | 거부 | ORM 경로에서도 거부 |

관리자 화면에서 action을 숨기는 것만으로는 권한통제가 되지 않는다. 공격자가 action 이름을 직접 POST할 수 있으므로 실행 함수 내부에서 대상 모델 권한을 다시 검사한다. 일반 `change_user` 권한과 계정 정지 권한을 분리해 제한된 운영자가 staff·superuser·그룹·권한 또는 정지 상태를 직접 편집하지 못하게 했다.

### 5.5 상품 상태 전이

```mermaid
stateDiagram-v2
    [*] --> ACTIVE
    ACTIVE --> RESERVED: 판매자 예약
    RESERVED --> ACTIVE: 판매자 예약 해제
    ACTIVE --> SOLD: 구매자 완료 확인
    RESERVED --> SOLD: 구매자 완료 확인
    ACTIVE --> DELETED: 판매자 soft delete
    RESERVED --> DELETED: 판매자 soft delete
    ACTIVE --> BLOCKED: 관리자 조치 또는 3인 자동 임시조치
    RESERVED --> BLOCKED: 관리자 조치 또는 3인 자동 임시조치
    SOLD --> BLOCKED: 관리자 조치 또는 3인 자동 임시조치
    BLOCKED --> ACTIVE: 자동차단 복구, 진행 거래 없음
    BLOCKED --> RESERVED: 자동차단 복구, 완료 대기 거래
    BLOCKED --> SOLD: 자동차단 복구, 완료 거래
```

판매자가 직접 바꿀 수 있는 상태는 `ACTIVE`↔`RESERVED`뿐이다. `SOLD`는 판매자가 상품 상태 버튼으로 정하지 않고, 상품에 묶인 1:1 대화에서 판매자가 완료를 요청한 뒤 해당 구매자가 확인했을 때만 거래 서비스가 설정한다. 완료된 거래가 있으면 상품 수정·삭제·재판매·새 대화 같은 일반 mutation을 모두 거부한다. 수정·삭제·Admin 저장 때 DB에서 현재 행을 다시 읽고 소유자·최신 상태·차단 metadata를 검사해 오래된 POST가 관리자 또는 자동 moderation의 차단을 되돌리지 못하게 했다. 일반 수정 폼은 hidden revision과 잠근 최신 `updated_at`도 비교해 두 탭의 제목·가격·하자 lost update를 409로 거부하고 알림 event 근거를 보호한다. 기존 호환상 revision 누락 소유자 요청은 강제 거부하지 않으므로 API화할 때 필수 revision/`If-Match`가 필요하다. SQLite의 `select_for_update()` 한계 때문에 실제 다중 사용자 운영 전 PostgreSQL에서 경쟁 부하 시험을 다시 해야 한다.

### 5.6 위협 모델과 신뢰경계

보호할 자산은 비밀번호 해시·세션, 사용자·상품·대화·신고, 관리자 권한, DEMO POINT 잔액·원장, `SECRET_KEY`와 배포설정이다. 주요 공격자는 익명 자동화 공격자, 인증된 악성 사용자, 과도한 권한을 가진 staff, 위조 전달 헤더를 보내는 직접 연결자, 취약·변조 의존성으로 가정했다.

주요 위협과 설계 통제는 다음과 같다.

- IDOR·Mass Assignment → UUID와 서버 세션·URL 문맥, 객체 소유자·참여자 재검사, Form 허용목록
- SQLi·XSS·CSRF → ORM, autoescape, `safe` 금지, CSRF middleware, 상태 변경 POST
- 파일 위장·메타데이터·폭탄 → 크기·픽셀·프레임·실제 형식 확인 후 JPEG 재인코딩
- brute force·자원 고갈 → 계정+네트워크 인증 제한, 기능별 rate/quota, 입력 길이·페이지 상한
- 이중 지출·중복 송금 → 조건부 debit, transaction, 멱등키, 이중 원장
- 관리자 권한 상승 → 전용 권한, 보호 계정, action 내부 재검사, 증거 필드 readonly
- 프록시 헤더 위조 → 직접 peer가 신뢰 IP일 때만 XFF/XFP 사용, 잘못된 운영설정은 시작 거부
- 공급망 변조 → 버전·SHA-256 해시 lock, 최소권한·SHA pin CI, CodeQL, Dependabot

### 5.7 사용자 요청 확장 기능 설계

세 기능은 기존 상품·검색·대화를 확장하되 각각 별도 신뢰경계를 둔다.

| 기능 | 추가 이유 | 권한·데이터 설계 | 핵심 불변조건 |
|---|---|---|---|
| 거래 완료 쌍방 후기 | 실제 거래 경험만 신뢰 판단에 사용 | 상품·buyer·seller가 고정된 `Conversation`에 묶인 `Trade`, 방향별 `Review`; 상품 전체 활성 거래와 현재 대화 거래 분리 | 판매자 요청+해당 구매자 확인, 다른 대화 진행 시 CTA·상대 신원 비공개, 현재 대화 거절·취소 기록, 완료 전 작성 금지, 양측 각 1건, 두 후기 동시 공개, `PUBLIC`만 개수·평균 집계 |
| 관심 검색·가격 하락 알림 | 반복 탐색 비용과 가격 변경 누락 감소 | 정규화 `SavedSearch`, 구조화 `ListingEvent`, 수신자별 `Notification` | 이벤트 이후 구독 비소급, 수신자+이벤트 1건, 차단·정지·판매자 제외, 현재 비공개 정보 숨김 |
| 다중 사진·하자 | 상품 상태 설명력과 신고 증거 강화 | 대표 1장+`ListingImage` 4장, 보호 썸네일-삭제 checkbox 결합, 허용목록 `ListingDefect`, `ReportImageEvidence` | client 5장·5MiB/장·20MiB 보조 검사, 서버 preflight 파일 미결합·6파일 generic 400, 부모-자식 인가, hidden revision 409, 실패 파일 정리, 신고 당시 전 사진 SHA와 하자 snapshot |

후기 자격은 `Listing.SOLD`가 아니라 특정 대화의 `Trade.COMPLETED`만 근거로 삼는다. 판매자 단독 상태 변경은 구매자를 증명하지 못하기 때문이다. 다른 대화에서 거래가 진행 중이면 그 사실만 일반 문구로 알리고 완료 CTA와 상대 식별정보는 노출하지 않는다. 알림은 자유 문구를 저장하지 않고 사실 이벤트를 저장해 중복·XSS·비공개 전환을 다룬다. 다중 이미지는 파일 수만 늘리지 않고 업로드 전체 자원 제한, 거부 파일 비결합, 썸네일-삭제 선택의 직접 결합, 동시 수정 revision, storage rollback, 신고 증거 수명주기를 함께 설계했다.

---

## 6. 구현 내용과 선택 이유

### 6.1 회원가입·인증

사용자명은 Unicode 정규화·공백 제거·소문자 저장을 하고 DB에서 대소문자 무관 유일성을 보장한다. 공개 가입 Form은 사용자명과 비밀번호만 받으며 `is_staff`, `is_superuser`, 그룹, 권한, 정지 상태를 받지 않는다. 비밀번호는 Django 표준 hasher와 검증기를 사용하고 최소 12자, 흔한 비밀번호, 숫자 전용, 사용자명 유사성을 검사한다.

일반 로그인과 Admin 로그인은 계정 HMAC과 네트워크 HMAC 범위를 함께 사용한다. 계정별 5회/15분, 네트워크별 원시도 30회/15분이며, 성공 시 해당 account 상태만 지우고 network 누적은 유지한다. 비밀번호 해시 전에 짧은 cache·DB 예약만 수행하고 hash 중에는 transaction이나 행 잠금을 유지하지 않는다. 계정 존재 여부와 무관하게 입력 사용자명의 ACCOUNT HMAC을 동일한 DB 경로로 처리하며, network 30회 상한으로 IP당 15분 window의 신규 ACCOUNT 행을 최대 30개로 제한한다. 만료 후 30분이 지난 행은 정리한다. 사용자명 150자·비밀번호 256자 상한도 고비용 인증 전에 검사하고 오류는 계정 존재 여부를 구분하지 않는다.

계정별 제한은 알려진 계정에 대한 표적 잠금 DoS 가능성과 brute force 방어 사이의 절충이다. 운영에서는 공유 Redis, 프록시·WAF 제한, 관리자 MFA와 위험 기반 지연을 함께 적용해야 한다.

공개 프로필은 활성·비정지·비staff·비superuser 계정만 조회하며 `User` 객체 전체를 template에 넘기지 않고 `username`과 최대 500자 `bio` primitive만 전달한다. 마이페이지의 `ProfileForm`은 `bio`만 허용하고 저장도 해당 필드만 명시해 forged `is_staff`, `is_superuser`, 이메일, 정지 상태를 무시한다. 비밀번호 변경은 현재 비밀번호를 요구하는 Django `PasswordChangeForm`과 기존 validators를 재사용한다. 256자 초과 입력은 hash 전에 거부하고 사용자별 시간당 10회로 제한하며, 성공하면 `update_session_auth_hash()`로 현재 로그인 세션을 안전하게 갱신한다. 범용 `UserChangeForm`과 자체 비밀번호 비교·hash는 과도한 필드 노출과 암호 구현 위험 때문에 사용하지 않았다.

### 6.2 상품·검색·이미지

판매자는 요청의 `seller` 필드를 신뢰하지 않고 로그인 세션에서 결정한다. 가격·제목·설명·지역 길이를 Form과 DB 제약으로 확인하고, 검색 정렬값은 허용목록에서만 선택한다. 공개 queryset은 `BLOCKED`, `DELETED`, 정지·비활성 판매자의 상품을 제외한다. 로그인 판매자는 `/listings/mine/`에서 자신의 삭제 전 상품을 페이지 단위로 찾을 수 있어 상세·수정·상태 관리 경로를 우회 URL 없이 사용할 수 있다.

이미지는 JPEG·PNG·WebP만 허용하며 최대 5MB, 1,200만 픽셀, 단일 프레임을 적용한다. 확장자나 `Content-Type`만 믿지 않고 Pillow로 실제 바이트를 디코딩·검증한다. EXIF 방향을 반영한 뒤 메타데이터 없는 RGB JPEG로 다시 인코딩하고 UUID 파일명을 부여한다. 미디어 디렉터리를 정적 공개하지 않고 인가된 view만 `image/jpeg`, `nosniff`, `private, no-store`로 응답한다. 교체·삭제는 transaction commit과 파일 생명주기를 맞추고 실패한 새 파일을 정리하되 신고 snapshot이 참조한 파일은 private storage에 보존한다. 익명 공개 HTML을 포함한 모든 동적 응답도 `private, no-store`·`Pragma: no-cache`로 보내 차단 전 metadata의 브라우저·공유 proxy cache 재노출을 막는다.

파일 input의 `accept="image/jpeg,image/png,image/webp"`와 “5MB 이하·1,200만 픽셀 이하” 안내는 사용자가 올바른 파일을 선택하도록 돕는 UX일 뿐 공격자가 우회할 수 있는 클라이언트 힌트다. 따라서 이를 서버 검증의 대체물로 사용하지 않고 위 디코딩·형식·크기·픽셀·재인코딩 검사를 그대로 유지한다. 편집 화면은 기본 `ClearableFileInput` 대신 `ProtectedListingImageInput`을 사용한다. 기존 파일은 내부 storage filename이나 `MEDIA_URL`을 렌더링하지 않고, 기존 `listing_image` 권한검사 URL의 미리보기와 일반 문구·삭제 checkbox만 제공한다.

추가 사진은 보호된 썸네일, 대표 사진부터 이어지는 번호와 해당 삭제 checkbox를 하나의 label에 직접 결합해 사용자가 선택 대상을 오인하지 않게 했다. 대표 사진 삭제를 선택하면 남은 첫 추가 사진이 대표로 승격된다는 결과도 화면에 설명한다. 브라우저 JavaScript는 기존·삭제·새 선택을 합친 최종 5장, 신규 파일 장당 5MiB와 합계 20MiB를 제출 전에 검사하지만, 이 값은 신뢰하지 않고 서버가 다시 판단한다.

SEC-031의 원인은 잠근 최신 Listing으로 값을 복사할 때 `ClearableFileInput`의 삭제 sentinel `False`를 파일 객체처럼 직접 대입한 것이었다. 수정 후 text field는 기존 허용목록으로 복사하고 image는 Django `FileField.save_form_data()`에 전달한다. framework가 삭제를 빈 파일명으로 정규화하므로 기존 이미지 유지·삭제·교체를 구분하면서 boolean의 `.name` 500을 없애고 기존 transaction·commit 파일 정리 의미도 유지한다.

운영 reverse proxy/Nginx가 `MEDIA_ROOT` 또는 `/_private-media/`를 정적 alias로 직접 서빙하면 guarded endpoint와 신고 증거 비공개를 우회한다. 따라서 두 경로를 절대 외부에 직접 노출하지 않고 모든 이미지 요청을 Django의 권한검사 이미지 view로만 통과시킨다.

다중 이미지 Form의 20MB 검사는 CSRF가 `request.POST`를 파싱한 뒤에야 실행될 수 있으므로 단독 자원 통제로 충분하지 않다. `MultipartUploadLimitMiddleware`를 CSRF보다 앞에 두어 multipart POST·PUT·PATCH의 알려진 21MiB 초과 길이는 body read 전 거부하고, 길이가 누락·chunked·축소된 경우에는 첫 upload handler가 여러 파일의 실제 chunk를 요청 단위로 누적해 같은 상한을 적용한다. 초과 응답은 내부 예외명·설정값 없이 일반 400과 보안 헤더를 사용한다. reverse proxy가 Django 전에 body를 수신하는 비용은 proxy body/time/connection limit으로 별도 통제해야 한다.

허용하지 않은 파일 field나 합계 preflight가 실패하면 거부 파일 객체를 `ListingForm`에 다시 bind하거나 디코딩하지 않는다. 길이 상한을 통과한 제목·설명 등 안전한 텍스트만 같은 폼에 유지하고 브라우저 보안상 사진은 다시 선택해야 함을 명확히 알린다. 전역 `DATA_UPLOAD_MAX_NUMBER_FILES=5`를 넘긴 6파일 위조는 view에 도달하기 전에 Django parser의 진단 없는 일반 400으로 종료한다. 수정 폼은 GET 시 `updated_at` microseconds 기반 hidden revision을 발급하고, POST transaction에서 잠근 최신 revision이 다르면 409로 전체 저장을 거부해 제목·가격·하자·파일과 가격 하락 event 근거의 lost update를 막는다.

공개 view뿐 아니라 Django Admin의 상품 Form도 같은 이미지 sanitizer를 사용한다. Admin을 별도 우회 업로드 경로로 남기지 않았고, 상품 추가를 비활성화하며 판매자·상태·차단 메타데이터는 action 또는 제한된 경로로만 변경한다. Admin 변경 직전 현재 Listing 행을 잠가 다시 읽고, 이미 purge된 상품의 stale 객체 저장을 거부한다. 또한 폼을 연 뒤 새로 바뀐 seller·status·차단 처리자·사유·시각이 하나라도 다르면 stale 저장을 거부하고, 일치할 때도 명시한 편집 가능 필드만 최신 잠금 객체에 복사한다.

### 6.3 대화·차단·신고

1:1 대화는 임의 사용자끼리 만드는 범용 DM이 아니라 **특정 상품·구매자·판매자 조합**에 묶인다. 같은 조합의 대화는 한 개만 생성되며, 제3자는 UUID를 알아도 접근할 수 없다. 발신자는 POST 값이 아니라 세션 사용자이고 차단 관계가 생기면 새 메시지와 송금을 막는다. 대화 목록은 30개씩 페이지네이션하고 마지막 메시지를 Subquery annotation으로 조회해 N+1 쿼리를 줄였다.

한 상품에 여러 구매자 대화가 있을 수 있으므로 상품 전체의 진행·완료 거래와 현재 대화의 거래를 구분한다. 다른 대화에서 완료 확인이 진행 중이면 현재 대화에는 완료·후기 CTA를 보이지 않고 “다른 거래가 진행 중”이라는 일반 안내만 제공해 상대 구매자 신원을 공개하지 않는다. 현재 대화에서 완료 요청이 거절 또는 취소되었다면 최신 닫힘 상태와 시각을 보여 사용자가 다음 행동을 이해하게 한다. 실제 상태 변경 service는 기존 참여자·거래 상태·UNIQUE 검증을 계속 수행한다.

PDF의 전체 채팅은 WebSocket/SSE 장기 연결 대신 2초마다 새 메시지만 가져오는 인증 HTTP polling으로 구현했다. 즉 새로고침 없이 갱신되지만 엄밀한 즉시 전달이 아니라 최대 약 2초 지연의 **near-real-time**이다. 현재 동기식 Django에 channel layer·연결 coordinator를 추가하지 않고 기존 세션, CSRF, cache rate limit, 보안 헤더를 재사용해 검증 가능한 범위를 유지하기 위해서다. cursor는 서명하고 응답은 최대 100건, 초기 50건이며 사용자별 조회 분당 40회·송신 10회, 본문 1,000자로 제한한다. 브라우저는 hidden tab에서 polling을 멈추고 오류 시 backoff하며 이전 요청과 겹치지 않고 DOM 메시지를 200개 이하로 유지한다. JSON의 사용자 입력은 `innerHTML`이 아니라 `textContent`로 새 노드에 넣는다. 차단 관계는 양방향으로 숨기고 정지·비활성 발신자 메시지도 조회하지 않는다. trade-off는 사용자 수에 비례한 polling 부하다.

사용자 신고와 차단은 순차 사용자 ID를 신뢰하지 않고, 사용자가 실제 참여한 대화에서 상대방을 서버가 계산한다. 상품 신고는 현재 공개 가능한 상품 문맥에서만 허용한다. 신고 대상은 사용자·상품 중 정확히 하나여야 하며 중복·일일 생성도 제한한다.

상품 신고 transaction은 상품 행을 잠그고 신고 시점의 제목·설명·가격·분류·상태·이미지 저장명과 SHA-256을 Report snapshot에 고정한다. 이미지 저장명에는 참조 조회용 DB index를 둔다. snapshot이 참조한 이미지는 교체·soft delete·Admin purge 뒤에도 공개 route 없는 private storage에 남겨 판매자 글을 동결하지 않으면서 원 증거를 보존한다. 보존 이미지 Admin endpoint는 `view_report` 권한을 재검사하고 매 요청 SHA-256을 상수시간 비교한다. 누락·과대·변조 파일은 404로 거부하고, 정상 응답은 `private, no-store`·`nosniff`이며 actor/report 열람 로그를 남긴다.

신고 원문은 분쟁·감사 증거이므로 Admin에서 reporter, 대상, category, details, 상태·처리자·시각을 직접 편집하거나 추가·삭제할 수 없게 했다. 상태 변경과 차단·정지는 권한을 재검사하는 action으로만 수행한다. staff·superuser도 대화 상대에 의해 신고될 수 있어 증거는 보존하되, 자동·일괄 정지 action은 자신·staff·superuser를 건너뛴다.

동일 대상에 대해 서로 다른 신고자 3명의 `OPEN` 신고가 접수되면 신고 저장 transaction 안에서 대상을 잠그고 자동 임시조치를 수행한다. 상품 판매자와 사용자 자신의 신고는 집계에서 제외하고 조건부 UNIQUE가 한 reporter의 중복 OPEN 신고를 막는다. 상품은 영구삭제하지 않고 `BLOCKED`, 일반 사용자는 `is_suspended=True`·`is_active=False`로 바꾸며 자동 사유·시각과 보안로그를 기록한다. staff·superuser는 자동 정지하지 않는다. 권한 있는 관리자는 자동 사유로 차단된 상품만 복구하고 관련 OPEN 신고를 `DISMISSED`로 바꿀 수 있다. 공모·오탐을 곧바로 영구 삭제로 연결하지 않고 사람의 검토·복구 가능성을 남긴 결정이다.

### 6.4 DEMO POINT 송금

가입 시 100,000P를 발행하지만 실제 화폐·예금·전자지급수단이 아니다. 충전·출금·환전·현금화·구매자 보호를 제공하지 않으며 금융정보를 받지 않는다.

송금은 다음 순서로 하나의 transaction에서 수행한다.

1. 송신·수신 사용자의 현재 활성 상태와 차단 관계를 다시 확인한다.
2. 같은 사용자의 멱등키가 이미 있으면 완전히 같은 요청만 기존 결과로 반환한다.
3. `balance >= amount` 조건부 UPDATE가 정확히 한 행을 차감했는지 확인한다.
4. 수신 지갑을 가산하고 Transfer를 기록한다.
5. 송신 음수·수신 양수 LedgerEntry 두 건을 만들고 합계 0을 확인한다.
6. 중간 실패 시 전체를 rollback한다.

`Transfer`와 `LedgerEntry`는 게시 후 instance `save/delete`, QuerySet `update/delete/bulk_update`, upsert형 bulk operation을 모델 계층에서 거부한다. 정정은 기존 행을 덮어쓰는 대신 향후 별도 반전 거래로 표현한다. 단, DB 관리자 직접 SQL은 ORM 통제를 우회하므로 운영 DB 최소권한과 독립 감사가 필요하다.

### 6.5 관리자와 운영설정

운영(`DEBUG=false`)에서는 Admin URL을 기본 비활성화하고 명시적 환경변수로만 활성화한다. 신고 상태 변경, 상품 차단, 사용자 정지를 `change_report`, `block_listing`, `suspend_user`로 분리하고 상품 영구 삭제는 `delete_listing`과 `purge_listing`을 모두 요구한다. 자동 차단 상품 복구도 `change_report`와 `block_listing`을 모두 요구한다. 신고 처리·차단·정지·복구 action은 관련 행을 transaction에서 잠그고 현재 상태를 다시 확인한 뒤 실행한다. 제한된 사용자 관리자는 일반 사용자 정보 일부를 볼 수 있어도 staff·superuser·그룹·권한·정지 상태를 forged POST로 변경할 수 없고, staff·superuser 대상 변경도 거부된다. 신고·메시지·대화·전체 채팅·사용자 행동·로그인 시도·원장은 read-only evidence로 관리한다.

설정은 다음 조건에서 fail-closed로 시작을 거부한다.

- 운영에서 `DEBUG=true`
- 운영 `SECRET_KEY` 누락, 50자 미만, 낮은 문자 다양성 또는 알려진 비안전 prefix
- 운영 `ALLOWED_HOSTS` 누락 또는 wildcard
- 운영 HTTPS redirect 비활성
- HTTPS 프록시 모드인데 신뢰 프록시 IP가 없음
- boolean 환경변수에 지원하지 않는 값 입력

개발 SECRET_KEY는 커밋된 고정값 대신 프로세스 시작 때 임시 생성해 재사용 비밀 노출을 막는다. 그 결과 개발 서버 재시작 시 세션이 무효화되는 것은 의도한 동작이다. 운영에서는 1년 HSTS, Secure·HttpOnly·SameSite 쿠키, frame deny, `nosniff`, same-origin referrer, CSP와 Permissions-Policy를 적용한다. Admin 호환 때문에 Admin 경로 CSP에는 제한적 inline 예외가 있으며 잔여위험으로 관리한다.

### 6.6 오류 처리와 정보 비노출

운영 `DEBUG=false` 시작 강제에 더해 `SafeExceptionMiddleware`를 개발·운영 모두에 적용했다. 처리되지 않은 예외와 예상된 `SuspiciousOperation`·`PermissionDenied`·`Http404`를 비진단 500·400·403·404로 응답하고, DEBUG의 resolver 404도 URL pattern을 나열하지 않는다. exception 객체, 요청 본문, 절대경로는 응답이나 보안 로그에 보간하지 않고 고정 event만 남긴다. 정상 validation 400, method 405, rate-limit 429, resolved JSON 404는 원래 status와 형식을 유지한다.

오류 template도 base template·context processor·static lookup·URL reverse 때문에 실패할 수 있다. `_standalone_error_response()`는 request·exception data와 template engine에 의존하지 않는 코드 상수의 최소 HTML을 반환한다. SecurityHeadersMiddleware는 이 fallback에도 CSP, `nosniff`, frame `DENY`, `private, no-store`를 적용한다. 발표 때 환경변수를 기억하는 절차만 믿지 않고 application 경계에서 심층 방어를 추가한 이유다.

### 6.7 쌍방 후기·알림·다중 사진과 하자 구현

- 판매자가 상품에 묶인 1:1 대화에서 완료를 요청하면 필요 시 `ACTIVE` 상품을 `RESERVED`로 두고, 해당 구매자가 확인하면 `Trade.COMPLETED`와 `Listing.SOLD`를 같은 transaction에 기록한다. 판매자의 일반 상태 POST는 `ACTIVE`↔`RESERVED`만 허용한다. 거절·취소는 시작 상태로 복구하고, 완료 거래 상품의 수정·삭제·재판매·새 대화를 서버에서 차단한다.
- 상품 전체 활성 거래가 현재 conversation과 다르면 완료·후기 CTA와 상대 신원을 숨기고, 현재 conversation의 최근 거절·취소만 기록·표시한다. 화면 은닉만 믿지 않고 service의 참여자·상태·UNIQUE 경계도 유지한다.
- 후기의 거래·방향·작성 대상·공개 상태는 POST에서 받지 않고 로그인 사용자와 거래 참여자로 파생한다. 첫 후기는 `PENDING`, 둘째 제출 transaction에서 양쪽을 `PUBLIC`으로 바꾼다. 공개 프로필과 상품 상세의 개수·평균도 `PUBLIC`만 집계해 첫 제출 여부와 평점이 aggregate로 새지 않게 한다. 본문은 500자, 1~5점, 일 10회이며 slash 구분을 포함한 전화번호·이메일·URL·긴 숫자 패턴을 거부하고 템플릿 autoescape를 유지한다.
- 저장 검색은 NFKC·공백·casefold 뒤 fingerprint로 중복을 막고 계정당 20개로 제한한다. 새 상품과 잠긴 old/new 가격의 실제 인하만 이벤트로 만들며 이벤트 이전에 존재한 검색·찜만 대상으로 한다. fan-out은 commit 후 실행하고 실패한 pending 이벤트는 `process_listing_events --limit N`으로 수동 재처리할 수 있다.
- 업로드 요청은 Pillow 처리 전 허용 field, 대표 포함 최대 5장, 합계 20MB를 검사한다. preflight 실패 파일은 폼에 재결합·디코딩하지 않고 텍스트만 유지하며 재선택을 안내한다. 각 파일은 5MB·12MP·JPEG/PNG/WebP·단일 프레임 확인 후 metadata 없는 JPEG로 재인코딩한다. 추가 사진 썸네일·번호·삭제 checkbox를 직접 결합하고 대표 삭제 시 첫 추가 사진 승격을 안내한다. stale·타 상품 자식 UUID는 거부하며 SQL 실패 뒤 request-created 파일을 정리한다. hidden revision과 잠근 최신 `updated_at` 불일치는 409로 전체 저장을 멈춘다.
- 하자 상태와 8개 코드는 허용목록이다. `PRESENT`일 때만 체크리스트·상세를 화면에 표시·활성화하고 `OTHER` 상세를 native required로 안내한다. 비-`PRESENT` 변경 시 브라우저 입력을 비활성화·초기화하지만 이를 보안 경계로 신뢰하지 않는다. 서버는 `PRESENT` 코드 필수·비-`PRESENT` code 거부·허용목록을 독립 검증하고 정상 비-`PRESENT`의 stale 상세는 빈 값으로 정규화한다. 상품·메시지·후기 폼은 공통 오류 요약·입력 링크·요약 포커스, native validation과 유효 제출의 `aria-busy`·disabled·진행 문구를 사용한다. 신고 시 전 사진의 순서·저장명·SHA-256과 하자 상태·코드·설명을 snapshot하고, 관리자 열람은 Report 권한·부모 관계·digest를 재검사하며 내부 저장명을 HTML에 표시하지 않는다.

---

## 7. KISA 시큐어코딩 기준 적용

### 7.1 기준 문서

- [KISA 소프트웨어 개발보안 가이드 게시물](https://www.kisa.or.kr/2060204/form?lang_type=KO&page=1&postSeq=5) — 확인 판본 2021.12.29
- [KISA Python 시큐어코딩 가이드 게시물](https://www.kisa.or.kr/2060204/form?lang_type=KO&menuSeq=4135&page=&postSeq=13) — 2023년 개정본
- [KISA 소프트웨어 보안약점 진단가이드 게시물](https://www.kisa.or.kr/2060204/form?lang_type=KO&page=1&postSeq=9)

### 7.2 49개 항목 판정 요약

| KISA 영역 | 전체 | 적용(A) | N/A | 주요 구현 증적 |
|---|---:|---:|---:|---|
| 입력데이터 검증 및 표현 | 17 | 10 | 7 | ORM, autoescape, CSRF, 이미지 재인코딩, 길이·가격·정렬 허용목록 |
| 보안기능 | 16 | 14 | 2 | 인증·인가, 비밀번호, 환경비밀, HTTPS·쿠키, 반복시도 제한, hash lock |
| 시간 및 상태 | 2 | 2 | 0 | 조건부 debit, 멱등성, stale 상품 재검사, pagination·quota |
| 에러처리 | 3 | 3 | 0 | 일반 오류화면, fail-closed, transaction rollback, 구체 예외 |
| 코드오류 | 5 | 3 | 2 | None 처리, 파일 자원 정리, 신뢰 불가 역직렬화 금지 |
| 캡슐화 | 4 | 4 | 0 | 세션별 데이터 경계, DEBUG/Admin 통제, 내부 상태 보호 |
| API 오용 | 2 | 1 | 1 | 위험 API 금지, 지원 버전·해시 lock, Bandit·pip-audit·CodeQL |
| **합계** | **49** | **37** | **12** | 상세 근거: `docs/07_KISA_BASELINE.md` |

N/A 예시는 XML·LDAP·전자서명·외부 TLS 요청·사용자 URL 서버 호출·자체 C 메모리 관리다. 현재 기능과 의존성이 없어 비적용이지만 `eval/exec`, shell, pickle, XML parser, `verify=False`, 외부 HTTP 호출 같은 금지 패턴을 검색해 기능 부재를 보조 확인한다. 향후 해당 기능을 추가하면 N/A를 자동으로 유지하지 않고 위협모델과 테스트를 다시 작성한다.

### 7.3 설계단계 적용

구현 체크리스트 외에도 설계 단계에서 입력·DB 조회·시스템 자원·웹 요청·HTTP·업로드 파일 검증, 인증·인가·비밀번호·반복시도, 중요정보 저장·전송, 예외·세션 통제를 산출물에 포함했다. 각 통제는 요구사항 ID, 구현 파일, 테스트 또는 수동 증적과 연결해 “가이드 준수”를 선언만 하지 않도록 했다.

---

## 8. 보안 구현의 핵심 불변조건

1. 요청이 보낸 `seller`, `sender`, `reporter`, 신고 사용자, 송금 발신자, 권한 필드는 신뢰하지 않는다.
2. 모든 객체 접근은 로그인 여부만이 아니라 소유자·대화 참여자·세부 권한을 다시 확인한다.
3. 상태 변경은 POST+CSRF이며 허용 상태 전이만 수행한다.
4. 보안·자원 제한은 가능한 한 고비용 Form 검증과 이미지 디코딩 전에 수행한다.
5. 가격·대상 XOR·정지/활성 관계·유일성은 Form뿐 아니라 DB 제약으로 중복 방어한다.
6. 비공개가 된 상품의 metadata와 이미지가 기존 URL·대화·cache로 다시 노출되지 않아야 한다.
7. 포인트 차감·가산·거래·분개는 전부 성공하거나 전부 실패해야 한다.
8. 게시된 거래·신고 증거는 일반 편집 화면으로 사후 변조할 수 없어야 한다.
9. 프록시 전달 헤더는 명시적으로 신뢰한 직접 peer에서만 사용한다.
10. 운영 필수 보안설정이 빠지면 경고만 하지 않고 시작을 거부한다.

---

## 9. 발견 보안약점과 변경 내역

다음 항목은 보고서 분량을 위해 의도적으로 삽입한 취약점이 아니라 요구사항 검토, 실패한 테스트, 수동 코드리뷰, 브라우저 QA, 정적·의존성 검사에서 실제로 발견한 문제다. 수정 전 코드는 최종 결과에 남기지 않고 원인, 변경 이유, 재현·회귀 증적으로 설명한다.

### 9.1 1차·2차 개발 중 발견 사항

| ID | 발견된 약점·영향 | 왜 변경했는가 | 어떻게 변경했는가 | 상태·증적 |
|---|---|---|---|---|
| SEC-001 | 신고 target을 모델 검증 전에 바인딩하지 않아 정상 신고 실패 및 대상 경계 혼동 | 클라이언트 대상 필드가 추가되면 임의 대상 지정으로 이어질 수 있음 | URL에서 조회한 정확히 한 대상을 `form.instance`에 먼저 바인딩, Form 대상 제외, DB XOR 유지 | 신고 대상·DB 제약 회귀 통과 |
| SEC-002 | 홈 템플릿의 미정의 GET 변수가 비회원 첫 화면 500 유발 | 누락 입력 하나로 가용성이 깨짐 | view에서 검증한 명시적 검색 context만 전달 | 빈 검색·익명 렌더링 회귀 통과 |
| SEC-003 | 운영 HSTS의 하위도메인·preload 정책 미적용 | 운영 HTTPS 정책이 부분 적용될 수 있음 | 1년 HSTS와 환경변수 제어, 운영 deploy check | 실제 도메인 준비 여부는 배포 전 확인 |
| SEC-004 | 설치 환경의 이전 `pip`에서 알려진 취약점 6건 | 런타임이 아니어도 공급망 설치 경로 자산임 | `pip` 26.1.2로 갱신 후 재감사 | 당시 재검사 0건; 제출 직전 재감사 필요 |
| SEC-005 | 모바일 CSS가 로그아웃 버튼을 숨김 | 공용 기기 사용자가 세션 종료를 찾기 어려움 | 숨김 규칙 제거, POST·CSRF 로그아웃 유지 | 브라우저 모바일 폭 확인; 최종 QA 반영 |
| SEC-006 | 송금 화면 지갑 context 누락으로 잔액 0 표시 | 서버 판단은 안전해도 사용자에게 잘못된 보안 상태 표시 | 인증 사용자 지갑을 view context에 전달 | 지갑 context 회귀 통과 |
| SEC-007 | 도움말·오류 ARIA ID 불일치 | 비밀번호 조건과 오류를 보조기술이 연결하지 못함 | Django 위젯 참조와 `_helptext`, `_error` ID 통일 | 템플릿·브라우저 확인 |
| SEC-008 | 신고 권한만으로 상품 차단·계정 정지 action을 호출할 수 있는 교차 모델 권한 상승 | action 숨김은 forged POST를 막지 못함 | 실행 시 `change_report`와 전용 `block_listing`/`suspend_user`를 각각 재검사, 보호 계정 제외 | 전용 권한·forged POST 회귀 통과 |
| SEC-009 | `/admin/login/`에 일반 로그인 제한을 우회하는 반복시도 경로 | 고가치 관리자 계정 brute force 가능 | Admin도 account 5회/network 30회 짧은 예약을 사용하고 성공 시 account만 clear | 일반·Admin 인증 회귀 통과 |
| SEC-010 | 정지 계정이 active로 남거나 기존 상품이 공개될 수 있음 | 정지의 보안 효과가 저장 경로에 따라 달라짐 | 모델 정규화+DB CHECK, 정지·비활성 판매자 공개 queryset 제외 | DB·공개범위 회귀 존재 |
| SEC-011 | 가입·상품·메시지·신고 생성 상한 부족 | DB·파일 저장소 고갈 DoS 가능 | 기능별 시간당/일일 rate, 활성·이력 quota, pagination | quota/rate·사전 gate 회귀 통과 |
| SEC-012 | 오래된 상품 수정 POST가 관리자 차단을 덮을 수 있고 임의 status 전이 가능 | TOCTOU와 상태 무결성 훼손 | transaction 안에서 최신 행·소유자·상태 재검사, 서버 전이 허용목록 | SQLite 동시성 한계는 잔여위험 |
| SEC-013 | 익명 동적 HTML·이미지 cache와 DB·파일 삭제 시점 불일치 | 차단·rollback·교체 후 metadata·파일 잔존 | 모든 동적 응답 `private, no-store`, evidence-aware commit 삭제, 실패 신규 파일 정리 | 익명 HTML·이미지·파일 수명주기 회귀 통과 |
| SEC-014 | XFF·XFP 신뢰경계가 불명확 | 헤더 위조로 네트워크 제한·HTTPS 판단 우회 가능 | 신뢰한 직접 프록시 IP에서만 전달 헤더 사용, 잘못된 프록시 설정 시작 거부 | 실제 프록시 overwrite 설정 필요 |
| SEC-015 | 순차 사용자 ID 신고·차단과 비공개 상품 metadata 재노출 | 계정 열거·무관 사용자 괴롭힘·moderation 우회 | 실제 대화에서 상대 파생, 공개 상품 신고만 허용, 비공개 placeholder | 대화 목록까지 후속 보강 |
| SEC-016 | 대화 목록 무제한 및 행별 마지막 메시지 N+1 | 사용자 데이터가 늘면 DB·HTML 자원 고갈 | 30개 pagination과 Subquery annotation | 운영 데이터 query plan 재측정 필요 |
| SEC-017 | Admin 밖 ORM에서 Transfer·LedgerEntry 수정·삭제 가능 | 감사 원장 사후 변조 가능 | append-only 모델·QuerySet, 정정은 별도 반전 원칙 | 직접 SQL은 최소권한·감사 필요 |
| SEC-018 | 버전만 고정하고 hash lock·지속 검사가 없음 | 패키지 아티팩트 치환과 main 보안회귀 탐지 부족 | SHA-256 runtime/dev lock, 최소권한·SHA pin CI, CodeQL, Dependabot | dev lock 빈 대상 hash 설치 성공; GitHub 최초 실행은 공개 후 확인 |

### 9.2 최종 보안 감사에서 추가 발견한 사항

아래 항목은 최종 보안 감사에서 발견·수정한 영역이며, 마지막 코드 기준 전체 테스트·coverage·정적 검사를 다시 실행해 검증했다.

| ID | 발견된 약점·공격 경로 | 변경 이유 | 적용한 수정 | 최종 검증 상태 |
|---|---|---|---|---|
| SEC-019 | `accounts.change_user`를 가진 제한 staff가 일반 사용자 편집 POST로 `is_staff`, `is_superuser`, 그룹·권한 또는 정지 상태를 바꿀 수 있음 | 계정 관리 권한이 관리자 권한 상승과 보호 계정 훼손으로 이어짐 | `accounts.suspend_user` 전용 권한 추가, 비-superuser의 특권·계정상태 필드 readonly, staff/superuser 변경 거부, self/bulk delete 보호 | 권한·password URL·forged POST 회귀 통과 |
| SEC-020 | 이미 로그인한 staff가 Admin login POST를 보내면 다른 계정의 성공으로 오판해 잠금 기록을 지울 수 있는 사전 인증 상태 혼동 | 기존 세션과 제출 계정을 분리하지 않으면 인증 감사 상태가 변조됨 | 로그인된 staff는 Admin index로 redirect, 로그인된 nonstaff는 403, 성공은 제출한 정규화 사용자명과 실제 인증 사용자까지 일치할 때만 인정 | staff/nonstaff 사전인증 회귀 통과 |
| SEC-021 | 비밀번호 해시 중 DB lock, 임의 이름별 행 증가, 과대 credential과 실제/미존재 분기 | SQLite 쓰기 잠금·DB 저장소 고갈·CPU DoS·계정 oracle 위험 | 짧은 예약, hash 중 lock 없음, 계정 5/network 30, 성공 account만 clear, 모든 ACCOUNT HMAC 동일 DB 경로, IP/window 신규 행 최대 30·30분 retention purge, 사전 길이 상한 | real/unknown·30회 경계·cleanup·oversized 회귀 통과 |
| SEC-022 | 상품 이미지·메시지·신고·송금 Form 검증 뒤 rate limit을 소비 | 공격자가 제한 카운터 전에 이미지 디코딩·긴 입력 검증 비용 반복 가능 | raw 길이·UUID 형식과 rate gate를 고비용 Form·이미지 처리 전에 배치하고 유효하지 않은 요청도 시도량에 포함 | sanitizer 미호출·429·잘못된 UUID 회귀 통과 |
| SEC-023 | `ReportAdmin` 일반 변경 화면으로 원문·대상·처리 metadata를 바꾸고 판매자 변경으로 원 상품 증거가 사라질 수 있음 | 신고 증거와 처리 감사기록의 무결성 훼손 | read-only, snapshot·SHA, 증거명 index·private 보존, `view_report` endpoint의 hash 재검증·no-store·nosniff·actor log | forged POST·보존·권한 열람·변조 거부 회귀 통과 |
| SEC-024 | Django Admin 상품 업로드가 sanitizer를 우회하고 purge된 stale 객체가 레코드를 되살릴 수 있음 | 위장 파일·moderation·삭제 무결성 우회 | 공용 sanitizer, Admin add 비활성, 제한 필드 readonly, 현재 행 잠금·부재 시 거부, evidence-aware 정리 | fake image·수명주기·stale resurrection 회귀 통과 |
| SEC-025 | 차단·삭제 상품의 대화 목록에서 등록시각 등 일부 metadata가 남음 | 제목·가격만 숨겨도 존재·활동 시점을 추론할 수 있음 | `listing_visible` 조건에서만 제목·상태·가격·이미지·등록시각 표시 | BLOCKED/DELETED 목록·상세 회귀 통과 |
| SEC-026 | staff·superuser가 상대방이면 신고 제출 자체를 거부 | 보호 계정 정지 방지와 증거 수집을 혼동해 내부자 신고 증거가 사라짐 | protected account 신고는 허용하되 suspension action만 자신·staff·superuser를 건너뜀 | 보호 계정 신고 OPEN·활성 유지 회귀 통과 |
| SEC-027 | CI 설치 대상과 개발 의존성 파일 이름·hash lock 정책이 불일치할 가능성 | 로컬과 CI 도구 버전 차이, hash 없는 설치 경로 발생 | `requirements-dev.in`과 `requirements-dev.lock`으로 일원화, CI는 `--require-hashes` dev lock 설치, deploy warning을 실패 처리 | 빈 대상 dev lock hash 설치 성공 |
| SEC-028 | 서버 작성·사용자 행동 모델을 generic Admin으로 변조하거나 일반 상품 권한만으로 차단·purge 가능 | 증거 무결성과 최소권한 훼손 | 관련 모델 read-only, 전용 조치 권한, Report action 행 잠금·OPEN 재검사 | forged evidence POST·전용 권한·action 잠금 회귀 통과 |
| SEC-029 | boolean 오타와 길이만 긴 저엔트로피 운영 SECRET_KEY 허용 | 잘못된 운영 구성을 안전하다고 오인 | strict boolean, key 50자·문자 다양성·비안전 prefix, HTTPS fail-closed | 격리 settings negative·정상 deploy 회귀 통과 |
| SEC-030 | 같은 reporter·대상의 병렬 요청이 중복 OPEN 신고 생성 가능 | 감사 처리 중복·자원 소모 | reporter 잠금과 대상별 조건부 UNIQUE, 충돌 일반화 | DB 제약·중복 웹 요청 회귀 통과 |

### 9.3 사용자 수동 QA와 후속 UI 감사에서 추가 발견하고 수정한 항목

| ID | 발견·재현 | 영향 | 적용한 변경과 이유 | 상태·직접 증적 |
|---|---|---|---|---|
| SEC-031 | 기존 상품 편집에서 `image-clear=on`을 제출하면 삭제 sentinel `False`를 파일 객체로 직접 대입해 `.name` AttributeError 500 | 상품 수정 가용성 저하, DEBUG 정보노출과 결합 | 잠긴 행의 image에 `FileField.save_form_data()`를 호출해 Django의 sentinel 정규화를 재사용하고 기존 transaction·commit 파일 정리를 유지 | **Fixed** — 유지·삭제·교체·동시 선택·잘못된 파일·증거 보존 회귀 통과 |
| SEC-032 | 기본 개발 실행의 처리되지 않은 400·404·500이 기술 오류 화면 사용 | traceback, 절대경로, 버전, 소스·로컬 변수, 요청·설정·POST 값 노출 가능 | `SafeExceptionMiddleware`가 DEBUG에서도 비진단 응답·고정 로그를 사용하고, 오류 template 실패 시 독립 static fallback 적용; 운영 DEBUG false는 계속 강제 | **Fixed** — DEBUG/production 400·403·404·500·CSRF, POST 비밀값, pattern 비노출, fallback·보안헤더 회귀 통과 |
| SEC-033 | 기본 `ClearableFileInput`이 기존 이미지의 내부 storage filename과 실제 공개가 금지된 `/_private-media/` 링크를 편집 HTML에 표시 | 내부 저장 구조의 불필요한 노출, 사용자를 무효 링크로 유도, guarded image 정책과 UI 불일치 | `ProtectedListingImageInput`이 `listing_image` 권한검사 URL의 미리보기와 일반 문구만 렌더링하고 저장명·`MEDIA_URL`은 제외 | **Fixed** — 기존 이미지 widget의 보호 URL·삭제 label, 내부 저장명·`MEDIA_URL` 부재 회귀 통과 |

SEC-031·032는 과거 120개 통과로 종결하지 않았다. 원인별 회귀를 추가하고 새 기능 테스트와 함께 관련 8개 클래스 **87개를 53.390초에 실행해 통과**한 뒤 Fixed로 판정했다. 후속 SEC-033은 `ListingSecurityTests` 26개와 전체 170개 회귀에서 별도로 검증했다. 표적 실행은 변경 후 전체 suite·coverage·정적 검사의 최종값을 대신하지 않는다.

### 9.4 변경 후에도 남는 보안 한계

“보안약점이 없다”는 절대적 표현 대신, 확인된 위험을 수정하고 남은 위험을 운영 전제로 공개한다.

- 알려진 사용자명을 5회 틀리게 입력해 표적 계정 잠금을 유도할 수 있다. brute force 방어와의 절충이며 MFA·risk-based delay·관리자 별도 네트워크가 필요하다.
- LocMemCache와 SQLite는 다중 프로세스 전역 rate limit·강한 행 잠금을 제공하지 않는다.
- 직접 SQL, DB 관리자, 저장소 backup·CDN은 ORM·HTTP 삭제 통제를 우회할 수 있다.
- 대화는 참여자 접근통제만 하며 종단간 암호화가 아니다.
- 관리자 MFA, 관리 네트워크 제한, 중앙 SIEM·경보는 포함되지 않았다.
- 3인 신고 임계치는 임시 차단·정지만 수행하며 금지 상품·사기·정품 여부는 관리자 검토에 의존한다. 신고 공모·오탐의 정식 이의제기와 계정 복구 SLA가 필요하다.
- 서로 다른 신고자 3명은 한 계정의 중복은 막지만 공격자가 만든 세 계정의 Sybil/공모까지 판별하지 못한다. 계정 신뢰도·단계적 제재·공모 탐지와 이의제기 SLA가 필요하다.
- 전체 채팅은 2초 polling이라 규모가 커지면 요청·DB 부하가 증가한다. 또한 현재 신고 route는 상품별 1:1 대화 상대를 근거로 하므로 전체 채팅의 특정 메시지에 증거를 묶는 신고 경계가 없다. 메시지 IDOR를 막는 메시지별 신고·snapshot과 보존·파기 기간이 필요하다.
- SQLite의 행 잠금은 실효성이 없어 저장 검색 quota와 거래 상태 경합은 PostgreSQL에서 다시 검증해야 한다. 알림 fan-out은 commit 후에도 웹 프로세스에서 동기 선형 탐색하며 수동 재처리는 자동 worker·backoff를 대체하지 않는다.
- 가격 하락 알림은 `(recipient,event)` 중복은 막지만 가격을 반복 인상·인하하면 새 이벤트가 계속 생길 수 있다. 최소 하락폭·cooldown·시간창 묶음 알림이 필요하다.
- 거래 완료 요청 거절·취소는 요청 전 상태를 복원하므로 최초 `RESERVED` 상품은 계속 예약 상태로 남는다. 예약 해제 주체·만료시간·자동 해제 정책이 필요하다.
- 후기 개인정보 패턴 검사는 보조 통제이며 우회 가능한 표현·욕설·분쟁을 모두 판별하지 못한다. 운영 신고·숨김·이의제기와 후기·알림·증거 보존/파기 정책이 필요하다.

### 9.5 세 확장 기능에서 발견하고 수정한 약점

| ID | 발견한 문제 | 적용한 변경 | 상태 |
|---|---|---|---|
| SEC-034~036 | 판매자 단독 `SOLD`, 완료 상품 직접 mutation, 후기 방향·선공개·PII/XSS | 대화 결합 상호확인, 완료 상품 종결, 서버 파생 방향·blind 공개·PII 패턴·autoescape | Fixed/Mitigated |
| SEC-037~038 | 알림 IDOR·비공개 가격 노출·소급/중복·rollback 유령·fan-out 부하 | 수신자 scope, 현재 공개성, 구조화 event·시각 경계·UNIQUE·on-commit·batch·수동 재처리 | Fixed/Mitigated |
| SEC-039~041 | 대표 제외 총량, stale/child IDOR, rollback orphan, 위조 하자, 추가 신고 증거·Admin 경계 누락 | 전 파일 batch 제한, 잠긴 자식 scope, 실패 cleanup, 하자 allowlist, 다중 SHA snapshot·report-scoped 검증 열람 | Fixed/Mitigated |
| SEC-042 | `PENDING` 후기의 공개 평균·개수 조기 반영 | 공개 후기 목록·개수·평균을 모두 `Visibility.PUBLIC`로 제한 | Fixed |
| SEC-043 | `/` 구분 전화번호가 후기 PII 패턴 우회 | 숫자 구분자 허용목록에 slash 추가, 400·미저장 회귀 | Mitigated |
| SEC-044 | stale Listing Admin 폼이 새 차단 상태 덮어쓰기 | 잠근 최신 보호 필드 비교, 불일치 거부, 허용 필드만 복사 | Fixed |
| SEC-045 | multipart body가 CSRF·Form 검사 전 parser·임시 저장소 자원을 소비 | CSRF 전 21MiB known-length 선차단, 누락·축소 길이의 실제 chunk 누적, 일반 400 | Mitigated |
| SEC-046 | 하자 상태 변경 뒤 숨은 stale 상세·모순 입력과 오류·제출 피드백 부족 | `PRESENT` 조건부 활성화·초기화, `OTHER` required, 서버 독립 조합 거부·stale 정규화, 오류 요약·포커스·제출 잠금 | Fixed |
| SEC-047 | 두 탭 상품 수정의 lost update와 상품 전체 거래·현재 대화 CTA 불일치 | hidden revision과 잠근 최신 `updated_at` 불일치 409·비저장, 다른 거래 CTA·상대 신원 비공개, 현재 대화 거절·취소 기록 | Mitigated |

업로드 preflight에서 거부 파일을 bound form에 재결합·디코딩하지 않고 텍스트만 유지하며 사진 재선택을 안내한 변경, 썸네일-삭제 checkbox·번호·대표 승격 안내, 상품·메시지·후기 공통 오류 요약·포커스·native validation·submit lock은 `docs/04_SECURITY_FINDINGS.md`의 UX-001로 별도 기록했다. 이는 서버 보안 경계와 사용자가 이해하는 결과를 일치시키는 품질 통제다.

상세 원인·CWE·검증·잔여 위험은 `docs/04_SECURITY_FINDINGS.md`의 SEC-034~047에 기록했다.

---

## 10. 테스트 계획·체크리스트와 결과

### 10.1 테스트 전략

기능별로 다음 네 층을 함께 검증한다.

1. **정상 흐름:** 가입, 등록, 검색, 대화, 신고, 송금, 관리자 처리.
2. **악성 입력:** SQLi·XSS 문자열, 과대 입력, 위장 이미지, 가격·상태·sender·seller·target 변조.
3. **인가 실패:** 비회원, 타인 상품, 비참여 대화, 무권한 staff, forged Admin POST.
4. **무결성·실패:** 중복 멱등키, 잔액 부족 rollback, stale update, 파일 저장 실패, 원장 변경·삭제 시도.

### 10.2 핵심 체크리스트

| 영역 | 확인 항목 | 기대 결과 |
|---|---|---|
| 인증·프로필 | 약한 비밀번호, 계정 존재 유무 오류, 반복시도, 과대 credential, 공개 필드·프로필 Mass Assignment, 현재 비밀번호, Admin 우회 | 약한 값 거부, 공통 오류, 사전 제한, `username`·`bio`만 공개, 권한 불변, 세션 안전 갱신 |
| 인가 | 타인 상품, 비참여 대화, 무권한 staff, action 직접 POST | 403/404 또는 안전한 거부, 상태 불변 |
| 입력·표현 | SQLi·XSS·CRLF·외부 next URL·정렬값·가격 경계 | 문자열 처리·escape·허용목록, 외부 redirect 없음 |
| CSRF·세션 | 상태 변경 GET, CSRF 누락, 로그인·로그아웃 세션 | POST 강제, 403, 로그인 회전·로그아웃 폐기 |
| 이미지·하자 | MIME 위장, SVG/HTML, 5MB·12MP 초과, 애니메이션, EXIF, 6파일·20MiB 초과, 거부 파일 재결합, 삭제 대상 오선택, 기존 이미지 sentinel, 하자 상태/code 모순·stale 상세·OTHER 누락 | preflight 파일 미결합·재선택, 6파일 generic 400, client 5장/5MiB/20MiB 보조 검사와 서버 독립 제한·JPEG 재인코딩, 썸네일-삭제 결합·대표 승격, 서버 하자 조합 거부·stale 정규화 |
| 상품 | 판매자 변조, quota/rate, 상태 전이, 관리자 차단 후 stale POST, 두 탭 lost update | 서버 판매자, 제한 적용, 허용 전이만, 차단 유지, hidden revision+잠근 `updated_at` 불일치 409·전체 비저장 |
| 대화·전체 채팅·신고 | sender 변조, CSRF·XSS·cursor·rate, 제3자 열람, 다른 거래 CTA·상대 추론, 사용자 ID 열거, 비공개 metadata, 고유 3인 임계치·보호계정·복구, 증거 변경·action 경합 | session sender, signed cursor·상한·textContent, current/other trade 분리·상대 최소공개, 실제 대화 대상, placeholder, 원자 임시조치·관리자 복구, read-only snapshot·행 잠금 |
| 송금·원장 | 음수·초과·잔액 부족, 중복키, 차단 사용자, update/delete | 전체 rollback, 1회 반영, 전송 거부, append-only |
| 운영설정·오류 | DEBUG, 예외·POST 비밀값, 오류 template 실패, SECRET_KEY, hosts, HTTPS, proxy trust, Admin 노출, 익명 동적 cache | 잘못된 구성은 시작 거부, DEBUG에서도 비진단 오류·fallback, 모든 동적 응답 no-store |
| 공급망 | hash 설치, Ruff, Bandit, pip-audit, CodeQL, secret scan | 미조치 Critical/High 0건 목표 |

세부 자동 TEST-ID는 `docs/06_TEST_CHECKLIST.md`, 제출자 수동 인수·제출 점검은 `docs/10_USER_ACCEPTANCE_CHECKLIST.md`, 요구사항 연결은 `docs/02_REQUIREMENTS_TRACEABILITY.md`에 있다.

### 10.3 수정 후 표적 회귀·최종 통합 검사와 과거 스냅샷

SEC-031·032와 신규 상세 기능을 직접 검증하는 8개 클래스 87개, SEC-033 첨부 widget 26개, 세 확장 기능과 추가 보안 표적 36개를 2026-07-13에 통과했다. 그 시점의 전체 206개와 coverage·정적·공급망·deploy 검사도 완료했다. 이후 SEC-042~044 표적 16개와 SEC-045 표적 7개를 분리 실행했고, SEC-047까지 포함한 최신 결합 표적 **40개 / 17.697초 / system check 0건 / Ruff PASS**와 변경 후 전체 Django tests **219 / 219 / 157.165초 / system check 0건**도 통과했다. 최종 coverage 계측은 **219 / 219 / 162.533초 / 6,037 statements / 354 miss / 94%**였고 Ruff lint·46 files format, Bandit·pip-audit, Django check·deploy, migration, Node JavaScript 구문과 `git diff --check`도 모두 통과했다. 아래 206개·170개·120개 결과는 과거 스냅샷이다. GitHub 원격 검사는 저장소 공개 전이라 미실행 상태다.

| 검사 | 실행 명령·범위 | 스냅샷 실제 결과 | 증적 |
|---|---|---|---|
| 수정 분기 표적 회귀 | 관련 8개 테스트 클래스 | **87개 통과 / 53.390초 / system check 문제 0건** | 2026-07-13 직접 실행 |
| 첨부 widget 표적 회귀 | `ListingSecurityTests` | **26개 통과 / system check 문제 0건** | 2026-07-13 직접 실행 |
| 확장 기능 보안 표적 | 후기·알림·다중 이미지·Admin 증거·이벤트 재처리·완료 복구 | **36개 통과 / system check 문제 0건** | 2026-07-13 직접 실행 |
| SEC-042~044 후속 표적 | `market.test_trade_reviews` + `market.tests.ListingAdminSecurityTests` | **16개 통과 / 17.393초 / system check 문제 0건** | 2026-07-13 직접 실행 |
| SEC-045 multipart 표적 | `config.tests.MultipartUploadLimitTests` | **7개 통과 / 0.023초 / system check 문제 0건** | 2026-07-13 직접 실행 |
| SEC-042~047 최신 결합 표적 | 다중 이미지·multipart·Listing Admin·거래 후기 4개 class | **40개 통과 / 17.697초 / system check 문제 0건 / Ruff PASS** | preflight·사진 UI·하자 add→clear·revision 409·거래 CTA·공통 폼 피드백 포함 |
| 변경 후 전체 Django tests | `manage.py test --verbosity 1` | **219 / 219 통과 / 157.165초 / system check 문제 0건** | 최신 전체 회귀 완료 |
| 직전 전체 tests | `manage.py test --verbosity 1` | **206개 통과 / 114.641초 / system check 문제 0건** | 후속 보안 변경 전 기준선 |
| 직전 Coverage | 전체 suite instrumentation | **206개 통과 / 115.434초 / 5,778 statements / 343 miss / 94%** | 후속 보안 변경 전 기준선 |
| 직전 check·migration·Ruff·Bandit·diff | 당시 전체 코드·가상환경 | **check 통과 / migration drift 없음 / lint·format 통과 / Bandit 0 / diff 오류 0** | 후속 보안 변경 전 기준선 |
| 변경 후 최종 Coverage | 전체 suite instrumentation | **219 / 219 통과 / 162.533초 / 6,037 statements / 354 miss / 94%** | 완료 |
| 변경 후 정적·공급망·운영 게이트 | Ruff lint/format, Bandit, pip-audit, Django check/deploy, migration, Node syntax, diff | **Ruff PASS·46 files formatted; Bandit 0; 알려진 취약점 0; check/deploy 0; migration no changes; Node syntax·diff PASS** | 완료 |
| 직전 pip-audit·deploy | 현재와 동일한 의존성·운영설정 | **알려진 취약점 0 / deploy 0** | 후속 UI/widget 변경은 의존성·운영설정 미변경 |
| 과거 Django tests | `python manage.py test` | 120개 전부 통과 | 2026-07-12 보존 스냅샷; 신규 분기 미포함 |
| 과거 Coverage | `coverage run manage.py test` / `coverage report -m` | TOTAL 3,169 statements / 223 miss / 93% | 2026-07-12 보존 스냅샷 |
| 과거 Ruff·Bandit·pip-audit·deploy | 당시 전체 코드 | 문제 0건 | 2026-07-12 보존 스냅샷 |
| 반응형 UI 구조 | CSS 중괄호·필수 breakpoint·외부 asset·template inline style/script·실제 viewport 검사 | 현재 중괄호 1112/1112, 1080/900/700/470/360px 규칙, 외부 asset 미추가; 최종 웜톤 1440×1000·320×800 overflow 0과 주요 조작 44px 이상 | TEST-R009~013; 하자 오류 UI의 키보드·스크린리더·200% 확대는 미수행 |
| Runtime hash 설치 | `pip install --require-hashes -r requirements.lock` | 빈 대상 설치 성공 | 로컬 설치 결과 |
| Dev hash 설치 | `pip install --require-hashes -r requirements-dev.lock` | 빈 대상 설치 성공 | 로컬 설치 결과 |
| 시크릿·금지 패턴 | 현재 파일+Git 이력, 위험 API·template escape 우회 검색 | 일치 0건 | 로컬 검색 결과 |
| GitHub CI·CodeQL | 첫 Public push의 Actions/Security | **미실행—Public push 후 확인** | `[입력 필요: URL·SHA]` |

### 10.4 브라우저 수동 QA

2026-07-12 브라우저 QA에서는 판매자 가입·로그인, 상품 등록·예약 상태 변경, 구매자 가입·로그인, 상품 상세·대화 시작·메시지, 대화 문맥 신고 화면, DEMO POINT 24,000P 송금과 잔액 100,000→76,000, 모바일 390px 로그아웃 노출을 확인했다. 폼 label을 한국어화한 뒤 재확인했고 브라우저 console 오류·경고가 없었다.

감청색 UI 적용 후 1440×1000에서 흰색 sticky header, blue gradient hero, 4열 상품 Grid, 카드 radius 20px와 shadow, 문서 가로 overflow 0을 다시 실측했다. 모바일 재접속은 브라우저 도구의 로컬 URL 보안 정책에 막혀 우회하지 않았고, 대신 1080/900/700/470/360px cascade를 독립 감사했다. 이 감사에서 901px 인증 header 경계, 35~40px 주요 보조 컨트롤, 긴 사용자 입력과 회원 nav overflow, sticky anchor 가림 가능성을 찾아 1080px 재선언, 주요 컨트롤 최소 44px target, `overflow-wrap`, 내부 nav scroll·fade, `scroll-margin-top`으로 수정했다. 실제 320px·200% 확대와 스크린리더 QA는 완료로 과장하지 않고 릴리스 전 항목으로 유지한다.

2026-07-13 모노크롬 전환 뒤 브라우저에서 1440×1000 홈의 4열 Grid·가로 overflow 0과 320×800 홈의 1열 Grid·sticky header·44px primary button·가로 overflow 0을 확인했다. 이는 현재 팔레트 이전의 역사적 UI 증적이다.

2026-07-13 사용자 QA에서는 기존 이미지 삭제 선택 시 SEC-031 500을 재현했다. DEBUG true 응답은 약 91KB의 기술 화면으로 예외명과 traceback을 포함했고, DEBUG false의 동일 500은 일반 오류 화면이었다. 이후 이미지 field 정규화와 DEBUG-safe 오류 middleware·standalone fallback을 구현하고 표적 회귀로 수정 분기를 확인했다. 이어 실제 브라우저에서 이미지가 있는 임시 상품의 `비우기` 저장이 상세 placeholder로 이어지고 DB image 값과 기존 파일이 제거되며 오류가 없음을 확인했다. DEBUG true의 미등록 URL도 일반 404만 표시해 URL pattern·Django 버전·traceback을 노출하지 않았다. QA 사용자·상품·파일은 확인 후 삭제했다.

최종 웜톤 cascade 적용 뒤 1440×1000 데스크톱과 320×800 모바일 브라우저에서 문서 가로 overflow가 모두 0이고 주요 조작이 44px 이상임을 확인했다. 상품 사진은 원색이며 외부 asset을 추가하지 않았다. 이 검사는 레이아웃·터치 크기의 브라우저 spot-check이고, 판매자·구매자 두 세션의 후기·알림·다중 이미지 전체 사용자 흐름을 대신하지 않는다. 200% 확대, 실제 키보드·스크린리더와 확장 기능 전체 UAT는 PDF 제출 전 확인 대상으로 남는다.

---

## 11. 공급망·CI와 릴리스 설계

직접 의존성은 `.in` 파일, 재현 가능한 설치 산출물은 SHA-256 해시를 포함한 `.lock` 파일로 구분했다.

- `requirements.in` → `requirements.lock`: Django·Pillow 런타임
- `requirements-dev.in` → `requirements-dev.lock`: runtime + Ruff·Bandit·Coverage·pip-audit·pip-tools
- CI는 `--require-hashes`로 개발 lock 하나를 설치한다.
- 외부 GitHub Action은 이동 가능한 tag가 아니라 검토한 commit SHA로 고정한다.
- CI 기본 권한은 `contents: read`, CodeQL에 필요한 범위만 `security-events: write`로 제한한다.
- push/PR에서 migration·deploy check·Ruff·Bandit·coverage gate·pip-audit를 실행하고, CodeQL과 Dependabot은 주기 실행한다.

로컬 파일이 존재하는 것만으로 원격 검증 성공을 주장하지 않는다. Public 저장소 첫 push 뒤 실제 Actions·CodeQL 결과 URL과 대상 SHA를 이 보고서에 기록한다.

---

## 12. 유지보수 계획

### 12.1 변경 관리

1. 요구사항이 바뀌면 REQ-ID, 위협모델, KISA A/N/A 판정을 먼저 수정한다.
2. 기능 변경과 정상·악성·권한 회귀 테스트를 같은 PR에 포함한다.
3. DB 모델 변경은 migration과 rollback·데이터 전환 영향을 검토한다.
4. 의존성 변경은 lock diff, 공식 release note, pip-audit, 전체 테스트 후 병합한다.
5. 보안 수정은 SEC-ID로 원인·영향·수정·재시험·잔여위험을 남긴다.
6. 배포 전 `check --deploy`, 시크릿·Git 이력, backup 복구, HTTPS·HSTS를 확인한다.

### 12.2 정기 운영 작업

| 주기 | 작업 | 이유 |
|---|---|---|
| 매 PR | CI, CodeQL, 권한·입력·원장 회귀 | 보안 회귀의 main 유입 차단 |
| 매주 | Dependabot·pip-audit 검토 | 새 의존성 취약점 조기 발견 |
| 매일/실시간 | 로그인 제한, 403/429/5xx, Admin action·증거 열람/무결성 실패 보안로그 감시 | brute force·권한 오용·증거 변조·가용성 이상 탐지 |
| 매일/실시간 | 전체 채팅 polling·송신 429와 지연, 자동 상품 차단·계정 정지·복구 로그 감시 | 요청 폭증·cache 장애·신고 공모·오탐 조기 발견 |
| 매일 | DB·미디어 암호화 backup 및 복구 샘플 확인 | 장애·랜섬웨어·오삭제 대응 |
| 매일 | 원장 reconciliation: 분개 2건, 합계 0, 지갑 cache 일치 | 직접 SQL·코드결함 탐지 |
| 매주 | DB 참조 없는 orphan 이미지, 신고 증거 저장명 index·보존기한 점검 | rollback·스토리지 장애 후 잔존 파일 정리와 증거 조회 성능 유지 |
| 분기 | 관리자 권한·그룹·휴면 계정 검토, 키 교체 절차 연습 | 권한 누적·계정 탈취 영향 축소 |
| 릴리스 전 | 클린 설치, Public 접근, PDF·README 링크 검수 | 제출·배포 재현성 보장 |

### 12.3 운영 전 필수 전환

- SQLite → PostgreSQL 및 실제 동시성·deadlock·isolation 부하 시험
- LocMemCache → 공유 원자 Redis와 cache 장애 시 fail-closed 정책
- 전체 채팅 2초 polling의 동시 사용자·DB query·worker 부하 시험 후 기준 초과 시 인증·origin·rate-limit을 유지한 WebSocket/channel layer 검토
- `runserver` → 지원 WSGI/ASGI 서버, TLS reverse proxy, 전달 헤더 overwrite
- reverse proxy/Nginx의 `MEDIA_ROOT`·`/_private-media/` 정적 alias 직접 노출 금지와 Django 권한검사 이미지 view 경유 검증
- 관리자 MFA·관리 네트워크 제한·별도 고권한 계정
- 중앙 로그·경보·감사 보존, 전체 채팅·1:1 메시지·신고 원문·snapshot의 보존·삭제 정책
- backup 암호화·복구 목표(RPO/RTO)와 정기 복구훈련
- 사용자 신고 처리 SLA, 자동 임시조치 오탐·공모 이의제기, 사용자 정지 복구 승인, 금지상품·분쟁 절차

### 12.4 보안 제보·사고 대응

공개 GitHub Issue에는 비밀번호, 세션, 토큰, 개인정보, 미수정 공격 코드를 올리지 않도록 `SECURITY.md`에 안내했다. GitHub Private vulnerability reporting을 사용하고, 접수 후 영향 commit·권한 전제·기밀성/무결성/가용성 영향·임시완화·수정·재검증·공개 여부를 기록한다. 비밀 노출 사고는 Git 삭제만으로 끝내지 않고 키 폐기·교체와 전체 이력 검사를 수행한다.

### 12.5 거래 약속·길찾기 후보 기능

이 기능은 **설계 후보이며 현재 구현되지 않았다.** 사용자가 제안한 “거래하기를 누르면 판매자·구매자의 GPS를 서로 표시”하는 방식은 정확한 생활권·이동경로가 상대방에게 노출되어 스토킹·재식별·목적 외 이용 위험을 키운다. 위치 권한은 브라우저 동의 한 번으로 계속 공개해도 되는 권한이 아니며 철회·삭제·보존 종료가 필요하다. 따라서 정확한 양측 GPS 실시간 공개는 현재 범위에서 **NO-GO**로 결정했다.

권장하는 최소 흐름은 다음과 같다.

1. 상품 상세의 `거래하기`는 임의 사용자 ID를 받지 않고 기존 1:1 대화의 판매자·구매자를 서버에서 파생한다.
2. 대화 참여자만 역·경찰서·공공시설 등 공개된 약속장소와 시간을 제안하고, 상대가 수락해야 약속을 확정한다. 자택·현재 좌표를 기본값으로 사용하지 않는다.
3. 수락 뒤 각 사용자는 자신의 출발지에서 약속장소까지 자차·대중교통 경로를 **본인 화면에서만** 조회한다. 상대에게는 원 좌표나 지도 marker 대신 “약 10~15분 후 도착”처럼 둥근 ETA 범위와 갱신시각만 선택적으로 공유한다.
4. 약속은 제안·수락·취소·완료·만료 상태와 버전을 가지며, 참여자 인가·stale update 거부·감사 event를 적용한다. 정확한 출발 좌표는 DB·URL·application log에 보존하지 않고 경로 계산에 필요한 짧은 시간만 처리한다.
5. 사용자가 매번 명시적으로 길찾기를 눌렀을 때만 HTTPS secure context에서 위치 권한을 요청하고, 목적·수신자·보존시간·철회/삭제 방법을 먼저 안내한다. 거절해도 역명·주소 검색이나 외부 지도 링크로 거래 약속을 사용할 수 있어야 한다.

1단계는 GPS 없이 `TradeAppointment`·`AppointmentEvent`와 공공장소 제안·수락, 카카오맵/네이버지도/TMAP 외부 길찾기 링크만 제공하는 방식이 적절하다. 2단계에서 자차와 대중교통 ETA를 한 공급자로 구현하려면 공식 범위상 TMAP을 후보로 검토할 수 있다. TMAP 대중교통 경로 API는 `totalTime`과 구간 정보를 제공하지만, 실제 도입 전에는 [TMAP API 포털](https://tmapapi.tmapmobility.com/)과 [대중교통 경로 API 명세](https://transit.tmapmobility.com/docs/routes)의 최신 key 발급·quota·가격·경로 데이터 보존 약관을 다시 확인한다. API key는 브라우저에 포함하지 않고 서버 proxy의 secret으로 관리하며 사용자별 rate limit·timeout·실패 fallback을 둔다.

현재 애플리케이션은 `Permissions-Policy: geolocation=()`로 위치 기능을 차단하고 CSP `connect-src 'self'`로 외부 지도 API 직접 연결도 허용하지 않는다. 기능을 구현할 때만 약속·길찾기 화면에 필요한 최소 범위로 정책을 다시 설계해야 하며, 전체 사이트에서 위치를 상시 허용해서는 안 된다. [W3C Geolocation](https://www.w3.org/TR/geolocation/)의 secure context·명시적 권한 원칙과 [찾기쉬운 생활법령정보의 개인위치정보 안내](https://easylaw.go.kr/CSP/CnpClsMain.laf?ccfNo=2&cciNo=1&cnpClsNo=2&csmSeq=1702&menuType=cnpcls&popMenu=ov)를 기준으로 동의·보존·파기 범위를 법률 검토한 뒤에만 GPS·ETA 기능을 완료로 표시한다.

---

## 13. AI 도구 활용과 사람의 검증

OpenAI Codex와 병렬 검토 에이전트를 요구사항 분석, 공식 자료 확인, 경쟁사 조사, 설계 대안 비교, 코드 구현, 위협모델, 테스트 생성, 보안 감사, 문서 통합에 적극 사용했다. AI를 사용한 목적은 작업을 대신 증명하게 하는 것이 아니라 짧은 기간에 독립적인 검토 관점을 늘리고 반복 검사를 자동화하는 것이었다.

| 활용 단계 | AI가 제안·수행한 일 | 그대로 믿지 않은 이유 | 사람·도구의 검증 |
|---|---|---|---|
| 요구사항 | PDF 페이지 추출, 7개 기능 REQ-ID 분해 | 페이지·기한 오독 가능 | 원본 PDF 35~36페이지 육안 대조, 사용자 정정 공지 우선 |
| KISA 조사 | 가이드 판본·49개 항목 분류 | 존재하지 않는 최신 판본을 만들어낼 수 있음 | KISA 공식 게시물·PDF 표지·목차 직접 확인 |
| 경쟁사 | 당근·번개장터 장단점·적용안 | 회사 홍보 수치와 독립 자료 혼동 가능 | 공식 서비스·보도자료와 소비자원 자료 구분·교차검토 |
| 설계 | Django/SPA, SQLite/PostgreSQL, DEMO POINT 대안 | 과제 범위·로컬 환경을 모를 수 있음 | PDF 요구, 도구 상태, 공격면·검증시간으로 ADR 결정 |
| 구현 | 계정·상품·대화·원장·Admin 초안 | AI 코드는 권한·경쟁조건을 빠뜨릴 수 있음 | 코드리뷰, DB 제약, 정상+악성+forged POST 테스트 |
| 보안 감사 | Admin 권한상승, 로그인 동시성, 증거 변경, rate 순서 발견 | 제안 수정도 새 DoS·lock 문제를 만들 수 있음 | 수정안 재검토, 짧은 예약·전용 권한·사전 gate로 재설계 |
| 자동검사 | Ruff·Bandit·pip-audit·coverage 해석 | 도구 0건이 취약점 0건을 뜻하지 않음 | 수동 위협모델·브라우저 QA·잔여위험 병행 |
| UI 재설계 | 감청색 토큰·Grid/Flex override와 경계 폭 감사 | AI가 cascade·한글/사용자 입력 폭·실제 접근성을 오판할 수 있음 | 1440×1000 실측, 독립 정적 감사, 전체 회귀와 제출 전 실제 모바일 QA |
| 모노크롬 전환·요구 재대조 | 검정·흰색 토큰, 기존 hard-coded 색상 감사, PDF 25~29페이지 14개 시스템 기능표 | 전역 grayscale의 상품 사진 왜곡, 흑백 focus 소실, 대기능표가 상세 누락을 숨길 수 있음 | 원색 상품 사진, 이중 focus ring, 1440·320px 실측, 5페이지 원문·코드·67 tests 대조 |
| 상세 기능·보안 보강 | 프로필·마이페이지·내 상품·전체 채팅·3인 신고 임계치, SEC-031·032 수정안과 회귀 | 범용 User 변경은 권한을 노출하고 WebSocket/SSE·영구 자동삭제는 검증범위·DoS를 키우며 예외 문자열 로그는 정보노출 가능 | 최소 field allowlist·Django PasswordChangeForm, 제한된 2초 polling, 고유 OPEN 3인 임시조치·복구, SafeExceptionMiddleware·fallback을 코드 대조하고 87개 표적 테스트 직접 실행 |
| 첨부 UI·위치 기능 검토 | 기본 file widget 정보노출 감사, scoped 세이지 스타일, 지도 제공자·GPS/ETA 아키텍처 비교 | 색의 의학적 효능을 단정하거나 API 소개만으로 정확한 위치 공유의 안전성·구현 가능성을 오판할 수 있음 | 보호 widget HTML과 서버 이미지 검증을 26개 표적·당시 170개·직전 206개 전체 회귀로 확인; TMAP·Kakao Mobility·NAVER·ODsay·W3C 공식 문서 대조; 정확한 상호 GPS는 거절하고 key·quota·약관·동의·보존·법률 검토 전 ETA 구현 보류 |
| 웜톤·후속 보안·작성·거래 UX 감사 | warm palette, 비공개 후기 aggregate·slash PII·Admin stale 저장·multipart, 조건부 하자, 거부 파일 재결합, 썸네일-삭제 오연결, 두 탭 lost update, 거래 CTA·공통 폼 피드백 공격 시나리오 점검 | 시각 결과와 표적 테스트만으로 전체 회귀·접근성·운영 동시성을 과장할 수 있음 | 1440×1000·320×800 확인, 최신 결합 40개·전체 219개·coverage 94%·정적/공급망/deploy/migration PASS; 키보드·스크린리더·200% 확대는 미완료로 분리 |
| 보고서 | 문서 초안과 추적표 통합 | GitHub URL·원격 검사 성공을 추정할 수 있음 | 로컬 수치는 실제 결과만 기록하고 Public URL·Actions·PDF 외부 상태만 placeholder 유지 |

AI 프롬프트에는 실제 비밀번호, 토큰, 세션 쿠키, 비밀키, 개인정보를 넣지 않았다. 제안된 기능이 과제 최소 요구에 없거나 보안 검증 범위를 지나치게 늘리면 채택하지 않았다. 예를 들어 React+REST+JWT, 실제 결제·외부 이미지 URL, 구현하지 않은 주문 상태 머신을 완료로 표현하는 안을 거절했다. AI가 작성한 코드는 route·model·form·template·migration을 주 에이전트가 직접 대조하고 테스트를 실제 실행했다. AI-020 단계에서 추정하지 않았던 전체 coverage는 이후 최종 통합 검사로 직접 측정했으며, 여전히 실행하지 않은 GitHub·외부 배포·PDF 결과만 성공으로 추정하지 않았다.

최종 AI 활용 건수와 프롬프트·채택/수정/거절 기록은 `docs/05_AI_USAGE_LOG.md`를 기준으로 PDF 생성 직전에 갱신한다.

---

## 14. 잔여 위험과 한계

| 위험 | 현재 영향 | 현재 보완 | 향후 조치 |
|---|---|---|---|
| SQLite 동시성 | 다중 사용자 쓰기 잠금·row lock 한계 | 조건부 UPDATE, 짧은 transaction, DB 제약 | PostgreSQL 부하·경쟁 시험 |
| LocMemCache | 인스턴스별 rate counter 분리 | 단일 프로세스 교육 범위 명시, DB 인증 lock 보조 | 공유 Redis·장애정책 |
| 표적 계정 lockout | 알려진 계정에 일시 가용성 저하 | 네트워크 원시도 제한, 공통 메시지, 로그 | MFA, risk scoring, progressive delay |
| 관리자 계정 | MFA·관리망 미구현 | 운영 Admin 기본 비활성, 세부 권한·로그 | MFA/IdP, VPN·IP allowlist |
| Admin CSP inline 예외 | XSS 방어 강도 일부 저하 | 일반 사용자 경로는 엄격 CSP, Admin 접근 제한 | nonce/hash 기반 정적 자산화 검토 |
| 대화 기밀성 | 서버·DB 관리자는 내용 접근 가능 | 참여자 객체 접근통제, HTTPS | 암호화 at rest, 보존기간, 필요 시 E2EE 별도 설계 |
| 전체 채팅 polling | 최대 약 2초 지연, 사용자가 늘면 HTTP·DB 부하 증가 | signed cursor, 100건, 조회·송신 rate, hidden 중단·backoff | PostgreSQL·Redis 부하 시험, 필요 시 WebSocket/channel layer |
| 자동 moderation 오탐·Sybil 공모 | 공격자가 만든 3개 계정의 고유 신고로 임시 서비스 제한 가능 | 중복·자기 신고 제외, 보호 계정, 영구삭제 금지, 감사로그·관리자 복구 | 계정 연령·신뢰도·공모 탐지, 단계적 제재, 이의제기·복구 SLA |
| 가격 알림 반복 스팸 | 가격 인상·인하 반복마다 새 하락 이벤트 생성 가능 | 이벤트별 수신자 UNIQUE, 차단·정지 제외 | 최소 하락폭·cooldown·시간창 묶음 알림·수신 설정 |
| 전체 채팅 신고 경계 | 특정 전체 채팅 메시지를 증거로 고정한 신고 route 없음 | 인증·출력·rate·관리자 read-only 메시지 | message ID 서버 바인딩, snapshot·IDOR·보존/파기·관리자 검토 |
| 예약 상태 복원 | 요청 전 `RESERVED`였으면 거절·취소 뒤에도 예약 유지 | 초기 상태 snapshot과 제한된 복원 | 예약 해제 주체·만료시간·자동/수동 해제 정책 |
| 대화·신고 보존 | 원문 장기 보관 시 개인정보·저장소 부담 | 최소 공개, 권한·read-only evidence | 메시지·신고별 보존·파기 기간과 legal hold 정책 |
| 파일 삭제 | backup·스토리지 장애에 orphan 가능 | commit 후 삭제, no-store, 정기 점검 계획 | object lifecycle·backup 보존 정책 |
| upstream 업로드 자원 | application 21MiB 제한 전에 reverse proxy가 큰 body·느린 연결을 수신할 수 있음 | CSRF 전 middleware·실제 chunk 누적·안전 400 | proxy body/time/connection limit과 부하 시험 |
| 원장 직접 SQL | ORM append-only 우회 | 서비스 단일 게시 경계, reconciliation 계획 | DB 최소권한·감사 trigger/외부 원장 |
| 실제 거래 보호 부재 | 배송·환불·사기 피해를 해결하지 않음 | DEMO POINT·교육용 경고, 금융정보 미수집 | 실제 서비스 확장 시 별도 규제·에스크로 설계 |
| 거래 위치·ETA 미구현 | 약속장소·도착시간 자동 안내가 없음 | 정확한 GPS 상호 공개를 하지 않고 현재 geolocation·외부 connect 차단 유지 | 공공장소 약속부터 구현 후 명시적 동의·최소보존·법률·TMAP key/quota/약관 검토 |
| 공개 CI 외부 상태 | 로컬 구성만으로 성공 보장 불가 | workflow·SHA pin·최소권한 구성 | 첫 push 후 Actions/CodeQL URL·SHA 증적 |

본 프로젝트는 교육용 결과물이며, 이 잔여 위험을 해결하지 않은 채 실제 금융·상거래 서비스로 운영해서는 안 된다.

---

## 15. GitHub 공개·README·제출 계획

### 15.1 공개 저장소 정보

- Public Repository: **[입력 필요: GitHub URL]**
- 최종 branch: **[입력 필요: main 등]**
- 최종 commit SHA: **[입력 필요]**
- release/tag: **[입력 필요]**
- GitHub Actions 결과: **[입력 필요: URL]**
- CodeQL 결과: **[입력 필요: URL]**
- 로그아웃 상태 공개 접근 확인시각: **[입력 필요: KST]**

### 15.2 README 재현 확인

README에는 Python 3.12 가상환경 생성, hash-locked 개발 의존성 설치, migration, 개발 서버 실행, 관리자 생성, 환경변수, 테스트·보안검사 명령, 운영 fail-closed 조건, 알려진 제약을 작성했다. 다음은 새 디렉터리·새 가상환경에서 README만 보고 재현한 뒤 기록한다.

- `[완료]` 빈 대상 디렉터리에 `requirements-dev.lock` hash 설치 성공
- `[최종 확인 필요]` migration과 서버 시작 성공
- `[최종 확인 필요]` 전체 테스트와 보안 검사 성공
- `[최종 확인 필요]` 비밀값·DB·업로드 없이 clone 가능
- `[완료]` README와 `docs/00~12` strict UTF-8 decode 오류 0건, 로컬 Markdown 링크 오류 0건, stale 완료 표현·의존성 파일명·조치 권한 표현 점검

남은 작업에는 clean clone README 재현, 실제 키보드/스크린리더·200% 확대와 확장 기능 브라우저 인수, 외부·개인 증적인 반·이름·전화번호, Public GitHub URL·SHA·tag, 원격 Actions/CodeQL, 외부 배포 선택 여부, 최종 PDF 캡처·렌더링이 포함된다. 로컬 최종 게이트는 전체 **219 / 219**, coverage **6,037 statements / 354 miss / 94%**, Ruff·Bandit·pip-audit·Django check/deploy·migration·Node syntax·diff PASS다. 과거 120개·93%, 168개·94%, 170개·94%, 206개·94%는 시점별 스냅샷으로만 보존한다.

### 15.3 공개 전 검사

- `.env`, `var/`, SQLite DB, 업로드, log, coverage 파일이 Git 추적 대상이 아닌지 확인
- 현재 파일과 전체 Git 이력에서 비밀·개인정보 검색
- 노출 흔적이 있으면 이력 수정만 하지 않고 키 폐기·교체
- lock 파일 diff와 `--require-hashes` 클린 설치 확인
- GitHub Actions·CodeQL·Dependabot 실제 실행 확인
- Public URL을 로그아웃·시크릿 브라우저에서 확인
- 보고서에 URL, tag, SHA, 검사시각 입력

### 15.4 PDF 제출 직전 검사

- 표지의 반·이름·전화번호 뒷자리·GitHub URL 입력
- 모든 `[입력 필요]`, `[최종 확인 필요]` placeholder 제거
- 표·코드·Mermaid 그림의 잘림, 한글 글꼴, 링크 클릭 확인
- GitHub URL을 PDF에서 직접 클릭하고 로그아웃 상태 접근 확인
- 파일명을 `[WHS][secure-coding][XX반]이름(뒷4자리).pdf`로 저장하고 공백 0개 확인
- 공식 기한 **2026-07-24 23:59:59** 이전 업로드 후 다시 내려받아 열기

---

## 16. 결론

TINY MARKET은 과제의 7개 필수 기능을 하나의 Django 애플리케이션으로 연결하면서, 중고거래에서 반복되는 수평 권한상승, 대상·발신자 변조, 저장형 XSS, 위험 파일, 신고 악용, 관리자 권한 오용, 이중 지출과 공급망 위험을 설계 단계부터 다뤘다. 당근의 낮은 사용 마찰과 번개장터의 전국 검색·거래 추적 장점을 가져오되, 실제로 제공하지 않는 위치 인증·안전결제·정품 보증을 과장하지 않았다.

개발 중 발견한 문제는 숨기지 않고 왜 위험했는지, 어떤 신뢰경계를 잘못 두었는지, 코드·DB·권한·테스트를 어떻게 바꿨는지 기록했다. 특히 최종 감사에서 제한 staff의 계정 권한상승, Admin 사전 인증 상태 혼동, 비밀번호 해시 중 DB lock, 신고 증거와 Admin 업로드 우회에 이어 비공개 후기 aggregate 노출, slash PII 우회, Admin stale 차단 덮어쓰기, multipart 파싱 전 자원고갈, 하자 조건부 입력의 stale·모순, 거부 파일 재결합, 두 탭 상품 lost update와 거래 상태·CTA 불일치까지 찾아 수정·완화했다.

결론은 자동검사 숫자 하나가 아니라 요구사항→설계→구현→공격 테스트→수정→잔여위험→유지보수의 추적성이다. 사용자 QA의 SEC-031·032, UI 감사의 SEC-033, 확장 기능의 SEC-034~041과 후속 SEC-042~047을 수정·완화했다. 최종 로컬 게이트는 비계측 **219개/157.165초**, coverage **219개/162.533초·6,037 statements/354 miss/94%**, Ruff·Bandit·pip-audit·Django check/deploy·migration·Node syntax·diff PASS다. 최종 웜톤 화면은 1440×1000·320×800에서 overflow 0과 주요 조작 44px 이상을 확인했다. revision 누락 호환과 SQLite 동시성은 운영 전 보강해야 한다. 정확한 상호 GPS는 위치 프라이버시 위험 때문에 구현하지 않고 공공장소 약속·개별 경로·ETA 범위 설계로 제한했다. Public GitHub, clean clone, 원격 Actions/CodeQL, 확장 기능 전체 브라우저·키보드·스크린리더·200% 확대 인수, 최종 PDF·지정 파일명·LMS 제출을 완료하기 전에는 제출본으로 확정하지 않는다.

---

## 부록 A. 요구사항-구현-증적 요약

| 요구사항 | 주요 구현 | 주요 보안 증적 | 현재 판정 |
|---|---|---|---|
| REQ-F001 가입·인증 | `accounts` User/Form/view/LoginAttempt·공개 프로필·마이페이지 | Mass Assignment, 공개 allowlist·XSS, 약한/현재 비밀번호, account 5/network 30, 변경 10/hour, oversized, session hash | 신규 프로필·마이페이지 표적 및 직전 전체 206개 회귀 통과 |
| REQ-F002 상품 | Listing/Form/view/내 상품/private image·multipart middleware·조건부 하자 UI | IDOR, 가격·상태, 21MiB pre-parser, 거부 파일 미결합·6파일 generic 400, 썸네일-삭제·대표 승격, revision stale 409, 이미지 위장·증거보존·Admin sanitizer, SEC-031·033·045~047 | 최신 결합 표적 40개, 삭제·유지·교체·보호 widget 표적, 직전 전체 회귀와 실제 브라우저 삭제 통과 |
| REQ-F003 소통 | Conversation/Message·GlobalChatMessage·polling API | 참여자·session sender, CSRF·XSS·signed cursor·rate, 차단, pagination·N+1, 비공개 metadata | 전체 채팅·Admin 표적 회귀 통과; scale QA 대기 |
| REQ-F004 차단·신고 | UserBlock/Report/moderation service/Admin | 대상 열거 거부, 고유 OPEN 3인 원자 집계, 보호 계정·임시조치·복구, snapshot/SHA/read-only evidence | 자동조치·복구 표적 회귀 통과; 이의제기 운영정책 필요 |
| REQ-F005 송금 | Wallet/Transfer/Ledger service | 조건부 debit, rollback, 멱등, 이중 원장, append-only | 2026-07-12 스냅샷 통과 |
| REQ-F006 검색 | home ORM query/filter/sort/page | SQLi 문자열, 허용목록, 길이, 비공개 제외 | 2026-07-12 스냅샷 통과 |
| REQ-F007 관리자 | Django Admin·전용 login | 전용 action 권한, read-only evidence, Admin 기본 비활성, 최신 보호 상태 재검사 | 기존 회귀와 SEC-044 포함 Admin 표적 7개 통과 |
| REQ-E001 상호확인 후기 | `Trade`·`Review`·공개 프로필 | 상품별 대화 참여자, current/other trade 분리·상대 최소공개, server direction, blind 공개와 `PUBLIC` aggregate, slash PII·XSS, 완료 상품 종결 | 최신 결합 표적의 거래 상태·CTA 분기와 최종 전체 219개 통과 |
| REQ-E002 관심·가격 알림 | `SavedSearch`·`ListingEvent`·`Notification` | owner IDOR, 시각 경계, 중복, 비공개 metadata, retry | 표적 12개+명령 1개와 직전 전체 206개 통과 |
| REQ-E003 다중 사진·하자 | `ListingImage`·`ListingDefect`·`ReportImageEvidence`·`listing_form.js` | client 5장·5MiB/장·20MiB, preflight 파일 미결합, child IDOR, orphan, 썸네일-삭제 결합·대표 승격, revision 409, 조건부 UI+서버 allowlist·stale 상세 정규화, 공통 오류·제출 잠금, SHA 증거 | 최신 결합 40개에서 add→clear·두 탭 conflict 포함, 최종 전체 219개·coverage 94% 통과 |

## 부록 B. 최종 검증 명령

Windows PowerShell 기준 예시는 다음과 같다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements-dev.lock
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
coverage erase
coverage run manage.py test
coverage report -m
ruff check .
ruff format --check .
bandit -c pyproject.toml -r accounts community config market
pip-audit -r requirements.lock --disable-pip
```

운영 검사에는 재사용하지 않을 충분히 긴 시험용 `SECRET_KEY`, 실제 형식의 host·origin, `DEBUG=false`를 설정하고 다음을 실행한다.

```powershell
python manage.py check --deploy --fail-level WARNING
python manage.py collectstatic --noinput
```

## 부록 C. 산출물 목록

| 산출물 | 역할 |
|---|---|
| `README.md` | 환경설정·실행·검증·운영 전제 |
| `SECURITY.md` | 위협모델·보안통제·제보·잔여위험 |
| `CHANGELOG.md` | 기능·보안 변경 이력 |
| `docs/00_PROJECT_JOURNAL.md` | 시간순 개발일지와 이유 |
| `docs/01_TWO_DAY_PLAN.md` | 이틀 압축 계획·완료기준 |
| `docs/02_REQUIREMENTS_TRACEABILITY.md` | 요구사항-구현-테스트 추적 |
| `docs/03_DECISION_LOG.md` | 주요 아키텍처 의사결정 |
| `docs/04_SECURITY_FINDINGS.md` | 보안약점 원인·수정·재시험 |
| `docs/05_AI_USAGE_LOG.md` | AI 사용·채택/수정/거절·사람 검증 |
| `docs/06_TEST_CHECKLIST.md` | 기능·공격·릴리스 체크리스트 |
| `docs/07_KISA_BASELINE.md` | KISA 49개 적용성·증적 |
| `docs/08_COMPETITOR_ANALYSIS.md` | 당근·번개장터 조사와 적용 결정 |
| `docs/09_REPORT_DRAFT.md` | 최종 제출 보고서 통합 초안 |
| `docs/10_USER_ACCEPTANCE_CHECKLIST.md` | PDF 원문 기반 사용자 수동 인수·보안·제출 점검 |
| `docs/11_CORE_SUBMISSION_CHECKLIST.md` | PDF 25~29페이지 14개 핵심 시스템 기능 체크리스트 |
| `docs/12_CORE_CHECKLIST_EXECUTED_2026-07-13.md` | 현재 코드에서 Codex가 직접 수행한 PASS·PARTIAL·FAIL 판정 |
| `.github/workflows/*.yml` | CI·CodeQL 지속 검증 |
| `requirements*.in/lock` | 직접 의존성과 hash-locked 설치 |

## 부록 D. 최종 증적 삽입 자리

1. `[삽입 필요]` PDF 35페이지의 7개 요구사항 캡처
2. `[삽입 필요]` 홈·검색 화면
3. `[삽입 필요]` 상품 등록·상세·상태 변경
4. `[삽입 필요]` 대화·신고·차단 흐름
5. `[삽입 필요]` DEMO POINT 지갑·송금·균형 원장 결과
6. `[삽입 필요]` 권한 분리된 Admin 화면
7. `[삽입 필요]` 최종 tests·coverage·Ruff·Bandit·pip-audit·deploy check 로그
8. `[삽입 필요]` Public GitHub와 성공한 Actions·CodeQL 화면(대상 SHA 포함)
9. `[삽입 필요]` 로그아웃 상태 Public 접근과 최종 PDF 파일명
