import asyncio
import contextlib
import csv
import importlib_resources
import jinja2
import sqlalchemy
from markupsafe import Markup
import opentelemetry.trace
from sqlalchemy.orm import joinedload
import uuid
import xlsxwriter
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesNSImpl

from . import exact_version
from . import convert
from . import database
from . import extract


tracer = opentelemetry.trace.get_tracer(__name__)


template_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        [importlib_resources.files('taguette').joinpath('templates')],
    ),
    autoescape=jinja2.select_autoescape(['html']),
    extensions=['jinja2.ext.i18n'],
)


def _render_string(template_name, locale, **kwargs):
    translator = _Translator(locale)

    template = template_env.get_template(template_name)
    return template.render(
        version=exact_version(),
        gettext=translator.gettext,
        ngettext=translator.ngettext,
        pgettext=translator.pgettext,
        **kwargs,
    )


class _Translator(object):
    def __init__(self, locale):
        self.locale = locale

    def gettext(self, message, **kwargs):
        trans = self.locale.translate(message)
        if kwargs:
            trans = trans % kwargs
        return trans

    def ngettext(self, singular, plural, n, **kwargs):
        trans = self.locale.translate(singular, plural, n)
        if kwargs:
            trans = trans % kwargs
        return trans

    def pgettext(
        self,
        context, message, plural_message=None,
        n=None,
        **kwargs,
    ):
        trans = self.locale.pgettext(context, message, plural_message, n)
        if kwargs:
            trans = trans % kwargs
        return trans


class ExportTagInfo(object):
    """Representação estruturada de uma tag para exportação."""
    def __init__(self, id, path, full_path, description):
        self.id = id
        self.path = path
        self.full_path = full_path
        self.description = description or ""

    def __str__(self):
        return self.full_path


def _get_highlights_for_export(db, project_id, path):
    # Carregar todas as tags do projeto para montar full_path e obter descrições
    tags_by_id = {
        tag.id: tag
        for tag in db.query(database.Tag).filter(database.Tag.project_id == project_id).all()
    }

    if path:
        t_highlight = database.Highlight.__table__
        t_highlight_tag = database.highlight_tags
        t_tag = database.Tag.__table__
        t_document = database.Document.__table__
        t_highlight_tag_m = database.highlight_tags.alias()
        t_tag_m = database.Tag.__table__.alias()
        query = (
            sqlalchemy.select([
                t_highlight.c.id,
                t_highlight.c.snippet,
                t_document.c.name,
                t_tag.c.id,
            ])
            .select_from(
                t_highlight
                .join(
                    t_highlight_tag,
                    t_highlight.c.id == t_highlight_tag.c.highlight_id,
                )
                .join(
                    t_tag,
                    t_tag.c.id == t_highlight_tag.c.tag_id,
                )
                .join(
                    t_highlight_tag_m,
                    t_highlight.c.id == t_highlight_tag_m.c.highlight_id,
                )
                .join(
                    t_tag_m,
                    t_tag_m.c.id == t_highlight_tag_m.c.tag_id,
                )
                .join(
                    t_document,
                    t_document.c.id == t_highlight.c.document_id,
                )
            )
            .where(t_tag_m.c.path.startswith(path, autoescape=True))
            .where(t_document.c.project_id == project_id)
            .order_by(
                t_highlight.c.document_id,
                t_highlight.c.start_offset,
                t_highlight.c.id,
            )
        )
    else:
        t_highlight = database.Highlight.__table__
        t_highlight_tag = database.highlight_tags
        t_tag = database.Tag.__table__
        t_document = database.Document.__table__
        query = (
            sqlalchemy.select([
                t_highlight.c.id,
                t_highlight.c.snippet,
                t_document.c.name,
                t_tag.c.id,
            ])
            .select_from(
                t_highlight
                .join(
                    t_highlight_tag,
                    t_highlight.c.id == t_highlight_tag.c.highlight_id,
                )
                .join(
                    t_tag,
                    t_tag.c.id == t_highlight_tag.c.tag_id,
                )
                .join(
                    t_document,
                    t_document.c.id == t_highlight.c.document_id,
                )
            )
            .where(t_document.c.project_id == project_id)
            .order_by(
                t_highlight.c.document_id,
                t_highlight.c.start_offset,
                t_highlight.c.id,
            )
        )

    highlights = []
    for row in db.execute(query).fetchall():
        highlight_id, snippet, document, tag_id = row
        tag_obj = tags_by_id.get(tag_id) if tag_id is not None else None
        tag_info = (
            ExportTagInfo(
                id=tag_obj.id,
                path=tag_obj.path,
                full_path=tag_obj.full_path(),
                description=tag_obj.description,
            )
            if tag_obj
            else None
        )

        if highlights and highlights[-1][0] == highlight_id:
            if tag_info:
                highlights[-1][3].append(tag_info)
        else:
            highlights.append((
                highlight_id,
                snippet,
                document,
                [] if tag_info is None else [tag_info],
            ))

    return highlights


