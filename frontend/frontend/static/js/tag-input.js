/**
 * TagInput - Reusable tag input component with autocomplete
 */
class TagInput {
    constructor(containerElement, initialTags = [], options = {}) {
        this.container = containerElement;
        this.tags = [...initialTags];
        this.availableTags = [];
        this.selectedIndex = -1;
        this.debounceTimer = null;

        this.options = {
            placeholder: options.placeholder || 'Add tags...',
            debounceMs: options.debounceMs || 300,
            maxSuggestions: options.maxSuggestions || 10
        };

        this.render();
        this.fetchAvailableTags();
    }

    /**
     * Render the component
     */
    render() {
        this.container.innerHTML = '';

        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'tag-input-container';

        // Render existing tags
        this.tags.forEach(tag => {
            const chip = this.createTagChip(tag);
            wrapper.appendChild(chip);
        });

        // Create input field
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'tag-input-field';
        input.placeholder = this.options.placeholder;

        // Event listeners
        input.addEventListener('keydown', (e) => this.handleKeyDown(e));
        input.addEventListener('input', (e) => this.handleInput(e));
        input.addEventListener('focus', () => this.showAutocomplete());
        input.addEventListener('blur', () => {
            // Delay to allow clicking autocomplete items
            setTimeout(() => this.hideAutocomplete(), 200);
        });

        wrapper.appendChild(input);

        // Create autocomplete dropdown
        const autocomplete = document.createElement('div');
        autocomplete.className = 'tag-autocomplete';
        autocomplete.style.display = 'none';
        wrapper.appendChild(autocomplete);

        this.container.appendChild(wrapper);

        // Store references
        this.inputElement = input;
        this.autocompleteElement = autocomplete;
        this.wrapperElement = wrapper;
    }

    /**
     * Create a tag chip element
     */
    createTagChip(tag) {
        const chip = document.createElement('span');
        chip.className = 'tag-chip';
        chip.textContent = tag;

        const remove = document.createElement('span');
        remove.className = 'tag-chip-remove';
        remove.textContent = '\u00d7';
        remove.onclick = () => this.removeTag(tag);

        chip.appendChild(remove);
        return chip;
    }

    /**
     * Handle keyboard input
     */
    handleKeyDown(e) {
        const input = e.target;

        // Enter, comma, or Tab - add tag
        if (e.key === 'Enter' || e.key === ',' || e.key === 'Tab') {
            e.preventDefault();

            // If autocomplete is visible and item selected, use that
            if (this.selectedIndex >= 0) {
                const items = this.autocompleteElement.querySelectorAll('.tag-autocomplete-item');
                if (items[this.selectedIndex]) {
                    const tag = items[this.selectedIndex].dataset.tag;
                    this.addTag(tag);
                    return;
                }
            }

            // Otherwise add from input
            const value = input.value.trim();
            if (value) {
                this.addTag(value);
            }
        }

        // Backspace on empty input - remove last tag
        else if (e.key === 'Backspace' && !input.value) {
            if (this.tags.length > 0) {
                this.removeTag(this.tags[this.tags.length - 1]);
            }
        }

        // Arrow keys - navigate autocomplete
        else if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.navigateAutocomplete(1);
        }
        else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.navigateAutocomplete(-1);
        }

        // Escape - hide autocomplete
        else if (e.key === 'Escape') {
            this.hideAutocomplete();
        }
    }

    /**
     * Handle input changes
     */
    handleInput(e) {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.updateAutocomplete(e.target.value);
        }, this.options.debounceMs);
    }

    /**
     * Add a tag
     */
    addTag(tag) {
        const normalized = tag.toLowerCase().trim();

        // Validate
        if (!normalized) return;
        if (this.tags.includes(normalized)) return;
        if (!/^[a-z0-9-_]+$/.test(normalized)) {
            console.warn(`Invalid tag format: ${tag}`);
            return;
        }

        this.tags.push(normalized);
        this.render();
        this.inputElement.value = '';
        this.hideAutocomplete();
        this.inputElement.focus();
    }

    /**
     * Remove a tag
     */
    removeTag(tag) {
        const index = this.tags.indexOf(tag);
        if (index > -1) {
            this.tags.splice(index, 1);
            this.render();
            this.inputElement.focus();
        }
    }

    /**
     * Get current tags
     */
    getTags() {
        return [...this.tags];
    }

    /**
     * Set tags programmatically
     */
    setTags(tags) {
        this.tags = [...tags];
        this.render();
    }

    /**
     * Fetch available tags from API
     */
    async fetchAvailableTags() {
        try {
            const response = await fetch('/api/tags');
            if (response.ok) {
                const data = await response.json();
                this.availableTags = data.tags || [];
            }
        } catch (error) {
            console.error('Failed to fetch tags:', error);
        }
    }

    /**
     * Show autocomplete dropdown
     */
    showAutocomplete() {
        this.updateAutocomplete(this.inputElement.value);
    }

    /**
     * Hide autocomplete dropdown
     */
    hideAutocomplete() {
        this.autocompleteElement.style.display = 'none';
        this.selectedIndex = -1;
    }

    /**
     * Update autocomplete suggestions
     */
    updateAutocomplete(query) {
        const trimmed = query.trim().toLowerCase();

        // Filter tags
        let suggestions = this.availableTags.filter(tag => {
            // Exclude already added tags
            if (this.tags.includes(tag)) return false;

            // Match query
            if (!trimmed) return true;
            return tag.includes(trimmed);
        });

        // Limit suggestions
        suggestions = suggestions.slice(0, this.options.maxSuggestions);

        // Render suggestions
        if (suggestions.length === 0) {
            this.hideAutocomplete();
            return;
        }

        this.autocompleteElement.innerHTML = '';
        suggestions.forEach((tag, index) => {
            const item = document.createElement('div');
            item.className = 'tag-autocomplete-item';
            item.dataset.tag = tag;

            // Highlight matching part
            if (trimmed) {
                const regex = new RegExp(`(${trimmed})`, 'gi');
                item.innerHTML = tag.replace(regex, '<mark>$1</mark>');
            } else {
                item.textContent = tag;
            }

            item.onclick = () => {
                this.addTag(tag);
            };

            this.autocompleteElement.appendChild(item);
        });

        this.autocompleteElement.style.display = 'block';
        this.selectedIndex = -1;
    }

    /**
     * Navigate autocomplete with arrow keys
     */
    navigateAutocomplete(direction) {
        const items = this.autocompleteElement.querySelectorAll('.tag-autocomplete-item');
        if (items.length === 0) return;

        // Update selected index
        this.selectedIndex += direction;

        // Wrap around
        if (this.selectedIndex < 0) this.selectedIndex = items.length - 1;
        if (this.selectedIndex >= items.length) this.selectedIndex = 0;

        // Update visual selection
        items.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }
}
