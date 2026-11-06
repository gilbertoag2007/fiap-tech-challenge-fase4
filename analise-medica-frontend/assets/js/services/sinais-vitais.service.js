(function () {
  function isRelatorioValido(relatorio) {
    return (
      relatorio !== null &&
      typeof relatorio === "object" &&
      relatorio.dados_do_paciente !== undefined &&
      relatorio.sinais_vitais !== undefined &&
      typeof relatorio.sinais_vitais === "object"
    );
  }

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

  async function buscarRelatorioSinaisVitais(idPaciente) {
    const response = await window.apiClient.get(
      window.VITAL_SIGNS_REPORT_ENDPOINT,
      {
        params: { id: idPaciente },
      },
    );

    if (!isRelatorioValido(response.data)) {
      throw new window.ApiError("invalid-response");
    }

    return response.data;
  }

  async function buscarTabelaReferenciaSinalVital(sinal) {
    const response = await window.apiClient.get(
      window.VITAL_SIGNS_REFERENCE_ENDPOINT,
      {
        params: { sinal },
      },
    );

    if (
      response.data === null ||
      typeof response.data !== "object" ||
      response.data.tabela === null ||
      typeof response.data.tabela !== "object"
    ) {
      throw new window.ApiError("invalid-response");
    }

    return response.data.tabela;
  }

  window.sinaisVitaisService = {
    buscarSinaisVitais,
    buscarRelatorioSinaisVitais,
    buscarTabelaReferenciaSinalVital,
  };
})();
