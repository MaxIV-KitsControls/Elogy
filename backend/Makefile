install:
	python3 -m venv env
	env/bin/pip install -e .[dev]

run:
	FLASK_APP=backend.app ELOGY_CONFIG_FILE=../config.py env/bin/flask run -p 8888 --reload --debugger
