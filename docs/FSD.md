# FSD.md - Especificação Funcional do Sistema (Functional Specification Document)

**Projeto:** Taguette - Sistema de Análise Qualitativa de Dados Textuais  
**Versão do Documento:** 1.0.0  
**Data:** 19/09/2026  
**Status:** Aguardando Aprovação Formal  
**Autores / Colaboradores:** Desenvolvedor & Antigravity AI  

---

## 1. Visão Geral e Objetivos do Incremento

### 1.1 Contexto e Justificativa
O **Taguette** é uma ferramenta de código aberto voltada para Análise Qualitativa de Dados Textuais (QDA). O sistema permite importar documentos, criar códigos/etiquetas (*tags*) e destacar trechos de texto (*highlights*), associando-os a uma ou mais tags.

Embora o sistema preveja originalmente em sua interface de apresentação a capacidade de *"create a hierarchy of tags"* e contenha notas técnicas em seu código (`// TODO: Show this as a tree`), a versão original implementou apenas uma estrutura plana de tags. Adicionalmente, a anotação conceitual das tags (**`Description`**) é subutilizada, aparecendo somente no Livro de Códigos (*Codebook*) e sendo omitida na exportação de trechos destacados (*Highlights*).

### 1.2 Objetivos Centrais do Incremento
1. **Exportação Plena da `Description`:** Disponibilizar a descrição conceitual das tags nas exportações de destaques (*Highlights*) e esteiras analíticas, garantindo a rastreabilidade das anotações conceituais dos pesquisadores.
2. **Hierarquização Completa de Tags (Taxonomia N-Níveis):** Permitir a criação de categorias, subcategorias, netas e sucessivas descendentes, com relações estritas de parentesco relacional no banco de dados.
3. **Experiência de Usuário (UX) Avançada e Segura:**
   - Navegação por *Drill-Down* com *Breadcrumbs* no modal de marcação de texto.
   - Barra de tags selecionadas com cartões de estado duplo (marcação/desmarcação segura com proteção contra perda de contexto e salto rápido na árvore).
   - Exibição da taxonomia em árvore interativa com recolhimento/expansão (`▶ / ▼`) na barra lateral esquerda.
   - Painel de destaques estruturado com navegação hierárquica e navegação para subtags filhas.
   - Regras seguras de exclusão (promoção de nível vs. cascata) e mesclagem (*merge*) com reparentamento e fusão de descrições.
4. **Interoperabilidade com a Web Semântica e Grafos de Conhecimento:**
   - Exportação direta para **Ontotext Refine** (planilha matricial com colunas de anotação `_note` criadas sob demanda).
   - Geração automática do arquivo **`mapping.json`** sob medida para o projeto no Ontotext Refine, definindo `owl:Class`, `rdfs:subClassOf`, `dcterms:description` e `rdfs:comment`.
   - Exportação em **HTML Interativo** da árvore de tags para exploração visual dinâmica.
   - Exportação direta no padrão **Turtle (`.ttl` / RDF)** para ingestão direta no Ontotext GraphDB, Protégé e Apache Jena.

---

## 2. Modelagem do Banco de Dados e Migrações Alembic

### 2.1 Modelo Existente (`Tag`)
Originalmente, a tabela `tags` possui:
- `id` (INTEGER, Primary Key, Autoincrement)
- `project_id` (INTEGER, Foreign Key para `projects.id`, ondelete='CASCADE')
- `path` (VARCHAR(200), Not Null, Index)
- `description` (TEXT, Not Null)

### 2.2 Alterações Estruturais no Banco de Dados
Para suportar hierarquia relacional pura e retrocompatível:
1. **Adição da coluna `parent_id` na tabela `tags`:**
   - Tipo: `INTEGER`, anulável (`nullable=True`).
   - Chave Estrangeira: `ForeignKey('tags.id', ondelete='RESTRICT')` ou tratada em nível de aplicação com opções de cascata/promoção.
   - Índice: `index=True` para otimização de consultas de árvores genealógicas.
   - `Tag.parent`: relacionamento `relationship('Tag', remote_side=[id], backref='children')`.
2. **Delimitador Canônico de Caminho Textual:**
   - Fica padronizado o caractere pipe **`|`** como delimitador de níveis para exibições e representações em texto (ex: `Pai | Filho | Neto`).
   - O validador `validate.tag_path` bloqueará expressamente o caractere `|` no nome individual de qualquer tag, evitando ambiguidades e quebras de separação.
3. **Nova Migração Alembic:**
   - Script versionado em `taguette/migrations/versions/` (ex: `add_tag_parent_id.py`).
   - Suporte verificado e testado para SQLite3 (utilizando `batch_alter_table` para contornar limitações de DDL do SQLite), PostgreSQL e MariaDB.

