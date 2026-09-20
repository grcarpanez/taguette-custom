from datetime import datetime, timezone
import logging
import os
import prometheus_client
import shutil
import string
import tempfile
from tornado.web import authenticated

from .. import convert
from .. import database
from .. import export
from .base import BaseHandler


logger = logging.getLogger(__name__)


class WriteAdapter(object):
    def __init__(self, write_func):
        self.write = write_func

    def flush(self):
        pass


PROM_EXPORT = prometheus_client.Counter(
    'export_total',
    "Export",
    ['what', 'extension'],
)


def init_PROM_EXPORT(w):
    for e in convert.html_to_extensions:
        PROM_EXPORT.labels(w, e).inc(0)


def return_doc(wrapped):
    """Decorator for returning a file, or a conversion error.
    """
    async def wrapper(self, *args):
        ext = args[-1].lower()
        try:
            name, mimetype, contents = await wrapped(self, *args)
        except convert.UnsupportedFormat:
            self.set_status(404)
            self.set_header('Content-Type', 'text/plain')
            return await self.finish("Unsupported format: %s" % ext)
        except convert.ConversionError as e:
            self.set_status(500)
            self.set_header('Content-Type', 'text/plain')
            return await self.finish("Conversion error: %s" % e)

        # Return document
        self.set_header('Content-Type', mimetype)
        if name:
            self.set_header('Content-Disposition',
                            'attachment; filename="%s.%s"' % (name, ext))
        else:
            self.set_header('Content-Disposition', 'attachment')

        for chunk in contents:
            self.write(chunk)
        return await self.finish()

    return wrapper


class ExportTagWrapper(object):
    """Wrapper para tags que permite customizar campos (ex.: suprimir description)."""
    def __init__(self, tag, include_notes=True):
        self._tag = tag
        self.id = tag.id
        self.project_id = tag.project_id
        self.parent_id = tag.parent_id
        self.parent = tag.parent
        self.path = tag.path
        self.description = tag.description if include_notes else ""
        self.highlights_count = tag.highlights_count
        self.documents_count = tag.documents_count
        self.highlights = tag.highlights

    def full_path(self, delimiter=' | '):
        return self._tag.full_path(delimiter=delimiter)

    def __getattr__(self, name):
        return getattr(self._tag, name)


def get_codebook_tags(project, handler):
    """Retorna as tags do projeto filtradas e ajustadas conforme parâmetros."""
    only_populated = handler.get_argument('only_populated', 'false').lower() in ('true', '1', 'yes')
    include_notes = handler.get_argument('include_notes', 'true').lower() in ('true', '1', 'yes')

    tags = list(project.tags)
    if only_populated:
        # Encontrar todas as tags populadas (com highlights vinculados)
        populated_ids = {t.id for t in tags if t.highlights_count and t.highlights_count > 0}
        # Incluir todos os ancestrais para manter a integridade da árvore e hierarquia
        tag_by_id = {t.id: t for t in tags}
        kept_ids = set()
        for t_id in populated_ids:
            curr_id = t_id
            while curr_id and curr_id in tag_by_id and curr_id not in kept_ids:
                kept_ids.add(curr_id)
                curr = tag_by_id[curr_id]
                curr_id = curr.parent_id

        tags = [t for t in tags if t.id in kept_ids]

    if not include_notes:
        tags = [ExportTagWrapper(t, include_notes=False) for t in tags]

    return tags


class ExportHighlightsCsv(BaseHandler):
    PROM_EXPORT.labels('highlights_doc', 'csv').inc(0)

    @authenticated
    def get(self, project_id, path):
        PROM_EXPORT.labels('highlights_doc', 'csv').inc()

        project, _ = self.get_project(project_id)
        include_notes = self.get_argument('include_notes', 'true').lower() in ('true', '1', 'yes')
        only_populated = self.get_argument('only_populated', 'true').lower() in ('true', '1', 'yes')
        transposed = self.get_argument('transposed', 'false').lower() in ('true', '1', 'yes')

        name = export.get_filename_for_highlights_export(path)
        self.set_header('Content-Type', 'text/csv; charset=utf-8')
        if name:
            self.set_header('Content-Disposition',
                            'attachment; filename="%s.csv"' % name)
        else:
            self.set_header('Content-Disposition', 'attachment')

        export.highlights_csv(
            self.db,
            project.id,
            path,
            WriteAdapter(self.write),
            include_notes=include_notes,
            only_populated=only_populated,
            transposed=transposed,
        )
        return self.finish()


