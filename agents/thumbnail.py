"""
thumbnail.py - noteサムネイル自動生成エージェント
Pillowで投資系のプロっぽいアイキャッチ画像を生成する
note推奨サイズ: 1280×670px
"""
import logging
import os
import sys
import textwrap
import random
import urllib.request
from pathlib import Path

logger = logging.getLogger("thumbnail")

# note推奨アイキャッチサイズ
WIDTH, HEIGHT = 1280, 670

# テーマ別カラースキーム
THEME_COLORS = {
    "japan_stocks": {
        "bg_top": (15, 30, 60),       # 深紺
        "bg_bottom": (30, 60, 120),   # 紺
        "accent": (255, 200, 0),      # ゴールド
        "text": (255, 255, 255),
        "sub_text": (180, 200, 255),
        "label": "日本株・銘柄分析",
        "icon": "📈",
    },
    "market_outlook": {
        "bg_top": (10, 40, 30),
        "bg_bottom": (20, 80, 60),
        "accent": (0, 220, 150),      # エメラルド
        "text": (255, 255, 255),
        "sub_text": (180, 255, 220),
        "label": "市場動向・マクロ分析",
        "icon": "🌐",
    },
    "nisa_investment": {
        "bg_top": (40, 20, 80),
        "bg_bottom": (80, 40, 140),
        "accent": (255, 120, 200),    # ピンク
        "text": (255, 255, 255),
        "sub_text": (220, 180, 255),
        "label": "NISA・長期投資",
        "icon": "💰",
    },
    "investment_strategy": {
        "bg_top": (60, 20, 10),
        "bg_bottom": (120, 40, 20),
        "accent": (255, 140, 0),      # オレンジ
        "text": (255, 255, 255),
        "sub_text": (255, 210, 180),
        "label": "投資戦略・メンタル",
        "icon": "🎯",
    },
}

FONT_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fonts")
NOTO_FONT_URL = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Bold.otf"
NOTO_FONT_REGULAR_URL = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf"


def get_font(size: int, bold: bool = False):
    """日本語フォントを取得（なければシステムフォントにフォールバック）"""
    try:
        from PIL import ImageFont
        os.makedirs(FONT_CACHE_DIR, exist_ok=True)

        font_file = os.path.join(FONT_CACHE_DIR, "NotoSansCJKjp-Bold.otf" if bold else "NotoSansCJKjp-Regular.otf")

        if not os.path.exists(font_file):
            url = NOTO_FONT_URL if bold else NOTO_FONT_REGULAR_URL
            logger.info(f"フォントをダウンロード中: {url}")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    with open(font_file, "wb") as f:
                        f.write(r.read())
            except Exception as e:
                logger.warning(f"フォントDL失敗: {e}")
                return ImageFont.load_default()

        return ImageFont.truetype(font_file, size)
    except Exception as e:
        logger.warning(f"フォント読み込み失敗: {e}")
        from PIL import ImageFont
        return ImageFont.load_default()


def draw_gradient(img, color_top: tuple, color_bottom: tuple):
    """縦グラデーション背景を描画"""
    from PIL import Image
    import struct

    pixels = img.load()
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
        g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
        b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)
        for x in range(WIDTH):
            pixels[x, y] = (r, g, b)


def draw_chart_decoration(draw, accent_color: tuple):
    """右下にダミーの株価チャート風デコレーションを描画"""
    # シンプルな上昇トレンドラインと棒グラフ
    chart_data = [320, 290, 350, 310, 380, 360, 420, 390, 460, 440, 500, 480, 550]
    base_x = 800
    base_y = 580
    col_width = 30
    spacing = 8

    for i, val in enumerate(chart_data):
        x = base_x + i * (col_width + spacing)
        h = int(val * 0.18)
        alpha = 60 + i * 12  # 薄いバーから濃くなる
        bar_color = (*accent_color, min(alpha, 180))
        draw.rectangle([x, base_y - h, x + col_width, base_y], fill=accent_color[:3] + (min(alpha, 150),))

    # トレンドライン
    points = []
    for i, val in enumerate(chart_data):
        x = base_x + i * (col_width + spacing) + col_width // 2
        y = base_y - int(val * 0.18)
        points.append((x, y))

    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=accent_color, width=3)


