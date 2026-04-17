"""
poster.py - note自動投稿エージェント（Playwright使用）
生成した記事をnote.comにブラウザ自動操作で投稿する
クッキーによるログインスキップに対応
"""
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from playwright_stealth import stealth_sync

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import NOTE_EMAIL, NOTE_PASSWORD, DATA_DIR, LOG_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("note_poster")

NOTE_LOGIN_URL = "https://note.com/login"
NOTE_NEW_POST_URL = "https://note.com/notes/new"

# クッキー認証（reCAPTCHA回避）
NOTE_COOKIES = os.environ.get("NOTE_COOKIES", "")


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


def upload_thumbnail(page, thumbnail_path: str) -> bool:
    """
    公開設定パネルでアイキャッチ画像をアップロードする。
    成功すれば True、失敗しても投稿自体はキャンセルしない。
    """
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        logger.info("サムネイルパスなし、スキップ")
        return False

    logger.info(f"サムネイルアップロード開始: {thumbnail_path}")

    # note の公開パネルで使われているファイル入力セレクタを順に試す
    FILE_INPUT_SELECTORS = [
        'input[type="file"][accept*="image"]',
        'input[type="file"][accept*="jpeg"]',
        'input[type="file"]',
    ]

    file_input_selector = None
    for sel in FILE_INPUT_SELECTORS:
        try:
            el = page.wait_for_selector(sel, timeout=5000, state="attached")
            if el:
                file_input_selector = sel
                logger.info(f"ファイル入力発見: {sel}")
                break
        except PlaywrightTimeout:
            continue

    if not file_input_selector:
        # クリックでファイル入力が現れるパターンを試す
        UPLOAD_BTN_SELECTORS = [
            'button:has-text("アイキャッチ")',
            'button:has-text("画像")',
            '[class*="eyecatch"]',
            '[class*="thumbnail"]',
            '[class*="cover"]',
        ]
        for btn_sel in UPLOAD_BTN_SELECTORS:
            try:
                btn = page.query_selector(btn_sel)
                if btn:
                    btn.click()
                    time.sleep(1)
                    for sel in FILE_INPUT_SELECTORS:
                        try:
                            el = page.wait_for_selector(sel, timeout=3000, state="attached")
                            if el:
                                file_input_selector = sel
                                break
                        except PlaywrightTimeout:
                            continue
                    if file_input_selector:
                        break
            except Exception:
                continue

    if not file_input_selector:
        logger.warning("アイキャッチのファイル入力が見つかりません（セレクタ要確認）")
        # デバッグ用スクリーンショット保存
        try:
            ss_path = os.path.join(LOG_DIR, "thumb_upload_debug.png")
            os.makedirs(LOG_DIR, exist_ok=True)
            page.screenshot(path=ss_path)
            logger.info(f"デバッグSS保存: {ss_path}")
        except Exception:
            pass
        return False

    try:
        page.set_input_files(file_input_selector, thumbnail_path)
        logger.info("ファイルをセット完了")
        time.sleep(2)

        # トリミング/確認ダイアログへの対応
        CONFIRM_TEXTS = ["適用", "OK", "確認", "保存", "設定する", "完了"]
        for confirm_text in CONFIRM_TEXTS:
            try:
                btn = page.wait_for_selector(
                    f'button:has-text("{confirm_text}")', timeout=3000
                )
                if btn:
                    btn.click()
                    logger.info(f"確認ボタンクリック: 「{confirm_text}」")
                    time.sleep(1.5)
                    break
            except PlaywrightTimeout:
                continue

        logger.info("サムネイルアップロード完了")
        return True

    except Exception as e:
        logger.warning(f"サムネイルアップロード失敗（投稿は続行）: {e}")
        return False


