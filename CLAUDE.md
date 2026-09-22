# CLAUDE.md

가족 카드 사이트 빌더. 데이터는 `family-wiki/data/` 이고 여기에는 코드만 둔다. 설명은 [README.md](README.md).

- `scripts/cards_data.py` — 적재(`load_local`·`load_remote`)와 스키마 검증.
  - 카드는 일곱 종류다. `data/profiles/*.json`(가족) · `data/projects/*.json`(계획) 은 파일마다 한 장이고,
    `data/daily.json`(하루 요약) · `data/schedule.json`(가족 일정) · `data/timeline.json`(일대기) ·
    `data/travels.json`(여행 지도) · `data/changelog.json`(최근 변경)은 **파일 하나가 한 장**이다.
    없으면 그 섹션만 빈다.
  - 소속 키는 `part` 가 아니라 **`group`** 이다 (기본값 `DEFAULT_GROUP`). `part` 가 남아 있으면 검증이 막는다.
  - 일정 창은 **달력일**이다. `day_window(today, days)` · `events_in_window(schedule, today, days)` 와
    최근 7일(`entries_within`) 은 순수 함수다. family-wiki `scripts/build_schedule.py` 와 **같은 규칙**이어야 한다 —
    어긋나면 사이트와 위키 표가 달라진다.
    - 주말을 건너뛰지 않는다. 업무일 함수(`is_business_day`·`business_window`·`prev_business_day`)는 **없다**.
      가족 일정은 주말이 본체다.
    - `holidays` 는 창 계산에서 빼지 않는다. 날짜 머리에 "공휴일" 표식(`_holiday_mark`)과 목록 아래 한 줄
      (`holiday_note`)에만 쓴다.
    - 사이트 일정은 오늘부터 `SITE_SCHEDULE_DAYS`(3)일이다. 정렬은 `(date, time, label)` 이고 빈 시각이 그날 맨 위.
    - 같은 날 같은 `(label, time, members)` 는 한 줄만 남긴다 — 정렬 뒤에 걸러서 먼저 담긴 **단발**이 이긴다.
    - `_norm_event` 가 내놓는 한 줄의 키와 **순서**는 `build_schedule._window_row` 와 같다:
      `date · end · time · kind · label · members · note · source · recurring · ongoing · done`.
      `source` 가 비면 `WIKI_SOURCE`(가족일정), `done` 은 반복 일정에서 늘 `false`, `end` 는 하루짜리면 `""`.
      테스트가 이 순서를 못 박는다 — 고칠 일이 생기면 family-wiki 쪽과 같이 고친다.
    - `source` 값(`가족일정`·`회사일정`·`gcal:<별칭>`)은 타입만 검사한다. 여기서 목록을 막으면 위키가 캘린더
      별칭을 하나 늘릴 때 일정 섹션이 통째로 사라진다.
    - 끝난 표시는 둘이고 문구가 다르다. 데이터의 `done`(위키 표의 `~~취소선~~`·✅)은 "완료",
      `event_done`(빌드 시각 기준)은 "지남" 이다.
  - 하루 요약은 `daily_days` 가 고른 **어제와 오늘**(달력일) 두 날만 시간순(어제 위, 오늘 아래)으로 그린다. 요약이 없는 날은 빈 블록.
    방의 `count` 는 **선택**이다 — 없으면 건수 칩을 빼고 그린다 (0건이라고 찍지 않는다).
  - `changelog.json` 의 바뀐 카드 이름은 `name` 이다 (레퍼런스의 `target` 도 읽는다). `entries_within` 이 `target` 키로 맞춰 돌려준다.
  - 일정 `kind` 는 아홉 값이다 (`EVENT_KINDS`: 가족·개인·회사·기념일·여행·병원·학교·마감·기타). family-wiki 와 같은 목록이어야 한다.
    새 값을 넣으면 `build_site.EVENT_KIND_CLASS` 에 색 클래스도 같이 넣는다 (테스트가 둘을 대조한다).
  - `profile` 과 `fun` 은 둘 다 `null` 이어도 된다 — 근거가 0인 새 카드는 이름만 있어도 실린다.
  - 일대기 `kind` 는 여덟 값이다 (`TIMELINE_KINDS`: 가족·여행·집·건강·로하·회사·기념일·기타). family-wiki 의
    `build_timeline.py` 와 같은 목록이어야 하고, 새 값을 넣으면 `build_site.TIMELINE_KIND_CLASS` 에 색 클래스도
    같이 넣는다 (테스트가 둘을 대조한다). `note` 는 일정 카드와 같이 **비어 있어야 한다** —
    병원명·금액·괄호는 위키 비고 칸에 남기고 카드로 내보내지 않는다.
  - 여행 `kind` 는 `해외`·`국내` 둘이다. `stops` 는 한 곳 이상이고 `lat` -90~90 · `lon` -180~180 **숫자**다.
    `highlights` 는 다섯 개·각 40자까지, `id` 는 파일 안에서 유일해야 한다 (사유에 id 값을 적지 않는다 —
    지명이 들어 있다). `members` 는 타입만 본다 — 명단 대조는 위키 쪽 일이다 (여기에는 호칭 목록이 없다).
  - `timeline_entries`·`travel_trips`·`trip_stops` 는 순수 함수다. 앞의 둘은 날짜 오름차순으로 정렬하고
    날짜로 읽히지 않는 줄을 버린다. `trip_stops` 는 좌표가 숫자·범위 안인 경유지만 남긴다 —
    검증을 우회한 값이 지도 밖에 찍히지 않게 한 번 더 거는 장치다.
