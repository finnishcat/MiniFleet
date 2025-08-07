from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import os
import docker
import asyncio
import json
import yaml
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from contextlib import asynccontextmanager
import time
from pydantic import BaseModel

# Global Docker clients for multiple servers
docker_clients = {}
default_client = None

class DockerServer(BaseModel):
    id: str
    name: str
    host: str
    port: int = 2376
    use_tls: bool = False
    cert_path: Optional[str] = None
    active: bool = True

class RegistryConfig(BaseModel):
    id: str
    name: str
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    active: bool = True

class DeploymentRequest(BaseModel):
    image: str
    tag: str
    container_name: str
    ports: List[str] = []
    environment: List[str] = []
    volumes: List[str] = []
    server_id: str = "local"

@asynccontextmanager
async def lifespan(app: FastAPI):
    global default_client, docker_clients
    try:
        # Initialize local Docker client
        default_client = docker.from_env()
        default_client.ping()
        docker_clients["local"] = default_client
        print("✅ Local Docker client initialized successfully")
        
        # Load configured Docker servers from database
        await load_docker_servers()
        
    except Exception as e:
        print(f"❌ Failed to initialize Docker client: {e}")
        default_client = None
    
    yield
    
    # Cleanup
    for client in docker_clients.values():
        if client:
            client.close()

async def load_docker_servers():
    """Load Docker servers from database and initialize clients"""
    global docker_clients
    try:
        servers = list(db['docker_servers'].find({"active": True}))
        for server in servers:
            try:
                if server['id'] != 'local':
                    # Connect to remote Docker server
                    base_url = f"tcp://{server['host']}:{server['port']}"
                    if server.get('use_tls', False):
                        # Add TLS configuration
                        tls_config = docker.tls.TLSConfig(
                            client_cert=(server.get('cert_path', ''), server.get('cert_path', '')),
                            verify=False
                        )
                        client = docker.DockerClient(base_url=base_url, tls=tls_config)
                    else:
                        client = docker.DockerClient(base_url=base_url)
                    
                    client.ping()
                    docker_clients[server['id']] = client
                    print(f"✅ Connected to Docker server: {server['name']}")
            except Exception as e:
                print(f"❌ Failed to connect to {server['name']}: {e}")
    except Exception as e:
        print(f"❌ Failed to load Docker servers: {e}")

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

# Collections
notifications_collection = db['notifications']
image_updates_collection = db['image_updates']
docker_servers_collection = db['docker_servers']
registries_collection = db['registries']

# Background images collection
BACKGROUND_IMAGES = [
    "https://images.unsplash.com/photo-1661064941810-7a62f443fdb1",
    "https://images.unsplash.com/photo-1561765781-f7de2b8c56a5",
    "https://images.unsplash.com/photo-1527998257557-0c18b22fa4cc",
    "https://images.unsplash.com/photo-1468581264429-2548ef9eb732",
    "https://images.unsplash.com/photo-1648726442906-b0b33ad693d7"
]

def get_docker_client(server_id: str = "local"):
    """Get Docker client for specified server"""
    return docker_clients.get(server_id, default_client)

@app.get("/")
async def root():
    return {"message": "Docker Monitor API - Multi-Server Support"}

# ========== DOCKER SERVER MANAGEMENT ==========