class ExportHighlightsXlsx(BaseHandler):
    PROM_EXPORT.labels('highlights_doc', 'xls').inc(0)

    @authenticated
    def get(self, project_id, path):
        PROM_EXPORT.labels('highlights_doc', 'xls').inc()

        project, _ = self.get_project(project_id)
        include_notes = self.get_argument('include_notes', 'true').lower() in ('true', '1', 'yes')
        only_populated = self.get_argument('only_populated', 'true').lower() in ('true', '1', 'yes')
        transposed = self.get_argument('transposed', 'false').lower() in ('true', '1', 'yes')

        name = export.get_filename_for_highlights_export(path)
        self.set_header('Content-Type',
                        ('application/vnd.openxmlformats-officedocument.'
                         'spreadsheetml.sheet'))
        if name:
            self.set_header('Content-Disposition',
                            'attachment; filename="%s.xlsx"' % name)
        else:
            self.set_header('Content-Disposition', 'attachment')

        tmp = tempfile.mkdtemp(prefix='taguette_xlsx_')
        try:
            filename = os.path.join(tmp, 'highlights.xlsx')
            export.highlights_xslx(
                self.db,
                project.id,
                path,
                filename,
                include_notes=include_notes,
                only_populated=only_populated,
                transposed=transposed,
            )
            with open(filename, 'rb') as fp:
                chunk = fp.read(4096)
                self.write(chunk)
                while len(chunk) == 4096:
                    chunk = fp.read(4096)
                    if chunk:
                        self.write(chunk)
            return self.finish()
        finally:
            shutil.rmtree(tmp)


class ExportHighlightsDoc(BaseHandler):
    init_PROM_EXPORT('highlights_doc')

    @authenticated
    @return_doc
    async def get(self, project_id, path, ext):
        ext = ext.lower()
        PROM_EXPORT.labels('highlights_doc', ext).inc()

        project, _ = self.get_project(project_id)
        include_notes = self.get_argument('include_notes', 'true').lower() in ('true', '1', 'yes')

        # Close DB connection to not overflow the connection pool
        self.close_db_connection()

        name = export.get_filename_for_highlights_export(path)
        mimetype, contents = export.highlights_doc(
            self.db,
            project.id,
            path,
            ext,
            config=self.application.config,
            locale=self.locale,
            include_notes=include_notes,
        )
        contents = await contents
        return name, mimetype, contents


_safe_filename_chars = set(
    string.ascii_letters
    + string.digits
    + ' ()+,-.=@[]_{}~'
)


def safe_filename(name):
    return ''.join(c for c in name if c in _safe_filename_chars)


class ExportDocument(BaseHandler):
    init_PROM_EXPORT('document')

    @authenticated
    @return_doc
    async def get(self, project_id, document_id, ext):
        PROM_EXPORT.labels('document', ext.lower()).inc()
        doc, _ = self.get_document(project_id, document_id, True)

        # Close DB connection to not overflow the connection pool
        self.close_db_connection()

        name = safe_filename(doc.name)

        mimetype, contents = await export.highlighted_document(
            self.db,
            doc,
            ext,
            config=self.application.config,
            locale=self.locale,
        )
        return name, mimetype, contents


class ExportCodebookXml(BaseHandler):
    PROM_EXPORT.labels('codebook', 'qdc').inc(0)

    @authenticated
    def get(self, project_id):
        PROM_EXPORT.labels('codebook', 'qdc').inc()
        project, _ = self.get_project(project_id)
        tags = get_codebook_tags(project, self)
        self.set_header('Content-Type', 'text/xml; charset=utf-8')
        self.set_header('Content-Disposition',
                        'attachment; filename="codebook.qdc"')

        export.codebook_xml(tags, WriteAdapter(self.write))
        return self.finish()


class ExportCodebookCsv(BaseHandler):
    PROM_EXPORT.labels('codebook', 'csv').inc(0)

    @authenticated
    def get(self, project_id):
        PROM_EXPORT.labels('codebook', 'csv').inc()
        project, _ = self.get_project(project_id)
        tags = get_codebook_tags(project, self)
        self.set_header('Content-Type', 'text/csv; charset=utf-8')
        self.set_header('Content-Disposition',
                        'attachment; filename="codebook.csv"')
        export.codebook_csv(tags, WriteAdapter(self.write))
        return self.finish()


class ExportCodebookXlsx(BaseHandler):
    PROM_EXPORT.labels('codebook', 'xls').inc(0)

    @authenticated
    def get(self, project_id):
        PROM_EXPORT.labels('codebook', 'xls').inc()
        project, _ = self.get_project(project_id)
        tags = get_codebook_tags(project, self)
        self.set_header('Content-Type',
                        ('application/vnd.openxmlformats-officedocument.'
                         'spreadsheetml.sheet'))
        self.set_header('Content-Disposition',
                        'attachment; filename="codebook.xlsx"')
        tmp = tempfile.mkdtemp(prefix='taguette_xlsx_')
        try:
            filename = os.path.join(tmp, 'codebook.xlsx')

            export.codebook_xlsx(tags, filename)

            with open(filename, 'rb') as fp:
                chunk = fp.read(4096)
                self.write(chunk)
                while len(chunk) == 4096:
                    chunk = fp.read(4096)
                    if chunk:
                        self.write(chunk)
            return self.finish()
        finally:
            shutil.rmtree(tmp)


