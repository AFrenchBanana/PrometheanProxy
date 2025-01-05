let beaconTimers = {};
// const socket = io();


document.addEventListener('DOMContentLoaded', function() {
    fetch(`/api/v1/beacons?history=${window.uuid}`)
        .then(response => response.json())
        .then(data => {
            const resultsInfo = document.getElementById('results-info');
            resultsInfo.innerHTML = ''; // Clear existing content

            if (data.history && data.history.length > 0) {
                const table = document.createElement('table');
                table.classList.add('table');

                const thead = document.createElement('thead');
                thead.innerHTML = `
                    <tr>
                        <th>Command ID</th>
                        <th>Command</th>
                        <th>Response</th>
                    </tr>
                `;
                table.appendChild(thead);

                const tbody = document.createElement('tbody');
                tbody.id = 'results-table-body';

                data.history.forEach(item => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${item.command_id}</td>
                        <td>${item.command}</td>
                        <td><pre><code>${item.response}</code></pre></td>
                    `;
                    tbody.appendChild(tr);
                });

                table.appendChild(tbody);
                resultsInfo.appendChild(table);
            } else {
                const table = document.createElement('table');
                table.classList.add('table');

                const thead = document.createElement('thead');
                thead.innerHTML = `
                    <tr>
                        <th>Command ID</th>
                        <th>Command</th>
                        <th>Response</th>
                    </tr>
                `;
                table.appendChild(thead);

                const tbody = document.createElement('tbody');
                tbody.id = 'results-table-body';

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td colspan="3">No history available.</td>
                `;
                tbody.appendChild(tr);

                table.appendChild(tbody);
                resultsInfo.appendChild(table);
            }

            // Show the results-info div
            resultsInfo.classList.remove('d-none');
            // Optionally hide other info-content divs
            document.getElementById('task-info').classList.add('d-none');
            document.getElementById('directory-info').classList.add('d-none');
        })
        .catch(error => {
            console.error('Error fetching history:', error);
        });
});
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
    let row = document.getElementById(`beacon-${window.uuid}`);
    if (!row) {
        row = document.createElement('tr');
        row.id = `beacon-${window.uuid}`; // Updated to use window.uuid
        row.innerHTML = `
            <td>${window.uuid}</td>
            <td>${beacon.address}</td>
            <td>${beacon.hostname}</td>
            <td>${beacon.operating_system}</td>
            <td><span class="last-beacon">${formatDateWithoutMilliseconds(lastBeaconDate)}</span></td>
            <td><span class="next-beacon" id="next-beacon-${window.uuid}">${formatDateWithoutMilliseconds(nextBeaconDate)}</span></td>
            <td><span class="countdown" id="countdown-${window.uuid}"></span></td>
        `;
        beaconTableBody.appendChild(row);
    } else {
        // Update existing row
        row.querySelector('.last-beacon').textContent = formatDateWithoutMilliseconds(lastBeaconDate);
        row.querySelector('.next-beacon').textContent = formatDateWithoutMilliseconds(nextBeaconDate);
        row.classList.add('highlight');
        setTimeout(() => row.classList.remove('highlight'), 2000);
    }

    beaconTimers[window.uuid] = { // Updated to use window.uuid
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
    const socket = io('http://127.0.0.1:8000');

    // Join a room specific to this UUID
    socket.emit('join', window.uuid);

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
        if (data.beacons && data.beacons[window.uuid]) {
            const singleBeaconData = {
                beacon: data.beacons[window.uuid]
            };
            updateLastBeacon(singleBeaconData);
            updateNextBeacon(window.uuid);
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

    // Listen for command_response to update Results tab
    socket.on('command_response', (data) => {
        console.log('Received command_response:', data); // Added for debugging

        // Ensure the UUID matches the current beacon's UUID
        if (data.uuid === window.uuid) {
            const resultsInfo = document.getElementById('results-info');
            const resultsTableBody = document.getElementById('results-table-body');

            if (resultsTableBody) {
                // **Prevent Duplicate Entries by Ensuring Consistent 'command_id'**
                const existingRow = resultsTableBody.querySelector(`tr[data-command-id="${data.command_id}"]`);
                if (existingRow) {
                    // Update the Response cell
                    existingRow.querySelector('td:nth-child(3)').innerHTML = `<pre><code>${data.response}</code></pre>`;
                } else {
                    // Remove "No history available." row if present and add new task
                    const noHistoryRow = resultsTableBody.querySelector('tr td[colspan="3"]');
                    if (noHistoryRow) {
                        noHistoryRow.parentElement.remove();
                    }

                    const tr = document.createElement('tr');
                    tr.setAttribute('data-command-id', data.command_id); 
                    tr.innerHTML = `
                        <td>${data.command_id}</td>
                        <td>${data.command}</td>
                        <td><pre><code>${data.response}</code></pre></td>
                    `;
                    resultsTableBody.appendChild(tr);
                }

                // Show the command-response-banner div
                const banner = document.getElementById('command-response-banner');
                banner.textContent = 'New command response received.';
                banner.classList.remove('d-none');

                // Hide the banner after 3 seconds
                setTimeout(() => {
                    banner.classList.add('d-none');
                }, 3000);
            } else {
                console.error('results-table-body element not found');
            }
        } else {
            console.warn(`UUID mismatch: received ${data.uuid}, expected ${window.uuid}`);
        }
    });

    // Set intervals for updating countdowns
    setInterval(() => updateNextBeacon(window.uuid), 1000);

    fetch(`/api/v1/beacons/${window.uuid}`)
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
                updateNextBeacon(window.uuid);
                toggleLoadingSpinner(false);
            }
        })
        .catch(error => {
            console.error('Error fetching beacon:', error);
            toggleLoadingSpinner(true);
        });

    // Add event listeners for buttons
    document.getElementById('task-btn').addEventListener('click', (event) => {
        showInfo('task-info', event);
    });
    document.getElementById('results-btn').addEventListener('click', (event) => {
        showInfo('results-info', event);
    });
    document.getElementById('directory-btn').addEventListener('click', (event) => {
        showInfo('directory-info', event);
    });
    document.getElementById('media-btn').addEventListener('click', (event) => {
        showInfo('media-info', event);
    });

    function showInfo(infoId, event) { // Updated function signature
        const infoBox = document.getElementById('info-box');
        const currentInfo = document.querySelector('.info-content:not(.d-none)');
        const newInfo = document.getElementById(infoId);
        const clickedButton = event.target; // Get the clicked button
        const direction = clickedButton.getAttribute('data-direction'); // Get the slide direction

        if (currentInfo !== newInfo) {
            // Determine animation classes based on direction
            let slideOutClass, slideInClass;
            if (direction === 'left') {
                slideOutClass = 'slide-out-right';
                slideInClass = 'slide-in-left';
            } else {
                slideOutClass = 'slide-out-left';
                slideInClass = 'slide-in-right';
            }

            // Add slide out animation to current info
            currentInfo.classList.add(slideOutClass);
            currentInfo.classList.remove('slide-in-left', 'slide-in-right');

            // After animation ends, hide current and show new with slide in animation
            currentInfo.addEventListener('animationend', () => {
                currentInfo.classList.add('d-none');
                currentInfo.classList.remove(slideOutClass);

                newInfo.classList.remove('d-none');
                newInfo.classList.add(slideInClass);
            }, { once: true });
        }
    }

    handleTaskSelection();
    submitTask();
});

