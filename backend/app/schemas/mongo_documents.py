"""
MongoDB collections and document shapes (operational schema).

Collections
-----------
invoices
  Core document for one uploaded file + extracted intelligence.

Fields (stored as BSON; dates as UTC datetime at midnight for date-only fields)
  _id: ObjectId
  invoice_number: str | null
  invoice_date: datetime | null   (UTC date start)
  due_date: datetime | null
  vendor_name: str | null
  vendor_normalized: str | null   (lowercase stripped for dedup queries)
  total_amount: float | null
  tax_amount: float | null
  currency: str
  line_items: [{ description, quantity, unit_price, amount, optional GST: taxable_value, gst_rate_pct, cgst_amount, sgst_amount, igst_amount, cess_amount }]
  category: str | null
  category_confidence: float | null
  detected_language: str | null
  validation: { is_valid, issues: [{ code, message, severity }], fraud_flags: [str] }
  embedding: list[float] | null   (for semantic search / RAG)
  raw_text: str | null            (optional full text; can be large)
  raw_text_preview: str | null
  storage_path: str
  original_filename: str
  mime_type: str
  extraction_backend: str        (e.g. docling, unstructured)
  created_at: datetime
  updated_at: datetime

Indexes (created in app.db.mongo.ensure_indexes)
  created_at DESC
  vendor_normalized + invoice_number
  invoice_date DESC
  due_date ASC
  category ASC

Neo4j graph (optional)
  (:Invoice {mongo_id, number, total, date})
  (:Vendor {key, name})
  (:Category {name})
  (Invoice)-[:FROM_VENDOR]->(Vendor)
  (Invoice)-[:IN_CATEGORY]->(Category)
"""

COLLECTION_INVOICES = "invoices"
COLLECTION_NOTIFICATIONS = "notifications"
COLLECTION_WORKSPACES = "workspaces"
