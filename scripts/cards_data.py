#!/usr/bin/env python3
"""family-wiki 의 data/ 카드 JSON 을 읽고 스키마를 검증한다 (build_site.py 가 쓴다).

데이터는 family-wiki(private) 의 일곱 종류다.

    data/profiles/*.json   가족 카드            docs/PROFILE_SCHEMA.md
    data/projects/*.json   계획 카드            docs/PROJECT_SCHEMA.md
    data/schedule.json     가족 일정 (한 파일)   docs/SCHEDULE_SCHEMA.md
    data/changelog.json    최근 변경 (한 파일)   docs/CHANGELOG_SCHEMA.md
    data/daily.json        하루 요약 (한 파일)   docs/DAILY_SCHEMA.md
    data/timeline.json     일대기   (한 파일)   docs/TIMELINE_SCHEMA.md
    data/travels.json      여행 지도 (한 파일)   docs/TRAVELS_SCHEMA.md

위키 본문(wiki/·raw/)은 읽지 않는다 — 카드는 사람이 공개 범위를 골라 다시 쓴 요약이다.
공개 범위는 그 저장소의 docs/PRIVACY.md.

환경변수
  GH_TOKEN               family-wiki 를 읽을 PAT — WIKI_READ_TOKEN (Contents: Read)
  ORG                    저장소 소유자 로그인 (기본 bestheroz — 개인 계정)
  WIKI_REPO              데이터 저장소       (기본 family-wiki)
  WIKI_REF               브랜치              (기본 main)
  CARDS_FORBIDDEN_NAMES  카드에 실으면 안 되는 사람 이름, 쉼표 구분 (비우면 이름 검사를 건너뛴다)

설계
- 표준 라이브러리만 사용한다.
- 카드 한 건이 스키마에 어긋나면 **그 파일만 건너뛰고** 사유를 남긴다. 한 파일의 실수로
  전체 카드가 사라지지 않게. 일정·변경·요약은 파일이 하나라 그 섹션만 빠진다.
- `schedule.json`·`changelog.json`·`daily.json`·`timeline.json`·`travels.json` 은 **없어도 정상**이다
  (경고 없이 그 섹션만 비운다).
- 일정 창은 **달력일**이다 (`day_window`·`events_in_window`). 가족 일정은 주말이 본체라
  업무일 창을 쓰지 않는다. 사이트는 오늘부터 달력일 3일(`SITE_SCHEDULE_DAYS`, 오늘·내일·모레)을
  그리고, 빌드 시각 기준 **지난 항목은 취소선**(`event_done`)을 긋는다.
  `holidays` 는 창 계산에서 빼지 않는다 — 날짜 머리에 "공휴일" 표식을 붙이는 데만 쓴다.
  이 두 함수는 family-wiki 의 `scripts/build_schedule.py` 와 **같은 규칙**이어야 한다.
  한쪽을 고치면 다른 쪽도 고친다 — 어긋나면 사이트와 위키 표가 달라진다.
- `daily.json` 은 날짜별 요약 묶음이다. 사이트는 **어제와 오늘** 두 날만 그린다 (`daily_days`) —
  저녁에 봐도 아침에 봐도 덮이게. 여기서도 달력일이다.
- 카드 JSON 의 소속 키는 `group` 이다 (값 예: 기본값 `DEFAULT_GROUP`). 레퍼런스의 `part` 는 쓰지 않는다.
- 이 저장소는 public 이고 사이트는 인터넷에 공개된다. 카드에 실으면 안 되는 이름은 코드가 아니라
  `CARDS_FORBIDDEN_NAMES` 시크릿에 둔다 — 소스에 실명을 적지 않는다.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta, timezone
from email.message import Message

API = "https://api.github.com"
KST = timezone(timedelta(hours=9), "KST")


class ApiError(Exception):
    """GitHub API 호출 실패."""


def warn(msg: str) -> None:
    print(f"::warning::{msg}" if os.environ.get("GITHUB_ACTIONS") else f"경고: {msg}", file=sys.stderr)


class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    """urllib 은 호스트가 바뀌어도 Authorization 을 넘긴다 — api.github.com 밖으로는 따라가지 않는다."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        if urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(API).netloc:
            raise ApiError(f"외부 호스트로의 리다이렉트 거부: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_SameHostRedirect)


class GitHub:
    """Contents API 읽기 전용 최소 클라이언트."""

    def __init__(self, token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "family-card-site-builder",
        }

    def get(self, path: str, params: dict[str, object] | None = None) -> tuple[object, Message]:
        # 파일명이 한글이면 ASCII 가 아니라 putrequest 에서 실패한다 — 경로 세그먼트를 퍼센트 인코딩한다.
        url = f"{API}{urllib.parse.quote(path, safe='/')}" + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(url, headers=self._headers)
        for attempt in range(1, 4):
            try:
                with _OPENER.open(req, timeout=30) as resp:
                    return json.load(resp), resp.headers
            except urllib.error.HTTPError as e:
                rate_limited = e.code == 429 or (e.code == 403 and e.headers.get("X-RateLimit-Remaining") == "0")
                if (e.code >= 500 or rate_limited) and attempt < 3:
                    time.sleep(2**attempt)
                    continue
                # 한 줄로 접는다 — ::error:: 주석은 첫 줄만 보여 준다.
                body = " ".join(e.read().decode("utf-8", errors="replace").split())[:300]
                if e.code == 401:
                    # "Bad credentials" 는 권한 부족(403·404)이 아니라 토큰 문자열 자체를 못 알아본 것이다.
                    # 시크릿에 토큰만 들어갔는지(접두어·공백·따옴표 없이), 폐기·만료되지 않았는지 본다 (2026-09-22).
                    raise ApiError(
                        f"HTTP 401 {path}: 토큰이 유효하지 않다 (Bad credentials). WIKI_READ_TOKEN 시크릿 값이 "
                        f"토큰 문자열 그대로인지, 폐기·만료되지 않았는지 확인한다. 로컬 확인: "
                        f"curl -sS -H 'Authorization: Bearer $TOKEN' https://api.github.com/user"
                    ) from e
                raise ApiError(f"HTTP {e.code} {path}: {body}") from e
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise ApiError(f"연결 실패 {path}: {e}") from e
        raise AssertionError("unreachable")


SCHEMA_VERSION = 1
DEFAULT_GROUP = "행복이 가득한 주니요미로하네"
BANNER = "MBTI·나이대는 추측이다. 말투 뱃지는 관측값이다. 관찰된 성향과 재미 코너를 섞어 읽지 않는다."

# ── 검증 규칙 (family-wiki/docs/PROFILE_SCHEMA.md · PROJECT_SCHEMA.md · PRIVACY.md) ───────────────
# 중첩 어디에 있어도 거부하는 키. 원문 인용과 성별 추정을 막는다.
FORBIDDEN_KEY_EXACT = ("raw_quote", "quotes", "gender", "성별")
FORBIDDEN_KEY_PREFIX = ("samples_",)

# JSON 전체를 문자열로 훑어 찾는 금지 패턴. 링크는 종류를 가리지 않고 막는다 — 카드에 링크를 싣지 않는다.
#
# **정본은 family-wiki 의 `scripts/common.py` `PRIVACY_RULES`** 이고 아홉 규칙 전부를 그대로 옮긴 것이다
# (라벨·정규식·주석·`ACCOUNT_DIGITS` 까지). **한쪽을 고치면 둘 다 고친다** — 어긋나면 위키의
# `sync_cards.py --check` 를 통과한 카드가 사이트에서 거부되거나, 반대로 --check 가 놓친 것이 인터넷에 나간다.
# 여기서 규칙을 좁히거나 넓히지 않는다. 고칠 것이 보이면 정본을 고치고 다시 옮긴다.
BASE_FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # 스킴 있는 링크 · `www.` · 스킴 없는 도메인 (`t.me/…` · `bit.ly/…` · `example.com/…`)
    ("링크", re.compile(
        r"https?://[^\s<>()\[\]\"'`]+"
        r"|(?<![\w.@-])www\.[^\s<>()\[\]\"'`]+"
        r"|(?<![\w.@/-])(?:t\.me|bit\.ly|[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|net|org|io|dev|me|kr|co\.kr|go\.kr|or\.kr|ne\.kr))"
        r"(?::\d{2,5})?/[^\s<>()\[\]\"'`]*", re.IGNORECASE)),
    ("키", re.compile(
        r"(?<![A-Za-z0-9_])(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
        r"|gho_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}"
        r"|ya29\.[0-9A-Za-z_-]{20,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})")),
    ("주민번호", re.compile(r"(?<!\d)\d{6}\s*-\s*[1-4]\d{6}(?!\d)")),
    ("카드번호", re.compile(r"(?<!\d)\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}(?!\d)")),
    ("전화", re.compile(r"(?<!\d)(?:01[016-9]|0\d{1,2})[-.\s]?\d{3,4}[-.\s]\d{4}(?!\d)|(?<!\d)01[016-9]\d{7,8}(?!\d)")),
    ("이메일", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]*[A-Za-z]{2,}")),
    # 숫자 자릿수로 한 번 더 건다 (`ACCOUNT_DIGITS`) — `2026-09-22` 같은 날짜가 계좌로 잡히지 않게
    ("계좌번호", re.compile(r"(?<![\d-])\d{2,6}-\d{2,6}(?:-\d{1,8})?(?:-\d{1,6})?(?![\d-])")),
    ("주소", re.compile(
        # 행정구역(시·군·구)이 앞에 붙은 동·도로명 + 번호. 중구·우동처럼 1글자 이름도 있다.
        # 번호 뒤에 단위 글자(3시·10명·2개)가 붙으면 주소가 아니다 (2026-09-22)
        r"[가-힣]{1,10}(?:시|군|구)\s*[가-힣0-9]{1,15}(?:동|로|길|가)\s*\d{1,5}(?:-\d{1,5})?(?:번지|호)?(?!\d)(?!\s*(?:시|분|명|개|건|번|차|회|층|대|권|장|주|일|월|년)(?![가-힣]))"
        r"|[가-힣]{1,10}(?:시|군)\s*[가-힣]{1,10}(?:구|군|읍|면)\s*\d{1,5}(?:-\d{1,5})?(?:번지|호)?(?!\d)(?!\s*(?:시|분|명|개|건|번|차|회|층|대|권|장|주|일|월|년)(?![가-힣]))"
        # 도로명 단독은 `번지`·`호` 가 붙어야 주소로 본다 — `참고로 2건`·`요청으로 09:10` 같은 조사 `~로` 오탐 때문 (2026-09-22)
        r"|[가-힣]{2,10}(?<!으)(?:로|길)\s*\d{1,4}(?:-\d{1,4})?\s*(?:번지|호)(?![가-힣])"
        # 동 + 지번(하이픈 필수) — `역삼동 12-3`. `10동 3반` 은 걸리지 않는다
        r"|(?<![가-힣])[가-힣]{2,10}동\s*\d{1,5}-\d{1,5}(?:번지)?"
        # 아파트·빌라 동/호수
        r"|[가-힣A-Za-z0-9]{1,20}(?:아파트|APT|빌라|오피스텔|타워)\s*\d{1,4}동(?:\s*\d{1,5}호)?"
        r"|(?<![\d가-힣])\d{1,4}동\s*\d{1,5}호(?![\d가-힣])")),
    ("생년월일", re.compile(
        # 날짜 뒤에 `생`·`출생`·`생일` 표시가 있거나 앞에 `생년월일`·`생일` 이 붙을 때만. 맨 날짜는 일정 카드의 본체라 잡지 않는다
        r"\d{2,4}\s*[.\-/년]\s*\d{1,2}\s*[.\-/월]\s*\d{1,2}\s*일?\s*(?:생|출생|생일)(?![가-힣])"
        r"|(?:생년월일|생일|출생)\s*[:：]?\s*\d{2,4}\s*[.\-/년]\s*\d{1,2}\s*[.\-/월]\s*\d{1,2}\s*일?"
        r"|(?:생년월일|생일)\s*[:：]?\s*\d{6}(?!\d)")),
)
# 계좌번호로 볼 숫자 자릿수. 정본(`common.ACCOUNT_DIGITS`)과 같다 — `2026-09-22`(8자리)·`2026-11`(6자리)은 빠진다.
ACCOUNT_DIGITS = range(10, 15)


