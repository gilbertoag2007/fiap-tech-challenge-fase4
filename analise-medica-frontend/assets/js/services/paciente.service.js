(function () {
  function isPatient(patient) {
    return (
      patient !== null &&
      typeof patient === "object" &&
      typeof patient.id === "string" &&
      typeof patient.cpf === "string" &&
      typeof patient.nome === "string" &&
      typeof patient.idade === "number" &&
      Number.isFinite(patient.idade) &&
      typeof patient.genero === "string" &&
      typeof patient.prontuario === "string"
    );
  }

  async function listarPacientes() {
    const response = await window.apiClient.get(window.PATIENTS_ENDPOINT);

    if (!Array.isArray(response.data) || !response.data.every(isPatient)) {
      throw new window.ApiError("invalid-response");
    }

    return response.data;
  }

  window.pacienteService = { listarPacientes };
})();
