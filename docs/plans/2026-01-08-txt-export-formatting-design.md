# Text Export Formatting Design

## Overview

Improve the `.txt` export format by combining timestamped fragments into readable prose with proper sentence and paragraph structure.

## Problem

Whisper outputs text in chunks based on audio timing, resulting in sentence fragments (one per line) that are hard to read as continuous text.

## Solution

Modify `StorageManager.export_to_txt()` to:

1. **Combine fragments into sentences** - Join fragments with spaces until reaching sentence-ending punctuation (`.` `?` `!`)
2. **Create paragraphs based on audio gaps** - Insert a blank line when there's a 2+ second gap between segments

## Example

**Current output:**
```
So today we're going to talk about
machine learning and specifically
how it applies to audio.
There's been a lot of progress lately.
Let me start with the basics.
```

**New output:**
```
So today we're going to talk about machine learning and specifically how it applies to audio. There's been a lot of progress lately.

Let me start with the basics.
```

## Implementation

Single file change: `frontend/frontend/services/storage.py`

```python
def export_to_txt(self, transcription_id: str) -> Optional[str]:
    data = self.load_transcription(transcription_id)
    if not data:
        return None

    segments = data.get('transcription', {}).get('segments', [])
    if not segments:
        return ''

    paragraphs = []
    current_sentence = []

    for i, segment in enumerate(segments):
        text = segment['text'].strip()
        current_sentence.append(text)

        # Check if sentence ends
        if text and text[-1] in '.?!':
            # Check for paragraph break (2+ second gap to next segment)
            if i + 1 < len(segments):
                gap = segments[i + 1]['start'] - segment['end']
                if gap >= 2.0:
                    # End paragraph
                    paragraphs.append(' '.join(current_sentence))
                    current_sentence = []

    # Don't forget remaining text
    if current_sentence:
        paragraphs.append(' '.join(current_sentence))

    return '\n\n'.join(paragraphs)
```

## Scope

- **Changed:** `.txt` export only
- **Unchanged:** `.srt` and `.json` exports (retain original segment structure)
- **No database changes** - formatting applied at export time
