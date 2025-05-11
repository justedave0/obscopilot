from obscopilot.ui.dashboard_tab import DashboardTab
from obscopilot.ui.twitch_tab import TwitchTab
from obscopilot.ui.obs_tab import OBSTab
from obscopilot.ui.ai_tab import AITab
from obscopilot.ui.workflows_tab import WorkflowsTab
from obscopilot.ui.settings_tab import SettingsTab
from obscopilot.ui.commands_tab import CommandsTab
from obscopilot.ui.about_dialog import AboutDialog

class MainWindow(QMainWindow):
    def initUI(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle("OBSCopilot")
        self.setMinimumSize(800, 600)
        
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.dashboard_tab = DashboardTab(self)
        self.twitch_tab = TwitchTab(self)
        self.obs_tab = OBSTab(self)
        self.ai_tab = AITab(self)
        self.workflows_tab = WorkflowsTab(self)
        self.commands_tab = CommandsTab(self)
        self.settings_tab = SettingsTab(self)
        
        # Add tabs to tab widget
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.twitch_tab, "Twitch")
        self.tabs.addTab(self.obs_tab, "OBS")
        self.tabs.addTab(self.ai_tab, "AI")
        self.tabs.addTab(self.workflows_tab, "Workflows")
        self.tabs.addTab(self.commands_tab, "Commands")
        self.tabs.addTab(self.settings_tab, "Settings")
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tabs)
        
        # Set main widget
        self.setCentralWidget(main_widget) 