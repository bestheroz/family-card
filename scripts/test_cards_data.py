#!/usr/bin/env python3
"""cards_data.py 의 검증 규칙과 build_site.py 의 공개 범위를 테스트한다.

근거: family-wiki 의 docs/PROFILE_SCHEMA.md · docs/PROJECT_SCHEMA.md · docs/SCHEDULE_SCHEMA.md ·
docs/CHANGELOG_SCHEMA.md · docs/DAILY_SCHEMA.md · docs/PRIVACY.md. 표준 라이브러리만 쓴다.

픽스처의 사람 이름은 실명이 아니라 호칭이다 (아빠·엄마·첫째). 그룹 이름도 가상("우리집")을 쓴다 —
기본 그룹 이름은 `cards_data.DEFAULT_GROUP` 으로만 참조한다.

    python3 -m unittest discover -s scripts -p 'test_*.py'
"""
from __future__ import annotations

import base64
import copy
import datetime
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_site  # noqa: E402
import cards_data  # noqa: E402

GROUP = "우리집"

# 2026-09-18 은 금요일이다. 달력일 창 테스트는 이 주말을 기준으로 쓴다 —
# 업무일 창이라면 주말이 빠지므로, 금·토·일이 나오는지가 규칙이 바뀌었다는 증거다.
THU = datetime.date(2026, 9, 17)
FRI = datetime.date(2026, 9, 18)
SAT = datetime.date(2026, 9, 19)
SUN = datetime.date(2026, 9, 20)
MON = datetime.date(2026, 9, 21)
TUE = datetime.date(2026, 9, 22)


def make_profile() -> dict:
    """docs/PROFILE_SCHEMA.md 기준의 정상 가족 카드."""
    return {
        "schema_version": 1,
        "name": "아빠",
        "group": GROUP,
        "role": "아빠",
        "generated": "2026-09-17",
        "sources": ["kakao:가족방"],
        "signals": {
            "utterances": 32,
            "total_chars": 4461,
            "avg_chars": 139,
            "chat_chars": 2174,
            "avg_chat_chars": 67,
            "active_hours": "07~22",
            "markers": {"존댓말요": 33, "습니다체": 14, "단정": 3},
            "endings_top": ["했어", "하자", "있어요"],
            "artifacts": 12,
            "confidence": "높음",
            "badge": {"marker": "단정", "ratio": 3.5, "count": 3, "kind": "많이"},
        },
        "profile": {
            "axes": {
                "delegation": 2,
                "verification": 5,
                "planning": 4,
                "thoroughness": 5,
                "exploration": 3,
            },
            "work_style": "관측된 행동 근거로만 쓴 2~3줄짜리 설명이다.",
            "strengths": ["근거 있는 강점 1", "근거 있는 강점 2"],
        },
        "fun": {
            "mbti": {"value": "INTJ", "strength": "약함", "basis": "축별 근거 한 줄"},
            "age_band": {"value": "30대 중후반", "strength": "약함", "basis": "ㅋ 9건 · 존댓말 33건"},
            "speech_badge": {
                "value": "먼저 챙기는 사람",
                "strength": "관측",
                "basis": "단정 표현을 가족 평균의 3.5배로 쓴다 · 관측 32건",
            },
            "nickname": "먼저 챙기는 사람",
            "how_to_talk": {
                "good": ["확인하고 싶은 범위를 적어 보낸다"],
                "avoid": ["촉박하게 던지는 것"],
                "best_time": "07~09시",
                "example": "확인 부탁해.",
            },
        },
    }


def make_project() -> dict:
    """docs/PROJECT_SCHEMA.md 기준의 정상 계획 카드 (가족 계획이다 — 회사 과제가 아니다)."""
    return {
        "schema_version": 1,
        "name": "제주여행",
        "title": "가을 제주 여행",
        "group": GROUP,
        "status": "진행중",
        "phase": "숙소 고르기",
        "target": "2026-11 출발",
        "generated": "2026-09-17",
        "summary": "한 줄 정의",
        "badges": ["올해 큰 계획"],
        "milestones": [
            {"label": "항공권 예약", "date": "2026-08-20", "state": "done"},
            {"label": "숙소 확정", "date": "2026-09 중", "state": "doing"},
            {"label": "출발", "date": "2026-11", "state": "todo"},
        ],
        "workstreams": [{"area": "예약", "state": "진행중", "note": "항공권 완료"}],
        "members": [{"name": "엄마", "role": "예약"}],
        "next": ["숙소 확정"],
        "recent": [{"date": "2026-09-17", "note": "후보 세 곳 추림"}],
    }


def make_schedule() -> dict:
    """docs/SCHEDULE_SCHEMA.md 기준의 정상 일정.

    반복 일정을 **주말(토·일)** 로 둔 것이 핵심이다 — 달력일 창이라 주말에도 펴져야 한다.
    """
    return {
        "schema_version": 1,
        "group": GROUP,
        "generated": "2026-09-17",
        "holidays": [],
        "events": [
            {"date": "2026-09-18", "time": "19:00", "kind": "가족", "label": "가족 저녁", "members": ["아빠"], "note": ""},
            {"date": "2026-09-18", "end": "2026-09-20", "time": "", "kind": "여행", "label": "주말 캠핑", "members": [], "note": ""},
        ],
        "recurring": [
            {"weekdays": [5, 6], "time": "09:00", "kind": "개인", "label": "주말 운동", "members": [], "until": "2026-10-31", "note": ""},
        ],
    }


def make_daily() -> dict:
    """docs/DAILY_SCHEMA.md 기준의 정상 하루 요약 — 어제(9/17)·오늘(9/18) 두 날."""
    return {
        "schema_version": 1,
        "group": GROUP,
        "generated": "2026-09-18",
        "keep_days": 7,
        "days": [
            {"date": "2026-09-18", "rooms": [
                {"room": "가족방", "count": 2, "items": ["공지: 주말 캠핑 준비물 공유"]},
            ]},
            {"date": "2026-09-17", "rooms": [
                {"room": "가족방", "count": 7, "items": ["일정: 첫째 학교 상담 9/23(수)", "엄마 병원 예약을 옮겼다"]},
                {"room": "부부방", "count": 0, "items": []},
            ]},
        ],
    }


def make_changelog() -> dict:
    """docs/CHANGELOG_SCHEMA.md 기준의 정상 변경 목록."""
    return {
        "schema_version": 1,
        "group": GROUP,
        "keep_days": 7,
        "entries": [
            {"date": "2026-09-18", "card": "project", "target": "제주여행", "summary": "마일스톤 갱신"},
            {"date": "2026-09-18", "card": "profile", "target": "아빠", "summary": "말투 신호 갱신"},
            {"date": "2026-09-17", "card": "site", "target": "", "summary": "일정 카드 신설"},
        ],
    }


class 그룹_키_검증(unittest.TestCase):
    """소속 키는 `part` 가 아니라 `group` 이다 (team-plan §1 · §4)."""

    def test_group이_있으면_통과(self):
        self.assertEqual(cards_data.validate_profile(make_profile(), "아빠"), [])

    def test_group이_없어도_통과한다(self):
        p = make_profile()
        del p["group"]
        self.assertEqual(cards_data.validate_profile(p, "아빠"), [])

    def test_group이_빈_문자열이면_거부(self):
        p = make_profile()
        p["group"] = "  "
        self.assertTrue(any("group" in e for e in cards_data.validate_profile(p, "아빠")))

    def test_part_키가_남아_있으면_거부(self):
        """레퍼런스(part-cards) 에서 가져온 JSON 을 그대로 쓰면 여기서 막힌다."""
        for data, check in (
            (make_profile(), lambda d: cards_data.validate_profile(d, "아빠")),
            (make_project(), lambda d: cards_data.validate_project(d, "제주여행")),
            (make_schedule(), cards_data.validate_schedule),
            (make_changelog(), cards_data.validate_changelog),
            (make_daily(), cards_data.validate_daily),
        ):
            with self.subTest(kind=type(data).__name__ + str(sorted(data)[:1])):
                data["part"] = "고객서비스파트"
                errs = check(data)
                self.assertTrue(any("part" in e and "group" in e for e in errs), errs)

    def test_기본_그룹_이름이_사이트_제목이_된다(self):
        h = build_site.render_index(
            profiles=[], projects=[], skipped=[], group=cards_data.DEFAULT_GROUP,
            built="2026-09-18 10:00 KST", generated="", today=FRI,
        )
        self.assertIn(f"<title>{cards_data.DEFAULT_GROUP} 카드</title>", h)


class 프로필_검증(unittest.TestCase):
    """docs/PROFILE_SCHEMA.md · docs/PRIVACY.md 의 검증 규칙."""

    def _errors(self, data, stem="아빠"):
        return cards_data.validate_profile(data, stem)

    def test_정상_카드는_통과(self):
        self.assertEqual(self._errors(make_profile()), [])

    def test_schema_version이_다르면_거부(self):
        p = make_profile()
        p["schema_version"] = 2
        self.assertTrue(any("schema_version" in e for e in self._errors(p)))

    def test_파일명과_name이_다르면_거부(self):
        self.assertTrue(any("name" in e for e in self._errors(make_profile(), stem="엄마")))

    def test_name_사유에_값도_파일명도_적지_않는다(self):
        """사유는 공개 index 하단과 public Actions 로그에 찍힌다 — 파일명이 곧 사람 호칭이다."""
        for errs in (
            self._errors(make_profile(), stem="김서연"),
            self._errors({"schema_version": 1, "name": "아빠/엄마", "group": GROUP}, "아빠/엄마"),
        ):
            with self.subTest(errs=errs):
                self.assertTrue(errs)
                for e in errs:
                    self.assertNotIn("아빠", e)
                    self.assertNotIn("김서연", e)

    def test_금지_키_gender_거부(self):
        p = make_profile()
        p["gender"] = "남"
        self.assertTrue(any("금지 키" in e for e in self._errors(p)))

    def test_중첩된_금지_키도_거부(self):
        p = make_profile()
        p["profile"]["samples_원문"] = ["실제로 이렇게 말했다"]
        self.assertTrue(any("금지 키" in e for e in self._errors(p)))

    def test_mbti_근거강도가_없으면_거부(self):
        p = make_profile()
        del p["fun"]["mbti"]["strength"]
        self.assertTrue(any("fun.mbti.strength" in e for e in self._errors(p)))

    def test_폐지된_fun_키_거부(self):
        """혈액형처럼 근거가 0이라 폐지한 항목이 되살아나면 빌드가 막는다."""
        p = make_profile()
        p["fun"]["blood_type"] = {"value": "A형", "strength": "없음(무작위)", "basis": "데이터 신호 0"}
        self.assertTrue(any("blood_type" in e for e in self._errors(p)))

    def test_fun이_null이면_통과(self):
        p = make_profile()
        p["fun"] = None  # 재미 코너를 뺀 경우
        self.assertEqual(self._errors(p), [])

    def test_profile이_null이면_통과(self):
        """근거가 0인 새 카드는 이름만 있어도 실린다 (team-plan §1)."""
        p = make_profile()
        p["profile"] = None
        self.assertEqual(self._errors(p), [])

    def test_profile이_객체도_null도_아니면_거부(self):
        p = make_profile()
        p["profile"] = "아직 없음"
        self.assertTrue(any("profile" in e for e in self._errors(p)))

    def test_이름만_있는_카드도_통과한다(self):
        self.assertEqual(
            self._errors({"schema_version": 1, "name": "첫째", "group": GROUP, "profile": None, "fun": None}, "첫째"),
            [],
        )

    def test_reactions_top이_있어도_검증은_통과(self):
        """수집기가 남긴 키다. 검증에서 막지 않고 렌더에서 무시한다."""
        p = make_profile()
        p["signals"]["reactions_top"] = [["👍", 14], ["❤", 4]]
        self.assertEqual(self._errors(p), [])


