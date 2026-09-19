# Plano de Instalação do Taguette do Zero (Guia Passo a Passo)

Este guia documenta o processo completo de instalação limpa do Taguette no Windows, com explicações detalhadas de cada comando para que você possa utilizá-lo como material didático e ensinar outras pessoas.

---

## 💡 Entendendo os Conceitos e Ferramentas

- **Por que Python 3.10?**
  O Taguette depende de versões específicas de bibliotecas como `SQLAlchemy 1.4` e `alembic 1.8`, que possuem instaladores binários (*wheels*) pré-compilados e estáveis para o Python 3.10 no Windows. Versões muito recentes (como 3.13 ou 3.14) não possuem esses binários e exigiriam compiladores C++ (Visual Studio Build Tools), o que complicaria a instalação.
- **Por que o Calibre?**
  O Taguette utiliza a ferramenta de linha de comando `ebook-convert` (que faz parte do Calibre) para converter documentos importados (como PDF, DOCX, EPUB) em HTML limpo e manipulável pelo sistema de marcação.
- **O que é o Poetry?**
  É a ferramenta oficial de gerenciamento de dependências e ambientes virtuais usada pelo Taguette. Ele isola as bibliotecas do projeto para não misturar com o Python global da sua máquina.
- **`poetry install`:**
  Lê o arquivo `poetry.lock` (que contém as versões exatas de cada dependência testada pelos desenvolvedores), cria o ambiente virtual isolado (caso ainda não exista) e baixa todas as bibliotecas necessárias.
- **Por que `poetry shell` costuma falhar no Windows?**
  Nas versões modernas do Poetry (2.x), o comando `shell` foi extraído para um plugin separado. Além disso, no Windows, o PowerShell por padrão restringe a execução de scripts (`ExecutionPolicy Restricted`), gerando erros ao tentar ativar o terminal virtualizado.
- **O que faz `poetry run taguette --debug`?**
  O `poetry run` roda qualquer comando **diretamente dentro do ambiente virtual** sem precisar ativar o shell antes. O argumento `--debug` ativa o modo de desenvolvimento: os erros mostram detalhes completos no terminal e o servidor reinicia automaticamente ao salvar alterações no código.

---

## Roteiro de Execução Passo a Passo

### Fase 1: Limpeza e Preparação do Diretório
- [x] **Passo 1: Limpeza da pasta antiga**
  ```powershell
  Remove-Item -Recurse -Force "D:\Taguette\taguette"
  ```
  *(Caso dê erro de arquivo em uso, feche editores de código como VS Code ou abas de terminal que estejam abertas na pasta).*

- [x] **Passo 2: Clonar o repositório oficial**
  No diretório `D:\Taguette`:
  ```powershell
  git clone https://gitlab.com/remram44/taguette.git
  ```

---

### Fase 2: Instalação dos Pré-requisitos de Sistema

- [x] **Passo 3: Instalar o Python 3.10**
  O próprio inicializador do Python no Windows (`py`) permite instalar runtimes adicionais diretamente:
  ```powershell
  py install 3.10
  ```
  *(Alternativa via gerenciador de pacotes do Windows: `winget install Python.Python.3.10`)*

  **Verificação:**
  ```powershell
  py -3.10 --version
  ```
  *(Retorna: `Python 3.10.x`)*

- [x] **Passo 4: Instalar o Calibre e definir a variável de ambiente**
  Pelo terminal via winget:
  ```powershell
  winget install calibre.calibre
  ```

  > [!IMPORTANT]
  > **Garantindo que o Taguette sempre encontre o Calibre no Windows:**
  > O Taguette verifica nativamente a variável de ambiente `CALIBRE`. Para que ele nunca se perca (mesmo com caches de terminal ou reinicializações), defina a variável permanente de usuário:
  > ```powershell
  > [Environment]::SetEnvironmentVariable("CALIBRE", "C:\Program Files\Calibre2", "User")
  > $env:CALIBRE = "C:\Program Files\Calibre2"
  > ```

  **Verificação:**
  ```powershell
  ebook-convert --version
  ```

---

### Fase 3: Configuração do Poetry e Dependências do Projeto

- [x] **Passo 5: Atualizar o pip e instalar o Poetry vinculado ao Python 3.10**
  ```powershell
  py -3.10 -m pip install --upgrade pip
  py -3.10 -m pip install poetry
  ```

- [x] **Passo 6: Entrar no diretório do projeto clonado**
  ```powershell
  cd D:\Taguette\taguette
  ```

- [x] **Passo 7: Configurar o Poetry para criar a pasta `.venv` dentro do projeto**
  ```powershell
  py -3.10 -m poetry config virtualenvs.in-project true
  ```

- [x] **Passo 8: Instalar todas as dependências do Taguette**
  ```powershell
  py -3.10 -m poetry install
  ```

---

### Fase 4: Execução e Validação do Sistema

- [x] **Passo 9: Iniciar o Taguette em modo de desenvolvimento**
  ```powershell
  py -3.10 -m poetry run taguette --debug
  ```

- [x] **Passo 10: Acessar a aplicação no navegador via link com token**
  O Taguette no modo desktop não usa a porta 8000, e sim a porta **7465**. Além disso, ele gera um link de autenticação com token no terminal:
  ```
  http://localhost:7465/?token=SEU_TOKEN_AQUI
  ```
  Copie o link exibido no seu terminal e abra no navegador.
  
- [x] **Passo 11: Validar o upload de documentos**
  Crie um projeto de teste e faça o upload de um arquivo (PDF, DOCX ou EPUB). O Taguette usará o `ebook-convert` do Calibre para converter e exibir o texto.
