from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import os
import docker
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
import requests
from contextlib import asynccontextmanager

# Global Docker client
docker_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global docker_client
    try:
        # Initialize Docker client
        docker_client = docker.from_env()
        # Test connection
        docker_client.ping()
        print("✅ Docker client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Docker client: {e}")
        docker_client = None
    
    yield
    
    # Cleanup
    if docker_client:
        docker_client.close()

app = FastAPI(lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URL)
db = client['docker_monitor']

# Background images collection
BACKGROUND_IMAGES = [
    "https://images.unsplash.com/photo-1661064941810-7a62f443fdb1",
    "https://images.unsplash.com/photo-1561765781-f7de2b8c56a5",
    "https://images.unsplash.com/photo-1527998257557-0c18b22fa4cc",
    "https://images.unsplash.com/photo-1468581264429-2548ef9eb732",
    "https://images.unsplash.com/photo-1648726442906-b0b33ad693d7"
]

@app.get("/")
async def root():
    return {"message": "Docker Monitor API"}

@app.get("/api/docker/status")
async def docker_status():
    """Check if Docker is accessible"""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker client not available")
    
    try:
        info = docker_client.info()
        return {
            "status": "connected",
            "containers_running": info.get("ContainersRunning", 0),
            "containers_paused": info.get("ContainersPaused", 0),
            "containers_stopped": info.get("ContainersStopped", 0),
            "images": info.get("Images", 0),
            "server_version": info.get("ServerVersion", "unknown"),
            "kernel_version": info.get("KernelVersion", "unknown"),
            "architecture": info.get("Architecture", "unknown")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Docker connection error: {str(e)}")

@app.get("/api/containers")
async def get_containers():
    """Get all containers (running and stopped)"""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker client not available")
    
    try:
        containers = docker_client.containers.list(all=True)
        container_list = []
        
        for container in containers:
            # Get basic container info
            container_info = {
                "id": container.id,
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "status": container.status,
                "state": container.attrs["State"]["Status"],
                "created": container.attrs["Created"],
                "ports": container.attrs.get("NetworkSettings", {}).get("Ports", {}),
                "labels": container.attrs.get("Config", {}).get("Labels", {}),
                "short_id": container.short_id
            }
            
            # Get uptime if running
            if container.status == "running":
                started_at = container.attrs["State"]["StartedAt"]
                if started_at:
                    start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    uptime = datetime.now().replace(tzinfo=start_time.tzinfo) - start_time
                    container_info["uptime"] = str(uptime).split('.')[0]  # Remove microseconds
            
            container_list.append(container_info)
        
        return {"containers": container_list}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get containers: {str(e)}")

@app.get("/api/containers/{container_id}/stats")
async def get_container_stats(container_id: str):
    """Get container resource usage stats"""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker client not available")
    
    try:
        container = docker_client.containers.get(container_id)
        stats = container.stats(stream=False)
        
        # Calculate CPU usage percentage
        cpu_percent = 0
        if "cpu_stats" in stats and "precpu_stats" in stats:
            cpu_stats = stats["cpu_stats"]
            precpu_stats = stats["precpu_stats"]
            
            if "cpu_usage" in cpu_stats and "cpu_usage" in precpu_stats:
                cpu_delta = cpu_stats["cpu_usage"]["total_usage"] - precpu_stats["cpu_usage"]["total_usage"]
                system_delta = cpu_stats["system_cpu_usage"] - precpu_stats["system_cpu_usage"]
                
                if system_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * len(cpu_stats["cpu_usage"]["percpu_usage"]) * 100
        
        # Calculate memory usage
        memory_usage = 0
        memory_limit = 0
        memory_percent = 0
        
        if "memory_stats" in stats:
            memory_stats = stats["memory_stats"]
            memory_usage = memory_stats.get("usage", 0)
            memory_limit = memory_stats.get("limit", 0)
            if memory_limit > 0:
                memory_percent = (memory_usage / memory_limit) * 100
        
        # Network I/O
        network_rx = 0
        network_tx = 0
        if "networks" in stats:
            for interface in stats["networks"].values():
                network_rx += interface.get("rx_bytes", 0)
                network_tx += interface.get("tx_bytes", 0)
        
        return {
            "container_id": container_id,
            "cpu_percent": round(cpu_percent, 2),
            "memory_usage": memory_usage,
            "memory_limit": memory_limit,
            "memory_percent": round(memory_percent, 2),
            "network_rx": network_rx,
            "network_tx": network_tx,
            "timestamp": datetime.now().isoformat()
        }
    
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get container stats: {str(e)}")

@app.get("/api/containers/{container_id}/logs")
async def get_container_logs(container_id: str, tail: int = 100):
    """Get container logs"""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker client not available")
    
    try:
        container = docker_client.containers.get(container_id)
        logs = container.logs(tail=tail, timestamps=True).decode('utf-8')
        
        return {
            "container_id": container_id,
            "logs": logs,
            "tail": tail
        }
    
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get container logs: {str(e)}")

@app.get("/api/containers/{container_id}/inspect")
async def get_container_inspect(container_id: str):
    """Get detailed container information"""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker client not available")
    
    try:
        container = docker_client.containers.get(container_id)
        return {
            "container_id": container_id,
            "inspect": container.attrs
        }
    
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect container: {str(e)}")

@app.get("/api/images")
async def get_images():
    """Get all Docker images"""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker client not available")
    
    try:
        images = docker_client.images.list()
        image_list = []
        
        for image in images:
            tags = image.tags if image.tags else ["<none>:<none>"]
            for tag in tags:
                image_info = {
                    "id": image.id,
                    "short_id": image.short_id,
                    "tag": tag,
                    "created": image.attrs["Created"],
                    "size": image.attrs["Size"],
                    "virtual_size": image.attrs.get("VirtualSize", image.attrs["Size"]),
                    "labels": image.attrs.get("Config", {}).get("Labels", {}),
                    "architecture": image.attrs.get("Architecture", "unknown")
                }
                image_list.append(image_info)
        
        return {"images": image_list}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get images: {str(e)}")

@app.get("/api/background-image")
async def get_background_image():
    """Get a random background image"""
    import random
    return {"image_url": random.choice(BACKGROUND_IMAGES)}

@app.get("/api/images/{image_name}/check-updates")
async def check_image_updates(image_name: str):
    """Check for image updates on Docker Hub"""
    try:
        # Parse image name
        if ":" in image_name:
            repo, tag = image_name.split(":", 1)
        else:
            repo = image_name
            tag = "latest"
        
        # Check Docker Hub API
        if "/" not in repo:
            # Official image
            api_url = f"https://registry.hub.docker.com/v2/repositories/library/{repo}/tags/"
        else:
            # User/organization image
            api_url = f"https://registry.hub.docker.com/v2/repositories/{repo}/tags/"
        
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            tags = [tag_info["name"] for tag_info in data.get("results", [])]
            
            return {
                "image": image_name,
                "available_tags": tags[:10],  # Limit to 10 most recent
                "has_updates": len(tags) > 0,
                "registry": "Docker Hub"
            }
        else:
            return {
                "image": image_name,
                "available_tags": [],
                "has_updates": False,
                "registry": "Docker Hub",
                "error": f"HTTP {response.status_code}"
            }
    
    except Exception as e:
        return {
            "image": image_name,
            "available_tags": [],
            "has_updates": False,
            "registry": "Docker Hub",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)