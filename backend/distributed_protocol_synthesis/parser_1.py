import automaton
import os
import os.path
import sys
import ply.lex as lex
import ply.yacc as yacc


tokens = (
    'NAME',
    'SEND',
    'RECEIVE',
    'LEFT_BRACE',
    'RIGHT_BRACE',
    'LEFT_PAREN',
    'RIGHT_PAREN',
    'LEFT_BRACKET',
    'RIGHT_BRACKET',
    'COMMA',
    'EQUALS',
    'FILE',
    'INCLUDE',
    'LIVENESS',
    'SAFETY',
    'PROCESS',
    'ENVIRONMENT',
    'STRONG_FAIRNESS',
    'ACCEPTING',
    'OUTPUTS',
    'INPUTS',
    'STRONG_NON_BLOCKING',
    'STATES',
    'INPUT_STATES',
    'OUTPUT_STATES',
    'PERM_STATES',
    'INPUT_ENABLED',
)

# Tokens

t_SEND = r'!'
t_RECEIVE = r'\?'
t_LEFT_BRACE = r'\{'
t_RIGHT_BRACE = r'\}'
t_LEFT_BRACKET = r'\['
t_RIGHT_BRACKET = r'\]'
t_LEFT_PAREN = r'\('
t_RIGHT_PAREN = r'\)'
t_COMMA = r','
t_EQUALS = r'='
t_ignore_COMMENT = r'\/\/.*'
t_FILE = r'\"[^"]*\"'

reserved = {
    'include' : 'INCLUDE',
    'liveness' : 'LIVENESS',
    'safety' : 'SAFETY',
    'process' : 'PROCESS',
    'environment' : 'ENVIRONMENT',
    'strong_fairness' : 'STRONG_FAIRNESS',
    'accepting' : 'ACCEPTING',
    'inputs' : 'INPUTS',
    'outputs' : 'OUTPUTS',
    'strong_non_blocking' : 'STRONG_NON_BLOCKING',
    'states' : 'STATES',
    'input_states' : 'INPUT_STATES',
    'output_states' : 'OUTPUT_STATES',
    'perm_states' : 'PERM_STATES',
    'input_enabled' : 'INPUT_ENABLED',
}

def t_NAME(t):
    r'[a-zA-Z_][a-zA-Z0-9_\']*'
    t.type = reserved.get(t.value, 'NAME')
    return t

t_ignore = " \t"

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

automata = []

automata_definitions = {}

dirnames = []
filenames = []

file_texts = []

syntax_error = False
semantic_error = False

strong_non_blocking_messages = []

def find_column(token):
    input = file_texts[-1]
    last_cr = input.rfind('\n',0,token.lexpos)
    if last_cr < 0:
        last_cr = 0
    else:
        last_cr += 1
    return token.lexpos - last_cr + 1

def type_check(a, inputs, outputs, states, input_enabled):
    global semantic_error
    for input in a.input_alphabet:
        if input not in inputs:
            print("In automaton %s, message %s used in input transition but "
                  "not declared in inputs." % (a.name, input))
            semantic_error = True

    for output in a.output_alphabet:
        if output not in outputs:
            print("In automaton %s, message %s used in output transition but "
                  "not declared in outputs." % (a.name, output))
            semantic_error = True

    if states is not None:
        for state in a.states():
            if state not in states:
                print("In automaton %s, state %s is used but "
                      "not declared in states." % (a.name, state))
                semantic_error = True

    if input_enabled is not None:
        for message in input_enabled:
            if message not in inputs:
                print("In automaton %s, message %s used in input enabled spec "
                      "but not is not an input of the automaton." % (a.name,
                                                                     message))
                semantic_error = True

def p_automata(t):
    '''automata : include automata
                | function automata
                | definition automata
                | instantiation automata
                | strong_non_blocking automata
                | include
                | function
                | definition
                | instantiation
                | strong_non_blocking
                | error'''
    if t[1] is not None:
        automata.append(t[1])

def p_include(t):
    '''include : INCLUDE FILE'''
    filename = t[2][1:-1]
    included_file = os.path.join(dirnames[-1], filename)

    if not os.path.exists(included_file):
        print ("Filename %s included at %s does not exist." %
               (included_file, t.lineno(2)))
        sys.exit(1)
    dirnames.append(os.path.dirname(included_file))

    lexer = lex.lex()
    s = open(included_file, 'r').read()
    file_texts.append(s)
    parser = yacc.yacc()
    parser.parse(s, lexer=lexer, tracking=True)

    file_texts.pop()
    dirnames.pop()

def p_strong_non_blocking(t):
    '''strong_non_blocking : STRONG_NON_BLOCKING LEFT_BRACKET names RIGHT_BRACKET'''

    global strong_non_blocking_messages
    if len(strong_non_blocking_messages) > 0:
        print("Only one strongly non blocking specification is allowed per file %s." % t.lineno(0))
        sys.exit(1)
    strong_non_blocking_messages = t[3]
    t[0] = None

