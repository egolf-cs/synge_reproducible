import itertools
import functools
import types
from pprint import pprint

def generalize_reachability(
        product_automaton, added_edges, bad_state_predicate):
    # Do a BFS to the error set
    state, predecessors = product_automaton.bfs_to_state(bad_state_predicate)
    assert state
    take_automaton_name = isinstance(added_edges[0][0], str)
    added_transitions = []
    path_len = 0
    while state != product_automaton.initial_state:
        path_len += 1
        previous_state, label = predecessors[state]
        aux = product_automaton.get_automata_edges(
            previous_state, label, state)
        write_transition, read_transition = aux
        for transition in [read_transition, write_transition]:
            transition = (
                transition[0].name if take_automaton_name 
                else 
                    transition[0],
                    transition[1][0],
                    transition[1][1],
                    transition[1][2])
            if transition in added_edges:
                added_transitions.append(transition)
        state = previous_state
    # print(path_len)
    return added_transitions

def generalize_reachability_alt(
        product_automaton, added_edges, bad_state_predicate):
    # Do a BFS to the error set
    state, predecessors = product_automaton.bfs_to_state(bad_state_predicate)
    assert state
    take_automaton_name = isinstance(added_edges[0][0], str)
    added_transitions = []
    path = []
    while state != product_automaton.initial_state:
        path.append(state)
        previous_state, label = predecessors[state]
        aux = product_automaton.get_automata_edges(
            previous_state, label, state)
        write_transition, read_transition = aux
        for transition in [read_transition, write_transition]:
            transition = (
                transition[0].name if take_automaton_name 
                else 
                    transition[0],
                    transition[1][0],
                    transition[1][1],
                    transition[1][2])
            if transition in added_edges:
                added_transitions.append(transition)
        state = previous_state
    path.append(state)
    # print(path_len)
    return added_transitions, path



def edges_that_solve_deadlock(p, deadlock):
    automata_states = deadlock.split(',')
    edges = []
    for i, a in enumerate(p.automata):
        if not a.is_environment:
            cand_edges = a.candidate_edges_from_state_iter(automata_states[i])
            cand_edges = list(cand_edges)
            # print("cand_edges", list(cand_edges))
            for start, label, end in cand_edges:
                message = label[:-1]
                if label.endswith('?'):
                    auta = enumerate(p.automata)
                    # This is a serious bug: non-environment processes can also
                    #   solve deadlocks?
                    # auta = [x for x in auta if x[1].is_environment]
                    # Even this isn't good enough:
                    auta = [x for x in auta if not x[1].is_monitor]
                    # Since there might be missing transitions that solve...
                    auta = [x for x in auta if message in x[1].output_alphabet]
                    neighbors = []
                    for i2, a2 in auta:
                        neigh = a2.state_neighbors.get(automata_states[i2], {})
                        neighbors.append(neigh)
                    bs = [n.get(message + "!", []) != [] for n in neighbors]
                    if any(bs):
                        edges.append((a.name, start, label, end))
                elif label.endswith('!'):
                    auta = enumerate(p.automata)
                    # auta = [x for x in auta if x[1].is_environment]
                    auta = [x for x in auta if not x[1].is_monitor]
                    auta = [x for x in auta if message in x[1].input_alphabet]
                    neighbors = []
                    for i2, a2 in auta:
                        neigh = a2.state_neighbors.get(automata_states[i2], {})
                        neighbors.append(neigh)
                    bs = [n.get(message + "?", []) != [] for n in neighbors]
                    if any(bs):
                        edges.append((a.name, start, label, end))
    return edges

def added_transitions_in_path(product_automaton, added_edges, path):
    added_transitions = []
    for state1, state2 in zip(path, path[1:]):
        aux = product_automaton.get_automata_edges_without_label(
            state1, state2)
        write_transition, read_transition = aux 
        for transition in [read_transition, write_transition]:
            transition = (
                transition[0].name,
                transition[1][0], 
                transition[1][1], 
                transition[1][2])
            if transition in added_edges:
                added_transitions.append(transition)
    return added_transitions

def add_determinism_constraints(solver, automata):
# determinism constraints
# TODO check if this is correct when output transitions are allowed.
    for a in automata:
        per_state_label_candidate_edges = {}
        for state1, label, state2 in a.candidate_edges():
            assert (a.name, state1, label, state2) in solver.candidates
            if (state1, label) not in per_state_label_candidate_edges:
                per_state_label_candidate_edges[(state1, label)] = []
            per_state_label_candidate_edges[(state1, label)].append(
                (a.name, state1, label, state2))
        solver.add_determinism_constraints(per_state_label_candidate_edges)

        # for a specific state, if there are both input and output candidates 
        #   leaving the state
        #   then a completion has to either pick output or input transitions
        for state in a.states():
            if (not a.is_input_state(state) 
                    and not a.is_output_state(state) 
                    and not 'final' in a.node[state]):
                input_candidates, output_candidates = [], []
                for start, label, end in a.candidate_edges_from_state(state):
                    if label.endswith('?'):
                        input_candidates.append((a.name, start, label, end))
                    elif label.endswith('!'):
                        output_candidates.append((a.name, start, label, end))
                solver.add_input_output_state_constraint(
                    input_candidates, output_candidates)

                # for a specific state, no two output transitions can be 
                #   enabled
                for candidate1, candidate2 in itertools.combinations(
                        output_candidates, 2):
                    solver.add_constraint(disable=[candidate1, candidate2])

def mk_determinism_constraints(solver, automata):
# determinism constraints
# TODO check if this is correct when output transitions are allowed.
    clauses = []
    for a in automata:
        per_state_label_candidate_edges = {}
        for state1, label, state2 in a.candidate_edges():
            assert (a.name, state1, label, state2) in solver.candidates
            if (state1, label) not in per_state_label_candidate_edges:
                per_state_label_candidate_edges[(state1, label)] = []
            per_state_label_candidate_edges[(state1, label)].append(
                (a.name, state1, label, state2))
        tmp = solver.mk_determinism_constraints(per_state_label_candidate_edges)
        clauses += tmp

        # for a specific state, if there are both input and output candidates 
        #   leaving the state
        #   then a completion has to either pick output or input transitions
        for state in a.states():
            if (not a.is_input_state(state) 
                    and not a.is_output_state(state) 
                    and not 'final' in a.nodes[state]):
                input_candidates, output_candidates = [], []
                for start, label, end in a.candidate_edges_from_state(state):
                    if label.endswith('?'):
                        input_candidates.append((a.name, start, label, end))
                    elif label.endswith('!'):
                        output_candidates.append((a.name, start, label, end))
                tmp = solver.mk_input_output_state_constraint(
                    input_candidates, output_candidates)
                clauses.append(tmp)

                # for a specific state, no two output transitions can be 
                #   enabled
                for candidate1, candidate2 in itertools.combinations(
                        output_candidates, 2):
                    tmp = solver.mk_constraint(disable=[candidate1, candidate2])
                    clauses.append(tmp)
    return solver.And(clauses)