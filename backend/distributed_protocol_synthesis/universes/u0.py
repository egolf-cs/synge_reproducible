import itertools

import z3

from synge.universe import Universe

import util
import product
import incomplete_product
from helpers import (
    edges_that_solve_deadlock, 
    mk_determinism_constraints)

class U0(Universe):

    def __init__(
            self, p, automata, snb, snb_messages, solver, **kwds) -> None:
        """The derived class extends _prune.
        
        All other functions, esp. init, will almost always be inherited. 
        """
        super().__init__(**kwds)
        
        self._next = None
        self._is_empty_b = False
        self._solver = solver
        self._state = None

        # Initialize the state (of the candidate space, i.e., a prop formula)
        # 1. The set of boolean variables
        # TODO: what if the set of boolean variables is empty?
        for a in automata:
            for start, label, end in a.candidate_edges():
                self._solver.add_variable((a.name, start, label, end))
                if a in p.equivalent_automata:
                    b = p.equivalent_automata[1]
                    start2 = util.switch_strings(
                        start, p.equivalent_names[0], p.equivalent_names[1])
                    label2 = util.switch_strings(
                        label, p.equivalent_names[0], p.equivalent_names[1])
                    end2 = util.switch_strings(
                        end, p.equivalent_names[0], p.equivalent_names[1])
                    self._solver._associate_candidate_with_last_variable(
                        (b.name, start2, label2, end2))
        self._solver.update()

        # 2. Add constraints
        #   Initialize some auxiliary automata/products/variables
        liveness_monitors = [a for a in p.automata if a.is_liveness]
        deadlock_product_automata = [a for a in p.automata if not a.is_monitor]
        liveness_product_automata = [deadlock_product_automata + [a] 
            for a in liveness_monitors]
        main_product = product.Product(deadlock_product_automata)
        incomplete = incomplete_product.IncompleteProduct(
            p.automata, snb_messages)
        is_input_enabled = all(
            a.state_neighbors.get(state, {}).get(message + '?', []) != []
            for a in automata
            for message in a.input_enabled
            for state in a.states()
            if not a.is_output_state(state))
        liveness_products = [
            product.Product(aa) for aa in liveness_product_automata] 

        #   Now use them
        clauses = []
        det_clause = mk_determinism_constraints(self._solver, automata)
        clauses.append(det_clause)
        for d in main_product.deadlock_states():
            aux = {"enable" : edges_that_solve_deadlock(main_product, d)}
            expr1 = self._solver.mk_constraint(**aux)
            clauses.append(expr1)
        if snb:
            tmp2 = sorted(incomplete.main_product.strong_blocking_states(
                snb_messages))
            for b in tmp2:
                tmp = incomplete.edge_sets_to_solve_snb_violation(b)
                for edges in tmp:
                    aux = {"enable" : edges}
                    expr2 = self._solver.mk_constraint(**aux)
                    clauses.append(expr2)
        if not is_input_enabled:
            for clause in incomplete.input_enabled_constraints():
                if len(clause) > 0:
                    aux = {"enable" : clause}
                    expr3 = self._solver.mk_constraint(**aux)
                    clauses.append(expr3)
        if (len(main_product.deadlock_states()) == 0 
                and (not snb 
                    or len(main_product.strong_blocking_states(
                        snb_messages)) == 0) 
                and is_input_enabled):
            for liveness_product in liveness_products:
                liveness_product = product.Product(liveness_product.automata)
                for cycle in liveness_product.strong_fair_cycles():
                    if len(cycle) == 1 or cycle[-1] != cycle[0]:
                        cycle += [cycle[0]]
                    x = liveness_product.candidates_to_make_cycle_unfair(cycle)
                    aux = {"enable" : x}
                    expr4 = self._solver.mk_constraint(**aux)
                    clauses.append(expr4)

        self._state = self._solver.And(clauses)
        self._solver.add(self._state)


    def _pick(self):
        self._mk_next()
        # self._emit(self._id, "_pick", "picked from", self.get_state())
        return self._is_empty_b, self._next

    def _mk_next(self):
        self._next = self._solver.solve()
        if not self._next:
            self._is_empty_b = True

    def _mk_expr_str(self, expr):
        return self._solver.mk_str(self._solver.simplify(expr))

    def get_state(self):
        # return self._solver.mk_str(self._state)
        return

    def set_state(self, expr):
        self._state = expr

