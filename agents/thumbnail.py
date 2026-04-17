"""
thumbnail.py - noteサムネイル自動生成エージェント
参考スタイル: 濃紺背景 + 超大タイトル(左) + オレンジアイコン(右)
note推奨サイズ: 1280×670px
"""
import logging
import math
import os
import random
import urllib.request

logger = logging.getLogger("thumbnail")

WIDTH, HEIGHT = 1280, 670

# ──────────────────────────────────────────────────
# テーマ別設定
# ──────────────────────────────────────────────────
THEME_COLORS = {
    "japan_stocks": {
        "bg": (12, 22, 60),
        "accent": (255, 160, 30),   # オレンジ
        "text": (255, 255, 255),
        "sub_text": (180, 200, 240),
        "label": "日本株・銘柄分析",
        "icon_set": "chart",
    },
    "market_outlook": {
        "bg": (8, 35, 28),
        "accent": (0, 210, 140),    # エメラルド
        "text": (255, 255, 255),
        "sub_text": (160, 230, 200),
        "label": "市場動向・マクロ",
        "icon_set": "globe",
    },
    "nisa_investment": {
        "bg": (20, 15, 55),
        "accent": (200, 100, 255),  # バイオレット
        "text": (255, 255, 255),
        "sub_text": (200, 175, 255),
        "label": "NISA・長期投資",
        "icon_set": "piggy",
    },
    "investment_strategy": {
        "bg": (40, 15, 8),
        "accent": (255, 120, 30),   # オレンジレッド
        "text": (255, 255, 255),
        "sub_text": (255, 190, 140),
        "label": "投資戦略・メンタル",
        "icon_set": "target",
    },
}

FONT_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fonts"
)
NOTO_BOLD_URL = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Bold.otf"
NOTO_REGULAR_URL = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf"

SYSTEM_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJKjp-Bold.otf",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/Library/Fonts/Arial Unicode MS.ttf",
    "/mnt/c/Windows/Fonts/meiryo.ttc",
]


def _dl_font(url, path):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            with open(path, "wb") as f:
                f.write(r.read())
        return True
    except Exception as e:
        logger.warning(f"フォントDL失敗: {e}")
        return False


def get_font(size: int, bold: bool = True):
    from PIL import ImageFont
    os.makedirs(FONT_CACHE_DIR, exist_ok=True)
    fname = "NotoSansCJKjp-Bold.otf" if bold else "NotoSansCJKjp-Regular.otf"
    fpath = os.path.join(FONT_CACHE_DIR, fname)
    url = NOTO_BOLD_URL if bold else NOTO_REGULAR_URL
    if not os.path.exists(fpath):
        logger.info(f"フォントDL中: {fname}")
        if not _dl_font(url, fpath):
            for sf in SYSTEM_FONT_CANDIDATES:
                if os.path.exists(sf):
                    try:
                        return ImageFont.truetype(sf, size)
                    except Exception:
                        continue
            return ImageFont.load_default()
    try:
        return ImageFont.truetype(fpath, size)
    except Exception:
        return ImageFont.load_default()


# ──────────────────────────────────────────────────
# ピクセル幅ベースのテキスト折り返し
# ──────────────────────────────────────────────────

def wrap_text_pixels(text: str, font, max_width: int) -> list[str]:
    from PIL import Image, ImageDraw
    tmp = Image.new("RGB", (1, 1))
    d = ImageDraw.Draw(tmp)

    def tw(t):
        if not t:
            return 0
        bb = d.textbbox((0, 0), t, font=font)
        return bb[2] - bb[0]

    if tw(text) <= max_width:
        return [text]

    BREAK_AFTER = set("】。、｜：！？")
    lines, remaining = [], text
    while remaining:
        if tw(remaining) <= max_width:
            lines.append(remaining)
            break
        lo, hi = 1, len(remaining)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if tw(remaining[:mid]) <= max_width:
                lo = mid
            else:
                hi = mid - 1
        cut = lo
        for i in range(cut, max(cut - 8, 0), -1):
            if remaining[i - 1] in BREAK_AFTER:
                cut = i
                break
        lines.append(remaining[:cut])
        remaining = remaining[cut:]
        if len(lines) >= 4:
            if remaining:
                last = lines[-1]
                while last and tw(last + "…") > max_width:
                    last = last[:-1]
                lines[-1] = last + "…"
            break
    return lines


# ──────────────────────────────────────────────────
# アイコン描画（PIL プリミティブで近似）
# ──────────────────────────────────────────────────

