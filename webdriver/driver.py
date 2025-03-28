import os
import queue
import threading
import time
import urllib.parse
from datetime import datetime
from random import randint

from playwright.sync_api import sync_playwright


def sanitize_filename(url):
    """Формирует название папки и имя файла."""
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    lat_lon = query_params.get("ll", [""])[0].replace(",", "_")
    text = query_params.get("text", [""])[0]
    zoom = query_params.get("z", [""])[0]

    filename_parts = [lat_lon, text, zoom]
    filename = "_".join(filter(None, filename_parts))

    return lat_lon[:100], filename[:100]


def get_screenshots(links, num_threads=1):
    """Сохранение скриншотов в папку."""
    pause_event = threading.Event()
    pause_event.set()

    failed_links = []
    failed_links_lock = threading.Lock()

    base_screenshot_dir = "screenshots"
    if not os.path.exists(base_screenshot_dir):
        os.makedirs(base_screenshot_dir)

    task_queue = queue.Queue()
    for link in links:
        task_queue.put(link)

    coordinates_to_time = {}

    def browser_worker(task_queue, browser_id):
        """Создание скриншотов."""
        while not task_queue.empty():
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=False,
                        args=["--disable-blink-features=AutomationControlled"],
                    )
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 720}
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
                            captcha_element = page.locator("text=" + captcha_text)

                            if captcha_element.is_visible():
                                print(
                                    f"Обнаружена капча в браузере {browser_id}, задания приостановлены"
                                )
                                pause_event.clear()

                                while captcha_element.is_visible():
                                    print("Ожидаем, пока капча будет решена...")
                                    time.sleep(5)
                                time.sleep(60)  # Время на решение капчи

                                print("Капча решена, продолжаем выполнение")
                                pause_event.set()
                                with failed_links_lock:
                                    failed_links.append(link)
                                continue

                            page.click(".sidebar-toggle-button")
                            time.sleep(1)
                            page.add_style_tag(
                                content=".popup { display: none !important; }"
                            )
                            time.sleep(randint(6, 10))

                            lat_lon, safe_filename = sanitize_filename(link)

                            if lat_lon not in coordinates_to_time:
                                main_timestamp = datetime.now().strftime("%H%M%d%m%y")
                                coordinates_to_time[lat_lon] = main_timestamp
                            else:
                                main_timestamp = coordinates_to_time[lat_lon]

                            screenshot_dir = os.path.join(
                                base_screenshot_dir, f"{lat_lon}_{main_timestamp}"
                            )
                            if not os.path.exists(screenshot_dir):
                                os.makedirs(screenshot_dir)

                            screenshot_time = datetime.now().strftime("%H%M%d%m%y")

                            screenshot_name = f"{safe_filename}_{screenshot_time}.png"
                            screenshot_path = os.path.join(
                                screenshot_dir, screenshot_name
                            )

                            page.screenshot(path=screenshot_path)

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
    for browser_id in range(1, num_threads + 3):
        thread = threading.Thread(target=browser_worker, args=(task_queue, browser_id))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    return failed_links
