from typing import Dict

MONTHLY_RATIOS: Dict[str, float] = {
"January": 0.092,
"February": 0.074,
"March": 0.076,
"April": 0.086,
"May": 0.085,
"June": 0.076,
"July": 0.084,
"August": 0.098,
"September": 0.092,
"October": 0.062,
"November": 0.072,
"December": 0.102,
}


PREVIOUS_MONTH = {
"January": "December",
"February": "January",
"March": "February",
"April": "March",
"May": "April",
"June": "May",
"July": "June",
"August": "July",
"September": "August",
"October": "September",
"November": "October",
"December": "November",
}

def predict_annual_consumption(input_month: str, input_kwh: float):
    """
    Predicts annual consumption and monthly breakdown from user input.
    :param input_month: Month user gave input (e.g., "August" if they submitted Aug 31)
    :param input_kwh: Consumption in kWh for that month
    :return: dict with annual_prediction and monthly_predictions
    """
    prev_month = PREVIOUS_MONTH[input_month]
    base_ratio = MONTHLY_RATIOS[prev_month]

    if base_ratio == 0:
        raise ValueError(f"Invalid ratio for month: {prev_month}")

    annual_predicted = input_kwh / base_ratio

    monthly_predictions = {}
    for month, ratio in MONTHLY_RATIOS.items():
        if month!=input_month:
            monthly_predictions[month] = round(annual_predicted * ratio, 2)
    print("monthly predictions",monthly_predictions)
    return {
        "input_month": input_month,
        "assumed_month": prev_month,
        "input_kwh": input_kwh,
        "ratio_used": base_ratio,
        "annual_prediction_kwh": round(annual_predicted, 2),
        "monthly_predictions": monthly_predictions
    }
    
