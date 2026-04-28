# 맘곁 태교 — 이론편

> 사주당 이씨와 오늘의 의학이 같은 자리에서 만난다
> 권의철 · 최소라 공저 · 2026년 4월 28일
> 펴낸곳 : 바비즈코리아

이 저장소는 『맘곁 태교 — 이론편』의 원고와 정적 HTML 빌드를 담는다.
GitHub Pages가 [`docs/`](docs/) 폴더를 그대로 서빙한다.

## 읽기

- 웹(GitHub Pages): `https://<user>.github.io/<repo>/` — 자동으로 [`docs/book.html`](docs/book.html)로 이동
- 로컬 파일: [`docs/book.html`](docs/book.html)
- 원고 마크다운: [`docs/`](docs/) 안의 `*.md` 파일들 (들어가며 / 1–10장 / 닫으며 / 부록 A·B·C·D·E)

## 구조

```
docs/                 # 마크다운 원고 + 빌드된 HTML (GitHub Pages 서빙 대상)
  book.html           # 본문 단일 HTML
  index.html          # ./book.html 으로 자동 이동(루트 URL용)
  .nojekyll           # Jekyll 처리 비활성화 — .md 소스가 그대로 보존됨
  *.md                # 각 장·부록·들어가며·닫으며의 원고
reviews/              # 검수 자료(의학 검수자 패키지·톤 가이드 등)
_build_html.py        # 마크다운 → 단일 HTML 빌더
CLAUDE.md             # 프로젝트 메모리 / 톤 가이드
```

## 빌드

```bash
python3 _build_html.py
```

빌더는 [`docs/`](docs/) 안의 마크다운을 읽어 같은 폴더에 `book.html`·`index.html`·`.nojekyll`을 갱신한다. 별도 dist 폴더는 사용하지 않는다.

## GitHub Pages 설정

저장소 **Settings → Pages**:

- Source: `Deploy from a branch`
- Branch: `main` / **Folder: `/docs`**

push 후 1–3분 안에 `https://<user>.github.io/<repo>/` 에서 책이 열린다.

## 업데이트 흐름

원고 수정 후:

```bash
python3 _build_html.py
git add .
git commit -m "수정 내용 한 줄 메모"
git push
```

push 즉시 GitHub Pages가 자동 재배포한다.
