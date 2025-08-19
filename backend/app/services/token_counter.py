"""
Token counting service for VoyageAI models.
Provides accurate token counting using tiktoken to respect API limits.
"""

import tiktoken
from typing import List, Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class VoyageTokenCounter:
    """Token-aware counting for VoyageAI models with safety margins."""
    
    # Model-specific encodings (VoyageAI uses OpenAI's tokenization)
    MODEL_ENCODINGS = {
        "voyage-large-2": "cl100k_base",
        "voyage-code-2": "cl100k_base", 
        "voyage-2": "cl100k_base",
        "voyage-lite-02-instruct": "cl100k_base",
    }
    
    def __init__(self, model_name: str):
        """
        Initialize token counter for specific VoyageAI model.
        
        Args:
            model_name: Name of the VoyageAI model (e.g., "voyage-large-2")
        """
        self.model_name = model_name
        self.encoding_name = self.MODEL_ENCODINGS.get(
            model_name, 
            "cl100k_base"  # Default encoding for unknown models
        )
        self.tokenizer = self._get_tokenizer(self.encoding_name)
        
        logger.info(f"Initialized token counter for model {model_name} with encoding {self.encoding_name}")
    
    @lru_cache(maxsize=16)
    def _get_tokenizer(self, encoding_name: str) -> tiktoken.Encoding:
        """Get cached tokenizer for encoding."""
        try:
            return tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.error(f"Failed to load encoding {encoding_name}: {e}")
            # Fallback to cl100k_base
            return tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """
        Count actual tokens for given text.
        
        Args:
            text: Input text to count tokens for
            
        Returns:
            Number of tokens in the text
        """
        if not text:
            return 0
            
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens for text: {e}")
            # Fallback estimation: ~4 chars per token
            return len(text) // 4
    
    def estimate_batch_tokens(self, texts: List[str]) -> int:
        """
        Estimate total tokens for a batch of texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            Total estimated tokens for all texts
        """
        return sum(self.count_tokens(text) for text in texts if text)
    
    def can_fit_in_limit(self, texts: List[str], token_limit: int = 9500) -> bool:
        """
        Check if texts can fit within token limit.
        
        Args:
            texts: List of text strings
            token_limit: Maximum allowed tokens (default: 9500 for safety)
            
        Returns:
            True if texts fit within limit
        """
        total_tokens = self.estimate_batch_tokens(texts)
        return total_tokens <= token_limit
    
    def find_max_batch_size(
        self, 
        texts: List[str], 
        token_limit: int = 9500,
        start_index: int = 0
    ) -> int:
        """
        Find maximum number of texts that fit within token limit.
        
        Args:
            texts: List of text strings to batch
            token_limit: Maximum allowed tokens
            start_index: Starting index in texts list
            
        Returns:
            Maximum number of texts that fit within limit
        """
        if start_index >= len(texts):
            return 0
            
        # Binary search for optimal batch size
        left, right = 1, min(len(texts) - start_index, 1000)  # Max 1000 chunks per batch
        best_size = 0
        
        while left <= right:
            mid = (left + right) // 2
            batch = texts[start_index:start_index + mid]
            
            if self.can_fit_in_limit(batch, token_limit):
                best_size = mid
                left = mid + 1
            else:
                right = mid - 1
        
        return max(best_size, 1)  # Always return at least 1 to avoid infinite loops


class AdaptiveBatchSizer:
    """Adapts batch sizes based on content analysis and token statistics."""
    
    def __init__(self):
        """Initialize adaptive batch sizer with default statistics."""
        self.avg_tokens_per_char = 0.25  # Initial estimate
        self.sample_count = 0
        self.max_samples = 1000  # Limit samples to prevent memory growth
        
    def update_statistics(self, text: str, actual_tokens: int):
        """
        Update token/character ratio based on real data.
        
        Args:
            text: The text that was tokenized
            actual_tokens: Actual token count from tokenizer
        """
        char_count = len(text)
        if char_count > 0:
            ratio = actual_tokens / char_count
            
            # Use exponential moving average for recent samples
            if self.sample_count == 0:
                self.avg_tokens_per_char = ratio
            else:
                # Weight recent samples more heavily
                alpha = min(0.1, 1.0 / self.sample_count)
                self.avg_tokens_per_char = (
                    alpha * ratio + (1 - alpha) * self.avg_tokens_per_char
                )
            
            self.sample_count = min(self.sample_count + 1, self.max_samples)
    
    def estimate_tokens_fast(self, text: str) -> int:
        """
        Fast token estimation based on character count and learned ratio.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return int(len(text) * self.avg_tokens_per_char)
    
    def estimate_batch_capacity(
        self, 
        remaining_texts: List[str], 
        token_limit: int = 9500,
        chunk_limit: int = 950
    ) -> int:
        """
        Estimate how many texts can fit in next batch.
        
        Args:
            remaining_texts: List of remaining texts to process
            token_limit: Maximum tokens per batch
            chunk_limit: Maximum chunks per batch
            
        Returns:
            Estimated number of texts that can fit
        """
        if not remaining_texts:
            return 0
        
        # Sample first 100 texts to estimate capacity
        sample_size = min(100, len(remaining_texts))
        sample_texts = remaining_texts[:sample_size]
        
        # Estimate total tokens for sample
        estimated_tokens = sum(
            self.estimate_tokens_fast(text) for text in sample_texts
        )
        
        if estimated_tokens <= token_limit:
            # All sampled texts fit, return min of sample size and chunk limit
            return min(len(remaining_texts), chunk_limit)
        
        # Calculate how many texts would fit based on average
        avg_tokens_per_text = estimated_tokens / sample_size
        estimated_capacity = int(token_limit / avg_tokens_per_text)
        
        # Apply safety margin and chunk limit
        return min(
            max(1, int(estimated_capacity * 0.9)),  # 10% safety margin
            chunk_limit,
            len(remaining_texts)
        )


# Convenience function for easy token counting
@lru_cache(maxsize=8)
def get_token_counter(model_name: str) -> VoyageTokenCounter:
    """Get cached token counter instance for model."""
    return VoyageTokenCounter(model_name)


def count_tokens(text: str, model_name: str = "voyage-large-2") -> int:
    """
    Convenience function to count tokens for a single text.
    
    Args:
        text: Text to count tokens for
        model_name: VoyageAI model name
        
    Returns:
        Number of tokens in the text
    """
    counter = get_token_counter(model_name)
    return counter.count_tokens(text)


def estimate_batch_tokens(texts: List[str], model_name: str = "voyage-large-2") -> int:
    """
    Convenience function to estimate tokens for a batch of texts.
    
    Args:
        texts: List of texts
        model_name: VoyageAI model name
        
    Returns:
        Total estimated tokens
    """
    counter = get_token_counter(model_name)
    return counter.estimate_batch_tokens(texts)