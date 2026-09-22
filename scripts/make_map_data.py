#!/usr/bin/env python3
"""여행 지도 카드의 윤곽선을 한 번 내려받아 `scripts/map_data.py` 로 굳힌다 (생성기).

    python3 scripts/make_map_data.py                    # scripts/map_data.py 를 다시 만든다
    python3 scripts/make_map_data.py --out /tmp/x.py    # 다른 곳에 써 보기

빌드(`build_site.py`)는 네트워크를 쓰지 않는다. 이 스크립트만 네트워크를 쓰고, 결과 파일을 커밋한다.
경계가 바뀌는 일은 거의 없으므로 다시 돌릴 일도 거의 없다.

출처는 Natural Earth (public domain) 다.
  세계 — ne_110m_admin_0_countries.geojson  (모든 나라)
  한국 — ne_50m_admin_0_countries.geojson   (`ADMIN == "South Korea"` 폴리곤만)

투영은 등장방형(equirectangular) 이다 — `x = lon`, `y = -lat`. viewBox 좌표가 곧 경위도라
렌더러가 핀을 찍을 때 따로 변환할 것이 없다 (`project_world`·`project_korea`).

단순화는 Douglas-Peucker 를 직접 돌린다 (표준 라이브러리만 쓴다). 크기 상한
(세계 150KB · 한국 40KB) 에 맞을 때까지 허용 오차를 키우며 다시 줄인다.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

KST = timezone(timedelta(hours=9), "KST")

RAW = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson"
WORLD_URL = f"{RAW}/ne_110m_admin_0_countries.geojson"
KOREA_URL = f"{RAW}/ne_50m_admin_0_countries.geojson"
KOREA_ADMIN = "South Korea"

WORLD_MAX_BYTES = 150 * 1024
KOREA_MAX_BYTES = 40 * 1024

Ring = list[tuple[float, float]]


# ─────────────────────────────────────────────────────────────────── 받기·고르기


def fetch_geojson(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "family-card-map-builder"})
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 (고정 https 주소)
        data = json.load(resp)
    if not isinstance(data, dict) or not isinstance(data.get("features"), list):
        raise SystemExit(f"GeoJSON 이 아니다: {url}")
    return data


def rings_of(geometry: object) -> list[Ring]:
    """Polygon·MultiPolygon 의 바깥 고리만 (구멍은 카드 크기에 비해 보이지 않는다)."""
    if not isinstance(geometry, dict):
        return []
    kind, coords = geometry.get("type"), geometry.get("coordinates")
    out: list[Ring] = []
    if kind == "Polygon" and isinstance(coords, list) and coords:
        out.append([(float(x), float(y)) for x, y in coords[0]])
    elif kind == "MultiPolygon" and isinstance(coords, list):
        for poly in coords:
            if isinstance(poly, list) and poly:
                out.append([(float(x), float(y)) for x, y in poly[0]])
    return out


def collect_rings(geo: dict[str, Any], admin: str | None = None) -> list[Ring]:
    rings: list[Ring] = []
    for feat in geo["features"]:
        if not isinstance(feat, dict):
            continue
        props = feat.get("properties") or {}
        if admin is not None and str(props.get("ADMIN", "")) != admin:
            continue
        rings.extend(rings_of(feat.get("geometry")))
    return rings


# ───────────────────────────────────────────────────────────── 단순화 (Douglas-Peucker)


def _seg_dist(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    """점 p 와 선분 ab 의 수직 거리 (도 단위)."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def simplify(points: Ring, tol: float) -> Ring:
    """Douglas-Peucker. 반복문으로 돈다 — 고리가 길어도 재귀 한도에 걸리지 않게."""
    if len(points) < 3 or tol <= 0:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi - lo < 2:
            continue
        worst, worst_i = -1.0, -1
        for i in range(lo + 1, hi):
            d = _seg_dist(points[i], points[lo], points[hi])
            if d > worst:
                worst, worst_i = d, i
        if worst > tol:
            keep[worst_i] = True
            stack.append((lo, worst_i))
            stack.append((worst_i, hi))
    return [p for p, k in zip(points, keep) if k]


def ring_extent(ring: Ring) -> float:
    """고리의 바깥 사각형 긴 변 (도). 아주 작은 섬을 걸러내는 기준이다."""
    xs = [x for x, _ in ring]
    ys = [y for _, y in ring]
    return max(max(xs) - min(xs), max(ys) - min(ys))


# ─────────────────────────────────────────────────────────────────── SVG 경로 문자열


def fmt(v: float, digits: int) -> str:
    s = f"{v:.{digits}f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0", "-") else s


def to_path(rings: list[Ring], digits: int) -> str:
    """등장방형 SVG 경로 — `x = lon`, `y = -lat`. 고리마다 `M…L…Z`."""
    parts: list[str] = []
    for ring in rings:
        if len(ring) < 3:
            continue
        pts = [(fmt(lon, digits), fmt(-lat, digits)) for lon, lat in ring]
        if pts[0] == pts[-1]:
            pts = pts[:-1]  # Z 가 닫아 준다
        if len(pts) < 3:
            continue
        head = f"M{pts[0][0]} {pts[0][1]}"
        tail = "".join(f"L{x} {y}" for x, y in pts[1:])
        parts.append(head + tail + "Z")
    return "".join(parts)


def shrink(
    rings: list[Ring], *, max_bytes: int, digits: int, tol0: float, min_extent: float
) -> tuple[str, float]:
    """상한에 맞을 때까지 허용 오차를 키운다. (경로 문자열, 쓴 허용 오차)."""
    tol = tol0
    for _ in range(40):
        kept = [r for r in rings if ring_extent(r) >= min_extent * max(tol / tol0, 1.0)]
        path = to_path([simplify(r, tol) for r in kept], digits)
        if len(path.encode("utf-8")) <= max_bytes:
            return path, tol
        tol *= 1.3
    raise SystemExit(f"상한 {max_bytes}B 까지 줄이지 못했다 (마지막 허용 오차 {tol:.3f}°)")


