# utils/validators.py
import re


def validate_password(password):
    """
    Memvalidasi kekuatan password.

    Rules:
    - Minimal 8 karakter
    - Mengandung huruf besar
    - Mengandung huruf kecil
    - Mengandung angka
    - Mengandung karakter spesial (!@#$%^&*)

    Returns:
        dict: {'is_valid': bool, 'errors': list}
    """
    errors = []

    if len(password) < 8:
        errors.append("Password harus minimal 8 karakter")

    if not re.search(r'[A-Z]', password):
        errors.append("Password harus mengandung huruf besar")

    if not re.search(r'[a-z]', password):
        errors.append("Password harus mengandung huruf kecil")

    if not re.search(r'[0-9]', password):
        errors.append("Password harus mengandung angka")

    if not re.search(r'[!@#$%^&*]', password):
        errors.append("Password harus mengandung karakter spesial (!@#$%^&*)")

    return {
        'is_valid': len(errors) == 0,
        'errors': errors
    }