def p_definition(t):
    '''definition : PROCESS NAME inner
                  | ENVIRONMENT NAME inner
                  | LIVENESS NAME inner
                  | SAFETY NAME inner'''
    environment = t[1] == 'environment'
    monitor = t[1] == 'liveness' or t[1] == 'safety'
    liveness = t[1] == 'liveness'
    safety = t[1] == 'safety'
    spec = t[3]

    initial = spec['initial']
    accepting = spec.get('accepting', None)
    edges = spec['edges']

    a = automaton.Automaton(name=t[2],
                            initial_state=initial,
                            is_environment=environment,
                            is_monitor=monitor,
                            is_liveness=liveness,
                            is_safety=safety)
    for edge, is_strong_fair in edges:
        start, end, label = edge
        a.add_edge(start, end, label=label)
        if not hasattr(a, 'strong_fairness_transitions'):
            a.strong_fairness_transitions = []
        if is_strong_fair:
            a.strong_fairness_transitions.append((start, label, end))
        
        # DEREK ADDED: 
        if not (environment or monitor):
            if label[-1] == "?":
                a.set_input_state(start)
            if label[-1] == "!":
                a.set_output_state(start)

    if spec['states'] is not None:
        for state in spec['states']:
            if state not in a.states():
                a.add_state(state)

    if spec['input_states'] is not None:
        for state in spec['input_states']:
            if state not in a.states():
                a.add_state(state)
            a.set_input_state(state)

    if spec['output_states'] is not None:
        for state in spec['output_states']:
            if state not in a.states():
                a.add_state(state)
            a.set_output_state(state)

    if spec['perm_states'] is not None:
        for state in spec['perm_states']:
            if state not in a.states():
                a.add_state(state)
            a.set_perm_state(state)

    type_check(a, spec['inputs'], spec['outputs'], spec['states'],
               spec['input_enabled'])

    for input in spec['inputs']:
        if input not in a.input_alphabet:
            a.input_alphabet.append(input)
    for output in spec['outputs']:
        if output not in a.output_alphabet:
            a.output_alphabet.append(output)
    if accepting is not None:
        for state in accepting:
            a.make_accepting(state)

    if spec['input_enabled'] is not None:
        a.input_enabled = spec['input_enabled']

    t[0] = a

def p_inner(t):
    '''inner : LEFT_BRACE \
               optional_states \
               optional_input_states \
               optional_output_states \
               optional_perm_states \
               inputs \
               optional_input_enabled \
               outputs \
               initial optional_accepting \
               edges \
               RIGHT_BRACE
    '''
    inner_dict = {}
    inner_dict['states'] = t[2]
    inner_dict['input_states'] = t[3]
    inner_dict['output_states'] = t[4]
    inner_dict['perm_states'] = t[5]
    inner_dict['inputs'] = t[6]
    inner_dict['input_enabled'] = t[7]
    inner_dict['outputs'] = t[8]
    inner_dict['initial'] = t[9]
    inner_dict['accepting'] = t[10]
    inner_dict['edges'] = t[11]
    t[0] = inner_dict

def p_inputs(t):
    'inputs : INPUTS LEFT_BRACKET names RIGHT_BRACKET'
    t[0] = t[3]

def p_input_enabled(t):
    'optional_input_enabled : INPUT_ENABLED LEFT_BRACKET names RIGHT_BRACKET'
    t[0] = t[3]

def p_input_enabled_empty(t):
    'optional_input_enabled : '
    t[0] = None

def p_outputs(t):
    'outputs : OUTPUTS LEFT_BRACKET names RIGHT_BRACKET'
    t[0] = t[3]

def p_states(t):
    'optional_states : STATES LEFT_BRACKET names RIGHT_BRACKET'
    t[0] = t[3]

def p_states_empty(t):
    'optional_states : '
    t[0] = None

def p_input_states(t):
    'optional_input_states : INPUT_STATES LEFT_BRACKET names RIGHT_BRACKET'
    t[0] = t[3]

def p_input_states_empty(t):
    'optional_input_states : '
    t[0] = None

def p_output_states(t):
    'optional_output_states : OUTPUT_STATES LEFT_BRACKET names RIGHT_BRACKET'
    t[0] = t[3]

def p_output_states_empty(t):
    'optional_output_states : '
    t[0] = None

def p_perm_states(t):
    'optional_perm_states : PERM_STATES LEFT_BRACKET names RIGHT_BRACKET'
    t[0] = t[3]

def p_perm_states_empty(t):
    'optional_perm_states : '
    t[0] = None

def p_accepting(t):
    '''optional_accepting : ACCEPTING LEFT_BRACKET names RIGHT_BRACKET'''
    t[0] = t[3]

def p_accepting_empty(t):
    '''optional_accepting : '''
    t[0] = None


