from synge.generalization import Generalizer

import product

class G0(Generalizer):
    
    def __init__(
            self, p, automata, snb, snb_messages, solver, **kwds) -> None:
        """The derived class implements _generalize. 
        This class takes care of initialization that is common across the 
        dist. protocol domain.
        """
        super().__init__(**kwds)

        self._p = p
        self._snb = snb
        self._snb_messages = snb_messages
        self._automata = automata

        self._solver = solver
        
        deadlock_product_automata = [
            a for a in p.automata if not a.is_monitor]
        self._main_product = product.Product(deadlock_product_automata)
        self._bad_state_predicates = p.bad_state_predicates
        if not self._bad_state_predicates:
            self._violates_bad_predicates = False
        self._equivalent_names = p.equivalent_names

        liveness_monitors = [a for a in p.automata if a.is_liveness]
        liveness_product_automata = [deadlock_product_automata + [a]
                                 for a in liveness_monitors]
        self._liveness_products = [
            product.Product(aa) for aa in liveness_product_automata]
            
        safety_monitors = [a for a in p.automata if a.is_safety]
        safety_product_automata = [
            deadlock_product_automata + [a] for a in safety_monitors]
        self._safety_products = [
            product.Product(aa) for aa in safety_product_automata]
