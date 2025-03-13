import sys
import time
import subprocess
import threading
import requests
import logging
import os
import json
import webbrowser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

# Bringing in the GUI stuff we need
import tkinter as tk
from tkinter import ttk, messagebox
import rumps  # Need this for the macOS menu bar icon

# Let's set up some decent logging - always helps when debugging later
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser("~/Library/Logs/wifi_reconnector.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Gotta store our settings somewhere the OS won't mess with
APP_SUPPORT_DIR = os.path.expanduser("~/Library/Application Support/WiFiReconnector")
if not os.path.exists(APP_SUPPORT_DIR):
    os.makedirs(APP_SUPPORT_DIR)
CONFIG_FILE = os.path.join(APP_SUPPORT_DIR, "wifi_config.json")

# Starting with some sensible defaults
DEFAULT_CONFIG = {
    "wifi_name": "",
    "login_url": "",
    "username": "",
    "password": "",
    "check_interval": 30,
    "auto_start": True
}

class WifiReconnector:
    def __init__(self):
        self.config = self.load_config()
        self.running = False
        self.thread = None
        self.root = None
        self.app = None
        
    def load_config(self):
        """Load configuration from file or create default"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            else:
                # First time running, let's create a fresh config
                return DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            # Something went wrong reading the file, better start fresh
            return DEFAULT_CONFIG.copy()
            
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            # Should probably tell the user their settings weren't saved...
    
    def is_connected(self):
        """Check if connected to the internet"""
        try:
            # Good old Google - if we can reach this, we're definitely online
            requests.get("https://www.google.com", timeout=5)
            return True
        except requests.ConnectionError:
            # No dice - either offline or behind a captive portal
            return False
    
    def is_connected_to_wifi(self):
        """Check if connected to the specified WiFi network (macOS specific)"""
        wifi_name = self.config["wifi_name"]
        if not wifi_name:
            return False
            
        try:
            # This is the macOS magic to get WiFi info - had to dig for this one!
            cmd = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I"
            output = subprocess.check_output(cmd, shell=True).decode('utf-8')
            
            # Now let's see if we're on the right network
            for line in output.split('\n'):
                if ' SSID: ' in line and wifi_name in line:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking WiFi connection: {e}")
            return False
    
    def connect_to_wifi(self):
        """Connect to the college WiFi network (macOS specific)"""
        wifi_name = self.config["wifi_name"]
        if not wifi_name:
            return False
            
        try:
            # Let macOS do the heavy lifting of connecting us
            cmd = f'networksetup -setairportnetwork en0 "{wifi_name}"'
            subprocess.run(cmd, shell=True)
            
            # Give it a moment to connect before we check
            time.sleep(5)
            return self.is_connected_to_wifi()
        except Exception as e:
            logger.error(f"Error connecting to WiFi: {e}")
            return False
    
    def authenticate(self):
        """Perform web authentication using college credentials"""
        login_url = self.config["login_url"]
        username = self.config["username"]
        password = self.config["password"]
        
        if not all([login_url, username, password]):
            logger.error("Authentication failed: Missing login credentials")
            # Can't do much without proper credentials
            return False
            
        try:
            # Setting up a headless browser - we don't need to see the login window
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # This is neat - webdriver_manager handles downloading the right Chrome driver
            # Let's try to use system Chrome first since it's probably there
            try:
                service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
                browser = webdriver.Chrome(service=service, options=options)
            except:
                # Fallback to regular Chrome if Chromium isn't available
                service = Service(ChromeDriverManager().install())
                browser = webdriver.Chrome(service=service, options=options)
            
            # Head to the login page
            browser.get(login_url)
            
            # Wait for the page to load - looking for anything that looks like a login form
            WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @type='email' or @id='username' or @name='username']"))
            )
            
            # Every site has a different layout, so we need to try various selectors
            # Let's find that username field
            username_field = None
            for selector in ["#username", "[name='username']", "[type='text']", "[type='email']"]:
                try:
                    username_field = browser.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
                    
            # Now for the password field
            password_field = None
            for selector in ["#password", "[name='password']", "[type='password']"]:
                try:
                    password_field = browser.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            # And finally the submit button
            submit_button = None
            for selector in ["[type='submit']", "button", "#loginButton", ".login-button"]:
                try:
                    submit_button = browser.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if username_field and password_field and submit_button:
                # Got all the elements, let's fill out the form
                username_field.send_keys(username)
                password_field.send_keys(password)
                submit_button.click()
                
                # Give it a moment to process the login
                time.sleep(5)
                browser.quit()
                
                logger.info("Authentication successful")
                return True
            else:
                logger.error("Could not find login form elements")
                browser.quit()
                # Couldn't figure out this login form - maybe it's not standard
                return False
                
        except TimeoutException:
            logger.error("Authentication page timed out")
            # The network might be too slow or the page doesn't load right
            return False
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    def monitor_connection(self):
        """Main function to monitor and fix WiFi connection"""
        logger.info("WiFi reconnection service started")
        
        while self.running:
            try:
                if not self.is_connected_to_wifi():
                    logger.info(f"Not connected to {self.config['wifi_name']}, attempting to connect...")
                    if self.connect_to_wifi():
                        logger.info("Successfully connected to WiFi")
                        # Now that we're connected, let's make sure we're authenticated
                        self.authenticate()
                elif not self.is_connected():
                    logger.info("Connected to WiFi but no internet access, attempting authentication...")
                    # We're on the right network but can't get to the internet - probably need to log in
                    self.authenticate()
                else:
                    logger.debug("Connection is stable")
                    # All good! We're online and authenticated
                    
                # Update the menu bar status so the user knows what's happening
                if self.app:
                    status = "Connected" if self.is_connected() else "Disconnected"
                    self.app.title = f"WiFi: {status}"
            except Exception as e:
                logger.error(f"Error in monitor thread: {e}")
                # Something unexpected happened, but we'll keep trying
                
            # Wait a bit before checking again - no need to hammer the system
            time.sleep(self.config["check_interval"])
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.monitor_connection, daemon=True)
            self.thread.start()
            logger.info("Monitoring started")
            if self.app:
                self.app.title = "WiFi: Monitoring..."
            return True
        return False
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=1.0)
            logger.info("Monitoring stopped")
            if self.app:
                self.app.title = "WiFi: Paused"
            return True
        return False

    def create_gui(self):
        """Create the configuration GUI"""
        self.root = tk.Tk()
        self.root.title("College WiFi Reconnector")
        self.root.geometry("450x400")
        self.root.resizable(False, False)
            
        # Make things look a bit nicer
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 10))
        style.configure('TLabel', font=('Arial', 10))
        style.configure('TEntry', font=('Arial', 10))
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # WiFi Settings
        ttk.Label(main_frame, text="WiFi Settings", font=('Arial', 12, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        ttk.Label(main_frame, text="WiFi Network Name:").grid(row=1, column=0, sticky=tk.W)
        wifi_name_var = tk.StringVar(value=self.config["wifi_name"])
        ttk.Entry(main_frame, textvariable=wifi_name_var, width=30).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Login Settings
        ttk.Label(main_frame, text="Login Settings", font=('Arial', 12, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=(10, 10))
        
        ttk.Label(main_frame, text="Login Page URL:").grid(row=3, column=0, sticky=tk.W)
        login_url_var = tk.StringVar(value=self.config["login_url"])
        ttk.Entry(main_frame, textvariable=login_url_var, width=30).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(main_frame, text="Username:").grid(row=4, column=0, sticky=tk.W)
        username_var = tk.StringVar(value=self.config["username"])
        ttk.Entry(main_frame, textvariable=username_var, width=30).grid(row=4, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(main_frame, text="Password:").grid(row=5, column=0, sticky=tk.W)
        password_var = tk.StringVar(value=self.config["password"])
        ttk.Entry(main_frame, textvariable=password_var, width=30, show="*").grid(row=5, column=1, sticky=tk.W, pady=5)
        
        # Other Settings
        ttk.Label(main_frame, text="Other Settings", font=('Arial', 12, 'bold')).grid(row=6, column=0, sticky=tk.W, pady=(10, 10))
        
        ttk.Label(main_frame, text="Check Interval (seconds):").grid(row=7, column=0, sticky=tk.W)
        check_interval_var = tk.StringVar(value=str(self.config["check_interval"]))
        ttk.Entry(main_frame, textvariable=check_interval_var, width=10).grid(row=7, column=1, sticky=tk.W, pady=5)
        
        auto_start_var = tk.BooleanVar(value=self.config["auto_start"])
        ttk.Checkbutton(main_frame, text="Start monitoring on application launch", variable=auto_start_var).grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Add to Login Items option - we want to run at startup probably
        startup_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="Launch at login", variable=startup_var).grid(row=9, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Buttons at the bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=10, column=0, columnspan=2, pady=(15, 0))
        
        ttk.Button(button_frame, text="Save Settings", command=lambda: self.save_settings(
            wifi_name_var.get(),
            login_url_var.get(),
            username_var.get(),
            password_var.get(),
            check_interval_var.get(),
            auto_start_var.get(),
            startup_var.get()
        )).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Test Connection", command=self.test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close Window", command=self.hide_window).pack(side=tk.LEFT, padx=5)
        
        # Status bar to show what's happening
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, padding=(2, 2))
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var, anchor=tk.W).pack(side=tk.LEFT)
        
        # When they close the window, just hide it instead of quitting
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # If they enabled auto-start, let's kick things off
        if self.config["auto_start"]:
            self.start_monitoring()
            self.status_var.set("Monitoring active")
        
        self.root.mainloop()
    
    def save_settings(self, wifi_name, login_url, username, password, check_interval, auto_start, add_to_login_items):
        """Save settings from GUI to config"""
        try:
            self.config["wifi_name"] = wifi_name
            self.config["login_url"] = login_url
            self.config["username"] = username
            self.config["password"] = password
            
            try:
                interval = int(check_interval)
                if interval < 10:
                    # Don't let them set a super short interval - that's just wasteful
                    interval = 10  # Minimum interval
                self.config["check_interval"] = interval
            except ValueError:
                messagebox.showerror("Invalid Input", "Check interval must be a number.")
                return
                
            self.config["auto_start"] = auto_start
            
            self.save_config()
            
            # Handle adding/removing from login items
            if add_to_login_items:
                self.add_to_login_items()
            else:
                self.remove_from_login_items()
            
            self.status_var.set("Settings saved successfully")
            messagebox.showinfo("Settings Saved", "Your settings have been saved successfully.")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Could not save settings: {e}")
    
    def add_to_login_items(self):
        """Add app to macOS login items"""
        try:
            app_path = os.path.abspath(sys.argv[0])
            if app_path.endswith('.py'):
                # We're running from source, can't easily add to login items
                logger.warning("Running from Python script, cannot add to login items automatically")
                return
                
            # Create a launch agent plist - this is how macOS starts things at login
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.wifireconnector.plist")
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wifireconnector</string>
    <key>ProgramArguments</key>
    <array>
        <string>{app_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
            with open(plist_path, 'w') as f:
                f.write(plist_content)
                
            # Tell launchd about our new agent
            subprocess.run(f"launchctl load {plist_path}", shell=True)
            logger.info("Added to login items")
        except Exception as e:
            logger.error(f"Error adding to login items: {e}")
    
    def remove_from_login_items(self):
        """Remove app from macOS login items"""
        try:
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.wifireconnector.plist")
            if os.path.exists(plist_path):
                # Unload and delete the launch agent
                subprocess.run(f"launchctl unload {plist_path}", shell=True)
                os.remove(plist_path)
                logger.info("Removed from login items")
        except Exception as e:
            logger.error(f"Error removing from login items: {e}")
    
    def test_connection(self):
        """Test the connection and authentication"""
        self.status_var.set("Testing connection...")
        
        if not self.config["wifi_name"]:
            messagebox.showerror("Error", "Please enter WiFi network name.")
            self.status_var.set("Test failed: Missing WiFi name")
            return
            
        if not self.is_connected_to_wifi():
            # We're not on the right network - let's offer to connect
            result = messagebox.askyesno("Not Connected", 
                f"You are not connected to {self.config['wifi_name']}. Would you like to connect now?")
            if result:
                self.connect_to_wifi()
            else:
                self.status_var.set("Test cancelled")
                return
        
        if not self.is_connected():
            # Connected to WiFi but no internet - probably need to authenticate
            result = messagebox.askyesno("No Internet", 
                "Connected to WiFi but no internet access. Would you like to try authentication?")
            if result:
                if self.authenticate():
                    messagebox.showinfo("Success", "Authentication successful!")
                    self.status_var.set("Authentication successful")
                else:
                    messagebox.showerror("Failed", "Authentication failed. Check your credentials and login URL.")
                    self.status_var.set("Authentication failed")
            else:
                self.status_var.set("Test cancelled")
        else:
            # Everything's working fine!
            messagebox.showinfo("Success", "You are connected to the internet!")
            self.status_var.set("Connection test successful")
    
    def hide_window(self):
        """Hide the main window"""
        self.root.withdraw()
    
    def show_window(self, sender):
        """Show the main window"""
        if self.root:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
    
    def start_from_menu(self, sender):
        """Start monitoring from menu item"""
        if self.start_monitoring():
            self.app.title = "WiFi: Monitoring..."
    
    def stop_from_menu(self, sender):
        """Stop monitoring from menu item"""
        if self.stop_monitoring():
            self.app.title = "WiFi: Paused"
    
    def show_logs(self, sender):
        """Open logs file in default text editor"""
        log_file = os.path.expanduser("~/Library/Logs/wifi_reconnector.log")
        subprocess.run(["open", log_file])
    
    def run_menu_app(self):
        """Run the macOS menu bar app"""
        self.app = rumps.App("WiFi Reconnector", icon="wifi_icon.icns" if os.path.exists("wifi_icon.icns") else None)
        
        # Set up the menu items
        self.app.menu = [
            rumps.MenuItem("Open Settings", callback=self.show_window),
            None,  # separator
            rumps.MenuItem("Start Monitoring", callback=self.start_from_menu),
            rumps.MenuItem("Stop Monitoring", callback=self.stop_from_menu),
            None,  # separator
            rumps.MenuItem("View Logs", callback=self.show_logs),
            rumps.MenuItem("About", callback=self.show_about),
            None,  # separator
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]
        
        # If auto-start is enabled, start monitoring right away
        if self.config["auto_start"]:
            self.start_monitoring()
        
        # Fire up the menu bar app
        self.app.run()
    
    def show_about(self, sender):
        """Show about dialog"""
        rumps.alert(
            title="About WiFi Reconnector",
            message="College WiFi Auto-Reconnector\n\nVersion 1.0\n\nAutomatically reconnects to your college WiFi and handles authentication.",
            ok="OK"
        )
    
    def quit_app(self, sender):
        """Quit the application"""
        self.stop_monitoring()
        rumps.quit_application()
    
    def run(self):
        """Run the application"""
        # Start the menu bar app
        menu_thread = threading.Thread(target=self.run_menu_app)
        menu_thread.daemon = True
        menu_thread.start()
        
        # Show the settings window on first run or just create it for later
        if not self.config["wifi_name"]:
            # First time running - better show them the settings
            self.create_gui()
        else:
            # Just create the window but don't show it
            self.root = tk.Tk()
            self.root.withdraw()
            self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

if __name__ == "__main__":
    app = WifiReconnector()
    app.run()
