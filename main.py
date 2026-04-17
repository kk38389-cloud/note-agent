"""
main.py - note自動投稿エージェント エントリーポイント
1. ニュース収集（news_fetcher）
2. 記事生成（writer） ← ニュース文脈を反映
3. サムネイル生成（thumbnail）
4. note投稿（poster）
"""
import sys
import logging
import os
from agents.news_fetcher import get_today_news, format_news_for_prompt
from agents.writer import run as write_article
from agents.thumbnail import run as generate_thumbnail
from agents.poster import run as post_article

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("note_main")

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")


def main():
    logger.info("========================================")
    logger.info("  note自動投稿エージェント スタート")
    logger.info("========================================")

    # Step 1: ニュース収集
    logger.info("[Step 1/3] 本日のニュースを収集中...")
    try:
        news_list = get_today_news(max_items=6)
        news_context = format_news_for_prompt(news_list)
        logger.info(f"ニュース収集完了: {len(news_list)}件")
    except Exception as e:
        logger.warning(f"ニュース収集に失敗しました（スキップ）: {e}")
        news_context = ""

    # Step 2: 記事生成（ニュース文脈を注入）
    logger.info("[Step 2/3] 記事生成中...")
    article = write_article(news_context=news_context)

    if not article:
        logger.error("記事生成に失敗しました。処理を終了します")
        sys.exit(1)

    logger.info(f"記事生成完了: 「{article['title']}」 ({article['char_count']}字) [{article.get('style', '')}]")

    # Step 3: サムネイル生成
    logger.info("[Step 3/4] サムネイル生成中...")
    try:
        thumbnail_path = generate_thumbnail(article)
        if thumbnail_path:
            logger.info(f"サムネイル生成完了: {thumbnail_path}")
            article["thumbnail_path"] = thumbnail_path
        else:
            logger.warning("サムネイル生成に失敗しました（投稿は続行）")
    except Exception as e:
        logger.warning(f"サムネイル生成エラー（投稿は続行）: {e}")

    # Step 4: note投稿（サムネイル付き）
    logger.info("[Step 4/4] noteに投稿中...")
    thumbnail_path = article.get("thumbnail_path", "")
    success = post_article(article, thumbnail_path=thumbnail_path)

    if success:
        logger.info("✅ note投稿が完了しました")
        logger.info(f"   タイトル : {article['title']}")
        logger.info(f"   テーマ   : {article['theme_name']}")
        logger.info(f"   スタイル : {article.get('style', '-')}")
        logger.info(f"   文字数   : {article['char_count']}字")
        if article.get("thumbnail_path"):
            logger.info(f"   サムネイル: {article['thumbnail_path']}")
        sys.exit(0)
    else:
        logger.error("❌ note投稿に失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
