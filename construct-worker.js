/* Keep Python parsing/building off the rendering thread. */
let runtime;
let queue = Promise.resolve();
self.onmessage = ({ data: request }) => {
    queue = queue.then(async () => {
        try {
            if (request.action === 'init') {
                importScripts('https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js');
                runtime = await loadPyodide({ indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/' });
                await runtime.loadPackage('micropip');
                const micropip = runtime.pyimport('micropip');
                try { await micropip.install('construct==2.10.70'); } finally { micropip.destroy(); }
                try { await runtime.loadPackage('cryptography'); } catch (_) { /* Optional examples. */ }
                await runtime.runPythonAsync(request.bootstrap);
                self.postMessage({ id: request.id, result: true });
                return;
            }
            runtime.globals.set('source_code', request.code);
            runtime.globals.set('input_value', request.input);
            try {
                const result = await runtime.runPythonAsync('load_structure(source_code)\n' + request.action);
                self.postMessage({ id: request.id, result: JSON.parse(result) });
            } finally {
                runtime.globals.delete('source_code');
                runtime.globals.delete('input_value');
            }
        } catch (error) {
            self.postMessage({ id: request.id, error: error.message });
        }
    });
};