- `scripts/build_site.py` — HTML 렌더링만. 표준 라이브러리, CSS 인라인, JS·CDN 없음. 모든 카드 문자열은 `esc()` 를 거친다.
  - 목록 섹션 순서는 **하루 요약 → 가족 일정 → 일대기 → 여행 지도 → 계획 → 가족 → 최근 변경**.
    앵커 `#projects`·`#timeline`·`#travels` 는 유지한다 (상세 페이지의 "← 목록" 이 그 자리로 돌아온다).
  - 사이트 제목(`<title>`)·히어로·푸터의 그룹 이름은 카드의 `group` 이고, 없으면 `DEFAULT_GROUP` 이다. 코드에 실명을 적지 않는다.
    그룹 이름이 길 수 있어 `.hero-title` 은 `word-break:keep-all` 로 **낱말 사이에서만** 두 줄로 접는다.
  - `render_index(..., now_hm=)` 은 빌드 시각 `HH:MM`. 비우면 오늘 것은 긋지 않는다 (테스트 기본).
  - 기준일은 `render_index(..., today=)` 로 넣는다 (기본 KST 오늘). 테스트가 날짜를 고정하는 자리다.
  - 색상 토큰은 `CSS` 의 `:root` 에 있다. **밝은 하늘·민트 파스텔 팔레트**다 — 하늘색 `--brand:#5FB4E6`,
    민트 `--fun70:#7FD3BE`, 아주 연한 하늘빛 바탕 `--bg:#F2F9FD`, 카드는 흰색 `--card:#FFFFFF`.
    회사 CI 오렌지도 옛 테라코타·세이지도 쓰지 않는다 (테스트가 `#F37321`·`#C05B3E` 류를 막는다).
    라이트가 기준이고 다크는 같은 토큰을 짙은 남청 바탕 위에서 밝힌다.
  - 토큰은 **면용**과 **글자용**으로 갈라 둔다. 파스텔 원색(`--brand`·`--brand70`·`--brand50`·`--fun70`·`--fun50`)은
    면·막대·칩·아바타 전용이고 글자로 쓰지 않는다 — 흰 바탕에서 대비가 2:1 대다.
    글자용(`--ink`·`--ink2`·`--muted`·`--brand-ink`·`--fun`·`--ok`·`--warn`)은 얹히는 면마다 대비 4.5:1 이상이다.
  - 파스텔 면 위의 글자는 `--on-brand`(짙은 남청)·`--on-warn` 이다. **`color:#fff` 를 새로 쓰지 않는다** —
    하늘·민트 칩에 흰 글자를 올리면 대비가 무너진다 (테스트가 `color:#fff` 를 막는다).
  - `--ok`(완료)·`--warn`(경고)은 파스텔로 낮춰도 **색상환에서 60° 이상** 떨어져 있어야 한다. 파스텔은 밝기가
    비슷해져 대비비로는 구분되지 않는다 — 테스트가 색상 거리로 본다.
  - 팔레트를 고치면 `scripts/test_cards_data.py` 의 `사이트_색` 이 WCAG 대비를 숫자로 다시 잰다
    (`TEXT_ON_SURFACE` 가 글자/면 짝 목록이다). 새 글자 토큰을 만들면 그 짝도 같이 적는다.
