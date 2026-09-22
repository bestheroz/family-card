# family-card — 가족 카드 사이트

**https://bestheroz.github.io/family-card/**

> ## ⚠️ 먼저 읽을 것 — 이 사이트는 인터넷에 공개된다
>
> 이 저장소와 사이트는 **public** 이다. 링크를 아는 사람은 누구나 본다. 검색 엔진 색인은 `noindex` 로 막았지만
> 그것은 색인만 막는 장치이고 접근을 막지 못한다. **가족 정보가 인터넷에 나간다는 뜻이다.**
>
> 그래서 카드에는 **호칭**(아빠·엄마·첫째)을 쓰고 실명을 쓰지 않는 편이 안전하다.
> 생년월일·학교명·주소·전화번호·병명·금액·링크는 검증기가 아예 막는다 (아래 "무엇이 나가나").
>
> **공개하고 싶지 않다면 선택지는 둘이다.**
>
> 1. **저장소를 private 으로 두고 GitHub Pro 로 Pages 를 켠다** — 유료 플랜에서는 private 저장소도 Pages 를 쓸 수 있다.
>    다만 **사이트 URL 자체는 여전히 공개**다 (Pages 에 접근 제어가 붙지 않는다). 저장소 코드만 가려지는 것이고
>    사이트는 링크를 아는 사람이 볼 수 있다. 공개 범위 문제를 해결해 주지 않는다.
> 2. **배포하지 않고 로컬 빌드만 쓴다** (가장 안전하다). Pages 를 아예 켜지 않고 필요할 때 손으로 그린다.
>
>    ```bash
>    python3 scripts/build_site.py --local ../family-wiki --out _site
>    open _site/index.html
>    ```
>
>    CSS 가 인라인이고 JS·CDN 이 없어서 `file://` 로 열어도 그대로 보인다.

