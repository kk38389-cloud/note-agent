"""
writer.py - note記事生成エージェント
シリーズ: AIで副業自動化に挑戦する90日間実録
"""
import json
import random
import logging
import urllib.request
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    ANTHROPIC_API_KEY, THEMES, ARTICLE_TOPICS,
    MIN_ARTICLE_LENGTH, MAX_ARTICLE_LENGTH,
    SERIES_TITLE, SERIES_CONCEPT
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("note_writer")


# ─────────────────────────────────────────
# タイトル公式（テーマ別）
# ─────────────────────────────────────────
TITLE_FORMULAS = {
    "build_record": [
        "【構築記録】{topic}｜失敗{count}回を経てたどり着いた方法",
        "正直に言います。{topic}でこんなにハマるとは思っていなかった",
        "【全手順公開】{topic}を完成させるまでの{count}週間",
        "{topic}でやらかした{count}つのミスと、その解決策",
        "【実録】{topic}にかかった時間とお金を全部さらします",
    ],
    "progress_report": [
        "【第{episode}回】{topic}｜今週の実数値を全公開します",
        "AI副業{weeks}週目の正直な報告：{topic}",
        "{topic}の現実｜スキ{likes}件・フォロワー{followers}人・収益{revenue}円",
        "【月次報告】{topic}の数字を隠さず公開する理由",
        "AI自動投稿を{weeks}週続けた結果、わかったこと",
    ],
    "ai_tips": [
        "【保存版】{topic}｜{count}回試して見えてきた法則",
        "Claudeに{topic}させるプロンプトを{count}ヶ月かけて改善した話",
        "正直、{topic}はこうすればよかった｜{count}つの改善点",
        "【比較検証】{topic}でAIと人間、どちらが優れているか",
        "{topic}で月{amount}円節約できた具体的な方法",
    ],
    "failure_report": [
        "【反省】{topic}で完全にやらかした話を正直に書きます",
        "AI副業{weeks}週目の失敗報告：{topic}",
        "恥ずかしいけど書きます。{topic}でした失敗の全貌",
        "【教訓】{topic}から学んだ{count}つのこと",
        "{topic}が原因で読者を失いかけた話",
    ],
}

TITLE_VARS = {
    "count": ["3", "5", "7", "2", "4"],
    "weeks": ["2", "3", "4", "6", "8"],
    "amount": ["3,000", "5,000", "1万", "2万"],
    "likes": ["12", "23", "47", "8", "31"],
    "followers": ["18", "34", "52", "7", "89"],
    "revenue": ["0", "500", "1,200", "3,400"],
}


# ─────────────────────────────────────────
# 記事スタイル（4パターン）
# ─────────────────────────────────────────
SERIES_STYLES = {
    "build_record": {
        "name": "構築記録型",
        "opening": "今回は{topic}について、実際にやってみてわかったことを正直に書きます。",
        "structure": [
            "【なぜこれを作ろうと思ったか】きっかけと動機",
            "【最初に試みたこと】最初のアプローチとその結果",
            "【ハマったポイント】エラー・失敗・想定外のこと",
            "【解決策と最終的な形】どう乗り越えたか・現在の状態",
            "【かかったコスト（時間・お金）】正直な数字",
            "【次にやること・次回予告】",
        ],
        "ending_hook": "次回は、このシステムを実際に動かしてみた結果と、新たに発生した問題を報告します。",
    },
    "progress_report": {
        "name": "進捗報告型",
        "opening": "AI副業自動化チャレンジ、今週も正直に報告します。",
        "structure": [
            "【今週の数字（全公開）】スキ数・フォロワー・収益の実数値",
            "【先週との比較】増えたか減ったか、その理由の考察",
            "【今週やったこと】システム改善・記事調整の内容",
            "【うまくいったこと・いかなかったこと】正直な評価",
            "【来週の目標と戦略】",
            "【次回予告】",
        ],
        "ending_hook": "来週は、今週試した改善策の効果を数字で報告します。結果がよければ詳しく解説します。",
    },
    "ai_tips": {
        "name": "AI活用ノウハウ型",
        "opening": "AIを使って副業記事を量産する中で、{topic}についての発見がありました。",
        "structure": [
            "【最初はこうしていた】改善前のやり方と問題点",
            "【気づいたきっかけ】なぜ変えようと思ったか",
            "【実際に試した方法】具体的な手順とプロンプト例",
            "【比較結果】改善前後の違いを具体的に",
            "【注意点・限界】万能ではないところも正直に",
            "【まとめと次回予告】",
        ],
        "ending_hook": "次回は、このノウハウをさらに発展させた応用編を公開します。",
    },
    "failure_report": {
        "name": "失敗報告型",
        "opening": "今週、やらかしました。{topic}の話を正直に書きます。",
        "structure": [
            "【何が起きたか】失敗の全貌を隠さず説明",
            "【なぜそうなったか】原因の分析（言い訳なし）",
            "【読者・システムへの影響】実害はあったか",
            "【すぐやった対処】緊急対応の内容",
            "【同じ失敗をしないための対策】具体的な改善点",
            "【次回予告】懲りずに続けます宣言",
        ],
        "ending_hook": "懲りずに続けます。次回は失敗から生まれた改善策の効果を報告します。",
    },
}