class 공개_금지_패턴(unittest.TestCase):
    """공개 사이트라 링크·연락처·주소·생년월일은 카드에 실을 수 없다 (docs/PRIVACY.md).

    앞쪽 규칙은 family-wiki 의 `scripts/common.py` `PRIVACY_RULES` 를 그대로 옮긴 것이다.
    """

    def _profile_errors(self, work_style: str):
        p = make_profile()
        p["profile"]["work_style"] = work_style
        return cards_data.validate_profile(p, "아빠")

    def test_링크는_종류를_가리지_않고_거부(self):
        for url in (
            "https://www.example.com/abc 를 참고한다.",
            "http://intra.example 로 들어가면 된다.",
            "www.example.co.kr 에 올려 두었다.",
        ):
            with self.subTest(url=url):
                self.assertTrue(any("금지 패턴" in e for e in self._profile_errors(url)))

    def test_전화번호_거부(self):
        self.assertTrue(any("전화" in e for e in self._profile_errors("급하면 010-1234-5678 로 연락한다.")))

    def test_이메일_거부(self):
        self.assertTrue(any("이메일" in e for e in self._profile_errors("문의는 someone@example.com 으로.")))

    def test_사유에_걸린_원문을_적지_않는다(self):
        """사유는 공개 index 하단과 public 저장소의 Actions 로그에 찍힌다 — 걸러 낸 번호가 사유로 새면 안 된다."""
        errors = self._profile_errors("급하면 010-1234-5678 로, 아니면 someone@example.com 으로.")
        self.assertTrue(errors)
        for e in errors:
            self.assertNotIn("1234", e)
            self.assertNotIn("example.com", e)

    def test_주민등록번호_형태_거부(self):
        self.assertTrue(any("주민번호" in e for e in self._profile_errors("서류에 880317-1234567 을 적었다.")))

    def test_계좌번호_거부(self):
        """하이픈 숫자 10~14자리. 정본 `common.ACCOUNT_DIGITS` 와 같은 자릿수로 건다."""
        for acct in (
            "생활비는 112-233-456789 로 보낸다.",
            "계좌 1002-345-678901 이다.",
            "3333-01-2345678 에 넣어 뒀다.",
        ):
            with self.subTest(acct=acct):
                errs = self._profile_errors(acct)
                self.assertTrue(any("계좌번호" in e for e in errs), errs)

    def test_전화번호를_계좌번호로_알리지_않는다(self):
        """앞 규칙이 잡은 자리는 뒤 규칙이 다시 잡지 않는다 — 정본 `common.find_private` 와 같은 우선순위다.
        사유가 틀리면 공개 index 하단에 엉뚱한 종류가 찍힌다."""
        errs = self._profile_errors("급하면 010-1234-5678 로 연락한다.")
        self.assertTrue(any("전화" in e for e in errs))
        self.assertFalse(any("계좌번호" in e for e in errs), errs)

    def test_카드번호_거부(self):
        self.assertTrue(any("카드번호" in e for e in self._profile_errors("결제는 1234-5678-9012-3456 으로 했다.")))

    def test_토큰_거부(self):
        """카드에 자격증명이 들어올 일은 없지만 정본이 막는 것은 여기서도 막는다."""
        self.assertTrue(any("키" in e for e in self._profile_errors("토큰 ghp_abcdefghijklmnopqrstuvwxyz01 을 넣었다.")))

    def test_스킴_없는_도메인_거부(self):
        """`https://` 가 없어도 링크는 링크다 — 단축 주소도 막는다."""
        for link in (
            "notion.com/abc 에 정리해 뒀다.",
            "t.me/family_room 으로 들어온다.",
            "bit.ly/3abcde 를 눌러 보라고 했다.",
            "blog.example.co.kr/2026/09 에 올렸다.",
        ):
            with self.subTest(link=link):
                errs = self._profile_errors(link)
                self.assertTrue(any("링크" in e for e in errs), errs)

    def test_숫자와_날짜가_섞인_정상_라벨은_통과한다(self):
        """날짜·시각·증감 표기·분수가 계좌로 잡히면 정상 카드가 통째로 빠진다."""
        for ok in (
            "2026-09-22 에 정했다.",
            "2026-11 출발이고 2026-09-29~2026-10-05 일정이다.",
            "10:30 에 모인다.",
            "발화 35→41건 · 평균 44→40자",
            "마일스톤 1/7 을 끝냈다.",
            "첫째 학교 상담 9/23(수)",
        ):
            with self.subTest(ok=ok):
                self.assertEqual(self._profile_errors(ok), [])

    def test_경로가_없으면_도메인으로_보지_않는다(self):
        """정본과 같은 판단이다 — 뒤에 `/…` 가 붙어야 링크로 본다 (`정리.md` 같은 파일명 오탐 방지)."""
        self.assertEqual(self._profile_errors("파일 이름은 정리.md 하나뿐이다."), [])

    def test_주소_거부(self):
        for addr in (
            "서울시 강남구 테헤란로 152 로 이사했다.",
            "강남구 삼성동 159-1 이다.",
            "역삼동 12-3 에 산다.",
            "테헤란로 152번지",
        ):
            with self.subTest(addr=addr):
                errs = self._profile_errors(addr)
                self.assertTrue(any("주소" in e for e in errs), errs)

    def test_한_글자_행정구역_이름도_주소다(self):
        """`중구`·`우동` 처럼 이름이 1글자인 곳이 있다 — 최소 길이를 2로 두면 실제 주소가 샌다 (정본 2026-09-22)."""
        for addr in ("중구 을지로 100", "해운대구 우동 1234-5", "강남구 역삼동 12"):
            with self.subTest(addr=addr):
                self.assertTrue(any("주소" in e for e in self._profile_errors(addr)), addr)

    def test_구_동으로_끝나는_낱말은_주소가_아니다(self):
        """`연구`·`친구`·`도구` 는 `구` 로 끝나고 `10동 3반` 은 `동` 으로 끝난다 — 번호가 붙어도 주소가 아니다."""
        for ok in ("연구 2건", "친구 3명", "도구 10개", "10동 3반"):
            with self.subTest(ok=ok):
                self.assertEqual(self._profile_errors(ok), [], ok)

    def test_번호_뒤에_단위_글자가_붙으면_주소가_아니다(self):
        """`강남구 신사동 3시 모임` 의 3은 번지가 아니라 시각이다 (정본의 단위 글자 제외)."""
        for ok in ("강남구 신사동 3시 모임", "수원시 영통구 10명"):
            with self.subTest(ok=ok):
                self.assertEqual(self._profile_errors(ok), [], ok)

    def test_아파트_동_호수_거부(self):
        """정본에 들어온 규칙 — 단지 이름 없이 `101동 1502호` 만 적어도 집을 특정한다."""
        for addr in (
            "행복아파트 101동 1502호 로 이사했다.",
            "행복빌라 3동 에 산다.",
            "테라스오피스텔 2동 901호",
            "101동 1502호 우편함을 확인했다.",
        ):
            with self.subTest(addr=addr):
                errs = self._profile_errors(addr)
                self.assertTrue(any("주소" in e for e in errs), errs)

    def test_조사로_쓰인_로는_주소로_보지_않는다(self):
        """`로`·`길` 은 조사로도 쓰인다 — 도로명 단독은 `번지`·`호` 가 붙어야 주소다 (정본 2026-09-22 결정).

        이 경계가 없으면 "아빠 회사로 3시에 출발" 같은 일정 라벨 하나로 일정 카드가 통째로 빠진다.
        """
        for ok in (
            "아빠 회사로 3시에 출발한다.",
            "집으로 6시까지 온다.",
            "학교로 2명이 같이 간다.",
            "참고로 2건 더 있다.",
            "여행 3일차에 렌터카를 바꾼다.",
        ):
            with self.subTest(ok=ok):
                self.assertEqual(self._profile_errors(ok), [])

    def test_동은_지번이나_호수가_붙어야_주소다(self):
        """`10동 3반` 같은 말은 주소가 아니다."""
        self.assertEqual(self._profile_errors("첫째는 10동 3반이다."), [])

    def test_생년월일_거부(self):
        """`생`·`출생`·`생일` 표시가 붙은 날짜만 생년월일로 본다 — 맨 날짜는 일정 카드의 본체라 잡지 않는다."""
        for birth in (
            "1988년 3월 17일 생",
            "1988년 3월 17일생",
            "2014년 5월 2일생",
            "생년월일: 1988-03-17",
            "생일 880317",
        ):
            with self.subTest(birth=birth):
                errs = self._profile_errors(birth)
                self.assertTrue(any("생년월일" in e for e in errs), errs)

    def test_연도_없는_기념일은_통과한다(self):
        """카드에는 연도 없는 기념일만 싣는다 — 9월 21일 생일은 태어난 해를 알려 주지 않는다."""
        self.assertEqual(self._profile_errors("9월 21일 생일을 챙긴다."), [])

    def test_일정_날짜는_통과한다(self):
        """`generated` 같은 YYYY-MM-DD 와 '9월 21일 모임' 은 생년월일이 아니다."""
        self.assertEqual(self._profile_errors("2026년 9월 21일 모임을 잡았다."), [])

    def test_일정과_요약도_같은_검사를_탄다(self):
        s = make_schedule()
        s["events"][0]["label"] = "서울시 강남구 테헤란로 152 로 이사"
        self.assertTrue(any("주소" in e for e in cards_data.validate_schedule(s)))
        d = make_daily()
        d["days"][0]["rooms"][0]["items"].append("엄마 1988.03.17 생일 정리")
        self.assertTrue(any("생년월일" in e for e in cards_data.validate_daily(d)))


