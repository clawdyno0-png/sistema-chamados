document.addEventListener("DOMContentLoaded", function () {
  const filtroStatus = document.getElementById("filtro-status");
  const filtroPrioridade = document.getElementById("filtro-prioridade");
  const linhasChamado = document.querySelectorAll(".linha-chamado");

  function aplicarFiltros() {
    const statusSelecionado = filtroStatus ? filtroStatus.value.toLowerCase() : "";
    const prioridadeSelecionada = filtroPrioridade ? filtroPrioridade.value.toLowerCase() : "";

    linhasChamado.forEach((linha) => {
      const statusLinha = (linha.dataset.status || "").toLowerCase();
      const prioridadeLinha = (linha.dataset.prioridade || "").toLowerCase();

      const statusOk = !statusSelecionado || statusLinha === statusSelecionado;
      const prioridadeOk = !prioridadeSelecionada || prioridadeLinha === prioridadeSelecionada;

      if (statusOk && prioridadeOk) {
        linha.style.display = "";
      } else {
        linha.style.display = "none";
      }
    });
  }

  if (filtroStatus) {
    filtroStatus.addEventListener("change", aplicarFiltros);
  }

  if (filtroPrioridade) {
    filtroPrioridade.addEventListener("change", aplicarFiltros);
  }

  aplicarFiltros();
});
