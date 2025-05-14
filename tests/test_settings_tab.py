import pytest
from unittest.mock import MagicMock, patch
import logging
import sys

from PyQt6.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout, QGroupBox, QFormLayout
from PyQt6.QtCore import Qt, QTimer

from ui.tabs.settings_tab import PasswordLineEdit, SettingsTab
from ui.tabs.settings_controller import SettingsController

# Test constants
TEST_HOST = "localhost"
TEST_PORT = 4455
TEST_PASSWORD = "testpassword"

# Need a QApplication for PyQt widgets
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # app.quit()  # Don't quit to avoid segfaults when running multiple tests

@pytest.fixture
def settings_tab(qapp):
    """Fixture that provides a settings tab."""
    tab = SettingsTab()
    return tab

@pytest.fixture
def password_line_edit(qapp):
    """Fixture that provides a password line edit."""
    line_edit = PasswordLineEdit()
    return line_edit

class TestPasswordLineEdit:
    @pytest.fixture
    def app(self):
        """Fixture that provides a QApplication instance."""
        app = QApplication([])
        yield app
        app.quit()
    
    @pytest.fixture
    def password_line_edit(self, app):
        """Fixture that provides a PasswordLineEdit instance."""
        return PasswordLineEdit()
    
    def test_init(self, password_line_edit):
        """Test initializing the password line edit."""
        assert password_line_edit.echoMode() == QLineEdit.EchoMode.Password
        assert password_line_edit.actions()  # Has the toggle action
    
    def test_toggle_password_visibility(self, password_line_edit):
        """Test toggling password visibility."""
        # Initially in password mode
        assert password_line_edit.echoMode() == QLineEdit.EchoMode.Password
        
        # Toggle to normal mode
        password_line_edit.toggle_password_visibility()
        assert password_line_edit.echoMode() == QLineEdit.EchoMode.Normal
        
        # Toggle back to password mode
        password_line_edit.toggle_password_visibility()
        assert password_line_edit.echoMode() == QLineEdit.EchoMode.Password
    
    def test_set_password(self, password_line_edit):
        """Test setting a password."""
        # Set a password
        result = password_line_edit.set_password("test_password")
        
        # Check that the password was set
        assert password_line_edit.text() == "test_password"
        assert result is True
        
        # Set an empty password
        result = password_line_edit.set_password("")
        
        # Check that the password was set
        assert password_line_edit.text() == ""
        assert result is True

