# 📄 ChronosFlow

Projeto em Python para processamento de dados e extração de informações de arquivos (ex: PDFs/imagens).

---

## 🚀 Tecnologias utilizadas

* Python 3.13.7
* NumPy
* Matplotlib
* Pytesseract
* pdf2image
* Selenium

---

## ⚠️ Pré-requisitos (IMPORTANTE)

Antes de rodar o projeto, você precisa instalar dependências **fora do Python**:

### 🔹 Tesseract OCR

Responsável pelo reconhecimento de texto nas imagens.

* **Windows:** baixar e instalar (ex: UB Mannheim)
* **Linux:**

```bash
sudo apt install tesseract-ocr
```

---

### 🔹 Poppler

Necessário para converter PDFs em imagens.

* **Windows:** baixar e adicionar ao PATH
* **Linux:**

```bash
sudo apt install poppler-utils
```

---

## 📦 Instalação

### 1. Clonar o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd CEMEP
```

### 2. Criar ambiente virtual

```bash
python -m venv venv
```

### 3. Ativar ambiente virtual

* **Windows:**

```bash
venv\Scripts\activate
```

* **Linux/macOS:**

```bash
source venv/bin/activate
```

### 4. Instalar dependências

```bash
pip install -r requirements.txt
```

---

## ▶️ Como executar

```bash
python scripts/main.py
```

---

## 📁 Estrutura do projeto

```
CEMEP/
│
├── scripts/
│   ├── main.py
│   └── extract_data.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🧠 Observações

* O diretório `venv/` não é versionado (não sobe para o GitHub)
* Certifique-se de que o Tesseract e o Poppler estão instalados corretamente
* Caso encontre erros de OCR ou PDF, verifique as variáveis de ambiente (PATH)

---

## 👨‍💻 Autor

* Pedro Gustavo Santos de Santana
