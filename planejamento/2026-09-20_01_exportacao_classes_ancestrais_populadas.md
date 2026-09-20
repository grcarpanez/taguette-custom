# Plano de Implementação: Preservação de Classes Ancestrais na Exportação de Destaques

**Data:** 20/09/2026  
**Status:** CONCLUÍDO COM SUCESSO (TESTES 100% APROVADOS)  
**Registro do Proceed:** "Pode executar, por favor" (20/09/2026 08:29)  
**Autor Técnico:** Antigravity AI & Desenvolvedor  
**Referência Canônica:** [docs/FSD.md](../docs/FSD.md)  

---

## 1. Contexto e Motivação
Na exportação do **Codebook** e na geração do **`mapping.json`**, a função `get_codebook_tags` já preserva todas as tags ancestrais de tags populadas através da subida na árvore (`parent_id`). Com isso, para uma estrutura `a > b > c > d > e` onde apenas `e` possui destaques:
- O `mapping.json` declara as classes `a`, `b`, `c`, `d`, `e`.
- Mapeia os axiomas `rdfs:subClassOf` entre elas.
- Mapeia instâncias para a coluna `a`, coluna `b`, coluna `c`, etc.

Porém, na exportação de **Destaques (*Highlights*)** em `taguette/export.py` (`_build_highlights_table` e `_build_highlights_table_transposed`):
- Quando `only_populated=True` (comportamento padrão quando a opção "incluir tags sem destaques" está desmarcada), o sistema filtrava estritamente as tags que possuíam destaques associados diretos (`used_tag_ids`).
- Como `a`, `b`, `c`, `d` não possuíam destaques diretos nelas mesmas, elas eram completamente omitidas da planilha gerada (tanto normal quanto transposta).
- Ao importar a planilha transposta no Ontotext Refine e carregar o `mapping.json`, o Ontotext acusava erro porque o mapeamento referenciava as colunas `a`, `b`, `c`, `d`, mas essas colunas não existiam no arquivo exportado.

---

## 2. Regra de Negócio Adaptada
- **Se `only_populated == True`:**
  - Incluir todas as tags diretamente associadas a destaques (`used_tag_ids`).
  - **Identificar e incluir todas as tags ancestrais** das tags diretamente associadas a destaques, subindo pela cadeia `parent_id` até a raiz do projeto.
  - Omitir apenas as tags que **não possuem destaques E não possuem nenhum descendente com destaques** (ex.: ramos inteiramente em branco como `x > y`).
- **Se `only_populated == False`:**
  - Incluir todas as tags do projeto (inclusive ramos totalmente em branco).

### Representação nas Planilhas
1. **Na Planilha Transposta (`_build_highlights_table_transposed`):**
   - As tags ancestrais que não possuem destaques diretos ganham uma coluna dedicada com:
     - `id`: vazio (`''`)
     - `document`: vazio (`''`)
     - `tag`: nome da tag (ex.: `a`)
     - `tag_path`: caminho completo (ex.: `a`)
     - `content`: vazio (`''`)
     - Coluna de nota `<tag>_note` (se possuir descrição e `include_notes=True`).
   - Com isso, a coluna `a` passa a existir fisicamente na planilha, atendendo 100% à exigência do Ontotext Refine.
2. **Na Planilha Regular (`_build_highlights_table`):**
   - As tags ancestrais ganham uma linha de referência com dados da tag e conteúdo de destaque em branco.

---

## 3. Arquivos Afetados
- `taguette/export.py`: Atualização em `_build_highlights_table` e `_build_highlights_table_transposed`.
- `tests.py`: Atualização de testes automatizados com cadeia hierárquica e tag isolada.
- `docs/STATUS.md`: Atualização do status vivo do projeto.
- `docs/ERROS.md`: Registro do incidente e prevenção.

---

## 4. Relatório de Execução e Verificação de Testes
- **Execução Técnica:**
  - Em `taguette/export.py`, mapeamento de `all_project_tags` e cálculo recursivo de `ancestor_ids` subindo por `parent_id`.
  - Inclusão automática das tags ancestrais (`extra_tag_ids = ancestor_ids - used_tag_ids`) quando `only_populated=True`, tanto no formato regular de destaques quanto na matriz transposta para Ontotext Refine.
- **Validação Automatizada:**
  - Adicionado caso de teste exaustivo em `tests.py` (`Pai > Filho > Neto` com destaque apenas em `Neto`, e tag isolada `IsoladoSemDestaque`).
  - Execução da suíte completa de testes:
    ```powershell
    py -3.10 -m poetry run python tests.py
    ```
  - **Resultado:**
    ```text
    Ran 37 tests in 13.040s
    OK (skipped=2)
    ```
  - 100% dos testes aprovados com sucesso.
