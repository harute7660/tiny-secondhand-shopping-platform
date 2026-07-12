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
