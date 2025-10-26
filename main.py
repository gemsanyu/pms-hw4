from typing import List

from ortools.linear_solver import pywraplp

from problem import RPP


def nested_shape(lst):
    shape = []
    while isinstance(lst, list):
        shape.append(len(lst))
        if not lst:  # empty list — stop here
            break
        lst = lst[0]
    return tuple(shape)

class Variables:
    def __init__(self, 
                 solver: pywraplp.Solver,
                 problem: RPP):
        self.capitals = [solver.NumVar(-solver.infinity(), solver.infinity(), f"F_{period}") for period in range(problem.num_periods+1)]
        # num_testers[p][m]
        self.num_testers = [
            [solver.IntVar(0, solver.infinity(), f"K_({p},{m})") for m in range(problem.num_testers+1)] 
            for p in range(len(problem.periods)+1)
        ]
        # num_handlers[p][h][a]
        self.num_handlers = [
            [
                [solver.IntVar(0, solver.infinity(), f"K^{h}_({p},{a})") for a in range(problem.num_handlers+1)]
                for h in range(problem.num_handler_categories+1)
            ]
            for p in range(problem.num_periods+1)
        ]
        # num_acquired_testers[p][m][z]
        self.num_acquired_testers = [
            [
                [solver.IntVar(0, solver.infinity(), f"X_({p},{m},{z})") for z in range(problem.num_tester_channels+1)]
                for m in range(problem.num_testers+1)
            ]
            for p in range(problem.num_periods+1)
        ]
        # num_acquired_handlers[p][h][a][z]
        self.num_acquired_handlers = [
            [
                [
                    [solver.IntVar(0, solver.infinity(), f"X^{h}_({p},{a},{z})") for z in range(problem.num_handler_channels+1)]
                    for a in range(problem.num_handlers+1)
                ]
                for h in range(problem.num_handler_categories+1)
            ]
            for p in range(problem.num_periods+1)
        ]
        # num_produced_main[p][m][t]
        self.num_produced_main = [
            [
                [solver.NumVar(0, solver.infinity(), f"Q_({p},{m},{t})") for t in range(problem.num_products+1)]
                for m in range(problem.num_testers+1)
            ]
            for p in range(problem.num_periods+1)
        ]
        # num_produced_combined[p][m][h][a][t]
        self.num_produced_combined = [
            [
                [
                    [
                        [solver.NumVar(0, solver.infinity(), f"Q^{h}_({p},{m},{a},{t})") for t in range(problem.num_products+1)]
                        for a in range(problem.num_handlers+1)
                    ]
                    for h in range(problem.num_handler_categories+1)
                ]
                for m in range(problem.num_testers+1)
            ]
            for p in range(problem.num_periods+1)
        ]
        #product_capacity_loading_qtys[p][t]
        self.product_capacity_loading_qtys = [
            [solver.IntVar(-solver.infinity(), solver.infinity(), f"S_({p},{t})") for t in range(problem.num_products+1)]
            for p in range(problem.num_periods+1)
        ]
        #product_capacity_loading_costs[p][t]
        self.product_capacity_loading_costs = [
            [solver.NumVar(-solver.infinity(), solver.infinity(), f"V_({p},{t})") for t in range(problem.num_products+1)]
            for p in range(problem.num_periods+1)
        ]
        


def solve(problem: RPP):
    solver = pywraplp.Solver.CreateSolver("SCIP")
    vars = Variables(solver, problem)

def run():
    problem = RPP()
    solve(problem)

if __name__ == "__main__":
    run()