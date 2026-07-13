# 기능·보안 테스트 체크리스트

자동검사 수치는 2026-07-12 로컬 재실행의 과거 스냅샷이다. `[x]`는 해당 범위의 자동 검사 또는 명시한 수동 코드 검토 완료, `[~]`는 일부만 확인했거나 GitHub·브라우저 등 추가 확인 대상, `[ ]`는 미완료, `N/A`는 이유를 확인한 비적용 항목이다. 2026-07-13 SEC-031·032와 누락 분기를 발견했으므로 수정 뒤 현재 120개 테스트와 신규 회귀를 모두 다시 실행하고 숫자를 갱신한다.

## 자동 검사 요약

| 검사 | 명령/범위 | 실제 결과 | 상태 |
|---|---|---|:---:|
| Django tests | `manage.py test` | 120개 전부 통과, 단 `image-clear`·오류 본문 비노출 분기 미포함 | 과거 스냅샷 완료·재실행 필요 |
| Coverage | 2026-07-12 120-test instrumentation | 3,169 statements / 223 miss / 93% | 과거 스냅샷 완료·재실행 필요 |
| Ruff | 애플리케이션·테스트 코드 | 오류 0건 | 완료 |
| Bandit | Python 코드 | 이슈 0건 | 완료 |
| pip-audit 최초 | 가상환경 전체 | `pip` 취약점 6건 | 발견 |
| pip-audit 재검사 | `pip` 26.1.2 갱신 후 | 취약점 0건 | 조치 완료 |
| Django 배포 검사 | 검증용 운영 환경의 `check --deploy` | 문제 0건 | 완료 |
| 금지 패턴 검색 | Python·HTML의 위험 API·escape 우회 | 일치 0건 | 완료 |
| Runtime lock | SHA-256 포함 `requirements.lock` | `--require-hashes` 설치 검증 | 완료 |
| Dev lock | `requirements-dev.lock` | 빈 대상 디렉터리에 `--require-hashes` 설치 성공 | 완료 |
| CI·CodeQL | push/PR workflow·security-extended | 파일·commit SHA pin 검토 | GitHub 실행 예정 |

## PDF 35페이지 최소 기능

- [x] TEST-F001 회원가입, 비밀번호 해시·검증, 로그인, POST 로그아웃
- [x] TEST-F002 공개 상품 목록·검색·상세 조회와 차단 상품 제외
- [~] TEST-F003 상품 등록, 판매 상태 허용 전이, stale 수정 방지, soft delete·이미지 정리 - 기존 이미지 삭제는 SEC-031 수정 대기
- [x] TEST-F004 상품별 1:1 대화, 참여자 제한, 30개 페이지 목록·마지막 메시지 annotation
- [x] TEST-F005 대화 상대 차단·신고, 상품 신고, 비공개 placeholder, Admin 조치
- [x] TEST-F006 DEMO POINT 송금, 지갑·내역 조회, 서버 잔액 판단
- [x] TEST-F007 Django Admin의 교차 모델 최소 권한·보호 계정과 원장 ORM 불변성

## 인증·인가

