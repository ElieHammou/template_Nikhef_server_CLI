"""
Move one or more resources to bin/ on the MyProject server.

    example_rm RESOURCE_TYPE NAME [NAME ...]
"""
import argparse, logging, sys
from my_server._logging import ColorHandler
log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("resource_type", choices=["type_a", "type_b", "misc"])
    parser.add_argument("names", nargs="+", metavar="NAME")
    parser.add_argument("-f", "--force", action="store_true")
    parser.add_argument("-m", "--message", default=None)
    parser.add_argument("--server", choices=["public", "private"], default=None)
    args = parser.parse_args()

    from my_server.server_utils import ServerError, trash
    message = args.message
    if message is None:
        try: message = input("Deletion comment (press Enter to skip): ").strip() or None
        except EOFError: message = None
    if not args.force:
        targets = ", ".join(f"'{n}'" for n in args.names)
        if input(f"Move {targets} to bin on server? [y/N] ").strip().lower() != "y":
            print("Aborted."); sys.exit(0)
    try:
        for name in args.names:
            trash(args.resource_type, name, server=args.server, message=message)
    except ServerError as e: log.error("%s", e); sys.exit(1)
    except KeyboardInterrupt: print("\nInterrupted.", file=sys.stderr); sys.exit(1)


if __name__ == "__main__": main()