---

## 3. Especificação Detalhada das Interfaces e Experiência do Usuário (Frontend)

### 3.1 Modal de Seleção de Tags em Destaques (*Highlight Modal*)
Quando o pesquisador seleciona um trecho de texto no documento, o modal de marcação oferece:

1. **Campo de Busca Rápida (*Find tags*):**
   - Filtragem dinâmica com destaque nos termos correspondentes.
2. **Barra de Tags Selecionadas (No topo do modal):**
   - Posicionamento: Abaixo da busca rápida e acima da trilha de navegação.
   - Altura máxima fixa com rolagem vertical suave calibrada (`scroll-behavior: smooth`) para nunca estourar a tela.
   - Cada tag vinculada ao destaque é renderizada como um cartão/chip compacto contendo:
     - Nome da tag folha.
     - *Tooltip* ao passar o mouse ou foco exibindo o caminho hierárquico completo: `Caminho: Categoria | Subcategoria | Tag`.
     - Indicador `×` de desmarcação.
   - **Comportamento Interativo Inteligente (Dois Estados):**
     - **1 Clique:** Alterna o estado visual do cartão para *Desmarcado/Riscado em Vermelho*. Isso desmarca a caixa de seleção daquela tag no nível correspondente. O cartão permanece visível na barra para que o pesquisador possa reativá-lo com mais 1 clique caso mude de ideia, sem perder o contexto nem ter que navegar novamente por toda a árvore.
     - **2 Cliques:** Executa o *Salto Rápido* na árvore, navegando o modal diretamente para a pasta/nível onde a tag reside, exibindo seus irmãos.
3. **Trilha de Navegação (*Breadcrumbs*) e Lista com *Drill-Down*:**
   - Botão raiz fixo: `🏠 Início`.
   - Conforme o usuário clica no nome de uma tag que possui filhas, o modal aprofunda na pasta e o cabeçalho registra: `🏠 Início ➔ nome_fantasia ➔ filho_1`.
   - Cada nível exibe caixas de seleção (*checkboxes*) para marcar/desmarcar as tags daquele nível.
   - Quebra automática de linha responsiva no breadcrumb para árvores profundas.
   - Clicar em qualquer termo da trilha de breadcrumbs retorna a navegação imediatamente àquele nível ancestral.

### 3.2 Barra Lateral Esquerda (Aba *Highlights*)
1. **Estrutura em Árvore:**
   - Substituição da lista plana por uma árvore hierárquica recuada (*treeview*).
   - Ícones de expansão e colapso (`▶` para recolhido, `▼` para expandido) ao lado de tags que possuem descendentes.
   - Exibição de badge com a contagem de ocorrências diretas e acumuladas do ramo.
   - Botão `Edit` ao lado de cada tag para edição de metadados e parentesco.
2. **Ação de Filtragem:**
   - Clicar no link de uma tag-pai carrega no painel direito os destaques vinculados.

### 3.3 Painel Direito de Visualização de Destaques (`/project/<id>/highlights/<path>`)
1. **Cabeçalho com Trilha de Navegação (*Breadcrumb*):**
   - Exibe o caminho completo da tag em visualização: `🏠 Início ➔ Categoria ➔ Subcategoria`.
2. **Corpo de Destaques:**
   - Exibe a lista de trechos de texto anotados com aquela tag.
3. **Seção de Subtags Filhas (No rodapé da visualização):**
   - Lista visualmente as subtags filhas diretas.
   - Cada cartão de subtag exibe seu nome, contagem de ocorrências e funciona como link navegável para abrir a visão daquela subtag, atualizando a trilha de navegação.

### 3.4 Fluxos de Criação e Reorganização de Tags e Subtags
1. **Pontos de Entrada para Criação de Subtags:**
   - **Na Barra Lateral Esquerda (Árvore Principal):** Cada tag da árvore exibirá, ao lado do botão `Edit`, um botão de ação rápida **`➕ Subtag`** (ou `+`). Ao clicar nele, o modal de criação abre imediatamente com o título *"Nova subtag em: [Nome da Tag Pai]"*, trazendo a tag pai selecionada e travada.
   - **No Modal de Destaques (*Highlight Modal*):** O rodapé da listagem se adapta contextualmente. Se o usuário estiver na raiz (`🏠 Início`), exibe `➕ Create a tag`. Se o usuário tiver navegado para dentro de uma pasta (ex: `nome_fantasia ➔ filho_1`), o link no rodapé altera dinamicamente para: `➕ Create a subtag in 'filho_1'`. Ao salvar, a nova subtag já aparece dentro daquela pasta e já vem marcada para o destaque de texto em edição.
