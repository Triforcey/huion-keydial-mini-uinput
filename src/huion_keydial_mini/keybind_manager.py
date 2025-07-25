#!/usr/bin/env python3
"""Keybind manager for Huion Keydial Mini with runtime control via Unix socket."""

import asyncio
import json
import logging
import socket
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum

from .config import Config


logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events that can be bound."""
    KEYBOARD = "keyboard"


@dataclass
class KeybindAction:
    """Represents a keybind action."""
    type: EventType
    keys: Optional[List[str]] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'type': self.type.value,
            'keys': self.keys,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KeybindAction':
        """Create from dictionary."""
        return cls(
            type=EventType(data['type']),
            keys=data.get('keys'),
            description=data.get('description')
        )


class KeybindManager:
    """Manages in-memory keybind mappings with Unix socket control interface."""

    def __init__(self, config: Config, socket_path: Optional[str] = None):
        self.config = config
        self.socket_path = socket_path or self._get_default_socket_path()
        self.keybind_map: Dict[str, KeybindAction] = {}
        self.server: Optional[asyncio.Server] = None
        self._load_initial_bindings()

    def _get_default_socket_path(self) -> str:
        """Get default socket path for user-level service."""
        socket_dir = Path.home() / ".local" / "share" / "huion-keydial-mini"
        socket_dir.mkdir(parents=True, exist_ok=True)
        return str(socket_dir / "control.sock")

    def _load_initial_bindings(self):
        """Load initial keybindings from config."""
        # Load button mappings
        for button, key in self.config.key_mappings.items():
            if key:
                self.keybind_map[button] = KeybindAction(
                    type=EventType.KEYBOARD,
                    keys=[k.strip() for k in key.split('+')],
                    description=f"Button {button} -> {key}"
                )

        # Load dial settings
        dial_settings = self.config.dial_settings
        if dial_settings.get('DIAL_CW'):
            self.keybind_map['DIAL_CW'] = KeybindAction(
                type=EventType.KEYBOARD,
                keys=[dial_settings['DIAL_CW']],
                description="Dial clockwise -> " + dial_settings['DIAL_CW']
            )

        if dial_settings.get('DIAL_CCW'):
            self.keybind_map['DIAL_CCW'] = KeybindAction(
                type=EventType.KEYBOARD,
                keys=[dial_settings['DIAL_CCW']],
                description="Dial counterclockwise -> " + dial_settings['DIAL_CCW']
            )

        if dial_settings.get('DIAL_CLICK'):
            self.keybind_map['DIAL_CLICK'] = KeybindAction(
                type=EventType.KEYBOARD,
                keys=[dial_settings['DIAL_CLICK']],
                description="Dial click -> " + dial_settings['DIAL_CLICK']
            )

        logger.info(f"Loaded {len(self.keybind_map)} initial keybindings")

    async def start_socket_server(self):
        """Start the Unix socket server for control interface."""
        try:
            # Remove existing socket file if it exists
            socket_path = Path(self.socket_path)
            if socket_path.exists():
                socket_path.unlink()

            self.server = await asyncio.start_unix_server(
                self._handle_client,
                path=self.socket_path
            )

            logger.info(f"Started control socket server at {self.socket_path}")

        except Exception as e:
            logger.error(f"Failed to start socket server: {e}")
            raise

    async def stop_socket_server(self):
        """Stop the Unix socket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

            # Remove socket file
            socket_path = Path(self.socket_path)
            if socket_path.exists():
                socket_path.unlink()

            logger.info("Stopped control socket server")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connection to the control socket."""
        try:
            # Read command
            data = await reader.read(1024)
            if not data:
                return

            command = json.loads(data.decode('utf-8'))
            response = await self._process_command(command)

            # Send response with newline delimiter
            writer.write((json.dumps(response) + '\n').encode('utf-8'))
            await writer.drain()

        except json.JSONDecodeError:
            error_response = {'status': 'error', 'message': 'Invalid JSON'}
            writer.write((json.dumps(error_response) + '\n').encode('utf-8'))
            await writer.drain()
        except Exception as e:
            logger.error(f"Error handling client command: {e}")
            error_response = {'status': 'error', 'message': str(e)}
            writer.write((json.dumps(error_response) + '\n').encode('utf-8'))
            await writer.drain()
        # Don't close the connection here - let the client close it

    async def _process_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Process a control command."""
        cmd_type = command.get('command')

        try:
            if cmd_type == 'get_bindings':
                return await self._cmd_get_bindings()
            elif cmd_type == 'set_binding':
                return await self._cmd_set_binding(command)
            elif cmd_type == 'remove_binding':
                return await self._cmd_remove_binding(command)
            elif cmd_type == 'list_actions':
                return await self._cmd_list_actions()
            else:
                return {'status': 'error', 'message': f'Unknown command: {cmd_type}'}
        except Exception as e:
            logger.error(f"Error processing command {cmd_type}: {e}")
            return {'status': 'error', 'message': str(e)}

    async def _cmd_get_bindings(self) -> Dict[str, Any]:
        """Get all current keybindings."""
        bindings = {}
        for action_id, action in self.keybind_map.items():
            bindings[action_id] = action.to_dict()

        return {
            'status': 'success',
            'bindings': bindings
        }

    async def _cmd_set_binding(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Set a keybinding."""
        action_id = command.get('action_id')
        action_data = command.get('action')

        if not action_id or not action_data:
            return {'status': 'error', 'message': 'Missing action_id or action'}

        try:
            action = KeybindAction.from_dict(action_data)
            self.keybind_map[action_id] = action

            logger.info(f"Set binding {action_id}: {action.description}")
            return {
                'status': 'success',
                'message': f'Binding {action_id} updated'
            }
        except Exception as e:
            return {'status': 'error', 'message': f'Invalid action data: {e}'}

    async def _cmd_remove_binding(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Remove a keybinding."""
        action_id = command.get('action_id')

        if not action_id:
            return {'status': 'error', 'message': 'Missing action_id'}

        if action_id in self.keybind_map:
            del self.keybind_map[action_id]
            logger.info(f"Removed binding {action_id}")
            return {
                'status': 'success',
                'message': f'Binding {action_id} removed'
            }
        else:
            return {
                'status': 'error',
                'message': f'Binding {action_id} not found'
            }

    async def _cmd_list_actions(self) -> Dict[str, Any]:
        """List available action IDs."""
        return {
            'status': 'success',
            'actions': list(self.keybind_map.keys())
        }

    def get_action(self, action_id: str) -> Optional[KeybindAction]:
        """Get a keybind action by ID."""
        return self.keybind_map.get(action_id)

    def set_action(self, action_id: str, action: KeybindAction):
        """Set a keybind action."""
        self.keybind_map[action_id] = action
        logger.info(f"Set binding {action_id}: {action.description}")

    def remove_action(self, action_id: str) -> bool:
        """Remove a keybind action."""
        if action_id in self.keybind_map:
            del self.keybind_map[action_id]
            logger.info(f"Removed binding {action_id}")
            return True
        return False

    def get_all_actions(self) -> Dict[str, KeybindAction]:
        """Get all current keybind actions."""
        return self.keybind_map.copy()


# Client-side functions for keydialctl
async def send_command(socket_path: str, command: Dict[str, Any]) -> Dict[str, Any]:
    """Send a command to the keybind manager via Unix socket."""
    try:
        reader, writer = await asyncio.open_unix_connection(socket_path)

        # Send command
        writer.write(json.dumps(command).encode('utf-8'))
        await writer.drain()

        # Read response (until newline delimiter)
        data = await reader.readline()
        if not data:
            return {'status': 'error', 'message': 'No response from service'}

        response = json.loads(data.decode('utf-8'))

        writer.close()
        await writer.wait_closed()

        return response

    except FileNotFoundError:
        return {'status': 'error', 'message': 'Service not running (socket not found)'}
    except ConnectionRefusedError:
        return {'status': 'error', 'message': 'Service not running (connection refused)'}
    except json.JSONDecodeError as e:
        return {'status': 'error', 'message': f'Invalid response from service: {e}'}
    except Exception as e:
        return {'status': 'error', 'message': f'Communication error: {e}'}
