SPHINXOPTS    = -n -W
SPHINXBUILD   = sphinx-build
SOURCEDIR     = .
BUILDDIR      = build
current_dir = $(shell pwd)

clean:
	rm -rf build

html: clean
	sphinx-build -M html \
	$(SOURCEDIR) \
 	$(BUILDDIR) \
 	$(SPHINXOPTS)

json:
	sphinx-build -M json \
	-d build/doctrees \
	$(SOURCEDIR) \
	$(BUILDDIR)/json \
	$(SPHINXOPTS)
