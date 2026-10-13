from checkout import checkout


def print_receipt(price, quantity):
    total = checkout(price, quantity)
    return f"Total: {total}"