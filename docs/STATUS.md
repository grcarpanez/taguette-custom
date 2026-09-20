# STATUS.md - Acompanhamento Vivo de Evolução do Projeto Taguette

Este documento é a bússola operacional do projeto. Ele deve ser consultado e atualizado obrigatoriamente a cada ciclo de entrega para registrar onde estamos, o que já foi concluído e para onde devemos ir.

**Última Atualização:** 20/09/2026  
**Status Atual:** Fase 2 Concluída e Refinada com 100% de Sucesso nos Testes Automatizados (37/37 OK)  
**Responsável Técnico:** Antigravity AI & Desenvolvedor  

---

## 1. Visão Geral do Progresso

| Macro-Fase | Descrição Resumida | Status | Progresso |
| :--- | :--- | :--- | :---: |
| **Fase 0** | Governança, Diretrizes de Agentes (`AGENTS.md`), Blindagem Git e Setup | **Concluído** | 100% |
| **Fase 1** | Especificação Funcional do Sistema (`docs/FSD.md`) e Mapeamento de Incrementos | **Concluído** | 100% |
| **Fase 2** | Desenvolvimento do Incremento (Hierarquia, Exportações e Ontotext) | **Concluído** | 100% |
| **Fase 3** | Criptografia Simétrica de Dados Sensíveis e Hardening de Sessões/RBAC | **Pendente** | 0% |
| **Fase 4** | Melhorias Funcionais, Testes Automatizados e Auditoria de Produção | **Pendente** | 0% |

---

## 2. Checklist Detalhado por Fase

### Fase 0: Governança, Diretrizes e Blindagem do Ambiente
- [x] Inspeção completa da stack tecnológica (Python 3.10, Tornado, SQLAlchemy, Alembic, Jinja2, Poetry, Calibre).
- [x] Correção e consolidação dos locais de arquivos:
  - `AGENTS.md` posicionado na raiz do repositório (`D:\Taguette\taguette\AGENTS.md`).
  - Planos de implementação consolidados em `planejamento/`.
  - Documentação viva consolidada em `docs/` (`FSD.md`, `STATUS.md`, `ERROS.md`).
- [x] Redação exaustiva do `AGENTS.md` com arquitetura, comandos, RBAC, governança e Conventional Commits.
- [x] Blindagem do repositório Git:
  - Remote original renomeado para `upstream`.
  - Push para upstream desativado permanentemente (`no_push`).
- [x] Configuração do repositório remoto pessoal do usuário (`origin`) para sincronização e backup na nuvem.
- [x] Commit inicial e push de governança na branch principal (`origin/master`).

---

### Fase 1: Especificação Funcional do Sistema (`docs/FSD.md`)
- [x] Entrevista estruturada com o usuário alinhando requisitos, regras de negócio e UX.
- [x] Mapeamento dos requisitos de negócio e motivadores dos incrementos no Taguette.
- [x] Especificação da exportação da `Description` em destaques (CSV, XLSX, DOCX, HTML, PDF).
- [x] Especificação da hierarquização relacional de tags (taxonomia N-níveis e delimitador `|`).
- [x] Especificação da experiência de usuário (UX) no modal (breadcrumbs, drill-down, chips com estado duplo e salto rápido).
- [x] Especificação da visualização em árvore na barra lateral esquerda e navegação no painel direito.
- [x] Especificação da integração semântica com Ontotext Refine (colunas `_note` dinâmicas e geração de `mapping.json`) e Turtle (`.ttl`).
- [x] Redação exaustiva do `docs/FSD.md` concluída.
- [x] Aprovação formal do `docs/FSD.md` e do Implementation Plan com autorização de execução (`Proceed`).

---

