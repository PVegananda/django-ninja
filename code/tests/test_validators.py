# tests/test_validators.py
from django.test import TestCase
from utils.validators import validate_password


class TestPasswordValidator(TestCase):
    """Test cases untuk fungsi validate_password."""

    def test_valid_password(self):
        """Test password yang memenuhi semua kriteria."""
        result = validate_password("SecureP@ss1")
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)

    def test_password_too_short(self):
        """Test password yang terlalu pendek."""
        result = validate_password("Ab1!")
        self.assertFalse(result['is_valid'])
        self.assertIn("Password harus minimal 8 karakter", result['errors'])

    def test_password_no_uppercase(self):
        """Test password tanpa huruf besar."""
        result = validate_password("password1!")
        self.assertFalse(result['is_valid'])
        self.assertIn("Password harus mengandung huruf besar", result['errors'])

    def test_password_no_lowercase(self):
        """Test password tanpa huruf kecil."""
        result = validate_password("PASSWORD1!")
        self.assertFalse(result['is_valid'])
        self.assertIn("Password harus mengandung huruf kecil", result['errors'])

    def test_password_no_number(self):
        """Test password tanpa angka."""
        result = validate_password("Password!")
        self.assertFalse(result['is_valid'])
        self.assertIn("Password harus mengandung angka", result['errors'])

    def test_password_no_special_char(self):
        """Test password tanpa karakter spesial."""
        result = validate_password("Password1")
        self.assertFalse(result['is_valid'])
        self.assertIn(
            "Password harus mengandung karakter spesial (!@#$%^&*)",
            result['errors']
        )

    def test_password_multiple_errors(self):
        """Test password dengan banyak error sekaligus."""
        result = validate_password("abc")
        self.assertFalse(result['is_valid'])
        # Harus ada minimal 4 error: pendek, tidak ada uppercase, angka, spesial
        self.assertGreaterEqual(len(result['errors']), 4)

    def test_empty_password(self):
        """Test password kosong."""
        result = validate_password("")
        self.assertFalse(result['is_valid'])
        self.assertGreaterEqual(len(result['errors']), 1)
