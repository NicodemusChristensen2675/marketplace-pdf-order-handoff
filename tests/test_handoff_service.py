import base64

from marketplace_handoff.forms_service import OrderHandoffService, demo_request


class FakeInfraiClient:
    def __init__(self) -> None:
        self.calls = []

    def pdf_generate(self, *, template_html: str, template_vars: dict, store: bool = False) -> dict:
        self.calls.append(
            {
                "template_html": template_html,
                "template_vars": template_vars,
                "store": store,
            }
        )
        fake_pdf = base64.b64encode(b"%PDF-1.4 fake marketplace handoff").decode("ascii")
        return {
            "ok": True,
            "data": {"pdf": fake_pdf},
            "error": None,
            "metadata": {},
        }


def test_complete_buyer_update_moves_order_to_ready_and_marks_flattened() -> None:
    fake = FakeInfraiClient()
    service = OrderHandoffService(fake)

    artifact = service.create_handoff(demo_request())

    assert artifact.status == "ready_for_handoff"
    assert artifact.filename == "handoff-ORD-1001.pdf"
    assert "Flattened for warehouse handoff: yes" in artifact.html_snapshot
    assert fake.calls[0]["store"] is False
    assert fake.calls[0]["template_vars"] == {}


def test_url_response_contains_pdf_data_uri() -> None:
    class UrlInfraiClient(FakeInfraiClient):
        def pdf_generate(self, *, template_html: str, template_vars: dict, store: bool = False) -> dict:
            return {"ok": True, "data": {"url": "data:application/pdf;base64," + base64.b64encode(b"%PDF-1.4 example").decode("ascii")}}

    artifact = OrderHandoffService(UrlInfraiClient()).create_handoff(demo_request())

    assert base64.b64decode(artifact.pdf_base64) == b"%PDF-1.4 example"