def get_filename_for_highlights_export(path):
    """Get a suitable filename for exported highlights.
    """
    if path:
        return None
    else:
        return 'all_tags'


def _build_highlights_table(db, project_id, path, include_notes=True, only_populated=True):
    highlights = _get_highlights_for_export(db, project_id, path)

    if include_notes:
        headers = ['id', 'document', 'tag', 'tag_path', 'tag_note', 'content']
    else:
        headers = ['id', 'document', 'tag', 'tag_path', 'content']

    rows = []
    used_tag_ids = set()
    for id, snippet, document, tags in highlights:
        content = convert.html_to_plaintext(snippet)
        if not tags:
            if include_notes:
                rows.append([str(id), document, '', '', '', content])
            else:
                rows.append([str(id), document, '', '', content])
        else:
            for tag in tags:
                used_tag_ids.add(tag.id)
                if include_notes:
                    rows.append([
                        str(id),
                        document,
                        tag.path,
                        tag.full_path,
                        tag.description,
                        content,
                    ])
                else:
                    rows.append([
                        str(id),
                        document,
                        tag.path,
                        tag.full_path,
                        content,
                    ])

    all_tags_q = db.query(database.Tag).filter(database.Tag.project_id == project_id)
    if path:
        all_tags_q = all_tags_q.filter(database.Tag.path.startswith(path))
    all_tags = all_tags_q.order_by(database.Tag.path).all()

    all_project_tags = {
        tag.id: tag
        for tag in db.query(database.Tag).filter(database.Tag.project_id == project_id).all()
    }

    # Identificar ancestrais de tags com destaques (para não deixar "filhas de fantasmas")
    ancestor_ids = set()
    for t_id in used_tag_ids:
        curr = all_project_tags.get(t_id)
        while curr and curr.parent_id:
            parent = all_project_tags.get(curr.parent_id)
            if parent:
                ancestor_ids.add(parent.id)
                curr = parent
            else:
                break

    if only_populated:
        # Se only_populated for True, as tags sem destaques diretos que possuem filhos populados (ancestrais)
        # DEVEM ser incluídas como linhas de referência para preservar a hierarquia completa
        extra_tag_ids = ancestor_ids - used_tag_ids
    else:
        # Se only_populated for False, todas as tags não utilizadas são incluídas
        extra_tag_ids = {tag.id for tag in all_tags} - used_tag_ids

    for tag in all_tags:
        if tag.id in extra_tag_ids:
            if include_notes:
                rows.append(['', '', tag.path, tag.full_path(), tag.description or '', ''])
            else:
                rows.append(['', '', tag.path, tag.full_path(), ''])

    return headers, rows


