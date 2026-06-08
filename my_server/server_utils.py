"""
Tools to upload/download resources to/from the MyProject WebDAV server.

Config file (~/.config/myproject/server.yaml):
    public:
      webdav_hostname: https://...
      webdav_login:    <token>
      webdav_password: <password>
      name:            Alice   # optional, shown in registry
    private: ...

Run 'example_server setup' to create this file.
"""

import datetime
import json
import logging
import pathlib
import tarfile
import tempfile

import yaml

log = logging.getLogger(__name__)

RESOURCE_TYPES = ["type_a", "type_b", "misc"]
_ARCHIVABLE_TYPES = ["type_a", "type_b"]
REGISTRY_PATH = "registry.json"
MISC_REGISTRY_PATH = "misc/registry_misc.json"
BIN_DIR = "bin"
BIN_REGISTRY_PATH = "bin/registry_bin.json"
SERVERS = ["public", "private"]

_REMOTE_DIRS = {
    "type_a": "type_a",
    "type_b": "type_b",
    "misc": "misc"
}

CONFIG_PATH = pathlib.Path.home() / ".config" / "myproject" / "server.yaml"


class ServerError(Exception):
    pass


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}


def _auto_server(config: dict, need_write: bool) -> str:
    if "private" in config:
        return "private"
    if "public" in config:
        return "public"
    raise ServerError(
        f"No server credentials found in {CONFIG_PATH}.\n"
        "Run 'example_server setup' to configure your credentials."
    )


def _get_client(server: str | None, need_write: bool = False):
    from webdav3.client import Client
    config = _load_config()
    if server is None:
        server = _auto_server(config, need_write)
    hint = "Run 'example_server setup' to configure your credentials."
    if server == "public":
        if "public" not in config:
            raise ServerError(
                f"Public server credentials not found in {CONFIG_PATH}.\n{hint}"
            )
    elif server == "private":
        if "private" not in config:
            raise ServerError(
                f"Private server credentials not found in {CONFIG_PATH}.\n{hint}"
            )
    else:
        raise ServerError(f"Unknown server '{server}'. Choose from: public, private")
    profile = config[server]
    for key in ("webdav_hostname", "webdav_login", "webdav_password"):
        if key not in profile:
            raise ServerError(f"Missing key '{key}' under '{server}:' in {CONFIG_PATH}")
    return Client(profile)


def _remote_path(resource_type: str, resource_name: str) -> str:
    if resource_type == "misc":
        return f"misc/{resource_name}"
    return f"{_REMOTE_DIRS[resource_type]}/{resource_name}.tar.gz"


def _compress(source: pathlib.Path, archive_path: pathlib.Path,
              arcname: str | None = None) -> None:
    log.info("Compressing %s ...", source)
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(source, arcname=arcname or source.name)


def _extract(archive_path: pathlib.Path, dest: pathlib.Path) -> None:
    log.info("Extracting to %s ...", dest)
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(dest)


def _ensure_remote_path(client, path: str) -> None:
    parts = pathlib.PurePosixPath(path).parts
    for i in range(1, len(parts) + 1):
        segment = str(pathlib.PurePosixPath(*parts[:i]))
        if not client.check(segment):
            client.mkdir(segment)


def _empty_registry() -> dict:
    return {
    "type_a": {},
    "type_b": {},
    "projects": []
    }


def _read_registry(client) -> dict:
    if not client.check(REGISTRY_PATH):
        return _empty_registry()
    with tempfile.TemporaryDirectory(prefix="example_registry_") as tmpdir:
        tmp = pathlib.Path(tmpdir) / "registry.json"
        client.download_sync(remote_path=REGISTRY_PATH, local_path=str(tmp))
        data = json.loads(tmp.read_text())
    return {**_empty_registry(), **data}


def _write_registry(client, registry: dict) -> None:
    with tempfile.TemporaryDirectory(prefix="example_registry_") as tmpdir:
        tmp = pathlib.Path(tmpdir) / "registry.json"
        tmp.write_text(json.dumps(registry, indent=2, sort_keys=True))
        client.upload_sync(remote_path=REGISTRY_PATH, local_path=str(tmp))


