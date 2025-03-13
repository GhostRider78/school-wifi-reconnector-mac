# College WiFi Reconnector

A macOS application that automatically reconnects to your college WiFi network and handles web authentication. Perfect for schools with captive portals that require frequent logins.

## Why I Built This

Got tired of constantly having to re-login to my college WiFi every time my laptop went to sleep. This app sits in your menu bar, monitors your connection, and handles all the authentication for you. No more login prompts!

## Features
Automatically reconnects to your configured WiFi network
Handles web authentication (captive portal login) 
Lives in your macOS menu bar for easy access


## Requirements

- macOS 10.14 or later
- Python 3.7+
- Chrome browser (for web authentication)

## Installation

### Option 1: Download the app

1. Go to the [Releases](https://github.com/yourusername/school-wifi-reconnector/releases) page
2. Download the latest `.dmg` file
3. Open the `.dmg` and drag the app to your Applications folder

### Option 2: Install from source

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/college-wifi-reconnector.git
   cd college-wifi-reconnector
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python wifi_reconnector.py
   ```

## Usage

1. On first launch, enter your WiFi details:
   - WiFi network name
   - Login page URL (the captive portal that appears when you need to authenticate)
   - Your username and password

2. Click "Save Settings" and "Test Connection" to verify everything works

3. The app runs in your menu bar - click the WiFi icon to access options

4. Optional: Enable "Launch at login" to start automatically when you log in

## How It Works

This app uses a combination of:
 macOS networking commands to monitor and connect to WiFi
 Selenium with ChromeDriver to handle web authentication
A background thread to periodically check connection status
Tkinter for the configuration UI
Rumps for the macOS menu bar integration

## Troubleshooting

If you encounter issues:

1. Check the logs at `~/Library/Logs/wifi_reconnector.log`
2. Make sure your WiFi name exactly matches what's shown in your network preferences
3. Verify your login URL, username, and password are correct
4. Try the "Test Connection" button from the settings window

## Contributing

Found a bug or want to add a feature? Contributions are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by the frustration of having to repeatedly log in to college WiFi
- Thanks to the developers of Selenium, Rumps, and other libraries that made this possible
