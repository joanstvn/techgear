(() => {
  const config = document.getElementById('techgear-api-config');
  if (!config) return;

  let apiBase;
  try {
    apiBase = JSON.parse(config.textContent).replace(/\/+$/, '');
  } catch (_) {
    return;
  }
  if (!apiBase || apiBase.includes('127.0.0.1') || apiBase.includes('localhost')) return;

  const retrySurface = document.querySelector('[data-api-retry]');
  const retryButton = document.querySelector('[data-api-retry-now]');
  const retryMessage = retrySurface?.querySelector('[data-api-retry-message]')
    || retrySurface?.querySelector('span');
  const retryKey = 'techgear-api-retry-count';
  let stopped = false;
  let activeRun = 0;
  if (!retrySurface) {
    try { sessionStorage.removeItem(retryKey); } catch (_) {}
  }

  window.addEventListener('pagehide', () => { stopped = true; }, { once: true });

  const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

  async function checkApi() {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    try {
      // Probe a real data endpoint: the API root can be healthy while MongoDB
      // (and therefore the catalog) is still unavailable. A readable response
      // also lets us distinguish a real recovery from an opaque no-cors response.
      const response = await fetch(`${apiBase}/products/`, {
        method: 'GET',
        cache: 'no-store',
        credentials: 'omit',
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });
      return response.ok;
    } catch (_) {
      return false;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  async function retryUntilReady({ manual = false } = {}) {
    if (stopped || (!manual && activeRun)) return;
    const run = ++activeRun;
    if (retryButton && manual) {
      retryButton.disabled = true;
      retryButton.setAttribute('aria-busy', 'true');
      retryButton.textContent = 'Comprobando…';
    }
    if (manual && retryMessage) retryMessage.textContent = 'Comprobando la conexión con el catálogo…';

    const delays = manual ? [0, 3000, 7000, 12000] : [0, 5000, 10000, 20000, 30000];
    let recovered = false;
    for (const delay of delays) {
      if (stopped || run !== activeRun) break;
      if (delay) await wait(delay);
      if (stopped || run !== activeRun) break;
      if (await checkApi()) {
        recovered = true;
        break;
      }
    }

    if (stopped || run !== activeRun) return;
    activeRun = 0;
    if (retryButton && manual) {
      retryButton.disabled = false;
      retryButton.removeAttribute('aria-busy');
      retryButton.textContent = 'Reintentar';
    }
    if (recovered) {
      let attempts = 0;
      try { attempts = Number(sessionStorage.getItem(retryKey) || 0); } catch (_) {}
      if (!manual && attempts >= 1) {
        if (retryMessage) retryMessage.textContent = 'El servicio ya responde, pero estos datos aún no se pudieron cargar. Pulsa Reintentar para actualizar el panel.';
        if (!retryButton) window.setTimeout(() => retryUntilReady(), 30000);
        return;
      }
      try { sessionStorage.setItem(retryKey, String(attempts + 1)); } catch (_) {}
      // The Django page rendered its data before this browser-side check. Reload
      // only after a confirmed recovery so its server-rendered view fetches fresh data.
      window.location.reload();
      return;
    }
    if (manual && retryMessage) {
      retryMessage.textContent = 'El servicio todavía no responde. Puedes seguir aquí y volver a intentarlo.';
    }
    if (!manual && !retryButton) window.setTimeout(() => retryUntilReady(), 30000);
  }

  retryButton?.addEventListener('click', () => retryUntilReady({ manual: true }));
  if (retrySurface) retryUntilReady();
})();
