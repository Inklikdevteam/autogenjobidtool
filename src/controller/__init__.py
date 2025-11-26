"""Controller package for the medical document processing system."""

from .main_controller import MainController, ProcessingError

__all__ = ['MainController', 'ProcessingError']