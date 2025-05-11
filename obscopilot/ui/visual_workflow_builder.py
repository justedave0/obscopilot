"""
Visual Workflow Builder for OBSCopilot.

This module provides a drag-and-drop interface for creating and editing workflows visually.
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple, Set

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsPathItem,
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QMenu, QAction, QDialog, QFrame,
    QToolBar, QComboBox, QListWidget, QListWidgetItem, QSplitter,
    QToolButton, QScrollArea, QSizePolicy, QGraphicsProxyWidget,
    QMessageBox, QGraphicsSceneMouseEvent, QGraphicsSceneDragDropEvent
)
from PyQt6.QtCore import (
    Qt, QPointF, QRectF, QSizeF, QLineF, pyqtSignal, 
    QMimeData, QDataStream, QByteArray, QIODevice
)
from PyQt6.QtGui import (
    QPen, QBrush, QColor, QPainterPath, QDrag, QPolygonF,
    QPainter, QPixmap, QFont, QFontMetrics, QTransform,
    QPainterPathStroker, QGradient, QLinearGradient
)

from obscopilot.workflows.models import (
    Workflow, WorkflowNode, WorkflowAction, WorkflowTrigger,
    ActionType, TriggerType
)
from obscopilot.workflows.registry import TRIGGER_REGISTRY, ACTION_REGISTRY

logger = logging.getLogger(__name__)


class NodeType:
    """Node types in the workflow graph."""
    
    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    START = "start"
    END = "end"


class ConnectionPoint(QGraphicsEllipseItem):
    """Connection point for workflow nodes."""
    
    SIZE = 10
    
    def __init__(self, parent=None, is_input=False):
        """Initialize the connection point.
        
        Args:
            parent: Parent item
            is_input: True if this is an input port, False for output
        """
        super().__init__(-self.SIZE/2, -self.SIZE/2, self.SIZE, self.SIZE, parent)
        self.is_input = is_input
        self.node = parent
        self.connection = None
        self.setAcceptDrops(True)
        
        # Set appearance
        if is_input:
            self.setBrush(QBrush(QColor("#6C8EBF")))  # Blue for inputs
        else:
            self.setBrush(QBrush(QColor("#D79B00")))  # Orange for outputs
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setZValue(2)
        
    def connect_to(self, other_point):
        """Connect this point to another connection point.
        
        Args:
            other_point: The connection point to connect to
            
        Returns:
            The created connection
        """
        if self.is_input == other_point.is_input:
            return None  # Can't connect inputs to inputs or outputs to outputs
            
        if self.is_input:
            source, target = other_point, self
        else:
            source, target = self, other_point
            
        # Create connection
        connection = Connection(source, target)
        source.connection = connection
        target.connection = connection
        
        # Add to scene
        if self.scene():
            self.scene().addItem(connection)
            
        return connection
        
    def mousePressEvent(self, event):
        """Handle mouse press events.
        
        Args:
            event: Mouse event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Start drag
            drag = QDrag(self.scene().views()[0])
            mime_data = QMimeData()
            
            # Store connection point info
            connection_data = QByteArray()
            stream = QDataStream(connection_data, QIODevice.OpenModeFlag.WriteOnly)
            stream.writeQString("connection_point")
            stream.writeBool(self.is_input)
            stream.writeQString(self.node.node_id)
            
            mime_data.setData("application/x-connection-point", connection_data)
            drag.setMimeData(mime_data)
            
            # Create pixmap for drag
            pixmap = QPixmap(self.SIZE*2, self.SIZE*2)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(self.brush())
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(self.SIZE/2, self.SIZE/2, self.SIZE, self.SIZE)
            painter.end()
            drag.setPixmap(pixmap)
            
            drag.exec()
            event.accept()
        else:
            super().mousePressEvent(event)
            
    def dragEnterEvent(self, event):
        """Handle drag enter events.
        
        Args:
            event: Drag enter event
        """
        if event.mimeData().hasFormat("application/x-connection-point"):
            mime_data = event.mimeData()
            connection_data = mime_data.data("application/x-connection-point")
            stream = QDataStream(connection_data, QIODevice.OpenModeFlag.ReadOnly)
            
            data_type = stream.readQString()
            is_input = stream.readBool()
            node_id = stream.readQString()
            
            # Only accept if connecting compatible ports
            if data_type == "connection_point" and is_input != self.is_input and node_id != self.node.node_id:
                event.acceptProposedAction()
                return
                
        event.ignore()
        
    def dropEvent(self, event):
        """Handle drop events.
        
        Args:
            event: Drop event
        """
        mime_data = event.mimeData()
        
        if mime_data.hasFormat("application/x-connection-point"):
            connection_data = mime_data.data("application/x-connection-point")
            stream = QDataStream(connection_data, QIODevice.OpenModeFlag.ReadOnly)
            
            data_type = stream.readQString()
            is_input = stream.readBool()
            node_id = stream.readQString()
            
            if data_type == "connection_point" and is_input != self.is_input:
                # Find the other connection point
                for item in self.scene().items():
                    if (isinstance(item, ConnectionPoint) and 
                        item.node.node_id == node_id and 
                        item.is_input == is_input):
                        # Connect the points
                        self.connect_to(item)
                        event.acceptProposedAction()
                        
                        # Update the workflow model
                        builder = self.scene().parent()
                        if builder:
                            builder.update_workflow_connections()
                        return
                        
        event.ignore()


