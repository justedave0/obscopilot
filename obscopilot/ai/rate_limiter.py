"""
Rate limiting and token usage tracking for AI services.

This module provides functionality to track token usage and implement rate limiting 
for OpenAI and other AI API calls.
"""

import time
import logging
from typing import Dict, Optional, List, Tuple
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token usage data for an API call."""
    
    timestamp: float
    prompt_tokens: int
    completion_tokens: int
    model: str
    total_cost: float


class RateLimiter:
    """Rate limiter for AI API calls with token tracking."""
    
    # Cost per 1K tokens for different models (in USD)
    DEFAULT_COSTS = {
        # OpenAI models
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
        "gpt-4-vision": {"prompt": 0.01, "completion": 0.03},
        # Google AI models
        "gemini-pro": {"prompt": 0.00025, "completion": 0.0005},
        "gemini-pro-vision": {"prompt": 0.0025, "completion": 0.005},
    }
    
    def __init__(self, max_tokens_per_minute: int = 90000, max_requests_per_minute: int = 60):
        """Initialize the rate limiter.
        
        Args:
            max_tokens_per_minute: Maximum tokens allowed per minute
            max_requests_per_minute: Maximum requests allowed per minute
        """
        self.max_tokens_per_minute = max_tokens_per_minute
        self.max_requests_per_minute = max_requests_per_minute
        
        # Track requests and token usage over time
        self.request_timestamps: List[float] = []
        self.token_usage_history: List[TokenUsage] = []
        
        # Track total usage by model
        self.model_usage: Dict[str, Dict[str, int]] = {}
        
        # Track total cost
        self.total_cost: float = 0.0
        
        # For thread safety
        self._lock = threading.RLock()
    
    def check_rate_limit(self) -> Tuple[bool, Optional[float]]:
        """Check if the current request exceeds rate limits.
        
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        with self._lock:
            current_time = time.time()
            minute_ago = current_time - 60
            
            # Clean up old timestamps
            self.request_timestamps = [t for t in self.request_timestamps if t > minute_ago]
            
            # Check request rate limit
            if len(self.request_timestamps) >= self.max_requests_per_minute:
                oldest = self.request_timestamps[0]
                retry_after = 60 - (current_time - oldest)
                return False, max(0, retry_after)
            
            # Calculate token usage in the last minute
            recent_usage = [
                usage for usage in self.token_usage_history 
                if usage.timestamp > minute_ago
            ]
            total_tokens = sum(
                usage.prompt_tokens + usage.completion_tokens for usage in recent_usage
            )
            
            # Check token rate limit
            if total_tokens >= self.max_tokens_per_minute:
                oldest_usage = recent_usage[0].timestamp if recent_usage else minute_ago
                retry_after = 60 - (current_time - oldest_usage)
                return False, max(0, retry_after)
            
            # Request is allowed, add current timestamp
            self.request_timestamps.append(current_time)
            return True, None
    
    def record_token_usage(
        self, 
        prompt_tokens: int, 
        completion_tokens: int, 
        model: str
    ) -> None:
        """Record token usage for an API call.
        
        Args:
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            model: Model name used for the API call
        """
        with self._lock:
            current_time = time.time()
            
            # Calculate cost
            model_costs = self.DEFAULT_COSTS.get(
                model, 
                {"prompt": 0.001, "completion": 0.002}  # Default costs if model not found
            )
            
            prompt_cost = (prompt_tokens / 1000) * model_costs["prompt"]
            completion_cost = (completion_tokens / 1000) * model_costs["completion"]
            total_cost = prompt_cost + completion_cost
            
            # Record usage
            usage = TokenUsage(
                timestamp=current_time,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model=model,
                total_cost=total_cost
            )
            
            self.token_usage_history.append(usage)
            
            # Update model usage statistics
            if model not in self.model_usage:
                self.model_usage[model] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "calls": 0,
                    "cost": 0.0
                }
            
            self.model_usage[model]["prompt_tokens"] += prompt_tokens
            self.model_usage[model]["completion_tokens"] += completion_tokens
            self.model_usage[model]["calls"] += 1
            self.model_usage[model]["cost"] += total_cost
            
            # Update total cost
            self.total_cost += total_cost
            
            # Clean up old usage data (keep last 24 hours)
            day_ago = current_time - 86400
            self.token_usage_history = [
                u for u in self.token_usage_history if u.timestamp > day_ago
            ]
    
    def get_usage_statistics(self) -> Dict:
        """Get usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        with self._lock:
            # Calculate time periods
            current_time = time.time()
            hour_ago = current_time - 3600
            day_ago = current_time - 86400
            
            # Get usage for different time periods
            last_hour_usage = [
                u for u in self.token_usage_history if u.timestamp > hour_ago
            ]
            last_day_usage = [
                u for u in self.token_usage_history if u.timestamp > day_ago
            ]
            
            # Calculate totals
            hour_tokens = sum(
                u.prompt_tokens + u.completion_tokens for u in last_hour_usage
            )
            hour_cost = sum(u.total_cost for u in last_hour_usage)
            
            day_tokens = sum(
                u.prompt_tokens + u.completion_tokens for u in last_day_usage
            )
            day_cost = sum(u.total_cost for u in last_day_usage)
            
            return {
                "total_cost": self.total_cost,
                "total_calls": sum(model["calls"] for model in self.model_usage.values()),
                "total_tokens": sum(
                    model["prompt_tokens"] + model["completion_tokens"] 
                    for model in self.model_usage.values()
                ),
                "by_model": self.model_usage,
                "last_hour": {
                    "tokens": hour_tokens,
                    "cost": hour_cost,
                    "calls": len(last_hour_usage)
                },
                "last_day": {
                    "tokens": day_tokens,
                    "cost": day_cost,
                    "calls": len(last_day_usage)
                }
            }


# Global instance for application-wide usage
rate_limiter = RateLimiter() 