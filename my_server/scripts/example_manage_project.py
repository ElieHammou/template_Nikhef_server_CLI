"""
Manage the project list on the MyProject server.

    example_manage_project list
    example_manage_project add    PROJECT_NAME
    example_manage_project rename OLD_NAME NEW_NAME
    example_manage_project remove PROJECT_NAME
"""
import argparse, logging, sys
from my_server._logging import ColorHandler
log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--server", choices=["public", "private"], default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    p_add = sub.add_parser("add"); p_add.add_argument("project_name")
    p_ren = sub.add_parser("rename")
    p_ren.add_argument("old_name"); p_ren.add_argument("new_name")
    p_rem = sub.add_parser("remove"); p_rem.add_argument("project_name")
    args = parser.parse_args()

    from my_server.server_utils import (
        ServerError, add_project, list_projects, remove_project, rename_project)
    try:
        if args.command == "list":
            projects = list_projects(server=args.server)
            print("\n".join(projects) if projects else "(no projects defined)")
        elif args.command == "add":
            add_project(args.project_name, server=args.server)
        elif args.command == "rename":
            rename_project(args.old_name, args.new_name, server=args.server)
        elif args.command == "remove":
            remove_project(args.project_name, server=args.server)
    except ServerError as e: log.error("%s", e); sys.exit(1)
    except KeyboardInterrupt: print("\nInterrupted.", file=sys.stderr); sys.exit(1)


if __name__ == "__main__": main()
