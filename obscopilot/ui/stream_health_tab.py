"""
Stream Health Tab for OBSCopilot.

This module provides a tab for monitoring stream health metrics.
"""

import asyncio
import datetime
import logging
from typing import Dict, List, Optional, Any

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QTabWidget, QGridLayout, QFrame, QScrollArea,
    QSplitter, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

from obscopilot.core.config import Config
from obscopilot.core.events import Event, EventType, event_bus
from obscopilot.obs.client import OBSClient
from obscopilot.obs.stream_health import StreamHealthMonitor
from obscopilot.storage.database import Database

logger = logging.getLogger(__name__)


class StreamHealthTab(QWidget):
    """Stream Health Tab for the main UI."""
    
    # Signal for async updates
    update_signal = pyqtSignal(dict)
    warning_signal = pyqtSignal(dict)
    
    def __init__(self, database: Database, obs_client: OBSClient, config: Config):
        """Initialize the stream health tab.
        
        Args:
            database: Database instance
            obs_client: OBS client instance
            config: Config instance
        """
        super().__init__()
        
        self.database = database
        self.obs_client = obs_client
        self.config = config
        self.health_monitor = StreamHealthMonitor(obs_client, database, config)
        
        # Chart data
        self.cpu_series = QLineSeries()
        self.dropped_frames_series = QLineSeries()
        self.fps_series = QLineSeries()
        self.bitrate_series = QLineSeries()
        
        # Data points counter for x-axis
        self.data_points = 0
        self.max_data_points = 60  # Show up to 60 data points (15 minutes with 15s interval)
        
        # Connect signals
        self.update_signal.connect(self.update_ui)
        self.warning_signal.connect(self.show_warning)
        
        # Initialize UI
        self.init_ui()
        
        # Register event handlers
        event_bus.subscribe(EventType.STREAM_HEALTH_UPDATED, self.handle_health_update)
        event_bus.subscribe(EventType.STREAM_HEALTH_WARNING, self.handle_health_warning)
    
    def init_ui(self):
        """Initialize the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Status header
        status_layout = QHBoxLayout()
        
        # Stream status indicator
        self.status_frame = QFrame()
        self.status_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.status_frame.setFixedSize(16, 16)
        self.status_frame.setStyleSheet("background-color: gray;")
        
        self.status_label = QLabel("Not streaming")
        self.status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        status_layout.addWidget(self.status_frame)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        # Stream duration
        self.duration_label = QLabel("Duration: 00:00:00")
        status_layout.addWidget(self.duration_label)
        
        main_layout.addLayout(status_layout)
        
        # Splitter for top metrics and charts
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(1)
        
        # Top metrics
        metrics_widget = QWidget()
        metrics_layout = QGridLayout(metrics_widget)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        
        # CPU Usage
        cpu_group = QGroupBox("CPU Usage")
        cpu_layout = QVBoxLayout(cpu_group)
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setValue(0)
        self.cpu_bar.setTextVisible(True)
        self.cpu_bar.setFormat("%v%")
        cpu_layout.addWidget(self.cpu_bar)
        
        # FPS
        fps_group = QGroupBox("FPS")
        fps_layout = QVBoxLayout(fps_group)
        self.fps_label = QLabel("0")
        self.fps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fps_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        fps_layout.addWidget(self.fps_label)
        
        # Dropped Frames
        drop_group = QGroupBox("Dropped Frames")
        drop_layout = QVBoxLayout(drop_group)
        self.drop_bar = QProgressBar()
        self.drop_bar.setRange(0, 100)
        self.drop_bar.setValue(0)
        self.drop_bar.setTextVisible(True)
        self.drop_bar.setFormat("%v%")
        drop_layout.addWidget(self.drop_bar)
        
        # Bitrate
        bitrate_group = QGroupBox("Bitrate")
        bitrate_layout = QVBoxLayout(bitrate_group)
        self.bitrate_label = QLabel("0 Kbps")
        self.bitrate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bitrate_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        bitrate_layout.addWidget(self.bitrate_label)
        
        # Add metrics to grid
        metrics_layout.addWidget(cpu_group, 0, 0)
        metrics_layout.addWidget(fps_group, 0, 1)
        metrics_layout.addWidget(drop_group, 1, 0)
        metrics_layout.addWidget(bitrate_group, 1, 1)
        
        # Bottom charts section with tabs
        charts_widget = QWidget()
        charts_layout = QVBoxLayout(charts_widget)
        
        # Tab widget for charts
        charts_tabs = QTabWidget()
        
        # CPU Chart
        cpu_chart = QChart()
        cpu_chart.setTitle("CPU Usage")
        cpu_chart.legend().hide()
        cpu_chart.addSeries(self.cpu_series)
        
        cpu_axis_x = QValueAxis()
        cpu_axis_x.setRange(0, self.max_data_points)
        cpu_axis_x.setLabelFormat("%d")
        cpu_axis_x.setTickCount(7)
        cpu_axis_x.setTitleText("Time (last 15 minutes)")
        
        cpu_axis_y = QValueAxis()
        cpu_axis_y.setRange(0, 100)
        cpu_axis_y.setLabelFormat("%d%%")
        cpu_axis_y.setTickCount(6)
        cpu_axis_y.setTitleText("CPU Usage")
        
        cpu_chart.addAxis(cpu_axis_x, Qt.AlignmentFlag.AlignBottom)
        cpu_chart.addAxis(cpu_axis_y, Qt.AlignmentFlag.AlignLeft)
        self.cpu_series.attachAxis(cpu_axis_x)
        self.cpu_series.attachAxis(cpu_axis_y)
        
        cpu_chart_view = QChartView(cpu_chart)
        cpu_chart_view.setRenderHint(cpu_chart_view.RenderHint.Antialiasing)
        charts_tabs.addTab(cpu_chart_view, "CPU Usage")
        
        # Dropped Frames Chart
        drop_chart = QChart()
        drop_chart.setTitle("Dropped Frames")
        drop_chart.legend().hide()
        drop_chart.addSeries(self.dropped_frames_series)
        
        drop_axis_x = QValueAxis()
        drop_axis_x.setRange(0, self.max_data_points)
        drop_axis_x.setLabelFormat("%d")
        drop_axis_x.setTickCount(7)
        drop_axis_x.setTitleText("Time (last 15 minutes)")
        
        drop_axis_y = QValueAxis()
        drop_axis_y.setRange(0, 10)  # 0-10%
        drop_axis_y.setLabelFormat("%.1f%%")
        drop_axis_y.setTickCount(6)
        drop_axis_y.setTitleText("Dropped Frames")
        
        drop_chart.addAxis(drop_axis_x, Qt.AlignmentFlag.AlignBottom)
        drop_chart.addAxis(drop_axis_y, Qt.AlignmentFlag.AlignLeft)
        self.dropped_frames_series.attachAxis(drop_axis_x)
        self.dropped_frames_series.attachAxis(drop_axis_y)
        
        drop_chart_view = QChartView(drop_chart)
        drop_chart_view.setRenderHint(drop_chart_view.RenderHint.Antialiasing)
        charts_tabs.addTab(drop_chart_view, "Dropped Frames")
        
        # FPS Chart
        fps_chart = QChart()
        fps_chart.setTitle("FPS")
        fps_chart.legend().hide()
        fps_chart.addSeries(self.fps_series)
        
        fps_axis_x = QValueAxis()
        fps_axis_x.setRange(0, self.max_data_points)
        fps_axis_x.setLabelFormat("%d")
        fps_axis_x.setTickCount(7)
        fps_axis_x.setTitleText("Time (last 15 minutes)")
        
        fps_axis_y = QValueAxis()
        fps_axis_y.setRange(0, 120)
        fps_axis_y.setLabelFormat("%d")
        fps_axis_y.setTickCount(7)
        fps_axis_y.setTitleText("FPS")
        
        fps_chart.addAxis(fps_axis_x, Qt.AlignmentFlag.AlignBottom)
        fps_chart.addAxis(fps_axis_y, Qt.AlignmentFlag.AlignLeft)
        self.fps_series.attachAxis(fps_axis_x)
        self.fps_series.attachAxis(fps_axis_y)
        
        fps_chart_view = QChartView(fps_chart)
        fps_chart_view.setRenderHint(fps_chart_view.RenderHint.Antialiasing)
        charts_tabs.addTab(fps_chart_view, "FPS")
        
        # Bitrate Chart
        bitrate_chart = QChart()
        bitrate_chart.setTitle("Bitrate")
        bitrate_chart.legend().hide()
        bitrate_chart.addSeries(self.bitrate_series)
        
        bitrate_axis_x = QValueAxis()
        bitrate_axis_x.setRange(0, self.max_data_points)
        bitrate_axis_x.setLabelFormat("%d")
        bitrate_axis_x.setTickCount(7)
        bitrate_axis_x.setTitleText("Time (last 15 minutes)")
        
        bitrate_axis_y = QValueAxis()
        bitrate_axis_y.setRange(0, 8000)  # 0-8000 Kbps
        bitrate_axis_y.setLabelFormat("%d")
        bitrate_axis_y.setTickCount(9)
        bitrate_axis_y.setTitleText("Bitrate (Kbps)")
        
        bitrate_chart.addAxis(bitrate_axis_x, Qt.AlignmentFlag.AlignBottom)
        bitrate_chart.addAxis(bitrate_axis_y, Qt.AlignmentFlag.AlignLeft)
        self.bitrate_series.attachAxis(bitrate_axis_x)
        self.bitrate_series.attachAxis(bitrate_axis_y)
        
        bitrate_chart_view = QChartView(bitrate_chart)
        bitrate_chart_view.setRenderHint(bitrate_chart_view.RenderHint.Antialiasing)
        charts_tabs.addTab(bitrate_chart_view, "Bitrate")
        
        charts_layout.addWidget(charts_tabs)
        
        # Add widgets to splitter
        splitter.addWidget(metrics_widget)
        splitter.addWidget(charts_widget)
        splitter.setSizes([100, 400])  # Initial sizes
        
        main_layout.addWidget(splitter)
        
        # Warning section
        self.warning_group = QGroupBox("Warnings")
        warning_layout = QVBoxLayout(self.warning_group)
        
        self.warning_table = QTableWidget(0, 3)  # Columns: Time, Type, Message
        self.warning_table.setHorizontalHeaderLabels(["Time", "Type", "Message"])
        self.warning_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.warning_table.horizontalHeader().setStretchLastSection(True)
        
        warning_layout.addWidget(self.warning_table)
        
        main_layout.addWidget(self.warning_group)
    
    def handle_health_update(self, event: Event) -> None:
        """Handle stream health update event.
        
        Args:
            event: Stream health update event
        """
        if not event.data:
            return
        
        # Emit signal to update UI
        self.update_signal.emit(event.data)
    
    def handle_health_warning(self, event: Event) -> None:
        """Handle stream health warning event.
        
        Args:
            event: Stream health warning event
        """
        if not event.data:
            return
        
        # Emit signal to show warning
        self.warning_signal.emit(event.data)
    
    def update_ui(self, data: Dict[str, Any]) -> None:
        """Update UI with new health data.
        
        Args:
            data: Stream health data
        """
        health_data = data.get('health_data', {})
        if not health_data:
            return
        
        # Update stream status
        is_streaming = health_data.get('raw_stream_status', {}).get('active', False)
        if is_streaming:
            self.status_frame.setStyleSheet("background-color: green;")
            self.status_label.setText("Streaming")
        else:
            self.status_frame.setStyleSheet("background-color: gray;")
            self.status_label.setText("Not streaming")
        
        # Update duration
        duration = health_data.get('stream_duration', 0)
        hours, remainder = divmod(int(duration), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.duration_label.setText(f"Duration: {hours:02}:{minutes:02}:{seconds:02}")
        
        # Update metrics
        cpu_usage = health_data.get('cpu_usage', 0)
        if cpu_usage is not None:
            self.cpu_bar.setValue(int(cpu_usage))
            
            # Set color based on value
            if cpu_usage >= self.health_monitor.cpu_critical_threshold:
                self.cpu_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
            elif cpu_usage >= self.health_monitor.cpu_warning_threshold:
                self.cpu_bar.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
            else:
                self.cpu_bar.setStyleSheet("QProgressBar::chunk { background-color: green; }")
        
        fps = health_data.get('fps', 0)
        if fps is not None:
            self.fps_label.setText(f"{fps:.1f}")
        
        drop_percentage = health_data.get('drop_percentage', 0)
        if drop_percentage is not None:
            self.drop_bar.setValue(int(drop_percentage))
            
            # Set color based on value
            if drop_percentage >= self.health_monitor.drop_critical_threshold:
                self.drop_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
            elif drop_percentage >= self.health_monitor.drop_warning_threshold:
                self.drop_bar.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
            else:
                self.drop_bar.setStyleSheet("QProgressBar::chunk { background-color: green; }")
        
        bitrate = health_data.get('kbits_per_sec', 0)
        if bitrate is not None:
            self.bitrate_label.setText(f"{bitrate:.0f} Kbps")
        
        # Update charts
        self.data_points += 1
        
        # Add data to series
        self.cpu_series.append(self.data_points, cpu_usage or 0)
        self.dropped_frames_series.append(self.data_points, drop_percentage or 0)
        self.fps_series.append(self.data_points, fps or 0)
        self.bitrate_series.append(self.data_points, bitrate or 0)
        
        # Keep only the last 60 points
        if self.data_points > self.max_data_points:
            # Update x-axis range to "scroll" the chart
            for chart in [self.cpu_series, self.dropped_frames_series, self.fps_series, self.bitrate_series]:
                axis_x = chart.attachedAxes()[0]
                axis_x.setRange(self.data_points - self.max_data_points, self.data_points)
    
    def show_warning(self, data: Dict[str, Any]) -> None:
        """Show a new warning in the warning table.
        
        Args:
            data: Warning data
        """
        warning = data.get('warning', {})
        if not warning:
            return
        
        # Add new row to warning table
        row = self.warning_table.rowCount()
        self.warning_table.insertRow(row)
        
        # Current time
        time_item = QTableWidgetItem(datetime.datetime.now().strftime("%H:%M:%S"))
        self.warning_table.setItem(row, 0, time_item)
        
        # Warning type
        warning_type = warning.get('type', 'unknown').replace('_', ' ').title()
        type_item = QTableWidgetItem(warning_type)
        self.warning_table.setItem(row, 1, type_item)
        
        # Warning message
        message = warning.get('message', 'Unknown warning')
        message_item = QTableWidgetItem(message)
        self.warning_table.setItem(row, 2, message_item)
        
        # Color based on severity
        level = warning.get('level', 'warning')
        if level == 'critical':
            for col in range(3):
                self.warning_table.item(row, col).setBackground(QColor(255, 200, 200))  # Light red
        else:
            for col in range(3):
                self.warning_table.item(row, col).setBackground(QColor(255, 240, 200))  # Light yellow
        
        # Scroll to the new row
        self.warning_table.scrollToBottom()
    
    def cleanup(self) -> None:
        """Clean up resources."""
        # Unregister event handlers
        event_bus.unsubscribe(EventType.STREAM_HEALTH_UPDATED, self.handle_health_update)
        event_bus.unsubscribe(EventType.STREAM_HEALTH_WARNING, self.handle_health_warning) 