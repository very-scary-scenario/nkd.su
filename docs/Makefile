SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SPHINXAPIDOC  ?= sphinx-apidoc
SOURCEDIR     = .
SOURCEROOT    = ..
PYTHONROOT    = ../nkdsu
BUILDDIR      = _build

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

clean:
	@rm -rf "$(BUILDDIR)"
	@rm -rf "$(SOURCEDIR)/code"

%: Makefile
	@(find $(SOURCEROOT) -path "*/migrations/*.py") | xargs $(SPHINXAPIDOC) --module-first --ext-viewcode --force -o "$(SOURCEDIR)/code" -H code $(PYTHONROOT)
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