def _build_highlights_table_transposed(db, project_id, path, include_notes=True, only_populated=True):
    highlights = _get_highlights_for_export(db, project_id, path)

    headers = ['id', 'document', 'tag', 'tag_path', 'content']
    columns = []
    used_tag_ids = set()
    notes_added = set()

    for id, snippet, document, tags in highlights:
        content = convert.html_to_plaintext(snippet)
        if not tags:
            columns.append([str(id), document, '', '', content])
        else:
            for tag in tags:
                used_tag_ids.add(tag.id)
                columns.append([
                    str(id),
                    document,
                    tag.path,
                    tag.full_path,
                    content,
                ])
                if include_notes and tag.description and tag.id not in notes_added:
                    notes_added.add(tag.id)
                    columns.append([
                        '',
                        '',
                        f"{tag.path}_note",
                        '',
                        tag.description,
                    ])

    all_tags_q = db.query(database.Tag).filter(database.Tag.project_id == project_id)
    if path:
        all_tags_q = all_tags_q.filter(database.Tag.path.startswith(path))
    all_tags = all_tags_q.order_by(database.Tag.path).all()

    all_project_tags = {
        tag.id: tag
        for tag in db.query(database.Tag).filter(database.Tag.project_id == project_id).all()
    }

    # Identificar ancestrais de tags com destaques (para não deixar "filhas de fantasmas")
    ancestor_ids = set()
    for t_id in used_tag_ids:
        curr = all_project_tags.get(t_id)
        while curr and curr.parent_id:
            parent = all_project_tags.get(curr.parent_id)
            if parent:
                ancestor_ids.add(parent.id)
                curr = parent
            else:
                break

    if only_populated:
        # Se only_populated for True, as tags sem destaques diretos que possuem filhos populados (ancestrais)
        # DEVEM ser incluídas com colunas dedicadas para permitir a importação no Ontotext Refine
        extra_tag_ids = ancestor_ids - used_tag_ids
    else:
        # Se only_populated for False, todas as tags não utilizadas são incluídas
        extra_tag_ids = {tag.id for tag in all_tags} - used_tag_ids

    for tag in all_tags:
        if tag.id in extra_tag_ids:
            columns.append(['', '', tag.path, tag.full_path(), ''])
            if include_notes and tag.description and tag.id not in notes_added:
                notes_added.add(tag.id)
                columns.append([
                    '',
                    '',
                    f"{tag.path}_note",
                    '',
                    tag.description,
                ])

    return headers, columns


@tracer.start_as_current_span('taguette/export/highlights_csv')
def highlights_csv(db, project_id, path, file, include_notes=True, only_populated=True, transposed=False):
    """Export highlights to a CSV file.
    """
    with contextlib.ExitStack() as stack:
        if not hasattr(file, 'write'):
            file = stack.enter_context(open(file, 'w', encoding='utf-8', newline=''))
        writer = csv.writer(file)
        if not transposed:
            headers, rows = _build_highlights_table(db, project_id, path, include_notes=include_notes, only_populated=only_populated)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(row)
        else:
            headers, columns = _build_highlights_table_transposed(db, project_id, path, include_notes=include_notes, only_populated=only_populated)
            for row_idx, h in enumerate(headers):
                writer.writerow([h] + [col[row_idx] for col in columns])


@tracer.start_as_current_span('taguette/export/highlights_xlsx')
def highlights_xslx(db, project_id, path, filename, include_notes=True, only_populated=True, transposed=False):
    """Export highlights to an Excel file with wrapped text and header-calibrated column widths.
    """
    workbook = xlsxwriter.Workbook(filename, {'strings_to_formulas': False})
    sheet = workbook.add_worksheet('highlights')

    header_format = workbook.add_format({'bold': True, 'text_wrap': True})
    cell_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})

    if not transposed:
        headers, rows = _build_highlights_table(db, project_id, path, include_notes=include_notes, only_populated=only_populated)
        for col, h in enumerate(headers):
            sheet.write(0, col, h, header_format)

        sheet.set_column(0, 0, 8.0, cell_format)
        sheet.set_column(1, 1, 20.0, cell_format)
        sheet.set_column(2, 2, 20.0, cell_format)
        sheet.set_column(3, 3, 30.0, cell_format)
        if include_notes:
            sheet.set_column(4, 4, 30.0, cell_format)
            sheet.set_column(5, 5, 50.0, cell_format)
        else:
            sheet.set_column(4, 4, 50.0, cell_format)

        for row_idx, row in enumerate(rows, start=1):
            for col_idx, val in enumerate(row):
                sheet.write(row_idx, col_idx, val, cell_format)
    else:
        headers, columns = _build_highlights_table_transposed(db, project_id, path, include_notes=include_notes, only_populated=only_populated)
        sheet.set_column(0, 0, 15.0, header_format)
        if columns:
            sheet.set_column(1, len(columns), 30.0, cell_format)

        for row_idx, h in enumerate(headers):
            sheet.write(row_idx, 0, h, header_format)
            for col_idx, col in enumerate(columns, start=1):
                sheet.write(row_idx, col_idx, col[row_idx], cell_format)

    workbook.close()