class 금지_실명(unittest.TestCase):
    """카드에 실으면 안 되는 이름은 소스가 아니라 CARDS_FORBIDDEN_NAMES 시크릿에 둔다."""

    def setUp(self):
        self._saved = os.environ.get("CARDS_FORBIDDEN_NAMES")

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("CARDS_FORBIDDEN_NAMES", None)
        else:
            os.environ["CARDS_FORBIDDEN_NAMES"] = self._saved

    def test_등록된_이름이_있으면_거부(self):
        os.environ["CARDS_FORBIDDEN_NAMES"] = "홍길동, 임꺽정"
        p = make_profile()
        p["profile"]["work_style"] = "임꺽정 이모와 자주 통화한다."
        self.assertTrue(any("금지 패턴" in e for e in cards_data.validate_profile(p, "아빠")))

    def test_계획_카드도_같은_검사를_탄다(self):
        os.environ["CARDS_FORBIDDEN_NAMES"] = "홍길동"
        pr = make_project()
        pr["recent"][0]["note"] = "홍길동 이모와 일정 맞춤"
        self.assertTrue(any("금지 패턴" in e for e in cards_data.validate_project(pr, "제주여행")))

    def test_목록이_비면_이름_검사를_건너뛴다(self):
        """빈 정규식은 모든 문자열에 걸린다 — 비었을 때 정상 카드가 통과하는지 확인한다."""
        os.environ["CARDS_FORBIDDEN_NAMES"] = ""
        self.assertEqual(cards_data.validate_profile(make_profile(), "아빠"), [])
        self.assertEqual(len(cards_data.forbidden_patterns()), len(cards_data.BASE_FORBIDDEN_PATTERNS))

    def test_공백만_있는_항목은_무시한다(self):
        os.environ["CARDS_FORBIDDEN_NAMES"] = " , ,  "
        self.assertEqual(cards_data.forbidden_names(), ())
        self.assertEqual(cards_data.validate_profile(make_profile(), "아빠"), [])


class 계획_검증(unittest.TestCase):
    """계획 JSON 도 가족 카드와 같은 공개 규칙을 탄다 (docs/PROJECT_SCHEMA.md)."""

    def _errors(self, data, stem="제주여행"):
        return cards_data.validate_project(data, stem)

    def test_정상_계획은_통과(self):
        self.assertEqual(self._errors(make_project()), [])

    def test_파일명과_name이_다르면_거부(self):
        self.assertTrue(self._errors(make_project(), stem="이사"))

    def test_status는_정해진_값만(self):
        p = make_project()
        p["status"] = "하는중"
        self.assertTrue(any("status" in e for e in self._errors(p)))

    def test_마일스톤_state는_정해진_값만(self):
        p = make_project()
        p["milestones"][0]["state"] = "finished"
        self.assertTrue(any("milestones[0].state" in e for e in self._errors(p)))

    def test_title이_없으면_거부(self):
        p = make_project()
        p["title"] = ""
        self.assertTrue(any("title" in e for e in self._errors(p)))

    def test_링크_거부(self):
        p = make_project()
        p["summary"] = "자세한 건 https://www.example.com/abc 참고"
        self.assertTrue(any("금지 패턴" in e for e in self._errors(p)))

    def test_금지_키_거부(self):
        p = make_project()
        p["workstreams"][0]["raw_quote"] = "원문 인용"
        self.assertTrue(any("금지 키" in e for e in self._errors(p)))

    def test_마일스톤과_담당이_비어도_통과(self):
        p = make_project()
        p["milestones"] = []
        p["members"] = []
        self.assertEqual(self._errors(p), [])


class 금지_키_훑기(unittest.TestCase):
    """금지 키는 중첩 어디에 있어도 경로째로 잡힌다."""

    def test_배열_안의_객체까지_훑는다(self):
        hits = cards_data.scan_forbidden_keys({"a": [{"quotes": ["원문"]}]})
        self.assertEqual(hits, ["$.a[0].quotes"])

    def test_접두사_규칙(self):
        self.assertEqual(cards_data.scan_forbidden_keys({"samples_원문": 1}), ["$.samples_원문"])

    def test_정상_데이터는_비어_있다(self):
        self.assertEqual(cards_data.scan_forbidden_keys(make_profile()), [])


class 말투_뱃지_칩(unittest.TestCase):
    """목록 카드에 들어가는 말투 뱃지 칩. 별명과 겹치지 않게 짧아야 한다."""

    def test_배수_뱃지(self):
        self.assertEqual(cards_data.badge_short({"marker": "단정", "ratio": 3.5, "kind": "많이"}), "단정 3.5배")

    def test_안쓰는_것도_뱃지다(self):
        self.assertEqual(cards_data.badge_short({"marker": "물결", "ratio": 0.0, "kind": "안씀"}), "물결 안 씀")

    def test_값이_없으면_빈_문자열(self):
        for bad in (None, {}, {"ratio": 3.5}, "단정", []):
            self.assertEqual(cards_data.badge_short(bad), "")

    def test_칩이_짧다(self):
        """길면 카드에서 별명과 뒤엉킨다."""
        self.assertLessEqual(len(cards_data.badge_short({"marker": "위임분담", "ratio": 6.3, "kind": "많이"})), 12)


class 계획_진행률(unittest.TestCase):
    """진행률은 마일스톤 완료 수로만 계산한다. 사람이 % 를 적는 칸은 없다."""

    def test_완료_수와_전체_수(self):
        done, total, _ = cards_data.project_progress(make_project()["milestones"])
        self.assertEqual((done, total), (1, 3))

    def test_다음은_진행중이_우선(self):
        self.assertEqual(cards_data.project_progress(make_project()["milestones"])[2], "숙소 확정")

    def test_진행중이_없으면_첫_예정(self):
        ms = [{"label": "a", "state": "done"}, {"label": "b", "state": "todo"}]
        self.assertEqual(cards_data.project_progress(ms)[2], "b")

    def test_비어_있으면_0(self):
        self.assertEqual(cards_data.project_progress([]), (0, 0, ""))
        self.assertEqual(cards_data.project_progress(None), (0, 0, ""))


class 반응_집계는_싣지_않는다(unittest.TestCase):
    """이 사이트는 이모지 반응 집계를 싣지 않는다 — 데이터에 남아 있어도 HTML 에 나오면 안 된다."""

    def setUp(self):
        self.data = make_profile()
        self.data["signals"]["reactions_top"] = [["👍", 14], ["❤", 4], ["🎄", 2]]

    def test_목록_카드에도_상세에도_나오지_않는다(self):
        listing = build_site.member_card(copy.deepcopy(self.data), "m/아빠.html")
        detail = build_site.render_person(copy.deepcopy(self.data), "2026-09-18 10:00 KST")
        for html_out, where in ((listing, "목록 카드"), (detail, "상세 페이지")):
            with self.subTest(where=where):
                self.assertNotIn("👍", html_out)
                self.assertNotIn("❤", html_out)
                self.assertNotIn("반응", html_out)
                self.assertNotIn("mchip react", html_out)

    def test_말투_뱃지는_그대로_나온다(self):
        """반응만 빼고 관측값 렌더는 살아 있어야 한다."""
        self.assertIn("단정 3.5배", build_site.member_card(self.data, "m/아빠.html"))


