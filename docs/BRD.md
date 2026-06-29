# Boujuron Banking Fraud Protection BRD

## Business Problem

Banks, fintechs, wallets, and payment processors need to detect suspicious money movement quickly without turning every unusual customer action into a hard block. Fraud teams face debit fraud, suspicious inflows, mule accounts, bot attacks, account takeovers, repeated failed payments, and post-incident reversals. If the system is too soft, funds leave before analysts respond. If it is too harsh, legitimate customers are blocked and support workload increases.

Boujuron is designed as a balanced fraud protection platform: it scores risk, separates severity from confidence, recommends the right level of intervention, and keeps a full audit trail for every decision.

## Target Users

- Fraud analysts who review suspicious transactions and close investigations.
- Financial crime teams that monitor suspicious inflows, mule behavior, and transaction abuse.
- Risk managers who configure policies and monitor operational workload.
- Engineering teams that integrate fraud decisions into login, wallet, debit, and credit flows.
- Executives who need visibility into fraud prevention, reversals, and false positives.

## Banking Fraud Pain Points

- Debit fraud: unauthorized transfers, new beneficiary abuse, high-velocity outflows, late-night transactions, suspicious devices, blacklisted IPs, and ATO-driven transfers.
- Credit fraud: unusual inflows, rapid credits from many sources, mule account behavior, dormant accounts receiving large credits, chargeback/reversal risk, and suspicious credit/debit sequences.
- Analyst overload: high alert volume means teams cannot manually inspect every case before funds move.
- False positives: unnecessary PND or blocks damage customer trust and increase support tickets.
- Audit pressure: institutions must explain who acted, why they acted, and when decisions were reversed.

## Debit Fraud Use Cases

- Large transfer from a new or rooted device.
- Repeated failed payment attempts followed by a successful debit.
- New beneficiary added before a high-value transfer.
- Transfer from a high-risk IP, VPN, TOR, or unusual location.
- Repetitive outflows that indicate account compromise or mule movement.

## Credit Fraud Use Cases

- Dormant account suddenly receives a large credit.
- Multiple rapid credits arrive from different sources.
- Incoming funds are followed quickly by suspicious debits.
- Sender/channel pattern indicates high reversal or chargeback risk.
- Account behavior resembles mule pass-through movement.

## Customer Experience Principle

Boujuron should not be a harsh blocking system. Low-risk activity should be allowed. Moderate risk should use step-up verification. Strong suspicious activity should be held for review. Only highly confident fraud should trigger PND or hard block.

## Why False Positives Must Be Reduced

False positives create customer frustration, failed transactions, support escalations, and reputational damage. A balanced decision model protects funds while reducing unnecessary friction.

## Why PND Is Reserved For Severe Cases

Post No Debit is operationally serious. It should only be used when the engine sees strong fraud evidence, high risk score, and high confidence. Boujuron keeps PND decisions auditable and reversible.

## Business Value

Boujuron helps institutions reduce fraud loss, shorten analyst review time, improve customer trust, standardize case handling, and produce audit-ready records. The platform supports both API-first automated decisioning and dashboard-first investigation workflows.
