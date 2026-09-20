# ERROS.md - Histórico Vivo de Incidentes, Causas Raiz e Lições Técnicas

Este documento registra todas as falhas, erros de compilação/testes, regressões ou incidentes encontrados durante o desenvolvimento do projeto **Taguette**, servindo como base de conhecimento preventivo para agentes e desenvolvedores.

---

## Estrutura Padrão de Registro de Incidentes

Cada novo incidente deve ser registrado com o modelo abaixo:

```markdown
### [INC-NNN] YYYY-MM-DD - Título Curto do Incidente
- **Módulo / Arquivo Afetado:** Caminho relativo do arquivo (ex: `taguette/convert.py`).
- **Sintoma / Erro:** Mensagem de erro exata ou comportamento anômalo observado.
- **Causa Raiz:** O que provocou a falha no nível técnico.
- **Solução Aplicada:** O que foi modificado para corrigir o problema.
- **Como Prevenir:** Diretriz ou teste automatizado para evitar reincidências.
```

---

## Histórico de Incidentes

### [INC-001] 2026-09-20 - Omissão de Classes Ancestrais com Filhos Populados na Exportação de Destaques
- **Módulo / Arquivo Afetado:** `taguette/export.py` (`_build_highlights_table` e `_build_highlights_table_transposed`).
- **Sintoma / Erro:** No Ontotext Refine, ao importar o `mapping.json` gerado a partir do codebook para uma planilha transposta de destaques com `only_populated=True`, o sistema acusa erro de que colunas referenciadas não existem no arquivo de dados.
- **Causa Raiz:** O filtro `only_populated=True` na exportação de destaques considerava exclusivamente as tags associadas diretamente aos destaques (`used_tag_ids`). Em taxonomias hierárquicas como `a > b > c > d > e`, se apenas `e` possuía destaques diretos, as tags ancestrais `a`, `b`, `c`, `d` eram excluídas da planilha por não terem destaques próprios, embora fossem mantidas no `mapping.json` e no codebook.
- **Solução Aplicada:** Adaptação da regra de negócio para rastrear os ancestrais das tags associadas a destaques subindo por `parent_id` até a raiz do projeto. As tags ancestrais que não possuem destaques diretos passam a ser incluídas obrigatoriamente (`extra_tag_ids = ancestor_ids - used_tag_ids`) com colunas dedicadas na planilha transposta e linhas de referência na planilha regular, garantindo a presença de todas as colunas mapeadas.
- **Como Prevenir:** Caso de teste automatizado específico implementado em `tests.py` (`test_semantic_and_tree_exports`), que cria uma hierarquia `Pai > Filho > Neto` com destaque exclusivo em `Neto` e valida a presença obrigatória de `Pai` e `Filho` e a ausência de tags isoladas sem destaques (`IsoladoSemDestaque`).

### [INC-002] 2026-09-20 - Duplicação e Referência Estática de `rdfs:comment` no `mapping.json`
- **Módulo / Arquivo Afetado:** `taguette/export.py` (`ontotext_mapping_json`) e `tests.py`.
- **Sintoma / Erro:** No Ontotext Refine, o predicado `rdfs:comment` era registrado duas vezes (uma vez na declaração da classe `owl:Class` como uma constante fixa exibida como `: teste`, e outra vez no sujeito GREL das instâncias de destaque apontando para a coluna `<tag>_note`), causando conflito de referências no Refine e inconsistência semântica.
- **Causa Raiz:** O gerador continha dois blocos adicionando `rdfs:comment`. No primeiro bloco (classes), o valor de `tag.description` foi inserido como `"source": "constant"` acompanhado indevidamente de `"transformation": {"expression": "", "language": "prefix"}`. No segundo bloco (GREL), o `rdfs:comment` foi adicionado a cada instância individual de destaque, duplicando o comentário que pertence conceitualmente à classe.
- **Solução Aplicada:** No sujeito da classe (`owl:Class`), o valor de `rdfs:comment` passou a ser dinâmico referenciando a coluna da planilha (`"source": "column", "columnName": f"{clean_name}_note"`), e o bloco de `rdfs:comment` foi removido das instâncias GREL (que mantêm exclusivamente `dcterms:description`).
- **Como Prevenir:** Asserção estrita no teste automatizado `test_semantic_and_tree_exports` verificando que `"columnName": "A_note"` está presente e que nenhum sujeito GREL possui propriedade `comment`.
