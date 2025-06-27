import logging
import os
import time
from pathlib import Path
import json
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException

from session import get_session_cookies
from housing import fetch_aanbod, filter_geschikt
from storage import load_ids, save_ids
from telegram_utils import send_telegram
from config import FOUND_FILE, VISITED_FILE, CHECK_INTERVAL, DATA_DIR

# Logging setup
os.makedirs(DATA_DIR, exist_ok=True)
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "bot.log"
logger = logging.getLogger()
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def close_popups(driver):
    """
    Sluit bekende popups die knoppen kunnen blokkeren.
    """
    # Notificaties-popup
    try:
        close_btn = driver.find_element(By.CSS_SELECTOR, "#b2-scrollcontainer a")
        close_btn.click()
        WebDriverWait(driver, 2).until(
            EC.invisibility_of_element_located((By.ID, "b2-scrollcontainer"))
        )
        logger.info("Notificatie-popup gesloten.")
    except NoSuchElementException:
        pass
    except Exception as e:
        logger.warning(f"Notificatie-popup kon niet worden gesloten: {e}")

    # Sitemelding-popup (oplichterswaarschuwing)
    try:
        close_btn = driver.find_element(By.CSS_SELECTOR, "#b43-b2-sitemelding a")
        close_btn.click()
        WebDriverWait(driver, 2).until(
            EC.invisibility_of_element_located((By.ID, "b43-b2-sitemelding"))
        )
        logger.info("Sitemelding-popup gesloten.")
    except NoSuchElementException:
        pass
    except Exception as e:
        logger.warning(f"Sitemelding-popup kon niet worden gesloten: {e}")

def scroll_to_reageer_button(driver, max_tries=12):
    """
    Scrollt trapsgewijs naar beneden tot de reageer-knop zichtbaar én klikbaar is.
    Returnt het button-element indien gevonden, anders None.
    """
    for _ in range(max_tries):
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(@class, 'btn-primary') and contains(., 'Reageren op deze Woning')]")
            if btn.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                # Wacht tot hij clickable is
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-primary') and contains(., 'Reageren op deze Woning')]")))
                return btn
        except Exception:
            pass
        # Scroll telkens één viewport verder
        driver.execute_script("window.scrollBy(0, window.innerHeight);")
        time.sleep(0.4)
    # Als hij niet gevonden is, probeer een laatste keer te wachten
    try:
        btn = WebDriverWait(driver, 7).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-primary') and contains(., 'Reageren op deze Woning')]"))
        )
        return btn
    except Exception:
        return None

def wait_and_click_reageer(driver):
    """
    Zorgt dat de reageerknop in beeld is, sluit popups als het niet lukt, probeer opnieuw.
    """
    btn = scroll_to_reageer_button(driver)
    if not btn:
        logger.warning("Reageer-knop niet gevonden na scrollen.")
        return False
    try:
        btn.click()
        return True
    except ElementClickInterceptedException:
        logger.info("Popup blokkeert click, probeer popups te sluiten en opnieuw te klikken...")
        # Sluit popups met class popup-dialog
        popups = driver.find_elements(By.CSS_SELECTOR, "div.popup-dialog")
        for popup in popups:
            try:
                close_btn = popup.find_element(By.TAG_NAME, "button")
                close_btn.click()
                WebDriverWait(driver, 5).until(EC.invisibility_of_element(popup))
            except Exception:
                driver.execute_script("arguments[0].style.display='none';", popup)
        # Scroll de knop in beeld en probeer opnieuw
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        try:
            btn.click()
            return True
        except Exception as e:
            logger.warning(f"Klikken na popup sluiten lukt niet: {e}")
            return False
    except Exception as e:
        logger.warning(f"Kon niet op de reageer-knop klikken: {e}")
        return False

def process_woning(driver, woning, gevonden, gereageerd):
    pid = woning.get('PublicatieId')
    if not pid or pid in gevonden:
        return

    detail_url = f"https://amsterdam.mijndak.nl/HuisDetails?PublicatieId={pid}"
    driver.get(detail_url)
    close_popups(driver)

    # Skip als reeds gereageerd
    try:
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((
                By.XPATH, "//button[contains(., 'Reactie intrekken')]"
            ))
        )
        logger.info(f"Overslaan {pid}: reeds gereageerd")
        gevonden.add(pid)
        gereageerd.add(pid)
        return
    except TimeoutException:
        pass

    msg = (
        f"🏠 *Nieuwe woning:* {woning.get('Adres', 'Onbekend adres')}\n"
        f"Prijs €{woning.get('Huur', 'n.v.t.')}, {woning.get('Oppervlakte', 'n.v.t.')}m², {woning.get('Kamers', 'n.v.t.')} kamers\n"
        f"[Details]({detail_url})"
    )
    send_telegram(msg)
    logger.info(f"Verstuurd notificatie voor {pid}")
    gevonden.add(pid)

    if pid not in gereageerd:
        success = wait_and_click_reageer(driver)
        if success:
            logger.info(f"Gereageerd op {pid}")
            send_telegram(f"✅ Gereageerd op {pid}")
            gereageerd.add(pid)
        else:
            screenshot_path = f"debug_{pid}.png"
            driver.save_screenshot(screenshot_path)
            logger.warning(f"Kon niet reageren op {pid}, zie screenshot: {screenshot_path}")

def main():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--ignore-certificate-errors')
    driver = webdriver.Chrome(options=options)

    # Login bij start (gebruik je eigen logica)
    session_cookies = get_session_cookies(headless=True)
    driver.get("https://amsterdam.mijndak.nl/")
    for name, value in session_cookies.items():
        driver.add_cookie({
            'name': name,
            'value': value,
            'domain': 'amsterdam.mijndak.nl',
            'path': '/'
        })
    driver.refresh()
    time.sleep(2)

    gevonden = load_ids(FOUND_FILE)
    gereageerd = load_ids(VISITED_FILE)

    try:
        while True:
            try:
                items = fetch_aanbod(get_session_cookies)
                geschikt = filter_geschikt(items)
                logger.info(f"Geschikte woningen gevonden: {len(geschikt)}")

                for woning in geschikt:
                    process_woning(driver, woning, gevonden, gereageerd)

                save_ids(gevonden, FOUND_FILE)
                save_ids(gereageerd, VISITED_FILE)
                logger.info(f'Wachten {CHECK_INTERVAL // 60} minuten...')
                time.sleep(CHECK_INTERVAL)

            except Exception as main_loop_error:
                logger.error(f"Fout in hoofdloop: {main_loop_error}. Probeer opnieuw in te loggen.")
                # Opnieuw inloggen als de sessie verlopen is
                session_cookies = get_session_cookies(headless=True)
                driver.get("https://amsterdam.mijndak.nl/")
                for name, value in session_cookies.items():
                    driver.add_cookie({
                        'name': name,
                        'value': value,
                        'domain': 'amsterdam.mijndak.nl',
                        'path': '/'
                    })
                driver.refresh()
                time.sleep(2)

    finally:
        driver.quit()

if __name__ == '__main__':
    main()