"""
Common Utilities
"""

import hashlib
import json
from typing import Dict, Any
import uuid
from datetime import datetime


def generate_request_id(prefix: str = "req") -> str:
    """Generate unique request ID"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def calculate_features_hash(features: Dict[str, Any]) -> str:
    """Calculate hash of features for caching"""
    features_str = json.dumps(features, sort_keys=True)
    return hashlib.sha256(features_str.encode()).hexdigest()


def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO 8601"""
    return dt.isoformat() + "Z"


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO 8601 timestamp"""
    if timestamp_str.endswith("Z"):
        timestamp_str = timestamp_str[:-1]
    return datetime.fromisoformat(timestamp_str)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    import re
    # Remove or replace unsafe characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = filename.replace(' ', '_')
    return filename[:255]  # Limit length


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def generate_s3_key(prefix: str, filename: str, user_id: str) -> str:
    """Generate S3 object key"""
    timestamp = datetime.utcnow().strftime("%Y/%m/%d")
    safe_filename = sanitize_filename(filename)
    unique_id = uuid.uuid4().hex[:8]
    return f"{prefix}/{timestamp}/{user_id}/{unique_id}_{safe_filename}"