class 일정_검증(unittest.TestCase):
    """docs/SCHEDULE_SCHEMA.md '검증'. 파일이 하나라 어긋나면 일정 섹션만 빠진다."""

    def _errors(self, data):
        return cards_data.validate_schedule(data)

    def test_정상_일정은_통과(self):
        self.assertEqual(self._errors(make_schedule()), [])

    def test_events와_recurring이_없어도_통과(self):
        self.assertEqual(self._errors({"schema_version": 1, "group": GROUP}), [])

    def test_schema_version이_다르면_거부(self):
        s = make_schedule()
        s["schema_version"] = 2
        self.assertTrue(any("schema_version" in e for e in self._errors(s)))

    def test_kind는_아홉_값이다(self):
        """가족·개인·회사·기념일·여행·병원·학교·마감·기타 (team-plan §1)."""
        self.assertEqual(
            cards_data.EVENT_KINDS,
            ("가족", "개인", "회사", "기념일", "여행", "병원", "학교", "마감", "기타"),
        )
        for kind in cards_data.EVENT_KINDS:
            with self.subTest(kind=kind):
                s = make_schedule()
                s["events"][0]["kind"] = kind
                self.assertEqual(self._errors(s), [])

    def test_목록에_없는_kind는_거부(self):
        for kind in ("회의", "근태", "보고", "행사", "회식"):
            with self.subTest(kind=kind):
                s = make_schedule()
                s["events"][0]["kind"] = kind
                self.assertTrue(any("events[0].kind" in e for e in self._errors(s)))

    def test_모든_kind에_사이트_색_클래스가_있다(self):
        """새 kind 를 넣고 CSS 클래스를 잊으면 칩이 회색으로 떨어진다."""
        self.assertEqual(sorted(build_site.EVENT_KIND_CLASS), sorted(cards_data.EVENT_KINDS))

    def test_date_형식이_틀리면_거부(self):
        s = make_schedule()
        s["events"][0]["date"] = "2026-9-18"
        self.assertTrue(any("events[0].date" in e for e in self._errors(s)))

    def test_end가_date보다_빠르면_거부(self):
        s = make_schedule()
        s["events"][1]["end"] = "2026-09-17"
        self.assertTrue(any("events[1].end" in e for e in self._errors(s)))

    def test_label이_비면_거부(self):
        s = make_schedule()
        s["events"][0]["label"] = "  "
        self.assertTrue(any("events[0].label" in e for e in self._errors(s)))

    def test_링크는_거부(self):
        s = make_schedule()
        s["events"][0]["label"] = "https://example.com/일정 참고"
        self.assertTrue(any("금지 패턴" in e for e in self._errors(s)))

    def test_weekdays_범위를_벗어나면_거부(self):
        s = make_schedule()
        s["recurring"][0]["weekdays"] = [0, 7]
        self.assertTrue(any("recurring[0].weekdays" in e for e in self._errors(s)))

    def test_weekdays가_배열이_아니면_거부(self):
        s = make_schedule()
        s["recurring"][0]["weekdays"] = 0
        self.assertTrue(any("recurring[0].weekdays" in e for e in self._errors(s)))

    def test_금지_키_거부(self):
        s = make_schedule()
        s["events"][0]["raw_quote"] = "원문 인용"
        self.assertTrue(any("금지 키" in e for e in self._errors(s)))

    def test_비고가_비어_있지_않으면_거부(self):
        """비고는 카드에 싣지 않는다 (docs/SCHEDULE_SCHEMA.md · team-plan §3).
        사이트가 그리지 않으니 값이 남아 있으면 조용히 버려지는 셈이다 — 그 전에 막는다."""
        s = make_schedule()
        s["events"][0]["note"] = "재검 · 32만원"
        errs = self._errors(s)
        self.assertTrue(any("events[0].note" in e for e in errs), errs)

    def test_반복_일정의_비고도_거부(self):
        s = make_schedule()
        s["recurring"][0]["note"] = "회비 3만원"
        self.assertTrue(any("recurring[0].note" in e for e in self._errors(s)))

    def test_비고_거부_사유에_원문을_적지_않는다(self):
        s = make_schedule()
        s["events"][0]["note"] = "재검 · 32만원"
        for e in self._errors(s):
            self.assertNotIn("32만원", e)
            self.assertNotIn("재검", e)

    def test_공휴일_날짜_형식을_검사한다(self):
        s = make_schedule()
        s["holidays"] = ["2026-09-31"]
        self.assertTrue(any("holidays[0]" in e for e in self._errors(s)))


class 하루_요약_검증(unittest.TestCase):
    def test_정상이면_통과(self):
        self.assertEqual(cards_data.validate_daily(make_daily()), [])

    def test_날짜_필수이고_중복_금지(self):
        d = make_daily()
        del d["days"][0]["date"]
        self.assertTrue(any("days[0].date" in e for e in cards_data.validate_daily(d)))
        d = make_daily()
        d["days"][1]["date"] = "2026-09-18"
        self.assertTrue(any("두 번" in e for e in cards_data.validate_daily(d)))

    def test_방_이름과_줄_형식(self):
        d = make_daily()
        r = d["days"][1]["rooms"]
        r[0]["room"] = ""
        r[0]["items"] = ["", 3]
        r[1]["count"] = -1
        errs = cards_data.validate_daily(d)
        self.assertTrue(any("days[1].rooms[0].room" in e for e in errs))
        self.assertEqual(sum("rooms[0].items[" in e for e in errs), 2)
        self.assertTrue(any("rooms[1].count" in e for e in errs))

    def test_링크가_있으면_거부(self):
        d = make_daily()
        d["days"][0]["rooms"][0]["items"].append("공지: https://example.com 참고")
        self.assertTrue(any("링크" in e for e in cards_data.validate_daily(d)))

    def test_줄_수_상한(self):
        d = make_daily()
        d["days"][0]["rooms"][0]["items"] = ["x"] * (cards_data.DAILY_MAX_ITEMS + 1)
        self.assertTrue(any("items:" in e for e in cards_data.validate_daily(d)))

    def test_days_가_없으면_빈_요약으로_통과(self):
        d = make_daily()
        del d["days"]
        self.assertEqual(cards_data.validate_daily(d), [])

    def test_count가_없어도_통과(self):
        """위키 쪽 daily.json 은 방 이름과 요약 줄만 적는다 — 건수는 선택이다."""
        d = make_daily()
        for day in d["days"]:
            for room in day["rooms"]:
                del room["count"]
        self.assertEqual(cards_data.validate_daily(d), [])

    def test_위키가_내놓은_빈_요약도_통과(self):
        """worker-2 가 만든 초기값 그대로 (days 가 빈 배열)."""
        self.assertEqual(
            cards_data.validate_daily(
                {"schema_version": 1, "group": GROUP, "generated": "2026-09-22", "keep_days": 2, "days": []}
            ),
            [],
        )


class 하루_요약_날짜(unittest.TestCase):
    """하루 요약 카드는 **어제와 오늘**, 달력일 두 날만 그린다 (업무일이 아니다)."""

    def test_어제_먼저_그다음_오늘(self):
        got = cards_data.daily_days(make_daily(), FRI)
        self.assertEqual([d["date"] for d in got], ["2026-09-17", "2026-09-18"])
        self.assertEqual(len(got[0]["rooms"]), 2)

    def test_월요일의_어제는_일요일이다(self):
        """업무일 창이라면 금요일이 나왔다 — 달력일이라 일요일이다."""
        got = cards_data.daily_days(make_daily(), MON)
        self.assertEqual([d["date"] for d in got], ["2026-09-20", "2026-09-21"])

    def test_요약이_없는_날도_빈_블록으로_돌려준다(self):
        got = cards_data.daily_days(make_daily(), MON)
        self.assertEqual([len(d["rooms"]) for d in got], [0, 0])

    def test_파일이_없어도_두_날(self):
        self.assertEqual(len(cards_data.daily_days(None, FRI)), 2)


class 지난_항목_판정(unittest.TestCase):
    def test_끝난_날이_오늘보다_앞이면_지났다(self):
        self.assertTrue(cards_data.event_done({"date": "2026-09-17", "end": ""}, FRI))
        self.assertTrue(cards_data.event_done({"date": "2026-09-15", "end": "2026-09-17"}, FRI))

    def test_오늘_것은_시각이_지났을_때만(self):
        self.assertTrue(cards_data.event_done({"date": "2026-09-18", "end": "", "time": "19:00"}, FRI, "20:00"))
        self.assertFalse(cards_data.event_done({"date": "2026-09-18", "end": "", "time": "19:00"}, FRI, "09:00"))
        self.assertFalse(cards_data.event_done({"date": "2026-09-18", "end": "", "time": "19:00"}, FRI, ""))

    def test_말로_된_시각과_종일은_긋지_않는다(self):
        self.assertFalse(cards_data.event_done({"date": "2026-09-18", "end": "", "time": "저녁"}, FRI, "23:00"))
        self.assertFalse(cards_data.event_done({"date": "2026-09-18", "end": "", "time": ""}, FRI, "23:00"))

    def test_진행_중인_기간은_지난_게_아니다(self):
        self.assertFalse(cards_data.event_done({"date": "2026-09-17", "end": "2026-09-20", "time": ""}, FRI, "23:00"))


class 변경_목록_검증(unittest.TestCase):
    """docs/CHANGELOG_SCHEMA.md '검증'."""

    def _errors(self, data):
        return cards_data.validate_changelog(data)

    def test_정상_변경목록은_통과(self):
        self.assertEqual(self._errors(make_changelog()), [])

    def test_card는_네_값만(self):
        c = make_changelog()
        c["entries"][0]["card"] = "일정"
        self.assertTrue(any("entries[0].card" in e for e in self._errors(c)))

    def test_summary가_비면_거부(self):
        c = make_changelog()
        c["entries"][1]["summary"] = ""
        self.assertTrue(any("entries[1].summary" in e for e in self._errors(c)))

    def test_date_형식이_틀리면_거부(self):
        c = make_changelog()
        c["entries"][2]["date"] = "9/17"
        self.assertTrue(any("entries[2].date" in e for e in self._errors(c)))

    def test_링크는_거부(self):
        c = make_changelog()
        c["entries"][0]["summary"] = "자세한 건 www.example.com 참고"
        self.assertTrue(any("금지 패턴" in e for e in self._errors(c)))

    def test_entries가_없어도_통과(self):
        self.assertEqual(self._errors({"schema_version": 1}), [])


class 달력일_창(unittest.TestCase):
    """`day_window` 는 오늘부터 달력일 `days` 개다. 주말·공휴일을 건너뛰지 않는다 (team-plan §1·§4).

    family-wiki 의 scripts/build_schedule.py 와 같은 규칙이어야 한다.
    """

    def w(self, today, days=cards_data.SITE_SCHEDULE_DAYS):
        return cards_data.day_window(today, days)

    def test_기본값은_사흘이다(self):
        self.assertEqual(cards_data.SITE_SCHEDULE_DAYS, 3)
        self.assertEqual(cards_data.day_window(FRI), (FRI, SUN))

    def test_금요일은_금토일이다(self):
        """업무일 창이라면 금·월·화였다 — 주말이 창 안에 들어오는지가 핵심이다."""
        self.assertEqual(self.w(FRI), (FRI, SUN))

    def test_토요일은_토일월이다(self):
        self.assertEqual(self.w(SAT), (SAT, MON))

    def test_목요일은_목금토이다(self):
        self.assertEqual(self.w(THU), (THU, SAT))

    def test_공휴일도_창에서_빠지지_않는다(self):
        """holidays 는 표시용이라 창 계산에 아예 들어오지 않는다."""
        self.assertEqual(self.w(FRI), (FRI, SUN))

    def test_하루_창(self):
        self.assertEqual(self.w(FRI, 1), (FRI, FRI))

    def test_숫자로_읽히면_그만큼_센다(self):
        """`max(int(days), 1)` — build_schedule.day_window 와 같은 식이다."""
        self.assertEqual(cards_data.day_window(FRI, "3"), (FRI, SUN))
        self.assertEqual(cards_data.day_window(FRI, 3.0), (FRI, SUN))

    def test_1미만이거나_숫자가_아니면_하루로_본다(self):
        for bad in (0, -3, None, True, [], "사흘"):
            with self.subTest(bad=bad):
                self.assertEqual(cards_data.day_window(FRI, bad), (FRI, FRI))

    def test_공휴일_표시_목록은_창_안만_돌려준다(self):
        s = make_schedule()
        s["holidays"] = ["2026-09-17", "2026-09-20", "2026-10-03"]
        self.assertEqual(cards_data.holidays_in_window(s, FRI, SUN), ["2026-09-20"])
        self.assertEqual(cards_data.holidays_in_window(None, FRI, SUN), [])


