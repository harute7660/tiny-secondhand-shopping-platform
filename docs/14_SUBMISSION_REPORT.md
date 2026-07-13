# Tiny Second-hand Shopping Platform 프로젝트 보고서

> 제출 전 `XX반`, 이름, 전화번호 뒷자리, Public GitHub URL을 채운 뒤 PDF로 변환한다. 현재 로컬 최종 commit SHA는 `49ca4f4e34d28f406e43c2cd816778ab858a3c71`이다.

## 1. 프로젝트 개요

본 프로젝트는 교육용 중고거래 플랫폼을 보안 중심으로 설계·구현한 Django 웹 애플리케이션이다. 과제 PDF의 필수 기능인 회원가입·로그인, 상품 등록·조회·검색, 사용자 간 소통, 악성 사용자·상품 차단, 사용자 간 가상 송금, 관리자 관리 기능을 구현했다. 추가로 실제 중고거래 서비스의 신뢰성을 높이기 위해 다중 사진·하자 체크리스트, 거래 완료 쌍방 후기, 관심 검색어·가격 하락 알림을 확장 기능으로 추가했다.

서비스는 실제 결제·실명 인증·배송·에스크로를 제공하지 않는다. `DEMO POINT`는 과제 검증용 가상 값이며 실제 금융정보를 입력하지 않도록 안내한다.

## 2. 요구사항 분석

요구사항은 PDF 35페이지의 7개 대기능과 PDF 25~29페이지의 상세 시스템 기능으로 나누어 추적했다. 최종 판정은 `docs/02_REQUIREMENTS_TRACEABILITY.md`에 기록했으며, 현재 로컬 시스템 기능 범위는 14개 상세 요구사항 모두 PASS다.

핵심 요구사항은 다음과 같다.

| 구분 | 구현 내용 | 보안 고려 |
|---|---|---|
| 사용자 계정 | 가입, 로그인, 로그아웃, 공개 프로필, 마이페이지, 비밀번호 변경 | 비밀번호 hash, 세션 회전, 역할 mass assignment 차단, 로그인 제한 |
| 상품 | 상품 등록·조회·검색·수정·상태 변경, 내 상품 관리 | 소유자 검증, revision 기반 lost update 방지, XSS 방지, 이미지 검증 |
| 소통 | 상품별 1:1 대화, 로그인 회원 전체 채팅 | 참여자 검증, sender 서버 결정, 차단 관계 반영, CSRF |
| 신고·차단 | 상품·사용자 신고, 자동 임시조치, 관리자 복구 | 신고자 자격 검증, 중복 신고 방지, 보호 계정 예외, 증거 보존 |
| 가상 송금 | DEMO POINT 송금과 원장 기록 | 원자적 이중 원장, append-only, 멱등 처리 |
| 후기·알림 | 거래 완료 쌍방 후기, 관심 검색·가격 하락 알림 | 실제 거래자만 후기, blind 공개, 수신자 scope, 비공개 metadata 재검사 |
| 운영 문서 | README, 보안 대장, 테스트 체크리스트, AI 사용 기록 | 요구사항과 보안 조치의 추적성 확보 |

## 3. 시스템 설계

아키텍처는 Django 서버 렌더링 기반으로 구성했다. 앱 경계는 계정(`accounts`), 전체 채팅(`community`), 거래 도메인(`market`), 설정·middleware(`config`)로 분리했다. 개발 DB는 SQLite를 사용하지만, 실제 다중 사용자 운영 전에는 PostgreSQL과 Redis 전환이 필요하다고 명시했다.

주요 모델은 `User`, `Listing`, `ListingImage`, `ListingDefect`, `Conversation`, `Message`, `GlobalChatMessage`, `Report`, `WalletAccount`, `Transfer`, `LedgerEntry`, `SavedSearch`, `Notification`, `Trade`, `Review`, `TradeEvidence`다. DB 제약은 UNIQUE, CHECK, FK, index를 사용해 애플리케이션 검증이 빠져도 핵심 무결성이 깨지지 않도록 했다.

보안 설계 원칙은 다음과 같다.

- 클라이언트가 보낸 `seller`, `sender`, `reporter`, `buyer`, 후기 방향은 신뢰하지 않고 세션·URL·DB 관계에서 결정한다.
- 상태 변경은 POST와 CSRF를 요구한다.
- 출력은 Django autoescape를 유지하고, 사용자 문자열을 `safe`로 렌더링하지 않는다.
- 파일 업로드는 크기·형식·픽셀·프레임 수를 검증한 뒤 metadata 없는 JPEG로 재인코딩한다.
- 완료 상품은 공개 데이터 최소화와 분쟁 증거 보존을 분리한다.

## 4. 구현 결과

프론트엔드는 웜톤 디자인으로 정리했다. 전체 배경은 크림색 canvas, 카드·입력은 따뜻한 흰색 surface, 주요 버튼은 테라코타 계열을 사용했다. 이미지 첨부 영역은 눈이 편안한 저채도 세이지 색을 제한적으로 적용했다. CSS Flexbox·Grid 기반으로 데스크톱과 모바일 반응형을 구성했다.

백엔드는 Django Form, ORM, transaction, middleware를 중심으로 구현했다. 특히 상품 수정은 hidden revision을 요구해 오래 열린 탭의 저장이 최신 데이터를 덮어쓰지 못하게 했다. 거래 완료는 판매자 요청과 구매자 확인이 모두 있어야 `SOLD`가 되며, 완료 거래만 쌍방 후기를 작성할 수 있다.