2. **Campos do Formulário de Criação/Edição:**
   - `Parent Tag`: Campo de seleção (*dropdown* hierárquico com recuo) listando todas as tags existentes, com opção padrão *"Nenhuma (Raiz)"*.
   - `Name`: Nome individual exclusivo daquela tag (até 200 caracteres, bloqueando o caractere delimitador `|`). O usuário digita apenas o nome específico do nó; o caminho hierárquico completo (`Pai | Filho | Neto`) é montado automaticamente pelo sistema, com suporte a profundidades arbitrárias sem truncamento.
   - `Description`: Caixa de texto para anotações conceituais do pesquisador.
3. **Reorganização de Árvore (Mover Galho / Re-parenting):**
   - Ao editar uma tag existente e alterar o campo `Parent Tag`, a tag selecionada e **toda a sua árvore de descendentes** são transferidas para o novo galho pai (sem excluir a tag pai anterior).
   - **Modal de Pré-visualização e Confirmação Segura:**  
     Assim como na mescla, ao alterar a tag-pai de um galho que possui descendentes, o sistema abrirá um modal de confirmação exibindo visualmente o *"Antes e Depois"* da árvore resultante para que o usuário verifique e confirme a operação antes de salvar.

---

## 4. Regras de Negócio, Integridade e Prevenção de Inconsistências

### 4.1 Exclusão de Tag com Descendentes
Ao solicitar a exclusão de uma tag que possui filhas ou netas, o sistema não realiza exclusão silenciosa nem trava sem explicação. Um modal de decisão oferece as seguintes opções ao usuário:
1. **Promover Subtags (Subir 1 nível):**  
   A tag selecionada é excluída. Todas as suas filhas imediatas são promovidas para o nível superior que o pai ocupava (se o pai era raiz, as filhas viram raiz; se o pai era filho de X, as filhas viram filhas de X). Os trechos destacados pelas filhas permanecem 100% íntegros.
2. **Excluir em Cascata:**  
   A tag selecionada e todas as suas subtags, netas e descendentes são excluídas em bloco, desvinculando-se dos destaques de texto. Exige digitação de confirmação ou confirmação explícita em botão de perigo.
3. **Cancelar:** Aborta a operação sem qualquer mutação de dados.

### 4.2 Mesclagem (*Merge*) de Tags
Na operação de mesclar duas tags (onde Tag Origem será desativada e absorvida por Tag Destino):
1. **Direção Inequívoca:** A interface indicará textualmente de forma clara: *"A tag [Origem] será eliminada e todo o seu conteúdo será absorvido pela tag [Destino]"*.
2. **Reparentamento de Linhagem:** Todas as filhas e a árvore de descendência da Tag Origem passam a ser filhas da Tag Destino, preservando a ramificação.
3. **Preservação de Descrições:**  
   - Caixa de seleção (*checkbox*): *"Preservar descrição da tag que deixará de existir"*.
   - Se marcada: Caso a Tag Destino já possua descrição, o texto da Tag Origem é concatenado ao final, separado por `; ` (ponto e vírgula com espaço). Se a Tag Destino não tinha descrição, recebe a descrição da Origem integralmente.
4. **Pré-visualização e Confirmação Segura:**  
   O modal apresentará um resumo visual de como a árvore resultante ficará antes da gravação definitiva no banco.

### 4.3 Prevenção contra Ciclos e Recursão Infinita
- O backend validará estritamente que uma tag não pode ser definida como pai de si mesma, nem como filha de qualquer uma de suas próprias descendentes diretas ou indiretas.
- Tentativas de criação de ciclos retornarão erro HTTP 400 (*Bad Request*) com mensagem amigável ao usuário.

---

## 5. Especificação das Exportações e Interoperabilidade Semântica

### 5.1 Exportação de Destaques (*Highlights*) em Formatos Tradicionais
Disponível em *"Export this view"* (para o projeto completo ou filtrado por tag):
1. **CSV e Excel (XLSX):**
   - Novas colunas estruturadas:
     - `id`: Identificador do destaque.
     - `document`: Nome do documento de origem.
     - `tag`: Nome da tag folha.
     - `tag_path`: Caminho hierárquico completo separado pelo delimitador padrão `|` (ex: `Categoria | Subcategoria | Tag`).
     - `description`: Conteúdo textual da descrição da tag.
     - `content`: Trecho de texto literal destacado.
   - Em caso de trechos com múltiplas tags, cada par `(tag_path, description)` é exportado na respectiva linha.
2. **Documentos Textuais (HTML, DOCX, PDF):**
   - Cada bloco de destaque exibe o trecho, o documento e, para cada tag associada, o caminho hierárquico e a sua descrição em itálico/bloco descritivo.

