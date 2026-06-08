"""
List resources available on the MyProject server.

    example_ls [RESOURCE_TYPE] [--server public|private] [--project NAME]

RESOURCE_TYPE: "type_a", "type_b", registry, misc, bin  (default: registry).
"""
import argparse
import logging
import sys

from my_server._logging import ColorHandler

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(ColorHandler())

_USE_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(text, *codes):
    return ("".join(codes) + str(text) + "\033[0m") if _USE_COLOR else str(text)


_BOLD  = "\033[1m"
_DIM   = "\033[2m"
_CYAN  = "\033[36m"
_GREEN = "\033[32m"


def _header(s): return _c(s, _BOLD, _CYAN)
def _bold(s):   return _c(s, _BOLD)
def _dim(s):    return _c(s, _DIM)
def _green(s):  return _c(s, _GREEN)
def _cmt(s):    return _dim(f'"{s[:50]}{"..." if len(s) > 50 else ""}"' )


def _table(title, headers, plain_rows, colored_rows):
    print(f"\n  {_header(title)}")
    if not plain_rows:
        print(_dim("  (none)"))
        return
    widths = [len(h) for h in headers]
    for row in plain_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def _hline(l, m, r):
        return "  " + l + m.join("\u2500" * (w + 2) for w in widths) + r

    def _row_line(plain_cells, colored_cells):
        parts = [f" {colored}{chr(32) * (w - len(plain))} "
                 for plain, colored, w in zip(plain_cells, colored_cells, widths)]
        return "  \u2502" + "\u2502".join(parts) + "\u2502"

    print(_hline("\u250c", "\u252c", "\u2510"))
    print(_row_line(headers, [_bold(h) for h in headers]))
    print(_hline("\u251c", "\u253c", "\u2524"))
    for p_row, c_row in zip(plain_rows, colored_rows):
        print(_row_line(p_row, c_row))
    print(_hline("\u2514", "\u2534", "\u2518"))


def _resource_rows(resources: dict):
    has_comment = any(m.get("comment") for m in resources.values())
    has_project = any(m.get("project") for m in resources.values())
    headers = ["Name", "Date", "Uploaded by"]
    if has_project:
        headers.append("Project")
    if has_comment:
        headers.append("Comment")
    plain, colored = [], []
    for name, meta in sorted(resources.items()):
        date = meta.get("created_at", "")[:10]
        uploader = meta.get("uploaded_by") or ""
        p = [name, date, uploader]
        c = [_bold(name), _dim(date), uploader]
        if has_project:
            proj = meta.get("project") or ""
            p.append(proj)
            c.append(_green(proj) if proj else "")
        if has_comment:
            cmt = meta.get("comment") or ""
            cp = f'"{cmt[:50]}{"..." if len(cmt) > 50 else ""}"' if cmt else ""
            p.append(cp)
            c.append(_cmt(cmt) if cmt else "")
        plain.append(p)
        colored.append(c)
    return headers, plain, colored


def _misc_rows(entries, misc_reg):
    has_comment = any(misc_reg.get(e, {}).get("comment") for e in entries)
    headers = ["Path", "Date", "Uploaded by"]
    if has_comment:
        headers.append("Comment")
    plain, colored = [], []
    for name in sorted(entries):
        meta = misc_reg.get(name, {})
        date = meta.get("uploaded_at", "")[:10]
        up = meta.get("uploaded_by") or ""
        p = [name, date or "\u2014", up or "\u2014"]
        c = [_bold(name), _dim(date) if date else _dim("\u2014"), up or _dim("\u2014")]
        if has_comment:
            cmt = meta.get("comment") or ""
            cp = f'"{cmt[:50]}{"..." if len(cmt) > 50 else ""}"' if cmt else ""
            p.append(cp)
            c.append(_cmt(cmt) if cmt else "")
        plain.append(p)
        colored.append(c)
    return headers, plain, colored


def _bin_rows(bin_reg):
    has_comment = any(e.get("comment") for e in bin_reg.values())
    headers = ["Type", "Name", "Deleted at", "Deleted by"]
    if has_comment:
        headers.append("Comment")
    plain, colored = [], []
    for key, meta in sorted(bin_reg.items()):
        rtype = meta.get("resource_type", "")
        rname = meta.get("resource_name", key)
        date = meta.get("deleted_at", "")[:10]
        deleter = meta.get("deleted_by") or ""
        p = [rtype, rname, date or "\u2014", deleter or "\u2014"]
        c = [_dim(rtype), _bold(rname),
             _dim(date) if date else _dim("\u2014"),
             deleter or _dim("\u2014")]
        if has_comment:
            cmt = meta.get("comment") or ""
            cp = f'"{cmt[:50]}{"..." if len(cmt) > 50 else ""}"' if cmt else ""
            p.append(cp)
            c.append(_cmt(cmt) if cmt else "")
        plain.append(p)
        colored.append(c)
    return headers, plain, colored


