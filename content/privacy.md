+++
title = "Privacy"

[extra]
menu = true
+++

I like to track my personal data like where I spend my time on my phone[^1], laptop[^2], even in my code editor[^3] and browser[^4]. Similarly, I very much interested in knowing how many people visit my website, from where and what do they read. For that purpose I am using a self-hosted instance of [Umami](https://umami.is).

## Analytics

Here is what I collect:

- Page views and referrer URLs
- General device type, browser, and operating system
- Country-level location (derived from your IP address, which is never stored)

Here is what I **don't** do:

- **No cookies.** Umami does not set any cookies on your device.
- **No cross-site tracking.** I have no interest in following you around the web.
- **No selling or sharing.** The data lives on my own server and is never shared with advertisers or third parties.
- **No personally identifiable information.** Your raw IP address is never logged or stored (only used transiently to derive an anonymised session token that resets daily).

## Third-Party Services

This site does not load any scripts, fonts, or resources from external third-party tracking domains. All assets (including fonts, icons, and the analytics script itself) are served directly from the site's domain (website is hosted on Cloudflare Pages) or from my self-hosted server (Oracle VM).

## Contact

If you have any questions or concerns, feel free to reach out at **[hi@sophic.dev](mailto:hi@sophic.dev)**.

[^1]: [Digital Wellbeing](https://play.google.com/store/apps/details?id=com.google.android.apps.wellbeing&hl=en-US): I have a lot of qualms about this one. It is made by Google, which does not have the best reputation when it comes to privacy. I use it because it's convenient and I don't know any alternative, but I am not fully comfortable with it and you probably shouldn't be either.

[^2]: [ActivityWatch](https://activitywatch.net)

[^3]: [wakapi](https://wakapi.dev)

[^4]: [https://github.com/sheepzh/time-tracker-4-browser](https://github.com/sheepzh/time-tracker-4-browser)
