# ============================================
# Supply AI System
# File: tests/test_forecasting.py
# Description: Unit tests for ML forecasting calculations
# ============================================

import unittest
import pandas as pd
from core.forecasting import run_forecast

class TestForecasting(unittest.TestCase):
    def test_run_forecast_output(self):
        df = run_forecast(silent=True)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn("item", df.columns)
        self.assertIn("base", df.columns)
        self.assertIn("current_stock", df.columns)
        self.assertIn("avg_daily_forecast", df.columns)
        
if __name__ == '__main__':
    unittest.main()