def _pick_project(projects):
    if not projects:
        print(_dim("  No projects defined. Use 'example_manage_project add <name>'."))
        return None
    print(f"\n  {_header(f'Projects ({len(projects)})')}")
    for i, p in enumerate(projects, 1):
        print(f"    {i}. {_green(p)}")
    try:
        raw = input("\nProject number (press Enter to cancel): ").strip()
    except EOFError:
        return None
    if not raw:
        return None
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(projects):
            return projects[idx]
        print("Invalid number.", file=sys.stderr)
    except ValueError:
        print("Invalid input.", file=sys.stderr)
    return None


def _resolve_project(downloader, requested):
    registry = downloader.get_registry()
    projects = sorted(registry.get("projects", []))
    if requested in projects:
        return requested
    print(f"  Project '{requested}' does not exist. "
          "Use 'example_manage_project add <name>' to create a new project.",
          file=sys.stderr)
    return _pick_project(projects)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "resource_type",
        choices=["type_a", "type_b", "registry", "misc", "bin"],
        nargs="?",
        default="registry",
    )
    parser.add_argument("--server", choices=["public", "private"], default=None)
    parser.add_argument("--project", default=None, metavar="NAME")
    parser.add_argument("--type", choices=["type_a", "type_b", "misc"], default=None,
                        dest="bin_type", metavar="TYPE")
    args = parser.parse_args()

    from my_server.server_utils import Downloader, ServerError

    try:
        downloader = Downloader(server=args.server)
        project_filter = None
        if args.project is not None:
            project_filter = _resolve_project(downloader, args.project)
            if project_filter is None:
                sys.exit(0)

        def _filter(resources):
            if project_filter is None:
                return resources
            return {k: v for k, v in resources.items()
                    if v.get("project") == project_filter}

        title_suffix = f" [{project_filter}]" if project_filter else ""

        if args.resource_type == "registry":
            registry = downloader.get_registry()
            type_a = _filter(registry.get("type_a", {}))
            type_b = _filter(registry.get("type_b", {}))
            _table(f"Type_a ({len(type_a)})" + title_suffix, *_resource_rows(type_a))
            _table(f"Type_b ({len(type_b)})" + title_suffix, *_resource_rows(type_b))
            if not project_filter:
                projects = sorted(registry.get("projects", []))
                print(f"\n  {_header(f'Projects ({len(projects)})')}")
                if projects:
                    for p in projects:
                        print(f"    {_green(p)}")
                else:
                    print(_dim("  (none)"))
            print()

        elif args.resource_type == "type_a":
            resources = downloader.list_resources("type_a")
            registry = downloader.get_registry()
            items = _filter(
                {r: registry["type_a"][r] for r in resources if r in registry["type_a"]}
            )
            _table(f"Type_a ({len(items)})" + title_suffix, *_resource_rows(items))
            if not project_filter:
                for r in resources:
                    if r not in registry["type_a"]:
                        print(f"  {_bold(r)}  {_dim('(not in registry)')}")
            print()

        elif args.resource_type == "type_b":
            resources = downloader.list_resources("type_b")
            registry = downloader.get_registry()
            items = _filter(
                {r: registry["type_b"][r] for r in resources if r in registry["type_b"]}
            )
            _table(f"Type_b ({len(items)})" + title_suffix, *_resource_rows(items))
            if not project_filter:
                for r in resources:
                    if r not in registry["type_b"]:
                        print(f"  {_bold(r)}  {_dim('(not in registry)')}")
            print()

        elif args.resource_type == "misc":
            entries = downloader.list_resources("misc")
            misc_reg = downloader.get_misc_registry()
            _table(f"misc/ ({len(entries)} entries)", *_misc_rows(entries, misc_reg))
            print()

        elif args.resource_type == "bin":
            bin_reg = downloader.get_bin_registry()
            if args.bin_type:
                bin_reg = {k: v for k, v in bin_reg.items()
                           if v.get("resource_type") == args.bin_type}
            type_suffix = f" [{args.bin_type}]" if args.bin_type else ""
            _table(f"Bin ({len(bin_reg)} entries){type_suffix}", *_bin_rows(bin_reg))
            print()

    except ServerError as e:
        log.error("%s", e)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
