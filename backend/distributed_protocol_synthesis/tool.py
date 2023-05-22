import argparse
import logging
import sys
import time
from pathlib import Path

import parser_1
import product
import driver
from logger import BasicLogger

def default_input_file_parsing(args):
    print("Parsing file {}".format(args.input_filename[0]))

    automata, strong_non_blocking_messages = parser_1.parse(
        args.input_filename[0])

    system = product.Product(automata)
    return automata, system, strong_non_blocking_messages

def synthesize(args):
    now = time.time()

    print("pre-parse in tool.py")
    automata, system, strong_non_blocking_messages = \
        default_input_file_parsing(args)
    print("post-parse in tool.py")
    if args.solver is None:
        solver_type = "z3"
    else:
        solvers = [
            "z3dead",
            "z3",
            "z3perm",
            "z3naive",
        ]
        if args.solver not in solvers:
            print("Invalid solver type.")
            print("Choose one in %s" % ', '.join(solvers))
            sys.exit(1)
        solver_type = args.solver
    if args.debug:
        logging.getLogger("cegis").setLevel(logging.DEBUG)
        logging.getLogger("cegis_solver").setLevel(logging.DEBUG)
        logging.getLogger("incomplete_product").setLevel(logging.DEBUG)

    print("pre-cegis.synthesize in tool.py")

    commit_path = Path("../../.git/refs/heads/main")
    commit_path = open(commit_path, "r")
    commit = commit_path.read()
    commit_path.close()

    incomplete_automata = [(a.name, a.state_neighbors) for a in automata]

    L = BasicLogger(str(now).replace(".","-"))
    L.emit("tool", "synthesize", "start time", now)
    L.emit("tool", "synthesize", "args", args)
    L.emit("tool", "synthesize", "commit", commit)
    L.emit("tool", "synthesize", "incomplete automata", incomplete_automata)
    result = driver.synthesize(
        system, solver_type, sys.stdout, args.seed, args.dead, L, 
        now,
        snb=args.snb,
        snb_messages=strong_non_blocking_messages, all=args.all,
        automata=automata, fname=args.input_filename[0])
    end_time = time.time()
    L.emit("tool", "synthesize", "end time", end_time)
    L.emit("tool", "synthesize", "total time", end_time - now)

def printcandidates(args):
    automata, _, _ = default_input_file_parsing(args)
    for a in automata:
        print(a.name)
        print(a.candidate_edges())

def print_dead_transitions(args):
    automata, system, _ = default_input_file_parsing(args)
    for automaton, transitions in system.dead_automata_transitions().items():
        print('Dead transitions for automaton: {}'.format(automaton))
        for transition in transitions:
            print(transition)

def main():
    main_arg_parser = argparse.ArgumentParser(prog='tool.py')
    subparsers = main_arg_parser.add_subparsers()

    synthesize_parser = subparsers.add_parser(
        'synthesize',
        help="Synthesize incomplete protocol given in input file.")
    synthesize_parser.add_argument(
        'input_filename', nargs=1,
        help="File with automata spec.")
    synthesize_parser.add_argument(
        "-snb", action='store_true',
         help="Add as a requirement that the result is strongly non-blocking.")
    synthesize_parser.add_argument(
        "-all", action='store_true',
        help="Add to produce all solutions.")

    synthesize_parser.add_argument(
        "-pa", action='store_true',
        help=('Add to print complete process automata'
            'in the end, when asking for one solution.'))
    synthesize_parser.add_argument(
        '-debug', action='store_true',
        help='Add to enable debug logging.')
    synthesize_parser.add_argument(
        '-seed', type=int, default=0,
        help='Random seed used by the z3 solver. Default is 0.')
    synthesize_parser.add_argument(
        '-dead', action='store_true',
        help='Check if transitions are taken in product or are "dead code".')

    help_solver_type = (
        "Default solver is z3minimum. Other options are "
        "gurobi, z3, z3rel, z3manmin, z3opt, crypto")
    synthesize_parser.add_argument("-s", "--solver", help=help_solver_type)
    synthesize_parser.set_defaults(func=synthesize)

    printcandidates_parser = subparsers.add_parser(
        'printcandidates',
        help="Print candidates of incompletet protocol given in input file.")
    printcandidates_parser.add_argument(
        'input_filename', nargs=1,
        help="File with automata spec.")
    printcandidates_parser.set_defaults(func=printcandidates)

    print_dead_transitions_parser = subparsers.add_parser(
        'printdeadtransitions',
        help=(
            "Print dead transitions of automata when in product given in input" 
            "file."))
    print_dead_transitions_parser.add_argument(
        'input_filename', nargs=1,
        help="File with automata spec.")
    print_dead_transitions_parser.set_defaults(func=print_dead_transitions)

    args = main_arg_parser.parse_args()
    
    try:
        func = args.func
    except AttributeError:
        main_arg_parser.error("too few arguments")
    func(args)


if __name__ == '__main__':
    main()
