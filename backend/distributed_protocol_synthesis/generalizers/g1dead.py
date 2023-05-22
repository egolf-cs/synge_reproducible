from pprint import pprint

from generalizers.g0 import G0

import product
import incomplete_product
from helpers import (
    generalize_reachability, 
    added_transitions_in_path, 
    edges_that_solve_deadlock)


class G1dead(G0):
    
    def __init__(
            self, p, automata, snb, snb_messages, solver, **kwds) -> None:
        super().__init__(p, automata, snb, snb_messages, solver, **kwds)

        self.num_iterations = 0

    def _generalize(self, candidate):

        new_transitions = candidate

        self.num_iterations += 1
        num_iterations = self.num_iterations
        results = []  
        
            
        self._main_product.add_automata_edges_by_name(new_transitions)

        self._incomplete = incomplete_product.IncompleteProduct(
            self._p.automata, self._snb_messages)

        self._safety_products = [product.Product(safety_product.automata) 
            for safety_product in self._safety_products]
        for sp in self._safety_products:
            sp.equivalent_names = self._equivalent_names

        deadlocks = self._main_product.deadlock_states()
        is_safe = all(safety_product.is_safe() 
            for safety_product in self._safety_products)
        blocking_states = []
        if self._snb:
            blocking_states = self._main_product.strong_blocking_states(
                self._snb_messages)

        removed_transitions = []
        if self._bad_state_predicates:
            aux = []
            for sp in self._safety_products:
                bs = []
                for a in sp.automata:
                    bs.append(hasattr(a, 'is_bad_predicate_monitor'))
                if any(bs):
                    aux.append(sp)
            bad_state_predicate_product = next(aux, self._main_product)

            bs2 = []
            for predicate in self._bad_state_predicates:
                for s in bad_state_predicate_product.states():
                    bs2.append(predicate(s))
            self._violates_bad_predicates = any(bs2)
            if self._violates_bad_predicates:
                for predicate in self._bad_state_predicates:
                    bs3 = [s for s in bad_state_predicate_product.states()]
                    bs3 = [predicate(s) for s in bs3]
                    if any(bs3):
                        bad_transitions = generalize_reachability(
                            bad_state_predicate_product, 
                            new_transitions, 
                            predicate)
                        results.append({"disable" : bad_transitions})
                        for t in bad_transitions:
                            removed_transitions.append(t)

        if not is_safe:
            for safety_product in self._safety_products:
                if safety_product.is_safe():
                    continue
                transitions = generalize_reachability(
                    safety_product, 
                    new_transitions, 
                    safety_product.is_safety_violating)
                results.append({"disable" : transitions})
        for d in deadlocks:
            disable_transitions = generalize_reachability(
                self._main_product, new_transitions, lambda s: s == d)
            bs4 = [
                t not in removed_transitions for t in disable_transitions]
            if all(bs4):
                enable_transitions = edges_that_solve_deadlock(
                    self._main_product, d)
                results.append(
                    {"enable" : enable_transitions,
                    "disable" : disable_transitions})

        for b in blocking_states:
            disable_transitions = generalize_reachability(
                self._main_product, new_transitions, lambda s: s == b)
            bs5 = [
                t not in removed_transitions for t in disable_transitions]
            if all(bs5):
                aux1 = self._incomplete.edge_sets_to_solve_snb_violation(b)
                for edges in aux1:
                    results.append(
                        {"enable" : edges,
                        "disable" : disable_transitions})

        is_live = None
        is_correct = (
            deadlocks == [] 
            and len(blocking_states) == 0 
            and is_safe 
            and not self._violates_bad_predicates)
        if is_correct:
            is_live = True
            for liveness_product in self._liveness_products:
                liveness_product = product.Product(
                    liveness_product.automata)
                cycles = liveness_product.strong_fair_cycles()
                for cycle in cycles:
                    is_live = False
                    edges_to_reach_cycle = generalize_reachability(
                        liveness_product, 
                        new_transitions, 
                        lambda state: state in cycle)
                    if len(cycle) == 1 or cycle[-1] != cycle[0]:
                        cycle += [cycle[0]]
                    edges_to_repeat_cycle = added_transitions_in_path(
                        liveness_product, new_transitions, cycle)
                    x = liveness_product.candidates_to_make_cycle_unfair(
                        cycle)
                    edges_to_exclude = (
                        edges_to_reach_cycle + edges_to_repeat_cycle)
                    results.append(
                        {"enable" : x,
                        "disable" : edges_to_exclude})
            if is_live:
                results.append(
                    {"disable" : new_transitions})

        if is_live is not None:
            is_correct = is_correct and is_live
            
        clauses = [self._solver.mk_constraint(**r) for r in results]
        expr = self._solver.And(clauses)
        neg_expr = self._solver.Not(expr)
        # self._emit("G1", "_generalize", "mk_constraints out", None)

        self._main_product.remove_automata_edges_by_name(new_transitions)
        return is_correct, neg_expr