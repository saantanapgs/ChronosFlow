import os
import re
import shutil
import unicodedata
from pdf2image import convert_from_path
from extract_data import extract_data, clean_text
from selenium_navigation import chronos_login, searching_monitored
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Função para 'normalizar' o nome do monitorado quando pesquisar no BD
def normalize(text):
    text = text.upper()
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ASCII', 'ignore').decode('ASCII')
    text = " ".join(text.split())
    return text

def match_name(name, folder):
    name_norm = normalize(name)
    folder_norm = normalize(folder) 

    return name_norm in folder_norm

#directory = r"C:\Users\Cemep.sejuc\Downloads\CEMEP-main\Scan"
directory = r"C:\Users\Cemep.sejuc\Documents\Cemep automatization\Scan_TESTE"

# Redirecionando para o site 'Synergye Chronos SE'
driver, wait = chronos_login()

for files in os.listdir(directory):
    if files.lower().endswith(".pdf"):
        pdf_path = os.path.join(directory, files)
        print(f"\nProcessando o arquivo: {files}")

        try:
            images = convert_from_path(pdf_path)
        except:
            print(f"Erro ao abrir o arquivo: {files}")
            continue

        full_text = ""

        for img in images:
            try:
                img = img.convert("RGB")  
                file_content = pytesseract.image_to_string(img, lang="por")
                full_text += file_content + "\n"
            except:
                print(f"Erro no OCR do arquivo: {files}")
                continue

        cleaned_text = clean_text(full_text)

        #print("==================================")
        #print(full_text)
        #print("==================================")

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
            print("Arquivo sem nome identificado, pulando movimentação.")
            continue

        cleaned_name = re.sub(r'[\\/*?:"<>|]', "", name)

        base_dir = r"\\Servidor1\d\MONITORAMENTO\MONITORADOS - BD\ATIVOS"
        
        folder_found = None

        for root, dirs, files in os.walk(base_dir):
            for folder in dirs:
                folder_path = os.path.join(root, folder)

                if match_name(cleaned_name, folder):
                    folder_found = folder_path
                    break

            if folder_found:
                break

        if folder_found:
            file_name = os.path.basename(final_path)
            destination_path = os.path.join(folder_found, file_name)

            cont = 1
            name_whitout_ext, ext = os.path.splitext(file_name)

            while os.path.exists(destination_path):
                new_name = f"{name_whitout_ext} {cont}{ext}"
                destination_path = os.path.join(folder_found, new_name)
                cont += 1

            shutil.move(final_path, destination_path)

            print(f"Movido para: {destination_path}")

            # Função pra pesquisar o monitorado no chronos
            searching_monitored(driver, wait, cleaned_name, final_name, destination_path)
            
        else:
            print(f"Pasta do monitorado(a): {cleaned_name} não encontrada.")
