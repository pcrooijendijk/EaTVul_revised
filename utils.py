# -*- coding: utf-8 -*-
"""
Created on Sat Oct 17 21:11:59 2020

@author: DrLC
"""

import re
from tree_sitter import Language, Parser

def is_fp(num):
    
    if num.lower() in ["inf", "nan"]:
        return False
    try:
        float(num)
        return True
    except:
        return False
    
def is_uid(uid):
    
    m = re.match(r"[a-zA-Z_][a-zA-Z0-9_]*", uid)
    if (m is not None) and m.group() == uid and (not is_keyword(uid)):
        return True
    return False

def is_keyword(uid):
    
    if uid in ["auto", "break", "case", "char", "const", "continue",
               "default", "do", "double", "else", "enum", "extern",
               "float", "for", "goto", "if", "inline", "int", "long",
               "register", "restrict", "return", "short", "signed",
               "sizeof", "static", "struct", "switch", "typedef",
               "union", "unsigned", "void", "volatile", "while",
               "_Alignas", "_Alignof", "_Atomic", "_Bool", "_Complex",
               "_Generic", "_Imaginary", "_Noreturn", "_Static_assert",
               "_Thread_local", "__func__"]:
        return True
    return False

def is_special_id(_id):
    
    if _id in ["NULL", "_IOFBF", "_IOLBF", "BUFSIZ", "EOF", "FOPEN_MAX", "TMP_MAX",  # <stdio.h> macro
               "FILENAME_MAX", "L_tmpnam", "SEEK_CUR", "SEEK_END", "SEEK_SET",
               "NULL", "EXIT_FAILURE", "EXIT_SUCCESS", "RAND_MAX", "MB_CUR_MAX",     # <stdlib.h> macro
               "main",                                      # main function
               "stdio", "cstdio", "stdio.h",                                # <stdio.h> & <cstdio>
               "size_t", "FILE", "fpos_t", "stdin", "stdout", "stderr",     # <stdio.h> types & streams
               "remove", "rename", "tmpfile", "tmpnam", "fclose", "fflush", # <stdio.h> functions
               "fopen", "freopen", "setbuf", "setvbuf", "fprintf", "fscanf",
               "printf", "scanf", "snprintf", "sprintf", "sscanf", "vprintf",
               "vscanf", "vsnprintf", "vsprintf", "vsscanf", "fgetc", "fgets",
               "fputc", "getc", "getchar", "putc", "putchar", "puts", "ungetc",
               "fread", "fwrite", "fgetpos", "fseek", "fsetpos", "ftell",
               "rewind", "clearerr", "feof", "ferror", "perror", "getline"
               "stdlib", "cstdlib", "stdlib.h",                             # <stdlib.h> & <cstdlib>
               "size_t", "div_t", "ldiv_t", "lldiv_t",                      # <stdlib.h> types
               "atof", "atoi", "atol", "atoll", "strtod", "strtof", "strtold",  # <stdlib.h> functions
               "strtol", "strtoll", "strtoul", "strtoull", "rand", "srand",
               "aligned_alloc", "calloc", "malloc", "realloc", "free", "abort",
               "atexit", "exit", "at_quick_exit", "_Exit", "getenv",
               "quick_exit", "system", "bsearch", "qsort", "abs", "labs",
               "llabs", "div", "ldiv", "lldiv", "mblen", "mbtowc", "wctomb",
               "mbstowcs", "wcstombs",
               "string", "cstring", "string.h",                                 # <string.h> & <cstring>
               "memcpy", "memmove", "memchr", "memcmp", "memset", "strcat",     # <string.h> functions
               "strncat", "strchr", "strrchr", "strcmp", "strncmp", "strcoll",
               "strcpy", "strncpy", "strerror", "strlen", "strspn", "strcspn",
               "strpbrk" ,"strstr", "strtok", "strxfrm",
               "memccpy", "mempcpy", "strcat_s", "strcpy_s", "strdup",      # <string.h> extension functions
               "strerror_r", "strlcat", "strlcpy", "strsignal", "strtok_r",
               "iostream", "istream", "ostream", "fstream", "sstream",      # <iostream> family
               "iomanip", "iosfwd",
               "ios", "wios", "streamoff", "streampos", "wstreampos",       # <iostream> types
               "streamsize", "cout", "cerr", "clog", "cin",
               "boolalpha", "noboolalpha", "skipws", "noskipws", "showbase",    # <iostream> manipulators
               "noshowbase", "showpoint", "noshowpoint", "showpos",
               "noshowpos", "unitbuf", "nounitbuf", "uppercase", "nouppercase",
               "left", "right", "internal", "dec", "oct", "hex", "fixed",
               "scientific", "hexfloat", "defaultfloat", "width", "fill",
               "precision", "endl", "ends", "flush", "ws", "showpoint",
               "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "sinh",    # <math.h> functions
               "cosh", "tanh", "exp", "sqrt", "log", "log10", "pow", "powf",
               "ceil", "floor", "abs", "fabs", "cabs", "frexp", "ldexp",
               "modf", "fmod", "hypot", "ldexp", "poly", "matherr"]:
        return True
    return False