def forbidden_names() -> tuple[str, ...]:
    """카드에 실으면 안 되는 사람 이름. public 저장소라 소스가 아니라 환경변수에 둔다."""
    return tuple(n.strip() for n in os.environ.get("CARDS_FORBIDDEN_NAMES", "").split(",") if n.strip())


def forbidden_patterns() -> tuple[tuple[str, re.Pattern[str]], ...]:
    """검사할 금지 패턴. 이름 목록이 비어 있으면 이름 검사는 건너뛴다 —
    빈 정규식은 모든 문자열에 걸리므로 반드시 분기한다. 시크릿을 갈아끼워도 다음 호출에 반영되도록
    상수가 아니라 함수로 둔다 (같은 목록이면 컴파일 결과를 재사용)."""
    names = forbidden_names()
    if not names:
        return BASE_FORBIDDEN_PATTERNS
    return BASE_FORBIDDEN_PATTERNS + (("금지 실명", _name_regex(names)),)


_name_cache: dict[tuple[str, ...], re.Pattern[str]] = {}


def _name_regex(names: tuple[str, ...]) -> re.Pattern[str]:
    rx = _name_cache.get(names)
    if rx is None:
        rx = re.compile("|".join(map(re.escape, names)))
        _name_cache[names] = rx
    return rx


UNSAFE_NAME = re.compile(r"[/\\:*?\"<>|\x00-\x1f]")
FUN_KEYS = (("mbti", "MBTI"), ("age_band", "나이대"), ("speech_badge", "말투 뱃지"))
RETIRED_FUN_KEYS = ("blood_type",)  # 근거가 0인 항목은 싣지 않는다

AXES = (
    ("delegation", "위임", "직접 처리", "위임·분담"),
    ("verification", "검증", "결과를 그대로 수용", "검증·팩트체크"),
    ("planning", "계획", "즉흥", "계획 우선"),
    ("thoroughness", "집요함", "요점만", "끝까지 파고듦"),
    ("exploration", "탐색", "단정형", "탐색·제안형"),
)

PROJECT_STATUSES = ("준비", "진행중", "보류", "완료")
PROJECT_STATUS_ORDER = {"진행중": 0, "준비": 1, "보류": 2, "완료": 3}
MILESTONE_STATES = ("done", "doing", "todo")

