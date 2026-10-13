def get_price(price, quantity):
    return price * quantity


def calculate_tax(amount):
    return amount * 0.20


def calculate_total(price, quantity):
    subtotal = get_price(price, quantity)
    tax = calculate_tax(subtotal)
    return subtotal + tax