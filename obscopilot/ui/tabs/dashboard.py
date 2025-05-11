"""
Dashboard for OBSCopilot.

This module provides a dashboard with live statistics and monitoring.
"""

import logging
from typing import Dict, List, Optional, Any
import time
import uuid
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QGridLayout, QGroupBox, QSizePolicy, QScrollArea,
    QToolButton, QMenu
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QCursor, QPixmap, QIcon

from obscopilot.core.config import Config
from obscopilot.core.events import EventType, Event, event_bus
from obscopilot.storage.repositories import StreamHealthRepository, UserStatsRepository
from obscopilot.storage.models import StreamHealthModel, UserStatsModel
from obscopilot.ui.dashboard_customizer import (
    DashboardManager, DashboardLayout, WidgetType, 
    WidgetDefinition, DashboardCustomizer
)

logger = logging.getLogger(__name__)


class StatCard(QFrame):
    """Card displaying a statistic."""
    
    def __init__(self, title: str, value: str, icon_path: Optional[str] = None, parent=None):
        """Initialize the stat card.
        
        Args:
            title: Card title
            value: Statistic value
            icon_path: Optional path to icon
            parent: Parent widget
        """
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAutoFillBackground(True)
        
        # Set up colors
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#2A2A2A"))
        self.setPalette(palette)
        
        # Minimum size
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # Initialize UI
        self.title = title
        self.value = value
        self.icon_path = icon_path
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Card title
        title_layout = QHBoxLayout()
        
        # Icon if provided
        if self.icon_path:
            icon_label = QLabel()
            icon_pixmap = QPixmap(self.icon_path)
            if not icon_pixmap.isNull():
                icon_label.setPixmap(icon_pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio))
                title_layout.addWidget(icon_label)
        
        # Title text
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # Value
        self.value_label = QLabel(self.value)
        self.value_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)
        
    def update_value(self, value: str):
        """Update the displayed value.
        
        Args:
            value: New value to display
        """
        self.value = value
        self.value_label.setText(value)


class EventItem(QFrame):
    """Widget displaying an event in the event log."""
    
    def __init__(self, event_type: str, message: str, timestamp: float, parent=None):
        """Initialize the event item.
        
        Args:
            event_type: Type of event
            message: Event message
            timestamp: Event timestamp
            parent: Parent widget
        """
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAutoFillBackground(True)
        
        # Set up colors
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#2A2A2A"))
        self.setPalette(palette)
        
        # Initialize UI
        self.event_type = event_type
        self.message = message
        self.timestamp = timestamp
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Time
        time_str = datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")
        time_label = QLabel(time_str)
        time_label.setFixedWidth(70)
        layout.addWidget(time_label)
        
        # Event type
        type_label = QLabel(self.event_type)
        type_label.setFixedWidth(120)
        
        # Set color based on event type
        if "ERROR" in self.event_type:
            type_label.setStyleSheet("color: #F44336;")
        elif "WARNING" in self.event_type:
            type_label.setStyleSheet("color: #FFC107;")
        elif "CONNECTED" in self.event_type:
            type_label.setStyleSheet("color: #4CAF50;")
        layout.addWidget(type_label)
        
        # Message
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)


