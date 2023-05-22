from universes.u0 import U0

class U1(U0):

    def __init__(
            self, p, automata, snb, snb_messages, solver, **kwds) -> None:
        super().__init__(p, automata, snb, snb_messages, solver, **kwds)

    def _prune(self, expr):
        neg_expr = self._solver.Not(expr)
        self._state = self._solver.And([self._state, neg_expr])
        self._solver.add(neg_expr)