class 창_안의_일정(unittest.TestCase):
    """창 안의 일정만 고른다. 반복은 창 안 **모든 날**에 편다 (주말·공휴일 포함)."""

    def labels(self, schedule, today, days=cards_data.SITE_SCHEDULE_DAYS):
        return [(e["date"], e["label"]) for e in cards_data.events_in_window(schedule, today, days)]

    def test_창_안의_하루_일정은_들어온다(self):
        self.assertIn(("2026-09-18", "가족 저녁"), self.labels(make_schedule(), FRI))

    def test_창_밖의_일정은_빠진다(self):
        s = make_schedule()
        s["events"].append({"date": "2026-09-22", "kind": "가족", "label": "다음주 모임"})
        self.assertNotIn(("2026-09-22", "다음주 모임"), self.labels(s, FRI))

    def test_반복_일정은_주말에도_펴진다(self):
        """주말 운동(토·일)은 금요일 창(금·토·일)에서 이틀 다 나와야 한다 — 업무일 창이라면 0건이었다."""
        got = [d for d, label in self.labels(make_schedule(), FRI) if label == "주말 운동"]
        self.assertEqual(got, ["2026-09-19", "2026-09-20"])

    def test_창_안_공휴일에도_반복을_편다(self):
        s = make_schedule()
        s["holidays"] = ["2026-09-19"]
        got = [d for d, label in self.labels(s, FRI) if label == "주말 운동"]
        self.assertEqual(got, ["2026-09-19", "2026-09-20"])

    def test_공휴일이_창_길이를_늘리지_않는다(self):
        s = make_schedule()
        s["holidays"] = ["2026-09-18", "2026-09-19", "2026-09-20"]
        self.assertEqual(cards_data.events_in_window(s, FRI), cards_data.events_in_window(make_schedule(), FRI))

    def test_창_시작_전에_시작해_창_안에_끝나는_기간_일정은_들어온다(self):
        s = make_schedule()
        s["events"].append({"date": "2026-09-16", "end": "2026-09-18", "kind": "병원", "label": "입원"})
        self.assertIn(("2026-09-16", "입원"), self.labels(s, FRI))

    def test_창보다_앞서_끝난_기간_일정은_빠진다(self):
        s = make_schedule()
        s["events"].append({"date": "2026-09-14", "end": "2026-09-17", "kind": "여행", "label": "지난 여행"})
        self.assertNotIn(("2026-09-14", "지난 여행"), self.labels(s, FRI))

    def test_until이_지나면_펴지지_않는다(self):
        s = make_schedule()
        s["recurring"][0]["until"] = "2026-09-18"
        self.assertNotIn("주말 운동", [label for _, label in self.labels(s, FRI)])

    def test_from_이전에는_펴지지_않는다(self):
        s = make_schedule()
        s["recurring"][0]["from"] = "2026-09-20"
        self.assertEqual([d for d, label in self.labels(s, FRI) if label == "주말 운동"], ["2026-09-20"])

    def test_from_until이_날짜가_아니면_경계가_없는_것으로_본다(self):
        """build_schedule.py 는 `parse_iso` 로 읽어 None 이면 하한/상한 없음이다 — 문자열로 비교하면
        `"9/1"` 이 미래처럼 커서 카드 쪽만 0건이 된다. 두 구현이 같아야 한다."""
        for bad in ("9/1", "2026.09.01", "", "곧", None, 20260901):
            with self.subTest(bad=bad):
                s = make_schedule()
                s["recurring"][0]["from"] = bad
                s["recurring"][0]["until"] = bad
                got = [d for d, label in self.labels(s, FRI) if label == "주말 운동"]
                self.assertEqual(got, ["2026-09-19", "2026-09-20"])

    def test_날짜가_ISO가_아닌_단발_일정은_빠진다(self):
        s = make_schedule()
        s["events"] = [{"date": "9/18", "kind": "가족", "label": "못 읽는 날짜"}]
        s["recurring"] = []
        self.assertEqual(cards_data.events_in_window(s, FRI), [])

    def test_정렬은_날짜_시각_라벨_순(self):
        s = make_schedule()
        s["events"] = [
            {"date": "2026-09-18", "time": "14:00", "kind": "가족", "label": "나중"},
            {"date": "2026-09-18", "time": "09:00", "kind": "가족", "label": "ㄴ 같은 시각"},
            {"date": "2026-09-18", "time": "09:00", "kind": "가족", "label": "ㄱ 같은 시각"},
            {"date": "2026-09-19", "time": "09:00", "kind": "가족", "label": "다음날"},
        ]
        s["recurring"] = []
        self.assertEqual(
            self.labels(s, FRI),
            [
                ("2026-09-18", "ㄱ 같은 시각"),
                ("2026-09-18", "ㄴ 같은 시각"),
                ("2026-09-18", "나중"),
                ("2026-09-19", "다음날"),
            ],
        )

    def test_정규화된_키와_순서는_위키쪽_window_row와_같다(self):
        """build_schedule.py 의 `_window_row` 가 내놓는 키와 순서 그대로여야 한다."""
        e = cards_data.events_in_window(make_schedule(), FRI)[0]
        self.assertEqual(
            list(e),
            ["date", "end", "time", "kind", "label", "members", "note", "source", "recurring", "ongoing", "done"],
        )

    def test_source가_비면_가족일정으로_본다(self):
        got = {e["label"]: e["source"] for e in cards_data.events_in_window(make_schedule(), FRI)}
        self.assertEqual(got["가족 저녁"], cards_data.WIKI_SOURCE)
        self.assertEqual(got["주말 운동"], cards_data.WIKI_SOURCE)

    def test_source를_적어_두면_그대로_돌려준다(self):
        s = make_schedule()
        s["events"][0]["source"] = "gcal:가족"
        got = {e["label"]: e["source"] for e in cards_data.events_in_window(s, FRI)}
        self.assertEqual(got["가족 저녁"], "gcal:가족")

    def test_done은_데이터가_적어_둔_값이다(self):
        s = make_schedule()
        s["events"][0]["done"] = True
        got = {e["label"]: e["done"] for e in cards_data.events_in_window(s, FRI)}
        self.assertTrue(got["가족 저녁"])
        self.assertFalse(got["주말 캠핑"])

    def test_반복_일정의_done은_언제나_false(self):
        s = make_schedule()
        s["recurring"][0]["done"] = True
        got = [e["done"] for e in cards_data.events_in_window(s, FRI) if e["label"] == "주말 운동"]
        self.assertEqual(got, [False, False])

    def test_같은_날_같은_일정은_한_줄만_남고_단발이_이긴다(self):
        """정기 일정을 단발로도 적어 두면 두 줄이 된다 — 기간·출처를 단 단발 쪽을 남긴다."""
        s = make_schedule()
        s["events"].append(
            {"date": "2026-09-19", "time": "09:00", "kind": "개인", "label": "주말 운동",
             "members": [], "note": "", "source": "gcal:가족"}
        )
        got = [e for e in cards_data.events_in_window(s, FRI) if e["label"] == "주말 운동"]
        self.assertEqual(
            [(e["date"], e["source"], e["recurring"]) for e in got],
            [("2026-09-19", "gcal:가족", False), ("2026-09-20", cards_data.WIKI_SOURCE, True)],
        )

    def test_누구가_다르면_다른_줄이다(self):
        s = make_schedule()
        s["events"].append(
            {"date": "2026-09-19", "time": "09:00", "kind": "개인", "label": "주말 운동", "members": ["엄마"]}
        )
        got = [e for e in cards_data.events_in_window(s, FRI) if e["date"] == "2026-09-19"]
        self.assertEqual(len(got), 2)

    def test_빈_시각이_그날_맨_위에_온다(self):
        s = make_schedule()
        s["events"] = [
            {"date": "2026-09-18", "time": "09:00", "kind": "가족", "label": "아침"},
            {"date": "2026-09-18", "time": "", "kind": "기념일", "label": "종일 항목"},
        ]
        s["recurring"] = []
        self.assertEqual([e["label"] for e in cards_data.events_in_window(s, FRI)], ["종일 항목", "아침"])

    def test_창_시작_전에_시작한_기간_일정은_진행_중이다(self):
        s = make_schedule()
        s["events"].append({"date": "2026-09-14", "end": "2026-09-20", "kind": "여행", "label": "외박", "members": []})
        got = {e["label"]: e for e in cards_data.events_in_window(s, FRI)}
        self.assertTrue(got["외박"]["ongoing"])
        self.assertFalse(got["가족 저녁"]["ongoing"])

    def test_반복_여부가_표시된다(self):
        got = {e["label"]: e for e in cards_data.events_in_window(make_schedule(), FRI)}
        self.assertTrue(got["주말 운동"]["recurring"])
        self.assertFalse(got["가족 저녁"]["recurring"])

    def test_일정이_없으면_빈_목록(self):
        self.assertEqual(cards_data.events_in_window(None, FRI), [])


