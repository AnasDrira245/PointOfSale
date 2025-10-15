from .basicEnum import BasicEnum


class RoleType(BasicEnum):
    ADMIN = "ADMIN"
    InventoryManager = "InventoryManager"
    Superuser = "Superuser"
    Vendor = "Vendor"
