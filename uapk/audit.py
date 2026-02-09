"""
Tamper-Evident Audit System
Provides append-only audit logging with hash chaining for non-repudiation.
M1.2: Added Ed25519 signatures on each audit event.
"""
import hashlib
import json
import uuid
import base64
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from uapk.cas import compute_merkle_root

# M1.2: Ed25519 signing support
try:
    from uapk.core.ed25519_keys import get_private_key, get_public_key
    from cryptography.exceptions import InvalidSignature
    ED25519_AVAILABLE = True
except ImportError:
    ED25519_AVAILABLE = False


class AuditLog:
    """
    Tamper-evident audit log with hash chaining.
    Each event links to the previous event via previousHash.
    """

    def __init__(self, log_path: str = "runtime/audit.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_hash: Optional[str] = None
        self._load_last_hash()

    def _load_last_hash(self):
        """Load the hash of the last event from the log"""
        if not self.log_path.exists():
            return

        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_event = json.loads(lines[-1])
                    self.last_hash = last_event.get('eventHash')
        except Exception:
            # If we can't load, start fresh
            pass

    def _compute_event_hash(self, event: Dict[str, Any]) -> str:
        """
        Compute hash of an event (canonical JSON).
        Hash includes: eventId, timestamp, eventType, action, params, result, decision, previousHash
        M1.2: Does NOT include eventSignature (signature is computed after hash).
        """
        # Create canonical representation
        canonical_fields = {
            'eventId': event['eventId'],
            'timestamp': event['timestamp'],
            'eventType': event['eventType'],
            'agentId': event.get('agentId', ''),
            'userId': event.get('userId', ''),
            'action': event['action'],
            'params': event.get('params', {}),
            'result': event.get('result'),
            'decision': event.get('decision', ''),
            'previousHash': event.get('previousHash', '')
        }

        # Canonical JSON
        canonical_json = json.dumps(canonical_fields, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    def _sign_event(self, event: Dict[str, Any]) -> str:
        """
        M1.2: Sign event with Ed25519 gateway private key.
        Signs canonical JSON of event (excluding eventSignature field itself).
        Returns base64-encoded signature.
        """
        if not ED25519_AVAILABLE:
            return ""

        # Create canonical JSON (exclude eventSignature, eventHash already computed)
        canonical_fields = {
            'eventId': event['eventId'],
            'timestamp': event['timestamp'],
            'eventType': event['eventType'],
            'agentId': event.get('agentId', ''),
            'userId': event.get('userId', ''),
            'action': event['action'],
            'params': event.get('params', {}),
            'result': event.get('result'),
            'decision': event.get('decision', ''),
            'previousHash': event.get('previousHash', ''),
            'eventHash': event['eventHash']
        }

        canonical_json = json.dumps(canonical_fields, sort_keys=True, separators=(',', ':'))
        message = canonical_json.encode('utf-8')

        # Sign with Ed25519
        try:
            private_key = get_private_key()
            signature = private_key.sign(message)
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            print(f"Warning: Failed to sign audit event: {e}")
            return ""

    def append_event(
        self,
        event_type: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        decision: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Append a new event to the audit log.
        M1.2: Now signs each event with Ed25519 gateway signature.
        Returns the complete event with hash and signature.
        """
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        timestamp = datetime.utcnow().isoformat() + "Z"

        event = {
            'eventId': event_id,
            'timestamp': timestamp,
            'eventType': event_type,
            'agentId': agent_id,
            'userId': user_id,
            'action': action,
            'params': params or {},
            'result': result,
            'decision': decision,
            'previousHash': self.last_hash or '',
            'eventHash': ''
        }

        # Compute hash
        event_hash = self._compute_event_hash(event)
        event['eventHash'] = event_hash

        # M1.2: Sign event with Ed25519 (if available)
        if ED25519_AVAILABLE:
            event['eventSignature'] = self._sign_event(event)
        else:
            event['eventSignature'] = None

        # Write to log (append-only)
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(event, separators=(',', ':')) + '\n')

        # Update last hash
        self.last_hash = event_hash

        return event

    def verify_chain(self) -> Dict[str, Any]:
        """
        Verify the integrity of the hash chain.
        Returns verification report.
        """
        if not self.log_path.exists():
            return {'valid': True, 'eventCount': 0, 'message': 'No events'}

        events: List[Dict[str, Any]] = []
        with open(self.log_path, 'r') as f:
            for line in f:
                events.append(json.loads(line.strip()))

        if not events:
            return {'valid': True, 'eventCount': 0, 'message': 'No events'}

        # Verify each event
        expected_previous = ''
        for i, event in enumerate(events):
            # Check previous hash links correctly
            if event['previousHash'] != expected_previous:
                return {
                    'valid': False,
                    'eventCount': len(events),
                    'failedAt': i,
                    'message': f"Hash chain broken at event {i}: expected previous {expected_previous}, got {event['previousHash']}"
                }

            # Recompute hash
            recomputed = self._compute_event_hash(event)
            if recomputed != event['eventHash']:
                return {
                    'valid': False,
                    'eventCount': len(events),
                    'failedAt': i,
                    'message': f"Event hash mismatch at event {i}"
                }

            expected_previous = event['eventHash']

        return {
            'valid': True,
            'eventCount': len(events),
            'message': 'Hash chain verified successfully'
        }

    def get_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve events from the log"""
        if not self.log_path.exists():
            return []

        events = []
        with open(self.log_path, 'r') as f:
            for line in f:
                events.append(json.loads(line.strip()))

        if limit:
            return events[-limit:]
        return events

    def compute_merkle_root(self) -> str:
        """Compute Merkle root of all event hashes"""
        events = self.get_events()
        if not events:
            return ""

        event_hashes = [e['eventHash'] for e in events]
        return compute_merkle_root(event_hashes)

    def verify_signatures(self) -> Dict[str, Any]:
        """
        M1.2: Verify Ed25519 signatures on all audit events.
        Returns verification report with counts and any failed events.
        """
        if not ED25519_AVAILABLE:
            return {
                'valid': False,
                'verified_count': 0,
                'failed_count': 0,
                'message': 'Ed25519 not available (cryptography module not installed)'
            }

        events = self.get_events()
        if not events:
            return {'valid': True, 'verified_count': 0, 'failed_count': 0, 'message': 'No events to verify'}

        try:
            public_key = get_public_key()
        except Exception as e:
            return {
                'valid': False,
                'verified_count': 0,
                'failed_count': len(events),
                'message': f'Failed to load public key: {e}'
            }

        verified_count = 0
        failed_events = []

        for i, event in enumerate(events):
            event_signature = event.get('eventSignature')

            if not event_signature:
                failed_events.append({
                    'index': i,
                    'eventId': event.get('eventId'),
                    'reason': 'No signature present'
                })
                continue

            # Reconstruct canonical JSON (exclude eventSignature)
            canonical_fields = {
                'eventId': event['eventId'],
                'timestamp': event['timestamp'],
                'eventType': event['eventType'],
                'agentId': event.get('agentId', ''),
                'userId': event.get('userId', ''),
                'action': event['action'],
                'params': event.get('params', {}),
                'result': event.get('result'),
                'decision': event.get('decision', ''),
                'previousHash': event.get('previousHash', ''),
                'eventHash': event['eventHash']
            }

            canonical_json = json.dumps(canonical_fields, sort_keys=True, separators=(',', ':'))
            message = canonical_json.encode('utf-8')

            # Verify signature
            try:
                signature = base64.b64decode(event_signature)
                public_key.verify(signature, message)
                verified_count += 1
            except InvalidSignature:
                failed_events.append({
                    'index': i,
                    'eventId': event.get('eventId'),
                    'reason': 'Invalid Ed25519 signature'
                })
            except Exception as e:
                failed_events.append({
                    'index': i,
                    'eventId': event.get('eventId'),
                    'reason': f'Verification error: {str(e)}'
                })

        failed_count = len(failed_events)
        all_valid = (failed_count == 0)

        return {
            'valid': all_valid,
            'verified_count': verified_count,
            'failed_count': failed_count,
            'failed_events': failed_events[:10] if failed_events else [],  # Limit to first 10
            'message': f'Verified {verified_count}/{len(events)} signatures' + ('' if all_valid else f', {failed_count} failed')
        }


# Global audit log instance
_audit_log: Optional[AuditLog] = None


def get_audit_log() -> AuditLog:
    """Get the global audit log instance"""
    global _audit_log
    if _audit_log is None:
        _audit_log = AuditLog()
    return _audit_log


def audit_event(
    event_type: str,
    action: str,
    params: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    decision: Optional[str] = None,
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Convenience function to log an audit event"""
    return get_audit_log().append_event(
        event_type=event_type,
        action=action,
        params=params,
        result=result,
        decision=decision,
        agent_id=agent_id,
        user_id=user_id
    )
