# Support assistant — design

A customer-support chatbot for our B2B SaaS. Each customer company is a tenant.

- Users sign in with the company SSO and chat in a web widget.
- On each question we embed it, search a shared vector index of all tenants'
  help-center articles and past support tickets (top 8 chunks), and send the
  chunks plus the question to an LLM.
- Users can upload PDFs (contracts, invoices) which are chunked into the same index.
- The model can call two tools: `lookup_order(order_id)` and
  `issue_refund(order_id, amount)`; refunds are executed immediately.
- Full prompts and responses are logged to our analytics warehouse for quality review.
- The public widget endpoint has no rate limit yet.
