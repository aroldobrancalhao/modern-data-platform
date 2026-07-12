from simulator.domain.customer.service import CustomerService
from simulator.domain.catalog.seller_service import SellerService
from simulator.domain.catalog.category_service import CategoryService
from simulator.domain.catalog.product_service import ProductService
from simulator.domain.inventory.warehouse_service import WarehouseService
from simulator.domain.inventory.inventory_service import InventoryService
from simulator.domain.orders.order_service import OrderService


class MarketplaceScheduler:
    def __init__(self) -> None:
        self._customer_service = CustomerService()
        self._seller_service = SellerService()
        self._category_service = CategoryService()
        self._product_service = ProductService()
        self._warehouse_service = WarehouseService()
        self._inventory_service = InventoryService()
        self._order_service = OrderService()

    def run(self) -> None:
        customer = self._customer_service.create_customer()
        print(f"Customer created: {customer.customer_id}")

        seller = self._seller_service.create_seller()
        print(f"Seller created: {seller.seller_id}")

        category = self._category_service.create_category()
        print(f"Category created: {category.category_id}")

        product = self._product_service.create_product()
        print(f"Product created: {product.product_id}")

        warehouse = self._warehouse_service.create_warehouse()
        print(f"Warehouse created: {warehouse.warehouse_id}")

        inventory = self._inventory_service.create_inventory()
        print(f"Inventory created: {inventory.inventory_id}")

        order = self._order_service.create_order()
        print(f"Order created: {order.order_number}")