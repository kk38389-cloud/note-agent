"""
note自動投稿エージェント - 設定ファイル
シリーズ: AIで副業自動化に挑戦する90日間実録
"""
import os

# === note アカウント設定 ===
NOTE_EMAIL = os.getenv("NOTE_EMAIL", "")
NOTE_PASSWORD = os.getenv("NOTE_PASSWORD", "")

# === Claude API ===
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# === 投稿設定 ===
MIN_ARTICLE_LENGTH = 1500
MAX_ARTICLE_LENGTH = 3000
POST_STATUS = "public"

# === シリーズ設定 ===
SERIES_TITLE = "AIで副業自動化に挑戦する90日間実録"
SERIES_CONCEPT = "プログラミング初心者がAIだけで副業システムを構築・収益化を目指すリアルな記録"

# === テーマ設定（4タイプローテーション） ===
THEMES = [
    {
        "id": "build_record",
        "name": "AI自動化・構築記録",
        "weight": 30,
        "hashtags": ["AI副業", "Claude", "自動化", "GitHub Actions", "副業"],
        "description": "システム構築の過程・エラー・解決を正直に記録する"
    },
    {
        "id": "progress_report",
        "name": "収益化・進捗報告",
        "weight": 30,
        "hashtags": ["副業収益", "note収益化", "AI副業", "進捗報告", "副業"],
        "description": "フォロワー数・スキ数・収益の実数値を公開する"
    },
    {
        "id": "ai_tips",
        "name": "AI活用ノウハウ",
        "weight": 25,
        "hashtags": ["ChatGPT", "Claude", "AI活用", "プロンプト", "自動化"],
        "description": "実際に使ってわかったAIツールの活用術・コツを共有する"
    },
    {
        "id": "failure_report",
        "name": "失敗・反省記録",
        "weight": 15,
        "hashtags": ["AI副業", "失敗談", "副業", "自動化", "note運用"],
        "description": "やらかしたこと・うまくいかなかったことを正直に報告する"
    },
]

# === 記事トピック一覧 ===
ARTICLE_TOPICS = [
    # AI自動化・構築記録
    ("build_record", "AIでnote自動投稿システムを作った全手順"),
    ("build_record", "GitHub Actionsで自動投稿を設定するときにハマったこと"),
    ("build_record", "Claudeに記事を書かせるプロンプトの試行錯誤"),
    ("build_record", "サムネイル自動生成の仕組みを作るまでの道のり"),
    ("build_record", "AI副業システムにかかった費用と時間の全記録"),
    ("build_record", "note自動投稿のクッキー認証を突破した方法"),
    # 収益化・進捗報告
    ("progress_report", "AI副業スタートから1ヶ月の正直な数字報告"),
    ("progress_report", "noteのフォロワーがゼロから増えるまでにやったこと"),
    ("progress_report", "AI自動投稿を続けて気づいた「伸びる記事」の条件"),
    ("progress_report", "月次報告：スキ数・フォロワー・収益の実数を全公開"),
    ("progress_report", "有料記事を初めて出した結果と反省"),
    # AI活用ノウハウ
    ("ai_tips", "Claudeへの指示の書き方で記事品質が3倍変わった"),
    ("ai_tips", "AIが書いた記事をバレずに自然にする編集術"),
    ("ai_tips", "プロンプトエンジニアリングを独学で身につけた方法"),
    ("ai_tips", "ChatGPTとClaudeを使い分けるべき場面の違い"),
    ("ai_tips", "AI記事生成のコストを月1000円以下に抑える方法"),
    # 失敗・反省記録
    ("failure_report", "自動投稿でクオリティの低い記事を出してしまった話"),
    ("failure_report", "AIに任せすぎて読者に怒られた経験"),
    ("failure_report", "3回連続でGitHub Actionsが失敗した原因と対策"),
    ("failure_report", "収益化を焦って間違えた価格設定の失敗談"),
]

# === パス設定 ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
