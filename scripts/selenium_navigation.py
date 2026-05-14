from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from login_credentials import user, password
import time

#print("Acessando o site")
def chronos_login():
  # Definindo o navegador
  options = Options()
  options.add_argument(r"--user-data-dir=C:\selenium_profile")
  driver = webdriver.Chrome(options=options)

  # Adicionando um delay para realizar cada passo da automação
  wait = WebDriverWait(driver, 10)

  driver.get("https://se.synergye.com.br/index.php?r=site/login")

  login_user = wait.until(
    EC.presence_of_element_located((By.ID, "LoginForm_username"))
  )
  login_user.send_keys(user)

  login_password = wait.until(
    EC.presence_of_element_located((By.ID, "LoginForm_password"))
  )
  login_password.send_keys(password)

  login_btn = wait.until(
      EC.element_to_be_clickable((By.XPATH,"//input[@type='submit']"))
  )
  login_btn.click()

  # Entrando no menu Operacional para acessar o link 'Pessoa monitorada'
  operational_reference = wait.until(
      EC.element_to_be_clickable((By.XPATH, "//li[contains(@class,'dir')]//a[contains(., 'Operacional')]"))
  )
  operational_reference.click()

  monitored_reference = wait.until(
      EC.element_to_be_clickable((By.XPATH, "//a[@href='/index.php?r=pessoa']"))
  )
  monitored_reference.click()

  return driver, wait
# Pesquisando o nome do monitorado que consta no arquivo renomeado pelo main.py
def searching_monitored(driver, wait, cleaned_name, final_name, destination_path):
  # Voltando para o default Iframe para evitar erros
  driver.switch_to.default_content()

  monitored_name_reference = wait.until(
      EC.element_to_be_clickable((By.ID, "Pessoa_pessoa_nome"))
  )
  monitored_name_reference.send_keys(cleaned_name)
  monitored_name_reference.send_keys(Keys.ENTER)
  time.sleep(2)
  

  # Esperando a tabela atualizar
  wait.until(
    EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'view')]"))
  )
  # Clicando no botão para abrir o perfil do monitorado
  view_btn = wait.until(
    EC.element_to_be_clickable((By.XPATH, "//a[contains(@class,'view')]"))
  )
  time.sleep(2)
  view_btn.click()
  
  # Clicando na sessão de 'Arquivos'
  files_btn = wait.until(
    EC.element_to_be_clickable((By.XPATH, "//a[@href='#arquivoPessoaTab']"))
  )
  files_btn.click()

  # Clicando para criar novo arquivo
  new_file_btn = wait.until(
      EC.element_to_be_clickable((By.XPATH, "//input[contains(@onclick, 'openFileModal')]"))
  )
  new_file_btn.click()

  # Adicionando delay após clicar em 'Novo'
  time.sleep(2)

  # Entrando no iframe
  iframes = wait.until(
    EC.presence_of_all_elements_located((By.TAG_NAME, "iframe"))
  )
  driver.switch_to.frame(iframes[-1])

  # Abrindo select
  categoria = wait.until(
      EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'v-select__selections')]"))
  )
  
  time.sleep(2)
  driver.execute_script("arguments[0].click();", categoria)

  # Selecionando Documentos
  documents_option = wait.until(
      EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Documentos')]"))
  )

  documents_option.click()

  # Digitando nome do arquivo
  file_name_input = wait.until(
      EC.visibility_of_element_located((By.XPATH, "//input[@aria-label='Nome do Arquivo']"))
  )

  file_name_input.send_keys(final_name)

  upload_input = wait.until(
    EC.presence_of_element_located((By.ID, "file"))
  )

  upload_input.send_keys(destination_path)

  time.sleep(2)
  save_btn = wait.until(
    EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'v-btn__content')]"))
  )
  save_btn.click()

  driver.switch_to.default_content()

  driver.get("https://se.synergye.com.br/index.php?r=pessoa")