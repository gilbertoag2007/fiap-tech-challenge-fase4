(function () {
  const prefix = '/v1/fisioterapia';
  async function request(endpoint, options = {}) {
    const response = await fetch(new URL(endpoint, window.API_BASE_URL), {
      ...options,
      headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}) },
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) {
      let detail = 'Não foi possível consultar a análise.';
      try {
        const error = await response.json();
        if (typeof error.detail === 'string') detail = error.detail;
      } catch (_) { /* Non-JSON server error; retain the useful default. */ }
      throw new Error(detail);
    }
    return response.json();
  }
  window.fisioterapiaService = {
    catalog: () => request(prefix + '/catalogo'),
    create: (videoId) => request(prefix + '/analises', { method: 'POST', body: JSON.stringify({ video_id: videoId }) }),
    task: (jobId) => request(prefix + '/analises/' + encodeURIComponent(jobId)),
    report: (jobId) => request(prefix + '/analises/' + encodeURIComponent(jobId) + '/relatorio'),
    pose: (jobId) => request(prefix + '/analises/' + encodeURIComponent(jobId) + '/pose'),
    videoUrl: (videoId) => new URL(prefix + '/videos/' + encodeURIComponent(videoId), window.API_BASE_URL).href,
  };
})();