def insert_paid_border(page) -> bool:
    """
    エディタ内に有料ボーダーを挿入する。
    無料パートの末尾にカーソルがある状態で呼び出す。
    失敗しても投稿はキャンセルしない。
    """
    logger.info("有料ボーダーを挿入中...")

    # アプローチ1: 「+」ボタンからブロックメニューを開く
    try:
        page.keyboard.press("Enter")
        time.sleep(0.5)

        PLUS_BTN_SELECTORS = [
            'button[aria-label*="ブロック"]',
            'button[aria-label*="追加"]',
            '[class*="addBlock"]',
            '[class*="block-add"]',
            '[class*="BlockAdd"]',
            '[class*="editorAdd"]',
        ]
        plus_btn = None
        for sel in PLUS_BTN_SELECTORS:
            try:
                plus_btn = page.wait_for_selector(sel, timeout=2000)
                if plus_btn:
                    logger.info(f"「+」ボタン発見: {sel}")
                    break
            except PlaywrightTimeout:
                continue

        if plus_btn:
            plus_btn.click()
            time.sleep(1)
            PAID_ITEM_SELECTORS = [
                'button:has-text("有料")',
                'li:has-text("有料")',
                '[class*="paid"]',
                'button:has-text("販売")',
                'li:has-text("有料ライン")',
            ]
            for sel in PAID_ITEM_SELECTORS:
                try:
                    item = page.wait_for_selector(sel, timeout=2000)
                    if item:
                        item.click()
                        logger.info(f"有料ボーダー挿入完了（メニュー）: {sel}")
                        time.sleep(1)
                        return True
                except PlaywrightTimeout:
                    continue
    except Exception as e:
        logger.warning(f"有料ボーダー アプローチ1失敗: {e}")

    # アプローチ2: スラッシュコマンド "/有料"
    try:
        page.keyboard.press("Enter")
        time.sleep(0.3)
        page.keyboard.type("/有料")
        time.sleep(1)
        SUGGESTION_SELECTORS = [
            'li:has-text("有料")',
            '[class*="suggestion"]:has-text("有料")',
            'button:has-text("有料ライン")',
            '[role="option"]:has-text("有料")',
        ]
        for sel in SUGGESTION_SELECTORS:
            try:
                option = page.wait_for_selector(sel, timeout=2000)
                if option:
                    option.click()
                    logger.info(f"有料ボーダー挿入完了（スラッシュ）: {sel}")
                    time.sleep(1)
                    return True
            except PlaywrightTimeout:
                continue
        # サジェストが出なかった場合は入力内容を削除
        page.keyboard.press("Escape")
        time.sleep(0.3)
        for _ in range(4):
            page.keyboard.press("Backspace")
    except Exception as e:
        logger.warning(f"有料ボーダー アプローチ2失敗: {e}")

    # デバッグスクリーンショット
    try:
        ss_path = os.path.join(LOG_DIR, "paid_border_debug.png")
        os.makedirs(LOG_DIR, exist_ok=True)
        page.screenshot(path=ss_path)
        logger.info(f"有料ボーダーデバッグSS保存: {ss_path}")
    except Exception:
        pass

    logger.warning("有料ボーダー挿入失敗（投稿は続行）")
    return False


def set_article_price(page, price: int = 300) -> bool:
    """
    公開設定パネルで記事価格を設定する。
    失敗しても投稿はキャンセルしない。
    """
    logger.info(f"記事価格を設定中: {price}円...")

    try:
        # 「販売設定」「有料にする」などのトグルを探す
        SALE_TOGGLE_SELECTORS = [
            'button:has-text("販売設定")',
            'button:has-text("有料にする")',
            'label:has-text("有料")',
            'input[type="radio"][value*="paid"]',
            '[class*="saleToggle"]',
            '[class*="SaleToggle"]',
            '[class*="priceToggle"]',
        ]
        for sel in SALE_TOGGLE_SELECTORS:
            try:
                toggle = page.wait_for_selector(sel, timeout=3000)
                if toggle:
                    toggle.click()
                    logger.info(f"販売設定トグルクリック: {sel}")
                    time.sleep(1)
                    break
            except PlaywrightTimeout:
                continue

        # 価格入力フィールドを探す
        PRICE_INPUT_SELECTORS = [
            'input[name*="price"]',
            'input[placeholder*="価格"]',
            'input[placeholder*="円"]',
            'input[type="number"]',
        ]
        for sel in PRICE_INPUT_SELECTORS:
            try:
                price_input = page.wait_for_selector(sel, timeout=3000)
                if price_input:
                    price_input.triple_click()
                    price_input.fill(str(price))
                    logger.info(f"価格入力完了: {price}円 (セレクタ: {sel})")
                    time.sleep(0.5)
                    return True
            except PlaywrightTimeout:
                continue

        logger.warning("価格入力フィールドが見つかりません")
        try:
            ss_path = os.path.join(LOG_DIR, "price_setting_debug.png")
            os.makedirs(LOG_DIR, exist_ok=True)
            page.screenshot(path=ss_path)
            logger.info(f"価格設定デバッグSS保存: {ss_path}")
        except Exception:
            pass
        return False

    except Exception as e:
        logger.warning(f"価格設定失敗（投稿は続行）: {e}")
        return False


