(function () {
  async function buscarSinaisVitais(idPaciente) {
    const response = await window.apiClient.get(
      window.VITAL_SIGNS_ENDPOINT,
      {
        params: { id: idPaciente },
        responseType: "text",
      },
    );

    if (typeof response.data !== "string") {
      throw new window.ApiError("invalid-csv");
    }

    return response.data;
  }

  window.sinaisVitaisService = { buscarSinaisVitais };
})();
