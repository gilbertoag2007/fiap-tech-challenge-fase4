(function () {
  const searchInput = document.getElementById("patient-search");
  if (!searchInput) {
    return;
  }

  const patientSelect = document.getElementById("patient-select");
  const patientDetails = document.getElementById("patient-details");
  const loadingAlert = document.getElementById("patient-loading");
  const errorAlert = document.getElementById("patient-error");
  const errorMessage = document.getElementById("patient-error-message");
  const emptyAlert = document.getElementById("patient-empty");
  const noResultsMessage = document.getElementById("patient-no-results");
  const retryButton = document.getElementById("retry-patients");
  const vitalSignsMessage = document.getElementById("vital-signs-message");
  const vitalSignsPlaceholder = document.getElementById("vital-signs-placeholder");
  const vitalSignsSection = document.getElementById("vital-signs-section");
  const vitalSignsPatient = document.getElementById("vital-patient-label");
  const vitalSignsLoading = document.getElementById("vital-loading");
  const vitalSignsError = document.getElementById("vital-error");
  const vitalSignsEmpty = document.getElementById("vital-empty");
  const vitalSignsIncomplete = document.getElementById("vital-incomplete");
  const vitalSignsChartGrid = document.getElementById("vital-chart-grid");
  const vitalDefinitions = [
    {
      code: "HR",
      name: "Frequência cardíaca",
      unit: "bpm",
      header: "HR",
      canvasId: "chart-hr",
      key: "hr",
      color: "#087e8b",
    },
    {
      code: "SpO2",
      name: "Saturação de oxigênio",
      unit: "%",
      header: "SpO2",
      canvasId: "chart-spo2",
      key: "spo2",
      color: "#2563eb",
    },
    {
      code: "NBPs",
      name: "Pressão arterial sistólica",
      unit: "mmHg",
      header: "NBP Sys",
      canvasId: "chart-nbps",
      key: "nbps",
      color: "#dc3545",
    },
    {
      code: "NBPd",
      name: "Pressão arterial diastólica",
      unit: "mmHg",
      header: "NBP Dias",
      canvasId: "chart-nbpd",
      key: "nbpd",
      color: "#d97706",
    },
    {
      code: "Pulse",
      name: "Frequência do pulso periférico",
      unit: "bpm",
      header: "PULSE",
      canvasId: "chart-pulse",
      key: "pulse",
      color: "#198754",
    },
    {
      code: "Resp",
      name: "Frequência respiratória",
      unit: "rpm",
      header: "RESP",
      canvasId: "chart-resp",
      key: "resp",
      color: "#7c3aed",
    },
  ];
  let patients = [];
  let vitalSignsRequest = 0;

  function normalize(value) {
    return value.trim().toLocaleLowerCase("pt-BR");
  }

  function showPatientError(error) {
    let message = "Não foi possível carregar os pacientes. Tente novamente mais tarde.";

    if (error.kind === "timeout") {
      message = "A consulta demorou mais do que o esperado. Verifique a conexão e tente novamente.";
    } else if (error.kind === "network") {
      message = "Não foi possível se conectar ao serviço de pacientes. Verifique se a API está disponível.";
    } else if (error.kind === "invalid-response") {
      message = "O serviço de pacientes retornou uma resposta inválida. Tente novamente mais tarde.";
    } else if (error.kind === "http" && error.status === 404) {
      message = "O serviço de pacientes não foi encontrado. Verifique a configuração do endpoint.";
    } else if (error.kind === "http" && error.status >= 500) {
      message = "O serviço de pacientes está temporariamente indisponível. Tente novamente mais tarde.";
    } else if (error.kind === "http") {
      message = "Não foi possível consultar os pacientes. Verifique a configuração do serviço.";
    }

    errorMessage.textContent = message;
    errorAlert.classList.remove("d-none");
    retryButton.classList.remove("d-none");
  }

  function resetVitalSigns() {
    vitalSignsRequest += 1;
    window.graficoComponent.destruirGraficos();
    vitalSignsSection.classList.add("d-none");
    vitalSignsPlaceholder.classList.remove("d-none");
    vitalSignsMessage.textContent =
      "Selecione um paciente para visualizar os sinais vitais.";
    vitalSignsPatient.textContent = "";
    vitalSignsLoading.classList.add("d-none");
    vitalSignsError.classList.add("d-none");
    vitalSignsError.textContent = "";
    vitalSignsEmpty.classList.add("d-none");
    vitalSignsIncomplete.classList.add("d-none");
    vitalSignsIncomplete.textContent = "";
    vitalSignsChartGrid.classList.remove("d-none");

    vitalDefinitions.forEach((definition) => {
      document.getElementById(`note-${definition.key}`).classList.add("d-none");
      document.getElementById(`period-${definition.key}`).textContent =
        "Tempo decorrido";
    });
  }

  function updatePatientOptions(filteredPatients) {
    const selectedId = patientSelect.value;
    const selectionIsVisible = filteredPatients.some(
      (patient) => patient.id === selectedId,
    );
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = filteredPatients.length
      ? "Selecione um paciente..."
      : "Nenhum paciente encontrado";

    const options = filteredPatients.map((patient) => {
      const option = document.createElement("option");
      option.value = patient.id;
      option.textContent = `${patient.nome} — ${patient.id}`;
      return option;
    });

    patientSelect.replaceChildren(placeholder, ...options);
    patientSelect.disabled = filteredPatients.length === 0;
    if (selectionIsVisible) {
      patientSelect.value = selectedId;
    } else {
      patientDetails.replaceChildren();
      patientDetails.classList.add("d-none");
      resetVitalSigns();
    }
    noResultsMessage.classList.toggle(
      "d-none",
      patients.length === 0 || filteredPatients.length > 0,
    );
  }

  function filterPatients() {
    const query = normalize(searchInput.value);
    const digitsQuery = query.replace(/\D/g, "");
    const filteredPatients = patients.filter((patient) => {
      const matchesNameOrId =
        normalize(patient.nome).includes(query) ||
        normalize(patient.id).includes(query);
      const matchesCpf =
        digitsQuery.length > 0 &&
        patient.cpf.replace(/\D/g, "").includes(digitsQuery);

      return matchesNameOrId || matchesCpf;
    });

    updatePatientOptions(filteredPatients);
  }

  function normalizeHeader(value) {
    return value
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("en")
      .replace(/[^a-z0-9]/g, "");
  }

  function parseNumericValue(value) {
    const text = String(value ?? "").trim();
    if (!text) {
      return null;
    }

    let normalized = text.replace(/\s/g, "");
    const commaIndex = normalized.lastIndexOf(",");
    const dotIndex = normalized.lastIndexOf(".");
    if (commaIndex !== -1 && dotIndex !== -1) {
      const decimalSeparator = commaIndex > dotIndex ? "," : ".";
      const groupingSeparator = decimalSeparator === "," ? "." : ",";
      normalized = normalized
        .split(groupingSeparator)
        .join("")
        .replace(decimalSeparator, ".");
    } else if (commaIndex !== -1) {
      normalized = normalized.replace(",", ".");
    }

    const number = Number(normalized);
    return Number.isFinite(number) ? number : null;
  }

  function parseVitalSignsCsv(csv) {
    if (!csv.trim()) {
      return {
        records: [],
        invalidRows: 0,
        invalidMeasurements: 0,
        fieldByKey: new Map(),
      };
    }

    const parsed = window.Papa.parse(csv, {
      header: true,
      skipEmptyLines: "greedy",
      dynamicTyping: false,
    });
    const fields = parsed.meta.fields || [];
    const normalizedFields = new Map(
      fields.map((field) => [normalizeHeader(field), field]),
    );
    const timeField = normalizedFields.get("temposegundos");
    if (!timeField) {
      throw new window.ApiError("invalid-csv");
    }

    const fieldByKey = new Map(
      vitalDefinitions.map((definition) => [
        definition.key,
        normalizedFields.get(normalizeHeader(definition.header)),
      ]),
    );
    const records = [];
    let invalidRows = 0;
    let invalidMeasurements = 0;

    parsed.data.forEach((row) => {
      const seconds = parseNumericValue(row[timeField]);
      if (seconds === null || seconds < 0) {
        invalidRows += 1;
        return;
      }

      const values = {};
      fieldByKey.forEach((field, key) => {
        if (!field) {
          values[key] = null;
          return;
        }

        const rawValue = row[field];
        values[key] = parseNumericValue(rawValue);
        if (String(rawValue ?? "").trim() && values[key] === null) {
          invalidMeasurements += 1;
        }
      });

      records.push({ seconds, values });
    });

    records.sort((first, second) => first.seconds - second.seconds);
    if (invalidRows || invalidMeasurements || parsed.errors.length) {
      console.warn("CSV de sinais vitais processado com registros ignorados.", {
        invalidRows,
        invalidMeasurements,
        parserErrors: parsed.errors.length,
      });
    }

    return { records, invalidRows, invalidMeasurements, fieldByKey };
  }

  function formatElapsedTime(seconds) {
    const totalSeconds = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const remainingSeconds = totalSeconds % 60;

    return [hours, minutes, remainingSeconds]
      .map((part) => String(part).padStart(2, "0"))
      .join(":");
  }

  function renderVitalSigns(parsedCsv) {
    const { records, fieldByKey } = parsedCsv;
    vitalSignsChartGrid.classList.remove("d-none");

    if (!records.length) {
      vitalSignsChartGrid.classList.add("d-none");
      if (parsedCsv.invalidRows > 0) {
        vitalSignsError.textContent =
          "Não foi possível interpretar os registros do arquivo CSV recebido.";
        vitalSignsError.classList.remove("d-none");
        return;
      }

      vitalSignsEmpty.classList.remove("d-none");
      return;
    }

    const insufficientIndicators = [];
    const firstSecond = records[0].seconds;
    const lastSecond = records[records.length - 1].seconds;

    vitalDefinitions.forEach((definition) => {
      const points = records.map((record) => ({
        x: record.seconds,
        y: record.values[definition.key],
      }));
      const pointCount = points.reduce(
        (count, point) => count + (point.y === null ? 0 : 1),
        0,
      );
      const note = document.getElementById(`note-${definition.key}`);
      const period = document.getElementById(`period-${definition.key}`);

      window.graficoComponent.criarGrafico({
        canvasId: definition.canvasId,
        code: definition.code,
        name: definition.name,
        unit: definition.unit,
        color: definition.color,
        points,
        pointCount,
      });

      if (!fieldByKey.get(definition.key) || pointCount < 2) {
        note.textContent = fieldByKey.get(definition.key)
          ? `Dados insuficientes para traçar uma linha (${pointCount} ${pointCount === 1 ? "registro" : "registros"}).`
          : "Indicador não disponível no CSV recebido.";
        note.classList.remove("d-none");
        insufficientIndicators.push(
          `${definition.code} (${pointCount} ${pointCount === 1 ? "registro" : "registros"})`,
        );
      } else {
        note.classList.add("d-none");
      }

      period.textContent =
        `Período: ${formatElapsedTime(firstSecond)}–${formatElapsedTime(lastSecond)}`;
    });

    if (insufficientIndicators.length) {
      vitalSignsIncomplete.textContent =
        `Dados insuficientes para alguns indicadores: ${insufficientIndicators.join(", ")}.`;
      vitalSignsIncomplete.classList.remove("d-none");
    }
  }

  async function loadVitalSigns(patient) {
    const requestId = ++vitalSignsRequest;
    window.graficoComponent.destruirGraficos();
    vitalSignsPlaceholder.classList.add("d-none");
    vitalSignsSection.classList.remove("d-none");
    vitalSignsPatient.textContent = `${patient.nome} · ${patient.id}`;
    vitalSignsLoading.classList.remove("d-none");
    vitalSignsError.classList.add("d-none");
    vitalSignsError.textContent = "";
    vitalSignsEmpty.classList.add("d-none");
    vitalSignsIncomplete.classList.add("d-none");
    vitalSignsIncomplete.textContent = "";
    vitalSignsChartGrid.classList.add("d-none");

    vitalDefinitions.forEach((definition) => {
      document.getElementById(`note-${definition.key}`).classList.add("d-none");
      document.getElementById(`period-${definition.key}`).textContent =
        "Tempo decorrido";
    });

    try {
      const csv = await window.sinaisVitaisService.buscarSinaisVitais(patient.id);
      if (requestId !== vitalSignsRequest) {
        return;
      }

      const parsedCsv = parseVitalSignsCsv(csv);
      vitalSignsLoading.classList.add("d-none");
      renderVitalSigns(parsedCsv);
    } catch (error) {
      if (requestId !== vitalSignsRequest) {
        return;
      }

      vitalSignsLoading.classList.add("d-none");
      vitalSignsChartGrid.classList.add("d-none");
      if (!(error instanceof window.ApiError)) {
        console.error("Erro ao carregar ou processar sinais vitais.", error);
      }
      vitalSignsError.textContent =
        "Não foi possível carregar os sinais vitais. Verifique a disponibilidade da API.";
      vitalSignsError.classList.remove("d-none");
    }
  }

  async function loadPatients() {
    loadingAlert.classList.remove("d-none");
    errorAlert.classList.add("d-none");
    retryButton.classList.add("d-none");
    emptyAlert.classList.add("d-none");
    patients = [];
    patientDetails.replaceChildren();
    patientDetails.classList.add("d-none");
    resetVitalSigns();
    searchInput.disabled = true;
    patientSelect.disabled = true;
    patientSelect.replaceChildren();

    try {
      patients = await window.pacienteService.listarPacientes();
      loadingAlert.classList.add("d-none");

      if (patients.length === 0) {
        emptyAlert.classList.remove("d-none");
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "Nenhum paciente disponível";
        patientSelect.replaceChildren(option);
        noResultsMessage.classList.add("d-none");
        return;
      }

      searchInput.disabled = false;
      filterPatients();
    } catch (error) {
      loadingAlert.classList.add("d-none");
      patients = [];
      if (!(error instanceof window.ApiError)) {
        console.error("Erro inesperado ao carregar pacientes.", error);
      }
      showPatientError(
        error instanceof window.ApiError
          ? error
          : new window.ApiError("unexpected"),
      );
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "Lista de pacientes indisponível";
      patientSelect.replaceChildren(option);
    }
  }

  searchInput.addEventListener("input", filterPatients);
  patientSelect.addEventListener("change", () => {
    const patient = patients.find((item) => item.id === patientSelect.value);
    if (!patient) {
      patientDetails.replaceChildren();
      patientDetails.classList.add("d-none");
      resetVitalSigns();
      return;
    }

    window.pacienteComponent.renderizarPaciente(patient, patientDetails);
    loadVitalSigns(patient);
  });
  retryButton.addEventListener("click", loadPatients);

  loadPatients();
})();
