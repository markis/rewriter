from ast import parse, unparse
from rewriter.walker import Walker

import argparse
from pprint import pprint

parser = argparse.ArgumentParser(prog="Rewriter", description="Rewrite python code")
parser.add_argument("filename")
# parser.add_argument("--type", default="Any")
parser.add_argument("-d", "--dry-run", action="store_true")

args = parser.parse_args()

if args and args.filename:
    with open(args.filename) as f:
        source = f.read()
    tree = parse(source)
    walker = Walker(args.filename, tree)
    walker.walk()
    result = unparse(tree)

    if walker.stats:
        print(args.filename)
        pprint(walker.stats)

    if not args.dry_run:
        with open(args.filename, "w") as f:
            f.write(result)