- **일대기·여행 지도** — 목록에는 일대기 최근 `SITE_TIMELINE_ITEMS`(12)건만 그리고 전체는 `t/timeline.html`,
  여행은 `t/travels.html` 이다. 두 상세 페이지는 **카드가 0건이어도 만든다** — 목록의 "전체 보기" 링크가 깨지지 않게.
  - 일대기는 **최신이 위**다 (연도 → 월 순으로 묶고 각 묶음도 최신 우선). 기간 항목은 `10/7 ~ 10/20`.
  - 여행 지도는 **인라인 SVG** 다. 윤곽선은 `scripts/map_data.py`(생성물)의 `WORLD_PATH`·`KOREA_PATH` 이고
    투영은 등장방형이라 **viewBox 좌표가 곧 경위도**다 (`project_world`·`project_korea` 는 `(lon, -lat)`).
    타일·CDN·JS·웹폰트를 쓰지 않으므로 `file://` 로 열어도 그대로 보인다.
  - **지도 데이터 다시 만들기**: `python3 scripts/make_map_data.py` — 이 스크립트만 네트워크를 쓴다
    (Natural Earth 110m 세계 · 50m 대한민국, 공용 도메인). 자체 Douglas-Peucker 로 상한(세계 150KB ·
    한국 40KB)에 맞을 때까지 줄이고 결과를 커밋한다. 경계는 거의 안 바뀌므로 다시 돌릴 일도 거의 없다.
    순서는 **`make_map_data.py` → 테스트 → 빌드** 다. 생성물에는 **링크를 두지 않는다** (카드 검증기가
    링크를 막고, 테스트가 `map_data.py` 에 `http` 가 없는지 본다). 손으로 고치지 않는다.
  - 핀은 여행 순서로 번호를 붙이고 같은 여행의 경유지는 점선(`.hop`)으로 잇는다. 핀 색은 국내 하늘색
    (`--brand`) · 해외 민트(`--fun70`) 이고 번호 글자는 `--on-brand` 다.
  - 핀 크기는 **viewBox 폭에 비례**한다 (`PIN_R_RATIO`). 한국 인셋은 좁게 그려지므로 `KOREA_PIN_SCALE` 로
    키운다 — 같은 비율로 두면 핀과 번호가 몇 px 로 줄어 읽히지 않는다.
  - 겹친 핀은 **거의 완전히 겹칠 때만**(반지름의 `PIN_OVERLAP` 배 안) 벌린다. 세계 지도에서는 핀 하나가
    수백 km 를 덮어서, 이웃 도시까지 벌리면 핀이 딴 나라에 찍힌다 (리스본·포르투가 그렇다).
    벌린 자리도 늘 viewBox 안이다 — 테스트가 핀 좌표를 박스와 대조한다.
  - 지도 색은 `--map-land`·`--map-line`·`--map-sea` 세 토큰이다. 라이트·다크에서 **역할이 뒤집힌다**
    (라이트는 밝은 땅 + 짙은 윤곽선, 다크는 짙은 땅 + 밝은 윤곽선). 팔레트 값만 쓰고 새 hex 를 늘리지 않으며,
    선/면 대비는 `TEXT_ON_SURFACE` 에 실려 4.5:1 검사를 함께 받는다.
- `scripts/test_cards_data.py` — 검증 규칙과 공개 범위 테스트. **커밋해서 유지한다** (워크플로가 빌드 전에 돌린다).
  `python3 -m unittest discover -s scripts -p 'test_*.py'`
  - 테스트 이름은 한국어다. 픽스처의 사람 이름은 호칭(아빠·엄마·첫째)이고 그룹은 가상("우리집")이다.
  - 임시 폴더만 쓴다. 저장소에 파일을 남기지 않는다.
