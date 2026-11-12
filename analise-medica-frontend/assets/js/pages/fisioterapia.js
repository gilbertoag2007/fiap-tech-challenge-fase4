(function () {
  const byId = (id) => document.getElementById(id);
  const exerciseSelect = byId('exercise-select');
  const cameraSelect = byId('camera-select');
  const videoSelect = byId('video-select');
  const analyze = byId('analyze-video');
  const player = byId('rehab-video');
  const overlay = byId('pose-overlay');
  const measureSelect = byId('measure-select');
  const service = window.fisioterapiaService;
  let catalog = { exercises: [], videos: [] };
  let revision = 0;
  let pollTimer = null;
  let animation = null;
  let pose = null;
  let report = null;
  let selectedRepetition = null;
  let chart = null;
  const names = {
    ombro_direito: 'Ângulo do ombro direito', ombro_esquerdo: 'Ângulo do ombro esquerdo',
    cotovelo_direito: 'Ângulo do cotovelo direito', cotovelo_esquerdo: 'Ângulo do cotovelo esquerdo',
    cotovelo: 'Ângulo do cotovelo', alinhamento_corporal: 'Alinhamento corporal',
    abducao_perna: 'Abdução da perna', joelho: 'Ângulo do joelho',
    separacao_pernas: 'Separação das pernas / tronco', inclinacao_tronco: 'Inclinação do tronco',
    assimetria_bracos: 'Assimetria dos braços',
  };
  const connections = [[5,6],[5,7],[7,9],[6,8],[8,10],[5,11],[6,12],[11,12],[11,13],[13,15],[12,14],[14,16]];

  function status(text) { byId('analysis-status').textContent = text; }
  function errorMessage(error) {
    byId('analysis-error').textContent = error.message === 'Failed to fetch'
      ? 'Não foi possível acessar a API. Confira se o servidor está em execução e tente novamente.' : error.message;
    byId('analysis-error').hidden = false;
  }
  function fillSelect(select, rows) {
    select.replaceChildren(...rows.map(([value, text]) => new Option(text, String(value))));
    select.disabled = !rows.length;
  }
  function selectedVideo() { return catalog.videos.find((video) => video.id === videoSelect.value); }
  function clearAnalysis() {
    revision += 1;
    clearTimeout(pollTimer);
    report = null; pose = null; selectedRepetition = null;
    byId('analysis-results').hidden = true;
    byId('analysis-error').hidden = true;
    byId('analysis-progress').hidden = true;
    byId('download-report').disabled = true;
    byId('selected-repetition').textContent = 'Selecione uma repetição após a análise.';
    fillSelect(measureSelect, []);
    if (chart) { chart.destroy(); chart = null; }
    overlay.getContext('2d').clearRect(0, 0, overlay.width, overlay.height);
  }
  function updateVideo() {
    clearAnalysis();
    const video = selectedVideo();
    analyze.disabled = !video;
    if (!video) { player.removeAttribute('src'); player.load(); status('Nenhuma gravação disponível.'); return; }
    player.src = service.videoUrl(video.id);
    byId('video-caption').textContent = 'Participante ' + video.person_id + ' · Câmera ' + video.camera;
    status('Gravação pronta para análise.');
  }
  function updateVideos() {
    const filtered = catalog.videos.filter((video) => video.exercise_id === Number(exerciseSelect.value) && video.camera === Number(cameraSelect.value));
    fillSelect(videoSelect, filtered.map((video) => [video.id, video.recording_id + ' — Participante ' + video.person_id]));
    updateVideo();
  }
  function updateCameras() {
    const cameras = [...new Set(catalog.videos.filter((video) => video.exercise_id === Number(exerciseSelect.value)).map((video) => video.camera))].sort();
    fillSelect(cameraSelect, cameras.map((camera) => [camera, 'Câmera ' + camera]));
    updateVideos();
  }
  async function loadCatalog() {
    clearAnalysis();
    analyze.disabled = true;
    byId('retry-catalog').hidden = true;
    status('Carregando o catálogo de vídeos…');
    try {
      const result = await service.catalog();
      if (!Array.isArray(result.exercises) || !Array.isArray(result.videos)) throw new Error('Catálogo de vídeos inválido.');
      catalog = result;
      fillSelect(exerciseSelect, catalog.exercises.map((exercise) => [exercise.id, exercise.name]));
      updateCameras();
    } catch (error) {
      status('Catálogo indisponível.');
      errorMessage(error);
      byId('retry-catalog').hidden = false;
    }
  }
  function seconds(value) { return Number(value).toFixed(1) + ' s'; }
  function addCell(row, text) { const cell = row.insertCell(); cell.textContent = text; return cell; }
  function renderReport(result) {
    if (!result || !Array.isArray(result.repetitions) || !result.summary) throw new Error('Relatório retornado pela API é inválido.');
    report = result;
    const summary = byId('analysis-summary');
    summary.replaceChildren();
    for (const [label, value] of [['Repetições',result.summary.total], ['Corretas',result.summary.correct], ['Incorretas',result.summary.incorrect], ['Não conclusivas',result.summary.nonconclusive]]) {
      const card = document.createElement('div'); card.className = 'rehab-stat';
      const number = document.createElement('strong'); number.textContent = value;
      const caption = document.createElement('span'); caption.textContent = label;
      card.append(number, caption); summary.append(card);
    }
    const body = byId('repetitions-body'); body.replaceChildren();
    for (const rep of result.repetitions) {
      const row = body.insertRow();
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'btn btn-sm btn-outline-primary';
      button.textContent = 'Ver repetição ' + rep.repetition_number;
      button.addEventListener('click', () => selectRepetition(rep, true));
      row.insertCell().append(button);
      addCell(row, seconds(rep.start_seconds) + ' – ' + seconds(rep.end_seconds));
      const prediction = addCell(row, rep.status);
      prediction.className = rep.prediction === null ? 'rehab-inconclusive' : rep.prediction === 0 ? 'rehab-incorrect' : 'rehab-correct';
      if (rep.reason) prediction.title = rep.reason;
      addCell(row, Math.round(rep.coverage * 100) + '%');
      addCell(row, rep.reference_label === 1 ? 'Correto' : rep.reference_label === 0 ? 'Incorreto' : 'Não informada');
    }
    byId('analysis-results').hidden = false;
    byId('download-report').disabled = false;
    if (result.repetitions.length) selectRepetition(result.repetitions[0], false);
  }
  function selectRepetition(rep, seek) {
    selectedRepetition = rep;
    byId('selected-repetition').textContent = 'Repetição ' + rep.repetition_number + ' · ' + seconds(rep.start_seconds) + ' a ' + seconds(rep.end_seconds);
    const keys = Object.keys((rep.series || []).find((row) => Object.keys(row).length) || {});
    fillSelect(measureSelect, keys.map((key) => [key, names[key] || key]));
    if (seek) { player.currentTime = rep.start_seconds; drawPose(); }
    drawChart();
  }
  function drawChart() {
    if (chart) { chart.destroy(); chart = null; }
    if (!selectedRepetition || !window.Chart || !measureSelect.value) return;
    const key = measureSelect.value;
    const fps = report.video.fps;
    const firstIndex = selectedRepetition.first_frame_index ?? Math.round(selectedRepetition.start_seconds * fps);
    const points = (selectedRepetition.series || []).map((row,index) => ({x:(firstIndex + index)/fps, y:row[key]}));
    chart = new window.Chart(byId('movement-chart'), {
      type: 'line', data: { datasets: [{label:names[key] || key, data:points, borderColor:'#087e8b', borderWidth:2, pointRadius:0, pointHitRadius:8, spanGaps:false}] },
      options: {responsive:true, maintainAspectRatio:false, animation:false,
        interaction:{intersect:false,mode:'nearest'}, plugins:{legend:{display:false}},
        scales:{x:{type:'linear',title:{display:true,text:'Tempo no vídeo (s)'}}, y:{title:{display:true,text:key==='separacao_pernas'?'Proporção':'Ângulo (graus)'}}}},
    });
  }
  function drawPose() {
    const rect = player.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    if (!rect.width || !rect.height) return;
    const w = Math.round(rect.width * dpr), h = Math.round(rect.height * dpr);
    if (overlay.width !== w || overlay.height !== h) { overlay.width = w; overlay.height = h; }
    const context = overlay.getContext('2d'); context.clearRect(0,0,w,h);
    if (!pose || !player.videoWidth) return;
    const frame = pose.points[Math.floor(player.currentTime * pose.fps)];
    if (!frame) return;
    const scale = Math.min(w/player.videoWidth, h/player.videoHeight);
    const width = player.videoWidth * scale, height = player.videoHeight * scale;
    const ox = (w-width)/2, oy = (h-height)/2;
    const visible = (point) => point && point[2] >= .5;
    context.strokeStyle = '#45f4c2'; context.fillStyle = '#fff'; context.lineWidth = 2*dpr;
    for (const [a,b] of connections) {
      if (!visible(frame[a]) || !visible(frame[b])) continue;
      context.beginPath(); context.moveTo(ox+frame[a][0]*width,oy+frame[a][1]*height);
      context.lineTo(ox+frame[b][0]*width,oy+frame[b][1]*height); context.stroke();
    }
    for (const point of frame.slice(5)) {
      if (!visible(point)) continue;
      context.beginPath(); context.arc(ox+point[0]*width,oy+point[1]*height,3*dpr,0,Math.PI*2); context.fill();
    }
  }
  function animate() { drawPose(); if (!player.paused && !player.ended) animation = requestAnimationFrame(animate); }
  async function analyzeVideo() {
    const video = selectedVideo(); if (!video) return;
    clearAnalysis(); const ownRevision = revision;
    analyze.disabled = true;
    const progress = byId('analysis-progress'); progress.hidden = false; progress.value = 0;
    status('Iniciando análise…');
    async function follow(task) {
      if (ownRevision !== revision) return;
      progress.value = Math.round(task.progress * 100);
      if (task.status === 'falhou') throw new Error(task.error || 'A análise falhou. Tente novamente.');
      if (task.status === 'concluido') {
        const result = await service.report(task.id);
        if (ownRevision !== revision) return;
        renderReport(result); progress.value = 100; status('Análise concluída. Selecione uma repetição para explorar o movimento.');
        analyze.disabled = false;
        try {
          const points = await service.pose(task.id);
          if (ownRevision === revision) { pose = points; drawPose(); }
        } catch (error) { if (ownRevision === revision) errorMessage(error); }
        return;
      }
      status(task.status === 'pendente' ? 'Aguardando processamento…' : 'Analisando os movimentos… ' + progress.value + '%');
      pollTimer = setTimeout(async () => {
        try { await follow(await service.task(task.id)); }
        catch (error) { failed(error); }
      }, 1000);
    }
    function failed(error) {
      if (ownRevision !== revision) return;
      errorMessage(error); status('Não foi possível concluir. Você pode tentar novamente.');
      analyze.disabled = false;
    }
    try { await follow(await service.create(video.id)); } catch (error) { failed(error); }
  }
  exerciseSelect.addEventListener('change', updateCameras);
  cameraSelect.addEventListener('change', updateVideos);
  videoSelect.addEventListener('change', updateVideo);
  analyze.addEventListener('click', analyzeVideo);
  measureSelect.addEventListener('change', drawChart);
  byId('retry-catalog').addEventListener('click', loadCatalog);
  byId('download-report').addEventListener('click', () => {
    if (!report) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(report,null,2)], {type:'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = 'fisioterapia-' + report.video.id + '.json';
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  player.addEventListener('play', () => { cancelAnimationFrame(animation); animate(); });
  player.addEventListener('timeupdate', drawPose);
  player.addEventListener('loadedmetadata', drawPose);
  window.addEventListener('resize', drawPose);
  window.addEventListener('pagehide', () => { revision += 1; clearTimeout(pollTimer); cancelAnimationFrame(animation); });
  loadCatalog();
})();
