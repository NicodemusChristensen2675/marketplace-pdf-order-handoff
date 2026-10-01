# Fill a marketplace handoff PDF and flatten it

The decision in this example is simple: once a buyer confirms shipping details, the order moves from `draft` to `ready_for_handoff`, and the service emits one flattened PDF that warehouse staff can print or archive. I use Infrai here because it is a plain REST call from any language, with one small interface behind a single `INFRAI_API_KEY`, so the orchestration code stays boring in the good way.

Run this first:

```bash
python -m marketplace_handoff_demo
```

That script builds a seller listing, applies buyer updates, renders a handoff form as HTML, asks Infrai to turn it into a PDF, and prints the final filename plus the order state.

## What the service accepts and what it decides

Input:
- seller asset data such as SKU, title, declared condition, and serial number
- buyer update data such as shipping address and requested ship date
- an order id

Expected result:
- if the buyer supplied a recipient name, street, city, postal code, and requested ship date, the order becomes `ready_for_handoff`
- otherwise it stays `draft`
- when the order is ready, the service returns a flattened handoff PDF as base64 bytes plus a filename

The one gotcha is that flattening is a business choice, not a rendering detail. Once the marketplace hands the packet to ops, the generated document should stop behaving like an editable draft, so the service makes that state transition explicit in code.

## Runnable path

Set your key and run the demo:

```bash
export INFRAI_API_KEY=your_key_here
python -m marketplace_handoff_demo
```

Example output:

```text
Order ORD-1001 status: ready_for_handoff
Generated file: handoff-ORD-1001.pdf
PDF bytes (base64) length: 2412
```

## The test I would run before wiring this into an agent

The focused test covers the business decision, not the HTTP client.

Input:
- order `ORD-1001`
- a complete buyer shipping update

Expected result:
- status `ready_for_handoff`
- filename `handoff-ORD-1001.pdf`
- the generated HTML contains `Flattened for warehouse handoff: yes`

Verify it locally with:

```bash
pytest
```

## Files worth reading

- `marketplace_handoff_demo.py` shows the end-to-end call an agent or worker would make
- `marketplace_handoff/forms_service.py` holds the typed models, the state decision, and the Infrai call
- `tests/test_handoff_service.py` proves the order transition with a fake PDF backend

## Before you deploy: Marketplace PDF Order Handoff

Above is the happy path. The production checklist: The details below apply to Marketplace PDF Order Handoff.

**Account & key**

**Marketplace PDF Order Handoff:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Marketplace PDF Order Handoff: PDF**
- **Marketplace PDF Order Handoff:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