- [x] TEST-A001 `login_required` 중요 기능과 비회원 리다이렉트 코드 검토
- [x] TEST-A002 사용자 A가 사용자 B의 상품 수정·삭제 시 404
- [x] TEST-A003 대화 비참여자의 상세 접근 404
- [x] TEST-A004 일반 사용자의 `/admin/` 접근 거부
- [x] TEST-A005 자기 자신과 대화·송금 불가 서비스 검증
- [x] TEST-A006 요청의 `seller`, `sender`, 권한·상태 필드가 서버 결정을 바꾸지 못함
- [x] TEST-A007 로그인 오류를 일반화해 계정 존재 여부 구분 방지
- [x] TEST-A008 계정별 5회/15분과 네트워크별 원시도 30회/15분 로그인 제한, 성공 시 해당 account 상태만 삭제하고 network 누적 유지
- [x] TEST-A009 정지 계정 로그인 거부
- [x] TEST-A010 신고 대상은 URL 문맥에서 검증 전에 서버 바인딩하고 DB는 대상 하나만 허용
- [x] TEST-A011 Admin 로그인도 계정 5회·network 30회 제한, 성공 시 해당 account 상태만 삭제하고 network 누적 유지
- [x] TEST-A012 신고 action은 `change_report`와 전용 `block_listing`/`suspend_user` 권한을 내부에서 재검사
- [x] TEST-A013 forged Admin POST로 숨겨진 상품 차단·계정 정지 action 실행 불가
- [x] TEST-A014 관리자 본인·staff·superuser 일괄 정지 제외
- [x] TEST-A015 단순 staff는 `market.view_listing` 없이 차단 상품 조회 불가
- [x] TEST-A016 정지 계정은 모델·DB 모두 active 상태가 될 수 없고 판매 상품도 비공개
- [x] TEST-A017 비-superuser의 User privilege·정지 필드와 password reset 위조 변경 거부
- [x] TEST-A018 Admin 사전 인증 staff POST는 타 계정 제한을 지우지 않고 nonstaff는 403
- [x] TEST-A019 실제·미존재 ACCOUNT HMAC의 동일 DB 경로, IP당 15분 신규 행 최대 30개·30분 retention cleanup, 과대 credential 사전 거부
- [x] TEST-A020 `block_listing`, `suspend_user`, `delete_listing`+`purge_listing` 전용 권한 조합별 허용·거부
- [x] TEST-A021 Message·Conversation·Favorite·UserBlock·LoginAttempt의 Admin 직접 추가·변경·삭제 거부
- [x] TEST-A022 신고 처리·차단·정지 action은 Report 행 잠금과 `OPEN` 재검사 뒤 실행
- [x] TEST-A023 purge된 상품의 stale Listing Admin 저장은 레코드를 다시 생성하지 못함

## 입력 검증 및 표현

- [x] TEST-I001 SQL 삽입 형태 검색어가 ORM의 일반 문자열로 처리됨
- [x] TEST-I002 상품·메시지 XSS 페이로드가 템플릿에서 이스케이프됨
- [x] TEST-I003 0·음수·상한 초과 상품 가격 거부
- [x] TEST-I004 외부 `next` URL과 `//evil.example` 리다이렉트 거부
- [x] TEST-I005 신고 대상·송금 발신자 추가 POST 필드 무시
- [x] TEST-I006 사용자 입력을 헤더·파일 경로·서버 URL로 사용하지 않는 데이터 흐름 검토
- [x] TEST-I007 순차 사용자 ID만으로 신고·차단 불가, 참여 대화에서 상대방을 서버가 파생
- [x] TEST-I008 비공개 상품 UUID를 신고 URL로 재사용해 metadata를 다시 열 수 없음

## CSRF·세션·쿠키·응답 헤더

- [x] TEST-S001 로그아웃·찜·대화 시작·차단 등 상태 변경은 POST 전용
- [x] TEST-S002 로그인·상품 등록의 CSRF 토큰 누락 요청 403
- [x] TEST-S003 로그인 시 세션 키 회전, POST 로그아웃 시 세션 폐기
- [x] TEST-S004 운영 쿠키 Secure·HttpOnly·SameSite와 HTTPS 리다이렉트 설정
- [x] TEST-S005 공개 응답 CSP·Permissions-Policy·DENY frame·nosniff·same-origin referrer
- [x] TEST-S006 인증·익명 공개 HTML을 포함한 모든 동적 응답 `private, no-store`·`Pragma: no-cache`
- [x] TEST-S007 운영 1년 HSTS·includeSubDomains·preload 설정과 배포 검사
- [x] TEST-S008 비신뢰 peer의 XFF·XFP 무시, 설정된 proxy에서만 client IP·HTTPS 전달 허용

## DEMO POINT 무결성과 경쟁조건

