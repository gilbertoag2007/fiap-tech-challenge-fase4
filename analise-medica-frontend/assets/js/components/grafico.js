(function () {
  const charts = new Map();
  const gridColor = "rgba(52, 64, 84, 0.08)";

  function formatElapsedTime(seconds) {
    const totalSeconds = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const remainingSeconds = totalSeconds % 60;

    return [hours, minutes, remainingSeconds]
      .map((part) => String(part).padStart(2, "0"))
      .join(":");
  }

  function criarGrafico(configuration) {
    const canvas = document.getElementById(configuration.canvasId);
    if (!canvas) {
      throw new Error(`Canvas não encontrado: ${configuration.canvasId}`);
    }

    const previousChart = charts.get(configuration.canvasId);
    if (previousChart) {
      previousChart.destroy();
    }

    const chart = new window.Chart(canvas, {
      type: "line",
      data: {
        datasets: [
          {
            label: `${configuration.name} (${configuration.code})`,
            data: configuration.points,
            borderColor: configuration.color,
            backgroundColor: configuration.color,
            borderWidth: 2,
            pointRadius: configuration.pointCount === 1 ? 3 : 0,
            pointHoverRadius: 4,
            pointHitRadius: 8,
            tension: 0.2,
            spanGaps: false,
          },
        ],
      },
      options: {
        animation: {
          duration: 250,
        },
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: "nearest",
        },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              title(items) {
                if (!items.length) {
                  return "";
                }

                return [
                  "Data: não informada pelo CSV",
                  `Tempo decorrido: ${formatElapsedTime(items[0].parsed.x)}`,
                ];
              },
              label(context) {
                return `${configuration.name}: ${context.parsed.y} ${configuration.unit}`;
              },
            },
          },
        },
        scales: {
          x: {
            type: "linear",
            title: {
              display: true,
              text: "Tempo decorrido (hh:mm:ss)",
              color: "#667085",
            },
            grid: {
              display: false,
            },
            ticks: {
              color: "#667085",
              maxTicksLimit: 8,
              callback(value) {
                return formatElapsedTime(value);
              },
            },
          },
          y: {
            title: {
              display: true,
              text: configuration.unit,
              color: "#667085",
            },
            grid: {
              color: gridColor,
            },
            ticks: {
              color: "#667085",
            },
          },
        },
      },
    });

    charts.set(configuration.canvasId, chart);
    return chart;
  }

  function destruirGraficos() {
    charts.forEach((chart) => chart.destroy());
    charts.clear();
  }

  window.graficoComponent = { criarGrafico, destruirGraficos };
})();
