# OBSCopilot API Reference

This document provides detailed information about the OBSCopilot API for developers who want to extend or integrate with OBSCopilot.

## Table of Contents

1. [Event System](#event-system)
2. [Workflow Engine](#workflow-engine)
3. [Twitch API Integration](#twitch-api-integration)
4. [OBS Integration](#obs-integration)
5. [AI Integration](#ai-integration)
6. [Storage System](#storage-system)
7. [UI Components](#ui-components)

## Event System

The event system is the backbone of OBSCopilot, enabling communication between different components through an event bus.

### EventType Enum

```python
class EventType(Enum):
    """Event types for the event bus."""
    
    # Core events
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    
    # Twitch events
    TWITCH_CONNECTED = "twitch_connected"
    TWITCH_DISCONNECTED = "twitch_disconnected"
    TWITCH_ERROR = "twitch_error"
    TWITCH_CHAT_MESSAGE = "twitch_chat_message"
    TWITCH_COMMAND = "twitch_command"
    TWITCH_FOLLOW = "twitch_follow"
    TWITCH_SUBSCRIPTION = "twitch_subscription"
    TWITCH_BITS = "twitch_bits"
    TWITCH_RAID = "twitch_raid"
    TWITCH_CHANNEL_POINTS_REDEEM = "twitch_channel_points_redeem"
    TWITCH_VIEWERS_UPDATED = "twitch_viewers_updated"
    
    # OBS events
    OBS_CONNECTED = "obs_connected"
    OBS_DISCONNECTED = "obs_disconnected"
    OBS_ERROR = "obs_error"
    OBS_SCENE_CHANGED = "obs_scene_changed"
    OBS_STREAM_STARTED = "obs_stream_started"
    OBS_STREAM_STOPPED = "obs_stream_stopped"
    OBS_RECORDING_STARTED = "obs_recording_started"
    OBS_RECORDING_STOPPED = "obs_recording_stopped"
    
    # Workflow events
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    
    # AI events
    AI_RESPONSE_GENERATED = "ai_response_generated"
    AI_ERROR = "ai_error"
    
    # Stream health events
    STREAM_HEALTH_UPDATED = "stream_health_updated"
    STREAM_HEALTH_WARNING = "stream_health_warning"
```

### Event Class

```python
class Event:
    """Event class for the event bus."""
    
    def __init__(self, event_type: EventType, data: Dict[str, Any] = None):
        """Initialize event.
        
        Args:
            event_type: Type of the event
            data: Event data
        """
        self.type = event_type
        self.data = data or {}
        self.timestamp = time.time()
```

### EventBus Class

```python
class EventBus:
    """Event bus for application events."""
    
    def __init__(self):
        """Initialize event bus."""
        self.listeners = defaultdict(list)
        
    def add_listener(self, event_type: EventType, listener: Callable[[Event], Any]):
        """Add event listener.
        
        Args:
            event_type: Type of event to listen for
            listener: Function to call when event occurs
        """
        self.listeners[event_type].append(listener)
        
    def remove_listener(self, event_type: EventType, listener: Callable[[Event], Any]):
        """Remove event listener.
        
        Args:
            event_type: Type of event
            listener: Listener to remove
        """
        if event_type in self.listeners:
            self.listeners[event_type] = [l for l in self.listeners[event_type] if l != listener]
            
    async def emit(self, event: Event):
        """Emit an event.
        
        Args:
            event: Event to emit
        """
        for listener in self.listeners[event.type]:
            try:
                result = listener(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
```

## Workflow Engine

The workflow engine manages workflows, which consist of triggers and actions.

### Workflow Model

```python
class Workflow(BaseModel):
    """Workflow model."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    enabled: bool = True
    triggers: List[Trigger] = []
    actions: List[Action] = []
    conditions: List[Condition] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### WorkflowEngine Class

```python
class WorkflowEngine:
    """Engine for executing workflows."""
    
    def __init__(self, workflow_repo=None, execution_repo=None):
        """Initialize workflow engine.
        
        Args:
            workflow_repo: Repository for workflow persistence
            execution_repo: Repository for execution logs
        """
        self.workflows = {}  # Map of workflow ID to workflow
        self.workflow_repo = workflow_repo
        self.execution_repo = execution_repo
        
    def register_workflow(self, workflow: Workflow):
        """Register a workflow with the engine.
        
        Args:
            workflow: Workflow to register
        """
        self.workflows[workflow.id] = workflow
        
    def unregister_workflow(self, workflow_id: str):
        """Unregister a workflow from the engine.
        
        Args:
            workflow_id: ID of the workflow to unregister
        """
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            
    async def execute_workflow(self, workflow_id: str, trigger_type: str, trigger_data: Dict = None):
        """Execute a workflow.
        
        Args:
            workflow_id: ID of the workflow to execute
            trigger_type: Type of trigger that initiated the workflow
            trigger_data: Data associated with the trigger
            
        Returns:
            True if execution was successful, False otherwise
        """
        # Workflow execution implementation...
```

## Twitch API Integration

OBSCopilot integrates with the Twitch API for chat, followers, subscriptions, and more.

### TwitchClient Class

```python
class TwitchClient:
    """Client for Twitch API integration."""
    
    def __init__(self, config: Config):
        """Initialize Twitch client.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.connected = False
        self.chat_client = None
        self.api_client = None
        
    async def connect(self):
        """Connect to Twitch API and chat."""
        # Implementation...
        
    def disconnect(self):
        """Disconnect from Twitch API and chat."""
        # Implementation...
        
    async def send_chat_message(self, message: str):
        """Send a message to the Twitch chat.
        
        Args:
            message: Message to send
            
        Returns:
            True if successful, False otherwise
        """
        # Implementation...
```

## OBS Integration

OBSCopilot integrates with OBS Studio through the WebSocket protocol.

### OBSClient Class

```python
class OBSClient:
    """Client for OBS WebSocket integration."""
    
    def __init__(self, config: Config):
        """Initialize OBS client.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.connected = False
        self.client = None
        
    async def connect(self):
        """Connect to OBS WebSocket.
        
        Returns:
            True if successful, False otherwise
        """
        # Implementation...
        
    def disconnect(self):
        """Disconnect from OBS WebSocket."""
        # Implementation...
        
    async def set_scene(self, scene_name: str):
        """Switch to the specified scene.
        
        Args:
            scene_name: Name of the scene
            
        Returns:
            True if successful, False otherwise
        """
        # Implementation...
        
    async def set_source_visibility(self, source_name: str, visible: bool, scene_name: Optional[str] = None):
        """Set the visibility of a source.
        
        Args:
            source_name: Name of the source
            visible: Whether the source should be visible
            scene_name: Name of the scene (or current scene if None)
            
        Returns:
            True if successful, False otherwise
        """
        # Implementation...
```

## AI Integration

OBSCopilot integrates with OpenAI and Google AI for generating responses.

### OpenAIClient Class

```python
class OpenAIClient:
    """OpenAI API client for generating AI responses."""
    
    def __init__(self, config: Config):
        """Initialize OpenAI client.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.client = None
        
    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        conversation_id: Optional[str] = None,
        user_info: Optional[Dict] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """Generate an AI response using the OpenAI API.
        
        Args:
            prompt: User prompt to generate a response for
            system_prompt: System prompt to guide the AI behavior
            conversation_id: ID for maintaining conversation context
            user_info: Information about the user to include in the context
            temperature: Temperature for response randomness (0-2)
            max_tokens: Maximum tokens in the response
            
        Returns:
            Generated response text or None on error
        """
        # Implementation...
```

## Storage System

OBSCopilot uses a database for storage and persistence.

### Repository Pattern

All database operations are performed through repositories:

```python
class Repository(Generic[T]):
    """Base repository for database operations."""
    
    def __init__(self, database: Database, model_class: Type[T]):
        """Initialize repository.
        
        Args:
            database: Database instance
            model_class: SQLAlchemy model class
        """
        self.database = database
        self.model_class = model_class
        
    def get(self, id: str) -> Optional[T]:
        """Get an entity by ID.
        
        Args:
            id: Entity ID
            
        Returns:
            Entity or None if not found
        """
        # Implementation...
        
    def get_all(self) -> List[T]:
        """Get all entities.
        
        Returns:
            List of entities
        """
        # Implementation...
        
    def create(self, entity: T) -> T:
        """Create a new entity.
        
        Args:
            entity: Entity to create
            
        Returns:
            Created entity
        """
        # Implementation...
        
    def update(self, entity: T) -> T:
        """Update an existing entity.
        
        Args:
            entity: Entity to update
            
        Returns:
            Updated entity
        """
        # Implementation...
        
    def delete(self, id: str) -> bool:
        """Delete an entity.
        
        Args:
            id: Entity ID
            
        Returns:
            True if successful, False otherwise
        """
        # Implementation...
```

### Database Schema

The database schema includes tables for:

- Workflows
- Workflow executions
- Stream health metrics
- User statistics
- Message history
- Settings

### SchemaManager Class

```python
class SchemaManager:
    """Database schema manager."""
    
    def __init__(self, config: Config):
        """Initialize schema manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.db_path = Path(config.get('database', 'path', 'data/obscopilot.db'))
        
    def init_schema(self) -> bool:
        """Initialize the database schema.
        
        Returns:
            True if successful, False otherwise
        """
        # Implementation...
        
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """Backup the database.
        
        Args:
            backup_path: Path to save backup (or None for default path)
            
        Returns:
            True if successful, False otherwise
        """
        # Implementation...
        
    def restore_database(self, backup_path: str) -> bool:
        """Restore the database from a backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful, False otherwise
        """
        # Implementation...
```

## UI Components

OBSCopilot provides several UI components that can be used to build custom interfaces or extend the application.

### WorkflowEditor Class

```python
class WorkflowEditor(QWidget):
    """Workflow editor widget for creating and editing workflows."""
    
    workflow_saved = pyqtSignal(object)
    
    def __init__(self, workflow: Optional[Workflow] = None, parent=None):
        """Initialize workflow editor.
        
        Args:
            workflow: Workflow to edit (or None for a new workflow)
            parent: Parent widget
        """
        # Implementation...
        
    def get_workflow(self) -> Workflow:
        """Get the current workflow from the editor.
        
        Returns:
            Current workflow with all changes
        """
        # Implementation...
```

The WorkflowEditor provides a comprehensive interface for creating and editing workflows. It includes the following features:

- Editing workflow name, description, and enabled state
- Adding, editing, and removing triggers with a dynamic configuration UI based on trigger type
- Adding, editing, and removing actions with a dynamic configuration UI based on action type
- Conditional action execution based on event data
- Importing and exporting workflows as JSON
- Previewing workflow execution

### TriggerWidget Class

```python
class TriggerWidget(QFrame):
    """Widget for editing a workflow trigger."""
    
    trigger_updated = pyqtSignal(object)
    trigger_deleted = pyqtSignal(str)
    
    def __init__(self, trigger: Trigger, parent=None):
        """Initialize the trigger widget.
        
        Args:
            trigger: Trigger object to edit
            parent: Parent widget
        """
        # Implementation...
```

The TriggerWidget provides a UI for editing a single trigger in a workflow. It dynamically generates form fields based on the trigger type's configuration schema.

### ActionWidget Class

```python
class ActionWidget(QFrame):
    """Widget for editing a workflow action."""
    
    action_updated = pyqtSignal(object)
    action_deleted = pyqtSignal(str)
    
    def __init__(self, action: Action, parent=None):
        """Initialize the action widget.
        
        Args:
            action: Action object to edit
            parent: Parent widget
        """
        # Implementation...
```

The ActionWidget provides a UI for editing a single action in a workflow. Like the TriggerWidget, it dynamically generates form fields based on the action type's configuration schema.

### Dashboard Class

```python
class Dashboard(QWidget):
    """Dashboard widget for displaying statistics and controls."""
    
    def __init__(self, parent=None):
        """Initialize dashboard.
        
        Args:
            parent: Parent widget
        """
        # Implementation...
        
    def add_widget(self, widget: QWidget, name: str, gridPos: Dict[str, int] = None):
        """Add a widget to the dashboard.
        
        Args:
            widget: Widget to add
            name: Name of the widget
            gridPos: Grid position (x, y, w, h) or None for automatic placement
        """
        # Implementation...
        
    def remove_widget(self, name: str):
        """Remove a widget from the dashboard.
        
        Args:
            name: Name of the widget to remove
        """
        # Implementation...
        
    def save_layout(self) -> Dict:
        """Save the current dashboard layout.
        
        Returns:
            Layout configuration as a dictionary
        """
        # Implementation...
        
    def load_layout(self, layout: Dict):
        """Load a dashboard layout.
        
        Args:
            layout: Layout configuration as a dictionary
        """
        # Implementation...
```

The Dashboard provides a customizable grid layout for displaying various widgets like stream health, viewer statistics, and more. It supports drag-and-drop rearrangement and resizing of widgets.

### StreamHealthTab Class

```python
class StreamHealthTab(QWidget):
    """Stream health monitoring tab."""
    
    def __init__(self, database, obs_client, config, parent=None):
        """Initialize stream health tab.
        
        Args:
            database: Database instance
            obs_client: OBS client instance
            config: Configuration instance
            parent: Parent widget
        """
        # Implementation...
```

The StreamHealthTab displays real-time metrics about the stream, including CPU usage, FPS, dropped frames, and more. It provides charts and alerts for monitoring stream performance.

### ViewerStatsTab Class

```python
class ViewerStatsTab(QWidget):
    """Viewer statistics tab."""
    
    def __init__(self, database, parent=None):
        """Initialize viewer statistics tab.
        
        Args:
            database: Database instance
            parent: Parent widget
        """
        # Implementation...
```

The ViewerStatsTab displays statistics about viewers, including viewer count over time, follow events, subscription events, and more.

## Extending OBSCopilot

Developers can extend OBSCopilot by:

1. Creating custom trigger types
2. Implementing new action types
3. Integrating with additional services
4. Creating plugins

For information on extending OBSCopilot, see the [Developer Guide](developer_guide.md). 