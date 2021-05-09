from mesa.time import SimultaneousActivation
from abm_buyer_seller.agents import WasteAgent
from abm_buyer_seller.agents import Buyer, Seller
from abm_buyer_seller.enums import CapacityPlanningStrategies
import bisect
import random
from statistics import mean
import numpy as np


FORECASTED_NUM_OF_WEEKS_CAP_PLANNING_LEAD = 28
FORECASTED_NUM_OF_WEEKS_CAP_PLANNING_MATCH = 14
FORECASTED_NUM_OF_WEEKS_CAP_PLANNING_LAG = 0


class SimultaneousActivationMoneyModel(SimultaneousActivation):
    """
    SimultaneousActivation class with added lists to store buyers and sellers separately.
    """

    total_waste_produced = 0
    total_waste_traded = 0

    total_profit_without_trading_seller = 0  # cost incurred without trading waste, ie all waste is disposed of
    total_profit_with_trading_seller = 0
    total_profit_without_trading_buyer = 0  # cost incurred without trading waste, ie all waste is disposed of
    total_profit_with_trading_buyer = 0

    def __init__(self, model) -> None:
        super().__init__(model)
        self.sellers = []
        self.buyers = []
        self.steps = 1

    def __str__(self) -> str:
        output = ""
        for i in self.sellers:
            output += (i[2].__str__() + "\n")
        for i in self.buyers:
            output += (i[2].__str__() + "\n")
        return output

    def add(self, agent: WasteAgent) -> None:
        """
        Adds an agent to the model.
        Depending on whether it is a seller or buyer, the agent is added in sorted order
        into the list of sellers or buyers.
        """
        self._agents[agent.unique_id] = agent
        if isinstance(agent, Seller):
            bisect.insort(self.sellers, (agent.min_price, agent.unique_id, agent))
        elif isinstance(agent, Buyer):
            bisect.insort(self.buyers, (agent.max_price, agent.unique_id, agent))
        else:
            raise TypeError

    def step(self) -> None:
        """
        Executes the step of all agents
        and updates the class variables for recycling rate and cost savings calculation.
        Finally, executes the advance of all agents.
        """
        if self.steps == 1:
            self.match_agents()
        average_daily_demand = int(self.steps * 2 + 50)  # steps * gradient + y-intercept
        for i in range(self.seller_num):
            seller = self.get_seller_from_list(i)
            seller.step()
            self.update_variables_seller(seller, random.randint(average_daily_demand - 5, average_daily_demand + 5))

        for i in range(self.buyer_num):
            buyer = self.get_buyer_from_list(i)
            buyer.step()
            self.update_variables_buyer(buyer, random.randint(average_daily_demand - 5, average_daily_demand + 5))

        if self.steps % 28 == 0:
            self.sellers = []
            self.buyers = []

        for agent in self.agent_buffer(shuffled=False):
            agent.advance()
            if self.steps % 28 == 0:
                self.plan_capacity(agent)
                self.change_price_and_waste_capacity(agent)
            elif self.steps % 28 == agent.days_taken_to_increase_capacity and self.steps > 28:
                agent.production_capacity = agent.new_production_capacity
                if isinstance(agent, Buyer):
                    agent.waste_treatment_capacity = agent.new_waste_treatment_capacity

        if self.steps % 28 == 0:
            self.initialise_agents()
            self.match_agents()

        self.steps += 1
        self.time += 1

    def match_agents(self) -> None:
        """
        Match agents according to minimum price of the seller and the maximum price of the buyer.
        """
        i = 0
        j = 0
        while True:
            seller = self.get_seller_from_list(i)
            buyer = self.get_buyer_from_list(j)
            if seller.min_price > buyer.max_price:
                if j == self.buyer_num - 1:
                    break
                j += 1
                continue

            cost = (seller.min_price + buyer.max_price) / 2
            if cost > buyer.cost_per_new_input:
                if j == self.buyer_num - 1:
                    break
                j += 1
                continue

            self.prepare_trade(seller, buyer)
            if i == (self.seller_num - 1) or j == (self.buyer_num - 1):
                break
            i += 1
            j += 1
        return

    @staticmethod
    def prepare_trade(seller, buyer) -> None:
        """
        Update the trading partners and the cost per unit waste of each agent.
        """

        seller.buyer = buyer
        buyer.seller = seller
        seller.is_matched = True
        buyer.is_matched = True

        cost = (seller.min_price + buyer.max_price) / 2
        seller.trade_cost = cost
        buyer.trade_cost = cost
        return

    def set_trade_quantity(self, seller) -> None:
        """
        Decides on the amount of waste to trade after being matched
        """
        buyer = seller.buyer
        seller_quantity = seller.waste_left
        buyer_quantity = buyer.waste_treatment_capacity
        trade_quantity = min(seller_quantity, buyer_quantity)
        seller.trade_quantity = trade_quantity
        buyer.trade_quantity = trade_quantity
        self.total_waste_traded += trade_quantity
        return

    def get_seller_from_list(self, index) -> Seller:
        """
        Returns seller from list of tuples.
        """
        return self.sellers[index][2]

    def get_buyer_from_list(self, index) -> Buyer:
        """
        Returns buyer from list of tuples.
        """
        return self.buyers[index][2]

    def update_variables_seller(self, seller, daily_demand) -> None:
        """
        Updates class variables related to the seller
        """
        seller.weekly_demand = daily_demand
        self.total_waste_produced += seller.waste_left
        self.total_profit_without_trading_seller += \
            daily_demand * seller.profit_per_good - \
            seller.waste_left * seller.cost_per_unit_waste_disposed - \
            seller.maintenance_cost_per_capacity * seller.production_capacity

        self.total_profit_with_trading_seller += \
            daily_demand * seller.profit_per_good - \
            seller.maintenance_cost_per_capacity * seller.production_capacity

        if seller.is_matched:
            self.set_trade_quantity(seller)
            cost = (seller.waste_left - seller.trade_quantity) * \
                seller.cost_per_unit_waste_disposed - \
                seller.trade_quantity * seller.trade_cost
            if seller.is_co_investing:
                cost += seller.buyer.waste_treatment_capacity * \
                        seller.buyer.maintenance_cost_per_capacity / 2
        else:
            cost = seller.waste_left * seller.cost_per_unit_waste_disposed
        self.total_profit_with_trading_seller -= cost
        return

    def update_variables_buyer(self, buyer, daily_demand) -> None:
        """
        Updates class variables related to the buyer
        """
        buyer.weekly_demand = daily_demand
        self.total_profit_without_trading_buyer += \
            daily_demand * buyer.profit_per_good - \
            buyer.new_input * buyer.cost_per_new_input - \
            buyer.maintenance_cost_per_capacity * buyer.total_capacity

        self.total_profit_with_trading_buyer += \
            daily_demand * buyer.profit_per_good - \
            buyer.maintenance_cost_per_capacity * buyer.production_capacity

        if buyer.is_matched and buyer.is_co_investing:
            cost = buyer.new_input * buyer.cost_per_new_input + \
                   buyer.trade_quantity * buyer.trade_cost + \
                   buyer.maintenance_cost_per_capacity * buyer.waste_treatment_capacity / 2
        elif buyer.is_matched and not buyer.is_co_investing:
            cost = buyer.new_input * buyer.cost_per_new_input + \
                   buyer.trade_quantity * buyer.trade_cost + \
                   buyer.maintenance_cost_per_capacity * buyer.waste_treatment_capacity
        else:
            cost = buyer.new_input * buyer.cost_per_new_input + \
                   buyer.maintenance_cost_per_capacity * buyer.waste_treatment_capacity
        self.total_profit_with_trading_buyer -= cost
        return

    def plan_capacity(self, agent: WasteAgent) -> None:
        """
        Plan production capacity depending on the past 28 weeks of demand and
        the type of capacity planning strategy the agent adopts
        """
        if self.steps % 28 != 0:  # take 28 weeks of data to come out with the forecast
            return
        x_values = np.array(list(range(1, 29)), dtype=np.float64)
        y_values = np.array(agent.demand_list, dtype=np.float64)
        m, c = self.best_fit_slope_and_intercept(x_values, y_values)
        if agent.capacity_planning_strategy is CapacityPlanningStrategies.lead:
            agent.new_production_capacity = int((28 + FORECASTED_NUM_OF_WEEKS_CAP_PLANNING_LEAD) * m + c)
        elif agent.capacity_planning_strategy is CapacityPlanningStrategies.match:
            agent.new_production_capacity = int((28 + FORECASTED_NUM_OF_WEEKS_CAP_PLANNING_MATCH) * m + c)
        elif agent.capacity_planning_strategy is CapacityPlanningStrategies.lag:
            agent.new_production_capacity = int((28 + FORECASTED_NUM_OF_WEEKS_CAP_PLANNING_LAG) * m + c)
        else:
            raise Exception

    @staticmethod
    def best_fit_slope_and_intercept(x_values, y_values) -> tuple:
        """
        Generates a best fit line a series of points
        :param x_values: list of x values
        :param y_values: list of y values
        :return: a tuple of the gradient and y intercept of the best fit line
        """
        m = (((mean(x_values) * mean(y_values)) - mean(x_values * y_values)) /
             ((mean(x_values) * mean(x_values)) - mean(x_values * x_values)))
        c = mean(y_values) - m * mean(x_values)
        return m, c

    def change_price_and_waste_capacity(self, agent) -> None:
        """
        Updates relevant information based on the change in production capacity
        """
        percentage_change = agent.new_production_capacity / agent.production_capacity
        if isinstance(agent, Seller):
            new_min_price = int(agent.min_price * percentage_change)
            agent.min_price = random.randint(new_min_price - 3, new_min_price + 3)
        elif isinstance(agent, Buyer):
            new_max_price = int(agent.max_price * percentage_change)
            agent.max_price = random.randint(new_max_price - 3, new_max_price + 3)
            new_cost_per_new_input = int(agent.cost_per_new_input * percentage_change)
            agent.cost_per_new_input = \
                random.randint(new_cost_per_new_input - 2, new_cost_per_new_input + 4)
            new_waste_treatment_capacity = int(agent.waste_treatment_capacity * percentage_change)
            agent.new_waste_treatment_capacity = \
                random.randint(new_waste_treatment_capacity - 1, new_waste_treatment_capacity + 1)
        self.add(agent)

    @property
    def seller_num(self) -> int:
        return len(self.sellers)

    @property
    def buyer_num(self) -> int:
        return len(self.buyers)

    def initialise_agents(self) -> None:
        for agent in self.agent_buffer(shuffled=False):
            agent.is_matched = False
        return
