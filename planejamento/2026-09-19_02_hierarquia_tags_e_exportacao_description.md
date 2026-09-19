# Plano de Implementação: Hierarquização de Tags, Exportação de Description e Interoperabilidade Semântica

**Data:** 19/09/2026  
**Status:** CONCLUÍDO COM SUCESSO (TESTES 100% APROVADOS)  
**Registro do Proceed:** "Verifique os comentários, se necessário, faça alteração no plano e execute." (19/09/2026 19:41)  
**Referência Canônica:** [docs/FSD.md](../docs/FSD.md)  
**Autor Técnico:** Antigravity AI & Desenvolvedor  

---

## 1. Contexto e Objetivos Executados
Implementação integral das funcionalidades aprovadas no `docs/FSD.md`:
1. **Exportação da `Description`:** Inclusão nas exportações de destaques (*highlights*) em CSV, Excel, HTML, DOCX e PDF com cabeçalho de anotação `tag_note` e quebra automática de texto (`text_wrap: True`) no Excel com largura calibrada pelo cabeçalho.
2. **Hierarquização Relacional de Tags:** Modelagem N-níveis com `Tag.parent_id`, relacionamentos autorreferenciais, prevenção de ciclos e delimitador canônico de exibição ` | `.
3. **UX Avançada de Criação e Navegação no Frontend:**
   - **Pontos de Entrada para Subtags:** Botão de ação rápida `➕ Subtag` na árvore da barra lateral e link contextual dinâmico `➕ Create a subtag in 'pasta_atual'` no rodapé do modal de destaques.
   - **Modal de Destaques:** Trilha de *Breadcrumbs* com *Drill-Down*, barra de tags selecionadas com cartões de estado duplo (1 clique desmarca/marca sem sumir; 2 cliques salta para o nível da tag com rolagem horizontal suave).
   - **Reorganização de Galhos (Re-parenting):** Mudança de "Tag-Pai" no formulário de edição com modal de confirmação inteligente exibindo pré-visualização visual do *"Antes e Depois"*.
   - **Exclusão Segura:** Opção de promover toda a cascata de descendentes em uma geração na árvore (`action='promote'`) ou exclusão em cascata (`action='cascade'`).
   - **Mesclagem Segura:** Reparentamento de toda a descendência (filhas, netas, etc.) para a tag receptora e fusão de descrições separadas por `; `.
   - **Barra Lateral e Painel Direito:** Árvore interativa com expandir/recolher (`▶ / ▼`) e exibição de subtags navegáveis no painel de destaques.
4. **Interoperabilidade com Ontotext e Web Semântica:**
   - Planilha matricial Ontotext Refine com colunas de anotação `<Tag>_note` criadas apenas se a descrição existir.
   - Geração automática do arquivo `mapping.json` (com `owl:Class`, `rdfs:subClassOf`, `dcterms:description` e `rdfs:comment`).
   - Codebook em HTML Interativo (`/project/<id>/export/codebook_tree.html`) e exportação direta em Turtle RDF (`/project/<id>/export/codebook.ttl`).

---

## 2. Arquivos Afetados e Módulos Técnicos

### 2.1 Banco de Dados e Migrações
* `taguette/database/models.py`: Coluna `Tag.parent_id`, relacionamentos autorreferenciais (`parent` e `children` com `passive_deletes=True`), método `full_path(' | ')`, atualização de `Command.tag_add` para incluir `parent_id`.
* `taguette/database/copy.py`: Cópia retrocompatível preservando a hierarquia relacional entre projetos.
* `taguette/migrations/versions/8f2a1b9c0d1e_add_tag_parent_id.py`: Migração Alembic com `batch_alter_table` para SQLite3.

### 2.2 Validação e API REST
* `taguette/validate.py`: Validação do nome individual da tag (até 200 caracteres) com bloqueio do delimitador `|`.
* `taguette/web/api.py`: `TagAdd` com `parent_id`, `TagUpdate` com detector de ciclos em tempo real, `TagDelete` com promoção segura de descendentes ou cascata, `TagMerge` com reparentamento de linhagem e fusão de descrições, e `Highlights`.
* `taguette/web/views.py`: Envio de `parent_id` em `tags_json` para o frontend.

### 2.3 Camada de Exportação
* `taguette/export.py`: Suporte a `tag_note` e `tag_path` em CSV/XLSX com text-wrapping, exportação Ontotext Refine (com `<tag>_note` dinâmico), gerador de `mapping.json`, exportação Turtle (`.ttl`) e HTML interativo.
* `taguette/web/export.py` e `taguette/web/__init__.py`: Handlers HTTP e rotas de exportação com prioridade de roteamento correta.
* `taguette/templates/export_codebook_tree.html`: Template autônomo e interativo do Livro de Códigos.

### 2.4 Interface do Usuário (Frontend)
* `taguette/templates/project.html`: Containers de breadcrumbs, barra de tags selecionadas, modais de confirmação visual com preview para exclusão, mescla e reorganização (mover galho), seletor de tag-pai e opções no menu de exportação.
* `taguette/static/js/taguette.js`: Árvore recursiva na barra lateral com botão `➕ Subtag`, drill-down por breadcrumbs no modal com criação contextual, cartões de estado duplo e salto com duplo clique, visualizador antes/depois para re-parenting, e sincronização via long-polling.

---

## 3. Relatório de Verificação e Testes
* Execução completa da suíte de testes automatizados:
  ```powershell
  py -3.10 -m poetry run python tests.py
  ```
* **Resultado:**
  ```text
  Ran 36 tests in 13.130s
  OK (skipped=2)
  ```
  - 32 testes legados mantidos e atualizados.
  - 4 novos testes unitários e de integração adicionados em `TestMultiuser`:
    1. `test_tag_hierarchy_validation_and_crud`: Validação de ciclo, bloqueio de `|`, CRUD de pais/filhos.
    2. `test_tag_delete_promote_and_cascade`: Exclusão com promoção de descendência e exclusão em cascata.
    3. `test_tag_merge_reparent_and_descriptions`: Mesclagem com reparentamento de filhos e concatenação de descrições.
    4. `test_semantic_and_tree_exports`: Validação de CSV Ontotext (`_note` condicional), JSON de mapeamento com `rdfs:subClassOf`, Turtle RDF (`.ttl`) e Livro de Códigos HTML em árvore.
