import unittest

from my_stock_web.view_models import stock_display_name


class StockDisplayNameTests(unittest.TestCase):
    def test_uses_korean_company_name(self) -> None:
        self.assertEqual(stock_display_name("KRX", "005930"), "삼성전자")
        self.assertEqual(stock_display_name("NASDAQ", "MSFT"), "마이크로소프트")
        self.assertEqual(stock_display_name("NYSE", "SPOT"), "스포티파이")

    def test_falls_back_to_ticker(self) -> None:
        self.assertEqual(stock_display_name("TEST-EXCHANGE", "TEST"), "TEST")


if __name__ == "__main__":
    unittest.main()
