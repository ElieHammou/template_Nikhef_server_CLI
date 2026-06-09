.. _server-tutorial:

Server Tutorial
===============

This tutorial covers all the commands available in the example Server CLI.

Resources are organised into three types: ``events``, ``analyses``, and ``misc``.
Two servers are available: ``public`` and ``private``.

**Default server selection** — all commands auto-detect the server:

- Private credentials configured → **private server** used by default.
- Public credentials configured → **public server** used by default.

Use ``--server public`` or ``--server private`` to override explicitly.

Installation
------------

.. code-block:: bash

   pip install -e /path/to/example_server
   # or from inside the repo directory:
   pip install -e .

First-time setup
----------------

All users must run setup once to configure server credentials:

.. code-block:: bash

   # From a credentials file (recommended)
   example_server setup my_credentials.yaml

   # Or interactively
   example_server setup

   # Overwrite an existing config
   example_server setup my_credentials.yaml --force

The credentials file format (include only the profiles you have access to):

.. code-block:: yaml

   public:
     webdav_hostname: https://surfdrive.surf.nl/public.php/webdav/
     webdav_login:    <token>
     webdav_password: <password>
     name:            Alice  # optional — shown in the registry next to uploads
   private:
     webdav_hostname: https://surfdrive.surf.nl/public.php/webdav/
     webdav_login:    <private-token>
     webdav_password: <password>
     name:            Alice

Credentials are saved to ``~/.config/example/server.yaml`` (mode 600).

List resources on the server
----------------------------

.. code-block:: bash

   # Display the full registry (events, analyses, projects)
   example_ls
   example_ls registry

   # List events
   example_ls events

   # List analyses
   example_ls analyses

   # List contents of misc/ with metadata
   example_ls misc

   # List trashed resources with deletion metadata
   example_ls bin
   example_ls bin --type events   # filter by resource type: events, analyses, or misc

   # Filter by project label
   example_ls events --project my_project

   # Target a specific server
   example_ls registry --server public

Upload
------

.. code-block:: bash

   # Upload an events set — prompts for an optional comment, then project selection
   example_upload events run42

   # Pass a comment directly with -m to skip the interactive prompt
   example_upload events run42 -m "Run 42, nominal beam conditions"

   # Upload from a specific local path
   example_upload events run42 /path/to/run42

   # Overwrite if it already exists on the server
   example_upload events run42 --force

   # Upload an analysis
   example_upload analyses myanalysis

   # Upload a file to misc/
   example_upload misc output.pkl
   example_upload misc results/run42/output.pkl /local/path/output.pkl

The comment is stored in the registry and shown in ``example_ls`` output.
After the comment prompt you are shown the project list and can pick one by number
(press Enter to skip). Use ``--project NAME`` to assign a project non-interactively.

Download
--------

.. code-block:: bash

   # Download an events set or analysis
   example_get events run42
   example_get analyses myanalysis

   # Download to a specific directory
   example_get events run42 /path/to/output

   # Download a file from misc/
   example_get misc results/run42/output.pkl

   # Explicitly target a server
   example_get events run42 --server public

misc/ — free-form storage
--------------------------

The ``misc/`` folder has no assumed structure. Files can be stored at any path inside it.

.. code-block:: bash

   # Create a directory structure inside misc/
   example_mkdir results/run42
   example_mkdir data/2026/june

   # Rename or remove entries in misc/
   example_mv misc old/path new/path
   example_rm misc results/run42/output.pkl

``example_mkdir`` only works in ``misc/`` — it will error if called on events or analyses.

Rename / update comment
-----------------------

``example_mv`` can rename a resource, update its comment, or both in one step.
At least one of ``NEW_NAME`` or ``--comment`` must be supplied.

.. code-block:: bash

   # Rename only
   example_mv events run42 run42_nominal
   example_mv analyses myanalysis myanalysis_v2 --server public
   example_mv misc old/path new/path

   # Update comment only (fix a typo, add precision)
   example_mv events run42 --comment "Run 42, nominal beam, 13.6 TeV"
   example_mv events run42 -c "Run 42, nominal beam, 13.6 TeV"

   # Rename and update comment in one step
   example_mv events run42 run42_nominal --comment "Run 42, nominal beam, 13.6 TeV"

Remove resources
---------------

Resources are **not permanently deleted** — they are moved to a ``bin/`` folder on the
server. The resource is removed from the registry and its entry (date, deleter, comment,
original metadata) is written to ``bin/registry_bin.json``.

.. code-block:: bash

   # Prompts for a deletion comment, then confirmation
   example_rm events run42

   # Provide comment inline to skip the prompt
   example_rm events run42 -m "superseded by run43"

   # Move multiple resources to bin at once (same comment applied to all)
   example_rm events run40 run41 run42

   # Skip confirmation prompt
   example_rm events run42 -f

   example_rm analyses myanalysis --server public
   example_rm misc results/run42/output.pkl

View what is currently in the bin:

.. code-block:: bash

   example_ls bin
   example_ls bin --type events

Restore resources
-----------------

Moves a resource from ``bin/`` back to its original remote path and reinstates its
registry entry. Fails if the original location is already occupied.

.. code-block:: bash

   example_restore events run42
   example_restore analyses myanalysis --server public
   example_restore misc results/run42/output.pkl

Projects
--------

Projects are metadata labels that can be attached to events and analyses to group them.
The list of valid projects is stored in the registry and managed with ``example_manage_project``.

.. code-block:: bash

   # List available projects
   example_manage_project list

   # Add a new project
   example_manage_project add LHCb_collab

   # Rename a project (updates all resources that reference it)
   example_manage_project rename LHCb_collab LHCb_collaboration

   # Remove a project
   example_manage_project remove LHCb_collaboration

During ``example_upload``, after the comment prompt, you are shown the project list and
can pick one by number (press Enter to skip). Use ``--project NAME`` to assign non-interactively:

.. code-block:: bash

   example_upload events run42 --project LHCb_collab

Server management
-----------------

.. code-block:: bash

   # Configure credentials (from a shared YAML file or interactively)
   example_server setup my_credentials.yaml
   example_server setup               # interactive
   example_server setup --force       # overwrite existing config

   # Show used / free space on the server
   example_server storage
   example_server storage --server private

   # Rebuild the registry from scratch
   example_server sync
   example_server sync --server public

   # List all available example commands with descriptions
   example_server tutorial

Sync details
~~~~~~~~~~~

``registry.json`` is updated automatically by ``example_upload``, ``example_mv``, and ``example_rm``.
If it ever drifts out of sync (e.g. files moved outside these tools), rebuild it with
``example_server sync``. Existing ``created_at`` and ``uploaded_by`` values are preserved where
possible; entries not previously in the registry receive the current time as a fallback.
Requires write credentials.
