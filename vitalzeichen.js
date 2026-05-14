const data = [
  {date:'2026-03-08',time:'08:00',sys:128,dia:81,p:79,o:95,t:37.1,v:3},
  {date:'2026-03-08',time:'12:00',sys:130,dia:85,p:82,o:96,t:37.0,v:2},
  {date:'2026-03-08',time:'16:00',sys:122,dia:78,p:76,o:97,t:36.8,v:4},
  {date:'2026-03-08',time:'20:00',sys:135,dia:88,p:84,o:94,t:37.2,v:3},
  {date:'2026-03-09',time:'08:00',sys:124,dia:79,p:80,o:97,t:36.9,v:2},
  {date:'2026-03-09',time:'12:00',sys:126,dia:82,p:83,o:96,t:37.0,v:3},
  {date:'2026-03-09',time:'16:30',sys:120,dia:70,p:78,o:97,t:36.8,v:3},
  {date:'2026-03-09',time:'20:00',sys:132,dia:86,p:85,o:95,t:37.1,v:4}
];

const canvas = document.getElementById('chart');
const ctx = canvas.getContext('2d');

const topPad = 20;
const bottomPad = 240;
const startX = 70;
const step = 165;

function yRR(v){ return bottomPad - ((v - 20) / (200 - 20)) * (bottomPad - topPad); }
function yO(v){ return bottomPad - ((v - 50) / (100 - 50)) * (bottomPad - topPad); }
function yT(v){ return bottomPad - ((v - 35) / (41 - 35)) * (bottomPad - topPad); }
function yV(v){ return bottomPad - ((v - 0) / (10 - 0)) * (bottomPad - topPad); }

function drawGrid(){
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  for(let i=0;i<=12;i++){
    const y = topPad + ((bottomPad - topPad) / 12) * i;
    ctx.strokeStyle = i % 2 === 0 ? '#a5afc1' : '#cdd5e3';
    ctx.lineWidth = i % 2 === 0 ? 1.4 : 1;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }

  data.forEach((d,i)=>{
    const x = startX + i * step;
    ctx.strokeStyle = '#edf1f7';
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, bottomPad);
    ctx.stroke();
  });
}

function drawPolyline(values, color, mapFn){
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  values.forEach((val,i)=>{
    const x = startX + i * step;
    const y = mapFn(val);
    if(i===0) ctx.moveTo(x,y);
    else ctx.lineTo(x,y);
  });
  ctx.stroke();

  values.forEach((val,i)=>{
    const x = startX + i * step;
    const y = mapFn(val);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x,y,3.4,0,Math.PI*2);
    ctx.fill();
  });
}

function drawRRandPulse(){
  data.forEach((d,i)=>{
    const x = startX + i * step;
    const ySys = yRR(d.sys);
    const yDia = yRR(d.dia);

    ctx.strokeStyle = '#2f8f4e';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x,ySys);
    ctx.lineTo(x,yDia);
    ctx.stroke();

    ctx.fillStyle = '#2f8f4e';
    ctx.beginPath();
    ctx.moveTo(x-7,ySys-4);
    ctx.lineTo(x+7,ySys-4);
    ctx.lineTo(x,ySys+9);
    ctx.closePath();
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(x-7,yDia+4);
    ctx.lineTo(x+7,yDia+4);
    ctx.lineTo(x,yDia-9);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = '#cf2f2f';
    ctx.beginPath();
    ctx.arc(x, yRR(d.p), 6, 0, Math.PI * 2);
    ctx.shadowColor = 'rgba(207,47,47,0.3)';
    ctx.shadowBlur = 6;
    ctx.fill();
    ctx.shadowBlur = 0;
  });
}

function drawAxisLabels(){
  data.forEach((d,i)=>{
    const x = startX + i * step;
    ctx.fillStyle = '#5a6483';
    ctx.font = '12px Arial';
    ctx.fillText(d.time, x-18, 260);
    if(i===0 || data[i-1].date !== d.date){
      ctx.font = '11px Arial';
      ctx.fillStyle = '#8891aa';
      ctx.fillText(d.date, x-30, 275);
    }
  });
}

function updateMetrics(){
  const d = data[data.length - 1];
  m_rr.innerText = d.sys + '/' + d.dia;
  m_p.innerText = d.p;
  m_o.innerText = d.o;
  m_t.innerText = Number(d.t).toFixed(1);
  m_v.innerText = d.v;
}

function updateTable(){
  tableBody.innerHTML = '';
  data.forEach(d=>{
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${d.date}</td>
      <td>${d.time}</td>
      <td>${d.sys}/${d.dia}</td>
      <td>${d.p}</td>
      <td>${d.o}</td>
      <td>${d.t}</td>
      <td>${d.v}</td>
    `;
    tableBody.appendChild(tr);
  });
}

function renderChart(){
  ctx.clearRect(0,0,canvas.width,canvas.height);
  drawGrid();
  drawPolyline(data.map(d=>d.o), '#336af1', yO);
  drawPolyline(data.map(d=>d.t), '#e48a24', yT);
  drawPolyline(data.map(d=>d.v), '#7b3fe0', yV);
  drawRRandPulse();
  drawAxisLabels();
  updateMetrics();
  updateTable();
}

openModal.onclick = () => modal.hidden = false;
close.onclick = () => modal.hidden = true;
document.querySelector('.doc-modal__backdrop').onclick = () => modal.hidden = true;
toggleTable.onclick = () => { tableWrap.hidden = !tableWrap.hidden; };

save.onclick = () => {
  data.push({
    date: date.value || '2026-03-10',
    time: time.value || '08:00',
    sys: +sys.value || 120,
    dia: +dia.value || 80,
    p: +pulse.value || 80,
    o: +o2.value || 97,
    t: +temp.value || 36.8,
    v: +vas.value || 3
  });
  modal.hidden = true;
  renderChart();
};

renderChart();