// Define a mapping between task options and their descriptions
const taskDescriptions = {
    'systeminfo': 'Retrieve system information including OS, uptime, and hardware details.', // Updated key from 'sysinfo' to 'systeminfo'
    'list_dir': 'List the contents of the specified directory.',
    'shell': 'Execute a shell command on the target system.',
    'close': 'Close the connection with the beacon.',
    'processes': 'List all running processes on the target system.',
    'diskusage': 'Check disk usage on the target system.',
    'netstat': 'Display network statistics and connections.',
    'session': 'Switch the beacon to session mode.',
    'directorytraversal': 'Perform directory traversal operations on the target system.',
    'takephoto': 'Capture a photo using the target system’s camera.'
};

// Function to handle dropdown selection
function handleTaskSelection() {
    const taskSelect = document.getElementById('task-select');
    const taskDescription = document.getElementById('task-description');
    const descriptionText = document.getElementById('description-text');
    const taskInput = document.getElementById('task-input');
    const submitBtn = document.getElementById('submit-task-btn');

    taskSelect.addEventListener('change', () => {
        const selectedValue = taskSelect.value;
        if (selectedValue && taskDescriptions[selectedValue]) {
            descriptionText.textContent = taskDescriptions[selectedValue];
            taskDescription.classList.remove('d-none');
            
            // Show input textbox only if the task requires input
            if (selectedValue === 'list_dir' || selectedValue === 'shell') { 
                taskInput.classList.remove('d-none', 'hide');
                taskInput.classList.add('show');
            } else { 
                taskInput.classList.remove('show');
                taskInput.classList.add('hide');
                document.getElementById('task-textbox').value = '';
            }
        } else {
            taskDescription.classList.add('d-none');
            taskInput.classList.remove('show');
            taskInput.classList.add('hide');
            descriptionText.textContent = '';
            document.getElementById('task-textbox').value = '';
        }
        validateForm();
    });

    // Add input event listener to the textbox
    const taskTextbox = document.getElementById('task-textbox');
    taskTextbox.addEventListener('input', validateForm);
}

