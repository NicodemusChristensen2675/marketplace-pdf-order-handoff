from marketplace_handoff import InfraiClient, OrderHandoffService
from marketplace_handoff.forms_service import decode_pdf_size, demo_request


def main() -> None:
    infrai = InfraiClient()
    service = OrderHandoffService(infrai)
    artifact = service.create_handoff(demo_request())
    print(f"Order {artifact.order_id} status: {artifact.status}")
    print(f"Generated file: {artifact.filename}")
    print(f"PDF bytes (base64) length: {len(artifact.pdf_base64)}")
    print(f"Decoded PDF size: {decode_pdf_size(artifact.pdf_base64)} bytes")


if __name__ == "__main__":
    main()
