(function () {
  function criarInformacao(label, value, className) {
    const container = document.createElement("div");
    container.className = className || "col-12 col-sm-6 col-xl-3";

    const term = document.createElement("dt");
    term.className = "patient-info-label";
    term.textContent = label;

    const description = document.createElement("dd");
    description.className = "patient-info-value mb-0";
    description.textContent = value;

    container.append(term, description);
    return container;
  }

  function mascararCpf(cpf) {
    const digits = cpf.replace(/\D/g, "");
    if (digits.length !== 11) {
      return "CPF indisponível";
    }

    return `${digits.slice(0, 3)}.***.***-${digits.slice(-2)}`;
  }

  function renderizarPaciente(patient, container) {
    const card = document.createElement("article");
    card.className = "patient-card card border-0";

    const body = document.createElement("div");
    body.className = "card-body";

    const header = document.createElement("div");
    header.className = "patient-card-header";

    const identity = document.createElement("div");
    identity.className = "d-flex align-items-center gap-3";

    const icon = document.createElement("span");
    icon.className = "patient-card-icon";
    icon.setAttribute("aria-hidden", "true");
    const iconGlyph = document.createElement("i");
    iconGlyph.className = "bi bi-person-vcard";
    icon.append(iconGlyph);

    const heading = document.createElement("div");
    const eyebrow = document.createElement("p");
    eyebrow.className = "eyebrow mb-1";
    eyebrow.textContent = "Paciente selecionado";
    const name = document.createElement("h2");
    name.className = "h4 mb-0";
    name.textContent = patient.nome;
    heading.append(eyebrow, name);
    identity.append(icon, heading);
    header.append(identity);

    const details = document.createElement("dl");
    details.className = "row g-3 patient-info-grid";
    details.append(
      criarInformacao("Identificador", patient.id),
      criarInformacao(
        "Idade",
        `${patient.idade} ${patient.idade === 1 ? "ano" : "anos"}`,
      ),
      criarInformacao("Gênero", patient.genero),
      criarInformacao("CPF", mascararCpf(patient.cpf)),
    );

    const history = document.createElement("div");
    history.className = "patient-history";
    const historyLabel = document.createElement("h3");
    historyLabel.className = "patient-info-label";
    historyLabel.textContent = "Histórico clínico";
    const historyText = document.createElement("p");
    historyText.className = "mb-0";
    historyText.textContent = patient.prontuario;
    history.append(historyLabel, historyText);

    body.append(header, details, history);
    card.append(body);
    container.replaceChildren(card);
    container.classList.remove("d-none");
  }

  window.pacienteComponent = { renderizarPaciente };
})();
