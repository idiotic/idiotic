all: run

run: venv conf.yaml
	venv/bin/python setup.py install
	venv/bin/python -m idiotic -v -c conf.yaml

venv: venv/bin/activate

venv/bin/activate: requirements.txt
	virtualenv venv
	venv/bin/pip install -Ur requirements.txt
	touch venv/bin/activate

clean:
	-rm -rf venv
	-find . -name \*.pyc -delete
	-find . -name __pycache__ -delete
	-rm -rf dist
	-rm *.rpm
	-rm -rf idiotic.egg-info/
	-rm -rf build/

rpm: venv
	venv/bin/python setup.py bdist_rpm --release $(shell git rev-list $(shell git tag)..HEAD --count)


deps_rpm: venv
	venv/bin/python contrib/build-deps.py

conf.yaml:
	cp contrib/conf.yaml .