@app.get("/api/docker/servers")
async def get_docker_servers():
    """Get all configured Docker servers"""
    try:
        servers = list(docker_servers_collection.find({}, {"_id": 0}))
        # Add local server if not in database
        local_exists = any(s['id'] == 'local' for s in servers)
        if not local_exists:
            servers.insert(0, {
                "id": "local",
                "name": "Local Server",
                "host": "localhost",
                "port": 2376,
                "use_tls": False,
                "active": True,
                "connected": "local" in docker_clients
            })
        
        # Add connection status
        for server in servers:
            server["connected"] = server["id"] in docker_clients
        
        return {"servers": servers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Docker servers: {str(e)}")

@app.post("/api/docker/servers")
async def add_docker_server(server: DockerServer):
    """Add a new Docker server"""
    try:
        # Check if server ID already exists
        existing = docker_servers_collection.find_one({"id": server.id})
        if existing:
            raise HTTPException(status_code=400, detail="Server ID already exists")
        
        # Try to connect to the server
        try:
            base_url = f"tcp://{server.host}:{server.port}"
            if server.use_tls:
                tls_config = docker.tls.TLSConfig(
                    client_cert=(server.cert_path, server.cert_path) if server.cert_path else None,
                    verify=False
                )
                test_client = docker.DockerClient(base_url=base_url, tls=tls_config)
            else:
                test_client = docker.DockerClient(base_url=base_url)
            
            test_client.ping()
            docker_clients[server.id] = test_client
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot connect to Docker server: {str(e)}")
        
        # Save to database
        server_data = server.dict()
        docker_servers_collection.insert_one(server_data)
        
        return {"success": True, "message": f"Docker server {server.name} added successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add Docker server: {str(e)}")

@app.delete("/api/docker/servers/{server_id}")
async def remove_docker_server(server_id: str):
    """Remove a Docker server"""
    try:
        if server_id == "local":
            raise HTTPException(status_code=400, detail="Cannot remove local server")
        
        # Remove from database
        result = docker_servers_collection.delete_one({"id": server_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Close connection
        if server_id in docker_clients:
            docker_clients[server_id].close()
            del docker_clients[server_id]
        
        return {"success": True, "message": f"Docker server removed successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove Docker server: {str(e)}")

# ========== REGISTRY MANAGEMENT ==========

@app.get("/api/registries")
async def get_registries():
    """Get all configured registries"""
    try:
        registries = list(registries_collection.find({}, {"_id": 0, "password": 0}))
        # Add Docker Hub as default
        hub_exists = any(r['id'] == 'dockerhub' for r in registries)
        if not hub_exists:
            registries.insert(0, {
                "id": "dockerhub",
                "name": "Docker Hub",
                "url": "https://registry.hub.docker.com",
                "active": True
            })
        return {"registries": registries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get registries: {str(e)}")

@app.post("/api/registries")
async def add_registry(registry: RegistryConfig):
    """Add a new registry"""
    try:
        # Check if registry ID already exists
        existing = registries_collection.find_one({"id": registry.id})
        if existing:
            raise HTTPException(status_code=400, detail="Registry ID already exists")
        
        # Save to database
        registry_data = registry.dict()
        registries_collection.insert_one(registry_data)
        
        return {"success": True, "message": f"Registry {registry.name} added successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add registry: {str(e)}")

# ========== MULTI-SERVER DOCKER OPERATIONS ==========

@app.get("/api/docker/status")
async def docker_status(server_id: str = "local"):
    """Check if Docker is accessible on specified server"""
    docker_client = get_docker_client(server_id)
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker client not available")
    
    try:
        info = docker_client.info()
        return {
            "server_id": server_id,
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
async def get_containers(server_id: str = "local"):
    """Get all containers from specified server"""
    docker_client = get_docker_client(server_id)
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker client not available")
    
    try:
        containers = docker_client.containers.list(all=True)
        container_list = []
        
        for container in containers:
            container_info = {
                "id": container.id,
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "status": container.status,
                "state": container.attrs["State"]["Status"],
                "created": container.attrs["Created"],
                "ports": container.attrs.get("NetworkSettings", {}).get("Ports", {}),
                "labels": container.attrs.get("Config", {}).get("Labels", {}),
                "short_id": container.short_id,
                "server_id": server_id
            }
            
            if container.status == "running":
                started_at = container.attrs["State"]["StartedAt"]
                if started_at:
                    start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    uptime = datetime.now().replace(tzinfo=start_time.tzinfo) - start_time
                    container_info["uptime"] = str(uptime).split('.')[0]
            
            container_list.append(container_info)
        
        return {"containers": container_list, "server_id": server_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get containers: {str(e)}")

@app.get("/api/images")
async def get_images(server_id: str = "local"):
    """Get all Docker images from specified server"""
    docker_client = get_docker_client(server_id)
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
                    "architecture": image.attrs.get("Architecture", "unknown"),
                    "server_id": server_id
                }
                image_list.append(image_info)
        
        return {"images": image_list, "server_id": server_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get images: {str(e)}")

# ========== ENHANCED DEPLOYMENT WORKFLOW ==========

@app.post("/api/deploy")
async def deploy_container(deployment: DeploymentRequest):
    """Deploy a new container from image"""
    docker_client = get_docker_client(deployment.server_id)
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker client not available")
    
    try:
        # Pull image first
        image_ref = f"{deployment.image}:{deployment.tag}"
        try:
            docker_client.images.pull(image_ref)
        except Exception as pull_error:
            print(f"Warning: Could not pull image {image_ref}: {pull_error}")
        
        # Parse ports
        port_bindings = {}
        ports = []
        for port_mapping in deployment.ports:
            if ":" in port_mapping:
                host_port, container_port = port_mapping.split(":", 1)
                port_bindings[container_port] = host_port
                ports.append(container_port)
        
        # Parse volumes
        volumes = {}
        for volume_mapping in deployment.volumes:
            if ":" in volume_mapping:
                host_path, container_path = volume_mapping.split(":", 1)
                volumes[host_path] = {"bind": container_path, "mode": "rw"}
        
        # Parse environment variables
        environment = {}
        for env_var in deployment.environment:
            if "=" in env_var:
                key, value = env_var.split("=", 1)
                environment[key] = value
        
        # Create and start container
        container = docker_client.containers.run(
            image_ref,
            name=deployment.container_name,
            ports=port_bindings,
            volumes=volumes,
            environment=environment,
            detach=True,
            remove=False
        )
        
        # Create notification
        notification = {
            "id": f"deploy-{int(time.time())}",
            "type": "success",
            "title": "Container Deployed",
            "message": f"Successfully deployed {deployment.container_name} from {image_ref}",
            "created_at": datetime.now().isoformat(),
            "read": False,
            "server_id": deployment.server_id
        }
        notifications_collection.insert_one(notification)
        
        return {
            "success": True,
            "container_id": container.id,
            "container_name": deployment.container_name,
            "image": image_ref,
            "server_id": deployment.server_id,
            "message": f"Container {deployment.container_name} deployed successfully"
        }
    
    except Exception as e:
        # Create error notification
        notification = {
            "id": f"deploy-error-{int(time.time())}",
            "type": "error",
            "title": "Deployment Failed",
            "message": f"Failed to deploy {deployment.container_name}: {str(e)}",
            "created_at": datetime.now().isoformat(),
            "read": False,
            "server_id": deployment.server_id
        }
        notifications_collection.insert_one(notification)
        
        raise HTTPException(status_code=500, detail=f"Failed to deploy container: {str(e)}")

@app.get("/api/images/{image_name}/tags")
async def get_image_tags(image_name: str, registry_id: str = "dockerhub"):
    """Get available tags for an image from registry"""
    try:
        # Get registry config
        if registry_id == "dockerhub":
            base_url = "https://registry.hub.docker.com/v2/repositories"
        else:
            registry = registries_collection.find_one({"id": registry_id})
            if not registry:
                raise HTTPException(status_code=404, detail="Registry not found")
            base_url = registry["url"]
        
        # Parse image name
        if "/" not in image_name:
            # Official image
            api_url = f"{base_url}/library/{image_name}/tags/"
        else:
            # User/organization image
            api_url = f"{base_url}/{image_name}/tags/"
        
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            tags = []
            
            for tag_info in data.get("results", [])[:20]:  # Limit to 20 most recent
                tags.append({
                    "name": tag_info["name"],
                    "last_updated": tag_info.get("last_updated"),
                    "full_size": tag_info.get("full_size", 0),
                    "architecture": tag_info.get("images", [{}])[0].get("architecture", "amd64") if tag_info.get("images") else "amd64"
                })
            
            return {
                "image": image_name,
                "registry": registry_id,
                "tags": tags,
                "total_count": len(tags)
            }
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Registry error: {response.status_code}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get image tags: {str(e)}")

# ========== KEEP EXISTING ENDPOINTS ==========
# (Previous endpoints for stats, logs, YAML, notifications, etc.)

@app.get("/api/containers/{container_id}/stats")
async def get_container_stats(container_id: str, server_id: str = "local"):
    """Get container resource usage stats"""
    docker_client = get_docker_client(server_id)
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
            "server_id": server_id,
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
async def get_container_logs(container_id: str, server_id: str = "local", tail: int = 200):
    """Get container logs"""
    docker_client = get_docker_client(server_id)
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker client not available")
    
    try:
        container = docker_client.containers.get(container_id)
        logs = container.logs(tail=tail, timestamps=True, follow=False).decode('utf-8')
        
        return {
            "container_id": container_id,
            "server_id": server_id,
            "logs": logs,
            "tail": tail
        }
    
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get container logs: {str(e)}")

@app.get("/api/containers/{container_id}/yaml")
async def get_container_yaml(container_id: str, server_id: str = "local"):
    """Get container configuration as YAML"""
    docker_client = get_docker_client(server_id)
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker client not available")
    
    try:
        container = docker_client.containers.get(container_id)
        inspect_data = container.attrs
        
        yaml_data = {
            "version": "3.8",
            "services": {
                inspect_data["Name"].lstrip("/"): {
                    "image": inspect_data["Config"]["Image"],
                    "container_name": inspect_data["Name"].lstrip("/"),
                    "restart": "unless-stopped",
                    "environment": inspect_data["Config"].get("Env", []),
                    "ports": [],
                    "volumes": [],
                    "networks": list(inspect_data.get("NetworkSettings", {}).get("Networks", {}).keys()),
                    "labels": inspect_data["Config"].get("Labels", {}),
                }
            }
        }
        
        yaml_string = yaml.dump(yaml_data, default_flow_style=False, indent=2)
        
        return {
            "container_id": container_id,
            "server_id": server_id,
            "yaml": yaml_string
        }
    
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get container YAML: {str(e)}")

@app.post("/api/containers/{container_id}/restart")
async def restart_container(container_id: str, server_id: str = "local"):
    """Restart a container"""
    docker_client = get_docker_client(server_id)
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker client not available")
    
    try:
        container = docker_client.containers.get(container_id)
        container.restart()
        
        return {
            "success": True,
            "container_id": container_id,
            "server_id": server_id,
            "message": f"Container {container.name} restarted successfully"
        }
    
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart container: {str(e)}")

@app.get("/api/notifications")
async def get_notifications():
    """Get all notifications"""
    try:
        notifications = list(notifications_collection.find({}, {"_id": 0}).sort("created_at", -1).limit(50))
        return {"notifications": notifications}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get notifications: {str(e)}")

@app.get("/api/background-image")
async def get_background_image():
    """Get a random background image"""
    import random
    return {"image_url": random.choice(BACKGROUND_IMAGES)}

@app.get("/api/images/{image_name}/check-updates")
async def check_image_updates(image_name: str, registry_id: str = "dockerhub"):
    """Check for image updates"""
    try:
        if ":" in image_name:
            repo, current_tag = image_name.split(":", 1)
        else:
            repo = image_name
            current_tag = "latest"
        
        # Get tags from registry
        tags_response = await get_image_tags(repo, registry_id)
        available_tags = tags_response["tags"]
        
        has_updates = len([t for t in available_tags if t["name"] != current_tag]) > 0
        
        return {
            "image": image_name,
            "current_tag": current_tag,
            "available_tags": available_tags[:10],
            "has_updates": has_updates,
            "registry": registry_id,
            "last_checked": datetime.now().isoformat()
        }
    
    except Exception as e:
        return {
            "image": image_name,
            "available_tags": [],
            "has_updates": False,
            "registry": registry_id,
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)