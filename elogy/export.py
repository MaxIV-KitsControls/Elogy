from tempfile import NamedTemporaryFile

import pdfkit


def export_entries_as_pdf(logbook, entries):

    """
    Super basic "proof-of-concept" PDF export
    No proper formatting, and does not embed images.
    Note that pdfkit relies on the external library "wkhtmltopdf".
    TODO: pdfkit seems a bit limited, look for a more flexible alternative.
    "reportlab" looks pretty good (https://bitbucket.org/rptlab/reportlab)
    """

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
