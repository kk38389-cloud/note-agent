"""
writer.py - note記事生成エージェント（売れる記事公式版）
分析に基づく「固定ファンがつく・続きが気になる」記事を生成する
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


# ─────────────────────────────────────────
# 売れるタイトル公式（分析結果より）
# ─────────────────────────────────────────
TITLE_FORMULAS = [
    # 実録・告白型（生々しさで信頼獲得）
    "【実録】{topic}で{amount}円の損失を出した私が、その後どう立て直したか",
    "正直に言います。{topic}で失敗した本当の理由と、今やっていること",
    "誰も教えてくれなかった{topic}の落とし穴｜{count}年やって気づいたこと",
    # 数字・具体性型（権威性）
    "{topic}を{count}銘柄スクリーニングした結果、残った条件が意外だった",
    "配当金{amount}円達成までの{count}ヶ月間、実際にやったことを全部公開",
    "【保存版】{topic}で負けた投資家{count}人に共通していた{num}つのパターン",
    # 否定・反転型（好奇心を刺激）
    "{topic}は「{count}倍になる株」より「絶対買わない株」を決めるほうが重要だった",
    "証券会社が絶対に教えない{topic}の真実｜私が{count}年かけて学んだこと",
    "「{topic}で失敗する人」と「成功する人」の違いは才能じゃなかった",
    # 時事×投資型（今すぐ読む理由を作る）
    "【今週の相場】{topic}が動いた本当の理由と、個人投資家が今すべきこと",
    "暴落相場で{topic}をどう動かしたか｜私のリアルな判断記録",
]

TITLE_VARS = {
    "amount": ["23万", "47万", "8万", "120万", "30万"],
    "count": ["3", "5", "10", "50", "100", "2", "4"],
    "num": ["3", "5", "7"],
}

# ─────────────────────────────────────────
# 売れる記事構成スタイル（5パターン）
# ─────────────────────────────────────────
SERIES_STYLES = [
    {
        "name": "実録・失敗告白型",
        "opening": "最初に正直に言います。私は{topic}で失敗しています。",
        "structure": [
            "【その失敗の全貌】金額・時期・銘柄名を含む具体的な失敗談",
            "【なぜそうなったのか】心理面・判断ミスの分析",
            "【同じ失敗をしている人の特徴】読者への鏡として",
            "【私が変えたこと】具体的な改善策と根拠",
            "【今の結果】正直に現状報告",
            "【次回予告】続きを読みたくなる引き",
        ],
        "ending_hook": "次回は、この失敗から生まれた「私だけのスクリーニング条件」を全部公開します。",
    },
    {
        "name": "銘柄分析・実践型",
        "opening": "{topic}について、今週じっくり分析してみました。",
        "structure": [
            "【なぜ今この銘柄/テーマに注目したか】時事背景",
            "【決算・財務データの読み解き】PER/PBR/配当利回りの実数値",
            "【チャートと需給の実態】個人投資家目線での解釈",
            "【買い・様子見・見送りの判断と根拠】自分の結論を明言",
            "【リスクシナリオ】悪い場合も正直に書く",
            "【次回予告】続きを読みたくなる引き",
        ],
        "ending_hook": "来週はこの銘柄を実際に買うかどうか、判断の瞬間を記録します。",
    },
    {
        "name": "スクリーニング公開型",
        "opening": "今回は私が実際に使っている{topic}のスクリーニング条件を全部さらします。",
        "structure": [
            "【なぜスクリーニングが必要か】感情投資との決別",
            "【私のスクリーニング条件（全公開）】具体的な数値条件",
            "【今回残った銘柄の傾向】セクター・特徴",
            "【その中で特に気になった1〜2銘柄】詳しく分析",
            "【スクリーニングの限界と補完方法】正直な欠点も書く",
            "【次回予告】続きを読みたくなる引き",
        ],
        "ending_hook": "次回は、スクリーニングをくぐり抜けた銘柄を実際に買った結果を報告します。",
    },
    {
        "name": "投資メンタル・心理型",
        "opening": "投資で一番難しいのは銘柄選びじゃない。自分の心との戦いだと気づきました。",
        "structure": [
            "【今週あった心理的な揺れ】具体的なエピソード",
            "【その時の頭の中】感情の動きを正直に描写",
            "【なぜ感情で動くと負けるのか】行動経済学的な解説",
            "【私が実際に使っているルール】具体的なマイルール",
            "【それでも揺れる時の対処法】読者が明日から使えること",
            "【次回予告】続きを読みたくなる引き",
        ],
        "ending_hook": "次回は、実際に感情に負けて損切りできなかった銘柄の顛末を公開します。",
    },
    {
        "name": "時事×投資考察型",
        "opening": "今週の相場、正直に言うとかなり迷いました。",
        "structure": [
            "【今週起きたこと】ニュースと株価の動きを整理",
            "【一般的な解説との私の見解の違い】独自視点を打ち出す",
            "【個人投資家が本当に気にすべきポイント】プロ目線との差",
            "【私のポートフォリオへの影響と対応】実際の行動",
            "【来週の注目ポイント】読者が使える予測",
            "【次回予告】続きを読みたくなる引き",
        ],
        "ending_hook": "来週は、今週の動きを受けて実際に売買した記録を全部公開します。",
    },
]


def select_topic(used_topics: list) -> dict:
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
    formula = random.choice(TITLE_FORMULAS)
    topic = topic_info["topic"]
    title = formula.format(
        topic=topic,
        amount=random.choice(TITLE_VARS["amount"]),
        count=random.choice(TITLE_VARS["count"]),
        num=random.choice(TITLE_VARS["num"]),
    )
    return title


def call_claude(title: str, topic: str, theme: str, style: dict, news_context: str = "") -> str:
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY未設定。モック記事を生成します")
        return generate_mock_article(title, topic, style)

    news_section = ""
    if news_context:
        news_section = f"""
