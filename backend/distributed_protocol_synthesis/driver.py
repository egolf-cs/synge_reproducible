# TODO: fix this import mechanism
import os, sys
x = os.path.realpath(__file__)
y = os.path.dirname(x)
y = os.path.dirname(y)
sys.path.append(y)



from solvers.z3 import Z3Solver
from synge.engine import Engine
from universes.u1 import U1
from generalizers.g1 import G1
from generalizers.g1dead import G1dead
from generalizers.g_perm import G_perm
from generalizers.g_naive import G_naive

def synthesize(
        p, solver_type, solutions_file, seed, print_dead_annotation, L,
        start_time,
        snb=False, snb_messages=[], all=False, automata=None, fname=None):

    solver = Z3Solver(random_seed=seed)
    L.emit_content = True

    args_u = [p, automata, snb, snb_messages, solver]
    kwds_u = {"id" : "U1", "L" : L}
    args_g = [p, automata, snb, snb_messages, solver]
    u = U1(*args_u, **kwds_u)
    if "dead" in solver_type:
        kwds_g = {"id" : "G1dead", "L" : L}
        g_unopt = G1dead(*args_g, **kwds_g)
    else:
        kwds_g = {"id" : "G1", "L" : L}
        g_unopt = G1(*args_g, **kwds_g)
    g = g_unopt

    if (solver_type == "z3perm" 
            or solver_type == "z3naive"):
        permables = {}
        for a in p.process_automata:
            if a.is_monitor:
                continue
            if len(a.perm_states) != 0:
                permables[a.name] = sorted(list(a.perm_states))
        for process, permable in permables.items():
            if "perm" in solver_type:
                kwds_g_perm = {"id" : f"G_perm_{process}", "L" : L}
                g = G_perm(g, process, permable, **kwds_g_perm)
            elif "naive" in solver_type:
                kwds_g_perm = {"id" : f"G_naive_{process}", "L" : L}
                g = G_naive(g, process, permable, **kwds_g_perm)

    eng = Engine(u, g, start_time, id="Engine", L=L)

    # TODO: refactor how result is used by tool.py, if at all
    result = []
    for solution in eng.generator():
        result.append(solution)
        print("Solution: ", solution)
        if not all:
            eng.interrupt = True
            # print("interrupting after first solution")
    return result

