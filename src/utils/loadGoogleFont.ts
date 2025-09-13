const cssCache = new Map<string, string>();
const fontCache = new Map<string, ArrayBuffer>();

const USER_AGENT =
  "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; de-at) AppleWebKit/533.21.1 (KHTML, like Gecko) Version/5.0.5 Safari/533.21.1";

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function shouldRetry(status?: number) {
  return (
    status === undefined || status === 429 || (status >= 500 && status < 600)
  );
}

async function fetchWithRetry(
  url: string,
  init?: RequestInit,
  opts?: { attempts?: number; timeoutMs?: number; backoffBaseMs?: number }
): Promise<Response> {
  const attempts = opts?.attempts ?? 4;
  const timeoutMs = opts?.timeoutMs ?? 8000;
  const backoffBaseMs = opts?.backoffBaseMs ?? 300;

  let lastError: unknown = undefined;

  for (let attempt = 0; attempt < attempts; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(url, {
        ...(init || {}),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (res.ok) return res;
      if (!shouldRetry(res.status) || attempt === attempts - 1) {
        return res;
      }
    } catch (err) {
      lastError = err;
      if (attempt === attempts - 1) break;
    } finally {
      clearTimeout(timer);
    }
    const delay =
      backoffBaseMs * Math.pow(2, attempt) + Math.floor(Math.random() * 100);
    await sleep(delay);
  }

  throw lastError ?? new Error("Fetch failed");
}

function parsePreferredFontUrl(
  css: string
): { url: string; format: string } | null {
  // Collect all url(...) format('...') pairs from the CSS
  const result: Array<{ url: string; format: string }> = [];
  const re = /url\((['"]?)(.+?)\1\)\s*format\(\s*['"]([^'"]+)['"]\s*\)/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(css)) !== null) {
    const url = m[2];
    const format = m[3].toLowerCase();
    result.push({ url, format });
  }

  if (result.length === 0) return null;

  // Prefer OpenType/TrueType for satori compatibility
  const preference = ["opentype", "truetype", "woff", "woff2"];
  for (const fmt of preference) {
    const match = result.find(r => r.format === fmt);
    if (match) return match;
  }
  return result[0];
}

async function loadGoogleFont(
  font: string,
  text: string,
  weight: number
): Promise<ArrayBuffer> {
  const API = `https://fonts.googleapis.com/css2?family=${font}:wght@${weight}&text=${encodeURIComponent(
    text
  )}`;

  // Fetch CSS (with cache + retries)
  let css = cssCache.get(API);
  if (!css) {
    const cssRes = await fetchWithRetry(
      API,
      {
        headers: {
          "User-Agent": USER_AGENT,
          Accept: "text/css,*/*;q=0.1",
        },
      },
      { attempts: 4, timeoutMs: 8000 }
    );

    if (!cssRes.ok) {
      throw new Error(
        "Failed to fetch Google Fonts CSS. Status: " + cssRes.status
      );
    }

    css = await cssRes.text();
    cssCache.set(API, css);
  }

  // Parse CSS for best available font URL (prefer opentype/truetype)
  const selection = parsePreferredFontUrl(css);
  if (!selection) {
    throw new Error(
      "Failed to parse Google Fonts CSS for a downloadable font resource"
    );
  }

  const resourceUrl = selection.url.startsWith("http")
    ? selection.url
    : `https:${selection.url}`;

  // Fetch font binary (with cache + retries)
  const cachedFont = fontCache.get(resourceUrl);
  if (cachedFont) return cachedFont;

  const res = await fetchWithRetry(
    resourceUrl,
    {
      headers: {
        "User-Agent": USER_AGENT,
        Accept:
          "font/ttf, font/otf, application/x-font-ttf, application/font-sfnt, */*",
        Referer: "https://fonts.googleapis.com/",
      },
    },
    { attempts: 4, timeoutMs: 12000 }
  );

  if (!res.ok) {
    throw new Error("Failed to download dynamic font. Status: " + res.status);
  }

  const buf = await res.arrayBuffer();
  fontCache.set(resourceUrl, buf);
  return buf;
}

async function loadGoogleFonts(
  text: string
): Promise<
  Array<{ name: string; data: ArrayBuffer; weight: number; style: string }>
> {
  const fontsConfig = [
    {
      name: "IBM Plex Mono",
      font: "IBM+Plex+Mono",
      weight: 400,
      style: "normal",
    },
    {
      name: "IBM Plex Mono",
      font: "IBM+Plex+Mono",
      weight: 700,
      style: "bold",
    },
  ];

  const fonts = await Promise.all(
    fontsConfig.map(async ({ name, font, weight, style }) => {
      try {
        const data = await loadGoogleFont(font, text, weight);
        return { name, data, weight, style };
      } catch {
        // Fallback: skip this font if it fails to load (e.g., offline build)
        return null;
      }
    })
  );

  return fonts.filter(
    (
      f
    ): f is {
      name: string;
      data: ArrayBuffer;
      weight: number;
      style: string;
    } => !!f
  );
}

export default loadGoogleFonts;
