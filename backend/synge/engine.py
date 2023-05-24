import time

class Engine:

    def __init__(self, U, G, start_time, id=None, L=None) -> None:

        self._id = id
        if L == None:
            self._emit = lambda *_: None
        else:
            self._emit = L.emit

        self.U = U
        self.G = G

        self.max_time = 4*60*60
        self.start_time = start_time
        self.max_iter = None
        self.interrupt = False
        
        self.iter = 0
        self.sol = 0

    def keep_going(self, iter):
        now = time.time()
        b1 = not self.interrupt 
        b2 = self.max_iter is None or iter <= self.max_iter
        b3 = now - self.start_time >= self.max_time
        if b3:
            self._emit("self._id", "keep_going", "timeout", True)
        return b1 and b2 and (not b3)

    def generator(self):
        if self.max_iter is not None:
            print(f"WARN: limiting to {self.max_iter} iterations")
        while self.keep_going(self.iter):
            is_empty, cand = self._pick()
            self.iter += 1
            if is_empty:
                break
            cand_correct, gen = self._generalize(cand)
            if cand_correct:
                self.sol += 1
                self._emit(self._id, "generator", "solution", cand)
                yield cand
            self._prune(gen)
        self._emit(self._id, "generator", "total iteration", self.iter)
        self._emit(self._id, "generator", "num solutions", self.sol)

    
    def _pick(self):
        return self.U.pick()
    def _generalize(self, cand):
        return self.G.generalize(cand)
    def _prune(self, gen):
        self.U.prune(gen)

