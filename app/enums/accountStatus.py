from .basicEnum import BasicEnum


class AccountStatus(BasicEnum):
    Active = "Active"
    Inactive = "Inactive" # email not confirmed
    # Blocked = "Blocked" cannot access the plateforme because he letf the company
