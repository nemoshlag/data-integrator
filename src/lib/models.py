from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from aws_lambda_powertools import Logger

logger = Logger()

@dataclass
class DynamoDBModel:
    """Base class for DynamoDB models."""
    @property
    def pk(self) -> str:
        """Get the partition key."""
        raise NotImplementedError

    @property
    def sk(self) -> str:
        """Get the sort key."""
        raise NotImplementedError

    def to_item(self) -> dict:
        """Convert to DynamoDB item."""
        return {
            'PK': self.pk,
            'SK': self.sk,
            **{k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        }

    @classmethod
    def from_item(cls, item: dict):
        """Create instance from DynamoDB item."""
        # Remove DynamoDB keys
        data = {k: v for k, v in item.items() if k not in ['PK', 'SK']}
        return cls(**data)

@dataclass
class Patient(DynamoDBModel):
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    updated_at: str = datetime.now().isoformat()

    @property
    def pk(self) -> str:
        return f"PATIENT#{self.patient_id}"

    @property
    def sk(self) -> str:
        return "METADATA"

@dataclass
class Admission(DynamoDBModel):
    patient_id: str
    admission_id: str
    admission_date: str
    ward: str
    bed_number: str
    status: str
    last_test_date: Optional[str] = None
    hours_since_test: Optional[int] = None
    updated_at: str = datetime.now().isoformat()

    @property
    def pk(self) -> str:
        return f"PATIENT#{self.patient_id}"

    @property
    def sk(self) -> str:
        return f"ADMISSION#{self.admission_id}"

    @property
    def needs_attention(self) -> bool:
        """Check if patient needs attention."""
        if self.status != 'Active':
            return False
        if not self.last_test_date:
            return True
        last_test = datetime.fromisoformat(self.last_test_date)
        hours = (datetime.now() - last_test).total_seconds() / 3600
        return hours >= 48

@dataclass
class LabTest(DynamoDBModel):
    test_id: str
    patient_id: str
    admission_id: str
    test_type: str
    test_date: str
    result: str
    status: str
    lab_location: str
    updated_at: str = datetime.now().isoformat()

    @property
    def pk(self) -> str:
        return f"ADMISSION#{self.admission_id}"

    @property
    def sk(self) -> str:
        return f"TEST#{self.test_date}#{self.test_id}"

# Custom Exceptions
class ModelValidationError(Exception):
    """Raised when model validation fails."""
    pass

class ModelNotFoundError(Exception):
    """Raised when model is not found in DynamoDB."""
    pass

# Helper Functions
def validate_iso_date(date_str: str) -> bool:
    """Validate ISO format date string."""
    try:
        datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False

def calculate_hours_since(date_str: str) -> float:
    """Calculate hours since given date."""
    if not date_str:
        return float('inf')
    date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    return (datetime.now() - date).total_seconds() / 3600