# 한 줄 태담 위젯 — 계약 테스트

`docs/practice-modern.html` 안의 태담 위젯이 **Task 2 Revision v3.1 FINAL MVP CONTRACT** 를
지키는지 실제 Chromium 에서 검증합니다. 문자열 검색이 아니라 브라우저 조작 기반입니다.

## 실행

가상환경은 **저장소 바깥**에 만듭니다. 이 저장소의 `.gitignore` 에는 `.venv/` 가 없어서
안에 만들면 untracked 파일로 노출됩니다.

```bash
# 저장소 루트에서
VENV=~/.venvs/taegyo-tests            # 저장소 바깥 아무 경로
python3 -m venv "$VENV"
"$VENV/bin/pip" install -r tests/requirements.txt
"$VENV/bin/playwright" install chromium

python3 _build_html.py                # 산출물을 먼저 만든다
"$VENV/bin/python" tests/test_taedam.py
```

번호로 일부만 돌릴 수 있습니다.

```bash
"$VENV/bin/python" tests/test_taedam.py 30 31 32
```

가상환경과 브라우저 바이너리는 커밋하지 않습니다.

## 무엇을 검증하나

| 묶음 | 내용 |
|---|---|
| 길이 | `trimmed.length` (UTF-16 code unit) 1..300. `Array.from`·`Intl.Segmenter` 부재 |
| 보관 | `mg_taegyo_draft_v1`, TTL 72h, `updatedAt` 은 실제 편집에서만 갱신, 만료분 미노출 |
| 삭제 | 명시적 확인으로만. 빈 입력은 보관본을 지우지 않는다. 실패를 성공처럼 말하지 않는다 |
| 충돌 | 다른 탭이 같은 키를 바꿔도 조용히 덮어쓰지 않는다 |
| 클립보드 | user activation 안에서 호출, 3단 폴백, degraded mode 에서도 동작 |
| 보안 | 본문이 URL·네트워크로 나가지 않음, HTML 로 렌더되지 않음, 외부 스크립트 0 |
| 접근성 | textarea 접근 가능한 이름, 다이얼로그 focus trap·Escape·포커스 복원, WCAG 대비 |

## 주의

- 테스트는 `docs/` 를 임시 정적 서버로 서빙합니다. 네트워크 접근이 필요 없습니다.
- 실기기 클립보드(카카오톡·인스타그램 인앱브라우저 → 외부 브라우저 전환) 검증은
  자동화 범위 밖이며 **릴리스 게이트(K-1)** 로 남아 있습니다.
- 위젯을 고칠 때는 `_build_html.py` 만 수정하고 `python3 _build_html.py` 로 재생성하세요.
  `docs/*.html` 은 생성물이라 직접 편집하면 다음 빌드에 지워집니다.
