"""
main.py - note自動投稿エージェント エントリーポイント
1. 記事生成（writer）
2. note投稿（poster）
"""
import sys
import logging
from agents.writer import run as write_article
from agents.poster import run as post_article

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("note_main")


def main():
    logger.info("========================================")
    logger.info("  note自動投稿エージェント スタート")
    logger.info("========================================")

    # Step 1: 記事生成
    logger.info("[Step 1/2] 記事生成中...")
    article = write_article()

    if not article:
        logger.error("記事生成に失敗しました。処理を終了します")
        sys.exit(1)

    logger.info(f"記事生成完了: 「{article['title']}」 ({article['char_count']}字)")

    # Step 2: note投稿
    logger.info("[Step 2/2] noteに投稿中...")
    success = post_article(article)

    if success:
        logger.info("✅ note投稿が完了しました")
        logger.info(f"   タイトル: {article['title']}")
        logger.info(f"   テーマ: {article['theme_name']}")
        logger.info(f"   文字数: {article['char_count']}字")
        sys.exit(0)
    else:
        logger.error("❌ note投稿に失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
