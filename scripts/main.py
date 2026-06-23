import os
import re
import shutil
import logging
import unicodedata
import time
from datetime import datetime

from pdf2image import convert_from_path
from extract_data import extract_data, clean_text
from selenium_navigation import chronos_login, searching_monitored
from manual_mode import run_manual_mode, chronos_with_retry
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Sistema de Logs

def setup_logging() -> logging.Logger:
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_file = os.path.join(logs_dir, "processamento.log")

    logger = logging.getLogger("CEMEP")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Handler para arquivo
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)

        # Handler para console
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)s — %(message)s",
            datefmt="%d/%m/%Y %H:%M:%S",
        )
        fh.setFormatter(fmt)
        ch.setFormatter(fmt)

        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


#  Menu de execução

def show_menu() -> str:
    print("\n=================================")
    print("1 - Processar SCAN")
    print("2 - Processar MANUAL")
    print("=================================")
    while True:
        escolha = input("Escolha: ").strip()
        if escolha in ("1", "2"):
            return escolha
        print("Opção inválida. Digite 1 ou 2.")


# Fila de processamento

def build_queue(files: list) -> dict:
    return {
        "pendentes": list(files),
        "processando": [],
        "concluidos": [],
        "erros": [],
    }


def print_summary(fila: dict) -> None:
    total = (
        len(fila["pendentes"])
        + len(fila["processando"])
        + len(fila["concluidos"])
        + len(fila["erros"])
    )
    print("\n==========================")
    print("RESUMO FINAL")
    print("==========================")
    print(f"Total      : {total}")
    print(f"Concluídos : {len(fila['concluidos'])}")
    print(f"Erros      : {len(fila['erros'])}")
    if fila["erros"]:
        print("\nArquivos com erro:")
        for f in fila["erros"]:
            print(f"  • {f}")
    print("==========================\n")


# Funções de normalização e busca

def normalize(text):
    text = text.upper()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ASCII", "ignore").decode("ASCII")
    text = " ".join(text.split())
    return text


def match_name(name, folder):
    name_norm = normalize(name)
    folder_norm = normalize(folder)
    return name_norm in folder_norm


# Caminhos
directory  = r"C:\Users\Cemep.sejuc\Documents\Cemep automatization\Scan_TESTE"
manual_dir = r"C:\Users\Cemep.sejuc\Documents\Cemep automatization\MANUAL"
base_dir   = r"\\Servidor1\d\MONITORAMENTO\MONITORADOS - BD\ATIVOS"

os.makedirs(manual_dir, exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), "..", "logs"), exist_ok=True)

# MAIN
if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Sistema iniciado")

    # Menu
    escolha = show_menu()

    # Login no Chronos 
    driver, wait = chronos_login()

    # MODO MANUAL 
    if escolha == "2":
        logger.info("Modo MANUAL")

        fila = run_manual_mode(
            driver=driver,
            wait=wait,
            manual_dir=manual_dir,
            base_bd_dir=base_dir,
            normalize_fn=normalize,
            match_name_fn=match_name,
            logger=logger,
        )

        print_summary(fila)
        driver.quit()

    # MODO SCAN_TESTE
    else:
        logger.info("Modo SCANTESTE")

        pdf_files = [f for f in os.listdir(directory) if f.lower().endswith(".pdf")]
        fila = build_queue(pdf_files)

        for files in pdf_files:
            pdf_path = os.path.join(directory, files)
            logger.info(f"Arquivo: {files}")
            print(f"\nProcessando o arquivo: {files}")

            # PROCESSANDO
            fila["pendentes"].remove(files)
            fila["processando"].append(files)

            try:
                images = convert_from_path(pdf_path)
            except Exception as e:
                logger.error(f"Erro ao abrir o arquivo: {files} | {e}")
                print(f"Erro ao abrir o arquivo: {files}")
                fila["processando"].remove(files)
                fila["erros"].append(files)
                continue

            full_text = ""
            for img in images:
                try:
                    img = img.convert("RGB")
                    file_content = pytesseract.image_to_string(img, lang="por")
                    full_text += file_content + "\n"
                except Exception as e:
                    logger.warning(f"Erro no OCR do arquivo: {files} | {e}")
                    print(f"Erro no OCR do arquivo: {files}")
                    continue

            cleaned_text = clean_text(full_text)
            file_type, name, date = extract_data(cleaned_text)

            print(f"Tipo: {file_type}")

            original_name = os.path.basename(pdf_path)

            if name:
                new_file_name = f"{file_type.upper()} - {name}"
                if date and date != ".":
                    new_file_name += f" - {date}"
                new_file_name = re.sub(r'[\\/*?:"<>|]', "", new_file_name)
                final_name = f"{new_file_name}.pdf"
            else:
                print(f"Nome não encontrado, mantendo nome original: {original_name}")
                final_name = original_name

            final_path = os.path.join(directory, final_name)
            counter = 1
            name_without_ext, ext = os.path.splitext(final_name)

            while os.path.exists(final_path):
                final_name = f"{name_without_ext} ({counter}){ext}"
                final_path = os.path.join(directory, final_name)
                counter += 1

            os.rename(pdf_path, final_path)
            print(f"Renomeado para: {final_name}")

            if not name:
                destino_manual = os.path.join(manual_dir, os.path.basename(final_path))
                contador = 1
                while os.path.exists(destino_manual):
                    nome_base, ext = os.path.splitext(os.path.basename(final_path))
                    destino_manual = os.path.join(manual_dir, f"{nome_base}_{contador}{ext}")
                    contador += 1

                shutil.move(final_path, destino_manual)
                print(f"Arquivo movido para análise manual: {destino_manual}")
                logger.info(f"Movido para MANUAL: {destino_manual}")

                fila["processando"].remove(files)
                fila["erros"].append(files)
                continue

            cleaned_name = re.sub(r'[\\/*?:"<>|]', "", name)

            folder_found = None
            for root, dirs, _ in os.walk(base_dir):
                for folder in dirs:
                    folder_path = os.path.join(root, folder)
                    if match_name(cleaned_name, folder):
                        folder_found = folder_path
                        break
                if folder_found:
                    break

            if folder_found:
                logger.info(f"Pasta encontrada: {folder_found}")
                file_name = os.path.basename(final_path)
                destination_path = os.path.join(folder_found, file_name)

                cont = 1
                name_without_ext2, ext2 = os.path.splitext(file_name)
                while os.path.exists(destination_path):
                    new_name = f"{name_without_ext2} {cont}{ext2}"
                    destination_path = os.path.join(folder_found, new_name)
                    cont += 1

                shutil.move(final_path, destination_path)
                logger.info(f"Arquivo movido: {destination_path}")
                print(f"Movido para: {destination_path}")

                # Retry no Chronos 
                logger.info(f"Envio para Chronos: {final_name}")
                sucesso = chronos_with_retry(
                    driver, wait, cleaned_name, final_name, destination_path, logger
                )

                if sucesso:
                    logger.info(f"Processamento concluído: {files}")
                    fila["processando"].remove(files)
                    fila["concluidos"].append(files)
                else:
                    logger.error(f"Falha no Chronos: {files}")
                    fila["processando"].remove(files)
                    fila["erros"].append(files)
                    driver.get("https://se.synergye.com.br/index.php?r=pessoa")

            else:
                logger.warning(f"Pasta não encontrada: {cleaned_name}")
                print(f"Pasta do monitorado(a): {cleaned_name} não encontrada.")
                fila["processando"].remove(files)
                fila["erros"].append(files)

        print_summary(fila)
        driver.quit()