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
        from elogy.app import app
        app.run()

    proc = Process(target=run_elogy)
    proc.start()

    yield

    proc.terminate()


@pytest.fixture(scope="function")
def db(request):

    from elogy.db import db, setup_database

    setup_database(":memory:", close=False)
    return db
    # with NamedTemporaryFile() as f:
    #     setup_database(f.name)
    #     yield db


@pytest.fixture(scope="module")
def elogy_client(request):
    os.environ["ELOGY_CONFIG_FILE"] = "../test/config.py"
    from elogy.app import app
    with app.test_client() as c:
        yield c
    try:
        os.remove(app.config["DATABASE"]["name"])
    except FileNotFoundError:
        pass