- **public 저장소·public 사이트다.** 위키 본문·카톡 원문을 넣는 코드를 쓰지 않는다.
  금지 패턴은 `cards_data.py` 의 `FORBIDDEN_*` · `forbidden_patterns()` 다.
  - **정본은 family-wiki 의 `scripts/common.py` `PRIVACY_RULES`** 이고 아홉 규칙
    (링크·키·주민번호·카드번호·전화·이메일·계좌번호·주소·생년월일)을 **그대로 옮긴 것**이다.
    라벨·정규식·주석·`ACCOUNT_DIGITS` 까지 같다. **한쪽을 고치면 둘 다 고친다** — 어긋나면 위키의
    `sync_cards.py --check` 를 통과한 카드가 사이트에서 거부되거나, --check 가 놓친 것이 인터넷에 나간다.
    여기서 규칙을 좁히거나 넓히지 않는다. 고칠 것이 보이면 **정본을 고치고 다시 옮긴다.**
  - 표류는 `정본과_같은_금지_패턴` 테스트가 잡는다 — 옆에 `../family-wiki` 나 `../my-wiki` 클론이 있으면
    라벨·순서·정규식 문자열·플래그·`ACCOUNT_DIGITS` 를 대조하고, 없으면(CI) 대조 없이 통과한다.
    옮길 때는 손으로 베끼지 말고 `common.py` 의 해당 블록 원문을 그대로 떠 온다 — 정본이 자주 움직인다.
  - 규칙 순서가 우선순위다. 앞 규칙이 잡은 자리는 뒤 규칙이 다시 잡지 않는다 (정본 `find_private` 와 같다) —
    전화번호를 "계좌번호" 라고 잘못 알리지 않게 하는 장치다. 계좌번호는 숫자 자릿수(`ACCOUNT_DIGITS`)로 한 번 더 건다.
  - 정본이 정한 경계 둘: 도로명 단독은 `번지`·`호` 가 붙어야 주소다 (조사 `~로` 오탐 방지), 생년월일은
    `생`·`출생`·`생일` 표시가 붙은 날짜만 잡는다 (맨 날짜는 일정 카드의 본체다). 테스트가 둘을 지킨다.
  - 사유에 **걸린 원문도 파일명도 적지 않는다** (`길이 N자` 만, `name` 사유는 값 없이). 사유는 공개 index 하단과
    public 저장소의 Actions 로그에 찍힌다 — 파일명이 곧 사람 호칭이라 적으면 그것이 인터넷에 나간다.
- **건너뛴 카드를 알릴 때 파일명을 쓰지 않는다** (2026-09-22 보안 검토).
  - 공개 index 하단 박스(`skipped_html`)는 **종류와 건수만** 찍는다 — 사유도 넣지 않는다.
  - 로그(`warn`)도 `CARD_KIND_KO` 의 종류명만 쓴다. 어느 파일인지는 로컬 빌드에서 확인한다.
  - 새 사유를 만들 때 카드 값·파일명·경로를 넣지 않는다. 테스트가 `CARDS_FORBIDDEN_NAMES` 에 든 이름을
    파일명으로 둔 카드로 HTML·stdout·stderr 를 끝에서 끝까지 확인한다.
- **비고(`events[].note`·`entries[].note`)는 카드에 싣지 않는다** (docs/SCHEDULE_SCHEMA.md ·
  docs/TIMELINE_SCHEMA.md · team-plan §3). 검증기가 비어 있지 않은
  `note` 를 거부하고 `schedule_html`·`timeline_item_html` 은 그리지 않는다. 키는 위키 계약 때문에 정규형에 남겨 두지만 화면에는 안 나온다.
- **코드에 실명을 두지 않는다.** 카드에 실리면 안 되는 이름은 `CARDS_FORBIDDEN_NAMES` 시크릿(쉼표 구분)에서 읽는다.
  비어 있으면 이름 검사는 건너뛴다.
- **이모지 반응 집계는 싣지 않는다.** 데이터에 키가 남아 있어도 검증은 통과시키고 렌더에서 무시한다.
- 한 건이 어긋나면 그 파일만 건너뛴다. 0건이어도 빌드는 성공한다.
  읽기 실패도 같다 — `load_local` 은 `read_text` 를 감싸서 UTF-8 이 아닌 파일 하나에 빌드가 죽지 않게 한다.
- 로컬 확인: `python3 scripts/build_site.py --local ../family-wiki --out _site` (위키 클론 이름이 다르면 그 경로를 준다).
- 커밋 메시지는 gitmoji 로 시작한다 (✨ 기능, 🐛 버그, ♻️ 리팩터링, 📝 문서, 🔧 설정).