[`family-wiki`](https://github.com/bestheroz/family-wiki)(private) 의 `data/` 카드 JSON 을 읽어
정적 HTML 로 그리고 GitHub Pages 로 배포한다. 이 저장소에는 **코드만** 있고 데이터는 없다 — 카드 내용은 위키 저장소에서 고친다.

## 어떻게 돌아가나

```
family-wiki/data/profiles/*.json  가족 카드   ─┐
family-wiki/data/projects/*.json  계획 카드   ─┤
family-wiki/data/daily.json       하루 요약   ─┤
family-wiki/data/schedule.json    가족 일정   ─┼→ cards_data.py (검증) → build_site.py → _site/ → GitHub Pages
family-wiki/data/timeline.json    일대기     ─┤
family-wiki/data/travels.json     여행 지도   ─┤
family-wiki/data/changelog.json   최근 변경   ─┘
```

목록 페이지의 섹션 순서는 **하루 요약 → 가족 일정 → 일대기 → 여행 지도 → 계획 → 가족 → 최근 변경** 이다.
어제·오늘 있었던 일이 맨 위, 곧 있을 일이 그 다음, 지나온 일과 잘 안 바뀌는 카드가 아래로 간다.

- **하루 요약** — `daily.json` 에서 **어제와 오늘**, 달력일 두 날만 시간순(어제 → 오늘)으로 그린다. 요약이 없는 날은 "아직 없다"로 둔다.
- **가족 일정** — **오늘부터 달력일 3일**(오늘·내일·모레)이다. **주말을 건너뛰지 않는다** — 가족 일정은 주말이 본체다.
  공휴일(`holidays`)도 창에서 빼지 않고 날짜 머리에 "공휴일" 표식만 붙인다. 빌드 시각 기준 **지난 항목은 취소선**을 긋는다.
- **일대기** — 가족사에 남을 일(이사·여행·입학·출산·큰 병치레 …)을 연도·월로 묶은 세로 타임라인이다.
  목록에는 **최근 12건**과 "전체 보기" 링크가 있고 전체는 `t/timeline.html` 한 장이다. 구분은 여덟 가지
  (`가족`·`여행`·`집`·`건강`·`로하`·`회사`·`기념일`·`기타`)이고 **비고(`note`)는 싣지 않는다**.
- **여행 지도** — 다녀온 곳을 **인라인 SVG** 지도에 찍는다. 세계 지도에 해외 여행지(민트 핀), 한국 인셋에
  국내 여행지(하늘색 핀)를 그리고 핀 번호는 여행 순서다. 같은 여행의 경유지는 점선으로 잇고 핀에 마우스를
  올리면 지명이 보인다. 지도 아래에 기간·여행지·누구·하이라이트 목록이 있고 전체는 `t/travels.html` 이다.
  **외부 타일·CDN·JS 를 쓰지 않는다** — 윤곽선은 `scripts/map_data.py` 에 굳혀 둔 Natural Earth(공용 도메인)
  경로 문자열이고 빌드는 네트워크가 필요 없다.
- **계획** — 여행·이사·목표 같은 가족 계획이다. 진행률은 마일스톤 완료 수로만 계산한다.
- **최근 변경** — **7일** 치만 그린다.

`daily.json` · `schedule.json` · `timeline.json` · `travels.json` · `changelog.json` 은 각각 **파일 하나**이고,
없으면 그 섹션만 빈 상태로 나온다.

## 어떤 모양인가

밝은 **하늘색·민트 파스텔**이다. 아주 연한 하늘빛 바탕에 흰 카드를 얹고, 대표색은 하늘색(`--brand:#5FB4E6`),
재미 코너는 민트다. 파스텔 원색은 면·막대·칩·아바타에만 쓰고, 글자에는 대비 4.5:1 이상인 짙은 톤
(`--brand-ink:#14607F` · `--fun:#176F5F` · `--muted:#59717E`)을 쓴다 — 테스트가 라이트·다크 두 모드에서
WCAG 대비를 숫자로 잰다. 다크 모드는 같은 토큰을 짙은 남청 바탕 위에서 밝힌 하늘·민트다.
글꼴은 기기에 있는 것만 쓰고(웹폰트 없음) CSS 는 인라인이다.

`.github/workflows/pages.yml` 은 family-wiki 가 보내는 `wiki-data-updated` 신호를 받으면 돈다 — 카드 데이터가 바뀐 순간에만 다시 그린다.
그 밖에 매일 09:37 KST 안전망, 수동 실행(Actions → Run workflow), `scripts/` 변경 push 때도 돈다. 빌드 전에 `scripts/test_*.py` 를 먼저 돌린다.

## 처음 설정 (한 번만)

1. **Pages** — Settings → Pages → Build and deployment → Source = **GitHub Actions**.
   (로컬 빌드만 쓸 생각이면 이 단계를 건너뛴다. 위 경고를 다시 읽는다.)
2. **Secret `WIKI_READ_TOKEN`** — Settings → Secrets and variables → Actions → Secrets.
   fine-grained PAT, Resource owner = **개인 계정**, 저장소 `family-wiki`, **Contents: Read**.
3. **family-wiki 의 `CARDS_DISPATCH_TOKEN`** — fine-grained PAT, Resource owner = 개인 계정, 저장소 `family-card`,
   **Contents: Read and write**. 데이터 변경을 즉시 반영하는 주 경로다. 없거나 만료되면 하루 1회 안전망으로만 갱신된다.
   만료되면 family-wiki 의 `notify-cards.yml` 이 실패해 빨간불로 알려 준다.
4. (선택) **`CARDS_FORBIDDEN_NAMES`** 시크릿 — 카드에 실리면 안 되는 이름을 쉼표로 구분해 넣는다.
   이 저장소는 public 이라 코드에 이름을 두지 않는다. 비워 두면 이름 검사만 건너뛴다.

## 무엇이 나가나

- 무엇을 싣고 뺄지는 family-wiki 의 `docs/PRIVACY.md` 와 스키마 일곱 장(`PROFILE_SCHEMA.md` · `PROJECT_SCHEMA.md` ·
  `SCHEDULE_SCHEMA.md` · `CHANGELOG_SCHEMA.md` · `DAILY_SCHEMA.md` · `TIMELINE_SCHEMA.md` · `TRAVELS_SCHEMA.md`)이 정한다
- **링크**(`https://` 없는 도메인·`t.me/…`·`bit.ly/…` 포함) **· 전화 · 이메일 · 주민번호 · 카드번호 · 계좌번호 ·
  토큰 · 주소 형태 · 생년월일 형태**가 있거나 원문 인용 키(`raw_quote`·`quotes`)·성별 추정 키가 있으면
  **그 파일만** 건너뛴다. 공개 사이트에는 **어느 종류가 몇 건 빠졌는지만** 적는다 — 파일명도 사유도 싣지 않는다
  (파일명이 곧 호칭이다). 어느 파일인지는 로컬 빌드에서 확인한다
- 이 규칙 아홉 개는 family-wiki 의 `scripts/common.py` `PRIVACY_RULES` 를 그대로 옮긴 것이다 — 위키에서
  `python3 scripts/sync_cards.py --check` 를 돌리면 사이트가 거부할 카드를 **푸시 전에** 알 수 있다
- **하루 요약** — 날짜별·카톡 방별로 정리할 때 LLM 이 쓴 한 줄 요약 몇 개. **원문 인용·링크 없음** (`DAILY_SCHEMA.md`)
- **가족 일정** — 날짜·종류(`가족`·`개인`·`회사`·`기념일`·`여행`·`병원`·`학교`·`마감`·`기타`)·한 줄 라벨·누구.
  병원은 구분만 적고 **병명은 싣지 않는다**. **비고(`note`)는 아예 싣지 않는다** — 값이 있으면 그 파일을 거부한다
- **일대기** — 날짜·구분·한 줄 제목·누구. 병원명·금액·괄호는 위키 비고 칸에 두고 **비고는 싣지 않는다**
  (값이 있으면 그 파일을 거부한다)
- **여행 지도** — 기간·여행지·나라·누구·하이라이트(각 40자 이내, 다섯 개까지)와 **도시 수준 근사 좌표**다.
  숙소명·예약번호·금액은 싣지 않는다. 좌표는 도시를 가리키고 집을 가리키지 않는다
- **최근 변경** — 어느 카드가 언제 무엇 때문에 바뀌었는지 한 줄. 위키 본문을 옮기지 않는다
- **이모지 반응 집계는 싣지 않는다** — 데이터에 남아 있어도 카드에 그리지 않는다
- MBTI·나이대는 추측이라 근거 강도가 붙는다. 재미 코너를 빼려면 그 카드 JSON 의 `fun` 을 `null` 로 둔다.
  근거가 아직 없으면 `profile` 도 `null` 로 둘 수 있다 (이름만 있는 카드)
- 카드가 0건이어도 사이트는 만들어진다

## 로컬에서 확인

```bash
python3 -m unittest discover -s scripts -p 'test_*.py'             # 검증 규칙 테스트
python3 scripts/build_site.py --local ../family-wiki --out _site    # 옆에 위키 클론이 있을 때, 토큰 불필요
open _site/index.html
```

지도 윤곽선(`scripts/map_data.py`)은 **생성물**이고 커밋해서 쓴다. 다시 만들 일이 생기면
`python3 scripts/make_map_data.py` 를 돌린다 — 그때만 네트워크를 쓴다 (Natural Earth, 공용 도메인).

위키 클론 디렉터리 이름이 `family-wiki` 가 아닐 수도 있다 (예: `../my-wiki`) — 그때는 `--local ../my-wiki` 처럼 실제 경로를 준다.
`--local` 에 경로를 생략하면 `../family-wiki` 를 본다.

표준 라이브러리만 쓴다 (Python 3.12+, CI 는 3.14 로 검증). `_site/` 는 커밋하지 않는다.