@tracer.start_as_current_span('taguette/export/highlights_doc')
def highlights_doc(db, project_id, path, ext, *, config, locale, include_notes=True):
    """Export highlights to a text document.
    """
    highlights = _get_highlights_for_export(db, project_id, path)

    html = _render_string(
        'export_highlights.html',
        locale,
        path=path,
        highlights=highlights,
        include_notes=include_notes,
    )

    mimetype, contents = convert.html_to(html, ext, config)
    return mimetype, contents


@tracer.start_as_current_span('taguette/export/highlighted_document')
async def highlighted_document(db, document, ext, *, config, locale):
    """Export a document annotated with highlights.

    Each highlight is followed by its tags in brackets.
    """
    highlights = (
        db.query(database.Highlight)
        .filter(database.Highlight.document_id == document.id)
        .order_by(database.Highlight.start_offset)
        .options(joinedload(database.Highlight.tags))
    ).all()

    highlights = [
        (hl.start_offset, hl.end_offset, [t.path for t in hl.tags])
        for hl in highlights
    ]

    html = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: extract.highlight(
            document.contents, highlights,
            show_tags=True,
        ),
    )

    html = _render_string(
        'export_document.html',
        locale,
        name=document.name,
        contents=Markup(html),
    )

    mimetype, contents = convert.html_to(
        html, ext,
        config,
    )
    contents = await contents
    return mimetype, contents


TAGUETTE_NAMESPACE = uuid.UUID('51B2B2B7-27EB-4ECB-9D56-E75B0A0496C2')


@tracer.start_as_current_span('taguette/export/codebook_xml')
def codebook_xml(tags, file):
    """Export a codebook in REFI-QDA format for the given tags.
    """
    with contextlib.ExitStack() as stack:
        if not hasattr(file, 'write'):
            file = stack.enter_context(open(file, 'wb'))

        # http://schema.qdasoftware.org/versions/Codebook/v1.0/Codebook.xsd
        output = XMLGenerator(
            file,
            encoding='utf-8',
            short_empty_elements=True,
        )
        output.startDocument()
        output.startPrefixMapping(None, 'urn:QDA-XML:codebook:1.0')
        output.startElementNS(
            (None, 'CodeBook'), 'CodeBook',
            AttributesNSImpl(
                {(None, 'origin'): 'Taguette %s' % exact_version()},
                {(None, 'origin'): 'origin'},
            ),
        )
        output.startElementNS(
            (None, 'Codes'), 'Codes',
            AttributesNSImpl({}, {}),
        )
        for tag in tags:
            guid = uuid.uuid5(TAGUETTE_NAMESPACE, tag.path)
            guid = str(guid).upper()
            output.startElementNS(
                (None, 'Code'), 'Code',
                AttributesNSImpl({(None, 'guid'): guid,
                                  (None, 'name'): tag.path,
                                  (None, 'isCodable'): 'true'},
                                 {(None, 'guid'): 'guid',
                                  (None, 'name'): 'name',
                                  (None, 'isCodable'): 'isCodable'}),
            )
            output.endElementNS((None, 'Code'), 'Code')
        output.endElementNS((None, 'Codes'), 'Codes')
        output.startElementNS(
            (None, 'Sets'), 'Sets',
            AttributesNSImpl({}, {}),
        )
        output.endElementNS((None, 'Sets'), 'Sets')
        output.endElementNS((None, 'CodeBook'), 'CodeBook')
        output.endPrefixMapping(None)
        output.endDocument()


