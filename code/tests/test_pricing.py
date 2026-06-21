# tests/test_pricing.py
from django.test import TestCase
from utils.pricing import calculate_discount


class TestCalculateDiscount(TestCase):
    """Unit test: menguji fungsi calculate_discount secara terisolasi."""

    def test_normal_discount(self):
        """Test diskon 20% dari harga 100000."""
        result = calculate_discount(100000, 20)
        self.assertEqual(result, 80000)

    def test_zero_discount(self):
        """Test tanpa diskon."""
        result = calculate_discount(100000, 0)
        self.assertEqual(result, 100000)

    def test_full_discount(self):
        """Test diskon 100%."""
        result = calculate_discount(100000, 100)
        self.assertEqual(result, 0)

    def test_invalid_discount_negative(self):
        """Test diskon negatif."""
        with self.assertRaises(ValueError):
            calculate_discount(100000, -10)

    def test_invalid_discount_over_100(self):
        """Test diskon lebih dari 100%."""
        with self.assertRaises(ValueError):
            calculate_discount(100000, 150)
