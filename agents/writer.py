"""
writer.py - note記事生成エージェント（中級者実践シリーズ版）
時事ニュースを織り交ぜた、固定ファンがつく実践的な記事を生成する
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

# 中級者向け実践シリーズ：記事スタイル定義
SERIES_STYLES = [
    {
        "name": "売買判断レポート",
        "title_template": "【実録】{topic}で実際にやった売買判断と結果",
        "structure": "検討背景 → 判断根拠（指標・チャート） → 実際の行動 → 結果と反省",
        "voice": "自分の経験を正直に語る一人称スタイル。失敗も包み隠さず書く",
    },
    {
        "name": "銘柄分析レポート",
        "title_template": "{topic}を徹底分析｜決算・指標・将来性を中級者目線で評価",
        "structure": "企業概要 → 直近決算のポイント → バリュエーション指標 → 投資判断",
        "voice": "客観的なデータに基づき、自分の見解をはっきり述べる",
    },
    {
        "name": "時事×投資考察",
        "title_template": "【今週の相場】{topic}が株価に与える影響を考察する",
        "structure": "今週の出来事 → 相場への影響 → 個人投資家がとるべき行動 → 注目銘柄",
        "voice": "ニュースと投資を繋げて、読者が次の行動を取れるよう具体的に書く",
    },
    {
        "name": "投資メンタル日記",
        "title_template": "{topic}で心が折れそうになった話と、それでも続ける理由",
        "structure": "きっかけ → 心理描写（共感を呼ぶ） → 乗り越えた方法 → 学んだこと",
        "voice": "弱さを見せることで読者と繋がる。完璧な投資家ではなく同じ人間として語る",
    },
    {
        "name": "スクリーニング公開",
        "title_template": "私が{topic}でスクリーニングした銘柄リストと選定理由を全公開",
        "structure": "スクリーニング条件 → 選ばれた銘柄の特徴 → 各銘柄の注目ポイント → 免責事項",
        "voice": "具体的な数字と条件を公開することで希少価値を出す",
    },
]


def select_topic(used_topics: list) -> dict:
    """重みに基づいてテーマとトピックを選択"""
    total_weight = sum(t["weight"] for t in THEMES)
    r = random.uniform(0, total_weight)
    cumulative = 0
    selected_theme = THEMES[0]
    for theme in THEMES:
        cumulative += theme["weight"]
        if r <= cumulative:
            selected_theme = theme
            break

    theme_topics = [t for t in ARTICLE_TOPICS if t[0] == selected_theme["id"]]
    unused = [t for t in theme_topics if t[1] not in used_topics]
    if not unused:
        unused = theme_topics

    topic_tuple = random.choice(unused)
    style = random.choice(SERIES_STYLES)

    return {
        "theme_id": selected_theme["id"],
        "theme_name": selected_theme["name"],
        "topic": topic_tuple[1],
        "hashtags": selected_theme["hashtags"],
        "style": style,
    }


def generate_title(topic_info: dict) -> str:
    """シリーズスタイルに基づいてタイトルを生成"""
    return topic_info["style"]["title_template"].format(topic=topic_info["topic"])


def call_claude(title: str, topic: str, theme: str, style: dict, news_context: str = "") -> str:
    """Claude APIで記事本文を生成（ニュース文脈付き）"""
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY未設定。モック記事を生成します")
        return generate_mock_article(title, topic)

    news_section = ""
    if news_context:
        news_section = f"""
【参考：本日の関連ニュース】
{news_context}

↑ 上記のニュースを記事に自然に織り交ぜてください。ニュースの内容を読者への文脈として活用し、今この記事を読む意味を感じさせてください。
"""

    prompt = f"""
あなたは個人投資家として株式投資を実践しながら、その経験をnoteで発信しているライターです。

タイトル: 「{title}」
テーマ: {theme}
トピック: {topic}
記事スタイル: {style['name']}
構成: {style['structure']}
文体・トーン: {style['voice']}
{news_section}

