let beaconTimers = {};
let loadingDotsInterval;

// Function to show/hide loading spinner
function toggleLoadingSpinner(show) {
    const spinner = document.getElementById('loading-spinner');
    const tableContainer = document.getElementById('beacon-table-container');
    const loadingMessage = document.getElementById('loading-message');
    if (show) {
        spinner.classList.remove('d-none');
        tableContainer.classList.add('d-none');
        loadingMessage.classList.remove('d-none');
        startLoadingDots();
    } else {
        spinner.classList.add('d-none');
        tableContainer.classList.remove('d-none');
        loadingMessage.classList.add('d-none');
        stopLoadingDots();
    }
}

function startLoadingDots() {
    let dotCount = 0;
    loadingDotsInterval = setInterval(() => {
        dotCount = (dotCount + 1) % 4;
        const dots = '.'.repeat(dotCount);
        document.getElementById('loading-message').textContent = `Waiting for beacons${dots}`;
    }, 500);
}

function stopLoadingDots() {
    clearInterval(loadingDotsInterval);
}

// Function to update beacon data dynamically
function updateLastBeacon() {
    fetch('/api/beacons')
        .then(response => response.json())
        .then(data => {
            const beaconTableBody = document.getElementById('beacon-table-body');
            beaconTableBody.innerHTML = ''; // Clear existing rows

            if (Object.keys(data.beacons).length === 0) {
                toggleLoadingSpinner(true);
                return;
            }

            toggleLoadingSpinner(false);

            Object.keys(data.beacons).forEach((uuid, index) => {
                const beacon = data.beacons[uuid];
                const row = `
                    <tr id="beacon-${index}" onclick="window.location.href='/beacons?uuid=${uuid}'">
                        <td>${uuid}</td>
                        <td>${beacon.address}</td>
                        <td>${beacon.hostname}</td>
                        <td>${beacon.operating_system}</td>
                        <td><span class="last-beacon">${beacon.last_beacon}</span></td>
                        <td><span class="next-beacon" id="next-beacon-${index}">${beacon.next_beacon}</span></td>
                        <td><span class="countdown" id="countdown-${index}"></span></td>
                    </tr>
                `;
                beaconTableBody.insertAdjacentHTML('beforeend', row);
                beaconTimers[uuid] = {
                    lastBeacon: new Date(beacon.last_beacon),
                    timer: beacon.timer,
                    jitter: beacon.jitter
                };
            });
            console.log('Beacons updated:', data.beacons);
        })
        .catch(error => {
            console.error('Error fetching beacons:', error);
            toggleLoadingSpinner(true);
        });
}

// Function to update the countdown and color based on time difference
function updateNextBeacon(uuid, index) {
    const countdownElement = document.querySelector(`#countdown-${index}`);

    const { lastBeacon, timer, jitter } = beaconTimers[uuid];
    const nextBeaconDate = new Date(lastBeacon.getTime() + timer * 1000);
    const expectedNextBeaconDate = new Date(nextBeaconDate.getTime() + jitter * 1000);

    const currentTime = new Date();
    const timeDiff = expectedNextBeaconDate - currentTime;
    const expectedTime = expectedNextBeaconDate - nextBeaconDate;

    if (timeDiff >= 0) {
        countdownElement.textContent = `Next Callback expected in ${Math.floor(timeDiff / 1000)} seconds`;
        countdownElement.style.color = 'green';
    } else if (Math.abs(timeDiff) <= expectedTime) {
        countdownElement.textContent = `Expected Callback was ${expectedNextBeaconDate.toISOString()}. It is ${Math.abs(Math.floor(timeDiff / 1000))} seconds late. (Within Jitter)`;
        countdownElement.style.color = 'orange';
    } else {
        countdownElement.textContent = `Expected Callback was ${expectedNextBeaconDate.toISOString()}. It is ${Math.abs(Math.floor(timeDiff / 1000))} seconds late`;
        countdownElement.style.color = 'red';
    }
}

function updateCountdowns() {
    Object.keys(beaconTimers).forEach((uuid, index) => {
        updateNextBeacon(uuid, index);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('Document loaded');
    updateLastBeacon();
    setInterval(updateCountdowns, 1000);
    setInterval(updateLastBeacon, 5000);
});
