# CLAUDE.md

가족 카드 사이트 빌더. 데이터는 `family-wiki/data/` 이고 여기에는 코드만 둔다. 설명은 [README.md](README.md).

- `scripts/cards_data.py` — 적재(`load_local`·`load_remote`)와 스키마 검증.
  - 카드는 다섯 종류다. `data/profiles/*.json`(가족) · `data/projects/*.json`(계획) 은 파일마다 한 장이고,
    `data/daily.json`(하루 요약) · `data/schedule.json`(가족 일정) · `data/changelog.json`(최근 변경)은
    **파일 하나가 한 장**이다. 없으면 그 섹션만 빈다.
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
- `scripts/build_site.py` — HTML 렌더링만. 표준 라이브러리, CSS 인라인, JS·CDN 없음. 모든 카드 문자열은 `esc()` 를 거친다.
  - 목록 섹션 순서는 **하루 요약 → 가족 일정 → 계획 → 가족 → 최근 변경**. 계획 앵커 `#projects` 는 유지한다.
  - 사이트 제목·히어로·푸터의 그룹 이름은 카드의 `group` 이고, 없으면 `DEFAULT_GROUP` 이다. 코드에 실명을 적지 않는다.
  - `render_index(..., now_hm=)` 은 빌드 시각 `HH:MM`. 비우면 오늘 것은 긋지 않는다 (테스트 기본).
  - 기준일은 `render_index(..., today=)` 로 넣는다 (기본 KST 오늘). 테스트가 날짜를 고정하는 자리다.
  - 색상 토큰은 `CSS` 의 `:root` 에 있다. **따뜻한 가족 팔레트**다 — 테라코타 `--brand:#C05B3E`, 세이지 `--fun:#546E50`,
    크림 바탕 `--bg:#FAF6F1`. 회사 CI 오렌지를 쓰지 않는다 (테스트가 `#F37321` 류를 막는다). 라이트가 기준이고 다크는 같은 토큰을 밝힌다.
  - 작은 글자에는 `--brand` 대신 `--brand-ink` 를 쓴다 — 라이트 바탕에서 `--brand` 는 본문 텍스트 대비가 모자란다.
    글자용 토큰(`--brand-ink`·`--fun`·`--muted`·`--ink2`)은 대비 4.5:1 이상으로 골랐다.
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
- **비고(`events[].note`)는 카드에 싣지 않는다** (docs/SCHEDULE_SCHEMA.md · team-plan §3). 검증기가 비어 있지 않은
  `note` 를 거부하고 `schedule_html` 은 그리지 않는다. 키는 위키 계약 때문에 정규형에 남겨 두지만 화면에는 안 나온다.
- **코드에 실명을 두지 않는다.** 카드에 실리면 안 되는 이름은 `CARDS_FORBIDDEN_NAMES` 시크릿(쉼표 구분)에서 읽는다.
  비어 있으면 이름 검사는 건너뛴다.
- **이모지 반응 집계는 싣지 않는다.** 데이터에 키가 남아 있어도 검증은 통과시키고 렌더에서 무시한다.
- 한 건이 어긋나면 그 파일만 건너뛴다. 0건이어도 빌드는 성공한다.
  읽기 실패도 같다 — `load_local` 은 `read_text` 를 감싸서 UTF-8 이 아닌 파일 하나에 빌드가 죽지 않게 한다.
- 로컬 확인: `python3 scripts/build_site.py --local ../family-wiki --out _site` (위키 클론 이름이 다르면 그 경로를 준다).
- 커밋 메시지는 gitmoji 로 시작한다 (✨ 기능, 🐛 버그, ♻️ 리팩터링, 📝 문서, 🔧 설정).
