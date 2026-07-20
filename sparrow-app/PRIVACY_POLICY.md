# Privacy Policy — Sparrow Desktop App

**Last Updated:** July 20, 2026  
**Version:** 0.1.0

## 1. Introduction

Sparrow ("we," "our," or "us") is a local-first desktop application built by Forhemit Sparrow. This Privacy Policy explains how Sparrow handles your data when you use our software.

**Our commitment: Your data stays on your machine.**

## 2. Data We Collect

### 2.1 Data Collected Locally (On Your Device)

- **Search queries** — Products you ask Sparrow to compare are stored only on your local device.
- **Comparison reports** — Generated HTML reports are saved locally in your `agent/reports/` directory.
- **Preferences** — Any customization settings (rubric weights, preferred vendors) are stored locally.
- **Application usage data** — Basic telemetry (crash reports, version info) is stored locally only.

### 2.2 Data Sent Externally

Sparrow makes limited external API calls to function:

| Service | Data Sent | Purpose |
|---------|-----------|---------|
| Brave Search API | Product search queries | Find real-time product pricing and availability |
| Agnes AI / OpenRouter | Anonymized query context | LLM-powered qualitative analysis |

**We do NOT:**
- Send personal identifiers (name, email, IP address) to any third party
- Store your search history on cloud servers
- Share your data with advertisers or analytics platforms
- Sell or license your data to anyone

## 3. Data Storage

- All data is stored **locally** on your device.
- Reports are saved as HTML files in `~/Documents/Sparrow/reports/` (or equivalent).
- Application settings are stored in your system's local preferences directory.
- You can delete all data at any time by deleting the Sparrow application folder.

## 4. Data Security

- Sparrow uses HTTPS for all external API communications.
- API keys are stored locally in a `.env` file and are never transmitted to Sparrow servers.
- The application runs with the minimum permissions required.
- No background data collection occurs.

## 5. Your Rights

You have the right to:
- **Access** your data at any time (it's all on your local device)
- **Delete** your data at any time (remove the application folder)
- **Export** your reports as HTML files
- **Opt out** of any external API calls (use offline/demo mode)

## 6. Children's Privacy

Sparrow is not intended for children under 13. We do not knowingly collect data from children.

## 7. Changes to This Policy

We may update this Privacy Policy from time to time. Changes will be reflected in the application's built-in Privacy page and on our website at [onestarcfo.com/privacy](https://onestarcfo.com/privacy).

## 8. Contact

For privacy-related questions:
- **Email:** [Contact us via our website](https://onestarcfo.com/contact)
- **Website:** [onestarcfo.com](https://onestarcfo.com)

---

*Sparrow is built with privacy as a foundational principle, not an afterthought.*
