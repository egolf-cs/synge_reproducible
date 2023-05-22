class Generalizer:

    def __init__(self, id=None, L=None) -> None:
        """Derived class overrides __init__ and _generalize."""
        self._id = id
        if L == None:
            self._emit = lambda *_: None
        else:
            self._emit = L.emit
    
    def _generalize(self, candidate):
        pass

    def generalize(self, candidate):
        # self._emit(self._id, "generalize", "input", candidate)
        res = self._generalize(candidate)
        # self._emit(self._id, "generalize", "output", res)
        return res