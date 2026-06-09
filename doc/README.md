# FASER Server Documentation

This directory contains the Sphinx-based documentation for the FASER Server CLI.

## Structure

```
doc/
└── sphinx/
    ├── Makefile              # Makefile for building documentation
    ├── source/
    │   ├── conf.py          # Sphinx configuration
    │   ├── index.rst        # Main documentation index
    │   └── server/
    │       ├── index.rst    # Server section index
    │       └── tutorial.rst # Server tutorial
    └── build/               # Generated HTML (gitignored)
```

## Regenerating the Documentation

1. **Install dependencies** (from repository root):
   ```bash
   pip install -e ".[docs]"
   ```

2. **Build the HTML documentation**:
   ```bash
   cd doc/sphinx
   make html
   ```

3. **View the documentation**:
   ```bash
   # On macOS
   open build/html/index.html
   
   # On Linux
   xdg-open build/html/index.html
   
   # Or use the make target
   make view
   ```

4. **Clean build artifacts**:
   ```bash
   make clean
   ```

## Adding New Content

### Adding a New Section

1. Create a new directory under `doc/sphinx/source/` for your section:
   ```bash
   mkdir -p doc/sphinx/source/new_section
   ```

2. Create an `index.rst` file in your new directory:
   ```rst
   .. _new_section:

   My New Section
   ==============

   Introduction to this section.

   .. toctree::
      :maxdepth: 2

      page1
      page2
   ```

3. Add your content files (e.g., `page1.rst`, `page2.rst`) in the same directory.

4. Reference your new section from the main `index.rst`:
   ```rst
   Contents
   ========

   .. toctree::
      :maxdepth: 2

      server/index
      new_section/index
   ```

### Adding a New Tutorial

1. Add a new `.rst` file in the appropriate section directory (e.g., `doc/sphinx/source/server/`):
   ```bash
   touch doc/sphinx/source/server/my_new_tutorial.rst
   ```

2. Add content to your tutorial file. Use reStructuredText syntax:
   ```rst
   .. _my-new-tutorial:

   My Tutorial Title
   ================

   Introduction paragraph.

   Code Example
   -----------

   .. code-block:: bash

      example_upload events my_events

   More content here.
   ```

3. Add your tutorial to the section's `index.rst`:
   ```rst
   .. toctree::
      :maxdepth: 2

      tutorial
      my_new_tutorial
   ```

### Adding a New Top-Level Section

Edit `doc/sphinx/source/index.rst` and add your section to the toctree:

```rst
Contents
========

.. toctree::
   :maxdepth: 2

   server/index
   new_top_level/index
```

## Useful Make Targets

| Target | Description |
|--------|-------------|
| `make html` | Build HTML documentation |
| `make clean` | Remove build directory |
| `make view` | Build and open in browser |
| `make latex` | Build LaTeX documentation |
| `make text` | Build plain text documentation |

## Documentation Dependencies

Dependencies are specified in `pyproject.toml` under `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
docs = [
    "sphinx>=4.0.0",
    "sphinx-rtd-theme>=0.5.0",
]
```

Install them with: `pip install -e ".[docs]"`

## Tips

- Use `.. code-block:: bash` for command examples
- Use `.. note::` for notes
- Use `.. warning::` for warnings
- Use `:ref:` to create cross-references between documents
- Every document that should appear in the table of contents must be listed in a `toctree` directive
