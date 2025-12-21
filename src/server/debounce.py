"""
Message Debounce Buffer for Fluid WhatsApp UX

Implements a 3-second debounce mechanism to aggregate rapid user messages
into a single coherent prompt before triggering the agent.
"""

import asyncio
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class MessageBuffer:
    """
    Stores aggregated messages for a single user with debounce timer
    """
    phone_number: str
    messages: list[str] = field(default_factory=list)
    timer_task: Optional[asyncio.Task] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def add_message(self, text: str):
        """Add a message to the buffer"""
        self.messages.append(text)
        self.last_updated = datetime.utcnow()
    
    def get_aggregated_text(self) -> str:
        """Return all messages combined with spaces"""
        return " ".join(self.messages)
    
    def clear(self):
        """Clear all buffered messages"""
        self.messages = []


class DebounceManager:
    """
    Manages message debouncing for all users
    
    When a message arrives:
    1. Add to buffer for that phone number
    2. Cancel existing timer (if any)
    3. Start new 3-second timer
    4. On timer expiry → trigger callback with aggregated text
    """
    
    def __init__(self, debounce_seconds: float = 3.0):
        """
        Initialize debounce manager
        
        Args:
            debounce_seconds: Time to wait before triggering callback (default: 3.0)
        """
        self.debounce_seconds = debounce_seconds
        self.buffers: Dict[str, MessageBuffer] = {}
        logger.info(f"✅ DebounceManager initialized with {debounce_seconds}s delay")
    
    async def add_message(
        self,
        phone_number: str,
        message_text: str,
        callback: Callable[[str, str], None]
    ):
        """
        Add message to buffer and manage debounce timer
        
        Args:
            phone_number: User's WhatsApp phone number
            message_text: Text of the incoming message
            callback: Async function to call with (phone_number, aggregated_text) when timer expires
        """
        # Get or create buffer for this user
        if phone_number not in self.buffers:
            self.buffers[phone_number] = MessageBuffer(phone_number=phone_number)
            logger.info(f"📝 Created new buffer for {phone_number}")
        
        buffer = self.buffers[phone_number]
        
        # Cancel existing timer if active
        if buffer.timer_task and not buffer.timer_task.done():
            buffer.timer_task.cancel()
            logger.debug(f"⏱️ Cancelled existing timer for {phone_number}")
        
        # Add new message to buffer
        buffer.add_message(message_text)
        logger.info(f"📥 Buffered message from {phone_number}: '{message_text}'")
        logger.debug(f"📊 Buffer now contains {len(buffer.messages)} message(s)")
        
        # Start new timer
        buffer.timer_task = asyncio.create_task(
            self._timer_callback(phone_number, callback)
        )
        logger.debug(f"⏳ Started {self.debounce_seconds}s timer for {phone_number}")
    
    async def _timer_callback(
        self,
        phone_number: str,
        callback: Callable[[str, str], None]
    ):
        """
        Internal timer callback - waits for debounce period then triggers agent
        
        Args:
            phone_number: User identifier
            callback: Function to call with aggregated text
        """
        try:
            # Wait for debounce period
            await asyncio.sleep(self.debounce_seconds)
            
            # Timer expired - get aggregated text
            buffer = self.buffers.get(phone_number)
            if not buffer:
                logger.warning(f"⚠️ Buffer disappeared for {phone_number}")
                return
            
            aggregated_text = buffer.get_aggregated_text()
            logger.success(
                f"✅ Timer expired for {phone_number}. "
                f"Aggregated {len(buffer.messages)} messages: '{aggregated_text}'"
            )
            
            # Clear buffer
            buffer.clear()
            
            # Trigger agent with aggregated text
            await callback(phone_number, aggregated_text)
            
        except asyncio.CancelledError:
            # Timer was cancelled (new message arrived)
            logger.debug(f"🔄 Timer cancelled for {phone_number} (new message arrived)")
        except Exception as e:
            logger.error(f"❌ Error in timer callback for {phone_number}: {e}")
    
    def get_buffer_status(self, phone_number: str) -> Optional[dict]:
        """
        Get current buffer status for debugging
        
        Args:
            phone_number: User identifier
            
        Returns:
            Dict with buffer info or None
        """
        buffer = self.buffers.get(phone_number)
        if not buffer:
            return None
        
        return {
            "phone_number": phone_number,
            "message_count": len(buffer.messages),
            "messages": buffer.messages,
            "created_at": buffer.created_at.isoformat(),
            "last_updated": buffer.last_updated.isoformat(),
            "timer_active": buffer.timer_task and not buffer.timer_task.done()
        }
    
    def clear_buffer(self, phone_number: str):
        """
        Manually clear buffer for a user (for testing)
        
        Args:
            phone_number: User identifier
        """
        if phone_number in self.buffers:
            buffer = self.buffers[phone_number]
            if buffer.timer_task:
                buffer.timer_task.cancel()
            del self.buffers[phone_number]
            logger.info(f"🗑️ Cleared buffer for {phone_number}")
