# 맘곁 태교 — 이론편

> 사주당 이씨와 오늘의 의학이 같은 자리에서 만난다
> 권의철 · 최소라 공저 · 2026년 4월 28일
> 펴낸곳 : 바비즈코리아

이 저장소는 『맘곁 태교 — 이론편』의 원고와 정적 HTML 빌드를 담는다.

## 읽기

- 웹: [`dist/book.html`](dist/book.html) (또는 GitHub Pages 활성화 시 루트 URL)
- 원고 마크다운: [`docs/`](docs/) — 들어가며 / 1–10장 / 닫으며 / 부록 A·B·C·D·E

## 구조

```
docs/                 # 본문·부록 마크다운 원고
reviews/              # 검수 자료(의학 검수자 패키지·톤 가이드 등)
dist/                 # 빌드된 HTML (GitHub Pages 배포 대상)
_build_html.py        # 마크다운 → 단일 HTML 빌더
CLAUDE.md             # 프로젝트 메모리 / 톤 가이드
```

## 빌드

```bash
python3 _build_html.py
```

`dist/book.html`(본문)과 `dist/index.html`(루트 URL용 리다이렉트)이 갱신된다.

## GitHub Pages

이 저장소를 GitHub에 push한 뒤 **Settings → Pages**에서

- Source: `Deploy from a branch`
- Branch: `main` / `/dist`

로 설정하면 `https://<user>.github.io/<repo>/` 에서 책이 열린다.
