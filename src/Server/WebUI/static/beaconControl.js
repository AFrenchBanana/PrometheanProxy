let beaconTimers = {};
let loadingDotsInterval;

// Function to show/hide loading spinner
function toggleLoadingSpinner(show) {
    const spinner = document.getElementById('loading-spinner');
    const tableContainer = document.getElementById('beacon-table-container');
    const loadingMessage = document.getElementById('loading-message');

    if (!spinner || !tableContainer || !loadingMessage) {
        console.error('Required elements not found');
        return;
    }

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

// Function to format date without milliseconds
function formatDateWithoutMilliseconds(date) {
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    return `${day}/${month} ${hours}:${minutes}:${seconds}`;
}

// Function to format time in minutes and seconds
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
}

// Function to update beacon data dynamically
function updateLastBeacon(data) {
    const beaconTableBody = document.getElementById('beacon-table-body');
    if (!beaconTableBody) {
        console.error('Beacon table body not found');
        return;
    }

    const beacon = data.beacon;
    const lastBeaconDate = new Date(beacon.last_beacon);
    const nextBeaconDate = new Date(lastBeaconDate.getTime() + Number(beacon.timer) * 1000);

    // Check if the row already exists
    let row = document.getElementById(`beacon-${uuid}`);
    if (!row) {
        row = document.createElement('tr');
        row.id = `beacon-${uuid}`;
        row.innerHTML = `
            <td>${uuid}</td>
            <td>${beacon.address}</td>
            <td>${beacon.hostname}</td>
            <td>${beacon.operating_system}</td>
            <td><span class="last-beacon">${formatDateWithoutMilliseconds(lastBeaconDate)}</span></td>
            <td><span class="next-beacon" id="next-beacon-${uuid}">${formatDateWithoutMilliseconds(nextBeaconDate)}</span></td>
            <td><span class="countdown" id="countdown-${uuid}"></span></td>
        `;
        beaconTableBody.appendChild(row);
    } else {
        // Update existing row
        row.querySelector('.last-beacon').textContent = formatDateWithoutMilliseconds(lastBeaconDate);
        row.querySelector('.next-beacon').textContent = formatDateWithoutMilliseconds(nextBeaconDate);
        row.classList.add('highlight');
        setTimeout(() => row.classList.remove('highlight'), 2000);
    }

    beaconTimers[uuid] = {
        lastBeacon: lastBeaconDate,
        timer: beacon.timer,
        jitter: beacon.jitter
    };

    console.log('Beacon updated:', data.beacon);
}

// Function to update the countdown and color based on time difference
function updateNextBeacon(uuid) {
    const countdownElement = document.getElementById(`countdown-${uuid}`);

    if (!countdownElement) {
        console.error(`Countdown element not found for uuid: ${uuid}`);
        return;
    }

    const timerData = beaconTimers[uuid];
    if (!timerData) {
        console.error(`Timer data not found for uuid: ${uuid}`);
        return;
    }

    const { lastBeacon, timer, jitter } = timerData;
    const nextBeaconDate = new Date(lastBeacon.getTime() + Number(timer) * 1000);
    const expectedNextBeaconDate = new Date(nextBeaconDate.getTime() + Number(jitter) * 1000);

    const currentTime = new Date();
    const timeDiff = nextBeaconDate - currentTime;
    const jitterDiff = expectedNextBeaconDate - currentTime;

    // Update the countdown text and style based on the time difference
    if (timeDiff >= 0) {
        countdownElement.textContent = `Next Callback expected in ${formatTime(Math.floor(timeDiff / 1000))}`;
        countdownElement.style.color = 'green';
    } else if (jitterDiff >= 0) {
        countdownElement.textContent = `Expected Callback was ${nextBeaconDate.toISOString()}. It is ${formatTime(Math.abs(Math.floor(timeDiff / 1000)))} late. (Within Jitter)`;
        countdownElement.style.color = 'orange';
    } else {
        countdownElement.textContent = `Expected Callback was ${expectedNextBeaconDate.toISOString()}. It is ${formatTime(Math.abs(Math.floor(jitterDiff / 1000)))} late`;
        countdownElement.style.color = 'red';
    }
}