class Dashboard(QWidget):
    """Dashboard widget displaying live statistics and status."""
    
    def __init__(
        self, 
        config: Config,
        stream_health_repo: StreamHealthRepository = None,
        user_stats_repo: UserStatsRepository = None,
        parent=None
    ):
        """Initialize the dashboard.
        
        Args:
            config: Application configuration
            stream_health_repo: Stream health repository
            user_stats_repo: User statistics repository
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.config = config
        self.stream_health_repo = stream_health_repo
        self.user_stats_repo = user_stats_repo
        
        # Stats storage
        self.stats = {
            "viewers": "0",
            "follows": "0",
            "subs": "0",
            "bits": "0",
            "uptime": "00:00:00",
            "messages": "0",
            "cpu": "0%",
            "fps": "0",
            "stream_health": "Offline"
        }
        
        # Event log
        self.events = []
        self.max_events = 100
        
        # Stream start time
        self.stream_start_time = None
        
        # Dashboard widgets
        self.widgets = {}
        
        # Initialize dashboard manager
        self.dashboard_manager = DashboardManager(config)
        
        # Initialize UI
        self._init_ui()
        
        # Load active layout
        self._load_active_layout()
        
        # Set up timer for regular updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_stats)
        self.update_timer.start(5000)  # Update every 5 seconds
        
        # Register for events
        self._register_events()
        
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Header with layout selector
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Dashboard")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        # Spacer
        header_layout.addStretch()
        
        # Customize button
        customize_button = QPushButton("Customize Dashboard")
        customize_button.clicked.connect(self._show_customizer)
        header_layout.addWidget(customize_button)
        
        layout.addLayout(header_layout)
        
        # Dashboard content
        self.dashboard_content = QWidget()
        self.dashboard_layout = QGridLayout(self.dashboard_content)
        self.dashboard_layout.setSpacing(10)
        
        # Add to scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.dashboard_content)
        
        layout.addWidget(scroll_area)
    
    def _load_active_layout(self):
        """Load the active dashboard layout."""
        # Clear existing widgets
        for widget in self.widgets.values():
            self.dashboard_layout.removeWidget(widget)
            widget.deleteLater()
        self.widgets.clear()
        
        # Get active layout
        layout = self.dashboard_manager.get_active_layout()
        if not layout:
            return
            
        # Create widgets
        for widget_def in layout.widgets:
            # Create widget based on type
            widget = self._create_widget(widget_def)
            if widget:
                # Add to grid
                pos = widget_def.position
                self.dashboard_layout.addWidget(
                    widget,
                    pos.get("row", 0),
                    pos.get("col", 0),
                    pos.get("row_span", 1),
                    pos.get("col_span", 1)
                )
                
                # Store reference
                self.widgets[widget_def.widget_id] = widget
    
    def _create_widget(self, widget_def: WidgetDefinition) -> QWidget:
        """Create a widget based on type.
        
        Args:
            widget_def: Widget definition
            
        Returns:
            Created widget or None
        """
        widget_type = widget_def.widget_type
        
        # Stat cards
        if widget_type == WidgetType.VIEWER_COUNT:
            return StatCard(widget_def.title, self.stats.get("viewers", "0"))
        elif widget_type == WidgetType.FOLLOWERS:
            return StatCard(widget_def.title, self.stats.get("follows", "0"))
        elif widget_type == WidgetType.SUBSCRIBERS:
            return StatCard(widget_def.title, self.stats.get("subs", "0"))
        elif widget_type == WidgetType.BITS:
            return StatCard(widget_def.title, self.stats.get("bits", "0"))
        elif widget_type == WidgetType.UPTIME:
            return StatCard(widget_def.title, self.stats.get("uptime", "00:00:00"))
        elif widget_type == WidgetType.MESSAGE_COUNT:
            return StatCard(widget_def.title, self.stats.get("messages", "0"))
        elif widget_type == WidgetType.CPU_USAGE:
            return StatCard(widget_def.title, self.stats.get("cpu", "0%"))
        elif widget_type == WidgetType.FPS:
            return StatCard(widget_def.title, self.stats.get("fps", "0"))
        elif widget_type == WidgetType.STREAM_HEALTH:
            return StatCard(widget_def.title, self.stats.get("stream_health", "Offline"))
            
        # Event log
        elif widget_type == WidgetType.RECENT_EVENTS:
            # Create event log
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            frame.setAutoFillBackground(True)
            
            # Set background color
            palette = frame.palette()
            palette.setColor(QPalette.ColorRole.Window, QColor("#2A2A2A"))
            frame.setPalette(palette)
            
            # Layout
            log_layout = QVBoxLayout(frame)
            
            # Header
            header = QHBoxLayout()
            title_label = QLabel(widget_def.title)
            title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            header.addWidget(title_label)
            header.addStretch()
            
            # Clear button
            clear_button = QPushButton("Clear")
            clear_button.setFixedWidth(60)
            clear_button.clicked.connect(self._clear_event_log)
            header.addWidget(clear_button)
            
            log_layout.addLayout(header)
            
            # Events container
            events_container = QWidget()
            self.events_layout = QVBoxLayout(events_container)
            self.events_layout.setSpacing(2)
            self.events_layout.setContentsMargins(0, 0, 0, 0)
            
            # Load initial events
            for event in self.events:
                event_item = EventItem(event["type"], event["message"], event["timestamp"])
                self.events_layout.addWidget(event_item)
            
            log_layout.addWidget(events_container)
            
            return frame
            
        # Default to empty frame
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        
        # Set background color
        palette = frame.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#2A2A2A"))
        frame.setPalette(palette)
        
        # Layout
        layout = QVBoxLayout(frame)
        
        # Title
        title_label = QLabel(widget_def.title)
        title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # Message
        message = QLabel(f"Widget type not implemented: {widget_type.value}")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)
        
        return frame
    
    def _show_customizer(self):
        """Show the dashboard customizer."""
        customizer = DashboardCustomizer(self.dashboard_manager, self)
        customizer.layout_updated.connect(self._on_layout_updated)
        customizer.exec()
    
    def _on_layout_updated(self, layout: DashboardLayout):
        """Handle layout updates from customizer.
        
        Args:
            layout: Updated layout
        """
        # Reload layout
        self._load_active_layout()
        
        # Update stats to refresh widgets
        self._update_stat_cards()
    
    def _update_stat_cards(self):
        """Update all stat cards with current values."""
        for widget_id, widget in self.widgets.items():
            if isinstance(widget, StatCard):
                # Get stat value based on widget title
                title = widget.title.lower()
                
                if "viewer" in title:
                    widget.update_value(self.stats.get("viewers", "0"))
                elif "follow" in title:
                    widget.update_value(self.stats.get("follows", "0"))
                elif "sub" in title:
                    widget.update_value(self.stats.get("subs", "0"))
                elif "bit" in title:
                    widget.update_value(self.stats.get("bits", "0"))
                elif "uptime" in title:
                    widget.update_value(self.stats.get("uptime", "00:00:00"))
                elif "message" in title:
                    widget.update_value(self.stats.get("messages", "0"))
                elif "cpu" in title:
                    widget.update_value(self.stats.get("cpu", "0%"))
                elif "fps" in title:
                    widget.update_value(self.stats.get("fps", "0"))
                elif "health" in title or "stream" in title:
                    widget.update_value(self.stats.get("stream_health", "Offline"))
    
    def _add_event(self, event_type: str, message: str):
        """Add an event to the event log.
        
        Args:
            event_type: Type of event
            message: Event message
        """
        # Create event
        event = {
            "type": event_type,
            "message": message,
            "timestamp": time.time()
        }
        
        # Add to events list
        self.events.insert(0, event)
        
        # Limit number of events
        if len(self.events) > self.max_events:
            self.events = self.events[:self.max_events]
        
        # Add to UI if event log exists
        if hasattr(self, 'events_layout'):
            # Create event item
            event_item = EventItem(event["type"], event["message"], event["timestamp"])
            
            # Add to layout
            self.events_layout.insertWidget(0, event_item)
            
            # Remove excess items
            if self.events_layout.count() > self.max_events:
                # Get last item
                item = self.events_layout.itemAt(self.events_layout.count() - 1)
                if item and item.widget():
                    # Remove from layout
                    self.events_layout.removeItem(item)
                    # Delete widget
                    item.widget().deleteLater()
    
    def _register_events(self):
        """Register for application events."""
        # Handle stream start/stop events
        event_bus.add_listener(EventType.OBS_STREAM_STARTED, self._on_stream_started)
        event_bus.add_listener(EventType.OBS_STREAM_STOPPED, self._on_stream_stopped)
        
        # Handle stream health events
        event_bus.add_listener(EventType.STREAM_HEALTH_UPDATED, self._on_stream_health_updated)
        event_bus.add_listener(EventType.STREAM_HEALTH_WARNING, self._on_stream_health_warning)
        
        # Handle Twitch events
        event_bus.add_listener(EventType.TWITCH_VIEWERS_UPDATED, self._on_viewers_updated)
        event_bus.add_listener(EventType.TWITCH_FOLLOW, self._on_follow)
        event_bus.add_listener(EventType.TWITCH_SUBSCRIPTION, self._on_subscription)
        event_bus.add_listener(EventType.TWITCH_BITS, self._on_bits)
        event_bus.add_listener(EventType.TWITCH_CHAT_MESSAGE, self._on_chat_message)
        
        # Handle connection events
        event_bus.add_listener(EventType.TWITCH_CONNECTED, lambda e: self._add_event("TWITCH CONNECTED", "Connected to Twitch"))
        event_bus.add_listener(EventType.TWITCH_DISCONNECTED, lambda e: self._add_event("TWITCH DISCONNECTED", "Disconnected from Twitch"))
        event_bus.add_listener(EventType.OBS_CONNECTED, lambda e: self._add_event("OBS CONNECTED", "Connected to OBS"))
        event_bus.add_listener(EventType.OBS_DISCONNECTED, lambda e: self._add_event("OBS DISCONNECTED", "Disconnected from OBS"))
        
        # Handle error events
        event_bus.add_listener(EventType.TWITCH_ERROR, lambda e: self._add_event("TWITCH ERROR", e.data.get('message', 'Unknown error')))
        event_bus.add_listener(EventType.OBS_ERROR, lambda e: self._add_event("OBS ERROR", e.data.get('message', 'Unknown error')))
        event_bus.add_listener(EventType.AI_ERROR, lambda e: self._add_event("AI ERROR", e.data.get('message', 'Unknown error')))
        
    def _update_stats(self):
        """Update dashboard statistics."""
        # Update uptime if stream is live
        if self.stream_start_time:
            uptime = datetime.now() - self.stream_start_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.stats["uptime"] = f"{hours:02}:{minutes:02}:{seconds:02}"
        
        # Update any other time-based stats
        self._update_stat_cards()
        
    def _on_stream_started(self, event: Event):
        """Handle stream started event.
        
        Args:
            event: Stream started event
        """
        self.stream_start_time = datetime.now()
        self.stats["uptime"] = "00:00:00"
        self.stats["stream_health"] = "Good"
        self._update_stat_cards()
        
        self._add_event("STREAM STARTED", "Stream started")
        
    def _on_stream_stopped(self, event: Event):
        """Handle stream stopped event.
        
        Args:
            event: Stream stopped event
        """
        self.stream_start_time = None
        self.stats["uptime"] = "00:00:00"
        self.stats["stream_health"] = "Offline"
        self._update_stat_cards()
        
        self._add_event("STREAM STOPPED", "Stream stopped")
        
    def _on_stream_health_updated(self, event: Event):
        """Handle stream health update event.
        
        Args:
            event: Stream health update event
        """
        data = event.data
        
        # Update CPU usage
        cpu_usage = data.get('cpu_usage')
        if cpu_usage is not None:
            self.stats["cpu"] = f"{cpu_usage:.1f}%"
        
        # Update FPS
        fps = data.get('fps')
        if fps is not None:
            self.stats["fps"] = f"{fps:.1f}"
        
        # Update health status
        status = data.get('status', 'Unknown')
        self.stats["stream_health"] = status
        
        self._update_stat_cards()
        
    def _on_stream_health_warning(self, event: Event):
        """Handle stream health warning event.
        
        Args:
            event: Stream health warning event
        """
        message = event.data.get('message', 'Unknown warning')
        self._add_event("STREAM HEALTH WARNING", message)
        
    def _on_viewers_updated(self, event: Event):
        """Handle viewers updated event.
        
        Args:
            event: Viewers updated event
        """
        viewers = event.data.get('count', 0)
        self.stats["viewers"] = str(viewers)
        self._update_stat_cards()
        
    def _on_follow(self, event: Event):
        """Handle follow event.
        
        Args:
            event: Follow event
        """
        username = event.data.get('username', 'Unknown')
        
        # Increment follows counter
        try:
            self.stats["follows"] = str(int(self.stats["follows"]) + 1)
            self._update_stat_cards()
        except ValueError:
            self.stats["follows"] = "1"
            self._update_stat_cards()
        
        self._add_event("NEW FOLLOW", f"{username} followed the channel")
        
    def _on_subscription(self, event: Event):
        """Handle subscription event.
        
        Args:
            event: Subscription event
        """
        username = event.data.get('username', 'Unknown')
        is_gift = event.data.get('is_gift', False)
        months = event.data.get('months', 1)
        
        # Increment subs counter
        try:
            self.stats["subs"] = str(int(self.stats["subs"]) + 1)
            self._update_stat_cards()
        except ValueError:
            self.stats["subs"] = "1"
            self._update_stat_cards()
        
        if is_gift:
            gifter = event.data.get('gifter_name', 'Someone')
            self._add_event("NEW GIFT SUB", f"{gifter} gifted a subscription to {username}")
        elif months > 1:
            self._add_event("RESUBSCRIPTION", f"{username} resubscribed for {months} months")
        else:
            self._add_event("NEW SUBSCRIPTION", f"{username} subscribed to the channel")
        
    def _on_bits(self, event: Event):
        """Handle bits event.
        
        Args:
            event: Bits event
        """
        username = event.data.get('username', 'Unknown')
        amount = event.data.get('bits', 0)
        
        # Increment bits counter
        try:
            current_bits = int(self.stats["bits"]) 
            self.stats["bits"] = str(current_bits + amount)
            self._update_stat_cards()
        except ValueError:
            self.stats["bits"] = str(amount)
            self._update_stat_cards()
        
        self._add_event("BITS DONATION", f"{username} cheered {amount} bits")
        
    def _on_chat_message(self, event: Event):
        """Handle chat message event.
        
        Args:
            event: Chat message event
        """
        # Increment message counter
        try:
            self.stats["messages"] = str(int(self.stats["messages"]) + 1)
            self._update_stat_cards()
        except ValueError:
            self.stats["messages"] = "1"
            self._update_stat_cards()
        
    def _clear_event_log(self):
        """Clear the event log."""
        # Clear events list
        self.events = []
        
        # Clear UI
        while self.events_layout.count() > 0:
            item = self.events_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add empty label
        self.events_empty_label = QLabel("No events logged")
        self.events_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.events_layout.addWidget(self.events_empty_label) 