"""Public entry points for the shared five-room Blender builder."""

from .room_builder import RoomContext, RoomDefinition, RenderSettings, build_room

__all__ = ["RoomContext", "RoomDefinition", "RenderSettings", "build_room"]
