from tempfile import NamedTemporaryFile
from slugify import slugify

try:
    import pdfkit
except ImportError:
    pdfkit = None


def export_entries_as_pdf(logbook, entries):

    """
    Super basic "proof-of-concept" PDF export
    No proper formatting, and does not embed images.
    Note that pdfkit relies on the external library "wkhtmltopdf".
    TODO: pdfkit seems a bit limited, look for a more flexible alternative.
    "reportlab" looks pretty good (https://bitbucket.org/rptlab/reportlab)
    """

    if pdfkit is None:
        return None

    entries_html = [
        """
        <p><b>Created at:</b> {created_at}</p>
        <p><b>Title:</b> {title}</p>
        <p><b>Authors:</b> {authors}</p>
        <p>{content}</p>
        """.format(title=entry.title or "(No title)",
                   authors=", ".join(a["name"] for a in entry.authors),
                   created_at=entry.created_at,
                   content=entry.content or "---")
        for entry in entries
    ]

    with NamedTemporaryFile(prefix=logbook.name,
                            suffix=".pdf",
                            delete=False) as f:
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
            pdfkit.from_string("<hr>".join(entries_html), f.name, options)
        except OSError:
            # Apparently there's some issue with wkhtmltopdf which produces
            # errors, but it works anyway. See
            # https://github.com/wkhtmltopdf/wkhtmltopdf/issues/2051
            pass
        return f.name

def export_entries_as_html(logbook, entries):

    """
    Super basic "proof-of-concept" html export
    No proper formatting, and does not embed images.
    """

    entries_html = [
        """
        <div><b>Created at:</b> {created_at}</div>
        <div><b>Title:</b> {title}</div>
        <div><b>Authors:</b> {authors}</div>
        <div>{content}</div>
        <hr/>
        """.format(title=entry.title or "(No title)",
                   authors=", ".join(a["name"] for a in entry.authors),
                   created_at=entry.created_at,
                   content=entry.content or "---")
        for entry in entries
    ]
    print(entries_html)
    with NamedTemporaryFile(prefix=slugify(logbook.name),
                            suffix=".html",
                            delete=True) as f:
        f.write('<h1>{}</h1>'.format(logbook.name).encode('utf8'))
        f.write('<div>{}</div><hr/>'.format(logbook.description).encode('utf8'))
        for entry_html in entries_html:
            f.write(entry_html.encode('utf8'))
    return f