# ─────────────────────────────────────────
# エピソード番号を取得
# ─────────────────────────────────────────
def get_episode_number(posts_file: str) -> int:
    """投稿履歴から次のエピソード番号を計算"""
    if not os.path.exists(posts_file):
        return 1
    try:
        with open(posts_file, "r", encoding="utf-8") as f:
            posts = json.load(f)
        return len(posts) + 1
    except Exception:
        return 1


def select_topic(used_topics: list) -> dict:
    """テーマとトピックをランダムに選択（使用済みを避ける）"""
    total_weight = sum(t["weight"] for t in THEMES)
    r = random.uniform(0, total_weight)
    cumulative = 0
    selected_theme = THEMES[0]
    for theme in THEMES:
        cumulative += theme["weight"]
        if r <= cumulative:
            selected_theme = theme
            break

    theme_id = selected_theme["id"]
    theme_topics = [t for t in ARTICLE_TOPICS if t[0] == theme_id]
    unused = [t for t in theme_topics if t[1] not in used_topics]
    if not unused:
        unused = theme_topics

    topic_tuple = random.choice(unused)
    style = SERIES_STYLES[theme_id]

    return {
        "theme_id": theme_id,
        "theme_name": selected_theme["name"],
        "topic": topic_tuple[1],
        "hashtags": selected_theme["hashtags"],
        "style": style,
    }


def generate_title(topic_info: dict, episode: int) -> str:
    """テーマに合ったタイトルを生成"""
    theme_id = topic_info["theme_id"]
    formulas = TITLE_FORMULAS.get(theme_id, TITLE_FORMULAS["build_record"])
    formula = random.choice(formulas)
    topic = topic_info["topic"]

    title = formula.format(
        topic=topic,
        episode=episode,
        count=random.choice(TITLE_VARS["count"]),
        weeks=random.choice(TITLE_VARS["weeks"]),
        amount=random.choice(TITLE_VARS["amount"]),
        likes=random.choice(TITLE_VARS["likes"]),
        followers=random.choice(TITLE_VARS["followers"]),
        revenue=random.choice(TITLE_VARS["revenue"]),
    )
    return title


