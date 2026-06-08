"""
MyProject server management.

    example_server {setup,storage,sync,tutorial} [options]
"""
import argparse, getpass, logging, pathlib, sys
import yaml
from my_server._logging import ColorHandler
log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())

_USE_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(t, *c): return ("".join(c) + str(t) + "\033[0m") if _USE_COLOR else str(t)


_BOLD = "\033[1m"; _DIM = "\033[2m"; _CYAN = "\033[36m"; _GREEN = "\033[32m"
def _header(s): return _c(s, _BOLD, _CYAN)
def _bold(s):   return _c(s, _BOLD)
def _dim(s):    return _c(s, _DIM)
def _green(s):  return _c(s, _GREEN)

_CONFIG_PATH = pathlib.Path.home() / ".config" / "myproject" / "server.yaml"
_REQUIRED_KEYS = ("webdav_hostname", "webdav_login", "webdav_password")
_PROFILES = ("public", "private")


def _validate(config):
    if not isinstance(config, dict): raise ValueError("Must be a YAML mapping.")
    unknown = set(config) - set(_PROFILES)
    if unknown: raise ValueError(f"Unknown profile(s): {', '.join(sorted(unknown))}")
    if not config: raise ValueError("No profiles configured.")
    for profile, values in config.items():
        if not isinstance(values, dict):
            raise ValueError(f"Profile '{profile}' must be a mapping.")
        for key in _REQUIRED_KEYS:
            if key not in values:
                raise ValueError(f"Missing key '{key}' under '{profile}:'.")


def _prompt_profile(profile):
    print(f"\n--- {profile.upper()} server ---")
    if input(f"Configure '{profile}' profile? [y/N] ").strip().lower() != "y":
        return None
    result = {
        "webdav_hostname": input("  webdav_hostname: ").strip(),
        "webdav_login":    input("  webdav_login:    ").strip(),
        "webdav_password": getpass.getpass("  webdav_password: "),
    }
    name = input("  name (shown in registry, optional): ").strip()
    if name: result["name"] = name
    return result


def _write_config(config):
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_PATH, "w") as f: yaml.dump(config, f, default_flow_style=False)
    _CONFIG_PATH.chmod(0o600)
    log.info("Credentials written to %s", _CONFIG_PATH)


_COMMANDS = [
    ("example_ls",
     "List server resources — type_a, type_b, registry, misc, bin.\n"
     "Use --project NAME to filter by project."),
    ("example_upload", "Upload a resource or misc file to the server."),
    ("example_get",    "Download a resource or misc file."),
    ("example_mv",
     "Rename a resource and/or update its comment.\n"
     "NEW_NAME is optional when --comment / -c is given."),
    ("example_rm",
     "Move one or more resources to bin/ on the server.\n"
     "Prompts for a deletion comment. Use -f to skip confirmation."),
    ("example_restore",        "Restore a resource from bin/ to its original location."),
    ("example_mkdir",          "Create a directory under misc/ on the server."),
    ("example_manage_project", "Manage the project list: add / rename / remove / list."),
    ("example_server",         "Setup credentials, check storage, sync registry."),
]


def _print_tutorial():
    cmd_w = max(len(cmd) for cmd, _ in _COMMANDS)
    print(f"\n  {_header('MyProject command reference')}\n")
    for cmd, desc in _COMMANDS:
        lines = desc.split("\n")
        print(f"  {_bold(cmd):{cmd_w + 10}}{lines[0]}")
        for extra in lines[1:]:
            print(f"  {chr(32) * (cmd_w + 10)}{_dim(extra)}")
    print(f"\n  {_dim('Run any command with --help for full usage.')}\n")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_setup = sub.add_parser("setup")
    p_setup.add_argument("credentials_yaml", nargs="?", default=None)
    p_setup.add_argument("--force", action="store_true")
    p_storage = sub.add_parser("storage")
    p_storage.add_argument("--server", choices=["public", "private"], default=None)
    p_sync = sub.add_parser("sync")
    p_sync.add_argument("--server", choices=["public", "private"], default=None)
    sub.add_parser("tutorial")
    args = parser.parse_args()

    try:
        if args.command == "setup":
            if _CONFIG_PATH.exists() and not args.force:
                log.error("%s already exists. Use --force to overwrite.", _CONFIG_PATH)
                sys.exit(1)
            if args.credentials_yaml is not None:
                src = pathlib.Path(args.credentials_yaml)
                if not src.exists(): log.error("File not found: %s", src); sys.exit(1)
                with open(src) as f: config = yaml.safe_load(f)
                try: _validate(config)
                except ValueError as e: log.error("%s", e); sys.exit(1)
            else:
                config = {}
                for profile in _PROFILES:
                    result = _prompt_profile(profile)
                    if result is not None: config[profile] = result
                if not config: log.error("No profiles configured."); sys.exit(1)
            _write_config(config)

        elif args.command == "storage":
            from my_server.server_utils import ServerError, get_free_space
            try:
                _TOTAL_GB = 1000.0
                free_bytes = get_free_space(server=args.server)
                free_gb = free_bytes / (1024 ** 3)
                used_gb = _TOTAL_GB - free_gb
                filled = round(used_gb / _TOTAL_GB * 30)
                bar = "\u2588" * filled + "\u2591" * (30 - filled)
                print(f"\n  {_header('Storage')}")
                print(f"  {bar}  {_bold(f'{used_gb:.1f}')} / {_TOTAL_GB:.0f} GB used"
                      f"  ({_green(f'{free_gb:.1f} GB free')})\n")
            except ServerError as e: log.error("%s", e); sys.exit(1)

        elif args.command == "sync":
            from my_server.server_utils import ServerError, sync_registry
            try: sync_registry(server=args.server)
            except ServerError as e: log.error("%s", e); sys.exit(1)

        elif args.command == "tutorial":
            _print_tutorial()

    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr); sys.exit(1)


if __name__ == "__main__": main()
