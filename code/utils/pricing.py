# utils/pricing.py


def calculate_discount(price, discount_percentage):
    """Menghitung harga setelah diskon."""
    if discount_percentage < 0 or discount_percentage > 100:
        raise ValueError("Discount harus antara 0 dan 100")
    discount_amount = price * (discount_percentage / 100)
    return price - discount_amount
