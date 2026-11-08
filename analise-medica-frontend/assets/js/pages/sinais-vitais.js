(function () {
  const searchInput = document.getElementById("patient-search");
  if (!searchInput) {
    return;
  }

  const patientSelect = document.getElementById("patient-select");
  const patientDetails = document.getElementById("patient-details");
  const analysisSummary = document.getElementById("analysis-summary");
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
      code: "PULSE",
      name: "Frequência do pulso periférico",
      unit: "bpm",
      header: "PULSE",
      canvasId: "chart-pulse",
      key: "pulse",
      color: "#198754",
    },
    {
      code: "RESP",
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

  function getStatusTone(status) {
    if (!status) {
      return "neutral";
    }

    const normalized = String(status).trim().toLocaleLowerCase("pt-BR");
    if (normalized.includes("normal")) {
      return "ok";
    }
    if (normalized.includes("alter")) {
      return "alert";
    }
    return "neutral";
  }

  function renderIndicatorSummary(
    definition,
    indicatorData,
    referenceTable,
    referenceError,
  ) {
    const container = document.getElementById(`result-${definition.key}`);
    if (!container) {
      return;
    }

    if (!indicatorData && !referenceTable && !referenceError) {
      container.classList.add("d-none");
      container.replaceChildren();
      return;
    }

    const header = document.createElement("div");
    header.className = "chart-result-header";

    const title = document.createElement("span");
    title.className = "chart-result-title";
    title.textContent = indicatorData?.descricao || definition.name;

    header.append(title);
    if (indicatorData) {
      const status = String(indicatorData.status || "Sem avaliação").trim();
      const badge = document.createElement("span");
      badge.className = `chart-result-status status-${getStatusTone(status)}`;
      badge.textContent = status || "Sem avaliação";
      header.append(badge);
    }

    const description = document.createElement("p");
    description.className = "chart-result-description";
    description.textContent = `${definition.name} · ${definition.unit}`;
    container.replaceChildren(header, description);
    if (indicatorData?.observacao) {
      const observation = document.createElement("p");
      observation.className = "chart-result-observation";
      observation.textContent = indicatorData.observacao;
      container.append(observation);
    }

    const referenceDetails = document.createElement("details");
    referenceDetails.className = "reference-table-details";
    const referenceSummary = document.createElement("summary");
    referenceSummary.textContent = "Consultar tabela de referência";
    referenceDetails.append(referenceSummary);

    if (referenceError) {
      const errorMessage = document.createElement("p");
      errorMessage.className = "reference-table-message text-danger";
      errorMessage.textContent = "Não foi possível carregar a tabela de referência.";
      referenceDetails.append(errorMessage);
    } else if (referenceTable) {
      referenceDetails.append(renderReferenceTable(referenceTable, definition.unit));
    } else {
      const emptyMessage = document.createElement("p");
      emptyMessage.className = "reference-table-message";
      emptyMessage.textContent = "Tabela de referência indisponível.";
      referenceDetails.append(emptyMessage);
    }

    container.append(referenceDetails);
    container.classList.remove("d-none");
  }

  function renderReferenceTable(reference, unit) {
    const rows = [];
    const adultRange = reference.faixa_adulta_normal;
    if (adultRange && adultRange.minimo !== undefined && adultRange.maximo !== undefined) {
      rows.push({
        context: "Adultos",
        value: `${adultRange.minimo} a ${adultRange.maximo} ${unit}`,
      });
    }

    Object.entries(reference.sexo || {}).forEach(([sex, value]) => {
      rows.push({
        context: sex.charAt(0).toLocaleUpperCase("pt-BR") + sex.slice(1),
        value,
      });
    });

    (Array.isArray(reference.faixa_por_idade) ? reference.faixa_por_idade : [])
      .forEach((range) => {
        if (range.faixa_etaria) {
          rows.push({
            context: range.faixa_etaria,
            value:
              range.minimo !== undefined && range.maximo !== undefined
                ? `${range.minimo} a ${range.maximo} ${unit}`
                : "Não informado",
          });
        }
      });

    const wrapper = document.createElement("div");
    wrapper.className = "reference-table-wrapper";
    if (!rows.length) {
      const message = document.createElement("p");
      message.className = "reference-table-message";
      message.textContent = "A tabela não contém faixas cadastradas.";
      wrapper.append(message);
      return wrapper;
    }

    const table = document.createElement("table");
    table.className = "table table-sm table-bordered reference-table";
    const head = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["Grupo", "Valores de referência"].forEach((label) => {
      const cell = document.createElement("th");
      cell.scope = "col";
      cell.textContent = label;
      headerRow.append(cell);
    });
    head.append(headerRow);

    const body = document.createElement("tbody");
    rows.forEach(({ context, value }) => {
      const row = document.createElement("tr");
      const contextCell = document.createElement("th");
      contextCell.scope = "row";
      contextCell.textContent = context;
      const valueCell = document.createElement("td");
      valueCell.textContent = value;
      row.append(contextCell, valueCell);
      body.append(row);
    });
    table.append(head, body);
    wrapper.append(table);

    if (reference.observacao) {
      const note = document.createElement("p");
      note.className = "reference-table-note";
      note.textContent = reference.observacao;
      wrapper.append(note);
    }
    return wrapper;
  }

  function renderAnalysisSummary(relatorio) {
    if (!relatorio || typeof relatorio !== "object") {
      analysisSummary.classList.add("d-none");
      analysisSummary.replaceChildren();
      return;
    }

    const indicadores = relatorio.sinais_vitais || {};
    const normalCount = Object.values(indicadores).filter((item) =>
      String(item?.status || "")
        .trim()
        .toLocaleLowerCase("pt-BR")
        .includes("normal"),
    ).length;
    const alteredCount = Object.values(indicadores).filter((item) =>
      String(item?.status || "")
        .trim()
        .toLocaleLowerCase("pt-BR")
        .includes("alter"),
    ).length;
    const total = Object.keys(indicadores).length;
    const duration =
      relatorio.tempo_analisado?.duracao_formatada || "Não informado";
    const patientName = relatorio.dados_do_paciente?.nome || "Paciente";

    const card = document.createElement("article");
    card.className = "analysis-summary-card";

    const header = document.createElement("div");
    header.className = "analysis-summary-header";

    const title = document.createElement("h3");
    title.textContent = `Resumo da análise — ${patientName}`;

    const badge = document.createElement("span");
    badge.className = `analysis-status-badge status-${
      alteredCount > 0 ? "alert" : "ok"
    }`;
    badge.textContent =
      alteredCount > 0
        ? `${alteredCount} indicadores alterados`
        : "Sem alterações relevantes";

    header.append(title, badge);

    const metrics = document.createElement("div");
    metrics.className = "analysis-summary-grid";

    const metricsDefinition = [
      { label: "Total", value: total },
      { label: "Normais", value: normalCount, tone: "ok" },
      { label: "Alterados", value: alteredCount, tone: "alert" },
      { label: "Duração", value: duration },
    ];

    metricsDefinition.forEach(({ label, value, tone }) => {
      const metric = document.createElement("div");
      metric.className = `analysis-metric${tone ? ` analysis-metric-${tone}` : ""}`;

      const metricLabel = document.createElement("span");
      metricLabel.className = "analysis-metric-label";
      metricLabel.textContent = label;

      const metricValue = document.createElement("span");
      metricValue.className = "analysis-metric-value";
      metricValue.textContent = String(value);

      metric.append(metricLabel, metricValue);
      metrics.append(metric);
    });

    card.append(header, metrics);
    analysisSummary.replaceChildren(card);
    analysisSummary.classList.remove("d-none");
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
    analysisSummary.classList.add("d-none");
    analysisSummary.replaceChildren();

    vitalDefinitions.forEach((definition) => {
      document.getElementById(`note-${definition.key}`).classList.add("d-none");
      document.getElementById(`period-${definition.key}`).textContent =
        "Tempo decorrido";
      const result = document.getElementById(`result-${definition.key}`);
      if (result) {
        result.classList.add("d-none");
        result.replaceChildren();
      }
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

  function parseTimeValue(value) {
    const text = String(value ?? "").trim();
    const seconds = parseNumericValue(text);
    if (seconds !== null) {
      return { seconds, dateTime: null };
    }

    const match = text.match(
      /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?$/,
    );
    if (!match) {
      return null;
    }

    const [, yearText, monthText, dayText, hourText, minuteText, secondText, fraction = ""] =
      match;
    const [year, month, day, hour, minute, second] = [
      yearText,
      monthText,
      dayText,
      hourText,
      minuteText,
      secondText,
    ].map(Number);
    const timestamp = Date.UTC(year, month - 1, day, hour, minute, second);
    const date = new Date(timestamp);
    if (
      date.getUTCFullYear() !== year ||
      date.getUTCMonth() !== month - 1 ||
      date.getUTCDate() !== day ||
      date.getUTCHours() !== hour ||
      date.getUTCMinutes() !== minute ||
      date.getUTCSeconds() !== second
    ) {
      return null;
    }

    return {
      seconds: timestamp / 1000 + (fraction ? Number(`0.${fraction}`) : 0),
      dateTime: `${yearText}-${monthText}-${dayText} ${hourText}:${minuteText}:${secondText}`,
    };
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
    const interpolatedFieldByKey = new Map(
      vitalDefinitions.map((definition) => {
        const field = normalizedFields.get(normalizeHeader(definition.header));
        return [
          definition.key,
          field
            ? normalizedFields.get(normalizeHeader(`${field}__interpolado`))
            : undefined,
        ];
      }),
    );
    const records = [];
    let hasDateTime;
    let invalidRows = 0;
    let invalidMeasurements = 0;

    parsed.data.forEach((row) => {
      const time = parseTimeValue(row[timeField]);
      if (
        time === null ||
        (time.dateTime === null && time.seconds < 0) ||
        (hasDateTime !== undefined && hasDateTime !== (time.dateTime !== null))
      ) {
        invalidRows += 1;
        return;
      }
      hasDateTime = time.dateTime !== null;

      const values = {};
      const interpolated = {};
      fieldByKey.forEach((field, key) => {
        if (!field) {
          values[key] = null;
          interpolated[key] = false;
          return;
        }

        const rawValue = row[field];
        values[key] = parseNumericValue(rawValue);
        const interpolationField = interpolatedFieldByKey.get(key);
        interpolated[key] = Boolean(
          interpolationField && row[interpolationField] === "True",
        );
        if (String(rawValue ?? "").trim() && values[key] === null) {
          invalidMeasurements += 1;
        }
      });

      records.push({
        seconds: time.seconds,
        dateTime: time.dateTime,
        values,
        interpolated,
      });
    });

    if (hasDateTime) {
      const firstTimestamp = records[0]?.seconds ?? 0;
      records.forEach((record) => {
        record.seconds =
          Math.round((record.seconds - firstTimestamp) * 1_000_000) / 1_000_000;
      });
    }
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

  function renderVitalSigns(parsedCsv, relatorio, referencias) {
    const { records, fieldByKey } = parsedCsv;
    vitalSignsChartGrid.classList.remove("d-none");

    if (relatorio && relatorio.sinais_vitais) {
      vitalDefinitions.forEach((definition) => {
        const indicatorData = relatorio.sinais_vitais[definition.code];
        const referenceResult = referencias[definition.code];
        renderIndicatorSummary(
          definition,
          indicatorData,
          referenceResult?.status === "fulfilled" ? referenceResult.value : null,
          referenceResult?.status === "rejected",
        );
      });
    } else {
      vitalDefinitions.forEach((definition) => {
        const referenceResult = referencias[definition.code];
        renderIndicatorSummary(
          definition,
          null,
          referenceResult?.status === "fulfilled" ? referenceResult.value : null,
          referenceResult?.status === "rejected",
        );
      });
    }

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
        dateTime: record.dateTime,
        interpolated: record.interpolated[definition.key],
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
      const result = document.getElementById(`result-${definition.key}`);
      if (result) {
        result.classList.add("d-none");
        result.replaceChildren();
      }
    });

    try {
      const [[csvResult, relatorioResult], referenceResults] =
        await Promise.all([
          Promise.allSettled([
            window.sinaisVitaisService.buscarSinaisVitais(patient.id),
            window.sinaisVitaisService.buscarRelatorioSinaisVitais(patient.id),
          ]),
          Promise.allSettled(
            vitalDefinitions.map((definition) =>
              window.sinaisVitaisService.buscarTabelaReferenciaSinalVital(
                definition.code,
              ),
            ),
          ),
        ]);

      if (requestId !== vitalSignsRequest) {
        return;
      }

      const referencias = Object.fromEntries(
        vitalDefinitions.map((definition, index) => [
          definition.code,
          referenceResults[index],
        ]),
      );
      referenceResults.forEach((result, index) => {
        if (result.status === "rejected") {
          console.error(
            `Não foi possível carregar a tabela de referência para ${vitalDefinitions[index].code}.`,
            result.reason,
          );
        }
      });

      if (relatorioResult.status === "fulfilled") {
        renderAnalysisSummary(relatorioResult.value);
      } else {
        analysisSummary.classList.add("d-none");
        analysisSummary.replaceChildren();
      }

      if (csvResult.status !== "fulfilled") {
        throw csvResult.reason;
      }

      const parsedCsv = parseVitalSignsCsv(csvResult.value);
      vitalSignsLoading.classList.add("d-none");
      renderVitalSigns(
        parsedCsv,
        relatorioResult.status === "fulfilled" ? relatorioResult.value : null,
        referencias,
      );
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
