"""
Scaling Examples for AI Engineering Pipeline
Demonstrates various scaling strategies
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from multiprocessing import Pool
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DistributedDataProcessing:
    """Example: Distributed Data Processing"""
    
    @staticmethod
    def process_chunk(chunk_data: pd.DataFrame) -> pd.DataFrame:
        """Process a chunk of data"""
        # Simulate processing
        processed = chunk_data.copy()
        processed['processed'] = processed.sum(axis=1)
        time.sleep(0.1)  # Simulate work
        return processed
    
    def process_parallel(self, data: pd.DataFrame, n_workers: int = 4) -> pd.DataFrame:
        """Process data in parallel using multiprocessing"""
        logger.info(f"Processing data with {n_workers} workers")
        
        # Split data into chunks
        chunk_size = len(data) // n_workers
        chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
        
        # Process in parallel
        with Pool(processes=n_workers) as pool:
            results = pool.map(self.process_chunk, chunks)
        
        # Combine results
        processed_data = pd.concat(results, ignore_index=True)
        logger.info(f"Processed {len(processed_data)} records")
        return processed_data


class AsyncModelServing:
    """Example: Async Model Serving for High Throughput"""
    
    def __init__(self, model):
        self.model = model
        self.request_queue = asyncio.Queue()
        self.results = {}
        
    async def predict_async(self, request_id: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """Async prediction"""
        # Simulate async processing
        await asyncio.sleep(0.01)  # Simulate I/O
        
        # Convert to DataFrame
        df = pd.DataFrame([features])
        
        # Make prediction (this would be async in real implementation)
        prediction = self.model.predict(df)[0]
        
        return {
            'request_id': request_id,
            'prediction': int(prediction),
            'timestamp': time.time()
        }
    
    async def batch_predict(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple requests concurrently"""
        logger.info(f"Processing {len(requests)} requests concurrently")
        
        tasks = [
            self.predict_async(req['request_id'], req['features'])
            for req in requests
        ]
        
        results = await asyncio.gather(*tasks)
        logger.info(f"Completed {len(results)} predictions")
        return results


class LoadBalancer:
    """Example: Simple Load Balancer for Model Serving"""
    
    def __init__(self, model_instances: List[Any]):
        self.instances = model_instances
        self.current_index = 0
        self.request_counts = [0] * len(model_instances)
        
    def get_instance(self, strategy: str = 'round_robin') -> Any:
        """Get model instance based on load balancing strategy"""
        if strategy == 'round_robin':
            instance = self.instances[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.instances)
            self.request_counts[self.current_index] += 1
            return instance
        
        elif strategy == 'least_connections':
            # Return instance with least requests
            min_index = self.request_counts.index(min(self.request_counts))
            self.request_counts[min_index] += 1
            return self.instances[min_index]
        
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    def predict(self, features: Dict[str, Any], strategy: str = 'round_robin') -> Dict[str, Any]:
        """Route prediction to appropriate instance"""
        instance = self.get_instance(strategy)
        df = pd.DataFrame([features])
        prediction = instance.predict(df)[0]
        return {'prediction': int(prediction)}