README에는 Windows PowerShell과 macOS/Linux 기준 설치·실행 명령, hash lock 기반 의존성 설치, migration, runserver, 보안 검사 명령, 운영 제한 사항을 명시했다.

## 5. 체크리스트 및 테스트 결과

최종 로컬 검증 결과는 다음과 같다.

| 검사 | 결과 |
|---|---|
| Django 전체 테스트 | 251 / 251 통과, 147.753초 |
| Coverage | 6,922 statements / 385 miss / 94% |
| Ruff | lint PASS, 50 files format PASS |
| Bandit | 8,082 lines, 이슈 0건 |
| pip check / pip-audit | 충돌 0건, runtime·development lock 알려진 취약점 0건 |
| Django check / deploy check | 문제·warning 0건 |
| migration | `0007`·`0008` 적용, drift 없음 |
| JS / CSS / diff / secret scan | syntax·중괄호·diff·고신뢰 secret scan PASS |

제출 전 사람이 반드시 확인해야 하는 항목은 다음과 같다.

- [ ] Public GitHub repository URL 입력 및 로그아웃 브라우저 접근 확인
- [ ] GitHub Actions·CodeQL·Dependabot 결과 확인
- [ ] 보고서에 반, 이름, 전화번호 뒷자리, GitHub URL, 최종 SHA 입력
- [ ] PDF 변환 후 한글·표·링크·페이지 잘림 육안 확인
- [ ] 제출 파일명을 `[WHS][secure-coding][XX반]이름(전화번호뒷자리).pdf` 형식으로 저장
- [ ] LMS 제출 완료 화면 확인

로컬 clean clone에서는 `check`, `makemigrations --check --dry-run`, `migrate --noinput`이 통과했다. 다만 Public GitHub에서 새로 clone한 fresh venv 설치와 원격 CI는 저장소 공개 후 별도 확인해야 한다.

## 6. 보안 약점 발견 및 조치

개발 중 확인한 주요 보안 약점과 조치는 `docs/04_SECURITY_FINDINGS.md`에 SEC-001~061, UX-001로 기록했다. 마지막 감사에서 특히 보완한 항목은 다음과 같다.

| ID | 확인한 약점 | 조치 |
|---|---|---|
| SEC-048 | 계정별 로그인 실패 잠금이 타인 계정 DoS가 될 수 있음 | 계정 hard lock 대신 네트워크 사전 상한과 실패 기록으로 완화 |
| SEC-049 | 신규 계정 3개의 신고 공모로 자동 차단 가능 | 가입 7일 이상·활성·미정지 신고자만 자동조치 집계 |
| SEC-050 | revision 누락 시 상품 수정 lost update 우회 | revision 정확히 1개 필수, 누락·중복 400, stale 409 |
| SEC-055 | 완료 상품 공개 정보가 계속 보존됨 | 공개 Listing 데이터 최소화, 거래·후기 참조 보존 |
| SEC-058 | 완료 상품 숨김이 분쟁 증거까지 잃게 할 수 있음 | 불변 `TradeEvidence`와 이미지 SHA-256 snapshot 보존 |
| SEC-059 | legacy 원장 반전 관계 migration의 조용한 데이터 손실 | `REVERSAL` kind와 relation 모두 fail-closed 검사 |
| SEC-060 | 후기 restore action의 부분 복구 가능성 | 쌍방 방향·상태·선택 수를 row lock 뒤 검증 |
| SEC-061 | 외부 Origin 요청이 pre-CSRF upload quota를 소모 가능 | Origin exact match와 Fetch Metadata를 quota 차감 전에 검사 |

잔여 위험도 기록했다. SQLite와 LocMemCache는 실제 다중 인스턴스 운영에 충분하지 않으며, 운영 전 PostgreSQL·Redis·reverse proxy upload 제한·관리자 MFA·백업·증거 보존/파기 정책이 필요하다. 이 프로젝트는 과제 제출용 로컬 검증 PASS 상태이며, 곧바로 실서비스 운영 안전을 의미하지 않는다.

## 7. 유지보수 계획

제출 직전 대규모 구조 분리는 회귀 위험이 커서 보류했다. 대신 유지보수 계획으로 기록했다.

- `market/views.py`, `services.py`, `admin.py`, `models.py`를 listing, trade, moderation, notification, evidence 영역으로 분리한다.
- `static/css/site.css`의 이전 디자인 잔여 rule을 제거하고 component 단위 CSS로 정리한다.
- 알림 fan-out은 request thread가 아니라 durable queue와 retry worker로 이전한다.
- PostgreSQL에서 동시 수정·거래 완료·신고 자동조치 경합 테스트를 재수행한다.
- 증거 snapshot의 보존 기간, legal hold, 사용자 삭제 요청, 승인된 purge 정책을 문서화한다.

## 8. GitHub Public 업로드 방법

1. GitHub에서 새 repository를 만들고 Public으로 설정한다.
2. 로컬에서 최종 검사를 통과한 뒤 commit을 만든다.
3. remote를 연결한다.

```powershell
git remote add origin https://github.com/<계정>/<저장소>.git
git branch -M main
git push -u origin main
```

4. GitHub repository 페이지를 로그아웃 또는 시크릿 창에서 열어 공개 접근을 확인한다.
5. Actions 탭에서 CI가 성공했는지 확인한다.
6. 보고서에 repository URL과 최종 commit SHA를 입력한다.

제출 PDF에는 Public repository 링크가 반드시 들어가야 한다. 최종 파일명은 공백 없이 `[WHS][secure-coding][XX반]이름(전화번호뒷자리).pdf` 형식으로 저장한다.
