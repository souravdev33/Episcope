let D;
let selectedDistrict = "ALL";
let selectedDisease = "dengue";
let forecastHorizon = 1;
const $ = (selector) => document.querySelector(selector);

function init(data, boundaries) {
  D = data;
  D.boundaries = boundaries;
  $("#fresh").textContent = new Date(data.generated_at).toLocaleString();
  data.diseases.forEach((value) => $("#disease").add(new Option(value, value)));
  data.districts.forEach((value) => $("#district").add(new Option(value, value)));
  selectedDisease = data.diseases[0] || selectedDisease;
  $("#disease").value = selectedDisease;
  $("#disease").addEventListener("change", () => {
    selectedDisease = $("#disease").value;
    render();
  });
  $("#district").addEventListener("change", () => {
    selectedDistrict = $("#district").value;
    render();
  });
  $("#horizon").addEventListener("change", () => {
    forecastHorizon = Number($("#horizon").value);
    render();
  });
  $("#reset").addEventListener("click", () => {
    selectedDistrict = "ALL";
    selectedDisease = data.diseases[0];
    forecastHorizon = 1;
    $("#district").value = "ALL";
    $("#disease").value = selectedDisease;
    $("#horizon").value = "1";
    render();
  });
  render();
}
function chooseDistrict(name) {
  selectedDistrict = selectedDistrict === name ? "ALL" : name;
  $("#district").value = selectedDistrict;
  render();
}
function render() {
  drawMap();
  drawSeries();
  drawHeatmap();
  drawAllocation();
  drawWarnings();
  drawQuality();
}
function noData(element, message) {
  element.innerHTML = "";
  const state = document.createElement("div");
  state.className = "empty-state";
  state.textContent = message;
  element.append(state);
}
function selectedRows(rows) {
  return rows.filter((row) => row.disease === selectedDisease &&
    (selectedDistrict === "ALL" || row.district === selectedDistrict));
}
function drawMap() {
  const element = $("#map");
  element.innerHTML = "";
  const width = element.clientWidth || 620;
  const height = 270;
  const svg = d3.select(element).append("svg").attr("viewBox", "0 0 " + width + " " + height);
  const rows = D.heatmap.filter((row) => row.disease === selectedDisease);
  if (!rows.length) return noData(element, "No district data matches this disease.");
  const latestYear = d3.max(rows, (row) => row.year);
  const counts = new Map();
  rows.filter((row) => row.year === latestYear).forEach((row) => {
    counts.set(row.district, (counts.get(row.district) || 0) + (row.cases || 0));
  });
  const rates = new Map(D.districts.map((district) => {
    const denominator = Number(D.population[district]) || 0;
    const count = counts.get(district) || 0;
    return [district, denominator ? count / denominator * 100000 : 0];
  }));
  const maxRate = d3.max([...rates.values()]) || 1;
  const color = d3.scaleSequential([0, maxRate], d3.interpolateViridis);
  const features = D.boundaries && D.boundaries.features;
  if (features && features.length) {
    $("#map-tag").textContent = "ADM2 CHOROPLETH";
    const collection = { type: "FeatureCollection", features };
    const projection = d3.geoMercator().fitSize([width - 12, height - 12], collection);
    const path = d3.geoPath(projection);
    const districtName = (feature) => feature.properties.district ||
      feature.properties.shapeName || feature.properties.name;
    svg.selectAll("path").data(features).join("path")
      .attr("d", path)
      .attr("fill", (feature) => {
        const name = districtName(feature);
        const count = counts.get(name) || 0;
        return count > 0 && count < 5 ? "#dce4e7" : color(rates.get(name) || 0);
      })
      .attr("stroke", (feature) => districtName(feature) === selectedDistrict ? "#102d3e" : "#fff")
      .attr("stroke-width", (feature) => districtName(feature) === selectedDistrict ? 2 : .7)
      .style("cursor", "pointer")
      .on("click", (event, feature) => chooseDistrict(districtName(feature)))
      .append("title").text((feature) => {
        const name = districtName(feature);
        const count = counts.get(name) || 0;
        const rate = rates.get(name) || 0;
        return name + ": " + (count > 0 && count < 5 ? "count suppressed" :
          count.toLocaleString() + " reports") + " | " + rate.toFixed(1) +
          " reports per 100,000 | " + latestYear;
      });
    return;
  }
  $("#map-tag").textContent = "SCHEMATIC FALLBACK";
  const columns = 8;
  D.districts.forEach((district, index) => {
    const x = 10 + (index % columns) * (width - 20) / columns;
    const y = 8 + Math.floor(index / columns) * 29;
    const tileWidth = (width - 20) / columns - 3;
    const value = counts.get(district) || 0;
    const group = svg.append("g").style("cursor", "pointer")
      .on("click", () => chooseDistrict(district));
    group.append("rect").attr("class", "tile")
      .attr("x", x).attr("y", y).attr("width", tileWidth).attr("height", 23).attr("rx", 5)
      .attr("fill", value > 0 && value < 5 ? "#dce4e7" : color(rates.get(district) || 0));
    group.append("text").attr("x", x + tileWidth / 2).attr("y", y + 14)
      .attr("text-anchor", "middle").attr("fill", (rates.get(district) || 0) > maxRate * .58 ? "#fff" : "#203645")
      .attr("font-size", "8px").text(district.slice(0, 9));
    group.append("title").text(district + " - schematic tile");
  });
}
function drawSeries() {
  const element = $("#series");
  element.innerHTML = "";
  const totals = new Map();
  selectedRows(D.heatmap).forEach((row) => {
    const key = row.year + "-W" + String(row.week).padStart(2, "0");
    totals.set(key, (totals.get(key) || 0) + (row.cases || 0));
  });
  const points = [...totals].sort((a, b) => a[0].localeCompare(b[0]))
    .slice(-24).map(([week, value]) => ({ week, value }));
  if (!points.length) return noData(element, "No weekly observations match this selection.");
  const forecasts = selectedRows(D.forecasts).filter((row) => row.horizon === forecastHorizon);
  const forecast = d3.sum(forecasts, (row) => row.mean || 0);
  const lower = d3.sum(forecasts, (row) => row.lower80 || 0);
  const upper = d3.sum(forecasts, (row) => row.upper80 || 0);
  const width = element.clientWidth || 560;
  const height = 250;
  const margin = { top: 14, right: 15, bottom: 38, left: 43 };
  const x = d3.scaleLinear([0, Math.max(1, points.length - 1 + forecastHorizon)],
    [margin.left, width - margin.right]);
  const y = d3.scaleLinear([0, Math.max(1, d3.max(points, (row) => row.value) || 1, upper * 1.15)],
    [height - margin.bottom, margin.top]);
  const svg = d3.select(element).append("svg").attr("viewBox", "0 0 " + width + " " + height);
  svg.append("g").attr("class", "axis").attr("transform", "translate(0," + (height - margin.bottom) + ")")
    .call(d3.axisBottom(x).ticks(5).tickFormat((index) =>
      points[Math.round(index)] ? points[Math.round(index)].week : "Forecast"));
  svg.append("g").attr("class", "axis").attr("transform", "translate(" + margin.left + ",0)")
    .call(d3.axisLeft(y).ticks(5));
  svg.append("path").datum(points).attr("fill", "none").attr("stroke", "#167b76")
    .attr("stroke-width", 2.5).attr("d", d3.line().x((row, i) => x(i)).y((row) => y(row.value)));
  svg.selectAll(".observation").data(points).join("circle")
    .attr("class", "observation").attr("cx", (row, i) => x(i)).attr("cy", (row) => y(row.value))
    .attr("r", 2.5).attr("fill", "#167b76")
    .append("title").text((row) => row.week + ": " +
      (row.value < 5 ? "suppressed" : row.value + " reported cases"));
  if (forecasts.length) {
    const x1 = x(points.length - 1);
    const x2 = x(points.length - 1 + forecastHorizon);
    svg.append("rect").attr("x", x1).attr("y", y(upper))
      .attr("width", Math.max(3, x2 - x1)).attr("height", Math.max(2, y(lower) - y(upper)))
      .attr("fill", "#eacb91").attr("opacity", .55);
    svg.append("path")
      .attr("d", "M" + x1 + "," + y(points[points.length - 1].value) + "L" + x2 + "," + y(forecast))
      .attr("fill", "none").attr("stroke", "#b8793e").attr("stroke-width", 2)
      .attr("stroke-dasharray", "5 4");
  }
}
function drawHeatmap() {
  const element = $("#heat");
  element.innerHTML = "";
  const rows = selectedRows(D.heatmap);
  const districts = selectedDistrict === "ALL" ? D.districts : [selectedDistrict];
  const max = d3.max(rows, (row) => row.cases || 0) || 5;
  districts.forEach((district) => {
    const rowElement = document.createElement("div");
    rowElement.className = "gridrow";
    const name = document.createElement("span");
    name.className = "district-name";
    name.textContent = district;
    rowElement.append(name);
    for (let week = 1; week <= 52; week += 1) {
      const value = d3.sum(rows.filter((row) => row.district === district && row.week === week),
        (row) => row.cases || 0);
      const cell = document.createElement("span");
      cell.className = "cell";
      cell.title = district + " - week " + week + ": " +
        (value < 5 ? "suppressed" : value + " reports");
      cell.style.background = value < 5
        ? "repeating-linear-gradient(135deg,#eee,#eee 3px,#ccd6da 3px,#ccd6da 5px)"
        : d3.interpolateViridis(value / max);
      cell.addEventListener("click", () => chooseDistrict(district));
      rowElement.append(cell);
    }
    element.append(rowElement);
  });
}
function drawAllocation() {
  const element = $("#allocation");
  element.innerHTML = "";
  const rows = D.allocations.filter((row) =>
    selectedDistrict === "ALL" || row.district === selectedDistrict)
    .sort((a, b) => b.recommended_units - a.recommended_units);
  if (!rows.length) return noData(element, "No allocation rows match this selection.");
  const table = document.createElement("table");
  table.className = "tbl";
  table.innerHTML = "<thead><tr><th>District</th><th>Demand</th><th>Stock*</th><th>Suggested</th></tr></thead>";
  const body = table.createTBody();
  rows.forEach((row) => {
    const tr = body.insertRow();
    tr.addEventListener("click", () => chooseDistrict(row.district));
    [row.district, row.demand_units, row.current_stock_units, row.recommended_units]
      .forEach((value) => { tr.insertCell().textContent = value; });
  });
  element.append(table);
  const note = document.createElement("p");
  note.className = "table-note";
  note.textContent = "Budget scenarios: " + D.budget_curve.map((row) =>
    "BDT " + (row.budget / 1000) + "k / " + row.units_funded + " units").join(" | ");
  element.append(note);
}
function drawWarnings() {
  const element = $("#warnings");
  element.innerHTML = "";
  const rows = selectedRows(D.alerts).sort((a, b) => b.score - a.score).slice(0, 20);
  if (!rows.length) return noData(element, "No threshold flags for this selection.");
  const table = document.createElement("table");
  table.className = "tbl";
  table.innerHTML = "<thead><tr><th>District</th><th>Week</th><th>Observed</th><th>Expected</th><th>Score</th></tr></thead>";
  const body = table.createTBody();
  rows.forEach((row) => {
    const tr = body.insertRow();
    tr.addEventListener("click", () => chooseDistrict(row.district));
    [row.district, row.year + "-W" + row.week, row.observed, row.expected, row.score]
      .forEach((value, index) => {
        const cell = tr.insertCell();
        cell.textContent = value;
        if (index === 4) cell.className = "warn";
      });
  });
  element.append(table);
}
function drawQuality() {
  const element = $("#quality");
  element.innerHTML = "";
  const q = D.quality;
  [["Rows received", q.rows_in], ["Valid silver", q.rows_clean],
    ["Quarantined", q.rows_quarantined], ["Rules applied", q.rule_count]]
    .forEach(([label, value]) => {
      const metric = document.createElement("div");
      metric.className = "metric";
      metric.innerHTML = "<b>" + Number(value).toLocaleString() + "</b><small>" + label + "</small>";
      element.append(metric);
    });
}
Promise.all([
  fetch("../data/serving/dashboard.json").then((response) => {
    if (!response.ok) throw new Error("Build the lake and analytics outputs first.");
    return response.json();
  }),
  fetch("../data/serving/districts.geojson")
    .then((response) => response.ok ? response.json() : null)
    .catch(() => null)
]).then(([data, boundaries]) => init(data, boundaries))
  .catch((error) => { $("#fresh").textContent = error.message; });
