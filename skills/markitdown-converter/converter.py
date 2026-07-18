#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

def can_convert(file_path):
    supported = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt',
                 '.html', '.htm', '.json', '.jsonl', '.xml', '.csv', '.tsv',
                 '.txt', '.md', '.rtf', '.odt', '.odp', '.ods']
    return Path(file_path).suffix.lower() in supported

def main():
    if len(sys.argv) < 2:
        print("Usage: converter.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    
    if not can_convert(file_path):
        print(f"Error: Unsupported format: {Path(file_path).suffix}", file=sys.stderr)
        sys.exit(1)
    
    try:
        result = subprocess.run(['markitdown', file_path], capture_output=True, text=True, check=True)
        print(result.stdout)
    except FileNotFoundError:
        print("Error: markitdown not installed. Run: pipx install markitdown", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
