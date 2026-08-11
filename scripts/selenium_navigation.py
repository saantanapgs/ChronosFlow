from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from login_credentials import user, password
import time


def chronos_login():
    options = Options()

    # Apagando logs internos do chrome no console
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)

    wait = WebDriverWait(driver, 10)

    driver.get("https://se.synergye.com.br/index.php?r=site/login")

    print("Site acessado")

    login_user = wait.until(
        EC.presence_of_element_located((By.ID, "LoginForm_username"))
    )
    login_user.send_keys(user)

    login_password = wait.until(
        EC.presence_of_element_located((By.ID, "LoginForm_password"))
    )
    login_password.send_keys(password)

    login_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='submit']"))
    )
    login_btn.click()

    operational_reference = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//li[contains(@class,'dir')]//a[contains(., 'Operacional')]")
        )
    )
    operational_reference.click()

    monitored_reference = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//a[@href='/index.php?r=pessoa']")
        )
    )
    monitored_reference.click()

    return driver, wait


def searching_monitored(driver, wait, cleaned_name, final_name, destination_path):
    import time

    driver.switch_to.default_content()

    monitored_name_reference = wait.until(
        EC.element_to_be_clickable((By.ID, "Pessoa_pessoa_nome"))
    )

    monitored_name_reference.click()
    monitored_name_reference.send_keys(Keys.CONTROL, "a")
    monitored_name_reference.send_keys(Keys.BACKSPACE)

    monitored_name_reference.send_keys(cleaned_name)
    monitored_name_reference.send_keys(Keys.ENTER)

    print(f"Pesquisando: {cleaned_name}")

    time.sleep(3)
    time.sleep(3)

    linhas = driver.find_elements(By.XPATH, "//table//tr")

    monitorado_encontrado = False

    for linha in linhas:
        try:
            texto_linha = linha.text.upper()

            if cleaned_name.upper() in texto_linha:
                print(f"\nMonitorado localizado.")

                view_btn = linha.find_element(
                    By.XPATH,
                    ".//a[contains(@class,'view')]"
                )

                driver.execute_script("arguments[0].click();", view_btn)
                monitorado_encontrado = True
                break

        except Exception:
            pass

    if not monitorado_encontrado:
        print(f"\nERRO: {cleaned_name} não foi encontrado na tabela.")
        driver.get("https://se.synergye.com.br/index.php?r=pessoa")
        return

    files_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//a[@href='#arquivoPessoaTab']"))
    )
    files_btn.click()

    new_file_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//input[contains(@onclick,'openFileModal')]")
        )
    )
    new_file_btn.click()

    time.sleep(2)

    iframes = wait.until(
        EC.presence_of_all_elements_located((By.TAG_NAME, "iframe"))
    )
    driver.switch_to.frame(iframes[-1])

    categoria = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'v-select__selections')]")
        )
    )
    driver.execute_script("arguments[0].click();", categoria)

    documents_option = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'Documentos')]"))
    )
    documents_option.click()

    file_name_input = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//input[@aria-label='Nome do Arquivo']")
        )
    )
    file_name_input.send_keys(final_name)

    upload_input = wait.until(
        EC.presence_of_element_located((By.ID, "file"))
    )
    upload_input.send_keys(destination_path)

    time.sleep(2)

    print("\n" + "=" * 44)
    print(f"  MONITORADO : {cleaned_name}")
    print(f"  ARQUIVO    : {final_name}")
    print(f"  DESTINO    : {destination_path}")
    print("=" * 44)

    confirmacao = input("  Confirmar upload? (S/N): ").strip().upper()
    print("=" * 44)

    if confirmacao != "S":
        print("  Upload cancelado.\n")
        driver.switch_to.default_content()
        driver.get("https://se.synergye.com.br/index.php?r=pessoa")
        return

    save_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(@class,'v-btn__content')]")
        )
    )
    save_btn.click()

    time.sleep(2)

    driver.switch_to.default_content()
    driver.get("https://se.synergye.com.br/index.php?r=pessoa")
    time.sleep(2)