@tracer.start_as_current_span('taguette/export/codebook_csv')
def codebook_csv(tags, file):
    """Export a codebook in CSV format for the given tags.
    """
    with contextlib.ExitStack() as stack:
        if not hasattr(file, 'write'):
            file = stack.enter_context(open(file, 'w'))

        writer = csv.writer(file)
        writer.writerow([
            'tag',
            'description',
            'number of highlights',
            'number of documents',
        ])
        for tag in tags:
            writer.writerow([
                tag.path,
                tag.description,
                tag.highlights_count,
                tag.documents_count,
            ])


@tracer.start_as_current_span('taguette/export/codebook_xlsx')
def codebook_xlsx(tags, filename):
    """Export a codebook in Excel format for the given tags.
    """
    workbook = xlsxwriter.Workbook(filename, {'strings_to_formulas': False})
    sheet = workbook.add_worksheet('codebook')

    header = workbook.add_format({'bold': True})

    sheet.write(0, 0, 'tag', header)
    sheet.write(0, 1, 'description', header)
    sheet.write(0, 2, 'number of highlights', header)
    sheet.write(0, 3, 'number of documents', header)
    sheet.set_column(0, 0, 30.0)
    sheet.set_column(1, 1, 80.0)
    for row, tag in enumerate(tags, start=1):
        sheet.write(row, 0, tag.path)
        sheet.write(row, 1, tag.description)
        sheet.write(row, 2, tag.highlights_count)
        sheet.write(row, 3, tag.documents_count)
    workbook.close()


@tracer.start_as_current_span('taguette/export/codebook_document')
async def codebook_document(tags, ext, *, config, locale):
    """Export a codebook as a text document for the given tags.
    """
    html = _render_string(
        'export_codebook.html',
        locale,
        tags=tags,
    )

    mimetype, contents = convert.html_to(
        html, ext,
        config,
    )
    contents = await contents
    return mimetype, contents


def _build_tree(tags):
    """Constrói estrutura de árvore hierárquica em memória."""
    nodes_by_id = {tag.id: {'tag': tag, 'children': []} for tag in tags}
    root_nodes = []
    for tag in tags:
        if tag.parent_id and tag.parent_id in nodes_by_id:
            nodes_by_id[tag.parent_id]['children'].append(nodes_by_id[tag.id])
        else:
            root_nodes.append(nodes_by_id[tag.id])
    return root_nodes


@tracer.start_as_current_span('taguette/export/codebook_tree_html')
def codebook_tree_html(project, tags):
    """Gera um arquivo HTML independente com a árvore hierárquica e busca."""
    tree_nodes = _build_tree(tags)
    template = template_env.get_template('export_codebook_tree.html')
    return template.render(
        project=project,
        tree_nodes=tree_nodes,
        tags=tags,
    )