- [x] TEST-T001 한 송금에 부호가 반대인 원장 2건이 생성되고 합계가 0
- [x] TEST-T002 잔액 부족 시 송금·원장·잔액 변경 전체 롤백
- [x] TEST-T003 같은 멱등키·같은 요청은 한 번만 반영
- [x] TEST-T004 같은 멱등키를 다른 금액에 재사용하면 거부
- [x] TEST-T005 조건부 잔액 차감으로 음수 방지, 캐시 잔액과 전체 원장 합계 일치
- [x] TEST-T006 차단 사용자 송금 거부, 클라이언트의 발신자 변조 무시
- [x] TEST-T007 송금 화면이 인증 사용자의 실제 지갑 context를 표시
- [x] TEST-T008 모든 게시 송금은 원장 정확히 2건이고 delta 합계 0
- [x] TEST-T009 Transfer instance·QuerySet update/delete/bulk_update 거부
- [x] TEST-T010 LedgerEntry instance·QuerySet update/delete/bulk_update 거부

## 상품 상태·자원·목록 성능

- [x] TEST-Q001 네트워크당 회원가입 5회/시간 제한과 원문 IP 대신 HMAC 키 저장
- [x] TEST-Q002 사용자당 상품 등록 10회/시간 제한
- [x] TEST-Q003 활성 상품 50개·전체 이력 500개 계정 quota를 계정 잠금 경계에서 검사
- [x] TEST-Q004 메시지 분당 20·일 500, 신고 일 10 상한 코드·회귀 검토
- [x] TEST-Q005 판매중·예약중·판매완료 허용 전이만 POST로 수행
- [x] TEST-Q006 관리자 차단 뒤 stale 수정 POST가 차단 상태를 되돌리지 못함
- [x] TEST-Q007 판매완료 상품에는 새 대화를 시작할 수 없음
- [x] TEST-Q008 대화 목록 30개 페이지네이션과 Subquery 마지막 메시지로 N+1 제거

## 파일 업로드

- [x] TEST-U001 JPEG·PNG·WebP 디코딩 가능 이미지와 MIME/시그니처 검증
- [x] TEST-U002 HTML·SVG·실행 파일과 위장 이미지 거부
- [x] TEST-U003 5MB·12MP·단일 프레임 상한 적용
- [x] TEST-U004 원본 이름을 버리고 UUID JPEG 경로 사용
- [x] TEST-U005 EXIF 방향 보정 후 JPEG 재인코딩으로 메타데이터 제거
- [x] TEST-U006 삭제·비공개 상품 이미지의 직접 접근 제한과 타 사용자 상품 변경 거부
- [x] TEST-U007 공개 이미지도 `private, no-store`이며 soft delete commit 뒤 파일 제거
- [x] TEST-U008 이미지 교체 DB 실패 시 새 고아 파일, 성공 시 이전 파일을 정리하는 경로 검토
- [x] TEST-U009 상품 신고 시 텍스트·가격·분류·상태·이미지 저장명 snapshot과 SHA-256 일치
- [x] TEST-U010 교체·soft delete·Admin purge 뒤에도 Report가 참조한 이미지는 private storage에 보존되고 공개 route로 접근 불가
- [x] TEST-U011 제한 소진 시 상품 Form·이미지 sanitizer 실행 전 429
- [x] TEST-U012 증거 endpoint의 `view_report` 권한, 매 요청 SHA-256 재검증, 변조 404, `no-store`·`nosniff`, actor log와 증거명 index
- [ ] TEST-U013 기존 이미지 삭제 체크는 302·DB 빈 이미지·commit 후 파일 삭제이며 500이 발생하지 않음 - SEC-031 수정 대기
- [ ] TEST-U014 이미지 미변경·교체·삭제+업로드 동시 선택·잘못된 이미지에서 기존/신규/증거 파일 생명주기 회귀 - SEC-031 수정 대기

## 오류 응답과 정보노출