class CachingLayer:
    """Example: Caching Layer for Model Predictions"""
    
    def __init__(self, model, cache_size: int = 1000):
        self.model = model
        self.cache = {}
        self.cache_size = cache_size
        self.hits = 0
        self.misses = 0
        
    def _hash_features(self, features: Dict[str, Any]) -> str:
        """Create hash key from features"""
        import hashlib
        feature_str = str(sorted(features.items()))
        return hashlib.md5(feature_str.encode()).hexdigest()
    
    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Predict with caching"""
        cache_key = self._hash_features(features)
        
        # Check cache
        if cache_key in self.cache:
            self.hits += 1
            logger.debug("Cache hit")
            return self.cache[cache_key]
        
        # Cache miss - compute prediction
        self.misses += 1
        df = pd.DataFrame([features])
        prediction = self.model.predict(df)[0]
        probability = self.model.predict_proba(df)[0].tolist()
        
        result = {
            'prediction': int(prediction),
            'probability': probability
        }
        
        # Add to cache (with LRU eviction if needed)
        if len(self.cache) >= self.cache_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[cache_key] = result
        return result
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        
        return {
            'cache_size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate
        }


class BatchProcessor:
    """Example: Batch Processing for Efficient Inference"""
    
    def __init__(self, model, batch_size: int = 32, max_wait_time: float = 0.1):
        self.model = model
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.batch_queue = []
        self.last_batch_time = time.time()
        
    def add_request(self, features: Dict[str, Any]) -> None:
        """Add request to batch queue"""
        self.batch_queue.append(features)
        
        # Process batch if full or timeout
        should_process = (
            len(self.batch_queue) >= self.batch_size or
            (time.time() - self.last_batch_time) >= self.max_wait_time
        )
        
        if should_process and self.batch_queue:
            self._process_batch()
    
    def _process_batch(self):
        """Process current batch"""
        if not self.batch_queue:
            return
        
        batch = self.batch_queue[:self.batch_size]
        self.batch_queue = self.batch_queue[self.batch_size:]
        
        # Convert to DataFrame
        df = pd.DataFrame(batch)
        
        # Batch prediction
        predictions = self.model.predict(df)
        probabilities = self.model.predict_proba(df)
        
        logger.info(f"Processed batch of {len(batch)} requests")
        self.last_batch_time = time.time()
        
        return predictions, probabilities


class AutoScaler:
    """Example: Auto-scaling Logic"""
    
    def __init__(self, min_instances: int = 1, max_instances: int = 10,
                 target_cpu: float = 0.7, scale_up_threshold: float = 0.8,
                 scale_down_threshold: float = 0.5):
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.target_cpu = target_cpu
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.current_instances = min_instances
        
    def should_scale(self, metrics: Dict[str, float]) -> int:
        """Determine if scaling is needed"""
        cpu_usage = metrics.get('cpu_usage', 0)
        request_rate = metrics.get('request_rate', 0)
        avg_latency = metrics.get('avg_latency_ms', 0)
        
        # Scale up conditions
        if (cpu_usage > self.scale_up_threshold or 
            avg_latency > 1000 or  # Latency > 1s
            request_rate > 100):  # High request rate
            if self.current_instances < self.max_instances:
                new_instances = min(
                    self.current_instances + 1,
                    self.max_instances
                )
                logger.info(f"Scaling up: {self.current_instances} -> {new_instances}")
                self.current_instances = new_instances
                return 1  # Scale up
        
        # Scale down conditions
        elif (cpu_usage < self.scale_down_threshold and
              avg_latency < 100 and
              request_rate < 10):
            if self.current_instances > self.min_instances:
                new_instances = max(
                    self.current_instances - 1,
                    self.min_instances
                )
                logger.info(f"Scaling down: {self.current_instances} -> {new_instances}")
                self.current_instances = new_instances
                return -1  # Scale down
        
        return 0  # No scaling needed


class DistributedTraining:
    """Example: Distributed Training Setup"""
    
    @staticmethod
    def train_on_chunk(chunk_data: tuple) -> Dict[str, Any]:
        """Train model on a data chunk (for distributed training)"""
        X_chunk, y_chunk = chunk_data
        
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(X_chunk, y_chunk)
        
        return {
            'model': model,
            'n_samples': len(X_chunk)
        }
    
    def train_distributed(self, X: pd.DataFrame, y: pd.Series, 
                         n_workers: int = 4) -> Any:
        """Train model using distributed approach"""
        logger.info(f"Training with {n_workers} workers")
        
        # Split data
        chunk_size = len(X) // n_workers
        chunks = [
            (X[i:i+chunk_size], y[i:i+chunk_size])
            for i in range(0, len(X), chunk_size)
        ]
        
        # Train on each chunk
        with Pool(processes=n_workers) as pool:
            results = pool.map(self.train_on_chunk, chunks)
        
        # Aggregate models (simple voting ensemble)
        models = [r['model'] for r in results]
        logger.info(f"Trained {len(models)} models")
        
        return models


# Example usage
if __name__ == "__main__":
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.datasets import make_classification
    
    # Generate sample data
    X, y = make_classification(n_samples=1000, n_features=10, random_state=42)
    X_df = pd.DataFrame(X)
    y_series = pd.Series(y)
    
    # Train a simple model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_df, y_series)
    
    print("=" * 50)
    print("Scaling Examples")
    print("=" * 50)
    
    # Example 1: Distributed Processing
    print("\n1. Distributed Data Processing")
    processor = DistributedDataProcessing()
    processed = processor.process_parallel(X_df, n_workers=4)
    
    # Example 2: Caching
    print("\n2. Caching Layer")
    cached_model = CachingLayer(model, cache_size=100)
    for i in range(10):
        features = X_df.iloc[i % 5].to_dict()  # Repeat some requests
        cached_model.predict(features)
    print(f"Cache stats: {cached_model.get_cache_stats()}")
    
    # Example 3: Load Balancing
    print("\n3. Load Balancing")
    instances = [model, model, model]  # Multiple instances
    lb = LoadBalancer(instances)
    for i in range(5):
        features = X_df.iloc[i].to_dict()
        result = lb.predict(features)
        print(f"Request {i+1}: {result}")
    
    # Example 4: Auto-scaling
    print("\n4. Auto-scaling")
    scaler = AutoScaler(min_instances=1, max_instances=5)
    test_metrics = [
        {'cpu_usage': 0.9, 'request_rate': 150, 'avg_latency_ms': 1200},
        {'cpu_usage': 0.3, 'request_rate': 5, 'avg_latency_ms': 50},
    ]
    for metrics in test_metrics:
        action = scaler.should_scale(metrics)
        print(f"Metrics: {metrics}, Action: {action}, Instances: {scaler.current_instances}")

