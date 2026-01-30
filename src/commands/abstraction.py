from abc import ABC, abstractmethod
from typing import Any, Optional

class CommandContext:
    """
    Abstracts the context in which a command is executed.
    This allows strategies to access platform-specific resources via the adapter.
    """
    def __init__(self, adapter: Any, event: Any, message_text: str):
        self.adapter = adapter
        self.event = event
        self.message_text = message_text

class Command(ABC):
    """
    Abstract base class for all commands.
    """
    @abstractmethod
    def match(self, text: str) -> bool:
        """
        Determines if this command should handle the given text.
        """
        pass

    @abstractmethod
    def execute(self, context: CommandContext) -> None:
        """
        Executes the command logic.
        """
        pass

class CommandRegistry:
    """
    Registry for managing and dispatching commands.
    """
    def __init__(self):
        self.commands = []

    def register(self, command: Command):
        self.commands.append(command)

    def get_command(self, text: str) -> Optional[Command]:
        for cmd in self.commands:
            if cmd.match(text):
                return cmd
        return None