def _read_misc_registry(client) -> dict:
    if not client.check(MISC_REGISTRY_PATH):
        return {}
    with tempfile.TemporaryDirectory(prefix="example_misc_reg_") as tmpdir:
        tmp = pathlib.Path(tmpdir) / "registry_misc.json"
        client.download_sync(remote_path=MISC_REGISTRY_PATH, local_path=str(tmp))
        return json.loads(tmp.read_text())


def _write_misc_registry(client, registry: dict) -> None:
    with tempfile.TemporaryDirectory(prefix="example_misc_reg_") as tmpdir:
        tmp = pathlib.Path(tmpdir) / "registry_misc.json"
        tmp.write_text(json.dumps(registry, indent=2, sort_keys=True))
        client.upload_sync(remote_path=MISC_REGISTRY_PATH, local_path=str(tmp))


def _read_bin_registry(client) -> dict:
    if not client.check(BIN_REGISTRY_PATH):
        return {}
    with tempfile.TemporaryDirectory(prefix="example_bin_reg_") as tmpdir:
        tmp = pathlib.Path(tmpdir) / "registry_bin.json"
        client.download_sync(remote_path=BIN_REGISTRY_PATH, local_path=str(tmp))
        return json.loads(tmp.read_text())


def _write_bin_registry(client, registry: dict) -> None:
    _ensure_remote_path(client, BIN_DIR)
    with tempfile.TemporaryDirectory(prefix="example_bin_reg_") as tmpdir:
        tmp = pathlib.Path(tmpdir) / "registry_bin.json"
        tmp.write_text(json.dumps(registry, indent=2, sort_keys=True))
        client.upload_sync(remote_path=BIN_REGISTRY_PATH, local_path=str(tmp))


def _list_resource_names(client, resource_type: str) -> list[str]:
    remote_dir = _REMOTE_DIRS[resource_type]
    if not client.check(remote_dir):
        return []
    names = []
    for e in client.list(remote_dir):
        e = e.rstrip("/")
        if e in (remote_dir, ""):
            continue
        if resource_type in _ARCHIVABLE_TYPES:
            if not e.endswith(".tar.gz"):
                continue
            e = e[: -len(".tar.gz")]
        elif resource_type == "misc" and e == "registry_misc.json":
            continue
        names.append(e)
    return names


def rename(
    resource_type: str,
    old_name: str,
    new_name: str | None = None,
    server: str | None = None,
    comment: str | None = None,
) -> None:
    """Rename a resource and/or update its comment."""
    if resource_type not in RESOURCE_TYPES:
        raise ServerError(
            f"Unknown resource type '{resource_type}'. "
            f"Choose from: {', '.join(RESOURCE_TYPES)}"
        )
    if new_name is None and comment is None:
        raise ServerError("Provide a new name, a --comment, or both.")
    client = _get_client(server, need_write=True)
    if new_name is not None and new_name != old_name:
        old_remote = _remote_path(resource_type, old_name)
        new_remote = _remote_path(resource_type, new_name)
        if not client.check(old_remote):
            raise ServerError(f"Resource '{old_name}' not found on server.")
        if client.check(new_remote):
            raise ServerError(
                f"'{new_name}' already exists on server. Choose a different name."
            )
        if resource_type == "misc":
            _ensure_remote_path(client, str(pathlib.PurePosixPath(new_remote).parent))
        client.move(remote_path_from=old_remote, remote_path_to=new_remote)
        log.info("Renamed '%s' -> '%s'.", old_name, new_name)
    else:
        new_name = old_name
        if not client.check(_remote_path(resource_type, old_name)):
            raise ServerError(f"Resource '{old_name}' not found on server.")
    if resource_type in _ARCHIVABLE_TYPES:
        registry = _read_registry(client)
        section = registry[resource_type]
        if old_name in section:
            entry = section.pop(old_name)
            if comment is not None:
                entry["comment"] = comment
                log.info("Updated comment for '%s'.", new_name)
            section[new_name] = entry
            _write_registry(client, registry)
    elif resource_type == "misc":
        misc_reg = _read_misc_registry(client)
        if old_name in misc_reg:
            entry = misc_reg.pop(old_name)
            if comment is not None:
                entry["comment"] = comment
                log.info("Updated comment for '%s'.", new_name)
            misc_reg[new_name] = entry
            _write_misc_registry(client, misc_reg)


