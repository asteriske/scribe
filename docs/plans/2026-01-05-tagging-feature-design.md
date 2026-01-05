# Tagging Feature Design

**Date:** 2026-01-05
**Status:** Approved

## Overview

Add arbitrary tagging capability to transcriptions for workflow organization. Users can assign tags like "kindle" or "format" to categorize transcriptions for downstream processing, without implementing the actual workflows yet.

## Requirements

- Tags stored as lowercase strings for consistency
- Autocomplete from previously used tags
- Tag input at three locations: submit form, list view, detail page
- Visual tag chip interface with inline editing
- No workflow implementation, just the tagging infrastructure

## Design Decisions

**Approach:** Simple tag list with JSON storage
- Store tags as JSON array in database column
- Normalize all tags to lowercase on save
- Autocomplete suggests from existing tags across all transcriptions
- No separate tag table (keep it simple)

**Rationale:** Simplest implementation that meets requirements. Can migrate to normalized tag table later if needed.

## Database Schema

### Transcription Table Changes

Add new column:
```sql
ALTER TABLE transcriptions ADD COLUMN tags TEXT DEFAULT '[]';
```

**Column Details:**
- Name: `tags`
- Type: `TEXT` (stores JSON array)
- Default: `[]` (empty array)
- Format: `["kindle", "format", "review"]`

### Model Changes

Update `Transcription` SQLAlchemy model:

```python
class Transcription(Base):
    # ... existing fields ...
    tags: List[str] = Field(default_factory=list)  # JSON column
```

**Tag Normalization Rules:**
- Convert to lowercase
- Strip leading/trailing whitespace
- Remove duplicates
- Filter out empty strings
- Validate format: `^[a-z0-9-_]+$`

**Validation Limits:**
- Max tag length: 50 characters
- Max tags per transcription: 20
- Allowed characters: lowercase alphanumeric, hyphens, underscores

## API Endpoints

### New Endpoint: Get All Tags

```
GET /api/tags
```

**Response:**
```json
{
  "tags": ["kindle", "format", "review", "work", "personal"]
}
```

- Returns all unique tags used across transcriptions
- Sorted alphabetically
- Only includes tags currently in use

### Modified Endpoints

**POST /api/transcribe**

Add optional `tags` field:

```json
{
  "url": "https://youtube.com/watch?v=...",
  "tags": ["kindle", "format"]  // optional, default []
}
```

**Response:** Same as current, includes `tags` array

**New: PATCH /api/transcriptions/{id}**

Update tags for existing transcription:

```json
{
  "tags": ["kindle", "review"]  // replaces existing tags completely
}
```

**Response:**
```json
{
  "id": "abc123",
  "tags": ["kindle", "review"],
  // ... rest of transcription object
}
```

**GET /api/transcriptions**
**GET /api/transcriptions/{id}**

Include `tags` array in all transcription responses.

### Validation

All endpoints normalize and validate tags:
1. Convert to lowercase
2. Strip whitespace
3. Remove duplicates
4. Enforce character restrictions
5. Check length limits
6. Return 400 error for invalid tags

## Frontend UI

### Tag Input Component

**Reusable JavaScript component** (`tag-input.js`):

**Features:**
- Text input field with inline tag chips
- Autocomplete dropdown showing existing tags
- Press Enter, comma, or Tab to create chip
- Click X on chip to remove
- Keyboard navigation (arrow keys in dropdown)
- Debounced autocomplete (300ms)

**Visual Elements:**
- Tag chips: rounded badges with light background
- Remove button: X icon, red on hover
- Input field: inline with chips, expands as needed
- Autocomplete: dropdown below, max 10 suggestions
- Highlight matching characters in autocomplete

### Integration Points

#### 1. Submit Form (index.html)

**Location:** Between URL input and submit button

```html
<div class="form-group">
    <label for="tags">Tags (optional)</label>
    <div id="tagInput"></div>
</div>
```

**Behavior:**
- Tag input component initialized on page load
- Tags sent with POST /api/transcribe
- Empty tags array if none added

#### 2. Recent Transcriptions List (index.html)

**Display Mode:**
- Tags shown as read-only chips below metadata
- "Edit tags" button or click chips to enter edit mode

**Edit Mode:**
- Read-only chips replaced with tag input component
- Save and Cancel buttons appear
- Save: PATCH /api/transcriptions/{id}, reload item
- Cancel: revert to read-only display
- Smooth transition, no layout jump

**HTML Structure:**
```html
<div class="transcription-item">
    <!-- existing content -->
    <div class="transcription-tags">
        <div class="tags-display"><!-- chips --></div>
        <div class="tags-edit" style="display:none">
            <!-- tag input component -->
            <button class="btn-save">Save</button>
            <button class="btn-cancel">Cancel</button>
        </div>
    </div>
</div>
```

#### 3. Transcription Detail Page (transcription.html)

**Location:** Near title/metadata at top

**Display Mode:**
- Tags section with read-only chips
- "Edit" button

