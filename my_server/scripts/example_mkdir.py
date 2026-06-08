"""
Create a directory under misc/ on the MyProject server.

    example_mkdir PATH
"""
import argparse, logging, sys
from my_server._logging import ColorHandler
log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path")
    parser.add_argument("--server", choices=["public", "private"], default=None)
    args = parser.parse_args()

    from my_server.server_utils import ServerError, mkdir_misc
    try:
        mkdir_misc(args.path, server=args.server)
    except ServerError as e: log.error("%s", e); sys.exit(1)
    except KeyboardInterrupt: print("\nInterrupted.", file=sys.stderr); sys.exit(1)


if __name__ == "__main__": main()