def trash(
    resource_type: str,
    resource_name: str,
    server: str | None = None,
    message: str | None = None,
) -> None:
    """Move a resource into bin/ instead of permanently deleting it."""
    if resource_type not in RESOURCE_TYPES:
        raise ServerError(
            f"Unknown resource type '{resource_type}'. "
            f"Choose from: {', '.join(RESOURCE_TYPES)}"
        )
    config = _load_config()
    resolved_server = server if server is not None else _auto_server(config, need_write=True)
    deleter_name = config.get(resolved_server, {}).get("name")
    client = _get_client(server, need_write=True)
    remote = _remote_path(resource_type, resource_name)
    if not client.check(remote):
        raise ServerError(f"Resource '{resource_name}' not found on server.")
    registry: dict = {}
    misc_reg: dict = {}
    original_meta: dict = {}
    if resource_type in _ARCHIVABLE_TYPES:
        registry = _read_registry(client)
        original_meta = registry.get(resource_type, {}).get(resource_name, {})
    elif resource_type == "misc":
        misc_reg = _read_misc_registry(client)
        original_meta = misc_reg.get(resource_name, {})
    bin_remote = f"{BIN_DIR}/{remote}"
    _ensure_remote_path(client, str(pathlib.PurePosixPath(bin_remote).parent))
    client.move(remote_path_from=remote, remote_path_to=bin_remote)
    log.info("Moved '%s' to bin.", resource_name)
    if resource_type in _ARCHIVABLE_TYPES:
        if resource_name in registry.get(resource_type, {}):
            del registry[resource_type][resource_name]
            _write_registry(client, registry)
    elif resource_type == "misc":
        if resource_name in misc_reg:
            del misc_reg[resource_name]
            _write_misc_registry(client, misc_reg)
    bin_reg = _read_bin_registry(client)
    entry: dict = {
        "deleted_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "deleted_by": deleter_name,
        "resource_type": resource_type,
        "resource_name": resource_name,
        "original_meta": original_meta,
    }
    if message:
        entry["comment"] = message
    bin_reg[f"{resource_type}/{resource_name}"] = entry
    _write_bin_registry(client, bin_reg)


def restore(
    resource_type: str,
    resource_name: str,
    server: str | None = None,
) -> None:
    """Move a resource from bin/ back to its original location."""
    if resource_type not in RESOURCE_TYPES:
        raise ServerError(
            f"Unknown resource type '{resource_type}'. "
            f"Choose from: {', '.join(RESOURCE_TYPES)}"
        )
    client = _get_client(server, need_write=True)
    key = f"{resource_type}/{resource_name}"
    bin_reg = _read_bin_registry(client)
    if key not in bin_reg:
        raise ServerError(f"'{resource_name}' (type: {resource_type}) is not in the bin.")
    entry = bin_reg[key]
    remote = _remote_path(resource_type, resource_name)
    bin_remote = f"{BIN_DIR}/{remote}"
    if not client.check(bin_remote):
        raise ServerError(
            f"Binned file not found at '{bin_remote}'. "
            "The bin registry may be out of sync — run 'example_server sync'."
        )
    if client.check(remote):
        raise ServerError(
            f"'{resource_name}' already exists at its original location. "
            "Rename or remove it before restoring."
        )
    _ensure_remote_path(client, str(pathlib.PurePosixPath(remote).parent))
    client.move(remote_path_from=bin_remote, remote_path_to=remote)
    log.info("Restored '%s' to %s.", resource_name, remote)
    original_meta = entry.get("original_meta", {})
    if resource_type in _ARCHIVABLE_TYPES:
        registry = _read_registry(client)
        registry[resource_type][resource_name] = original_meta
        _write_registry(client, registry)
    elif resource_type == "misc":
        misc_reg = _read_misc_registry(client)
        misc_reg[resource_name] = original_meta
        _write_misc_registry(client, misc_reg)
    del bin_reg[key]
    _write_bin_registry(client, bin_reg)
    log.info("Registry restored.")