class 최근_변경_창(unittest.TestCase):
    """최근 7일 = 오늘 포함 7일. today-6 은 들어오고 today-7 은 빠진다."""

    def _log(self, *dates):
        return {
            "schema_version": 1,
            "entries": [{"date": d, "card": "site", "target": "", "summary": d} for d in dates],
        }

    def test_오늘_포함_7일_경계(self):
        got = cards_data.entries_within(self._log("2026-09-18", "2026-09-12", "2026-09-11"), FRI)
        self.assertEqual([e["date"] for e in got], ["2026-09-18", "2026-09-12"])

    def test_미래_날짜는_빠진다(self):
        self.assertEqual(cards_data.entries_within(self._log("2026-09-19"), FRI), [])

    def test_keep_days를_존중한다(self):
        log = self._log("2026-09-18", "2026-09-17", "2026-09-16")
        log["keep_days"] = 2
        self.assertEqual([e["date"] for e in cards_data.entries_within(log, FRI)], ["2026-09-18", "2026-09-17"])

    def test_인자로_준_days가_keep_days를_이긴다(self):
        log = self._log("2026-09-18", "2026-09-17")
        log["keep_days"] = 7
        self.assertEqual([e["date"] for e in cards_data.entries_within(log, FRI, 1)], ["2026-09-18"])

    def test_최신순이고_같은_날은_파일_순서를_지킨다(self):
        got = cards_data.entries_within(make_changelog(), FRI)
        self.assertEqual(
            [(e["date"], e["summary"]) for e in got],
            [
                ("2026-09-18", "마일스톤 갱신"),
                ("2026-09-18", "말투 신호 갱신"),
                ("2026-09-17", "일정 카드 신설"),
            ],
        )

    def test_바뀐_카드_이름은_name_에서_읽는다(self):
        """위키 쪽 sync_cards.py 는 `name` 을 쓴다. 레퍼런스의 `target` 도 읽어 주고, 돌려주는 키는 `target` 하나다."""
        log = {
            "schema_version": 1,
            "group": GROUP,
            "keep_days": 7,
            "entries": [
                {"date": "2026-09-18", "card": "schedule", "name": "가족 일정", "kind": "갱신", "summary": "회사 일정 반영"},
                {"date": "2026-09-18", "card": "profile", "target": "아빠", "summary": "말투 신호 갱신"},
            ],
        }
        self.assertEqual(cards_data.validate_changelog(log), [])
        got = cards_data.entries_within(log, FRI)
        self.assertEqual([e["target"] for e in got], ["가족 일정", "아빠"])
        self.assertEqual(got[0]["kind"], "갱신")

    def test_변경목록이_없으면_빈_목록(self):
        self.assertEqual(cards_data.entries_within(None, FRI), [])


class 목록_페이지(unittest.TestCase):
    """섹션 순서는 하루 요약 → 가족 일정 → 계획 → 가족 → 최근 변경."""

    def _index(self, **kw):
        args = {
            "profiles": [make_profile()],
            "projects": [make_project()],
            "skipped": [],
            "group": GROUP,
            "built": "2026-09-18 10:00 KST",
            "generated": "2026-09-17",
            "schedule": make_schedule(),
            "changelog": make_changelog(),
            "today": FRI,
            "daily": make_daily(),
        }
        args.update(kw)
        return build_site.render_index(**args)

    def _part(self, start, end, **kw) -> str:
        h = self._index(**kw)
        return h[h.index(f"sec {start}"):h.index(f"sec {end}")]

    def test_섹션_순서(self):
        h = self._index()
        order = [h.index(f"sec {cls}") for cls in ("sec-daily", "sec-sched", "sec-proj", "sec-members", "sec-changes")]
        self.assertEqual(order, sorted(order))

    def test_섹션_제목이_가족_맥락이다(self):
        h = self._index()
        for title in ("하루 요약", "가족 일정", "계획", "가족", "최근 변경"):
            with self.subTest(title=title):
                self.assertIn(f'<h2 class="sectitle">{title}</h2>', h)

    def test_회사_문구는_남아_있지_않다(self):
        h = self._index()
        for word in ("파트", "업무 요약", "파트원", "프로젝트", "멤버"):
            with self.subTest(word=word):
                self.assertNotIn(word, h)

    def test_사이트_제목은_그룹_이름에서_만든다(self):
        self.assertIn(f"<title>{GROUP} 카드</title>", self._index())

    def test_히어로_칩에_건수가_붙는다(self):
        """금요일 빌드 → 창은 금·토·일. 가족 저녁(금) + 주말 캠핑(금~일) + 주말 운동 토·일 = 4건."""
        h = self._index()
        self.assertIn("<b>일정</b>4건", h)
        self.assertIn("<b>변경</b>3건", h)
        self.assertIn("<b>가족</b>1명", h)
        self.assertIn("<b>계획</b>1건", h)

    def test_창_범위를_부제에_적는다(self):
        h = self._index()
        self.assertIn("9/18(금) ~ 9/20(일)", h)
        self.assertIn("오늘·내일·모레 (주말 포함)", h)

    def test_주말_일정이_카드에_보인다(self):
        sched = self._part("sec-sched", "sec-proj")
        self.assertIn("가족 저녁", sched)
        self.assertIn("주말 운동", sched)
        self.assertIn("9/19(토)", sched)
        self.assertIn("9/20(일)", sched)
        self.assertIn('<span class="today">오늘</span>', sched)

    def test_공휴일은_날짜_머리에_표식만_붙는다(self):
        s = make_schedule()
        s["holidays"] = ["2026-09-19"]
        sched = self._part("sec-sched", "sec-proj", schedule=s)
        self.assertIn('<span class="hol">공휴일</span>', sched)
        self.assertIn("주말 운동", sched)  # 창에서 빼지 않는다
        self.assertIn("창 안 공휴일: 9/19(토)", sched)

    def test_지난_일정은_취소선(self):
        """빌드 시각 20:00 → 19:00 가족 저녁은 지났고, 시각이 없는 주말 캠핑은 안 지났다."""
        sched = self._part("sec-sched", "sec-proj", now_hm="20:00")
        li = sched[sched.index("가족 저녁") - 400:sched.index("가족 저녁")]
        self.assertIn('<li class="done">', li)
        self.assertIn('<span class="did">지남</span>', sched)
        self.assertIn("text-decoration:line-through", self._index())

    def test_빌드_시각이_없으면_오늘_것은_긋지_않는다(self):
        self.assertNotIn('class="done"', self._part("sec-sched", "sec-proj"))

    def test_데이터가_끝났다고_적어_두면_완료로_긋는다(self):
        """위키 표의 `~~취소선~~`·✅ 는 시각과 무관하게 치운 일이다 — '지남' 과 구분한다."""
        s = make_schedule()
        s["events"][0]["done"] = True
        sched = self._part("sec-sched", "sec-proj", schedule=s)
        self.assertIn('<span class="did">완료</span>', sched)
        self.assertNotIn('<span class="did">지남</span>', sched)
        self.assertEqual(sched.count('<li class="done">'), 1)

    def test_방_건수가_없으면_건수_칩을_빼고_그린다(self):
        """0건이라고 거짓말하지 않는다."""
        d = make_daily()
        for day in d["days"]:
            for room in day["rooms"]:
                del room["count"]
        part = self._part("sec-daily", "sec-sched", daily=d)
        self.assertIn('<div class="droom-head">가족방</div>', part)
        self.assertNotIn("메시지 0건", part)
        self.assertIn("<li>공지: 주말 캠핑 준비물 공유</li>", part)

    def test_어제_시작한_기간_일정은_진행_중이지_지난_게_아니다(self):
        s = make_schedule()
        s["events"].append({"date": "2026-09-17", "end": "2026-09-19", "kind": "병원", "label": "입원", "members": []})
        part = self._part("sec-sched", "sec-proj", schedule=s, now_hm="23:00")
        self.assertIn("입원", part)
        self.assertIn('<span class="on">진행 중</span>', part)
        self.assertEqual(part.count('<li class="done">'), 1)  # 가족 저녁만

    def test_비고는_HTML에_그리지_않는다(self):
        """검증기를 우회해 note 가 들어와도(손으로 고친 JSON) 사이트에 나오지 않아야 한다."""
        s = make_schedule()
        s["events"][0]["note"] = "재검 · 32만원"
        sched = self._part("sec-sched", "sec-proj", schedule=s)
        self.assertIn("가족 저녁", sched)  # 일정 자체는 그린다
        self.assertNotIn("재검", sched)
        self.assertNotIn("32만원", sched)
        self.assertNotIn("evnote", self._index())

    def test_기간_일정은_시작과_끝을_다_적는다(self):
        self.assertIn("9/18(금)~9/20(일)", self._index())

    def test_일정이_없으면_빈_상태_문구(self):
        h = self._index(schedule=None)
        self.assertIn("오늘부터 3일 안에 잡힌 일정이 없다", h)
        self.assertIn("<b>일정</b>0건", h)

    def test_하루_요약은_어제와_오늘_두_날(self):
        part = self._part("sec-daily", "sec-sched")
        self.assertIn("하루 요약", part)
        self.assertLess(part.index("9/17(목)"), part.index("9/18(금)"))  # 어제 먼저, 오늘이 아래
        self.assertIn('<div class="droom-head">가족방<span class="dcount">메시지 7건</span></div>', part)
        self.assertIn("<li>일정: 첫째 학교 상담 9/23(수)</li>", part)
        self.assertIn("<li>공지: 주말 캠핑 준비물 공유</li>", part)
        self.assertIn('<li class="empty">올라온 메시지 없음</li>', part)  # 부부방 0건
        self.assertNotIn("9/16", part)

    def test_월요일에는_일요일과_월요일(self):
        """업무일 창이라면 금요일이 나왔다."""
        d = make_daily()
        d["days"] = [{"date": "2026-09-20", "rooms": [{"room": "가족방", "count": 1, "items": ["일요일 줄"]}]}]
        part = self._part("sec-daily", "sec-sched", today=MON, daily=d)
        self.assertIn("9/20(일)", part)
        self.assertIn("일요일 줄", part)
        self.assertIn("9/21(월)", part)
        self.assertNotIn("9/18(금)", part)
        self.assertIn("요약이 아직 없다", part)  # 월요일 것은 아직

    def test_요약_파일이_없어도_섹션은_있다(self):
        h = self._index(daily=None)
        self.assertIn("sec-daily", h)
        self.assertEqual(h.count("요약이 아직 없다"), 2)

    def test_변경이_없으면_빈_상태_문구(self):
        h = self._index(changelog=None)
        self.assertIn("최근 7일간 바뀐 카드가 없다", h)
        self.assertIn("<b>변경</b>0건", h)

    def test_변경_대상이_카드와_같으면_상세로_링크(self):
        h = self._index()
        self.assertIn(build_site.href_for("p", make_project()), h)
        self.assertIn(build_site.href_for("m", make_profile()), h)

    def test_변경_칩은_가족_계획으로_적는다(self):
        h = self._index()
        self.assertIn('<span class="ck ck-profile">가족</span>', h)
        self.assertIn('<span class="ck ck-project">계획</span>', h)

    def test_카드가_없는_이름은_링크하지_않는다(self):
        log = make_changelog()
        log["entries"][1]["target"] = "없는사람"
        h = self._index(changelog=log)
        self.assertIn("없는사람", h)
        self.assertNotIn('href="m/없는사람.html"', h)

    def test_긴_요약은_낱말_안에서_끊지_않는다(self):
        """좁은 폭에서 `발화` 가 `발`/`화` 로 갈라지면 읽을 수 없다."""
        self.assertIn("word-break:keep-all", self._index())

    def test_가족_카드에_이니셜_아바타가_붙는다(self):
        h = self._index()
        self.assertIn('<span class="avatar', h)
        self.assertIn('class="mhead"', h)

    def test_반복_일정은_매주로_구분된다(self):
        self.assertIn("매주", self._index())

    def test_모든_것이_비어도_빌드된다(self):
        h = self._index(schedule=None, changelog=None, daily=None, profiles=[], projects=[])
        for cls in ("sec-daily", "sec-sched", "sec-proj", "sec-members", "sec-changes"):
            self.assertIn(cls, h)

    def test_CDN과_JS는_없다(self):
        h = self._index()
        self.assertNotIn("<script", h)
        self.assertNotIn("http://", h)
        self.assertNotIn("https://", h)

    def test_색인을_막는다(self):
        self.assertIn('<meta name="robots" content="noindex,nofollow">', self._index())


