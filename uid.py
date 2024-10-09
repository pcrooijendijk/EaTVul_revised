# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 21:45:02 2020

@author: DrLC
"""

from cparser import CCode
from utils import normalize, denormalize, is_uid, is_special_id

import copy

class UIDStruct(object):
    
    def __init__(self, code, norm=True, mask="<unk>"):
        
        self.history = []
        self.norm = norm
        self.code = [t.strip() for t in code]
        self._build_cc()
        self._build_symtab()
        if self.norm:
            self.code = normalize(self.code)
        self.mask = mask
    
    def _build_cc(self):
        
        self.ccode = CCode(" ".join(self.code))
    
    def _build_symtab(self):
        
        self.sym2pos = {}
        for sym in self.ccode.getSymbolTable().getSymbols():
            if is_special_id(sym):
                continue
            self.sym2pos[sym] = []
            for i in range(len(self.code)):
                if self.code[i] == sym:
                    self.sym2pos[sym].append(i)
                    
    def gen_mask(self):
        
        mask = {}
        for s in self.sym2pos.keys():
            mask[s] = copy.deepcopy(self.code)
            for p in self.sym2pos[s]:
                mask[s][p] = self.mask
        return mask
    
    def update_sym(self, old_sym, new_sym):
        
        if old_sym not in self.sym2pos.keys() or new_sym in self.sym2pos.keys():
            return False
        if (not is_uid(new_sym)) or is_special_id(new_sym):
            return False
        self.history.append((old_sym, new_sym))
        self.sym2pos[new_sym] = self.sym2pos.pop(old_sym)
        for p in self.sym2pos[new_sym]:
            self.code[p] = new_sym
        return True
    
    
    
    
    
if __name__ == "__main__":
    
    import pickle
    import tqdm
    
    len_threshold = -1
    
    with open("../../data/norm.pkl", "rb")  as f:
        d = pickle.load(f)
        
    for i in tqdm.tqdm(range(len(d['src']))):
        if len_threshold > 0 and len(d['src'][i])  >= len_threshold:
            continue

        s = [t.strip() for t in d['src'][i]]
        uid = UIDStruct(s)
        
        assert uid.ccode.getTokenSeq() == s, \
            "\n"+str(uid.ccode.getTokenSeq())+"\n"+str(s)
        assert uid.code == normalize(s), \
            "\n"+str(uid.code)+"\n"+str(d['norm'][i])
        
        for s in uid.sym2pos.keys():
            for p in uid.sym2pos[s]:
                assert uid.code[p] == s, \
                    "\n"+str(uid.code)+"\n"+str(uid.sym2pos)+"\n"+str(p)+" ["+uid.code[p]+"] ["+s+"]"

        keys = list(uid.sym2pos.keys())
        
        assert len(keys) < 2 or not uid.update_sym("AnImpossiblyLongVariableWhichCanNeverShowUpInCode", "Prefix_"+keys[1])
        assert len(keys) < 2 or not uid.update_sym(keys[0], keys[1])
        assert len(keys) < 2 or not uid.update_sym(keys[0], "123")
        assert len(keys) < 2 or not uid.update_sym(keys[0], "1_wrong_id")
        assert len(keys) < 2 or not uid.update_sym(keys[0], "+_()_$#*UIQ")
        assert len(keys) < 2 or not uid.update_sym(keys[0], "for")
        assert len(keys) < 2 or not uid.update_sym(keys[0], "main")
        assert len(keys) < 2 or not uid.update_sym(keys[0], "NULL")

        update = []
        for m in keys:
            new_m = "Prefix_"+m
            uid.update_sym(m, new_m)
            update.append((m, new_m))
        keys = list(uid.sym2pos.keys())
        for m in keys:
            new_m = "Prefix_"+m
            uid.update_sym(m, new_m)
            update.append((m, new_m))
        assert update == uid.history
        denorm = denormalize(uid.code)
        try:
            CCode(" ".join(denormalize(uid.code)))
        except:
            assert False, \
                "\n"+str(uid.code)+"\n"+str(denorm)