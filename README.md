# 📚 Light Novel Downloader

[![python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://www.gnu.org/licenses/mit)

Este repositório contém diferentes ecossistemas e soluções para baixar, organizar e unificar capítulos de light novels, com foco especial no site Central Novel. O motor de scraping principal foi totalmente reconstruído em Python utilizando cloudscraper e concorrência (multi-threading) para máxima performance.

## 🚀 Destaques da Nova Engine Python

- Velocidade Extrema: Download multi-threaded capaz de atingir marcas de > 2 capítulos por segundo (280 capítulos em pouco mais de 2 minutos).
- Bypass de Cloudflare: Integração com cloudscraper que simula perfeitamente a engine de navegadores modernos, evitando bloqueios automatizados.
- Escrita Segura (Thread-Safe): Implementação de travas de concorrência (file_lock) que impedem a corrupção de arquivos .zip no Windows ao salvar dados simultâneos de múltiplas threads.

## 📁 Estrutura do Projeto
LIGHT_NOVEL_DOWNLOADER/
├── desktop-version/              # 🎯 Aplicação desktop integrada (Eel + HTML/JS UI)
│   ├── main.py                   # Motor principal com Eel e cloudscraper
│   ├── web/                      # Arquivos da interface web
│   │   ├── index.html            # Interface HTML
│   │   ├── script.js             # Lógica JavaScript
│   │   └── style.css             # Estilização
│   └── Light Novel Downloader.spec # Configuração PyInstaller (para compilação)
├── local-version/                # Scripts CLI via terminal
├── electron-version/             # Versão Electron [Legado]
├── web-version/                  # Solução Flask [Legado]
├── README_PROJETO.md             # Documentação detalhada complementar
└── README.md                      # Este arquivo

## 🛠️ Instalação das Dependências (Módulos Python)
Para rodar os scripts da local-version (CLI) ou da nova desktop-version (Eel), instale as bibliotecas necessárias abrindo o terminal (PowerShell ou CMD) na raiz do projeto e executando:

`pip install cloudscraper beautifulsoup4 tqdm requests eel lxml`

**Para compilar em executável desktop (.exe, .deb, etc):**
`pip install pyinstaller`

## 💻 Como Executar as Principais Soluções

### 1. Nova Versão Desktop (Interface Eel - Dentro de desktop-version/)
Uma aplicação desktop nativa e leve que une o design moderno de uma interface web com a velocidade e estabilidade do motor multi-thread em Python.

**Executar com Python (desenvolvimento):**
1. Acesse a pasta do aplicativo: `cd desktop-version`
2. Execute o comando: `python main.py`
3. Uma janela dedicada se abrirá. Insira os dados do intervalo de capítulos e use o seletor nativo do sistema operacional para decidir onde salvar seu arquivo .zip.

**Compilar em Executável:**
1. Acesse a pasta do aplicativo: `cd desktop-version`
2. Compile usando PyInstaller: `pyinstaller "Light Novel Downloader.spec"`
3. O executável estará em: `dist/Light Novel Downloader.exe` (Windows) ou `dist/Light Novel Downloader` (Linux)
4. Distribua o executável gerado - **sem necessidade de instalar Python**

### 2. Versão CLI (Linha de Comando - Dentro de local-version/)

Ideal para downloads diretos, minimalistas e rápidos com barra de progresso em tempo real diretamente no seu terminal.

1. Acesse a pasta dos scripts locais: cd local-version
2. Execute o comando: python .\scrapping.py
3. Defina o intervalo de capítulos e escolha o modo de salvamento: 1 para pasta com arquivos TXT separados ou 2 para compilado direto em arquivo ZIP.

## 💡 Dicas de Uso e Comportamento

- O "Delay" Inicial: Ao iniciar um download, o progresso pode parecer congelado em 0% por cerca de 15 a 20 segundos no início. Isso é perfeitamente normal! É o tempo que o cloudscraper leva para quebrar o desafio de JavaScript do Cloudflare em segundo plano. Assim que o cookie é gerado, as threads começam a baixar os dados em alta velocidade.
- Teto de Segurança: O limite padrão de segurança do motor está definido para MAX_CONCURRENT = 10 com tempo de respiração dinâmico de 1.5s a 3.5s. Esse arranjo garante 100% de sucesso contra bloqueios por excesso de requisições (Erro HTTP 429).

## 🔧 Compilação e Distribuição (Desktop Version)

### PyInstaller Configuration
O arquivo `Light Novel Downloader.spec` na pasta `desktop-version/` já está pré-configurado com:
- ✅ Todos os módulos ocultos necessários (eel, cloudscraper, bs4, requests, lxml)
- ✅ Pasta `web/` incluída como dado (interface web embarcada)
- ✅ Otimizações de bytecode ativadas

### Compilação Multi-Plataforma
```bash
cd desktop-version

# Windows (.exe)
pyinstaller "Light Novel Downloader.spec"

# Linux (.deb - requer fpm)
pyinstaller "Light Novel Downloader.spec"
fpm -s dir -t deb -n light-novel-downloader dist/Light\ Novel\ Downloader

# macOS
pyinstaller "Light Novel Downloader.spec"
```

O executável final estará na pasta `dist/` e **não requer instalação prévia de Python**.

📄 Licença
Este projeto está sob a licença MIT.

Dúvidas, melhorias no scraper ou sugestões? Abra uma issue ou envie um e-mail para marlonprado04@gmail.com
