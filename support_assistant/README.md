# Zepto Support Assistant

A small offline GenAI/RAG service for answering questions about Zepto delivery, returns, membership, tracking, cancellation, gift cards, damaged/missing items, and customer support policies.

The required graded baseline uses `MOCK_LLM=1` (the default), so no LLM API key or external LLM provider is required.

## Project Structure

```text
support_assistant/
├── docs/
│   ├── doc_01_delivery_policy.txt
│   ├── doc_02_returns_refunds.txt
│   ├── doc_03_membership_tiers.txt
│   ├── doc_04_order_tracking.txt
│   ├── doc_05_order_cancellation.txt
│   ├── doc_06_damaged_missing_items.txt
│   ├── doc_07_gift_cards.txt
│   └── doc_08_customer_support_hours.txt
├── chroma_db/
├── main.py
├── requirements.txt
├── Dockerfile
└── README.md