- [ ] TEST-E001 `DEBUG=False` BadRequest·PermissionDenied·404·예상하지 못한 예외·CSRF가 각각 400/403/404/500/403 커스텀 화면 사용
- [ ] TEST-E002 오류 본문에 `Traceback`, `Exception Value`, 절대경로, Python/Django 버전, settings, POST 비밀값 없음
- [ ] TEST-E003 오류 응답에도 CSP·`nosniff`·`DENY`·`private, no-store` 적용
- [ ] TEST-E004 standalone 500이 DB·세션·URL reverse·공통 템플릿 장애에도 최소 응답 반환
- [ ] TEST-E005 400·405·429 공통 안내와 429 `Retry-After` 확인

## 회귀·접근성 점검

- [x] TEST-R001 홈의 빈 검색·누락 GET context가 500을 만들지 않음
- [x] TEST-R002 Django 5.2 위젯 `aria-describedby`와 `_helptext`, `_error` ID 일치
- [x] TEST-R003 470px 이하에서도 POST 로그아웃 컨트롤을 숨기지 않음
- [x] TEST-R004 전체 템플릿 파싱 성공, 인라인 script/style과 escape 우회 없음
- [x] TEST-R005 차단·삭제 상품 대화는 제목·가격·이미지 링크 대신 비공개 placeholder 표시
- [x] TEST-R006 가입 포인트 발행 내역은 빈 사용자명이 아니라 시스템 지급으로 표시
- [x] TEST-R007 Report 원문·snapshot·처리 metadata는 read-only이고 forged Admin POST에도 불변
- [~] TEST-R008 320px·200% 확대, 키보드 전용, 색 대비와 실제 스크린리더 브라우저 QA
- [x] TEST-R009 감청색 UI 1440×1000 실화면에서 sticky header·hero·4열 Grid·문서 가로 overflow 0 확인; 1080/900/700/470/360px cascade, header·검색·CTA·상태 변경·페이지네이션·신고 컨트롤 최소 44px, 회원 nav 내부 overflow와 긴 입력 줄바꿈 정적 감사

## 명시적 N/A

- N/A-001 별도 주문의 구매 요청·승인·거절·취소·환불 상태 머신: PDF 최소 요구사항이 아니며 현재 `Trade`/`Order` 모델과 URL이 없다. 상품 자체의 판매중·예약중·판매완료 상태 전이는 구현·검증했지만 이를 주문 승인으로 주장하지 않는다.
- N/A-002 실제 결제·은행계좌·카드·환전·출금: DEMO POINT만 사용하며 금융정보를 수집하지 않는다.
- N/A-003 XML, LDAP, DNS 기반 권한 결정, 사용자 URL 서버 호출, 전자서명·웹훅: 해당 기능과 의존성이 없다.
- N/A-004 자체 C 확장·수동 메모리 해제: Python/Django 애플리케이션 범위에 없다.

## 2026-07-13 릴리스 확인

- [~] REL-T01 README만 사용한 새 환경 설치·마이그레이션·실행·테스트
- [~] REL-T02 현재 파일과 Git 전체 이력에서 비밀·개인정보 0건
- [~] REL-T03 GitHub Public URL을 로그아웃 브라우저에서 열고 릴리스 SHA 기록
- [~] REL-T04 보고서 PDF 렌더링, 페이지 잘림·링크·GitHub URL 확인
- [~] REL-T05 공백 없는 지정 파일명과 공식 기한 2026-07-24 확인
- [~] REL-T06 최초 GitHub Actions CI·CodeQL·Dependabot 실행 결과와 대상 commit SHA 기록
- [~] REL-T07 운영 reverse proxy가 `MEDIA_ROOT`·`/_private-media/`를 직접 alias로 노출하지 않고 모든 이미지 요청이 Django 권한검사 view를 통과하는지 배포 설정 검증
- [x] REL-T08 README와 `docs/00~10` strict UTF-8 decode 오류 0건, 로컬 Markdown 링크 오류 0건, stale 완료 표현 정정
- [ ] REL-T09 SEC-031·032 수정, 신규 오류 회귀, 전체 테스트·coverage·정적·의존성 검사 재실행 후 Open 상태 해소
