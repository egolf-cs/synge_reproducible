import z3
from pprint import pprint

from synge.generalization import Generalizer

from list_utils.permutations import (
    permutation_dicts, 
    apply_stateperm_var_full,)

# Wrapper for allowing Z3 ASTs to be stored into Python Hashtables. 
class AstRefKey:
    def __init__(self, n):
        self.n = n
    def __hash__(self):
        return self.n.hash()
    def __eq__(self, other):
        return self.n.eq(other.n)
    def __repr__(self):
        return str(self.n)

def askey(n):
    assert isinstance(n, z3.AstRef)
    return AstRefKey(n)

def get_vars(f):
    r = set()
    def collect(f):
      if z3.is_const(f): 
          if f.decl().kind() == z3.Z3_OP_UNINTERPRETED and not askey(f) in r:
              r.add(askey(f))
      else:
          for c in f.children():
              collect(c)
    collect(f)
    return r

class G_perm(Generalizer):
    
    def __init__(
            self, subG, process=None, permable=None, **kwds) -> None:
        super().__init__(**kwds)

        # This generalizer wraps around, e.g., G1 and does permutation stuff
        self._subgeneralizer = subG
        self._solver = subG._solver
        self.candidates = self._solver.candidates
        self.reverse_candidates = dict([(str(v),k) for (k,v) in self.candidates.items()])
        self.better_candidates = {}
        self.mk_better_candidates()

        self.proc = process
        if permable == None or process == None:
            self._permable = []
        else:
            self._permable = permable

        self._emit(self._id, "__init__", "permutable states", self._permable)

    def mk_better_candidates(self):
        for k, v in self.candidates.items():
            (proc, p, a, q) = k
            if proc not in self.better_candidates:
                self.better_candidates[proc] = {}
            if p not in self.better_candidates[proc]:
                self.better_candidates[proc][p] = {}
            if q not in self.better_candidates[proc][p]:
                self.better_candidates[proc][p][q] = {}
            self.better_candidates[proc][p][q][a] = v

    def _generalize(self, candidate):
        is_correct, preliminary_gen = self._subgeneralizer.generalize(
            candidate)
        clauses = [preliminary_gen]
        G = list(permutation_dicts(self._permable))
        for perm in G:
            candidate_pr = self.apply_perm(perm, preliminary_gen)
            clauses.append(candidate_pr)
        return is_correct, self._solver.Or(clauses)

    def dummy_perm_bad(self, perm):
            d = {}
            for k, v in self.candidates.items():
                pk = apply_stateperm_var_full(perm, k, self.proc)
                d[v] = self.candidates[pk]
            return d
    
    def dummy_perm(self, perm, expr):
        dummy_vars = get_vars(expr)
        dummy_vars = [z3.Bool(str(k)) for k in dummy_vars]
        res = {}
        for k in dummy_vars:
            (proc, p, a, q) = self.reverse_candidates[str(k)]
            k = self.candidates[(proc, p, a, q)]
            if proc != self.proc:
                continue
            if not(p in perm or q in perm):
                continue
            if p in perm:
                p = perm[p]
            if q in perm:
                q = perm[q]
            newk = self.better_candidates[self.proc][p][q][a]
            res[k] = newk
        return res     

    def apply_perm(self, perm, expr):
        dperm = self.dummy_perm(perm, expr)
        expr_pr = self._solver.substitute(
            expr, [(k,v) for k,v in dperm.items()])
        return expr_pr