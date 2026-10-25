"""
Selenium test for the DevOps Task Manager.

Usage:
    pip install selenium
    set APP_URL=http://<your-alb-dns-name>        (Windows)
    export APP_URL=http://<your-alb-dns-name>     (Linux/Mac)
    python test_app.py

HEADLESS=0 shows the browser window (handy for a screen recording).
"""
import os
import sys
import time
import uuid

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

APP_URL = os.getenv("APP_URL", "http://localhost").rstrip("/")
HEADLESS = os.getenv("HEADLESS", "1") == "1"


def make_driver():
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    return webdriver.Chrome(options=opts)  # Selenium Manager fetches the driver automatically


def test_page_title(driver):
    driver.get(APP_URL)
    assert "DevOps Task Manager" in driver.title, f"Unexpected title: {driver.title}"


def test_heading_visible(driver):
    heading = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "main-heading"))
    )
    assert heading.text == "DevOps Task Manager", f"Unexpected heading: {heading.text}"


def test_add_task(driver):
    task_text = f"selenium-test-{uuid.uuid4().hex[:6]}"
    driver.find_element(By.ID, "task-input").send_keys(task_text)
    driver.find_element(By.ID, "add-btn").click()
    WebDriverWait(driver, 10).until(
        EC.text_to_be_present_in_element((By.ID, "task-list"), task_text)
    )
    assert task_text in driver.find_element(By.ID, "task-list").text


def test_mark_task_done(driver):
    before = int(driver.find_element(By.ID, "stat-done").text)
    driver.find_element(By.CSS_SELECTOR, "#task-list .check").click()
    WebDriverWait(driver, 10).until(
        lambda d: int(d.find_element(By.ID, "stat-done").text) == before + 1
    )


def test_server_host_shown(driver):
    host = driver.find_element(By.ID, "server-host").text
    assert host, "Container hostname not displayed"
    print(f"        (served by container: {host})")


def test_system_page(driver):
    driver.find_element(By.ID, "nav-system").click()
    heading = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "system-heading"))
    )
    assert heading.text == "System Status"
    assert "connected" in driver.find_element(By.ID, "db-status").text.lower()


def main():
    driver = make_driver()
    tests = [
        test_page_title,
        test_heading_visible,
        test_add_task,
        test_mark_task_done,
        test_server_host_shown,
        test_system_page,
    ]
    failed = 0
    print(f"Testing {APP_URL}\n")
    try:
        for t in tests:
            try:
                t(driver)
                print(f"  PASS  {t.__name__}")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"  FAIL  {t.__name__}: {exc}")
        driver.save_screenshot("selenium_result.png")
    finally:
        driver.quit()

    print(f"\n{len(tests) - failed}/{len(tests)} tests passed. Screenshot: selenium_result.png")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
