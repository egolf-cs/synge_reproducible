"""
TODO: Make current fair_cycles process_fair_cycles
TODO: Make no fairness assumption liveness cycles function
TODO: Fix fair cycles algorithm: remove states from which X is enabled, if X 
    in enabled / taken
TODO: Check if local deadlock can simply be checked on product automaton 
    transitions
TODO: Fix state receptiveness
"""

import itertools
import collections
import networkx

import automaton
import util




class Product(automaton.Automaton):
    def __init__(self, automata, **kwargs):
        initial_state = ','.join([p.initial_state for p in automata])
        super(Product, self).__init__(
            automata=automata, initial_state=initial_state)
        self.automata = automata
        self.process_automata = [a for a in automata if not a.is_environment]
        process_automata_names = [a.name for a in self.process_automata]
        equivalent_automata = self._mk_equivalent_automata(
            process_automata_names)
        self.equivalent_automata = sorted(equivalent_automata)
        self.equivalent_names = []
        self.add_node(initial_state)
        self.bad_state_predicates = []
        self.monitor_indices, self.monitors = automaton.get_monitors(automata)
        self.non_monitor_indices = set(
            range(len(self.automata))).difference(self.monitor_indices)
        self.communicating_pairs = communicating_pairs(
            automata, self.monitor_indices)
        self.zip_indices_monitors = list(
            zip(self.monitor_indices, self.monitors))
        self.pair_transitions = product_state_pair_transitions(automata)
        self.message_to_monitors = collections.defaultdict(list)
        for mi, m in self.zip_indices_monitors:
            for message in m.input_alphabet:
                self.message_to_monitors[message].append((mi, m))
        frontier = set([initial_state])
        visited = set([])


        # print(" > frontier")
        while len(frontier) > 0:
            # print("Len frontier:", len(frontier))
            state = frontier.pop()
            visited.add(state)
            for successor, label in self.product_state_successors(state):
                # print(successor)
                self.add_edge(state, successor, label=label)
                if successor not in visited:
                    frontier.add(successor)
        # print(" < frontier")
        # assert(False)


        self.readers = collections.defaultdict(list)
        self.writer = dict()
        for a in self.automata:
            for m in a.input_alphabet:
                self.readers[m].append(a)
            for m in a.output_alphabet:
                self.writer[m] = a

    def _mk_equivalent_automata(self, process_automata_names):
        equivalent_automata = []
        for a in self.process_automata:
            tmp12 = util.switch_strings(a.name, "1", "2")
            tmp21 = util.switch_strings(a.name, "2", "1")
            if ("1" in a.name and tmp12 in process_automata_names 
                    or "2" in a.name and tmp21 in process_automata_names):
                equivalent_automata.append(a)
        return equivalent_automata

    def add_automata_edges_by_name(self, edges, all_out_strong = False):
        for auto_name, source, label, target in edges:
            a = self.automaton_by_name(auto_name)
            a.add_edge(source, target, label=label)
            if all_out_strong:
                tmp = [b+"!" for b in a.output_alphabet]
                if label in tmp:
                    if not hasattr(a, 'strong_fairness_transitions'):
                        a.strong_fairness_transitions = []
                    new_strng = (source, label, target)
                    a.strong_fairness_transitions += [new_strng]
        self.__init__(self.automata)

    def remove_automata_edges_by_name(self, edges):
        for auto_name, source, label, target in edges:
            self.automaton_by_name(auto_name).remove_edge_with_label(
                source, target, label)

    def automaton_by_name(self, name):
        return next(a for a in self.automata if a.name == name)

    def automaton_index_by_name(self, name):
        tmp = [(i, a) for i, a in enumerate(self.automata) if a.name == name]
        if tmp is []:
            return None
        else:
            return tmp[0]

    def automaton_state(self, a, state):
        if isinstance(a, automaton.Automaton):
            a = a.name
        return state.split(',')[self.automaton_index_by_name(a)[0]]

    def candidates_to_make_cycle_unfair(self, cycle):
        candidates = set([])
        fair_transitions = self.strong_fair_transitions()
        enabled = self.enabled_transitions_in_subgraph(cycle, fair_transitions)
        taken = self.taken_transitions_in_subgraph(cycle, fair_transitions)
        fair_not_enabled = set.difference(set(fair_transitions), set(taken))
        for state in cycle:
            automata_states = state.split(',')
            for b, transition in fair_not_enabled:
                start, label, end = transition
                b_index = self.automata.index(b)
                b_state = automata_states[b_index]
                if start == b_state:
                    decoration = '!' if label[-1] == '?' else '?'
                    matching_label = label[:-1] + decoration
                    for a in self.automata:
                        if a.is_environment:
                            continue
                        if (not (label[:-1] in a.input_alphabet 
                                or label[:-1] in a.output_alphabet)):
                            continue
                        astate = self.automaton_state(a, state)
                        cand_edges = a.candidate_edges_from_state(astate)
                        for source, label, target in cand_edges:
                            if label == matching_label:
                                candidates.add((a.name, source, label, target))
        return candidates

    def deadlock_states(self):
        return list(self.deadlock_states_iter())

    def deadlock_states_iter(self):
        for d in super(Product, self).deadlock_states_iter():
            if any(d.split(',')[i] != 'final'
                   for i, a in enumerate(self.automata)
                   if not a.is_environment):
                yield d

    def dead_automata_transitions(self):
        dead_transitions = dict()
        for automaton in self.automata:
            dead_transitions[automaton] = set()
            for start, end, data in automaton.edges(data=True):
                dead_transitions[automaton].add((start, data['label'], end))
        for state in self.states():
            for message, neighbors in self.state_neighbors[state].items():
                for next_state in neighbors:
                    automata_states = state.split(',')
                    next_automata_states = next_state.split(',')
                    for i, automaton in enumerate(self.automata):
                        label = None
                        if message in automaton.input_alphabet:
                            label = message + '?'
                        if message in automaton.output_alphabet:
                            label = message + '!'
                        if label is not None:
                            transition = (
                                automata_states[i], 
                                label, 
                                next_automata_states[i])
                            if transition in dead_transitions[automaton]:
                                dead_transitions[automaton].remove(transition)
        return dead_transitions

    def enabled_transitions_in_subgraph(self, subgraph, transitions):
        enabled = set([])
        for state in subgraph:
            for successor, message in self.product_state_successors(state):
                readers = self.readers[message]
                for reader in readers:
                    reader_index = self.automata.index(reader)
                    reader_start_state = state.split(',')[reader_index]
                    reader_end_state = successor.split(',')[reader_index]
                    if any(v['label'] == message + '?'
                            for _, v in reader.get_edge_data(
                                reader_start_state, reader_end_state).items()):
                        guard = (
                            reader, 
                            (reader_start_state, message + '?', 
                                reader_end_state))
                        if guard in transitions:
                            enabled.add(guard)
                writer = self.writer[message]
                writer_index = self.automata.index(writer)
                writer_start_state = state.split(',')[writer_index]
                writer_end_state = successor.split(',')[writer_index]
                if any(v['label'] == message + '!'
                        for _, v in writer.get_edge_data(
                            writer_start_state, writer_end_state).items()):
                    guard2 = (
                        writer, 
                        (writer_start_state, 
                            message + '!', writer_end_state))
                    if guard2 in transitions:
                        enabled.add(guard2)
        return enabled

    def taken_transitions_in_subgraph(self, subgraph, transitions):
        taken = set([])
        for state in subgraph:
            for successor, message in self.product_state_successors(state):
                if successor not in subgraph:
                    continue
                readers = self.readers[message]
                for reader in readers:
                    reader_index = self.automata.index(reader)
                    reader_start_state = state.split(',')[reader_index]
                    reader_end_state = successor.split(',')[reader_index]
                    if any(v['label'] == message + '?'
                            for _, v in reader.get_edge_data(
                                reader_start_state, reader_end_state).items()):
                        guard3 = (
                            reader, 
                            (reader_start_state, 
                                message + '?', 
                                reader_end_state))
                        if guard3 in transitions:
                            taken.add(guard3)
                writer = self.writer[message]
                writer_index = self.automata.index(writer)
                writer_start_state = state.split(',')[writer_index]
                writer_end_state = successor.split(',')[writer_index]
                if any(v['label'] == message + '!'
                        for _, v in writer.get_edge_data(
                            writer_start_state, writer_end_state).items()):
                    guard4 = (
                        writer, 
                        (writer_start_state, 
                            message + '!', 
                            writer_end_state))
                    if guard4 in transitions:
                        taken.add(guard4)
        return taken

    def get_automata_edges(self, product_state1, label, product_state2):
        automata_states1 = product_state1.split(',')
        automata_states2 = product_state2.split(',')
        differing_indices = [
            i for i, a in enumerate(self.automata)
            if ((label in a.input_alphabet or label in a.output_alphabet)
                and not a.is_monitor)]
        assert len(differing_indices) == 2
        index1, index2 = differing_indices
        neighbors = self.automata[index1].state_neighbors[
            automata_states1[index1]]
        if "%s?" % label in neighbors:
            send_index, receive_index = index2, index1
        else:
            send_index, receive_index = index1, index2
        result = (
            (self.automata[send_index], 
                (automata_states1[send_index], 
                label + "!", 
                automata_states2[send_index])),
            (self.automata[receive_index], 
                (automata_states1[receive_index], 
                label + "?", 
                automata_states2[receive_index])))
        return result

    def get_automata_edges_without_label(self, product_state1, product_state2):
        automata_states1 = product_state1.split(',')
        automata_states2 = product_state2.split(',')
        label = None
        for label2, neighbors in self.state_neighbors[product_state1].items():
            if product_state2 in neighbors:
                label = label2
                break
        assert label
        differing_indices = [
            i for i, a in enumerate(self.automata)
            if ((label in a.input_alphabet or label in a.output_alphabet)
                and not a.is_monitor)]
        assert len(differing_indices) == 2
        index1, index2 = differing_indices
        neighbors = self.automata[index1].state_neighbors[
            automata_states1[index1]]
        if "%s?" % label in neighbors:
            send_index, receive_index = index2, index1
        else:
            send_index, receive_index = index1, index2
        result = (
            (self.automata[send_index], 
                (automata_states1[send_index], 
                label + "!", 
                automata_states2[send_index])),
            (self.automata[receive_index], 
                (automata_states1[receive_index], 
                label + "?", 
                automata_states2[receive_index])))
        return result

    def is_state_strongly_non_blocking(self, state, messages):
        """Checks if a state is strongly non-blocking with respect to messages.
        Specifically it checks that, for every individual automaton, if there 
        is
        an output transition on one of the messages (locally) then for every
        other automaton that can read that message, either it is in an output
        state or it has an input transition leaving the state.

        Args:
          - state: product state as a comma separated string to check if it is
            strongly non-blocking.
          - messages: list of messages on which strong non-blockingness is to 
            be checked.
        """
        automata_states = state.split(',')
        for state, automaton in zip(automata_states, self.automata):
            for message in automaton.output_alphabet:
                if message not in messages:
                    continue
                if (message + "!") not in automaton.state_neighbors[state]:
                    continue
                # automaton can send a message. We check that all who can
                # read the message are either in output state
                for other_state, other_automaton in zip(automata_states,
                                                        self.automata):
                    if message not in other_automaton.input_alphabet:
                        continue
                    if ((message + "?") not in
                        other_automaton.state_neighbors[other_state] and
                        not other_automaton.is_output_state(other_state)):
                        return False
        return True

    def strong_blocking_states(self, messages):
        return [state for state in self.states()
                if not self.is_state_strongly_non_blocking(state, messages)]

    def strong_fair_transitions(self):
        result = []
        for a in self.automata:
            if not hasattr(a, 'strong_fairness_transitions'):
                continue
            for transition in a.strong_fairness_transitions:
                result.append((a, transition))
        return result

    def strong_fair_cycles(self):
        return list(self.strong_fair_cycles_iter())

    def strong_fair_cycles_iter(self):
        graph = networkx.DiGraph()
        for node in self.nodes():
            graph.add_node(node)
        for edge in self.edges(data=True):
            graph.add_edge(*edge[:-1], **edge[-1])
        sccs_to_check_aux = networkx.strongly_connected_components(graph)
        sccs_to_check = [graph.subgraph(c) for c in sccs_to_check_aux]
        fair_transitions = self.strong_fair_transitions()
        while sccs_to_check:
            scc = sccs_to_check.pop()
            if networkx.is_frozen(scc):
                scc = networkx.DiGraph(scc)
            # discard single node scc's with no self loop
            if len(scc) == 1:
                the_node = list(scc.nodes())[0]
                if the_node not in self.neighbors(the_node):
                    continue
            initial_state = next((state for state in scc
                                  if self.is_liveness_accepting(state)), None)
            if initial_state is None:
                continue
            enabled = self.enabled_transitions_in_subgraph(
                scc, fair_transitions)
            taken = self.taken_transitions_in_subgraph(scc, fair_transitions)
            assert set.issubset(taken, enabled)
            if enabled != taken:
                # remove any state from which an enabled local transition is 
                #   not taken
                nodes_to_remove = []
                for enabled_transition in set.difference(enabled, taken):
                    for node in scc:
                        subgraph = self.enabled_transitions_in_subgraph(
                            [node], fair_transitions)
                        if enabled_transition in subgraph:
                            nodes_to_remove.append(node)
                    for node in nodes_to_remove:
                        if node in scc:
                            scc.remove_node(node)
                more_to_check_aux = networkx.strongly_connected_components(scc)
                more_to_check = [scc.subgraph(c) for c in more_to_check_aux]
                sccs_to_check += more_to_check
                continue
            transitions_to_cover = list(taken)
            path = [initial_state]
            while transitions_to_cover:
                transition = transitions_to_cover.pop()
                edge = next(
                    edge for edge in scc.edges()
                    if transition in self.taken_transitions_in_subgraph(
                        edge, fair_transitions))
                path += networkx.shortest_path(scc, path[-1], edge[0])[1:]
                path += [edge[1]]
                for transition in self.taken_transitions_in_subgraph(
                        path, fair_transitions):
                    if transition in transitions_to_cover:
                        transitions_to_cover.remove(transition)
            if len(path) == 1:
                if path[0] in self.successors(path[0]):
                    yield path
                else:
                    other_state = next(
                        v for v in self.successors(initial_state) if v in scc)
                    result = (
                        [initial_state] + networkx.shortest_path(
                            scc, other_state, initial_state))
                    yield result
            else:
                yield path + networkx.shortest_path(
                    scc, path[-1], initial_state)[1:-1]

    def product_state_successors(self, product_state, verbose=False):
        return list(
            self.product_state_successors_iter(product_state, verbose=verbose))

    def product_state_successors_iter(self, product_state, verbose=False):
        """Given a state of the product automaton, i.e., a comma joined
           sequence of states, it returns a list of successor product
           states.
        """

        automata_states = product_state.split(',')
        for i1, i2 in self.communicating_pairs:
            pairs = self.pair_transitions.get(
                ((automata_states[i1], i1), (automata_states[i2], i2)), [])
            for s1, s2, message in pairs:
                if verbose:
                    print(s1, s2, message)
                new_automata_states = list(automata_states)
                new_automata_states[i1] = s1
                new_automata_states[i2] = s2

                matching_monitor_indices = []
                matching_monitor_successors = []

                for monitor_message in [message]:
                    for mi, m in self.message_to_monitors[monitor_message]:
                        neighbors = m.state_neighbors[automata_states[mi]]
                        m_derived = neighbors.get(
                            monitor_message + "?", [automata_states[mi]])
                        matching_monitor_successors.append(m_derived)
                        matching_monitor_indices.append(mi)

                prod = itertools.product(*matching_monitor_successors)
                if matching_monitor_successors != []:
                    for monitor_successor_states in prod:
                        new_new_automata_states = list(new_automata_states)
                        z = zip(
                            matching_monitor_indices, monitor_successor_states)
                        for mi, mss in z:
                            new_new_automata_states[mi] = mss
                        new_product_state = ','.join(new_new_automata_states)
                        yield (new_product_state, message)

                if matching_monitor_successors == []:
                    yield (','.join(new_automata_states), message)

    def is_safe(self):
        bs = [not self.is_safety_violating(state) for state in self.nodes()]
        return all(bs)

    def is_safety_violating(self, product_state):
        return any(m.is_safety and product_state.split(',')[i] == 'error'
                   for i, m in self.zip_indices_monitors)

    def is_liveness_accepting(self, product_state):
        automata_states = product_state.split(',')
        for i, m in self.zip_indices_monitors:
            if m.is_liveness:
                if (m.is_accepting(automata_states[i]) and
                        not self.is_safety_violating(product_state)):
                    return True
        return False

    def print_automata_names(self):
        print(','.join([a.name for a in self.automata]))

    def print_trace_to_state(self, target_state):
        state, predecessors = self.bfs_to_state(lambda s: s == target_state)
        assert state
        added_transitions = []
        output = []
        while state != self.initial_state:
            output.insert(0, state)
            previous_state, label = predecessors[state]
            write_transition, read_transition = self.get_automata_edges(
                previous_state, label, state)
            for transition in [read_transition, write_transition]:
                transition = (
                    transition[0].name,
                    transition[1][0], 
                    transition[1][1], 
                    transition[1][2])
                output.insert(0, transition)
            state = previous_state
        output.insert(0, state)
        for o in output:
            print(o)

    def print_strong_blockingness_reason(self, state, messages):
        automata_states = state.split(',')
        for state, automaton in zip(automata_states, self.automata):
            for message in automaton.output_alphabet:
                if message not in messages:
                    continue
                if (message + "!") not in automaton.state_neighbors[state]:
                    continue
                # automaton can send a message. We check that all who can
                # read the message are either in output state
                for other_state, other_automaton in zip(automata_states,
                                                        self.automata):
                    if message not in other_automaton.input_alphabet:
                        continue
                    if ((message + "?") not in
                        other_automaton.state_neighbors[other_state] and
                        not other_automaton.is_output_state(other_state)):
                        print("Automaton %s in state %s wants to send %s but "
                              "automaton %s in state %s is not reading it." %
                              (automaton.name, state, message,
                               other_automaton.name, other_state))

    def print_path(system, path_of_states):
        assert len(path_of_states) > 1
        previous_state = path_of_states[0]
        print(previous_state)
        for state in path_of_states[1:]:
            wo_lab = system.get_automata_edges_without_label(
                previous_state, state)
            write_transition, read_transition = wo_lab 
            for transition in [read_transition, write_transition]:
                print (transition[0].name,
                       transition[1][0], transition[1][1], transition[1][2])
            print(state)
            previous_state = state