class Connection(QGraphicsPathItem):
    """Connection between two nodes in the workflow."""
    
    def __init__(self, source: ConnectionPoint, target: ConnectionPoint):
        """Initialize the connection.
        
        Args:
            source: Source connection point
            target: Target connection point
        """
        super().__init__()
        
        self.source = source
        self.target = target
        
        # Set appearance
        self.setPen(QPen(QColor("#828282"), 2, Qt.PenStyle.SolidLine))
        self.setZValue(0)
        
        # Update path
        self.update_path()
        
    def update_path(self):
        """Update the connection path based on current positions."""
        if not self.source or not self.target:
            return
            
        # Get positions in scene coordinates
        source_pos = self.source.scenePos()
        target_pos = self.target.scenePos()
        
        # Create path
        path = QPainterPath()
        path.moveTo(source_pos)
        
        # Calculate control points for a quadratic bezier curve
        control_x = (source_pos.x() + target_pos.x()) / 2
        control_y1 = source_pos.y()
        control_y2 = target_pos.y()
        
        path.cubicTo(
            QPointF(control_x, control_y1),
            QPointF(control_x, control_y2),
            target_pos
        )
        
        self.setPath(path)
        
    def paint(self, painter, option, widget):
        """Paint the connection with an arrowhead.
        
        Args:
            painter: QPainter
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # Update path
        self.update_path()
        
        # Draw path
        painter.setPen(self.pen())
        painter.drawPath(self.path())
        
        # Draw arrowhead
        if self.source and self.target:
            # Get positions
            source_pos = self.source.scenePos()
            target_pos = self.target.scenePos()
            
            # Calculate direction vector
            dx = target_pos.x() - source_pos.x()
            dy = target_pos.y() - source_pos.y()
            length = (dx**2 + dy**2)**0.5
            
            if length > 0:
                dx, dy = dx/length, dy/length
                
                # Create arrow at target
                arrow_size = 10
                arrow = QPolygonF()
                
                # Calculate arrow points
                arrow.append(target_pos)
                arrow.append(QPointF(
                    target_pos.x() - arrow_size * dx - arrow_size * dy * 0.5,
                    target_pos.y() - arrow_size * dy + arrow_size * dx * 0.5
                ))
                arrow.append(QPointF(
                    target_pos.x() - arrow_size * dx + arrow_size * dy * 0.5,
                    target_pos.y() - arrow_size * dy - arrow_size * dx * 0.5
                ))
                
                # Draw arrow
                painter.setBrush(QBrush(self.pen().color()))
                painter.drawPolygon(arrow)


class WorkflowNodeItem(QGraphicsRectItem):
    """Visual representation of a workflow node."""
    
    # Node dimensions
    WIDTH = 180
    HEIGHT = 80
    
    def __init__(self, node_id: str, node_type: str, title: str, parent=None):
        """Initialize the workflow node item.
        
        Args:
            node_id: Node identifier
            node_type: Type of node
            title: Node title
            parent: Parent item
        """
        super().__init__(0, 0, self.WIDTH, self.HEIGHT, parent)
        
        self.node_id = node_id
        self.node_type = node_type
        self.title = title
        self.config = {}
        self.input_points = []
        self.output_points = []
        
        # Set up node appearance
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable | 
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        
        # Visual setup
        self._init_ui()
        
        # Add standard ports
        self.add_input_point()
        self.add_output_point()
        
    def _init_ui(self):
        """Initialize UI components."""
        # Set appearance based on node type
        if self.node_type == NodeType.TRIGGER:
            color = QColor("#B85450")  # Red
        elif self.node_type == NodeType.ACTION:
            color = QColor("#6C8EBF")  # Blue
        elif self.node_type == NodeType.CONDITION:
            color = QColor("#D79B00")  # Orange
        elif self.node_type == NodeType.START:
            color = QColor("#82B366")  # Green
        elif self.node_type == NodeType.END:
            color = QColor("#9673A6")  # Purple
        else:
            color = QColor("#666666")  # Gray
            
        # Create gradient
        gradient = QLinearGradient(0, 0, 0, self.HEIGHT)
        gradient.setColorAt(0, color.lighter(120))
        gradient.setColorAt(1, color)
        
        self.setBrush(QBrush(gradient))
        self.setPen(QPen(color.darker(120), 2))
        
        # Add text items
        self.title_item = QGraphicsTextItem(self.title, self)
        self.title_item.setPos(10, 5)
        self.title_item.setDefaultTextColor(Qt.GlobalColor.white)
        
        # Set font
        font = QFont("Arial", 10, QFont.Weight.Bold)
        self.title_item.setFont(font)
        
        # Set text width to fit node
        document = self.title_item.document()
        document.setTextWidth(self.WIDTH - 20)
        
    def add_input_point(self, y_pos=None):
        """Add an input connection point to the node.
        
        Args:
            y_pos: Y position for the point (None for automatic)
            
        Returns:
            The created connection point
        """
        if y_pos is None:
            # Place at middle left if there are no input points yet,
            # otherwise evenly distribute
            if not self.input_points:
                y_pos = self.HEIGHT / 2
            else:
                y_pos = self.HEIGHT / (len(self.input_points) + 2) * (len(self.input_points) + 1)
        
        point = ConnectionPoint(self, is_input=True)
        point.setPos(0, y_pos)
        self.input_points.append(point)
        return point
        
    def add_output_point(self, y_pos=None):
        """Add an output connection point to the node.
        
        Args:
            y_pos: Y position for the point (None for automatic)
            
        Returns:
            The created connection point
        """
        if y_pos is None:
            # Place at middle right if there are no output points yet,
            # otherwise evenly distribute
            if not self.output_points:
                y_pos = self.HEIGHT / 2
            else:
                y_pos = self.HEIGHT / (len(self.output_points) + 2) * (len(self.output_points) + 1)
        
        point = ConnectionPoint(self, is_input=False)
        point.setPos(self.WIDTH, y_pos)
        self.output_points.append(point)
        return point
        
    def itemChange(self, change, value):
        """Handle changes to the item's properties.
        
        Args:
            change: The change type
            value: The new value
            
        Returns:
            The value to be used
        """
        # Update connection paths when node moves
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update all connections
            for point in self.input_points + self.output_points:
                if point.connection:
                    point.connection.update_path()
        
        return super().itemChange(change, value)
        
    def contextMenuEvent(self, event):
        """Handle context menu events.
        
        Args:
            event: Context menu event
        """
        menu = QMenu()
        
        # Add actions
        edit_action = menu.addAction("Edit Node")
        delete_action = menu.addAction("Delete Node")
        
        # Add port actions
        menu.addSeparator()
        add_input_action = menu.addAction("Add Input")
        add_output_action = menu.addAction("Add Output")
        
        # Show menu and handle selection
        action = menu.exec(event.screenPos())
        
        if action == edit_action:
            self._edit_node()
        elif action == delete_action:
            self._delete_node()
        elif action == add_input_action:
            self.add_input_point()
        elif action == add_output_action:
            self.add_output_point()
            
    def _edit_node(self):
        """Open the node editor dialog."""
        # TODO: Implement node editing
        pass
        
    def _delete_node(self):
        """Delete this node."""
        # Remove all connections
        for point in self.input_points + self.output_points:
            if point.connection:
                if point.is_input:
                    point.connection.source.connection = None
                else:
                    point.connection.target.connection = None
                    
                if point.connection.scene():
                    point.connection.scene().removeItem(point.connection)
                
        # Remove from scene
        if self.scene():
            self.scene().removeItem(self)
            
            # Update workflow model
            builder = self.scene().parent()
            if builder:
                builder.update_workflow_model()


class TriggerItem(WorkflowNodeItem):
    """Visual representation of a workflow trigger."""
    
    def __init__(self, trigger_id: str, trigger_type: TriggerType, name: str, parent=None):
        """Initialize the trigger item.
        
        Args:
            trigger_id: Trigger identifier
            trigger_type: Type of trigger
            name: Trigger name
            parent: Parent item
        """
        super().__init__(trigger_id, NodeType.TRIGGER, name, parent)
        self.trigger_type = trigger_type
        
        # Triggers only have outputs
        self.input_points = []
        
        # Update UI
        self._update_ui()
        
    def _update_ui(self):
        """Update UI components."""
        # Add type information
        type_str = str(self.trigger_type.value).replace('_', ' ').title()
        type_item = QGraphicsTextItem(type_str, self)
        type_item.setPos(10, 30)
        type_item.setDefaultTextColor(Qt.GlobalColor.white)
        
        # Set text width to fit node
        document = type_item.document()
        document.setTextWidth(self.WIDTH - 20)


class ActionItem(WorkflowNodeItem):
    """Visual representation of a workflow action."""
    
    def __init__(self, action_id: str, action_type: ActionType, name: str, parent=None):
        """Initialize the action item.
        
        Args:
            action_id: Action identifier
            action_type: Type of action
            name: Action name
            parent: Parent item
        """
        super().__init__(action_id, NodeType.ACTION, name, parent)
        self.action_type = action_type
        
        # Update UI
        self._update_ui()
        
    def _update_ui(self):
        """Update UI components."""
        # Add type information
        type_str = str(self.action_type.value).replace('_', ' ').title()
        type_item = QGraphicsTextItem(type_str, self)
        type_item.setPos(10, 30)
        type_item.setDefaultTextColor(Qt.GlobalColor.white)
        
        # Set text width to fit node
        document = type_item.document()
        document.setTextWidth(self.WIDTH - 20)


class VisualWorkflowScene(QGraphicsScene):
    """Graphics scene for the visual workflow editor."""
    
    def __init__(self, parent=None):
        """Initialize the workflow scene.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Set up scene properties
        self.setSceneRect(0, 0, 2000, 1500)
        
        # Draw grid
        self._draw_grid()
        
    def _draw_grid(self, grid_size=20):
        """Draw the background grid.
        
        Args:
            grid_size: Size of grid cells
        """
        # Draw light gray grid lines
        pen = QPen(QColor(80, 80, 80, 40), 1, Qt.PenStyle.SolidLine)
        
        # Draw vertical lines
        for x in range(0, int(self.width()), grid_size):
            self.addLine(x, 0, x, self.height(), pen)
            
        # Draw horizontal lines
        for y in range(0, int(self.height()), grid_size):
            self.addLine(0, y, self.width(), y, pen)
            
    def mousePressEvent(self, event):
        """Handle mouse press events.
        
        Args:
            event: Mouse event
        """
        super().mousePressEvent(event)
        
    def dragEnterEvent(self, event):
        """Handle drag enter events.
        
        Args:
            event: Drag enter event
        """
        if event.mimeData().hasFormat("application/x-workflow-node"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
            
    def dragMoveEvent(self, event):
        """Handle drag move events.
        
        Args:
            event: Drag move event
        """
        if event.mimeData().hasFormat("application/x-workflow-node"):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)
            
    def dropEvent(self, event):
        """Handle drop events.
        
        Args:
            event: Drop event
        """
        if event.mimeData().hasFormat("application/x-workflow-node"):
            mime_data = event.mimeData()
            node_data = mime_data.data("application/x-workflow-node")
            stream = QDataStream(node_data, QIODevice.OpenModeFlag.ReadOnly)
            
            # Read node data
            node_type = stream.readQString()
            item_type = stream.readQString()
            name = stream.readQString()
            
            # Create new UUID for the node
            node_id = str(uuid.uuid4())
            
            # Create appropriate node
            if node_type == NodeType.TRIGGER:
                trigger_type = TriggerType(item_type)
                node = TriggerItem(node_id, trigger_type, name)
            elif node_type == NodeType.ACTION:
                action_type = ActionType(item_type)
                node = ActionItem(node_id, action_type, name)
            else:
                return
                
            # Position at drop point
            node.setPos(event.scenePos() - QPointF(node.WIDTH/2, node.HEIGHT/2))
            
            # Add to scene
            self.addItem(node)
            
            # Update workflow model
            builder = self.parent()
            if builder:
                builder.update_workflow_model()
                
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class NodePaletteItem(QListWidgetItem):
    """List widget item for the node palette."""
    
    def __init__(self, node_type: str, item_type: str, name: str, parent=None):
        """Initialize the node palette item.
        
        Args:
            node_type: Type of node (trigger, action, etc.)
            item_type: Specific type of item
            name: Display name
            parent: Parent widget
        """
        super().__init__(name, parent)
        self.node_type = node_type
        self.item_type = item_type
        self.setToolTip(f"Drag to add {name} to workflow")
        
        
