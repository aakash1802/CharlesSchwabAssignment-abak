# Examples

## Input brief

```text
Build a command-line tool that reads a CSV of trades and prints the total
market value per account. Market value is quantity times price. The CSV
columns are account, symbol, quantity, and price. Invalid rows are skipped
and counted in a summary line. Do not call any external API.
```

## Spec excerpt that follows the brief

```markdown
## Sources

| Id | Requirement |
| --- | --- |
| R1 | Read a CSV of trades and print total market value per account. |
| R2 | Market value is quantity times price. |
| R3 | CSV columns are account, symbol, quantity, and price. |
| R4 | Invalid rows are skipped and counted in a summary line. |
| R5 | Do not call any external API. |

## Behavior

1. Given a CSV with columns account, symbol, quantity, and price, the solution must print one total market value per account (R1, R2, R3).
2. The solution must skip a row it cannot use and include the skip count in a summary line (R4).
3. The solution must not call an external API (R5).

## Assumptions

- A row is invalid when quantity or price is missing or not numeric. The brief says to skip invalid rows but does not define invalid.

## Open questions

- [ ] What is the exact summary line format?
- [ ] Should account totals be sorted?
```

## Do not do this

The brief does not mention Charles Schwab, authentication, or a database. This is invented scope and must not appear in the spec:

```markdown
The service must authenticate to the Schwab Trader API and store totals in SQLite.
```