class Uploader:
    def __init__(self, server: str | None = None):
        config = _load_config()
        resolved_server = server if server is not None else _auto_server(config, need_write=True)
        self._client = _get_client(server, need_write=True)
        self._server = resolved_server
        self._uploader_name = config.get(resolved_server, {}).get("name")

    def _ensure_remote_dir(self, resource_type: str) -> None:
        remote_dir = _REMOTE_DIRS[resource_type]
        if not self._client.check(remote_dir):
            self._client.mkdir(remote_dir)

    def upload(
        self,
        resource_type: str,
        resource_name: str,
        local_path: pathlib.Path | None = None,
        force: bool = False,
        message: str | None = None,
        project: str | None = None,
    ) -> None:
        resource_name = resource_name.rstrip("/\\")
        if resource_type not in RESOURCE_TYPES:
            raise ServerError(
                f"Unknown resource type '{resource_type}'. "
                f"Choose from: {', '.join(RESOURCE_TYPES)}"
            )
        if resource_type == "misc":
            if local_path is None:
                local_path = pathlib.Path(resource_name).name
            local_path = pathlib.Path(local_path)
            if not local_path.exists():
                raise ServerError(f"Local path does not exist: {local_path}")
            remote = _remote_path("misc", resource_name)
            if not force and self._client.check(remote):
                raise ServerError(
                    f"'misc/{resource_name}' already exists on the {self._server} server. "
                    "Use --force to overwrite."
                )
            _ensure_remote_path(self._client, str(pathlib.PurePosixPath(remote).parent))
            log.info("Uploading %s -> %s ...", local_path, remote)
            self._client.upload_sync(remote_path=remote, local_path=str(local_path))
            log.info("Upload complete.")
            misc_reg = _read_misc_registry(self._client)
            entry = {
                "uploaded_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "uploaded_by": self._uploader_name,
            }
            if message:
                entry["comment"] = message
            if project:
                entry["project"] = project
            misc_reg[resource_name] = entry
            _write_misc_registry(self._client, misc_reg)
            log.info("To download: example_get misc %s", resource_name)
            return
        if local_path is None:
            local_path = pathlib.Path.cwd() / resource_name
            resource_name = pathlib.Path(resource_name).name
        local_path = pathlib.Path(local_path)
        if not local_path.exists():
            raise ServerError(f"Local path does not exist: {local_path}")
        self._ensure_remote_dir(resource_type)
        remote = _remote_path(resource_type, resource_name)
        if not force and self._client.check(remote):
            raise ServerError(
                f"'{resource_name}' already exists on the {self._server} server. "
                "Use --force to overwrite."
            )
        with tempfile.TemporaryDirectory(prefix="example_upload_") as tmpdir:
            archive = pathlib.Path(tmpdir) / f"{resource_name}.tar.gz"
            _compress(local_path, archive, arcname=resource_name)
            log.info("Uploading %s -> %s ...", archive.name, remote)
            self._client.upload_sync(remote_path=remote, local_path=str(archive))
        log.info("Upload complete.")
        registry = _read_registry(self._client)
        entry = {
            "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "uploaded_by": self._uploader_name,
        }
        if message:
            entry["comment"] = message
        if project:
            entry["project"] = project
        registry[resource_type][resource_name] = entry
        _write_registry(self._client, registry)
        log.info("Registry updated.")
        log.info("To download: example_get %s %s", resource_type, resource_name)


class Downloader:
    def __init__(self, server: str | None = None):
        self._client = _get_client(server, need_write=False)
        self._server = server or "auto"

    def get_registry(self) -> dict:
        return _read_registry(self._client)

    def get_misc_registry(self) -> dict:
        return _read_misc_registry(self._client)

    def get_bin_registry(self) -> dict:
        return _read_bin_registry(self._client)

    def list_resources(self, resource_type: str) -> list[str]:
        if resource_type not in RESOURCE_TYPES:
            raise ServerError(
                f"Unknown resource type '{resource_type}'. "
                f"Choose from: {', '.join(RESOURCE_TYPES)}"
            )
        return _list_resource_names(self._client, resource_type)

    def download(
        self,
        resource_type: str,
        resource_name: str,
        local_path: pathlib.Path | None = None,
    ) -> pathlib.Path:
        if resource_type not in RESOURCE_TYPES:
            raise ServerError(
                f"Unknown resource type '{resource_type}'. "
                f"Choose from: {', '.join(RESOURCE_TYPES)}"
            )
        if resource_type == "misc":
            remote = _remote_path("misc", resource_name)
            if not self._client.check(remote):
                raise ServerError(
                    f"misc/{resource_name} not found on the {self._server} server."
                )
            if local_path is None:
                local_path = pathlib.Path.cwd()
            local_path = pathlib.Path(local_path)
            local_path.mkdir(parents=True, exist_ok=True)
            dest = local_path / pathlib.Path(resource_name).name
            log.info("Downloading %s ...", remote)
            self._client.download_sync(remote_path=remote, local_path=str(dest))
            log.info("Download complete: %s", dest)
            return dest
        if local_path is None:
            local_path = pathlib.Path.cwd()
        local_path = pathlib.Path(local_path)
        local_path.mkdir(parents=True, exist_ok=True)
        remote = _remote_path(resource_type, resource_name)
        if not self._client.check(remote):
            raise ServerError(
                f"Resource '{resource_name}' (type: {resource_type}) "
                f"not found on the {self._server} server."
            )
        with tempfile.TemporaryDirectory(prefix="example_download_") as tmpdir:
            archive = pathlib.Path(tmpdir) / f"{resource_name}.tar.gz"
            log.info("Downloading %s ...", remote)
            self._client.download_sync(remote_path=remote, local_path=str(archive))
            _extract(archive, local_path)
        dest = local_path / resource_name
        log.info("Download complete: %s", dest)
        return dest