function updateCountdowns() {
    Object.keys(beaconTimers).forEach((uuid) => {
        updateNextBeacon(uuid);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('Document loaded');
    toggleLoadingSpinner(true);

    // Initialize WebSocket connection
    const socket = io('http://127.0.0.1:8080');

    // Log WebSocket connection details
    socket.on('connect', () => {
        console.log('WebSocket connected');
    });

    socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
    });

    socket.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error);
    });

    // Log WebSocket requests
    socket.onAny((event, ...args) => {
        console.log(`WebSocket request: Event=${event}, Args=${JSON.stringify(args)}`);
    });

    // Listen for beacon updates
    socket.on('beacon_update', (data) => {
        // Only update if the data contains our specific UUID
        if (data.beacons && data.beacons[uuid]) {
            const singleBeaconData = {
                beacon: data.beacons[uuid]
            };
            updateLastBeacon(singleBeaconData);
            updateNextBeacon(uuid);
            toggleLoadingSpinner(false);
        }
    });

    // Handle countdown updates
    socket.on('countdown_update', (data) => {
        if (data.uuid && data.timer !== undefined && data.jitter !== undefined) {
            const countdownElement = document.querySelector(`#countdown-${data.uuid}`);
            if (countdownElement) {
                const { timer, jitter } = data;
    
                // Get the last beacon time and calculate the next expected time
                const lastBeacon = beaconTimers[data.uuid].lastBeacon;
                const nextBeaconDate = new Date(lastBeacon.getTime() + (timer * 1000));
                const expectedNextBeaconDate = new Date(nextBeaconDate.getTime() + (jitter * 1000));
    
                const currentTime = new Date();
                const timeDiff = nextBeaconDate - currentTime;
                const jitterDiff = expectedNextBeaconDate - currentTime;
    
                // Update the countdown text and color based on the time difference
                if (timeDiff >= 0) {
                    countdownElement.textContent = `Next Callback expected in ${formatTime(Math.floor(timeDiff / 1000))}`;
                    countdownElement.style.color = 'green';
                } else if (jitterDiff >= 0) {
                    countdownElement.textContent = `Expected Callback was ${nextBeaconDate.toISOString()}. It is ${formatTime(Math.abs(Math.floor(timeDiff / 1000)))} late. (Within Jitter)`;
                    countdownElement.style.color = 'orange';
                } else {
                    countdownElement.textContent = `Expected Callback was ${expectedNextBeaconDate.toISOString()}. It is ${formatTime(Math.abs(Math.floor(jitterDiff / 1000)))} late`;
                    countdownElement.style.color = 'red';
                }
    
                // Update beaconTimers to reflect the latest countdown update
                beaconTimers[data.uuid].lastBeacon = new Date(expectedNextBeaconDate.getTime() - jitterDiff);
    
                // Highlight the row green (no fade-out effect)
                const row = document.getElementById(`beacon-${data.uuid}`);
                if (row) {
                    // Add Bootstrap class for green background
                    row.classList.add('bg-success', 'text-white');
    
                    // Set a timeout to remove the highlight after 1 second
                    setTimeout(() => {
                        row.classList.remove('bg-success', 'text-white');
                    }, 1000); // 1 second for the highlight effect
                }
            } else {
                console.error(`Countdown element not found for uuid: ${data.uuid}`);
            }
        }
    });

    // Set intervals for updating countdowns
    setInterval(() => updateNextBeacon(uuid), 1000);

    fetch(`/api/v1/beacons/${uuid}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Received beacon data:', data);
            if (!data.beacon) {
                console.error('No beacon data received');
                toggleLoadingSpinner(true);
            } else {
                updateLastBeacon(data);
                updateNextBeacon(uuid);
                toggleLoadingSpinner(false);
            }
        })
        .catch(error => {
            console.error('Error fetching beacon:', error);
            toggleLoadingSpinner(true);
        });
});

// Expose necessary functions and variables to the global scope
window.beaconTimers = beaconTimers;
window.formatDateWithoutMilliseconds = formatDateWithoutMilliseconds;
window.updateNextBeacon = updateNextBeacon;
window.toggleLoadingSpinner = toggleLoadingSpinner;
