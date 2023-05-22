import logging

import product

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class IncompleteProduct(object):
    # TODO : Change main_product to no_monitors_product
    def __init__(self, automata, snb_messages):
        self._automata = automata
        self._non_monitors = [
            automaton for automaton in automata if not automaton.is_monitor]
        self._safety_monitors = [
            automaton for automaton in automata if automaton.is_safety]
        self._liveness_monitors = [
            automaton for automaton in automata if automaton.is_liveness]
        self._snb_messages = snb_messages

        self._main_product = None
        self._safety_products = None
        self._liveness_products = None

    @property
    def main_product(self):
        if self._main_product is None:
            self._main_product = product.Product(self._non_monitors)
        return self._main_product

    @property
    def liveness_products(self):
        if self._liveness_products is None:
            self._liveness_products = [
                product.Product(self._non_monitors + [monitor])
                for monitor in self._liveness_monitors]
        return self._liveness_products

    @property
    def safety_products(self):
        if self._safety_products is None:
            self._safety_products = [
                product.Product(self._non_monitors + [monitor])
                for monitor in self._safety_monitors]
        return self._safety_products

    # TODO: refactor this so that there aren't quadruple nested for loops
    def edge_sets_to_solve_snb_violation(self, blocking):
        automata_states = blocking.split(',')
        state_automaton_pairs = list(zip(automata_states, self._non_monitors))
        for state, automaton in state_automaton_pairs:
            for message in automaton.output_alphabet:
                neighbors = automaton.state_neighbors[state]
                if (message not in self._snb_messages 
                        or (message + "!") not in neighbors):
                    continue
                # automaton can send a message. We check that all who can
                # read the message either read it or are in output state.
                # TODO Make the following work for broadcast messages
                tmp = [
                    a for a in self._non_monitors 
                    if message in a.input_alphabet]
                if len(tmp) > 1:
                    raise ValueError(
                        "Strong non blockingness is only implemented"
                        " for non-broadcast messages.")
                for other_state, other_automaton in state_automaton_pairs:
                    if (message not in other_automaton.input_alphabet 
                            or (message + "?") in
                                other_automaton.state_neighbors[other_state] 
                            or other_automaton.is_output_state(other_state)):
                        continue
                    edges = []
                    candidates = other_automaton.candidate_edges_from_state(
                        other_state)
                    if not other_automaton.is_input_state(other_state):
                        output_candidates = [
                            c for c in candidates if c[1][-1] == "!"]
                        for _, output_message, end_state in output_candidates:
                            edges.append((other_automaton.name,
                                          other_state,
                                          output_message,
                                          end_state))
                    # The product state is blocking because there are not input
                    # transitions from other_state
                    for _, other_message, end in candidates:
                        if other_message == message + "?":
                            edges.append((other_automaton.name,
                                          other_state,
                                          other_message,
                                          end))
                    yield edges

    def __input_enabled_constraints(self, automaton, state, message):
        disjuncts = []
        if automaton.is_input_state(state):
            for _, label, end in automaton.candidate_edges_from_state(state):
                assert label.endswith('?'), ('There should not be write '
                                             'candidates from an input state.')
                if label == message + '?':
                    disjuncts.append((automaton.name, state, label, end))
        elif not automaton.is_output_state(state):
            # If the state is neither output nor input then either any of the
            # output candidate transitions has to be enabled to make the state
            # an output one, or one of the input message transitions to 
            #   directly
            # satisfy enabledness.
            for _, label, end in automaton.candidate_edges_from_state(state):
                if label.endswith('!'):
                    disjuncts.append((automaton.name, state, label, end))
                elif label == message + '?':
                    disjuncts.append((automaton.name, state, label, end))
        return disjuncts

    def input_enabled_constraints(self):
        conjuncts = []
        for automaton in self._automata:
            for message in automaton.input_enabled:
                for state in automaton.states():
                    conjuncts.append(
                        self.__input_enabled_constraints(
                            automaton, state, message))
        return conjuncts
