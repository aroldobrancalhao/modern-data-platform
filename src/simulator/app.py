from simulator.domain.customer.service import CustomerService


def main() -> None:
    service = CustomerService()

    customer = service.create_customer()

    print(f"Customer created: {customer.customer_id}")


if __name__ == "__main__":
    main()