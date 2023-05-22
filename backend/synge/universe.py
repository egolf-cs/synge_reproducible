class Universe:

    def __init__(self, id=None, L=None) -> None:
        """Derived class overrides __init__,  _pick, _prune,
        get_state, and set_state.
        """
        self._id = id
        if L == None:
            self._emit = lambda *_: None
        else:
            self._emit = L.emit

    def _pick(self):
        pass
    def _prune(self,expr):
        pass
    def _mk_expr_str(self, expr):
        return expr
    
    def pick(self):
        # self._emit(self._id, "pick", "input", tuple())
        res = self._pick()
        # self._emit(self._id, "pick", "output", res)
        return res

    def prune(self, expr):
        # self._emit(self._id, "prune", "input", self._mk_expr_str(expr))
        self._prune(expr)
        # self._emit(self._id, "prune", "output", None)

    def get_state(self):
        pass

    def set_state(self, expr):
        pass