def wrap_title(title: str, max_chars_per_line: int = 18) -> list[str]:
    """タイトルを適切な行数に折り返す"""
    if len(title) <= max_chars_per_line:
        return [title]

    lines = []
    while title:
        if len(title) <= max_chars_per_line:
            lines.append(title)
            break
        # 句読点・括弧で区切れる場所を探す
        cut = max_chars_per_line
        for punct in ['】', '。', '、', '｜', '：']:
            idx = title[:max_chars_per_line + 1].rfind(punct)
            if idx > max_chars_per_line // 2:
                cut = idx + 1
                break
        lines.append(title[:cut])
        title = title[cut:]

    return lines[:3]  # 最大3行


def generate_thumbnail(article: dict, output_path: str) -> str:
    """
    記事情報からサムネイル画像を生成して保存する
    Returns: 保存したファイルパス
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        logger.error("Pillowがインストールされていません: pip install Pillow")
        return ""

    theme_id = article.get("theme_id", "japan_stocks")
    colors = THEME_COLORS.get(theme_id, THEME_COLORS["japan_stocks"])
    title = article.get("title", "投資実践レポート")
    style_name = article.get("style", "実践シリーズ")

    # キャンバス作成
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img, "RGBA")

    # グラデーション背景
    draw_gradient(img, colors["bg_top"], colors["bg_bottom"])

    # 左側にアクセントバー
    draw.rectangle([0, 0, 8, HEIGHT], fill=colors["accent"])

    # チャート風デコレーション（右下）
    try:
        draw_chart_decoration(draw, colors["accent"])
    except Exception:
        pass

    # 右上にシリーズラベル
    font_small = get_font(28, bold=False)
    draw.text((WIDTH - 20, 30), colors["label"], font=font_small,
              fill=colors["sub_text"], anchor="rt")

    # スタイルバッジ
    badge_text = f"  {style_name}  "
    font_badge = get_font(26, bold=True)
    badge_x, badge_y = 50, 60
    draw.rounded_rectangle(
        [badge_x - 4, badge_y - 4, badge_x + len(badge_text) * 15 + 4, badge_y + 40],
        radius=8, fill=colors["accent"]
    )
    draw.text((badge_x, badge_y), badge_text, font=font_badge, fill=(20, 20, 20))

    # メインタイトル
    title_lines = wrap_title(title, max_chars_per_line=20)
    font_title = get_font(64, bold=True)
    font_title_small = get_font(52, bold=True)

    title_y = 160
    for i, line in enumerate(title_lines):
        font = font_title if i == 0 else font_title_small
        # 影効果
        draw.text((52, title_y + 3), line, font=font, fill=(0, 0, 0, 100))
        draw.text((50, title_y), line, font=font, fill=colors["text"])
        title_y += (72 if i == 0 else 62)

    # 区切り線
    line_y = title_y + 20
    draw.line([(50, line_y), (400, line_y)], fill=colors["accent"], width=3)

    # サブテキスト
    font_sub = get_font(32, bold=False)
    theme_name = article.get("theme_name", "日本株・投資")
    draw.text((50, line_y + 20), f"#{theme_name}  #投資実践  #中級者向け",
              font=font_sub, fill=colors["sub_text"])

    # 下部ブランド名
    font_brand = get_font(30, bold=True)
    draw.text((50, HEIGHT - 50), "投資実践ノート by note",
              font=font_brand, fill=colors["accent"])

    # 保存
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG", optimize=True)
    logger.info(f"サムネイル生成: {output_path} ({WIDTH}x{HEIGHT}px)")
    return output_path


def run(article: dict) -> str:
    """サムネイル生成のメイン処理"""
    logger.info("=== サムネイル生成 開始 ===")

    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "thumbnails"
    )
    filename = f"thumb_{article.get('theme_id', 'default')}_{hash(article.get('title', '')) % 10000:04d}.png"
    output_path = os.path.join(output_dir, filename)

    result = generate_thumbnail(article, output_path)
    if result:
        logger.info("=== サムネイル生成 完了 ===")
    else:
        logger.error("=== サムネイル生成 失敗 ===")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_article = {
        "title": "【実録】高配当株で年間配当30万円を達成するまでの道のり",
        "theme_id": "japan_stocks",
        "theme_name": "日本株・個別銘柄",
        "style": "売買判断レポート",
    }
    path = run(test_article)
    if path:
        print(f"生成完了: {path}")
