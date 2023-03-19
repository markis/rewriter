from rewriter.options import parse_options
from rewriter.parser import parse_tree, unparse_tree
from rewriter.walker import Walker

opts = parse_options()
tree = parse_tree(opts)

walker = Walker(opts, tree)
walker.walk()

if opts.verbose:
    walker.print_stats()

if not opts.dry_run:
    unparse_tree(opts, tree, walker.stats)
