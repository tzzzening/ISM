from mesa import Model
from abm_buyer_seller.time import SimultaneousActivationMoneyModel
from abm_buyer_seller.agents import Seller, Buyer
from mesa.datacollection import DataCollector
import random


def compute_recycling_rate(model) -> float:
    return model.total_waste_traded / model.total_waste_produced


def compute_seller_savings(model) -> float:
    money_saved = model.total_profit_without_trading_seller - model.total_profit_with_trading_seller
    return money_saved / model.total_profit_without_trading_seller


def compute_buyer_savings(model) -> float:
    money_saved = model.total_profit_without_trading_buyer - model.total_profit_with_trading_buyer
    return money_saved / model.total_profit_without_trading_buyer


def compute_overall_savings(model) -> float:
    total_profit_without_trading = \
        model.total_profit_without_trading_seller + model.total_profit_without_trading_buyer
    total_profit_with_trading = \
        model.total_profit_with_trading_seller + model.total_profit_with_trading_buyer
    money_saved = total_profit_without_trading - total_profit_with_trading
    return money_saved / total_profit_without_trading


class WasteModel(Model):
    """
    A model with waste sellers and buyers that interact with one another by trading
    """

    total_waste_produced = 0
    total_waste_traded = 0
    total_profit_without_trading_seller = 0  # cost incurred without trading waste, ie all waste is disposed of
    total_profit_with_trading_seller = 0
    total_profit_without_trading_buyer = 0  # cost incurred without trading waste, ie all waste is disposed of
    total_profit_with_trading_buyer = 0

    def __init__(self, seller_num, buyer_num) -> None:
        super().__init__()
        self.seller_num = seller_num
        self.buyer_num = buyer_num
        self.schedule = SimultaneousActivationMoneyModel(self)
        self.running = True
        self.steps = 0

        for i in range(seller_num):
            seller = Seller(unique_id=self.next_id(),
                            min_price=random.randint(10, 14),
                            production_capacity=random.randint(160, 200),
                            model=self)
            self.schedule.add(seller)
        for i in range(buyer_num):
            buyer = Buyer(unique_id=self.next_id(),
                          waste_treatment_capacity=random.randint(40, 60),
                          max_price=random.randint(12, 16),
                          production_capacity=random.randint(150, 190),
                          model=self)
            self.schedule.add(buyer)

        self.data_collector = DataCollector(
            model_reporters={'Recycling_Rate': compute_recycling_rate,
                             'Seller_Savings': compute_seller_savings,
                             'Buyer_Savings': compute_buyer_savings,
                             'Overall_Savings': compute_overall_savings},
            agent_reporters=None)

    def step(self) -> None:
        """
        Takes one step of the model.
        Updates the class level variables.
        """
        self.steps = self.schedule.steps
        self.schedule.step()
        self.total_waste_produced = self.schedule.total_waste_produced
        self.total_waste_traded = self.schedule.total_waste_traded
        self.total_profit_without_trading_seller = self.schedule.total_profit_without_trading_seller
        self.total_profit_with_trading_seller = self.schedule.total_profit_with_trading_seller
        self.total_profit_without_trading_buyer = self.schedule.total_profit_without_trading_buyer
        self.total_profit_with_trading_buyer = self.schedule.total_profit_with_trading_buyer
        if self.steps == 300:
            print()
            print(compute_recycling_rate(self))
            print(compute_seller_savings(self))
            print(compute_buyer_savings(self))
            print(compute_overall_savings(self))
        self.data_collector.collect(self)

    def __str__(self) -> str:
        return "\nCurrent Status:\n" + self.schedule.__str__()
