from time import sleep

from psycopg import Connection

from simulator.core.batch_writer import BatchWriter
from simulator.core.database import Database
from simulator.core.reference_pool import ReferencePool
from simulator.core.seed import seed_carriers
from simulator.core.seed import seed_payment_methods
from simulator.core.settings import get_settings
from simulator.domain.catalog.category_service import CategoryService
from simulator.domain.catalog.product_service import ProductService
from simulator.domain.catalog.seller_service import SellerService
from simulator.domain.customer.customer_service import CustomerService
from simulator.domain.inventory.inventory_service import InventoryService
from simulator.domain.inventory.restock_service import RestockService
from simulator.domain.inventory.warehouse_service import WarehouseService
from simulator.domain.logistics.shipment_service import ShipmentService
from simulator.domain.orders.order_service import OrderService
from simulator.domain.payments.payment_service import PaymentService
from simulator.domain.reviews.review_service import ReviewService


class MarketplaceScheduler:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._database = Database()

        self._customer_service = CustomerService()
        self._seller_service = SellerService()
        self._category_service = CategoryService()
        self._product_service = ProductService()
        self._warehouse_service = WarehouseService()
        self._inventory_service = InventoryService()
        self._restock_service = RestockService()
        self._order_service = OrderService()
        self._payment_service = PaymentService()
        self._shipment_service = ShipmentService()
        self._review_service = ReviewService()

    def run_cycle(
        self,
        connection: Connection,
        writer: BatchWriter,
        pool: ReferencePool,
    ) -> None:
        customer = self._customer_service.create_customer(connection, writer, pool)
        print(f"Customer created: {customer.customer_id}")

        seller = self._seller_service.create_seller(connection, pool)
        print(f"Seller created: {seller.seller_id}")

        category = self._category_service.create_category(connection, pool)
        print(f"Category created: {category.category_id}")

        product = self._product_service.create_product(connection, pool)
        print(f"Product created: {product.product_id}")

        warehouse = self._warehouse_service.create_warehouse(connection)
        print(f"Warehouse created: {warehouse.warehouse_id}")

        inventory = self._inventory_service.create_inventory(connection, pool)
        print(f"Inventory created: {inventory.inventory_id}")

        order = self._order_service.create_order(connection, writer, pool)
        print(f"Order created: {order.order_number}")

        if self._settings.enable_payments:
            payment = self._payment_service.create_payment(writer, pool)
            print(f"Payment created: {payment.payment_id} ({payment.status})")

        if self._settings.enable_shipments:
            shipment = self._shipment_service.create_shipment(writer, pool)
            print(f"Shipment created: {shipment.shipment_id} ({shipment.status})")

        if self._settings.enable_reviews:
            review = self._review_service.create_review(writer, pool)
            print(f"Review created: {review.review_id} ({review.rating}★)")

        self._restock_service.maybe_restock(
            connection,
            self._settings.simulator_restock_probability,
        )

    def run_batch(self) -> None:
        print(f"\nStarting batch with {self._settings.simulator_batch_size} cycle(s)\n")

        with self._database.connection() as connection:
            pool = ReferencePool()
            pool.payment_method_ids = seed_payment_methods(connection)
            pool.carrier_ids = seed_carriers(connection)

            writer = BatchWriter(
                connection,
                flush_threshold=self._settings.simulator_insert_batch_size,
            )

            for index in range(self._settings.simulator_batch_size):
                print(f"========== Cycle {index + 1} ==========")

                self.run_cycle(connection, writer, pool)

            writer.flush()

        print("\nBatch finished.\n")

    def run(self) -> None:
        self.run_batch()

    def run_forever(self) -> None:
        while True:
            self.run_batch()

            print(f"Waiting {self._settings.simulator_interval_seconds} second(s)...")

            sleep(self._settings.simulator_interval_seconds)
