const lightState = document.getElementById('light-state');
const modeState = document.getElementById('mode');
const sensorValue = document.getElementById('sensor');
const thresholdValue = document.getElementById('threshold');
const thresholdInput = document.getElementById('threshold-input');

async function fetchStatus() {
  try {
    const response = await fetch('/api/status');
    if (!response.ok) {
      throw new Error('Ошибка запроса статуса');
    }
    const data = await response.json();
    renderStatus(data);
  } catch (err) {
    console.error(err);
  }
}

function renderStatus(data) {
  lightState.textContent = data.is_on ? 'включен' : 'выключен';
  modeState.textContent = data.auto ? 'авто' : 'ручной';
  sensorValue.textContent = data.sensor_value === null ? 'нет данных' : data.sensor_value.toFixed(2);
  thresholdValue.textContent = data.darkness_threshold.toFixed(2);
  thresholdInput.value = data.darkness_threshold.toFixed(2);
}

async function postJSON(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Запрос ${url} завершился ошибкой`);
  }
  return response.json();
}

document.getElementById('btn-auto').addEventListener('click', async () => {
  try {
    const data = await postJSON('/api/auto', { enabled: true });
    renderStatus(await fetch('/api/status').then(r => r.json()));
  } catch (err) {
    console.error(err);
  }
});

document.getElementById('btn-manual-on').addEventListener('click', async () => {
  try {
    await postJSON('/api/manual', { turn_on: true });
    renderStatus(await fetch('/api/status').then(r => r.json()));
  } catch (err) {
    console.error(err);
  }
});

document.getElementById('btn-manual-off').addEventListener('click', async () => {
  try {
    await postJSON('/api/manual', { turn_on: false });
    renderStatus(await fetch('/api/status').then(r => r.json()));
  } catch (err) {
    console.error(err);
  }
});

const form = document.getElementById('threshold-form');
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const value = parseFloat(thresholdInput.value);
  if (Number.isNaN(value)) {
    return;
  }
  try {
    await postJSON('/api/threshold', { value });
    renderStatus(await fetch('/api/status').then(r => r.json()));
  } catch (err) {
    console.error(err);
  }
});

fetchStatus();
setInterval(fetchStatus, 5000);
