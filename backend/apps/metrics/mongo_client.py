import os
import logging
from datetime import datetime, timezone
from django.conf import settings

logger = logging.getLogger('netwatch.metrics.mongo')

# In-memory buffer for telemetry when MongoDB is not connected or in local development mode
_in_memory_telemetry = []

class MongoTelemetryClient:
    """
    MongoDB Telemetry client for high-throughput semi-structured time-series metrics.
    Provides graceful degradation with local in-memory circular buffer if Mongo is unreachable.
    """
    def __init__(self):
        self.uri = getattr(settings, 'MONGODB_URI', 'mongodb://localhost:27017/')
        self.db_name = getattr(settings, 'MONGODB_DB_NAME', 'netwatch_telemetry')
        self.enabled = getattr(settings, 'MONGODB_ENABLED', False)
        self.client = None
        self.db = None
        self._connected = False
        
        if self.enabled:
            self._connect()

    def _connect(self):
        try:
            import pymongo
            self.client = pymongo.MongoClient(self.uri, serverSelectionTimeoutMS=2000)
            # Trigger quick server ping
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self._connected = True
            logger.info("Connected successfully to MongoDB Telemetry store.")
        except Exception as e:
            self._connected = False
            logger.warning(f"MongoDB connection unavailable ({str(e)}). Using in-memory telemetry buffer.")

    def insert_metric(self, device_id: str, metric_type: str, value: float, unit: str = '', source: str = 'snmp', metadata: dict = None):
        """
        Record a time-series metric document.
        """
        doc = {
            'device_id': str(device_id),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metric_type': metric_type,
            'value': float(value),
            'unit': unit,
            'source': source,
            'metadata': metadata or {}
        }

        if self._connected and self.db is not None:
            try:
                self.db.telemetry_metrics.insert_one(doc)
                return True
            except Exception as e:
                logger.error(f"Failed to insert metric into MongoDB: {str(e)}")

        # Append to buffer (keep last 1000 items)
        _in_memory_telemetry.append(doc)
        if len(_in_memory_telemetry) > 1000:
            _in_memory_telemetry.pop(0)
        return True

    def get_device_metrics(self, device_id: str, metric_type: str = None, limit: int = 50):
        """
        Retrieve recent metrics for a device.
        """
        if self._connected and self.db is not None:
            try:
                query = {'device_id': str(device_id)}
                if metric_type:
                    query['metric_type'] = metric_type
                docs = list(self.db.telemetry_metrics.find(query, {'_id': 0}).sort('timestamp', -1).limit(limit))
                return docs
            except Exception as e:
                logger.error(f"Error querying MongoDB telemetry: {str(e)}")

        # Fallback query from in-memory buffer
        matches = [d for d in _in_memory_telemetry if d['device_id'] == str(device_id)]
        if metric_type:
            matches = [d for d in matches if d['metric_type'] == metric_type]
        matches.sort(key=lambda x: x['timestamp'], reverse=True)
        return matches[:limit]

# Singleton instance
telemetry_client = MongoTelemetryClient()
