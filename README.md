# Word Format Batch Editor

A web-based batch Word document format processor with structure-aware editing.

## Quick Start

### Windows
1. Extract the archive
2. Double-click `install.bat` to install dependencies
3. Double-click `WordFormatEditor.bat` to start

### Linux/Mac
1. Extract the archive
2. Run `chmod +x install.sh start.sh`
3. Run `./install.sh` to install dependencies
4. Run `./start.sh` to start

## GUI Features

- **Start/Stop Server** - One-click server management
- **System Tray** - Minimize to tray, run in background
- **Open Browser** - Quick access to web interface
- **Status Monitoring** - Real-time server status

## Usage

1. Upload .docx files via the web interface
2. Create format rules in the editor
3. Preview changes in real-time
4. Execute batch processing
5. Download processed files

## Requirements

- Python 3.11+
- Node.js 18+ (optional, for frontend build)

## API Documentation

After starting the server, visit:
- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/docs

## License

MIT