class 사이트_색(unittest.TestCase):
    """따뜻한 가족 팔레트다 — 회사 CI 오렌지가 남아 있으면 안 된다 (team-plan §1)."""

    def test_한화_오렌지가_없다(self):
        for hexcode in ("#F37321", "#F89B6C", "#FBB584", "#FF8F45", "#E8431B"):
            with self.subTest(hexcode=hexcode):
                self.assertNotIn(hexcode.lower(), build_site.CSS.lower())

    def test_라이트와_다크_토큰이_둘_다_있다(self):
        self.assertIn("--brand-ink:#9A4227", build_site.CSS)
        self.assertIn("@media (prefers-color-scheme:dark)", build_site.CSS)
        self.assertEqual(build_site.CSS.count("--brand-ink:"), 2)

    def test_작은_글자용_토큰이_따로_있다(self):
        """본문·칩 글자에는 --brand 가 아니라 대비 4.5:1 이상인 --brand-ink 를 쓴다."""
        self.assertIn("color:var(--brand-ink)", build_site.CSS)


class 정본과_같은_금지_패턴(unittest.TestCase):
    """금지 패턴이 family-wiki 의 `scripts/common.py` `PRIVACY_RULES` 와 **글자까지** 같은지 본다.

    두 관문(위키 `sync_cards.py --check` · 카드 빌드)이 갈리면 --check 를 통과한 카드가 사이트에서
    거부되거나, --check 가 놓친 것이 인터넷에 나간다. 그래서 정규식 문자열까지 대조한다.

    옆에 위키 클론이 없으면(CI 가 그렇다) **통과**시킨다 — 이 저장소만으로 도는 테스트를 깨지 않는다.
    대조할 수 있을 때만 어긋남을 잡는 표류 감지기다.
    """

    WIKI_DIRS = ("family-wiki", "my-wiki")

    def _common(self):
        """옆 위키 클론의 `common` 모듈. 못 찾거나 못 읽으면 None."""
        import importlib.util

        for name in self.WIKI_DIRS:
            path = SCRIPTS_DIR.parent.parent / name / "scripts" / "common.py"
            if not path.is_file():
                continue
            try:
                spec = importlib.util.spec_from_file_location("_wiki_common", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception:  # noqa: BLE001 — 남의 저장소를 읽는 일이다. 못 읽으면 대조를 건너뛴다
                return None
            if hasattr(module, "PRIVACY_RULES"):
                return module
        return None

    def test_라벨과_순서가_같다(self):
        wiki = self._common()
        if wiki is None:
            return  # 옆에 위키 클론이 없다 — 대조 없이 통과
        self.assertEqual(
            [label for label, _ in cards_data.BASE_FORBIDDEN_PATTERNS],
            [label for label, _ in wiki.PRIVACY_RULES],
        )

    def test_정규식_문자열과_플래그가_같다(self):
        wiki = self._common()
        if wiki is None:
            return
        for (label, mine), (wiki_label, theirs) in zip(cards_data.BASE_FORBIDDEN_PATTERNS, wiki.PRIVACY_RULES):
            with self.subTest(label=label):
                self.assertEqual(label, wiki_label)
                self.assertEqual(mine.pattern, theirs.pattern)
                self.assertEqual(mine.flags, theirs.flags)

    def test_카드_전용_규칙이_없다(self):
        """정본에 없는 규칙을 카드 쪽에 몰래 두지 않는다 — 두면 --check 가 통과한 카드가 거부된다."""
        wiki = self._common()
        if wiki is None:
            return
        self.assertEqual(
            {label for label, _ in cards_data.BASE_FORBIDDEN_PATTERNS} - {label for label, _ in wiki.PRIVACY_RULES},
            set(),
        )

    def test_계좌번호_자릿수도_같다(self):
        wiki = self._common()
        if wiki is None:
            return
        self.assertEqual(cards_data.ACCOUNT_DIGITS, wiki.ACCOUNT_DIGITS)

    def test_위키가_없어도_대조_테스트는_통과한다(self):
        """이 저장소만 클론한 CI 에서도 위 네 테스트가 통과해야 한다 (skip 이 아니라 통과)."""
        saved = self.WIKI_DIRS
        try:
            self.WIKI_DIRS = ("없는-저장소-이름",)
            self.assertIsNone(self._common())
            self.test_라벨과_순서가_같다()
            self.test_정규식_문자열과_플래그가_같다()
            self.test_카드_전용_규칙이_없다()
            self.test_계좌번호_자릿수도_같다()
        finally:
            self.WIKI_DIRS = saved



class 가짜_깃허브:
    """경로별로 정해 둔 응답을 돌려주는 최소 클라이언트. 값이 ApiError 면 그것을 던진다."""

    def __init__(self, routes: dict[str, object]) -> None:
        self.routes = routes
        self.calls: list[str] = []

    def get(self, path: str, params: dict | None = None):
        self.calls.append(path)
        resp = self.routes.get(path, cards_data.ApiError(f"HTTP 404 {path}: Not Found"))
        if isinstance(resp, Exception):
            raise resp
        return resp, {}


class 원격_적재(unittest.TestCase):
    """토큰이 저장소를 못 보면 GitHub 은 404 를 준다 — 그것을 '데이터 없음'으로 오해해 빈 사이트를 배포하지 않는다."""

    def test_저장소가_안_보이면_오류로_올린다(self):
        gh = 가짜_깃허브({})  # 모든 경로 404
        with self.assertRaises(cards_data.ApiError) as cm:
            cards_data.load_remote(gh, "bestheroz", "family-wiki", "main")
        self.assertIn("WIKI_READ_TOKEN", str(cm.exception))
        self.assertIn("/repos/bestheroz/family-wiki", gh.calls)

    def test_저장소는_보이고_폴더만_없으면_빈_목록(self):
        gh = 가짜_깃허브({"/repos/bestheroz/family-wiki": {"name": "family-wiki"}})
        self.assertEqual(cards_data.load_remote(gh, "bestheroz", "family-wiki", "main"), [])

    def test_일정_변경_요약_파일도_같이_받는다(self):
        """파일 하나짜리 카드도 Contents API 로 받는다. 없으면(404) 그 섹션만 빈다."""
        body = base64.b64encode(json.dumps(make_schedule(), ensure_ascii=False).encode()).decode()
        gh = 가짜_깃허브(
            {
                "/repos/bestheroz/family-wiki": {"name": "family-wiki"},
                "/repos/bestheroz/family-wiki/contents/data/schedule.json": {"encoding": "base64", "content": body},
            }
        )
        cards = cards_data.load_remote(gh, "bestheroz", "family-wiki", "main")
        self.assertEqual([(c.kind, c.file, c.ok) for c in cards], [("schedule", "schedule.json", True)])

    def test_404_아닌_오류는_그대로_올린다(self):
        gh = 가짜_깃허브({"/repos/o/w/contents/data/profiles": cards_data.ApiError("HTTP 401 x: Bad credentials")})
        with self.assertRaises(cards_data.ApiError) as cm:
            cards_data.load_remote(gh, "o", "w", "main")
        self.assertIn("HTTP 401", str(cm.exception))


class API_오류_메시지(unittest.TestCase):
    """API 접근 실패는 체인 트레이스백이 아니라 한 줄 메시지로 끝난다 — 로그에서 원인이 바로 보여야 한다."""

    def _run_main(self, *, actions: bool) -> SystemExit:
        env = {"GH_TOKEN": "x", "GITHUB_ACTIONS": "true"} if actions else {"GH_TOKEN": "x"}
        saved = {k: os.environ.pop(k, None) for k in ("GH_TOKEN", "GITHUB_ACTIONS")}
        orig_load, orig_argv = build_site.load_remote, sys.argv
        try:
            os.environ.update(env)
            build_site.load_remote = lambda *a, **k: (_ for _ in ()).throw(
                cards_data.ApiError("family-wiki 를 읽을 수 없다 (HTTP 404)")
            )
            sys.argv = ["build_site.py", "--out", "/nonexistent/should-not-be-created"]
            with self.assertRaises(SystemExit) as cm:
                build_site.main()
            return cm.exception
        finally:
            build_site.load_remote, sys.argv = orig_load, orig_argv
            for k, v in saved.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v

    def test_actions_에서는_error_주석으로_올린다(self):
        e = self._run_main(actions=True)
        self.assertEqual(e.code, "::error::family-wiki 를 읽을 수 없다 (HTTP 404)")
        self.assertIsNone(e.__cause__)

    def test_로컬에서는_오류_접두어(self):
        e = self._run_main(actions=False)
        self.assertEqual(e.code, "오류: family-wiki 를 읽을 수 없다 (HTTP 404)")

    def test_토큰이_없으면_local_을_알려_준다(self):
        saved = os.environ.pop("GH_TOKEN", None)
        orig_argv = sys.argv
        try:
            sys.argv = ["build_site.py", "--out", "/nonexistent/should-not-be-created"]
            with self.assertRaises(SystemExit) as cm:
                build_site.main()
            self.assertIn("--local", str(cm.exception.code))
        finally:
            sys.argv = orig_argv
            if saved is not None:
                os.environ["GH_TOKEN"] = saved


class 로컬_적재(unittest.TestCase):
    """schedule.json·changelog.json·daily.json 은 파일 하나가 카드 하나다. 없으면 없는 대로 간다."""

    def _root(self, files: dict[str, str]) -> pathlib.Path:
        root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / "data" / "profiles").mkdir(parents=True)
        (root / "data" / "projects").mkdir(parents=True)
        for name, body in files.items():
            (root / "data" / name).write_text(body, encoding="utf-8")
        return root

    def test_파일이_없으면_카드도_없다(self):
        self.assertEqual(cards_data.load_local(self._root({})), [])

    def test_읽으면_kind와_file이_붙는다(self):
        root = self._root(
            {
                "schedule.json": json.dumps(make_schedule(), ensure_ascii=False),
                "changelog.json": json.dumps(make_changelog(), ensure_ascii=False),
            }
        )
        got = {c.kind: c for c in cards_data.load_local(root)}
        self.assertEqual(sorted(got), ["changelog", "schedule"])
        self.assertEqual(got["schedule"].file, "schedule.json")
        self.assertTrue(got["schedule"].ok and got["changelog"].ok)

    def test_daily_json_도_카드_하나로_읽는다(self):
        root = self._root({"daily.json": json.dumps(make_daily(), ensure_ascii=False)})
        got = {c.kind: c for c in cards_data.load_local(root)}
        self.assertEqual(sorted(got), ["daily"])
        self.assertTrue(got["daily"].ok)
        bad = make_daily()
        bad["days"][0]["rooms"][0]["items"] = ["전화 010-1234-5678"]
        root = self._root({"daily.json": json.dumps(bad, ensure_ascii=False)})
        self.assertFalse(cards_data.load_local(root)[0].ok)

    def test_어긋나면_그_파일만_건너뛴다(self):
        bad = make_schedule()
        bad["events"][0]["kind"] = "회식"
        root = self._root(
            {
                "schedule.json": json.dumps(bad, ensure_ascii=False),
                "changelog.json": json.dumps(make_changelog(), ensure_ascii=False),
            }
        )
        got = {c.kind: c for c in cards_data.load_local(root)}
        self.assertFalse(got["schedule"].ok)
        self.assertTrue(got["changelog"].ok)

    def test_UTF8이_아닌_파일은_그것만_건너뛴다(self):
        """인코딩이 깨진 카드 하나가 빌드를 죽이면 사이트가 통째로 안 나온다."""
        root = self._root({"changelog.json": json.dumps(make_changelog(), ensure_ascii=False)})
        (root / "data" / "profiles" / "아빠.json").write_bytes(b'{"name": "\xc0\xc0"}')
        got = {c.file: c for c in cards_data.load_local(root)}
        self.assertFalse(got["profiles/아빠.json"].ok)
        self.assertTrue(got["changelog.json"].ok)  # 나머지는 그대로 들어온다

    def test_읽기_실패_사유에_파일명을_넣지_않는다(self):
        root = self._root({})
        (root / "data" / "profiles" / "김서연.json").write_bytes(b"\xff\xfe\x00bad")
        card = cards_data.load_local(root)[0]
        self.assertFalse(card.ok)
        for e in card.errors:
            self.assertNotIn("김서연", e)
            self.assertNotIn(str(root), e)

    def test_읽을_수_없는_파일이어도_빌드는_된다(self):
        root = self._root({})
        (root / "data" / "profiles" / "아빠.json").write_bytes(b"\xff\xfe\x00bad")
        out = pathlib.Path(tempfile.mkdtemp()) / "_site"
        self.addCleanup(shutil.rmtree, out.parent, True)
        build_site.build(cards_data.load_local(root), out)
        body = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn("검증에서 건너뛴 카드 1건", body)
        self.assertNotIn("아빠", body)

    def test_data_폴더가_없어도_빈_목록(self):
        """위키 클론에 아직 data/ 가 없어도 빌드가 멈추지 않는다."""
        root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        self.assertEqual(cards_data.load_local(root), [])


