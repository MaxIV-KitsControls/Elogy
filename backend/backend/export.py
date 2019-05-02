from datetime import datetime
from tempfile import NamedTemporaryFile

from flask import current_app
from slugify import slugify

try:
    import pdfkit
except ImportError:
    pdfkit = None

from .attachments import embed_attachments


def export_entries_as_pdf(logbook, entries, n, offset):

    """
    Export entries as a PDF. Simply uses the HTML export function below,
    and converts the HTML into PDF using pdfkit.
    Note that pdfkit relies on the external library "wkhtmltopdf".
    TODO: pdfkit seems a bit limited, look for a more flexible alternative.
    "reportlab" looks pretty good (https://bitbucket.org/rptlab/reportlab)
    """

    if pdfkit is None:
        raise ValueError("No pdfkit/wkhtmltopdf available.")

    html, n_entries = export_entries_as_html(logbook, entries, n, offset)

    with NamedTemporaryFile(prefix=logbook.name,
                            suffix=".pdf",
                            delete=True) as f:
        options = {
            "load-error-handling": "ignore",
            "load-media-error-handling": "ignore",
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
        }
        try:
            pdfkit.from_string(html, f.name, options)
        except OSError:
            # Apparently there's some issue with wkhtmltopdf which produces
            # errors, but it works anyway. See
            # https://github.com/wkhtmltopdf/wkhtmltopdf/issues/2051
            pass

        f.seek(0)
        return f.read(), n_entries


def export_entries_as_html(logbook, entries, n, offset):

    """
    Takes the given logbook entries and generates a single HTML string.
    Inline images are embedded, to make it a standalone document.
    """

    entries = list(entries)
    if not entries:
        raise ValueError("No entries!")

    template = current_app.jinja_env.get_or_select_template(
        "entry_export.html.jinja2")

    current_app.logger.info("Rendering HTML for logbook %s; n=%d, offset=%d",
                            logbook.id, n, offset)
    html = template.render(logbook=logbook, entries=entries,
                           n=len(entries), offset=offset,
                           embed=embed_attachments,
                           export_time=datetime.now())

    return html, len(entries)


def export_entries(logbook, entries, n_entries, offset, filetype):

    if filetype == "html":
        html, real_n_entries = export_entries_as_html(
            logbook, entries, n=n_entries, offset=offset)
        data = html.encode("utf-8")
        mimetype = "text/html"
    elif filetype == "pdf":
        pdf, real_n_entries = export_entries_as_pdf(
            logbook, entries, n=n_entries, offset=offset)
        data = pdf
        mimetype = "application/pdf"

    filename = "{}_{}_{}-{}.{}".format(
        slugify(logbook.name),
        datetime.now().strftime("%Y%m%dT%H%M%S"),
        offset,
        offset + real_n_entries,
        filetype
    )
    return data, real_n_entries, mimetype, filename
