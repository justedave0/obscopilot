"""
OBSCopilot OBS Control Module

This module handles interactions with OBS through both the Python scripting API
and the WebSocket API (if available).
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Union

# Configure logging
logger = logging.getLogger("OBSCopilot.OBSControl")

# Try to import the OBS WebSocket client
try:
    import obsws_python as obsws
    HAVE_OBSWS = True
except ImportError:
    HAVE_OBSWS = False
    logger.warning("obsws-python not found, using limited OBS scripting API")

# Global variables
obsws_client = None

def connect_to_obs_websocket(host: str, port: int, password: str) -> bool:
    """Connect to OBS WebSocket server"""
    global obsws_client
    
    if not HAVE_OBSWS:
        logger.warning("obsws-python not installed, cannot connect to OBS WebSocket")
        return False
    
    try:
        # Disconnect existing client if any
        if obsws_client:
            obsws_client = None
        
        # Create new client
        obsws_client = obsws.ReqClient(
            host=host,
            port=port,
            password=password
        )
        
        # Test connection with a simple request
        version = obsws_client.get_version()
        logger.info(f"Connected to OBS WebSocket: OBS {version.obs_version}, WebSocket {version.obs_web_socket_version}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to OBS WebSocket: {e}")
        obsws_client = None
        return False

def disconnect_from_obs_websocket() -> None:
    """Disconnect from OBS WebSocket server"""
    global obsws_client
    
    if obsws_client:
        obsws_client = None
        logger.info("Disconnected from OBS WebSocket")

def is_connected() -> bool:
    """Check if connected to OBS WebSocket"""
    return obsws_client is not None if HAVE_OBSWS else False

def get_scenes() -> List[str]:
    """Get list of all scene names"""
    try:
        if obsws_client:
            # Using WebSocket API
            scenes = obsws_client.get_scene_list().scenes
            return [scene["sceneName"] for scene in scenes]
        else:
            # Using OBS Python API
            import obspython as obs
            scene_names = []
            scenes = obs.obs_frontend_get_scenes()
            
            for scene in scenes:
                name = obs.obs_source_get_name(scene)
                scene_names.append(name)
            
            obs.source_list_release(scenes)
            return scene_names
    except Exception as e:
        logger.error(f"Error getting scene list: {e}")
        return []

def get_current_scene() -> str:
    """Get the name of the current scene"""
    try:
        if obsws_client:
            # Using WebSocket API
            scene = obsws_client.get_current_program_scene().current_program_scene_name
            return scene
        else:
            # Using OBS Python API
            import obspython as obs
            current_scene = obs.obs_frontend_get_current_scene()
            scene_name = obs.obs_source_get_name(current_scene)
            obs.obs_source_release(current_scene)
            return scene_name
    except Exception as e:
        logger.error(f"Error getting current scene: {e}")
        return ""

def switch_to_scene(scene_name: str) -> bool:
    """Switch to a different scene"""
    try:
        if obsws_client:
            # Using WebSocket API
            obsws_client.set_current_program_scene(scene_name=scene_name)
            logger.info(f"Switched to scene '{scene_name}'")
            return True
        else:
            # Using OBS Python API
            import obspython as obs
            scenes = obs.obs_frontend_get_scenes()
            success = False
            
            for scene in scenes:
                name = obs.obs_source_get_name(scene)
                if name == scene_name:
                    obs.obs_frontend_set_current_scene(scene)
                    logger.info(f"Switched to scene '{scene_name}'")
                    success = True
                    break
            
            obs.source_list_release(scenes)
            return success
    except Exception as e:
        logger.error(f"Error switching scenes: {e}")
        return False

def get_sources_in_scene(scene_name: str) -> List[Dict[str, Any]]:
    """Get list of all sources in a scene"""
    try:
        if obsws_client:
            # Using WebSocket API
            scene_items = obsws_client.get_scene_item_list(scene_name=scene_name).scene_items
            return [{
                "name": item["sourceName"],
                "id": item["sceneItemId"],
                "type": item["sourceType"],
                "visible": item["sceneItemEnabled"]
            } for item in scene_items]
        else:
            # Using OBS Python API
            import obspython as obs
            sources = []
            
            # Get the scene
            scene_source = obs.obs_get_source_by_name(scene_name)
            if scene_source:
                scene = obs.obs_scene_from_source(scene_source)
                
                # Define callback to get info for each item
                def callback(scene, item, data):
                    source = obs.obs_sceneitem_get_source(item)
                    source_id = obs.obs_sceneitem_get_id(item)
                    source_name = obs.obs_source_get_name(source)
                    source_type = obs.obs_source_get_type(source)
                    source_type_str = {
                        obs.OBS_SOURCE_TYPE_INPUT: "input",
                        obs.OBS_SOURCE_TYPE_FILTER: "filter",
                        obs.OBS_SOURCE_TYPE_TRANSITION: "transition",
                        obs.OBS_SOURCE_TYPE_SCENE: "scene"
                    }.get(source_type, "unknown")
                    
                    visible = obs.obs_sceneitem_visible(item)
                    
                    sources.append({
                        "name": source_name,
                        "id": source_id,
                        "type": source_type_str,
                        "visible": visible
                    })
                    
                    return True
                
                # Enumerate all items in the scene
                obs.obs_scene_enum_items(scene, callback, None)
                obs.obs_source_release(scene_source)
            
            return sources
    except Exception as e:
        logger.error(f"Error getting sources in scene '{scene_name}': {e}")
        return []

def set_source_visibility(scene_name: str, source_name: str, visible: bool) -> bool:
    """Set visibility of a source in a scene"""
    try:
        if obsws_client:
            # Using WebSocket API
            # First, find the scene item ID
            scene_items = obsws_client.get_scene_item_list(scene_name=scene_name).scene_items
            scene_item_id = None
            
            for item in scene_items:
                if item["sourceName"] == source_name:
                    scene_item_id = item["sceneItemId"]
                    break
            
            if scene_item_id is not None:
                obsws_client.set_scene_item_enabled(
                    scene_name=scene_name, 
                    scene_item_id=scene_item_id, 
                    enabled=visible
                )
                logger.info(f"Set source '{source_name}' in scene '{scene_name}' visibility to {visible}")
                return True
            else:
                logger.warning(f"Source '{source_name}' not found in scene '{scene_name}'")
                return False
        else:
            # Using OBS Python API
            import obspython as obs
            
            # Get the scene
            scene_source = obs.obs_get_source_by_name(scene_name)
            if not scene_source:
                logger.warning(f"Scene '{scene_name}' not found")
                return False
            
            scene = obs.obs_scene_from_source(scene_source)
            
            # Find the scene item
            scene_item = obs.obs_scene_find_source_recursive(scene, source_name)
            if not scene_item:
                logger.warning(f"Source '{source_name}' not found in scene '{scene_name}'")
                obs.obs_source_release(scene_source)
                return False
            
            # Set visibility
            obs.obs_sceneitem_set_visible(scene_item, visible)
            logger.info(f"Set source '{source_name}' in scene '{scene_name}' visibility to {visible}")
            
            obs.obs_source_release(scene_source)
            return True
    except Exception as e:
        logger.error(f"Error setting source visibility: {e}")
        return False

def get_text_sources() -> List[str]:
    """Get list of all text sources"""
    try:
        if obsws_client:
            # Using WebSocket API
            inputs = obsws_client.get_input_list().inputs
            return [input["inputName"] for input in inputs if input["inputKind"] in ["text_ft2_source", "text_gdiplus"]]
        else:
            # Using OBS Python API
            import obspython as obs
            text_sources = []
            
            # Define source callback
            def source_enum_proc(source, data):
                source_id = obs.obs_source_get_unversioned_id(source)
                if source_id in ["text_ft2_source", "text_gdiplus"]:
                    name = obs.obs_source_get_name(source)
                    text_sources.append(name)
                return True
            
            # Enumerate all sources
            obs.obs_enum_sources(source_enum_proc, None)
            return text_sources
    except Exception as e:
        logger.error(f"Error getting text sources: {e}")
        return []

def set_text_source_content(source_name: str, text: str) -> bool:
    """Set the text of a text source"""
    try:
        if obsws_client:
            # Using WebSocket API
            source_settings = obsws_client.get_input_settings(source_name=source_name).input_settings
            source_settings["text"] = text
            obsws_client.set_input_settings(source_name=source_name, input_settings=source_settings)
            logger.info(f"Updated text for source '{source_name}'")
            return True
        else:
            # Using OBS Python API
            import obspython as obs
            source = obs.obs_get_source_by_name(source_name)
            if not source:
                logger.warning(f"Text source '{source_name}' not found")
                return False
            
            settings = obs.obs_data_create()
            obs.obs_data_set_string(settings, "text", text)
            obs.obs_source_update(source, settings)
            
            obs.obs_data_release(settings)
            obs.obs_source_release(source)
            
            logger.info(f"Updated text for source '{source_name}'")
            return True
    except Exception as e:
        logger.error(f"Error updating text source: {e}")
        return False

def get_media_sources() -> List[str]:
    """Get list of all media sources"""
    try:
        if obsws_client:
            # Using WebSocket API
            inputs = obsws_client.get_input_list().inputs
            return [input["inputName"] for input in inputs if input["inputKind"] in ["ffmpeg_source", "vlc_source"]]
        else:
            # Using OBS Python API
            import obspython as obs
            media_sources = []
            
            # Define source callback
            def source_enum_proc(source, data):
                source_id = obs.obs_source_get_unversioned_id(source)
                if source_id in ["ffmpeg_source", "vlc_source"]:
                    name = obs.obs_source_get_name(source)
                    media_sources.append(name)
                return True
            
            # Enumerate all sources
            obs.obs_enum_sources(source_enum_proc, None)
            return media_sources
    except Exception as e:
        logger.error(f"Error getting media sources: {e}")
        return []

def control_media_source(source_name: str, action: str) -> bool:
    """Control a media source (play, pause, stop, restart)"""
    valid_actions = ["play", "pause", "stop", "restart"]
    if action not in valid_actions:
        logger.error(f"Invalid media control action: {action}")
        return False
    
    try:
        if obsws_client:
            # Using WebSocket API
            if action == "play":
                obsws_client.trigger_media_input_action(
                    input_name=source_name,
                    media_action="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PLAY"
                )
            elif action == "pause":
                obsws_client.trigger_media_input_action(
                    input_name=source_name,
                    media_action="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PAUSE"
                )
            elif action == "stop":
                obsws_client.trigger_media_input_action(
                    input_name=source_name,
                    media_action="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_STOP"
                )
            elif action == "restart":
                obsws_client.trigger_media_input_action(
                    input_name=source_name,
                    media_action="OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART"
                )
            
            logger.info(f"Media source '{source_name}' action: {action}")
            return True
        else:
            # Using OBS Python API
            import obspython as obs
            source = obs.obs_get_source_by_name(source_name)
            if not source:
                logger.warning(f"Media source '{source_name}' not found")
                return False
            
            # Get media state
            state = obs.obs_source_media_get_state(source)
            
            # Execute action
            if action == "play":
                if state != obs.OBS_MEDIA_STATE_PLAYING:
                    obs.obs_source_media_play_pause(source, False)
            elif action == "pause":
                if state == obs.OBS_MEDIA_STATE_PLAYING:
                    obs.obs_source_media_play_pause(source, True)
            elif action == "stop":
                obs.obs_source_media_stop(source)
            elif action == "restart":
                obs.obs_source_media_restart(source)
            
            obs.obs_source_release(source)
            logger.info(f"Media source '{source_name}' action: {action}")
            return True
    except Exception as e:
        logger.error(f"Error controlling media source: {e}")
        return False

def get_streaming_status() -> Dict[str, Any]:
    """Get streaming status"""
    try:
        if obsws_client:
            # Using WebSocket API
            stream_status = obsws_client.get_stream_status()
            return {
                "active": stream_status.output_active,
                "duration": stream_status.output_duration,
                "reconnecting": stream_status.output_reconnecting,
                "timecode": stream_status.output_timecode
            }
        else:
            # Using OBS Python API
            import obspython as obs
            return {
                "active": obs.obs_frontend_streaming_active(),
                "duration": 0,  # Not available in Python API
                "reconnecting": False,  # Not available in Python API
                "timecode": ""  # Not available in Python API
            }
    except Exception as e:
        logger.error(f"Error getting streaming status: {e}")
        return {
            "active": False,
            "duration": 0,
            "reconnecting": False,
            "timecode": ""
        }

def get_recording_status() -> Dict[str, Any]:
    """Get recording status"""
    try:
        if obsws_client:
            # Using WebSocket API
            record_status = obsws_client.get_record_status()
            return {
                "active": record_status.output_active,
                "paused": record_status.output_paused,
                "duration": record_status.output_duration,
                "timecode": record_status.output_timecode
            }
        else:
            # Using OBS Python API
            import obspython as obs
            return {
                "active": obs.obs_frontend_recording_active(),
                "paused": obs.obs_frontend_recording_paused(),
                "duration": 0,  # Not available in Python API
                "timecode": ""  # Not available in Python API
            }
    except Exception as e:
        logger.error(f"Error getting recording status: {e}")
        return {
            "active": False,
            "paused": False,
            "duration": 0,
            "timecode": ""
        }

def get_virtual_camera_status() -> bool:
    """Check if virtual camera is active"""
    try:
        if obsws_client:
            # Using WebSocket API
            return obsws_client.get_virtual_cam_status().output_active
        else:
            # Using OBS Python API
            import obspython as obs
            return obs.obs_frontend_virtualcam_active()
    except Exception as e:
        logger.error(f"Error getting virtual camera status: {e}")
        return False

def execute_action(action_type: str, action_data: Dict[str, Any], event_data: Any = None) -> bool:
    """Execute an OBS action with the given data"""
    try:
        if action_type == "show_source":
            scene_name = action_data.get("scene_name", "")
            source_name = action_data.get("source_name", "")
            
            if not scene_name or not source_name:
                logger.error("Missing scene_name or source_name for show_source action")
                return False
            
            return set_source_visibility(scene_name, source_name, True)
        
        elif action_type == "hide_source":
            scene_name = action_data.get("scene_name", "")
            source_name = action_data.get("source_name", "")
            
            if not scene_name or not source_name:
                logger.error("Missing scene_name or source_name for hide_source action")
                return False
            
            return set_source_visibility(scene_name, source_name, False)
        
        elif action_type == "update_text":
            source_name = action_data.get("source_name", "")
            text_format = action_data.get("text", "")
            
            if not source_name or not text_format:
                logger.error("Missing source_name or text for update_text action")
                return False
            
            # Replace placeholders with event data if available
            if event_data:
                for key in dir(event_data):
                    if not key.startswith("_") and not callable(getattr(event_data, key)):
                        placeholder = f"{{{key}}}"
                        if placeholder in text_format:
                            text_format = text_format.replace(placeholder, str(getattr(event_data, key)))
            
            return set_text_source_content(source_name, text_format)
        
        elif action_type == "switch_scene":
            scene_name = action_data.get("scene_name", "")
            
            if not scene_name:
                logger.error("Missing scene_name for switch_scene action")
                return False
            
            return switch_to_scene(scene_name)
        
        elif action_type == "play_media":
            source_name = action_data.get("source_name", "")
            
            if not source_name:
                logger.error("Missing source_name for play_media action")
                return False
            
            return control_media_source(source_name, "play")
        
        else:
            logger.error(f"Unknown action type: {action_type}")
            return False
    
    except Exception as e:
        logger.error(f"Error executing action {action_type}: {e}")
        return False 