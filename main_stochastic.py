from typing import List

from ortools.linear_solver import pywraplp
from problem_stochastic import RPP


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
        self.capitals = [
            [solver.NumVar(-solver.infinity(), solver.infinity(), f"F^{scenario}_{period}") for period in range(problem.num_periods+1)]
            for scenario in range(problem.num_scenarios)
        ]
        # num_testers[m]
        self.num_testers = [None]+[solver.IntVar(problem.initial_num_testers[(m,)], solver.infinity(), f"K_({m})") for m in range(1, problem.num_testers+1)]
        # num_handlers[h][a]
        self.num_handlers = [[None]] + [
                [None] + [solver.IntVar(problem.initial_num_handlers[(h, a)], solver.infinity(), f"K^{h}_{a}") for a in range(1, problem.num_handlers+1)]
                for h in range(1, problem.num_handler_categories+1)
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
        self.num_produced_by_handler_categories = [
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
            [solver.NumVar(-solver.infinity(), solver.infinity(), f"S_({p},{t})") for t in range(problem.num_products+1)]
            for p in range(problem.num_periods+1)
        ]
        self.Spos = [
            [solver.NumVar(0, solver.infinity(), f"Spos_({p},{t})") for t in range(problem.num_products+1)]
            for p in range(problem.num_periods+1)
        ]
        self.Sneg = [
            [solver.NumVar(0, solver.infinity(), f"Sneg_({p},{t})") for t in range(problem.num_products+1)]
            for p in range(problem.num_periods+1)
        ]
        #product_capacity_loading_costs[p][t]
        self.product_capacity_loading_costs = [
            [solver.NumVar(-solver.infinity(), solver.infinity(), f"V_({p},{t})") for t in range(problem.num_products+1)]
            for p in range(problem.num_periods+1)
        ]
        self.y = [
            [solver.BoolVar(f"y_({p},{t})") for t in range(problem.num_products+1)]
            for p in range(problem.num_periods+1)
        ]
        self.BigM = 999999999999
        
        


def solve(problem: RPP):
    solver: pywraplp.Solver = pywraplp.Solver.CreateSolver("SCIP")
    vars = Variables(solver, problem)
    # Constraint (2)
    for p in problem.periods:
        for m in problem.testers:
            # 1️⃣ Available testers in period p, tester type m
            num_available_testers = (
                vars.num_testers[m]
                + sum(vars.num_acquired_testers[p][m][z] for z in problem.tester_channels)
            )

            # 2️⃣ Effective utilization rate (hours × utilization fraction)
            total_utilization_rate = (
                problem.tester_work_hours[p, m]
                * problem.tester_target_utils[p, m]
            )

            # 3️⃣ Production workload adjusted by tester ability
            num_produced_main = sum(
                (problem.tester_ablities[m, t] * vars.num_produced_main[p][m][t])/(problem.tester_throughputs[m,t]*total_utilization_rate)
                for t in problem.products
            )

            # 4️⃣ Capacity constraint
            solver.Add(
                num_available_testers >= num_produced_main,
                f"TesterCapacity[p={p},m={m}]"
            )
    
    # Constraint (3)
    for p in problem.periods:
        for m in problem.testers:
            for h in problem.handler_categories:
                for t in problem.products:
                    sum_produced_by_categories = sum(
                        problem.handler_ablities[m,h,a,t]*vars.num_produced_by_handler_categories[p][m][h][a][t]
                        for a in problem.handlers
                    )
                    solver.Add(sum_produced_by_categories == vars.num_produced_main[p][m][t])
    
    # Constraint (4)
    for p in problem.periods:
        for a in problem.handlers:
            for h in problem.handler_categories:
                num_available_handlers = vars.num_handlers[h][a] + sum(vars.num_acquired_handlers[p][h][a][z] for z in problem.handler_channels)
                total_utilization_rate = problem.handler_work_hours[p,h,a]*problem.handler_target_utils[p,h,a]
                sum_produced_by_categories = sum(
                        (problem.handler_ablities[m,h,a,t]*vars.num_produced_by_handler_categories[p][m][h][a][t])/(problem.handler_throughputs[m,h,a,t]*total_utilization_rate)
                        for m in problem.testers for t in problem.products
                    )
                solver.Add(num_available_handlers >= sum_produced_by_categories)
    
    # Constraint (5prelude)
    for p in range(problem.num_periods+1):
        for t in problem.products:
            solver.Add(vars.Spos[p][t] <= vars.BigM * vars.y[p][t])
            solver.Add(vars.Sneg[p][t] <= vars.BigM * (1 - vars.y[p][t]))
            solver.Add(vars.product_capacity_loading_qtys[p][t] == vars.Spos[p][t] - vars.Sneg[p][t])
    for t in problem.products:
        solver.Add(vars.product_capacity_loading_qtys[0][t] == problem.initial_capacity_loading_qty[(t,)])
    # Constraint (5)
    for p in problem.periods:
        for t in problem.products:
            num_produced_main = sum(
                (problem.tester_ablities[m, t] * vars.num_produced_main[p][m][t])
                for m in problem.testers
            )
            solver.Add(vars.product_capacity_loading_qtys[p][t] == vars.product_capacity_loading_qtys[p-1][t] + num_produced_main - problem.demands_mts[p,t]) 
    
    # Constraint (6)
    for p in problem.periods:
        for t in problem.products:
            num_produced_main = sum(
                (problem.tester_ablities[m, t] * vars.num_produced_main[p][m][t])
                for m in problem.testers
            )
            solver.Add(num_produced_main <= problem.demands_mto[p,t])

    # Constraint (7)
    for p in problem.periods:
        for t in problem.products:
            excess_cost = problem.excess_production_cost[p,t]*vars.Spos[p][t]
            shortage_cost = problem.shortage_cost[p,t]*vars.Sneg[p][t]
            solver.Add(vars.product_capacity_loading_costs[p][t] == excess_cost + shortage_cost)

    # Constraint (8prelude)
    solver.Add(vars.capitals[0] == problem.capital)
    # Constraint (8)
    for p in problem.periods:
        tester_borrow_total_cost = sum(problem.tester_borrow_prices[p,m,z]*vars.num_acquired_testers[p][m][z] for m in problem.testers for z in problem.tester_channels)
        handler_borrow_total_cost = sum(problem.handler_borrow_prices[p,h,a,z]*vars.num_acquired_handlers[p][h][a][z] for z in problem.handler_channels for a in problem.handlers for h in problem.handler_categories)
        inventory_cost = sum(vars.product_capacity_loading_costs[p][t] for t in problem.products)
        total_profit_mts = sum(problem.product_profits[p,t]*problem.demands_mts[p,t] for t in problem.products)
        total_profit_mto = sum(problem.product_profits[p,t]*vars.num_produced_main[p][m][t] for t in problem.products for m in problem.testers)
        last_capital = vars.capitals[p-1]*(1+problem.interest_rates[p])
        solver.Add(vars.capitals[p] == last_capital - tester_borrow_total_cost - handler_borrow_total_cost - inventory_cost + total_profit_mts + total_profit_mto)

    # Objective
    last_period = max(problem.periods)
    compound_interest = 1
    for p in problem.periods:
        compound_interest *= (1 + problem.interest_rates[p])
    last_capital = vars.capitals[last_period]/compound_interest
    tester_purchase_cost = sum((problem.tester_initial_prices[(m,)]- problem.tester_salvage_prices[(m,)])*(vars.num_testers[m]-problem.initial_num_testers[(m,)]) for m in problem.testers)
    handler_purchase_cost = sum((problem.handler_initial_prices[h,a]-problem.handler_salvage_prices[h,a])*(vars.num_handlers[h][a]-problem.initial_num_handlers[h,a]) for h in problem.handler_categories for a in problem.handlers)
    obj = last_capital - tester_purchase_cost - handler_purchase_cost
    solver.Maximize(obj)
    solver.SetNumThreads(16)
    status = solver.Solve()
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        print("Objective =", solver.Objective().Value())
    # print(status)
    # for var in solver.variables():
    #     val = var.solution_value()
    #     # if abs(val) > 1e-6:   # print only non-zero variables (optional)
    #     print(f"{var.name():<30s} = {val:,.6f}")

def run():
    problem = RPP(num_scenarios=10, #tambahin jadi berapa gitu, 10?
                 distribution="uniform", #antara uniform atau normal 
                 variance=0.1) #dari 0.1 sampai 1? 
    # solve(problem)

if __name__ == "__main__":
    run()