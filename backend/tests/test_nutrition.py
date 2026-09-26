from decimal import Decimal

def nutrition_for_grams(per_100g: Decimal, grams: Decimal) -> Decimal:
    """The same formula used by the day endpoint; retain Decimal precision."""
    return per_100g * grams / Decimal("100")

def test_100g_based_calculation():
    assert nutrition_for_grams(Decimal("356.7"), Decimal("50")) == Decimal("178.35")

def test_recipe_style_portion_calculation():
    # 600 kcal cooked recipe weighing 750 g: a 250 g portion is 200 kcal.
    assert nutrition_for_grams(Decimal("80"), Decimal("250")) == Decimal("200")
