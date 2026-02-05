PREFIX ?= /usr/local
PYTHON ?= python3

.PHONY: build install uninstall clean test

build:
	$(PYTHON) -m build --wheel

install:
	$(PYTHON) -m pip install . --prefix=$(PREFIX)

uninstall:
	$(PYTHON) -m pip uninstall -y wsr

clean:
	rm -rf build/ dist/ *.egg-info/ src/*.egg-info/

test:
	PYTHONPATH=. $(PYTHON) -m pytest tests/ -v
