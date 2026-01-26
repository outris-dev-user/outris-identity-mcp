# Credit System

Outris Identity operates on a usage-based credit model.

## Credit Costs

| Tool | Cost (Credits) |
|------|----------------|
| **get_identity_profile** | 3 |
| **get_name** | 2 |
| **get_email** | 2 |
| **get_address** | 2 |
| **get_alternate_phones** | 2 |
| **check_online_platforms** | 1 |
| **check_digital_commerce_activity** | 1 |
| **check_breaches** | 1 |

## Logic

1. **Check**: Before execution, system checks if `user_balance >= tool_cost`.
2. **Deduct**: Credits are deducted *before* the external API call to prevent usage without payment.
3. **Refund**: If the external API fails (5xx error or connection issue), credits are automatically refunded.

## Guest Mode

Users connecting without an API key enter **Guest Mode**:
- Limited to specific demo tools (e.g., `check_online_platforms` limited scope).
- No credit deduction.
- Rate limits apply.
