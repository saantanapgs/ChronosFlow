import time
import threading

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from login_credentials import user, password


def chronos_login():
    options = Options()
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    wait   = WebDriverWait(driver, 10)

    driver.get("https://se.synergye.com.br/index.php?r=site/login")
    print("Site acessado")

    wait.until(EC.presence_of_element_located((By.ID, "LoginForm_username"))).send_keys(user)
    wait.until(EC.presence_of_element_located((By.ID, "LoginForm_password"))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit']"))).click()

    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//li[contains(@class,'dir')]//a[contains(., 'Operacional')]")
    )).click()

    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//a[@href='/index.php?r=pessoa']")
    )).click()

    return driver, wait


def _log(msg_queue, text):
    """Envia para a fila da GUI ou imprime no terminal."""
    if msg_queue is not None:
        msg_queue.put(("log", text))
    else:
        print(text)


def searching_monitored(driver, wait, cleaned_name, final_name,
                        destination_path, msg_queue=None):
    """
    Pesquisa o monitorado no Chronos, prepara o upload e solicita confirmação.
    Quando msg_queue é fornecido (GUI), a confirmação abre uma janela gráfica.
    Quando msg_queue é None (CMD), usa input() no terminal.
    """
    driver.switch_to.default_content()

    campo = wait.until(EC.element_to_be_clickable((By.ID, "Pessoa_pessoa_nome")))
    campo.click()
    campo.send_keys(Keys.CONTROL, "a")
    campo.send_keys(Keys.BACKSPACE)
    campo.send_keys(cleaned_name)
    campo.send_keys(Keys.ENTER)

    _log(msg_queue, f"Pesquisando: {cleaned_name}")

    time.sleep(6)

    linhas = driver.find_elements(By.XPATH, "//table//tr")
    monitorado_encontrado = False

    for linha in linhas:
        try:
            if cleaned_name.upper() in linha.text.upper():
                _log(msg_queue, "Monitorado localizado.")
                view_btn = linha.find_element(By.XPATH, ".//a[contains(@class,'view')]")
                driver.execute_script("arguments[0].click();", view_btn)
                monitorado_encontrado = True
                break
        except Exception:
            pass

    if not monitorado_encontrado:
        _log(msg_queue, f"ERRO: {cleaned_name} não encontrado na tabela.")
        driver.get("https://se.synergye.com.br/index.php?r=pessoa")
        return

    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//a[@href='#arquivoPessoaTab']")
    )).click()

    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//input[contains(@onclick,'openFileModal')]")
    )).click()

    time.sleep(2)

    iframes = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "iframe")))
    driver.switch_to.frame(iframes[-1])

    categoria = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//div[contains(@class,'v-select__selections')]")
    ))
    driver.execute_script("arguments[0].click();", categoria)

    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//*[contains(text(),'Documentos')]")
    )).click()

    wait.until(EC.visibility_of_element_located(
        (By.XPATH, "//input[@aria-label='Nome do Arquivo']")
    )).send_keys(final_name)

    wait.until(EC.presence_of_element_located((By.ID, "file"))).send_keys(destination_path)

    time.sleep(2)

    # ── Confirmação ───────────────────────────────────────────────────────────
    if msg_queue is not None:
        # GUI: envia evento para a fila e espera resposta do operador na janela
        event  = threading.Event()
        holder = {"result": False}
        msg_queue.put(("confirm", (cleaned_name, final_name, destination_path, event, holder)))
        event.wait()
        confirmado = holder["result"]
    else:
        # Terminal: input() clássico
        print("\n" + "=" * 44)
        print(f"  MONITORADO : {cleaned_name}")
        print(f"  ARQUIVO    : {final_name}")
        print(f"  DESTINO    : {destination_path}")
        print("=" * 44)
        confirmado = input("  Confirmar upload? (S/N): ").strip().upper() == "S"
        print("=" * 44)

    if not confirmado:
        _log(msg_queue, "Upload cancelado.")
        driver.switch_to.default_content()
        driver.get("https://se.synergye.com.br/index.php?r=pessoa")
        return

    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//div[contains(@class,'v-btn__content')]")
    )).click()

    time.sleep(2)
    driver.switch_to.default_content()
    driver.get("https://se.synergye.com.br/index.php?r=pessoa")
    time.sleep(2)