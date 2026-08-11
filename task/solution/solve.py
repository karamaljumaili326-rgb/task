#!/usr/bin/env python3
"""Reference solution for compliance report generation."""

import csv
import json
from datetime import datetime
from collections import defaultdict

# Hardcoded OFAC SDN list
OFAC_SDN = {"Iran", "Syria", "North Korea", "Cuba"}

# Parse input files
transactions = []
with open("/app/transactions.csv", "r") as f:
    reader = csv.DictReader(f)
    if reader.fieldnames is None:
        reader.fieldnames = []
    for row in reader:
        if not row or not any(row.values()):
            continue
        try:
            row["amount"] = float(row["amount"])
            row["date"] = datetime.strptime(row["date"], "%Y-%m-%d")
            transactions.append(row)
        except (ValueError, KeyError):
            pass

# Load approvals
approvals = {}
try:
    with open("/app/approvals.txt", "r") as f:
        for line in f:
            line = line.strip()
            if ":" in line:
                tid, status = line.split(":", 1)
                approvals[tid.strip()] = status.strip()
except FileNotFoundError:
    pass

violations = {
    "kyc": [],
    "aml": [],
    "sanctions": [],
    "jurisdiction": []
}

# Rule 1: KYC — amount > $10,000 from individual to non-FATF jurisdiction
for tx in transactions:
    if (tx.get("customer_type") == "individual" and 
        tx.get("amount", 0) > 10000 and 
        tx.get("jurisdiction") not in ["USA", "UK", "Canada", "Australia", "Japan"]):
        violations["kyc"].append({
            "transaction_id": tx["transaction_id"],
            "reason": "Individual transaction >$10,000 to non-FATF jurisdiction without KYC documentation"
        })

# Rule 2: AML — transactions >$50,000 from business to same counterparty within 7 days
business_txs = defaultdict(list)
for tx in transactions:
    if tx.get("customer_type") == "business" and tx.get("amount", 0) > 50000:
        business_txs[tx.get("counterparty_country")].append(tx)

for counterparty, txs_list in business_txs.items():
    txs_list.sort(key=lambda x: x["date"])
    for i, tx in enumerate(txs_list):
        within_7days = [t for t in txs_list if (t["date"] - tx["date"]).days <= 7 and t["date"] >= tx["date"]]
        if len(within_7days) > 1:
            violations["aml"].append({
                "transaction_id": tx["transaction_id"],
                "count": len(within_7days)
            })

# Rule 3: Sanctions — counterparty country in OFAC list
for tx in transactions:
    if tx.get("counterparty_country") in OFAC_SDN:
        violations["sanctions"].append({
            "transaction_id": tx["transaction_id"],
            "counterparty_country": tx["counterparty_country"]
        })

# Rule 4: Jurisdiction — certain jurisdictions require approval
restricted_jurisdictions = {"Iran", "Syria", "North Korea", "Cuba"}
for tx in transactions:
    if (tx.get("jurisdiction") in restricted_jurisdictions and 
        tx.get("amount", 0) > 5000):
        if tx["transaction_id"] not in approvals:
            violations["jurisdiction"].append({
                "transaction_id": tx["transaction_id"],
                "required_jurisdiction": tx["jurisdiction"],
                "missing_approval": True
            })

# Determine severity
total_violations = sum(len(v) for v in violations.values())
if violations["sanctions"] or total_violations >= 3:
    severity = "high"
elif total_violations >= 1:
    severity = "medium"
else:
    severity = "low"

# Build report
report = {
    "total_transactions": len(transactions),
    "violations": violations,
    "severity": severity,
    "summary": f"Found {total_violations} compliance violations across {len(transactions)} transactions. Severity: {severity}."
}

# Write output
with open("/app/compliance_report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Compliance report generated:", json.dumps(report, indent=2))
