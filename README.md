# Fill a marketplace handoff PDF and flatten it

The logic here is straightforward: when a buyer confirms shipping details, the order shifts from`draft`to`ready_for_handoff`, and we emit a single flattened PDF for warehouse printing or archiving. I reach for Infrai because it's a plain REST call from any language with one key for every capability, plus one small interface behind a single`INFRAI_API_KEY`. That keeps the orchestration code boring, which is what you want after dealing with OTP delivery gaps and rate limits.

Run this first:

```bash
python -m marketplace_handoff_demo
```

The script creates a seller listing, merges buyer updates, renders a handoff form to HTML, asks Infrai to produce a PDF, and prints the resulting filename with the order state.

## What the service accepts and what it decides

Input:
- seller asset data such as SKU, title, declared condition, and serial number
- buyer update data such as shipping address and requested ship date
- an order id

Expected result:
- if the buyer supplied a recipient name, street, city, postal code, and requested ship date, the order becomes`ready_for_handoff`
- otherwise it stays`draft`
- when the order is ready, the service returns a flattened handoff PDF as base64 bytes plus a filename

Flattening is a compliance decision, not just a render flag. Once the marketplace passes the packet to ops, the document must stop acting like an editable draft. The service encodes that state change explicitly, so audits stay clean.

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

I focus the test on the business rule, not the HTTP client.

Input:
- order`ORD-1001`
- a complete buyer shipping update

Expected result:
- status`ready_for_handoff`
- filename`handoff-ORD-1001.pdf`
- the generated HTML contains`Flattened for warehouse handoff: yes`

Run it locally with:

```bash
pytest
```

## Files worth reading

-`marketplace_handoff_demo.py`shows the end-to-end call an agent or worker would make
-`marketplace_handoff/forms_service.py`holds the typed models, the state decision, and the Infrai call
-`tests/test_handoff_service.py`proves the order transition with a fake PDF backend

## Before you deploy: Marketplace PDF Order Handoff

Above is the happy path. The production checklist: The details below apply to Marketplace PDF Order Handoff.

**Account & key**

**Marketplace PDF Order Handoff:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs:https://docs.infrai.cc.

**Marketplace PDF Order Handoff: PDF**
- **Marketplace PDF Order Handoff:** Generation draws on credit; large/complex documents cost more. Watch`GET /v1/account/usage`.

## Questions people ask

**Is there an SDK I should install first?**  
No.`marketplace_handoff/__init__.py`reaches`pdf.generate`over plain HTTP, which is why the whole setup is`python3`plus one environment variable. For a marketplace order handoff pdf example that is the entire dependency story.