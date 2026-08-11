You are analyzing compliance records for a financial services company. Your task is to parse and validate a dataset of transaction records, identify regulatory violations, and generate an auditable compliance report.

## Input Files

- `/app/transactions.csv` — A CSV with columns: `transaction_id`, `amount`, `customer_type`, `date`, `jurisdiction`, `counterparty_country`
- `/app/approvals.txt` — Pre-approval records (format: `transaction_id:approval_status`, one per line)

## Requirements

1. **Parse the CSV** and validate that all required fields are present and non-empty.

2. **Identify violations** against these regulatory rules:
   - **KYC Rule**: Any transaction >$10,000 from a `customer_type` of "individual" to a non-FATF jurisdiction requires explicit KYC documentation. Flag if missing.
   - **AML Rule**: Transactions >$50,000 from `customer_type` "business" within a 7-day rolling window to the same counterparty must be reported. Count violations.
   - **Sanctions Rule**: Transactions to counterparty countries in the OFAC SDN list (Iran, Syria, North Korea, Cuba) are blocked. Flag all such transactions.
   - **Jurisdiction Rule**: Transactions from jurisdictions in [Iran, Syria, North Korea, Cuba] with amount >$5,000 require pre-approval from `/app/approvals.txt`. If missing, flag.

3. **Generate `/app/compliance_report.json`** with this exact schema:
   ```json
   {
     "total_transactions": <int>,
     "violations": {
       "kyc": [{"transaction_id": "...", "reason": "..."}],
       "aml": [{"transaction_id": "...", "count": <int>}],
       "sanctions": [{"transaction_id": "...", "counterparty_country": "..."}],
       "jurisdiction": [{"transaction_id": "...", "required_jurisdiction": "...", "missing_approval": true}]
     },
     "severity": "<low|medium|high>",
     "summary": "<brief human-readable summary>"
   }
   ```

4. **Determine severity**:
   - "high" if any sanctions violations or >=3 total violations
   - "medium" if 1-2 total violations
   - "low" if 0 violations

The task is hard because you must:
- Correctly parse and join multiple data sources (CSV + approvals file)
- Implement temporal logic (7-day rolling window for AML) with careful date parsing
- Exactly implement regulatory thresholds (>$10,000 vs. =$10,000)
- Handle edge cases (malformed dates, missing fields, empty files, duplicate transaction IDs)