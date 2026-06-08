#!/usr/bin/env python3
"""
Generate a WebDAV server CLI package from a minimal configuration.

Edit CONFIG below, then run:
    python generate_server_cli.py [output_dir]

'misc' free-form storage is always included automatically.
All other types in 'archivable_types' are stored as tar.gz archives.
"""

import pathlib
import sys

# ---------------------------------------------------------------------------
# Edit this — everything else is derived automatically
# ---------------------------------------------------------------------------

CONFIG = {
    "package":          "my_server",           # pip package name & Python package dir
    "prefix":           "example",                  # CLI command prefix: my_ls, my_upload …
    "project":          "MyProject",           # display name used in docs and titles
    "archivable_types": ["type_a", "type_b"],  # resource types stored as tar.gz archives
    "config_dir":       "myproject",           # credentials in ~/.config/<config_dir>/server.yaml
    "description":      "CLI tools for the MyProject WebDAV server",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sub(text: str, **kw) -> str:
    """Replace <<KEY>> with kw[KEY] throughout text."""
    for k, v in kw.items():
        text = text.replace(f"<<{k}>>", v)
    return text


def _pylist(items):
    return "[" + ", ".join(f'"{i}"' for i in items) + "]"


def _pytuple(items):
    if len(items) == 1:
        return f'("{items[0]}",)'
    return "(" + ", ".join(f'"{i}"' for i in items) + ")"


def _choices_str(items):
    return ", ".join(f'"{i}"' for i in items)


# ---------------------------------------------------------------------------
# Dynamic code-snippet generators
# ---------------------------------------------------------------------------

def _remote_dirs_dict(archivable):
    all_types = archivable + ["misc"]
    pairs = [f'    "{t}": "{t}"' for t in all_types]
    return "{\n" + ",\n".join(pairs) + "\n}"


def _empty_registry_body(archivable):
    entries = [f'    "{t}": {{}}' for t in archivable] + ['    "projects": []']
    return "{\n" + ",\n".join(entries) + "\n    }"


def _sync_loops(archivable):
    blocks = []
    for rtype in archivable:
        singular = rtype.rstrip("s") if rtype.endswith("s") else rtype
        blocks.append(
            f'    for name in _list_resource_names(client, "{rtype}"):\n'
            f'        try:\n'
            f'            log.info("Registering {singular} \'%s\' ...", name)\n'
            f'            old = old_registry["{rtype}"].get(name, {{}})\n'
            f'            registry["{rtype}"][name] = {{\n'
            f'                "created_at": old.get("created_at", now),\n'
            f'                "uploaded_by": old.get("uploaded_by"),\n'
            f'            }}\n'
            f'        except Exception as exc:\n'
            f'            log.warning("Skipping {rtype} \'%s\': %s", name, exc)'
        )
    return "\n\n".join(blocks)


def _rename_project_sections(archivable):
    return '    for section in (' + ", ".join(f'"{t}"' for t in archivable) + "):"


def _ls_registry_block(archivable):
    lines = ['        if args.resource_type == "registry":']
    lines.append('            registry = downloader.get_registry()')
    for rtype in archivable:
        lines.append(f'            {rtype} = _filter(registry.get("{rtype}", {{}}))')
    for rtype in archivable:
        title = rtype.capitalize()
        lines.append(
            f'            _table(f"{title} ({{len({rtype})}})" + title_suffix,'
            f' *_resource_rows({rtype}))'
        )
    lines += [
        '            if not project_filter:',
        '                projects = sorted(registry.get("projects", []))',
        '                print(f"\\n  {_header(f\'Projects ({len(projects)})\')}")',
        '                if projects:',
        '                    for p in projects:',
        '                        print(f"    {_green(p)}")',
        '                else:',
        '                    print(_dim("  (none)"))',
        '            print()',
    ]
    return "\n".join(lines)


def _ls_elif_blocks(archivable):
    blocks = []
    for rtype in archivable:
        title = rtype.capitalize()
        blocks.append(
            f'        elif args.resource_type == "{rtype}":\n'
            f'            resources = downloader.list_resources("{rtype}")\n'
            f'            registry = downloader.get_registry()\n'
            f'            items = _filter(\n'
            f'                {{r: registry["{rtype}"][r] for r in resources'
            f' if r in registry["{rtype}"]}}\n'
            f'            )\n'
            f'            _table(f"{title} ({{len(items)}})" + title_suffix,'
            f' *_resource_rows(items))\n'
            f'            if not project_filter:\n'
            f'                for r in resources:\n'
            f'                    if r not in registry["{rtype}"]:\n'
            f'                        print(f"  {{_bold(r)}}'
            f'  {{_dim(\'(not in registry)\')}}")\n'
            f'            print()'
        )
    return "\n\n".join(blocks)


def _tutorial_commands(prefix, archivable):
    p = prefix
    archivable_str = ", ".join(archivable)
    lines = [
        f'    ("{p}_ls",',
        f'     "List server resources — {archivable_str}, registry, misc, bin.\\n"',
        f'     "Use --project NAME to filter by project."),',
        f'    ("{p}_upload", "Upload a resource or misc file to the server."),',
        f'    ("{p}_get",    "Download a resource or misc file."),',
        f'    ("{p}_mv",',
        f'     "Rename a resource and/or update its comment.\\n"',
        f'     "NEW_NAME is optional when --comment / -c is given."),',
        f'    ("{p}_rm",',
        f'     "Move one or more resources to bin/ on the server.\\n"',
        f'     "Prompts for a deletion comment. Use -f to skip confirmation."),',
        f'    ("{p}_restore",        "Restore a resource from bin/ to its original location."),',
        f'    ("{p}_mkdir",          "Create a directory under misc/ on the server."),',
        f'    ("{p}_manage_project", "Manage the project list: add / rename / remove / list."),',
        f'    ("{p}_server",         "Setup credentials, check storage, sync registry."),',
    ]
    return "\n".join(lines)


def _pyproject_scripts(pkg, prefix):
    p = prefix
    lines = [
        f'{p}_ls              = "{pkg}.scripts.{p}_ls:main"',
        f'{p}_upload          = "{pkg}.scripts.{p}_upload:main"',
        f'{p}_get             = "{pkg}.scripts.{p}_get:main"',
        f'{p}_mv              = "{pkg}.scripts.{p}_mv:main"',
        f'{p}_rm              = "{pkg}.scripts.{p}_rm:main"',
        f'{p}_restore         = "{pkg}.scripts.{p}_restore:main"',
        f'{p}_mkdir           = "{pkg}.scripts.{p}_mkdir:main"',
        f'{p}_manage_project  = "{pkg}.scripts.{p}_manage_project:main"',
        f'{p}_server          = "{pkg}.scripts.{p}_server:main"',
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File generators — all use '''...''' templates + sub() substitution.
# Python {braces} in templates pass through sub() unchanged.
# ---------------------------------------------------------------------------

def gen_pyproject(pkg, prefix, desc, archivable):
    return sub(
        '[build-system]\n'
        'requires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n'
        '\n'
        '[project]\n'
        'name = "<<PKG>>"\n'
        'version = "0.1.0"\n'
        'description = "<<DESC>>"\n'
        'requires-python = ">=3.12"\n'
        'dependencies = [\n'
        '    "webdavclient3",\n'
        '    "pyyaml",\n'
        ']\n'
        '\n'
        '[project.scripts]\n'
        '<<SCRIPTS>>\n',
        PKG=pkg, DESC=desc, SCRIPTS=_pyproject_scripts(pkg, prefix),
    )


def gen_logging():
    # Identical for all packages — no substitution needed.
    return '''\
"""Simple color logging handler — no external dependencies."""

import logging
import sys

_USE_COLOR = hasattr(sys.stderr, "isatty") and sys.stderr.isatty()

_LEVEL_COLORS = {
    logging.DEBUG:    "\\033[2m",
    logging.INFO:     "\\033[0m",
    logging.WARNING:  "\\033[33m",
    logging.ERROR:    "\\033[31m",
    logging.CRITICAL: "\\033[31;1m",
}
_RESET = "\\033[0m"


class ColorHandler(logging.StreamHandler):
    def __init__(self):
        super().__init__(stream=sys.stdout)
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record):
        try:
            msg = self.format(record)
            if _USE_COLOR:
                color = _LEVEL_COLORS.get(record.levelno, "")
                line = (
                    f"{color}{record.levelname}: {msg}{_RESET}"
                    if record.levelno >= logging.WARNING
                    else f"{color}{msg}{_RESET}"
                )
            else:
                line = (
                    f"{record.levelname}: {msg}"
                    if record.levelno >= logging.WARNING
                    else msg
                )
            stream = sys.stderr if record.levelno >= logging.WARNING else sys.stdout
            print(line, file=stream)
        except Exception:
            self.handleError(record)
'''


def gen_server_utils(pkg, prefix, project, config_dir, archivable):
    all_types = archivable + ["misc"]
    return sub(
        '"""\n'
        'Tools to upload/download resources to/from the <<PROJECT>> WebDAV server.\n'
        '\n'
        'Config file (~/.config/<<CONFIG_DIR>>/server.yaml):\n'
        '    public:\n'
        '      webdav_hostname: https://...\n'
        '      webdav_login:    <token>\n'
        '      webdav_password: <password>\n'
        '      name:            Alice   # optional, shown in registry\n'
        '    private: ...\n'
        '\n'
        "Run '<<PREFIX>>_server setup' to create this file.\n"
        '"""\n'
        '\n'
        'import datetime\n'
        'import json\n'
        'import logging\n'
        'import pathlib\n'
        'import tarfile\n'
        'import tempfile\n'
        '\n'
        'import yaml\n'
        '\n'
        'log = logging.getLogger(__name__)\n'
        '\n'
        'RESOURCE_TYPES = <<ALL_TYPES>>\n'
        '_ARCHIVABLE_TYPES = <<ARCHIVABLE>>\n'
        'REGISTRY_PATH = "registry.json"\n'
        'MISC_REGISTRY_PATH = "misc/registry_misc.json"\n'
        'BIN_DIR = "bin"\n'
        'BIN_REGISTRY_PATH = "bin/registry_bin.json"\n'
        'SERVERS = ["public", "private"]\n'
        '\n'
        '_REMOTE_DIRS = <<REMOTE_DIRS>>\n'
        '\n'
        'CONFIG_PATH = pathlib.Path.home() / ".config" / "<<CONFIG_DIR>>" / "server.yaml"\n'
        '\n'
        '\n'
        'class ServerError(Exception):\n'
        '    pass\n'
        '\n'
        '\n'
        'def _load_config() -> dict:\n'
        '    if not CONFIG_PATH.exists():\n'
        '        return {}\n'
        '    with open(CONFIG_PATH) as f:\n'
        '        return yaml.safe_load(f) or {}\n'
        '\n'
        '\n'
        'def _auto_server(config: dict, need_write: bool) -> str:\n'
        '    if "private" in config:\n'
        '        return "private"\n'
        '    if "public" in config:\n'
        '        return "public"\n'
        '    raise ServerError(\n'
        '        f"No server credentials found in {CONFIG_PATH}.\\n"\n'
        '        "Run \'<<PREFIX>>_server setup\' to configure your credentials."\n'
        '    )\n'
        '\n'
        '\n'
        'def _get_client(server: str | None, need_write: bool = False):\n'
        '    from webdav3.client import Client\n'
        '    config = _load_config()\n'
        '    if server is None:\n'
        '        server = _auto_server(config, need_write)\n'
        '    hint = "Run \'<<PREFIX>>_server setup\' to configure your credentials."\n'
        '    if server == "public":\n'
        '        if "public" not in config:\n'
        '            raise ServerError(\n'
        '                f"Public server credentials not found in {CONFIG_PATH}.\\n{hint}"\n'
        '            )\n'
        '    elif server == "private":\n'
        '        if "private" not in config:\n'
        '            raise ServerError(\n'
        '                f"Private server credentials not found in {CONFIG_PATH}.\\n{hint}"\n'
        '            )\n'
        '    else:\n'
        '        raise ServerError(f"Unknown server \'{server}\'. Choose from: public, private")\n'
        '    profile = config[server]\n'
        '    for key in ("webdav_hostname", "webdav_login", "webdav_password"):\n'
        '        if key not in profile:\n'
        '            raise ServerError(f"Missing key \'{key}\' under \'{server}:\' in {CONFIG_PATH}")\n'
        '    return Client(profile)\n'
        '\n'
        '\n'
        'def _remote_path(resource_type: str, resource_name: str) -> str:\n'
        '    if resource_type == "misc":\n'
        '        return f"misc/{resource_name}"\n'
        '    return f"{_REMOTE_DIRS[resource_type]}/{resource_name}.tar.gz"\n'
        '\n'
        '\n'
        'def _compress(source: pathlib.Path, archive_path: pathlib.Path,\n'
        '              arcname: str | None = None) -> None:\n'
        '    log.info("Compressing %s ...", source)\n'
        '    with tarfile.open(archive_path, "w:gz") as tar:\n'
        '        tar.add(source, arcname=arcname or source.name)\n'
        '\n'
        '\n'
        'def _extract(archive_path: pathlib.Path, dest: pathlib.Path) -> None:\n'
        '    log.info("Extracting to %s ...", dest)\n'
        '    with tarfile.open(archive_path, "r:gz") as tar:\n'
        '        tar.extractall(dest)\n'
        '\n'
        '\n'
        'def _ensure_remote_path(client, path: str) -> None:\n'
        '    parts = pathlib.PurePosixPath(path).parts\n'
        '    for i in range(1, len(parts) + 1):\n'
        '        segment = str(pathlib.PurePosixPath(*parts[:i]))\n'
        '        if not client.check(segment):\n'
        '            client.mkdir(segment)\n'
        '\n'
        '\n'
        'def _empty_registry() -> dict:\n'
        '    return <<EMPTY_REGISTRY>>\n'
        '\n'
        '\n'
        'def _read_registry(client) -> dict:\n'
        '    if not client.check(REGISTRY_PATH):\n'
        '        return _empty_registry()\n'
        '    with tempfile.TemporaryDirectory(prefix="<<PREFIX>>_registry_") as tmpdir:\n'
        '        tmp = pathlib.Path(tmpdir) / "registry.json"\n'
        '        client.download_sync(remote_path=REGISTRY_PATH, local_path=str(tmp))\n'
        '        data = json.loads(tmp.read_text())\n'
        '    return {**_empty_registry(), **data}\n'
        '\n'
        '\n'
        'def _write_registry(client, registry: dict) -> None:\n'
        '    with tempfile.TemporaryDirectory(prefix="<<PREFIX>>_registry_") as tmpdir:\n'
        '        tmp = pathlib.Path(tmpdir) / "registry.json"\n'
        '        tmp.write_text(json.dumps(registry, indent=2, sort_keys=True))\n'
        '        client.upload_sync(remote_path=REGISTRY_PATH, local_path=str(tmp))\n'
        '\n'
        '\n'
        'def _read_misc_registry(client) -> dict:\n'
        '    if not client.check(MISC_REGISTRY_PATH):\n'
        '        return {}\n'
        '    with tempfile.TemporaryDirectory(prefix="<<PREFIX>>_misc_reg_") as tmpdir:\n'
        '        tmp = pathlib.Path(tmpdir) / "registry_misc.json"\n'
        '        client.download_sync(remote_path=MISC_REGISTRY_PATH, local_path=str(tmp))\n'
        '        return json.loads(tmp.read_text())\n'
        '\n'
        '\n'
        'def _write_misc_registry(client, registry: dict) -> None:\n'
        '    with tempfile.TemporaryDirectory(prefix="<<PREFIX>>_misc_reg_") as tmpdir:\n'
        '        tmp = pathlib.Path(tmpdir) / "registry_misc.json"\n'
        '        tmp.write_text(json.dumps(registry, indent=2, sort_keys=True))\n'
        '        client.upload_sync(remote_path=MISC_REGISTRY_PATH, local_path=str(tmp))\n'
        '\n'
        '\n'
        'def _read_bin_registry(client) -> dict:\n'
        '    if not client.check(BIN_REGISTRY_PATH):\n'
        '        return {}\n'
        '    with tempfile.TemporaryDirectory(prefix="<<PREFIX>>_bin_reg_") as tmpdir:\n'
        '        tmp = pathlib.Path(tmpdir) / "registry_bin.json"\n'
        '        client.download_sync(remote_path=BIN_REGISTRY_PATH, local_path=str(tmp))\n'
        '        return json.loads(tmp.read_text())\n'
        '\n'
        '\n'
        'def _write_bin_registry(client, registry: dict) -> None:\n'
        '    _ensure_remote_path(client, BIN_DIR)\n'
        '    with tempfile.TemporaryDirectory(prefix="<<PREFIX>>_bin_reg_") as tmpdir:\n'
        '        tmp = pathlib.Path(tmpdir) / "registry_bin.json"\n'
        '        tmp.write_text(json.dumps(registry, indent=2, sort_keys=True))\n'
        '        client.upload_sync(remote_path=BIN_REGISTRY_PATH, local_path=str(tmp))\n'
        '\n'
        '\n'
        'def _list_resource_names(client, resource_type: str) -> list[str]:\n'
        '    remote_dir = _REMOTE_DIRS[resource_type]\n'
        '    if not client.check(remote_dir):\n'
        '        return []\n'
        '    names = []\n'
        '    for e in client.list(remote_dir):\n'
        '        e = e.rstrip("/")\n'
        '        if e in (remote_dir, ""):\n'
        '            continue\n'
        '        if resource_type in _ARCHIVABLE_TYPES:\n'
        '            if not e.endswith(".tar.gz"):\n'
        '                continue\n'
        '            e = e[: -len(".tar.gz")]\n'
        '        elif resource_type == "misc" and e == "registry_misc.json":\n'
        '            continue\n'
        '        names.append(e)\n'
        '    return names\n'
        '\n'
        '\n'
        'def rename(\n'
        '    resource_type: str,\n'
        '    old_name: str,\n'
        '    new_name: str | None = None,\n'
        '    server: str | None = None,\n'
        '    comment: str | None = None,\n'
        ') -> None:\n'
        '    """Rename a resource and/or update its comment."""\n'
        '    if resource_type not in RESOURCE_TYPES:\n'
        '        raise ServerError(\n'
        '            f"Unknown resource type \'{resource_type}\'. "\n'
        '            f"Choose from: {\', \'.join(RESOURCE_TYPES)}"\n'
        '        )\n'
        '    if new_name is None and comment is None:\n'
        '        raise ServerError("Provide a new name, a --comment, or both.")\n'
        '    client = _get_client(server, need_write=True)\n'
        '    if new_name is not None and new_name != old_name:\n'
        '        old_remote = _remote_path(resource_type, old_name)\n'
        '        new_remote = _remote_path(resource_type, new_name)\n'
        '        if not client.check(old_remote):\n'
        '            raise ServerError(f"Resource \'{old_name}\' not found on server.")\n'
        '        if client.check(new_remote):\n'
        '            raise ServerError(\n'
        '                f"\'{new_name}\' already exists on server. Choose a different name."\n'
        '            )\n'
        '        if resource_type == "misc":\n'
        '            _ensure_remote_path(client, str(pathlib.PurePosixPath(new_remote).parent))\n'
        '        client.move(remote_path_from=old_remote, remote_path_to=new_remote)\n'
        '        log.info("Renamed \'%s\' -> \'%s\'.", old_name, new_name)\n'
        '    else:\n'
        '        new_name = old_name\n'
        '        if not client.check(_remote_path(resource_type, old_name)):\n'
        '            raise ServerError(f"Resource \'{old_name}\' not found on server.")\n'
        '    if resource_type in _ARCHIVABLE_TYPES:\n'
        '        registry = _read_registry(client)\n'
        '        section = registry[resource_type]\n'
        '        if old_name in section:\n'
        '            entry = section.pop(old_name)\n'
        '            if comment is not None:\n'
        '                entry["comment"] = comment\n'
        '                log.info("Updated comment for \'%s\'.", new_name)\n'
        '            section[new_name] = entry\n'
        '            _write_registry(client, registry)\n'
        '    elif resource_type == "misc":\n'
        '        misc_reg = _read_misc_registry(client)\n'
        '        if old_name in misc_reg:\n'
        '            entry = misc_reg.pop(old_name)\n'
        '            if comment is not None:\n'
        '                entry["comment"] = comment\n'
        '                log.info("Updated comment for \'%s\'.", new_name)\n'
        '            misc_reg[new_name] = entry\n'
        '            _write_misc_registry(client, misc_reg)\n'
        '\n'
        '\n'
        'def trash(\n'
        '    resource_type: str,\n'
        '    resource_name: str,\n'
        '    server: str | None = None,\n'
        '    message: str | None = None,\n'
        ') -> None:\n'
        '    """Move a resource into bin/ instead of permanently deleting it."""\n'
        '    if resource_type not in RESOURCE_TYPES:\n'
        '        raise ServerError(\n'
        '            f"Unknown resource type \'{resource_type}\'. "\n'
        '            f"Choose from: {\', \'.join(RESOURCE_TYPES)}"\n'
        '        )\n'
        '    config = _load_config()\n'
        '    resolved_server = server if server is not None else _auto_server(config, need_write=True)\n'
        '    deleter_name = config.get(resolved_server, {}).get("name")\n'
        '    client = _get_client(server, need_write=True)\n'
        '    remote = _remote_path(resource_type, resource_name)\n'
        '    if not client.check(remote):\n'
        '        raise ServerError(f"Resource \'{resource_name}\' not found on server.")\n'
        '    registry: dict = {}\n'
        '    misc_reg: dict = {}\n'
        '    original_meta: dict = {}\n'
        '    if resource_type in _ARCHIVABLE_TYPES:\n'
        '        registry = _read_registry(client)\n'
        '        original_meta = registry.get(resource_type, {}).get(resource_name, {})\n'
        '    elif resource_type == "misc":\n'
        '        misc_reg = _read_misc_registry(client)\n'
        '        original_meta = misc_reg.get(resource_name, {})\n'
        '    bin_remote = f"{BIN_DIR}/{remote}"\n'
        '    _ensure_remote_path(client, str(pathlib.PurePosixPath(bin_remote).parent))\n'
        '    client.move(remote_path_from=remote, remote_path_to=bin_remote)\n'
        '    log.info("Moved \'%s\' to bin.", resource_name)\n'
        '    if resource_type in _ARCHIVABLE_TYPES:\n'
        '        if resource_name in registry.get(resource_type, {}):\n'
        '            del registry[resource_type][resource_name]\n'
        '            _write_registry(client, registry)\n'
        '    elif resource_type == "misc":\n'
        '        if resource_name in misc_reg:\n'
        '            del misc_reg[resource_name]\n'
        '            _write_misc_registry(client, misc_reg)\n'
        '    bin_reg = _read_bin_registry(client)\n'
        '    entry: dict = {\n'
        '        "deleted_at": datetime.datetime.now().isoformat(timespec="seconds"),\n'
        '        "deleted_by": deleter_name,\n'
        '        "resource_type": resource_type,\n'
        '        "resource_name": resource_name,\n'
        '        "original_meta": original_meta,\n'
        '    }\n'
        '    if message:\n'
        '        entry["comment"] = message\n'
        '    bin_reg[f"{resource_type}/{resource_name}"] = entry\n'
        '    _write_bin_registry(client, bin_reg)\n'
        '\n'
        '\n'
        'def restore(\n'
        '    resource_type: str,\n'
        '    resource_name: str,\n'
        '    server: str | None = None,\n'
        ') -> None:\n'
        '    """Move a resource from bin/ back to its original location."""\n'
        '    if resource_type not in RESOURCE_TYPES:\n'
        '        raise ServerError(\n'
        '            f"Unknown resource type \'{resource_type}\'. "\n'
        '            f"Choose from: {\', \'.join(RESOURCE_TYPES)}"\n'
        '        )\n'
        '    client = _get_client(server, need_write=True)\n'
        '    key = f"{resource_type}/{resource_name}"\n'
        '    bin_reg = _read_bin_registry(client)\n'
        '    if key not in bin_reg:\n'
        '        raise ServerError(f"\'{resource_name}\' (type: {resource_type}) is not in the bin.")\n'
        '    entry = bin_reg[key]\n'
        '    remote = _remote_path(resource_type, resource_name)\n'
        '    bin_remote = f"{BIN_DIR}/{remote}"\n'
        '    if not client.check(bin_remote):\n'
        '        raise ServerError(\n'
        '            f"Binned file not found at \'{bin_remote}\'. "\n'
        '            "The bin registry may be out of sync — run \'<<PREFIX>>_server sync\'."\n'
        '        )\n'
        '    if client.check(remote):\n'
        '        raise ServerError(\n'
        '            f"\'{resource_name}\' already exists at its original location. "\n'
        '            "Rename or remove it before restoring."\n'
        '        )\n'
        '    _ensure_remote_path(client, str(pathlib.PurePosixPath(remote).parent))\n'
        '    client.move(remote_path_from=bin_remote, remote_path_to=remote)\n'
        '    log.info("Restored \'%s\' to %s.", resource_name, remote)\n'
        '    original_meta = entry.get("original_meta", {})\n'
        '    if resource_type in _ARCHIVABLE_TYPES:\n'
        '        registry = _read_registry(client)\n'
        '        registry[resource_type][resource_name] = original_meta\n'
        '        _write_registry(client, registry)\n'
        '    elif resource_type == "misc":\n'
        '        misc_reg = _read_misc_registry(client)\n'
        '        misc_reg[resource_name] = original_meta\n'
        '        _write_misc_registry(client, misc_reg)\n'
        '    del bin_reg[key]\n'
        '    _write_bin_registry(client, bin_reg)\n'
        '    log.info("Registry restored.")\n'
        '\n'
        '\n'
        'class Uploader:\n'
        '    def __init__(self, server: str | None = None):\n'
        '        config = _load_config()\n'
        '        resolved_server = server if server is not None else _auto_server(config, need_write=True)\n'
        '        self._client = _get_client(server, need_write=True)\n'
        '        self._server = resolved_server\n'
        '        self._uploader_name = config.get(resolved_server, {}).get("name")\n'
        '\n'
        '    def _ensure_remote_dir(self, resource_type: str) -> None:\n'
        '        remote_dir = _REMOTE_DIRS[resource_type]\n'
        '        if not self._client.check(remote_dir):\n'
        '            self._client.mkdir(remote_dir)\n'
        '\n'
        '    def upload(\n'
        '        self,\n'
        '        resource_type: str,\n'
        '        resource_name: str,\n'
        '        local_path: pathlib.Path | None = None,\n'
        '        force: bool = False,\n'
        '        message: str | None = None,\n'
        '        project: str | None = None,\n'
        '    ) -> None:\n'
        '        resource_name = resource_name.rstrip("/\\\\")\n'
        '        if resource_type not in RESOURCE_TYPES:\n'
        '            raise ServerError(\n'
        '                f"Unknown resource type \'{resource_type}\'. "\n'
        '                f"Choose from: {\', \'.join(RESOURCE_TYPES)}"\n'
        '            )\n'
        '        if resource_type == "misc":\n'
        '            if local_path is None:\n'
        '                local_path = pathlib.Path(resource_name).name\n'
        '            local_path = pathlib.Path(local_path)\n'
        '            if not local_path.exists():\n'
        '                raise ServerError(f"Local path does not exist: {local_path}")\n'
        '            remote = _remote_path("misc", resource_name)\n'
        '            if not force and self._client.check(remote):\n'
        '                raise ServerError(\n'
        '                    f"\'misc/{resource_name}\' already exists on the {self._server} server. "\n'
        '                    "Use --force to overwrite."\n'
        '                )\n'
        '            _ensure_remote_path(self._client, str(pathlib.PurePosixPath(remote).parent))\n'
        '            log.info("Uploading %s -> %s ...", local_path, remote)\n'
        '            self._client.upload_sync(remote_path=remote, local_path=str(local_path))\n'
        '            log.info("Upload complete.")\n'
        '            misc_reg = _read_misc_registry(self._client)\n'
        '            entry = {\n'
        '                "uploaded_at": datetime.datetime.now().isoformat(timespec="seconds"),\n'
        '                "uploaded_by": self._uploader_name,\n'
        '            }\n'
        '            if message:\n'
        '                entry["comment"] = message\n'
        '            if project:\n'
        '                entry["project"] = project\n'
        '            misc_reg[resource_name] = entry\n'
        '            _write_misc_registry(self._client, misc_reg)\n'
        '            log.info("To download: <<PREFIX>>_get misc %s", resource_name)\n'
        '            return\n'
        '        if local_path is None:\n'
        '            local_path = pathlib.Path.cwd() / resource_name\n'
        '            resource_name = pathlib.Path(resource_name).name\n'
        '        local_path = pathlib.Path(local_path)\n'
        '        if not local_path.exists():\n'
        '            raise ServerError(f"Local path does not exist: {local_path}")\n'
        '        self._ensure_remote_dir(resource_type)\n'
        '        remote = _remote_path(resource_type, resource_name)\n'
        '        if not force and self._client.check(remote):\n'
        '            raise ServerError(\n'
        '                f"\'{resource_name}\' already exists on the {self._server} server. "\n'
        '                "Use --force to overwrite."\n'
        '            )\n'
        '        with tempfile.TemporaryDirectory(prefix="<<PREFIX>>_upload_") as tmpdir:\n'
        '            archive = pathlib.Path(tmpdir) / f"{resource_name}.tar.gz"\n'
        '            _compress(local_path, archive, arcname=resource_name)\n'
        '            log.info("Uploading %s -> %s ...", archive.name, remote)\n'
        '            self._client.upload_sync(remote_path=remote, local_path=str(archive))\n'
        '        log.info("Upload complete.")\n'
        '        registry = _read_registry(self._client)\n'
        '        entry = {\n'
        '            "created_at": datetime.datetime.now().isoformat(timespec="seconds"),\n'
        '            "uploaded_by": self._uploader_name,\n'
        '        }\n'
        '        if message:\n'
        '            entry["comment"] = message\n'
        '        if project:\n'
        '            entry["project"] = project\n'
        '        registry[resource_type][resource_name] = entry\n'
        '        _write_registry(self._client, registry)\n'
        '        log.info("Registry updated.")\n'
        '        log.info("To download: <<PREFIX>>_get %s %s", resource_type, resource_name)\n'
        '\n'
        '\n'
        'class Downloader:\n'
        '    def __init__(self, server: str | None = None):\n'
        '        self._client = _get_client(server, need_write=False)\n'
        '        self._server = server or "auto"\n'
        '\n'
        '    def get_registry(self) -> dict:\n'
        '        return _read_registry(self._client)\n'
        '\n'
        '    def get_misc_registry(self) -> dict:\n'
        '        return _read_misc_registry(self._client)\n'
        '\n'
        '    def get_bin_registry(self) -> dict:\n'
        '        return _read_bin_registry(self._client)\n'
        '\n'
        '    def list_resources(self, resource_type: str) -> list[str]:\n'
        '        if resource_type not in RESOURCE_TYPES:\n'
        '            raise ServerError(\n'
        '                f"Unknown resource type \'{resource_type}\'. "\n'
        '                f"Choose from: {\', \'.join(RESOURCE_TYPES)}"\n'
        '            )\n'
        '        return _list_resource_names(self._client, resource_type)\n'
        '\n'
        '    def download(\n'
        '        self,\n'
        '        resource_type: str,\n'
        '        resource_name: str,\n'
        '        local_path: pathlib.Path | None = None,\n'
        '    ) -> pathlib.Path:\n'
        '        if resource_type not in RESOURCE_TYPES:\n'
        '            raise ServerError(\n'
        '                f"Unknown resource type \'{resource_type}\'. "\n'
        '                f"Choose from: {\', \'.join(RESOURCE_TYPES)}"\n'
        '            )\n'
        '        if resource_type == "misc":\n'
        '            remote = _remote_path("misc", resource_name)\n'
        '            if not self._client.check(remote):\n'
        '                raise ServerError(\n'
        '                    f"misc/{resource_name} not found on the {self._server} server."\n'
        '                )\n'
        '            if local_path is None:\n'
        '                local_path = pathlib.Path.cwd()\n'
        '            local_path = pathlib.Path(local_path)\n'
        '            local_path.mkdir(parents=True, exist_ok=True)\n'
        '            dest = local_path / pathlib.Path(resource_name).name\n'
        '            log.info("Downloading %s ...", remote)\n'
        '            self._client.download_sync(remote_path=remote, local_path=str(dest))\n'
        '            log.info("Download complete: %s", dest)\n'
        '            return dest\n'
        '        if local_path is None:\n'
        '            local_path = pathlib.Path.cwd()\n'
        '        local_path = pathlib.Path(local_path)\n'
        '        local_path.mkdir(parents=True, exist_ok=True)\n'
        '        remote = _remote_path(resource_type, resource_name)\n'
        '        if not self._client.check(remote):\n'
        '            raise ServerError(\n'
        '                f"Resource \'{resource_name}\' (type: {resource_type}) "\n'
        '                f"not found on the {self._server} server."\n'
        '            )\n'
        '        with tempfile.TemporaryDirectory(prefix="<<PREFIX>>_download_") as tmpdir:\n'
        '            archive = pathlib.Path(tmpdir) / f"{resource_name}.tar.gz"\n'
        '            log.info("Downloading %s ...", remote)\n'
        '            self._client.download_sync(remote_path=remote, local_path=str(archive))\n'
        '            _extract(archive, local_path)\n'
        '        dest = local_path / resource_name\n'
        '        log.info("Download complete: %s", dest)\n'
        '        return dest\n'
        '\n'
        '\n'
        'def mkdir_misc(path: str, server: str | None = None) -> None:\n'
        '    client = _get_client(server, need_write=True)\n'
        '    full_path = f"misc/{path.strip(\'/\')}"\n'
        '    _ensure_remote_path(client, full_path)\n'
        '    log.info("Created misc/%s.", path.strip("/"))\n'
        '\n'
        '\n'
        'def sync_registry(server: str | None = None) -> dict:\n'
        '    """Rebuild the registry by inspecting all resources on the server."""\n'
        '    client = _get_client(server, need_write=True)\n'
        '    old_registry = _read_registry(client)\n'
        '    now = datetime.datetime.now().isoformat(timespec="seconds")\n'
        '    registry = _empty_registry()\n'
        '\n'
        '<<SYNC_LOOPS>>\n'
        '\n'
        '    registry["projects"] = old_registry.get("projects", [])\n'
        '    _write_registry(client, registry)\n'
        '    counts = ", ".join(f"{len(registry[t])} {t}" for t in _ARCHIVABLE_TYPES)\n'
        '    log.info("Registry synced: %s.", counts)\n'
        '    return registry\n'
        '\n'
        '\n'
        'def list_projects(server: str | None = None) -> list:\n'
        '    client = _get_client(server, need_write=False)\n'
        '    return sorted(_read_registry(client).get("projects", []))\n'
        '\n'
        '\n'
        'def add_project(project_name: str, server: str | None = None) -> None:\n'
        '    client = _get_client(server, need_write=True)\n'
        '    registry = _read_registry(client)\n'
        '    projects = registry.setdefault("projects", [])\n'
        '    if project_name in projects:\n'
        '        raise ServerError(f"Project \'{project_name}\' already exists.")\n'
        '    projects.append(project_name)\n'
        '    registry["projects"] = sorted(projects)\n'
        '    _write_registry(client, registry)\n'
        '    log.info("Added project \'%s\'.", project_name)\n'
        '\n'
        '\n'
        'def rename_project(old_name: str, new_name: str, server: str | None = None) -> None:\n'
        '    """Rename a project and update all resources that reference it."""\n'
        '    client = _get_client(server, need_write=True)\n'
        '    registry = _read_registry(client)\n'
        '    projects = registry.setdefault("projects", [])\n'
        '    if old_name not in projects:\n'
        '        raise ServerError(f"Project \'{old_name}\' not found.")\n'
        '    if new_name in projects:\n'
        '        raise ServerError(f"Project \'{new_name}\' already exists.")\n'
        '    projects[projects.index(old_name)] = new_name\n'
        '    registry["projects"] = sorted(projects)\n'
        '<<RENAME_PROJECT_SECTIONS>>\n'
        '        for meta in registry.get(section, {}).values():\n'
        '            if meta.get("project") == old_name:\n'
        '                meta["project"] = new_name\n'
        '    _write_registry(client, registry)\n'
        '    log.info("Renamed project \'%s\' -> \'%s\'.", old_name, new_name)\n'
        '\n'
        '\n'
        'def remove_project(project_name: str, server: str | None = None) -> None:\n'
        '    client = _get_client(server, need_write=True)\n'
        '    registry = _read_registry(client)\n'
        '    projects = registry.setdefault("projects", [])\n'
        '    if project_name not in projects:\n'
        '        raise ServerError(f"Project \'{project_name}\' not found.")\n'
        '    projects.remove(project_name)\n'
        '    registry["projects"] = sorted(projects)\n'
        '    _write_registry(client, registry)\n'
        '    log.info("Removed project \'%s\'.", project_name)\n'
        '\n'
        '\n'
        'def get_free_space(server: str | None = None) -> int:\n'
        '    return _get_client(server, need_write=False).free()\n',
        PKG=pkg, PREFIX=prefix, PROJECT=project, CONFIG_DIR=config_dir,
        ALL_TYPES=_pylist(all_types),
        ARCHIVABLE=_pylist(archivable),
        REMOTE_DIRS=_remote_dirs_dict(archivable),
        EMPTY_REGISTRY=_empty_registry_body(archivable),
        SYNC_LOOPS=_sync_loops(archivable),
        RENAME_PROJECT_SECTIONS=_rename_project_sections(archivable),
    )


def gen_ls(pkg, prefix, project, archivable):
    all_types = archivable + ["misc"]
    ls_choices = _choices_str(archivable + ["registry", "misc", "bin"])
    bin_choices = _choices_str(all_types)
    project_cond = _pytuple(archivable)
    reg_block  = _ls_registry_block(archivable)
    elif_blocks = _ls_elif_blocks(archivable)

    # Template uses plain string concatenation — no f-strings, so {braces} pass through.
    template = (
        '"""\n'
        'List resources available on the <<PROJECT>> server.\n'
        '\n'
        '    <<PREFIX>>_ls [RESOURCE_TYPE] [--server public|private] [--project NAME]\n'
        '\n'
        'RESOURCE_TYPE: <<LS_CHOICES_DOC>>, registry, misc, bin  (default: registry).\n'
        '"""\n'
        'import argparse\n'
        'import logging\n'
        'import sys\n'
        '\n'
        'from <<PKG>>._logging import ColorHandler\n'
        '\n'
        'log = logging.getLogger()\n'
        'log.setLevel(logging.INFO)\n'
        'log.addHandler(ColorHandler())\n'
        '\n'
        '_USE_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()\n'
        '\n'
        '\n'
        'def _c(text, *codes):\n'
        '    return ("".join(codes) + str(text) + "\\033[0m") if _USE_COLOR else str(text)\n'
        '\n'
        '\n'
        '_BOLD  = "\\033[1m"\n'
        '_DIM   = "\\033[2m"\n'
        '_CYAN  = "\\033[36m"\n'
        '_GREEN = "\\033[32m"\n'
        '\n'
        '\n'
        'def _header(s): return _c(s, _BOLD, _CYAN)\n'
        'def _bold(s):   return _c(s, _BOLD)\n'
        'def _dim(s):    return _c(s, _DIM)\n'
        'def _green(s):  return _c(s, _GREEN)\n'
        'def _cmt(s):    return _dim(f\'"{s[:50]}{"..." if len(s) > 50 else ""}"\' )\n'
        '\n'
        '\n'
        'def _table(title, headers, plain_rows, colored_rows):\n'
        '    print(f"\\n  {_header(title)}")\n'
        '    if not plain_rows:\n'
        '        print(_dim("  (none)"))\n'
        '        return\n'
        '    widths = [len(h) for h in headers]\n'
        '    for row in plain_rows:\n'
        '        for i, cell in enumerate(row):\n'
        '            widths[i] = max(widths[i], len(cell))\n'
        '\n'
        '    def _hline(l, m, r):\n'
        '        return "  " + l + m.join("\\u2500" * (w + 2) for w in widths) + r\n'
        '\n'
        '    def _row_line(plain_cells, colored_cells):\n'
        '        parts = [f" {colored}{chr(32) * (w - len(plain))} "\n'
        '                 for plain, colored, w in zip(plain_cells, colored_cells, widths)]\n'
        '        return "  \\u2502" + "\\u2502".join(parts) + "\\u2502"\n'
        '\n'
        '    print(_hline("\\u250c", "\\u252c", "\\u2510"))\n'
        '    print(_row_line(headers, [_bold(h) for h in headers]))\n'
        '    print(_hline("\\u251c", "\\u253c", "\\u2524"))\n'
        '    for p_row, c_row in zip(plain_rows, colored_rows):\n'
        '        print(_row_line(p_row, c_row))\n'
        '    print(_hline("\\u2514", "\\u2534", "\\u2518"))\n'
        '\n'
        '\n'
        'def _resource_rows(resources: dict):\n'
        '    has_comment = any(m.get("comment") for m in resources.values())\n'
        '    has_project = any(m.get("project") for m in resources.values())\n'
        '    headers = ["Name", "Date", "Uploaded by"]\n'
        '    if has_project:\n'
        '        headers.append("Project")\n'
        '    if has_comment:\n'
        '        headers.append("Comment")\n'
        '    plain, colored = [], []\n'
        '    for name, meta in sorted(resources.items()):\n'
        '        date = meta.get("created_at", "")[:10]\n'
        '        uploader = meta.get("uploaded_by") or ""\n'
        '        p = [name, date, uploader]\n'
        '        c = [_bold(name), _dim(date), uploader]\n'
        '        if has_project:\n'
        '            proj = meta.get("project") or ""\n'
        '            p.append(proj)\n'
        '            c.append(_green(proj) if proj else "")\n'
        '        if has_comment:\n'
        '            cmt = meta.get("comment") or ""\n'
        '            cp = f\'"{cmt[:50]}{"..." if len(cmt) > 50 else ""}"\' if cmt else ""\n'
        '            p.append(cp)\n'
        '            c.append(_cmt(cmt) if cmt else "")\n'
        '        plain.append(p)\n'
        '        colored.append(c)\n'
        '    return headers, plain, colored\n'
        '\n'
        '\n'
        'def _misc_rows(entries, misc_reg):\n'
        '    has_comment = any(misc_reg.get(e, {}).get("comment") for e in entries)\n'
        '    headers = ["Path", "Date", "Uploaded by"]\n'
        '    if has_comment:\n'
        '        headers.append("Comment")\n'
        '    plain, colored = [], []\n'
        '    for name in sorted(entries):\n'
        '        meta = misc_reg.get(name, {})\n'
        '        date = meta.get("uploaded_at", "")[:10]\n'
        '        up = meta.get("uploaded_by") or ""\n'
        '        p = [name, date or "\\u2014", up or "\\u2014"]\n'
        '        c = [_bold(name), _dim(date) if date else _dim("\\u2014"), up or _dim("\\u2014")]\n'
        '        if has_comment:\n'
        '            cmt = meta.get("comment") or ""\n'
        '            cp = f\'"{cmt[:50]}{"..." if len(cmt) > 50 else ""}"\' if cmt else ""\n'
        '            p.append(cp)\n'
        '            c.append(_cmt(cmt) if cmt else "")\n'
        '        plain.append(p)\n'
        '        colored.append(c)\n'
        '    return headers, plain, colored\n'
        '\n'
        '\n'
        'def _bin_rows(bin_reg):\n'
        '    has_comment = any(e.get("comment") for e in bin_reg.values())\n'
        '    headers = ["Type", "Name", "Deleted at", "Deleted by"]\n'
        '    if has_comment:\n'
        '        headers.append("Comment")\n'
        '    plain, colored = [], []\n'
        '    for key, meta in sorted(bin_reg.items()):\n'
        '        rtype = meta.get("resource_type", "")\n'
        '        rname = meta.get("resource_name", key)\n'
        '        date = meta.get("deleted_at", "")[:10]\n'
        '        deleter = meta.get("deleted_by") or ""\n'
        '        p = [rtype, rname, date or "\\u2014", deleter or "\\u2014"]\n'
        '        c = [_dim(rtype), _bold(rname),\n'
        '             _dim(date) if date else _dim("\\u2014"),\n'
        '             deleter or _dim("\\u2014")]\n'
        '        if has_comment:\n'
        '            cmt = meta.get("comment") or ""\n'
        '            cp = f\'"{cmt[:50]}{"..." if len(cmt) > 50 else ""}"\' if cmt else ""\n'
        '            p.append(cp)\n'
        '            c.append(_cmt(cmt) if cmt else "")\n'
        '        plain.append(p)\n'
        '        colored.append(c)\n'
        '    return headers, plain, colored\n'
        '\n'
        '\n'
        'def _pick_project(projects):\n'
        '    if not projects:\n'
        '        print(_dim("  No projects defined. Use \'<<PREFIX>>_manage_project add <name>\'."))\n'
        '        return None\n'
        '    print(f"\\n  {_header(f\'Projects ({len(projects)})\')}")\n'
        '    for i, p in enumerate(projects, 1):\n'
        '        print(f"    {i}. {_green(p)}")\n'
        '    try:\n'
        '        raw = input("\\nProject number (press Enter to cancel): ").strip()\n'
        '    except EOFError:\n'
        '        return None\n'
        '    if not raw:\n'
        '        return None\n'
        '    try:\n'
        '        idx = int(raw) - 1\n'
        '        if 0 <= idx < len(projects):\n'
        '            return projects[idx]\n'
        '        print("Invalid number.", file=sys.stderr)\n'
        '    except ValueError:\n'
        '        print("Invalid input.", file=sys.stderr)\n'
        '    return None\n'
        '\n'
        '\n'
        'def _resolve_project(downloader, requested):\n'
        '    registry = downloader.get_registry()\n'
        '    projects = sorted(registry.get("projects", []))\n'
        '    if requested in projects:\n'
        '        return requested\n'
        '    print(f"  Project \'{requested}\' does not exist. "\n'
        '          "Use \'<<PREFIX>>_manage_project add <name>\' to create a new project.",\n'
        '          file=sys.stderr)\n'
        '    return _pick_project(projects)\n'
        '\n'
        '\n'
        'def main():\n'
        '    parser = argparse.ArgumentParser(\n'
        '        description=__doc__,\n'
        '        formatter_class=argparse.RawDescriptionHelpFormatter,\n'
        '    )\n'
        '    parser.add_argument(\n'
        '        "resource_type",\n'
        '        choices=[<<LS_CHOICES>>],\n'
        '        nargs="?",\n'
        '        default="registry",\n'
        '    )\n'
        '    parser.add_argument("--server", choices=["public", "private"], default=None)\n'
        '    parser.add_argument("--project", default=None, metavar="NAME")\n'
        '    parser.add_argument("--type", choices=[<<BIN_CHOICES>>], default=None,\n'
        '                        dest="bin_type", metavar="TYPE")\n'
        '    args = parser.parse_args()\n'
        '\n'
        '    from <<PKG>>.server_utils import Downloader, ServerError\n'
        '\n'
        '    try:\n'
        '        downloader = Downloader(server=args.server)\n'
        '        project_filter = None\n'
        '        if args.project is not None:\n'
        '            project_filter = _resolve_project(downloader, args.project)\n'
        '            if project_filter is None:\n'
        '                sys.exit(0)\n'
        '\n'
        '        def _filter(resources):\n'
        '            if project_filter is None:\n'
        '                return resources\n'
        '            return {k: v for k, v in resources.items()\n'
        '                    if v.get("project") == project_filter}\n'
        '\n'
        '        title_suffix = f" [{project_filter}]" if project_filter else ""\n'
        '\n'
        '<<REG_BLOCK>>\n'
        '\n'
        '<<ELIF_BLOCKS>>\n'
        '\n'
        '        elif args.resource_type == "misc":\n'
        '            entries = downloader.list_resources("misc")\n'
        '            misc_reg = downloader.get_misc_registry()\n'
        '            _table(f"misc/ ({len(entries)} entries)", *_misc_rows(entries, misc_reg))\n'
        '            print()\n'
        '\n'
        '        elif args.resource_type == "bin":\n'
        '            bin_reg = downloader.get_bin_registry()\n'
        '            if args.bin_type:\n'
        '                bin_reg = {k: v for k, v in bin_reg.items()\n'
        '                           if v.get("resource_type") == args.bin_type}\n'
        '            type_suffix = f" [{args.bin_type}]" if args.bin_type else ""\n'
        '            _table(f"Bin ({len(bin_reg)} entries){type_suffix}", *_bin_rows(bin_reg))\n'
        '            print()\n'
        '\n'
        '    except ServerError as e:\n'
        '        log.error("%s", e)\n'
        '        sys.exit(1)\n'
        '    except KeyboardInterrupt:\n'
        '        print("\\nInterrupted by user.", file=sys.stderr)\n'
        '        sys.exit(1)\n'
        '\n'
        '\n'
        'if __name__ == "__main__":\n'
        '    main()\n'
    )
    return sub(
        template,
        PKG=pkg, PREFIX=prefix, PROJECT=project,
        LS_CHOICES=ls_choices,
        LS_CHOICES_DOC=_choices_str(archivable),
        BIN_CHOICES=bin_choices,
        REG_BLOCK=reg_block,
        ELIF_BLOCKS=elif_blocks,
    )


def gen_script(pkg, prefix, project, archivable, script_type: str) -> str:
    all_types = archivable + ["misc"]
    choices = _choices_str(all_types)
    project_cond = _pytuple(archivable)

    SCRIPTS = {
        "upload": (
            '"""\n'
            'Upload a resource to the <<PROJECT>> server.\n'
            '\n'
            '    <<PREFIX>>_upload RESOURCE_TYPE RESOURCE_NAME [LOCAL_PATH]\n'
            '"""\n'
            'import argparse, logging, sys\n'
            'from <<PKG>>._logging import ColorHandler\n'
            'log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())\n'
            '\n'
            '\n'
            'def _prompt_project(projects):\n'
            '    if not projects: return None\n'
            '    print("Available projects:")\n'
            '    for i, p in enumerate(projects, 1): print(f"  {i}. {p}")\n'
            '    raw = input("Project number (press Enter to skip): ").strip()\n'
            '    if not raw: return None\n'
            '    try:\n'
            '        idx = int(raw) - 1\n'
            '        if 0 <= idx < len(projects): return projects[idx]\n'
            '        print("Invalid number.", file=sys.stderr)\n'
            '    except ValueError:\n'
            '        print("Invalid input.", file=sys.stderr)\n'
            '    return None\n'
            '\n'
            '\n'
            'def main():\n'
            '    parser = argparse.ArgumentParser(\n'
            '        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)\n'
            '    parser.add_argument("resource_type", choices=[<<CHOICES>>])\n'
            '    parser.add_argument("resource_name")\n'
            '    parser.add_argument("local_path", nargs="?", default=None)\n'
            '    parser.add_argument("--server", choices=["public", "private"], default=None)\n'
            '    parser.add_argument("-f", "--force", action="store_true")\n'
            '    parser.add_argument("-m", "--message", default=None)\n'
            '    parser.add_argument("--project", default=None)\n'
            '    args = parser.parse_args()\n'
            '\n'
            '    message = args.message\n'
            '    if message is None:\n'
            '        try: message = input("Comment (press Enter to skip): ").strip() or None\n'
            '        except EOFError: message = None\n'
            '\n'
            '    from <<PKG>>.server_utils import ServerError, Uploader, list_projects\n'
            '    project = args.project\n'
            '    if args.resource_type in <<PROJECT_COND>>:\n'
            '        try:\n'
            '            projects = list_projects(server=args.server)\n'
            '            if project is not None:\n'
            '                if project not in projects:\n'
            '                    print(f"Project \'{project}\' does not exist.", file=sys.stderr)\n'
            '                    project = _prompt_project(projects)\n'
            '            else:\n'
            '                project = _prompt_project(projects)\n'
            '        except (ServerError, EOFError): pass\n'
            '\n'
            '    try:\n'
            '        Uploader(server=args.server).upload(\n'
            '            args.resource_type, args.resource_name, args.local_path,\n'
            '            args.force, message, project)\n'
            '    except ServerError as e: log.error("%s", e); sys.exit(1)\n'
            '    except KeyboardInterrupt: print("\\nInterrupted.", file=sys.stderr); sys.exit(1)\n'
            '\n'
            '\n'
            'if __name__ == "__main__": main()\n'
        ),
        "get": (
            '"""\n'
            'Download a resource from the <<PROJECT>> server.\n'
            '\n'
            '    <<PREFIX>>_get RESOURCE_TYPE RESOURCE_NAME [LOCAL_PATH]\n'
            '"""\n'
            'import argparse, logging, sys\n'
            'from <<PKG>>._logging import ColorHandler\n'
            'log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())\n'
            '\n'
            '\n'
            'def main():\n'
            '    parser = argparse.ArgumentParser(\n'
            '        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)\n'
            '    parser.add_argument("resource_type", choices=[<<CHOICES>>])\n'
            '    parser.add_argument("resource_name")\n'
            '    parser.add_argument("local_path", nargs="?", default=None)\n'
            '    parser.add_argument("--server", choices=["public", "private"], default=None)\n'
            '    args = parser.parse_args()\n'
            '\n'
            '    from <<PKG>>.server_utils import Downloader, ServerError\n'
            '    try:\n'
            '        Downloader(server=args.server).download(\n'
            '            args.resource_type, args.resource_name, args.local_path)\n'
            '    except ServerError as e: log.error("%s", e); sys.exit(1)\n'
            '    except KeyboardInterrupt: print("\\nInterrupted.", file=sys.stderr); sys.exit(1)\n'
            '\n'
            '\n'
            'if __name__ == "__main__": main()\n'
        ),
        "mv": (
            '"""\n'
            'Rename a resource and/or update its comment on the <<PROJECT>> server.\n'
            '\n'
            '    <<PREFIX>>_mv RESOURCE_TYPE OLD_NAME [NEW_NAME] [--comment TEXT]\n'
            '"""\n'
            'import argparse, logging, sys\n'
            'from <<PKG>>._logging import ColorHandler\n'
            'log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())\n'
            '\n'
            '\n'
            'def main():\n'
            '    parser = argparse.ArgumentParser(\n'
            '        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)\n'
            '    parser.add_argument("resource_type", choices=[<<CHOICES>>])\n'
            '    parser.add_argument("old_name")\n'
            '    parser.add_argument("new_name", nargs="?", default=None)\n'
            '    parser.add_argument("--comment", "-c", default=None)\n'
            '    parser.add_argument("--server", choices=["public", "private"], default=None)\n'
            '    args = parser.parse_args()\n'
            '    if args.new_name is None and args.comment is None:\n'
            '        parser.error("Provide a new name, --comment, or both.")\n'
            '\n'
            '    from <<PKG>>.server_utils import ServerError, rename\n'
            '    try:\n'
            '        rename(args.resource_type, args.old_name, args.new_name,\n'
            '               server=args.server, comment=args.comment)\n'
            '    except ServerError as e: log.error("%s", e); sys.exit(1)\n'
            '    except KeyboardInterrupt: print("\\nInterrupted.", file=sys.stderr); sys.exit(1)\n'
            '\n'
            '\n'
            'if __name__ == "__main__": main()\n'
        ),
        "rm": (
            '"""\n'
            'Move one or more resources to bin/ on the <<PROJECT>> server.\n'
            '\n'
            '    <<PREFIX>>_rm RESOURCE_TYPE NAME [NAME ...]\n'
            '"""\n'
            'import argparse, logging, sys\n'
            'from <<PKG>>._logging import ColorHandler\n'
            'log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())\n'
            '\n'
            '\n'
            'def main():\n'
            '    parser = argparse.ArgumentParser(\n'
            '        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)\n'
            '    parser.add_argument("resource_type", choices=[<<CHOICES>>])\n'
            '    parser.add_argument("names", nargs="+", metavar="NAME")\n'
            '    parser.add_argument("-f", "--force", action="store_true")\n'
            '    parser.add_argument("-m", "--message", default=None)\n'
            '    parser.add_argument("--server", choices=["public", "private"], default=None)\n'
            '    args = parser.parse_args()\n'
            '\n'
            '    from <<PKG>>.server_utils import ServerError, trash\n'
            '    message = args.message\n'
            '    if message is None:\n'
            '        try: message = input("Deletion comment (press Enter to skip): ").strip() or None\n'
            '        except EOFError: message = None\n'
            '    if not args.force:\n'
            '        targets = ", ".join(f"\'{n}\'" for n in args.names)\n'
            '        if input(f"Move {targets} to bin on server? [y/N] ").strip().lower() != "y":\n'
            '            print("Aborted."); sys.exit(0)\n'
            '    try:\n'
            '        for name in args.names:\n'
            '            trash(args.resource_type, name, server=args.server, message=message)\n'
            '    except ServerError as e: log.error("%s", e); sys.exit(1)\n'
            '    except KeyboardInterrupt: print("\\nInterrupted.", file=sys.stderr); sys.exit(1)\n'
            '\n'
            '\n'
            'if __name__ == "__main__": main()\n'
        ),
        "restore": (
            '"""\n'
            'Restore a resource from bin/ back to its original location.\n'
            '\n'
            '    <<PREFIX>>_restore RESOURCE_TYPE NAME\n'
            '"""\n'
            'import argparse, logging, sys\n'
            'from <<PKG>>._logging import ColorHandler\n'
            'log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())\n'
            '\n'
            '\n'
            'def main():\n'
            '    parser = argparse.ArgumentParser(\n'
            '        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)\n'
            '    parser.add_argument("resource_type", choices=[<<CHOICES>>])\n'
            '    parser.add_argument("name", metavar="NAME")\n'
            '    parser.add_argument("-f", "--force", action="store_true")\n'
            '    parser.add_argument("--server", choices=["public", "private"], default=None)\n'
            '    args = parser.parse_args()\n'
            '\n'
            '    from <<PKG>>.server_utils import ServerError, restore\n'
            '    if not args.force:\n'
            '        if input(f"Restore \'{args.name}\' from bin? [y/N] ").strip().lower() != "y":\n'
            '            print("Aborted."); sys.exit(0)\n'
            '    try:\n'
            '        restore(args.resource_type, args.name, server=args.server)\n'
            '    except ServerError as e: log.error("%s", e); sys.exit(1)\n'
            '    except KeyboardInterrupt: print("\\nInterrupted.", file=sys.stderr); sys.exit(1)\n'
            '\n'
            '\n'
            'if __name__ == "__main__": main()\n'
        ),
        "mkdir": (
            '"""\n'
            'Create a directory under misc/ on the <<PROJECT>> server.\n'
            '\n'
            '    <<PREFIX>>_mkdir PATH\n'
            '"""\n'
            'import argparse, logging, sys\n'
            'from <<PKG>>._logging import ColorHandler\n'
            'log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())\n'
            '\n'
            '\n'
            'def main():\n'
            '    parser = argparse.ArgumentParser(\n'
            '        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)\n'
            '    parser.add_argument("path")\n'
            '    parser.add_argument("--server", choices=["public", "private"], default=None)\n'
            '    args = parser.parse_args()\n'
            '\n'
            '    from <<PKG>>.server_utils import ServerError, mkdir_misc\n'
            '    try:\n'
            '        mkdir_misc(args.path, server=args.server)\n'
            '    except ServerError as e: log.error("%s", e); sys.exit(1)\n'
            '    except KeyboardInterrupt: print("\\nInterrupted.", file=sys.stderr); sys.exit(1)\n'
            '\n'
            '\n'
            'if __name__ == "__main__": main()\n'
        ),
        "manage_project": (
            '"""\n'
            'Manage the project list on the <<PROJECT>> server.\n'
            '\n'
            '    <<PREFIX>>_manage_project list\n'
            '    <<PREFIX>>_manage_project add    PROJECT_NAME\n'
            '    <<PREFIX>>_manage_project rename OLD_NAME NEW_NAME\n'
            '    <<PREFIX>>_manage_project remove PROJECT_NAME\n'
            '"""\n'
            'import argparse, logging, sys\n'
            'from <<PKG>>._logging import ColorHandler\n'
            'log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())\n'
            '\n'
            '\n'
            'def main():\n'
            '    parser = argparse.ArgumentParser(\n'
            '        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)\n'
            '    parser.add_argument("--server", choices=["public", "private"], default=None)\n'
            '    sub = parser.add_subparsers(dest="command", required=True)\n'
            '    sub.add_parser("list")\n'
            '    p_add = sub.add_parser("add"); p_add.add_argument("project_name")\n'
            '    p_ren = sub.add_parser("rename")\n'
            '    p_ren.add_argument("old_name"); p_ren.add_argument("new_name")\n'
            '    p_rem = sub.add_parser("remove"); p_rem.add_argument("project_name")\n'
            '    args = parser.parse_args()\n'
            '\n'
            '    from <<PKG>>.server_utils import (\n'
            '        ServerError, add_project, list_projects, remove_project, rename_project)\n'
            '    try:\n'
            '        if args.command == "list":\n'
            '            projects = list_projects(server=args.server)\n'
            '            print("\\n".join(projects) if projects else "(no projects defined)")\n'
            '        elif args.command == "add":\n'
            '            add_project(args.project_name, server=args.server)\n'
            '        elif args.command == "rename":\n'
            '            rename_project(args.old_name, args.new_name, server=args.server)\n'
            '        elif args.command == "remove":\n'
            '            remove_project(args.project_name, server=args.server)\n'
            '    except ServerError as e: log.error("%s", e); sys.exit(1)\n'
            '    except KeyboardInterrupt: print("\\nInterrupted.", file=sys.stderr); sys.exit(1)\n'
            '\n'
            '\n'
            'if __name__ == "__main__": main()\n'
        ),
    }
    return sub(SCRIPTS[script_type],
               PKG=pkg, PREFIX=prefix, PROJECT=project,
               CHOICES=choices, PROJECT_COND=project_cond)


def gen_server_script(pkg, prefix, project, config_dir, archivable):
    commands = _tutorial_commands(prefix, archivable)
    return sub(
        '"""\n'
        '<<PROJECT>> server management.\n'
        '\n'
        '    <<PREFIX>>_server {setup,storage,sync,tutorial} [options]\n'
        '"""\n'
        'import argparse, getpass, logging, pathlib, sys\n'
        'import yaml\n'
        'from <<PKG>>._logging import ColorHandler\n'
        'log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())\n'
        '\n'
        '_USE_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()\n'
        '\n'
        '\n'
        'def _c(t, *c): return ("".join(c) + str(t) + "\\033[0m") if _USE_COLOR else str(t)\n'
        '\n'
        '\n'
        '_BOLD = "\\033[1m"; _DIM = "\\033[2m"; _CYAN = "\\033[36m"; _GREEN = "\\033[32m"\n'
        'def _header(s): return _c(s, _BOLD, _CYAN)\n'
        'def _bold(s):   return _c(s, _BOLD)\n'
        'def _dim(s):    return _c(s, _DIM)\n'
        'def _green(s):  return _c(s, _GREEN)\n'
        '\n'
        '_CONFIG_PATH = pathlib.Path.home() / ".config" / "<<CONFIG_DIR>>" / "server.yaml"\n'
        '_REQUIRED_KEYS = ("webdav_hostname", "webdav_login", "webdav_password")\n'
        '_PROFILES = ("public", "private")\n'
        '\n'
        '\n'
        'def _validate(config):\n'
        '    if not isinstance(config, dict): raise ValueError("Must be a YAML mapping.")\n'
        '    unknown = set(config) - set(_PROFILES)\n'
        '    if unknown: raise ValueError(f"Unknown profile(s): {\', \'.join(sorted(unknown))}")\n'
        '    if not config: raise ValueError("No profiles configured.")\n'
        '    for profile, values in config.items():\n'
        '        if not isinstance(values, dict):\n'
        '            raise ValueError(f"Profile \'{profile}\' must be a mapping.")\n'
        '        for key in _REQUIRED_KEYS:\n'
        '            if key not in values:\n'
        '                raise ValueError(f"Missing key \'{key}\' under \'{profile}:\'.")\n'
        '\n'
        '\n'
        'def _prompt_profile(profile):\n'
        '    print(f"\\n--- {profile.upper()} server ---")\n'
        '    if input(f"Configure \'{profile}\' profile? [y/N] ").strip().lower() != "y":\n'
        '        return None\n'
        '    result = {\n'
        '        "webdav_hostname": input("  webdav_hostname: ").strip(),\n'
        '        "webdav_login":    input("  webdav_login:    ").strip(),\n'
        '        "webdav_password": getpass.getpass("  webdav_password: "),\n'
        '    }\n'
        '    name = input("  name (shown in registry, optional): ").strip()\n'
        '    if name: result["name"] = name\n'
        '    return result\n'
        '\n'
        '\n'
        'def _write_config(config):\n'
        '    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)\n'
        '    with open(_CONFIG_PATH, "w") as f: yaml.dump(config, f, default_flow_style=False)\n'
        '    _CONFIG_PATH.chmod(0o600)\n'
        '    log.info("Credentials written to %s", _CONFIG_PATH)\n'
        '\n'
        '\n'
        '_COMMANDS = [\n'
        '<<COMMANDS>>\n'
        ']\n'
        '\n'
        '\n'
        'def _print_tutorial():\n'
        '    cmd_w = max(len(cmd) for cmd, _ in _COMMANDS)\n'
        '    print(f"\\n  {_header(\'<<PROJECT>> command reference\')}\\n")\n'
        '    for cmd, desc in _COMMANDS:\n'
        '        lines = desc.split("\\n")\n'
        '        print(f"  {_bold(cmd):{cmd_w + 10}}{lines[0]}")\n'
        '        for extra in lines[1:]:\n'
        '            print(f"  {chr(32) * (cmd_w + 10)}{_dim(extra)}")\n'
        '    print(f"\\n  {_dim(\'Run any command with --help for full usage.\')}\\n")\n'
        '\n'
        '\n'
        'def main():\n'
        '    parser = argparse.ArgumentParser(\n'
        '        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)\n'
        '    sub = parser.add_subparsers(dest="command", required=True)\n'
        '    p_setup = sub.add_parser("setup")\n'
        '    p_setup.add_argument("credentials_yaml", nargs="?", default=None)\n'
        '    p_setup.add_argument("--force", action="store_true")\n'
        '    p_storage = sub.add_parser("storage")\n'
        '    p_storage.add_argument("--server", choices=["public", "private"], default=None)\n'
        '    p_sync = sub.add_parser("sync")\n'
        '    p_sync.add_argument("--server", choices=["public", "private"], default=None)\n'
        '    sub.add_parser("tutorial")\n'
        '    args = parser.parse_args()\n'
        '\n'
        '    try:\n'
        '        if args.command == "setup":\n'
        '            if _CONFIG_PATH.exists() and not args.force:\n'
        '                log.error("%s already exists. Use --force to overwrite.", _CONFIG_PATH)\n'
        '                sys.exit(1)\n'
        '            if args.credentials_yaml is not None:\n'
        '                src = pathlib.Path(args.credentials_yaml)\n'
        '                if not src.exists(): log.error("File not found: %s", src); sys.exit(1)\n'
        '                with open(src) as f: config = yaml.safe_load(f)\n'
        '                try: _validate(config)\n'
        '                except ValueError as e: log.error("%s", e); sys.exit(1)\n'
        '            else:\n'
        '                config = {}\n'
        '                for profile in _PROFILES:\n'
        '                    result = _prompt_profile(profile)\n'
        '                    if result is not None: config[profile] = result\n'
        '                if not config: log.error("No profiles configured."); sys.exit(1)\n'
        '            _write_config(config)\n'
        '\n'
        '        elif args.command == "storage":\n'
        '            from <<PKG>>.server_utils import ServerError, get_free_space\n'
        '            try:\n'
        '                _TOTAL_GB = 1000.0\n'
        '                free_bytes = get_free_space(server=args.server)\n'
        '                free_gb = free_bytes / (1024 ** 3)\n'
        '                used_gb = _TOTAL_GB - free_gb\n'
        '                filled = round(used_gb / _TOTAL_GB * 30)\n'
        '                bar = "\\u2588" * filled + "\\u2591" * (30 - filled)\n'
        '                print(f"\\n  {_header(\'Storage\')}")\n'
        '                print(f"  {bar}  {_bold(f\'{used_gb:.1f}\')} / {_TOTAL_GB:.0f} GB used"\n'
        '                      f"  ({_green(f\'{free_gb:.1f} GB free\')})\\n")\n'
        '            except ServerError as e: log.error("%s", e); sys.exit(1)\n'
        '\n'
        '        elif args.command == "sync":\n'
        '            from <<PKG>>.server_utils import ServerError, sync_registry\n'
        '            try: sync_registry(server=args.server)\n'
        '            except ServerError as e: log.error("%s", e); sys.exit(1)\n'
        '\n'
        '        elif args.command == "tutorial":\n'
        '            _print_tutorial()\n'
        '\n'
        '    except KeyboardInterrupt:\n'
        '        print("\\nInterrupted.", file=sys.stderr); sys.exit(1)\n'
        '\n'
        '\n'
        'if __name__ == "__main__": main()\n',
        PKG=pkg, PREFIX=prefix, PROJECT=project,
        CONFIG_DIR=config_dir, COMMANDS=commands,
    )


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def write_all(cfg, output_dir: pathlib.Path):
    pkg    = cfg["package"]
    prefix = cfg["prefix"]
    proj   = cfg["project"]
    cdir   = cfg["config_dir"]
    desc   = cfg["description"]
    arch   = cfg["archivable_types"]

    files = {
        "pyproject.toml":                            gen_pyproject(pkg, prefix, desc, arch),
        f"{pkg}/__init__.py":                        "",
        f"{pkg}/_logging.py":                        gen_logging(),
        f"{pkg}/server_utils.py":                    gen_server_utils(pkg, prefix, proj, cdir, arch),
        f"{pkg}/scripts/__init__.py":                "",
        f"{pkg}/scripts/{prefix}_ls.py":             gen_ls(pkg, prefix, proj, arch),
        f"{pkg}/scripts/{prefix}_upload.py":         gen_script(pkg, prefix, proj, arch, "upload"),
        f"{pkg}/scripts/{prefix}_get.py":            gen_script(pkg, prefix, proj, arch, "get"),
        f"{pkg}/scripts/{prefix}_mv.py":             gen_script(pkg, prefix, proj, arch, "mv"),
        f"{pkg}/scripts/{prefix}_rm.py":             gen_script(pkg, prefix, proj, arch, "rm"),
        f"{pkg}/scripts/{prefix}_restore.py":        gen_script(pkg, prefix, proj, arch, "restore"),
        f"{pkg}/scripts/{prefix}_mkdir.py":          gen_script(pkg, prefix, proj, arch, "mkdir"),
        f"{pkg}/scripts/{prefix}_manage_project.py": gen_script(pkg, prefix, proj, arch, "manage_project"),
        f"{pkg}/scripts/{prefix}_server.py":         gen_server_script(pkg, prefix, proj, cdir, arch),
    }

    for rel_path, content in files.items():
        dest = output_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        print(f"  wrote  {rel_path}")

    print(f"\nDone. Install with:  pip install -e {output_dir}\n")


# ---------------------------------------------------------------------------

def main():
    output_dir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(".")
    print(f"Generating '{CONFIG['package']}' into {output_dir} …\n")
    write_all(CONFIG, output_dir)


if __name__ == "__main__":
    main()
