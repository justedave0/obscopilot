"""
Viewer statistics tab for OBSCopilot UI.

This module provides a UI tab for viewing and analyzing Twitch viewer statistics.
"""

import asyncio
import datetime
import logging
from typing import Dict, List, Any, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QScrollArea, QFrame, QSplitter, QComboBox, QDateEdit,
    QGroupBox, QFormLayout, QProgressBar, QSpacerItem, QSizePolicy,
    QLineEdit
)

from obscopilot.core.events import Event, EventType, event_bus
from obscopilot.storage.database import Database
from obscopilot.twitch.viewer_stats import ViewerStatsTracker

logger = logging.getLogger(__name__)


class ViewerStatsTab(QWidget):
    """Tab for Twitch viewer statistics."""
    
    # Signal for async updates from the ViewerStatsTracker
    stats_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None, database: Optional[Database] = None):
        """Initialize viewer stats tab.
        
        Args:
            parent: Parent widget
            database: Database instance
        """
        super().__init__(parent)
        
        self.database = database
        self.stats_tracker = None
        
        if database:
            self.stats_tracker = ViewerStatsTracker(database)
        
        self.init_ui()
        
        # Setup refresh timer (every 5 seconds)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_stats)
        self.refresh_timer.start(5000)
        
        # Connect signals
        self.stats_updated.connect(self.update_dashboard)
    
    def init_ui(self):
        """Initialize the UI."""
        main_layout = QVBoxLayout(self)
        
        # Create tabs
        tab_widget = QTabWidget()
        
        # Dashboard tab
        self.dashboard_widget = QWidget()
        self.init_dashboard_tab()
        tab_widget.addTab(self.dashboard_widget, "Dashboard")
        
        # Viewers tab
        self.viewers_widget = QWidget()
        self.init_viewers_tab()
        tab_widget.addTab(self.viewers_widget, "Viewer List")
        
        # Analytics tab
        self.analytics_widget = QWidget()
        self.init_analytics_tab()
        tab_widget.addTab(self.analytics_widget, "Analytics")
        
        # Sessions tab
        self.sessions_widget = QWidget()
        self.init_sessions_tab()
        tab_widget.addTab(self.sessions_widget, "Stream Sessions")
        
        main_layout.addWidget(tab_widget)
    
    def init_dashboard_tab(self):
        """Initialize the dashboard tab."""
        layout = QVBoxLayout(self.dashboard_widget)
        
        # Stream status section
        status_container = QGroupBox("Stream Status")
        status_layout = QVBoxLayout(status_container)
        
        # Status row
        status_row = QHBoxLayout()
        
        # Live status
        self.live_status = QLabel("OFFLINE")
        self.live_status.setStyleSheet("font-size: 18px; font-weight: bold; color: #888888;")
        status_row.addWidget(self.live_status)
        
        # Stream duration
        self.stream_duration = QLabel("Duration: 00:00:00")
        self.stream_duration.setStyleSheet("font-size: 14px; color: #888888;")
        status_row.addWidget(self.stream_duration)
        
        status_row.addStretch()
        
        # Manual tracking controls
        self.start_tracking_btn = QPushButton("Start Tracking")
        self.start_tracking_btn.clicked.connect(self.start_tracking)
        status_row.addWidget(self.start_tracking_btn)
        
        self.stop_tracking_btn = QPushButton("Stop Tracking")
        self.stop_tracking_btn.clicked.connect(self.stop_tracking)
        self.stop_tracking_btn.setEnabled(False)
        status_row.addWidget(self.stop_tracking_btn)
        
        status_layout.addLayout(status_row)
        
        # Stats grid
        stats_grid = QHBoxLayout()
        
        # Viewer stats
        viewer_stats = QGroupBox("Viewers")
        viewer_stats_layout = QFormLayout(viewer_stats)
        
        self.active_viewers_label = QLabel("0")
        self.active_viewers_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        viewer_stats_layout.addRow("Active Viewers:", self.active_viewers_label)
        
        self.total_viewers_label = QLabel("0")
        self.total_viewers_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        viewer_stats_layout.addRow("Total Unique Viewers:", self.total_viewers_label)
        
        self.peak_viewers_label = QLabel("0")
        self.peak_viewers_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        viewer_stats_layout.addRow("Peak Viewers:", self.peak_viewers_label)
        
        stats_grid.addWidget(viewer_stats)
        
        # Engagement stats
        engagement_stats = QGroupBox("Engagement")
        engagement_stats_layout = QFormLayout(engagement_stats)
        
        self.messages_label = QLabel("0")
        self.messages_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        engagement_stats_layout.addRow("Chat Messages:", self.messages_label)
        
        self.new_followers_label = QLabel("0")
        self.new_followers_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        engagement_stats_layout.addRow("New Followers:", self.new_followers_label)
        
        self.new_subs_label = QLabel("0")
        self.new_subs_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        engagement_stats_layout.addRow("New Subscribers:", self.new_subs_label)
        
        self.bits_label = QLabel("0")
        self.bits_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        engagement_stats_layout.addRow("Bits Received:", self.bits_label)
        
        stats_grid.addWidget(engagement_stats)
        
        status_layout.addLayout(stats_grid)
        
        layout.addWidget(status_container)
        
        # Top viewers section
        viewer_lists_section = QHBoxLayout()
        
        # Top chatters
        top_chatters_container = QGroupBox("Top Chatters")
        top_chatters_layout = QVBoxLayout(top_chatters_container)
        
        self.top_chatters_table = QTableWidget(0, 2)
        self.top_chatters_table.setHorizontalHeaderLabels(["Username", "Messages"])
        self.top_chatters_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.top_chatters_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        top_chatters_layout.addWidget(self.top_chatters_table)
        viewer_lists_section.addWidget(top_chatters_container)
        
        # Top donors
        top_donors_container = QGroupBox("Top Donors")
        top_donors_layout = QVBoxLayout(top_donors_container)
        
        self.top_donors_table = QTableWidget(0, 2)
        self.top_donors_table.setHorizontalHeaderLabels(["Username", "Bits"])
        self.top_donors_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.top_donors_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        top_donors_layout.addWidget(self.top_donors_table)
        viewer_lists_section.addWidget(top_donors_container)
        
        # Most loyal viewers
        loyal_viewers_container = QGroupBox("Most Loyal Viewers")
        loyal_viewers_layout = QVBoxLayout(loyal_viewers_container)
        
        self.loyal_viewers_table = QTableWidget(0, 2)
        self.loyal_viewers_table.setHorizontalHeaderLabels(["Username", "Watch Time"])
        self.loyal_viewers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.loyal_viewers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        loyal_viewers_layout.addWidget(self.loyal_viewers_table)
        viewer_lists_section.addWidget(loyal_viewers_container)
        
        layout.addLayout(viewer_lists_section)
        
        # Add refresh button at the bottom
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh Now")
        refresh_btn.clicked.connect(self.refresh_stats)
        refresh_layout.addWidget(refresh_btn)
        
        layout.addLayout(refresh_layout)
    
    def init_viewers_tab(self):
        """Initialize the viewers tab."""
        layout = QVBoxLayout(self.viewers_widget)
        
        # Search and filter controls
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Search:"))
        self.viewer_search = QLineEdit()
        self.viewer_search.setPlaceholderText("Search by username...")
        self.viewer_search.textChanged.connect(self.filter_viewers)
        filter_layout.addWidget(self.viewer_search)
        
        filter_layout.addWidget(QLabel("Filter:"))
        self.viewer_filter = QComboBox()
        self.viewer_filter.addItems(["All Viewers", "Moderators", "VIPs", "Subscribers", "Followers"])
        self.viewer_filter.currentIndexChanged.connect(self.filter_viewers)
        filter_layout.addWidget(self.viewer_filter)
        
        layout.addLayout(filter_layout)
        
        # Viewers table
        self.viewers_table = QTableWidget(0, 8)
        self.viewers_table.setHorizontalHeaderLabels([
            "Username", "Role", "Messages", "Watch Time", "Streams Watched", 
            "Bits Donated", "First Seen", "Last Seen"
        ])
        self.viewers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.viewers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.viewers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.viewers_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.viewers_table)
        
        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        
        refresh_viewers_btn = QPushButton("Refresh Viewers")
        refresh_viewers_btn.clicked.connect(self.refresh_viewers)
        controls_layout.addWidget(refresh_viewers_btn)
        
        layout.addLayout(controls_layout)
    
    def init_analytics_tab(self):
        """Initialize the analytics tab."""
        layout = QVBoxLayout(self.analytics_widget)
        
        # Time period selection
        time_layout = QHBoxLayout()
        
        time_layout.addWidget(QLabel("Time Period:"))
        self.time_period = QComboBox()
        self.time_period.addItems([
            "All Time", "Last 7 Days", "Last 30 Days", "This Month", "Custom"
        ])
        self.time_period.currentIndexChanged.connect(self.update_analytics)
        time_layout.addWidget(self.time_period)
        
        time_layout.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(datetime.datetime.now().date().replace(day=1))
        self.from_date.setEnabled(False)
        time_layout.addWidget(self.from_date)
        
        time_layout.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(datetime.datetime.now().date())
        self.to_date.setEnabled(False)
        time_layout.addWidget(self.to_date)
        
        time_layout.addStretch()
        
        layout.addLayout(time_layout)
        
        # Stats cards
        cards_layout = QHBoxLayout()
        
        # Total viewers card
        total_viewers_card = QGroupBox("Total Viewers")
        total_viewers_layout = QVBoxLayout(total_viewers_card)
        self.total_viewers_count = QLabel("0")
        self.total_viewers_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_viewers_count.setStyleSheet("font-size: 24px; font-weight: bold;")
        total_viewers_layout.addWidget(self.total_viewers_count)
        cards_layout.addWidget(total_viewers_card)
        
        # Total messages card
        total_messages_card = QGroupBox("Total Messages")
        total_messages_layout = QVBoxLayout(total_messages_card)
        self.total_messages_count = QLabel("0")
        self.total_messages_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_messages_count.setStyleSheet("font-size: 24px; font-weight: bold;")
        total_messages_layout.addWidget(self.total_messages_count)
        cards_layout.addWidget(total_messages_card)
        
        # New followers card
        followers_card = QGroupBox("New Followers")
        followers_layout = QVBoxLayout(followers_card)
        self.followers_count = QLabel("0")
        self.followers_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.followers_count.setStyleSheet("font-size: 24px; font-weight: bold;")
        followers_layout.addWidget(self.followers_count)
        cards_layout.addWidget(followers_card)
        
        # New subscribers card
        subscribers_card = QGroupBox("New Subscribers")
        subscribers_layout = QVBoxLayout(subscribers_card)
        self.subscribers_count = QLabel("0")
        self.subscribers_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subscribers_count.setStyleSheet("font-size: 24px; font-weight: bold;")
        subscribers_layout.addWidget(self.subscribers_count)
        cards_layout.addWidget(subscribers_card)
        
        # Total bits card
        bits_card = QGroupBox("Total Bits")
        bits_layout = QVBoxLayout(bits_card)
        self.bits_count = QLabel("0")
        self.bits_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bits_count.setStyleSheet("font-size: 24px; font-weight: bold;")
        bits_layout.addWidget(self.bits_count)
        cards_layout.addWidget(bits_card)
        
        layout.addLayout(cards_layout)
        
        # Placeholder for future charts/graphs
        charts_section = QGroupBox("Stream Analytics")
        charts_layout = QVBoxLayout(charts_section)
        
        placeholder = QLabel("Detailed analytics charts will be available in a future update.")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #888888; padding: 40px;")
        charts_layout.addWidget(placeholder)
        
        layout.addWidget(charts_section)
        
        # Add spacer
        layout.addStretch()
    
    def init_sessions_tab(self):
        """Initialize the sessions tab."""
        layout = QVBoxLayout(self.sessions_widget)
        
        # Sessions table
        self.sessions_table = QTableWidget(0, 7)
        self.sessions_table.setHorizontalHeaderLabels([
            "Date", "Title", "Game", "Duration", "Peak Viewers", 
            "Unique Viewers", "Messages"
        ])
        self.sessions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.sessions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.sessions_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.sessions_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.sessions_table)
        
        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        
        refresh_sessions_btn = QPushButton("Refresh Sessions")
        refresh_sessions_btn.clicked.connect(self.refresh_sessions)
        controls_layout.addWidget(refresh_sessions_btn)
        
        layout.addLayout(controls_layout)
    
    def showEvent(self, event):
        """Handle show event.
        
        Args:
            event: Show event
        """
        super().showEvent(event)
        
        # Start the tracker if not already running
        if self.stats_tracker:
            asyncio.create_task(self.start_tracker())
        
        # Refresh immediately when tab is shown
        self.refresh_stats()
    
    def hideEvent(self, event):
        """Handle hide event.
        
        Args:
            event: Hide event
        """
        super().hideEvent(event)
    
    async def start_tracker(self):
        """Start the viewer stats tracker."""
        if self.stats_tracker:
            await self.stats_tracker.start()
    
    async def stop_tracker(self):
        """Stop the viewer stats tracker."""
        if self.stats_tracker:
            await self.stats_tracker.stop()
    
    @pyqtSlot()
    def start_tracking(self):
        """Start manual stream tracking."""
        if self.stats_tracker:
            asyncio.create_task(self.stats_tracker.start_stream_tracking())
            self.start_tracking_btn.setEnabled(False)
            self.stop_tracking_btn.setEnabled(True)
            self.refresh_stats()
    
    @pyqtSlot()
    def stop_tracking(self):
        """Stop manual stream tracking."""
        if self.stats_tracker:
            asyncio.create_task(self.stats_tracker.end_stream_tracking())
            self.start_tracking_btn.setEnabled(True)
            self.stop_tracking_btn.setEnabled(False)
            self.refresh_stats()
    
    @pyqtSlot()
    def refresh_stats(self):
        """Refresh all statistics."""
        if self.stats_tracker:
            asyncio.create_task(self.load_current_stats())
            asyncio.create_task(self.load_top_viewers())
    
    @pyqtSlot()
    def refresh_viewers(self):
        """Refresh viewers list."""
        # TODO: Implement viewers list refresh
        pass
    
    @pyqtSlot()
    def refresh_sessions(self):
        """Refresh sessions list."""
        if self.stats_tracker:
            asyncio.create_task(self.load_recent_sessions())
    
    @pyqtSlot(str)
    def filter_viewers(self):
        """Filter viewers based on search text and filter selection."""
        # TODO: Implement viewer filtering
        pass
    
    @pyqtSlot(int)
    def update_analytics(self):
        """Update analytics based on time period selection."""
        # Enable/disable date selection for custom time period
        enable_custom = self.time_period.currentText() == "Custom"
        self.from_date.setEnabled(enable_custom)
        self.to_date.setEnabled(enable_custom)
        
        # TODO: Update analytics data based on selected time period
    
    @pyqtSlot(dict)
    def update_dashboard(self, stats: Dict[str, Any]):
        """Update dashboard with current stats.
        
        Args:
            stats: Current statistics
        """
        is_live = stats.get('is_live', False)
        
        # Update live status
        if is_live:
            self.live_status.setText("LIVE")
            self.live_status.setStyleSheet("font-size: 18px; font-weight: bold; color: #FF0000;")
            self.start_tracking_btn.setEnabled(False)
            self.stop_tracking_btn.setEnabled(True)
        else:
            self.live_status.setText("OFFLINE")
            self.live_status.setStyleSheet("font-size: 18px; font-weight: bold; color: #888888;")
            self.start_tracking_btn.setEnabled(True)
            self.stop_tracking_btn.setEnabled(False)
        
        # Format duration
        duration = stats.get('duration', 0)
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours:02}:{minutes:02}:{seconds:02}"
        self.stream_duration.setText(f"Duration: {duration_str}")
        
        # Update viewer stats
        self.active_viewers_label.setText(str(stats.get('active_viewers', 0)))
        self.total_viewers_label.setText(str(stats.get('total_unique_viewers', 0)))
        self.peak_viewers_label.setText(str(stats.get('peak_viewers', 0)))
        
        # Update engagement stats
        self.messages_label.setText(str(stats.get('message_count', 0)))
        self.new_followers_label.setText(str(stats.get('new_followers', 0)))
        self.new_subs_label.setText(str(stats.get('new_subscribers', 0)))
        self.bits_label.setText(str(stats.get('bits_received', 0)))
    
    async def load_current_stats(self):
        """Load current stats from the tracker."""
        if self.stats_tracker:
            stats = await self.stats_tracker.get_current_stats()
            self.stats_updated.emit(stats)
    
    async def load_top_viewers(self):
        """Load top viewers lists."""
        if not self.stats_tracker:
            return
        
        # Load top chatters
        chatters = await self.stats_tracker.get_top_chatters(10)
        self.top_chatters_table.setRowCount(len(chatters))
        for i, chatter in enumerate(chatters):
            self.top_chatters_table.setItem(i, 0, QTableWidgetItem(chatter['username']))
            self.top_chatters_table.setItem(i, 1, QTableWidgetItem(str(chatter['message_count'])))
        
        # Load top donors
        donors = await self.stats_tracker.get_top_donors(10)
        self.top_donors_table.setRowCount(len(donors))
        for i, donor in enumerate(donors):
            self.top_donors_table.setItem(i, 0, QTableWidgetItem(donor['username']))
            self.top_donors_table.setItem(i, 1, QTableWidgetItem(str(donor['bits_donated'])))
        
        # Load most loyal viewers
        loyal = await self.stats_tracker.get_most_loyal_viewers(10)
        self.loyal_viewers_table.setRowCount(len(loyal))
        for i, viewer in enumerate(loyal):
            self.loyal_viewers_table.setItem(i, 0, QTableWidgetItem(viewer['username']))
            # Convert seconds to hours and minutes
            hours = viewer['watch_time'] // 3600
            minutes = (viewer['watch_time'] % 3600) // 60
            watch_time = f"{hours}h {minutes}m"
            self.loyal_viewers_table.setItem(i, 1, QTableWidgetItem(watch_time))
    
    async def load_recent_sessions(self):
        """Load recent stream sessions."""
        if not self.stats_tracker:
            return
        
        sessions = await self.stats_tracker.get_recent_sessions(10)
        self.sessions_table.setRowCount(len(sessions))
        
        for i, session in enumerate(sessions):
            # Format date
            if session.get('started_at'):
                started = datetime.datetime.fromisoformat(session['started_at'])
                date_str = started.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = "Unknown"
                
            self.sessions_table.setItem(i, 0, QTableWidgetItem(date_str))
            self.sessions_table.setItem(i, 1, QTableWidgetItem(session.get('title', 'Untitled')))
            self.sessions_table.setItem(i, 2, QTableWidgetItem(session.get('game_name', 'Unknown')))
            
            # Format duration
            duration = session.get('duration', 0)
            if duration:
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                duration_str = f"{hours}h {minutes}m"
            else:
                duration_str = "Unknown"
            self.sessions_table.setItem(i, 3, QTableWidgetItem(duration_str))
            
            # Stats
            self.sessions_table.setItem(i, 4, QTableWidgetItem(str(session.get('peak_viewers', 0))))
            self.sessions_table.setItem(i, 5, QTableWidgetItem(str(session.get('unique_viewers', 0))))
            self.sessions_table.setItem(i, 6, QTableWidgetItem(str(session.get('messages_count', 0))))
    
    def closeEvent(self, event):
        """Handle close event.
        
        Args:
            event: Close event
        """
        # Stop refresh timer
        self.refresh_timer.stop()
        
        # Stop tracker
        if self.stats_tracker:
            asyncio.create_task(self.stop_tracker())
        
        event.accept() 