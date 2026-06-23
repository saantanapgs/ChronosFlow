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

# Padrões de data para remover do final do nome
_PADROES_DATA = [
    r"\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}",   # 15.06.2026 / 15/06/26
    r"\d{1,2}\s+de\s+\w+\s+de\s+\d{4}",       # 15 de junho de 2026
    r"\d{4}",                                   # ano isolado
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
    """
    Extrai o nome do monitorado a partir do nome do arquivo.

    Exemplos:
        "RG - PEDRO SANTANA.pdf"              → "PEDRO SANTANA"
        "CNH - JOAO SILVA.pdf"                → "JOAO SILVA"
        "TERMO DE SUBSTITUIÇÃO - MARIA SOUZA - 15.06.2026.pdf" → "MARIA SOUZA"
    """
    # Remove extensão
    name = os.path.splitext(filename)[0]

    # Converte para maiúsculas para comparação uniforme
    name = name.upper().strip()

    # Remove tipo documental do início
    name = _RE_TIPOS.sub("", name).strip()

    # Remove separador inicial caso tenha sobrado
    name = re.sub(r"^[-–—\s]+", "", name).strip()

    # Remove data do final
    for _ in range(3):
        new_name = _RE_DATA_FINAL.sub("", name).strip()
        new_name = re.sub(r"[-–—\s]+$", "", new_name).strip()
        if new_name == name:
            break
        name = new_name

    # Remove espaços duplicados
    name = re.sub(r"\s{2,}", " ", name).strip()

    return name if name else None


# Retry automático do Chronos
_MAX_TENTATIVAS = 3
_ESPERA_RETRY = 5 


def chronos_with_retry(
    driver,
    wait,
    cleaned_name: str,
    final_name: str,
    destination_path: str,
    logger: logging.Logger,
) -> bool:
    """
    Tenta enviar o arquivo ao Chronos até _MAX_TENTATIVAS vezes.
    Retorna True em caso de sucesso, False após esgotar as tentativas.
    """
    excecoes_retentaveis = (
        TimeoutException,
        ElementClickInterceptedException,
        WebDriverException,
    )

    for tentativa in range(1, _MAX_TENTATIVAS + 1):
        try:
            logger.info(
                f"Chronos — tentativa {tentativa}/{_MAX_TENTATIVAS}: {final_name}"
            )
            searching_monitored(driver, wait, cleaned_name, final_name, destination_path)
            logger.info(f"Chronos — sucesso: {final_name}")
            return True

        except excecoes_retentaveis as e:
            logger.warning(
                f"Chronos — falha temporária (tentativa {tentativa}): {e}"
            )
            if tentativa < _MAX_TENTATIVAS:
                logger.info(f"Aguardando {_ESPERA_RETRY}s antes de nova tentativa...")
                time.sleep(_ESPERA_RETRY)
                try:
                    driver.get("https://se.synergye.com.br/index.php?r=pessoa")
                    time.sleep(2)
                except Exception:
                    pass
            else:
                logger.error(
                    f"Chronos — esgotadas as tentativas para: {final_name} | Erro: {e}"
                )
                return False

        except Exception as e:
            # Erro não retentável (ex.: operador cancelou)
            logger.error(f"Chronos — erro não retentável: {e}")
            return False

    return False


# Processamento de um arquivo MANUAL
def _find_folder_in_bd(cleaned_name: str, base_dir: str, normalize_fn, match_name_fn) -> str | None:
    """Reutiliza a mesma lógica de busca já existente no main.py."""
    folder_found = None
    for root, dirs, _ in os.walk(base_dir):
        for folder in dirs:
            if match_name_fn(cleaned_name, folder):
                folder_found = os.path.join(root, folder)
                break
        if folder_found:
            break
    return folder_found


def _safe_move(src: str, dest_dir: str) -> str:
    """
    Move src para dest_dir sem sobrescrever.
    Se o nome já existir, acrescenta _1, _2, ...
    Retorna o caminho de destino final.
    """
    filename = os.path.basename(src)
    dest_path = os.path.join(dest_dir, filename)

    if os.path.exists(dest_path):
        name_base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(dest_dir, f"{name_base}_{counter}{ext}")
            counter += 1

    shutil.move(src, dest_path)
    return dest_path


def process_manual_file(
    pdf_path: str,
    driver,
    wait,
    base_bd_dir: str,
    normalize_fn,
    match_name_fn,
    fila: dict,
    logger: logging.Logger,
) -> None:
    """
    Processa um único arquivo do fluxo MANUAL.
    Atualiza a fila e registra logs.
    """
    filename = os.path.basename(pdf_path)
    logger.info(f"Arquivo: {filename}")

    # Marca como PROCESSANDO
    if filename in fila["pendentes"]:
        fila["pendentes"].remove(filename)
    fila["processando"].append(filename)

    try:
        # Extrai nome do arquivo (sem OCR)
        name = extract_name_from_filename(filename)
        logger.info(f"Nome extraído: {name}")
        print(f"\n[MANUAL] Arquivo : {filename}")
        print(f"[MANUAL] Nome    : {name}")

        if not name:
            raise ValueError("Não foi possível extrair o nome do arquivo.")

        cleaned_name = re.sub(r'[\\/*?:"<>|]', "", name)

        # Busca pasta no BD
        folder_found = _find_folder_in_bd(
            cleaned_name, base_bd_dir, normalize_fn, match_name_fn
        )

        if not folder_found:
            raise FileNotFoundError(
                f"Pasta do monitorado '{cleaned_name}' não encontrada no BD."
            )

        logger.info(f"Pasta encontrada: {folder_found}")
        print(f"[MANUAL] Pasta   : {folder_found}")

        # Move o arquivo
        destination_path = _safe_move(pdf_path, folder_found)
        final_name = os.path.basename(destination_path)

        logger.info(f"Arquivo movido: {destination_path}")
        print(f"[MANUAL] Movido  : {destination_path}")

        # Envia para o Chronos (com retry)
        logger.info(f"Envio para Chronos: {final_name}")
        sucesso = chronos_with_retry(
            driver, wait, cleaned_name, final_name, destination_path, logger
        )

        if sucesso:
            logger.info(f"Processamento concluído: {filename}")
            fila["processando"].remove(filename)
            fila["concluidos"].append(filename)
        else:
            raise RuntimeError("Falha no envio ao Chronos após todas as tentativas.")

    except Exception as e:
        logger.error(f"Erro: {e}")
        print(f"[MANUAL] ERRO    : {e}")

        if filename in fila["processando"]:
            fila["processando"].remove(filename)
        fila["erros"].append(filename)

        # Retorna ao ponto de pesquisa do Chronos para não travar o fluxo
        try:
            driver.get("https://se.synergye.com.br/index.php?r=pessoa")
        except Exception:
            pass


# Loop principal do MODO MANUAL
def run_manual_mode(
    driver,
    wait,
    manual_dir: str,
    base_bd_dir: str,
    normalize_fn,
    match_name_fn,
    logger: logging.Logger,
) -> dict:
    """
    Processa todos os PDFs da pasta MANUAL.
    Retorna a fila final com os estados de cada arquivo.
    """
    pdf_files = [
        f for f in os.listdir(manual_dir) if f.lower().endswith(".pdf")
    ]

    if not pdf_files:
        print("\n[MANUAL] Nenhum arquivo PDF encontrado na pasta MANUAL.")
        logger.info("MANUAL: Nenhum arquivo encontrado.")
        return {"pendentes": [], "processando": [], "concluidos": [], "erros": []}

    fila = {
        "pendentes": list(pdf_files),
        "processando": [],
        "concluidos": [],
        "erros": [],
    }

    logger.info(f"MANUAL: {len(pdf_files)} arquivo(s) na fila.")
    print(f"\n[MANUAL] {len(pdf_files)} arquivo(s) encontrado(s).\n")

    for filename in pdf_files:
        pdf_path = os.path.join(manual_dir, filename)
        process_manual_file(
            pdf_path=pdf_path,
            driver=driver,
            wait=wait,
            base_bd_dir=base_bd_dir,
            normalize_fn=normalize_fn,
            match_name_fn=match_name_fn,
            fila=fila,
            logger=logger,
        )

    return fila