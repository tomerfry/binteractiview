/* Pure byte-editing and interval-index helpers; also exercised by Node tests. */
function encodeInteger(text, size, info = {}) {
    if (!/^[+-]?(?:0x[0-9a-f]+|[0-9]+)$/i.test(text)) throw new Error('Invalid integer');
    const negative = text.startsWith('-');
    let value = BigInt(text.replace(/^[+-]/, '')) * (negative ? -1n : 1n);
    const bits = BigInt(size * 8);
    const min = info.signed ? -(1n << (bits - 1n)) : 0n;
    const max = info.signed ? (1n << (bits - 1n)) - 1n : (1n << bits) - 1n;
    if (value < min || value > max) throw new Error(`Value exceeds ${size} byte(s)`);
    value = BigInt.asUintN(size * 8, value);
    const bytes = new Uint8Array(size);
    for (let i = 0; i < size; i++) {
        bytes[info.endian === 'little' ? i : size - i - 1] = Number(value & 255n);
        value >>= 8n;
    }
    return bytes;
}

function encodeScalar(text, size, info = {}) {
    if (info.type === 'boolean') {
        if (!/^(true|false|0|1)$/i.test(text)) throw new Error('Enter true or false');
        return Uint8Array.of(/^(true|1)$/i.test(text) ? 1 : 0);
    }
    if (info.type !== 'float') return encodeInteger(text, size, info);
    if (!text.trim() || !Number.isFinite(Number(text))) throw new Error('Enter a finite number');
    const bytes = new Uint8Array(size);
    const view = new DataView(bytes.buffer);
    if (size === 4) view.setFloat32(0, Number(text), info.endian === 'little');
    else if (size === 8) view.setFloat64(0, Number(text), info.endian === 'little');
    else throw new Error('Use hex mode for this float size');
    const result = size === 4 ? view.getFloat32(0, info.endian === 'little') : view.getFloat64(0, info.endian === 'little');
    if (!Number.isFinite(result)) throw new Error('Value exceeds the float range');
    return bytes;
}

function createHighlightLookup(ranges) {
    // Sweep boundaries once, retaining the original first-match priority.
    const events = [];
    ranges.forEach((range, index) => {
        if (range.length > 0) {
            events.push({ at: range.offset, index, start: true });
            events.push({ at: range.offset + range.length, index, start: false });
        }
    });
    events.sort((a, b) => a.at - b.at);
    const active = new Set(), heap = [], segments = [];
    const push = value => {
        let i = heap.length;
        heap.push(value);
        while (i > 0) {
            const parent = (i - 1) >> 1;
            if (heap[parent] <= value) break;
            heap[i] = heap[parent]; i = parent;
        }
        heap[i] = value;
    };
    const pop = () => {
        const last = heap.pop();
        if (!heap.length) return;
        let i = 0;
        while (i * 2 + 1 < heap.length) {
            let child = i * 2 + 1;
            if (child + 1 < heap.length && heap[child + 1] < heap[child]) child++;
            if (last <= heap[child]) break;
            heap[i] = heap[child]; i = child;
        }
        heap[i] = last;
    };
    for (let i = 0; i < events.length;) {
        const at = events[i].at;
        while (i < events.length && events[i].at === at) {
            const event = events[i++];
            if (event.start) { active.add(event.index); push(event.index); }
            else active.delete(event.index);
        }
        while (heap.length && !active.has(heap[0])) pop();
        segments.push({ at, range: heap.length ? ranges[heap[0]] : null });
    }
    return offset => {
        let lo = 0, hi = segments.length;
        while (lo < hi) {
            const mid = (lo + hi) >>> 1;
            if (segments[mid].at <= offset) lo = mid + 1;
            else hi = mid;
        }
        return lo ? segments[lo - 1].range : null;
    };
}
if (typeof module !== 'undefined') module.exports = { encodeInteger, encodeScalar, createHighlightLookup };
