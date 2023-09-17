# Minimal makefile for Sphinx documentation
#

RASENMAEHER_ROOT = `git rev-parse --show-toplevel`

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
DOCSDIR       = "$(RASENMAEHER_ROOT)/docs"
SOURCEDIR     = "."
DOCSBUILDDIR  = "$(RASENMAEHER_ROOT)/build/docs"
BUILDDIR      = "$(RASENMAEHER_ROOT)/build"

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(DOCSBUILDDIR)" $(SPHINXOPTS) $(O)

clean:
	@echo "Cleaning build folder..."
	rm -rf "$(BUILDDIR)"

.PHONY: help Makefile


# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile



	
	
	@echo "help"
	which gcp
	@echo "Cleaning build folder..."
	rm -rf "$(BUILDDIR)"
	mkdir -p "$(DOCSBUILDDIR)"

	@echo "Copying docs & config to build folder..."
	cp -a "$(DOCSDIR)" "$(BUILDDIR)"
	cd "$(RASENMAEHER_ROOT)" && \
		find . -type f \( -name "*.md" -o -name "*.rst" -o -name "*.png" -o -name "*.jpg" -o -name "*.svg" -name "*.py" \) \
			-not -path "*/.*" \
			-not -path "./build/*" \
			-not -path "./docs/*" \
			-not -path "./venv/*" \
			-exec /usr/local/bin/gcp  --parents "{}" ./build/docs/ \;

	@echo "Building rst files..."
	sphinx-apidoc -o "$(DOCSBUILDDIR)" ../ \
	$(shell find .. -type d -name "*tests*")

	@echo "Building html files..."
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(DOCSBUILDDIR)" $(SPHINXOPTS) $(O)