# 핵심 체크리스트 실제 수행 결과 - 2026-07-13

`11_CORE_SUBMISSION_CHECKLIST.md`의 18개 항목을 Codex가 현재 코드에서 직접 실행·검토한 결과다. 일부 통과를 전체 통과로 표시하지 않았으며, 알려진 결함과 외부 제출 작업은 그대로 `FAIL`·`BLOCKED`로 남겼다.

## 검사 기준

- 대상 commit: `34676427c50af7395961019ead097030d352ebe8`
- 완료 시각: `2026-07-13 16:37:03 +09:00`
- 환경: Windows, Python 3.12.13, Django 5.2.16
- 브라우저 실측: 1440×1000, 320×800
- 판정: `PASS` / `FAIL` / `BLOCKED`

## 수행 결과

| ID | 상태 | 직접 수행한 결과·증적 | 실패·차단 사유 / 다음 조치 |
|---|:---:|---|---|
| A-01 | **PASS** | `requirements-dev.lock --require-hashes`를 빈 target에 설치 성공(102개 top-level entry). Git tracked clean copy에서 전체 migration과 `manage.py check` 성공 | 임시 검증 디렉터리는 확인 후 삭제 |
| A-02 | **PASS** | HEAD SHA 확인 후 Django **120개**, 82.231초, 실패·오류 0. 동일 Python 코드의 coverage **3,169 statements / 223 miss / 93%** | 코드 변경 시 전체 재실행 |
| A-03 | **FAIL** | 기존 이미지 삭제 `image-clear=on`에서 SEC-031 500 재현 이력이 있고 현재 코드가 미수정. 관련 전용 회귀도 없음 | `FileField.save_form_data()` 정규화와 유지·교체·삭제·동시 선택·악성 파일 회귀 필요 |
| A-04 | **PASS** | 120개 tests에서 인증·IDOR·CSRF·Mass Assignment·차단·송금 원자성·멱등성·원장 불변성 회귀 통과 | SEC-031·032 전용 분기는 A-03·A-06에서 별도 FAIL |
| A-05 | **PASS** | Ruff lint 0, format 27 files 통과, Bandit 2,996줄·이슈 0, pip-audit 알려진 취약점 0 | pip-audit는 UTF-8 프로세스 모드로 최종 exit 0 확인 |
| A-06 | **FAIL** | production `check --deploy --fail-level WARNING`은 문제 0. DEBUG false 수동 대조에서는 기술 문자열 비노출 | 400·403·404·500·CSRF 본문·header 자동 회귀와 standalone 500이 없어 최종 PASS 불가 |
| A-07 | **PASS** | Git 현재 파일·전체 이력에서 AWS/GitHub token·private key·실제 로컬 절대경로 패턴 0, DB·media·upload·log 추적 0 | 패턴 기반 검사이므로 Public push 전 사람의 diff·GitHub secret scan 재확인 |
| B-01 | **PASS** | 가입·로그인·POST 로그아웃·정지 계정 회귀가 120 tests에 포함되어 통과. 로그인 페이지 password input·외부 asset 0·overflow 0 확인 | 최종 발표 계정으로 한 번 더 수동 확인 권장 |
| B-02 | **FAIL** | 등록·조회·IDOR·상태·일반 이미지 검증은 통과했으나 기존 이미지 삭제가 SEC-031 500 | A-03 수정 뒤 상품 전체 흐름 재시험 |
| B-03 | **PASS** | ORM 검색·SQLi/XSS 문자열·필터·정렬·비공개 제외 회귀 통과. 홈 검색·필터 DOM 확인 | 최종 데이터로 결과 화면 캡처 필요 |
| B-04 | **PASS** | 대화 참여자·발신자 서버결정·제3자 접근·차단·pagination 회귀 통과 | 발표용 A/B/C 계정 수동 시나리오 권장 |
| B-05 | **PASS** | 신고 대상 파생·사용자/상품 차단·관리자 forged action·보호 계정·증거 보존 회귀 통과 | Public 배포의 실제 관리자 URL은 별도 확인 |
| B-06 | **PASS** | DEMO POINT 잔액·이중 원장·멱등·rollback·append-only 회귀 통과 | 실제 금융서비스가 아니라는 고지 유지 |
| B-07 | **FAIL** | 홈 1440px: 4열·overflow 0. 홈 320px: 1열·overflow 0·primary button 44px. 로그인·안전 페이지 overflow 0, console error/warn 0, 외부 asset 0. 상품 사진 `filter: none` | 자동 브라우저에서 실제 Tab focus 이동을 확인하지 못함. 사용자 키보드·200% 확대 확인 필요 |
| E-01 | **PASS** | 보고서 초안에 요구사항 분석·시스템 설계·구현·테스트·유지보수와 선택 이유가 있고 Markdown link·UTF-8 검사 통과 | 최종 PDF 렌더는 E-04에서 별도 차단 |
| E-02 | **FAIL** | SEC-001~032와 AI-001~018 기록 존재. 그러나 SEC-031·032가 Open이라 변경·재시험 증적이 없음 | 두 항목 수정·재시험 후 보고서 상태 갱신 |
| E-03 | **BLOCKED** | README와 workflow 파일은 존재하고 clean tracked copy의 migration/check 성공 | Git remote 없음. Public GitHub·로그아웃 공개·Actions/CodeQL·원격 SHA 확인 필요 |
| E-04 | **BLOCKED** | 파일명·기한·placeholder 검사 규칙은 문서화됨 | 반·이름·전화 뒤 4자리, GitHub URL, 최종 PDF와 LMS 제출 권한이 필요 |

## 집계와 결론

- PASS: **11 / 18**
- FAIL: **5 / 18**
- BLOCKED: **2 / 18**
- 최종 승인: **NOT READY**

제출 전에 최소한 SEC-031 이미지 삭제, SEC-032 오류 비노출 자동 회귀, 실제 키보드 확인, 보안약점 수정·재시험, Public GitHub, 최종 PDF·LMS를 완료해야 한다. 기존 120개 통과만으로 이 실패·차단 항목을 덮지 않는다.
