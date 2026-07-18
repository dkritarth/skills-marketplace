---
name: markitdown-converter
version: 1.0.0
description: Convert documents (PDF, Word, Excel, PowerPoint, HTML, etc.) to markdown using Microsoft's markitdown library, then read the markdown output instead of binary files
license: MIT
compatibility: claude-code codex morphmind opencode
allowed-tools: [Read, Write, Edit, Bash]
auto-invoke: ["\.pdf$", "\.docx?$", "\.xlsx?$", "\.pptx?$", "\.html?$"]
---

# Markitdown Converter Skill

Automatically convert documents to markdown before reading them. Supports PDFs, Word docs, Excel spreadsheets, PowerPoint presentations, HTML, and more.

## Setup

Install markitdown (one-time):
```bash
pipx install markitdown
```

## Usage

Convert a file:
```bash
python ~/.claude/skills/markitdown-converter/converter.py <file-path>
```

Or use the markitdown CLI directly:
```bash
markitdown file.pdf > file.md
```

## Supported formats

PDF, Word, Excel, PowerPoint, HTML, JSON, CSV, and more. See converter.py for full list.