def post_to_note(article: dict, thumbnail_path: str = "") -> bool:
    """Playwrightでnoteに記事を投稿"""
    title = article["title"]
    hashtags = article.get("hashtags", [])

    # 有料コンテンツの分割対応
    has_paid = article.get("has_paid_content", False)
    body_free = article.get("body_free", article.get("body", ""))
    body_paid = article.get("body_paid", "")
    article_price = article.get("price", 300)

    # ハッシュタグ文字列
    hashtag_str = " ".join([f"#{tag}" for tag in hashtags])

    # 無料パート末尾にハッシュタグを付ける（有料の場合は無料パートのみにタグ追加）
    if has_paid:
        full_body_free = f"{body_free}\n\n{hashtag_str}"
        full_body_paid = body_paid
    else:
        body = article.get("body", body_free)
        full_body_free = f"{body}\n\n{hashtag_str}"
        full_body_paid = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )

        page = context.new_page()
        stealth_sync(page)

        try:
            # ─── 認証方法の選択 ───
            if NOTE_COOKIES:
                # クッキーを使ってログインをスキップ（reCAPTCHA回避）
                logger.info("クッキーでログイン中...")
                try:
                    raw_cookies = json.loads(NOTE_COOKIES)
                    logger.info(f"クッキー件数: {len(raw_cookies)}")
                    # 最初のクッキーのキー一覧をデバッグ出力（値は非表示）
                    if raw_cookies:
                        logger.info(f"クッキーフィールド: {list(raw_cookies[0].keys())}")
                    # 絶対最小構成：name + value + url のみ
                    cookies = []
                    for i, c in enumerate(raw_cookies):
                        name = c.get("name", "")
                        value = c.get("value")
                        if not name or value is None:
                            logger.info(f"スキップ [{i}]: name={name!r}, value={value!r}")
                            continue
                        cookies.append({
                            "name": name,
                            "value": str(value),
                            "url": "https://note.com",
                        })
                    logger.info(f"{len(cookies)}件のクッキーを追加します")
                    context.add_cookies(cookies)
                    logger.info(f"{len(cookies)}件のクッキーをセット完了")
                except json.JSONDecodeError as e:
                    logger.error(f"クッキーのJSON解析エラー: {e}")
                    return False

                # /notes/new に直接アクセスしてログイン確認（トップページは認証不要なので使わない）
                page.goto(NOTE_NEW_POST_URL, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=15000)
                time.sleep(2)

                if "login" in page.url:
                    logger.error("クッキーが無効または期限切れです。Cookie Editorで再エクスポートしてください")
                    screenshot_path = os.path.join(LOG_DIR, "cookie_failed.png")
                    os.makedirs(LOG_DIR, exist_ok=True)
                    page.screenshot(path=screenshot_path)
                    return False

                logger.info(f"クッキーでログイン成功・投稿ページ到達: {page.url}")
                # すでに/notes/newにいるのでそのまま続行
                time.sleep(1)

            elif NOTE_EMAIL and NOTE_PASSWORD:
                # メール/パスワードでログイン（reCAPTCHAが出る場合は失敗）
                logger.info("メール/パスワードでログイン中...")
                page.goto(NOTE_LOGIN_URL, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=15000)

                page.wait_for_selector('#email', timeout=15000)
                page.fill('#email', NOTE_EMAIL)
                time.sleep(0.5)
                page.fill('#password', NOTE_PASSWORD)
                time.sleep(0.5)
                page.click('button:has-text("ログイン")')

                try:
                    page.wait_for_url(lambda url: "login" not in url, timeout=25000)
                    logger.info(f"ログイン成功: {page.url}")
                except PlaywrightTimeout:
                    screenshot_path = os.path.join(LOG_DIR, "login_failed.png")
                    os.makedirs(LOG_DIR, exist_ok=True)
                    page.screenshot(path=screenshot_path)
                    logger.error("ログイン失敗（reCAPTCHAが表示されている可能性があります）")
                    return False

                time.sleep(2)

            else:
                logger.error("NOTE_COOKIES または NOTE_EMAIL/NOTE_PASSWORD が未設定です")
                return False

            # ─── タイトル入力 ───
            logger.info(f"タイトル入力: {title}")
            title_selector = 'textarea[placeholder="記事タイトル"]'
            page.wait_for_selector(title_selector, timeout=15000)
            page.click(title_selector)
            page.fill(title_selector, title)
            time.sleep(0.5)

            # ─── 本文入力 ───
            logger.info("本文入力中...")
            body_selector = 'div.ProseMirror'
            page.wait_for_selector(body_selector, timeout=10000)
            page.click(body_selector)
            time.sleep(0.5)

            def type_paragraphs(text: str):
                """テキストを段落ごとにエディタへ入力する"""
                paragraphs = text.split("\n")
                for i, para in enumerate(paragraphs):
                    if para:
                        page.keyboard.type(para, delay=5)
                    page.keyboard.press("Enter")
                    if i % 20 == 0 and i > 0:
                        time.sleep(0.3)

            # 無料パートを入力
            type_paragraphs(full_body_free)
            time.sleep(0.5)

            if has_paid and full_body_paid:
                # 有料ボーダーを挿入
                border_ok = insert_paid_border(page)
                if border_ok:
                    logger.info("有料パート入力中...")
                    type_paragraphs(full_body_paid)
                    logger.info("有料パート入力完了")
                else:
                    # ボーダー挿入失敗時は有料パートも続けて入力（全文公開になるが投稿は継続）
                    logger.warning("有料ボーダーなしで有料パートを追加（全文公開）")
                    type_paragraphs(full_body_paid)

            time.sleep(1)
            logger.info("本文入力完了")

            # ─── 「公開に進む」ボタンをクリック ───
            logger.info("公開処理中...")
            publish_btn = 'button:has-text("公開に進む")'
            page.wait_for_selector(publish_btn, timeout=10000)
            page.click(publish_btn)
            time.sleep(2)

            # ─── サムネイル（アイキャッチ）アップロード ───
            upload_thumbnail(page, thumbnail_path)

            # ─── 記事価格の設定（有料コンテンツのみ） ───
            if has_paid:
                set_article_price(page, price=article_price)
                time.sleep(1)

            # 公開確認ダイアログの「投稿する」ボタン
            try:
                confirm_btn = page.wait_for_selector(
                    'button:has-text("投稿する")', timeout=8000
                )
                if confirm_btn:
                    confirm_btn.click()
                    logger.info("投稿確認ボタンをクリック")
            except PlaywrightTimeout:
                # 確認ダイアログがない場合はそのまま続行
                logger.info("確認ダイアログなし、そのまま続行")

            time.sleep(3)
            page.wait_for_load_state("networkidle", timeout=15000)

            note_url = page.url
            logger.info(f"投稿完了: {note_url}")
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


