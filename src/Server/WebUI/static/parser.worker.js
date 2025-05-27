// This worker's only job is to parse JSON without blocking the main thread.
self.onmessage = function(event) {
    try {
        const jsonObject = JSON.parse(event.data);
        // Send the parsed object back to the main thread
        self.postMessage({ success: true, data: jsonObject });
    } catch (e) {
        // If parsing fails, send an error back
        self.postMessage({ success: false, error: e.message });
    }
};