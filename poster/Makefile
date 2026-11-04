# Build the poster: `make` runs the figure scripts, then renders poster.pdf.
# `make poster` only renders, using the figures already in figures/.

PYTHON ?= python
SCRIPTS := $(filter-out scripts/poster_style.py,$(wildcard scripts/*.py))

.PHONY: all figures poster clean

all: figures poster

figures:
	@for s in $(SCRIPTS); do echo "== $$s"; $(PYTHON) $$s || exit 1; done

poster:
	quarto render poster.qmd

clean:
	rm -f poster.pdf poster.typ
