import os
import queue
import threading
import time

from playwright.sync_api import sync_playwright


def browser_worker(task_queue, browser_id):
    """Обработка ссылок в браузере."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False, args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(viewport={"width": 800, "height": 800})
            page = context.new_page()

            while not task_queue.empty():
                try:
                    link = task_queue.get_nowait()
                    page.goto(link, wait_until="load")
                    time.sleep(1)
                    page.click(".sidebar-toggle-button")
                    time.sleep(1)
                    page.add_style_tag(content=".app { display: none !important; }")
                    time.sleep(3)
                    screenshot_name = f"{browser_id}_{int(time.time())}.png"
                    page.screenshot(path=os.path.join("screenshots", screenshot_name))
                except queue.Empty:
                    break
                finally:
                    task_queue.task_done()
            browser.close()

    except Exception as e:
        print(f"Ошибка в браузере {browser_id}: {e}")


links = []

# Очередь заданий
task_queue = queue.Queue()
for link in links:
    task_queue.put(link)

# Потоки
threads = []
for browser_id in range(1, 4):
    thread = threading.Thread(target=browser_worker, args=(task_queue, browser_id))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()
