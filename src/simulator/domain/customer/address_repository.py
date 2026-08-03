from simulator.core.batch_writer import BatchWriter
from simulator.domain.customer.address_model import CustomerAddress


class CustomerAddressRepository:
    def __init__(self, writer: BatchWriter) -> None:
        self._writer = writer

    def insert(
        self,
        address: CustomerAddress,
    ) -> None:
        self._writer.add(
            "marketplace.customer_addresses",
            (
                "address_id",
                "customer_id",
                "address_type",
                "street",
                "street_number",
                "complement",
                "district",
                "city",
                "state",
                "country",
                "postal_code",
                "is_default",
                "created_at",
                "updated_at",
            ),
            (
                address.address_id,
                address.customer_id,
                address.address_type,
                address.street,
                address.street_number,
                address.complement,
                address.district,
                address.city,
                address.state,
                address.country,
                address.postal_code,
                address.is_default,
                address.created_at,
                address.updated_at,
            ),
        )
