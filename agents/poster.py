"""
poster.py - note自動投稿エージェント（Playwright使用）
生成した記事をnote.comにブラウザ自動操作で投稿する
"""
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import NOTE_EMAIL, NOTE_PASSWORD, DATA_DIR, LOG_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("note_poster")

NOTE_LOGIN_URL = "https://note.com/login"
NOTE_NEW_POST_URL = "https://note.com/notes/new"


def save_post_history(article: dict, note_url: str = ""):
    """投稿履歴をJSONに保存"""
    posts_file = os.path.join(DATA_DIR, "posts.json")
    posts = []
    if os.path.exists(posts_file):
        with open(posts_file, "r", encoding="utf-8") as f:
            posts = json.load(f)

    posts.append({
        "posted_at": datetime.now().isoformat(),
        "title": article["title"],
        "topic": article["topic"],
        "theme_id": article["theme_id"],
        "theme_name": article["theme_name"],
        "char_count": article["char_count"],
        "note_url": note_url,
        "hashtags": article["hashtags"],
    })

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(posts_file, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    logger.info(f"投稿履歴を保存: {posts_file}")


def post_to_note(article: dict) -> bool:
    """Playwrightでnoteに記事を投稿"""
    if not NOTE_EMAIL or not NOTE_PASSWORD:
        logger.error("NOTE_EMAIL または NOTE_PASSWORD が未設定です")
        return False

    title = article["title"]
    body = article["body"]
    hashtags = article.get("hashtags", [])

    # ハッシュタグを本文末尾に追加
    hashtag_str = " ".join([f"#{tag}" for tag in hashtags])
    full_body = f"{body}\n\n{hashtag_str}"

    with sync_playwright() as p:
        # GitHub Actions環境ではヘッドレスモード
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            # ─── ログイン ───
            logger.info("noteにログイン中...")
            page.goto(NOTE_LOGIN_URL, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # メールアドレス入力（note.comはid="email"）
            page.wait_for_selector('#email', timeout=15000)
            page.fill('#email', NOTE_EMAIL)
            time.sleep(0.5)

            # パスワード入力（note.comはid="password"）
            page.fill('#password', NOTE_PASSWORD)
            time.sleep(0.5)

            # ログインボタンクリック（type="button"でテキストが「ログイン」）
            page.click('button:has-text("ログイン")')
            page.wait_for_load_state("networkidle", timeout=20000)
            time.sleep(2)

            # ログイン確認
            if "login" in page.url:
                logger.error("ログイン失敗。メールアドレスまたはパスワードを確認してください")
                return False

            logger.info("ログイン成功")

            # ─── 新規記事作成ページへ ───
            logger.info("新規記事作成ページに移動中...")
            page.goto(NOTE_NEW_POST_URL, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(2)

            # ─── タイトル入力 ───
            logger.info(f"タイトル入力: {title}")
            title_selector = 'div[data-placeholder="タイトル"]'
            page.wait_for_selector(title_selector, timeout=10000)
            page.click(title_selector)
            page.type(title_selector, title, delay=30)
            time.sleep(0.5)

            # ─── 本文入力 ───
            logger.info("本文入力中...")
            body_selector = 'div[data-placeholder="本文を入力してください"]'
            # セレクタが違う場合の代替
            if not page.is_visible(body_selector):
                body_selector = 'div.o-noteEditable'

            page.click(body_selector)
            time.sleep(0.5)

            # 本文を段落ごとに入力（長文対応）
            paragraphs = full_body.split("\n")
            for i, para in enumerate(paragraphs):
                if para:
                    page.keyboard.type(para, delay=10)
                page.keyboard.press("Enter")

                # 長文の場合は少し待機（タイムアウト防止）
                if i % 20 == 0 and i > 0:
                    time.sleep(0.3)

            time.sleep(1)
            logger.info("本文入力完了")

            # ─── 公開ボタンをクリック ───
            logger.info("公開処理中...")

            # 「公開」ボタンを探す
            publish_btn_selectors = [
                'button:has-text("公開")',
                'button[data-type="publish"]',
                '.m-headerPostMenu__publish button',
            ]

            publish_btn = None
            for selector in publish_btn_selectors:
                try:
                    if page.is_visible(selector):
                        publish_btn = selector
                        break
                except Exception:
                    continue

            if not publish_btn:
                logger.error("公開ボタンが見つかりません")
                # スクリーンショット保存（デバッグ用）
                screenshot_path = os.path.join(LOG_DIR, "publish_error.png")
                os.makedirs(LOG_DIR, exist_ok=True)
                page.screenshot(path=screenshot_path)
                logger.info(f"スクリーンショット保存: {screenshot_path}")
                return False

            page.click(publish_btn)
            time.sleep(1)

            # 最終確認ダイアログがある場合
            try:
                confirm_btn = page.wait_for_selector(
                    'button:has-text("投稿する")', timeout=5000
                )
                if confirm_btn:
                    confirm_btn.click()
                    logger.info("投稿確認ボタンをクリック")
            except PlaywrightTimeout:
                pass  # 確認ダイアログがない場合はスキップ

            # 投稿完了を待つ
            time.sleep(3)
            page.wait_for_load_state("networkidle", timeout=15000)

            # 投稿後のURLを取得
            note_url = page.url
            logger.info(f"投稿完了: {note_url}")

            # 履歴保存
            save_post_history(article, note_url)
            return True

        except PlaywrightTimeout as e:
            logger.error(f"タイムアウトエラー: {e}")
            try:
                screenshot_path = os.path.join(LOG_DIR, "timeout_error.png")
                os.makedirs(LOG_DIR, exist_ok=True)
                page.screenshot(path=screenshot_path)
            except Exception:
                pass
            return False

        except Exception as e:
            logger.error(f"投稿エラー: {e}", exc_info=True)
            try:
                screenshot_path = os.path.join(LOG_DIR, "error.png")
                os.makedirs(LOG_DIR, exist_ok=True)
                page.screenshot(path=screenshot_path)
            except Exception:
                pass
            return False

        finally:
            browser.close()


def run(article: dict) -> bool:
    """メイン処理"""
    logger.info("=== note投稿エージェント 開始 ===")
    success = post_to_note(article)
    if success:
        logger.info("=== note投稿 完了 ===")
    else:
        logger.error("=== note投稿 失敗 ===")
    return success


if __name__ == "__main__":
    # テスト用: モック記事を投稿
    mock_article = {
        "title": "テスト記事：高配当株の選び方",
        "body": "## テスト\nこれはテスト投稿です。\n\n## まとめ\nテスト完了。\n\n※本記事は情報提供のみです。",
        "theme_id": "japan_stocks",
        "theme_name": "日本株・個別銘柄",
        "topic": "高配当株の選び方",
        "hashtags": ["日本株", "高配当", "投資"],
        "char_count": 100,
    }
    run(mock_article)