def run(article: dict, thumbnail_path: str = "") -> bool:
    """メイン処理"""
    logger.info("=== note投稿エージェント 開始 ===")
    if thumbnail_path:
        logger.info(f"サムネイル: {thumbnail_path}")
    success = post_to_note(article, thumbnail_path=thumbnail_path)
    if success:
        logger.info("=== note投稿 完了 ===")
    else:
        logger.error("=== note投稿 失敗 ===")
    return success


if __name__ == "__main__":
    mock_article = {
        "title": "【実録】AIに記事を書かせたら読者に怒られた話",
        "body": "## テスト\nこれはテスト投稿です。\n\n## まとめ\nテスト完了。",
        "body_free": "## 正直に言います\nAIに全部まかせたら怒られました。\n\nこの記事では、その失敗から学んだことを有料パートで詳しく解説します。",
        "body_paid": "## 失敗の全容\n実際に起きたことはこうです。\n\nプロンプトはこちら：\n```\n（省略）\n```\n\n## 対策\n次からはこうします。",
        "has_paid_content": True,
        "price": 300,
        "theme_id": "failure_report",
        "theme_name": "失敗・反省記録",
        "topic": "AIに任せすぎて読者に怒られた経験",
        "hashtags": ["AI副業", "失敗談", "副業", "自動化", "note運用"],
        "char_count": 300,
        "char_count_free": 80,
        "char_count_paid": 120,
    }
    run(mock_article)
