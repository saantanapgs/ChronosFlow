import os
import re
import shutil
import logging
import unicodedata
import time

from pdf2image import convert_from_path
from extract_data import extract_data, clean_text
from selenium_navigation import chronos_login, searching_monitored
from manual_mode import run_manual_mode, chronos_with_retry
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Logs

def setup_logging() -> logging.Logger:
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(logs_dir, exist_ok=True)

    logger = logging.getLogger("CEMEP")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    # Formatacao do arquivo
    fh = logging.FileHandler(
        os.path.join(logs_dir, "processamento.log"), encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)-7s — %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
    ))

    # Console
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("  ⚠  %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


#  Menu de execução

def show_menu() -> str:
    print("\n=================================")
    print("  1 - Processar SCAN")
    print("  2 - Processar MANUAL")
    print("=================================")
    while True:
        escolha = input("  Escolha: ").strip()
        if escolha in ("1", "2"):
            return escolha
        print("  Opção inválida. Digite 1 ou 2.")


# Fila de processamento

def build_queue(files: list) -> dict:
    return {
        "pendentes": list(files),
        "processando": [],
        "concluidos": [],
        "erros": [],
    }


def print_summary(fila: dict) -> None:
    total = sum(len(v) for v in fila.values())
    print("\n" + "=" * 34)
    print("  RESUMO FINAL")
    print("=" * 34)
    print(f"  Total      : {total}")
    print(f"  Concluídos : {len(fila['concluidos'])}")
    print(f"  Erros      : {len(fila['erros'])}")
    if fila["erros"]:
        print("\n  Arquivos com erro:")
        for f in fila["erros"]:
            print(f"    • {f}")
    print("=" * 34 + "\n")


# Normalização e busca (mantidas idênticas ao original)

def normalize(text):
    text = text.upper()
    import unicodedata as ud
    text = ud.normalize("NFKD", text)
    text = text.encode("ASCII", "ignore").decode("ASCII")
    return " ".join(text.split())


def match_name(name, folder):
    return normalize(name) in normalize(folder)


# Caminhos

directory  = r"C:\Program Files\automatization_scan_project\Scan_TESTE"
manual_dir = r"C:\Program Files\automatization_scan_project\MANUAL"
base_dir   = r"C:\Program Files\automatization_scan_project\MONITORAMENTO\MONITORADOS\ATIVOS"

os.makedirs(manual_dir, exist_ok=True)

# MAIN
if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Sistema iniciado")

    escolha = show_menu()

    print("\n  Abrindo navegador...\n")
    driver, wait = chronos_login()

    # MODO MANUAL 
    if escolha == "2":
        logger.info("Modo MANUAL iniciado")

        fila = run_manual_mode(
            driver=driver,
            wait=wait,
            manual_dir=manual_dir,
            base_bd_dir=base_dir,
            normalize_fn=normalize,
            match_name_fn=match_name,
            logger=logger,
        )

    # MODO SCAN  
    else:
        logger.info("Modo SCAN iniciado")

        pdf_files = [f for f in os.listdir(directory) if f.lower().endswith(".pdf")]
        fila = build_queue(pdf_files)

        for files in pdf_files:
            pdf_path = os.path.join(directory, files)
            logger.info(f"Arquivo: {files}")

            sep = "─" * 44
            print(f"\n{sep}")
            print(f"  Arquivo : {files}")

            fila["pendentes"].remove(files)
            fila["processando"].append(files)

            try:
                images = convert_from_path(pdf_path)
            except Exception as e:
                logger.error(f"Erro ao abrir PDF: {files} | {e}")
                print(f"  ERRO ao abrir o arquivo.")
                fila["processando"].remove(files)
                fila["erros"].append(files)
                continue

            full_text = ""
            for img in images:
                try:
                    img = img.convert("RGB")
                    full_text += pytesseract.image_to_string(img, lang="por") + "\n"
                except Exception as e:
                    logger.warning(f"Erro no OCR: {files} | {e}")

            cleaned_text = clean_text(full_text)
            file_type, name, date = extract_data(cleaned_text)

            print(f"  Tipo    : {file_type}")

            original_name = os.path.basename(pdf_path)

            if name:
                new_file_name = f"{file_type.upper()} - {name}"
                if date and date != ".":
                    new_file_name += f" - {date}"
                new_file_name = re.sub(r'[\\/*?:"<>|]', "", new_file_name)
                final_name = f"{new_file_name}.pdf"
            else:
                print(f"  Nome não identificado — mantendo nome original.")
                final_name = original_name

            final_path = os.path.join(directory, final_name)
            counter = 1
            base_sem_ext, ext = os.path.splitext(final_name)
            while os.path.exists(final_path):
                final_name = f"{base_sem_ext} ({counter}){ext}"
                final_path = os.path.join(directory, final_name)
                counter += 1

            os.rename(pdf_path, final_path)
            print(f"  Renome  : {final_name}")

            if not name:
                destino = os.path.join(manual_dir, os.path.basename(final_path))
                c = 1
                while os.path.exists(destino):
                    b, e = os.path.splitext(os.path.basename(final_path))
                    destino = os.path.join(manual_dir, f"{b}_{c}{e}")
                    c += 1
                shutil.move(final_path, destino)
                logger.info(f"Movido para MANUAL: {destino}")
                print(f"  → MANUAL: {destino}")
                fila["processando"].remove(files)
                fila["erros"].append(files)
                continue

            cleaned_name = re.sub(r'[\\/*?:"<>|]', "", name)

            folder_found = None
            for root, dirs, _ in os.walk(base_dir):
                for folder in dirs:
                    if match_name(cleaned_name, folder):
                        folder_found = os.path.join(root, folder)
                        break
                if folder_found:
                    break

            if not folder_found:
                logger.warning(f"Pasta não encontrada: {cleaned_name}")
                print(f"  AVISO: pasta de '{cleaned_name}' não encontrada no BD.")
                fila["processando"].remove(files)
                fila["erros"].append(files)
                continue

            logger.info(f"Pasta encontrada: {folder_found}")
            print(f"  Pasta   : {folder_found}")

            dest_path = os.path.join(folder_found, os.path.basename(final_path))
            c2 = 1
            b2, e2 = os.path.splitext(os.path.basename(final_path))
            while os.path.exists(dest_path):
                dest_path = os.path.join(folder_found, f"{b2} {c2}{e2}")
                c2 += 1

            shutil.move(final_path, dest_path)
            logger.info(f"Arquivo movido: {dest_path}")
            print(f"  Movido  : {dest_path}")

            logger.info(f"Enviando para Chronos: {final_name}")
            sucesso = chronos_with_retry(
                driver, wait, cleaned_name, final_name, dest_path, logger
            )

            if sucesso:
                logger.info(f"Concluído: {files}")
                fila["processando"].remove(files)
                fila["concluidos"].append(files)
            else:
                logger.error(f"Falha no Chronos: {files}")
                fila["processando"].remove(files)
                fila["erros"].append(files)
                driver.get("https://se.synergye.com.br/index.php?r=pessoa")

    print_summary(fila)
    logger.info("Sistema encerrado")
    driver.quit()