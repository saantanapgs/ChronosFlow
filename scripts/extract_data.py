import re 

# Função para limpar o texto extraido
def clean_text(file_content):
    file_content = file_content.upper()
    file_content = file_content.replace("\n", " ")
    file_content = re.sub(r"\s+", " ", file_content)
    return file_content

# Detectando o tipo do arquivo
def detect_file_type(file_content):
    file_content = file_content.upper()
    file_start = file_content[:500]

    if re.search(r"BOLETIM\s+DE\s+OCORR", file_start):
        return "BO"

    elif re.search(r"PERDA\s+DO\s+DISPOSITIVO", file_start):
        return "PERDA_DISPOSITIVO"
    
    elif "SUBSTITUI" in file_start:
        return "TERMO_SUBSTITUICAO"
    
    elif "DEVOLU" in file_start:
        return "TERMO_DEVOLUCAO"
    
    elif "DECLARA" in file_start:
        return "TERMO_DECLARACAO"
    
    elif re.search(r"MANDADO\s+DE\s+PRIS", file_start):
        return "MANDADO"
    
    elif "ALVAR" in file_start:
        return "ALVARA"

    elif (r"CARTEIRA\sDE\sIDENTIDADE", file_start):
        return "RG"
    
    elif re.search(r"DE\s+HABILITA", file_start):
        return "CNH"
    
    else:
        return "Unknow"
    
# TERMOS DE SUBSTITUICAO/DECLARACAO/DEVOLUCAO
def extract_termo(file_content):
    months = {
        "janeiro": "01", "fevereiro": "02", "marco": "03", "abril": "04", "maio": "05","junho": "06",
        "julho": "07", "agosto": "08", "setembro": "09", "outubro": "10","novembro": "11", "dezembro": "12"
    }
    # Tipo do termo
    if "SUBSTITUI" in file_content:
        file_type = "Termo de substituição"
    elif "DEVOLU" in file_content:
        file_type = "Termo de devolução"
    else:
        file_type = "Termo de declaração"

    # Extraindo a data emitida no arquivo
    date_match = re.search(
        r"(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4})",
        file_content.lower())
    
    date = date_match.group(0) if date_match else None

    if date_match:
        day, written_month,year = date_match.groups()
        month = months.get(written_month, "00")
        date = f"{day.zfill(2)}.{month}.{year}"
    else:
        date = "."

    # Nome do monitorado/vítima
    name_match = re.search(
        r"MONITORADO[:\-]?\s*([A-Z\s]+)(?:PROCESSO|$)",
        file_content)
    
    name = name_match.group(1).strip() if name_match else None

    if name:
        name = name.split("PROCESSO")[0].strip()

    return file_type, name, date

# REGISTRO GERAL
def extract_rg(file_content):
    # Normaliza quebras de linha
    text = file_content.upper()

    # Procura o texto logo abaixo de NOME/NAME
    name_match = re.search(
        r"NOME\s*/?\s*NAME\s*\n+([A-ZÀ-Ú\s]+)",
        text,
        re.MULTILINE
    )

    if not name_match:
        # Fallback para casos em que o OCR remove a quebra de linha
        name_match = re.search(
            r"NOME\s*/?\s*NAME\s*([A-ZÀ-Ú\s]{5,})",
            text
        )

    name = None

    if name_match:
        name = " ".join(name_match.group(1).split())

        # Remove linhas que claramente não são nomes
        palavras_invalidas = [
            "FILIACAO",
            "FILIATION",
            "NATURALIDADE",
            "NASCIMENTO",
            "SEXO",
            "CPF",
            "RG",
            "DOC",
            "VALIDADE"
        ]

        for palavra in palavras_invalidas:
            if palavra in name:
                name = name.split(palavra)[0].strip()

    return "RG", name, "."