def is_java_uid(uid):
    
    m = re.match(r"[a-zA-Z_][a-zA-Z0-9_]*", uid)
    if (m is not None) and m.group() == uid and (not is_java_keyword(uid)):
        return True
    return False

def is_java_keyword(uid):
    
    # https://en.wikipedia.org/wiki/List_of_Java_keywords
    if uid in ["abstract", "assert", "boolean", "break", "byte", "case", "catch",
               "char", "class", "const", "continue", "default", "do", "double",
               "else", "enum", "extends", "final", "finally", "float", "for",
               "goto", "if", "implements", "import", "instanceof", "int", 
               "interface", "long", "native", "new", "package", "private",
               "protected", "public", "return", "strictfp", "short", "static",
               "super", "switch", "synchronized", "this", "throw", "throws",
               "transient", "try", "void", "volatile", "while",
               "permits", "record", "sealed", "var", "yield",
               "true", 'false', 'null',
               "const", "goto"]:
        return True
    return False

def is_java_special_id(uid):
    
    java_special_ids = getattr(is_java_special_id, 'special_ids', None)
    if java_special_ids is None:
        with open("../data/java_special_ids.txt", "r") as f:
            is_java_special_id.special_ids = f.read().split()
            is_java_special_id.special_ids.append("main")
            java_special_ids = getattr(is_java_special_id, 'special_ids', None)
    if uid in java_special_ids:
        return True
    return False

def tokenize_java(src, so_path='../data/java-language.so'):
    
    parser = getattr(tokenize_java, 'parser', None)
    if parser is None:
        JAVA_LANGUAGE = Language(so_path, 'java')
        tokenize_java.parser = Parser()
        tokenize_java.parser.set_language(JAVA_LANGUAGE)
        parser = getattr(tokenize_java, 'parser', None)
    byte_seq = bytes(src, encoding='utf-8')
    tree = parser.parse(byte_seq)
    tokens = []
    def get_tokenseq(node):
        if node.type != 'comment' and len(node.children) <= 0:
            tokens.append(byte_seq[node.start_byte: node.end_byte])
        for c in node.children:
            get_tokenseq(c)
    get_tokenseq(tree.root_node)
    tokens = [str(t, 'utf-8') for t in tokens]
    return tokens
        

def normalize(seq):
    
    norm = []
    for t in seq:
        if "'" in t:
            norm.append("<char>")
        elif '"' in t:
            norm.append("<str>")
        elif t.isdigit() or t[:2] == "0x":
            norm.append("<int>")
        elif is_fp(t):
            norm.append("<fp>")
        else:
            norm.append(t)
    return norm

def denormalize(seq):
    
    denorm = []
    for t in seq:
        if t == "<char>":
            denorm.append("'0'")
        elif t == "<str>":
            denorm.append("\"0\"")
        elif t == "<int>":
            denorm.append("0")
        elif t == "<fp>":
            denorm.append("0.0")
        else:
            denorm.append(t)
    return denorm

def align_subtokens(tokens, subtokens, bpe_indicator='Ġ', specials=[]):
    
    align = [-1]
    idx = 0
    for i in range(1, len(subtokens)-1):
        if subtokens[i][0] == bpe_indicator or subtokens[i] in specials:
            idx += 1
        align.append(idx)
    assert idx == len(tokens) - 1, \
        "\n"+str([(subtokens[i], tokens[align[i]]) for i in range(1, len(subtokens)-1)])
    align.append(-1)
    assert len(align) == len(subtokens)
    align_rev = []
    for i in range(1, len(subtokens)-1):
        if align[i] == len(align_rev):
            align_rev.append([])
        align_rev[align[i]].append(i)
    assert len(align_rev) == len(tokens)
    return align, align_rev