def draw_calendar_icon(draw, cx, cy, size, color, bg):
    """カレンダーアイコン"""
    s = size
    x0, y0 = cx - s // 2, cy - s // 2
    x1, y1 = cx + s // 2, cy + s // 2
    r = s // 8
    # 外枠
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=color)
    # 内側（白っぽい）
    inner = s // 8
    draw.rounded_rectangle(
        [x0 + inner, y0 + inner * 2, x1 - inner, y1 - inner],
        radius=r // 2, fill=bg
    )
    # ヘッダー部（色）
    draw.rounded_rectangle([x0, y0, x1, y0 + s // 4], radius=r, fill=color)
    # グリッド（3×3）
    grid_x0 = x0 + inner * 2
    grid_y0 = y0 + s // 4 + inner
    grid_x1 = x1 - inner * 2
    grid_y1 = y1 - inner
    cols, rows = 3, 3
    cw = (grid_x1 - grid_x0) // cols
    ch = (grid_y1 - grid_y0) // rows
    cell_r = max(2, cw // 6)
    for gy in range(rows):
        for gx in range(cols):
            bx0 = grid_x0 + gx * cw + 2
            by0 = grid_y0 + gy * ch + 2
            draw.rounded_rectangle(
                [bx0, by0, bx0 + cw - 4, by0 + ch - 4],
                radius=cell_r, fill=color
            )
    # 留め具（上部2つ）
    pin_w, pin_h = max(4, s // 12), max(8, s // 7)
    for px in [x0 + s // 4, x1 - s // 4]:
        draw.rounded_rectangle(
            [px - pin_w // 2, y0 - pin_h // 2, px + pin_w // 2, y0 + pin_h // 2],
            radius=pin_w // 2, fill=color
        )


def draw_lightbulb_icon(draw, cx, cy, size, color, bg):
    """電球アイコン"""
    s = size
    bulb_r = int(s * 0.36)
    # 電球本体（円）
    draw.ellipse([cx - bulb_r, cy - bulb_r - s // 10,
                  cx + bulb_r, cy + bulb_r - s // 10], fill=color)
    # ベース（台形）
    base_w = int(bulb_r * 1.0)
    base_h = int(s * 0.22)
    base_y = cy + bulb_r - s // 10
    points = [
        (cx - base_w // 2, base_y),
        (cx + base_w // 2, base_y),
        (cx + base_w // 3, base_y + base_h),
        (cx - base_w // 3, base_y + base_h),
    ]
    draw.polygon(points, fill=color)
    # 光の筋（白線）
    shine_w = max(2, s // 20)
    for offset, length in [(-bulb_r // 3, bulb_r // 2), (0, int(bulb_r * 0.7)),
                            (bulb_r // 3, bulb_r // 2)]:
        sx = cx + offset
        draw.line([(sx, cy - bulb_r - s // 10 - 4),
                   (sx, cy - bulb_r - s // 10 - 4 - length)],
                  fill=bg, width=shine_w)


def draw_circular_arrow(draw, cx, cy, size, color):
    """循環矢印アイコン（円弧＋矢頭）"""
    r = int(size * 0.38)
    lw = max(3, size // 12)
    # 上半分の弧（時計回り）
    draw.arc([cx - r, cy - r, cx + r, cy + r], start=200, end=20, fill=color, width=lw)
    # 下半分の弧（反時計回り）
    draw.arc([cx - r, cy - r, cx + r, cy + r], start=20, end=200, fill=color, width=lw)
    # 矢頭（右上）
    ah = lw * 2
    ax = int(cx + r * math.cos(math.radians(20)))
    ay = int(cy - r * math.sin(math.radians(20)))
    draw.polygon([(ax, ay - ah), (ax + ah, ay), (ax - ah, ay)], fill=color)
    # 矢頭（左下）
    ax2 = int(cx + r * math.cos(math.radians(200)))
    ay2 = int(cy - r * math.sin(math.radians(200)))
    draw.polygon([(ax2, ay2 + ah), (ax2 - ah, ay2), (ax2 + ah, ay2)], fill=color)


def draw_pencil_icon(draw, cx, cy, size, color, bg):
    """鉛筆アイコン"""
    # 鉛筆を斜め45度で描画
    s = size
    pw = max(4, s // 6)   # 幅
    ph = int(s * 0.75)    # 長さ
    tip = int(s * 0.2)    # 先端
    # 胴体（回転した長方形を多角形で）
    angle = -45  # 度
    rad = math.radians(angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)

    def rot(dx, dy):
        return (cx + dx * cos_a - dy * sin_a,
                cy + dx * sin_a + dy * cos_a)

    # 胴体
    body = [rot(-pw // 2, -ph // 2 + tip),
            rot(pw // 2, -ph // 2 + tip),
            rot(pw // 2, ph // 2),
            rot(-pw // 2, ph // 2)]
    draw.polygon(body, fill=color)
    # 先端（三角形）
    tip_pts = [rot(0, -ph // 2),
               rot(pw // 2, -ph // 2 + tip),
               rot(-pw // 2, -ph // 2 + tip)]
    draw.polygon(tip_pts, fill=bg)
    # 消しゴム部（後端）
    eraser = [rot(-pw // 2, ph // 2),
              rot(pw // 2, ph // 2),
              rot(pw // 2, ph // 2 + max(4, s // 8)),
              rot(-pw // 2, ph // 2 + max(4, s // 8))]
    draw.polygon(eraser, fill=(220, 220, 220))


def draw_target_icon(draw, cx, cy, size, color, bg):
    """ターゲット（的）アイコン"""
    for i, (r, fill) in enumerate([(size // 2, color),
                                    (size // 3, bg),
                                    (size // 5, color),
                                    (size // 10, bg)]):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def draw_chart_icon(draw, cx, cy, size, color, bg):
    """上昇チャートアイコン"""
    s = size
    # 枠
    x0, y0 = cx - s // 2, cy - s // 2
    x1, y1 = cx + s // 2, cy + s // 2
    draw.rectangle([x0, y0, x1, y1], fill=color)
    # 棒グラフ
    bars = [0.4, 0.55, 0.45, 0.7, 0.65, 0.85]
    bw = (x1 - x0 - (len(bars) + 1) * 4) // len(bars)
    for i, h in enumerate(bars):
        bx = x0 + 4 + i * (bw + 4)
        bh = int((y1 - y0 - 10) * h)
        draw.rectangle([bx, y1 - 5 - bh, bx + bw, y1 - 5], fill=bg)


ICON_SETS = {
    "chart": [
        (draw_chart_icon, 0),
        (draw_circular_arrow, 1),
        (draw_pencil_icon, 2),
    ],
    "globe": [
        (draw_calendar_icon, 0),
        (draw_circular_arrow, 1),
        (draw_lightbulb_icon, 2),
    ],
    "piggy": [
        (draw_lightbulb_icon, 0),
        (draw_calendar_icon, 1),
        (draw_target_icon, 2),
    ],
    "target": [
        (draw_target_icon, 0),
        (draw_circular_arrow, 1),
        (draw_pencil_icon, 2),
    ],
}


def draw_icon_group(draw, icon_set_name: str, accent, bg, area_x, area_y, area_w, area_h):
    """右エリアにアイコングループを配置"""
    icon_size = min(area_w, area_h) // 2
    icons = ICON_SETS.get(icon_set_name, ICON_SETS["chart"])

    positions = [
        (area_x + area_w // 2, area_y + area_h // 4),         # 中央上
        (area_x + area_w * 3 // 4, area_y + area_h * 3 // 4), # 右下
        (area_x + area_w // 4, area_y + area_h * 2 // 3),     # 左下
    ]

    for (draw_fn, idx), (icx, icy) in zip(icons, positions):
        sz = icon_size if idx == 0 else int(icon_size * 0.7)
        try:
            draw_fn(draw, icx, icy, sz, accent, bg)
        except Exception as e:
            logger.debug(f"アイコン描画スキップ: {e}")


# ──────────────────────────────────────────────────
# メイン生成関数
# ──────────────────────────────────────────────────

def generate_thumbnail(article: dict, output_path: str) -> str:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        logger.error("Pillow未インストール: pip install Pillow")
        return ""

    theme_id = article.get("theme_id", "japan_stocks")
    colors = THEME_COLORS.get(theme_id, THEME_COLORS["japan_stocks"])
    title = article.get("title", "投資実践レポート")
    style_name = article.get("style", "")
    series_no = article.get("series_no", "")

    bg = colors["bg"]
    accent = colors["accent"]
    text_color = colors["text"]
    sub_color = colors["sub_text"]

    img = Image.new("RGB", (WIDTH, HEIGHT), bg)
    draw = ImageDraw.Draw(img, "RGBA")

    # ── レイアウト定数 ──────────────────────────────
    MARGIN = 60
    TEXT_AREA_W = int(WIDTH * 0.63)   # タイトルを置く幅
    ICON_AREA_X = int(WIDTH * 0.61)   # アイコンエリア左端
    ICON_AREA_W = WIDTH - ICON_AREA_X
    ICON_AREA_H = HEIGHT

    # ── 背景：微妙な暗い斜線でテクスチャ感 ────────────
    line_color = tuple(max(0, c - 8) for c in bg)
    for x_offset in range(-HEIGHT, WIDTH, 40):
        draw.line(
            [(x_offset, 0), (x_offset + HEIGHT, HEIGHT)],
            fill=line_color, width=1
        )

    # ── 左端アクセントバー ──────────────────────────
    draw.rectangle([0, 0, 7, HEIGHT], fill=accent)

    # ── 右エリア：薄いオーバーレイ ───────────────────
    draw.rectangle(
        [ICON_AREA_X, 0, WIDTH, HEIGHT],
        fill=(*bg, 0)  # 透明（背景と同じ）
    )

    # ── アイコングループ描画 ─────────────────────────
    icon_set_name = colors.get("icon_set", "chart")
    draw_icon_group(draw, icon_set_name, accent, bg,
                    ICON_AREA_X, 0, ICON_AREA_W, ICON_AREA_H)

    # ── 上部ラベル帯 ────────────────────────────────
    label_h = 56
    draw.rectangle([0, 0, TEXT_AREA_W, label_h], fill=(*accent, 220))

    # ラベルテキスト
    font_label = get_font(28, bold=True)
    label_parts = []
    if series_no:
        label_parts.append(f"【{series_no}】")
    label_parts.append(f"{colors['label']}で収益化！")
    if style_name:
        label_parts.append(f" — {style_name}")
    label_text = "".join(label_parts)

    draw.text((MARGIN, 14), label_text, font=font_label, fill=(15, 15, 15))

    # ── メインタイトル ──────────────────────────────
    title_top = label_h + 30
    title_max_h = HEIGHT - title_top - 120  # 下部余白分
    title_max_w = TEXT_AREA_W - MARGIN - 20

    # フォントサイズを動的に決定
    chosen_font = None
    chosen_lines = None
    for font_size in (100, 88, 76, 66, 56, 48):
        f = get_font(font_size, bold=True)
        lines = wrap_text_pixels(title, f, title_max_w)
        line_h = font_size + int(font_size * 0.2)
        if len(lines) * line_h <= title_max_h:
            chosen_font = f
            chosen_lines = lines
            chosen_line_h = line_h
            break
    if chosen_font is None:
        chosen_font = get_font(48, bold=True)
        chosen_lines = wrap_text_pixels(title, chosen_font, title_max_w)
        chosen_line_h = 62

    cur_y = title_top
    for line in chosen_lines:
        # テキストシャドウ（奥行き感）
        draw.text((MARGIN + 4, cur_y + 4), line,
                  font=chosen_font, fill=(0, 0, 0, 160))
        draw.text((MARGIN, cur_y), line, font=chosen_font, fill=text_color)
        cur_y += chosen_line_h

    # ── 区切りライン ────────────────────────────────
    sep_y = cur_y + 18
    draw.rectangle([MARGIN, sep_y, MARGIN + 200, sep_y + 4], fill=accent)

    # ── サブテキスト（タグ） ──────────────────────────
    theme_name = article.get("theme_name", "日本株・投資")
    font_sub = get_font(26, bold=False)
    draw.text((MARGIN, sep_y + 14),
              f"＃{theme_name}　＃投資実践　＃中級者向け",
              font=font_sub, fill=sub_color)

    # ── ブランド名（左下） ───────────────────────────
    font_brand = get_font(28, bold=True)
    draw.text((MARGIN, HEIGHT - 46), "投資実践ノート",
              font=font_brand, fill=accent)

    # ── 保存 ────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG", optimize=True)
    logger.info(f"サムネイル生成: {output_path} ({WIDTH}x{HEIGHT}px)")
    return output_path


# ──────────────────────────────────────────────────
# エントリポイント
# ──────────────────────────────────────────────────

def run(article: dict) -> str:
    logger.info("=== サムネイル生成 開始 ===")
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "thumbnails",
    )
    filename = (
        f"thumb_{article.get('theme_id', 'default')}"
        f"_{hash(article.get('title', '')) % 10000:04d}.png"
    )
    output_path = os.path.join(output_dir, filename)
    result = generate_thumbnail(article, output_path)
    if result:
        logger.info("=== サムネイル生成 完了 ===")
    else:
        logger.error("=== サムネイル生成 失敗 ===")
    return result


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO)

    test_cases = [
        {
            "title": "【実録】米国株下落時の日本株の動き方で実際にやった売買判断と結果",
            "theme_id": "market_outlook",
            "theme_name": "市場動向・マクロ",
            "style": "時事考察",
            "series_no": "第9回",
        },
        {
            "title": "正直に言います。高配当株で失敗した本当の理由と今やっていること",
            "theme_id": "japan_stocks",
            "theme_name": "日本株・個別銘柄",
            "style": "実録・失敗告白",
            "series_no": "第7回",
        },
        {
            "title": "損切りできない人が読むべき投資メンタル管理術",
            "theme_id": "investment_strategy",
            "theme_name": "投資戦略・メンタル",
            "style": "投資メンタル",
            "series_no": "",
        },
    ]
    for article in test_cases:
        path = run(article)
        print(f"{'OK' if path else 'NG'}: {path or article['title']}")
