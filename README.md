# Binteractiview Enhanced - Feature Addition

## New Features Added

✅ **Right-click context menu** on parsed value tree fields  
✅ **Edit field values** with type-aware validation  
✅ **Save-on-exit confirmation** with automatic save to `/tmp/`  
✅ **Go to offset** from tree fields  
✅ **Change tracking** for modified fields  

## Quick Installation

1. **Backup your files:**
   ```bash
   cd /path/to/binteractiview
   cp bintv/app.py bintv/app.py.backup
   cp bintv/widgets/reactive_construct_tree.py bintv/widgets/reactive_construct_tree.py.backup
   ```

2. **Replace with enhanced versions:**
   ```bash
   # Replace reactive_construct_tree.py
   cp reactive_construct_tree.py bintv/widgets/reactive_construct_tree.py
   
   # Replace app.py
   cp app.py bintv/app.py
   ```

3. **Done!** No additional dependencies needed.

## Usage

### Edit a Field Value:
1. Right-click on any field in the parsed values tree (right panel)
2. Select "✏️  Edit Value" from the context menu
3. Enter new value (supports decimal, hex, bytes, strings, floats, bools)
4. Click "Save"

### Input Formats:
- **Integers**: `255` or `0xFF`
- **Bytes**: `DEADBEEF` or `DE AD BE EF`
- **Strings**: Plain text
- **Floats**: `3.14159`
- **Booleans**: `true`/`false` or `1`/`0`

### Saving Changes:
When you exit (Ctrl+Q), if there are unsaved changes:
- **Save & Exit**: Saves to `/tmp/{filename}_modified{ext}`
- **Exit Without Saving**: Discards all changes
- **Cancel**: Returns to app

### Additional Features:
- **Go to Offset**: Right-click field → "📍 Go to Offset" (jumps hex view)
- **View Changes**: Check log panel (Ctrl+L) for modification history

## What Changed

### Files Modified:

1. **`bintv/widgets/reactive_construct_tree.py`**
   - Added `EditValueScreen` class (modal for editing)
   - Added `ContextMenu` class (right-click menu)
   - Added `FieldEditRequest` and `GotoOffsetRequest` messages
   - Added `on_tree_node_right_clicked()` handler

2. **`bintv/app.py`**
   - Added `ConfirmExitScreen` class (exit confirmation)
   - Added `has_unsaved_changes` flag
   - Added `modified_fields` tracking
   - Added `save_modified_file()` method
   - Added handlers for edit requests
   - Modified `action_quit()` to show confirmation

## Key Capabilities

✨ **Type-Aware Editing**: Automatically validates input based on field type  
✨ **Offset Tracking**: Finds exact byte location from RawCopy wrappers  
✨ **Real-time Updates**: Changes immediately reflected in hex view  
✨ **Safe Exit**: Always prompts before losing unsaved work  
✨ **Change Log**: All modifications logged with offsets  

## Example Log Messages

```
✅ Updated header.version: 1 → 2 at offset 0x0004
✅ Updated header.flags: 4660 → 22136 at offset 0x000C
💾 Saved modified file to: /tmp/firmware_modified.bin
```

## Limitations

- Only primitive values (ints, bytes, strings, floats, bools) can be edited
- Field size must remain the same (no growing/shrinking)
- Defaults to little-endian for multi-byte integers
- No undo/redo (use "Exit Without Saving" to discard)

## Documentation

- **IMPLEMENTATION_GUIDE.md** - Detailed usage and troubleshooting
- **ARCHITECTURE.md** - Technical details and component interaction

---

**Ready to use!** Open any binary file and start editing fields by right-clicking in the tree view.
