import os
import re
import shutil
import time
import logging

from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    WebDriverException,
)

from selenium_navigation import searching_monitored

# Extração de nome pelo nome do arquivo

_TIPOS_DOCUMENTAIS = [
    r"TERMO\s+DE\s+SUBSTITUI[CÇ][ÃA]O",
    r"TERMO\s+DE\s+DEVOLU[CÇ][ÃA]O",
    r"TERMO\s+DE\s+DECLARA[CÇ][ÃA]O",
    r"DECLARA[CÇ][ÃA]O\s+DE\s+PERDA\s+DE\s+DISPOSITIVO",
    r"MANDADO\s+DE\s+PRIS[ÃA]O",
    r"ALVAR[AÁ]\s+DE\s+SOLTURA",
    r"BOLETIM\s+DE\s+OCORR[EÊ]NCIA",
    r"PERDA\s+DISPOSITIVO",
    r"ALVARA",
    r"ALVARÁ",
    r"TERMO",
    r"B\.O",
    r"CNH",
    r"RG",
    r"BO",
]

_PADROES_DATA = [
    r"\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}",
    r"\d{1,2}\s+de\s+\w+\s+de\s+\d{4}",
    r"\d{4}",
]

_RE_TIPOS = re.compile(
    r"^\s*(?:" + "|".join(_TIPOS_DOCUMENTAIS) + r")\s*[-–—]?\s*",
    re.IGNORECASE | re.UNICODE,
)
_RE_DATA_FINAL = re.compile(
    r"\s*[-–—]?\s*(?:" + "|".join(_PADROES_DATA) + r")\s*$",
    re.IGNORECASE | re.UNICODE,
)


def extract_name_from_filename(filename: str) -> str | None:
    name = os.path.splitext(filename)[0].upper().strip()
    name = _RE_TIPOS.sub("", name).strip()
    name = re.sub(r"^[-–—\s]+", "", name).strip()
    for _ in range(3):
        new_name = _RE_DATA_FINAL.sub("", name).strip()
        new_name = re.sub(r"[-–—\s]+$", "", new_name).strip()
        if new_name == name:
            break
        name = new_name
    name = re.sub(r"\s{2,}", " ", name).strip()
    return name if name else None


# Retry automático do Chronos
_MAX_TENTATIVAS = 3
_ESPERA_RETRY   = 5


def chronos_with_retry(driver, wait, cleaned_name, final_name, destination_path, logger):
    excecoes_retentaveis = (
        TimeoutException,
        ElementClickInterceptedException,
        WebDriverException,
    )

    for tentativa in range(1, _MAX_TENTATIVAS + 1):
        try:
            logger.debug(f"Chronos tentativa {tentativa}/{_MAX_TENTATIVAS}: {final_name}")
            searching_monitored(driver, wait, cleaned_name, final_name, destination_path)
            logger.info(f"Chronos OK: {final_name}")
            return True

        except excecoes_retentaveis as e:
            logger.warning(f"Chronos falha temporária (tentativa {tentativa}): {e}")
            if tentativa < _MAX_TENTATIVAS:
                print(f"  ↻  Tentativa {tentativa} falhou, aguardando {_ESPERA_RETRY}s...")
                time.sleep(_ESPERA_RETRY)
                try:
                    driver.get("https://se.synergye.com.br/index.php?r=pessoa")
                    time.sleep(2)
                except Exception:
                    pass
            else:
                logger.error(f"Chronos esgotado: {final_name} | {e}")
                print(f"  ✗  Chronos falhou após {_MAX_TENTATIVAS} tentativas.")
                return False

        except Exception as e:
            logger.error(f"Chronos erro inesperado: {e}")
            return False

    return False


# Helpers internos
def _find_folder(cleaned_name, base_dir, normalize_fn, match_name_fn):
    for root, dirs, _ in os.walk(base_dir):
        for folder in dirs:
            if match_name_fn(cleaned_name, folder):
                return os.path.join(root, folder)
    return None


def _safe_move(src, dest_dir):
    filename  = os.path.basename(src)
    dest_path = os.path.join(dest_dir, filename)
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(filename)
        c = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(dest_dir, f"{base}_{c}{ext}")
            c += 1
    shutil.move(src, dest_path)
    return dest_path


# Processamento de um único arquivo MANUA
def process_manual_file(pdf_path, driver, wait, base_bd_dir,
                        normalize_fn, match_name_fn, fila, logger):
    filename = os.path.basename(pdf_path)
    sep = "─" * 44

    print(f"\n{sep}")
    print(f"  Arquivo : {filename}")

    if filename in fila["pendentes"]:
        fila["pendentes"].remove(filename)
    fila["processando"].append(filename)

    try:
        name = extract_name_from_filename(filename)
        if not name:
            raise ValueError("Nome não pôde ser extraído do arquivo.")

        logger.info(f"Arquivo: {filename} | Nome: {name}")
        print(f"  Nome    : {name}")

        cleaned_name = re.sub(r'[\\/*?:"<>|]', "", name)

        folder = _find_folder(cleaned_name, base_bd_dir, normalize_fn, match_name_fn)
        if not folder:
            raise FileNotFoundError(f"Pasta de '{cleaned_name}' não encontrada no BD.")

        logger.info(f"Pasta encontrada: {folder}")
        print(f"  Pasta   : {folder}")

        dest = _safe_move(pdf_path, folder)
        final_name = os.path.basename(dest)
        logger.info(f"Movido: {dest}")
        print(f"  Movido  : {dest}")

        logger.info(f"Enviando para Chronos: {final_name}")
        ok = chronos_with_retry(driver, wait, cleaned_name, final_name, dest, logger)

        if ok:
            logger.info(f"Concluído: {filename}")
            fila["processando"].remove(filename)
            fila["concluidos"].append(filename)
        else:
            raise RuntimeError("Chronos falhou após todas as tentativas.")

    except Exception as e:
        logger.error(f"Erro em '{filename}': {e}")
        print(f"  ERRO    : {e}")
        if filename in fila["processando"]:
            fila["processando"].remove(filename)
        fila["erros"].append(filename)
        try:
            driver.get("https://se.synergye.com.br/index.php?r=pessoa")
        except Exception:
            pass


# Loop principal do MANUAL

def run_manual_mode(driver, wait, manual_dir, base_bd_dir,
                    normalize_fn, match_name_fn, logger):
    pdf_files = [f for f in os.listdir(manual_dir) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print("\n  Nenhum arquivo PDF encontrado na pasta MANUAL.")
        logger.info("MANUAL: pasta vazia.")
        return {"pendentes": [], "processando": [], "concluidos": [], "erros": []}

    fila = {
        "pendentes"  : list(pdf_files),
        "processando": [],
        "concluidos" : [],
        "erros"      : [],
    }

    print(f"  {len(pdf_files)} arquivo(s) na fila.\n")
    logger.info(f"MANUAL: {len(pdf_files)} arquivo(s) na fila.")

    for filename in pdf_files:
        process_manual_file(
            pdf_path     = os.path.join(manual_dir, filename),
            driver       = driver,
            wait         = wait,
            base_bd_dir  = base_bd_dir,
            normalize_fn = normalize_fn,
            match_name_fn= match_name_fn,
            fila         = fila,
            logger       = logger,
        )

    return fila