def product_state_pair_transitions(automata):
    """ Returns a dictionary that maps pairs of individual automata states to 
    list of successor states.
        The keys of the dictionary are of the form ((s1 state of A_i, i), (s2 
        state of A_j, j))
        The values are lists with elements of the form (s1' state of A_i, s2' 
        state of A_j, message)
        where s1', s2' are the successors of s1, s2 on transitions with labels 
        message! and message? respectively.
        Monitors are ignored for now.
    """
    d = collections.defaultdict(list)
    monitor_indices, monitors = automaton.get_monitors(automata)
    automata_indices = list(range(len(automata)))
    for mi in monitor_indices:
        automata_indices.remove(mi)
    for i1, i2 in itertools.product(automata_indices, repeat=2):
        a1, a2 = automata[i1], automata[i2]
        isect = set(a1.output_alphabet).intersection(set(a2.input_alphabet))
        if len(isect) > 0:
            for s1, s2 in itertools.product(a1.states(), a2.states()):
                for e1, e2 in itertools.product(
                    set(a1.outgoing_labels(s1)), set(a2.outgoing_labels(s2))):
                    if e1[:-1] == e2[:-1] and e1[-1] == "!" and e2[-1] == "?":
                        message = e1[:-1]
                        prod = itertools.product(
                            a1.state_neighbors[s1]["{0}!".format(message)],
                            a2.state_neighbors[s2]["{0}?".format(message)])
                        for s1s, s2s in prod:
                            d[((s1, i1), (s2, i2))].append((s1s, s2s, message))
    return d


def communicating_pairs(automata, indices_to_ignore=None):
    result = communicating_pairs_iter(
        automata, indices_to_ignore=indices_to_ignore)
    return list(result)


def communicating_pairs_iter(automata, indices_to_ignore=None):
    """ automata is a list of automata.
        The function returns a list of pairs (i1, i2)
        such that automata[i1] and automata[i2] write and read some common 
        message
    """
    indices = list(range(len(automata)))
    if indices_to_ignore is not None:
        for i in indices_to_ignore:
            indices.remove(i)
    for i1, i2 in itertools.combinations(indices, 2):
        inter_aux = set(automata[i1].output_alphabet)
        inter = inter_aux.intersection(automata[i2].input_alphabet)
        if len(inter) > 0:
            yield (i1, i2)
        inter_aux = set(automata[i1].input_alphabet)
        inter = inter_aux.intersection(automata[i2].output_alphabet)
        if len(inter) > 0:
            yield (i2, i1)
