from multiprocessing import Process
import os
from tempfile import NamedTemporaryFile

import pytest
from splinter import Browser


@pytest.fixture
def browser():
    return Browser("phantomjs")


@pytest.fixture(scope="module")
def elogy(request):

    "Start up an instance of "

    os.environ["ELOGY_CONFIG_FILE"] = "../test/config.py"

    def run_elogy():
        from elogy import app
        app.run()

    proc = Process(target=run_elogy)
    proc.start()

    yield

    proc.terminate()


@pytest.fixture(scope="module")
def elogy_client(request):
    try:
        os.remove("/tmp/test.db")
    except OSError as e:
        print("isjdisj", e)
        pass
    os.environ["ELOGY_CONFIG_FILE"] = "../test/config.py"
    from elogy import app
    with app.test_client() as c:
        yield c
