"""Verify compliance report correctness against regulatory rules."""

import json
from datetime import datetime


def test_report_schema():
    """Verify the compliance report JSON has the required schema."""
    with open("/app/compliance_report.json", "r") as f:
        report = json.load(f)
    
    assert "total_transactions" in report
    assert isinstance(report["total_transactions"], int)
    assert "violations" in report
    assert "severity" in report
    assert report["severity"] in ["low", "medium", "high"]
    assert "summary" in report
    assert isinstance(report["summary"], str)
    
    # Check violations structure
    violations = report["violations"]
    assert "kyc" in violations and isinstance(violations["kyc"], list)
    assert "aml" in violations and isinstance(violations["aml"], list)
    assert "sanctions" in violations and isinstance(violations["sanctions"], list)
    assert "jurisdiction" in violations and isinstance(violations["jurisdiction"], list)


def test_kyc_violations():
    """Test that KYC violations are correctly identified for >$10k individual transactions."""
    with open("/app/transactions.csv", "r") as f:
        lines = f.readlines()
    
    with open("/app/compliance_report.json", "r") as f:
        report = json.load(f)
    
    # Parse CSV manually to verify logic
    import csv
    with open("/app/transactions.csv", "r") as f:
        reader = csv.DictReader(f)
        kyc_should_trigger = []
        for row in reader:
            if (row.get("customer_type") == "individual" and 
                float(row.get("amount", 0)) > 10000 and 
                row.get("jurisdiction") not in ["USA", "UK", "Canada", "Australia", "Japan"]):
                kyc_should_trigger.append(row["transaction_id"])
    
    flagged_kyc = [v["transaction_id"] for v in report["violations"]["kyc"]]
    assert set(flagged_kyc) == set(kyc_should_trigger), \
        f"KYC violations mismatch: expected {kyc_should_trigger}, got {flagged_kyc}"


def test_sanctions_violations():
    """Test that OFAC SDN list is correctly enforced."""
    with open("/app/compliance_report.json", "r") as f:
        report = json.load(f)
    
    sanctions = report["violations"]["sanctions"]
    ofac_list = {"Iran", "Syria", "North Korea", "Cuba"}
    for v in sanctions:
        assert "transaction_id" in v
        assert "counterparty_country" in v
        assert v["counterparty_country"] in ofac_list, \
            f"Sanctions violation country {v['counterparty_country']} not in OFAC list"


def test_severity_logic():
    """Test that severity is correctly determined based on violation count."""
    with open("/app/compliance_report.json", "r") as f:
        report = json.load(f)
    
    total_violations = sum(len(v) for v in report["violations"].values())
    severity = report["severity"]
    
    if report["violations"]["sanctions"] or total_violations >= 3:
        assert severity == "high", f"Expected 'high' severity but got '{severity}' with {total_violations} violations"
    elif total_violations >= 1:
        assert severity == "medium", f"Expected 'medium' severity but got '{severity}' with {total_violations} violations"
    else:
        assert severity == "low", f"Expected 'low' severity but got '{severity}' with {total_violations} violations"


def test_transactions_counted():
    """Verify transaction count is correct."""
    import csv
    with open("/app/transactions.csv", "r") as f:
        reader = csv.DictReader(f)
        expected_count = sum(1 for row in reader if row and any(row.values()))
    
    with open("/app/compliance_report.json", "r") as f:
        report = json.load(f)
    
    assert report["total_transactions"] == expected_count, \
        f"Transaction count mismatch: expected {expected_count}, got {report['total_transactions']}"