# 일정·변경 (docs/SCHEDULE_SCHEMA.md · docs/CHANGELOG_SCHEMA.md)
# kind 아홉 값은 family-wiki 의 build_schedule.py 와 같은 목록이어야 한다 (team-plan §1).
EVENT_KINDS = ("가족", "개인", "회사", "기념일", "여행", "병원", "학교", "마감", "기타")
# 일정 한 줄의 출처. 비어 있으면 위키 표에서 온 것으로 본다 (build_schedule.py 의 `WIKI_SOURCE`).
# 값은 `가족일정` · `회사일정` · `gcal:<캘린더별칭>` 셋이다. 렌더에 쓰지 않으므로 목록을 강제하지는 않는다 —
# 여기서 막으면 위키 쪽이 별칭을 하나 늘릴 때 일정 섹션이 통째로 사라진다.
WIKI_SOURCE = "가족일정"
CHANGE_CARDS = ("profile", "project", "schedule", "timeline", "travel", "site")

# 일대기 (docs/TIMELINE_SCHEMA.md) — 가족사에 남을 사건만 고른 한 줄들이다.
# kind 여덟 값은 family-wiki 의 build_timeline.py 와 같은 목록이어야 한다.
# 새 값을 넣으면 build_site.TIMELINE_KIND_CLASS 에 색 클래스도 같이 넣는다 (테스트가 둘을 대조한다).
TIMELINE_KINDS = ("가족", "여행", "집", "건강", "로하", "회사", "기념일", "기타")
SITE_TIMELINE_ITEMS = 12  # 목록 페이지에 그리는 최근 건수 — 전체는 t/timeline.html

# 여행 (docs/TRAVELS_SCHEMA.md) — 좌표는 도시 수준 근사값이다.
TRAVEL_KINDS = ("해외", "국내")
TRAVEL_MAX_HIGHLIGHTS = 5
TRAVEL_HIGHLIGHT_CHARS = 40
DATE_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # 날짜 비교를 문자열로 하므로 형식이 어긋나면 받지 않는다
SITE_SCHEDULE_DAYS = 3  # 일정 카드 창: 오늘·내일·모레 (달력일, 주말 포함)
CHANGELOG_KEEP_DAYS = 7
DAILY_MAX_ITEMS = 12  # 방 하나의 요약 줄 상한 — 카드는 한눈에 읽는 길이여야 한다
DAILY_MAX_ROOMS = 6


# ───────────────────────────────────────────────────────────────────────── 유틸


def text(v: object) -> str:
    return "" if v is None else str(v).strip()


def num(v: object, default: float = 0) -> float:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def str_list(v: object, limit: int | None = None) -> list[str]:
    items = [text(x) for x in v] if isinstance(v, list) else []
    items = [x for x in items if x]
    return items[:limit] if limit else items


def sub(d: dict[str, Any], key: str) -> dict[str, Any]:
    """d[key] 가 객체면 그것, 아니면 빈 dict. (get 을 두 번 부르면 타입이 좁혀지지 않는다)"""
    v = d.get(key)
    return v if isinstance(v, dict) else {}


def parse_iso(value: object) -> date | None:
    """`YYYY-MM-DD` 만 받는다. 아니면 None — 지어내지 않는다.

    정본 `common.parse_iso` 를 그대로 옮겼다. 창 계산이 문자열 비교가 아니라 날짜 비교라서
    읽을 수 없는 값은 "없음"으로 떨어진다 — `from` 이 깨져 있을 때 위키는 하한 없음으로 펴고
    카드는 한 건도 못 펴는 식으로 갈리지 않게 한다.
    """
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


# ───────────────────────────────────────────────────────────────────────── 검증


def scan_forbidden_keys(node: object, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}"
            ks = str(k)
            if ks in FORBIDDEN_KEY_EXACT or ks.startswith(FORBIDDEN_KEY_PREFIX):
                hits.append(p)
            hits.extend(scan_forbidden_keys(v, p))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hits.extend(scan_forbidden_keys(v, f"{path}[{i}]"))
    return hits


def _version_errors(data: dict[str, Any]) -> list[str]:
    if data.get("schema_version") != SCHEMA_VERSION:
        return [f"schema_version: {SCHEMA_VERSION} 이어야 합니다 (현재 {data.get('schema_version')!r})"]
    return []


def _group_errors(data: dict[str, Any]) -> list[str]:
    """소속 키는 `group` 이다. 레퍼런스의 `part` 가 남아 있으면 그 자리에서 막는다.

    `group` 이 없으면 정상이다 — 사이트가 `DEFAULT_GROUP` 을 쓴다.
    """
    if "part" in data:
        return [f"part: 가족 저장소에서는 `group` 으로 이름이 바뀌었습니다 (값 예: {DEFAULT_GROUP!r})"]
    g = data.get("group")
    if g is None:
        return []
    if not isinstance(g, str) or not g.strip():
        return ["group: 비어 있지 않은 문자열이어야 합니다 (빼면 기본 그룹 이름을 씁니다)"]
    return []


def _meta_errors(data: dict[str, Any]) -> list[str]:
    """모든 카드가 함께 타는 머리 검사 — `schema_version` 과 `group`."""
    return _version_errors(data) + _group_errors(data)


def _privacy_errors(data: dict[str, Any]) -> list[str]:
    """모든 카드가 함께 타는 공개 범위 검사 — 금지 키와 금지 패턴 (docs/PRIVACY.md)."""
    errors = [f"금지 키: {p} — 원문 인용·성별 추정은 넣지 않습니다 (docs/PRIVACY.md)" for p in scan_forbidden_keys(data)]
    blob = json.dumps(data, ensure_ascii=False)
    taken: list[tuple[int, int]] = []  # 앞 규칙이 차지한 자리는 뒤 규칙이 다시 잡지 않는다 (정본 `find_private` 와 같다)
    seen: set[str] = set()
    for label, rx in forbidden_patterns():
        for m in rx.finditer(blob):
            # 계좌번호는 숫자 자릿수로 한 번 더 건다 (정본 `common.find_private` 와 같다) —
            # 날짜(`2026-09-22`)·기간(`2026-11`)이 계좌로 잡히면 정상 카드가 통째로 빠진다.
            if label == "계좌번호" and sum(ch.isdigit() for ch in m.group(0)) not in ACCOUNT_DIGITS:
                continue
            a, b = m.span()
            # 규칙 순서가 곧 우선순위다 — 전화번호를 "계좌번호" 라고 잘못 알리지 않게 한다
            if any(a < tb and b > ta for ta, tb in taken):
                continue
            taken.append((a, b))
            if label in seen:
                continue  # 한 종류에 한 줄만 — 사유 목록이 길어져도 알려 주는 것은 같다
            seen.add(label)
            # 걸린 원문은 사유에 넣지 않는다 — 사유는 공개 index 하단과 public 저장소의 Actions 로그에 찍힌다.
            # 전화번호를 걸러 놓고 사유에 그 번호를 적으면 결국 같은 것이 새는 셈이다 (2026-09-22).
            errors.append(f"금지 패턴({label}) · 길이 {len(m.group(0))}자 — docs/PRIVACY.md")
    return errors


def _common_errors(data: dict[str, Any], stem: str) -> list[str]:
    """파일 하나가 카드 하나인 가족·계획 카드용 — `name` 이 파일명과 같아야 한다.

    사유에 `name` 값도 파일명도 넣지 않는다 — 사유는 공개 index 하단과 public 저장소의 Actions 로그에
    찍힌다. 파일명이 곧 사람 호칭이라 사유에 적으면 그것이 인터넷에 나간다 (2026-09-22 보안 검토).
    """
    errors = _meta_errors(data)
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("name: 비어 있습니다")
    elif name.strip() != stem:
        errors.append("name: 파일명과 다릅니다")
    elif UNSAFE_NAME.search(name) or name.strip() in (".", ".."):
        errors.append("name: 파일 경로로 쓸 수 없는 문자가 있습니다")
    return errors + _privacy_errors(data)


