# Binteractiview Enhanced - Architecture Overview

## Component Interaction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        BintvApp (Main App)                       │
│  - Manages binary data (original + modified)                    │
│  - Tracks unsaved changes                                       │
│  - Handles construct parsing                                    │
│  - Coordinates between widgets                                  │
└────────────┬────────────────────────────┬────────────────────────┘
             │                            │
             │                            │
             ▼                            ▼
┌────────────────────────┐    ┌──────────────────────────┐
│ ReactiveConstructTree  │    │       HexView            │
│  - Displays parsed     │    │  - Shows hex dump        │
│    structure           │◄───┤  - Cursor tracking       │
│  - Right-click menu    │    │  - Field highlighting    │
│  - Field editing UI    │    │  - Offset display        │
└────────┬───────────────┘    └──────────────────────────┘
         │
         │ Right-click on field
         ▼
┌────────────────────────┐
│    ContextMenu         │
│  ┌──────────────────┐  │
│  │ ✏️  Edit Value   │──┼──┐
│  ├──────────────────┤  │  │
│  │ 📋 Copy Value    │  │  │
│  ├──────────────────┤  │  │
│  │ 📍 Go to Offset  │──┼──┼──┐
│  └──────────────────┘  │  │  │
└────────────────────────┘  │  │
                            │  │
         Edit Value         │  │  Goto Offset
         selected           │  │  selected
                            │  │
                ┌───────────┘  └──────────┐
                ▼                         ▼
    ┌───────────────────────┐    ┌────────────────┐
    │  EditValueScreen      │    │ Jump hex view  │
    │  ┌─────────────────┐  │    │ cursor to      │
    │  │ Field: version  │  │    │ field offset   │
    │  │ Type: dword     │  │    └────────────────┘
    │  │ Current: 1      │  │
    │  │ New: [input]    │  │
    │  ├─────────────────┤  │
    │  │  [Save][Cancel] │  │
    │  └─────────────────┘  │
    └───────────┬───────────┘
                │ Save clicked
                ▼
    ┌───────────────────────────┐
    │ ValueEdited Message       │
    │  - field_path             │
    │  - old_value              │
    │  - new_value              │
    │  - value_type             │
    └───────────┬───────────────┘
                │
                ▼
    ┌───────────────────────────┐
    │ BintvApp Handler          │
    │  1. Find field offset     │
    │  2. Convert value to bytes│
    │  3. Update data buffer    │
    │  4. Mark unsaved changes  │
    │  5. Reparse construct     │
    │  6. Update hex view       │
    └───────────────────────────┘


## Exit Flow with Save Confirmation

User presses Ctrl+Q
         │
         ▼
┌─────────────────────────────┐
│ Check has_unsaved_changes?  │
└────────┬────────────────────┘
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    ▼         ▼
┌───────┐  ┌────────────────┐
│ Show  │  │ Show simple    │
│ Save  │  │ exit confirm   │
│ Dialog│  └────────────────┘
└───┬───┘
    │
    ▼
┌───────────────────────────────┐
│ ConfirmExitScreen             │
│ ┌───────────────────────────┐ │
│ │ ⚠️  Unsaved Changes       │ │
│ │                           │ │
│ │ [💾 Save & Exit]          │ │──┐
│ │ [🚫 Exit Without Saving]  │ │  │
│ │ [Cancel]                  │ │  │
│ └───────────────────────────┘ │  │
└───────────────────────────────┘  │
                                   │
         ┌─────────────────────────┼────────────┐
         │                         │            │
         ▼                         ▼            ▼
    Save & Exit          Exit Without Save   Cancel
         │                         │            │
         ▼                         │            │
┌──────────────────┐               │            │
│ save_modified_   │               │            │
│ file()           │               │            │
│  - Create path:  │               │            │
│    /tmp/xxx_mod  │               │            │
│  - Write data    │               │            │
│  - Log success   │               │            │
└────────┬─────────┘               │            │
         │                         │            │
         └─────────┬───────────────┘            │
                   ▼                            ▼
              Exit app                   Return to app


## Data Flow: Field Edit Operation

1. USER ACTION
   └─> Right-click on tree field
       └─> ContextMenu appears

2. MENU SELECTION
   └─> User selects "Edit Value"
       └─> EditValueScreen modal opens

3. VALUE INPUT
   └─> User enters new value
       └─> Input validation (type-specific)
           └─> Parse string to appropriate type