【記事の要件】
- 文字数: {MIN_ARTICLE_LENGTH}〜{MAX_ARTICLE_LENGTH}字
- 対象読者: 投資経験1〜3年の中級者。基礎は分かっているが実践で迷っている人
- 見出し（##）を4〜6個使い、論理的に構成する
- 具体的な数字（PER、配当利回り、騰落率など）を必ず含める
- 自分の失敗談や迷いを正直に書く（共感ポイントになる）
- 「〇〇すべき」より「私はこうした」という一人称で書く
- 最後に今後の連載予告を入れて読者をつなぎとめる
- 免責事項を自然な流れで入れる（固い文体にしない）

【禁止事項】
- 根拠のない断言（「必ず上がる」「絶対おすすめ」）
- 初心者向けの説明口調
- ありきたりな「分散投資が大切」だけで終わる薄い内容

記事本文のみを出力してください（タイトルは不要）。
"""

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 5000,
        "system": (
            "あなたは日本株を中心に投資経験5年の個人投資家兼noteライターです。"
            "読者は投資経験1〜3年の中級者。難しい理論より「実際どうだったか」という実体験を重視します。"
            "毎週読みたくなるような、固定ファンがつく記事を書いてください。"
            "特定銘柄に関しては「参考情報であり投資推奨ではない」ことを自然な文章の中で伝えてください。"
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

    with urllib.request.urlopen(req, timeout=90) as res:
        data = json.loads(res.read().decode())

    return data["content"][0]["text"]


def generate_mock_article(title: str, topic: str) -> str:
    return f"""## 今回やろうと思ったきっかけ

正直に言います。先月、{topic}で20万円以上の含み損を抱えました。

「こんなはずじゃなかった」と思いながら、なぜこうなったのかを徹底的に振り返った記録です。

## 私の判断根拠と、どこが間違っていたか

当時の私の分析はこうでした：
- PER：14倍（割安と判断）
- 配当利回り：3.8%（高配当として魅力的）
- 直近決算：増収増益（順調と判断）

しかし見落としていたのは、セクター全体に逆風が吹いていたことです。

## 中級者が陥りやすい「個別最適の罠」

個別銘柄の数字だけ良くても、マクロ環境が悪ければ株価は下がる。これは頭では分かっていました。でも実際には見ていなかった。

今回の失敗で学んだのは、銘柄分析の前に必ず「セクターの風向き」を確認するということです。

## 今後どうするか

含み損のまま保有を続けるか、損切りするか——判断基準を明確にしました。

次回はその判断プロセスを全部公開します。「損切りできない」と悩んでいる方に読んでほしい内容です。

---
※本記事は個人の投資経験の記録であり、投資助言ではありません。投資はご自身の判断と責任で行ってください。
"""


def run(news_context: str = "") -> dict | None:
    """記事を1本生成して返す"""
    logger.info("=== note記事生成 開始 ===")

    # 使用済みトピック読み込み
    posts_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "posts.json"
    )
    posts = []
    if os.path.exists(posts_file):
        with open(posts_file, "r", encoding="utf-8") as f:
            posts = json.load(f)
    used_topics = [p.get("topic", "") for p in posts]

    # トピック・スタイル選択
    topic_info = select_topic(used_topics)
    title = generate_title(topic_info)
    logger.info(f"テーマ: {topic_info['theme_name']} / スタイル: {topic_info['style']['name']}")
    logger.info(f"タイトル: {title}")

    # 記事生成（ニュース文脈付き）
    try:
        body = call_claude(
            title, topic_info["topic"], topic_info["theme_name"],
            topic_info["style"], news_context
        )
        logger.info(f"記事生成完了: {len(body)}文字")
    except Exception as e:
        logger.error(f"記事生成エラー: {e}")
        return None

    if len(body) < MIN_ARTICLE_LENGTH:
        logger.warning(f"文字数不足: {len(body)}字（最低{MIN_ARTICLE_LENGTH}字）")

    article = {
        "title": title,
        "body": body,
        "theme_id": topic_info["theme_id"],
        "theme_name": topic_info["theme_name"],
        "topic": topic_info["topic"],
        "style": topic_info["style"]["name"],
        "hashtags": topic_info["hashtags"],
        "char_count": len(body),
    }

    logger.info("=== note記事生成 完了 ===")
    return article


if __name__ == "__main__":
    article = run()
    if article:
        print(f"タイトル: {article['title']}")
        print(f"スタイル: {article['style']}")
        print(f"文字数: {article['char_count']}")
        print("--- 本文（先頭300字）---")
        print(article["body"][:300])
