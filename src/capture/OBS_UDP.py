import cv2
import socket
import threading
import time
import asyncio
import numpy as np
from typing import Optional, Callable, Tuple, Awaitable
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import logging

logger = logging.getLogger(__name__)

# Optional TurboJPEG for faster CPU JPEG decode
try:
    from turbojpeg import TurboJPEG, TJPF_BGR
    _jpeg = TurboJPEG()
except Exception:
    _jpeg = None


class OBS_UDP_Receiver:
    """
    OBS UDP receiver for MJPEG stream from OBS Studio
    Supports receiving Motion JPEG stream over UDP protocol
    """
    
    def __init__(self, ip: str = "192.168.0.1", port: int = 1234, target_fps: int = 60, max_workers: int = None):
        """
        Initialize OBS UDP receiver
        
        Args:
            ip: IP address to receive UDP stream from
            port: Port number to receive UDP stream on
            target_fps: Target FPS for processing (deprecated, kept for compatibility)
            max_workers: Maximum number of worker threads for frame processing (None = auto)
        """
        self.ip = ip
        self.port = port
        self.target_fps = target_fps  # Kept for compatibility, not used for limiting
        self.frame_interval = 1.0 / target_fps if target_fps > 0 else 0  # Not enforced
        
        # Connection state
        self.socket = None
        self.is_connected = False
        self.is_receiving = False
        
        # Threading / Async
        self.receive_thread = None
        self.stop_event = threading.Event()
        self._loop = None  # asyncio loop (background thread)
        self._loop_thread = None
        self._transport = None  # asyncio.DatagramTransport
        self._protocol = None   # protocol instance
        
        # Multi-threaded frame processing
        self.max_workers = max_workers if max_workers is not None else min(8, (threading.active_count() or 1) + 4)
        self.executor = None  # ThreadPoolExecutor for parallel frame decoding
        self.frame_queue = Queue(maxsize=100)  # Queue for decoded frames (max 100 frames)
        self.processing_lock = threading.Lock()  # Lock for processing stats
        
        # Frame processing
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.frame_callback = None
        self.frame_callback_async: Optional[Callable[[np.ndarray], Awaitable[None]]] = None
        
        # Performance monitoring
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.current_fps = 0.0
        self.processing_fps = 0.0
        self.last_processing_time = time.time()
        self.processing_counter = 0
        self.receive_delay = 0.0
        self.processing_delay = 0.0
        self.decoding_fps = 0.0
        self.decoding_counter = 0
        self.last_decoding_time = time.time()
        
        # MJPEG buffer - use bytearray for better performance
        self.mjpeg_buffer = bytearray()
        self.buffer_lock = threading.Lock()  # Thread-safe buffer access
        self.mjpeg_start_marker = b'\xff\xd8'  # JPEG start marker
        self.mjpeg_end_marker = b'\xff\xd9'    # JPEG end marker
        self.max_buffer_size = 2 * 1024 * 1024  # 2MB limit
        
        logger.info(f"OBS_UDP_Receiver initialized: {ip}:{port}, max_workers={self.max_workers}")
    
    def set_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """
        Set callback function for frame processing
        
        Args:
            callback: Function to call with each received frame
        """
        self.frame_callback = callback
    
    def set_frame_callback_async(self, callback: Callable[[np.ndarray], Awaitable[None]]):
        """
        Set async callback function for frame processing.
        The coroutine will be scheduled on the internal asyncio loop thread.
        """
        self.frame_callback_async = callback
    
    def connect(self) -> bool:
        """
        Connect to UDP stream
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self.is_connected:
                self.disconnect()
            
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Increase receive buffer size for high FPS streams
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
            self.socket.settimeout(5.0)  # 5 second timeout
            
            # Bind to receive UDP packets
            self.socket.bind((self.ip, self.port))
            
            self.is_connected = True
            self.stop_event.clear()
            
            # Start receiving thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            # Start thread pool executor for parallel frame decoding
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="FrameDecoder")
            
            # Start frame processing thread
            self.processing_thread = threading.Thread(target=self._frame_processing_loop, daemon=True)
            self.processing_thread.start()
            
            logger.info(f"Connected to UDP stream at {self.ip}:{self.port}")
            return True
            
        except OSError as e:
            logger.error(f"Failed to connect to UDP stream: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to UDP stream: {e}")
            self.is_connected = False
            return False

    # -------------------- Async version --------------------
    class _UDPProtocol(asyncio.DatagramProtocol):
        """Asyncio protocol to receive UDP datagrams and forward to receiver."""
        def __init__(self, receiver: "OBS_UDP_Receiver"):
            self.receiver = receiver

        def datagram_received(self, data: bytes, addr):
            receive_time = time.time()
            try:
                self.receiver._process_mjpeg_data(data, receive_time)
            except Exception as e:
                logger.error(f"Protocol datagram handling error: {e}", exc_info=True)

        def error_received(self, exc):
            logger.error(f"UDP error received: {exc}")

    def _ensure_loop_thread(self):
        if self._loop and self._loop_thread and self._loop_thread.is_alive():
            return
        self._loop = asyncio.new_event_loop()
        def run_loop(loop: asyncio.AbstractEventLoop):
            asyncio.set_event_loop(loop)
            loop.run_forever()
        self._loop_thread = threading.Thread(target=run_loop, args=(self._loop,), daemon=True)
        self._loop_thread.start()

    async def _connect_asyncio(self):
        if self.is_connected:
            await self._disconnect_asyncio()
        loop = asyncio.get_running_loop()
        listen = await loop.create_datagram_endpoint(
            lambda: OBS_UDP_Receiver._UDPProtocol(self),
            local_addr=(self.ip, self.port),
        )
        self._transport, self._protocol = listen
        self.is_connected = True
        self.is_receiving = True
        self.stop_event.clear()
        
        # Start thread pool executor for parallel frame decoding
        if self.executor is None:
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="FrameDecoder")
        
        # Start frame processing thread
        if not hasattr(self, 'processing_thread') or not self.processing_thread.is_alive():
            self.processing_thread = threading.Thread(target=self._frame_processing_loop, daemon=True)
            self.processing_thread.start()
        
        logger.info(f"[async] Connected to UDP stream at {self.ip}:{self.port}")
        return True

    async def _disconnect_asyncio(self):
        try:
            self.is_receiving = False
            self.is_connected = False
            self.stop_event.set()
            
            if self.executor:
                self.executor.shutdown(wait=False, cancel_futures=True)
                self.executor = None
            
            # Clear frame queue
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except Exception:
                    break
            
            if self._transport is not None:
                self._transport.close()
                await asyncio.sleep(0.1)  # Give transport time to close
                self._transport = None
            self._protocol = None
            
            # Clean up loop if no longer needed
            if self._loop and self._loop_thread and self._loop_thread.is_alive():
                self._loop.call_soon_threadsafe(self._loop.stop)
                self._loop_thread.join(timeout=2.0)
                self._loop = None
                self._loop_thread = None
            
            logger.info("[async] Disconnected from UDP stream")
        except Exception as e:
            logger.error(f"[async] Error during disconnect: {e}", exc_info=True)

    def connect_async(self) -> bool:
        """
        Start asyncio-based UDP receiving in a background event loop thread.
        Returns True if scheduling succeeded.
        """
        try:
            self._ensure_loop_thread()
            fut = asyncio.run_coroutine_threadsafe(self._connect_asyncio(), self._loop)
            return bool(fut.result(timeout=5.0))
        except asyncio.TimeoutError:
            logger.error("Async connect timeout")
            return False
        except Exception as e:
            logger.error(f"Failed to start async UDP receiver: {e}", exc_info=True)
            return False

    def disconnect_async(self):
        """Stop asyncio-based UDP receiving and close transport."""
        try:
            if self._loop:
                fut = asyncio.run_coroutine_threadsafe(self._disconnect_asyncio(), self._loop)
                try:
                    fut.result(timeout=3.0)
                except (asyncio.TimeoutError, Exception):
                    pass
        except Exception as e:
            logger.error(f"Error scheduling async disconnect: {e}", exc_info=True)
    
    def disconnect(self):
        """Disconnect from UDP stream"""
        try:
            self.is_connected = False
            self.is_receiving = False
            self.stop_event.set()
            
            if self.receive_thread and self.receive_thread.is_alive():
                self.receive_thread.join(timeout=2.0)
            
            if self.executor:
                self.executor.shutdown(wait=False, cancel_futures=True)
                self.executor = None
            
            # Clear frame queue
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except Exception:
                    break
            
            if self.socket:
                self.socket.close()
                self.socket = None
            
            # Clear buffer
            with self.buffer_lock:
                self.mjpeg_buffer.clear()
            
            # Clear current frame
            with self.frame_lock:
                self.current_frame = None
            
            logger.info("Disconnected from UDP stream")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}", exc_info=True)
    
    def _receive_loop(self):
        """Main receiving loop for UDP packets"""
        self.is_receiving = True
        logger.info("Started UDP receive loop")
        
        while not self.stop_event.is_set() and self.is_connected:
            try:
                # Receive UDP packet
                data, addr = self.socket.recvfrom(65536)  # Max UDP packet size
                receive_time = time.time()
                
                # Process MJPEG data
                self._process_mjpeg_data(data, receive_time)
                
            except socket.timeout:
                continue
            except OSError as e:
                if self.is_connected:
                    logger.error(f"Socket error in receive loop: {e}")
                break
            except Exception as e:
                if self.is_connected:
                    logger.error(f"Error in receive loop: {e}", exc_info=True)
                break
        
        self.is_receiving = False
        logger.info("UDP receive loop ended")
    
    def _frame_processing_loop(self):
        """Process decoded frames from thread pool in a separate thread"""
        logger.info("Started frame processing loop")
        
        while not self.stop_event.is_set() and self.is_connected:
            try:
                # Get next decoded frame from queue with timeout
                try:
                    future, receive_time = self.frame_queue.get(timeout=0.1)
                    # Wait for frame to be decoded
                    frame = future.result(timeout=1.0)
                    if frame is not None:
                        self._update_frame(frame, receive_time)
                except Exception:
                    continue  # Timeout or error, continue loop
                    
            except Exception as e:
                if self.is_connected:
                    logger.error(f"Error in frame processing loop: {e}", exc_info=True)
                continue
        
        logger.info("Frame processing loop ended")
    
    def _process_mjpeg_data(self, data: bytes, receive_time: float):
        """
        Process incoming MJPEG data and extract frames with improved error handling
        
        Args:
            data: Raw UDP packet data
            receive_time: Timestamp when data was received
        """
        try:
            # Add data to buffer with lock for thread safety
            with self.buffer_lock:
                self.mjpeg_buffer.extend(data)
                
                # Prevent buffer from growing too large
                buffer_len = len(self.mjpeg_buffer)
                if buffer_len > self.max_buffer_size:
                    logger.debug(f"MJPEG buffer too large ({buffer_len} bytes), clearing")
                    self.mjpeg_buffer.clear()
                    return
                
                # Work with local copy of buffer for processing
                buffer = bytes(self.mjpeg_buffer)
            
            # Look for complete JPEG frames
            frames_processed = 0
            max_frames_per_packet = 5  # Prevent infinite loops
            bytes_removed_from_start = 0  # Track how much we've removed from buffer start
            
            while frames_processed < max_frames_per_packet:
                start_pos = buffer.find(self.mjpeg_start_marker)
                if start_pos == -1:
                    # No start marker found, keep only last part of buffer
                    if len(buffer) > 2048:
                        with self.buffer_lock:
                            # Keep last 1024 bytes
                            if len(self.mjpeg_buffer) > 1024:
                                self.mjpeg_buffer = self.mjpeg_buffer[-1024:]
                    break
                
                # Remove data before start marker from buffer
                if start_pos > 0:
                    bytes_removed_from_start += start_pos
                    buffer = buffer[start_pos:]
                
                # Find end marker
                end_pos = buffer.find(self.mjpeg_end_marker, 2)
                if end_pos == -1:
                    # No complete frame yet, wait for more data
                    break
                
                # Extract complete JPEG frame
                jpeg_data = buffer[:end_pos + 2]
                frame_end_pos = end_pos + 2
                
                # Update buffer - remove processed data
                bytes_removed_from_start += frame_end_pos
                buffer = buffer[frame_end_pos:]
                
                # Validate JPEG data size and content
                if len(jpeg_data) < 100:  # Skip very small frames
                    continue
                
                # Additional validation: check for reasonable JPEG size
                if len(jpeg_data) > 10 * 1024 * 1024:  # 10MB limit per frame
                    logger.debug(f"JPEG frame too large: {len(jpeg_data)} bytes, skipping")
                    continue
                
                # Submit frame decoding to thread pool for parallel processing
                if self.executor and not self.stop_event.is_set():
                    future = self.executor.submit(self._decode_jpeg_frame, jpeg_data, receive_time)
                    # Store future with timestamp for processing
                    try:
                        self.frame_queue.put_nowait((future, receive_time))
                    except Exception:
                        # Queue full, skip this frame to maintain real-time performance
                        pass
                    frames_processed += 1
            
            # Update actual buffer in lock - remove all processed data at once
            if bytes_removed_from_start > 0:
                with self.buffer_lock:
                    if bytes_removed_from_start <= len(self.mjpeg_buffer):
                        self.mjpeg_buffer = self.mjpeg_buffer[bytes_removed_from_start:]
                
        except Exception as e:
            logger.error(f"Error processing MJPEG data: {e}", exc_info=True)
            # Clear buffer on error to prevent corruption
            with self.buffer_lock:
                self.mjpeg_buffer.clear()
    
    def _decode_jpeg_frame(self, jpeg_data: bytes, receive_time: float) -> Optional[np.ndarray]:
        """
        Decode JPEG data to OpenCV frame with robust error handling
        
        Args:
            jpeg_data: Raw JPEG data
            receive_time: Timestamp when data was received
            
        Returns:
            Decoded frame as numpy array or None if failed
        """
        try:
            # Validate JPEG data length
            if len(jpeg_data) < 100:  # Minimum reasonable JPEG size
                return None
            
            # Check for valid JPEG markers
            if not (jpeg_data.startswith(b'\xff\xd8') and jpeg_data.endswith(b'\xff\xd9')):
                return None
            
            # Fast path: TurboJPEG if available
            frame = None
            if _jpeg is not None:
                try:
                    frame = _jpeg.decode(jpeg_data, pixel_format=TJPF_BGR)
                except Exception:
                    pass  # Fall back to OpenCV
            
            if frame is None:
                # Convert bytes to numpy array
                nparr = np.frombuffer(jpeg_data, np.uint8)
                # Decode with OpenCV on CPU
                try:
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                except cv2.error:
                    try:
                        frame = cv2.imdecode(nparr, cv2.IMREAD_ANYCOLOR)
                    except cv2.error:
                        return None
            
            if frame is None or frame.size == 0:
                return None
            
            # Validate frame dimensions
            if len(frame.shape) < 2 or frame.shape[0] <= 0 or frame.shape[1] <= 0:
                return None
            
            height, width = frame.shape[:2]
            if height < 10 or width < 10 or height > 10000 or width > 10000:
                return None
            
            # Optimized corruption check - sample-based instead of full array scan
            if self._is_frame_corrupted(frame):
                return None
            
            # Calculate receive delay
            self.receive_delay = (time.time() - receive_time) * 1000  # Convert to ms
            return frame
            
        except cv2.error:
            pass  # Silently handle decode errors
        except Exception:
            pass  # Silently handle unexpected errors
        
        return None
    
    @staticmethod
    def _is_frame_corrupted(frame: np.ndarray) -> bool:
        """
        Fast corruption check using sampling instead of full array scan
        
        Args:
            frame: Frame to check
            
        Returns:
            True if frame appears corrupted
        """
        try:
            h, w = frame.shape[:2]
            # Sample corners and center instead of checking entire frame
            sample_points = [
                frame[0, 0], frame[0, -1], frame[-1, 0], frame[-1, -1],
                frame[h//2, w//2]
            ]
            # Check if all samples are the same (uniform frame)
            if len(set(tuple(sample) for sample in sample_points)) == 1:
                return True
            # Check if all samples are zero
            if all(np.all(sample == 0) for sample in sample_points):
                return True
            return False
        except Exception:
            return True  # Assume corrupted if check fails
    
    def _update_frame(self, frame: np.ndarray, receive_time: float):
        """
        Update current frame and trigger processing
        
        Args:
            frame: New frame
            receive_time: Timestamp when frame was received
        """
        try:
            with self.frame_lock:
                self.current_frame = frame.copy()
            
            # Update decoding FPS counter
            with self.processing_lock:
                self.decoding_counter += 1
                current_time = time.time()
                if current_time - self.last_decoding_time >= 1.0:
                    self.decoding_fps = self.decoding_counter / (current_time - self.last_decoding_time)
                    self.decoding_counter = 0
                    self.last_decoding_time = current_time
            
            # Update FPS counter
            self._update_fps_counters()
            
            # Trigger frame callback(s) if set (async execution for non-blocking)
            processing_start = time.time()
            if self.frame_callback_async and self._loop:
                try:
                    asyncio.run_coroutine_threadsafe(self.frame_callback_async(frame.copy()), self._loop)
                except Exception as e:
                    logger.error(f"Error scheduling async frame callback: {e}")
            if self.frame_callback:
                try:
                    # Callback in separate thread to avoid blocking
                    if self.executor:
                        self.executor.submit(self.frame_callback, frame.copy())
                    else:
                        self.frame_callback(frame.copy())
                except Exception as e:
                    logger.error(f"Frame callback error: {e}", exc_info=True)
            processing_end = time.time()

            # Calculate processing delay
            with self.processing_lock:
                self.processing_delay = (processing_end - processing_start) * 1000  # Convert to ms
                # Update processing FPS
                self.processing_counter += 1
                if processing_end - self.last_processing_time >= 1.0:
                    self.processing_fps = self.processing_counter / (processing_end - self.last_processing_time)
                    self.processing_counter = 0
                    self.last_processing_time = processing_end
            
        except Exception as e:
            logger.error(f"Error updating frame: {e}", exc_info=True)
    
    def _update_fps_counters(self):
        """Update FPS counters for monitoring"""
        current_time = time.time()
        self.fps_counter += 1
        
        if current_time - self.last_fps_time >= 1.0:
            self.current_fps = self.fps_counter / (current_time - self.last_fps_time)
            self.fps_counter = 0
            self.last_fps_time = current_time
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Get current frame
        
        Returns:
            Current frame or None if no frame available
        """
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def get_performance_stats(self) -> dict:
        """
        Get performance statistics
        
        Returns:
            Dictionary with performance metrics
        """
        with self.buffer_lock:
            buffer_size = len(self.mjpeg_buffer)
        
        with self.processing_lock:
            processing_fps = self.processing_fps
            processing_delay = self.processing_delay
            decoding_fps = self.decoding_fps
        
        return {
            'current_fps': self.current_fps,
            'processing_fps': processing_fps,
            'decoding_fps': decoding_fps,
            'target_fps': self.target_fps,
            'receive_delay_ms': self.receive_delay,
            'processing_delay_ms': processing_delay,
            'is_connected': self.is_connected,
            'is_receiving': self.is_receiving,
            'buffer_size_bytes': buffer_size,
            'queue_size': self.frame_queue.qsize(),
            'max_workers': self.max_workers
        }
    
    def set_target_fps(self, fps: int):
        """
        Set target FPS (deprecated, kept for compatibility - no longer enforced)
        
        Args:
            fps: Target FPS value (for monitoring only)
        """
        self.target_fps = max(1, fps)  # No upper limit, just for monitoring
        self.frame_interval = 1.0 / self.target_fps if self.target_fps > 0 else 0
        logger.info(f"Target FPS set to {self.target_fps} (monitoring only, no limit enforced)")
    
    def update_connection_params(self, ip: str, port: int):
        """
        Update connection parameters
        
        Args:
            ip: New IP address
            port: New port number
        """
        self.ip = ip
        self.port = port
        logger.info(f"Connection parameters updated: {ip}:{port}")


