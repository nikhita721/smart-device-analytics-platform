"""
WebSocket Server for Live IoT Data Streaming
Provides real-time data streaming via WebSocket connections
"""

import asyncio
import json
import logging
import websockets
from websockets.server import WebSocketServerProtocol
from datetime import datetime
import threading
import queue
import time
from typing import Dict, List, Set
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_ingestion.live_kafka_consumer import initialize_live_streaming, get_live_data, get_live_metrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiveStreamingWebSocketServer:
    """
    WebSocket server for live IoT data streaming
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.data_queue = queue.Queue(maxsize=1000)
        self.is_running = False
        
        # Initialize live streaming
        try:
            self.consumer, self.processor = initialize_live_streaming()
            logger.info("Live streaming initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize live streaming: {e}")
            self.consumer = None
            self.processor = None
    
    async def register_client(self, websocket: WebSocketServerProtocol):
        """Register a new WebSocket client"""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        # Send initial data
        try:
            initial_data = {
                'type': 'connection',
                'message': 'Connected to live IoT data stream',
                'timestamp': datetime.now().isoformat(),
                'server_info': {
                    'host': self.host,
                    'port': self.port,
                    'clients': len(self.clients)
                }
            }
            await websocket.send(json.dumps(initial_data))
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
    
    async def unregister_client(self, websocket: WebSocketServerProtocol):
        """Unregister a WebSocket client"""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle WebSocket client connection"""
        await self.register_client(websocket)
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.process_client_message(websocket, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error processing client message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client connection closed")
        except Exception as e:
            logger.error(f"Error in client handler: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def process_client_message(self, websocket: WebSocketServerProtocol, data: Dict):
        """Process messages from WebSocket clients"""
        message_type = data.get('type', 'unknown')
        
        if message_type == 'ping':
            # Respond to ping with pong
            response = {
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            }
            await websocket.send(json.dumps(response))
        
        elif message_type == 'subscribe':
            # Client wants to subscribe to specific data types
            subscription = data.get('subscription', {})
            logger.info(f"Client subscription: {subscription}")
            
            response = {
                'type': 'subscription_confirmed',
                'subscription': subscription,
                'timestamp': datetime.now().isoformat()
            }
            await websocket.send(json.dumps(response))
        
        elif message_type == 'get_metrics':
            # Client requests current metrics
            metrics = get_live_metrics()
            response = {
                'type': 'metrics',
                'data': metrics,
                'timestamp': datetime.now().isoformat()
            }
            await websocket.send(json.dumps(response))
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def broadcast_data(self, data: Dict):
        """Broadcast data to all connected clients"""
        if not self.clients:
            return
        
        message = json.dumps(data)
        disconnected_clients = set()
        
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.clients.discard(client)
    
    def data_producer_thread(self):
        """Background thread to produce data for WebSocket clients"""
        while self.is_running:
            try:
                # Get live data
                live_data = get_live_data()
                if live_data:
                    # Prepare data for broadcasting
                    broadcast_data = {
                        'type': 'iot_data',
                        'data': live_data,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Add to queue for async processing
                    if not self.data_queue.full():
                        self.data_queue.put(broadcast_data)
                
                time.sleep(0.1)  # 10 messages per second
                
            except Exception as e:
                logger.error(f"Error in data producer thread: {e}")
                time.sleep(1)
    
    async def data_consumer_loop(self):
        """Async loop to consume data from queue and broadcast"""
        while self.is_running:
            try:
                # Get data from queue (non-blocking)
                if not self.data_queue.empty():
                    data = self.data_queue.get_nowait()
                    await self.broadcast_data(data)
                
                # Also broadcast metrics periodically
                if len(self.clients) > 0:
                    metrics = get_live_metrics()
                    if metrics:
                        metrics_data = {
                            'type': 'metrics_update',
                            'data': metrics,
                            'timestamp': datetime.now().isoformat()
                        }
                        await self.broadcast_data(metrics_data)
                
                await asyncio.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                logger.error(f"Error in data consumer loop: {e}")
                await asyncio.sleep(1)
    
    async def start_server(self):
        """Start the WebSocket server"""
        self.is_running = True
        
        # Start data producer thread
        producer_thread = threading.Thread(target=self.data_producer_thread, daemon=True)
        producer_thread.start()
        
        # Start data consumer loop
        consumer_task = asyncio.create_task(self.data_consumer_loop())
        
        # Start WebSocket server
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info(f"WebSocket server running on ws://{self.host}:{self.port}")
            await asyncio.gather(consumer_task)
    
    def stop_server(self):
        """Stop the WebSocket server"""
        self.is_running = False
        logger.info("WebSocket server stopped")

# Global server instance
websocket_server = None

def start_websocket_server(host: str = "localhost", port: int = 8765):
    """Start the WebSocket server"""
    global websocket_server
    
    if websocket_server and websocket_server.is_running:
        logger.warning("WebSocket server is already running")
        return
    
    websocket_server = LiveStreamingWebSocketServer(host, port)
    
    try:
        asyncio.run(websocket_server.start_server())
    except KeyboardInterrupt:
        logger.info("WebSocket server stopped by user")
    except Exception as e:
        logger.error(f"Error starting WebSocket server: {e}")
    finally:
        if websocket_server:
            websocket_server.stop_server()

if __name__ == "__main__":
    # Start WebSocket server
    start_websocket_server()
