"""
Upload a resource to the MyProject server.

    example_upload RESOURCE_TYPE RESOURCE_NAME [LOCAL_PATH]
"""
import argparse, logging, sys
from my_server._logging import ColorHandler
log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())


def _prompt_project(projects):
    if not projects: return None
    print("Available projects:")
    for i, p in enumerate(projects, 1): print(f"  {i}. {p}")
    raw = input("Project number (press Enter to skip): ").strip()
    if not raw: return None
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(projects): return projects[idx]
        print("Invalid number.", file=sys.stderr)
    except ValueError:
        print("Invalid input.", file=sys.stderr)
    return None


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("resource_type", choices=["type_a", "type_b", "misc"])
    parser.add_argument("resource_name")
    parser.add_argument("local_path", nargs="?", default=None)
    parser.add_argument("--server", choices=["public", "private"], default=None)
    parser.add_argument("-f", "--force", action="store_true")
    parser.add_argument("-m", "--message", default=None)
    parser.add_argument("--project", default=None)
    args = parser.parse_args()

    message = args.message
    if message is None:
        try: message = input("Comment (press Enter to skip): ").strip() or None
        except EOFError: message = None

    from my_server.server_utils import ServerError, Uploader, list_projects
    project = args.project
    if args.resource_type in ("type_a", "type_b"):
        try:
            projects = list_projects(server=args.server)
            if project is not None:
                if project not in projects:
                    print(f"Project '{project}' does not exist.", file=sys.stderr)
                    project = _prompt_project(projects)
            else:
                project = _prompt_project(projects)
        except (ServerError, EOFError): pass

    try:
        Uploader(server=args.server).upload(
            args.resource_type, args.resource_name, args.local_path,
            args.force, message, project)
    except ServerError as e: log.error("%s", e); sys.exit(1)
    except KeyboardInterrupt: print("\nInterrupted.", file=sys.stderr); sys.exit(1)


if __name__ == "__main__": main()