class OBS_UDP_Manager:
    """
    Manager class for OBS UDP connections
    Provides high-level interface for UDP stream management
    """
    
    def __init__(self):
        self.receiver = None
        self.is_connected = False
        
    def create_receiver(self, ip: str, port: int, target_fps: int = 60) -> OBS_UDP_Receiver:
        """
        Create new UDP receiver
        
        Args:
            ip: IP address
            port: Port number
            target_fps: Target FPS
            
        Returns:
            OBS_UDP_Receiver instance
        """
        self.receiver = OBS_UDP_Receiver(ip, port, target_fps)
        return self.receiver
    
    def connect(self, ip: str, port: int, target_fps: int = 60) -> bool:
        """
        Connect to UDP stream
        
        Args:
            ip: IP address
            port: Port number
            target_fps: Target FPS
            
        Returns:
            True if connection successful
        """
        if self.receiver:
            self.receiver.disconnect()
        
        self.receiver = OBS_UDP_Receiver(ip, port, target_fps)
        success = self.receiver.connect()
        self.is_connected = success
        return success

    # -------------------- Async helpers --------------------
    def connect_async(self, ip: str, port: int, target_fps: int = 60) -> bool:
        """Connect using asyncio-based receiver running in background loop thread."""
        if self.receiver:
            try:
                self.receiver.disconnect_async()
            except Exception:
                pass
        self.receiver = OBS_UDP_Receiver(ip, port, target_fps)
        success = self.receiver.connect_async()
        self.is_connected = success
        return success

    def disconnect_async(self):
        if self.receiver:
            self.receiver.disconnect_async()
            self.receiver = None
        self.is_connected = False
    
    def disconnect(self):
        """Disconnect from UDP stream"""
        if self.receiver:
            self.receiver.disconnect()
            self.receiver = None
        self.is_connected = False
    
    def get_receiver(self) -> Optional[OBS_UDP_Receiver]:
        """Get current receiver instance"""
        return self.receiver
    
    def is_stream_active(self) -> bool:
        """Check if stream is active"""
        return self.is_connected and self.receiver and self.receiver.is_receiving
