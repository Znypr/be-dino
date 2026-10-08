# Player access and paid random items

2026-10-08 — owner direction: enable as many eligible players as possible to
play Be Dino. Do not exclude a player from the whole game merely because they
cannot use paid random rewards.

Planned behavior:
- Check PolicyService:GetPolicyInfoForPlayerAsync on the server.
- When ArePaidRandomItemsRestricted is true, block paid random nests and every
  indirect paid-currency route. Keep normal gameplay and genuinely free earned
  nests available. Guaranteed purchases can remain available where permitted.
- Treat failed or pending policy checks as ineligible for paid random purchases.
- Enforce restrictions on the server as well as in the purchase UI.
- Disclose all possible final outcomes and numerical odds before paid purchase.
- If trading is introduced, enforce IsPaidItemTradingAllowed too.

Questionnaire answers must match the actual published implementation. A
guaranteed nest with random contents is still a paid random item when obtainable
directly or indirectly with Robux. Unverified code is not proof of compliance
or noncompliance: verify the deployed build before answering the API question.
Do not copy assumptions about RIVALS; its implementation has not been verified.

Reference: https://create.roblox.com/docs/production/monetization/paid-random-items

Release tasks (open): verify restricted, unrestricted, failed/pending policy
responses; direct and indirect purchases; free earned rewards; odds disclosure;
published-version parity. Keep paid random items disabled until these pass.
Broader age access also depends on Roblox publishing eligibility, content rating
and audience evaluation; passing this policy alone does not certify all-age reach.
