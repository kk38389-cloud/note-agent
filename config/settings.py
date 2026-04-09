"""
note自動投稿エージェント - 設定ファイル
"""
import os

# === note アカウント設定 ===
NOTE_EMAIL = os.getenv("NOTE_EMAIL", "")
NOTE_PASSWORD = os.getenv("NOTE_PASSWORD", "")

# === Claude API ===
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# === 投稿設定 ===
MIN_ARTICLE_LENGTH = 1500   # 最低文字数
MAX_ARTICLE_LENGTH = 3000   # 最大文字数
POST_STATUS = "public"      # "public" or "draft"（下書き保存）

# === テーマ設定（株式・投資） ===
THEMES = [
    {
        "id": "japan_stocks",
        "name": "日本株・個別銘柄",
        "weight": 35,
        "hashtags": ["日本株", "個別銘柄", "株式投資", "決算"],
        "article_types": [
            "【初心者向け】{topic}を徹底解説",
            "【保存版】{topic}の完全ガイド",
            "プロが教える{topic}の真実",
        ]
    },
    {
        "id": "market_outlook",
        "name": "市場動向・マクロ分析",
        "weight": 25,
        "hashtags": ["日経平均", "相場分析", "投資戦略", "マクロ経済"],
        "article_types": [
            "【相場分析】{topic}",
            "今知るべき{topic}",
            "投資家なら押さえておきたい{topic}",
        ]
    },
    {
        "id": "nisa_investment",
        "name": "NISA・長期投資",
        "weight": 25,
        "hashtags": ["NISA", "新NISA", "長期投資", "積立投資"],
        "article_types": [
            "新NISAで{topic}をやってみた結果",
            "【完全解説】{topic}",
            "{topic}で失敗しないための全知識",
        ]
    },
    {
        "id": "investment_strategy",
        "name": "投資戦略・メンタル",
        "weight": 15,
        "hashtags": ["投資戦略", "投資メンタル", "ポートフォリオ", "資産運用"],
        "article_types": [
            "投資で失敗する人がやっている{topic}",
            "【実体験】{topic}から学んだこと",
            "{topic}を乗り越えるための投資術",
        ]
    },
]

# === 記事トピック一覧 ===
ARTICLE_TOPICS = [
    # 日本株・個別銘柄
    ("japan_stocks", "高配当株の選び方と注意点"),
    ("japan_stocks", "決算書の読み方入門：3つの財務諸表を理解する"),
    ("japan_stocks", "配当利回り4%以上の優良銘柄の探し方"),
    ("japan_stocks", "増配株投資で資産を増やす方法"),
    ("japan_stocks", "PER・PBR・ROEを使った銘柄スクリーニング"),
    # 市場動向
    ("market_outlook", "円安が日本株に与える影響と対策"),
    ("market_outlook", "日銀政策変更で何が変わるか"),
    ("market_outlook", "景気サイクルに合わせた投資タイミング"),
    ("market_outlook", "米国株下落時の日本株の動き方"),
    # NISA・長期投資
    ("nisa_investment", "新NISAの成長投資枠とつみたて枠の使い分け"),
    ("nisa_investment", "NISAで個別株を選ぶ基準"),
    ("nisa_investment", "インデックス投資と個別株投資を組み合わせる方法"),
    ("nisa_investment", "配当金生活に必要な資産額の計算方法"),
    # 投資戦略
    ("investment_strategy", "損切りができない人の心理と対策"),
    ("investment_strategy", "暴落相場を乗り越えるポートフォリオの作り方"),
    ("investment_strategy", "集中投資と分散投資の正しい使い分け"),
]

# === パス設定 ===
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
