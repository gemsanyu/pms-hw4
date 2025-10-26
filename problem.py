import pathlib
import re
from typing import Dict, List, Union

import pandas as pd


def df_to_multikey_dict(df: pd.DataFrame, 
                        keys: Union[str, List[str]], 
                        values: Union[str, List[str]])->Dict:
    """
    Convert a pandas DataFrame into a multi-key dictionary.
    
    Parameters
    ----------
    df : pd.DataFrame
        The source DataFrame.
    keys : str | list[str]
        One or more column names to use as keys.
    values : str | list[str]
        One or more column names to use as values.
    
    Returns
    -------
    dict
        A dictionary mapping tuples of key values → value(s).
        If `values` has one column → returns single value.
        If `values` has multiple columns → returns dict of {col: val}.
    """
    # Ensure keys and values are lists
    if isinstance(keys, str):
        keys = [keys]
    if isinstance(values, str):
        values = [values]
    
    records = df[keys + values].to_dict("records")
    result = {}
    for row in records:
        key_tuple = tuple(row[k] for k in keys)
        if len(values) == 1:
            result[key_tuple] = row[values[0]]
        else:
            result[key_tuple] = {v: row[v] for v in values}
    return result

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
        self.demands_df = pd.read_csv(data_dir/"demands.csv")
        self.demands_mts = df_to_multikey_dict(self.demands_df, ["p","t"], "demand")
        self.demands_mto = df_to_multikey_dict(self.demands_df, ["p","t"], "demand")
        self.handler_initial_prices = df_to_multikey_dict(self.handler_initial_prices_df, ["h", "a"], "initial_price")
        self.handler_borrow_prices = df_to_multikey_dict(self.handler_borrow_prices_df, ["p","h","a","z"], "price")
        self.handler_ablities = df_to_multikey_dict(self.handler_ablities_df, ["m","h","a","t"], "ability")
        self.handler_salvage_prices = df_to_multikey_dict(self.handler_salvage_prices_df, ["h","a"], "salvage_price")
        self.handler_throughputs = df_to_multikey_dict(self.handler_throughputs_df, ["m","h","a","t"], "throughput")
        self.tester_initial_prices = df_to_multikey_dict(self.tester_initial_prices_df, ["m"], "initial_price")
        self.tester_borrow_prices = df_to_multikey_dict(self.tester_borrow_prices_df, ["p","m","z"], "price")
        self.tester_ablities = df_to_multikey_dict(self.tester_ablities_df, ["m","t"], "ability")
        self.tester_salvage_prices = df_to_multikey_dict(self.tester_salvage_prices_df, "m", "salvage_price")
        self.tester_throughputs = df_to_multikey_dict(self.tester_throughputs_df, ["m","t"], "throughput")
        self.product_profits = df_to_multikey_dict(self.product_profits_df, ["p", "t"], "profit")
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
        
        self.excess_production_cost_df: pd.DataFrame
        self.excess_production_cost: Dict
        self.shortage_cost_df: pd.DataFrame
        self.shortage_cost: Dict
        self.interest_rates: pd.DataFrame
        self.initial_num_handlers: Dict
        self.initial_num_testers: Dict
        self.initial_num_handlers_df: pd.DataFrame
        self.initial_num_testers_df: pd.DataFrame
        self.handler_work_hours: Dict
        self.handler_work_hours_df: pd.DataFrame
        self.tester_work_hours: Dict
        self.tester_work_hours_df: pd.DataFrame
        self.handler_target_utils: Dict
        self.tester_target_utils: Dict
        self.handler_target_utils_df: pd.DataFrame
        self.tester_target_utils_df: pd.DataFrame
        self.capital: float
        self.initial_capacity_loading_qty: Dict
        self.initial_capacity_loading_qty_df: pd.DataFrame

        self.read_others()

    def read_others(self):
        other_info_filepath = self.data_dir/"others.txt"
        text:str
        with open(other_info_filepath.absolute(), mode="r", encoding="utf-8") as f:
            text = f.read()
        match = re.search(r"\bIp\s+([+-]?\d+(?:\.\d+)?)", text)
        if match:
            interest_rate = float(match.group(1))
            self.interest_rates = {p:interest_rate for p in self.periods} 
            # self.interest_rates = pd.DataFrame(interest_rates_dict)
        match = re.search(r"=\s*[^*]*\*\s*([+-]?\d+(?:\.\d+)?)", text)
        if match:
            excess_cost_multiplier = float(match.group(1))
            self.excess_production_cost_df = self.product_profits_df.copy()
            self.excess_production_cost_df["cost"] = self.product_profits_df["profit"]*excess_cost_multiplier
            self.excess_production_cost = df_to_multikey_dict(self.excess_production_cost_df, ["p","t"], "cost")
        match = re.search(r"yp,m=yp,a= (\d(\.\d*)?)", text)
        if match:
            util = float(match.group(1))
            handler_utils_list = [{"a":a, "h":h, "p":p, "util":util} for h in self.handler_categories for a in self.handlers for p in self.periods]
            self.handler_target_utils_df = pd.DataFrame(handler_utils_list)
            self.handler_target_utils = df_to_multikey_dict(self.handler_target_utils_df, ["p","h","a"], "util")
            tester_utils_list = [{"m":m, "p":p, "util":util} for m in self.testers for p in self.periods]
            self.tester_target_utils_df = pd.DataFrame(tester_utils_list)
            self.tester_target_utils = df_to_multikey_dict(self.tester_target_utils_df, ["p","m"], "util")
        match = re.search(r"(\w+)\s*=\s*\{([^}]*)\}", text)
        if match:
            numbers = [int(x) for x in match.group(2).split(",")]
            result = [
                {"a": i + 1, "h": j + 1, "K0": n}
                for i, n in enumerate(numbers)
                for j in range(len(numbers))
            ]
            self.initial_num_handlers_df = pd.DataFrame(result)
            self.initial_num_handlers = df_to_multikey_dict(self.initial_num_handlers_df, ["h","a"], "K0")
        match = re.search(r"K0m\s*=\s*\{([^}]*)\}", text)
        if match:
            numbers = [int(x) for x in match.group(1).split(",")]
            result = [{"m":i + 1, "K0": n } for i, n in enumerate(numbers)]
            self.initial_num_testers_df = pd.DataFrame(result)
            self.initial_num_testers = df_to_multikey_dict(self.initial_num_testers_df, "m", "K0")
        match = re.search(r"F0\s*=\s*([+-]?\d+(?:\.\d+)?)", text)
        if match:
            self.capital = float(match.group(1))
        match = re.search(r"S0\s*=\s*\{([^}]*)\}", text)
        if match:
            numbers = [float(x) for x in match.group(1).split(",")]
            result = [{"t":i + 1, "S0": n } for i, n in enumerate(numbers)]
            self.initial_capacity_loading_qty_df = pd.DataFrame(result)
            self.initial_capacity_loading_qty = df_to_multikey_dict(self.initial_capacity_loading_qty_df, "t", "S0")
            # print(result)
        match = re.search(r"\*\s*([+-]?\d+(?:\.\d+)?)", text)
        if match:
            shortage_multiplier = float(match.group(1))
            self.shortage_cost_df = self.product_profits_df.copy()
            self.shortage_cost_df["cost"] = self.shortage_cost_df["profit"]*shortage_multiplier
            self.shortage_cost = df_to_multikey_dict(self.shortage_cost_df, ["p","t"], "cost")
        match = re.search(r"\bwp,m\s+([+-]?\d+(?:\.\d+)?)", text)
        if match:
            workhours = float(match.group(1))
            workhour_dict_list = [{"m":m, "p":p, "workhours":workhours} for m in self.testers for p in self.periods]
            self.tester_work_hours_df = pd.DataFrame(workhour_dict_list)
            self.tester_work_hours = df_to_multikey_dict(self.tester_work_hours_df, ["p","m"], "workhours")
            workhour_dict_list = [{"a":a, "h":h, "p":p, "workhours":workhours} for a in self.handlers for h in self.handler_categories for p in self.periods]
            self.handler_work_hours_df = pd.DataFrame(workhour_dict_list)
            self.handler_work_hours = df_to_multikey_dict(self.handler_work_hours_df, ["p","h","a"], "workhours")