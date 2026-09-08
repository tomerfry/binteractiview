# Web regression checks

From the repository root:

```sh
python -m pip install --target .test-deps construct==2.10.70
npm install --prefix .test-deps --no-save @babel/parser
node tests/test_web.js
python tests/test_web.py
```

The Node suite checks JavaScript/JSX syntax, exact integer and float encoding,
100,000-field highlight lookup, overlap priority, and exports the actual browser
templates for Python tests. The Python suite checks parsing, nested building,
type preservation, template isolation, full sample consumption, and lossless
rebuilds of the principal file samples.

After editing `web-runtime.py`, run `python tests/sync_web.py` to update the
embedded runtime in `index.html`. To regenerate `full-formats.js`, install
Pillow and run `python tests/full_samples.py`.

Serve the repository with `python -m http.server 8000` for browser testing.
Verify scrolling with a large file and a large array construct, expanding more
than 100 fields, jumping to fields, resizing, switching templates during a parse,
editing signed/big-endian/64-bit values, and building then saving a loaded sample.
The app loads Pyodide and Construct from the network and requires HTTP(S) for its worker.
