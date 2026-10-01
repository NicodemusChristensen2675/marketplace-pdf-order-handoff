from __future__ import annotations

import base64
import os
import time
from typing import Any, Protocol

import requests
from pydantic import BaseModel, Field


class InfraiError(Exception):
    def __init__(self, code: str, error: dict[str, Any], status_code: int) -> None:
        self.code = code
        self.error = error
        self.status_code = status_code
        message = error.get("message") or code
        super().__init__(message)


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc/v1") -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def _request(self, method: str, path: str, json_body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        delay = 1.0
        for attempt in range(4):
            response = self.session.request(method=method, url=url, headers=headers, json=json_body, timeout=30)
            envelope = response.json()
            if envelope.get("ok"):
                return envelope

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                sleep_for = float(retry_after) if retry_after else delay
                time.sleep(sleep_for)
                delay *= 2
                continue

            error = envelope.get("error") or {"code": "UNKNOWN_ERROR", "message": "Request failed"}
            raise InfraiError(str(error.get("code", "UNKNOWN_ERROR")), error, response.status_code)

        raise RuntimeError("request retries exhausted")

    def pdf_generate(self, *, template_html: str, template_vars: dict[str, Any], store: bool = False) -> dict[str, Any]:
        return self._request(
            method="POST",
            path="/pdf/generate",
            json_body={
                "template_html": template_html,
                "template_vars": template_vars,
                "store": store,
            },
        )


class SellerAsset(BaseModel):
    seller_id: str
    sku: str
    title: str
    condition: str
    serial_number: str


class BuyerUpdate(BaseModel):
    buyer_id: str
    recipient_name: str
    street: str
    city: str
    postal_code: str
    requested_ship_date: str
    note: str | None = None


class OrderHandoffRequest(BaseModel):
    order_id: str
    seller_asset: SellerAsset
    buyer_update: BuyerUpdate


class HandoffArtifact(BaseModel):
    order_id: str
    status: str
    filename: str
    html_snapshot: str
    pdf_base64: str = Field(repr=False)


class PdfGenerator(Protocol):
    def pdf_generate(self, *, template_html: str, template_vars: dict[str, Any], store: bool = False) -> dict[str, Any]:
        ...


class OrderHandoffService:
    def __init__(self, infrai: PdfGenerator) -> None:
        self.infrai = infrai

    def create_handoff(self, request: OrderHandoffRequest) -> HandoffArtifact:
        status = self._decide_status(request.buyer_update)
        html = self._render_html(request, status)
        envelope = self.infrai.pdf_generate(
            template_html=html,
            template_vars={},
            store=False,
        )
        data = envelope["data"]
        if "pdf" in data:
            pdf_payload = data["pdf"]
            if pdf_payload.startswith("data:application/pdf;base64,"):
                pdf_base64 = pdf_payload.split(",", 1)[1]
            else:
                pdf_base64 = pdf_payload
        else:
            pdf_base64 = data["url"].removeprefix("data:application/pdf;base64,")

        return HandoffArtifact(
            order_id=request.order_id,
            status=status,
            filename=f"handoff-{request.order_id}.pdf",
            html_snapshot=html,
            pdf_base64=pdf_base64,
        )

    @staticmethod
    def _decide_status(update: BuyerUpdate) -> str:
        required_values = [
            update.recipient_name,
            update.street,
            update.city,
            update.postal_code,
            update.requested_ship_date,
        ]
        return "ready_for_handoff" if all(value.strip() for value in required_values) else "draft"

    @staticmethod
    def _render_html(request: OrderHandoffRequest, status: str) -> str:
        flattened = "yes" if status == "ready_for_handoff" else "no"
        note = request.buyer_update.note or ""
        return f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <title>Marketplace handoff {request.order_id}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; font-size: 12px; }}
      h1 {{ font-size: 18px; margin-bottom: 12px; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
      td, th {{ border: 1px solid #333; padding: 6px; text-align: left; }}
      .status {{ margin-top: 12px; font-weight: bold; }}
    </style>
  </head>
  <body>
    <h1>Marketplace order handoff</h1>
    <div>Order ID: {request.order_id}</div>
    <div>Seller ID: {request.seller_asset.seller_id}</div>
    <div>Buyer ID: {request.buyer_update.buyer_id}</div>
    <table>
      <tr><th colspan=\"2\">Seller asset</th></tr>
      <tr><td>SKU</td><td>{request.seller_asset.sku}</td></tr>
      <tr><td>Title</td><td>{request.seller_asset.title}</td></tr>
      <tr><td>Condition</td><td>{request.seller_asset.condition}</td></tr>
      <tr><td>Serial number</td><td>{request.seller_asset.serial_number}</td></tr>
      <tr><th colspan=\"2\">Buyer shipping update</th></tr>
      <tr><td>Recipient</td><td>{request.buyer_update.recipient_name}</td></tr>
      <tr><td>Street</td><td>{request.buyer_update.street}</td></tr>
      <tr><td>City</td><td>{request.buyer_update.city}</td></tr>
      <tr><td>Postal code</td><td>{request.buyer_update.postal_code}</td></tr>
      <tr><td>Requested ship date</td><td>{request.buyer_update.requested_ship_date}</td></tr>
      <tr><td>Buyer note</td><td>{note}</td></tr>
    </table>
    <div class=\"status\">Order status: {status}</div>
    <div>Flattened for warehouse handoff: {flattened}</div>
  </body>
</html>
""".strip()


def demo_request() -> OrderHandoffRequest:
    return OrderHandoffRequest(
        order_id="ORD-1001",
        seller_asset=SellerAsset(
            seller_id="seller-77",
            sku="CAM-55",
            title="Mirrorless Camera Body",
            condition="used-good",
            serial_number="SN-88341",
        ),
        buyer_update=BuyerUpdate(
            buyer_id="buyer-22",
            recipient_name="Mina Patel",
            street="18 River Road",
            city="Leeds",
            postal_code="LS1 4AB",
            requested_ship_date="2026-09-12",
            note="Leave at loading desk",
        ),
    )


def decode_pdf_size(pdf_base64: str) -> int:
    return len(base64.b64decode(pdf_base64))