@tracer.start_as_current_span('taguette/export/highlights_ontotext_csv')
def highlights_ontotext_csv(db, project, file, tags=None):
    """Exporta matriz para Ontotext Refine com notas dinâmicas."""
    with contextlib.ExitStack() as stack:
        if not hasattr(file, 'write'):
            file = stack.enter_context(open(file, 'w', encoding='utf-8', newline=''))

        if tags is None:
            tags = sorted(project.tags, key=lambda t: t.path.lower())
        else:
            tags = sorted(tags, key=lambda t: t.path.lower())

        tags_with_notes = set(
            tag.id for tag in tags if tag.description and tag.description.strip()
        )

        header = ['id', 'document']
        for tag in tags:
            clean_col = tag.path.replace(' ', '_')
            header.append(clean_col)
            if tag.id in tags_with_notes:
                header.append(f"{clean_col}_note")

        writer = csv.writer(file)
        writer.writerow(header)

        highlights = (
            db.query(database.Highlight)
            .join(database.Document)
            .filter(database.Document.project_id == project.id)
            .options(joinedload(database.Highlight.tags), joinedload(database.Highlight.document))
            .order_by(database.Highlight.document_id, database.Highlight.start_offset)
            .all()
        )

        for hl in highlights:
            content = convert.html_to_plaintext(hl.snippet)
            row = [hl.id, hl.document.name]
            hl_tag_ids = {t.id for t in hl.tags}
            for tag in tags:
                if tag.id in hl_tag_ids:
                    row.append(content)
                    if tag.id in tags_with_notes:
                        row.append(tag.description)
                else:
                    row.append('')
                    if tag.id in tags_with_notes:
                        row.append('')
            writer.writerow(row)


@tracer.start_as_current_span('taguette/export/ontotext_mapping_json')
def ontotext_mapping_json(project, tags):
    """Gera a configuração mapping.json para o Ontotext Refine."""
    import json

    tags_with_notes = set(
        tag.id for tag in tags if tag.description and tag.description.strip()
    )

    subject_mappings = []

    # 1. Mapeamento de Classes e Hierarquias (owl:Class, rdfs:subClassOf, rdfs:comment)
    for tag in tags:
        clean_name = tag.path.replace(' ', '_')
        prop_mappings = []

        if tag.parent is not None:
            parent_clean = tag.parent.path.replace(' ', '_')
            prop_mappings.append({
                "property": {
                    "transformation": {"expression": "rdfs", "language": "prefix"},
                    "valueSource": {"source": "constant", "constant": "subClassOf"}
                },
                "values": [{
                    "transformation": {"expression": "", "language": "prefix"},
                    "valueSource": {"source": "constant", "constant": parent_clean},
                    "valueType": {"propertyMappings": [], "type": "iri", "typeMappings": []}
                }]
            })

        if tag.id in tags_with_notes:
            prop_mappings.append({
                "property": {
                    "transformation": {"expression": "rdfs", "language": "prefix"},
                    "valueSource": {"source": "constant", "constant": "comment"}
                },
                "values": [{
                    "transformation": {"expression": "", "language": "prefix"},
                    "valueSource": {"source": "constant", "constant": tag.description},
                    "valueType": {
                        "type": "datatype_literal",
                        "datatype": {
                            "transformation": {"expression": "xsd", "language": "prefix"},
                            "valueSource": {"source": "constant", "constant": "string"}
                        }
                    }
                }]
            })

        subject_mappings.append({
            "propertyMappings": prop_mappings,
            "subject": {
                "transformation": {"expression": "", "language": "prefix"},
                "valueSource": {"source": "constant", "constant": clean_name}
            },
            "typeMappings": [{
                "transformation": {"expression": "owl", "language": "prefix"},
                "valueSource": {"source": "constant", "constant": "Class"}
            }]
        })

    # 2. Mapeamento dos trechos de destaque (instâncias por linha com dcterms:description)
    for tag in tags:
        clean_name = tag.path.replace(' ', '_')
        prop_mappings = [
            {
                "property": {
                    "transformation": {"expression": "dcterms", "language": "prefix"},
                    "valueSource": {"source": "constant", "constant": "description"}
                },
                "values": [{
                    "valueSource": {"columnName": clean_name, "source": "column"},
                    "valueType": {
                        "type": "datatype_literal",
                        "datatype": {
                            "transformation": {"expression": "xsd", "language": "prefix"},
                            "valueSource": {"source": "constant", "constant": "string"}
                        }
                    }
                }]
            }
        ]

        if tag.id in tags_with_notes:
            note_col = f"{clean_name}_note"
            prop_mappings.append({
                "property": {
                    "transformation": {"expression": "rdfs", "language": "prefix"},
                    "valueSource": {"source": "constant", "constant": "comment"}
                },
                "values": [{
                    "valueSource": {"columnName": note_col, "source": "column"},
                    "valueType": {
                        "type": "datatype_literal",
                        "datatype": {
                            "transformation": {"expression": "xsd", "language": "prefix"},
                            "valueSource": {"source": "constant", "constant": "string"}
                        }
                    }
                }]
            })

        subject_mappings.append({
            "propertyMappings": prop_mappings,
            "subject": {
                "transformation": {
                    "expression": f'if(isNonBlank(cells["{clean_name}"].value), "{clean_name}_" + rowIndex, null)',
                    "language": "grel"
                },
                "valueSource": {"source": "row_index"}
            },
            "typeMappings": [{
                "transformation": {"expression": "", "language": "prefix"},
                "valueSource": {"source": "constant", "constant": clean_name}
            }]
        })

    mapping = {
        "baseIRI": "http://exemple.org/base/",
        "namespaces": {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "dcterms": "http://purl.org/dc/terms/",
            "": "http://exemple.org/resource/"
        },
        "subjectMappings": subject_mappings
    }
    return json.dumps(mapping, indent=2, ensure_ascii=False)