def instantiate_automaton(name, arguments, automaton_spec):
    parameters, spec, automaton_type = automaton_spec
    initial = spec['initial']
    accepting = spec.get('accepting', None)
    inputs = spec['inputs']
    outputs = spec['outputs']
    edges = spec['edges']

    environment = automaton_type == 'environment'
    monitor = (automaton_type == 'liveness' or
               automaton_type == 'safety')
    liveness = automaton_type == 'liveness'
    safety = automaton_type == 'safety'

    a = automaton.Automaton(name=name,
                            initial_state=initial,
                            is_environment=environment,
                            is_monitor=monitor,
                            is_liveness=liveness,
                            is_safety=safety)

    for edge, is_strong_fair in edges:
        start, end, label = edge
        found = False
        for parameter, argument in zip(parameters, arguments):
            if label[:-1] == parameter:
                found = True
                label = argument + label[-1]
                break
        a.add_edge(start, end, label=label)
        if not hasattr(a, 'strong_fairness_transitions'):
            a.strong_fairness_transitions = []
        if is_strong_fair:
            a.strong_fairness_transitions.append((start, label, end))
    if accepting is not None:
        for state in accepting:
            a.make_accepting(state)
    # TODO do type checking on instantiated automata
    for input in spec['inputs']:
        if input not in a.input_alphabet:
            a.input_alphabet.append(input)
    for output in spec['outputs']:
        if output not in a.output_alphabet:
            a.output_alphabet.append(output)
    if spec['states'] is not None:
        for state in spec['states']:
            if state not in a.states():
                a.add_state(state)

    return a

def p_instantiation(t):
    'instantiation : NAME EQUALS NAME LEFT_PAREN names RIGHT_PAREN'
    automaton_spec = automata_definitions.get(t[3], None)
    if automaton_spec is None:
        print("Automaton definition %s not found in line %s." % (t[3], t.lineno(3)))
        raise SyntaxError
    t[0] = instantiate_automaton(t[1], t[5], automaton_spec)

def p_function(t):
    '''function : PROCESS NAME LEFT_PAREN names RIGHT_PAREN inner
                | ENVIRONMENT NAME LEFT_PAREN names RIGHT_PAREN inner
                | LIVENESS NAME LEFT_PAREN names RIGHT_PAREN inner
                | SAFETY NAME LEFT_PAREN names RIGHT_PAREN inner
    '''
    automata_definitions[t[2]] = (t[4], t[6], t[1])

def p_names_many(t):
    'names : NAME COMMA names'
    t[0] = [t[1]] + t[3]

def p_names_single(t):
    '''names : NAME
             |'''
    t[0] = [] if len(t) == 1 else [t[1]]

def p_initial(t):
    'initial : NAME NAME'
    if t[1] != 'initial':
        raise SyntaxError
    t[0] = t[2]

def p_edges_many(t):
    'edges : edge edges'
    t[0] = [t[1]] + t[2]

def p_edges_empty(t):
    'edges : '
    t[0] = []

def p_edge(t):
    '''edge : NAME NAME SEND NAME
            | NAME NAME RECEIVE NAME'''
    t[0] = ((t[1], t[4], t[2] + t[3]), False)

def p_edge_with_strong_fairness(t):
    '''edge : NAME NAME SEND NAME STRONG_FAIRNESS
            | NAME NAME RECEIVE NAME STRONG_FAIRNESS'''
    t[0] = ((t[1], t[4], t[2] + t[3]), True)

def p_error(t):
    print("Syntax error at token %s, line %s and column %s" %
          (t.value, t.lexer.lineno, find_column(t)))
    global syntax_error
    syntax_error = True

def parse(filename):
    global strong_non_blocking_messages
    dirnames.append(os.path.dirname(filename))

    lexer = lex.lex()
    parser = yacc.yacc()

    file_texts.append(open(filename, 'r').read())

    parser.parse(file_texts[-1], lexer=lexer, tracking=True)

    global semantic_error
    global syntax_error

    if syntax_error:
        print("Error parsing model.")
        sys.exit(1)

    if semantic_error:
        print("Error interpreting model.")
        sys.exit(1)

    print("# automata read: {}".format(len(automata)))

    skip_drawing = False
    if os.path.exists('figures') and os.path.isdir('figures'):
        open('figures/temp.html', 'w').close()
    elif not os.path.exists('figures'):
        os.makedirs("figures")
    else:
        # figures exists and is not a folder
        skip_drawing = True
    if False and not skip_drawing:
        for a in automata:
            a.draw_to_file('figures/temp.html', append=True)

    for message in strong_non_blocking_messages:
        if not any(message in automaton.output_alphabet
                   for automaton in automata):
            print("Strong non blocking message %s is not in the output"
                  " alphabet of any automaton" % message)
            sys.exit(1)

    return automata, strong_non_blocking_messages


# if __name__ == '__main__':
#     main()