def call_claude(title: str, topic: str, theme_name: str, style: dict,
                episode: int, news_context: str = "") -> str:
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY未設定。モック記事を生成します")
        return generate_mock_article(title, topic, style, episode)

    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    today_str = now_jst.strftime("%Y年%m月%d日")
    this_year = now_jst.year
    last_year = this_year - 1

    news_section = ""
    if news_context:
        news_section = f"【関連ニュース（自然に織り込む）】\n{news_context}\n"

    structure_text = "\n".join([f"  {s}" for s in style["structure"]])

    prompt = f"""
あなたは会社員をしながらAI副業自動化に挑戦中のブロガーです。
シリーズ「{SERIES_TITLE}」を毎週noteで更新中。{SERIES_CONCEPT}

今日の日付: {today_str}（今年={this_year}年、去年={last_year}年）

第{episode}回 / テーマ:{theme_name} / トピック:{topic}
タイトル:「{title}」
書き出し（必ずこの一文から始める）:「{style['opening'].format(topic=topic)}」
{news_section}

━━━━━━━━━━━━━━━━━━━━━━━━
【記事構成：無料パート＋有料パートの2部構成で書く】
━━━━━━━━━━━━━━━━━━━━━━━━

■ 無料パート（400〜600字）
目的：「この続きを300円払ってでも読みたい」と思わせる

書き方のルール：
1. 冒頭は「痛い失敗談」か「意外な数字」から始める
   例:「深夜2時、Claudeが生成した記事を見て頭を抱えました。」
   例:「3週間で投稿した9本の記事。スキの合計は…12件でした。」

2. 問題・葛藤を読者と共有する（あるある感）
   読者が「自分もそう思ってた」と感じる瞬間を作る

3. 「解決の糸口を見つけた」ことだけをほのめかす
   具体的な方法は絶対に書かない。「あること」「ある方法」と表現する

4. 有料パートの予告を具体的に書く（これが購入動機になる）
   ❌ 悪い例：「続きは有料です」
   ✅ 良い例：
   「この記事の有料パートでは以下を公開します：
   ・私が実際に使っているClaudeへのプロンプト（全文コピペOK）
   ・記事品質が上がった具体的な変更点3つ
   ・今月のAPI費用の実額と費用対効果の計算式」

   → 「これだけ具体的なら300円出す価値ある」と思わせる

---PAID_BORDER---

■ 有料パート（1200〜2000字）
目的：「買ってよかった」と思わせる。期待を超える内容にする

構成（この順で書く）：
{structure_text}

書き方のルール：
1. 具体的な数字を必ず入れる
   - 時間：「作業12時間」「深夜2時まで」
   - コスト：「Claude API月890円」「Pro契約月3,000円」
   - 結果：「スキ+23件」「フォロワー+7人」「収益500円」

2. 手順・コマンド・プロンプトを実際に書く
   読者がコピーして使えるレベルまで具体化する
   コードブロックやプロンプト例を積極的に使う

3. 「うまくいかなかったこと」も正直に書く
   失敗の告白が信頼につながる。美化しない

4. 最後は必ずこの形式で締める：
   ---
   **次回予告**
   {style['ending_hook']}

   毎週{this_year}年更新中。フォローしておくと通知が届きます。
   「スキ」を押してもらえると次を書くモチベになります😊

   ※本記事はAI副業に挑戦する個人の記録です。収益を保証するものではありません。

━━━━━━━━━━━━━━━━━━━━━━━━
【出力形式】
無料パートの本文を書いてから、
「---PAID_BORDER---」という区切り文字を1行で入れ、
そのあと有料パートの本文を書く。
タイトルや説明文は不要。本文のみ出力。
━━━━━━━━━━━━━━━━━━━━━━━━
"""

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 7000,
        "system": (
            f"あなたは会社員をしながらAI副業自動化に挑戦中のブロガーです。"
            f"シリーズ「{SERIES_TITLE}」を毎週noteで更新しています。"
            "特徴:①失敗も数字も正直に書く ②手順・コスト・プロンプトを具体的に公開する "
            "③過度な成功アピールをしない ④読者と同じ目線 "
            "⑤無料パートで「続きを買いたい」と思わせ、有料パートで期待を超える。"
            "---PAID_BORDER---という区切り文字で無料/有料を分けて出力してください。"
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


def generate_mock_article(title: str, topic: str, style: dict, episode: int) -> str:
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    this_year = now_jst.year

    return f"""{style['opening'].format(topic=topic)}

第{episode}回です。今週もリアルな進捗を報告します。

深夜1時、またPCの前に座っています。
{topic}に取り組んで3週間。正直、思っていたより全然うまくいっていません。

今週の数字を先に言います。スキ数：+3件（合計19件）、フォロワー：+2人（合計23人）、収益：0円。

ゼロです。

でも今週、ひとつだけ「これは使える」という発見がありました。

この記事の有料パートでは以下を公開します：
・私が実際に使っているClaudeへのプロンプト（コピペOK）
・記事生成コストを月890円に抑えた具体的な設定
・スキ数が増えた記事と増えなかった記事の明確な違い3つ

---PAID_BORDER---

## 今週やったこと・学んだこと

{topic}について、実際に手を動かして気づいたことを書きます。

最初はうまくいきませんでした。
エラーが出て、調べて、また別のエラーが出て。
そのループを合計12時間繰り返しました。

### 実際に使っているプロンプト（全文）

```
あなたはAI副業に挑戦中の会社員ブロガーです。
以下のトピックについて、失敗談と学びを正直に書いてください。
数字は必ず具体的に（時間・コスト・結果）。
```

このプロンプトに変えてから、記事の「読んだ感」が変わりました。

### コストの実態

- Claude API: 月890円（記事12本生成）
- GitHub Actions: 無料枠で収まっています
- 合計: 月890円

### スキが増えた記事の共通点

調べてみると明確な傾向がありました。

1. 冒頭に具体的な数字がある
2. 失敗談から始まっている
3. 見出しに「正直」「実録」が入っている

この3つが揃った記事のスキ率が、そうでない記事の2.3倍でした。

## 失敗したこと

AIに丸投げしすぎた記事を1本出してしまいました。
内容が薄く、読み返すと「これはダメだ」とわかるレベル。
今後は生成後に必ず自分でチェックします。

---

**次回予告**
{style['ending_hook']}

毎週{this_year}年更新中。フォローしておくと通知が届きます。
「スキ」を押してもらえると次を書くモチベになります😊

※本記事はAI副業に挑戦する個人の記録です。収益を保証するものではありません。
"""


def run(news_context: str = "") -> dict | None:
    logger.info("=== note記事生成 開始 ===")

    posts_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "posts.json"
    )

    # 使用済みトピックと現在のエピソード番号を取得
    posts = []
    if os.path.exists(posts_file):
        with open(posts_file, "r", encoding="utf-8") as f:
            posts = json.load(f)
    used_topics = [p.get("topic", "") for p in posts]
    episode = get_episode_number(posts_file)

    topic_info = select_topic(used_topics)
    title = generate_title(topic_info, episode)

    logger.info(f"第{episode}回 / テーマ: {topic_info['theme_name']}")
    logger.info(f"スタイル: {topic_info['style']['name']}")
    logger.info(f"タイトル: {title}")

    try:
        body = call_claude(
            title,
            topic_info["topic"],
            topic_info["theme_name"],
            topic_info["style"],
            episode,
            news_context,
        )
        logger.info(f"記事生成完了: {len(body)}文字")
    except Exception as e:
        logger.error(f"記事生成エラー: {e}")
        return None

    if len(body) < MIN_ARTICLE_LENGTH:
        logger.warning(f"文字数不足: {len(body)}字（最低{MIN_ARTICLE_LENGTH}字）")

    enhanced_hashtags = topic_info["hashtags"] + ["副業記録", "AI自動化", "note運用"]

    # 無料/有料パートに分割
    PAID_BORDER = "---PAID_BORDER---"
    if PAID_BORDER in body:
        parts = body.split(PAID_BORDER, 1)
        body_free = parts[0].strip()
        body_paid = parts[1].strip()
    else:
        # 分割記号がない場合は全文を無料扱い
        logger.warning("有料ボーダーが見つかりません。全文を無料として扱います")
        body_free = body
        body_paid = ""

    # 投稿用の本文（無料＋区切り＋有料を結合、poster.pyが分割して処理）
    full_body = body

    article = {
        "title": title,
        "body": full_body,        # poster.pyが---PAID_BORDER---で分割
        "body_free": body_free,   # 無料パート（参照用）
        "body_paid": body_paid,   # 有料パート（参照用）
        "has_paid_content": bool(body_paid),
        "theme_id": topic_info["theme_id"],
        "theme_name": topic_info["theme_name"],
        "topic": topic_info["topic"],
        "style": topic_info["style"]["name"],
        "series_no": f"第{episode}回",
        "episode": episode,
        "hashtags": list(dict.fromkeys(enhanced_hashtags)),
        "char_count": len(full_body),
        "char_count_free": len(body_free),
        "char_count_paid": len(body_paid),
    }

    logger.info(f"無料パート: {len(body_free)}字 / 有料パート: {len(body_paid)}字")

    logger.info("=== note記事生成 完了 ===")
    return article


if __name__ == "__main__":
    article = run()
    if article:
        print(f"\n{article['series_no']} タイトル: {article['title']}")
        print(f"スタイル: {article['style']}")
        print(f"文字数: {article['char_count']}")
        print("\n--- 本文（先頭500字）---")
        print(article["body"][:500])
        print("\n--- 本文（末尾300字）---")
        print(article["body"][-300:])
