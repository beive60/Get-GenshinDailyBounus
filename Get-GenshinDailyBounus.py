import asyncio
import os
from playwright.async_api import async_playwright, TimeoutError

# --- 設定 ---
AUTH_FILE = "auth_state.json"
TARGET_URL = "https://act.hoyoverse.com/ys/event/e20221107-community/index.html"
# --- ここまで ---

async def main():
    async with async_playwright() as p:
        # ブラウザを起動
        browser = await p.chromium.launch(headless=False) # 動作確認のためヘッドレスモードを無効化

        # 認証情報ファイルがあれば利用し、なければ新しいコンテキストを作成
        if os.path.exists(AUTH_FILE):
            print(f"'{AUTH_FILE}' を読み込んでコンテキストを作成します。")
            context = await browser.new_context(storage_state=AUTH_FILE)
        else:
            print(f"認証ファイルが見つかりません。新しいコンテキストを作成します。")
            context = await browser.new_context()

        # 最初のページを開く
        page = await context.new_page()
        print(f"{TARGET_URL} にアクセスします...")
        await page.goto(TARGET_URL)

        try:
            # 新規タブが開く処理を待機
            async with context.expect_page() as new_page_info:
                print("ツールボックス内の要素をクリックします...")
                # セレクタが非常に長いため、サイトの更新で失敗する可能性があります
                await page.locator(
                    '#frame > div > div.src-components-common-assets-__pcModal_---modal---AYjGhX > div.src-components-common-assets-__pcModal_---rightBox---axd9hm > div.src-components-common-assets-__pcModal_---gameToolsBox---NkOOAy > div.src-components-common-assets-__pcModal_---gameToolsContent---euCXJ2 > div.src-components-common-assets-__pcModal_---longPitBox---mPYNmV > div'
                ).click(timeout=15000) # 15秒待機
            
            checkin_page = await new_page_info.value
            print("新しいタブにフォーカスを当てます。")
            await checkin_page.bring_to_front()
            await checkin_page.wait_for_load_state('domcontentloaded')

            # ログインが必要だった場合にループを再開するためのフラグ
            needs_retry = True
            while needs_retry:
                needs_retry = False # ループの開始時にリセット

                print("チェックイン項目を調査します...")
                # チェックインリストの親要素
                list_parent_selector = 'div.components-home-assets-__sign-content-test_---sign-list---3Nz_jn'
                # 親要素が表示されるまで待機
                await checkin_page.wait_for_selector(list_parent_selector, timeout=15000)
                
                # 親要素の子要素をすべて取得
                items = await checkin_page.query_selector_all(f'{list_parent_selector} > div')

                for item in items:
                    # 赤い点のspan要素があるか確認
                    red_point = await item.query_selector('span.components-home-assets-__sign-content-test_---red-point---2jUBf9')
                    if red_point:
                        print("クリック対象の要素を見つけました。クリックします。")
                        await item.click()
                        
                        # ログインモーダルが表示されるか短時間待機
                        try:
                            login_modal_selector = 'body > div.el-overlay'
                            await checkin_page.wait_for_selector(login_modal_selector, timeout=5000) # 5秒待機
                            
                            print("\n--- ユーザー操作が必要です ---")
                            print("ログイン認証が必要です。表示されたブラウザでログインを完了してください。")
                            input("ログインが完了したら、この画面に戻ってEnterキーを押してください...")
                            print("--------------------------\n")
                            
                            # ユーザー操作後、ループを最初からやり直す
                            needs_retry = True
                            await checkin_page.reload() # 念のためページをリロード
                            break # 現在のforループを抜けてwhileループの先頭に戻る
                        
                        except TimeoutError:
                            # ログインモーダルが表示されなかった場合
                            print("クリックは成功しました。ログインは不要でした。")
                            # サイトの反応を待つ
                            await checkin_page.wait_for_timeout(3000)
                
                if not needs_retry:
                    print("すべてのチェックイン項目の確認が完了しました。")

            # 現在のブラウザコンテキストの認証情報（Cookieなど）をファイルに保存
            print(f"現在の認証情報を '{AUTH_FILE}' に保存します。")
            await context.storage_state(path=AUTH_FILE)

        except TimeoutError:
            print("タイムアウトエラー: 指定された要素が見つかりませんでした。サイトの構造が変更された可能性があります。")
        except Exception as e:
            print(f"予期せぬエラーが発生しました: {e}")

        finally:
            # スクリプトの終了
            print("処理が完了しました。ブラウザを閉じます。")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