def mkdir_misc(path: str, server: str | None = None) -> None:
    client = _get_client(server, need_write=True)
    full_path = f"misc/{path.strip('/')}"
    _ensure_remote_path(client, full_path)
    log.info("Created misc/%s.", path.strip("/"))


def sync_registry(server: str | None = None) -> dict:
    """Rebuild the registry by inspecting all resources on the server."""
    client = _get_client(server, need_write=True)
    old_registry = _read_registry(client)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    registry = _empty_registry()

    for name in _list_resource_names(client, "type_a"):
        try:
            log.info("Registering type_a '%s' ...", name)
            old = old_registry["type_a"].get(name, {})
            registry["type_a"][name] = {
                "created_at": old.get("created_at", now),
                "uploaded_by": old.get("uploaded_by"),
            }
        except Exception as exc:
            log.warning("Skipping type_a '%s': %s", name, exc)

    for name in _list_resource_names(client, "type_b"):
        try:
            log.info("Registering type_b '%s' ...", name)
            old = old_registry["type_b"].get(name, {})
            registry["type_b"][name] = {
                "created_at": old.get("created_at", now),
                "uploaded_by": old.get("uploaded_by"),
            }
        except Exception as exc:
            log.warning("Skipping type_b '%s': %s", name, exc)

    registry["projects"] = old_registry.get("projects", [])
    _write_registry(client, registry)
    counts = ", ".join(f"{len(registry[t])} {t}" for t in _ARCHIVABLE_TYPES)
    log.info("Registry synced: %s.", counts)
    return registry


def list_projects(server: str | None = None) -> list:
    client = _get_client(server, need_write=False)
    return sorted(_read_registry(client).get("projects", []))


def add_project(project_name: str, server: str | None = None) -> None:
    client = _get_client(server, need_write=True)
    registry = _read_registry(client)
    projects = registry.setdefault("projects", [])
    if project_name in projects:
        raise ServerError(f"Project '{project_name}' already exists.")
    projects.append(project_name)
    registry["projects"] = sorted(projects)
    _write_registry(client, registry)
    log.info("Added project '%s'.", project_name)


def rename_project(old_name: str, new_name: str, server: str | None = None) -> None:
    """Rename a project and update all resources that reference it."""
    client = _get_client(server, need_write=True)
    registry = _read_registry(client)
    projects = registry.setdefault("projects", [])
    if old_name not in projects:
        raise ServerError(f"Project '{old_name}' not found.")
    if new_name in projects:
        raise ServerError(f"Project '{new_name}' already exists.")
    projects[projects.index(old_name)] = new_name
    registry["projects"] = sorted(projects)
    for section in ("type_a", "type_b"):
        for meta in registry.get(section, {}).values():
            if meta.get("project") == old_name:
                meta["project"] = new_name
    _write_registry(client, registry)
    log.info("Renamed project '%s' -> '%s'.", old_name, new_name)


def remove_project(project_name: str, server: str | None = None) -> None:
    client = _get_client(server, need_write=True)
    registry = _read_registry(client)
    projects = registry.setdefault("projects", [])
    if project_name not in projects:
        raise ServerError(f"Project '{project_name}' not found.")
    projects.remove(project_name)
    registry["projects"] = sorted(projects)
    _write_registry(client, registry)
    log.info("Removed project '%s'.", project_name)


def get_free_space(server: str | None = None) -> int:
    return _get_client(server, need_write=False).free()