class ExportCodebookDoc(BaseHandler):
    init_PROM_EXPORT('codebook')

    @authenticated
    @return_doc
    async def get(self, project_id, ext):
        ext = ext.lower()
        PROM_EXPORT.labels('codebook', ext).inc()
        project, _ = self.get_project(project_id)
        tags = get_codebook_tags(project, self)

        # Close DB connection to not overflow the connection pool
        self.close_db_connection()

        mimetype, contents = await export.codebook_document(
            tags,
            ext,
            config=self.application.config,
            locale=self.locale,
        )
        return 'codebook', mimetype, contents


class ExportSqlite(BaseHandler):
    PROM_EXPORT.labels('project', 'sqlite3').inc(0)

    @authenticated
    async def get(self, project_id):
        PROM_EXPORT.labels('project', 'sqlite3').inc()
        project, _ = self.get_project(project_id)

        # Result filename
        export_name = '%s_%s.sqlite3' % (
            datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            safe_filename(project.name),
        )

        with tempfile.TemporaryDirectory(
            prefix='taguette_export_',
        ) as tmp_dir:
            filename = os.path.join(tmp_dir, 'db.sqlite3')

            # Connect to database
            dest_db = database.connect('sqlite:///%s' % filename)()

            # Create user
            admin = database.User(login='admin')
            dest_db.add(admin)
            dest_db.commit()

            # Copy data
            database.copy_project(
                self.db, dest_db,
                project.id, 'admin',
            )
            dest_db.commit()

            # Close DB connection to not overflow the connection pool
            self.close_db_connection()

            # Send the file
            self.set_header('Content-Type', 'application/vnd.sqlite3')
            self.set_header('Content-Disposition',
                            'attachment; filename="%s"' % export_name)
            with open(filename, 'rb') as fp:
                while True:
                    chunk = fp.read(4096)
                    self.write(chunk)
                    if len(chunk) != 4096:
                        break
                    await self.flush()
                return await self.finish()


class ExportCodebookTreeHtml(BaseHandler):
    PROM_EXPORT.labels('codebook', 'html').inc(0)

    @authenticated
    def get(self, project_id):
        PROM_EXPORT.labels('codebook', 'html').inc()
        project, _ = self.get_project(project_id)
        tags = get_codebook_tags(project, self)
        html = export.codebook_tree_html(project, tags)
        self.set_header('Content-Type', 'text/html; charset=utf-8')
        self.set_header('Content-Disposition',
                        'attachment; filename="codebook_tree.html"')
        return self.finish(html)


class ExportOntotextCsv(BaseHandler):
    PROM_EXPORT.labels('ontotext', 'csv').inc(0)

    @authenticated
    def get(self, project_id):
        PROM_EXPORT.labels('ontotext', 'csv').inc()
        project, _ = self.get_project(project_id)
        tags = get_codebook_tags(project, self)
        self.set_header('Content-Type', 'text/csv; charset=utf-8')
        self.set_header('Content-Disposition',
                        'attachment; filename="ontotext_refine.csv"')
        export.highlights_ontotext_csv(
            self.db,
            project,
            WriteAdapter(self.write),
            tags=tags,
        )
        return self.finish()


class ExportOntotextMappingJson(BaseHandler):
    PROM_EXPORT.labels('ontotext', 'json').inc(0)

    @authenticated
    def get(self, project_id):
        PROM_EXPORT.labels('ontotext', 'json').inc()
        project, _ = self.get_project(project_id)
        tags = get_codebook_tags(project, self)
        mapping = export.ontotext_mapping_json(project, tags)
        self.set_header('Content-Type', 'application/json; charset=utf-8')
        self.set_header('Content-Disposition',
                        'attachment; filename="mapping.json"')
        return self.finish(mapping)


class ExportCodebookTtl(BaseHandler):
    PROM_EXPORT.labels('codebook', 'ttl').inc(0)

    @authenticated
    def get(self, project_id):
        PROM_EXPORT.labels('codebook', 'ttl').inc()
        project, _ = self.get_project(project_id)
        tags = get_codebook_tags(project, self)
        self.set_header('Content-Type', 'text/turtle; charset=utf-8')
        self.set_header('Content-Disposition',
                        'attachment; filename="codebook.ttl"')
        export.codebook_and_highlights_ttl(
            self.db,
            project,
            WriteAdapter(self.write),
            tags=tags,
        )
        return self.finish()