def validate_profile(data: object, stem: str) -> list[str]:
    """거부 사유 목록. 빈 리스트면 통과 (docs/PROFILE_SCHEMA.md).

    `profile` 과 `fun` 은 둘 다 `null` 이어도 된다 — 근거가 0인 새 카드는 이름만 있어도 실린다.
    """
    if not isinstance(data, dict):
        return [f"최상위가 객체가 아닙니다 (현재 {type(data).__name__})"]
    errors = _common_errors(data, stem)
    prof = data.get("profile")
    if prof is not None and not isinstance(prof, dict):
        errors.append("profile: 객체이거나 null 이어야 합니다 (근거가 아직 없으면 null)")
    fun = data.get("fun")
    if fun is not None:
        if not isinstance(fun, dict):
            errors.append("fun: 객체이거나 null 이어야 합니다 (재미 코너를 빼려면 null)")
        else:
            for key, ko in FUN_KEYS:
                blk = fun.get(key)
                if not isinstance(blk, dict):
                    errors.append(f'fun.{key}: {{"value":…, "strength":…, "basis":…}} 객체가 필요합니다')
                elif not text(blk.get("strength")):
                    errors.append(f"fun.{key}.strength: 근거 강도 표기가 없습니다 ({ko})")
            for key in RETIRED_FUN_KEYS:
                if key in fun:
                    errors.append(f"fun.{key}: 근거가 없어 폐지된 항목입니다. JSON 에서 지우세요")
    return errors


def validate_project(data: object, stem: str) -> list[str]:
    """거부 사유 목록. 빈 리스트면 통과 (docs/PROJECT_SCHEMA.md)."""
    if not isinstance(data, dict):
        return [f"최상위가 객체가 아닙니다 (현재 {type(data).__name__})"]
    errors = _common_errors(data, stem)
    if not text(data.get("title")):
        errors.append("title: 비어 있습니다 (카드에 표시할 계획 이름)")
    status = text(data.get("status"))
    if status not in PROJECT_STATUSES:
        errors.append(f"status: {' | '.join(PROJECT_STATUSES)} 중 하나여야 합니다 (현재 {status!r})")
    ms = data.get("milestones", [])
    if ms is not None and not isinstance(ms, list):
        errors.append("milestones: 배열이어야 합니다")
    else:
        for i, m in enumerate(ms or []):
            if not isinstance(m, dict) or not text(m.get("label")):
                errors.append(f'milestones[{i}]: {{"label":…, "date":…, "state":…}} 객체가 필요합니다')
            elif text(m.get("state")) not in MILESTONE_STATES:
                errors.append(f"milestones[{i}].state: {' | '.join(MILESTONE_STATES)} 중 하나여야 합니다")
    for key in ("workstreams", "members", "recent"):
        v = data.get(key, [])
        if v is not None and not isinstance(v, list):
            errors.append(f"{key}: 배열이어야 합니다")
    for i, m in enumerate(data.get("members") or []):
        if not isinstance(m, dict) or not text(m.get("name")):
            errors.append(f'members[{i}]: {{"name":…, "role":…}} 객체가 필요합니다')
    return errors


def _date_errors(value: object, where: str, required: bool = True) -> list[str]:
    s = text(value)
    if not s:
        return [f"{where}: 비어 있습니다 (YYYY-MM-DD)"] if required else []
    if not DATE_RX.match(s):
        return [f"{where}: YYYY-MM-DD 형식이어야 합니다 (현재 {s!r})"]
    try:
        date.fromisoformat(s)
    except ValueError:
        return [f"{where}: 달력에 없는 날짜입니다 ({s!r})"]
    return []


def _valid_date(s: str) -> bool:
    """형식이 맞고 달력에 있는 날짜인지 (2026-09-31 은 형식은 맞지만 없다)."""
    return not _date_errors(s, "")


def _event_errors(e: object, where: str, recurring: bool) -> list[str]:
    """events[] 와 recurring[] 이 공유하는 검사 — kind 는 아홉 값, label 은 비어 있지 않음."""
    if not isinstance(e, dict):
        return [f"{where}: 객체가 아닙니다"]
    errors: list[str] = []
    kind = text(e.get("kind"))
    if kind not in EVENT_KINDS:
        errors.append(f"{where}.kind: {' | '.join(EVENT_KINDS)} 중 하나여야 합니다 (현재 {kind!r})")
    if not text(e.get("label")):
        errors.append(f"{where}.label: 비어 있습니다 (카드에 찍을 한 줄)")
    # 비고는 카드에 싣지 않는다 (docs/SCHEDULE_SCHEMA.md · team-plan §3). 사이트가 그리지 않으므로
    # 값이 남아 있으면 조용히 버려지는 셈이다 — 그 전에 여기서 막아 위키 쪽에서 비우게 한다.
    if text(e.get("note")):
        errors.append(f"{where}.note: 비고는 카드에 싣지 않습니다 — 비워야 합니다 (docs/SCHEDULE_SCHEMA.md)")
    src = e.get("source")
    if src is not None and not isinstance(src, str):
        errors.append(f"{where}.source: 문자열이어야 합니다 (가족일정 · 회사일정 · gcal:<별칭>)")
    done = e.get("done")
    if done is not None and not isinstance(done, bool):
        errors.append(f"{where}.done: true 나 false 여야 합니다 (현재 {done!r})")
    if not recurring:
        errors.extend(_date_errors(e.get("date"), f"{where}.date"))
        errors.extend(_date_errors(e.get("end"), f"{where}.end", required=False))
        start, end = text(e.get("date")), text(e.get("end"))
        if end and DATE_RX.match(start) and DATE_RX.match(end) and end < start:
            errors.append(f"{where}.end: date 이상이어야 합니다 ({start} → {end})")
    else:
        wd = e.get("weekdays")
        if not isinstance(wd, list) or not wd:
            errors.append(f"{where}.weekdays: 0=월 … 6=일 정수 배열이 필요합니다")
        else:
            bad = [d for d in wd if not isinstance(d, int) or isinstance(d, bool) or not 0 <= d <= 6]
            if bad:
                errors.append(f"{where}.weekdays: 0~6 정수만 들어갑니다 (현재 {bad!r})")
        # from·until 도 문자열로 비교하므로 형식이 어긋나면 전개 범위가 조용히 틀어진다
        for key in ("from", "until"):
            errors.extend(_date_errors(e.get(key), f"{where}.{key}", required=False))
    return errors


def validate_schedule(data: object) -> list[str]:
    """거부 사유 목록. 빈 리스트면 통과 (docs/SCHEDULE_SCHEMA.md '검증').

    파일이 하나라 어긋나면 일정 섹션만 빠지고 나머지 카드는 그대로 나온다.
    `name` 검사는 하지 않는다 — 가족 카드와 달리 파일명이 곧 카드 이름이 아니다.
    """
    if not isinstance(data, dict):
        return [f"최상위가 객체가 아닙니다 (현재 {type(data).__name__})"]
    errors = _meta_errors(data)
    holidays = data.get("holidays")
    if holidays is not None and not isinstance(holidays, list):
        errors.append("holidays: YYYY-MM-DD 배열이어야 합니다")
    else:
        for i, h in enumerate(holidays or []):
            errors.extend(_date_errors(h, f"holidays[{i}]"))
    for key, recurring in (("events", False), ("recurring", True)):
        v = data.get(key)
        if v is None:
            continue  # 없으면 빈 배열로 본다
        if not isinstance(v, list):
            errors.append(f"{key}: 배열이어야 합니다")
            continue
        for i, e in enumerate(v):
            errors.extend(_event_errors(e, f"{key}[{i}]", recurring))
    return errors + _privacy_errors(data)


