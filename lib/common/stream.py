"""Stream configuration and utilities."""

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class StreamConfig:
    """Configuration for audio stream processing.
    
    Defines the sampling rate, processing rate, and audio format for
    stream processing pipelines. Provides validation and derived properties.
    
    Attributes:
        sample_rate: Audio sampling rate in Hz.
        rate: Processing rate in Hz.
        format: Audio format (default "float32").
    """

    sample_rate: int
    rate: int
    format: str = "float32"

    def __post_init__(self) -> None:
        """Validate StreamConfig after initialization.
        
        Raises:
            ValueError: If sample_rate not divisible by rate, or invalid values.
        """
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.rate <= 0:
            raise ValueError("rate must be positive")
        if self.sample_rate % self.rate != 0:
            raise ValueError(
                f"sample_rate ({self.sample_rate}) must be divisible by "
                f"rate ({self.rate})"
            )
        if self.format != "float32":
            raise ValueError(f"Unsupported format: {self.format}")

    @property
    def block_size(self) -> int:
        """Compute block size from sample_rate and rate.
        
        Returns:
            Number of samples per processing block.
        """
        return self.sample_rate // self.rate

    @classmethod
    def from_file(cls, path: str) -> "StreamConfig":
        """Load StreamConfig from JSON file.
        
        Args:
            path: Path to JSON configuration file.
            
        Returns:
            StreamConfig instance loaded and validated from file.
            
        Raises:
            FileNotFoundError: If file does not exist.
            json.JSONDecodeError: If JSON is invalid.
            ValueError: If validation fails.
        """
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)