【本日の関連ニュース（記事に自然に織り込んでください）】
{news_context}
"""

    structure_text = "\n".join([f"  {s}" for s in style["structure"]])

    prompt = f"""
あなたは日本株投資5年目の個人投資家で、毎週noteに投資日記を書いています。
読者3,000人以上の固定ファンがいて、「正直すぎる投資記録」で人気です。

━━━━━━━━━━━━━━━━━━━━━━━━
タイトル: 「{title}」
テーマ: {theme} / {topic}
今回の記事スタイル: {style['name']}
冒頭の書き出し（この一文から始めてください）: 「{style['opening'].format(topic=topic)}」
━━━━━━━━━━━━━━━━━━━━━━━━
{news_section}

【構成（この順番で書いてください）】
{structure_text}

【売れる記事の必須要素】
1. 冒頭3行で読者の「あるある」な痛みを言語化する
   例:「スキが多い記事を見て真似したのに、なぜか自分のポートフォリオは同じ成果が出ない。そんな経験、ありませんか？」

2. 具体的な数字を必ず含める
   - 実際の株価・PER・配当利回り・損益額（架空でもリアルな数字を）
   - 「〇〇倍」「〇〇万円」「〇〇%」などを積極的に使う

3. 著者の「迷い・弱さ」を正直に書く
   - 完璧な投資家像を出さない
   - 「正直、まだ答えは出ていない」「今も迷っている」が共感を生む

4. 見出しに「感情語」を入れる
   - 「やらかした理由」「後悔した瞬間」「やっと気づいた」など

5. 終わり方のルール（最重要）
   - 記事の最後は必ず「次回予告」で終わる
   - テンプレート:
     ---
     **次回予告**
     {style['ending_hook']}

     この続きが気になる方は、フォローしておくと更新通知が届きます。
     「スキ」を押してもらえると、続きを書くモチベになります😊

     ※本記事は個人の投資記録であり、特定銘柄の売買を推奨するものではありません。

【禁止事項】
- 「〇〇が大切です」で終わる教科書的まとめ
- 「投資は長期・分散・積立が基本」だけの薄い結論
- 初心者向け用語説明（読者は中級者）
- 根拠のない断言・過度な推奨表現