### Fase 2: Desenvolvimento do Incremento (Hierarquia, Exportações e Ontotext)
- [x] Elaboração e aprovação do Implementation Plan da Fase 2 em `planejamento/`.
- [x] Implementação de `parent_id` no modelo `Tag` e migração Alembic (`8f2a1b9c0d1e_add_tag_parent_id.py`).
- [x] Validações de nomes e regras de API no backend:
  - Bloqueio estrito do caractere `|` em nomes de tags (`taguette/validate.py`).
  - Prevenção em tempo real de auto-parentesco e ciclos ascendentes (`TagUpdate`).
  - Exclusão com promoção de descendentes (`action='promote'`) ou exclusão em cascata (`action='cascade'`).
  - Mesclagem com reparentamento de toda a descendência e fusão de descrições (`TagMerge`).
  - Propagação via websocket/long-polling de `parent_id` nos eventos em tempo real (`Command.tag_add`).
- [x] Camada de exportação:
  - Planilhas CSV e XLSX com colunas `tag_path` e `tag_note` (com auto-ajuste de largura e text wrap no Excel).
  - Livro de Códigos Interativo em árvore com busca e nós recolhíveis (`/project/<id>/export/codebook_tree.html`).
  - Planilha matricial Ontotext Refine (`/project/<id>/export/ontotext.csv`) com colunas `<tag>_note` dinâmicas (apenas se preenchidas).
  - Gerador de mapeamento semântico `mapping.json` Ontotext Refine (`/project/<id>/export/ontotext_mapping.json`) com `owl:Class`, `rdfs:subClassOf`, `dcterms:description` e `rdfs:comment`.
  - Exportação direta em Turtle RDF (`/project/<id>/export/codebook.ttl`).
  - Exportação transposta de destaques (matriz para Ontotext / Modelo Aba 2) com metadados verticais e tratamento de fórmulas no XlsxWriter (`strings_to_formulas: False`).
  - Preservação obrigatória de classes ancestrais com descendentes populados até a raiz na exportação de destaques (`INC-001`), eliminando erros de colunas inexistentes no Ontotext Refine ao importar `mapping.json`.
  - Refinamento do gerador `mapping.json`: vinculação dinâmica de `rdfs:comment` à coluna `<tag>_note` no sujeito da classe `owl:Class` (`INC-002`), eliminando o valor estático chumbado e a duplicata conflitante nas instâncias GREL.
- [x] Frontend:
  - Árvore lateral recursiva com setas expansíveis (`▶ / ▼`) e botão rápido `➕ Subtag`.
  - Painel de destaques exibindo cabeçalho da categoria, full path, anotação e cards de subtags.
  - Modal de marcação com Trilha de Pastas (*Breadcrumbs*), criação contextual de subtags e Barra de Chips com Estado Duplo (1 clique desmarca/risca em vermelho; 2 cliques salta para a pasta da tag com rolagem suave).
  - Modais com pré-visualização "Antes e Depois" para reorganização de galhos e mescla.
  - Correção de ancoragem de dropdowns de exportação à direita com `data-display="static"`.
- [x] Detecção do Sistema:
  - Auto-detecção de caminhos padrão do Calibre no Windows (`C:\Program Files\Calibre2`) e macOS em `taguette/convert.py`.
- [x] Testes automatizados na suíte completa (`py -3.10 -m poetry run python tests.py`):
  - **37 testes executados e aprovados com 100% de sucesso (OK).**

---

### Fase 3: Criptografia Simétrica e Fortalecimento de Sessões/RBAC
- [ ] Elaboração do Implementation Plan da Fase 3 em `planejamento/`.
- [ ] Aprovação do plano pelo usuário (`Proceed`).
- [ ] Implementação de camada de criptografia simétrica autenticada para dados sensíveis em repouso.
- [ ] Auditoria e endurecimento do controle de acesso baseado em papéis (RBAC).
- [ ] Testes automatizados de controle de acesso e proteção de dados.

---

## 3. Próximos Passos Imediatos

1. **Apresentação do Walkthrough ao Usuário:** Apresentar a correção das classes ancestrais populadas e instrução de testes.
2. **Git Commit e Push:** Commitar as alterações em `pt-BR` de acordo com Conventional Commits e sincronizar com o repositório remoto `origin/master`.
3. **Início da Fase 3:** Avançar para a implementação de segurança, cookies e criptografia conforme planejado.