def validate_changelog(data: object) -> list[str]:
    """거부 사유 목록. 빈 리스트면 통과 (docs/CHANGELOG_SCHEMA.md '검증')."""
    if not isinstance(data, dict):
        return [f"최상위가 객체가 아닙니다 (현재 {type(data).__name__})"]
    errors = _meta_errors(data)
    keep = data.get("keep_days")
    if keep is not None and (not isinstance(keep, int) or isinstance(keep, bool) or keep < 1):
        errors.append(f"keep_days: 1 이상의 정수여야 합니다 (현재 {keep!r})")
    entries = data.get("entries")
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        errors.append("entries: 배열이어야 합니다")
        entries = []
    for i, e in enumerate(entries):
        where = f"entries[{i}]"
        if not isinstance(e, dict):
            errors.append(f"{where}: 객체가 아닙니다")
            continue
        errors.extend(_date_errors(e.get("date"), f"{where}.date"))
        cardk = text(e.get("card"))
        if cardk not in CHANGE_CARDS:
            errors.append(f"{where}.card: {' | '.join(CHANGE_CARDS)} 중 하나여야 합니다 (현재 {cardk!r})")
        if not text(e.get("summary")):
            errors.append(f"{where}.summary: 비어 있습니다 (무엇이 바뀌었는지 한 줄)")
    return errors + _privacy_errors(data)


def validate_timeline(data: object) -> list[str]:
    """거부 사유 목록. 빈 리스트면 통과 (docs/TIMELINE_SCHEMA.md '검증').

    파일이 하나라 어긋나면 일대기 섹션만 빠지고 나머지 카드는 그대로 나온다.
    `note`(비고)는 일정 카드와 같은 규칙이다 — 병원명·금액·괄호는 위키 비고 칸에 두고 카드에는 싣지 않는다.
    `members` 는 타입만 본다. 명단(`family: true`)에 있는 호칭인지는 위키 쪽이 표를 보고 가린다 —
    카드 저장소에는 명단이 없다 (public 이라 코드에 호칭을 두지 않는다).
    """
    if not isinstance(data, dict):
        return [f"최상위가 객체가 아닙니다 (현재 {type(data).__name__})"]
    errors = _meta_errors(data)
    entries = data.get("entries")
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        errors.append("entries: 배열이어야 합니다")
        entries = []
    for i, e in enumerate(entries):
        where = f"entries[{i}]"
        if not isinstance(e, dict):
            errors.append(f"{where}: 객체가 아닙니다")
            continue
        errors.extend(_date_errors(e.get("date"), f"{where}.date"))
        errors.extend(_date_errors(e.get("end"), f"{where}.end", required=False))
        start, end = text(e.get("date")), text(e.get("end"))
        if end and DATE_RX.match(start) and DATE_RX.match(end) and end < start:
            errors.append(f"{where}.end: date 이상이어야 합니다 ({start} → {end})")
        kind = text(e.get("kind"))
        if kind not in TIMELINE_KINDS:
            errors.append(f"{where}.kind: {' | '.join(TIMELINE_KINDS)} 중 하나여야 합니다 (현재 {kind!r})")
        if not text(e.get("title")):
            errors.append(f"{where}.title: 비어 있습니다 (카드에 찍을 한 줄)")
        if text(e.get("note")):
            errors.append(f"{where}.note: 비고는 카드에 싣지 않습니다 — 비워야 합니다 (docs/TIMELINE_SCHEMA.md)")
        mem = e.get("members")
        if mem is not None and not isinstance(mem, list):
            errors.append(f"{where}.members: 호칭 배열이어야 합니다")
    return errors + _privacy_errors(data)


def _stop_errors(s: object, where: str) -> list[str]:
    """경유지 한 곳 — 이름과 좌표. 좌표는 도시 수준 근사값이면 된다 (docs/TRAVELS_SCHEMA.md)."""
    if not isinstance(s, dict):
        return [f"{where}: 객체가 아닙니다"]
    errors: list[str] = []
    if not text(s.get("name")):
        errors.append(f"{where}.name: 비어 있습니다 (지도 핀에 붙일 지명)")
    for key, limit in (("lat", 90.0), ("lon", 180.0)):
        v = s.get(key)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            errors.append(f"{where}.{key}: 숫자여야 합니다 (현재 {v!r})")
        elif not -limit <= float(v) <= limit:
            errors.append(f"{where}.{key}: -{limit:g} ~ {limit:g} 범위여야 합니다 (현재 {v!r})")
    return errors


def validate_travels(data: object) -> list[str]:
    """거부 사유 목록. 빈 리스트면 통과 (docs/TRAVELS_SCHEMA.md '검증').

    `highlights` 의 링크·금액·숙소명·예약번호 중 링크류는 `_privacy_errors` 가 막는다. 금액·숙소명은
    기계가 가릴 수 없어 위키 쪽 규칙이다 — 여기서는 개수와 길이만 본다.
    """
    if not isinstance(data, dict):
        return [f"최상위가 객체가 아닙니다 (현재 {type(data).__name__})"]
    errors = _meta_errors(data)
    trips = data.get("trips")
    if trips is None:
        trips = []
    if not isinstance(trips, list):
        errors.append("trips: 배열이어야 합니다")
        trips = []
    seen: set[str] = set()
    for i, t in enumerate(trips):
        where = f"trips[{i}]"
        if not isinstance(t, dict):
            errors.append(f"{where}: 객체가 아닙니다")
            continue
        tid = text(t.get("id"))
        if not tid:
            errors.append(f"{where}.id: 비어 있습니다 (YYYY-MM-지역, 파일 안에서 유일)")
        elif tid in seen:
            errors.append(f"{where}.id: 같은 id 가 두 번 있습니다")  # 값은 적지 않는다 — 지명이 들어 있다
        else:
            seen.add(tid)
        if not text(t.get("title")):
            errors.append(f"{where}.title: 비어 있습니다 (카드에 찍을 여행지 이름)")
        errors.extend(_date_errors(t.get("start"), f"{where}.start"))
        errors.extend(_date_errors(t.get("end"), f"{where}.end"))
        start, end = text(t.get("start")), text(t.get("end"))
        if DATE_RX.match(start) and DATE_RX.match(end) and end < start:
            errors.append(f"{where}.end: start 이상이어야 합니다 ({start} → {end})")
        kind = text(t.get("kind"))
        if kind not in TRAVEL_KINDS:
            errors.append(f"{where}.kind: {' | '.join(TRAVEL_KINDS)} 중 하나여야 합니다 (현재 {kind!r})")
        stops = t.get("stops")
        if not isinstance(stops, list) or not stops:
            errors.append(f"{where}.stops: 한 곳 이상이어야 합니다 ({{\"name\":…, \"lat\":…, \"lon\":…}})")
        else:
            for j, s in enumerate(stops):
                errors.extend(_stop_errors(s, f"{where}.stops[{j}]"))
        hl = t.get("highlights")
        if hl is None:
            hl = []
        if not isinstance(hl, list):
            errors.append(f"{where}.highlights: 배열이어야 합니다")
        else:
            if len(hl) > TRAVEL_MAX_HIGHLIGHTS:
                errors.append(f"{where}.highlights: {TRAVEL_MAX_HIGHLIGHTS}개 이하여야 합니다 (현재 {len(hl)})")
            for j, h in enumerate(hl):
                if not isinstance(h, str) or not h.strip():
                    errors.append(f"{where}.highlights[{j}]: 비어 있지 않은 문자열이어야 합니다")
                elif len(h.strip()) > TRAVEL_HIGHLIGHT_CHARS:
                    # 사유에 원문을 넣지 않는다 — 길이만 적는다 (일정·프로필 카드와 같은 규칙)
                    errors.append(
                        f"{where}.highlights[{j}]: {TRAVEL_HIGHLIGHT_CHARS}자 이내여야 합니다 (현재 {len(h.strip())}자)"
                    )
        mem = t.get("members")
        if mem is not None and not isinstance(mem, list):
            errors.append(f"{where}.members: 호칭 배열이어야 합니다")
    return errors + _privacy_errors(data)


