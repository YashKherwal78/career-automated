# Eligibility Quality Report
**Raw Opportunities**: 1390
**Eligible**: 517
**Rejected**: 873

## 1. Eligible Role Distribution
- **Other**: 445 (86.1%)
- **Product Manager**: 48 (9.3%)
- **AI Engineer**: 20 (3.9%)
- **AI Product Manager**: 2 (0.4%)
- **Marketing**: 1 (0.2%)
- **Technical Product Manager**: 1 (0.2%)

## 2. Eligible Company Distribution
| Company | Eligible Jobs | Total Discovered | Eligibility Rate |
|---------|---------------|------------------|------------------|
| stripe | 184 | 493 | 37.3% |
| anthropic | 131 | 390 | 33.6% |
| scaleai | 66 | 176 | 37.5% |
| figma | 50 | 171 | 29.2% |
| slice | 47 | 75 | 62.7% |
| phonepe | 31 | 69 | 44.9% |
| groww | 8 | 16 | 50.0% |

## 3. Manual Review Sample (100 Eligible)
- **Definitely Apply**: 17
- **Maybe**: 24
- **Reject**: 59

### Top 10 'Reject' Examples in Eligible Queue
- Solutions Consultant (Berlin, Germany) @ figma
- People Consultant @ stripe
- Anthropic Fellows Program @ anthropic
- Employment Counsel (London, United Kingdom) @ figma
- People Business Partner @ slice
- Operations Specialist @ scaleai
- Future Territory Managers - Connecticut @ slice
- Global People Operations Specialist @ slice
- Product Designer, Growth & Monetization @ figma
- Delivery & Warehouse Associate - Philly (Day Shift) @ slice

## 4. False Negatives (from 50 Rejected sample)
- Staff Software Engineer, People Products @ anthropic (Rejected by REJECT_SENIORITY)
- Product Partner Manager @ figma (Rejected by REJECT_SENIORITY)
- Engineering Manager, Product (Privy) @ stripe (Rejected by REJECT_SENIORITY)
- Strategic Finance, Systems & AI Innovation @ figma (Rejected by REJECT_BUSINESS_DEPT)
- Principal AI Ops Architect, GPS @ scaleai (Rejected by REJECT_SENIORITY)
- Product Marketing Manager, Audience and Messaging @ figma (Rejected by REJECT_SENIORITY)
- Cluster Collection Manager - Chennai @ phonepe (Rejected by REJECT_SENIORITY)
- Sales Enablement & Training Specialist @ stripe (Rejected by REJECT_BUSINESS_DEPT)

## 5. Rule Performance
| Rule | Executions | Accepts | Rejects |
|------|------------|---------|---------|
| REJECT_SENIORITY | 686 | 0 | 686 |
| IMPLICIT_ALLOW | 449 | 449 | 0 |
| REJECT_ENGINEERING_DEPT | 113 | 0 | 113 |
| REJECT_BUSINESS_DEPT | 61 | 0 | 61 |
| ALLOW_PRODUCT_MANAGER | 41 | 41 | 0 |
| ALLOW_AI_PRODUCT | 27 | 27 | 0 |
| REJECT_EMPLOYMENT_TYPE | 13 | 0 | 13 |