**Edit Mode:**
- Toggle to tag input component
- Save/Cancel buttons
- Save: PATCH /api/transcriptions/{id}
- Updates tags without page reload

## JavaScript Implementation

### File Structure

```
frontend/static/js/
├── app.js              # existing
├── index.js            # existing, modified
├── tag-input.js        # new - reusable component
└── transcription.js    # new - detail page functionality
```

### TagInput Class

**Constructor:**
```javascript
new TagInput(containerElement, initialTags, options)
```

**Methods:**
- `render()` - Build and display UI
- `addTag(tag)` - Add a tag chip
- `removeTag(tag)` - Remove a tag chip
- `getTags()` - Return current tags array
- `setTags(tags)` - Set tags programmatically
- `fetchAutocomplete()` - Load suggestions from API

**State:**
- Current tags array
- Available tags (cached from API)
- Input value
- Selected autocomplete index

**Events:**
- Input keydown: Enter/comma/Tab creates tag, arrows navigate
- Input focus: show autocomplete
- Input blur: hide autocomplete (debounced)
- Chip click: remove tag
- Autocomplete item click: add tag

### Autocomplete Logic

1. Fetch all tags from GET /api/tags on first focus
2. Cache for session (store in component)
3. Filter cached tags based on current input
4. Exclude tags already added
5. Case-insensitive substring matching
6. Show max 10 results
7. Debounce input (300ms) to avoid excessive filtering

### Integration Code

**index.js modifications:**

```javascript
// Submit form
const tagInput = new TagInput(
    document.getElementById('tagInput'),
    []
);

// On form submit
const tags = tagInput.getTags();
// Include in POST body

// Recent list - for each transcription
const listTags = new TagInput(
    editContainer,
    transcription.tags
);

// Save button
const newTags = listTags.getTags();
await updateTranscriptionTags(id, newTags);
```

**transcription.js (new file):**

Handle tag editing on detail page, similar to list view logic.

### Error Handling

- API fetch failures: show "Failed to load tags" message
- PATCH failures: alert "Failed to update tags"
- Validation errors: show inline error message
- Network timeouts: graceful fallback
- Malformed responses: console error, user-friendly message

## CSS Styling

### Tag Chip Styles

```css
.tag-chip {
    display: inline-block;
    padding: 4px 8px;
    margin: 2px;
    background: #e0e0e0;
    border-radius: 12px;
    font-size: 0.85em;
    color: #333;
}

.tag-chip-remove {
    margin-left: 6px;
    cursor: pointer;
    color: #666;
    font-weight: bold;
}

.tag-chip-remove:hover {
    color: #d32f2f;
}
```

### Tag Input Container

```css
.tag-input-container {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 4px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    min-height: 38px;
    background: white;
}

.tag-input-container:focus-within {
    border-color: #4CAF50;
    box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.1);
}

.tag-input-field {
    border: none;
    outline: none;
    flex-grow: 1;
    min-width: 120px;
    padding: 4px;
    font-size: 0.9em;
}
```

### Autocomplete Dropdown

```css
.tag-autocomplete {
    position: absolute;
    background: white;
    border: 1px solid #ccc;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    max-height: 200px;
    overflow-y: auto;
    z-index: 1000;
    min-width: 200px;
}

.tag-autocomplete-item {
    padding: 8px 12px;
    cursor: pointer;
    font-size: 0.9em;
}

.tag-autocomplete-item:hover,
.tag-autocomplete-item.selected {
    background: #f5f5f5;
}

.tag-autocomplete-item mark {
    background: #ffeb3b;
    font-weight: bold;
}
```

### Edit Mode Buttons

```css
.tags-edit {
    margin-top: 8px;
}

.tags-edit .btn-save,
.tags-edit .btn-cancel {
    padding: 6px 12px;
    margin-right: 8px;
    font-size: 0.85em;
    border-radius: 4px;
    cursor: pointer;
}

.tags-edit .btn-save {
    background: #4CAF50;
    color: white;
    border: none;
}

.tags-edit .btn-cancel {
    background: #f5f5f5;
    color: #333;
    border: 1px solid #ccc;
}
```

## Implementation Order

1. **Backend first:**
   - Database migration (add tags column)
   - Update Transcription model
   - Add GET /api/tags endpoint
   - Add PATCH /api/transcriptions/{id} endpoint
   - Update POST /api/transcribe to accept tags
   - Include tags in GET responses

2. **Frontend component:**
   - Create tag-input.js component
   - Build autocomplete logic
   - Add CSS styles

3. **Integration:**
   - Submit form integration
   - Recent list integration
   - Detail page integration

4. **Testing:**
   - Backend unit tests
   - Frontend manual testing
   - Edge cases (special characters, limits, etc.)

## Future Enhancements

Not included in this design, but possible later:
- Filter transcriptions by tag
- Tag usage statistics
- Bulk tag operations
- Tag renaming/merging
- Tag colors/icons
- Migrate to normalized tag table