// Function to validate form and enable/disable submit button
function validateForm() {
    const taskSelect = document.getElementById('task-select').value;
    const taskInput = document.getElementById('task-textbox').value.trim();
    const submitBtn = document.getElementById('submit-task-btn');
    const taskInputContainer = document.getElementById('task-input');

    if (taskSelect) {
        if (taskInputContainer.classList.contains('show')) {
            // If input is required, enable submit only if input is provided
            submitBtn.disabled = taskInput === '';
        } else {
            // If input is not required, enable submit as long as a task is selected
            submitBtn.disabled = false;
        }
    } else {
        submitBtn.disabled = true;
    }
}

// Function to generate UUID
function generateUUID() {
    // Simple UUID generator
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Function to submit task
function submitTask() {
    const submitBtn = document.getElementById('submit-task-btn');
    submitBtn.addEventListener('click', () => {
        const taskSelect = document.getElementById('task-select').value;
        const taskInput = document.getElementById('task-textbox').value.trim();

        // Define tasks that require input
        const tasksRequiringInput = ['list_dir', 'shell']; 
        const requiresInput = tasksRequiringInput.includes(taskSelect);

        if (!taskSelect || (requiresInput && !taskInput)) {
            alert('Please select a task and enter the input.');
            return;
        }

        const command_id = generateUUID(); // Renamed from 'command_uuid' to 'command_id'
        const payload = {
            command_id: command_id, // Use 'command_id' consistently
            task: taskSelect,
            data: taskInput || null
        };

        fetch(`/api/v1/beacons?command=${window.uuid}`, { // Uses global 'uuid' for beacon UUID
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            // Show confirmation alert
            const confirmationAlert = document.getElementById('confirmation-alert');
            confirmationAlert.classList.remove('d-none');
            // Automatically hide the alert after 5 seconds
            setTimeout(() => {
                confirmationAlert.classList.add('d-none');
            }, 5000);

            // **Remove "No history available." row if present**
            const resultsTableBody = document.getElementById('results-table-body');
            const noHistoryRow = resultsTableBody.querySelector('tr td[colspan="3"]');
            if (noHistoryRow) {
                noHistoryRow.parentElement.remove();
            }

            // **Add new task to Results tab**
            const tr = document.createElement('tr');
            tr.setAttribute('data-command-id', command_id);
            tr.innerHTML = `
                <td>${command_id}</td>
                <td>${taskSelect}</td>
                <td>Awaiting Response</td>
            `;
            resultsTableBody.appendChild(tr);

            // Reset the form
            submitBtn.disabled = true; // Reset the button state
            document.getElementById('task-select').value = '';
            document.getElementById('task-input').value = '';
            document.getElementById('task-input').classList.add('hide');
            document.getElementById('task-input').classList.remove('show');
            document.getElementById('task-description').classList.add('d-none');
        })
        .catch(error => {
            console.error('Error submitting task:', error);
            alert('Failed to submit task.');
        });
    });
}

// Expose necessary functions and variables to the global scope
window.beaconTimers = beaconTimers;
window.formatDateWithoutMilliseconds = formatDateWithoutMilliseconds;
window.updateNextBeacon = updateNextBeacon;
window.toggleLoadingSpinner = toggleLoadingSpinner;
