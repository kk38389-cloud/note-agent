"""
writer.py - note記事生成エージェント
Claude APIを使って1500〜3000字の株式・投資記事を生成する
"""
import json
import random
import logging
import urllib.request
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    ANTHROPIC_API_KEY, THEMES, ARTICLE_TOPICS,
    MIN_ARTICLE_LENGTH, MAX_ARTICLE_LENGTH
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("note_writer")


def select_topic(used_topics: list) -> dict:
    """重みに基づいてテーマとトピックを選択"""
    # 重み付きテーマ選択
    total_weight = sum(t["weight"] for t in THEMES)
    r = random.uniform(0, total_weight)
    cumulative = 0
    selected_theme = THEMES[0]
    for theme in THEMES:
        cumulative += theme["weight"]
        if r <= cumulative:
            selected_theme = theme
            break

    # 未使用トピックを優先選択
    theme_topics = [t for t in ARTICLE_TOPICS if t[0] == selected_theme["id"]]
    unused = [t for t in theme_topics if t[1] not in used_topics]

    if not unused:
        # 全部使ったらリセット
        unused = theme_topics

    topic_tuple = random.choice(unused)
    return {
        "theme_id": selected_theme["id"],
        "theme_name": selected_theme["name"],
        "topic": topic_tuple[1],
        "hashtags": selected_theme["hashtags"],
        "article_types": selected_theme["article_types"],
    }


def generate_title(topic_info: dict) -> str:
    """記事タイトルを生成"""
    template = random.choice(topic_info["article_types"])
    return template.format(topic=topic_info["topic"])


def call_claude(title: str, topic: str, theme: str) -> str:
    """Claude APIで記事本文を生成"""
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY未設定。モック記事を生成します")
        return generate_mock_article(title, topic)

    prompt = f"""
あなたは株式・投資分野の専門ライターです。以下のテーマでnote記事を書いてください。

タイトル: {title}
テーマ: {theme}
トピック: {topic}

【記事の要件】
- 文字数: {MIN_ARTICLE_LENGTH}〜{MAX_ARTICLE_LENGTH}字
- 対象読者: 投資初心者〜中級者
- 見出し（##）を3〜5個使って構成する
- 具体的な数字・例を積極的に使う
- 「投資は自己責任です」という注意書きを最後に入れる
- 読みやすい平易な言葉で書く
- 箇条書きを適切に活用する

【構成例】
## はじめに
## {topic}とは
## 具体的な方法・ポイント（2〜3個の見出し）
## まとめ

記事本文のみを出力してください（タイトルは不要）。
"""

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 4000,
        "system": (
            "あなたはnote（ブログプラットフォーム）向け株式・投資記事の専門ライターです。"
            "正確で分かりやすく、読者が行動に移せる実践的な記事を書いてください。"
            "特定銘柄を強く推奨する表現は避け、あくまで情報提供として書いてください。"
        ),
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=60) as res:
        data = json.loads(res.read().decode())

    return data["content"][0]["text"]


def generate_mock_article(title: str, topic: str) -> str:
    """APIキー未設定時のモック記事"""
    return f"""## はじめに

投資を始めたばかりの方、あるいはもっと効率的に資産を増やしたいとお考えの方に向けて、今回は「{topic}」について詳しく解説します。

## {topic}の基本を理解する

まず基本から始めましょう。投資の世界では、正しい知識を持つことが成功への第一歩です。

- **ポイント1**: 焦らず長期的な視点を持つ
- **ポイント2**: 分散投資でリスクを管理する
- **ポイント3**: 定期的に見直しを行う

## 実践的な活用方法

理論だけでなく、実際に行動に移すことが大切です。以下のステップで始めてみましょう。

1. まず少額から始める
2. 定期的に積み立てる習慣をつける
3. 市場の動きに一喜一憂しない

## よくある失敗と対策

初心者が陥りやすい失敗を事前に知っておくことで、リスクを大幅に減らすことができます。

最も多い失敗は「感情で売買する」ことです。株価が下がると不安になり、上がると欲が出る。この心理を理解し、ルールを決めて機械的に投資することが重要です。

## まとめ

{topic}は、正しい知識と継続的な実践によって成果が出る分野です。今日から一歩ずつ始めてみましょう。

---
※本記事は情報提供を目的としており、投資助言ではありません。投資は自己責任で行ってください。
"""


def run() -> dict | None:
    """記事を1本生成して返す"""
    logger.info("=== note記事生成 開始 ===")

    # 使用済みトピックを読み込む
    posts_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "posts.json"
    )
    posts = []
    if os.path.exists(posts_file):
        with open(posts_file, "r", encoding="utf-8") as f:
            posts = json.load(f)
    used_topics = [p.get("topic", "") for p in posts]

    # トピック選択
    topic_info = select_topic(used_topics)
    title = generate_title(topic_info)
    logger.info(f"テーマ: {topic_info['theme_name']} / タイトル: {title}")

    # 記事生成
    try:
        body = call_claude(title, topic_info["topic"], topic_info["theme_name"])
        logger.info(f"記事生成完了: {len(body)}文字")
    except Exception as e:
        logger.error(f"記事生成エラー: {e}")
        return None

    # 文字数チェック
    if len(body) < MIN_ARTICLE_LENGTH:
        logger.warning(f"文字数不足: {len(body)}字（最低{MIN_ARTICLE_LENGTH}字）")

    article = {
        "title": title,
        "body": body,
        "theme_id": topic_info["theme_id"],
        "theme_name": topic_info["theme_name"],
        "topic": topic_info["topic"],
        "hashtags": topic_info["hashtags"],
        "char_count": len(body),
    }

    logger.info("=== note記事生成 完了 ===")
    return article


if __name__ == "__main__":
    article = run()
    if article:
        print(f"タイトル: {article['title']}")
        print(f"文字数: {article['char_count']}")
        print("--- 本文（先頭200字）---")
        print(article["body"][:200])