### 5.2 Exportação do Livro de Códigos (*Codebook*) em HTML Interativo
Na aba *Project info* -> *Export codebook*:
- Nova opção: **HTML Interativo**.
- Gera um documento web independente (HTML + CSS + JS embutidos) contendo a árvore de tags do projeto em formato expansível/retrátil, exibindo descrições, número de documentos e ocorrências de destaques, permitindo busca e navegação visual offline.

### 5.3 Exportação Especializada para Ontotext Refine e Web Semântica
O Taguette fornecerá um módulo de exportação dedicado a grafos de conhecimento e ontologias:

#### A) Planilha Matriz de Dados (CSV / Excel para Ontotext Refine)
- Cada classe/tag utilizada é exportada como uma coluna contendo o trecho de texto literal (destaque), pronto para ser mapeado como `dcterms:description`.
- **Regra de Omissão Consciente da Coluna de Descrição:**  
  A coluna companheira de anotação com o sufixo **`_note`** (ex: `<Tag>_note`), destinada a alimentar o **`rdfs:comment`**, **somente será gerada se a tag possuir o campo `Description` preenchido**. Tags sem descrição não terão colunas `_note` vazias, mantendo a planilha limpa e otimizada.

#### B) Geração Automática do Arquivo `mapping.json` (Ontotext Refine)
O Taguette gerará e exportará o arquivo de configuração de mapeamento RDF para o Ontotext Refine contendo:
- Declaração de `baseIRI` e namespaces (`rdf`, `rdfs`, `owl`, `xsd`, `dcterms`, `resource`).
- Mapeamento de todas as tags como sujeitos de tipo `owl:Class`.
- Mapeamento das relações de parentesco com a propriedade `rdfs:subClassOf`.
- Mapeamento dinâmico via GREL dos trechos marcados para instâncias `<Classe_rowIndex>` com `dcterms:description`.
- Mapeamento das anotações das colunas `_note` existentes para a propriedade `rdfs:comment`.

#### C) Exportação Direta em Turtle (`.ttl` / RDF)
Para importação direta no Ontotext GraphDB, Apache Jena ou Protégé sem passar pelo Refine:
- Gera a ontologia completa em sintaxe Turtle (`.ttl`), com as classes, axiomas de subclasse, anotações `rdfs:comment`, e as instâncias individuais dos trechos destacados vinculadas aos respectivos documentos de origem.

---

## 6. Arquitetura de Comunicação em Tempo Real e Eventos (`commands`)

Todas as mutações de hierarquia serão propagadas via long-polling para os demais usuários conectados através de novos campos no payload da tabela `commands`:
- `tag_add`: incluirá `parent_id` e `path_string`.
- `tag_update`: incluirá novo `parent_id`, `path_string` e lista de filhas afetadas.
- `tag_delete`: notificará o tipo de exclusão executada (cascata ou promoção de nível com novos `parent_id`s).
- `tag_merge`: notificará a fusão, as tags reparentadas e a nova descrição acumulada.

---

## 7. Critérios de Aceitação e Plano de Testes Automatizados

O incremento será validado na suíte oficial `tests.py` cobrindo:
1. **Testes Unitários de Modelagem e Banco:**
   - Criação de tags em múltiplos níveis de profundidade (pai, filho, neto, bisneto).
   - Validação de integridade referencial e migração Alembic.
   - Rejeição de ciclos de dependência em `Tag.parent_id`.
   - Rejeição de nomes de tags contendo o caractere pipe `|`.
2. **Testes de Regras de Negócio (Exclusão e Mescla):**
   - Teste de exclusão com promoção de subtags (+1 nível).
   - Teste de exclusão em cascata.
   - Teste de mescla com reparentamento de filhas e concatenação de `description` com `; `.
3. **Testes de Exportação:**
   - Validação das colunas `tag_path` e `description` nas exportações CSV e XLSX de destaques.
   - Validação da exportação do `mapping.json` e conformidade da sintaxe JSON.
   - Validação de que colunas `_note` só aparecem para tags que possuem descrição preenchida.
   - Validação da geração de arquivo Turtle (`.ttl`) com triplas bem formadas.
4. **Testes de Interface (Navegação):**
   - Teste funcional do modal de destaques: verificação do drill-down de breadcrumbs, alternância de estado de desmarcação no chip sem fechamento e salto duplo clique.
   - Teste de expansão/recolhimento da árvore na barra lateral.

---

## 8. Aprovação Formal do Documento

Este documento estabelece o contrato técnico e funcional definitivo para a implementação das funcionalidades no Taguette.

- [ ] **Aprovação do Usuário / Pesquisador:** Registrada formalmente no canal de desenvolvimento.
- [ ] **Data de Aprovação:** ___/___/2026
- [ ] **Próximo Passo:** Elaboração do Implementation Plan técnico da Fase de Desenvolvimento em `planejamento/`.
