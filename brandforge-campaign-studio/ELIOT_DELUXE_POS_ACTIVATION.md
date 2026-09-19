# Eliot by Deluxe POS Activation

BrandForge now provides a **non-sensitive POS operations workspace** that converts a generated POS Menu asset into a category-aware service catalog, calculates quote totals, and exports a Deluxe-oriented catalog-and-receipt mapping package. The workflow intentionally does not collect, process, or store any card, wallet, EMV, or PCI-sensitive data.

## Included POS Capabilities

| Capability | Status | Notes |
|---|---:|---|
| Brand-locked service catalog | Ready | Converts generated POS categories and items into a register catalog. |
| Quote register | Ready | Calculates subtotal, configurable sales tax, optional tip, and total in cents. |
| Receipt configuration | Ready | Captures a location label and receipt footer for the mapping package. |
| Deluxe catalog mapping | Ready | Exports a non-sensitive JSON onboarding package. |
| Eliot/Deluxe payment capture | Activation required | Requires merchant-specific credentials and the approved Deluxe integration method. |
| Card-present terminal processing | Activation required | Must use the Deluxe native Mobile POS SDK and supported hardware. |
| Card-not-present checkout | Activation required | Must use Deluxe Hosted Payment Forms or an approved embedded payment flow. |

## Required Merchant Activation Inputs

Deluxe documentation specifies an active merchant account configured for API access, a **Client ID**, **Client Secret**, and **Partner Token** issued by the Deluxe Implementations Team. BrandForge must store these only as server-side secrets under the following names:

| Environment variable | Purpose |
|---|---|
| `DELUXE_CLIENT_ID` | Identifies the BrandForge integration to Deluxe. |
| `DELUXE_CLIENT_SECRET` | Server-only credential used when obtaining a temporary bearer token. |
| `DELUXE_PARTNER_TOKEN` | Identifies the merchant context for permitted Deluxe API requests. |

Before enabling a payment capture button, confirm with Deluxe which product and transaction flow is approved for the merchant: **Hosted Payment Form / embedded web payment** for card-not-present, or **Mobile POS SDK** for card-present transactions. The native mobile SDK is required for physical terminal interactions; a web browser should not attempt to read card-present devices directly.

## Safe Production Handoff

1. In BrandForge, generate the POS Menu asset and open **POS Operations**.
2. Confirm service names, prices, tax behavior, location label, and receipt footer.
3. Export the **Deluxe catalog mapping** JSON and provide it to the merchant onboarding or Deluxe Implementations contact.
4. Obtain merchant credentials and written confirmation of the approved production API/SDK product.
5. Add the three credentials as server-side project secrets; do not paste them into the browser or source control.
6. Configure the final hosted payment or native SDK path, then test in Deluxe’s merchant-approved sandbox before enabling a live checkout action.

## Credential Bypass for the Current Release

At the project owner’s direction, this release **does not request, infer, or bypass** Deluxe merchant credentials. It remains fully useful before activation: the POS workspace saves quote records, produces a plain-text **quote receipt** clearly marked as not a payment receipt, and exports the non-sensitive catalog mapping for merchant onboarding. The live payment switch remains unavailable until Deluxe issues the merchant credentials and confirms the approved hosted-payment or native Mobile POS SDK product.

## External Documentation

Deluxe’s Merchant Services API documentation identifies `https://api.deluxe.com` as its base URL and states that Client ID, Client Secret, Partner Token, and a temporary bearer token are used for merchant-authorized calls.[1] The Deluxe integration guide describes embedded payments, digital wallets, hosted payment forms, mobile SDKs, APIs, and webhooks, and notes that the Mobile SDK supports secure mobile POS processing.[2]

[1]: https://developer.deluxe.com/api-ref/merchant-services
[2]: https://developer.deluxe.com/docs-content/online-payment-integrations-get-started
