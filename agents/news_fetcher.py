"""
news_fetcher.py - 株式・投資関連ニュース自動収集エージェント
日経・ロイター等のRSSから当日のホットなニュースを取得する
"""
import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("news_fetcher")

JST = timezone(timedelta(hours=9))

# 株式・投資系RSSフィード（無料・公開）
RSS_FEEDS = [
    {
        "name": "ロイター マーケット",
        "url": "https://feeds.reuters.com/reuters/JPBusinessNews",
        "category": "market",
    },
    {
        "name": "Yahoo!ファイナンス 株式ニュース",
        "url": "https://news.yahoo.co.jp/rss/topics/market.xml",
        "category": "japan_stocks",
    },
    {
        "name": "株探（かぶたん）ニュース",
        "url": "https://kabutan.jp/rss/news.rss",
        "category": "japan_stocks",
    },
    {
        "name": "Investing.com 日本株",
        "url": "https://jp.investing.com/rss/news_25.rss",
        "category": "market",
    },
]


def fetch_rss(url: str, timeout: int = 10) -> list[dict]:
    """RSSフィードを取得してニュースリストを返す"""
    items = []
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NoteAgent/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read()

        root = ET.fromstring(content)
        # RSS 2.0 形式
        for item in root.findall(".//item")[:10]:
            title = item.findtext("title", "").strip()
            desc = item.findtext("description", "").strip()
            pub_date = item.findtext("pubDate", "")
            link = item.findtext("link", "")

            if title:
                items.append({
                    "title": title,
                    "description": desc[:200] if desc else "",
                    "pub_date": pub_date,
                    "link": link,
                })
    except Exception as e:
        logger.warning(f"RSS取得失敗 ({url}): {e}")

    return items


def get_today_news(max_items: int = 8) -> list[dict]:
    """
    各RSSから本日のニュースを収集してまとめて返す
    Returns:
        [{"source": "...", "title": "...", "description": "..."}, ...]
    """
    all_news = []

    for feed in RSS_FEEDS:
        logger.info(f"ニュース取得: {feed['name']}")
        items = fetch_rss(feed["url"])
        for item in items[:3]:  # 各フィードから最大3件
            all_news.append({
                "source": feed["name"],
                "category": feed["category"],
                "title": item["title"],
                "description": item["description"],
            })

    if not all_news:
        logger.warning("RSSからニュースを取得できませんでした。モックニュースを使用します")
        all_news = _mock_news()

    # 重複タイトルを除去して最大件数に絞る
    seen = set()
    unique_news = []
    for n in all_news:
        if n["title"] not in seen:
            seen.add(n["title"])
            unique_news.append(n)
        if len(unique_news) >= max_items:
            break

    logger.info(f"取得ニュース: {len(unique_news)}件")
    return unique_news


def format_news_for_prompt(news_list: list[dict]) -> str:
    """ニュースリストをプロンプト挿入用テキストにフォーマット"""
    if not news_list:
        return "（本日のニュース取得なし）"

    lines = [f"【本日 {datetime.now(JST).strftime('%Y年%m月%d日')} の株式・投資ニュース】"]
    for i, n in enumerate(news_list, 1):
        lines.append(f"{i}. [{n['source']}] {n['title']}")
        if n.get("description"):
            lines.append(f"   → {n['description'][:100]}")

    return "\n".join(lines)


def _mock_news() -> list[dict]:
    """RSS取得失敗時のフォールバック"""
    return [
        {"source": "市場概況", "category": "market",
         "title": "日経平均、米国株安を受けて小幅続落", "description": "前日比100円安で取引終了"},
        {"source": "市場概況", "category": "market",
         "title": "東証プライム売買代金、3兆円超え", "description": "個人投資家の買いが活発"},
        {"source": "企業ニュース", "category": "japan_stocks",
         "title": "高配当株への資金流入続く", "description": "NISA枠を活用した長期投資需要が拡大"},
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    news = get_today_news()
    print(format_news_for_prompt(news))