class NodePaletteWidget(QListWidget):
    """Palette of available nodes to add to the workflow."""
    
    def __init__(self, parent=None):
        """Initialize the node palette widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Enable drag
        self.setDragEnabled(True)
        
        # Populate with available node types
        self._populate_nodes()
        
    def _populate_nodes(self):
        """Populate the palette with available node types."""
        # Add triggers section header
        self.addItem("-- Triggers --")
        self.item(self.count() - 1).setFlags(Qt.ItemFlag.NoItemFlags)
        
        # Add available triggers
        for trigger_type, trigger_info in TRIGGER_REGISTRY.items():
            name = trigger_info["name"]
            item = NodePaletteItem(NodeType.TRIGGER, trigger_type.value, name)
            self.addItem(item)
            
        # Add actions section header
        self.addItem("-- Actions --")
        self.item(self.count() - 1).setFlags(Qt.ItemFlag.NoItemFlags)
        
        # Add available actions
        for action_type, action_info in ACTION_REGISTRY.items():
            name = action_info["name"]
            item = NodePaletteItem(NodeType.ACTION, action_type.value, name)
            self.addItem(item)
            
    def startDrag(self, supported_actions):
        """Handle drag start events.
        
        Args:
            supported_actions: Supported drag actions
        """
        item = self.currentItem()
        if not item or not isinstance(item, NodePaletteItem):
            return
            
        # Create drag
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Store node info
        node_data = QByteArray()
        stream = QDataStream(node_data, QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(item.node_type)
        stream.writeQString(item.item_type)
        stream.writeQString(item.text())
        
        mime_data.setData("application/x-workflow-node", node_data)
        drag.setMimeData(mime_data)
        
        # Create pixmap for drag
        pixmap = QPixmap(150, 50)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set color based on node type
        if item.node_type == NodeType.TRIGGER:
            color = QColor("#B85450")  # Red
        elif item.node_type == NodeType.ACTION:
            color = QColor("#6C8EBF")  # Blue
        else:
            color = QColor("#666666")  # Gray
            
        # Draw rounded rectangle
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(120), 2))
        painter.drawRoundedRect(0, 0, 150, 50, 10, 10)
        
        # Draw text
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(QRectF(5, 5, 140, 20), Qt.AlignmentFlag.AlignLeft, item.text())
        painter.setFont(QFont("Arial", 8))
        painter.drawText(QRectF(5, 25, 140, 20), Qt.AlignmentFlag.AlignLeft, item.item_type)
        
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPointF(pixmap.width()/2, pixmap.height()/2).toPoint())
        
        drag.exec(supported_actions)


class VisualWorkflowBuilder(QWidget):
    """Visual workflow builder widget."""
    
    workflow_updated = pyqtSignal(Workflow)
    
    def __init__(self, workflow: Optional[Workflow] = None, parent=None):
        """Initialize the visual workflow builder.
        
        Args:
            workflow: Initial workflow to edit (or None for a new workflow)
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Create new workflow if none provided
        self.workflow = workflow or Workflow(
            name="New Workflow",
            description="",
            triggers=[],
            nodes={}
        )
        
        # Initialize UI
        self._init_ui()
        
        # Load workflow if provided
        if workflow:
            self._load_workflow()
        
    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QToolBar()
        
        # Zoom controls
        zoom_in_btn = QToolButton()
        zoom_in_btn.setText("Zoom In")
        zoom_in_btn.clicked.connect(self._zoom_in)
        toolbar.addWidget(zoom_in_btn)
        
        zoom_out_btn = QToolButton()
        zoom_out_btn.setText("Zoom Out")
        zoom_out_btn.clicked.connect(self._zoom_out)
        toolbar.addWidget(zoom_out_btn)
        
        zoom_reset_btn = QToolButton()
        zoom_reset_btn.setText("Reset Zoom")
        zoom_reset_btn.clicked.connect(self._zoom_reset)
        toolbar.addWidget(zoom_reset_btn)
        
        toolbar.addSeparator()
        
        # Auto-layout button
        auto_layout_btn = QToolButton()
        auto_layout_btn.setText("Auto Layout")
        auto_layout_btn.clicked.connect(self._auto_layout)
        toolbar.addWidget(auto_layout_btn)
        
        layout.addWidget(toolbar)
        
        # Main container
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Node palette panel
        palette_panel = QWidget()
        palette_layout = QVBoxLayout(palette_panel)
        
        palette_label = QLabel("Node Palette")
        palette_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        palette_layout.addWidget(palette_label)
        
        self.node_palette = NodePaletteWidget()
        palette_layout.addWidget(self.node_palette)
        
        splitter.addWidget(palette_panel)
        
        # Graphics view panel
        view_panel = QWidget()
        view_layout = QVBoxLayout(view_panel)
        
        # Create scene
        self.scene = VisualWorkflowScene(self)
        
        # Create view
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setAcceptDrops(True)
        
        view_layout.addWidget(self.view)
        splitter.addWidget(view_panel)
        
        # Set initial sizes
        splitter.setSizes([200, 800])
        
        layout.addWidget(splitter)
        
    def _zoom_in(self):
        """Zoom in the view."""
        self.view.scale(1.2, 1.2)
        
    def _zoom_out(self):
        """Zoom out the view."""
        self.view.scale(1/1.2, 1/1.2)
        
    def _zoom_reset(self):
        """Reset view zoom."""
        self.view.resetTransform()
        
    def _auto_layout(self):
        """Automatically arrange nodes in the scene."""
        # Simple layered layout implementation
        # First layer: triggers
        # Second layer: actions
        
        triggers = []
        actions = []
        
        # Collect nodes by type
        for item in self.scene.items():
            if isinstance(item, TriggerItem):
                triggers.append(item)
            elif isinstance(item, ActionItem):
                actions.append(item)
                
        # Position triggers
        y_pos = 50
        for trigger in triggers:
            trigger.setPos(100, y_pos)
            y_pos += trigger.HEIGHT + 30
            
        # Position actions
        y_pos = 50
        for action in actions:
            action.setPos(400, y_pos)
            y_pos += action.HEIGHT + 30
            
        # Update connections
        for item in self.scene.items():
            if isinstance(item, WorkflowNodeItem):
                item.itemChange(QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged, item.pos())
                
    def _load_workflow(self):
        """Load the current workflow into the visual editor."""
        # Clear scene first (except grid)
        for item in self.scene.items():
            if (isinstance(item, WorkflowNodeItem) or 
                isinstance(item, Connection)):
                self.scene.removeItem(item)
                
        # Add triggers
        node_items = {}
        
        for trigger in self.workflow.triggers:
            trigger_item = TriggerItem(
                trigger.id, 
                trigger.type,
                trigger.name
            )
            
            # Position
            x_pos = 100
            y_pos = 100 + len(node_items) * 100
            trigger_item.setPos(x_pos, y_pos)
            
            # Add to scene
            self.scene.addItem(trigger_item)
            node_items[trigger.id] = trigger_item
            
        # Add action nodes
        for node_id, node in self.workflow.nodes.items():
            action_item = ActionItem(
                node_id,
                node.action.type,
                node.action.name
            )
            
            # Position - place in columns based on connections
            x_pos = 400
            y_pos = 100 + len(node_items) * 100
            action_item.setPos(x_pos, y_pos)
            
            # Add to scene
            self.scene.addItem(action_item)
            node_items[node_id] = action_item
            
        # Add connections
        for node_id, node in self.workflow.nodes.items():
            if node_id in node_items:
                source_item = node_items[node_id]
                
                # Connect to next nodes
                for target_id in node.next_nodes:
                    if target_id in node_items:
                        target_item = node_items[target_id]
                        
                        # Get output point from source
                        source_point = source_item.output_points[0]
                        
                        # Get input point from target
                        target_point = target_item.input_points[0]
                        
                        # Create connection
                        source_point.connect_to(target_point)
                        
        # Center view on content
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.view.centerOn(0, 0)
        
    def update_workflow_model(self):
        """Update the workflow model from the visual representation."""
        # Clear current workflow nodes and connections
        self.workflow.nodes = {}
        self.workflow.triggers = []
        
        # Collect nodes by type
        for item in self.scene.items():
            # Add triggers
            if isinstance(item, TriggerItem):
                trigger = WorkflowTrigger(
                    id=item.node_id,
                    name=item.title,
                    type=item.trigger_type,
                    config=item.config
                )
                self.workflow.triggers.append(trigger)
                
            # Add actions
            elif isinstance(item, ActionItem):
                action = WorkflowAction(
                    name=item.title,
                    type=item.action_type,
                    config=item.config
                )
                
                node = WorkflowNode(
                    id=item.node_id,
                    action=action
                )
                
                self.workflow.nodes[item.node_id] = node
                
        # Update connections
        self.update_workflow_connections()
        
        # Emit signal
        self.workflow_updated.emit(self.workflow)
        
    def update_workflow_connections(self):
        """Update workflow connections from the visual representation."""
        # Clear existing connections
        for node in self.workflow.nodes.values():
            node.next_nodes = []
            
        # Add connections from the scene
        for item in self.scene.items():
            if isinstance(item, WorkflowNodeItem):
                # Get node ID
                node_id = item.node_id
                
                # Skip if not found in workflow
                if node_id not in self.workflow.nodes and item.node_type != NodeType.TRIGGER:
                    continue
                    
                # Get output connections
                for point in item.output_points:
                    if point.connection:
                        target_point = point.connection.target
                        target_node = target_point.node
                        
                        # Add connection in workflow
                        if item.node_type == NodeType.TRIGGER:
                            # If this is a trigger, we need to set entry node
                            if not self.workflow.entry_node_id and target_node.node_id in self.workflow.nodes:
                                self.workflow.entry_node_id = target_node.node_id
                        else:
                            # Regular node to node connection
                            if node_id in self.workflow.nodes and target_node.node_id in self.workflow.nodes:
                                self.workflow.nodes[node_id].next_nodes.append(target_node.node_id)
                                
    def get_workflow(self) -> Workflow:
        """Get the current workflow.
        
        Returns:
            Current workflow with all changes
        """
        # Make sure model is up to date
        self.update_workflow_model()
        return self.workflow 