【文字数】{MIN_ARTICLE_LENGTH}〜{MAX_ARTICLE_LENGTH}字（多めに書いてください）

記事本文のみ出力してください（タイトル・説明文は不要）。
"""

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 6000,
        "system": (
            "あなたは日本株投資5年目の個人投資家です。"
            "毎週noteに「正直すぎる投資記録」を書いて固定ファン3,000人を持っています。"
            "特徴:①失敗も包み隠さず書く ②具体的な数字を必ず出す ③続きが気になる終わり方をする "
            "④読者と同じ目線で語る（上から目線NG）⑤毎回「次回予告」で終わる。"
            "投資助言にならないよう、あくまで個人の記録として書いてください。"
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


def generate_mock_article(title: str, topic: str, style: dict) -> str:
    return f"""最初に正直に言います。私は{topic}で失敗しています。

先月、含み損が47万円を超えた時、初めてスマホの証券アプリを開くのが怖くなりました。

## その失敗の全貌

時期: 2024年秋〜2025年初頭
対象: {topic}関連3銘柄
損失額: -47万円（評価損）

一番やらかしたのは「下がったら買い増す」を繰り返したことです。
PERが割安に見えたから、という理由だけで。

## なぜそうなったのか

今思えば、単純に「値ごろ感」だけで判断していました。

- セクター全体のトレンドを見ていなかった
- 業績の質（営業利益率の推移）を確認していなかった
- 自分の許容損失額を決めていなかった

この3つが全部欠けていました。

## 同じ失敗をしている人の特徴

読者の方から「私も同じです」というコメントをよくもらうのですが、共通しているのは：

**「下がった = 割安」という思い込み**

株価が下がる理由は必ずあります。その理由が一時的なものか、構造的なものかを見極めずに買うのが最大の罠です。

## 私が変えたこと

今は買う前に必ずチェックリストを使っています。

□ 過去3期の営業利益率は安定しているか
□ セクター全体の方向性はどうか
□ この銘柄だけの下落か、セクター全体の下落か

これだけで、無駄な買い増しは8割減りました。

## 今の結果

正直に言うと、まだ全回復はしていません。
-47万円が今は-12万円です。

ただ、新しいルールで入った銘柄は全て含み益です。

---

**次回予告**
{style['ending_hook']}

この続きが気になる方は、フォローしておくと更新通知が届きます。
「スキ」を押してもらえると、続きを書くモチベになります😊

※本記事は個人の投資記録であり、特定銘柄の売買を推奨するものではありません。
"""


def run(news_context: str = "") -> dict | None:
    logger.info("=== note記事生成 開始 ===")

    posts_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "posts.json"
    )
    posts = []
    if os.path.exists(posts_file):
        with open(posts_file, "r", encoding="utf-8") as f:
            posts = json.load(f)
    used_topics = [p.get("topic", "") for p in posts]

    topic_info = select_topic(used_topics)
    title = generate_title(topic_info)
    logger.info(f"テーマ: {topic_info['theme_name']} / スタイル: {topic_info['style']['name']}")
    logger.info(f"タイトル: {title}")

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

    # ハッシュタグを強化版に更新
    enhanced_hashtags = topic_info["hashtags"] + [
        "投資記録", "資産形成", "個人投資家"
    ]

    article = {
        "title": title,
        "body": body,
        "theme_id": topic_info["theme_id"],
        "theme_name": topic_info["theme_name"],
        "topic": topic_info["topic"],
        "style": topic_info["style"]["name"],
        "hashtags": list(dict.fromkeys(enhanced_hashtags)),  # 重複除去
        "char_count": len(body),
    }

    logger.info("=== note記事生成 完了 ===")
    return article


if __name__ == "__main__":
    article = run()
    if article:
        print(f"\nタイトル: {article['title']}")
        print(f"スタイル: {article['style']}")
        print(f"文字数: {article['char_count']}")
        print("\n--- 本文（先頭400字）---")
        print(article["body"][:400])
        print("\n--- 本文（末尾400字）---")
        print(article["body"][-400:])