# CARTEIRA NACIONAL DE HABILITACAO
def extract_cnh(file_content):
    name_match = re.search(r"NOME[:\-]?\s*([A-Z\s]+)", file_content)
    name = name_match.group(1).strip() if name_match else None

    return "CNH", name, "."

# ALVARA DE SOLTURA
def extract_alvara(file_content):
    months = {
        "janeiro": "01", "fevereiro": "02", "marco": "03", "abril": "04", "maio": "05","junho": "06",
        "julho": "07", "agosto": "08", "setembro": "09", "outubro": "10","novembro": "11", "dezembro": "12"
    }

    date_match = re.search(
        r"(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4})",
        file_content.lower())
    
    date = date_match.group(0) if date_match else None

    if date_match:
        day, written_month,year = date_match.groups()
        month = months.get(written_month, "00")
        date = f"{day.zfill(2)}.{month}.{year}"
    else:
        date = "."

    name_match = re.search(r"PESSOA[:\-]?\s*([A-Z\s]+)(?:CPF|$)", file_content)
    name = name_match.group(1).strip() if name_match else None

    return "Alvará de Soltura", name, date

def extract_perda_dispositivo(file_content):
    months = {
        "janeiro": "01", "fevereiro": "02", "marco": "03", "abril": "04", "maio": "05","junho": "06",
        "julho": "07", "agosto": "08", "setembro": "09", "outubro": "10","novembro": "11", "dezembro": "12"
    }
    name_match = re.search(r"EU[,\-]?\s*([A-Z\s]+)(?:,|$   )", file_content)
    name = name_match.group(1).strip() if name_match else None

    data_match = re.search(
        r"(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4})", 
        file_content.lower())
    date = data_match.group(0) if data_match else None

    if data_match:
        day, written_month, year = data_match.groups()
        month = months.get(written_month, "00")
        date = f"{day.zfill(2)}.{month}.{year}"
    else:
        date = "."

    return "Declaração de perda de dispositivo", name, date

# BOLETIM DE OCORRENCIA
def extract_bo(file_content):
    months = {
        "janeiro": "01", "fevereiro": "02", "marco": "03", "abril": "04", "maio": "05","junho": "06",
        "julho": "07", "agosto": "08", "setembro": "09", "outubro": "10","novembro": "11", "dezembro": "12"
    }

    date_match = re.search(
        r"(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4})",
        file_content.lower())
    
    date = date_match.group(0) if date_match else None

    if date_match:
        day, written_month,year = date_match.groups()
        month = months.get(written_month, "00")
        date = f"{day.zfill(2)}.{month}.{year}"
    else:
        date = "."

    # Nome do monitorado/vítima
    name_match = re.search(
        r"CIVIL[:\-]?\s*([A-Z\s]+?)(?:\(|$)",
        file_content
    )
    name = name_match.group(1).strip() if name_match else None

    if name:
        name = name.split("(")[0].strip()

    return "B.O", name, date

def extract_mandado(file_content):
    
    name_match = re.search(r"PESSOA[:\-]?\s*([A-Z\s]+)(?:CPF|$)", file_content)
    name = name_match.group(1).strip() if name_match else None

    return "Mandado de prisão", name, "."

# MAIN FUNCTION
def extract_data(file_content):
    doc_type = detect_file_type(file_content)

    if doc_type in ["TERMO_SUBSTITUICAO", "TERMO_DEVOLUCAO", "TERMO_DECLARACAO"]:
        return extract_termo(file_content)
    
    elif doc_type == "RG":
        return extract_rg(file_content)
    
    elif doc_type == "CNH":
        return extract_cnh(file_content)
    
    elif doc_type == "ALVARA":
        return extract_alvara(file_content)
    
    elif doc_type == "PERDA_DISPOSITIVO":
        return extract_perda_dispositivo(file_content)
    
    elif doc_type == "BO":
        return extract_bo(file_content)
    
    elif doc_type == "MANDADO":
        return extract_mandado(file_content)
    
    else:
        return "Arquivo nao suportado", None, None
    
