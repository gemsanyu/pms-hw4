import pathlib
import re
from typing import List

import pandas as pd


class RPP:
    def __init__(self):
        data_dir = pathlib.Path("clean-data")
        self.data_dir = data_dir
        self.handler_initial_prices_df = pd.read_csv(data_dir/"handler_initial_price.csv")
        self.handler_borrow_prices_df = pd.read_csv(data_dir/"handler_borrow_price.csv")
        self.handler_ablities_df = pd.read_csv(data_dir/"handler_ability.csv")
        self.handler_salvage_prices_df = pd.read_csv(data_dir/"handler_salvage_price.csv")
        self.handler_throughputs_df = pd.read_csv(data_dir/"handler_throughput.csv")
        self.tester_initial_prices_df = pd.read_csv(data_dir/"tester_initial_price.csv")
        self.tester_borrow_prices_df = pd.read_csv(data_dir/"tester_borrow_price.csv")
        self.tester_ablities_df = pd.read_csv(data_dir/"tester_ability.csv")
        self.tester_salvage_prices_df = pd.read_csv(data_dir/"tester_salvage_price.csv")
        self.tester_throughputs_df = pd.read_csv(data_dir/"tester_throughput.csv")
        self.product_profits_df = pd.read_csv(data_dir/"product_profit.csv")
        self.periods: List[int] = self.product_profits_df["p"].unique().tolist()
        self.testers: List[int] = self.tester_initial_prices_df["m"].unique().tolist()
        self.handlers: List[int] = self.handler_salvage_prices_df["a"].unique().tolist()
        self.handler_categories: List[int] = self.handler_throughputs_df["h"].unique().tolist()
        self.products: List[int] = self.product_profits_df["t"].unique().tolist()
        self.tester_channels: List[int] = self.tester_borrow_prices_df["z"].unique().tolist()
        self.handler_channels: List[int] = self.handler_borrow_prices_df["z"].unique().tolist()
        self.num_periods = len(self.periods)
        self.num_testers = len(self.testers)
        self.num_handlers = len(self.handlers)
        self.num_handler_categories = len(self.handler_categories)
        self.num_tester_channels = len(self.tester_channels)
        self.num_handler_channels = len(self.handler_channels)
        self.num_products = len(self.products)
        
        self.excess_production_cost: pd.DataFrame
        self.shortage_cost: pd.DataFrame
        self.interest_rates: pd.DataFrame
        self.initial_num_handlers: pd.DataFrame
        self.initial_num_testers: pd.DataFrame
        self.tester_work_hours: pd.DataFrame
        self.handler_target_utils: pd.DataFrame
        self.tester_target_utils: pd.DataFrame
        self.capital: float
        self.initial_capacity_loading_qty: pd.DataFrame

        self.read_others()

    def read_others(self):
        other_info_filepath = self.data_dir/"others.txt"
        text:str
        with open(other_info_filepath.absolute(), mode="r", encoding="utf-8") as f:
            text = f.read()
        match = re.search(r"\bIp\s+([+-]?\d+(?:\.\d+)?)", text)
        if match:
            interest_rate = float(match.group(1))
            interest_rates_dict = [{"p":p, "rate":interest_rate} for p in self.periods]
            self.interest_rates = pd.DataFrame(interest_rates_dict)
        match = re.search(r"=\s*[^*]*\*\s*([+-]?\d+(?:\.\d+)?)", text)
        if match:
            excess_cost_multiplier = float(match.group(1))
            self.excess_production_cost = self.product_profits_df.copy()
            self.excess_production_cost["cost"] = self.product_profits_df["profit"]*excess_cost_multiplier
        match = re.search(r"yp,m=yp,a= (\d(\.\d*)?)", text)
        if match:
            util = float(match.group(1))
            handler_utils_list = [{"a":a, "p":p, "util":util} for a in self.handlers for p in self.periods]
            self.handler_target_utils = pd.DataFrame(handler_utils_list)
            tester_utils_list = [{"m":m, "p":p, "util":util} for m in self.testers for p in self.periods]
            self.tester_target_utils = pd.DataFrame(tester_utils_list)
        match = re.search(r"(\w+)\s*=\s*\{([^}]*)\}", text)
        if match:
            numbers = [int(x) for x in match.group(2).split(",")]
            result = [{"a":i + 1, "K0": n } for i, n in enumerate(numbers)]
            self.initial_num_handlers = pd.DataFrame(result)
        match = re.search(r"K0m\s*=\s*\{([^}]*)\}", text)
        if match:
            numbers = [int(x) for x in match.group(1).split(",")]
            result = [{"m":i + 1, "K0": n } for i, n in enumerate(numbers)]
            self.initial_num_testers = pd.DataFrame(result)
        match = re.search(r"F0\s*=\s*([+-]?\d+(?:\.\d+)?)", text)
        if match:
            self.capital = float(match.group(1))
        match = re.search(r"S0\s*=\s*\{([^}]*)\}", text)
        if match:
            numbers = [float(x) for x in match.group(1).split(",")]
            result = [{"t":i + 1, "S0": n } for i, n in enumerate(numbers)]
            self.initial_capacity_loading_qty = pd.DataFrame(result)
            # print(result)
        match = re.search(r"\*\s*([+-]?\d+(?:\.\d+)?)", text)
        if match:
            shortage_multiplier = float(match.group(1))
            self.shortage_cost = self.product_profits_df.copy()
            self.shortage_cost["cost"] = self.shortage_cost["profit"]*shortage_multiplier
        match = re.search(r"\bwp,m\s+([+-]?\d+(?:\.\d+)?)", text)
        if match:
            workhours = float(match.group(1))
            workhour_dict_list = [{"m":m, "p":p, "workhours":workhours} for m in self.testers for p in self.periods]
            self.tester_work_hours = pd.DataFrame(workhour_dict_list)
        