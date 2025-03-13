"""
Logger utility for the Streamlit app.

This module provides enhanced logging capabilities with customizable log levels,
formatting, and Streamlit integration.
"""

import logging
import sys
import time
import streamlit as st
from typing import Dict, Optional, Any, List, Union, Callable

# Log levels
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

# Custom formatter class that includes timing information
class TimedFormatter(logging.Formatter):
    def format(self, record):
        record.elapsed = time.time() - self.startup_time
        return super().format(record)
    
    def __init__(self, fmt=None, datefmt=None, style='%', startup_time=None):
        super().__init__(fmt, datefmt, style)
        self.startup_time = startup_time if startup_time else time.time()

class StreamlitLogger:
    """
    Advanced logger for Streamlit applications that provides both console and
    Streamlit-based logging with timing information.
    """
    def __init__(
        self, 
        name: str = "streamlit_app", 
        level: int = logging.INFO,
        log_to_streamlit: bool = True,
        log_to_console: bool = True,
        format_string: str = "%(elapsed).2fs | %(levelname)s | %(message)s"
    ):
        self.name = name
        self.level = level
        self.log_to_streamlit = log_to_streamlit
        self.log_to_console = log_to_console
        self.format_string = format_string
        self.startup_time = time.time()
        
        # Initialize logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers = []  # Remove any existing handlers
        
        # Add console handler if requested
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            formatter = TimedFormatter(format_string, startup_time=self.startup_time)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # Initialize log history for Streamlit
        if "log_history" not in st.session_state:
            st.session_state.log_history = []
    
    def debug(self, msg: str, *args, **kwargs):
        """Log a debug message and add to Streamlit session if enabled."""
        self.logger.debug(msg, *args, **kwargs)
        if self.log_to_streamlit and self.level <= DEBUG:
            self._add_to_streamlit(msg, "debug", kwargs.get("context", {}))
    
    def info(self, msg: str, *args, **kwargs):
        """Log an info message and add to Streamlit session if enabled."""
        self.logger.info(msg, *args, **kwargs)
        if self.log_to_streamlit and self.level <= INFO:
            self._add_to_streamlit(msg, "info", kwargs.get("context", {}))
    
    def warning(self, msg: str, *args, **kwargs):
        """Log a warning message and add to Streamlit session if enabled."""
        self.logger.warning(msg, *args, **kwargs)
        if self.log_to_streamlit and self.level <= WARNING:
            self._add_to_streamlit(msg, "warning", kwargs.get("context", {}))
    
    def error(self, msg: str, *args, **kwargs):
        """Log an error message and add to Streamlit session if enabled."""
        self.logger.error(msg, *args, **kwargs)
        if self.log_to_streamlit and self.level <= ERROR:
            self._add_to_streamlit(msg, "error", kwargs.get("context", {}))
    
    def critical(self, msg: str, *args, **kwargs):
        """Log a critical message and add to Streamlit session if enabled."""
        self.logger.critical(msg, *args, **kwargs)
        if self.log_to_streamlit and self.level <= CRITICAL:
            self._add_to_streamlit(msg, "critical", kwargs.get("context", {}))
    
    def _add_to_streamlit(self, msg: str, level: str, context: Dict[str, Any] = None):
        """Add a log entry to the Streamlit session state."""
        if "log_history" not in st.session_state:
            st.session_state.log_history = []
        
        st.session_state.log_history.append({
            "timestamp": time.time(),
            "elapsed": time.time() - self.startup_time,
            "level": level,
            "message": msg,
            "context": context or {}
        })
    
    def get_log_history(self) -> List[Dict[str, Any]]:
        """Get the current log history from Streamlit session state."""
        return st.session_state.log_history if "log_history" in st.session_state else []
    
    def clear_log_history(self):
        """Clear the log history in Streamlit session state."""
        if "log_history" in st.session_state:
            st.session_state.log_history = []
    
    def display_logs(self, container: Optional[Any] = None, 
                    max_entries: int = 100, 
                    level_filter: Optional[str] = None):
        """
        Display logs in a Streamlit container with filtering options.
        
        Args:
            container: Streamlit container to display logs in. If None, uses st directly.
            max_entries: Maximum number of log entries to display.
            level_filter: Filter logs by level (debug, info, warning, error, critical).
        """
        logs = self.get_log_history()
        
        # Apply filtering
        if level_filter:
            logs = [log for log in logs if log["level"] == level_filter]
        
        # Apply limit
        logs = logs[-max_entries:] if len(logs) > max_entries else logs
        
        # Use the provided container or st directly
        ctx = container or st
        
        if not logs:
            ctx.info("No logs to display.")
            return
        
        for log in logs:
            elapsed = f"{log['elapsed']:.2f}s"
            message = log['message']
            level = log['level'].upper()
            
            if log['level'] == 'debug':
                ctx.text(f"⏱️ {elapsed} | 🔍 DEBUG | {message}")
            elif log['level'] == 'info':
                ctx.text(f"⏱️ {elapsed} | ℹ️ INFO | {message}")
            elif log['level'] == 'warning':
                ctx.warning(f"⏱️ {elapsed} | {message}")
            elif log['level'] == 'error':
                ctx.error(f"⏱️ {elapsed} | {message}")
            elif log['level'] == 'critical':
                ctx.error(f"⏱️ {elapsed} | 🔥 CRITICAL | {message}")

# Create a default logger instance
logger = StreamlitLogger(name="streamlit_app", level=INFO)

def get_logger(name: str = "streamlit_app", level: int = None) -> StreamlitLogger:
    """Get a logger instance with the specified name and level."""
    global logger
    if name == "streamlit_app" and logger:
        if level is not None:
            logger.level = level
            logger.logger.setLevel(level)
        return logger
    
    return StreamlitLogger(name=name, level=level or INFO) 