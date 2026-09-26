import unittest

from app.seed_foods import STARTER_FOODS, as_food_kwargs


class StarterFoodsTest(unittest.TestCase):
    def test_catalogue_is_searchable_and_nutritionally_valid(self):
        names = [row[0] for row in STARTER_FOODS]
        self.assertGreaterEqual(len(names), 50)
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(any("nyers" in name.lower() for name in names))
        self.assertTrue(any("főtt" in name.lower() for name in names))
        for row in STARTER_FOODS:
            food = as_food_kwargs(row)
            self.assertTrue(food["name"])
            self.assertEqual(food["source"], "usda")
            for nutrient in ("kcal", "protein", "carbs", "fat", "fiber", "sugar", "saturated_fat", "salt"):
                self.assertGreaterEqual(food[nutrient], 0, f"{food['name']}: {nutrient}")


if __name__ == "__main__":
    unittest.main()
