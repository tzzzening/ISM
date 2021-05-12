from abm_buyer_seller.model import WasteModel
from mesa.batchrunner import BatchRunner

# TO RUN WEB SERVER, UNCOMMENT THESE 2 LINES AND COMMENT OUT LINE 8 ONWARDS
# from abm_buyer_seller.server import server
# server.launch()


def compute_recycling_rate(model) -> float:
    return model.total_waste_traded / model.total_waste_produced


def compute_seller_savings(model) -> float:
    money_saved = model.total_profit_without_trading_seller - model.total_profit_with_trading_seller
    return money_saved / model.total_profit_without_trading_seller


def compute_buyer_savings(model) -> float:
    money_saved = model.total_profit_without_trading_buyer - model.total_profit_with_trading_buyer
    return money_saved / model.total_profit_without_trading_buyer


def compute_overall_savings(model) -> float:
    total_costs_without_trading = \
        model.total_profit_without_trading_seller + model.total_profit_without_trading_buyer
    total_costs_with_trading = \
        model.total_profit_with_trading_seller + model.total_profit_with_trading_buyer
    money_saved = total_costs_without_trading - total_costs_with_trading
    return money_saved / total_costs_without_trading


variable_params = {'seller_num': range(30, 31), 'buyer_num': range(30, 31)}
batch_run = BatchRunner(WasteModel, variable_params,
                        iterations=15, max_steps=301,
                        model_reporters={'Recycling_Rate': compute_recycling_rate,
                                         'Seller_Savings': compute_seller_savings,
                                         'Buyer_Savings': compute_buyer_savings,
                                         'Overall_Savings': compute_overall_savings
                                         })

batch_run.run_all()
run_data = batch_run.get_model_vars_dataframe()
run_data.to_excel(r'C:\Users\09nhn\OneDrive\Documents\Uni\ISM\Python\15.00.f.xlsx', index=False)
# sheet name legend
# number_of_runs,
# seller_capacity_planning: 0 Lead, 1 Lag, 3 Match
# buyer_capacity_planning: 0 Lead, 1 Lag, 3 Match
# co_investing: True, False
