"""
Rename a resource and/or update its comment on the MyProject server.

    example_mv RESOURCE_TYPE OLD_NAME [NEW_NAME] [--comment TEXT]
"""
import argparse, logging, sys
from my_server._logging import ColorHandler
log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("resource_type", choices=["type_a", "type_b", "misc"])
    parser.add_argument("old_name")
    parser.add_argument("new_name", nargs="?", default=None)
    parser.add_argument("--comment", "-c", default=None)
    parser.add_argument("--server", choices=["public", "private"], default=None)
    args = parser.parse_args()
    if args.new_name is None and args.comment is None:
        parser.error("Provide a new name, --comment, or both.")

    from my_server.server_utils import ServerError, rename
    try:
        rename(args.resource_type, args.old_name, args.new_name,
               server=args.server, comment=args.comment)
    except ServerError as e: log.error("%s", e); sys.exit(1)
    except KeyboardInterrupt: print("\nInterrupted.", file=sys.stderr); sys.exit(1)


if __name__ == "__main__": main()
