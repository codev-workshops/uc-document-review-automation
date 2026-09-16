"""Configured field groups used by the comparison agent."""

NAME_FIELDS = {"borrower_name", "original_borrower", "new_borrower", "recipient_name"}
ADDRESS_FIELDS = {"property_address", "recipient_address"}
AMOUNT_FIELDS = {"loan_amount", "original_amount", "current_balance", "new_payment_amount"}
RATE_FIELDS = {"interest_rate", "new_interest_rate", "coverage_percentage"}
DATE_FIELDS = {"maturity_date", "new_maturity_date", "modification_date", "effective_date"}
