"""
This script downloads a HTML version of a given logbook.
Useful e.g. for letting users bring their logbook notes home.
"""

from argparse import ArgumentParser
from itertools import count
import os
import re
import shutil
from time import sleep
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED

from requests import Session


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("elogy_url",
                        help="Base URL to the Elogy instance.")
    parser.add_argument("logbook_id",
                        help="Id (a number) of the logbook to export.")
    parser.add_argument("-o", "--out",
                        help="Name of the directory to put the exported HTML files in. Default: logbook_<id>")
    parser.add_argument("-n", type=int, default=100,
                        help="Number of entries to render per HTML file.")
    parser.add_argument("-z", "--zip", action="store_true",
                        help="Instead of a directory, create a zip file of the same name.")
    args = parser.parse_args()

    logbook_url = "{args.elogy_url}/api/logbooks/{args.logbook_id}/entries/".format(args=args)

    dirname = args.out or "logbook_{args.logbook_id}".format(args=args)

    session = Session()

    with TemporaryDirectory() as tmpdir:

        html_filenames = []

        print("Downloading HTML exports...")
        for i in count():
            print(" - Batch {}...".format(i))
            params = dict(
                download="html",
                n=args.n,
                offset=args.n * i,
                reverse_order=False  # chronological order makes more sense here..?
            )
            response = session.get(logbook_url, params=params)
            if response.status_code == 200:
                disp = response.headers['content-disposition']
                filename, = re.findall("filename=(.+)", disp)
                html_filenames.append(filename)
                with open(os.path.join(tmpdir, filename), "w") as f:
                    f.write(response.text)
            elif response.status_code == 400:
                break
            else:
                print("An error occurred (code %d): %r", response.status_code, response.text)
                os.exit(1)
            sleep(0.2)  # Give server some breathing room :)

        with open(os.path.join(tmpdir, "index.html"), "w") as f:
            f.writelines([
                "<body>\n",
                "  <ul>\n",
                *("    <li><a href={f}>{f}</a></li>\n".format(f=f) for f in html_filenames),
                "  </ul>\n"
                "</body>"
            ])

        if args.zip:
            zip_file = dirname + ".zip"
            print("Zipping data into destination '{}'...".format(zip_file))
            with ZipFile(zip_file, mode="w", compression=ZIP_DEFLATED) as zf:
                zf.write(os.path.join(tmpdir, "index.html"), os.path.join(dirname, "index.html"))
                for filename in html_filenames:
                    zf.write(os.path.join(tmpdir, filename), os.path.join(dirname, filename))
        else:
            print("Putting results in destination '{}'...".format(dirname))
            shutil.copytree(tmpdir, dirname)
