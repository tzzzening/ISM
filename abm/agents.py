"""
The classes for sellers and buyers, the 2 agents in the waste model.
"""

from mesa import Agent
from abm.enums import CapacityPlanningStrategies


class WasteAgent(Agent):
    """
    Base class for a waste model agent.
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.is_matched = False
        self.trade_quantity = 0
        self.days_taken_to_increase_capacity = 7
        self.weekly_demand = 0
        self.demand_list = []
        self.capacity_planning_strategy = None
        self.day_capacity_changes = 0
        self.new_production_capacity = 0
        self.maintenance_cost_per_capacity = 2
        self.weekly_production = 0
        self.production_capacity = 0
        self.profit_per_good = 0
        self.is_co_investing = False

    def edit_demand_list(self) -> None:
        """
        Keeps a record of the demand for the past 28 weeks.
        """
        self.demand_list.append(self.weekly_demand)
        if len(self.demand_list) > 28:  # 28 is the number to plot the demand forecast
            del self.demand_list[0]


class Seller(WasteAgent):
    """
    A seller that produces waste from its production of goods.
    """
    def __init__(self, unique_id, min_price, production_capacity, model) -> None:
        super().__init__(unique_id, model)
        self.min_price = min_price
        self.production_capacity = production_capacity
        self.buyer = None
        self.waste_left = 0
        self.cost_per_unit_waste_disposed = 5
        self.trade_cost = 0
        self.capacity_planning_strategy = CapacityPlanningStrategies.lag
        self.waste_generated_per_good = 1
        self.profit_per_good = 70

    def __str__(self) -> str:
        output = "Agent {} (seller) has {} waste produced, with min price of {}. "\
            .format(self.unique_id, self.waste_left, self.min_price)
        if self.is_matched:
            output += "Sold to buyer {}.".format(self.buyer.unique_id)
        return output

    def sell(self) -> None:
        self.waste_left -= self.trade_quantity

    def step(self) -> None:
        """
        Generate production and waste for the week.
        """
        self.weekly_production = self.production_capacity
        self.waste_left = self.waste_generated_per_good * self.weekly_production

    def advance(self) -> None:
        if self.is_matched:
            self.sell()
        self.edit_demand_list()


class Buyer(WasteAgent):
    """
    A buyer that buys waste as input materials for production of goods.
    """
    def __init__(self, unique_id, waste_treatment_capacity, max_price, production_capacity, model) -> None:
        super().__init__(unique_id, model)
        self.waste_treatment_capacity = waste_treatment_capacity
        self.new_waste_treatment_capacity = 0
        self.waste_treatment_capacity_list = []  # temp
        self.max_price = max_price
        self.seller = None
        self.trade_cost = None
        self.waste_treatment_capacity_left = 0
        self.cost_per_new_input = 20
        self.new_input = 150
        self.input_per_good = 1
        self.production_capacity = production_capacity
        self.capacity_planning_strategy = CapacityPlanningStrategies.lag
        self.profit_per_good = 60

    def __str__(self) -> str:
        output = "Agent {} (buyer) has capacity of {}, with max price of {}. "\
            .format(self.unique_id, self.waste_treatment_capacity_left, self.max_price)
        if self.is_matched:
            output += "Bought from seller {}.".format(self.seller.unique_id)
        return output

    def buy(self) -> None:
        self.waste_treatment_capacity_left -= self.trade_quantity

    def step(self) -> None:
        """
        Update waste treatment capacity and generate production.
        """
        self.waste_treatment_capacity_left = self.waste_treatment_capacity
        self.weekly_production = min(self.production_capacity, self.total_input // self.input_per_good)

    def advance(self) -> None:
        if self.is_matched:
            self.buy()
        self.edit_demand_list()

    @property
    def total_input(self):
        if self.is_matched:
            return self.new_input + self.trade_quantity
        else:
            return self.new_input

    @property
    def total_capacity(self):
        return self.production_capacity + self.waste_treatment_capacity
