from .basicEnum import BasicEnum

class RoleType(BasicEnum):
    Admin="Admin"
    InventoryManager="InventoryManager"
    Superuser="Superuser"
    Vendor = "Vendor"