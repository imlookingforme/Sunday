"""Server-Sent Events (SSE) for real-time dashboard updates."""

import asyncio
import json
from typing import AsyncGenerator


async def sse_event_generator(state) -> AsyncGenerator[str, None]:
    """Generate SSE events for real-time dashboard updates.
    
    This replaces polling loops with a single SSE connection,
    significantly reducing server load and improving responsiveness.
    """
    last_orb_state = None
    last_intelligence_data = {}
    
    try:
        while True:
            # Check for orb state changes
            if state.orb_state != last_orb_state:
                event = {
                    "type": "orb_state_change",
                    "state": state.orb_state,
                    "timestamp": asyncio.get_event_loop().time()
                }
                yield f"event: orb_state\ndata: {json.dumps(event)}\n\n"
                last_orb_state = state.orb_state
            
            # Check for intelligence module updates
            for module, data in state.intelligence_data.items():
                if module not in last_intelligence_data or last_intelligence_data[module] != data:
                    event = {
                        "type": "intelligence_update",
                        "module": module,
                        "data": data,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    yield f"event: intelligence\ndata: {json.dumps(event)}\n\n"
                    last_intelligence_data[module] = data
            
            # Send heartbeat every 5 seconds to keep connection alive
            yield f"event: heartbeat\ndata: {json.dumps({'timestamp': asyncio.get_event_loop().time()})}\n\n"
            
            # Wait before next check
            await asyncio.sleep(0.5)
    
    except asyncio.CancelledError:
        # Client disconnected
        state.remove_client()
        yield f"event: disconnect\ndata: {json.dumps({'message': 'Client disconnected'})}\n\n"
