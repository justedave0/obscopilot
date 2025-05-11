from obscopilot.ui.dashboard_tab import DashboardTab
from obscopilot.ui.twitch_tab import TwitchTab
from obscopilot.ui.obs_tab import OBSTab
from obscopilot.ui.ai_tab import AITab
from obscopilot.ui.workflows_tab import WorkflowsTab
from obscopilot.ui.settings_tab import SettingsTab
from obscopilot.ui.commands_tab import CommandsTab
from obscopilot.ui.viewer_stats_tab import ViewerStatsTab
from obscopilot.ui.alerts_tab import AlertsTab
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
        self.tab_widget = QTabWidget()
        
        # Dashboard tab
        self.dashboard_tab = DashboardTab(self)
        self.tab_widget.addTab(self.dashboard_tab, "Dashboard")
        
        # Twitch tab
        self.twitch_tab = TwitchTab(self, self.twitch_client)
        self.tab_widget.addTab(self.twitch_tab, "Twitch")
        
        # OBS tab
        self.obs_tab = OBSTab(self, self.obs_client)
        self.tab_widget.addTab(self.obs_tab, "OBS")
        
        # AI tab
        self.ai_tab = AITab(self, self.ai_client)
        self.tab_widget.addTab(self.ai_tab, "AI Assistant")
        
        # Workflows tab
        self.workflows_tab = WorkflowsTab(self, self.workflow_engine)
        self.tab_widget.addTab(self.workflows_tab, "Workflows")
        
        # Commands tab
        self.commands_tab = CommandsTab(self, self.database, self.command_registry)
        self.tab_widget.addTab(self.commands_tab, "Commands")
        
        # Viewer Stats tab
        self.viewer_stats_tab = ViewerStatsTab(self, self.database)
        self.tab_widget.addTab(self.viewer_stats_tab, "Viewer Stats")
        
        # Alerts tab
        self.alerts_tab = AlertsTab(self, self.database)
        self.tab_widget.addTab(self.alerts_tab, "Alerts")
        
        # Settings tab
        self.settings_tab = SettingsTab(self, self.config)
        self.tab_widget.addTab(self.settings_tab, "Settings")
        
        main_layout.addWidget(self.tab_widget)
        
        # Set main widget
        self.setCentralWidget(main_widget)
        
        # Create status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready") 