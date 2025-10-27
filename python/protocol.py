"""
Protocol definitions for Canteen P2P communication.

Defines message formats for deployment commands sent over libp2p streams.
"""
import json
from typing import Optional
from dataclasses import dataclass, asdict


# Protocol ID for deployment commands
DEPLOYMENT_PROTOCOL_ID = "/canteen/deployment/1.0.0"


@dataclass
class DeploymentRequest:
    """Request to deploy a Docker image."""
    action: str  # "deploy" or "undeploy"
    image: str
    replicas: int = 1
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self))
    
    @staticmethod
    def from_json(data: str) -> 'DeploymentRequest':
        """Deserialize from JSON."""
        obj = json.loads(data)
        return DeploymentRequest(**obj)
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes for stream transmission."""
        json_str = self.to_json()
        # Length-prefixed message: 4 bytes length + JSON data
        length = len(json_str).to_bytes(4, byteorder='big')
        return length + json_str.encode('utf-8')
    
    @staticmethod
    def from_bytes(data: bytes) -> 'DeploymentRequest':
        """Deserialize from bytes."""
        # First 4 bytes are length
        length = int.from_bytes(data[:4], byteorder='big')
        json_str = data[4:4+length].decode('utf-8')
        return DeploymentRequest.from_json(json_str)


@dataclass
class DeploymentResponse:
    """Response to a deployment request."""
    success: bool
    message: str
    image: Optional[str] = None
    replicas: Optional[int] = None
    error: Optional[str] = None
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self))
    
    @staticmethod
    def from_json(data: str) -> 'DeploymentResponse':
        """Deserialize from JSON."""
        obj = json.loads(data)
        return DeploymentResponse(**obj)
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes for stream transmission."""
        json_str = self.to_json()
        length = len(json_str).to_bytes(4, byteorder='big')
        return length + json_str.encode('utf-8')
    
    @staticmethod
    def from_bytes(data: bytes) -> 'DeploymentResponse':
        """Deserialize from bytes."""
        length = int.from_bytes(data[:4], byteorder='big')
        json_str = data[4:4+length].decode('utf-8')
        return DeploymentResponse.from_json(json_str)


@dataclass
class StatusRequest:
    """Request cluster status."""
    action: str = "status"
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        json_str = json.dumps({"action": self.action})
        length = len(json_str).to_bytes(4, byteorder='big')
        return length + json_str.encode('utf-8')


@dataclass
class StatusResponse:
    """Response with cluster status."""
    success: bool
    total_members: int
    connected_count: int
    members: list
    error: Optional[str] = None
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        json_str = json.dumps(asdict(self))
        length = len(json_str).to_bytes(4, byteorder='big')
        return length + json_str.encode('utf-8')
    
    @staticmethod
    def from_bytes(data: bytes) -> 'StatusResponse':
        """Deserialize from bytes."""
        length = int.from_bytes(data[:4], byteorder='big')
        json_str = data[4:4+length].decode('utf-8')
        obj = json.loads(json_str)
        return StatusResponse(**obj)
