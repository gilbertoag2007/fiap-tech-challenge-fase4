(function () {
  class ApiError extends Error {
    constructor(kind, status) {
      super(kind);
      this.name = "ApiError";
      this.kind = kind;
      this.status = status;
    }
  }

  const http = window.axios.create({
    baseURL: window.API_BASE_URL,
    timeout: 10000,
    headers: {
      Accept: "application/json",
    },
  });

  http.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response) {
        return Promise.reject(new ApiError("http", error.response.status));
      }

      if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") {
        return Promise.reject(new ApiError("timeout"));
      }

      return Promise.reject(new ApiError("network"));
    },
  );

  window.apiClient = http;
  window.ApiError = ApiError;
})();