def viewbox(rings: list[Ring], pad: float, digits: int) -> str:
    xs = [x for r in rings for x, _ in r]
    ys = [-y for r in rings for _, y in r]
    x0, x1 = min(xs) - pad, max(xs) + pad
    y0, y1 = min(ys) - pad, max(ys) + pad
    return f"{fmt(x0, digits)} {fmt(y0, digits)} {fmt(x1 - x0, digits)} {fmt(y1 - y0, digits)}"


# ─────────────────────────────────────────────────────────────────────── 파일 쓰기


HEADER = '''#!/usr/bin/env python3
"""여행 지도 카드가 쓰는 윤곽선 (생성물 — 손으로 고치지 않는다).

    다시 만들기: python3 scripts/make_map_data.py

출처: Natural Earth {ne_ver} — **public domain** (저작권 없음, 출처 표기 의무 없음).
  세계 ne_110m_admin_0_countries · 한국 ne_50m_admin_0_countries (`ADMIN == "South Korea"`)
  받아 온 주소는 make_map_data.py 에 있다 (이 파일에는 링크를 두지 않는다 — 카드 검증기가 링크를 막는다).
생성 {generated} · Douglas-Peucker 허용 오차 세계 {world_tol:.3f}° · 한국 {korea_tol:.3f}°

투영은 등장방형이다 — `x = lon`, `y = -lat`. viewBox 좌표가 곧 경위도라 핀을 찍을 때
`project_world`·`project_korea` 가 값을 그대로 넘긴다 (변환 상수가 없다).
빌드는 네트워크를 쓰지 않는다.
"""

from __future__ import annotations

'''

TAIL = '''

def project_world(lat: float, lon: float) -> tuple[float, float]:
    """세계 지도 좌표 (WORLD_VIEWBOX 와 같은 좌표계). 등장방형이라 `(lon, -lat)` 이다."""
    return float(lon), -float(lat)


def project_korea(lat: float, lon: float) -> tuple[float, float]:
    """한국 지도 좌표 (KOREA_VIEWBOX 와 같은 좌표계). 세계와 같은 등장방형이고 viewBox 만 다르다."""
    return float(lon), -float(lat)
'''


def render_module(
    world_path: str, world_vb: str, korea_path: str, korea_vb: str, world_tol: float, korea_tol: float
) -> str:
    head = HEADER.format(
        ne_ver="v5 (nvkelso/natural-earth-vector)",
        generated=datetime.now(KST).date().isoformat(),
        world_tol=world_tol,
        korea_tol=korea_tol,
    )
    body = (
        f'WORLD_VIEWBOX = "{world_vb}"\n'
        f'KOREA_VIEWBOX = "{korea_vb}"\n\n'
        f'WORLD_PATH = (\n{wrap(world_path)}\n)\n\n'
        f'KOREA_PATH = (\n{wrap(korea_path)}\n)\n'
    )
    return head + body + TAIL


def wrap(path: str, width: int = 112) -> str:
    """긴 경로 문자열을 줄로 접는다 — 한 줄이 수십 KB 면 편집기가 버벅인다."""
    lines = []
    i = 0
    while i < len(path):
        cut = min(i + width, len(path))
        if cut < len(path):  # 좌표 가운데서 끊지 않는다 — 명령 문자(M·L·Z) 앞에서만 끊는다
            j = cut
            while j > i + 1 and path[j] not in "MLZ":
                j -= 1
            if j > i + 1:
                cut = j
        lines.append('    "' + path[i:cut] + '"')
        i = cut
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Natural Earth 경계를 받아 scripts/map_data.py 를 만든다")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "map_data.py"), metavar="FILE")
    args = ap.parse_args()

    print(f"세계 경계 받는 중 … {WORLD_URL}", file=sys.stderr)
    world_rings = collect_rings(fetch_geojson(WORLD_URL))
    print(f"  고리 {len(world_rings)}개", file=sys.stderr)
    print(f"한국 경계 받는 중 … {KOREA_URL}", file=sys.stderr)
    korea_rings = collect_rings(fetch_geojson(KOREA_URL), admin=KOREA_ADMIN)
    print(f"  고리 {len(korea_rings)}개", file=sys.stderr)
    if not world_rings or not korea_rings:
        raise SystemExit("경계를 하나도 못 골랐다 — 속성 이름이 바뀌었는지 본다 (ADMIN)")

    # viewBox 는 단순화 전 원본 범위로 잡는다 — 줄여도 그림이 잘려 나가지 않게.
    world_vb = "-180 -90 360 180"  # 등장방형 전체. 지구 전체를 언제나 같은 자리에 둔다
    korea_vb = viewbox(korea_rings, pad=0.35, digits=2)

    world_path, world_tol = shrink(world_rings, max_bytes=WORLD_MAX_BYTES, digits=2, tol0=0.09, min_extent=0.6)
    korea_path, korea_tol = shrink(korea_rings, max_bytes=KOREA_MAX_BYTES, digits=3, tol0=0.005, min_extent=0.02)

    out = Path(args.out)
    out.write_text(
        render_module(world_path, world_vb, korea_path, korea_vb, world_tol, korea_tol), encoding="utf-8"
    )
    print(
        f"{out} 생성 — 세계 {len(world_path.encode()) / 1024:.1f}KB (오차 {world_tol:.3f}°) · "
        f"한국 {len(korea_path.encode()) / 1024:.1f}KB (오차 {korea_tol:.3f}°) · "
        f"한국 viewBox {korea_vb}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
