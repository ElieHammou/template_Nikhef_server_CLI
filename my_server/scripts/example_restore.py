"""
Restore a resource from bin/ back to its original location.

    example_restore RESOURCE_TYPE NAME
"""
import argparse, logging, sys
from my_server._logging import ColorHandler
log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("resource_type", choices=["type_a", "type_b", "misc"])
    parser.add_argument("name", metavar="NAME")
    parser.add_argument("-f", "--force", action="store_true")
    parser.add_argument("--server", choices=["public", "private"], default=None)
    args = parser.parse_args()

    from my_server.server_utils import ServerError, restore
    if not args.force:
        if input(f"Restore '{args.name}' from bin? [y/N] ").strip().lower() != "y":
            print("Aborted."); sys.exit(0)
    try:
        restore(args.resource_type, args.name, server=args.server)
    except ServerError as e: log.error("%s", e); sys.exit(1)
    except KeyboardInterrupt: print("\nInterrupted.", file=sys.stderr); sys.exit(1)


if __name__ == "__main__": main()
