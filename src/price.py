class Price(int):
    """ValueObject for price"""

    def __new__(cls, value):
        integer = super().__new__(cls, value)  # let int handle coercion
        if integer < 0:
            raise ValueError('Invalid value: please provide a non-negative whole number')
        if integer > 999_999_999:
            raise ValueError('Invalid value: number too large')
        return integer
