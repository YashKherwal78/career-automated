# Company Intelligence Database Validation Report

## Infrastructure Metrics
- **Total Companies Imported**: 131
- **Companies with Verified ATS Slugs**: 131
- **Companies with Active Jobs**: 10
- **Failed Syncs**: 0
- **Average Sync Time**: 0.68s per company
- **Total Sync Time**: 88.86s

## ATS Distribution
- **Greenhouse**: 122
- **Lever**: 9

## Hiring Signals (Extracted Natively)
- **Product Manager Jobs**: 87
- **Associate Product Manager Jobs**: 6
- **AI Jobs**: 141
- **Founder's Office Jobs**: 1

## Top Companies by Hiring Volume
| Company | Active Jobs |
|---------|-------------|
| Stripe | 492 |
| Datadog | 412 |
| Anthropic | 392 |
| Brex | 248 |
| Airbnb | 232 |
| Mistral AI | 175 |
| Figma | 170 |
| Vercel | 76 |
| PhonePe | 68 |
| Mercury | 52 |

## Validation Conclusion
The Company Intelligence Database successfully seeded the initial 130+ companies and executed a direct, zero-dependency sync against their native ATS endpoints.
The static schema preserves the long-term CRM graph, while the dynamic schema operationalizes hiring velocity. Discovery is now natively capable of monitoring thousands of startups as a proprietary asset without relying on Apify or search engines.