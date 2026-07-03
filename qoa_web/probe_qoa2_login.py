#!/usr/bin/env python3
"""Probe qoa2 login and avatar flows for product research."""

import json
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options

BASE = "https://qoa2.base44.app"
EMAIL = "test1@itelearn.com"
PASSWORDS = ["test@itelearn.com", "test@itelearn"]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    opts = Options()
    opts.add_argument("--headless=new")
    driver = webdriver.Edge(options=opts)
    report: dict = {"login_attempts": [], "post_login": {}}
    logged_in = False
    try:
        for pw in PASSWORDS:
            driver.get(f"{BASE}/login")
            time.sleep(2)
            email_el = driver.find_elements(By.CSS_SELECTOR, "input[type='email'], input[name='email']")
            pass_el = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
            if not email_el or not pass_el:
                report["login_attempts"].append(
                    {"password": pw, "error": "fields not found", "url": driver.current_url}
                )
                continue
            email_el[0].clear()
            email_el[0].send_keys(EMAIL)
            pass_el[0].clear()
            pass_el[0].send_keys(pw)
            for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
                label = (btn.text or "").strip().lower()
                if label in ("sign in", "log in", "login", "continue"):
                    btn.click()
                    break
            else:
                buttons = driver.find_elements(By.CSS_SELECTOR, "button")
                if buttons:
                    buttons[0].click()
            time.sleep(5)
            on_login = "/login" in driver.current_url.lower()
            attempt = {
                "password": pw,
                "url_after": driver.current_url,
                "title": driver.title,
                "still_on_login": on_login,
            }
            if not on_login:
                attempt["success"] = True
                logged_in = True
            else:
                attempt["success"] = False
                body = driver.find_element(By.TAG_NAME, "body").text[:200]
                attempt["body_snippet"] = body
            report["login_attempts"].append(attempt)
            if logged_in:
                break

        if logged_in:
            time.sleep(2)
            avatars = []
            for name in ("Client", "Consultant", "Promoter", "Nalanda"):
                btns = driver.find_elements(
                    By.XPATH, f"//button[normalize-space()='{name}']"
                )
                entry = {"name": name, "found": bool(btns)}
                if btns:
                    try:
                        btns[0].click()
                        time.sleep(1.5)
                        main = driver.find_elements(By.TAG_NAME, "main")
                        entry["snippet"] = (
                            main[0].text[:400] if main else driver.find_element(By.TAG_NAME, "body").text[:400]
                        )
                    except Exception as exc:
                        entry["click_error"] = str(exc)
                avatars.append(entry)
            report["post_login"]["avatars"] = avatars
            report["post_login"]["url"] = driver.current_url
            report["post_login"]["title"] = driver.title
            for path in ("/build", "/arena", "/dashboard"):
                driver.get(BASE + path)
                time.sleep(2)
                key = "route_" + path.strip("/")
                report["post_login"][key] = {
                    "url": driver.current_url,
                    "title": driver.title,
                    "snippet": driver.find_element(By.TAG_NAME, "body").text[:350],
                }
    finally:
        driver.quit()

    out = Path(__file__).parent / "qoa2_login_probe.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
