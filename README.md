# 📚 Light Novel Downloader

[![python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://www.gnu.org/licenses/mit)

Este repositório contém diferentes ecossistemas e soluções para baixar, organizar e unificar capítulos de light novels. A versão desktop oferece suporte ao Central Novel e ao Free Web Novel, identificando a fonte a partir da URL informada. O motor de scraping principal utiliza cloudscraper e concorrência (multi-threading).

## 🚀 Destaques da Nova Engine Python

- Velocidade Extrema: Download multi-threaded capaz de atingir marcas de > 2 capítulos por segundo (280 capítulos em pouco mais de 2 minutos).
- Requisições resilientes: Integração com cloudscraper e novas tentativas para erros transitórios. O acesso continua sujeito aos limites e bloqueios aplicados por cada site.
- Escrita Segura: Arquivos TXT e EPUB são gerados sem sobrescrever saídas existentes.
- Fontes na versão desktop: Central Novel (URL base terminada em hífen) e Free Web Novel (URL de um capítulo, no formato `/novel/nome-da-obra/chapter-1`).

## 📁 Estrutura do Projeto
LIGHT_NOVEL_DOWNLOADER/
├── desktop-version/              # 🎯 Aplicação desktop integrada (Eel + HTML/JS UI)
│   ├── main.py                   # Interface Eel, downloads e saídas
│   ├── chapters.py               # Modelo, validação de fonte e extração normalizada
│   ├── test_chapter_extraction.py # Testes de extração e integração
│   ├── web/                      # Arquivos da interface web
│   │   ├── index.html            # Interface HTML
│   │   ├── script.js             # Lógica JavaScript
│   │   └── style.css             # Estilização
│   └── Light Novel Downloader.spec # Configuração PyInstaller (para compilação)
├── cli-version/                  # Scripts CLI via terminal
├── legacy/                       # Versão Electron e web [Legado]
└── README.md                     # Este arquivo

## 🛠️ Instalação das Dependências (Módulos Python)
Para rodar os scripts da local-version (CLI) ou da nova desktop-version (Eel), instale as bibliotecas necessárias abrindo o terminal (PowerShell ou CMD) na raiz do projeto e executando:

`pip install cloudscraper beautifulsoup4 tqdm requests eel lxml EbookLib`

**Para compilar em executável desktop (.exe, .deb, etc):**
`pip install pyinstaller`

## 💻 Como Executar as Principais Soluções

### 1. Nova Versão Desktop (Interface Eel - Dentro de desktop-version/)
Uma aplicação desktop nativa e leve que une o design moderno de uma interface web com a velocidade e estabilidade do motor multi-thread em Python.

Para baixar do **Central Novel**, mantenha uma URL base terminada em hífen, como `https://centralnovel.com/shadow-slave-capitulo-`. Para o **Free Web Novel**, cole a URL real de qualquer capítulo da obra, como `https://freewebnovel.com/novel/captured-by-the-cold-detective-bl/chapter-1`. Não use `nome-da-obra` literalmente: substitua pelo slug real da novel. Informe o intervalo desejado; o aplicativo reconhece o site e ajusta o número do capítulo em cada requisição. Na versão desktop, escolha arquivos TXT individuais ou um livro EPUB com sumário navegável. O suporte ao Free Web Novel está na versão desktop; a CLI e as versões legadas ainda usam o formato do Central Novel.

Os arquivos de capítulo incluem o número, o título do capítulo e o nome da obra, por exemplo `Capítulo 00001 - Missing Neighbor - Captured By The Cold Detective (BL).txt`. A extração do Central Novel lê o título do capítulo em `cat-series` e o nome da obra antes de “Capítulo” em `entry-title`; no Free Web Novel, usa `span.chapter` e `h1.tit`. Ambos são convertidos para o mesmo formato de capítulo antes de gerar TXT ou EPUB. Capítulos sem acesso ou com conteúdo ausente são registrados como `ERRO_<número>.txt`; esses arquivos podem ser sobrescritos ao tentar novamente. Arquivos de capítulo e resultados de unificação existentes não são sobrescritos. Antes de unificar, resolva ou remova os arquivos `ERRO_*.txt` da pasta. O executável em `desktop-version/dist/` foi recompilado com estas alterações.

**Executar com Python (desenvolvimento):**
1. Acesse a pasta do aplicativo: `cd desktop-version`
2. Execute o comando: `python main.py`
3. Uma janela dedicada se abrirá. Insira os dados do intervalo de capítulos e use o seletor nativo para escolher a pasta de destino dos TXT ou EPUB.

**Compilar em Executável:**
1. Acesse a pasta do aplicativo: `cd desktop-version`
2. Compile usando PyInstaller: `pyinstaller "Light Novel Downloader.spec"`
3. O executável estará em: `dist/Light Novel Downloader.exe` (Windows) ou `dist/Light Novel Downloader` (Linux)
4. Distribua o executável gerado - **sem necessidade de instalar Python**

### 2. Versão CLI (Linha de Comando - Dentro de local-version/)

Ideal para downloads diretos, minimalistas e rápidos com barra de progresso em tempo real diretamente no seu terminal.

1. Acesse a pasta dos scripts locais: cd cli-version
2. Execute o comando: python .\main.py
3. Defina o intervalo de capítulos e escolha o modo de salvamento: 1 para TXT individuais ou 2 para um ZIP.

### Testes da versão desktop

Na pasta `desktop-version/`, execute `python -m unittest test_chapter_extraction` para validar a extração dos dois sites, os formatos de saída e o título enviado ao log.

## 💡 Dicas de Uso e Comportamento

- O progresso pode demorar a aparecer enquanto o site responde. Erros de rede e bloqueios HTTP são mostrados por capítulo; novas tentativas não garantem que uma fonte protegida por Cloudflare permita o acesso.
- Para evitar timeouts no Central Novel, a versão desktop limita automaticamente os downloads a 3 simultâneos e usa timeout mínimo de 60 segundos. No Free Web Novel, valem os ajustes avançados configurados pelo usuário.
- Antes de baixar, confirme que o Free Web Novel usa o slug real da obra e que o intervalo existe. Um link de exemplo com `nome-da-obra` é rejeitado pela interface.

## 🔧 Compilação e Distribuição (Desktop Version)

### PyInstaller Configuration
O arquivo `Light Novel Downloader.spec` na pasta `desktop-version/` já está pré-configurado com:
- ✅ Todos os módulos ocultos necessários (eel, cloudscraper, bs4, requests, lxml, EbookLib)
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
