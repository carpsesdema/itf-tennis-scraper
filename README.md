#  Tennis Scraper - Pro Edition

A comprehensive, professional-grade application for scraping and monitoring ITF tennis matches from multiple sources with a modern GUI interface and bet365 betting indicator detection.

## 🎾 Key Features

### Core Functionality
- **Flashscore Integration**: Real-time scraping with bet365 betting indicator detection
- **Tie Break Alerts**: Automatic detection and highlighting of match tie breaks
- **Live Match Monitoring**: Continuous monitoring with configurable refresh intervals
- **Advanced Filtering**: Filter by players, tournaments, status, rankings, and more
- **Export Capabilities**: CSV, JSON, and Excel export with customizable formats
- **Automatic Updates**: Built-in update system with GitHub integration

### Professional GUI
- **Modern Interface**: Clean, responsive design with dark/light theme support
- **Live Match Highlighting**: Visual indicators for ongoing matches and tie breaks
- **Advanced Table Features**: Sorting, filtering, context menus
- **Settings Management**: Comprehensive configuration options
- **Progress Tracking**: Real-time scraping progress and statistics
- **Log Viewer**: Built-in log monitoring and management

### Technical Excellence
- **Modular Architecture**: Clean separation of concerns with plugin system
- **Async Processing**: High-performance asynchronous scraping
- **Error Handling**: Robust error recovery and logging
- **Type Safety**: Full type hints throughout the codebase
- **Browser Automation**: Playwright-based scraping with stealth features

## 🚀 Quick Start

### For End Users (Executable)

1. **Download the latest release**:
   - Go to [Releases](https://github.com/carpsesdema/itf-tennis-scraper/releases)
   - Download `ITFTennisScraperPro_vX.X.X.exe`

2. **Run the application**:
   - Double-click the downloaded `.exe` file
   - No installation required!

3. **Start monitoring**:
   - Click "▶ Start Scraping" to begin continuous monitoring
   - Matches with bet365 indicators will be highlighted
   - Tie break matches will be specially marked with 🚨

### For Developers

1. **Clone the repository**:
   ```bash
   git clone https://github.com/carpsesdema/itf-tennis-scraper.git
   cd itf-tennis-scraper
   ```

2. **Set up development environment**:
   ```bash
   python scripts/setup_dev.py
   ```

3. **Activate virtual environment**:
   ```bash
   # Windows
   tennis_scraper_env\Scripts\activate
   
   # Linux/Mac
   source tennis_scraper_env/bin/activate
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

## 📦 Building and Deployment

### Quick Build
```bash
python build_and_deploy.py --version 1.0.1 --changelog "Bug fixes and improvements"
```

### Manual Upload (if GitHub token not set)
```bash
python build_and_deploy.py --version 1.0.1 --changelog "New features" --no-github
python upload_helper.py 1.0.1 "New features added"
```

## ⚙️ Configuration

### Bet365 Detection
The application detects matches with bet365 betting indicators by looking for specific bookmaker IDs on Flashscore. Configure in Settings > Sources:

- **Bet365 Indicator Fragment**: `/549/` (default)
- **Match Tie Break Keywords**: Customizable list of keywords to detect tie breaks

### Refresh Settings
- **Auto-refresh Interval**: 30-3600 seconds (default: 300s)
- **Continuous Monitoring**: Keeps running until manually stopped
- **Single Refresh**: Manual refresh button for one-time updates

### Data Sources
Currently supports:
- **Flashscore**: Primary source with bet365 indicator detection
- Future sources can be added via the plugin system

## 🎯 Tie Break Detection

The application automatically detects match tie breaks using configurable keywords:
- "match tie break"
- "match tie-break" 
- "super tiebreak"
- "first to 10"
- And more...

When tie breaks are detected:
- 🚨 Critical alerts in logs
- Special highlighting in the matches table
- Status bar notifications
- Enhanced export metadata

## 💾 Export Options

### Supported Formats
- **CSV**: Standard comma-separated values
- **JSON**: Structured data with metadata
- **Excel**: Formatted spreadsheets with auto-sizing

### Export Features
- Include/exclude metadata
- Custom timestamp formats
- Configurable field selection
- Progress tracking for large exports

## 🔧 Development

### Code Structure
```
tennis_scraper/
├── core/           # Business logic and models
├── gui/            # PySide6 user interface
├── scrapers/       # Website scrapers
├── utils/          # Utilities and helpers
├── updates/        # Auto-update system
└── config.py       # Configuration management
```

### Running Tests
```bash
python scripts/run_tests.py --coverage
```

### Code Quality
```bash
python scripts/lint_code.py
```

### Building Executable
```bash
python build_and_deploy.py --version X.Y.Z --changelog "Description"
```

## 🔄 Update System

The application includes an automatic update system:

1. **Automatic Checks**: Checks for updates on startup (configurable)
2. **GitHub Integration**: Downloads updates from GitHub releases
3. **One-Click Install**: Automatic installer launch
4. **Version Skipping**: Option to skip specific versions

### Update Process
1. Application checks GitHub releases API
2. Compares current version with latest release
3. Downloads update if available
4. Launches installer and closes application
5. User runs installer to update

## 🛠️ Advanced Configuration

### Browser Settings
- **Headless Mode**: Hide browser windows during scraping
- **User Agent**: Customize browser identification
- **Request Timeouts**: Configure network timeouts
- **Retry Logic**: Set maximum retry attempts

### Performance Tuning
- **Concurrent Scrapers**: Adjust parallel processing
- **Cache Settings**: Configure match caching
- **Memory Management**: Optimize for large datasets
- **Resource Blocking**: Block unnecessary web resources

## 📋 System Requirements

### Minimum Requirements
- **OS**: Windows 10, macOS 10.14, or Linux (Ubuntu 18.04+)
- **Memory**: 4GB RAM
- **Storage**: 100MB free space
- **Network**: Internet connection for scraping

### Recommended
- **OS**: Windows 11, macOS 12+, or recent Linux
- **Memory**: 8GB+ RAM
- **Storage**: 500MB+ free space
- **Network**: Stable broadband connection

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Run tests
pytest
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Legal Notice

This software is designed for educational and personal use. Users are responsible for ensuring compliance with:

1. Website Terms of Service
2. Data scraping best practices  
3. Local laws and regulations
4. Respectful use of web resources

The developers are not responsible for misuse of this software or any legal consequences arising from its use.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/carpsesdema/itf-tennis-scraper/issues)
- **Documentation**: Check the `/docs` folder (coming soon)
- **Email**: [Contact Developer](mailto:your.email@example.com)

## 📊 Status

- **Version**: 1.0.0
- **Status**: Active Development
- **Python**: 3.8+
- **GUI**: PySide6/Qt6
- **Last Updated**: May 2025

---

**Made with ❤️ for tennis enthusiasts and sports betting professionals**