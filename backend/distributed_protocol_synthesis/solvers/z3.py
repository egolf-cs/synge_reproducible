import itertools

import z3

class Solver(object):
    def __init__(self):
        self.candidates = dict()
        self.reverse_candidates = dict()
        self.variable_index = 1
        self.num_constraints = 0

    def associate_candidate_with_last_variable(self, candidate):
        self.candidates[candidate] = self.last_variable
        self.reverse_candidates[str(self.last_variable)].append(candidate)

    def update(self):
        pass

class Z3Solver(Solver):
    def __init__(self, random_seed=None):
        if random_seed == None:
            random_seed = 0
        super(Z3Solver, self).__init__()
        self.random_seed = random_seed
        z3.set_param('smt.random_seed', self.random_seed)
        self.z3_solver = z3.Solver()

    def mk_constraint(self, disable=None, enable=None):
        disable = [] if disable is None else disable
        enable = [] if enable is None else enable
        disable_lits = [z3.Not(self.candidates[edge]) for edge in disable]
        enable_lits = [self.candidates[edge] for edge in enable]
        Cbar = z3.Or(*(disable_lits + enable_lits))
        return Cbar
        
    def And(self, args):
        return z3.And(*args)
    def Or(self, args):
        return z3.Or(*args)
    def Not(self, arg):
        return z3.Not(arg)
    def substitute(self, expr, tpls):
        return z3.substitute(expr, tpls)

    def mk_determinism_constraints(self, per_state_label_candidate_edges):
        clauses = []
        for edges in per_state_label_candidate_edges.values():
            for edge1, edge2 in itertools.combinations(edges, 2):
                expr = z3.Not(
                    z3.And(self.candidates[edge1], self.candidates[edge2]))
                clauses.append(expr)
        return clauses

    def mk_input_output_state_constraint(
            self, input_candidates, output_candidates):
        clauses = []
        for candidate1 in input_candidates:
            for candidate2 in output_candidates:
                expr = z3.And(
                    self.candidates[candidate1], self.candidates[candidate2])
                expr = z3.Not(expr)
                clauses.append(expr)
        return z3.And(*clauses)

    def add_variable(self, candidate):
        variable = z3.Bool(self.variable_index)
        self.candidates[candidate] = variable
        self.reverse_candidates[str(variable)] = [candidate]
        self.last_variable = variable
        self.last_variable_index = self.variable_index
        self.variable_index += 1

    def push(self):
        self.z3_solver.push()

    def pop(self):
        self.z3_solver.pop()

    def add(self,phi):
        self.num_constraints += 1
        self.z3_solver.add(phi)

    def solve(self):
        if self.z3_solver.check() == z3.unsat:
            return False
        model = self.z3_solver.model()
        new_transitions = []
        for variable in model:
            if z3.is_true(model[variable]):
                new_transitions += self.reverse_candidates[str(variable)]
        return new_transitions

    def solve_alt(self):
        models = self.enumerate(100)
        model = models[-1]
        return model


    def enumerate(self, n):
        self.push()
        candidate = self.solve_alt()

        res = [candidate]
        while candidate and len(res) < n:
            res.append(candidate)
            constraint = self.mk_constraint(disable=candidate)
            self.z3_solver.add(constraint)
            candidate = self.solve_alt()

        self.pop()
        return res

    def mk_str(self, expr):
        return expr.sexpr()

    def simplify(self,expr):
        return z3.simplify(expr)
    
    def dimacs(self):
        return self.z3_solver.dimacs()