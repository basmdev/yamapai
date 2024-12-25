import os
import queue
import threading
import time

from playwright.sync_api import sync_playwright


def get_screenshots(links, num_threads=1):
    """Сохраняет скриншоты и возвращает список необработанных ссылок."""
    pause_event = threading.Event()
    pause_event.set()

    failed_links = []
    failed_links_lock = threading.Lock()

    screenshot_dir = "screenshots"

    task_queue = queue.Queue()
    for link in links:
        task_queue.put(link)

    if not os.path.exists(screenshot_dir):
        os.makedirs(screenshot_dir)

    def browser_worker(task_queue, browser_id):
        while not task_queue.empty():
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=False,
                        args=["--disable-blink-features=AutomationControlled"],
                    )
                    context = browser.new_context(
                        viewport={"width": 800, "height": 800}
                    )
                    page = context.new_page()

                    while not task_queue.empty():
                        try:
                            pause_event.wait()

                            link = task_queue.get_nowait()
                            page.goto(link, wait_until="load")
                            time.sleep(1)

                            captcha_text = (
                                "Подтвердите, что запросы отправляли вы, а не робот"
                            )
                            if captcha_text in page.content():
                                print(
                                    f"Обнаружена капча в браузере {browser_id}, задания приостановлены"
                                )
                                pause_event.clear()
                                time.sleep(3600)
                                pause_event.set()
                                with failed_links_lock:
                                    failed_links.append(link)
                                continue

                            page.click(".sidebar-toggle-button")
                            time.sleep(1)
                            page.add_style_tag(
                                content=".app { display: none !important; }"
                            )
                            time.sleep(1)
                            page.add_style_tag(
                                content=".popup { display: none !important; }"
                            )
                            time.sleep(10)
                            screenshot_name = f"{browser_id}_{int(time.time())}.png"
                            page.screenshot(
                                path=os.path.join(screenshot_dir, screenshot_name)
                            )
                        except Exception as task_error:
                            print(
                                f"Ошибка при обработке задания в браузере {browser_id}: {task_error}"
                            )
                            with failed_links_lock:
                                failed_links.append(link)
                        finally:
                            task_queue.task_done()

                    browser.close()
            except Exception as e:
                print(f"Ошибка в браузере {browser_id}, перезапуск: {e}")
                time.sleep(2)

    threads = []
    for browser_id in range(1, num_threads + 1):
        thread = threading.Thread(target=browser_worker, args=(task_queue, browser_id))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    return failed_links
