from pycparser import parse_file, c_generator, c_parser

def translate_to_c(filename):
    """ Simply use the c_generator module to emit a parsed AST.
    """
    ast = parse_file(filename, use_cpp=True)
    generator = c_generator.CGenerator()
    print(generator.visit(ast))


translate_to_c("output.c")


# # Create a parser object
# parser = c_parser.CParser()

# # Parse the C code
# ast = parser.parse(c_code)

# # Print the AST
# ast.show()
