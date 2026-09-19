# AGENTS.md - Diretrizes Operacionais, Governança e Arquitetura para Agentes de IA

Este documento é a referência canônica e mandatória para qualquer agente de IA ou desenvolvedor atuando na evolução, manutenção e incremento do projeto **Taguette**.

---

## 1. Idioma e Comunicação
- **Português do Brasil (`pt-BR`) Mandatório:** Toda a comunicação com o usuário, respostas, relatórios, documentações e especificações devem ser redigidos estritamente em português do Brasil.
- **Comentários de Código e Logs:** Novos comentários de código, docstrings adicionadas, saídas de log e mensagens de erro do sistema devem ser redigidos em português do Brasil (`pt-BR`), exceto termos técnicos e palavras-chave universais da linguagem de programação.
- **Mensagens de Commit:** Devem ser redigidas em português do Brasil (`pt-BR`), respeitando o padrão Conventional Commits (Seção 9).

---

## 2. Stack Tecnológica e Arquitetura Original

Qualquer incremento deve respeitar fielmente a arquitetura existente, evitando a introdução de frameworks concorrentes ou estruturas alienígenas ao ecossistema já consolidado do projeto.

### 2.1 Backend e Servidor
- **Linguagem & Runtime:** Python 3.10 (executado via PowerShell no Windows).
- **Gerenciador de Dependências:** [Poetry](https://python-poetry.org/) com ambiente virtual isolado (`.venv` na raiz do repositório).
- **Framework Web:** [Tornado Web Framework](https://www.tornadoweb.org/) (`tornado.web`, `tornado.ioloop`, `tornado.gen`), baseado em loop assíncrono nativo (`asyncio`).
- **Mapeamento Objeto-Relacional (ORM):** [SQLAlchemy 1.4](https://www.sqlalchemy.org/) (`declarative_base`, sessões gerenciadas por requisição no `BaseHandler`).
- **Bancos de Dados Suportados:**
  - **SQLite3:** Padrão para uso monousuário / modo desktop (armazenado em `Documents/Taguette/taguette.sqlite3`).
  - **PostgreSQL / MariaDB:** Suportados para implantações em modo servidor multiusuário.
- **Controle de Migrações de Banco:** [Alembic](https://alembic.sqlalchemy.org/) (`alembic.ini` e migrações versionadas em `taguette/migrations/versions/`).
- **Template Engine:** [Jinja2](https://jinja.palletsprojects.com/) com suporte a internacionalização (`jinja2.ext.i18n`), localizado em `taguette/templates/`.

### 2.2 Frontend e Tempo Real
- **Arquitetura Frontend:** Server-Side Rendered (SSR) via Jinja2 + assets estáticos em `taguette/static/`.
- **Bibliotecas de Interface:**
  - CSS: **Bootstrap 4** customizado e tipografia/ícones **FontAwesome** (`webfonts/`).
  - JavaScript: **jQuery 3.7.1** e Bootstrap bundle em `taguette/static/js/`.
  - Lógica central da aplicação em JavaScript nativo/jQuery concentrada em `taguette/static/js/taguette.js`.
- **Colaboração em Tempo Real (Live Editing):** Mecanismo de **Long-Polling** que escuta a tabela de eventos `commands` no banco de dados. Em implantações distribuídas com múltiplos servidores, utiliza **Redis Pub/Sub** para sincronização imediata.
- **Gerenciamento de Cache de Assets:** O Tornado gerencia os assets estáticos através de `static_url(..., include_version=True)`, gerando hashes MD5 automáticos nos arquivos em modo de produção. Não existe Service Worker (`sw.js`).

### 2.3 Conversão, Higienização e Processamento de Documentos
- **Conversão de Documentos:**
  - **Calibre (`ebook-convert`):** Executado em subprocesso assíncrono (`asyncio.Semaphore`, concorrência limitada a 4) com timeout rígido para converter DOCX, PDF, EPUB, RTF e HTML em HTML semântico.
  - **wvWare (`wvHtml`):** Para conversão de arquivos legados Microsoft Word 97 (`.doc`).
  - **subtitle-parser:** Para processamento de legendas em formato `.srt` e `.vtt`.
- **Higienização e Proteção XSS:** O HTML gerado pelas conversões passa obrigatoriamente por **BeautifulSoup4** (remoção de `<head>`, `<script>`, `<style>`) e **Bleach** (remoção de tags e atributos não autorizados, sanitização de links e imagens).
- **Extração de Texto e Destaques:** O módulo `taguette/extract.py` extrai texto puro e mapeia os destaques (*highlights*) calculando offsets de bytes em UTF-8.
- **Exportação de Dados:** Geração de planilhas Excel via **XlsxWriter** e conversão reversa para HTML/DOCX/PDF via Calibre (`taguette/export.py` e `taguette/convert.py`).

### 2.4 Internacionalização (i18n)
- GNU gettext integrado com Babel.
- Catálogos de mensagens em `po/` (.pot/.po) compilados para arquivos binários `.mo` em `taguette/l10n/`.
- Dois catálogos ativos: `taguette_main` (servidor/templates) e `taguette_javascript` (servido para o frontend via `/trans.js`).

---

## 3. Ambientes do Projeto

### 3.1 Ambiente de Desenvolvimento Local (Windows / PowerShell)
- **Interpretador:** Python 3.10 (invocado preferencialmente via `py -3.10`).
- **Isolamento:** Execução estritamente vinculada ao Poetry: `py -3.10 -m poetry run <comando>`.
- **Dependência Externa Calibre:** Deve estar instalado e o caminho acessível via variável de ambiente `$env:CALIBRE = "C:\Program Files\Calibre2"`.

### 3.2 Isolamento e Blindagem do Repositório Git
Para assegurar que nenhum código, teste ou documentação interna seja inadvertidamente publicado no repositório original do Taguette:
1. **Upstream Original Bloqueado:** O repositório remoto oficial (`gitlab.com/remram44/taguette.git`) está configurado como `upstream` com a URL de push definida como `no_push`. Qualquer comando acidental de push para o upstream é imediatamente abortado pelo próprio Git.
2. **Repositório Pessoal (`origin`):** Todas as atualizações e sincronizações remotas devem apontar exclusivamente para o repositório sob o controle da conta do usuário.

---

## 4. Estrutura de Pastas do Repositório

```text
D:\Taguette\taguette\
├── AGENTS.md                  # Este arquivo canônico de instruções para agentes de IA
├── ARCHITECTURE.md            # Arquitetura original descrita pelo criador do projeto
├── Dockerfile                 # Contêiner Docker oficial
├── alembic.ini                # Configuração do motor de migrações Alembic
├── pyproject.toml             # Manifesto do Poetry com metadados e dependências
├── poetry.lock                # Lockfile com hashes e versões exatas de dependências
├── tests.py                   # Suíte de testes automatizados do Taguette
│
├── docs\                      # Pasta de documentação viva e especificações do projeto
│   ├── FSD.md                 # Especificação Funcional do Sistema (Functional Specification Document)
│   ├── STATUS.md              # Arquivo vivo de status, etapas concluídas e próximos passos
│   └── ERROS.md               # Histórico vivo de incidentes, causas raiz e lições técnicas
│
├── planejamento\              # Planos de implementação aprovados (Implementation Plans)
│   ├── implementation_plan1.md # Registro histórico do plano de instalação no Windows
│   └── YYYY-MM-DD_NN_nome.md  # Novos planos aprovados
│
├── po\                        # Arquivos de internacionalização e tradução (.po / .pot)
├── scripts\                   # Scripts utilitários de build e atualização de traduções
│
└── taguette\                  # Pacote principal Python da aplicação
    ├── database\              # Modelagem SQLAlchemy e conexão com banco de dados
    │   ├── base.py            # Metadados base e métricas
    │   ├── models.py          # Modelos de dados (User, Project, Document, Tag, Highlight, etc.)
    │   └── copy.py            # Utilitários de cópia e exportação de projetos
    ├── migrations\            # Scripts de migração Alembic versionados
    │   └── versions\          # Histórico de revisões de esquema de banco
    ├── web\                   # Camada HTTP e rotas do Tornado
    │   ├── base.py            # BaseHandler, autenticação, permissões, sessão e contexto
    │   ├── views.py           # Views que renderizam páginas HTML
    │   ├── api.py             # Handlers da API REST / JSON
    │   └── export.py          # Handlers de exportação de dados
    ├── templates\             # Templates Jinja2 (.html, .txt, .js)
    ├── static\                # Arquivos estáticos servidos pelo Tornado
    │   ├── css\               # Folhas de estilo customizadas e Bootstrap
    │   ├── js\                # taguette.js, jquery, bootstrap
    │   └── webfonts\          # Fontes e glifos do FontAwesome
    ├── convert.py             # Integração com Calibre, wvWare e parsers de formato
    ├── extract.py             # Extração semântica e cálculo de offsets de texto
    ├── export.py              # Exportação de projetos para XLSX, DOCX, PDF
    ├── import_codebook.py     # Importação de livros de códigos (codebooks)
    ├── validate.py            # Validadores de integridade de dados e formato
    └── main.py                # Ponto de entrada CLI (taguette, taguette server, etc.)
```

> [!NOTE]
> Sempre que novos diretórios ou módulos forem criados durante o ciclo de incrementos, a estrutura acima deve ser prontamente atualizada em `docs/STATUS.md`.

---

## 5. Comandos Principais de Operação

Todos os comandos de terminal devem ser executados a partir do diretório raiz do repositório (`D:\Taguette\taguette`) utilizando o runtime Python 3.10 via Poetry:

| Finalidade | Comando no PowerShell |
| :--- | :--- |
| **Inicialização Desktop (Modo Debug)** | `py -3.10 -m poetry run taguette --debug` |
| **Inicialização Desktop Padrão** | `py -3.10 -m poetry run taguette` |
| **Inicialização sem abrir Navegador** | `py -3.10 -m poetry run taguette --no-browser` |
| **Definir Porta e Endereço Customizados** | `py -3.10 -m poetry run taguette -p 7465 -b 127.0.0.1` |
| **Executar Suíte Completa de Testes** | `py -3.10 -m poetry run python tests.py -v` |
| **Executar Teste Específico** | `py -3.10 -m poetry run python tests.py -v TestClass.test_metodo` |
| **Executar Migrações do Banco de Dados** | `py -3.10 -m poetry run taguette migrate` |
| **Gerar Configuração de Servidor Padrão** | `py -3.10 -m poetry run taguette default-config -o config.py` |
| **Iniciar em Modo Servidor Multiusuário** | `py -3.10 -m poetry run taguette server config.py` |

---

## 6. Regras de Segurança e Blindagem Técnica

### 6.1 Controle de Acesso e RBAC (Role-Based Access Control)
- Todo endpoint que manipule projetos, documentos, etiquetas (*tags*) ou destaques (*highlights*) deve verificar rigorosamente as permissões do usuário logado.
- Utilizar os métodos utilitários do `BaseHandler` (`get_project()` e `get_document()`), que consultam a tabela associativa `ProjectMember` e retornam o enum `Privileges`.
- Validar estritamente antes de qualquer operação:
  - `privileges.can_edit_project_meta()`
  - `privileges.can_delete_project()`
  - `privileges.can_edit_members()`
  - `privileges.can_add_document()` / `can_edit_document()` / `can_delete_document()`
  - `privileges.can_add_tag()` / `can_update_tag()` / `can_delete_tag()` / `can_merge_tags()`
  - `privileges.can_add_highlight()` / `can_delete_highlight()`

### 6.2 Prevenção de XSS (Cross-Site Scripting)
- Qualquer conteúdo HTML importado ou convertido precisa passar obrigatoriamente pelo sanitizador `bleach.clean()` com whitelist estrita de tags e atributos permitidos.
- Proibição absoluta de permitir `<script>`, `<iframe>`, `<object>`, `<embed>`, ou atributos de eventos JavaScript inline (`onclick`, `onload`, `onerror`).
- Links e URLs de imagens devem ser sanitizados para permitir somente esquemas seguros (`http://`, `https://`, `mailto:`), descartando `javascript:`, `data:` ou URLs relativas arbitrárias.

### 6.3 Prevenção de SQL Injection
- Todas as operações com banco de dados devem utilizar a camada ORM do SQLAlchemy.
- Caso seja estritamente indispensável executar SQL bruto (*raw SQL*), é mandatório o uso de `sqlalchemy.text()` com passagem de parâmetros parametrizados (*bind parameters*). Concatenação de strings em SQL é terminantemente proibida.

### 6.4 Proteção contra CSRF / XSRF
- O Tornado tem `xsrf_cookies=True` habilitado. Todas as rotas POST, PUT, DELETE baseadas em formulários HTML devem renderizar `{{ xsrf_form_html() }}`.
- Chamadas de API via JavaScript/AJAX devem enviar o token de CSRF lido do cookie `_xsrf` no cabeçalho HTTP `X-XSRFToken`.

### 6.5 Autenticação e Gestão de Sessões
- Senhas de usuários devem ser tratadas exclusivamente via `User.set_password()` e validadas via `User.check_password()`, utilizando hashing com algoritmo moderno `scrypt` (com salt criptográfico e limite de memória `SCRYPT_MAX_MEM`), ou fallback para `pbkdf2` com 500.000 iterações ou `bcrypt`.
- Cookies de sessão (`user`) devem ser emitidos como cookies seguros e assinados via HMAC (`set_secure_cookie()`) utilizando a chave de segredo `SECRET_KEY`.

### 6.6 Importação Segura de Arquivos e Prevenção de Path Traversal
- Nomes de arquivos enviados por upload devem ser obrigatoriamente filtrados pelas funções `taguette.utils.sanitize_filename()` e `taguette.validate.fix_filename()`, neutralizando caracteres de escape (`../`, `..\`) e caracteres de controle.
- Validação de cabeçalhos de arquivos (*magic bytes* / MIME-type real) antes de submeter o payload para conversores externos como Calibre ou wvWare.
- Execução de conversores externos encapsulada em diretórios temporários isolados (`tempfile.mkdtemp()`), com descarte garantido em blocos `try ... finally: shutil.rmtree(tmp)`.
- Controle de concorrência com semáforos (`MeasuredSemaphore` / `PROC_MAX_CONCURRENT`) e timeout estrito com `SIGTERM` seguido de `SIGKILL` para prevenir travamento ou esgotamento de recursos da máquina.

---

## 7. Protocolo de Governança, Planejamento Mandatório e Arquivos Vivos

### 7.1 REGRA DE OURO MANDATÓRIA (INEGOCIÁVEL): CRIAÇÃO PRÉVIA DE IMPLEMENTATION PLAN
> [!IMPORTANT]
> **É EXPRESSAMENTE E TERMINANTEMENTE PROIBIDO alterar qualquer linha de código, arquivo de configuração, script ou banco de dados sem antes:**
> 1. Elaborar um **Implementation Plan** completo, estruturado e minucioso.
> 2. Apresentar o plano ao usuário e **aguardar sua aprovação explícita (`Proceed`)**.
> 3. Salvar o plano aprovado na pasta `planejamento/` na raiz do repositório.
>
> **Nenhuma modificação pode ser executada sem a autorização prévia e inequívoca do usuário.**

### 7.2 Rotina de Salvamento de Planos e Aprovações (`planejamento/`)
Todos os planos de implementação, contendo o escopo, arquivos afetados, decisões arquiteturais, checklist de testes e o registro formal de aprovação do usuário (`Proceed`), devem ser salvos e mantidos permanentemente no diretório `planejamento/`:
- **Padrão de nomenclatura obrigatório:** `planejamento/YYYY-MM-DD_NN_nome_da_tarefa.md`
  - Exemplo: `planejamento/2026-09-19_01_validacao_upload_e_governanca.md`
- **Conteúdo mínimo obrigatório de cada arquivo de planejamento:**
  1. **Metadados:** Data, Autor, Status (`Pendente`, `Em Andamento`, `Concluído`) e Registro do Proceed do Usuário (data/hora e transcrição da mensagem de aprovação).
  2. **Contexto e Objetivos:** O que motivou a demanda e qual o objetivo funcional/técnico.
  3. **Decisões Técnicas e Arquiteturais:** Modelagem SQLAlchemy, migrações Alembic, handlers Tornado, endpoints de API e componentes de interface.
  4. **Arquivos a Modificar / Criar:** Lista completa dos arquivos afetados.
  5. **Plano de Verificação e Testes:** Testes unitários (`tests.py`), testes manuais no navegador e critérios de aceitação.
  6. **Relatório de Execução (Pós-conclusão):** Resumo do que foi executado e evidências de validação.

---

### 7.3 Ciclo de Trabalho Operacional do Taguette (Passo a Passo)
Todo trabalho neste repositório deve seguir rigorosamente as 3 fases abaixo:

#### FASE 1: Análise e Planejamento Prévio (Sem Alterar Código)
1. Ler os arquivos de contexto e especificação na pasta `docs/`:
   - `docs/FSD.md` (Especificação Funcional do Sistema)
   - `docs/STATUS.md` (Arquivo vivo de status atual e etapas)
   - `docs/ERROS.md` (Arquivo vivo de histórico de erros e lições aprendidas)
2. Elaborar o **Implementation Plan** detalhado conforme o padrão definido.
3. Submeter o plano para revisão do usuário e **PARAR**.
4. **Aguardar a aprovação explícita do usuário (`Proceed`)**. Não avançar para codificação sem essa confirmação.
5. Arquivar o plano com status aprovado em `planejamento/YYYY-MM-DD_NN_nome_da_tarefa.md`.

#### FASE 2: Execução e Verificação Técnica
1. Executar as modificações de código e configurações estritamente alinhadas ao plano aprovado.
2. Se houver modificação de modelos SQLAlchemy (`taguette/database/models.py`), **obrigatoriamente**:
   - Gerar e versionar a nova migração do Alembic em `taguette/migrations/versions/`.
   - Testar a aplicação da migração via `py -3.10 -m poetry run taguette migrate`.
3. Executar a suíte de testes automatizados do Taguette e garantir 100% de aprovação:
   ```powershell
   py -3.10 -m poetry run python tests.py -v
   ```
4. Se o frontend tiver sido alterado (`taguette/templates/` ou `taguette/static/`), validar a interface visual e funcional no navegador e instruir o usuário quanto ao recarregamento forçado de cache (`Ctrl + F5` ou `Ctrl + Shift + R`).

#### FASE 3: Conclusão, Documentação Viva e Reporte
1. **Atualizar `docs/STATUS.md`:**
   - Registrar as novas funcionalidades e ajustes no checklist da respectiva etapa.
   - Atualizar a data de última modificação e a porcentagem/status do progresso.
2. **Atualizar `docs/ERROS.md` (se houver incidentes ou dificuldades superadas):**
   - Registrar o erro/sintoma, a causa raiz, a solução técnica aplicada e como prevenir reincidências.
3. **Atualizar o registro em `planejamento/`:**
   - Marcar o plano como `Concluído` e preencher o Relatório de Execução com as evidências.
4. **Executar Commit Semântico Mandatório (Seção 9):**
   - Realizar os commits regulares e atômicos no Git seguindo rigorosamente a Norma Operacional de Versionamento (Conventional Commits em `pt-BR`).
5. **Informar detalhadamente ao usuário:**
   - O que foi construído, modificado e testado.
   - Roteiro prático com comandos e ações para o usuário validar a entrega no ambiente local.

> [!CAUTION]
> Use sempre caminhos relativos à raiz do repositório (`D:\Taguette\taguette`). Nunca utilize links no formato `file:///` nem exponha credenciais ou segredos em documentações ou commits.

---

## 8. Boas Práticas de Engenharia e Código
- **Simplicidade e Clareza:** Código legível, modular e autoexplicativo, aderente aos princípios da PEP 8 para Python.
- **Funções Pequenas e Focadas:** Métodos com responsabilidade única (Single Responsibility Principle - SRP).
- **Nomes Descritivos:** Variáveis, funções e classes com nomes claros e objetivos, respeitando as convenções já existentes no código original do Taguette.
- **Convenção de Nomes Mandatória:**
  - Classes: `CamelCase` (ex: `DocumentAdd`, `ProjectMember`).
  - Funções e variáveis: `snake_case` (ex: `get_project`, `to_html_chunks`).
  - Constantes: `UPPER_SNAKE_CASE` (ex: `PROC_MAX_CONCURRENT`, `DEFAULT_CONFIG`).
- **Sem Escopo Fantasma:** Não inventar funcionalidades, botões ou refatorações fora do escopo estritamente aprovado no plano de implementação e descrito em `docs/FSD.md`.
- **Tratamento Resiliente de Exceções:** Tratar casos de borda, falhas de I/O de arquivos, subprocessos externos (Calibre) e transações de banco de dados com tratamento gracioso e mensagens de erro informativas.

---

## 9. Norma Operacional de Versionamento: Boas Práticas, Convenções e Prefixos no Git

Este capítulo consolida a norma obrigatória de versionamento do código-fonte, reunindo todos os prefixos semânticos, regras de commits atômicos, nomenclatura de branches e melhores práticas operacionais.

### 9.1 O Padrão Conventional Commits (Prefixos Oficiais e Estendidos)

A convenção adotada pelo projeto é o **Conventional Commits** (compatível com ferramentas de automação de releases e changelog semântico).

#### Estrutura Fundamental
```text
<tipo>[escopo opcional]: <descrição concisa e no imperativo em pt-BR>

[corpo opcional explicando o 'porquê' e o contexto da mudança]

[rodapé(s) opcional(is): BREAKING CHANGE ou referências a issues/tarefas]
```

---

#### Tabela Completa de Prefixos

| Prefixo | Finalidade / Quando Utilizar | Exemplo Real |
| :--- | :--- | :--- |
| **`feat`** | Introdução de uma nova funcionalidade no sistema ou API. | `feat(auth): adicionar integração de login com sso` |
| **`fix`** | Correção de bug / problema que afeta o usuário ou o fluxo esperado. | `fix(convert): corrigir timeout na conversão de documentos pdf grandes` |
| **`docs`** | Alterações exclusivas na documentação (STATUS.md, FSD.md, README, etc.). | `docs(governanca): adicionar agents.md e normas de commit` |
| **`style`** | Modificações que não afetam o significado do código (espaçamento, formatação, CSS visual). | `style(templates): ajustar espaçamento dos botoes de destaque` |
| **`refactor`** | Refatoração de código: alteração interna que não corrige bug nem adiciona funcionalidade. | `refactor(database): simplificar consulta de membros do projeto` |
| **`perf`** | Alteração de código com foco estrito em melhoria de desempenho/performance. | `perf(extract): otimizar calculo de offsets de texto em utf-8` |
| **`test`** | Adição de novos testes ou correção/atualização de testes existentes. | `test(api): adicionar testes unitarios para criacao de projetos` |
| **`build`** | Mudanças no sistema de build, dependências externas (Poetry, pyproject.toml, pacotes). | `build(deps): atualizar bleach para versao 6.1.0` |
| **`ci`** | Alterações em arquivos e scripts de Integração Contínua (GitLab CI, GitHub Actions). | `ci(test): incluir step de verificacao de cobertura de testes` |
| **`chore`** | Tarefas de manutenção rotineira que não modificam arquivos de produção ou testes (.gitignore, etc.). | `chore(gitignore): ignorar arquivos temporarios do calibre` |
| **`revert`** | Reversão explícita de um commit anterior. | `revert: feat(export): reverter geracao assincrona de xlsx` |
| **`deps`** | Atualização de bibliotecas e dependências do projeto. | `deps(security): atualizar sqlalchemy para versao compativel` |
| **`security`** | Correções críticas de vulnerabilidades ou implementação de patches de segurança. | `security(upload): validar magic bytes no upload de documentos` |
| **`release`** | Commit de corte/geração de release, versionamento ou alteração de changelog. | `release: lancar versao 1.6.0 com novos incrementos` |
| **`wip`** | *Work In Progress* (usado apenas em branches de rascunho/locais; **nunca** na branch principal). | `wip: experimentando novo parser de texto` |

---

#### Quebra de Compatibilidade (*Breaking Changes*)

Quando uma alteração quebra contratos existentes de API ou compatibilidade com versões anteriores:
1. Adicione uma exclamação `!` logo antes dos dois pontos:
   ```text
   feat(api)!: alterar estrutura de retorno do endpoint de documentos
   ```
2. Ou inclua a menção explícita no rodapé:
   ```text
   feat(api): alterar estrutura do endpoint de documentos

   BREAKING CHANGE: O endpoint `/api/project/{id}/documents` agora retorna `doc_id` no lugar de `id`.
   ```

---

### 9.2 Padrão Gitmoji (Alternativa Visual)

Se adotado no projeto, os prefixos textuais podem ser complementados por emojis padronizados:

| Emoji | Código | Prefixo Equivalente | Finalidade |
| :---: | :--- | :--- | :--- |
| ✨ | `:sparkles:` | `feat` | Introduzir novos recursos/features |
| 🐛 | `:bug:` | `fix` | Corrigir um bug |
| 📝 | `:memo:` | `docs` | Escrever ou atualizar documentação |
| 💄 | `:lipstick:` | `style` | Atualizar UI/arquivos de estilo visual |
| ♻️ | `:recycle:` | `refactor` | Refatorar código |
| ⚡️ | `:zap:` | `perf` | Melhorar performance |
| ✅ | `:white_check_mark:` | `test` | Adicionar ou atualizar testes |
| 👷 | `:construction_worker:` | `ci` | Adicionar/modificar scripts de CI |
| 📦️ | `:package:` | `build` | Adicionar/atualizar pacotes e dependências |
| 🔧 | `:wrench:` | `chore` | Modificar configurações do projeto |
| 🔒️ | `:lock:` | `security` | Corrigir problemas de segurança |
| ⏪️ | `:rewind:` | `revert` | Reverter alterações anteriores |
| 🚧 | `:construction:` | `wip` | Trabalho em progresso |
| 🚀 | `:rocket:` | `release` | Implantar / publicar nova versão |
| 💥 | `:boom:` | `BREAKING CHANGE` | Introduzir mudanças com quebra de compatibilidade |

---

### 9.3 Padrão de Nomenclatura de Branches

A consistência nas branches evita conflitos e facilita integrações contínuas:

#### Estrutura Recomendada
```text
<categoria>/<id-da-tarefa-opcional>-<descricao-kebab-case>
```

#### Prefixos de Branches
| Prefixo | Cenário de Uso | Exemplo |
| :--- | :--- | :--- |
| **`feature/`** ou **`feat/`** | Desenvolvimento de uma nova funcionalidade. | `feature/TAG-10-filtro-avancado-tags` |
| **`bugfix/`** ou **`fix/`** | Correção de defeito encontrado em desenvolvimento/testes. | `fix/TAG-12-timeout-conversao-calibre` |
| **`hotfix/`** | Correção crítica e urgente diretamente na branch principal. | `hotfix/TAG-99-falha-sessao-cookie` |
| **`release/`** | Preparação de uma nova versão para envio a produção. | `release/v1.6.0` |
| **`support/`** | Manutenção de versões legadas de suporte. | `support/v1.5.x` |
| **`refactor/`** | Alteração técnica estrutural sem impacto funcional direto. | `refactor/modularizar-conversao-documentos` |
| **`chore/`** | Manutenção técnica interna, limpeza ou tarefas de configuração. | `chore/atualizar-dependencias-poetry` |
| **`test/`** | Criação ou reestruturação isolada de suítes de testes. | `test/adicionar-testes-import-codebook` |
| **`experiment/`** ou **`spike/`** | Prova de conceito (PoC) exploratória sem garantia de merge. | `spike/testar-novo-leitor-epub` |

---

### 9.4 Regras de Ouro para Mensagens de Commit

1. **Use o modo imperativo no assunto:**
   - ✅ `feat: adicionar filtro de documentos` (Adicione / Adicionar)
   - ❌ `feat: adicionado filtro de documentos` ou `feat: adicionando filtro`
2. **Limite o tamanho da linha de cabeçalho:** Mantenha o cabeçalho em no máximo **50 a 72 caracteres**.
3. **Não finalize o cabeçalho com ponto final (`.`):** Seja conciso e direto.
4. **Use letras minúsculas no cabeçalho:** `feat: permitir exportacao customizada` (evite maiúsculas sem necessidade).
5. **Separe o assunto do corpo com uma linha em branco:** O Git usa a primeira linha como título e o restante como descrição detalhada.
6. **No corpo, foque no *porquê* e no *como*, não no *o quê*:** O diff do Git já mostra o que mudou; explique a razão da abordagem.
7. **Referencie planos e tarefas:** Exemplo: `Ref: planejamento/2026-09-19_01_validacao_upload.md`.
8. **SEMPRE utilize nomenclatura e idioma em pt-BR.**

---

### 9.5 Boas Práticas Operacionais no Fluxo do Git

#### 1. Commits Atômicos (*Atomic Commits*)
- Faça commits pequenos que contenham apenas **uma alteração lógica**.
- Nunca misture refatoração de código com correções de bug ou novas funcionalidades no mesmo commit.
- Vantagem: se for necessário fazer `git revert` ou usar `git bisect`, você não desfaz alterações indesejadas.

#### 2. Higiene de Branches e Histórico
- **Mantenha a branch atualizada com `rebase`:** Antes de mesclar, faça o rebase com a branch base (`git pull --rebase origin master`) para manter um histórico linear e resolver conflitos localmente.
- **Squash Commits no Merge:** Agrupe múltiplos micro-commits de teste (`"ajuste"`, `"conserto"`) em um único commit coeso ao mesclar.
- **Deletar branches mescladas:** Mantenha o repositório limpo após o merge de branches de funcionalidade.

#### 3. O Que NUNCA Versionar
- **Segredos e Credenciais:** Tokens, senhas, chaves privadas, certificados `.pem`.
- **Artefatos de Build e Ambientes:** `.venv/`, `__pycache__/`, `dist/`, `.pytest_cache/`.
- **Bancos de Dados Locais e Arquivos Temporários:** `taguette.sqlite3`, arquivos `.tmp`, logs.
- **Arquivos da IDE e do Sistema:** `.vscode/`, `.idea/`, `Thumbs.db`, `.DS_Store`.
- **Solução:** O `.gitignore` do repositório deve estar rigorosamente configurado e respeitado.

#### 4. Gestão de Tags e Releases (SemVer)
Adote o **Versionamento Semântico** (`MAJOR.MINOR.PATCH`):
- **MAJOR (v2.0.0):** Quebra de compatibilidade com versões anteriores.
- **MINOR (v1.6.0):** Adição de nova funcionalidade retrocompatível.
- **PATCH (v1.5.3):** Correção de bugs retrocompatível.

Use tags anotadas:
```powershell
git tag -a v1.6.0 -m "Release v1.6.0: Incrementos de seguranca e governanca"
git push origin v1.6.0
```
