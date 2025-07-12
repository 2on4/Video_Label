import logging
from typing import Optional

def setup_logging(log_file: str = 'app.log', level: int = logging.INFO) -> None:
    """Setup logging configuration.
    
    Args:
        log_file: Path to log file.
        level: Logging level.
    """
    logging.basicConfig(
        filename=log_file,
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info("Logging setup complete.")

def log_operation(operation: dict) -> None:
    """Log an operation for undo (appends to operations.json)."""
    import json
    try:
        with open('operations.json', 'a') as f:
            json.dump(operation, f)
            f.write('\n')
    except IOError as e:
        logging.error(f"Failed to log operation: {e}") 