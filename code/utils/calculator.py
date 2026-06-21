# utils/calculator.py


def add(a, b):
    """Menjumlahkan dua bilangan."""
    return a + b


def subtract(a, b):
    """Mengurangkan bilangan b dari a."""
    return a - b


def multiply(a, b):
    """Mengalikan dua bilangan."""
    return a * b


def divide(a, b):
    """Membagi bilangan a dengan b."""
    if b == 0:
        raise ValueError("Tidak bisa membagi dengan nol!")
    return a / b