4. VALUE CONVERSION
   └─> _value_to_bytes(new_value, type, size)
       ├─> int → struct.pack (with size/endianness)
       ├─> bytes → direct use
       ├─> str → encode('utf-8') + padding
       └─> float → struct.pack (4 or 8 bytes)

5. DATA UPDATE
   └─> data[start:end] = new_bytes
       ├─> Update hex view display
       ├─> Mark has_unsaved_changes = True
       └─> Track in modified_fields dict

6. REPARSE
   └─> Re-run construct parser on modified data
       └─> Update tree view with new parsed values
           └─> Highlight changed fields (visual feedback)

7. SAVE ON EXIT
   └─> Write to /tmp/{filename}_modified{ext}
       └─> Log saved location


## Message Types

### Custom Messages Defined

1. **ReactiveConstructTree.FieldEditRequest**
   - Sent when: User selects "Edit Value" from context menu
   - Contains: field_path, field_name, value, value_type, offsets
   - Handler: on_reactive_construct_tree_field_edit_request()

2. **EditValueScreen.ValueEdited**  
   - Sent when: User clicks "Save" in edit dialog
   - Contains: field_path, old_value, new_value, value_type
   - Handler: on_edit_value_screen_value_edited()

3. **ReactiveConstructTree.GotoOffsetRequest**
   - Sent when: User selects "Go to Offset" from context menu
   - Contains: offset (int)
   - Handler: on_reactive_construct_tree_goto_offset_request()

4. **ContextMenu.MenuItemSelected**
   - Sent when: User selects any context menu item
   - Contains: action (str), field_data (dict)
   - Handler: Inline handler in on_tree_node_right_clicked()


## State Management

### App State Variables

```python
# Binary data
self.data: bytearray              # Current modified data
self.original_data: bytearray     # Original unchanged data

# Change tracking  
self.has_unsaved_changes: bool    # Flag for exit confirmation
self.modified_fields: dict        # {path: {old, new, offset}}

# Parsing state
self._parsed_data: Container      # Construct parsed structure
self._flattened_construct_data: list  # Flat list with offsets
self._construct: Struct           # Construct definition
```

### Tree Widget State

```python
# Tree data
self.parsed_data: Container       # Reactive, triggers tree rebuild

# UI state
self._expanded_paths: set         # Preserve expansion state on refresh
```


## Key Algorithms

### 1. Field Offset Lookup

```
_get_field_offsets(field_path) -> (start, end)
  1. Split path by '/'
  2. Navigate through parsed_data structure
  3. At each level:
     - For dict/Container: use key lookup
     - For list/ListContainer: parse index from '[N]'
  4. Check if final value has offset1/offset2 (RawCopy)
  5. Return (offset1, offset2) or (None, None)
```

### 2. Value to Bytes Conversion

```
_value_to_bytes(value, type, size, original) -> bytes
  1. Check value type
  2. Determine format:
     - For int: detect size (1,2,4,8) and signed/unsigned
     - For bytes: direct use
     - For str: encode UTF-8 + pad/truncate to size
     - For float: use 4 or 8 byte format
  3. Use struct.pack with format string
  4. Validate output size matches expected
  5. Return packed bytes
```

### 3. Tree Population with Context Data

```
populate_node(node, data, path)
  1. Recursively traverse data structure
  2. For each field:
     - Store path in node.data for right-click lookup
     - Store key/index for navigation
     - Store value for editing
  3. Leaf nodes get full context:
     - node.data = {path, key, value}
  4. Branch nodes track structure:
     - node.data = {path, key}
```


## File Structure

```
binteractiview/
├── bintv/
│   ├── app.py                          # ✨ Enhanced main application
│   ├── widgets/
│   │   ├── reactive_construct_tree.py  # ✨ Enhanced tree with context menu
│   │   ├── hex_view.py                 # Existing hex viewer
│   │   └── __init__.py
│   ├── svg_exporter.py                 # Existing SVG export
│   ├── neon_pallete.py                 # Existing color scheme
│   └── main.py                         # Entry point
└── README.md
```

## Dependencies

No new dependencies required! Uses only existing imports:
- `textual` - TUI framework
- `construct` - Binary parsing
- `struct` - Byte packing/unpacking
- `os` - File operations
- Standard library modules

---

This architecture maintains separation of concerns while adding powerful editing capabilities!