class 빌드_산출물(unittest.TestCase):
    """카드가 0건이어도 사이트는 만들어진다 (team-plan §7)."""

    def _out(self) -> pathlib.Path:
        out = pathlib.Path(tempfile.mkdtemp()) / "_site"
        self.addCleanup(shutil.rmtree, out.parent, True)
        return out

    def test_카드가_0건이어도_index가_생긴다(self):
        out = self._out()
        build_site.build([], out)
        self.assertTrue((out / "index.html").is_file())
        self.assertTrue((out / ".nojekyll").is_file())
        body = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn(f"<title>{cards_data.DEFAULT_GROUP} 카드</title>", body)

    def test_카드가_있으면_상세_페이지도_생긴다(self):
        out = self._out()
        cards = [
            cards_data.Card("profile", "profiles/아빠.json", make_profile()),
            cards_data.Card("project", "projects/제주여행.json", make_project()),
        ]
        build_site.build(cards, out)
        self.assertTrue((out / "m" / "아빠.html").is_file())
        self.assertTrue((out / "p" / "제주여행.html").is_file())
        self.assertIn(f"<title>{GROUP} 카드</title>", (out / "index.html").read_text(encoding="utf-8"))

    def test_건너뛴_카드는_종류와_건수만_남는다(self):
        """공개 index 하단에는 파일명도 사유도 적지 않는다 (2026-09-22 보안 검토)."""
        out = self._out()
        bad = make_profile()
        bad["gender"] = "남"
        card = cards_data.Card("profile", "profiles/아빠.json", bad, cards_data.validate_profile(bad, "아빠"))
        build_site.build([card], out)
        body = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn("검증에서 건너뛴 카드 1건", body)
        self.assertIn("가족 카드 1건 건너뜀", body)
        self.assertNotIn(".json", body)          # 파일명 없음 (`data/profiles/` 안내는 정적 문구다)
        self.assertNotIn("금지 키", body)         # 사유 없음
        self.assertNotIn("gender", body)
        self.assertFalse((out / "m" / "아빠.html").exists())

    def test_여러_종류가_건너뛰면_종류별로_센다(self):
        out = self._out()
        bad_profile = make_profile()
        bad_profile["gender"] = "남"
        bad_sched = make_schedule()
        bad_sched["events"][0]["kind"] = "회식"
        cards = [
            cards_data.Card("profile", "profiles/아빠.json", bad_profile, ["금지 키: $.gender"]),
            cards_data.Card("profile", "profiles/엄마.json", bad_profile, ["금지 키: $.gender"]),
            cards_data.Card("schedule", "schedule.json", bad_sched, ["events[0].kind"]),
        ]
        build_site.build(cards, out)
        body = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn("검증에서 건너뛴 카드 3건", body)
        self.assertIn("가족 카드 2건 · 일정 카드 1건 건너뜀", body)
        self.assertNotIn("엄마", body)

    def test_건너뛴_카드의_파일명은_HTML과_로그에_남지_않는다(self):
        """`CARDS_FORBIDDEN_NAMES` 로 막아 둔 이름이 파일명이면 그 이름이 인터넷에 나가면 안 된다.

        `data/profiles/김서연.json` 의 `name` 을 "첫째" 로 두면 파일명 불일치로 건너뛴다 —
        그때 사유·박스·로그 어디에도 파일명이 남지 않는지 끝에서 끝까지 확인한다.
        """
        import contextlib
        import io

        saved = os.environ.get("CARDS_FORBIDDEN_NAMES")
        os.environ["CARDS_FORBIDDEN_NAMES"] = "김서연"
        root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        if saved is None:
            self.addCleanup(lambda: os.environ.pop("CARDS_FORBIDDEN_NAMES", None))
        else:
            self.addCleanup(os.environ.__setitem__, "CARDS_FORBIDDEN_NAMES", saved)
        (root / "data" / "profiles").mkdir(parents=True)
        (root / "data" / "projects").mkdir(parents=True)
        card = make_profile()
        card["name"] = "첫째"
        (root / "data" / "profiles" / "김서연.json").write_text(
            json.dumps(card, ensure_ascii=False), encoding="utf-8"
        )
        out = self._out()
        orig_argv = sys.argv
        buf_out, buf_err = io.StringIO(), io.StringIO()
        try:
            sys.argv = ["build_site.py", "--local", str(root), "--out", str(out)]
            with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
                build_site.main()
        finally:
            sys.argv = orig_argv
        body = (out / "index.html").read_text(encoding="utf-8")
        logs = buf_out.getvalue() + buf_err.getvalue()
        self.assertIn("검증에서 건너뛴 카드 1건", body)
        self.assertIn("가족 카드", logs)  # 종류는 남아야 고칠 수 있다
        for where, blob in (("HTML", body), ("로그", logs)):
            with self.subTest(where=where):
                self.assertNotIn("김서연", blob)
                self.assertNotIn("첫째", blob)


class 달력에_없는_날짜(unittest.TestCase):
    def test_검증이_거부한다(self):
        s = make_schedule()
        s["events"][0]["date"] = "2026-09-31"
        self.assertTrue(any("달력에 없는" in e for e in cards_data.validate_schedule(s)))

    def test_창_계산이_건너뛴다(self):
        s = make_schedule()
        s["events"] = [{"date": "2026-09-31", "kind": "기타", "label": "없는 날"}]
        s["recurring"] = []
        self.assertEqual(cards_data.events_in_window(s, datetime.date(2026, 9, 29)), [])

    def test_하루짜리_end_는_비운다(self):
        s = make_schedule()
        s["events"] = [{"date": "2026-09-18", "end": "2026-09-18", "kind": "기타", "label": "하루"}]
        s["recurring"] = []
        got = cards_data.events_in_window(s, FRI)
        self.assertEqual(got[0]["end"], "")


if __name__ == "__main__":
    unittest.main()
