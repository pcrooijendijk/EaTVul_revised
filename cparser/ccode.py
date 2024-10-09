# -*- coding: utf-8 -*-
"""
Created on Fri Sept 20 11:45:12 2019

@author: DrLC
"""

import copy

from .myparser import TreeNode, SymTab
from .myparser import getParsingTree, getSymbolTable
from .error import SyntaxError

class CCode(object):

    def __init__(self, _input):

        if isinstance(_input, str):
            root = getParsingTree(_input)
            symtab = getSymbolTable(root)
        elif isinstance(_input, TreeNode):
            root = _input
            symtab = getSymbolTable(_input)
        else:
            raise(TypeError("Invalid _input: "+str(_input)
                +".\nPlease use valid string or TreeNode type."))
        self._root = root
        self._syms = symtab
        self._tokens = self._getToken(self._root)

    def getParsingTree(self):

        return copy.deepcopy(self._root)

    def getSymbolTable(self):

        return copy.deepcopy(self._syms)
    
    def getTokenSeq(self):
        
        return self._tokens
    
    def _getToken(self, node):
        
        if node.getType() == '#':
            return [node.getValue().strip()]
        ret = []
        for c in node.getChildren():
            ret += self._getToken(c)
        for i in range(len(ret)):
            ret[i] = ret[i].strip()
        return ret