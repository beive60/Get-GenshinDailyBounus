import asyncio
import os
from playwright.async_api import async_playwright, TimeoutError

# --- 設定 ---
TARGET_URL = "https://act.hoyoverse.com/ys/event/e20221107-community/index.html"
# --- ここまで ---

async def main():
    env = os.path.dirname(os.path.abspath(__file__))
    auth_file_path = os.path.join(env, "auth_state.json")
    async with async_playwright() as p:
        # ブラウザを起動
        browser = await p.chromium.launch(headless=False) # 動作確認のためヘッドレスモードを無効化

        # 認証情報ファイルがあれば利用し、なければ新しいコンテキストを作成
        if os.path.exists(auth_file_path):
            print(f"'{auth_file_path}' を読み込んでコンテキストを作成します。")
            context = await browser.new_context(storage_state=auth_file_path)
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
                
                # クリック直後に指定された要素が表示されるかチェック
                try:
                    special_element_selector = 'body > div._1NVi6w4R.custom-mihoyo-common-mask > div > div > span'
                    await page.wait_for_selector(special_element_selector, timeout=3000)
                    print("クリック直後に特定の要素を発見しました。クリックします。")
                    await page.locator(special_element_selector).click()
                    await page.wait_for_timeout(2000)  # クリック後の反応を待つ
                except TimeoutError:
                    print("クリック直後に特定の要素は表示されませんでした。")
                except Exception as e:
                    print(f"クリック直後の特定要素処理でエラーが発生しました: {e}")
            
            checkin_page = await new_page_info.value
            print("新しいタブにフォーカスを当てます。")
            await checkin_page.bring_to_front()
            await checkin_page.wait_for_load_state('domcontentloaded')
            
            # 特定の要素が存在する場合はクリック
            try:
                special_element_selector = 'body > div._1NVi6w4R.custom-mihoyo-common-mask > div > div > span'
                special_element = await checkin_page.query_selector(special_element_selector)
                if special_element:
                    print("特定の要素を発見しました。クリックします。")
                    await special_element.click()
                    await checkin_page.wait_for_timeout(2000)  # クリック後の反応を待つ
                    # 特定のタイトル要素が表示されたかチェック
                    title_element_selector = 'body > div.m-modal.m-dialog.pc-dialog.m-dialog-sign.components-common-common-dialog-__index_---common-dialog---99ed7a.components-common-common-dialog-__index_---sign-dialog---3tldeh > div.m-dialog-wrapper.sign-wrapper > div.m-dialog-body.pc-dialog-body > div > div > div.components-common-common-dialog-__index_---title---xH8wpC'
                    congratulations_selector = 'div.components-common-common-dialog-__index_---title---xH8wpC'
                    
                    try:
                        # どちらかの要素が表示されるまで待機
                        title_element_found = False
                        congratulations_found = False
                        
                        # タイトル要素をチェック
                        try:
                            await checkin_page.wait_for_selector(title_element_selector, timeout=1000)
                            title_element_found = True
                            print("指定されたタイトル要素が表示されました。スクリプトを終了します。")
                        except TimeoutError:
                            pass
                        
                        # Congratulationsメッセージをチェック
                        try:
                            await checkin_page.wait_for_selector(congratulations_selector, timeout=1000)
                            congratulations_element = await checkin_page.query_selector(congratulations_selector)
                            if congratulations_element:
                                element_text = await congratulations_element.text_content()
                                if "Congratulations" in element_text and "checked in today" in element_text:
                                    congratulations_found = True
                                    print("チェックイン完了メッセージが表示されました。スクリプトを終了します。")
                        except TimeoutError:
                            pass
                        
                        # いずれかの終了条件が満たされた場合は終了
                        if title_element_found or congratulations_found:
                            return
                        else:
                            print("指定された終了条件の要素は表示されませんでした。処理を継続します。")
                            
                    except Exception as inner_e:
                        print(f"終了条件チェックでエラーが発生しました: {inner_e}")
            except Exception as e:
                print(f"特定要素のクリック処理でエラーが発生しました: {e}")

                
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
                        
                        # クリック後の反応を待つ（少し長めに）
                        print("クリック後の反応を待機しています...")
                        await checkin_page.wait_for_timeout(3000)
                        
                        # 複数のログインモーダルセレクタを試す
                        login_modal_found = False
                        login_modal_selectors = [
                            'body > div.el-overlay',
                            '.el-overlay',
                            '[class*="modal"]',
                            '[class*="login"]',
                            '[class*="dialog"]',
                            'div[role="dialog"]',
                            '.el-dialog__wrapper'
                        ]
                        
                        for selector in login_modal_selectors:
                            try:
                                print(f"ログインモーダルを検索中: {selector}")
                                await checkin_page.wait_for_selector(selector, timeout=2000)
                                print(f"ログインモーダルを発見しました: {selector}")
                                login_modal_found = True
                                break
                            except TimeoutError:
                                continue
                            except Exception as e:
                                print(f"セレクタ {selector} でエラー: {e}")
                                continue
                        
                        if login_modal_found:
                            print("\n--- ユーザー操作が必要です ---")
                            print("ログイン認証が必要です。表示されたブラウザでログインを完了してください。")
                            input("ログインが完了したら、この画面に戻ってEnterキーを押してください...")
                            print("--------------------------\n")
                            
                            # ユーザー操作後、ループを最初からやり直す
                            needs_retry = True
                            # 現在のブラウザコンテキストの認証情報（Cookieなど）をファイルに保存
                            print(f"現在の認証情報を '{auth_file_path}' に保存します。")
                            await context.storage_state(path=auth_file_path)
                            break # 現在のforループを抜けてwhileループの先頭に戻る
                        else:
                            # ログインモーダルが表示されなかった場合
                            print("ログインモーダルは検出されませんでした。クリックは成功しました。")
                            # サイトの反応をさらに待つ
                            await checkin_page.wait_for_timeout(2000)
                
                if not needs_retry:
                    print("すべてのチェックイン項目の確認が完了しました。")

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
