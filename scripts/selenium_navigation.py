from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from login_credentials import user, password
import time

#print("Acessando o site")
def chronos_login():
    # Definindo o navegador
    options = Options()
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    service = Service(
        r"C:\Users\Cemep.sejuc\.cache\selenium\chromedriver\win64\149.0.7827.55\chromedriver.exe"
    )

    #print("Iniciando o navegador")

    driver = webdriver.Chrome(
        service=service,
        options=options
    )

    #print("Navegador criado")

    # Adicionando um delay para realizar cada passo da automação
    wait = WebDriverWait(driver, 10)

    #print("Acessando o site")

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

# Pesquisando o nome do monitorado que consta no arquivo renomeado pelo main.py
def searching_monitored(driver, wait, cleaned_name, final_name, destination_path):
    import time

    # Volta para o conteúdo principal
    driver.switch_to.default_content()

    # Campo de pesquisa
    monitored_name_reference = wait.until(
        EC.element_to_be_clickable((By.ID, "Pessoa_pessoa_nome"))
    )

    # Limpa pesquisa anterior
    monitored_name_reference.click()
    monitored_name_reference.send_keys(Keys.CONTROL, "a")
    monitored_name_reference.send_keys(Keys.BACKSPACE)

    # Pesquisa novo monitorado
    monitored_name_reference.send_keys(cleaned_name)
    monitored_name_reference.send_keys(Keys.ENTER)

    print(f"Pesquisando: {cleaned_name}")

    # Aguarda atualização da tabela
    time.sleep(3)

    # Aguarda aparecer algum botão View
    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//a[contains(@class,'view')]")
        )
    )

    # Pega todos os botões View encontrados
    views = driver.find_elements(
        By.XPATH,
        "//a[contains(@class,'view')]"
    )

    print(f"Views encontradas: {len(views)}")

    if len(views) == 0:
        print(f"Nenhum resultado encontrado para {cleaned_name}")
        return

    # Clica na primeira View retornada pela pesquisa
    driver.execute_script(
        "arguments[0].click();",
        views[0]
    )

    # Aba Arquivos
    files_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//a[@href='#arquivoPessoaTab']")
        )
    )
    files_btn.click()

    # Botão Novo
    new_file_btn = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//input[contains(@onclick,'openFileModal')]"
            )
        )
    )
    new_file_btn.click()

    time.sleep(2)

    # Entra no iframe do modal
    iframes = wait.until(
        EC.presence_of_all_elements_located(
            (By.TAG_NAME, "iframe")
        )
    )

    driver.switch_to.frame(iframes[-1])

    # Categoria
    categoria = wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//div[contains(@class,'v-select__selections')]"
            )
        )
    )

    driver.execute_script(
        "arguments[0].click();",
        categoria
    )

    # Documentos
    documents_option = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//*[contains(text(),'Documentos')]"
            )
        )
    )

    documents_option.click()

    # Nome do arquivo
    file_name_input = wait.until(
        EC.visibility_of_element_located(
            (
                By.XPATH,
                "//input[@aria-label='Nome do Arquivo']"
            )
        )
    )

    file_name_input.send_keys(final_name)

    # Upload
    upload_input = wait.until(
        EC.presence_of_element_located(
            (By.ID, "file")
        )
    )

    upload_input.send_keys(destination_path)

    time.sleep(2)

    # Salvar
    save_btn = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//div[contains(@class,'v-btn__content')]"
            )
        )
    )

    save_btn.click()

    time.sleep(2)

    # Sai do iframe
    driver.switch_to.default_content()

    # Volta para pesquisa de monitorados
    driver.get(
        "https://se.synergye.com.br/index.php?r=pessoa"
    )

    time.sleep(2)