@tracer.start_as_current_span('taguette/export/codebook_and_highlights_ttl')
def codebook_and_highlights_ttl(db, project, file, tags=None):
    """Exporta o projeto em sintaxe Turtle (.ttl / RDF) para GraphDB/Protégé."""
    with contextlib.ExitStack() as stack:
        if not hasattr(file, 'write'):
            file = stack.enter_context(open(file, 'w', encoding='utf-8'))

        if tags is None:
            tags = project.tags
        tags_set = {t.id for t in tags}

        lines = [
            "@prefix : <http://exemple.org/resource/> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "@prefix dcterms: <http://purl.org/dc/terms/> .",
            "",
            "# --- Taxonomia de Classes e Categorias ---",
            "",
        ]

        def escape_ttl_literal(s):
            if not s:
                return ""
            return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')

        for tag in tags:
            clean_name = tag.path.replace(' ', '_')
            lines.append(f":{clean_name} a owl:Class ;")
            lines.append(f'    rdfs:label "{escape_ttl_literal(tag.path)}" ;')
            if tag.parent and tag.parent.id in tags_set:
                parent_clean = tag.parent.path.replace(' ', '_')
                lines.append(f"    rdfs:subClassOf :{parent_clean} ;")
            if tag.description:
                lines.append(f'    rdfs:comment "{escape_ttl_literal(tag.description)}"^^xsd:string ;')
            lines[-1] = lines[-1][:-2] + " .\n"

        lines.append("\n# --- Instâncias de Destaques (Highlights) ---\n")

        highlights = (
            db.query(database.Highlight)
            .join(database.Document)
            .filter(database.Document.project_id == project.id)
            .options(joinedload(database.Highlight.tags), joinedload(database.Highlight.document))
            .all()
        )

        tag_dict = {t.id: t for t in tags}

        for hl in highlights:
            content = convert.html_to_plaintext(hl.snippet)
            escaped_content = escape_ttl_literal(content)
            doc_name = escape_ttl_literal(hl.document.name)
            for tag in hl.tags:
                if tag.id not in tags_set:
                    continue
                tag_obj = tag_dict.get(tag.id, tag)
                clean_name = tag_obj.path.replace(' ', '_')
                inst_uri = f":{clean_name}_hl_{hl.id}"
                lines.append(f"{inst_uri} a :{clean_name} ;")
                lines.append(f'    dcterms:description "{escaped_content}"^^xsd:string ;')
                lines.append(f'    dcterms:source "{doc_name}"^^xsd:string ;')
                if tag_obj.description:
                    lines.append(f'    rdfs:comment "{escape_ttl_literal(tag_obj.description)}"^^xsd:string ;')
                lines[-1] = lines[-1][:-2] + " .\n"

        file.write("\n".join(lines))
