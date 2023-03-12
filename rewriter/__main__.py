from ast import parse, unparse
from rewriter.walker import Walker

source = ""
tree = parse(source)
Walker(tree).walk()
result = unparse(tree)
print(result)
