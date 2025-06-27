from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import USERNAME, PASSWORD

LOGIN_URL = 'https://amsterdam.mijndak.nl/Inloggen'

def get_session_cookies(headless: bool = True, timeout: int = 20) -> dict:
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--blink-settings=imagesEnabled=false')

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, timeout)
        try:
            accept_btn = wait.until(EC.element_to_be_clickable((By.ID, 'cookiescript_accept')))
            accept_btn.click()
        except Exception:
            pass

        wait.until(EC.presence_of_element_located((By.ID, 'Input_UsernameVal'))).send_keys(USERNAME)
        driver.find_element(By.ID, 'Input_PasswordVal').send_keys(PASSWORD)
        login_btn = driver.find_element(By.XPATH, "//button[contains(., 'Log in')]")
        driver.execute_script("arguments[0].click();", login_btn)
        wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(., 'Uitloggen')]")))
        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    finally:
        driver.quit()
    return cookies