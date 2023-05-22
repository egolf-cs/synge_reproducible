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

class G_naive(Generalizer):
    
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
        G = list(permutation_dicts(self._permable))
        clauses = [preliminary_gen]
        for perm in G:
            new_cand = self._apply_perm_to_candidate(perm, candidate)
            _, gen = self._subgeneralizer.generalize(
                new_cand)
            clauses.append(gen)
        return is_correct, self._solver.Or(clauses)
    
    def _apply_perm_to_candidate(self, perm, candidate):
        new_candidate = []
        for proc, p, a, q in candidate:
            if proc != self.proc:
                pass
            else:
                if p in perm:
                    p = perm[p]
                if q in perm:
                    q = perm[q]
            new_candidate.append((proc, p, a, q))
        return new_candidate