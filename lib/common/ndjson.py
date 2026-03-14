"""NDJSON reader and writer for streaming data."""

import json
from typing import Any, Iterator, TextIO


class NdjsonReader:
    """Iterator for reading NDJSON (newline-delimited JSON) streams.
    
    Reads JSON objects, one per line, from a text stream. Skips empty lines
    and raises ValueError for malformed JSON with line number information.
    """

    def __init__(self, stream: TextIO) -> None:
        """Initialize NdjsonReader.
        
        Args:
            stream: Text input stream to read from.
        """
        self.stream = stream
        self._line_num = 0

    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Iterate over JSON records in the stream.
        
        Yields:
            Parsed JSON object as a dictionary.
            
        Raises:
            ValueError: If a line contains invalid JSON.
        """
        for line in self.stream:
            self._line_num += 1
            line = line.rstrip('\n\r')
            
            # Skip empty lines
            if not line:
                continue
            
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON at line {self._line_num}: {e}"
                ) from e


class NdjsonWriter:
    """Writer for NDJSON (newline-delimited JSON) streams.
    
    Writes JSON objects, one per line, to a text stream with automatic
    flushing for streaming scenarios.
    """

    def __init__(self, stream: TextIO) -> None:
        """Initialize NdjsonWriter.
        
        Args:
            stream: Text output stream to write to.
        """
        self.stream = stream

    def write(self, record: dict[str, Any]) -> None:
        """Write a JSON record followed by newline.
        
        Args:
            record: Dictionary to serialize and write.
        """
        self.stream.write(json.dumps(record) + '\n')
        self.stream.flush()