def _room_errors(r: object, where: str) -> list[str]:
    if not isinstance(r, dict):
        return [f"{where}: 객체가 아닙니다"]
    errors = []
    if not text(r.get("room")):
        errors.append(f"{where}.room: 비어 있습니다 (방 별칭)")
    # `count` 는 없어도 된다 — 위키 쪽 daily.json 은 방 이름과 요약 줄만 적는다. 있으면 건수를 카드에 찍는다.
    cnt = r.get("count")
    if cnt is not None and (not isinstance(cnt, int) or isinstance(cnt, bool) or cnt < 0):
        errors.append(f"{where}.count: 0 이상의 정수여야 합니다 (현재 {cnt!r})")
    items = r.get("items")
    if items is None:
        items = []
    if not isinstance(items, list):
        return errors + [f"{where}.items: 배열이어야 합니다"]
    if len(items) > DAILY_MAX_ITEMS:
        errors.append(f"{where}.items: {DAILY_MAX_ITEMS}줄 이하여야 합니다 (현재 {len(items)})")
    for j, it in enumerate(items):
        if not isinstance(it, str) or not it.strip():
            errors.append(f"{where}.items[{j}]: 비어 있지 않은 문자열이어야 합니다")
    return errors


def validate_daily(data: object) -> list[str]:
    """거부 사유 목록. 빈 리스트면 통과 (docs/DAILY_SCHEMA.md '검증').

    날짜마다 방별 요약 줄 목록이다. 줄은 카톡 원문 인용이 아니라 정리할 때 LLM 이 쓴 한 줄 요약이고,
    링크·전화번호·주소 등 금지 패턴은 다른 카드와 같이 `_privacy_errors` 가 막는다.
    """
    if not isinstance(data, dict):
        return [f"최상위가 객체가 아닙니다 (현재 {type(data).__name__})"]
    errors = _meta_errors(data)
    days = data.get("days")
    if days is None:
        days = []
    if not isinstance(days, list):
        errors.append("days: 배열이어야 합니다")
        days = []
    seen: set[str] = set()
    for i, d in enumerate(days):
        where = f"days[{i}]"
        if not isinstance(d, dict):
            errors.append(f"{where}: 객체가 아닙니다")
            continue
        errors.extend(_date_errors(d.get("date"), f"{where}.date"))
        key = text(d.get("date"))
        if key in seen:
            errors.append(f"{where}.date: 같은 날짜가 두 번 있습니다 ({key})")
        seen.add(key)
        rooms = d.get("rooms")
        if rooms is None:
            rooms = []
        if not isinstance(rooms, list):
            errors.append(f"{where}.rooms: 배열이어야 합니다")
            continue
        if len(rooms) > DAILY_MAX_ROOMS:
            errors.append(f"{where}.rooms: {DAILY_MAX_ROOMS}개 이하여야 합니다 (현재 {len(rooms)})")
        for j, r in enumerate(rooms):
            errors.extend(_room_errors(r, f"{where}.rooms[{j}]"))
    return errors + _privacy_errors(data)


# ───────────────────────────────────────────────────── 달력일 창 (일정·요약 공통)
#
# family-wiki 의 scripts/build_schedule.py 와 **같은 규칙**이다. 사이트와 위키 표가 같은 날짜를
# 보게 하려고 순수 함수로 떼어 두었다 (docs/SCHEDULE_SCHEMA.md).
# 업무일 개념은 쓰지 않는다 — 가족 일정은 주말이 본체다 (team-plan §1·§4).


def day_window(today: date, days: int = SITE_SCHEDULE_DAYS) -> tuple[date, date]:
    """(창 시작, 창 끝) — 오늘부터 **달력일** `days` 개. 주말·공휴일을 건너뛰지 않는다.

    목 → (목, 토) · 금 → (금, 일) · 토 → (토, 월). `days` 가 1 미만이면 하루로 본다.
    """
    try:
        span = max(int(days), 1)  # build_schedule.day_window 와 같은 식이다
    except (TypeError, ValueError):
        span = 1  # 숫자로 읽을 수 없는 값에도 터지지 않는다 (위키 쪽은 항상 정수를 준다)
    return today, today + timedelta(days=span - 1)


def daily_days(daily: object, today: date) -> list[dict[str, Any]]:
    """하루 요약 카드에 그릴 날들 — **어제와 오늘**(달력일), 어제가 먼저·오늘이 아래.

    요약이 없는 날도 빈 블록으로 돌려준다 — 저녁에 봐도 아침에 봐도 두 날이 덮이게.
    """
    d = daily if isinstance(daily, dict) else {}
    by_date = {text(x.get("date")): x for x in (d.get("days") or []) if isinstance(x, dict) and text(x.get("date"))}
    out = []
    for day in (today - timedelta(days=1), today):
        key = day.isoformat()
        src = by_date.get(key) or {}
        rooms = [r for r in (src.get("rooms") or []) if isinstance(r, dict) and text(r.get("room"))]
        out.append({"date": key, "rooms": rooms})
    return out


def event_done(e: dict[str, Any], now_date: date, now_hm: str = "") -> bool:
    """빌드 시각 기준 이미 지난 항목인가 — 사이트가 취소선을 긋는다.

    끝난 날(`end` 또는 `date`)이 오늘보다 앞이면 지났다. 오늘 것은 `time` 이 `HH:MM` 이고 `now_hm` 보다 앞일 때만.
    '오후'·'점심' 같은 말로 된 시각은 비교하지 않는다 (지났다고 단정할 근거가 없다).
    """
    last = text(e.get("end")) or text(e.get("date"))
    if not last or not _valid_date(last):
        return False
    if last < now_date.isoformat():
        return True
    if text(e.get("date")) == now_date.isoformat() and last == now_date.isoformat():
        t = text(e.get("time"))
        if now_hm and re.fullmatch(r"\d{2}:\d{2}", t) and re.fullmatch(r"\d{2}:\d{2}", now_hm):
            return t < now_hm
    return False


