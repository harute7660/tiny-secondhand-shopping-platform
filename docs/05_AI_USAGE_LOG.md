# AI 도구 활용·검증 기록

AI 출력은 참고자료이며 사실성, 보안성, 요구사항 적합성을 사람이 공식 문서·코드리뷰·테스트로 검증한 뒤 반영한다. 프롬프트에는 비밀번호, 토큰, 세션, 개인정보를 입력하지 않는다.

| ID | 날짜 | 도구 | 사용 목적 | 산출물 | 채택/수정/거절 | 사람의 검증 | 관련 증적 |
|---|---|---|---|---|---|---|---|
| AI-001 | 2026-07-12 | OpenAI Codex | 과제 요구사항 분해와 1차 아키텍처 제안 | 기능·보안·테스트·보고서 계획 | PDF 확인 전 초안은 보류하고 35페이지의 7개 기능으로 갱신 | 사용자 원문·PDF와 대조 | `02_REQUIREMENTS_TRACEABILITY.md` |
| AI-002 | 2026-07-12 | OpenAI Codex | KISA 공식 출처와 첨부파일 판본 확인 | 공식 게시물·문서 판본 구분 | 채택 | KISA 공식 페이지와 PDF 표지·목차 직접 확인 | `00_PROJECT_JOURNAL.md` |
| AI-003 | 2026-07-12 | OpenAI Codex 및 병렬 검토 에이전트 | 보안 아키텍처, 위협, 이틀 일정 독립 검토 | Django 구조, KISA 적용성, 일정안 | SQLite/Docker 여부를 로컬 환경 결과에 맞게 수정 | KISA 49개 항목, 로컬 도구 상태, 일정과 대조 | `01_TWO_DAY_PLAN.md`, `03_DECISION_LOG.md`, `07_KISA_BASELINE.md` |
| AI-004 | 2026-07-12 | OpenAI Codex | 강의 PDF 요구사항 추출 | 34~36페이지와 24페이지 렌더링 | 35페이지 7개 필수 기능 채택, 슬라이드 기한은 사용자 정정 공지로 수정 | PDF 원본 페이지 육안 확인 | `02_REQUIREMENTS_TRACEABILITY.md` |
| AI-005 | 2026-07-12 | OpenAI Codex 및 병렬 조사 에이전트 | 당근·번개장터 비교 조사 | 공식 기능·신뢰 장치·공개 한계와 과제 적용안 | 회사 자체 지표와 소비자 조사 구분, 장점만 선택 적용 | 공식 서비스·보도자료와 한국소비자원 자료 교차검증 | `08_COMPETITOR_ANALYSIS.md` |
| AI-006 | 2026-07-12 | OpenAI Codex 및 병렬 구현 에이전트 | 계정·도메인·UI를 분리 구현 | Django 코드·템플릿·테스트 초안 | 서버가 사용자·대상·발신자를 결정하는 코드만 채택하고 통합 수정 | 당시 중간 스냅샷: Django tests 72개, Coverage 91% | 구현 코드·`06_TEST_CHECKLIST.md` |
| AI-007 | 2026-07-12 | OpenAI Codex 병렬 보안·템플릿 검토 | view·URL·template context와 접근성 통합 점검 | 신고 실패, 잔액 0 표시, 모바일 로그아웃, ARIA 참조 문제 발견 | 신고 대상을 검증 전에 서버 바인딩하고 context·CSS·ARIA 수정 | 실패 재현, 템플릿 파싱, 관련 회귀 테스트와 전체 테스트 | `04_SECURITY_FINDINGS.md` SEC-001·005~007 |
| AI-008 | 2026-07-12 | OpenAI Codex | 정적 분석·공급망 검사 결과 해석 | Ruff·Bandit·pip-audit·Coverage 결과 | `pip` 취약점 6건을 설치 도구라고 무시하지 않고 26.1.2로 갱신 | Ruff 0, Bandit 0, Coverage 91%, pip-audit 재검사 0 | `04_SECURITY_FINDINGS.md` SEC-004 |
| AI-009 | 2026-07-12 | OpenAI Codex | 운영 보안 설정 검토 | HSTS 하위 도메인·preload 보강안 | 운영 기본값과 환경변수 제어를 함께 채택 | 검증용 운영 환경에서 `manage.py check --deploy` 문제 0건 | `config/settings.py`, SEC-003 |
| AI-010 | 2026-07-12 | OpenAI Codex | 문서와 실제 구현·테스트 추적성 감사 | 오래된 주문 상태 머신 체크리스트 발견 | 미구현 기능을 완료로 포장하지 않고 N/A·향후 범위로 정정 | 모델·URL·테스트 전수 대조 | `02_REQUIREMENTS_TRACEABILITY.md`, `06_TEST_CHECKLIST.md` |
| AI-011 | 2026-07-12 | OpenAI Codex 및 병렬 보안 감사 에이전트 | 관리자·경쟁조건·자원고갈·proxy 신뢰경계 2차 위협 모델 | 교차 모델 권한, 보호 계정, Admin 로그인, DB 불변식, quota/rate, TOCTOU 개선안 | UI 숨김만으로 권한을 통제하는 안은 거절하고 action 내부·DB·트랜잭션 경계 방어 채택 | forged Admin POST, DB CHECK, rate/quota, stale update, proxy 테스트 | `04_SECURITY_FINDINGS.md` SEC-008~014 |
| AI-012 | 2026-07-12 | OpenAI Codex 및 병렬 통합 감사 에이전트 | 신고·차단·대화 목록·비공개 상품 흐름 재검토 | 대화 기반 대상 파생, placeholder, pagination·Subquery 제안 | 순차 사용자 ID 직접 대상을 거절하고 실제 대화 문맥만 채택 | 열거 거부, 비공개 metadata, annotation 테스트 | `04_SECURITY_FINDINGS.md` SEC-015~016 |
| AI-013 | 2026-07-12 | OpenAI Codex | 금융 원장 불변성 재검토 | ORM instance·QuerySet 우회 경로 식별 | Admin read-only만으로 충분하다는 가정을 거절하고 append-only 모델 계층 적용 | 송금·원장 update/delete와 균형 원장 테스트 | `04_SECURITY_FINDINGS.md` SEC-017 |
| AI-014 | 2026-07-12 | OpenAI Codex | 공급망·지속 검증 설계 | hash lock, CI, CodeQL, Dependabot 초안 | 런타임 lock과 최소 권한·SHA pin workflow를 채택 | 로컬 파일·pin 검토; GitHub 실행 성공은 미확인으로 유지 | `requirements.lock`, `.github/`, SEC-018 |
| AI-015 | 2026-07-12 | OpenAI Codex | 최종 회귀 실행과 문서 수치 갱신 | 전체 테스트와 coverage 보고서 | 실제 명령 결과만 반영 | 120개 전부 통과, Coverage 93%, Ruff·Bandit 0 | `06_TEST_CHECKLIST.md` |
| AI-016 | 2026-07-12 | OpenAI Codex 및 병렬 UI 감사 에이전트 | 감청색 반응형 디자인 구현과 경계 폭·터치 영역 감사 | CSS 토큰·Grid/Flex·반응형 override와 개선 목록 | Tailwind 신규 의존성은 거절하고 기존 CSS 구조를 채택; 901px cascade·주요 컨트롤 44px 미달·긴 입력 overflow 제안은 수정 반영 | AI-assisted 1440×1000 실측, CSS cascade·DOM 정적 감사, Django 회귀; 사용자 최종 모바일 육안검수는 pending | `static/css/site.css`, ADR-008, TEST-R009 |
| AI-017 | 2026-07-13 | OpenAI Codex 및 병렬 오류·UI 감사 에이전트 | 사용자 제보 이미지 500 진단, 오류 정보노출 대조, PDF 원문 기반 수동 체크리스트 작성 | SEC-031·032 원인·재현, DEBUG True/False 오류 결과, 사용자 인수·제출 체크리스트 | 오류를 숨기거나 기존 120개 통과로 종결하지 않고 Open finding과 테스트 공백으로 기록; UI 복제 주장은 코드·asset 감사로 검증 | PDF 24·34~36페이지 렌더링·텍스트 대조, 격리 test DB 재현, DEBUG별 응답 본문 검사, 구현·문서 교차검토 | `04_SECURITY_FINDINGS.md`, `10_USER_ACCEPTANCE_CHECKLIST.md` |
| AI-018 | 2026-07-13 | OpenAI Codex, Browser, 병렬 UI·테스트·보안 감사 에이전트 | 블랙·화이트 UI 전환, 18개 필수 체크리스트 축약, 현재 코드 직접 검증 | 모노크롬 CSS override, 핵심/수행 체크리스트, 이름 후보 10개 | 전역 grayscale·상품 사진 흑백화는 정보 왜곡 때문에 거절; 기존 layout·semantic HTML 유지, 중립 UI와 원색 상품 사진 채택 | 1440×1000·320×800·로그인·안전 화면 실측, 120 tests·93% coverage, Ruff·Bandit·pip-audit·deploy check, CSS/asset/secret scan | `static/css/site.css`, ADR-009, `11_CORE_SUBMISSION_CHECKLIST.md`, `12_CORE_CHECKLIST_EXECUTED_2026-07-13.md` |
| AI-019 | 2026-07-13 | OpenAI Codex, PDF 도구, 병렬 요구사항·코드 감사 에이전트 | 사용자 정정에 따라 PDF 25~29페이지 시스템 기능 체크리스트 재작성 | 14개 기능표와 실제 구현 판정 | 기존 18개 표의 범위가 잘못됐음을 인정하고 제출·보안 점검은 분리; 빨간 글씨를 임의로 선택 처리하지 않음 | 5페이지 렌더·텍스트 교차확인, route/model introspection, 관련 5개 클래스 67 tests 46.119초 통과, 구현 파일 대조 | ADR-010, `11_CORE_SUBMISSION_CHECKLIST.md`, `12_CORE_CHECKLIST_EXECUTED_2026-07-13.md` |
| AI-020 | 2026-07-13 | OpenAI Codex 및 병렬 계정·채팅·마켓 구현 에이전트 | PDF 상세 기능 공백 구현, SEC-031·032 수정, 보고서 추적성 갱신 | 공개 프로필·마이페이지·내 상품·전체 채팅·3인 신고 임계치, 안전한 오류 처리와 테스트 초안 | 범용 User 수정·WebSocket/SSE·신고 즉시 영구삭제·예외 문자열 로그를 거절. 최소 공개 필드, Django PasswordChangeForm, 제한된 2초 polling, 고유 OPEN 3인 임시조치·관리자 복구, SafeExceptionMiddleware·독립 fallback을 채택 | 주 에이전트가 코드 diff·route/model/form/template를 직접 대조하고 관련 8개 클래스 87 tests를 53.390초에 실행해 통과 확인. 전체 suite·coverage·GitHub·외부 배포·PDF 결과는 추정하지 않고 pending 유지 | ADR-011~014, `04_SECURITY_FINDINGS.md`, `community/README.md`, 구현 코드·테스트 |
| AI-021 | 2026-07-13 | OpenAI Codex 및 브라우저 자동 검증 | 변경 전체 품질 게이트와 SEC-031 실제 사용자 흐름, 반응형·오류 비노출 재검증 | 전체 회귀·coverage·정적·공급망·deploy 수치와 실제 브라우저 증적 | 표적 테스트만으로 완료 처리하지 않고 전체 168개와 현재 의존성을 재검사; 실제 이미지 삭제는 임시 QA 데이터로 확인 후 정리 | 168 tests/104.916초, 4,190 statements/94%, Ruff·Bandit·pip-audit·deploy 통과. 이미지 비우기 후 DB·파일, DEBUG 404 본문, 1440/320px overflow와 console을 직접 확인 | `06_TEST_CHECKLIST.md`, `09_REPORT_DRAFT.md`, `12_CORE_CHECKLIST_EXECUTED_2026-07-13.md` |
| AI-022 | 2026-07-13 | OpenAI Codex 및 병렬 UI·공식 API·위치 프라이버시 검토 에이전트 | 첨부 영역 시각 구분과 기본 이미지 widget 정보노출 감사, 거래 약속·자차/대중교통 길찾기 후보 조사 | 저채도 세이지 첨부 UI, 보호된 현재 이미지 widget, 정확한 상호 GPS를 쓰지 않는 약속·ETA 설계안 | “특정 색은 의학적으로 눈이 편하다”는 단정과 정확한 양측 GPS 실시간 공개는 거절. 모노크롬 chrome·원색 상품 사진, 충분한 대비의 저채도 세이지, 보호 URL·일반 문구, 공공 약속장소 수락 후 개별 경로·상대 ETA 범위를 채택; TMAP 연동은 key·quota·약관·동의·보존·법률 검토 전 보류 | widget HTML에서 내부 storage filename·`MEDIA_URL` 비노출을 코드·회귀로 확인. `ListingSecurityTests` 26개, 비계측 전체 170개/102.496초, coverage 계측 170개/103.560초·4,222 statements/94%, check·migration·Ruff·Bandit·diff·CSS 935/935 통과. 지도 가능 범위는 TMAP·Kakao Mobility·NAVER·ODsay와 W3C 공식 문서로 대조했으며 새 브라우저 시각 QA는 수행했다고 주장하지 않음 | `market/forms.py`, `market/templates/market/widgets/protected_listing_image_input.html`, `static/css/site.css`, `00_PROJECT_JOURNAL.md`, `09_REPORT_DRAFT.md` |

## 2026-07-13 제출 단계 기록 원칙

- 보고서 문장·표·PDF 생성에 AI를 사용하면 사용 목적, 사람이 수정한 부분, 원본 코드·테스트와의 대조 결과를 같은 표에 추가한다.
- GitHub URL, 테스트 성공, 제출 시각처럼 외부 상태가 필요한 사실은 AI가 추정하지 않고 사람이 실제 화면·명령 결과로 확인한 뒤 기록한다.
- 7월 13일 예정 작업은 실행 전 성공으로 기재하지 않는다.

## AI 코드 반영 규칙

1. 요구사항과 맞는지 확인한다.
2. 인증·인가·입력 검증·오류 처리·비밀정보 처리를 수동 검토한다.
3. 정상 테스트와 악성 입력 테스트를 추가한다.
4. 정적 분석, 의존성 검사, 시크릿 검사를 통과시킨다.
5. 검증되지 않은 코드와 존재하지 않는 출처는 보고서에 사용하지 않는다.
