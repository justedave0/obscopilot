# OBSCopilot Developer Guide

This guide provides information for developers who want to extend or customize OBSCopilot.

## Table of Contents

1. [Project Structure](#project-structure)
2. [Development Environment](#development-environment)
3. [Adding Trigger Types](#adding-trigger-types)
4. [Adding Action Types](#adding-action-types)
5. [Creating UI Components](#creating-ui-components)
6. [Working with Events](#working-with-events)
7. [Database and Storage](#database-and-storage)
8. [Testing Your Extensions](#testing-your-extensions)

## Project Structure

The OBSCopilot codebase is organized as follows:

```
obscopilot/
├── core/           # Core functionality (config, events, utils)
├── workflows/      # Workflow engine and components
│   ├── triggers/   # Trigger implementations
│   └── actions/    # Action implementations
├── twitch/         # Twitch API integration
├── obs/            # OBS WebSocket integration
├── ai/             # AI services integration
├── ui/             # User interface components
└── storage/        # Database and persistence
```

## Development Environment

To set up a development environment for OBSCopilot:

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/obscopilot.git
   cd obscopilot
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   pip install -e .  # Install in development mode
   ```

4. Run tests to verify setup:
   ```
   python -m pytest
   ```

## Adding Trigger Types

Triggers are the events that can initiate workflows. To add a new trigger type:

1. Define a new trigger type in `obscopilot/workflows/models.py`:
   ```python
   class TriggerType(Enum):
       # Existing trigger types...
       MY_CUSTOM_TRIGGER = "my_custom_trigger"
   ```

2. Create a new trigger class in `obscopilot/workflows/triggers/`:
   ```python
   # obscopilot/workflows/triggers/my_trigger.py
   from obscopilot.workflows.models import BaseTrigger, TriggerType
   
   class MyCustomTrigger(BaseTrigger):
       """Custom trigger for handling specific events."""
       
       trigger_type = TriggerType.MY_CUSTOM_TRIGGER
       
       @classmethod
       def config_schema(cls):
           """Define configuration schema for this trigger."""
           return {
               "parameter1": {
                   "type": "string",
                   "label": "Parameter 1",
                   "default": "",
                   "required": True
               },
               # More parameters...
           }
       
       def matches_event(self, event, context):
           """Check if this trigger matches the given event."""
           # Implementation...
           return True  # or False
   ```

3. Register your trigger in `obscopilot/workflows/triggers/__init__.py`:
   ```python
   from .my_trigger import MyCustomTrigger
   
   __all__ = [
       # Existing triggers...
       'MyCustomTrigger',
   ]
   ```

## Adding Action Types

Actions are the operations that can be performed when a workflow is triggered. To add a new action type:

1. Define a new action type in `obscopilot/workflows/models.py`:
   ```python
   class ActionType(Enum):
       # Existing action types...
       MY_CUSTOM_ACTION = "my_custom_action"
   ```

2. Create a new action class in `obscopilot/workflows/actions/`:
   ```python
   # obscopilot/workflows/actions/my_action.py
   from obscopilot.workflows.models import BaseAction, ActionType
   
   class MyCustomAction(BaseAction):
       """Custom action for performing specific operations."""
       
       action_type = ActionType.MY_CUSTOM_ACTION
       
       @classmethod
       def config_schema(cls):
           """Define configuration schema for this action."""
           return {
               "parameter1": {
                   "type": "string",
                   "label": "Parameter 1",
                   "default": "",
                   "required": True
               },
               # More parameters...
           }
       
       async def execute(self, context):
           """Execute the action."""
           # Implementation...
           return True  # Success or False for failure
   ```

3. Register your action in `obscopilot/workflows/actions/__init__.py`:
   ```python
   from .my_action import MyCustomAction
   
   __all__ = [
       # Existing actions...
       'MyCustomAction',
   ]
   ```

4. Add a handler method in the WorkflowEngine class to execute your action:
   ```python
   # obscopilot/workflows/engine.py
   async def _handle_my_custom_action(self, action, context):
       """Handle my custom action."""
       # Implementation...
       return result
   ```

5. Register the handler in the `_setup_action_handlers` method of the WorkflowEngine class:
   ```python
   def _setup_action_handlers(self):
       self.action_handlers = {
           # Existing handlers...
           ActionType.MY_CUSTOM_ACTION: self._handle_my_custom_action,
       }
   ```

## Creating UI Components

To create a new UI component for OBSCopilot:

1. Create a new file in the `obscopilot/ui/` directory:
   ```python
   # obscopilot/ui/my_component.py
   from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
   
   class MyComponent(QWidget):
       """My custom UI component."""
       
       def __init__(self, parent=None):
           """Initialize component."""
           super().__init__(parent)
           self._init_ui()
       
       def _init_ui(self):
           """Initialize UI elements."""
           layout = QVBoxLayout(self)
           layout.addWidget(QLabel("My Custom Component"))
           
           # Add more widgets and functionality...
   ```

2. To make your component available in the main application, add it to the appropriate section in `obscopilot/ui/main.py`:
   ```python
   from obscopilot.ui.my_component import MyComponent
   
   # In MainWindow._init_ui or another appropriate method:
   self.my_component = MyComponent()
   self.some_tab_widget.addTab(self.my_component, "My Component")
   ```

## Working with Events

OBSCopilot uses an event-driven architecture. To interact with the event system:

1. Define a new event type in `obscopilot/core/events.py`:
   ```python
   class EventType(Enum):
       # Existing event types...
       MY_CUSTOM_EVENT = "my_custom_event"
   ```

2. Subscribe to events:
   ```python
   from obscopilot.core.events import event_bus, EventType
   
   def my_event_handler(event):
       """Handle my custom event."""
       print(f"Received event: {event.type} with data: {event.data}")
   
   # Subscribe to the event
   event_bus.subscribe(EventType.MY_CUSTOM_EVENT, my_event_handler)
   ```

3. Emit events:
   ```python
   from obscopilot.core.events import Event, EventType, event_bus
   
   # Create and emit an event
   event = Event(EventType.MY_CUSTOM_EVENT, {"key": "value"})
   await event_bus.emit(event)
   ```

## Database and Storage

OBSCopilot uses SQLite for storage. To interact with the database:

1. Define a new model in `obscopilot/storage/models.py`:
   ```python
   from sqlalchemy import Column, Integer, String, ForeignKey
   from sqlalchemy.ext.declarative import declarative_base
   
   Base = declarative_base()
   
   class MyModel(Base):
       """My custom database model."""
       
       __tablename__ = "my_models"
       
       id = Column(Integer, primary_key=True)
       name = Column(String, nullable=False)
       description = Column(String)
   ```

2. Create a repository for your model in `obscopilot/storage/repositories.py`:
   ```python
   from obscopilot.storage.models import MyModel
   
   class MyModelRepository:
       """Repository for my model."""
       
       def __init__(self, database):
           """Initialize repository.
           
           Args:
               database: Database instance
           """
           self.database = database
       
       def get(self, id):
           """Get a model by ID."""
           with self.database.session() as session:
               return session.query(MyModel).filter(MyModel.id == id).first()
       
       def get_all(self):
           """Get all models."""
           with self.database.session() as session:
               return session.query(MyModel).all()
       
       def create(self, name, description=None):
           """Create a new model."""
           with self.database.session() as session:
               model = MyModel(name=name, description=description)
               session.add(model)
               session.commit()
               return model
       
       # Add more methods as needed...
   ```

## Testing Your Extensions

It's important to test your extensions to ensure they work correctly:

1. Create unit tests in the `tests/unit/` directory:
   ```python
   # tests/unit/test_my_extension.py
   import pytest
   from unittest.mock import MagicMock
   
   from obscopilot.workflows.triggers.my_trigger import MyCustomTrigger
   
   def test_my_trigger_matches_event():
       """Test my custom trigger."""
       # Create a mock event
       event = MagicMock()
       event.type = "my_custom_event"
       event.data = {"key": "value"}
       
       # Create trigger
       trigger = MyCustomTrigger(config={"parameter1": "test"})
       
       # Test matching
       assert trigger.matches_event(event, {}) is True
   ```

2. Create integration tests in the `tests/integration/` directory:
   ```python
   # tests/integration/test_my_integration.py
   import pytest
   from unittest.mock import MagicMock, AsyncMock
   
   from obscopilot.workflows.actions.my_action import MyCustomAction
   
   @pytest.mark.asyncio
   async def test_my_action_execution():
       """Test my custom action execution."""
       # Create dependencies
       dependencies = MagicMock()
       
       # Create action
       action = MyCustomAction(
           config={"parameter1": "test"},
           dependencies=dependencies
       )
       
       # Execute action
       result = await action.execute({})
       
       # Verify result
       assert result is True
   ```

3. Create UI tests in the `tests/ui/` directory:
   ```python
   # tests/ui/test_my_component.py
   import pytest
   from PyQt6.QtWidgets import QApplication
   
   from obscopilot.ui.my_component import MyComponent
   
   @pytest.fixture
   def app():
       """QApplication fixture."""
       app = QApplication.instance()
       if app is None:
           app = QApplication([])
       yield app
   
   def test_my_component(app):
       """Test my custom component."""
       component = MyComponent()
       assert component is not None
       # More assertions...
   ```

4. Run tests:
   ```
   python -m pytest tests/unit/test_my_extension.py
   python -m pytest tests/integration/test_my_integration.py
   python -m pytest tests/ui/test_my_component.py
   ```

## Example: Creating a Timer Trigger and Action

Let's walk through a complete example of creating a timer trigger and action:

### Timer Trigger

```python
# obscopilot/workflows/triggers/timer_trigger.py
import time
from obscopilot.workflows.models import BaseTrigger, TriggerType

class TimerTrigger(BaseTrigger):
    """Trigger that activates after a specified time interval."""
    
    trigger_type = TriggerType.TIMER
    
    @classmethod
    def config_schema(cls):
        """Define configuration schema for timer trigger."""
        return {
            "interval": {
                "type": "integer",
                "label": "Interval (seconds)",
                "default": 60,
                "required": True,
                "minimum": 1,
                "maximum": 86400  # 1 day
            },
            "repeat": {
                "type": "boolean",
                "label": "Repeat",
                "default": False,
                "required": False
            }
        }
    
    def __init__(self, **kwargs):
        """Initialize timer trigger."""
        super().__init__(**kwargs)
        self.last_triggered = 0
    
    def matches_event(self, event, context):
        """Check if enough time has passed since last trigger."""
        current_time = time.time()
        interval = self.config.get("interval", 60)
        
        if current_time - self.last_triggered >= interval:
            self.last_triggered = current_time
            return True
        
        return False
```

### Timer Action

```python
# obscopilot/workflows/actions/timer_action.py
import asyncio
from obscopilot.workflows.models import BaseAction, ActionType

class DelayAction(BaseAction):
    """Action that introduces a delay in workflow execution."""
    
    action_type = ActionType.DELAY
    
    @classmethod
    def config_schema(cls):
        """Define configuration schema for delay action."""
        return {
            "seconds": {
                "type": "integer",
                "label": "Delay (seconds)",
                "default": 5,
                "required": True,
                "minimum": 1,
                "maximum": 300  # 5 minutes
            }
        }
    
    async def execute(self, context):
        """Execute the delay action."""
        seconds = self.config.get("seconds", 5)
        
        # Add to context for logging
        context.set_variable("delay_seconds", seconds)
        
        # Sleep for the specified duration
        await asyncio.sleep(seconds)
        
        return True
```

With these examples, you should be able to extend OBSCopilot with custom triggers and actions to suit your needs. 