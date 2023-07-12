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

def synthesize_aux(automata, args, system, solver_type, seed, snb, strong_non_blocking_messages, allb):
    now = time.time()

    print("pre-parse in tool.py")
    print("post-parse in tool.py")

    print("pre-cegis.synthesize in tool.py")

    # commit_path = Path("../../.git/refs/heads/main")
    commit_path = Path(".git/refs/heads/main")
    commit_path = open(commit_path, "r")
    commit = commit_path.read()
    commit_path.close()

    incomplete_automata = [(a.name, a.state_neighbors) for a in automata]

    L = BasicLogger(str(now).replace(".","-"))
    L.emit("tool", "synthesize", "start time", now)
    L.emit("tool", "synthesize", "args", args)
    L.emit("tool", "synthesize", "commit", commit)
    L.emit("tool", "synthesize", "incomplete automata", incomplete_automata)
    result, iter = driver.synthesize(
        system, solver_type, seed, L, 
        now,
        snb=snb,
        snb_messages=strong_non_blocking_messages, all=allb,
        automata=automata)
    end_time = time.time()
    L.emit("tool", "synthesize", "end time", end_time)
    L.emit("tool", "synthesize", "total time", end_time - now)

    return result, iter, end_time - now

def synthesize(args):
    automata, system, strong_non_blocking_messages = \
        default_input_file_parsing(args)
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

    synthesize_aux(automata, args, system, solver_type, args.seed, args.snb, strong_non_blocking_messages, args.all)

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

def mk_entry(args):

    if args.table_num in [1,2]:
        dir_suff = "dist"
    elif args.table_num in [4,5]:
        dir_suff = "non"
    elif args.table_num == 3:
        dir_suff = "dist_zero"
    elif args.table_num == 6:
        dir_suff = "non_zero"
    else:
        raise AssertionError(f"table_num must be in 1..6, but {args.table_num} is not.")
    
    if args.case_study not in ["ABP", "2PC"]:
        raise AssertionError(f"case_study must be ABP or 2PC, but {args.case_study} is not.")
    
    dir = f"backend/distributed_protocol_synthesis/examples/{args.case_study}_{dir_suff}"

    if args.case_study == "ABP":
        file_pref = "snd-"
    else:
        file_pref = ""

    input_filename = f"{dir}/{file_pref}{args.states}.txt"
    automata, strong_non_blocking_messages = parser_1.parse(input_filename)
    system = product.Product(automata)

    if args.algorithm == "unopt":
        solver_type = "z3dead"
    elif args.algorithm == "dead":
        solver_type = "z3"
    elif args.algorithm == "naive":
        solver_type = "z3naive"
    elif args.algorithm == "perm":
        solver_type = "z3perm"
    else:
        raise AssertionError(
            f"algorithm must be unopt, dead, naive, or perm; "
            "but {args.algorithm} is not.")
    
    if args.table_num in [1, 3, 4, 6]:
        seed = 0
    else:
        seed = args.seed
        if seed is None:
            raise AssertionError(
                f"seed must be specified since "
                "table_num={args.table} is 2 or 5")

    if args.table_num in [1, 4]:
        allb = True
    else:
        allb = False

    results, iter, delta_time = synthesize_aux(
        automata, args, system, solver_type, seed, 
        None, strong_non_blocking_messages, allb)
    
    print(f"Results for {args}")
    print(f"num_solutions={len(results)}\tnum_iterations={iter}\telapsed_time={delta_time}")


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
        '-seed', type=int, default=0,
        help='Random seed used by the z3 solver. Default is 0.')

    help_solver_type = (
        "Default solver is z3. Other options are "
        "gurobi, z3naive, z3perm, z3dead")
    synthesize_parser.add_argument("-s", "--solver", help=help_solver_type)
    synthesize_parser.set_defaults(func=synthesize)

    entry_parser = subparsers.add_parser(
        'entry',
        help="Reproduce an entry in the table."
    )
    entry_parser.add_argument(
        'table_num', type=int,
        help="A number 1-6 corresponding to a table from the paper."
    )
    entry_parser.add_argument(
        'case_study',
        help="2PC | ABP"
    )
    entry_parser.add_argument(
        'states',
        help=("A string of digits corresponding to the states in the A column of the table."
              " E.g. if case_study=ABP, then states=12 correspondes to the row with header ABP;{s1,s2}"
        )
    )
    entry_parser.add_argument(
        'algorithm',
        help="unopt | dead | naive | perm"
    )
    entry_parser.add_argument(
        '-seed', type=int, default=None,
        help=(
            "This is specified if and only if the table number is 2 or 5." 
            " seed must be a value in 0..9."
            " The entry reported in the table is an average of the times" 
            " returned using all 10 of these seeds."
        )
    )
    entry_parser.set_defaults(func=mk_entry)

    args = main_arg_parser.parse_args()
    print(args)
    
    try:
        func = args.func
    except AttributeError:
        main_arg_parser.error("too few arguments")
    func(args)



if __name__ == '__main__':
    main()
