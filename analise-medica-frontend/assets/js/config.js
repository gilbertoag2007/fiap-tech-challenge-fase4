window.API_BASE_URL = window.APP_CONFIG?.apiBaseUrl || "http://127.0.0.1:8000";
window.DEMO_MODE = window.APP_CONFIG?.demoMode === true;
window.API_TIMEOUT = window.DEMO_MODE ? 120000 : 10000;
const demoNotice = document.getElementById("demo-notice");
if (demoNotice) demoNotice.hidden = !window.DEMO_MODE;
window.PATIENTS_ENDPOINT = "/v1/sinais-vitais/paciente";
window.VITAL_SIGNS_ENDPOINT = "/v1/sinais-vitais/datalhamento";
window.VITAL_SIGNS_REPORT_ENDPOINT = "/v1/sinais-vitais/relatorio";
window.VITAL_SIGNS_REFERENCE_ENDPOINT = "/v1/sinais-vitais/tabela-referencia";