class TestSettingsTab:
    @pytest.fixture
    def app(self):
        """Fixture that provides a QApplication instance."""
        app = QApplication([])
        yield app
        app.quit()
    
    @pytest.fixture
    def settings_controller(self):
        """Fixture that provides a mock settings controller."""
        controller = MagicMock(spec=SettingsController)
        controller.load_settings = MagicMock()
        controller.connection_successful = MagicMock()
        controller.connection_failed = MagicMock()
        controller.disconnection_successful = MagicMock()
        controller.disconnection_failed = MagicMock()
        controller.settings_loaded = MagicMock()
        controller.notify_auto_connect_started = MagicMock()
        controller.connect_to_obs = MagicMock()
        controller.disconnect_from_obs = MagicMock()
        controller.set_auto_connect_enabled = MagicMock(return_value=True)
        controller.is_connected = MagicMock(return_value=False)
        return controller
    
    @pytest.fixture
    def settings_tab(self, app, settings_controller):
        """Fixture that provides a SettingsTab instance with a mock controller."""
        with patch('PyQt6.QtCore.QTimer.singleShot'):
            tab = SettingsTab(settings_controller=settings_controller)
            return tab
    
    def test_init(self, settings_tab, settings_controller):
        """Test initializing the settings tab."""
        assert settings_tab.controller == settings_controller
        assert not settings_tab.settings_loaded
        
        # Check that UI elements were created
        assert hasattr(settings_tab, 'obs_websocket_group')
        assert hasattr(settings_tab, 'host_input')
        assert hasattr(settings_tab, 'port_input')
        assert hasattr(settings_tab, 'password_input')
        assert hasattr(settings_tab, 'auto_connect_checkbox')
        assert hasattr(settings_tab, 'connect_button')
        assert hasattr(settings_tab, 'connection_status_label')
    
    def test_setup_connections(self, settings_tab, settings_controller):
        """Test setting up signal connections."""
        # Call setup_connections explicitly to verify connections
        settings_tab.setup_connections()
        
        # Check that all controller signals are connected
        assert settings_controller.connection_successful.connect.called
        assert settings_controller.connection_failed.connect.called
        assert settings_controller.disconnection_successful.connect.called
        assert settings_controller.disconnection_failed.connect.called
        assert settings_controller.settings_loaded.connect.called
        assert settings_controller.notify_auto_connect_started.connect.called
    
    def test_delayed_init_settings_not_loaded(self, settings_tab, settings_controller):
        """Test delayed initialization when settings aren't loaded."""
        # Reset status
        settings_tab.settings_loaded = False
        
        # Create a mock for update_ui_from_controller
        settings_tab.update_ui_from_controller = MagicMock()
        
        # Call delayed_init
        settings_tab.delayed_init()
        
        # Check that load_settings was called
        settings_controller.load_settings.assert_called_once()
        
        # Check that update_ui_from_controller was called
        settings_tab.update_ui_from_controller.assert_called_once()
    
    def test_delayed_init_settings_already_loaded(self, settings_tab, settings_controller):
        """Test delayed initialization when settings are already loaded."""
        # Set status
        settings_tab.settings_loaded = True
        
        # Create a mock for update_ui_from_controller
        settings_tab.update_ui_from_controller = MagicMock()
        
        # Call delayed_init
        settings_tab.delayed_init()
        
        # Check that load_settings was not called
        settings_controller.load_settings.assert_not_called()
        
        # Check that update_ui_from_controller was called
        settings_tab.update_ui_from_controller.assert_called_once()
    
    def test_on_settings_loaded(self, settings_tab):
        """Test handling loaded settings."""
        # Create test settings
        test_settings = {
            "obs_host": "example.com",
            "obs_port": 1234,
            "obs_password": "test_password",
            "auto_connect_enabled": True
        }
        
        # Mock set_password
        original_set_password = settings_tab.password_input.set_password
        settings_tab.password_input.set_password = MagicMock(return_value=True)
        
        # Call on_settings_loaded
        settings_tab.on_settings_loaded(test_settings)
        
        # Check that settings were loaded correctly
        assert settings_tab.settings_loaded is True
        assert settings_tab.host_input.text() == "example.com"
        assert settings_tab.port_input.value() == 1234
        settings_tab.password_input.set_password.assert_called_once_with("test_password")
        assert settings_tab.auto_connect_checkbox.isChecked() is True
        
        # Restore original method
        settings_tab.password_input.set_password = original_set_password
    
    def test_on_settings_loaded_failed_password_set(self, settings_tab):
        """Test handling loaded settings with failed password set."""
        # Create test settings
        test_settings = {
            "obs_host": "example.com",
            "obs_port": 1234,
            "obs_password": "test_password",
            "auto_connect_enabled": True
        }
        
        # Mock set_password to return False (failure)
        settings_tab.password_input.set_password = MagicMock(return_value=False)
        
        # Mock delayed_set_password
        settings_tab.delayed_set_password = MagicMock()
        
        # Mock QTimer.singleShot
        with patch('PyQt6.QtCore.QTimer.singleShot') as mock_timer:
            # Call on_settings_loaded
            settings_tab.on_settings_loaded(test_settings)
            
            # Check that delayed_set_password was scheduled
            mock_timer.assert_called_once()
    
    def test_delayed_set_password_success(self, settings_tab):
        """Test setting a password after a delay with success."""
        # Mock set_password to return True
        settings_tab.password_input.set_password = MagicMock(return_value=True)
        settings_tab.password_input.text = MagicMock(return_value="test_password")
        
        # Call delayed_set_password
        settings_tab.delayed_set_password("test_password")
        
        # Check that set_password was called
        settings_tab.password_input.set_password.assert_called_once_with("test_password")
    
    def test_delayed_set_password_failure(self, settings_tab):
        """Test setting a password after a delay with failure."""
        # Mock set_password to return True but text() to return a different value
        settings_tab.password_input.set_password = MagicMock(return_value=True)
        settings_tab.password_input.text = MagicMock(return_value="wrong_password")
        
        # Call delayed_set_password
        settings_tab.delayed_set_password("test_password")
        
        # Check that set_password was called
        settings_tab.password_input.set_password.assert_called_once_with("test_password")
    
    def test_connect_to_obs(self, settings_tab, settings_controller):
        """Test connecting to OBS."""
        # Set input values
        settings_tab.host_input.setText("example.com")
        settings_tab.port_input.setValue(1234)
        settings_tab.password_input.setText("test_password")
        
        # Call connect_to_obs
        settings_tab.connect_to_obs()
        
        # Check that connect_to_obs was called with the correct arguments
        settings_controller.connect_to_obs.assert_called_once_with("example.com", 1234, "test_password")
    
    def test_disconnect_from_obs(self, settings_tab, settings_controller):
        """Test disconnecting from OBS."""
        # Call disconnect_from_obs
        settings_tab.disconnect_from_obs()
        
        # Check that disconnect_from_obs was called
        settings_controller.disconnect_from_obs.assert_called_once()
    
    def test_on_connection_successful(self, settings_tab):
        """Test handling a successful connection."""
        # Create mocks
        settings_tab.connection_status_label = MagicMock()
        settings_tab.connect_button = MagicMock()
        settings_tab.controller.is_connected = MagicMock(return_value=True)
        
        # Call on_connection_successful
        settings_tab.on_connection_successful()
        
        # Check that UI was updated
        settings_tab.connection_status_label.setText.assert_called_once_with("Connected")
        settings_tab.connection_status_label.setStyleSheet.assert_called_once_with("color: green")
        settings_tab.connect_button.setText.assert_called_once_with("Disconnect")
    
    def test_on_connection_failed(self, settings_tab):
        """Test handling a failed connection."""
        # Create mocks
        settings_tab.connection_status_label = MagicMock()
        
        # Call on_connection_failed
        error_message = "Test error"
        settings_tab.on_connection_failed(error_message)
        
        # Check that UI was updated
        settings_tab.connection_status_label.setText.assert_called_once_with("Not Connected")
        settings_tab.connection_status_label.setStyleSheet.assert_called_once_with("color: red")
    
    def test_on_disconnection_successful(self, settings_tab):
        """Test handling a successful disconnection."""
        # Create mocks
        settings_tab.connection_status_label = MagicMock()
        settings_tab.connect_button = MagicMock()
        
        # Call on_disconnection_successful
        settings_tab.on_disconnection_successful()
        
        # Check that UI was updated
        settings_tab.connection_status_label.setText.assert_called_once_with("Not Connected")
        settings_tab.connection_status_label.setStyleSheet.assert_called_once_with("color: red")
        settings_tab.connect_button.setText.assert_called_once_with("Connect")
    
    def test_on_disconnection_failed(self, settings_tab):
        """Test handling a failed disconnection."""
        # Mock the QMessageBox.warning method
        with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warning:
            # Call on_disconnection_failed
            error_message = "Test error"
            settings_tab.on_disconnection_failed(error_message)
            
            # Check that warning was shown
            mock_warning.assert_called_once()
    
    def test_on_auto_connect_clicked(self, settings_tab, settings_controller):
        """Test handling auto-connect checkbox clicks."""
        # Call on_auto_connect_clicked with True
        settings_tab.on_auto_connect_clicked(True)
        
        # Check that set_auto_connect_enabled was called with True
        settings_controller.set_auto_connect_enabled.assert_called_once_with(True)
        
        # Reset mock
        settings_controller.set_auto_connect_enabled.reset_mock()
        
        # Call on_auto_connect_clicked with False
        settings_tab.on_auto_connect_clicked(False)
        
        # Check that set_auto_connect_enabled was called with False
        settings_controller.set_auto_connect_enabled.assert_called_once_with(False)
    
    def test_on_auto_connect_started(self, settings_tab):
        """Test handling auto-connect start notification."""
        # Mock _show_auto_connect_notification
        settings_tab._show_auto_connect_notification = MagicMock()
        
        # Call on_auto_connect_started
        host = "example.com"
        port = 1234
        settings_tab.on_auto_connect_started(host, port)
        
        # Check that _show_auto_connect_notification was called
        settings_tab._show_auto_connect_notification.assert_called_once_with(host, port)
    
    def test_show_auto_connect_notification(self, settings_tab):
        """Test showing auto-connect notification."""
        # Mock QMessageBox.information
        with patch('PyQt6.QtWidgets.QMessageBox.information') as mock_info:
            # Call _show_auto_connect_notification
            host = "example.com"
            port = 1234
            settings_tab._show_auto_connect_notification(host, port)
            
            # Check that information was shown
            mock_info.assert_called_once()
    
    def test_update_ui_from_controller_connected(self, settings_tab):
        """Test updating UI from controller when connected."""
        # Mock controller
        settings_tab.controller.is_connected = MagicMock(return_value=True)
        
        # Mock UI elements
        settings_tab.connection_status_label = MagicMock()
        settings_tab.connect_button = MagicMock()
        
        # Call update_ui_from_controller
        settings_tab.update_ui_from_controller()
        
        # Check that UI was updated for connected state
        settings_tab.connection_status_label.setText.assert_called_once_with("Connected")
        settings_tab.connection_status_label.setStyleSheet.assert_called_once_with("color: green")
        settings_tab.connect_button.setText.assert_called_once_with("Disconnect")
    
    def test_update_ui_from_controller_disconnected(self, settings_tab):
        """Test updating UI from controller when disconnected."""
        # Mock controller
        settings_tab.controller.is_connected = MagicMock(return_value=False)
        
        # Mock UI elements
        settings_tab.connection_status_label = MagicMock()
        settings_tab.connect_button = MagicMock()
        
        # Call update_ui_from_controller
        settings_tab.update_ui_from_controller()
        
        # Check that UI was updated for disconnected state
        settings_tab.connection_status_label.setText.assert_called_once_with("Not Connected")
        settings_tab.connection_status_label.setStyleSheet.assert_called_once_with("color: red")
        settings_tab.connect_button.setText.assert_called_once_with("Connect") 