def _norm_event(e: dict[str, Any], day: str, end: str, recurring: bool, ongoing: bool = False) -> dict[str, Any]:
    """일정 한 줄의 정규형. 키와 순서는 build_schedule.py 의 `_window_row` 와 같아야 한다.

    `done` 은 데이터가 적어 둔 값이다 (위키 표의 `~~취소선~~`·✅). 반복 일정에는 붙지 않는다 —
    "지난 항목" 판정은 빌드 시각으로 따로 하는 일이다 (`event_done`).
    """
    return {
        "date": day,
        "end": end,
        "time": text(e.get("time")),
        "kind": text(e.get("kind")),
        "label": text(e.get("label")),
        "members": str_list(e.get("members")),
        "note": text(e.get("note")),
        "source": text(e.get("source")) or WIKI_SOURCE,
        "recurring": recurring,
        "ongoing": ongoing,
        "done": bool(e.get("done")) and not recurring,
    }


def events_in_window(schedule: object, today: date, days: int = SITE_SCHEDULE_DAYS) -> list[dict[str, Any]]:
    """창 안의 이벤트를 날짜순(같은 날은 time → label)으로 돌려준다.

    - 창은 `day_window` — 오늘부터 달력일 `days` 개다. 주말도 공휴일도 창 안에 들어온다.
    - 단발 이벤트: `date <= 창 끝` 이고 `(end 또는 date) >= 창 시작` 이면 들어온다.
    - 반복 일정: 창 안의 **모든 날**에 요일을 맞춰 전개한다 (주말·공휴일도 편다).
      `weekdays` 에 요일이 있고 `from <= 날짜 <= until` 이어야 한다. `from`·`until` 이 날짜로 읽히지 않으면
      그 경계는 **없는 것으로 본다** (build_schedule.py 와 같다 — 한쪽만 통째로 사라지지 않게).
    - `holidays` 는 여기서 쓰지 않는다 — 표시용이다 (build_site 가 날짜 머리에 표식을 붙인다).
    - 같은 날 같은 `(라벨, 시각, 누구)` 는 한 줄만 남긴다. 단발로도 적어 둔 일정이 정기 일정과 겹칠 때가 있고,
      먼저 담긴 **단발** 쪽이 남는다 (기간·출처를 달고 있어 더 많은 것을 말한다).
    """
    d = schedule if isinstance(schedule, dict) else {}
    start, end = day_window(today, days)

    # 날짜는 문자열이 아니라 `parse_iso` 로 읽은 date 로 비교한다 — 읽을 수 없는 값은 "없음" 이다.
    # 문자열 비교로 두면 `from: "9/1"` 같은 값이 미래 날짜처럼 커서 반복 일정이 통째로 사라진다.
    out: list[dict[str, Any]] = []
    for e in d.get("events") or []:
        if not isinstance(e, dict):
            continue
        began = parse_iso(e.get("date"))
        if began is None:
            continue
        finished = parse_iso(e.get("end")) or began
        if began <= end and finished >= start:
            # 하루짜리는 end 를 비운다 (build_schedule._window_row 와 같다)
            tail = finished.isoformat() if finished != began else ""
            # ongoing: 창 시작 전에 시작해 아직 안 끝난 기간 일정 — "진행 중" 표식용
            out.append(_norm_event(e, began.isoformat(), tail, recurring=False, ongoing=began < start))

    for r in d.get("recurring") or []:
        if not isinstance(r, dict):
            continue
        wd = r.get("weekdays")
        weekdays = {int(w) for w in wd if isinstance(w, int) and 0 <= w <= 6} if isinstance(wd, list) else set()
        since, until = parse_iso(r.get("from")), parse_iso(r.get("until"))
        cur = start
        while cur <= end:
            if cur.weekday() in weekdays and (since is None or cur >= since) and (until is None or cur <= until):
                out.append(_norm_event(r, cur.isoformat(), "", recurring=True))
            cur += timedelta(days=1)

    out.sort(key=lambda x: (x["date"], x["time"], x["label"]))
    # 정렬이 안정적이라 같은 키끼리는 담은 순서를 지킨다 — 단발이 반복보다 먼저 담겼으므로 단발이 남는다
    seen: set[tuple[Any, ...]] = set()
    unique: list[dict[str, Any]] = []
    for row in out:
        key = (row["date"], row["label"], row["time"], tuple(row["members"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def holidays_in_window(schedule: object, start: date, end: date) -> list[str]:
    """창 안에 든 공휴일 날짜 — 표시용. 창 계산에서 빼지 않는다."""
    d = schedule if isinstance(schedule, dict) else {}
    s_iso, e_iso = start.isoformat(), end.isoformat()
    return sorted({h for h in str_list(d.get("holidays")) if s_iso <= h <= e_iso})


def entries_within(changelog: object, today: date, days: int | None = None) -> list[dict[str, Any]]:
    """오늘을 포함해 `days` 일 안의 변경 항목을 최신순으로. 같은 날은 파일에 적힌 순서를 지킨다.

    `days` 가 None 이면 `changelog.keep_days` (기본 7). 7 이면 today-6 까지 들어오고 today-7 은 빠진다.

    바뀐 카드 이름은 `name` 에 적는다 (위키 쪽 sync_cards.py 가 쓰는 키). 레퍼런스의 `target` 도 읽어 준다 —
    돌려주는 키는 `target` 하나로 맞춘다.
    """
    d = changelog if isinstance(changelog, dict) else {}
    if days is None:
        keep = d.get("keep_days", CHANGELOG_KEEP_DAYS)
        days = keep if isinstance(keep, int) and not isinstance(keep, bool) and keep >= 1 else CHANGELOG_KEEP_DAYS
    floor = (today - timedelta(days=days - 1)).isoformat()
    ceil = today.isoformat()
    items: list[dict[str, Any]] = []
    for e in d.get("entries") or []:
        if not isinstance(e, dict):
            continue
        day = text(e.get("date"))
        if not DATE_RX.match(day) or not (floor <= day <= ceil):
            continue
        items.append(
            {
                "date": day,
                "card": text(e.get("card")),
                "target": text(e.get("name")) or text(e.get("target")),
                "kind": text(e.get("kind")),
                "summary": text(e.get("summary")),
            }
        )
    # reverse=True 로도 같은 키끼리의 원래 순서는 유지된다 (파이썬 정렬은 안정적이다)
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


def timeline_entries(timeline: object) -> list[dict[str, Any]]:
    """일대기 항목을 `date` 오름차순으로. 날짜로 읽히지 않는 줄은 빠진다.

    같은 날 여러 건은 파일에 적힌 순서를 지킨다 (파이썬 정렬이 안정적이다) — 위키 표의 순서가 곧 그날의 순서다.
    """
    d = timeline if isinstance(timeline, dict) else {}
    out = [
        e
        for e in (d.get("entries") or [])
        if isinstance(e, dict) and DATE_RX.match(text(e.get("date"))) and _valid_date(text(e.get("date")))
    ]
    out.sort(key=lambda e: text(e.get("date")))
    return out


def travel_trips(travels: object) -> list[dict[str, Any]]:
    """여행을 `start` 오름차순으로. 날짜로 읽히지 않는 여행은 빠진다 (핀 번호가 곧 이 순서다)."""
    d = travels if isinstance(travels, dict) else {}
    out = [
        t
        for t in (d.get("trips") or [])
        if isinstance(t, dict) and DATE_RX.match(text(t.get("start"))) and _valid_date(text(t.get("start")))
    ]
    out.sort(key=lambda t: text(t.get("start")))
    return out


def trip_stops(trip: object) -> list[dict[str, Any]]:
    """좌표가 숫자이고 범위 안인 경유지만. 검증을 우회한 값이 지도 밖으로 나가지 않게 한 번 더 건다."""
    t = trip if isinstance(trip, dict) else {}
    out = []
    for s in t.get("stops") or []:
        if not isinstance(s, dict):
            continue
        lat, lon = s.get("lat"), s.get("lon")
        if not isinstance(lat, (int, float)) or isinstance(lat, bool):
            continue
        if not isinstance(lon, (int, float)) or isinstance(lon, bool):
            continue
        if not (-90 <= float(lat) <= 90 and -180 <= float(lon) <= 180):
            continue
        out.append(s)
    return out


def project_progress(milestones: object) -> tuple[int, int, str]:
    """(완료 수, 전체 수, 다음 마일스톤). 진행 중인 것이 있으면 그것이 '다음'이다."""
    raw = milestones if isinstance(milestones, list) else []
    items: list[dict[str, Any]] = [m for m in raw if isinstance(m, dict) and text(m.get("label"))]
    done = sum(1 for m in items if text(m.get("state")) == "done")
    for want in ("doing", "todo"):
        for m in items:
            if text(m.get("state")) == want:
                return done, len(items), text(m.get("label"))
    return done, len(items), ""


def badge_short(badge: object) -> str:
    """목록 셀용 짧은 말투 뱃지 — `단정 3.5배` · `물결 안 씀`."""
    if not isinstance(badge, dict) or not text(badge.get("marker")):
        return ""
    marker = text(badge.get("marker"))
    if text(badge.get("kind")) == "안씀":
        return f"{marker} 안 씀"
    ratio = num(badge.get("ratio"))
    return f"{marker} {ratio:g}배" if ratio else marker


# ───────────────────────────────────────────────────────────────────────── 적재


# 디렉터리 하나에 카드 여러 장 / 파일 하나가 카드 한 장
CARD_DIRS = (("profile", "profiles"), ("project", "projects"))
CARD_FILES = (
    ("schedule", "schedule.json"),
    ("changelog", "changelog.json"),
    ("daily", "daily.json"),
    ("timeline", "timeline.json"),
    ("travel", "travels.json"),
)


@dataclass
class Card:
    kind: str  # "profile" | "project" | "schedule" | "changelog" | "daily" | "timeline" | "travel"
    file: str  # 표시용 경로 (profiles/아빠.json · schedule.json)
    data: dict[str, Any] | None
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.data is not None and not self.errors


def _parse(kind: str, shown: str, raw: str) -> Card:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return Card(kind, shown, None, [f"JSON 파싱 실패 — {e.lineno}행 {e.colno}열: {e.msg}"])
    stem = Path(shown).stem
    if kind == "profile":
        errors = validate_profile(data, stem)
    elif kind == "project":
        errors = validate_project(data, stem)
    elif kind == "schedule":
        errors = validate_schedule(data)
    elif kind == "daily":
        errors = validate_daily(data)
    elif kind == "timeline":
        errors = validate_timeline(data)
    elif kind == "travel":
        errors = validate_travels(data)
    else:
        errors = validate_changelog(data)
    return Card(kind, shown, data if isinstance(data, dict) else None, errors)


READ_FAILED = "파일을 읽지 못했습니다 (UTF-8 이 아니거나 읽기 실패) — 그 파일만 건너뜁니다"


def _read(path: Path) -> str | None:
    """UTF-8 텍스트, 못 읽으면 None. 한 파일의 인코딩 때문에 빌드 전체가 죽지 않게 한다.

    사유에 경로도 원문도 넣지 않는다 — 사유는 공개 index 하단과 public Actions 로그에 찍힌다.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def load_local(root: Path) -> list[Card]:
    cards: list[Card] = []
    for kind, sub_dir in CARD_DIRS:
        d = root / "data" / sub_dir
        if not d.is_dir():
            warn(f"디렉터리 없음: data/{sub_dir}")
            continue
        for jp in sorted(d.glob("*.json")):
            raw = _read(jp)
            shown = f"{sub_dir}/{jp.name}"
            cards.append(_parse(kind, shown, raw) if raw is not None else Card(kind, shown, None, [READ_FAILED]))
    for kind, fname in CARD_FILES:
        fp = root / "data" / fname
        if fp.is_file():  # 없으면 그 섹션만 비운다 — 경고하지 않는다
            raw = _read(fp)
            cards.append(_parse(kind, fname, raw) if raw is not None else Card(kind, fname, None, [READ_FAILED]))
    return cards


def _ensure_repo_visible(gh: GitHub, org: str, repo: str) -> None:
    """저장소 메타데이터가 404 면 토큰이 저장소를 못 보는 것이다 (없거나 만료됐거나 접근 권한이 빠짐)."""
    try:
        gh.get(f"/repos/{org}/{repo}")
    except ApiError as e:
        if "HTTP 404" in str(e):
            raise ApiError(
                f"{org}/{repo} 를 읽을 수 없다 (HTTP 404). 토큰(WIKI_READ_TOKEN)이 없거나 만료됐거나 "
                f"이 저장소 Contents: Read 권한이 빠져 있다. 데이터 없음이 아니라 접근 실패다."
            ) from e
        raise


def load_remote(gh: GitHub, org: str, repo: str, ref: str) -> list[Card]:
    """Contents API 로 data/profiles · data/projects 와 파일 카드 셋을 받는다.

    디렉터리가 없으면(404) 비어 있는 것으로 본다. 다만 GitHub 은 토큰이 못 보는 private 저장소에도
    404 를 주므로, 저장소 자체가 안 보이면 "데이터 없음"이 아니라 오류로 올린다 — 그래야 빈 사이트가
    정상 배포로 덮어쓰지 않고 워크플로가 실패해 토큰 문제를 알린다.
    """
    cards: list[Card] = []
    for kind, sub_dir in CARD_DIRS:
        try:
            listing, _ = gh.get(f"/repos/{org}/{repo}/contents/data/{sub_dir}", {"ref": ref})
        except ApiError as e:
            if "HTTP 404" in str(e):
                _ensure_repo_visible(gh, org, repo)
                warn(f"{repo}/data/{sub_dir} 없음 — 건너뜀")
                continue
            raise
        if not isinstance(listing, list):
            raise ApiError(f"data/{sub_dir} 응답이 목록이 아님: {str(listing)[:200]}")
        for entry in sorted(listing, key=lambda e: str(e.get("name"))):
            name = str(entry.get("name", ""))
            if entry.get("type") != "file" or not name.endswith(".json"):
                continue
            body, _ = gh.get(f"/repos/{org}/{repo}/contents/{entry['path']}", {"ref": ref})
            if not isinstance(body, dict) or body.get("encoding") != "base64":
                cards.append(Card(kind, f"{sub_dir}/{name}", None, ["파일 본문을 받지 못했습니다 (1MB 초과?)"]))
                continue
            raw = base64.b64decode(str(body.get("content", ""))).decode("utf-8", errors="replace")
            cards.append(_parse(kind, f"{sub_dir}/{name}", raw))
    for kind, fname in CARD_FILES:
        try:
            body, _ = gh.get(f"/repos/{org}/{repo}/contents/data/{fname}", {"ref": ref})
        except ApiError as e:
            if "HTTP 404" in str(e):
                continue  # 아직 안 만든 파일이다 — 그 섹션만 비운다
            raise
        if not isinstance(body, dict) or body.get("encoding") != "base64":
            cards.append(Card(kind, fname, None, ["파일 본문을 받지 못했습니다 (1MB 초과?)"]))
            continue
        raw = base64.b64decode(str(body.get("content", ""))).decode("utf-8", errors="replace")
        cards.append(_parse(kind, fname, raw))
    return cards
