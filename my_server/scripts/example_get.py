"""
Download a resource from the MyProject server.

    example_get RESOURCE_TYPE RESOURCE_NAME [LOCAL_PATH]
"""
import argparse, logging, sys
from my_server._logging import ColorHandler
log = logging.getLogger(); log.setLevel(logging.INFO); log.addHandler(ColorHandler())


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("resource_type", choices=["type_a", "type_b", "misc"])
    parser.add_argument("resource_name")
    parser.add_argument("local_path", nargs="?", default=None)
    parser.add_argument("--server", choices=["public", "private"], default=None)
    args = parser.parse_args()

    from my_server.server_utils import Downloader, ServerError
    try:
        Downloader(server=args.server).download(
            args.resource_type, args.resource_name, args.local_path)
    except ServerError as e: log.error("%s", e); sys.exit(1)
    except KeyboardInterrupt: print("\nInterrupted.", file=sys.stderr); sys.exit(1)


if __name__ == "__main__": main()
